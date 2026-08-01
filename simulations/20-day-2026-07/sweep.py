#!/usr/bin/env python3
"""Sweep the two genuinely underdetermined rules and report the whole range.

Neither of these has a value in the corpus, so picking one and reporting a
single number would be a choice dressed up as a measurement.

  level_tolerance   PARAMETERS.md:127 says "unstated ... sweep 0.1-0.5% of
                    price, floor at spread width". It drives the confluence
                    check, which is currently rejecting 86% of all setups.

  pullback index    "first or second pullback, never the third" needs a rule
    reset           for when counting restarts. Losing VWAP is one reading; a
                    stock that holds VWAP all morning then never resets and is
                    locked out after two legs. Making a new high of day is the
                    other defensible reading - each fresh leg is a new move.

Reported as a grid, not a best cell. If the sign of the result flips across the
grid, the strategy is undetermined by its own documentation, and that is the
finding.
"""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim
from run20 import fetch_symbol
from concurrent.futures import ThreadPoolExecutor

OUT = os.path.dirname(os.path.abspath(__file__))


def main():
    lists = json.load(open(os.path.join(OUT, 'watchlists20.json')))
    need = sorted({r['sym'] for v in lists.values() for r in v})
    bars = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        for sym, d in ex.map(fetch_symbol, need):
            bars[sym] = d

    print(f'{"reset":<10}{"tol%":>7}{"setups":>8}{"pass":>6}{"trades":>8}'
          f'{"wins":>6}{"win%":>7}{"P&L $":>10}{"exp R":>8}')
    for reset in ('vwap', 'newhod'):
        sim.PULLBACK_RESET = reset
        for tol in (0.001, 0.0025, 0.005, 0.01, 0.02):
            sim.LEVEL_TOL_PCT = tol
            import importlib
            import engine20
            importlib.reload(engine20)
            tot, ntr, nw, setups, passes, Rs = 0.0, 0, 0, 0, 0, []
            for day, rows in lists.items():
                watch = [r['sym'] for r in rows]
                if not watch:
                    continue
                per = {s: bars[s][day] for s in watch
                       if s in bars and day in bars[s]}
                res = engine20.run_day(dt.date(*map(int, day.split('-'))),
                                       watch, per, 5, [])
                tot += res['pnl']
                setups += res['setups']
                passes += res['passes']
                for t in res['trades']:
                    ntr += 1
                    R = t['pnl'] / (t['risk_ps'] * t['full'])
                    Rs.append(R)
                    if t['pnl'] > 0:
                        nw += 1
            exp = sum(Rs) / len(Rs) if Rs else 0
            print(f'{reset:<10}{tol*100:>7.2f}{setups:>8}{passes:>6}{ntr:>8}'
                  f'{nw:>6}{(100*nw/ntr if ntr else 0):>7.1f}{tot:>10.2f}'
                  f'{exp:>+8.3f}')


if __name__ == '__main__':
    main()
