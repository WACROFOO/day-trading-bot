#!/usr/bin/env python3
"""How far is target 1, measured in R, across every setup the detector makes?

PARAMETERS.md section 6 puts `target_typical` at $0.15-0.20 per share and
section 8 caps `stop_max_distance` at $0.20. Those two numbers describe a
target roughly ONE R away, which is arithmetically incompatible with reading
`min_reward_risk >= 2.0` as "(target_1 - entry) >= 2 x risk". Either the
typical target or the veto is wrong; they cannot both describe the same trade.

This settles it from the data rather than the arithmetic: for every setup in
the 17-day window, the distance from entry to the nearest structural objective
in units of risk. If the mass sits near 1R, the veto is rejecting the
strategy's own documented target.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import datetime as dt
import json
from concurrent.futures import ThreadPoolExecutor

import sim
from sim import (Indicators, PullbackTracker, evaluate, GATE_CONDITIONS,
                 SLIPPAGE, spread_estimate)
from run20 import fetch_symbol
from run20b import build

OUT = _DATA
stats = json.load(open(os.path.join(OUT, 'scan20_stats.json')))
daily = json.load(open(os.path.join(OUT, 'daily20.json')))
pool = {c['sym']: c for c in json.load(open(os.path.join(OUT, 'pool20.json')))}
so = {s: c['mcap'] / c['price'] for s, c in pool.items() if c['price']}
lists = build(stats, daily, so)

need = sorted({r['sym'] for v in lists.values() for r in v})
bars = {}
with ThreadPoolExecutor(max_workers=5) as ex:
    for s, d in ex.map(fetch_symbol, need):
        bars[s] = d

rows = []
for day, w in sorted(lists.items()):
    for r in w:
        d = bars.get(r['sym'], {}).get(day)
        if not d or not d.get('session'):
            continue
        ind = Indicators()
        for b in d.get('pre', []):
            ind.update(b, in_session=False)
        tr, prev, flipped = PullbackTracker(), None, []
        for bar in d['session']:
            if not (dt.time(9, 35) <= bar['dt'].time() < dt.time(11, 30)):
                if bar['dt'].time() >= dt.time(11, 30):
                    break
            hod_prev = ind.session_high
            ind.update(bar, in_session=True)
            pb = tr.update(bar, prev, ind)
            if pb and dt.time(9, 35) <= bar['dt'].time() < dt.time(11, 30):
                ok, checks = evaluate(pb, bar, ind, flipped)
                gate = all(v[0] for k, v in checks.items() if k in GATE_CONDITIONS)
                entry = min(pb['trigger_level'] + SLIPPAGE, bar['h'])
                risk = entry - pb['low']
                imp = pb['impulse']
                pole = (max(x['h'] for x in imp) - min(x['l'] for x in imp)) if imp else 0
                objs = [x for x in (hod_prev, pb['low'] + pole) if x and x > entry]
                t1 = min(objs) if objs else 0
                if risk > 0 and t1:
                    rows.append(dict(day=day, sym=r['sym'], gate=gate, risk=risk,
                                     dist=t1 - entry, R=(t1 - entry) / risk))
            prev = bar
            if ind.session_high and bar['h'] >= ind.session_high:
                flipped = (flipped + [round(bar['h'], 2)])[-6:]


def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(p * len(v)))] if v else 0


for label, sel in (('every setup', rows),
                   ('setups passing all 8 gate conditions',
                    [x for x in rows if x['gate']])):
    if not sel:
        continue
    Rs = [x['R'] for x in sel]
    ds = [x['dist'] for x in sel]
    rk = [x['risk'] for x in sel]
    print(f'=== {label} (n={len(sel)}) ===')
    print(f'  distance to target 1, in R    '
          f'p25 {pct(Rs,.25):.2f}   median {pct(Rs,.5):.2f}   '
          f'p75 {pct(Rs,.75):.2f}   p90 {pct(Rs,.9):.2f}')
    print(f'  distance to target 1, $/share '
          f'p25 {pct(ds,.25):.3f}   median {pct(ds,.5):.3f}   p75 {pct(ds,.75):.3f}')
    print(f'  risk per share, $             '
          f'p25 {pct(rk,.25):.3f}   median {pct(rk,.5):.3f}   p75 {pct(rk,.75):.3f}')
    print(f'  share of setups reaching 2R   '
          f'{100 * sum(1 for x in Rs if x >= 2) / len(Rs):.0f}%')
    print()

print('PARAMETERS.md section 6: target_typical ~ $0.15-0.20 per share')
print('PARAMETERS.md section 8: stop_max_distance <= $0.20 per share')
