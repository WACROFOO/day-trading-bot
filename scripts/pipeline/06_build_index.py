#!/usr/bin/env python3
"""Build the master index from the per-transcript summaries.

Each file in knowledge-base/summaries/ carries YAML frontmatter and a fixed set
of headings (see _SCHEMA.md). This script reads that structure across all of
them and produces one navigable document plus a machine-readable roll-up.

The frontmatter is parsed by hand rather than with PyYAML: the schema fixes the
key set and the value shapes, so a dependency buys nothing, and a hand parser
fails loudly on a malformed file instead of silently accepting it.

Input:  knowledge-base/summaries/<video_id>.md
Output: knowledge-base/summaries/INDEX.md      browsable index
        knowledge-base/data/summary_index.json same data, for later scripts

Usage:
    python scripts/pipeline/06_build_index.py [--strict]
"""

import argparse
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
SUMMARIES = os.path.join(ROOT, 'knowledge-base', 'summaries')
INDEX_MD = os.path.join(SUMMARIES, 'INDEX.md')
INDEX_JSON = os.path.join(ROOT, 'knowledge-base', 'data', 'summary_index.json')

# Section headings the schema mandates, mapped to the key they land under.
SECTIONS = {
    'Mechanical rules': 'rules',
    'Setups and patterns': 'setups',
    'Indicators, tools, platforms': 'tools',
    'Numbers and thresholds': 'numbers',
    'Claims needing verification': 'claims',
    'Caption quality notes': 'caption_notes',
}

CLASS_LABEL = {
    'howto': 'How-to and guides',
    'rules': 'Strategies, setups, rules',
    'mistakes': 'Mistakes and lessons',
}

NONE_MARKERS = ('_none stated._', '_none._', 'none stated.')

# The summaries were written independently, so the same subject arrived under
# several spellings. Merging them is what makes the topic list navigable: an
# unmerged list splits `momentum` across three tags and buries all three.
ALIASES = {
    'momentum-trading': 'momentum',
    'momentum-stocks': 'momentum',
    'candlestick-patterns': 'candlesticks',
    'candlestick': 'candlesticks',
    'moving-averages': 'moving-average',
    'ema': 'moving-average',
    'sma': 'moving-average',
    'support-and-resistance': 'support-resistance',
    'stop-losses': 'stop-loss',
    'entry': 'entries',
    'exit': 'exits',
    'risk': 'risk-management',
    'position-size': 'position-sizing',
    'scanner': 'scanners',
    'broker': 'brokers',
    'catalysts': 'catalyst',
    'premarket': 'pre-market',
    'halts': 'halt',
    'level2': 'level-2',
    'vwap-strategy': 'vwap',
    'small-accounts': 'small-account',
    'shorting': 'short-selling',
    'short-sell': 'short-selling',
    'tax': 'taxes',
}


def normalise_topics(tags, seen):
    """Apply the alias map, then collapse a plural onto its singular when both
    spellings appear somewhere in the corpus. Tags with only one spelling are
    left exactly as written."""
    out = []
    for t in tags:
        t = ALIASES.get(t, t)
        if t.endswith('s') and t[:-1] in seen and t not in ALIASES.values():
            t = t[:-1]
        if t not in out:
            out.append(t)
    return out


def parse_frontmatter(text, path):
    """Return (dict, body). Raises ValueError on a malformed header."""
    if not text.startswith('---'):
        raise ValueError('no YAML frontmatter')
    end = text.find('\n---', 3)
    if end == -1:
        raise ValueError('unterminated frontmatter')
    head, body = text[3:end], text[end + 4:]

    meta = {}
    for line in head.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' not in line:
            raise ValueError(f'frontmatter line is not key: value -> {line!r}')
        key, _, val = line.partition(':')
        key, val = key.strip(), val.strip()

        if val.startswith('[') and val.endswith(']'):
            val = [v.strip().strip('"\'') for v in val[1:-1].split(',') if v.strip()]
        elif val.lower() in ('true', 'false'):
            val = val.lower() == 'true'
        elif re.fullmatch(r'-?\d+', val):
            val = int(val)
        else:
            val = val.strip('"\'')
        meta[key] = val
    return meta, body


def split_sections(body):
    """Map each `## Heading` to its bullet lines."""
    out = {}
    current = None
    for line in body.splitlines():
        if line.startswith('## '):
            current = line[3:].strip()
            out[current] = []
        elif current is not None:
            out[current].append(line)
    return out


def count_bullets(lines):
    """Bullets in a section, treating an explicit 'none' marker as zero."""
    joined = '\n'.join(lines).strip().lower()
    if not joined or any(m in joined for m in NONE_MARKERS):
        return 0
    return sum(1 for ln in lines if ln.lstrip().startswith(('- ', '* ')))


