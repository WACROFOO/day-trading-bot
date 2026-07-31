#!/usr/bin/env python3
"""Recover an operational definition of 'support' from the transcripts.

`support` and `resistance` are the second most-invoked concept in the corpus
(157 rule statements) and the least codeable: a backtest cannot act on the word.
The usual response is to pick a proxy - prior day's low, a level touched three
times, the nearest whole dollar - but that substitutes the tester's definition
for the trader's and then measures the substitution.

This script avoids the substitution by asking what he actually names. Every time
the word appears, the surrounding speech is scanned for the concrete level types
he could be referring to, and the co-occurrences are counted. If one type
dominates, the proxy is not a guess any more.

Captions carry no punctuation, so context is taken as a fixed word window rather
than a sentence. The window is wide enough to catch a level named a clause away
and narrow enough that a level from an unrelated thought rarely lands inside it.

Input:  knowledge-base/transcripts/*.txt
Output: knowledge-base/data/support_definition.md

Usage:
    python scripts/pipeline/08_define_support.py [--window 40] [--samples 6]
"""

import argparse
import glob
import os
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
TRANSCRIPTS = os.path.join(ROOT, 'knowledge-base', 'transcripts')
OUT = os.path.join(ROOT, 'knowledge-base', 'data', 'support_definition.md')

TS_RE = re.compile(r'^\[(\d{2}):(\d{2}):(\d{2})\]\s*')
TERM_RE = re.compile(r'\bsupport|\bresistance', re.I)

# The concrete level types a spoken 'support' could resolve to. Ordered only for
# stable output; matching is non-exclusive because one sentence often names two
# ("the nine EMA right at the whole dollar").
LEVEL_TYPES = [
    ('whole / half dollar',   r'whole (dollar|number)|half dollar|round number|psychological'),
    ('moving average',        r'\b\d+ ?(ema|sma|day moving|moving average)|moving average|\bema\b|\bsma\b'),
    ('VWAP',                  r'\bvwap\b|volume weighted'),
    ('high of day',           r'high of (the )?day|\bhod\b|daily high|highs of the day'),
    ('low of day',            r'low of (the )?day|\blod\b|daily low|lows of the day'),
    ('pre-market level',      r'pre.?market (high|low|level)'),
    ('prior day level',       r'yesterday|previous day|prior day|previous close|prior close'),
    ('daily / weekly chart',  r'daily chart|weekly chart|daily level|daily resistance|daily support'),
    ('pullback / flag low',   r'low of the (pullback|flag|candle)|pullback low|flag low'),
    ('former resistance',     r'(becomes?|turns? into|acts? as|flip(s|ped)? (to|into)) (support|resistance)'
                              r'|old (support|resistance)|previous (support|resistance)|former (support|resistance)'),
    ('trend line',            r'trend ?line|ascending (support|line|trend)|descending (support|resistance|trend|line)'),
    ('consolidation base',    r'consolidat|\bbase\b|sideways'),
    ('volume shelf',          r'heavy volume|volume (shelf|level)|lot of volume (at|around)'),
    ('gap level',             r'gap (fill|up level|down)|filled the gap'),
    ('52-week / all-time',    r'52.?week|all.?time (high|low)'),
]
LEVEL_RE = [(name, re.compile(pat, re.I)) for name, pat in LEVEL_TYPES]

# Does the mention carry an instruction, or is it narration? Only the former is
# a rule worth encoding.
ACTION_RE = re.compile(
    r'\b(buy|buying|enter|entry|add|long|sell|short|stop|target|exit|take profit|'
    r'break|bounce|hold|hold(s|ing)? (above|at)|reject)\b', re.I)


def load(path):
    """Return [(seconds, word)] with the header and timestamps stripped."""
    stream = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            m = TS_RE.match(line)
            if not m:
                continue
            h, mm, s = (int(g) for g in m.groups())
            sec = h * 3600 + mm * 60 + s
            for w in TS_RE.sub('', line).split():
                stream.append((sec, w))
    return stream


