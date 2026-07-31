#!/usr/bin/env python3
"""Plan the per-transcript summarisation work into balanced batches.

Transcript length varies by a factor of forty (9 KB to 360 KB), so batching by
file count would hand one worker a trivial job and another more text than fits
in its context. Batches are packed by byte budget instead, longest file first,
which keeps every batch inside the context limit and roughly equal in size.

Files already summarised are skipped, so the plan can be regenerated after a
partial run and will only contain outstanding work.

Input:  knowledge-base/transcripts/*.txt
        knowledge-base/data/teaching_shortlist.json   for titles and classes
Output: knowledge-base/data/summary_batches.json

Usage:
    python scripts/pipeline/04_plan_summaries.py [--budget-kb 200]
"""

import argparse
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
TRANSCRIPTS = os.path.join(ROOT, 'knowledge-base', 'transcripts')
SUMMARIES = os.path.join(ROOT, 'knowledge-base', 'summaries')
SHORTLIST = os.path.join(ROOT, 'knowledge-base', 'data', 'teaching_shortlist.json')
OUT = os.path.join(ROOT, 'knowledge-base', 'data', 'summary_batches.json')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--budget-kb', type=int, default=200,
                    help='max transcript bytes per batch, in KB')
    ap.add_argument('--all', action='store_true',
                    help='replan every transcript, not just the missing ones')
    args = ap.parse_args()

    with open(SHORTLIST, encoding='utf-8') as f:
        meta = {v['id']: v for v in json.load(f)['videos']}

    items = []
    for path in sorted(glob.glob(os.path.join(TRANSCRIPTS, '*.txt'))):
        vid = os.path.splitext(os.path.basename(path))[0]
        done = os.path.exists(os.path.join(SUMMARIES, f'{vid}.md'))
        if done and not args.all:
            continue
        m = meta.get(vid, {})
        items.append({
            'id': vid,
            'bytes': os.path.getsize(path),
            'title': m.get('title', ''),
            'duration_sec': m.get('duration_sec'),
            'teaching_class': m.get('teaching_class', ''),
        })

    if not items:
        print('Nothing outstanding: every transcript already has a summary.')
        return

    budget = args.budget_kb * 1024
    # Longest first: an oversized file lands alone in its own batch instead of
    # dragging a nearly-full batch over the limit.
    items.sort(key=lambda i: -i['bytes'])

    batches = []
    for it in items:
        for b in batches:
            if b['bytes'] + it['bytes'] <= budget:
                b['items'].append(it)
                b['bytes'] += it['bytes']
                break
        else:
            batches.append({'items': [it], 'bytes': it['bytes']})

    for n, b in enumerate(batches, 1):
        b['batch'] = n

    total = sum(b['bytes'] for b in batches)
    print(f'{len(items)} transcripts, {total / 1e6:.1f} MB -> {len(batches)} batches '
          f'(budget {args.budget_kb} KB)')
    print(f'  largest batch  {max(b["bytes"] for b in batches) / 1024:.0f} KB')
    print(f'  smallest batch {min(b["bytes"] for b in batches) / 1024:.0f} KB')
    print(f'  files/batch    {min(len(b["items"]) for b in batches)}'
          f'-{max(len(b["items"]) for b in batches)}')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'budget_kb': args.budget_kb,
                   'batch_count': len(batches),
                   'batches': batches}, f, indent=2, ensure_ascii=False)
    print(f'Wrote {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
