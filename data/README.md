# data/

One file: `claims.db`, the searchable evidence database.

SQLite with FTS5 (BM25, porter-stemmed). 7,937 claims extracted from the
video summaries, each tagged (kind/topic) and carrying a video id plus a
timestamp, so every claim deep-links to the second it was said. A second
table holds raw caption chunks for "is it actually in there" checks.

- Build / rebuild: `python scripts/pipeline/12_build_claims_db.py`
- Query:           `python scripts/search.py "pullback volume"`
                   (`--layer chunks` for raw captions, `--concept`, `--param`,
                    `--coverage`, `--explain`)

Distinct from `knowledge-base/data/` (channel indexes, digests) and
`research/momentum-replication/data/` (market data and run outputs).