def hms(sec):
    return f'{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--window', type=int, default=40,
                    help='words of context either side of the term')
    ap.add_argument('--samples', type=int, default=6,
                    help='verbatim excerpts to print per level type')
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(TRANSCRIPTS, '*.txt')))
    if not paths:
        print('No transcripts found.')
        return

    mentions = 0
    actionable = 0
    unresolved_count = 0
    unresolved = []
    type_mentions = Counter()
    type_videos = defaultdict(set)
    type_samples = defaultdict(list)
    pair_counts = Counter()
    sr_split = Counter()
    videos_with_term = set()

    for path in paths:
        vid = os.path.splitext(os.path.basename(path))[0]
        stream = load(path)
        words = [w for _, w in stream]
        lowered = [w.lower() for w in words]

        for i, w in enumerate(lowered):
            if not TERM_RE.search(w):
                continue
            mentions += 1
            videos_with_term.add(vid)
            sr_split['resistance' if 'resist' in w else 'support'] += 1

            lo = max(0, i - args.window)
            hi = min(len(words), i + args.window + 1)
            ctx = ' '.join(words[lo:hi])

            is_action = bool(ACTION_RE.search(ctx))
            if is_action:
                actionable += 1

            hits = [name for name, pat in LEVEL_RE if pat.search(ctx)]
            if not hits:
                if is_action:
                    unresolved_count += 1
                    # Store a bounded sample; the count above is the real figure.
                    if len(unresolved) < 25:
                        unresolved.append((vid, hms(stream[i][0]), ctx))
                continue

            for name in hits:
                type_mentions[name] += 1
                type_videos[name].add(vid)
                if len(type_samples[name]) < args.samples and is_action:
                    type_samples[name].append((vid, hms(stream[i][0]), ctx))
            for a in range(len(hits)):
                for b in range(a + 1, len(hits)):
                    pair_counts[tuple(sorted((hits[a], hits[b])))] += 1

    lines = [
        '# What "support" actually means in the corpus',
        '',
        f'`support` / `resistance` appears **{mentions:,} times** across '
        f'**{len(videos_with_term)} of {len(paths)} videos**. '
        f'{actionable:,} of those mentions sit next to an instruction '
        '(buy, stop, target, exit) rather than pure narration.',
        '',
        f'Context window: {args.window} words either side. A mention is tagged '
        'with every concrete level type named nearby, so tags are not exclusive '
        '— "the 9 EMA right at the whole dollar" counts for both.',
        '',
        'Generated by `scripts/pipeline/08_define_support.py`.',
        '',
        f'- support: {sr_split["support"]:,}',
        f'- resistance: {sr_split["resistance"]:,}',
        '',
        '## Which level type is he naming',
        '',
        '| level type | mentions | videos |',
        '|---|---|---|',
    ]
    for name, n in type_mentions.most_common():
        lines.append(f'| {name} | {n} | {len(type_videos[name])} |')

    lines += ['', '## Level types named together', '',
              'Pairs inside the same window. A high count means the two are '
              'used as confirmation of each other, not as alternatives.', '',
              '| pair | count |', '|---|---|']
    for (a, b), n in pair_counts.most_common(20):
        lines.append(f'| {a} + {b} | {n} |')

    lines += ['', '## Verbatim usage', '',
              'Captions are unpunctuated; read them as speech.', '']
    for name, _ in type_mentions.most_common():
        if not type_samples[name]:
            continue
        lines += [f'### {name}', '']
        for vid, ts, ctx in type_samples[name]:
            lines.append(f'- `{vid}` [{ts}] …{ctx}…')
        lines.append('')

    pct = 100 * unresolved_count / actionable if actionable else 0
    lines += ['## Actionable but unresolved', '',
              f'{unresolved_count:,} of {actionable:,} actionable mentions '
              f'({pct:.0f}%) carry an instruction but name no concrete level '
              'within the window. These are the genuinely discretionary ones — '
              'the residue a proxy cannot recover. Sample below.', '']
    for vid, ts, ctx in unresolved:
        lines.append(f'- `{vid}` [{ts}] …{ctx}…')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    print(f'{mentions:,} mentions in {len(videos_with_term)} videos, '
          f'{actionable:,} actionable')
    for name, n in type_mentions.most_common():
        print(f'  {name:22} {n:5d}  ({len(type_videos[name])} videos)')
    print(f"  {chr(39)}unresolved{chr(39)}: {unresolved_count}")
    print(f'Wrote {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
