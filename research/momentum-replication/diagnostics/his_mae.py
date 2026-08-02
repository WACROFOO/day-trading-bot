#!/usr/bin/env python3
"""Timing or selection? The same adverse-excursion test, on HIS names.

diagnostics/mae.py showed that of the trades the engine takes, most fall 3-7R
below the entry and never reach target 1. Two explanations survive that:

  timing      the detector enters pullbacks too early or too late, and would do
              the same damage on his names too
  selection   the detector is fine and the scanner is handing it the wrong
              stocks - his names would hold up where the watchlist names do not

The recap labels separate them. This runs the detector over the 61 labelled
session-ticker pairs, takes the FIRST setup on each that clears the gate, and
replays it forward exactly as mae.py does - worst excursion before target 1,
and whether target 1 was reached.

Same detector, same gate, same window, same forward replay. The only thing that
changes is which stocks it is pointed at. Whichever way the drawdowns come out
answers the question.

Comparison is against the engine's own trades, which mae.py prints.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import datetime as dt
import json
from concurrent.futures import ThreadPoolExecutor

from engine20 import run_day
from run20 import fetch_symbol
from sim import HARD_STOP

OUT = _DATA
cal = json.load(open(os.path.join(OUT, 'calibration.json')))
pairs, seen = [], set()
for r in cal['rows']:
    if r[2] == '?':
        continue
    k = (r[0], r[1].rstrip('*'))
    if k in seen:
        continue
    seen.add(k)
    pairs.append(k)

bars = {}
with ThreadPoolExecutor(max_workers=5) as ex:
    for s, d in ex.map(fetch_symbol, sorted({p[1] for p in pairs})):
        bars[s] = d

rows = []
for day, sym in sorted(pairs):
    d = bars.get(sym, {}).get(day)
    if not d or not d.get('session'):
        continue
    # run the symbol alone: nothing competes for the trade slot, so the first
    # gate-clearing setup of the session is the one taken
    res = run_day(dt.date(*map(int, day.split('-'))), [sym], {sym: d}, 1, [])
    if not res['trades']:
        continue
    t = res['trades'][0]
    ses = [b for b in d['session']
           if b['dt'].strftime('%H:%M') > t['entry_time']
           and b['dt'].time() < HARD_STOP]
    worst, hit, hit_at = 0.0, False, ''
    for b in ses:
        if b['h'] >= t['t1']:
            hit, hit_at = True, b['dt'].strftime('%H:%M')
            break
        worst = min(worst, (b['l'] - t['entry']) / t['risk_ps'])
    rows.append(dict(day=day, sym=sym, t=t['entry_time'], risk=t['risk_ps'],
                     R=t['pnl'] / (t['risk_ps'] * t['full']),
                     mae=worst, hit=hit, hit_at=hit_at, pnl=t['pnl']))

print(f'=== the detector, pointed at HIS names ({len(rows)} of {len(pairs)} '
      f'pairs produced a trade) ===')
print(f'{"day":<12}{"sym":<6}{"in":>6}{"$/sh":>6}{"engine":>8}'
      f'{"worst before T1":>17}{"T1 reached":>12}')
for r in rows:
    print(f'{r["day"]:<12}{r["sym"]:<6}{r["t"]:>6}{r["risk"]:>6.2f}'
          f'{r["R"]:>+8.2f}{r["mae"]:>16.2f}R'
          f'{(r["hit_at"] if r["hit"] else "no"):>12}')

if rows:
    hit = sum(1 for r in rows if r['hit'])
    won = sum(1 for r in rows if r['pnl'] > 0)
    deep = [r for r in rows if r['mae'] <= -2]
    maes = sorted(r['mae'] for r in rows)
    med = maes[len(maes) // 2]
    print(f'\ntarget 1 reached on {hit} of {len(rows)} ({100*hit/len(rows):.0f}%)'
          f'   engine won {won} ({100*won/len(rows):.0f}%)')
    print(f'median worst excursion {med:.2f}R   '
          f'fell past -2R on {len(deep)} of {len(rows)} '
          f'({100*len(deep)/len(rows):.0f}%)')
    print('\ncompare diagnostics/mae.py on the engine\'s own watchlist:')
    print('  target 1 reached on 5 of 11 (45%), won 3 (27%), '
          'fell past -2R on 5 of 11 (45%)')
