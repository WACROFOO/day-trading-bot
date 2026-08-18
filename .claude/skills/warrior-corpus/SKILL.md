---
name: warrior-corpus
description: Search and cite the Ross Cameron / Warrior Trading corpus in this repo — 258 teaching transcripts, 69 daily recaps, 290 live streams, 2,063 written blog articles, 126 help-desk articles, 7,937 tagged claims, and 23 measurement reports. Use whenever a question is about what he says, teaches, or did; about a strategy rule, parameter, pattern, or indicator; about how the Warrior platform, scanners or chat room behave; or before re-deriving anything this project has already measured.
---

# Warrior Trading corpus

Everything is local. Do not WebSearch for what he says — search the corpus.

## Start here, always — index first, contents second

```bash
python3 scripts/kb.py where "micro pullback"     # 1. WHICH FOLDER (indexes only)
python3 scripts/kb.py open knowledge-base/strategies   # 2. that folder's index
python3 scripts/corpus.py --index                # 3. what exists per register
python3 scripts/corpus.py "micro pullback"       # 4. counts per register
```

**Steps 1–2 are not optional politeness — they are what makes this fast.**
`kb.py where` searches only README/INDEX files, so it answers "which folder"
in one command instead of returning 400 undifferentiated line-hits. Every
directory here has a real index; going straight to full-text search discards
that work and is how a five-step answer becomes a fifteen-step one.

`--index` then costs nothing and prevents the most common error: answering
from one register when another contradicts it.

**Grep of `knowledge-base/` is blocked by a hook**, not merely discouraged —
searching code is unaffected. If steps 1–3 truly cannot find it, append
`# INDEX-FAILED: <what you sought, which index should have had it>` to the
command; that runs, logs to `research/index-failures.log`, and obliges
`python3 scripts/kb.py doctor` plus the index fix in the same commit.

Reaching for grep is a finding about the index, not about the corpus.

## The registers are the method, not filing

| register | n | answers |
|---|---|---|
| `teaching` | 258 | what he **says** the rule is — hindsight, edited for YouTube |
| `recaps` | 69 | what he **did** that day — labelled outcomes, the calibration set |
| `streams` | 290 | decisions made **before** the outcome was known |
| `blog` | 2,063 | edited written prose, dated; **419 are written trade recaps** |
| `support` | 126 | help desk — what the **platform** does, never what the method is |
| `strategy-docs` | 9 | our spec; `PARAMETERS.md` is the numeric source of truth |
| `reports` | 23 | **what this project already measured** |

**A count that is lopsided across registers is itself the finding.** Every
significant correction in this project came from that split:

- ABCD: 185 mentions in teaching, **3 in recaps** → taught far more than traded
- Halts: the "don't hold size in a halt" rule had **one** supporting file; the
  halt-cycle framework and the T1-avoidance rule were missed entirely by
  reading one video
- Timing: `07:00` appears **78** times in the July recaps against 36 for
  `09:30`, and `pre-market` **161** times against 9 for `the close` — the
  challenge is traded pre-market, not at the open

## Commands

```bash
python scripts/corpus.py "halt" --files               # rank the source files
python scripts/corpus.py "abcd" --show streams -n 6   # read matching lines
python scripts/corpus.py "profit target" --claims     # claims.db + youtu.be?t= links
python scripts/mine_streams.py timing                 # live-stream evidence by topic
```

For anything numeric, `--claims` is the right entry point: 7,937 claims and
1,749 extracted parameters, each deep-linked to a video timestamp. Cite that
link, not a paraphrase.

## Rules for answering

1. **Check `reports/` before measuring anything.** 23 reports already cover the
   pillar score, exits, the regime filter, the March-2024 out-of-sample test,
   the VWAP condition and the known-edge literature. Re-deriving a settled
   result wastes the turn.
2. **Cite the register.** "185 mentions across 37 teaching files" is an answer;
   "he says X" is not.
3. **Quote with provenance** — video id + timestamp, or the blog article's
   source URL (kept in a header comment in every fetched file).
4. **When teaching and streams disagree, the streams win.** They are decisions
   made before the outcome was known.
5. **State the register split when it is lopsided**, even when unasked.

## Directory indexes — the navigation layer

Every directory has a `README.md` that is a real index. **Read it before
listing files.** `knowledge-base/warrior-blog/README.md` maps 26 category
folders; each category README lists its articles by length with source links.

`python3 scripts/kb.py map` prints the whole tree with each index's one-line
purpose — the cheapest possible orientation when the question is unfamiliar.

The index layer is maintained, not decorative: `kb.py doctor` fails when a
README omits its own subdirectories, because a directory invisible in its
parent index is a directory the next reader will grep for.
`knowledge-base/warrior-support/README.md` maps 18 folders under the support
portal's own 5 categories, so a folder name there is the vendor's own filing,
not a guess of ours.

## Corpus-specific gotchas

- Transcripts are auto-captioned: tickers appear as `CUPR`, `cupr`, or spelled
  out, and lines repeat. Search case-insensitively and expect duplicates.
- `knowledge-base/warrior-blog/other/` holds 898 under-classified articles —
  search it explicitly rather than trusting the category name.
- `NOT-FETCHED.md` lists 99 URLs with no extractable text (36 are video-only
  stubs whose transcript is already in `recaps/` or `streams/`).
- Blog files carry `<!-- source: URL -->` and `<!-- lastmod: DATE -->` headers.
- `support` is a **vendor manual, not a method register**: it answers "why did
  my pre-market order reject" or "what does that scanner column mean", never
  "is this a good entry". Do not cite it for a rule — `FILTERS.md` wins, and a
  disagreement between the two is a support-article staleness bug, not a rule
  change. Its files carry a `<!-- modified: DATE -->` header; several are years
  old and describe screens that have since been redesigned.

## Refetching

```bash
python scripts/fetch_warrior_fast.py        # blog + transcripts, resumable
python scripts/fetch_warrior_support.py     # help desk, cached, cheap re-runs
```

Uses one curl per batch with `--compressed --http2 --parallel`. Do **not**
raise concurrency or rotate user-agents: the site 504s under load, its
robots.txt already allows ClaudeBot, and gzip alone cuts transfer 14×
(1,391,904 → 97,873 bytes per page).
