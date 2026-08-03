#!/usr/bin/env python3
"""How binding is the `price > VWAP` gate, and is it redundant with the 9 EMA?

Two claims to test against our own July data.

1. IwDORxvXAAs 20:49 - "you'll almost never have an instance where you'll be
   below VWAP and above the 9 MA, that's very uncommon, they're rarely
   inverted. So by saying it has to be above the 9 EMA, kind of by default I'm
   saying it should also be above VWAP." If that holds, `price > VWAP` costs
   nothing on top of `price > 9 EMA` and the two conditions are one condition.

2. PARAMETERS.md sets `require_above_vwap: true` as a hard entry gate. But the
   corpus contains a named setup - "break of VWAP" (65 mentions, 46 files) -
   whose entry is BELOW VWAP by construction. If that setup is a meaningful
   share of his entries, the gate as written cannot represent him.

This replays every pullback trigger the detector finds on the July watchlist
and records the joint state of the two conditions at that moment, plus how
often VWAP is the single condition standing between a setup and a trade.

Runs offline from data/bars_cache.

Usage:
    python diagnostics/vwap.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402

import datetime as dt
import json
from collections import Counter

import sim
from engine20 import run_day
from run20 import fetch_symbol

OUT = _DATA
VWAP_K, EMA_K = 'price > VWAP', 'price > 9 EMA'

# Every setup the detector reaches passes through sim.evaluate. Wrapping it is
# the only way to see the check vector for setups the engine then discards -
# the rejects counter aggregates them and loses the joint distribution.
seen = []
_evaluate = sim.evaluate


def evaluate(pb, bar, ind, flipped):
    ok, checks = _evaluate(pb, bar, ind, flipped)
    gating = {k: v[0] for k, v in checks.items() if k in sim.GATE_CONDITIONS}
    seen.append(gating)
    return ok, checks


sim.evaluate = evaluate
import engine20                                            # noqa: E402
engine20.evaluate = evaluate


def main():
    watch = json.load(open(os.path.join(OUT, 'watchlists20.json')))
    need = sorted({r['sym'] for v in watch.values() for r in v})
    bars = {}
    for s in need:
        _, d = fetch_symbol(s)
        if d:
            bars[s] = d

    days = 0
    for day, rows in sorted(watch.items()):
        names = [r['sym'] for r in rows]
        per = {s: bars[s][day] for s in names
               if s in bars and day in bars[s]}
        if not per:
            continue
        days += 1
        run_day(dt.date(*map(int, day.split('-'))), names, per, 5, [])

    n = len(seen)
    if not n:
        print('no setups reached the gate - nothing to measure')
        return

    print(f'=== {n} pullback triggers evaluated across {days} sessions ===\n')

    # 1. the inversion claim
    joint = Counter((g.get(VWAP_K), g.get(EMA_K)) for g in seen)
    print('joint state of the two conditions at the trigger bar:')
    print(f'{"":<22}{"above 9 EMA":>13}{"below 9 EMA":>13}')
    for v in (True, False):
        lbl = 'above VWAP' if v else 'below VWAP'
        print(f'{lbl:<22}{joint[(v, True)]:>13}{joint[(v, False)]:>13}')
    inverted = joint[(False, True)] + joint[(True, False)]
    print(f'\ninverted (the two disagree): {inverted}/{n} = {inverted / n:.1%}')
    print('  of which below VWAP but above 9 EMA: '
          f'{joint[(False, True)]} = {joint[(False, True)] / n:.1%}')
    print('  "they\'re rarely inverted" - IwDORxvXAAs 20:49\n')

    # 2. how binding the gate is on its own
    passed_all = sum(1 for g in seen if all(g.values()))
    only_vwap = sum(1 for g in seen
                    if not g.get(VWAP_K)
                    and all(v for k, v in g.items() if k != VWAP_K))
    only_ema = sum(1 for g in seen
                   if not g.get(EMA_K)
                   and all(v for k, v in g.items() if k != EMA_K))
    print(f'setups clearing every gate condition: {passed_all} ({passed_all / n:.1%})')
    print(f'blocked by VWAP alone:                {only_vwap} '
          f'(+{only_vwap / n:.1%} if the gate were dropped)')
    print(f'blocked by 9 EMA alone:               {only_ema}\n')

    print('per-condition pass rate, most binding last:')
    rates = sorted(((k, sum(1 for g in seen if g.get(k)) / n)
                    for k in sim.GATE_CONDITIONS), key=lambda x: -x[1])
    for k, r in rates:
        print(f'  {r:>6.1%}  {k}')


if __name__ == '__main__':
    main()
