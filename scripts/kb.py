#!/usr/bin/env python3
"""Navigate the knowledge base by its indexes instead of grepping it blind.

Every directory here carries a README that is a real index. Grepping the whole
tree ignores that work: it returns 400 line-hits with no idea which register
they came from, and register is the finding (185 ABCD mentions in teaching
against 3 in recaps is the answer, not a detail).

So: descend. Read the index layer, pick the directory, then read files.

    python3 scripts/kb.py map              the whole index tree, one line each
    python3 scripts/kb.py where "float"    which INDEXES mention it -> where to go
    python3 scripts/kb.py open strategies  a directory's index + what is in it
    python3 scripts/kb.py doctor           indexes that have gone stale

`where` is the entry point for an unfamiliar question — it searches READMEs
only, so it answers "which folder" in one step instead of "which of 400 lines".
Once you know the folder, corpus.py searches its contents.

`doctor` is the part that keeps this honest. An index that omits half its
subdirectories silently sends the reader back to grepping, which is exactly
the failure this tool exists to remove.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {'.git', '__pycache__', 'node_modules', '.claude'}
# Directories whose contents are bulk corpus, not things to enumerate.
BULK = {'transcripts', 'streams', 'recaps', 'summaries', 'captures', 'bars_cache'}


def walk_dirs(base=ROOT):
    for dp, dn, fn in os.walk(base):
        dn[:] = sorted(d for d in dn if d not in SKIP and not d.startswith('.'))
        yield dp, dn, fn


def purpose(readme):
    """First non-heading, non-fence prose line — the index's own summary."""
    try:
        with open(readme, encoding='utf-8', errors='replace') as fh:
            infence = False
            for line in fh:
                s = line.strip()
                if s.startswith('```'):
                    infence = not infence
                    continue
                if infence or not s or s.startswith(('#', '|', '-', '>', '*')):
                    continue
                return re.sub(r'[`*\[\]]', '', s)[:96]
    except OSError:
        pass
    return ''


def cmd_map(args):
    rows = []
    for dp, dn, fn in walk_dirs():
        rel = os.path.relpath(dp, ROOT)
        if rel == '.':
            rel = ''
        r = os.path.join(dp, 'README.md')
        nfiles = len([f for f in fn if not f.startswith('.')])
        depth = rel.count(os.sep) + (1 if rel else 0)
        rows.append((depth, rel, os.path.exists(r), nfiles,
                     purpose(r) if os.path.exists(r) else ''))
    print(f'INDEX MAP · {ROOT}')
    print('· = has README   ✗ = none (you will have to grep it)\n')
    for depth, rel, has, n, why in rows:
        if not rel:
            continue
        name = '  ' * (depth - 1) + os.path.basename(rel)
        mark = '·' if has else '✗'
        print(f'{mark} {name:<42} {n:>4}f  {why}')
    miss = [r for _, r, h, n, _ in rows if not h and n and r]
    print(f'\n{len(rows) - 1} directories · {len(miss)} without an index')


def cmd_where(args):
    """Search the INDEX LAYER only. One step from question to directory."""
    if not args:
        print('kb.py where TERM'); return 1
    term = ' '.join(args).lower()
    hits = []
    for dp, dn, fn in walk_dirs():
        for f in fn:
            if not f.endswith('.md'):
                continue
            # index files only: READMEs and the *-INDEX / *-PLAN top docs
            if f != 'README.md' and not re.match(r'^[A-Z0-9-]+\.md$', f):
                continue
            p = os.path.join(dp, f)
            try:
                with open(p, encoding='utf-8', errors='replace') as fh:
                    lines = fh.read().splitlines()
            except OSError:
                continue
            match = [(i + 1, l.strip()) for i, l in enumerate(lines)
                     if term in l.lower()]
            if match:
                hits.append((len(match), os.path.relpath(p, ROOT), match))
    if not hits:
        print(f'"{term}" appears in NO index.')
        print('That means either it is not a concept this repo files under, or an')
        print('index is stale — run `kb.py doctor`, then fall back to corpus.py.')
        return 1
    hits.sort(reverse=True)
    print(f'"{term}" in the index layer — {len(hits)} index file(s), '
          'most mentions first\n')
    for n, rel, match in hits[:12]:
        print(f'  {rel}  ({n})')
        for ln, txt in match[:3]:
            print(f'      {ln}: {txt[:104]}')
        if len(match) > 3:
            print(f'      … {len(match) - 3} more')
        print(f'      → next: python3 scripts/kb.py open {os.path.dirname(rel) or "."}')
        print()


def cmd_open(args):
    if not args:
        print('kb.py open DIR'); return 1
    d = os.path.join(ROOT, args[0])
    if not os.path.isdir(d):
        print(f'no such directory: {args[0]}'); return 1
    r = os.path.join(d, 'README.md')
    if os.path.exists(r):
        with open(r, encoding='utf-8', errors='replace') as fh:
            print(fh.read())
    else:
        print(f'({args[0]} has no README — contents only)\n')
    base = os.path.basename(d.rstrip('/'))
    fn = sorted(f for f in os.listdir(d) if not f.startswith('.'))
    files = [f for f in fn if os.path.isfile(os.path.join(d, f))]
    subs = [f for f in fn if os.path.isdir(os.path.join(d, f))
            and f not in SKIP]
    print('─' * 70)
    if subs:
        print('subdirectories: ' + ', '.join(subs))
    if base in BULK and len(files) > 20:
        print(f'contents: {len(files)} files (bulk corpus — search with '
              f'corpus.py, do not list)')
    else:
        print(f'contents ({len(files)}): ' + ', '.join(files[:40])
              + (' …' if len(files) > 40 else ''))


def cmd_doctor(args):
    """An index is stale when it does not mention its own subdirectories."""
    stale, missing = [], []
    for dp, dn, fn in walk_dirs():
        rel = os.path.relpath(dp, ROOT)
        r = os.path.join(dp, 'README.md')
        nfiles = len([f for f in fn if not f.startswith('.')])
        if not os.path.exists(r):
            if nfiles:
                missing.append(rel)
            continue
        with open(r, encoding='utf-8', errors='replace') as fh:
            body = fh.read()
        unlisted = [d for d in dn if d not in body]
        if unlisted:
            stale.append((rel, unlisted, len(dn)))

    print('INDEX DOCTOR\n')
    print(f'{len(stale)} stale index(es) — subdirectories the README never names:')
    for rel, un, tot in sorted(stale):
        print(f'  {rel or "."}/README.md  omits {len(un)}/{tot}: {", ".join(un)}')
    if not stale:
        print('  none')
    print(f'\n{len(missing)} directory(ies) with files and no index:')
    for rel in sorted(missing):
        print(f'  {rel}')
    if not missing:
        print('  none')
    print('\nA reader who cannot see a directory in its parent index will grep '
          'the tree\ninstead — which is the habit this tool exists to remove.')
    return 1 if (stale or missing) else 0


def main():
    cmds = {'map': cmd_map, 'where': cmd_where, 'open': cmd_open,
            'doctor': cmd_doctor}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(__doc__)
        return 1
    return cmds[sys.argv[1]](sys.argv[2:]) or 0


if __name__ == '__main__':
    sys.exit(main())
