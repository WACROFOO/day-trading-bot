# Knowledge Base

Reference material for building the day trading bot: traders studied, strategies documented, and — importantly — what has and has not been independently verified.

## Structure

```
sources/      Profiles of traders/educators whose methods we study
strategies/   The CANONICAL strategy documents (the only copy — see its README)
transcripts/  Raw captions for the 257-video teaching shortlist
summaries/    Per-video rule/threshold summaries (the claims DB is built from these)
recaps/       Daily recap transcripts, June–July 2026, real upload dates (the calibration set)
streams/      Live-stream transcripts, 2021–2023 (~1.3M words — decisions before the outcome)
data/         Channel indexes, digests, and derived reference files
```

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