def load_one(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    meta, body = parse_frontmatter(text, path)
    sections = split_sections(body)

    rec = {
        'video_id': meta.get('video_id') or os.path.splitext(os.path.basename(path))[0],
        'title': meta.get('title', ''),
        'url': meta.get('url', ''),
        'duration_min': meta.get('duration_min'),
        'teaching_class': meta.get('teaching_class', ''),
        'topics': meta.get('topics') or [],
        'has_rules': bool(meta.get('has_rules')),
        'summary_file': f"{os.path.splitext(os.path.basename(path))[0]}.md",
        'counts': {},
    }
    for heading, key in SECTIONS.items():
        rec['counts'][key] = count_bullets(sections.get(heading, []))

    # The flag is a claim about the file; trust the file's own content over it.
    rec['has_rules'] = rec['counts']['rules'] > 0
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--strict', action='store_true',
                    help='stop on the first unparseable summary instead of '
                         'reporting it and continuing')
    args = ap.parse_args()

    paths = [p for p in sorted(glob.glob(os.path.join(SUMMARIES, '*.md')))
             if os.path.basename(p) not in ('_SCHEMA.md', 'INDEX.md')]

    records, broken = [], []
    for p in paths:
        try:
            records.append(load_one(p))
        except (ValueError, OSError) as exc:
            if args.strict:
                raise
            broken.append((os.path.basename(p), str(exc)))

    if broken:
        print(f'{len(broken)} summaries failed to parse:')
        for name, why in broken:
            print(f'  {name}: {why}')

    if not records:
        print('No summaries found. Run the summarisation fleet first.')
        return

    # Two passes: the plural-collapse rule can only fire once every spelling in
    # the corpus is known, so the vocabulary is gathered before it is applied.
    raw_before = len({ALIASES.get(t, t) for r in records for t in r['topics']})
    seen = {ALIASES.get(t, t) for r in records for t in r['topics']}
    for r in records:
        r['topics'] = normalise_topics(r['topics'], seen)

    # Topic frequency drives the topic section of the index and shows at a
    # glance which subjects the corpus actually covers in depth.
    topics = {}
    for r in records:
        for t in r['topics']:
            topics.setdefault(t, []).append(r['video_id'])

    totals = {key: sum(r['counts'][key] for r in records) for key in SECTIONS.values()}
    by_class = {}
    for r in records:
        by_class.setdefault(r['teaching_class'] or 'unclassified', []).append(r)

    hours = sum(r['duration_min'] or 0 for r in records) / 60

    lines = [
        '# Transcript index',
        '',
        f'{len(records)} videos, {hours:.0f} hours. One summary per transcript in '
        'this directory, written to `_SCHEMA.md`.',
        '',
        'Generated by `scripts/pipeline/06_build_index.py` — do not edit by hand.',
        '',
        '## What is in the corpus',
        '',
        '| section | entries |',
        '|---|---|',
        f'| mechanical rules | {totals["rules"]} |',
        f'| setups and patterns | {totals["setups"]} |',
        f'| indicators, tools, platforms | {totals["tools"]} |',
        f'| numbers and thresholds | {totals["numbers"]} |',
        f'| claims needing verification | {totals["claims"]} |',
        '',
        f'{sum(1 for r in records if r["has_rules"])} of {len(records)} videos '
        'state at least one codeable rule.',
        '',
        '## Topics',
        '',
        'Tag, then how many videos carry it. Tags were written per-summary and '
        'then merged by the alias map in the build script, so spelling variants '
        'of one subject appear once.',
        '',
    ]

    for tag, ids in sorted(topics.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        lines.append(f'- `{tag}` — {len(ids)}')

    lines += ['', '## Videos', '']

    for cls in ('howto', 'rules', 'mistakes'):
        group = by_class.get(cls)
        if not group:
            continue
        group.sort(key=lambda r: -(r['duration_min'] or 0))
        lines += [
            f'### {CLASS_LABEL[cls]} ({len(group)})',
            '',
            '| video | min | rules | numbers | topics |',
            '|---|---|---|---|---|',
        ]
        for r in group:
            title = (r['title'] or r['video_id']).replace('|', '\\|')
            topic_s = ', '.join(f'`{t}`' for t in r['topics'][:5])
            lines.append(
                f'| [{title}]({r["summary_file"]}) | {r["duration_min"] or "?"} '
                f'| {r["counts"]["rules"]} | {r["counts"]["numbers"]} | {topic_s} |')
        lines.append('')

    leftovers = by_class.get('unclassified')
    if leftovers:
        lines += [f'### Unclassified ({len(leftovers)})', '']
        for r in leftovers:
            lines.append(f'- [{r["title"] or r["video_id"]}]({r["summary_file"]})')
        lines.append('')

    with open(INDEX_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    os.makedirs(os.path.dirname(INDEX_JSON), exist_ok=True)
    with open(INDEX_JSON, 'w', encoding='utf-8') as f:
        json.dump({
            'video_count': len(records),
            'total_hours': round(hours, 1),
            'totals': totals,
            'topics': {t: sorted(ids) for t, ids in topics.items()},
            'unparseable': [{'file': n, 'error': w} for n, w in broken],
            'videos': records,
        }, f, indent=2, ensure_ascii=False)

    print(f'{len(records)} summaries indexed, {hours:.0f}h')
    for key in ('rules', 'setups', 'tools', 'numbers', 'claims'):
        print(f'  {key:8} {totals[key]:5d}')
    print(f'  topics   {len(topics):5d}  (merged from {raw_before})')
    print(f'Wrote {os.path.relpath(INDEX_MD, ROOT)}')
    print(f'Wrote {os.path.relpath(INDEX_JSON, ROOT)}')


if __name__ == '__main__':
    main()
