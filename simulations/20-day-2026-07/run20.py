#!/usr/bin/env python3
"""Passes 2 and 3: build a watchlist per day, then trade each day forward.

Pass 2 picks the watchlist from pre-market statistics only (plus the 09:35
volume confirmation). Pass 3 fetches session bars for the selected names and
runs the engine day by day.

Trade limit is a CLI argument. The playbook says 2; this run uses 5 on request,
which is a deliberate deviation and is reported as such.
"""
import datetime as dt
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine20 import run_day

ET = dt.timezone(dt.timedelta(hours=-4))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/121.0 Safari/537.36")
OUT = os.path.dirname(os.path.abspath(__file__))

WINDOWS = [(dt.datetime(2026, 7, 1), dt.datetime(2026, 7, 8)),
           (dt.datetime(2026, 7, 8), dt.datetime(2026, 7, 15)),
           (dt.datetime(2026, 7, 15), dt.datetime(2026, 7, 22)),
           (dt.datetime(2026, 7, 22), dt.datetime(2026, 7, 29)),
           (dt.datetime(2026, 7, 29), dt.datetime(2026, 8, 1, 12))]

MAX_NAMES = 5          # playbook: end pre-market with 3-5 names


def get(url, tries=3):
    for i in range(tries):
        p = subprocess.run(['curl', '-s', '--max-time', '50',
                            '-H', f'User-Agent: {UA}', url],
                           capture_output=True, text=True)
        o = p.stdout.strip()
        if o.startswith('{') and '"chart"' in o:
            try:
                return json.loads(o)
            except json.JSONDecodeError:
                pass
        time.sleep(1.0 + 2.0 * i)
    return None


def fetch_symbol(sym):
    out = defaultdict(lambda: dict(pre=[], session=[]))
    for a, b in WINDOWS:
        url = (f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}'
               f'?period1={int(a.timestamp())}&period2={int(b.timestamp())}'
               f'&interval=1m&includePrePost=true')
        d = get(url)
        try:
            r = d['chart']['result'][0]
        except (TypeError, KeyError, IndexError):
            continue
        ts, q = r.get('timestamp') or [], r['indicators']['quote'][0]
        for i, t in enumerate(ts):
            c = q['close'][i]
            if c is None:
                continue
            d_ = dt.datetime.fromtimestamp(t, ET)
            bar = dict(dt=d_, o=q['open'][i] or c, h=q['high'][i] or c,
                       l=q['low'][i] or c, c=c, v=q['volume'][i] or 0)
            key = str(d_.date())
            if d_.time() < dt.time(9, 30):
                out[key]['pre'].append(bar)
            elif d_.time() < dt.time(16, 0):
                out[key]['session'].append(bar)
    return sym, dict(out)


def build_watchlists(stats, shares_out):
    """Pre-market only, plus the 09:35 volume confirmation."""
    byday = defaultdict(list)
    for r in stats:
        byday[r['day']].append(r)

    lists = {}
    for day, rows in sorted(byday.items()):
        picks = []
        for r in rows:
            if not (2.0 <= r['pre_last'] <= 20.0):
                continue
            if r['gap_pct'] < 10.0:
                continue
            if r['pre_bars'] < 5:                 # a 1-2 bar gap is a stale quote
                continue
            if r['rvol5'] < 5.0:                  # confirmed at 09:35
                continue
            so = shares_out.get(r['sym'], 0)
            if not so or so > 20e6:               # float proxy
                continue
            picks.append(r)
        picks.sort(key=lambda r: -r['gap_pct'])
        lists[day] = picks[:MAX_NAMES]
    return lists


def main():
    # Several limits are run against the SAME fetched bars and the same
    # watchlists, so the only thing that differs between them is the rule.
    limits = [int(x) for x in sys.argv[1:]] or [5]
    stats = json.load(open(os.path.join(OUT, 'scan20_stats.json')))
    pool = {c['sym']: c for c in json.load(open(os.path.join(OUT, 'pool20.json')))}
    shares_out = {s: (c['mcap'] / c['price']) for s, c in pool.items() if c['price']}

    lists = build_watchlists(stats, shares_out)
    need = sorted({r['sym'] for rows in lists.values() for r in rows})
    print(f'{len(lists)} trading days, {len(need)} distinct symbols to fetch',
          flush=True)
    for day in sorted(lists):
        syms = ', '.join(f"{r['sym']}(+{r['gap_pct']:.0f}%)" for r in lists[day])
        print(f'  {day}  {syms or "-- no names --"}', flush=True)

    cache_path = os.path.join(OUT, 'bars20.json')
    bars = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        for sym, d in ex.map(fetch_symbol, need):
            bars[sym] = d
    print(f'fetched {len(bars)} symbols', flush=True)

    for max_trades in limits:
        results, log = [], []
        for day in sorted(lists):
            watch = [r['sym'] for r in lists[day]]
            if not watch:
                results.append(dict(day=day, pnl=0.0, trades=[], setups=0,
                                    passes=0, halted='no watchlist', rejects={}))
                continue
            per_sym = {}
            for s in watch:
                d = bars.get(s, {}).get(day)
                if d:
                    per_sym[s] = d
            daylog = []
            res = run_day(dt.date(*map(int, day.split('-'))), watch, per_sym,
                          max_trades, daylog)
            res['log'] = daylog
            results.append(res)
            log.extend([f'{day} {l}' for l in daylog])

        json.dump(dict(max_trades=max_trades, results=results),
                  open(os.path.join(OUT, f'run20_max{max_trades}.json'), 'w'),
                  indent=1, default=str)
        total = sum(r['pnl'] for r in results)
        ntr = sum(len(r['trades']) for r in results)
        print(f'=== max_trades={max_trades}: {len(results)} days | '
              f'{ntr} trades | total ${total:+.2f} ===', flush=True)


if __name__ == '__main__':
    main()
