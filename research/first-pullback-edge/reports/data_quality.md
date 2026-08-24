# Data quality — measured before any strategy number is shown

```
Reproduce: python3 research/first-pullback-edge/src/data_quality.py
           -> results/data_quality.json
Measured 2026-08-24 from this container. Every row below is a request that
was actually made; the failures are recorded as failures.
```

No conclusion in `final_report.md` is stronger than this page. Read it first.

---

## 1. Providers reachable from here

| Provider | Auth | Reachable | Result |
|---|---|---|---|
| Yahoo chart v8 | none | **yes** | the only working feed |
| Polygon.io | key | no | `401 API Key was not provided` |
| Alpaca market data | key | no | `401 Authorization Required` |
| Tiingo | token | no | `403 Please supply a token` |
| EODHD | key | no | `401 Unauthenticated` |
| Finnhub | key | no | `401 Please use an API key` |
| Nasdaq screener | none | yes | used for the symbol pool |

No market-data credentials are present in this environment
(`POLYGON_API_KEY`, `ALPACA_API_KEY_ID` and the rest are all unset). The
pipeline has adapters for Polygon and Alpaca and activates them the moment a
key appears; nothing else had to change.

---

## 2. The three hard requirements, and how the available feed scores

The study needs 1-minute bars, multiple years of them, and delisted names.
Yahoo fails all three.

### 2a. 1-minute history reaches 25 days, not years — MEASURED

| lookback | session probed | bars returned |
|---:|---|---:|
| 2 d | 2026-08-21 | 957 |
| 10 d | 2026-08-14 | 959 |
| 20 d | 2026-08-04 | 960 |
| **25 d** | **2026-07-30** | **960** |
| 30 d | 2026-07-24 | **0** |
| 35 d | 2026-07-20 | **0** |
| 45 d | 2026-07-10 | **0** |
| 60 d | 2026-06-25 | **0** |
| 120 d | 2026-04-24 | **0** |
| 365 d | 2025-08-22 | **0** |

Beyond ~30 calendar days the endpoint returns `HTTP 422 Unprocessable
Entity`. Coarser intervals reach further (5-minute ≈ 60 days, 1-hour ≈ 730
days) and are useless here: the entry trigger is the high of a 1-minute
candle (`PARAMETERS.md:144`), and a 5-minute bar cannot express it.

**Consequence: the A–F ablation can only be RUN on 19 trading sessions.**
That is the single most important fact in this study.

### 2b. Pre-market volume is zero for every symbol — MEASURED

| symbol | pre-market bars | bars with volume |
|---|---:|---:|
| AAPL | 327 | **0** |
| SPY | 314 | **0** |
| TSLA | 330 | **0** |
| NVDA | 330 | **0** |

The most liquid instruments on the market return zero extended-hours volume
from this endpoint. It is an API limitation, not thin tape — the same finding
the sibling package recorded in `research/momentum-replication/DATA-SOURCES.md`
and re-measured here.

Consequences, all of them structural:

- VWAP anchored "session incl. pre-market" (`ross-fp-v4.pine:518`) cannot be
  computed as specified. This study anchors VWAP at 09:30 and says so.
