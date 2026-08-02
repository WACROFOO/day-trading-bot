#!/usr/bin/env python3
"""Test run over one week: 2026-07-27 .. 2026-07-31.

Same engine, same data, same rules as the 17-day run - just scoped to the five
most recent trading sessions and reported day by day.

Usage:
    python pipeline/week.py            # playbook default, 2 trades/day
    python pipeline/week.py 5          # 5 trades/day
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402

import datetime as dt
import json
from concurrent.futures import ThreadPoolExecutor

from engine20 import run_day
from run20 import fetch_symbol
from run20b import build

OUT = _DATA
WEEKS = {
    '07-27': ['2026-07-27', '2026-07-28', '2026-07-29', '2026-07-30', '2026-07-31'],
    '07-20': ['2026-07-20', '2026-07-21', '2026-07-22', '2026-07-23', '2026-07-24'],
}
WEEK = WEEKS[os.environ.get('WEEK', '07-27')]
ACCOUNT = 10_000.0


def main():
    max_trades = int(sys.argv[1]) if len(sys.argv) > 1 else 2

    stats = json.load(open(os.path.join(OUT, 'scan20_stats.json')))
    daily = json.load(open(os.path.join(OUT, 'daily20.json')))
    pool = {c['sym']: c for c in json.load(open(os.path.join(OUT, 'pool20.json')))}
    shares_out = {s: c['mcap'] / c['price'] for s, c in pool.items() if c['price']}
    lists = {d: v for d, v in build(stats, daily, shares_out).items() if d in WEEK}

    need = sorted({r['sym'] for v in lists.values() for r in v})
    bars = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        for sym, d in ex.map(fetch_symbol, need):
            bars[sym] = d

    # Same rate_of_change > 0 confirmation run20b applies after fetching
    # (PARAMETERS.md sec.1). Without it this runner silently traded a wider
    # watchlist than the pipeline, and reported 3 trades where the audited
    # 17-day run reported 2.
    # ROC_ONCE=0 disables this. §1 is the UNIVERSE FILTER - a scanner
    # criterion, and a scanner runs continuously through the session rather
    # than once at 09:35. Applying it as a one-shot exclusion kills a name for
    # the whole day because it was soft in its first five minutes, which is a
    # different rule from the one stated. Both readings are run below.
    dropped = 0
    for day in ([] if os.environ.get('ROC_ONCE') == '0' else list(lists)):
        keep = []
        for r in lists[day]:
            d = bars.get(r['sym'], {}).get(day)
            first5 = [b for b in (d or {}).get('session', [])
                      if b['dt'].time() < dt.time(9, 35)]
            if first5 and first5[-1]['c'] > first5[0]['o']:
                keep.append(r)
            else:
                dropped += 1
        lists[day] = keep

    print(f'=== week of {WEEK[0]}, max {max_trades} trades/day, '
          f'${ACCOUNT:,.0f} account ===')
    print(f'(rate-of-change <= 0 dropped {dropped} name-days)\n')
    print(f'{"day":<12}{"watchlist":<44}{"setups":>7}{"pass":>5}{"trades":>7}{"P&L":>10}')
    results, equity = [], 0.0
    for day in WEEK:
        rows = lists.get(day, [])
        watch = [r['sym'] for r in rows]
        names = ', '.join(f'{r["sym"]}(+{r["gap_pct"]:.0f}%)' for r in rows) or '—'
        if not watch:
            print(f'{day:<12}{names[:43]:<44}{"—":>7}{"—":>5}{"—":>7}{"0.00":>10}')
            results.append(dict(day=day, pnl=0.0, trades=[], setups=0, passes=0))
            continue
        per = {s: bars[s][day] for s in watch if s in bars and day in bars[s]}
        log = []
        res = run_day(dt.date(*map(int, day.split('-'))), watch, per,
                      max_trades, log)
        res['log'] = log
        results.append(res)
        equity += res['pnl']
        print(f'{day:<12}{names[:43]:<44}{res["setups"]:>7}{res["passes"]:>5}'
              f'{len(res["trades"]):>7}{res["pnl"]:>10.2f}')

    total = sum(r['pnl'] for r in results)
    trades = [t for r in results for t in r['trades']]
    print(f'\n{"":<56}{"WEEK":>19}{total:>10.2f}   '
          f'({100*total/ACCOUNT:+.2f}% on the account)')

    if trades:
        print(f'\n=== trades ===')
        print(f'{"day":<12}{"sym":<6}{"in":>6}{"out":>6}{"entry":>7}{"stop":>7}'
              f'{"$/sh":>6}{"sh":>6}{"exit":>7}{"P&L":>9}{"R":>7}  reason')
        for r in results:
            for t in r['trades']:
                R = t['pnl'] / (t['risk_ps'] * t['full'])
                print(f'{r["day"]:<12}{t["sym"]:<6}{t["entry_time"]:>6}'
                      f'{t["exit_time"]:>6}{t["entry"]:>7.2f}{t["stop"]:>7.2f}'
                      f'{t["risk_ps"]:>6.2f}{t["full"]:>6}{t["exit"]:>7.2f}'
                      f'{t["pnl"]:>9.2f}{R:>+7.2f}  {t["reason"]}')
        wins = [t for t in trades if t['pnl'] > 0]
        Rs = [t['pnl'] / (t['risk_ps'] * t['full']) for t in trades]
        print(f'\ntrades {len(trades)}   winners {len(wins)} '
              f'({100*len(wins)/len(trades):.0f}%)   '
              f'expectancy {sum(Rs)/len(Rs):+.2f}R')

    rej = {}
    for r in results:
        for k, v in (r.get('rejects') or {}).items():
            rej[k] = rej.get(k, 0) + v
    if rej:
        print(f'\n=== why setups were rejected ===')
        for k, v in sorted(rej.items(), key=lambda x: -x[1]):
            print(f'  {v:>4}  {k}')

    json.dump(dict(week=WEEK, max_trades=max_trades, total=total,
                   results=[{k: v for k, v in r.items() if k != 'log'}
                            for r in results]),
              open(os.path.join(OUT, f'week_{WEEK[0]}_max{max_trades}.json'), 'w'),
              indent=1, default=str)


if __name__ == '__main__':
    main()
