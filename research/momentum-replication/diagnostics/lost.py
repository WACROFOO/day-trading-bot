#!/usr/bin/env python3
"""The gate said yes and the engine still did not trade. Why?

calibrate.py scores a setup as "passed" when every documented GATE_CONDITION
holds. run_day applies two further filters that are not in that set - the 2:1
target test and the spread-versus-risk sizing test - plus the day-level trade
limit and the 09:35 rate-of-change confirmation. This replays each pair the
gate accepted, one symbol at a time so nothing competes for a trade slot, and
reports what the engine did with it.

One symbol per run means the trade limit cannot bind, so any pair that still
does not trade was stopped by a rule, not by a queue.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import datetime as dt
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from engine20 import run_day
from run20 import fetch_symbol

OUT = _DATA
rows = json.load(open(os.path.join(OUT, 'pillars.json')))
gaters = [r for r in rows if r['gate']]
need = sorted({r['sym'] for r in gaters})
bars = {}
with ThreadPoolExecutor(max_workers=5) as ex:
    for s, d in ex.map(fetch_symbol, need):
        bars[s] = d

print(f'=== {len(gaters)} pairs whose setups passed every gate condition ===')
print(f'{"day":<12}{"sym":<7}{"setups":>7}{"pass":>6}{"trades":>7}{"P&L":>9}'
      f'{"R":>7}  what stopped it')
tot, taken, agg = 0.0, 0, Counter()
for r in sorted(gaters, key=lambda x: (x['day'], x['sym'])):
    d = (bars.get(r['sym']) or {}).get(r['day'])
    if not d:
        continue
    res = run_day(dt.date(*map(int, r['day'].split('-'))), [r['sym']],
                  {r['sym']: d}, 5, [])
    rej = res.get('rejects') or {}
    for k, v in rej.items():
        agg[k] += v
    ts = res['trades']
    tot += res['pnl']
    taken += len(ts)
    R = sum(t['pnl'] / (t['risk_ps'] * t['full']) for t in ts)
    why = ('traded: ' + ', '.join(t['reason'] for t in ts) if ts
           else '; '.join(f'{k} x{v}' for k, v in
                          sorted(rej.items(), key=lambda x: -x[1])[:2]) or 'no setup')
    print(f'{r["day"]:<12}{r["sym"]:<7}{res["setups"]:>7}{res["passes"]:>6}'
          f'{len(ts):>7}{res["pnl"]:>9.2f}{R:>+7.2f}  {why}')

print(f'\n{taken} trades, ${tot:+.2f} if every one of these were reachable')
print('\nrejections across all of them, most common first:')
for k, v in agg.most_common():
    print(f'  {v:>4}  {k}')
