#!/usr/bin/env python3
"""Build the queryable claims database from summaries and transcripts.

Everything downstream of the summaries has so far been prose: `rules_digest.md`
counts concepts, `PARAMETERS.md` asserts an `n=`, and neither can be checked
without rerunning the pipeline by hand. The counts were right, but they were
not *auditable* — the extractor reads the video id from each summary filename
and then throws it away when it writes the digest.

This stage keeps it. One row per claim, provenance mandatory, so:

    n = SELECT COUNT(*) FROM claim WHERE ...

is a query rather than an assertion, and every claim carries the video and the
second it was said. Deep links are derived, never stored.

Two layers get indexed, and the difference matters:

  claim  - the summariser's extracted statements. Clean, tagged, citable, and
           *lossy*: a rule the summariser skipped is not in here.
  chunk  - windows of the raw captions. Noisy and unpunctuated, but complete.
           This is the layer that can answer "did he ever say X", which the
           summaries structurally cannot.

Both get an FTS5 index. Searching claims tells you what the corpus teaches;
searching chunks tells you what it actually contains.

The taxonomy (subject buckets, concept vocabulary, unit classes) is imported
from 07_extract_rules.py rather than restated, so the digest and the database
can never drift apart.

Input:  knowledge-base/summaries/<video_id>.md
        knowledge-base/transcripts/<video_id>.txt
Output: data/claims.db

Usage:
    python scripts/pipeline/12_build_claims_db.py
    python scripts/pipeline/12_build_claims_db.py --no-transcripts   # faster
"""

import argparse
import glob
import importlib.util
import json
import os
import re
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
SUMMARIES = os.path.join(ROOT, 'knowledge-base', 'summaries')
TRANSCRIPTS = os.path.join(ROOT, 'knowledge-base', 'transcripts')
OUT = os.path.join(ROOT, 'data', 'claims.db')

SKIP_FILES = {'_SCHEMA.md', 'INDEX.md'}

# The summariser writes a fixed heading set (summaries/_SCHEMA.md), so each
# section maps to a claim kind. Casing varies in a couple of files.
SECTIONS = {
    'mechanical rules': 'rule',
    'numbers and thresholds': 'number',
    'setups and patterns': 'setup',
    'indicators, tools, platforms': 'tool',
    'claims needing verification': 'caveat',
}


