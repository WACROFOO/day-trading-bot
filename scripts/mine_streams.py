#!/usr/bin/env python3
"""Mine the live streams for statements that bear on the strategy.

The teaching videos explain setups after the outcome is known. A live stream is
the only register in the corpus where he commits to a decision BEFORE it - so
this searches for the moment of decision, not the explanation of it.

Queries are grouped by the open question they would settle, from
`research/momentum-replication/NEXT-STEPS.md` sections 5 and 7. Each hit prints
the surrounding seconds so a phrase can be read in context rather than trusted
as a keyword match.

Usage:
    python scripts/mine_streams.py                 # every topic
    python scripts/mine_streams.py timing          # one topic
    python scripts/mine_streams.py --list
"""
import glob
import html
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
CAPS = os.path.join(ROOT, 'knowledge-base', 'streams')

# Each topic is (regex, why it matters). The regexes are deliberately loose;
# precision comes from reading the context window, not from the pattern.
TOPICS = {
    'timing': (
        r"\b(too extended|too far extended|extended here|chasing|i'm not chasing|"
        r"missed (it|the entry)|too late|late entry|i want the first|first pullback|"
        r"second pullback|third pullback|too many pullbacks|late in the move|"
        r"back ?side|front ?side)\b",
        'NEXT-STEPS section 5: the replication fails on entry timing'),
    'no-trade': (
        r"\b(i'm not going to take|not taking (this|that)|i'll pass|passing on|"
        r"no trade|skip(ping)? (this|that|it)|i don't like (this|that|it)|"
        r"wouldn't take|not a good|too risky here|stepping aside)\b",
        'what he REJECTS is the mirror of the gate and is barely in the corpus'),
    'price-floor': (
        r"\b(under (a|one) dollar|below (a|one) dollar|sub[- ]?(a )?dollar|"
        r"one dollar stock|two dollar|\$1 stock|penny stock|too cheap)\b",
        'NEXT-STEPS section 7: price_min 2.00 or 1.00'),
    'float': (
        r"\b(float|shares outstanding)\b.{0,40}\b(million|m\b)",
        'NEXT-STEPS section 7: float ceiling 20M vs 10M'),
    'timeframe': (
        r"\b(ten|10)[- ]second|\bthirty[- ]second|\b(one|1)[- ]minute chart|"
        r"\bfive[- ]minute chart|\btick chart\b",
        'NEXT-STEPS section 7: MIN_DIP_BARS assumes the 1-minute chart is finest'),
    'scanner': (
        r"\b(scanner|scan|high of day momo|momo scanner|gapper|gap scanner|"
        r"just popped up|just hit the scanner|coming up on the scan)\b",
        'is the scan continuous through the session, or a pre-market list?'),
    'halt': (
        r"\b(halt(ed|s)?|resum(e|ed|ing)|circuit breaker|t12|luld)\b",
        'halts are modelled from teaching videos only'),
    'add-back': (
        r"\b(add(ing)? back|adding to|scal(e|ing) in|second entry|re-?enter|"
        r"starter position|full size|half size)\b",
        'position building is in PARAMETERS as percentages, not as a trigger'),
    'exit': (
        r"\b(taking profit|selling into|sold half|out at|scaling out|"
        r"i'm out|cut it|red to green|hold(ing)? the rest|runner)\b",
        'the exits are settled on paper but never seen in real time'),
    'risk': (
        r"\b(max loss|daily goal|stop trading|done for the day|walk away|"
        r"revenge trad|tilt|overtrad)\b",
        'the account rules the engine enforces mechanically'),
}


def load():
    """{video_id: [(seconds, text)]} from the plain-text stream transcripts."""
    out = {}
    for p in sorted(glob.glob(os.path.join(CAPS, '*.txt'))):
        vid = os.path.basename(p)[:-4]
        rows, title = [], ''
        for line in open(p, encoding='utf-8'):
            if line.startswith('# ') and not title:
                title = line[2:].strip()
            if not line.startswith('['):
                continue
            ts, _, txt = line[1:].partition('] ')
            h, m, s = (ts.split(':') + ['0', '0'])[:3]
            try:
                rows.append((int(h) * 3600 + int(m) * 60 + int(s), txt.strip()))
            except ValueError:
                continue
        if rows:
            out[vid] = (title, rows)
    return out


def search(data, pat, window=18, cap=14):
    rx = re.compile(pat, re.I)
    hits = []
    for vid, (title, rows) in data.items():
        for i, (sec, txt) in enumerate(rows):
            if not rx.search(txt):
                continue
            lo = max(0, i - 2)
            ctx = ' '.join(t for _, t in rows[lo:i + 4])
            hits.append((vid, title, sec, ctx[:340]))
    return hits[:cap], len(hits)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if '--list' in sys.argv:
        for k, (_, why) in TOPICS.items():
            print(f'  {k:<12}{why}')
        return
    data = load()
    if not data:
        sys.exit(f'no transcripts in {CAPS}')
    total = sum(len(r) for _, r in data.values())
    print(f'{len(data)} streams, {total:,} caption lines\n')
    for name, (pat, why) in TOPICS.items():
        if args and name not in args:
            continue
        hits, n = search(data, pat)
        print(f'{"=" * 72}\n{name.upper()}  ({n} hits)\n  why: {why}\n{"=" * 72}')
        for vid, title, sec, ctx in hits:
            print(f'\n  [{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}] '
                  f'{title[:52]}')
            print(f'  https://www.youtube.com/watch?v={vid}&t={sec}s')
            print(f'    {ctx}')
        print()


if __name__ == '__main__':
    main()
