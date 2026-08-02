#!/usr/bin/env python3
"""Corrected 20-day run: watchlists from consistently-adjusted daily bars.

Changes from run20.py, all of them fixes for the window-stitching bug:

  gap        measured open-vs-previous-close inside ONE daily response, so both
             prices share an adjustment basis. Still known at 09:35.
  splits     any symbol-day within 3 trading days of a split is dropped, and a
             hard +200% sanity cap catches adjustment artifacts the split
             calendar missed.
  volume     the RVOL denominator is a trailing 10-session average from the same
             daily response, not from the stitched 1-minute data.

Intraday execution still uses the 1-minute bars, which are internally
consistent within a single day - the stitching bug only ever corrupted
comparisons ACROSS days.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import datetime as dt
import json
import os
import sys
from collections import defaultdict


from engine20 import run_day
from run20 import fetch_symbol
from concurrent.futures import ThreadPoolExecutor

OUT = _DATA
# The playbook's "3-5 names" is what one person can watch; the source scans the
# whole market to find them. Widening changes how many candidates the engine
# SEES, not how many trades it may take - the trade limit still binds.
MAX_NAMES = int(os.environ.get('WATCH_NAMES', 5))
# PARAMETERS.md:20 states price_min >= 2.00 (n=144) and records "1.00 also
# stated" in the same row. PRICE_MIN switches between the corpus's two values.
PRICE_MIN = float(os.environ.get('PRICE_MIN', 2.0))

# Not a documented rule - a guard added to catch the reverse-split artifacts of
# HISTORY defect 1. It also rejected LABT's real +249% move, so it is switchable.
GAP_SANITY_CAP = float(os.environ.get('GAP_CAP', 200.0))
SPLIT_BUFFER = 3              # trading days either side of a split


def build(stats, daily, shares_out):
    v5_by = {(r['sym'], r['day']): r['v5'] for r in stats}
    days_all = sorted({r['day'] for r in stats})

    byday = defaultdict(list)
    for sym, d in daily.items():
        rows = d['rows']
        idx = {r['day']: i for i, r in enumerate(rows)}
        split_days = set()
        for sd in d['splits']:
            if sd in idx:
                i = idx[sd]
                for j in range(max(0, i - SPLIT_BUFFER),
                               min(len(rows), i + SPLIT_BUFFER + 1)):
                    split_days.add(rows[j]['day'])
            else:
                split_days.add(sd)

        for i, r in enumerate(rows):
            day = r['day']
            if day not in days_all or i == 0 or day in split_days:
                continue
            prev = rows[i - 1]
            if not prev['c']:
                continue
            gap = (r['o'] / prev['c'] - 1) * 100
            if gap < 10.0 or gap > GAP_SANITY_CAP:
                continue
            if not (PRICE_MIN <= r['o'] <= 20.0):
                continue
            so = shares_out.get(sym, 0)
            if not so or so > 20e6:
                continue
            hist = rows[max(0, i - 10):i]
            avg = sum(x['v'] for x in hist) / len(hist) if hist else 0
            v5 = v5_by.get((sym, day))
            if not avg or v5 is None:
                continue
            rvol5 = v5 / (avg * 5 / 390)
            if rvol5 < 5.0:
                continue

            byday[day].append(dict(sym=sym, day=day, gap_pct=round(gap, 2),
                                   open_px=r['o'], rvol5=round(rvol5, 1)))

    return {d: sorted(v, key=lambda r: -r['gap_pct'])[:MAX_NAMES]
            for d, v in sorted(byday.items())}


def main():
    limits = [int(x) for x in sys.argv[1:]] or [5]
    stats = json.load(open(os.path.join(OUT, 'scan20_stats.json')))
    daily = json.load(open(os.path.join(OUT, 'daily20.json')))
    pool = {c['sym']: c for c in json.load(open(os.path.join(OUT, 'pool20.json')))}
    shares_out = {s: c['mcap'] / c['price'] for s, c in pool.items() if c['price']}

    lists = build(stats, daily, shares_out)
    all_days = sorted({r['day'] for r in stats})
    for d in all_days:
        lists.setdefault(d, [])
    lists = dict(sorted(lists.items()))

    need = sorted({r['sym'] for v in lists.values() for r in v})
    print(f'{len(lists)} trading days, {len(need)} distinct symbols\n')
    for day, rows in lists.items():
        s = ', '.join(f"{r['sym']}(+{r['gap_pct']:.0f}%,{r['rvol5']:.0f}x)"
                      for r in rows)
        print(f'  {day}  {s or "-- no qualifying names --"}')

    bars = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        for sym, d in ex.map(fetch_symbol, need):
            bars[sym] = d
    # rate_of_change_min > 0 - "% gain per minute, rising" (PARAMETERS.md sec.1).
    # The corpus gives the SIGN but no magnitude, so this is expressed without a
    # threshold: at 09:35, is the stock higher than it opened? A name that has
    # broken from its pre-market high is falling by then, not rising, which is
    # what "faded from pre-market high" (PARAMETERS.md:31, a documented REJECT)
    # describes. Uses only 09:30-09:34 bars, so it is known when trading starts.
    dropped = 0
    for day in list(lists):
        keep = []
        for r in lists[day]:
            d = bars.get(r['sym'], {}).get(day)
            first5 = [b for b in (d or {}).get('session', [])
                      if b['dt'].time() < dt.time(9, 35)]
            if not first5:
                continue
            if first5[-1]['c'] > first5[0]['o']:      # rising
                keep.append(r)
            else:
                dropped += 1
        lists[day] = keep
    print(f'\nfetched {len(bars)} symbols; rate-of-change <= 0 dropped '
          f'{dropped} name-days\n', flush=True)

    # Persist AFTER every selection rule has been applied, so the audit and
    # the diagnostics replay exactly the watchlist the run traded.
    json.dump(lists, open(os.path.join(OUT, 'watchlists20.json'), 'w'), indent=1)


    for mt in limits:
        results = []
        for day, rows in lists.items():
            watch = [r['sym'] for r in rows]
            if not watch:
                results.append(dict(day=day, pnl=0.0, trades=[], setups=0,
                                    passes=0, halted='no watchlist',
                                    rejects={}, watch=[]))
                continue
            per = {s: bars[s][day] for s in watch
                   if s in bars and day in bars[s]}
            log = []
            res = run_day(dt.date(*map(int, day.split('-'))), watch, per, mt, log)
            res['log'] = log
            results.append(res)
        json.dump(dict(max_trades=mt, results=results),
                  open(os.path.join(OUT, f'run20_max{mt}.json'), 'w'),
                  indent=1, default=str)
        tot = sum(r['pnl'] for r in results)
        n = sum(len(r['trades']) for r in results)
        print(f'=== max_trades={mt}: {len(results)} days | {n} trades | '
              f'total ${tot:+.2f} ===', flush=True)


if __name__ == '__main__':
    main()
