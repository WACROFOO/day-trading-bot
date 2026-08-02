#!/usr/bin/env python3
"""Friday's movers, filtered the way his Sunday watch-list videos filter them.

Method taken from `knowledge-base/recaps/xtslg3eW2tU.txt` (2026-07-26, "These
Are The TWO Stocks I'm Watching for Monday"), where he narrates the process:
start from the top gainers, then reject on volume ("no volume really"), price
("it's too cheap"), shape ("that's just a dead cat bounce off the low"), and
daily-chart context (room to the 200 MA, or overhead resistance from a recent
high). What survives is a WATCH list, which he then re-checks pre-market -
"I don't know by 7:30 if this will still be in play".

This cannot evaluate the news catalyst (no feed here), which is one of the five
pillars, so every row is provisional by construction.

Usage:  python diagnostics/monday.py [YYYY-MM-DD]
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import json

OUT = _DATA
DAY = sys.argv[1] if len(sys.argv) > 1 else '2026-07-31'

pool = {c['sym']: c for c in json.load(open(os.path.join(OUT, 'pool20.json')))}
daily = json.load(open(os.path.join(OUT, 'daily20.json')))

rows = []
for sym, d in daily.items():
    r = d['rows']
    idx = {x['day']: i for i, x in enumerate(r)}
    if DAY not in idx:
        continue
    i = idx[DAY]
    if i == 0:
        continue
    cur, prev = r[i], r[i - 1]
    if not prev['c'] or not cur['o']:
        continue
    c = pool.get(sym, {})
    px = cur['c']
    if not (1.0 <= px <= 25.0):          # his band, slightly widened to look around it
        continue
    hist = r[max(0, i - 50):i]
    avgv = sum(x['v'] for x in hist) / len(hist) if hist else 0
    if not avgv:
        continue
    hi50 = max(x['h'] for x in hist) if hist else 0
    ma200 = (sum(x['c'] for x in r[max(0, i - 200):i]) / len(r[max(0, i - 200):i])
             if i >= 20 else None)
    mcap = c.get('mcap') or 0
    cpx = c.get('price') or px
    rows.append(dict(
        sym=sym, name=(c.get('name') or '')[:26],
        close=px, day_pct=100 * (cur['c'] / prev['c'] - 1),
        run_pct=100 * (cur['h'] / cur['l'] - 1) if cur['l'] else 0,
        vol=cur['v'], rvol=cur['v'] / avgv,
        close_str=100 * (cur['c'] - cur['l']) / (cur['h'] - cur['l']) if cur['h'] > cur['l'] else 0,
        float_m=(mcap / cpx / 1e6) if cpx else 0,
        blue_sky=cur['h'] >= hi50, hi50=hi50,
        vs_ma200=(100 * (px / ma200 - 1)) if ma200 else None,
        splits=[s for s in d.get('splits', []) if s >= r[max(0, i - 15)]['day']],
    ))

# --- his filters, in the order he applies them ------------------------------
cands = [r for r in rows if r['day_pct'] >= 20 or r['run_pct'] >= 40]
cands = [r for r in cands if r['vol'] >= 1_000_000]        # "no volume really"
cands = [r for r in cands if r['close'] >= 2.0]            # "it's too cheap"
cands = [r for r in cands if r['rvol'] >= 5]
cands.sort(key=lambda r: -r['day_pct'])

print(f'=== {DAY} (Friday) — candidates for the next session ===')
print(f'{len(rows)} names in the $1-25 band; {len(cands)} clear gain + volume + '
      f'price + rvol\n')
print(f'{"sym":<7}{"day%":>7}{"range%":>8}{"volume":>13}{"rvol":>7}{"close":>7}'
      f'{"close@":>7}{"float":>8}{"vs200MA":>9}  note')
for r in cands[:22]:
    note = []
    if r['blue_sky']:
        note.append('BLUE SKY (50-day high)')
    else:
        note.append(f'overhead {r["hi50"]:.2f}')
    if r['close_str'] < 35:
        note.append('closed WEAK (dead-cat risk)')
    elif r['close_str'] > 70:
        note.append('closed strong')
    if r['splits']:
        note.append('RECENT SPLIT')
    if r['float_m'] and r['float_m'] < 20:
        note.append(f'{r["float_m"]:.1f}M float')
    ma = f'{r["vs_ma200"]:+.0f}%' if r["vs_ma200"] is not None else 'n/a'
    print(f'{r["sym"]:<7}{r["day_pct"]:>+7.0f}{r["run_pct"]:>8.0f}{r["vol"]:>13,}'
          f'{r["rvol"]:>7.0f}{r["close"]:>7.2f}{r["close_str"]:>6.0f}%'
          f'{(r["float_m"] or 0):>7.1f}M'
          f'{ma:>9}'
          f'  {"; ".join(note)}')
