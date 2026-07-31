#!/usr/bin/env python3
"""Split timestamped transcripts into overlapping, timestamped chunks.

Auto-generated captions carry no punctuation, so sentence splitting is
unreliable. Instead this uses a sliding window measured in words, which keeps
chunks a predictable size for the embedding model while the overlap stops an
idea from being cut in half at a boundary.

Every chunk keeps the video id and its start/end timestamp so any rule
extracted downstream can be cited back to the exact moment it was said.

Input:  data/subtitles/<video_id>.txt
Output: data/kb/chunks.jsonl

Usage:
    python scripts/pipeline/01_chunk.py [--words 220] [--overlap 60]
"""

import argparse
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
SUB_DIR = os.path.join(ROOT, 'data', 'subtitles')
OUT_DIR = os.path.join(ROOT, 'data', 'kb')
OUT_PATH = os.path.join(OUT_DIR, 'chunks.jsonl')

LINE_RE = re.compile(r'^\[(\d{2}):(\d{2}):(\d{2})\]\s*(.*)$')


def parse_transcript(path):
    """Return (meta, [(seconds, text), ...]) for one transcript file."""
    meta = {'title': '', 'url': '', 'duration_sec': None}
    events = []

    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('# https://'):
                meta['url'] = line[2:].strip()
            elif line.startswith('# duration_sec:'):
                raw = line.split(':', 1)[1].strip()
                meta['duration_sec'] = int(raw) if raw.isdigit() else None
            elif line.startswith('#') and not meta['title']:
                meta['title'] = line[1:].strip()
            else:
                m = LINE_RE.match(line)
                if m:
                    h, mm, s, text = m.groups()
                    if text:
                        events.append((int(h) * 3600 + int(mm) * 60 + int(s), text))
    return meta, events


def chunk_events(events, target_words, overlap_words):
    """Slide a word-count window over caption events.

    Yields (start_sec, end_sec, text). The window advances by
    target_words - overlap_words, so consecutive chunks share context.
    """
    # Flatten to words while remembering the timestamp each word came from.
    words, stamps = [], []
    for sec, text in events:
        for w in text.split():
            words.append(w)
            stamps.append(sec)

    if not words:
        return

    stride = max(target_words - overlap_words, 1)
    for start in range(0, len(words), stride):
        window = words[start:start + target_words]
        if not window:
            break
        # Drop a trailing stub that is almost entirely overlap already.
        if start > 0 and len(window) < overlap_words:
            break
        yield stamps[start], stamps[min(start + len(window) - 1, len(stamps) - 1)], \
            ' '.join(window)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--words', type=int, default=220,
                    help='target words per chunk')
    ap.add_argument('--overlap', type=int, default=60,
                    help='words shared between consecutive chunks')
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    paths = sorted(glob.glob(os.path.join(SUB_DIR, '*.txt')))
    print(f'Transcripts: {len(paths)}', flush=True)

    n_chunks = 0
    skipped = 0
    with open(OUT_PATH, 'w', encoding='utf-8') as out:
        for i, path in enumerate(paths, 1):
            video_id = os.path.splitext(os.path.basename(path))[0]
            meta, events = parse_transcript(path)
            if not events:
                skipped += 1
                continue

            for start, end, text in chunk_events(events, args.words, args.overlap):
                rec = {
                    'chunk_id': f'{video_id}:{start}',
                    'video_id': video_id,
                    'title': meta['title'],
                    'url': meta['url'],
                    't_start': start,
                    't_end': end,
                    'text': text,
                }
                out.write(json.dumps(rec, ensure_ascii=False) + '\n')
                n_chunks += 1

            if i % 250 == 0:
                print(f'  {i}/{len(paths)} files -> {n_chunks:,} chunks', flush=True)

    print(f'Wrote {n_chunks:,} chunks from {len(paths) - skipped} transcripts '
          f'({skipped} empty) -> {OUT_PATH}', flush=True)


if __name__ == '__main__':
    main()
