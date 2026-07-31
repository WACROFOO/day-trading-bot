#!/usr/bin/env python3
"""Select the instructional videos from the channel index.

Roughly half the channel is daily P&L recaps ("+$35,347 in 3 Hours"), which
narrate one morning's trades and state few reusable rules. The instructional
videos are a small minority but carry almost all of the mechanical content, and
they announce themselves in the title.

Three classes are kept, in descending order of how directly they state rules:

    howto     step-by-step explanations of a technique
    rules     named strategies, setups, patterns, scanners, risk limits
    mistakes  post-mortems, which state rules by way of their violation

Title matching is deliberately the primary filter rather than view count. Views
here are age-independent (r=0.06 against upload date) but arrive rounded to two
significant figures from flat extraction, so they separate a 10,000-view video
from a 1,000,000-view one and nothing finer. Duration only excludes clips too
short to contain an explanation.

Input:  knowledge-base/data/daytradewarrior_videos.json
Output: knowledge-base/data/teaching_shortlist.json   same shape as the index,
        so any script that reads the index can read this instead

Usage:
    python scripts/pipeline/00_select_teaching.py [--min-minutes 8] [--preview]
"""

import argparse
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
INDEX = os.path.join(ROOT, 'knowledge-base', 'data', 'daytradewarrior_videos.json')
OUT = os.path.join(ROOT, 'knowledge-base', 'data', 'teaching_shortlist.json')

# Ordered: a video is labelled with the first class it matches, so a title that
# is both a guide and a strategy counts once, as the stronger of the two.
CLASSES = [
    ('howto', re.compile(
        r'\bhow to\b|\bhow i\b|\btutorials?\b|\bexplained?\b|\bguides?\b'
        r'|\blessons?\b|\bclass \d|\bcourses?\b|\bbasics\b|\bbeginners?\b'
        r'|\btrainings?\b|\bstep[- ]by[- ]step\b|\bmasterclass\b'
        r'|\bfundamentals?\b|\bchapters?\b|\bwalk(through| through)\b', re.I)),
    ('rules', re.compile(
        r'\bstrateg(y|ies)\b|\brules?\b|\bsetups?\b|\bpatterns?\b'
        r'|\bindicators?\b|\bscanners?\b|\bcriteria\b|\bchecklists?\b'
        r'|\brisk manage|\bstop[- ]loss|\bposition siz|\bentr(y|ies)\b'
        r'|\bexits?\b|\btechnical analysis\b|\bcandlesticks?\b'
        r'|\bsupport (and|&|/) resistance\b|\bmoving average', re.I)),
    ('mistakes', re.compile(
        r'\bmistakes?\b|\bwhat i learned\b|\blessons learned\b'
        r'|\bwhy i (lost|blew|stopped|quit|avoid|never)\b|\bnever do\b'
        r'|\bdon.t do\b|\bworst (trade|mistake|habit)|\bblew up\b'
        r'|\bhow to avoid\b|\bpitfalls?\b', re.I)),
]

# A recap title can still contain a teaching phrase ("How I made $4k today").
# These markers say the video is a narration of one session, so they veto.
RECAP_VETO = re.compile(
    r'\brecap\b|\bday in the life\b|\bwatch me\b|\blive trad'
    r'|\bmorning show\b|\bstocks? to watch\b|\bwatch ?list\b'
    r'|\bgame ?plan\b|\bpremarket\b|\bhalt(ed|s)?\b'
    r'|\btop gapper|\bbreaking news\b|\bearnings\b', re.I)

# The veto is about subject matter, not vocabulary: "Trading Halts Explained"
# and "How to Trade Breaking News" teach the very topic the veto looks for.
# An unambiguous teaching marker therefore outranks it.
STRONG_TEACH = re.compile(
    r'\bhow to\b|\bstep[- ]by[- ]step\b|\bfull training\b|\bguides?\b'
    r'|\bexplained?\b|\btutorials?\b|\bmasterclass\b|\bcourses?\b', re.I)

# A bare P&L figure with no instructional phrasing is a recap by another name.
PNL = re.compile(r'\$[\d,.]+\s*[kKmM]?\b|\+\s?\d+%|\bup \d+%', re.I)


def classify(title):
    """Return the class name for a title, or None if it is not instructional."""
    if RECAP_VETO.search(title) and not STRONG_TEACH.search(title):
        return None
    for name, pattern in CLASSES:
        if pattern.search(title):
            return name
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--min-minutes', type=float, default=8.0,
                    help='drop clips too short to contain an explanation')
    ap.add_argument('--preview', action='store_true',
                    help='print the selection without writing the shortlist')
    args = ap.parse_args()

    with open(INDEX, encoding='utf-8') as f:
        index = json.load(f)
    videos = index['videos']

    selected = []
    dropped_short = 0
    for v in videos:
        cls = classify(v.get('title', ''))
        if not cls:
            continue
        # A P&L figure survives only alongside genuine instructional phrasing,
        # and never in the weakest class.
        if PNL.search(v['title']) and cls == 'mistakes':
            continue
        if (v.get('duration_sec') or 0) < args.min_minutes * 60:
            dropped_short += 1
            continue
        out = dict(v)
        out['teaching_class'] = cls
        selected.append(out)

    # Longest first: the full trainings carry the most rules per fetch, so a
    # run cut short by a rate limit still lands the highest-value transcripts.
    selected.sort(key=lambda v: -(v.get('duration_sec') or 0))

    by_class = {}
    for v in selected:
        by_class[v['teaching_class']] = by_class.get(v['teaching_class'], 0) + 1

    hours = sum(v.get('duration_sec') or 0 for v in selected) / 3600
    print(f'Index {len(videos)} videos -> selected {len(selected)} '
          f'({len(selected) / len(videos) * 100:.1f}%), {hours:.0f}h of material')
    for name, _ in CLASSES:
        print(f'  {name:9} {by_class.get(name, 0):4d}')
    print(f'  (dropped {dropped_short} instructional titles under '
          f'{args.min_minutes:g} min)')

    if args.preview:
        print()
        for v in selected[:40]:
            print(f"  {v['teaching_class']:9} {(v['duration_sec'] or 0) // 60:4d}m "
                  f"{v['view_count'] or 0:9d}  {v['title'][:64]}")
        return

    out = {
        'channel': index.get('channel'),
        'channel_id': index.get('channel_id'),
        'source_index': os.path.basename(INDEX),
        'selection': {
            'classes': [name for name, _ in CLASSES],
            'min_minutes': args.min_minutes,
            'counts': by_class,
            'total_hours': round(hours, 1),
        },
        'video_count': len(selected),
        'videos': selected,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f'Wrote {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
