# Data sources — what was tested, and what the harness actually needs

## The requirement

| Need | Why |
|---|---|
| 1-minute bars | the entry trigger is a 1-minute candle (`PARAMETERS.md:144`) |
| **extended-hours bars with volume** | the source trades 07:00–09:30 (`PARAMETERS.md:71`); VWAP, RVOL and the pullback-volume filter all need volume |
| 6–12 months history | 17 days caps the sample at ~35 trades even at correct frequency |
| low-float small caps, incl. delisted | the universe is sub-20M float names that reverse-split and delist often |
| ~2,500 symbols/day scan | watchlist construction |

---

## Corrected finding: the pre-market blocker is Yahoo, not the symbols

`OBSERVATIONS.md` recorded 0 of 20,848 pre-market bars carrying volume, and the
README attributed it to these symbols being thin. **That attribution was wrong.**
Measured on Yahoo, last 5 days, `includePrePost=true`:

| Symbol | Pre-market bars | With volume |
|---|---:|---:|
| AAPL | 1,642 | **0** |
| TSLA | 1,650 | **0** |
| NVDA | 1,650 | **0** |
| SPY | 1,570 | **0** |
| EHGO | 1,138 | 0 |
| VEEE | 933 | 0 |

The most liquid instruments on the market return zero pre-market volume from
this endpoint. It is an API limitation, not a liquidity artifact — which means
a feed that carries consolidated extended-hours volume removes the blocker
entirely.

---

## Tested from this environment

| Source | Auth | Result |
|---|---|---|
| Yahoo chart v8 | none | 1-min, ~30 days, 7-day windows, **no extended-hours volume**; responses adjusted independently per window (see HISTORY defect 1) |
| Nasdaq `api.nasdaq.com/api/quote/.../chart` | none | reachable, but returns **daily** points only — 2 points for a 2-day range |
| Nasdaq screener | none | works; used for the candidate universe |
| Twelve Data | demo key | 1-min works (5,000 bars ≈ 13 days). `prepost=true` returns extended-hours bars with **volume 0**. Small caps rejected on the demo key |
| Alpha Vantage | demo key | demo key refuses real queries |
| Financial Modeling Prep | none | 401 |
| Polygon | none | 401 |
| Stooq | none | JavaScript proof-of-work challenge |

Nothing reachable without an account solves the extended-hours volume problem.

---

## Not testable here — needs an account

Assessed on published data models rather than measured, so **verify before
paying**. The single decisive test is at the bottom of this file.

| Source | Rough cost | Fit |
|---|---|---|
| **Polygon.io Stocks Starter** | ~$29/mo | Consolidated SIP, 5 years of 1-min aggregates, extended hours included, unlimited calls on paid tiers, retains delisted tickers. Best fit on paper |
| **Alpaca Algo Trader Plus** | ~$99/mo | Full SIP; free tier is **IEX-only** (~2–3% of consolidated volume), so free-tier RVOL would not be comparable to thresholds calibrated on consolidated volume. Doubles as the paper-trading broker |
| **Databento** | pay-as-you-go | Most precise; can buy just the window needed. Priced per GB, so a scoped calibration pull is cheap |
| **EODHD** | ~$20–80/mo | Cheap 1-min history; extended-hours coverage and delisted retention both need checking |
| **Polygon free tier** | free | 5 calls/min, 2 years. Far too slow for a 2,500-symbol scan — but ~100 requests is 20 minutes, which is **fast enough for the calibration step** described below |

---

## Two jobs, different requirements

**Calibration** — check the detector fires where he actually traded. Needs maybe
50–150 symbol-days, pulled from the tickers and dates named in his recap videos
(`claims.db` already holds those with timestamps). Low volume of requests,
so a free or trial tier can do it. This is the step that would settle whether
the pullback detector matches the pattern he trades, which 15 defect fixes
could not.

**The backtest** — needs the full universe over 6–12 months, which is where a
paid tier is unavoidable.

Doing calibration first is what keeps a subscription from buying a bigger sample
of the wrong thing.

---

## Decisive test before committing money

For any candidate feed, one query answers it:

```
fetch 1-minute bars for AAPL on any recent date, extended hours included
→ do the 04:00–09:30 bars carry non-zero volume?
```

Yahoo and Twelve Data both fail this. If a feed passes it, also check:

1. **Delisted retention** — request a ticker that has since delisted or
   reverse-split. If it 404s, the backtest inherits survivorship bias, and this
   universe delists constantly.
2. **Split handling across a date range** — request a window spanning a known
   reverse split and confirm the whole response shares one adjustment basis.
   Getting this wrong is what produced the fabricated +10,555% gaps in
   HISTORY defect 1.
3. **Small-cap coverage** — confirm sub-$300M names resolve at all; several
   providers cover only liquid universes.
