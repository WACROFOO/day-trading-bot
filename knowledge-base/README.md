# Knowledge Base

Reference material for building the day trading bot: traders studied, strategies documented, and — importantly — what has and has not been independently verified.

## Structure

```
THE ROSS MATERIAL
  strategies/       The CANONICAL rules. FILTERS.md is the bible, PARAMETERS.md
                    the numeric spec, SCANNERS.md the Day Trade Dash mapping
  transcripts/      Raw captions, 258-video teaching shortlist — what he SAYS
  recaps/           69 daily recaps, real upload dates — what he DID that day
  streams/          290 live streams — decisions BEFORE the outcome was known
  summaries/        Per-video rule/threshold summaries; the claims DB is built here
  warrior-blog/     2,090 written articles in 26 topic folders, each with an index
  warrior-support/  126 vendor help-desk articles. Platform mechanics ONLY —
                    never a rule; FILTERS.md wins any disagreement
  daytrade-dash/    His actual scanner platform: taxonomy, alert-export captures,
                    the calibration protocol
  tradingview/      Our Pine implementations — the strategy and the scanner
  data/             Channel indexes, digests, derived reference files
  sources/          Profiles of the traders/educators studied
  prompts/          Reusable prompt scaffolds

NOT THE ROSS MATERIAL — do not cross-reference, in either direction
  orderflow-scalping/   A DIFFERENT trader's futures model. Self-contained.
```

Top-level documents: `STUDY-PLAN.md`, `DAILY-ROUTINE-FR.md`,
`TRADINGVIEW-SETUP.md`, `WARRIOR-BLOG-INDEX.md`, `60-DAY-PLAN.md`.

**Navigate this by its indexes, not by grepping it.** `python3 scripts/kb.py
where "term"` searches the index layer only and tells you which folder in one
step; `kb.py open DIR` prints that folder's index. Grep is the fallback for
when the index has failed, and `kb.py doctor` finds indexes that have.

The three transcript registers differ in what they can prove: teaching videos
explain setups after the fact, recaps narrate a finished day, and only the
live streams record decisions before the outcome is known. Claims about *how
he trades* need the streams; claims about *what he traded on a given 2026
day* need the recaps.

## Start here

**`STUDY-PLAN.md`** — the full curriculum: everything Ross Cameron teaches,
ordered by dependency rather than by his publishing order, with the canonical
video for each module and a gate to pass before moving on. Built from the
concept-frequency map in `data/rules_digest.md`, so it covers what he actually
emphasises.

**`DAILY-ROUTINE-FR.md`** — the session hour by hour in France time (CEST is
+6h on ET): when to scan, when the plan closes, the two-hour tradeable window,
and the hard stop.

**`TRADINGVIEW-SETUP.md`** — the three screeners and the chart layout, with
the exact filter fields, plus the two things TradingView cannot do (relative
volume pre-market, and free float) and the workarounds.

## How to use this

Every strategy document is written as a set of mechanical rules so it can be translated into code and backtested. **Documenting a strategy here does not mean it works.** Each document carries a "Verification Status" section stating what evidence exists.

## Standing rules for this knowledge base

1. **Separate claim from evidence.** Record what a source claims, and separately record what has been independently verified. Never merge the two.
2. **Marketing numbers are not backtest results.** Performance figures published by someone selling a course are advertising until we reproduce them ourselves on out-of-sample data.
3. **Note the regulatory record.** If an educator has been subject to regulatory action over performance claims, that belongs in the document.
4. **Survivorship bias is the default.** Traders with public track records are visible because they succeeded. The ones who blew up small accounts using identical methods do not make YouTube videos.
5. **A strategy is not validated until we have run it walk-forward, out-of-sample, with realistic costs and slippage.**
