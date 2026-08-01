#!/usr/bin/env python3
"""Consolidate the per-video rules and thresholds into one ranked digest.

The summaries hold 2,040 rules and 2,904 numbers spread across 257 files, which
is too much to read end to end. The obvious move — collapse near-duplicates on a
word signature — does almost nothing here: 2,040 statements reduce to 2,031,
because every video phrases the same idea differently. The repetition is real
but it lives at the level of the concept, not the sentence.

So rules are filed under a subject bucket and then grouped by which piece of the
channel's vocabulary they invoke. That surfaces the true weighting: "micro
pullback" appearing in dozens of separately-worded entry rules is the signal
that a single restated sentence never shows.

Numeric thresholds get their own pass. Every figure is pulled with the phrase
around it and grouped by what it measures, which turns scattered mentions of
"float under 20 million" into a single parameter with a distribution.

Input:  knowledge-base/summaries/*.md
Output: knowledge-base/data/rules_digest.md

Usage:
    python scripts/pipeline/07_extract_rules.py [--per-bucket 30]
"""

import argparse
import glob
import os
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
SUMMARIES = os.path.join(ROOT, 'knowledge-base', 'summaries')
OUT = os.path.join(ROOT, 'knowledge-base', 'data', 'rules_digest.md')

# Ordered: a rule is filed under the first subject it matches, so a sentence
# about both entry and stop-loss lands in the more specific of the two.
BUCKETS = [
    ('stock-selection', r'\bfloat\b|\bgapp?(er|ing|ed)\b|\bcatalyst\b|\bnews\b'
                        r'|\bscann?er\b|\brelative volume\b|\brvol\b'
                        r'|\bwatch ?list\b|\bpre-?market\b|\bshares? outstanding\b'
                        r'|\bpick|\bselect|\bcriteri|\bstock must\b'),
    ('entry',           r'\bentr(y|ies)\b|\benter\b|\bbuy\b|\bgetting? in\b'
                        r'|\btrigger\b|\bbreak(out|s)? (above|over)\b|\blong\b'),
    ('stop-loss',       r'\bstop[- ]?loss\b|\bstop\b|\bcut (the )?loss'
                        r'|\bget out\b|\brisk (is|of|per)\b|\bmax loss\b'),
    ('exit',            r'\bexit\b|\bsell\b|\btake profit\b|\btarget\b'
                        r'|\bscal(e|ing) out\b|\btrail\b|\bhold(ing)? (the )?rest\b'),
    ('position-sizing', r'\bposition siz|\bshare size\b|\bhow many shares\b'
                        r'|\bsiz(e|ing) (up|down|the)\b|\brisk[- ]rewar'
                        r'|\bprofit[- ]loss ratio\b|\b\d+:\d+\b'),
    ('risk-limits',     r'\bdaily (max|loss|goal)\b|\bmax(imum)? loss\b'
                        r'|\bstop trading\b|\bshut (it )?down\b|\bwalk away\b'
                        r'|\bred day\b|\brule of\b|\bnever risk\b'),
    ('timing',          r'\b9:?3\d\b|\bopen(ing)? bell\b|\bfirst (hour|30|15)\b'
                        r'|\bmidday\b|\bpower hour\b|\btime of day\b|\bam\b|\bpm\b'
                        r'|\bmorning\b|\bafternoon\b'),
    ('patterns',        r'\bbull flag\b|\bflag\b|\bpullback\b|\babcd\b'
                        r'|\bgap and go\b|\bmicro pullback\b|\bflat top\b'
                        r'|\breversal\b|\bdip and rip\b|\bcandle\b|\bdoji\b'
                        r'|\bhammer\b|\bengulf'),
    ('indicators',      r'\bvwap\b|\bmacd\b|\bema\b|\bsma\b|\bmoving average\b'
                        r'|\bindicator\b|\blevel ?2\b|\btime (and|&) sales\b'
                        r'|\bbollinger\b|\bstochastic\b|\bvolume bar'),
    ('psychology',      r'\bemotion\b|\bdiscipline\b|\bfomo\b|\bgreed\b|\bfear\b'
                        r'|\brevenge\b|\bpatien|\bconfidence\b|\bmindset\b'
                        r'|\btilt\b|\boverconfiden'),
    ('account-admin',   r'\bpdt\b|\bpattern day trader\b|\bbroker\b|\bcommission\b'
                        r'|\bhotkey\b|\btax\b|\bmargin\b|\bsimulat|\bpaper trad'
                        r'|\bwithdraw\b|\bllc\b'),
]
BUCKET_RE = [(name, re.compile(pat, re.I)) for name, pat in BUCKETS]

