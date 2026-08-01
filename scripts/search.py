#!/usr/bin/env python3
"""Search the corpus. Every hit comes back with a deep link into the video.

Two layers, and which one you want depends on the question:

    --layer claims   (default) what the corpus *teaches*. Clean, tagged
                     sentences. Fast to read, but only as complete as the
                     summariser was.
    --layer chunks   what the corpus *contains*. Raw caption windows. Noisy,
                     but this is the only layer that can settle "is this
                     actually in there, or did the summariser drop it".
    --layer both     run both.

Ranking is BM25 (SQLite FTS5, porter-stemmed). Dense retrieval is deliberately
not wired in here: `02_embed.py` needs numpy plus a sentence-transformer, which
are not installed in every environment, and BM25 alone answers most questions
against a corpus this size. If the vectors are present, fusing them in is the
natural next change — see `--explain` for what BM25 is and is not good at.

Usage:
    python scripts/search.py "pullback volume"
    python scripts/search.py "stop loss" --concept "stop at pullback low"
    python scripts/search.py "float" --kind number --limit 30
    python scripts/search.py "third pullback" --layer chunks
    python scripts/search.py --concepts                # list the vocabulary
    python scripts/search.py --param "float (shares)"  # value distribution
    python scripts/search.py --coverage                # per-video completeness
"""

import argparse
import os
import re
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.join(os.path.dirname(__file__), '..')
DB = os.path.join(ROOT, 'data', 'claims.db')

EXPLAIN = """\
BM25 matches words, not meaning. On auto-captions that has a specific failure
mode worth knowing about: this channel states the same rule forty different
ways, so a query for "lighter volume on the dip" will miss "small red candles"
even though they are the same instruction.

Two ways around it, both cheap:
  - query the concept tag instead of the words:  --concept "volume confirmation"
  - use OR:  python scripts/search.py "pullback OR dip OR flag"

FTS5 syntax that works here: "quoted phrase", AND, OR, NOT, prefix*.
"""


def link(video_id, t):
    base = f'https://www.youtube.com/watch?v={video_id}'
    return f'{base}&t={t}s' if t is not None else base


def hhmmss(t):
    if t is None:
        return '  --:--'
    return f'{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}'


def connect(path):
    if not os.path.exists(path):
        sys.exit(f'No database at {os.path.relpath(path, ROOT)}.\n'
                 f'Build it first:  python scripts/pipeline/12_build_claims_db.py')
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    return db


def fts_ok(db, query):
    """FTS5 raises on unbalanced quotes and bare operators. Fall back to a
    quoted literal rather than making the caller escape things by hand."""
    try:
        db.execute("SELECT * FROM claim_fts WHERE claim_fts MATCH ? LIMIT 1",
                   (query,)).fetchone()
        return query
    except sqlite3.OperationalError:
        return '"' + query.replace('"', '') + '"'


def search_claims(db, query, kind, concept, subject, limit):
    where, params = [], []
    if query:
        where.append('claim_fts MATCH ?')
        params.append(fts_ok(db, query))
    if kind:
        where.append('c.kind = ?')
        params.append(kind)
    if subject:
        where.append('c.subject = ?')
        params.append(subject)
    if concept:
        where.append('EXISTS (SELECT 1 FROM claim_concept cc'
                     ' WHERE cc.claim_id = c.id AND cc.concept = ?)')
        params.append(concept)

    order = 'bm25(claim_fts)' if query else 'c.video_id, c.t_start'
    sql = f"""
        SELECT c.id, c.video_id, c.t_start, c.kind, c.subject, c.text, v.title
        FROM claim c
        JOIN video v ON v.video_id = c.video_id
        {'JOIN claim_fts ON claim_fts.rowid = c.id' if query else ''}
        {'WHERE ' + ' AND '.join(where) if where else ''}
        ORDER BY {order} LIMIT ?
    """
    params.append(limit)
    return db.execute(sql, params).fetchall()


