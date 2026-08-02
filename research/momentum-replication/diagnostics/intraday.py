#!/usr/bin/env python3
"""The names that never gapped: were they moving intraday instead?

pillars.py charged the largest block of misses - 21 of 61 - to gap >= 10%,
measured open against previous close. That is a PRE-MARKET test, and a scanner
that only runs before the open can only ever find pre-market movers. If the
names he traded that failed it were nonetheless up 10%+ intraday, the gap
threshold is not mis-set: the scanner is running at the wrong time.

For each such pair this reports the largest rise from the session open within
the trading window, and the clock time it first crossed +10%.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import datetime as dt
import json
from concurrent.futures import ThreadPoolExecutor
from run20 import fetch_symbol

OUT = _DATA
rows = json.load(open(os.path.join(OUT, 'pillars.json')))
miss = [r for r in rows if r['reason'] == 'gap >= 10%']
need = sorted({r['sym'] for r in miss})
bars = {}
with ThreadPoolExecutor(max_workers=5) as ex:
    for s, d in ex.map(fetch_symbol, need):
        bars[s] = d

print(f'=== the {len(miss)} pairs rejected for not gapping 10% ===')
print(f'{"day":<12}{"sym":<7}{"gap%":>7}{"intraday max":>14}{"+10% at":>10}'
      f'{"setups":>8}{"gated":>7}')
hit = 0
for r in sorted(miss, key=lambda x: (x['day'], x['sym'])):
    d = (bars.get(r['sym']) or {}).get(r['day']) or {}
    ses = d.get('session') or []
    if not ses:
        print(f'{r["day"]:<12}{r["sym"]:<7}{(r["gap"] or 0):>7.0f}'
              f'{"no session bars":>14}')
        continue
    o = ses[0]['o']
    mx = max(b['h'] for b in ses)
    when = next((b['dt'].strftime('%H:%M') for b in ses if b['h'] >= o * 1.10), '-')
    hit += when != '-'
    print(f'{r["day"]:<12}{r["sym"]:<7}{(r["gap"] or 0):>7.0f}'
          f'{100 * (mx / o - 1):>13.0f}%{when:>10}{r["setups"]:>8}{r["gate"]:>7}')
print(f'\n{hit} of {len(miss)} rose 10%+ from the open intraday - they were '
      f'movers, just not pre-market ones.')