# The channel's working vocabulary. A rule is tagged with every concept it
# mentions, and the tag counts are what reveal emphasis — the same instruction
# is written forty different ways, but it always names the same concept.
CONCEPTS = {
    'micro pullback': r'micro[- ]?pullback',
    'first candle to make a new high': r'new high|first candle.*high|makes? a new high',
    'first candle to make a new low': r'new low|first candle.*low|makes? a new low',
    'bull flag': r'bull flag',
    'flat top breakout': r'flat[- ]?top',
    'gap and go': r'gap ?(and|&|-) ?go|\bgapp?(er|ing)\b',
    'abcd pattern': r'\babcd\b',
    'dip and rip': r'dip ?(and|&|-) ?rip',
    'reversal': r'reversal|revers(e|ing)',
    'red-to-green move': r'red[ -]to[ -]green|\brtg\b',
    'high of day break': r'high of (the )?day|\bhod\b|day.?s high',
    'whole/half dollar level': r'whole (dollar|number)|half dollar|round number',
    'support and resistance': r'support|resistance',
    'moving average (9 EMA)': r'\b9 ?ema\b|nine ema',
    'moving average (20 EMA)': r'\b20 ?ema\b|twenty ema',
    'moving average (200 MA)': r'\b200 ?(ema|sma|ma)\b',
    'VWAP': r'\bvwap\b',
    'MACD': r'\bmacd\b',
    'volume confirmation': r'volume',
    'relative volume': r'relative volume|\brvol\b',
    'level 2 / time and sales': r'level ?2|time (and|&) sales|\btape\b',
    'float size': r'\bfloat\b',
    'news catalyst': r'catalyst|breaking news|\bnews\b|press release',
    'scanner alert': r'scann?er|\balert\b',
    'pre-market activity': r'pre-?market',
    'first hour / market open': r'9:?3\d|market open|opening bell|first (hour|30 min|15 min)',
    'midday avoidance': r'midday|lunch|after 11|11:?\d\d ?a',
    'stop at pullback low': r'stop.{0,30}(low of|pullback|flag)',
    'stop at whole number': r'stop.{0,30}(whole|half) (dollar|number)',
    'break-even stop': r'break[- ]?even',
    'trailing stop': r'trail',
    'max loss per trade': r'max(imum)? loss|risk (no )?more than|never risk',
    'daily loss limit': r'daily (max|loss|stop)|stop trading|shut (it )?down|walk away',
    'profit-loss ratio 2:1': r'2 ?: ?1|two to one|twice',
    'scaling out': r'scal(e|ing) out|sell(ing)? half|take (some )?profit',
    'adding to a winner': r'add(ing)? to|scal(e|ing) in',
    'position sizing by risk': r'position siz|share size|how many shares',
    'accuracy / win rate': r'accuracy|win rate|percentage of.{0,10}win',
    'A-quality setup only': r'a[- ]quality|\ba\+? setup|best setup|quality setup',
    'watchlist': r'watch ?list',
    'paper trading / simulator': r'simulat|paper trad|demo account',
    'hotkeys': r'hot ?key',
    'PDT rule': r'\bpdt\b|pattern day trader|25,?000',
    'emotional control': r'emotion|discipline|fomo|greed|fear|revenge|tilt|patien',
    'halts': r'\bhalt',
    'short selling': r'short(ing|-sell| sell)',
    'small cap focus': r'small[- ]?cap|penny stock|low[- ]?float',
    'daily chart context': r'daily chart|daily (level|resistance|support)',
}
CONCEPT_RE = [(name, re.compile(pat, re.I)) for name, pat in CONCEPTS.items()]

STOPWORDS = set('''a an the to of in on at for with and or is are be do dont
don't you your it its this that these those if when then than as by from into
over under out up down not no more most very just also can will would should
i we they he she my our their there here what which who how why all any some
each other same so such only own too s t re ve ll'''.split())

# What a figure measures, decided by the words around it. Ordered by
# specificity: "20 million float" must not be filed under a bare price rule.
UNITS = [
    ('float (shares)',        r'float'),
    ('relative volume (x)',   r'relative volume|\brvol\b|times? (the )?(average|normal) volume'),
    ('share volume',          r'\bvolume\b'),
    ('share price ($)',       r'\bprice\b|\bstock (is|at|between|under|over)\b|\btrading (at|between)\b'),
    ('percent gain (%)',      r'\bgain|\bup\b|\bmove(d|s)?\b|\bpercent|%'),
    ('position size (shares)', r'\bshares?\b'),
    ('account size ($)',      r'\baccount\b|\bcapital\b|\bstart(ed|ing)? with\b'),
    ('profit-loss ratio',     r'\bprofit[- ]loss\b|\brisk[- ]rewar|\b\d+:\d+'),
    ('max loss ($)',          r'\bmax(imum)? loss\b|\bdaily loss\b|\bstop trading\b'),
    ('win rate (%)',          r'\bwin rate\b|\baccuracy\b|\bsuccess rate\b'),
    ('time of day',           r'\b9:\d\d|\b10:\d\d|\bminutes? (after|into)\b|\bam\b|\bpm\b'),
]
UNIT_RE = [(name, re.compile(pat, re.I)) for name, pat in UNITS]

