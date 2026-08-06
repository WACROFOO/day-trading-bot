---
name: premarket-stars
description: Rank the pre-market gappers the way Ross Cameron runs his gap scanner — sorted by gap %, rejected on float and price before the chart, all decision metrics from finviz. Use for "what are the stars of the pre-market", "what's gapping", "what should I watch", or to vet one pre-market name.
---

# Pre-market stars

```bash
python scripts/premarket_stars.py           # survivors
python scripts/premarket_stars.py --all     # + rejects and why
```

Discovery (gap %, pre-market volume/high) = TradingView. Every deciding
metric = finviz. Nothing from bars.

## Gates, in order — a cascade, not a score

| gate | kill if |
|---|---|
| price | outside USD 2–20 (he prefers 2.50–9) |
| float | over 20M — checked *before* the chart |
| volume | under 250k pre-market |
| catalyst | none dated today |
| still rising | more than 25% off the pre-market high |

Separates STAR from WATCH: rotation (pm volume ÷ float), % of an average day,
short float ≥15%.

## Then, by hand, top two only

1. **Filings** — shelf/ATM vs market cap, reverse split (sub-5M shares out is
   the tell). finviz cannot see these.
2. **Chart shape** — `python scripts/premarket_dd.py SYM`. Above pre-market
   VWAP? Descending peaks?

## Reporting

State the ET time. Survivors in gap-% order with float, price, rotation,
catalyst. Name the rejects and their gate — that is most of the value. If
nothing survives, say so; sparse mornings are normal. Faded ≠ dead: report the
fade, not a verdict. Always say which RVOL denominator you used.

Selection only, not expectancy — see `reports/2026-08-regime-filter.md`. Paper.
Rationale, quotes and provenance: `REFERENCE.md`.
