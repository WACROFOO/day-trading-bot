#!/usr/bin/env python3
"""Summarize the scraped YouTube video index."""

import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PATH = os.path.join(os.path.dirname(__file__), '..',
                    'knowledge-base', 'data', 'daytradewarrior_videos.json')

with open(PATH, encoding='utf-8') as f:
    data = json.load(f)

vids = data['videos']

# Flat extraction omits upload_date but returns an approximate epoch timestamp.
for v in vids:
    if not v.get('upload_date') and v.get('timestamp'):
        v['upload_date'] = datetime.fromtimestamp(
            v['timestamp'], tz=timezone.utc).strftime('%Y%m%d')

print(f"Channel: {data['channel']}  ({data['channel_id']})")
print(f"Videos indexed: {len(vids)}")

dated = [v for v in vids if v.get('upload_date')]
print(f"With upload_date: {len(dated)}  |  missing: {len(vids) - len(dated)}")

if dated:
    ds = sorted(v['upload_date'] for v in dated)
    print(f"Date range: {ds[0]} -> {ds[-1]}")
    years = Counter(d[:4] for d in ds)
    print("\nVideos per year:")
    for y in sorted(years):
        print(f"  {y}: {years[y]:>4}  {'#' * min(60, years[y] // 4)}")

durs = [v['duration_sec'] for v in vids if v.get('duration_sec')]
if durs:
    durs_sorted = sorted(durs)
    total_h = sum(durs) / 3600
    print(f"\nDuration: {len(durs)} videos, {total_h:,.0f} hours total")
    print(f"  median {durs_sorted[len(durs)//2]/60:.1f} min, "
          f"max {max(durs)/60:.1f} min")
    shorts = sum(1 for d in durs if d <= 60)
    print(f"  <=60s (Shorts): {shorts}  |  >20 min (long-form): "
          f"{sum(1 for d in durs if d > 1200)}")

views = [v['view_count'] for v in vids if v.get('view_count')]
if views:
    print(f"\nViews: total {sum(views):,}, median {sorted(views)[len(views)//2]:,}, "
          f"max {max(views):,}")

# Series / topic tagging by title keyword
patterns = {
    'Small Account Challenge': r'small account challenge',
    'Challenge (any)': r'challenge',
    'Recap / Trade Recap': r'recap',
    'Live trading': r'\blive\b',
    'Strategy / How-to': r'strategy|how to|tutorial|lesson|beginner',
    'Red day / loss': r'red day|max loss|loss',
    'Halt': r'\bhalt',
    'Bull flag': r'bull flag',
    'Gap / gapper': r'\bgap',
    'Short selling': r'short selling|shorting|short squeeze',
}
print("\nTitle keyword counts:")
for label, pat in patterns.items():
    n = sum(1 for v in vids if v.get('title') and re.search(pat, v['title'], re.I))
    print(f"  {label:<26} {n:>4}")

print("\nTop 10 most-viewed:")
for v in sorted([v for v in vids if v.get('view_count')],
                key=lambda x: -x['view_count'])[:10]:
    t = (v['title'] or '')[:62]
    print(f"  {v['view_count']:>10,}  {v.get('upload_date') or '        '}  {t}")
