#!/usr/bin/env python3
"""Apply the support-definition method to the rest of the discretionary set.

08_define_support.py established that a concept the corpus states 157 times is
not a blank to be filled with an invented proxy - the definition is present in
the speech, and tagging each mention with the concrete things named alongside it
recovers most of it. This script runs the same procedure over the remaining
concepts PARAMETERS.md flagged as unquantifiable.

Each concept declares the phrases that invoke it and the concrete resolvers it
could decompose into. A mention is tagged with every resolver named within the
window, so tags are not exclusive. The useful output is the shape of the
distribution: one dominant resolver means the concept is a synonym, several
co-occurring means it is confluence, and a high unresolved rate means it really
is discretion and no proxy will recover it.

Input:  knowledge-base/transcripts/*.txt
Output: knowledge-base/data/discretionary_definitions.md

Usage:
    python scripts/pipeline/10_define_discretionary.py [--window 45] [--samples 5]
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
OUT = os.path.join(ROOT, 'knowledge-base', 'data', 'discretionary_definitions.md')

TS_RE = re.compile(r'^\[(\d{2}):(\d{2}):(\d{2})\]\s*')

ACTION_RE = re.compile(
    r'\b(buy|buying|enter|entry|add|long|sell|short|stop|target|exit|take profit|'
    r'break|bounce|hold|reject|skip|pass|avoid|wait)\b', re.I)

# Shared resolvers: the strategy's own filter vocabulary. Several concepts
# decompose into the same terms, which is itself a finding.
FILTER_RESOLVERS = [
    ('float size',          r'\bfloat\b|shares outstanding'),
    ('news catalyst',       r'catalyst|breaking news|press release|\bnews\b'),
    ('relative volume',     r'relative volume|\brvol\b|times (the )?average|heavy volume'),
    ('price range',         r'\$\d|\bdollar stock|price range|under \$?\d+|between \$?\d+'),
    ('percent gain',        r'up \d+ ?%|\d+ ?percent|gainer|up on the day'),
    ('MACD',                r'\bmacd\b'),
    ('VWAP',                r'\bvwap\b'),
    ('moving average',      r'\bema\b|\bsma\b|moving average'),
    ('volume confirmation', r'volume (is |was |coming|picking|surge|spike)|on volume|'
                            r'big volume|volume confirm'),
    ('first / second pullback', r'first pullback|second pullback|micro pullback|first candle'),
    ('time of day',         r'\b9:?3\d|10 ?a\.?m|11 ?a\.?m|first (hour|30 minutes|five minutes)|'
                            r'open(ing)? bell|midday'),
    ('room to the upside',  r'room to (run|the upside)|no resistance|clear (of|above)|'
                            r'nothing (above|overhead)|blue sky'),
    ('daily chart context', r'daily chart|on the daily|long term chart'),
    ('halt',                r'\bhalt(ed|s)?\b|circuit breaker'),
    ('spread / liquidity',  r'\bspreads?\b|\bthin(ly)?\b|\billiquid\b|\bliquidity\b|'
                            r'easy to get (in|out)'),
]

TAPE_RESOLVERS = [
    ('large seller / buyer', r'big (seller|buyer)|large (seller|buyer|order)|'
                             r'\bseller (at|up|sitting)|wall of'),
    ('order size on level',  r'\d+,?\d* shares (on|at|bid|ask)|size (on the|at the)|'
                             r'lot of shares'),
    ('aggressive buying',    r'hitting the ask|taking the (ask|offer)|buyers (stepping|coming)|'
                             r'green on the tape|prints? (green|going off)'),
    ('aggressive selling',   r'hitting the bid|sellers (stepping|coming)|red on the tape'),
    ('speed of prints',      r'(fast|quick|rapid|slow)(ing)? (prints|tape|moving)|'
                             r'tape (is )?(fast|slow|moving)|speed of'),
    ('refresh / reload',     r'refresh|reload|keeps? (coming|stacking) back|iceberg|hidden'),
    ('pulling orders',       r'pull(ing|ed)? (the |their )?(orders?|bids?|offers?)|'
                             r'orders? disappear|spoof'),
    ('bid support',          r'bid (is |are )?(holding|stacking|building)|buyers on the bid|'
                             r'stacked bids?'),
    ('spread width',         r'\bspread\b|wide|tight'),
    ('whole-dollar orders',  r'whole (dollar|number)|half dollar|round number|psychological'),
    ('confirmation to act',  r'confirm|wait(ing)? for|before I (buy|enter)|proof|'
                             r"don'?t anticipate"),
]

CONCEPTS = {
    'A-quality setup': {
        # Deliberately excludes a bare "a setup" - that phrase is how he refers
        # to any setup at all, and folding it in triples the count with mentions
        # that say nothing about quality.
        'terms': r"\ba[- ]?quality\b|\ba\+ ?setup|grade a setup|best setup|"
                 r"ideal setup|perfect setup|highest quality|quality setup|"
                 r"\b(good|great|clean|textbook) setup",
        'resolvers': FILTER_RESOLVERS,
        'note': 'PARAMETERS.md §10 records this as having no stated discriminator '
                'between an A setup and a B setup. If it decomposes into the same '
                'filter the strategy already applies, it is not a separate concept.',
    },
    'tape / Level 2': {
        'terms': r'level ?(2|two)\b|time and sales|\bthe tape\b|tape read|'
                 r'\blevel ii\b|order book',
        'resolvers': TAPE_RESOLVERS,
        'note': 'Needs full order-book data to test, which OHLCV bars cannot '
                'supply. The question here is not whether it is codeable but '
                'what data would be required, and whether any of it reduces to '
                'something bars already carry.',
    },
    'emotional control': {
        'terms': r'\bemotion(al|s)?\b|\bfomo\b|greed|revenge trad|tilt|'
                 r'discipline|psycholog|mindset|frustrat|angry|impulse',
        'resolvers': [
            ('after a loss',        r'after (a|the) (loss|losing|red)|losing trade|got stopped'),
            ('after a win',         r'after (a|the) (win|green|profit)|winning trade|feeling good'),
            ('size too large',      r'too (big|large|much size)|oversiz|position (was )?too'),
            ('breaking max loss',   r'max loss|daily (loss|stop)|blew (through|past)'),
            ('chasing',             r'chas(e|ing)|too late|extended|missed the entry'),
            ('overtrading',         r'overtrad|too many trades|forcing|force a trade'),
            ('walk away rule',      r'walk away|shut (it )?down|stop trading|call it a day|'
                                    r'close the (platform|computer)'),
            ('rules as the fix',    r'follow(ing)? (the |my )?rules|stick to (the|my)|'
                                    r'process|checklist|plan'),
        ],
        'note': 'Included as a control. If a concept resists decomposition it '
                'should show a high unresolved rate here, which tells us the '
                'method is discriminating rather than always finding structure.',
    },
}


def load(path):
    stream = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('#') or not line:
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


def scan(paths, term_re, resolvers, window, samples):
    res_re = [(n, re.compile(p, re.I)) for n, p in resolvers]
    stats = {
        'mentions': 0, 'actionable': 0, 'unresolved': 0,
        'hits': Counter(), 'videos': defaultdict(set),
        'samples': defaultdict(list), 'pairs': Counter(),
        'seen_videos': set(), 'unresolved_samples': [],
    }
    for path in paths:
        vid = os.path.splitext(os.path.basename(path))[0]
        stream = load(path)
        words = [w for _, w in stream]
        text = ' '.join(words)
        if not term_re.search(text):
            continue
        lowered = text.lower()
        # Match on the joined text so multi-word terms ("time and sales") are
        # found; map the character offset back to a word index for the window.
        offsets = []
        pos = 0
        for idx, w in enumerate(words):
            offsets.append((pos, idx))
            pos += len(w) + 1

        for m in term_re.finditer(lowered):
            wi = 0
            for start, idx in offsets:
                if start > m.start():
                    break
                wi = idx
            stats['mentions'] += 1
            stats['seen_videos'].add(vid)
            lo, hi = max(0, wi - window), min(len(words), wi + window + 1)
            ctx = ' '.join(words[lo:hi])
            is_action = bool(ACTION_RE.search(ctx))
            if is_action:
                stats['actionable'] += 1
            found = [n for n, p in res_re if p.search(ctx)]
            if not found:
                if is_action:
                    stats['unresolved'] += 1
                    if len(stats['unresolved_samples']) < 12:
                        stats['unresolved_samples'].append((vid, hms(stream[wi][0]), ctx))
                continue
            for n in found:
                stats['hits'][n] += 1
                stats['videos'][n].add(vid)
                if len(stats['samples'][n]) < samples and is_action:
                    stats['samples'][n].append((vid, hms(stream[wi][0]), ctx))
            for a in range(len(found)):
                for b in range(a + 1, len(found)):
                    stats['pairs'][tuple(sorted((found[a], found[b])))] += 1
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--window', type=int, default=45)
    ap.add_argument('--samples', type=int, default=5)
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(TRANSCRIPTS, '*.txt')))
    if not paths:
        print('No transcripts found.')
        return

    lines = [
        '# Decomposing the discretionary concepts',
        '',
        'The same procedure `08_define_support.py` used on support and '
        'resistance, applied to the rest of the set `PARAMETERS.md` §10 listed '
        'as unquantifiable. Each mention is tagged with every concrete resolver '
        f'named within {args.window} words. Tags are not exclusive.',
        '',
        'Read the shape, not just the totals. One dominant resolver means the '
        'concept is a synonym for something already encoded. Several '
        'co-occurring means confluence. A high unresolved rate means the '
        'concept really is discretion.',
        '',
        'Generated by `scripts/pipeline/10_define_discretionary.py`.',
        '',
    ]

    for name, spec in CONCEPTS.items():
        term_re = re.compile(spec['terms'], re.I)
        st = scan(paths, term_re, spec['resolvers'], args.window, args.samples)
        m, a, u = st['mentions'], st['actionable'], st['unresolved']
        rate = 100 * u / a if a else 0

        print(f'\n{name}: {m:,} mentions, {len(st["seen_videos"])} videos, '
              f'{a:,} actionable, {u:,} unresolved ({rate:.0f}%)')
        for n, c in st['hits'].most_common(8):
            print(f'  {n:26} {c:5d}  ({len(st["videos"][n])} videos)')

        lines += [
            f'## {name}',
            '',
            spec['note'],
            '',
            f'**{m:,} mentions** across **{len(st["seen_videos"])} videos**. '
            f'{a:,} sit next to an instruction; **{u:,} of those ({rate:.0f}%) '
            'name no resolver at all**.',
            '',
            '| resolves to | mentions | videos |',
            '|---|---|---|',
        ]
        for n, c in st['hits'].most_common():
            lines.append(f'| {n} | {c} | {len(st["videos"][n])} |')

        if st['pairs']:
            lines += ['', '**Named together:**', '', '| pair | count |', '|---|---|']
            for (x, y), c in st['pairs'].most_common(10):
                lines.append(f'| {x} + {y} | {c} |')

        lines += ['', '### Verbatim', '']
        for n, _ in st['hits'].most_common(5):
            if not st['samples'][n]:
                continue
            lines.append(f'**{n}**')
            lines.append('')
            for vid, ts, ctx in st['samples'][n]:
                lines.append(f'- `{vid}` [{ts}] …{ctx}…')
            lines.append('')

        if st['unresolved_samples']:
            lines += ['### Unresolved sample', '']
            for vid, ts, ctx in st['unresolved_samples']:
                lines.append(f'- `{vid}` [{ts}] …{ctx}…')
            lines.append('')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'\nWrote {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
