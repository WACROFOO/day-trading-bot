#!/usr/bin/env python3
"""Verify every corpus citation in a document actually resolves.

Rule 1 of CLAUDE.md covers market data: no fetch, no claim. It says nothing
about the OTHER half of this repo's output — what he said, in which video, at
which second. Those are the claims a reader cannot check by glancing at a
chart, which makes them the ones worth checking mechanically.

This resolves the verifiable subset:

    js25lIZMUSY @00:22:49   -> does that transcript exist, and does that
                               timestamp appear in it?
    `scripts/tape.py`       -> does that path exist?
    reports/foo.md          -> does that path exist?

It CANNOT check that a quote is accurate to its audio, that a number was read
correctly, or that a claim is fairly characterised. It checks that the
citation POINTS SOMEWHERE REAL. A fabricated video id, an invented timestamp
and a path to a file that was never written all die here; a real citation
attached to a wrong conclusion does not.

    python3 scripts/factcheck.py FILE [FILE...]
    python3 scripts/factcheck.py --staged        # what git is about to commit

Exit 0 = every citation resolved, 1 = at least one did not.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB = os.path.join(ROOT, 'knowledge-base')
CORPUS_DIRS = ['transcripts', 'recaps', 'streams']

# A youtube id: 11 chars of [A-Za-z0-9_-]. Require a timestamp nearby or a
# .txt suffix, otherwise ordinary words and hashes match constantly.
CITE = re.compile(
    r'`?([A-Za-z0-9_-]{11})(?:\.txt)?`?\s*'
    r'(?:@|\[|\bat\s+)\s*(\d{1,2}:\d{2}(?::\d{2})?)')
# repo paths in backticks: scripts/x.py, research/.../y.md
PATH = re.compile(r'`([a-zA-Z0-9_./-]+\.(?:py|md|pine|csv|json|txt|sh))`')


def corpus_index():
    idx = {}
    for d in CORPUS_DIRS:
        p = os.path.join(KB, d)
        if not os.path.isdir(p):
            continue
        for fn in os.listdir(p):
            if fn.endswith('.txt'):
                idx.setdefault(fn[:-4], os.path.join(p, fn))
    return idx


def norm(ts):
    """00:22:49 and 22:49 both mean the same second in a [HH:MM:SS] file."""
    parts = ts.split(':')
    if len(parts) == 2:
        parts = ['00'] + parts
    return ':'.join(f'{int(x):02d}' for x in parts)


def check(path, idx):
    with open(path, encoding='utf-8', errors='replace') as fh:
        text = fh.read()
    bad, ok = [], 0

    # A file that TESTS this checker must contain broken citations — they are
    # its fixtures. Blocking the test suite for having fake video ids in it is
    # the checker misreading its own reflection. The exemption is a declaration
    # rather than a filename pattern, so it cannot be claimed by accident and
    # is visible in the file that claims it.
    # Assembled from halves so THIS file never contains the literal marker.
    # Spelled out whole, factcheck.py exempted itself the moment the feature
    # shipped — a checker that skips its own source is worse than no checker.
    if ('FACTCHECK' '-FIX' 'TURES') in text:
        return 'exempt', []

    for vid, ts in CITE.findall(text):
        if vid not in idx:
            bad.append((f'{vid} @{ts}', 'no such transcript in the corpus'))
            continue
        want = norm(ts)
        with open(idx[vid], encoding='utf-8', errors='replace') as fh:
            body = fh.read()
        if f'[{want}]' in body:
            ok += 1
            continue
        # auto-captions split lines by the second; allow ±2s before failing
        near = False
        h, m, s = (int(x) for x in want.split(':'))
        base = h * 3600 + m * 60 + s
        for delta in (-2, -1, 1, 2):
            t = base + delta
            cand = f'[{t // 3600:02d}:{(t % 3600) // 60:02d}:{t % 60:02d}]'
            if cand in body:
                near = True
                break
        if near:
            ok += 1
        else:
            bad.append((f'{vid} @{ts}', 'transcript exists, timestamp does not'))

    # Paths are written relative to whatever the author had in mind: the repo
    # root, the document's own directory, or a parent of it. Resolving only
    # against ROOT reported 5 false positives on the first run of this script,
    # all of them real files. Try the plausible bases before calling it dead.
    doc_dir = os.path.dirname(os.path.abspath(path))
    bases = [ROOT, doc_dir]
    d = doc_dir
    while d.startswith(ROOT) and d != ROOT:
        d = os.path.dirname(d)
        bases.append(d)
    for rel in set(PATH.findall(text)):
        if rel.startswith(('http', 'www')):
            continue
        if any(os.path.exists(os.path.join(b, rel)) for b in bases):
            ok += 1
        elif '/' in rel:
            # The distinction that matters for hallucination detection: a real
            # file written with a sloppy base is a typo; a name that exists
            # NOWHERE is the signature of an invented reference. Reporting
            # both identically buries the one that matters — on this script's
            # first run, 5 of 6 hits were real files and 1 was a forward
            # reference to a report that had never been written.
            base = os.path.basename(rel)
            found = None
            for dp, dn, fn in os.walk(ROOT):
                dn[:] = [x for x in dn if x != '.git']
                if base in fn:
                    found = os.path.relpath(os.path.join(dp, base), ROOT)
                    break
            if found:
                bad.append((rel, f'wrong path — the file exists at {found}'))
            else:
                bad.append((rel, 'NOT FOUND ANYWHERE IN THE REPO — verify this '
                                 'reference exists before committing'))

    return ok, bad


def staged():
    out = subprocess.run(['git', 'diff', '--cached', '--name-only',
                          '--diff-filter=ACM'],
                         capture_output=True, text=True, cwd=ROOT).stdout
    return [os.path.join(ROOT, f) for f in out.split()
            if f.endswith(('.md', '.pine', '.py'))]


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    files = staged() if args == ['--staged'] else args
    if not files:
        print('factcheck: nothing staged to check')
        return 0

    idx = corpus_index()
    total_bad = 0
    for f in files:
        if not os.path.exists(f):
            continue
        ok, bad = check(f, idx)
        rel = os.path.relpath(f, ROOT)
        if ok == 'exempt':
            print(f'– {rel}  (declares itself fixtures — broken citations '
                  f'are its test data)')
        elif bad:
            print(f'✗ {rel}')
            for what, why in bad:
                print(f'    {what}  —  {why}')
            total_bad += len(bad)
        elif ok:
            print(f'✓ {rel}  ({ok} citations resolved)')
    if total_bad:
        print(f'\n{total_bad} citation(s) did not resolve. A citation that '
              'points nowhere is the\nsignature of an invented one — fix or '
              'remove it before committing.')
        print('NOT CHECKED: quote accuracy, number accuracy, fair '
              'characterisation. This\nverifies that a reference EXISTS, '
              'never that it says what you claim.')
    return 1 if total_bad else 0


if __name__ == '__main__':
    sys.exit(main())
