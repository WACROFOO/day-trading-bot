#!/usr/bin/env python3
"""Selection or timing, at a sample size that can tell them apart.

diagnostics/his_mae.py asked the question on gate-clearing trades and got 11
per side - two samples that look alike with no power to say whether they are.
The gate is what makes the sample small, and the gate is not what is being
tested here. So this drops it.

For EVERY setup the detector produces - on the engine's watchlist names, and
on the tickers his recaps name - it replays forward from the entry bar and
records the worst excursion before target 1. Same detector, same window, same
replay. The only thing that differs is which stocks it is pointed at.

If his names hold up where watchlist names collapse, the SELECTION is wrong.
If both collapse the same way, the detector's TIMING is wrong and a better
watchlist will not save it.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import datetime as dt
import json
from concurrent.futures import ThreadPoolExecutor

from sim import (Indicators, PullbackTracker, evaluate, GATE_CONDITIONS,
                 SLIPPAGE, HARD_STOP)
from run20 import fetch_symbol
from run20b import build

OUT = _DATA
stats = json.load(open(os.path.join(OUT, 'scan20_stats.json')))
daily = json.load(open(os.path.join(OUT, 'daily20.json')))
pool = {c['sym']: c for c in json.load(open(os.path.join(OUT, 'pool20.json')))}
so = {s: c['mcap'] / c['price'] for s, c in pool.items() if c['price']}

watch = {(d, r['sym']) for d, v in build(stats, daily, so).items() for r in v}
cal = json.load(open(os.path.join(OUT, 'calibration.json')))
his = {(r[0], r[1].rstrip('*')) for r in cal['rows'] if r[2] != '?'}

bars = {}
with ThreadPoolExecutor(max_workers=5) as ex:
    for s, d in ex.map(fetch_symbol, sorted({p[1] for p in watch | his})):
        bars[s] = d


def excursions(day, sym):
    """(worst R before target 1, reached target 1) for every setup."""
    d = bars.get(sym, {}).get(day)
    if not d or not d.get('session'):
        return []
    ses = d['session']
    ind = Indicators()
    for b in d.get('pre', []):
        ind.update(b, in_session=False)
    tr, prev, flipped, out = PullbackTracker(), None, [], []
    for i, bar in enumerate(ses):
        if bar['dt'].time() >= HARD_STOP:
            break
        hod_prev = ind.session_high
        ind.update(bar, in_session=True)
        pb = tr.update(bar, prev, ind)
        if pb and dt.time(9, 35) <= bar['dt'].time() < HARD_STOP:
            _, checks = evaluate(pb, bar, ind, flipped)
            gate = all(v[0] for k, v in checks.items() if k in GATE_CONDITIONS)
            entry = min(pb['trigger_level'] + SLIPPAGE, bar['h'])
            risk = entry - pb['low']
            imp = pb['impulse']
            pole = (max(x['h'] for x in imp) - min(x['l'] for x in imp)) if imp else 0
            objs = [x for x in (hod_prev, pb['low'] + pole) if x and x > entry]
            t1 = min(objs) if objs else 0
            if risk > 0 and t1:
                worst, hit = 0.0, False
                for b in ses[i + 1:]:
                    if b['dt'].time() >= HARD_STOP:
                        break
                    if b['h'] >= t1:
                        hit = True
                        break
                    worst = min(worst, (b['l'] - entry) / risk)
                out.append((worst, hit, gate))
        prev = bar
        if ind.session_high and bar['h'] >= ind.session_high:
            flipped = (flipped + [round(bar['h'], 2)])[-6:]
    return out


groups = {'engine watchlist': watch, 'his recap names': his,
          'both (overlap)': watch & his}
res = {k: [e for day, sym in sorted(v) for e in excursions(day, sym)]
       for k, v in groups.items()}


def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(p * len(v)))] if v else 0.0


print('=== every setup, replayed forward to target 1 or the 11:30 cutoff ===\n')
print(f'{"":<20}{"setups":>8}{"reach T1":>10}{"median":>9}{"p25":>8}{"p10":>8}'
      f'{"past -2R":>10}')
for k, v in res.items():
    if not v:
        continue
    m = [x[0] for x in v]
    print(f'{k:<20}{len(v):>8}{100*sum(1 for x in v if x[1])/len(v):>9.0f}%'
          f'{pct(m,.5):>8.2f}R{pct(m,.25):>7.2f}R{pct(m,.10):>7.2f}R'
          f'{100*sum(1 for x in m if x <= -2)/len(v):>9.0f}%')

print('\n=== same, restricted to setups that clear all 8 gate conditions ===\n')
print(f'{"":<20}{"setups":>8}{"reach T1":>10}{"median":>9}{"p25":>8}{"p10":>8}'
      f'{"past -2R":>10}')
for k, v in res.items():
    v = [x for x in v if x[2]]
    if not v:
        continue
    m = [x[0] for x in v]
    print(f'{k:<20}{len(v):>8}{100*sum(1 for x in v if x[1])/len(v):>9.0f}%'
          f'{pct(m,.5):>8.2f}R{pct(m,.25):>7.2f}R{pct(m,.10):>7.2f}R'
          f'{100*sum(1 for x in m if x <= -2)/len(v):>9.0f}%')

print('\n=== the setups that DO reach target 1: how deep first? ===')
print('(a dip past -1R is the stop, so these are targets reached only by a')
print(' trade that would already have been closed)\n')
print(f'{"":<20}{"reached T1":>11}{"median dip":>12}{"dipped past -1R":>17}')
for k, v in res.items():
    v = [x for x in v if x[1]]
    if not v:
        continue
    m = [x[0] for x in v]
    print(f'{k:<20}{len(v):>11}{pct(m,.5):>11.2f}R'
          f'{100*sum(1 for x in m if x <= -1)/len(v):>16.0f}%')

print(f'\nname-days: watchlist {len(watch)}, his {len(his)}, '
      f'shared {len(watch & his)}')