- Pre-market RVOL cannot be computed at all.
- The pullback-volume ratio (variant D's whole rule) is meaningless before
  09:30, so **the pre-market session cannot be tested**.
- The 07:00–09:30 window the source trades — the window his own July recaps
  name 78 times against 36 for 09:30
  (`research/momentum-replication/reports/2026-07-challenge.md`) — is out of
  reach. Everything below is an RTH-only measurement of a strategy whose
  author says the pre-market often contains the whole move.

### 2c. Delisted symbols 404 — MEASURED

| symbol | daily bars returned | retained? |
|---|---:|---|
| MULN | 0 | **no** |
| ATVI | 0 | **no** |
| TWTR | 0 | **no** |
| SIVBQ | 0 | **no** |
| BBBYQ | 0 | **no** |
| WEWKQ | 0 | **no** |
| FRCB | 1,029 | yes |
| AMTD | 1,030 | yes |
| SNDL | 1,030 | yes |

**Six of nine delisted or post-bankruptcy tickers are gone.** The symbol pool
is a Nasdaq screener snapshot of what is listed *today* (6,742 names), so a
company that gapped 40% in 2023 and was delisted in 2024 is invisible to the
universe builder — and this is precisely the population that delists.

> **CRITICAL LIMITATION.** The multi-year universe in
> `data/candidate_days.parquet` is survivorship-biased. The direction of the
> bias is not obviously favourable — survivors of a small-cap momentum
> universe are not straightforwardly the winners — but it is real, it is
> unquantified, and it cannot be repaired from this feed.

---

## 3. Corporate actions

| Item | Handling |
|---|---|
| Adjustment basis | Yahoo adjusts **each response independently**. Two requests spanning a split are not comparable. |
| Mitigation | `daily_bundle()` fetches bars *and* the split calendar in ONE request per symbol, so every bar compared shares one basis. Minute bars are fetched one calendar day per request, so no minute comparison ever straddles two bases. |
| Splits detected | 46 candidate ticker-days fall on a recorded split date. |
| Reverse-split artefacts | 139 candidate ticker-days show an open/prev-close ratio within 4% of a clean integer (2×, 3×, 5×, 10× …). Per `CLAUDE.md` rule 6 these are **flagged, not vetoed** — a clean integer is the tell, a 2.54× move is a move. All 139 are excluded from the intraday run and kept in the universe table with the ratio recorded. |
| Dividends | Irrelevant at this price/holding period; not modelled. |
| Ticker changes | Not handled. Yahoo resolves current tickers only, so a name that changed symbol appears as two unrelated series or as nothing. |

---

## 4. Missing bars, halts and suspicious records

Yahoo omits empty minutes rather than emitting a zero-volume bar, so a gap in
the series is either "nothing traded" or "the stock was halted" and **the feed
cannot tell you which.**

- Every missing-minute gap inside RTH sets `halt_flag` on any position open
  across it, and the flag is carried into the trade ledger.
- No LULD halt/resume feed is reachable here, so a stop that "filled" across a
  gap may in reality have been a halt that reopened far below. Those trades are
  reported separately, never silently counted.
- The engine's gap-through-stop path fills at the **bar open**, not at the
  stop, which is the conservative reading.

Sanity checks run on every bar loaded (`probe_suspicious`): non-positive
prices, `high < low`, close or open outside `[low, high]`, and zero-volume
bars with a non-zero range. Counts are in `results/data_quality.json`.

---

## 5. What is simply absent

| Field the brief asks for | Status |
|---|---|
| Quote / NBBO data | **absent.** Spread is a proxy: the 25th percentile of recent 1-minute ranges, floored at one tick. Every use is labelled an estimate. |
| Trade / tick data | **absent.** Intrabar sequence is therefore unknowable, which is why ambiguity is a *policy* with three reported readings rather than a fact. |
| Halt / resume timestamps | **absent.** See above. |
| Point-in-time float | **absent.** A current float snapshot is not the float on the trade date, especially in a universe that dilutes constantly. The float column exists in the ledger and is `null` with `float_provenance="unavailable"` on every row. **The float cut of brief §17 cannot be produced.** |
| Timestamped historical news | **absent.** **The catalyst analysis of brief §18 cannot be produced.** No row is labelled "no catalyst": absence of a news feed is not absence of news. |
| Short interest, borrow | absent; not required by A–F. |

---

## 6. Timezone and DST

All bar timestamps are epoch seconds, converted to `America/New_York` at read
time via `zoneinfo`, so DST transitions are handled by the tz database rather
than by a fixed offset. Session-minute indices are computed from 04:00 ET.
Sessions are keyed by ET calendar date. (The blotter convention noted in
`CLAUDE.md` — France local = ET + 6h in summer — is not used anywhere in this
pipeline; nothing here reads a blotter.)

---

## 7. What would fix this

One subscription removes items 2a, 2b and 2c together.

### Polygon.io Stocks Starter — the recommended fix

```bash
export POLYGON_API_KEY=...          # then re-run, nothing else changes
python3 research/first-pullback-edge/run.py universe \
    --start 2021-01-01 --end 2026-08-21 --provider polygon
python3 research/first-pullback-edge/run.py ablation --days 1200 --provider polygon
```

`src/data.py::PolygonProvider` is written and wired: `/v2/aggs` with
`adjusted=false` for raw intraday bars, `/v3/reference/splits` for the split
calendar applied separately, `/v3/reference/tickers?date=` for the
point-in-time symbol list **including delisted names** (this is the
survivorship fix), and `/v3/quotes` for a real spread.

Verify these three before paying — they are the whole reason to:

1. `AAPL` 1-minute for a recent date with extended hours → do the 04:00–09:30
   bars carry **non-zero volume**?
2. A ticker that has since delisted (`MULN`, `BBBYQ`) → does it return bars
   rather than a 404?
3. A window spanning a known reverse split → does the whole response share one
   adjustment basis?

### Alternatives

| Source | Cost | Caveat |
|---|---|---|
| Alpaca Algo Trader Plus | ~$99/mo | free tier is **IEX-only** (~2–3% of consolidated volume) — RVOL computed on it is not comparable to any consolidated threshold. Adapter written. |
| Databento | pay-as-you-go | most precise, priced per GB; a scoped pull for the calibration window is cheap. Adapter not written. |
| EODHD | ~$20–80/mo | cheap 1-minute history; extended-hours coverage and delisted retention both need the three tests above. |

Halts still need a separate source in every case (UTP/CTA halt files or a
vendor halt feed); no provider above supplies them in the bar API.
