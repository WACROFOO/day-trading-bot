#!/usr/bin/env python3
"""Look-ahead audit for the 17-day run.

For each cut-off, every day's session is truncated there and re-run. Any trade
that was ENTERED before the cut-off must come back byte-identical - same
symbol, time, entry, stop, size. If a later bar can change an earlier decision,
the engine is reading the future.

Trades entered after the cut-off are naturally absent and are not compared.
"""
import datetime as dt
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine20 import run_day
from run20 import fetch_symbol

OUT = os.path.dirname(os.path.abspath(__file__))
MAX_TRADES = 5


def run(bars, lists, cutoff):
    out = []
    for day, rows in lists.items():
        watch = [r['sym'] for r in rows]
        if not watch:
            continue
        per = {}
        for s in watch:
            d = bars.get(s, {}).get(day)
            if not d:
                continue
            sess = d['session']
            if cutoff:
                sess = [b for b in sess if b['dt'].strftime('%H:%M') < cutoff]
            per[s] = dict(pre=d['pre'], session=sess)
        res = run_day(dt.date(*map(int, day.split('-'))), watch, per,
                      MAX_TRADES, [])
        for t in res['trades']:
            out.append((day, t['sym'], t['entry_time'], round(t['entry'], 4),
                        round(t['stop'], 4), t['full']))
    return out


def main():
    lists = json.load(open(os.path.join(OUT, 'watchlists20.json')))
    need = sorted({r['sym'] for v in lists.values() for r in v})
    bars = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        for sym, d in ex.map(fetch_symbol, need):
            bars[sym] = d

    full = run(bars, lists, None)
    print(f'{"cut-off":<10} {"entries<cut":>12} {"match full run":>16}')
    ok = True
    for cut in ['10:00', '10:30', '11:00', '11:30', None]:
        got = run(bars, lists, cut)
        if cut:
            expect = [t for t in full if t[2] < cut]
            got = [t for t in got if t[2] < cut]
        else:
            expect = full
        same = got == expect
        ok &= same
        print(f'{str(cut):<10} {len(expect):>12} {"YES" if same else "NO <- LEAK":>16}')
    print()
    print('PASS - no decision changed when future bars were added.' if ok
          else 'FAIL - look-ahead detected.')


if __name__ == '__main__':
    main()
