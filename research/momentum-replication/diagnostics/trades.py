#!/usr/bin/env python3
"""The 17-day run, trade by trade, with the realised profit/loss ratio.

run20b.py prints a total; this prints what produced it, which is what the
2:1 question needs. RR_FILTER=0 drops the pre-entry reward:risk veto so the
ratio can be measured as an outcome instead of assumed as a gate.

Usage:
    python diagnostics/trades.py            # 2:1 as an entry filter
    RR_FILTER=0 python diagnostics/trades.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import datetime as dt
import json
from concurrent.futures import ThreadPoolExecutor

import engine20
from engine20 import run_day
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

for day in list(lists):                      # the 09:35 rate-of-change check
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
    rows += [(day, t) for t in res['trades']]

print(f'=== 17 sessions, max 5 trades/day, 2:1 entry veto '
      f'{"ON" if engine20.RR_FILTER else "OFF"} ===')
print(f'{"day":<12}{"sym":<6}{"in":>6}{"out":>6}{"entry":>7}{"$/sh":>6}{"sh":>6}'
      f'{"P&L":>9}{"R":>7}  reason')
for day, t in rows:
    R = t['pnl'] / (t['risk_ps'] * t['full'])
    print(f'{day:<12}{t["sym"]:<6}{t["entry_time"]:>6}{t["exit_time"]:>6}'
          f'{t["entry"]:>7.2f}{t["risk_ps"]:>6.2f}{t["full"]:>6}{t["pnl"]:>9.2f}'
          f'{R:>+7.2f}  {t["reason"]}')

tot = sum(t['pnl'] for _, t in rows)
w = [t for _, t in rows if t['pnl'] > 0]
l = [t for _, t in rows if t['pnl'] <= 0]
aw = sum(t['pnl'] for t in w) / len(w) if w else 0.0
al = -sum(t['pnl'] for t in l) / len(l) if l else 0.0
Rs = [t['pnl'] / (t['risk_ps'] * t['full']) for _, t in rows]
print(f'\ntrades {len(rows)}   winners {len(w)} '
      f'({100 * len(w) / max(1, len(rows)):.0f}%)   total ${tot:+.2f}   '
      f'expectancy {sum(Rs) / max(1, len(Rs)):+.2f}R')
print(f'avg winner ${aw:.2f}   avg loser ${al:.2f}   '
      f'realised profit/loss ratio {(aw / al) if al else 0:.2f}:1')