NUM_RE = re.compile(
    r'\$?\d[\d,]*\.?\d*\s*(?:million|mil|m\b|billion|b\b|k\b|%|:1|x\b)?', re.I)
TS_RE = re.compile(r'^\s*[-*]\s*\[[\d:]+\]\s*')
STAMP_RE = re.compile(r'\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]')
BULLET_RE = re.compile(r'^\s*[-*]\s+')
NONE_RE = re.compile(r'_none|no specific|none stated', re.I)


def stamp_seconds(line):
    """The [hh:mm:ss] on a bullet, as seconds. None when the summary omitted it.

    Kept so the digest can cite. Dropping this was the reason "which video says
    this?" used to require re-deriving the answer from the summaries by hand.
    """
    m = STAMP_RE.search(line)
    if not m:
        return None
    a, b, c = m.group(1), m.group(2), m.group(3)
    if c is None:
        return int(a) * 60 + int(b)
    return int(a) * 3600 + int(b) * 60 + int(c)


def cite(vid, secs):
    """A markdown link that opens the video at the moment the rule was said."""
    url = f'https://www.youtube.com/watch?v={vid}'
    if secs is None:
        return f'[`{vid}`]({url})'
    return f'[`{vid}` @{secs // 60}:{secs % 60:02d}]({url}&t={secs}s)'


def read_section(body, heading):
    """Return the bullet lines under one `## heading`."""
    lines, grab = [], False
    for line in body.splitlines():
        if line.startswith('## '):
            grab = line[3:].strip() == heading
            continue
        if grab and BULLET_RE.match(line):
            lines.append(line)
    return lines


