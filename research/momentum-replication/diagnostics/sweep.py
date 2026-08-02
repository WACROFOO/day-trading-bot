#!/usr/bin/env python3
"""Recall of his own trades, across the two parameters the pillar audit blamed.

pillars.py charged most of the scanner's misses to the $2 price floor and the
top-5-by-gap truncation. Neither is settled in the corpus: PARAMETERS.md:20
records both 2.00 and 1.00 for price_min, and "3-5 names" describes what a
person can watch rather than what a scanner must discard. This measures both
readings against the recap labels instead of arguing them.

Recall here is of session-ticker pairs the RECAPS name - it says nothing about
how many other names each setting also lets in, which is reported alongside as
watchlist size. A setting that admits everything would score 100% and be
useless.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import json
import run20b
from run20b import build

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
    pairs.append(dict(day=r[0], sym=r[1].rstrip('*'), gate=r[7]))
gaters = [p for p in pairs if p['gate']]

stats = json.load(open(os.path.join(OUT, 'scan20_stats.json')))
daily = json.load(open(os.path.join(OUT, 'daily20.json')))
pool = {c['sym']: c for c in json.load(open(os.path.join(OUT, 'pool20.json')))}
shares_out = {s: c['mcap'] / c['price'] for s, c in pool.items() if c['price']}

print(f'{len(pairs)} pairs he named, {len(gaters)} of which the entry gate accepts\n')
print(f'{"price_min":>10}{"names":>7}{"his names on WL":>17}{"of those, gaters":>18}'
      f'{"WL size/day":>13}')
for pmin in (2.0, 1.0):
    for names in (5, 10, 20):
        run20b.PRICE_MIN, run20b.MAX_NAMES = pmin, names
        w = build(stats, daily, shares_out)
        onwl = {(d, r['sym']) for d, v in w.items() for r in v}
        hit = sum(1 for p in pairs if (p['day'], p['sym']) in onwl)
        gh = sum(1 for p in gaters if (p['day'], p['sym']) in onwl)
        size = sum(len(v) for v in w.values()) / max(1, len(w))
        print(f'{pmin:>10.2f}{names:>7}{hit:>10} ({100*hit/len(pairs):>3.0f}%)'
              f'{gh:>12} ({100*gh/len(gaters):>3.0f}%){size:>13.1f}')
