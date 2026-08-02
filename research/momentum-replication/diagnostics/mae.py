#!/usr/bin/env python3
"""Were the entries wrong, or were the stops too tight?

With the 2:1 veto removed the engine takes 11 trades over 17 sessions and wins
3. The corpus claims 65-75% accuracy. That gap has exactly two shapes and they
call for opposite fixes:

  bad entries   price never goes where the setup said it would, and a wider
                stop only loses more per trade
  tight stops   price reaches target 1 anyway, after first dipping through a
                stop placed under the pullback low

This measures it directly. For every trade the engine took, it replays forward
from the entry bar to the end of the trading window and records the worst
price seen before target 1 (the maximum adverse excursion, in R), and whether
target 1 was reached at all.

The forward replay looks past the engine's own exit ON PURPOSE - that is the
question being asked. Nothing here feeds back into a P&L.
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
from sim import HARD_STOP

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
for day in list(lists):
    keep = []
    for r in lists[day]:
        d = bars.get(r['sym'], {}).get(day)
        f5 = [b for b in (d or {}).get('session', []) if b['dt'].time() < dt.time(9, 35)]
        if f5 and f5[-1]['c'] > f5[0]['o']:
            keep.append(r)
    lists[day] = keep

rows = []
for day, w in sorted(lists.items()):
    syms = [r['sym'] for r in w]
    per = {s: bars[s][day] for s in syms if s in bars and day in bars[s]}
    if not per:
        continue
    res = run_day(dt.date(*map(int, day.split('-'))), syms, per, 5, [])
    for t in res['trades']:
        ses = [b for b in per[t['sym']]['session']
               if b['dt'].strftime('%H:%M') > t['entry_time']
               and b['dt'].time() < HARD_STOP]
        risk = t['risk_ps']
        worst, hit, hit_at = 0.0, False, ''
        for b in ses:
            if b['h'] >= t['t1']:
                hit, hit_at = True, b['dt'].strftime('%H:%M')
                break
            worst = min(worst, (b['l'] - t['entry']) / risk)
        rows.append(dict(day=day, sym=t['sym'], t=t['entry_time'],
                         pnl=t['pnl'], reason=t['reason'], risk=risk,
                         mae=worst, hit=hit, hit_at=hit_at,
                         engine_R=t['pnl'] / (t['risk_ps'] * t['full'])))

print('=== every trade, replayed forward to the end of the window ===')
print(f'{"day":<12}{"sym":<6}{"in":>6}{"$/sh":>6}{"engine":>8}'
      f'{"worst before T1":>17}{"T1 reached":>12}')
for r in rows:
    print(f'{r["day"]:<12}{r["sym"]:<6}{r["t"]:>6}{r["risk"]:>6.2f}'
          f'{r["engine_R"]:>+8.2f}{r["mae"]:>16.2f}R'
          f'{(r["hit_at"] if r["hit"] else "no"):>12}')

st = [r for r in rows if r['engine_R'] <= -0.99]
rec = [r for r in st if r['hit']]
print(f'\n{len(st)} trades stopped out at -1R.')
print(f'  of those, {len(rec)} went on to reach target 1 anyway '
      f'inside the same window')
if st:
    print(f'  their worst excursion before that: '
          + ', '.join(f'{r["mae"]:.2f}R' for r in sorted(st, key=lambda x: x['mae'])))
allhit = sum(1 for r in rows if r['hit'])
won = sum(1 for r in rows if r['pnl'] > 0)
print(f'\ntarget 1 was reachable on {allhit} of {len(rows)} trades '
      f'({100 * allhit / max(1, len(rows)):.0f}%); the engine won {won}.')