def search_chunks(db, query, limit, width):
    rows = db.execute("""
        SELECT c.video_id, c.t_start, c.text, v.title
        FROM chunk c
        JOIN chunk_fts ON chunk_fts.rowid = c.id
        JOIN video v ON v.video_id = c.video_id
        WHERE chunk_fts MATCH ?
        ORDER BY bm25(chunk_fts) LIMIT ?
    """, (fts_ok(db, query), limit)).fetchall()

    # Caption windows run ~200 words. Print a window around the first match
    # instead of the whole chunk: the timestamp is the deliverable, the text is
    # only there to show why the hit is relevant.
    terms = [t for t in re.findall(r'[a-z]+', query.lower())
             if t not in ('and', 'or', 'not')]
    out = []
    for r in rows:
        text = r['text']
        pos = 0
        for t in terms:
            m = re.search(re.escape(t), text, re.I)
            if m:
                pos = m.start()
                break
        lo = max(0, pos - width // 2)
        snippet = text[lo:lo + width].strip()
        out.append((r, ('...' if lo else '') + snippet + '...'))
    return out


def cmd_concepts(db):
    rows = db.execute("""
        SELECT cc.concept, COUNT(*) n, COUNT(DISTINCT c.video_id) v
        FROM claim_concept cc JOIN claim c ON c.id = cc.claim_id
        GROUP BY cc.concept ORDER BY v DESC
    """).fetchall()
    print(f'{"videos":>6} {"claims":>7}  concept')
    for r in rows:
        print(f'{r["v"]:>6} {r["n"]:>7}  {r["concept"]}')


def cmd_param(db, name):
    rows = db.execute("""
        SELECT p.op, p.value, p.value_max, p.video_id, p.t_start, p.raw
        FROM param p WHERE p.name = ? ORDER BY p.value
    """, (name,)).fetchall()
    if not rows:
        names = db.execute(
            'SELECT name, COUNT(*) n FROM param GROUP BY name ORDER BY n DESC'
        ).fetchall()
        print(f'No parameter called "{name}". Known parameters:')
        for r in names:
            print(f'  {r["n"]:>5}  {r["name"]}')
        return

    from collections import Counter
    dist = Counter()
    for r in rows:
        key = (r['op'], r['value'], r['value_max'])
        dist[key] += 1

    print(f'{name} — {len(rows)} figures across '
          f'{len({r["video_id"] for r in rows})} videos\n')
    print(f'{"count":>5}  value')
    for (op, val, vmax), n in dist.most_common(15):
        shown = f'{val:,.4g}' + (f' to {vmax:,.4g}' if vmax else '')
        print(f'{n:>5}  {op} {shown}')

    if len(dist) > 1:
        top = dist.most_common(2)
        if top[1][1] >= top[0][1] * 0.4:
            print('\n  ! Two values are close in frequency. This parameter is '
                  'disputed in the\n    source, not settled — sweep both before '
                  'trusting either.')

    print('\nExamples:')
    for r in rows[:6]:
        print(f'  [{hhmmss(r["t_start"])}] {r["raw"][:88]}')
        print(f'            {link(r["video_id"], r["t_start"])}')


def cmd_coverage(db, pillars, limit):
    """Which single video covers the most of the strategy.

    A video "covers" a pillar if any of its claims carry that concept. This is
    the query that answers "what should I watch first" without reading 257
    summaries.
    """
    rows = db.execute("""
        SELECT v.video_id, v.title, v.duration_min,
               COUNT(DISTINCT cc.concept) covered,
               COUNT(DISTINCT c.id) claims
        FROM video v
        JOIN claim c ON c.video_id = v.video_id
        JOIN claim_concept cc ON cc.claim_id = c.id
        WHERE cc.concept IN (%s)
        GROUP BY v.video_id
        ORDER BY covered DESC, claims DESC LIMIT ?
    """ % ','.join('?' * len(pillars)), (*pillars, limit)).fetchall()

    print(f'Coverage of {len(pillars)} core pillars\n')
    print(f'{"cov":>6} {"claims":>7} {"min":>5}  video')
    for r in rows:
        print(f'{r["covered"]:>3}/{len(pillars):<2} {r["claims"]:>7} '
              f'{r["duration_min"] or 0:>5}  {r["title"][:56]}')
        print(f'{"":>20}  {link(r["video_id"], None)}')


CORE_PILLARS = [
    'micro pullback', 'first candle to make a new high', 'volume confirmation',
    'support and resistance', 'stop at pullback low', 'position sizing by risk',
    'daily loss limit', 'profit-loss ratio 2:1', 'scaling out', 'VWAP', 'MACD',
    'float size', 'news catalyst', 'relative volume', 'first hour / market open',
]


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('query', nargs='?', default='')
    ap.add_argument('--db', default=DB)
    ap.add_argument('--layer', choices=['claims', 'chunks', 'both'],
                    default='claims')
    ap.add_argument('--kind', choices=['rule', 'number', 'setup', 'tool', 'caveat'])
    ap.add_argument('--subject')
    ap.add_argument('--concept')
    ap.add_argument('--limit', type=int, default=12)
    ap.add_argument('--width', type=int, default=180,
                    help='characters of caption context per chunk hit')
    ap.add_argument('--concepts', action='store_true', help='list the vocabulary')
    ap.add_argument('--param', help='show the value distribution for a parameter')
    ap.add_argument('--coverage', action='store_true',
                    help='rank videos by how much of the strategy they cover')
    ap.add_argument('--explain', action='store_true')
    args = ap.parse_args()

    if args.explain:
        print(EXPLAIN)
        return

    db = connect(args.db)

    if args.concepts:
        return cmd_concepts(db)
    if args.param:
        return cmd_param(db, args.param)
    if args.coverage:
        return cmd_coverage(db, CORE_PILLARS, args.limit)
    if not args.query and not (args.concept or args.kind or args.subject):
        ap.error('give a query, or one of --concept / --kind / --subject / '
                 '--concepts / --param / --coverage')

    if args.layer in ('claims', 'both'):
        rows = search_claims(db, args.query, args.kind, args.concept,
                             args.subject, args.limit)
        print(f'CLAIMS — {len(rows)} hit(s)\n')
        for r in rows:
            tag = f'{r["kind"]}/{r["subject"]}' if r['subject'] else r['kind']
            print(f'[{hhmmss(r["t_start"])}] ({tag}) {r["text"][:150]}')
            print(f'           {r["title"][:60]}')
            print(f'           {link(r["video_id"], r["t_start"])}\n')

    if args.layer in ('chunks', 'both'):
        if not args.query:
            return
        hits = search_chunks(db, args.query, args.limit, args.width)
        print(f'CAPTIONS — {len(hits)} hit(s)\n')
        for r, snippet in hits:
            print(f'[{hhmmss(r["t_start"])}] {snippet}')
            print(f'           {r["title"][:60]}')
            print(f'           {link(r["video_id"], r["t_start"])}\n')


if __name__ == '__main__':
    main()
