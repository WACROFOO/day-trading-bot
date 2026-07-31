#!/usr/bin/env python3
"""Count the two mechanics that make 'support' codeable.

08_define_support.py answers *which level* he means. Two of the answers it
surfaced are mechanics rather than level types, and both are testable without a
proxy:

  touch count   - a price becomes a level by being rejected there repeatedly.
                  "we tap 650 we tap 650 we tap 650 and then finally we break"
  break-retest  - once broken, the same price is expected to hold from the other
                  side. "this was previously resistance can it become support"

If either is stated often enough, it is not a heuristic to be invented by the
tester - it is the definition, and it can be computed straight from OHLCV.

Input:  knowledge-base/transcripts/*.txt
Output: stdout only; the findings belong in the strategy docs, not another file.

Usage:
    python scripts/pipeline/09_level_mechanics.py [--window 30]
"""

import argparse
import glob
import os
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
TRANSCRIPTS = os.path.join(ROOT, 'knowledge-base', 'transcripts')

TS_RE = re.compile(r'^\[\d{2}:\d{2}:\d{2}\]\s*')
TERM_RE = re.compile(r'support|resistance', re.I)

MECHANICS = [
    ('touch / tap count',   r'\btaps?\b|\btapping\b|\btouch(es|ed|ing)?\b|'
                            r'(second|third|fourth) (time|try|tap|attempt)'),
    ('double / triple top', r'double top|triple top|double bottom'),
    ('break then retest',   r'retest|comes? back (down |up )?to|pull(s|ed)? back to|'
                            r'back (down )?to (that|the) level'),
    ('flip role',           r'(becomes?|turns? into|acts? as) (support|resistance)|'
                            r'previously (support|resistance)|was resistance|was support'),
    ('holds vs breaks',     r"can'?t break|couldn'?t break|fails? to break|"
                            r'\bholds?\b|\bheld\b|\bbreaks? (through|above|below)\b'),
    ('order clustering',    r'orders? (clustered|stacked|sitting)|lot of orders|'
                            r'buy orders down|sell orders up|big seller|big buyer'),
    ('round-number step',   r'(next|another) (level|whole|half)|'
                            r'\b(50|fifty) cents?\b|half dollar|whole dollar'),
]
MECH_RE = [(n, re.compile(p, re.I)) for n, p in MECHANICS]

# Explicit touch counts, to see whether a specific number is stated.
COUNT_RE = re.compile(r'\b(second|third|fourth|fifth|two|three|four|2|3|4) '
                      r'(time|times|try|tries|tap|taps|attempt|attempts)\b', re.I)


def words_of(path):
    out = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.startswith('#') or not TS_RE.match(line):
                continue
            out.extend(TS_RE.sub('', line.rstrip('\n')).split())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--window', type=int, default=30)
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(TRANSCRIPTS, '*.txt')))
    mech_hits = Counter()
    mech_videos = {n: set() for n, _ in MECHANICS}
    counts = Counter()
    total = 0

    for path in paths:
        vid = os.path.splitext(os.path.basename(path))[0]
        words = words_of(path)
        lowered = [w.lower() for w in words]
        for i, w in enumerate(lowered):
            if not TERM_RE.search(w):
                continue
            total += 1
            ctx = ' '.join(words[max(0, i - args.window):i + args.window + 1])
            for name, pat in MECH_RE:
                if pat.search(ctx):
                    mech_hits[name] += 1
                    mech_videos[name].add(vid)
            for m in COUNT_RE.finditer(ctx):
                counts[m.group(1).lower()] += 1

    print(f'{total:,} support/resistance mentions, window +-{args.window} words\n')
    print(f'{"mechanic":24} {"hits":>6} {"videos":>7}  {"% of mentions":>13}')
    for name, n in mech_hits.most_common():
        print(f'{name:24} {n:6d} {len(mech_videos[name]):7d}  {100*n/total:12.1f}%')

    print('\nExplicit touch counts stated near a level:')
    norm = {'two': '2', '2': '2', 'second': '2',
            'three': '3', '3': '3', 'third': '3',
            'four': '4', '4': '4', 'fourth': '4', 'fifth': '5'}
    rolled = Counter()
    for k, v in counts.items():
        rolled[norm.get(k, k)] += v
    for k in sorted(rolled, key=lambda x: -rolled[x]):
        print(f'  {k}: {rolled[k]}')


if __name__ == '__main__':
    main()
