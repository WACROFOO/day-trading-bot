#!/usr/bin/env python3
"""Prove the simulation did not use future data.

The test: truncate the day at successively later cut-offs and re-run. A
forward-only engine must produce byte-identical decisions for every decision
that happened before the cut-off. If any trade appears, disappears or changes
price when later bars become available, the engine read them.

Run with the data cut at 09:41 (one minute past the last decision), 10:00,
10:30 and the full day. All four must agree.
"""
import json
import os
import subprocess
import sys

OUT = os.path.dirname(os.path.abspath(__file__))
FULL = os.path.join(OUT, 'friday_bars.json')
TMP = os.path.join(OUT, '_truncated.json')


def run(cutoff):
    raw = json.load(open(FULL))
    if cutoff:
        for sym, d in raw.items():
            d['session'] = [b for b in d['session'] if b['iso'][11:16] < cutoff]
    json.dump(raw, open(TMP, 'w'))

    # point run_sim at the truncated file by swapping it in
    bak = FULL + '.bak'
    os.rename(FULL, bak)
    os.rename(TMP, FULL)
    try:
        subprocess.run([sys.executable, os.path.join(OUT, 'run_sim.py')],
                       capture_output=True, text=True, timeout=300)
        res = json.load(open(os.path.join(OUT, 'sim_result.json')))
    finally:
        os.remove(FULL)
        os.rename(bak, FULL)

    return [(t['sym'], t['entry_time'], round(t['entry'], 4),
             round(t['stop'], 4), t['shares'] if 'shares' in t else None,
             t.get('exit_time'), round(t.get('exit') or 0, 4),
             round(t['pnl'], 2)) for t in res['trades']], res['day_pnl']


def main():
    cutoffs = ['09:41', '10:00', '10:30', '11:30', None]
    base = None
    print(f'{"cut-off":<10} {"trades":>7} {"day P&L":>10}  identical to full run?')
    rows = []
    for c in cutoffs:
        trades, pnl = run(c)
        rows.append((c, trades, pnl))
    full = rows[-1][1]
    ok = True
    for c, trades, pnl in rows:
        same = (trades == full)
        ok &= same
        print(f'{str(c):<10} {len(trades):>7} {pnl:>10.2f}  '
              f'{"YES" if same else "NO  <-- LEAK"}')
    print()
    if ok:
        print('PASS - decisions are identical whether or not future bars exist.')
        print('       The engine is forward-only.')
    else:
        print('FAIL - look-ahead detected.')
    for t in full:
        print('  ', t)


if __name__ == '__main__':
    main()
