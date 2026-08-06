#!/usr/bin/env python3
"""One search across every register of the corpus, with citations.

The corpus is four independent registers plus a claims database, and which one
answers a question matters more than the answer's wording. Repeatedly in this
project a rule looked settled in one register and was contradicted in another:
the halt rules, the ABCD entry point, the 10-second timing, and the fact that
the July challenge is traded pre-market rather than at the open all came out of
checking more than one.

    transcripts/    257 teaching videos   what he SAYS the rule is (hindsight)
    recaps/          69 daily recaps      what he DID that day (labelled)
    streams/        289 live streams      decisions BEFORE the outcome is known
    warrior-blog/  2063 written articles  edited, dated prose
    data/claims.db 7937 tagged claims     deep-linked to a video timestamp

So the default output is a per-register breakdown, not a flat list. A term that
appears 200 times in teaching and twice in recaps is a different fact from one
that appears evenly.

Usage:
    python scripts/corpus.py "micro pullback"          # counts per register
    python scripts/corpus.py "halt" --files            # which files, ranked
    python scripts/corpus.py "abcd" --show streams -n 6   # matching lines
    python scripts/corpus.py "profit target" --claims  # claims.db + timestamps
    python scripts/corpus.py --index                   # what exists, where
"""
import argparse
import os
import re
import sqlite3
import subprocess
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB = os.path.join(ROOT, 'knowledge-base')
DB = os.path.join(ROOT, 'data', 'claims.db')

REGISTERS = [
    ('teaching', os.path.join(KB, 'transcripts'),
     'what he SAYS the rule is — hindsight, edited for YouTube'),
    ('recaps', os.path.join(KB, 'recaps'),
     'what he DID that day — labelled outcomes, the calibration set'),
    ('streams', os.path.join(KB, 'streams'),
     'decisions made BEFORE the outcome was known — the honest register'),
    ('blog', os.path.join(KB, 'warrior-blog'),
     'edited written prose, dated; 419 of these are written trade recaps'),
    ('strategy-docs', os.path.join(KB, 'strategies'),
     'our canonical spec — PARAMETERS.md is the numeric source of truth'),
    ('reports', os.path.join(ROOT, 'research', 'momentum-replication', 'reports'),
     'what this project has already measured — check before re-deriving'),
]


def nfiles(path):
    """Recursive: warrior-blog nests one directory per category, so a
    top-level listdir reported 18 'files' for 2,063 articles."""
    return sum(1 for _, _, fs in os.walk(path) for f in fs
               if not f.startswith('.')) if os.path.isdir(path) else 0


def rg(pattern, path, extra=None):
    if not os.path.exists(path):        # files as well as dirs - --show greps one file
        return ''
    cmd = ['rg', '-i', '--no-heading', '-N']
    cmd += extra or []
    cmd += ['-e', pattern, path]
    p = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
    return p.stdout


def counts(pattern):
    out = []
    for name, path, why in REGISTERS:
        raw = rg(pattern, path, ['-c'])
        files = [l for l in raw.splitlines() if ':' in l]
        hits = sum(int(l.rsplit(':', 1)[1]) for l in files if l.rsplit(':', 1)[1].isdigit())
        total = nfiles(path)
        out.append((name, len(files), total, hits, why))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('query', nargs='?')
    ap.add_argument('--files', action='store_true', help='rank the matching files')
    ap.add_argument('--show', metavar='REGISTER', help='print matching lines from one register')
    ap.add_argument('-n', type=int, default=4, help='files to show with --show')
    ap.add_argument('-C', type=int, default=1, help='context lines with --show')
    ap.add_argument('--claims', action='store_true', help='search claims.db (FTS5, timestamps)')
    ap.add_argument('--index', action='store_true', help='print the corpus map')
    a = ap.parse_args()

    if a.index or not a.query:
        print('CORPUS MAP\n')
        for name, path, why in REGISTERS:
            n = nfiles(path)
            rel = os.path.relpath(path, ROOT)
            print(f'  {name:<14}{n:>5} files  {rel}')
            print(f'  {"":<14}            {why}')
        print(f'\n  claims.db      7937 claims / 1749 params / 10218 chunks, '
              f'each deep-linked to a video timestamp')
        print('\n  blog categories:')
        bp = os.path.join(KB, 'warrior-blog')
        if os.path.isdir(bp):
            for c in sorted(os.listdir(bp)):
                d = os.path.join(bp, c)
                if os.path.isdir(d) and not c.startswith('.'):
                    k = len([f for f in os.listdir(d) if f.endswith('.md') and f != 'README.md'])
                    print(f'    {k:>5}  {c}')
        print('\n  Read the README.md in any directory first — every one is an index.')
        return 0

    q = a.query
    if a.claims:
        if not os.path.exists(DB):
            print('claims.db not found')
            return 1
        c = sqlite3.connect(DB)
        rows = c.execute(
            "SELECT c.video_id, c.t_start, c.kind, c.subject, c.text, v.title "
            "FROM claim_fts f JOIN claim c ON c.id = f.rowid "
            "LEFT JOIN video v ON v.video_id = c.video_id "
            "WHERE claim_fts MATCH ? ORDER BY rank LIMIT 25", (q,)).fetchall()
        print(f'{len(rows)} claims matching {q!r}\n')
        for vid, t, kind, subj, text, title in rows:
            ts = int(t or 0)
            print(f'[{kind}] {subj}')
            print(f'  {text[:150]}')
            print(f'  https://youtu.be/{vid}?t={ts}  ({(title or "")[:52]})\n')
        return 0

    if a.show:
        reg = dict((n, p) for n, p, _ in REGISTERS)
        if a.show not in reg:
            print(f'unknown register. one of: {", ".join(reg)}')
            return 1
        raw = rg(q, reg[a.show], ['-c'])
        ranked = sorted(((int(l.rsplit(":", 1)[1]), l.rsplit(":", 1)[0])
                         for l in raw.splitlines()
                         if ':' in l and l.rsplit(':', 1)[1].isdigit()), reverse=True)
        for n, f in ranked[:a.n]:
            print(f'\n=== {os.path.basename(f)}  ({n} hits) ===')
            print(rg(q, f, ['-C', str(a.C), '-m', '6']).rstrip()[:2000])
        return 0

    rows = counts(q)
    print(f'"{q}" across the corpus\n')
    print(f'{"register":<15}{"files":>12}{"hits":>8}   what this register answers')
    for name, nf, total, hits, why in rows:
        frac = f'{nf}/{total}'
        print(f'{name:<15}{frac:>12}{hits:>8}   {why[:44]}')
    tot = sum(r[3] for r in rows)
    print(f'\n{tot} total hits.')
    if rows[0][3] and not rows[1][3]:
        print('NOTE: present in teaching but absent from the recaps — taught more '
              'than traded. Check streams before treating it as a rule.')
    if a.files:
        for name, path, _ in REGISTERS:
            raw = rg(q, path, ['-c'])
            ranked = sorted(((int(l.rsplit(":", 1)[1]), os.path.basename(l.rsplit(':', 1)[0]))
                             for l in raw.splitlines()
                             if ':' in l and l.rsplit(':', 1)[1].isdigit()), reverse=True)
            if ranked:
                print(f'\n{name}:')
                for n, f in ranked[:8]:
                    print(f'  {n:>5}  {f}')
    print('\nnext: --files to rank sources, --show <register> to read lines, '
          '--claims for timestamps')
    return 0


if __name__ == '__main__':
    sys.exit(main())