def load_taxonomy():
    """Import 07_extract_rules.py for its buckets, concepts and unit classes.

    The module name starts with a digit, so a plain import statement is not
    valid syntax and it has to be loaded by path.
    """
    path = os.path.join(os.path.dirname(__file__), '07_extract_rules.py')
    spec = importlib.util.spec_from_file_location('extract_rules', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TS_RE = re.compile(r'\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]')
BULLET_RE = re.compile(r'^\s*[-*]\s+')
NONE_RE = re.compile(r'_none|no specific|none stated', re.I)
FM_RE = re.compile(r'^---\n(.*?)\n---', re.S)


def parse_ts(text):
    """First [hh:mm:ss] or [mm:ss] in the line, as seconds. None if absent.

    A handful of summaries carry a malformed stamp like [00:207] where the
    caption index lost a colon. Those parse as mm:ss and land in the right
    minute, which is close enough for a deep link.
    """
    m = TS_RE.search(text)
    if not m:
        return None
    a, b, c = m.group(1), m.group(2), m.group(3)
    if c is None:
        return int(a) * 60 + int(b)
    return int(a) * 3600 + int(b) * 60 + int(c)


def parse_frontmatter(body):
    m = FM_RE.match(body)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ':' not in line:
            continue
        k, v = line.split(':', 1)
        out[k.strip()] = v.strip().strip('"')
    return out


def iter_sections(body):
    """Yield (kind, bullet_line) for every bullet under a known heading."""
    kind = None
    for line in body.splitlines():
        if line.startswith('## '):
            kind = SECTIONS.get(line[3:].strip().lower())
            continue
        if kind and BULLET_RE.match(line):
            yield kind, line


def clean(line):
    text = TS_RE.sub('', line)
    text = BULLET_RE.sub('', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    return re.sub(r'\s{2,}', ' ', text).strip(' .')


# --- numeric parsing ---------------------------------------------------------
#
# The point of a typed value is not tidiness, it is disagreement. "float under
# 20 million" and "float under 10 million" are both in the corpus; as prose one
# becomes a footnote on the other, as rows they are a distribution you can see.

SCALE = {'million': 1e6, 'mil': 1e6, 'm': 1e6, 'billion': 1e9, 'b': 1e9,
         'k': 1e3, 'thousand': 1e3}

OPS = [
    ('range', r'\bbetween\b|\bto\b|\brange\b|–|—'),
    ('<=', r'\bunder\b|\bbelow\b|\bless than\b|\bno more than\b|\bmax(imum)?\b'
           r'|\bup to\b|\bsmaller than\b|\bunderneath\b'),
    ('>=', r'\bover\b|\babove\b|\bat least\b|\bmore than\b|\bmin(imum)?\b'
           r'|\bor (higher|more|greater)\b|\bgreater than\b|\bplus\b|\+'),
]
OPS_RE = [(op, re.compile(pat, re.I)) for op, pat in OPS]

NUM_RE = re.compile(
    r'\$?\s?(\d[\d,]*(?:\.\d+)?)\s*'
    r'(million|mil|billion|thousand|[mbk]\b|%|x\b|:1)?', re.I)


def parse_numbers(text):
    """Every figure in the line, scaled. Returns [(value, suffix, pos), ...]."""
    out = []
    for m in NUM_RE.finditer(text):
        raw = m.group(1).replace(',', '')
        try:
            val = float(raw)
        except ValueError:
            continue
        suffix = (m.group(2) or '').lower().strip()
        if suffix in SCALE:
            val *= SCALE[suffix]
        out.append((val, suffix, m.start()))
    return out


def classify(text, unit_re):
    """The unit class this line measures, and where that keyword sits.

    The position is the point of this: a summary bullet is a whole sentence
    ("Trade 2 Day 6: 500 shares at $4.20, float 2.9 million"), so taking the
    first figure files 2 as a float. Taking the figure *nearest the keyword*
    files 2.9 million, which is what the line actually says.
    """
    for name, pat in unit_re:
        m = pat.search(text)
        if m:
            return name, m.start()
    return 'unclassified', 0


def pick_numbers(nums, anchor):
    """Reorder figures by distance from the keyword that named the unit."""
    return sorted(nums, key=lambda n: abs(n[2] - anchor))


def parse_op(text):
    for op, pat in OPS_RE:
        if pat.search(text):
            return op
    return '='


def build_schema(db):
    db.executescript("""
    PRAGMA journal_mode = WAL;

    CREATE TABLE video (
      video_id       TEXT PRIMARY KEY,
      title          TEXT,
      url            TEXT,
      duration_min   INTEGER,
      teaching_class TEXT,
      topics         TEXT
    );

    -- One row per statement the summariser extracted. t_start is the second in
    -- the video where it was said; NULL only when the summary omitted a stamp.
    CREATE TABLE claim (
      id       INTEGER PRIMARY KEY,
      video_id TEXT NOT NULL REFERENCES video(video_id),
      t_start  INTEGER,
      kind     TEXT NOT NULL,     -- rule | number | setup | tool | caveat
      subject  TEXT,              -- entry | stop-loss | exit | ...
      text     TEXT NOT NULL,
      sig      TEXT               -- word fingerprint, for collapsing rephrasings
    );
    CREATE INDEX claim_video ON claim(video_id);
    CREATE INDEX claim_kind  ON claim(kind);
    CREATE INDEX claim_sig   ON claim(sig);

    -- Many-to-many: one sentence usually names two or three concepts.
    CREATE TABLE claim_concept (
      claim_id INTEGER NOT NULL REFERENCES claim(id),
      concept  TEXT NOT NULL,
      PRIMARY KEY (claim_id, concept)
    );
    CREATE INDEX cc_concept ON claim_concept(concept);

    -- Typed figures. value_max is set only when op = 'range'.
    CREATE TABLE param (
      id        INTEGER PRIMARY KEY,
      claim_id  INTEGER NOT NULL REFERENCES claim(id),
      video_id  TEXT NOT NULL,
      t_start   INTEGER,
      name      TEXT NOT NULL,    -- unit class: float (shares), share price ($), ...
      op        TEXT NOT NULL,    -- <= | >= | = | range
      value     REAL NOT NULL,
      value_max REAL,
      raw       TEXT NOT NULL
    );
    CREATE INDEX param_name ON param(name);

    -- Windows of raw caption text. Complete but noisy: this is the layer that
    -- can prove a rule was never stated, which the summaries cannot.
    CREATE TABLE chunk (
      id       INTEGER PRIMARY KEY,
      video_id TEXT NOT NULL,
      t_start  INTEGER NOT NULL,
      t_end    INTEGER NOT NULL,
      text     TEXT NOT NULL
    );
    CREATE INDEX chunk_video ON chunk(video_id);

    CREATE VIRTUAL TABLE claim_fts USING fts5(
      text, content='claim', content_rowid='id', tokenize='porter unicode61');
    CREATE VIRTUAL TABLE chunk_fts USING fts5(
      text, content='chunk', content_rowid='id', tokenize='porter unicode61');
    """)


def load_summaries(db, tax):
    paths = [p for p in sorted(glob.glob(os.path.join(SUMMARIES, '*.md')))
             if os.path.basename(p) not in SKIP_FILES]
    n_claims = n_params = 0

    for path in paths:
        vid = os.path.splitext(os.path.basename(path))[0]
        with open(path, encoding='utf-8') as f:
            body = f.read()
        fm = parse_frontmatter(body)

        duration = fm.get('duration_min', '')
        db.execute(
            'INSERT OR REPLACE INTO video VALUES (?,?,?,?,?,?)',
            (vid, fm.get('title', ''),
             fm.get('url', f'https://www.youtube.com/watch?v={vid}'),
             int(duration) if duration.isdigit() else None,
             fm.get('teaching_class', ''), fm.get('topics', '')))

        for kind, line in iter_sections(body):
            text = clean(line)
            if not text or NONE_RE.search(text):
                continue
            t = parse_ts(line)
            subject = tax.bucket_of(text) if kind in ('rule', 'number') else None
            cur = db.execute(
                'INSERT INTO claim (video_id, t_start, kind, subject, text, sig)'
                ' VALUES (?,?,?,?,?,?)',
                (vid, t, kind, subject, text, tax.signature(text)))
            cid = cur.lastrowid
            n_claims += 1

            for concept in tax.concepts_of(text):
                db.execute('INSERT OR IGNORE INTO claim_concept VALUES (?,?)',
                           (cid, concept))

            if kind == 'number':
                name, anchor = classify(text, tax.UNIT_RE)
                if name == 'unclassified':
                    continue
                nums = pick_numbers(parse_numbers(text), anchor)
                if not nums:
                    continue
                op = parse_op(text)
                # A range needs two figures; if only one survived, it is a
                # point value that merely happened to contain the word "to".
                if op == 'range' and len(nums) >= 2:
                    lo, hi = sorted([nums[0][0], nums[1][0]])
                    db.execute(
                        'INSERT INTO param (claim_id, video_id, t_start, name,'
                        ' op, value, value_max, raw) VALUES (?,?,?,?,?,?,?,?)',
                        (cid, vid, t, name, 'range', lo, hi, text))
                else:
                    db.execute(
                        'INSERT INTO param (claim_id, video_id, t_start, name,'
                        ' op, value, value_max, raw) VALUES (?,?,?,?,?,?,?,?)',
                        (cid, vid, t, name,
                         '=' if op == 'range' else op, nums[0][0], None, text))
                n_params += 1

    return len(paths), n_claims, n_params


CAPTION_RE = re.compile(r'^\[(\d{2}):(\d{2}):(\d{2})\]\s*(.*)$')


def load_transcripts(db, window=30, overlap=6):
    """Window the caption lines into overlapping chunks.

    Windowed by line count rather than words: auto-captions carry no
    punctuation, so there are no sentences to respect, and caption lines are
    already a near-uniform 6-9 words. The overlap keeps an idea that straddles
    a boundary findable from either side.
    """
    paths = sorted(glob.glob(os.path.join(TRANSCRIPTS, '*.txt')))
    n_chunks = 0

    for path in paths:
        vid = os.path.splitext(os.path.basename(path))[0]
        lines = []
        with open(path, encoding='utf-8', errors='replace') as f:
            for line in f:
                m = CAPTION_RE.match(line.strip())
                if not m:
                    continue
                secs = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
                body = m.group(4).strip()
                if body:
                    lines.append((secs, body))
        if not lines:
            continue

        step = max(1, window - overlap)
        for i in range(0, len(lines), step):
            group = lines[i:i + window]
            if not group:
                break
            text = ' '.join(t for _, t in group)
            db.execute(
                'INSERT INTO chunk (video_id, t_start, t_end, text)'
                ' VALUES (?,?,?,?)',
                (vid, group[0][0], group[-1][0], text))
            n_chunks += 1
            if i + window >= len(lines):
                break

    return len(paths), n_chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--no-transcripts', action='store_true',
                    help='skip the raw caption index (claims only, much faster)')
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    if os.path.exists(args.out):
        os.remove(args.out)
    for suffix in ('-wal', '-shm'):
        stale = args.out + suffix
        if os.path.exists(stale):
            os.remove(stale)

    tax = load_taxonomy()
    db = sqlite3.connect(args.out)
    build_schema(db)

    n_videos, n_claims, n_params = load_summaries(db, tax)
    print(f'{n_videos} summaries -> {n_claims} claims, {n_params} typed figures')

    if args.no_transcripts:
        n_tx = n_chunks = 0
        print('transcripts skipped')
    else:
        n_tx, n_chunks = load_transcripts(db)
        print(f'{n_tx} transcripts -> {n_chunks} caption chunks')

    db.execute("INSERT INTO claim_fts(claim_fts) VALUES ('rebuild')")
    db.execute("INSERT INTO chunk_fts(chunk_fts) VALUES ('rebuild')")

    # How much of the claim layer is actually citable. This is the number that
    # says whether "which video said this" is answerable in general.
    total, stamped = db.execute(
        'SELECT COUNT(*), COUNT(t_start) FROM claim').fetchone()
    db.commit()

    print(f'{stamped}/{total} claims carry a timestamp '
          f'({100 * stamped / total:.1f}% citable to the second)')
    print()
    print('Top concepts by distinct videos:')
    rows = db.execute("""
        SELECT cc.concept, COUNT(*) n, COUNT(DISTINCT c.video_id) v
        FROM claim_concept cc JOIN claim c ON c.id = cc.claim_id
        WHERE c.kind = 'rule'
        GROUP BY cc.concept ORDER BY v DESC LIMIT 10
    """).fetchall()
    for concept, n, v in rows:
        print(f'  {v:3d} videos  {n:4d} statements  {concept}')

    db.close()
    print(f'\nWrote {os.path.relpath(args.out, ROOT)}')


if __name__ == '__main__':
    main()
