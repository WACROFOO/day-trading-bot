# Momentum strategy replication — handoff package

Self-contained. Everything needed to reproduce, verify, and continue the work is
in this folder.

---

## The task

A day-trading strategy is documented in `strategy/`. It was transcribed from 257
instructional videos by one trader who reports trading it profitably over ten
years.

This package contains a mechanical implementation of that strategy and a
forward-only simulation harness that replays it against real 1-minute market
data for 17 trading days (2026-07-09 → 2026-07-31).

**The implementation does not currently reproduce the behaviour described in the
source.** The measured discrepancies are in `OBSERVATIONS.md`. Thirteen defects
have already been found and corrected; they are recorded in `HISTORY.md` so the
same ground is not covered twice.

No conclusion has been reached about whether the strategy itself is profitable.
It has not yet been tested, because the implementation is not yet faithful
enough for its output to be evidence either way.

---

## Source of truth

The strategy is defined by these documents, in this order of authority:

| File | What it is |
|---|---|
| `../../knowledge-base/strategies/PARAMETERS.md` | Numeric specification, with `n=` evidence counts per rule — §13 lists the misreading traps |
| `../../knowledge-base/strategies/PLAYBOOK.md` | The same rules as an execution sequence |
| `../../knowledge-base/strategies/PLAYBOOK_V2.md` | Generated from the evidence database, with citations |
| `../../knowledge-base/strategies/STRATEGY_V2.md` | Generated parameter distributions, disputed values flagged |
| `../../knowledge-base/strategies/small-cap-momentum-bull-flag.md` | The pattern in isolation |

(`strategy/` here used to hold copies; they drifted from the originals and were
removed — see `strategy/README.md`.)

Behind those sits the primary evidence: 257 video transcripts and per-video
summaries under `../../knowledge-base/`, indexed into a queryable database.

```bash
python ../../scripts/pipeline/12_build_claims_db.py   # builds data/claims.db
python ../../scripts/search.py "profit target"        # 7,937 claims, deep-linked
python ../../scripts/search.py --concept "scaling out"
python ../../scripts/search.py --param "float (shares)"
python ../../scripts/search.py "third pullback" --layer chunks   # raw captions
```

Every claim carries a video id and a timestamp, so any rule can be checked
against the moment it was stated. 93.5% of claims are citable to the second.
When the documents and the corpus disagree, the corpus is the evidence and the
documents are an interpretation of it.

---

## What is in here

```
strategy/      the documented strategy (read-only reference)
engine/        sim.py         indicators, pullback tracker, entry evaluation
               engine20.py    one trading day, minute by minute
pipeline/      scan20.py      pre-market statistics, 2,486 symbols x 20 days
               fetch_daily.py consistently-adjusted daily bars
               run20b.py      watchlist construction + the run
diagnostics/   audit20.py     look-ahead audit
               loo.py         leave-one-out constraint analysis
               sweep.py       parameter sweeps
               gradient.py    pillar-count gradient
               probe*.py      measurements of setup geometry and timing
data/          cached inputs and current outputs
```

`RUN.md` has the commands. `OBSERVATIONS.md` has the measurements.
`HISTORY.md` has what has already been tried.

---

## What has been verified

**The simulation does not read future data.** This is enforced by construction —
indicators are incremental, and the engine is a strict left-to-right pass — and
checked by `diagnostics/audit20.py`, which truncates every session at successive
cut-offs and re-runs. Any trade entered before a cut-off must return identical.
It currently passes at 10:00, 10:30, 11:00, 11:30 and the full session.

**Selection does not use outcomes.** Watchlists are built from pre-market bars
plus the first five minutes of session volume. The candidate pool is filtered on
price and market capitalisation with bands deliberately wider than the
strategy's, so no symbol is included or excluded because of how its day
finished.

Any change to the engine should leave both of these true. The audit is the check
for the first; the second lives in `pipeline/run20b.py::build`.

---

## Known constraints of the data

- Yahoo 1-minute history reaches back about 30 days and is served in 7-day
  windows. **Each response is adjusted independently**, so bars from different
  windows are not directly comparable — this previously produced fabricated
  gaps of +10,000% around reverse splits. Daily bars are fetched in a single
  window for anything that compares across days.
- Pre-market volume is null on this endpoint for **every** symbol, including
  AAPL/TSLA/NVDA/SPY — an API limitation, not a property of thin names. So
  relative volume can only be confirmed from 09:30 onward, and the pre-market
  session the source trades cannot be modelled at all. See `DATA-SOURCES.md`.
- No quote data, therefore no true spread. A spread estimate is derived from
  the tightest quartile of recent 1-minute ranges.
- Two entry conditions in the source (`no_seller_wall`, `tape_green`) require
  Level 2 depth and time-and-sales, which are not available. They are not
  evaluated.
- Float is approximated by market capitalisation divided by price, from a
  current snapshot.

---

## Ground rules that have been applied

These are stated because breaking them silently is how the earlier results went
wrong, not because they are the only defensible choices.

1. **A number is not a finding.** The current run produces 3 trades. Any P&L
   computed from it is dominated by a single trade and is not evidence.
2. **Fitting to the sample is not a fix.** Relaxing a threshold until the trade
   count or the P&L improves produces a number, not a result. Earlier work
   reached +$245 by lowering a gate; it was discarded because the underlying
   gradient was non-monotonic, which is the falsification test the source
   specification itself prescribes (`PARAMETERS.md` §12 step 3).
3. **Changes should be traceable to the source.** Every one of the thirteen
   corrections in `HISTORY.md` cites the document or video timestamp it
   restores. Where the corpus genuinely specifies nothing, that is recorded as
   an open parameter rather than filled in with a guess.

---

## Related work in this repository

- `../../knowledge-base/` — 257 transcripts, per-video summaries, rules digest
- `../../scripts/pipeline/12_build_claims_db.py` — builds the queryable evidence database
- `../../scripts/search.py` — queries it; `--explain` describes the two layers
- `../../archive/simulations/` — the earlier single-day and 17-day write-ups this package supersedes

The archived reports are kept for the record but contain conclusions that
were later withdrawn; `HISTORY.md` here lists which ones and why.
