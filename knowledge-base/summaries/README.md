# summaries/

One markdown file per teaching video (259 files), generated from the
transcripts: rules stated, numeric thresholds, setups discussed, with
timestamps. These are the layer the claims database is built from
(`scripts/pipeline/12_build_claims_db.py`), so their coverage bounds what
`scripts/search.py --layer claims` can find; `--layer chunks` searches the
raw captions instead and is the arbiter when a summary might have dropped
something.

Filenames are YouTube video ids. The matching raw transcripts are in
`../transcripts/`.