def clean(line):
    """Strip the bullet, the timestamp and bold markers."""
    text = TS_RE.sub('', line)
    text = BULLET_RE.sub('', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    return text.strip()


def signature(text):
    """A word-set fingerprint, so two phrasings of one rule collapse together."""
    words = [w for w in re.findall(r'[a-z]+', text.lower())
             if w not in STOPWORDS and len(w) > 2]
    return ' '.join(sorted(set(words))[:7])


def bucket_of(text):
    for name, pat in BUCKET_RE:
        if pat.search(text):
            return name
    return 'other'


def concepts_of(text):
    """Every vocabulary item the rule invokes. A rule usually names two or three
    — "buy the micro pullback over the 9 EMA on volume" is one sentence and
    three concepts — so tags are not exclusive the way buckets are."""
    return [name for name, pat in CONCEPT_RE if pat.search(text)]


def unit_of(text):
    for name, pat in UNIT_RE:
        if pat.search(text):
            return name
    return 'unclassified'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--per-bucket', type=int, default=30,
                    help='how many distinct rules to print per subject')
    args = ap.parse_args()

    paths = [p for p in sorted(glob.glob(os.path.join(SUMMARIES, '*.md')))
             if os.path.basename(p) not in ('_SCHEMA.md', 'INDEX.md')]

    # sig -> {text: best phrasing, videos: set, bucket: name}
    rules = {}
    numbers = defaultdict(list)
    setups = Counter()
    setup_defs = {}
    tools = Counter()
    n_rules = n_numbers = 0

    for path in paths:
        vid = os.path.splitext(os.path.basename(path))[0]
        with open(path, encoding='utf-8') as f:
            body = f.read()

        for line in read_section(body, 'Mechanical rules'):
            text = clean(line)
            if not text or NONE_RE.search(text):
                continue
            n_rules += 1
            sig = signature(text)
            if not sig:
                continue
            secs = stamp_seconds(line)
            rec = rules.setdefault(sig, {'text': text, 'videos': set(),
                                         'bucket': bucket_of(text),
                                         'concepts': concepts_of(text),
                                         'cite': (vid, secs)})
            rec['videos'].add(vid)
            # Keep the shortest phrasing: the terser statement of a repeated
            # rule is almost always the clearer one. The citation travels with
            # it, so the printed link always points at the printed sentence.
            if len(text) < len(rec['text']):
                rec['text'] = text
                rec['cite'] = (vid, secs)

        for line in read_section(body, 'Numbers and thresholds'):
            text = clean(line)
            if not text or NONE_RE.search(text):
                continue
            n_numbers += 1
            numbers[unit_of(text)].append((text, vid, stamp_seconds(line)))

        for line in read_section(body, 'Setups and patterns'):
            text = clean(line)
            if not text or NONE_RE.search(text):
                continue
            name = re.split(r'\s+[—–-]\s+', text)[0].strip().lower()
            name = re.sub(r'[^a-z0-9 &/-]', '', name)[:40].strip()
            if name:
                setups[name] += 1
                if name not in setup_defs and '—' in text:
                    setup_defs[name] = text.split('—', 1)[1].strip()[:160]

        for line in read_section(body, 'Indicators, tools, platforms'):
            text = clean(line)
            if not text or NONE_RE.search(text):
                continue
            name = re.split(r'\s+[—–-]\s+', text)[0].strip().lower()
            name = re.sub(r'\(.*?\)', '', name)
            name = re.sub(r'[^a-z0-9 &/.-]', '', name)[:40].strip()
            if name:
                tools[name] += 1

    by_bucket = defaultdict(list)
    for rec in rules.values():
        by_bucket[rec['bucket']].append(rec)

    concept_freq = Counter()
    for rec in rules.values():
        for c in rec['concepts']:
            concept_freq[c] += 1

    out = [
        '# Rules digest',
        '',
        f'{n_rules} rule statements from {len(paths)} videos. Each is filed '
        'under one subject and tagged with every concept it names. The concept '
        'counts, not the sentence counts, are what show emphasis: the same '
        'instruction is written a different way in every video.',
        '',
        'Every rule and figure links to the video and the second it was\n        stated; where a rule is stated in several videos the link is to the\n        clearest phrasing.',
        '',
        'Generated by `scripts/pipeline/07_extract_rules.py`.',
        '',
        '## Concept frequency across all rules',
        '',
    ]
    for name, n in concept_freq.most_common():
        out.append(f'- **{n}** {name}')
    out.append('')

    order = [n for n, _ in BUCKETS] + ['other']
    for name in order:
        recs = by_bucket.get(name)
        if not recs:
            continue
        out += [f'## {name} ({len(recs)} rules)', '']

        # Inside a subject, lead with the concepts that subject leans on hardest,
        # and print each rule under the first one it hits. A rule with no
        # recognised concept still gets printed, at the end, rather than lost.
        local = Counter(c for r in recs for c in r['concepts'])
        printed = set()
        for concept, _ in local.most_common():
            group = [r for r in recs
                     if concept in r['concepts'] and id(r) not in printed]
            if len(group) < 2:
                continue
            out += [f'### {concept} ({len(group)})', '']
            for rec in group[:args.per_bucket]:
                printed.add(id(rec))
                n_vids = len(rec['videos'])
                seen_in = f' _({n_vids} videos)_' if n_vids > 1 else ''
                out.append(f'- {rec["text"]} — {cite(*rec["cite"])}{seen_in}')
            if len(group) > args.per_bucket:
                out.append(f'- _...{len(group) - args.per_bucket} more._')
                for rec in group:
                    printed.add(id(rec))
            out.append('')

        rest = [r for r in recs if id(r) not in printed]
        if rest:
            out += [f'### uncategorised ({len(rest)})', '']
            for rec in rest[:args.per_bucket]:
                out.append(f'- {rec["text"]} — {cite(*rec["cite"])}')
            if len(rest) > args.per_bucket:
                out.append(f'- _...{len(rest) - args.per_bucket} more._')
            out.append('')

    out += ['## Named setups, by how many videos discuss them', '']
    for name, n in setups.most_common(40):
        definition = setup_defs.get(name, '')
        out.append(f'- **{n}x** {name}' + (f' — {definition}' if definition else ''))

    out += ['', '## Tools and indicators, by how many videos mention them', '']
    for name, n in tools.most_common(40):
        out.append(f'- **{n}x** {name}')

    out += ['', f'## Numeric thresholds ({n_numbers} figures)', '']
    for unit, _ in UNITS + [('unclassified', '')]:
        entries = numbers.get(unit)
        if not entries:
            continue
        out += [f'### {unit} ({len(entries)})', '']
        seen = set()
        for text, vid, secs in entries:
            sig = signature(text)
            if sig in seen:
                continue
            seen.add(sig)
            out.append(f'- {text} — {cite(vid, secs)}')
            if len(seen) >= args.per_bucket:
                out.append(f'- _...{len(entries) - len(seen)} more figures._')
                break
        out.append('')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))

    print(f'{n_rules} rule statements -> {len(rules)} distinct')
    for name in order:
        if by_bucket.get(name):
            print(f'  {name:16} {len(by_bucket[name]):4d}')
    print(f'{n_numbers} numeric figures, {len(setups)} setup names, '
          f'{len(tools)} tool names')
    print(f'Wrote {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
