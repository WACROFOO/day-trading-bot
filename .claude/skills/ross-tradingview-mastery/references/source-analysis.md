# Warrior scanner source analysis and clean-room TradingView mapping

> **Superseded values, 2026-08-18.** Five formulas below were written before
> the Warrior corpus was searched for scanner definitions. The corpus states
> four of them outright. Corrections are marked `SUPERSEDED →` in place; the
> original wording is kept because the reasoning is the asset. Full evidence,
> with register and timestamp for every threshold, is in
> `knowledge-base/strategies/SCANNERS.md`.

## Result

The scanner formulas are not embedded in the public page HTML or hard-coded in the downloadable JavaScript bundle. The delivered client is a user interface and transport layer. Scanner widgets, data-point definitions, strategies and filter values are obtained from protected server APIs.

This means the exact proprietary thresholds cannot be recovered from ordinary **View Source**. Replication must use public descriptions, visible output behavior and independently chosen thresholds.

## Client resources inspected

The authenticated dashboard loads these scanner-relevant resources:

- `/static/js/main.90ba69d2.js`
- `/charting_library/charting_library.standalone.js`
- scanner data and configuration APIs described below

The main application bundle is minified and approximately 5 MB. No readable hard-coded definitions for Ross's named strategies were found.

## Scanner API surface exposed by the client

The bundle references these routes:

- `GET /v1/scanner/config`
- `GET /v1/scanner/const`
- `GET /v1/scanner/widgets`
- `GET /v1/scanner/strategies?widget_id=...`
- `POST /v1/scanner/widget`
- `POST /v1/scanner/strategy`
- `PUT /v1/scanner/strategy?id=...`
- `DELETE /v1/scanner/strategy?id=...`
- `GET /v1/scanner/config-changes`
- `/v1/scanner/data-sync/export`
- `/v1/scanner/data-sync/import`
- `/alert-status`

The scanner configuration endpoints require bearer authorization. Authentication credentials were not extracted or copied during this analysis.

## Configuration model revealed by the client

The client constructs a strategy with this conceptual structure:

```text
strategy
  name
  filters[]
    point_id
    conditions
    match_any_condition
  toplist_options, for list scanners
    sorted_point_id
    ascending_or_descending
    greatest_count
    least_count
  alert_options, for alert scanners
    event_ids
    color
    disabled
```

The `point_id` values and condition thresholds come from `/v1/scanner/const` and `/v1/scanner/config`; they are not shipped as readable constants in the static bundle. The bundle's offline fallback objects contain empty widget, field and data-point arrays.

## Live HOD snapshot inspected

A read-only snapshot of 40 visible HOD alerts produced these observed ranges:

| Visible strategy | Alerts | Price range | Float range |
|---|---:|---:|---:|
| Former Momo Stock | 9 | $2.07–$8.65 | 0.319M–1.60M |
| Squeeze: up 5% in 5 minutes | 3 | $1.73–$1.99 | 0.842M–33.39M |
| Squeeze: up 10% in 10 minutes | 13 | $3.50–$8.65 | 0.319M–5.38M |
| Low Float Volatility Hunter | 3 | $1.07–$8.00 | 0.319M–4.45M |
| Low Float – High Relative Volume | 10 | $3.60–$4.62 | 1.60M–5.38M |
| Medium Float – High Relative Volume – under $20 | 2 | $1.78–$1.80 | 33.39M |

These are observations, not threshold proofs. Several displayed relative-volume values were implausibly large, so the Warrior RVOL figures should not be copied directly into TradingView. Vendor formulas, premarket annualization and bad reference-volume data can create radically different numbers.

## What can be replicated independently

The visible columns establish the useful data model:

- last price;
- percentage change from prior close;
- gap percentage;
- total volume;
- daily relative volume;
- five-minute relative volume;
- float;
- short interest;
- position in range;
- new-high event;
- rapid percentage move over a time window;
- 52-week breakout;
- prior-runner status;
- news/catalyst status.

TradingView can calculate most price and volume fields. It cannot reliably reproduce Warrior's true-float feed, news-flame status or proprietary former-runner database.

## Clean-room formulas for TradingView

### Top Gainers

```text
score = 100 × (last_price / previous_daily_close - 1)
sort score descending
```

Do not impose the Five Pillars filters on this broad list. It is intended to identify the day's largest percentage movers.

### Low Float Top Gainers

```text
include when verified_float <= low_float_limit
score = percentage change from previous close
sort score descending
```

Recommended transparent starting limit: 20 million shares. This is an independent approximation, not a recovered Warrior threshold.

### Ross-style Five Pillars list

```text
2 <= price <= 20          # "between 5 and 10 is even better"
percentage change from prior close >= 10
daily relative volume >= 5
verified float <= 20 million     # SUPERSEDED -> < 10 million
news/catalyst = manual external check
```

`SUPERSEDED ->` **float < 10 million.** Pillar 5 verbatim: *"the float should
be less than 10 million shares, but lower is also better"*
(`oKlhUSSHe2Q` [00:30:38]). 20M is the *scanner dial* from `FILTERS.md`
Layer 0, not the pillar. Also confirmed: this alert is a **state**, not an
event — rows drop off when a name stops meeting the criteria
(`oKlhUSSHe2Q` [00:31:18]), so it cannot be implemented as an append-only feed.

The technical list should expose four automatic tests and keep catalyst/news as a separate manual field.

### Five Pillars HOD alert

```text
technical Five Pillars candidate
AND current high > previous intraday high
AND close > previous intraday high
AND five-minute relative volume >= configured threshold
```

Recommended starting five-minute RVOL threshold: 2x. Calibrate this against Warrior Scanner History rather than treating it as proprietary fact.

### Running Up

```text
100 × (current_close / close_N_minutes_ago - 1) >= configured_move
AND five-minute relative volume >= configured threshold
AND last_price < high_of_day                      # ADDED, confirmed
```

`SUPERSEDED ->` **the below-high-of-day exclusion is definitional**, not
optional: *"the running up scanner tells me when a stock is squeezing up right
now even if it's below its high of day. **In fact, it has to be below the high
of day. Otherwise we'll put it on the high of day momentum scanner.**"*
(`w97KlUrVDk0` [01:00:52]). Running Up and HOD Momentum are complement sets.
Without the exclusion the two widgets duplicate each other and the trade the
scanner exists to surface — an entry below the day's high — is lost.

Move size and window remain UNKNOWN. Transparent starting point: 3% in 2
minutes with five-minute RVOL of at least 2x.

### Explicit Squeeze branches

```text
5-minute squeeze  = move over approximately 5 minutes >= 5%
10-minute squeeze = move over approximately 10 minutes >= 10%
```

Both windows are CONFIRMED (`w97KlUrVDk0` [00:58:40], `yg5E_mqGFGg`
[00:16:36], [00:17:16]); the 5/5 branch is described as *"kind of like a
pre-alert"* for the 10/10. Audio alerts are enabled on the 10/10 branch and
the low-float branches only — *"the others I don't use audio alerts for"*
(`yg5E_mqGFGg` [00:19:36]).

Add a volume confirmation to reduce illiquid single-print alerts.

### 52-week breakout

```text
current high >= highest high of the preceding 252 daily sessions
```

The prior-high calculation must exclude the current daily bar.

### Former momentum stock proxy

```text
highest one-day percentage gain during the preceding 120 sessions >= configured threshold
```

~~Transparent starting threshold: 50%.~~ `SUPERSEDED ->` **100%.** He states
it: *"low float former momentum stock. That means this is a stock that in the
past went up **over 100% in one day**, and that's in the recent past"*
(`w97KlUrVDk0` [00:58:29]). 50% roughly doubles the candidate pool against
what he describes.

**Second confirmed property, previously missing: this strategy runs on
loosened thresholds so it fires earlier than the others.** *"Low float former
momo stocks, when they pick up, they can start moving really quickly, and so
for that reason I want to see them a little sooner… some of the filters are
adjusted a little bit so I could see it quicker. I don't do that for every
type of stock because otherwise you start getting a lot of false alerts"*
(`yg5E_mqGFGg` [00:16:03]). A replica applying one threshold set across all
HOD branches has deleted the early-warning this branch exists for.

The lookback window and the exact loosening remain UNKNOWN; it is still a
proxy for Warrior's private former-runner database.

### High of Day Momentum family

Base event:

```text
new intraday high
AND close above the previous intraday high
AND above-average recent volume
```

Then classify the event using independently configured branches:

- low float + medium RVOL;
- low float + high RVOL;
- low float + high RVOL + price above $20;
- low float + high ATR percentage; `SUPERSEDED ->` the stated component is **float sub-1 million shares** (*"low float volatility hunter — it's a low float stock, sub 1 million shares"*, `w97KlUrVDk0` [00:58:35]). The ATR half is still our inference.
- former-momentum proxy;
- medium float + medium/high RVOL;
- 5% in 5 minutes;
- 10% in 10 minutes;
- 52-week breakout.

### Reversal family — CONFIRMED, previously absent from this document

The platform ships ten reversal strategies and this reference had none.

```text
V5 variant   >= 3 consecutive same-direction candles
V8 variant   >= 4 consecutive same-direction candles
timeframe    5-minute (a 1-minute variant also ships)
direction    consecutive green -> top reversal (short)
             consecutive red   -> bottom reversal (long)
extremes     RSI > 80 or < 20        <- what the shipped hybrid filters
             RSI > 90 or < 10        <- what he says interests him
             candle FULLY outside Bollinger Bands, 20 period / 2 std dev
ideal        5-10 consecutive candles ending in a pin bar or doji
entry        first candle to make a new low (short), stop at the high
```

Sources: `eCSzHYl8apo` [00:10:03], [00:10:30], [00:11:17], [00:11:49],
[00:11:56]; `jfe1Zl-5EQI` [00:17:55], [00:18:10], [00:20:07], [00:20:41];
`yg5E_mqGFGg` [00:21:08].

**V5 and V8 are one dial, not two settings.** He switches between them
intraday to keep the alert rate followable: *"some days we'll have so many
alerts you can't follow them all, so you go to the V8. Other days there are so
few alerts on the V8 you want more ideas, so you look at the V5"*
(`eCSzHYl8apo` [00:12:04]).

**Register warning.** Ten shipped reversal strategies against 5 teaching
files, **0 video recaps** and 2 streams in the corpus; `bollinger` is 0 in
both streams and recaps. Implement it if you want the platform mapped —
do not treat it as a strategy he trades.

## Calibration procedure

To approximate the private thresholds responsibly:

1. Export or record at least 20 trading days of visible Scanner History.
2. For every alert, record symbol, timestamp, strategy name, price, volume, float, daily RVOL, five-minute RVOL, gain and gap.
3. Recalculate the same measurements in TradingView at the alert timestamp.
4. Compare the minimum and distribution of each metric by strategy name.
5. Choose thresholds that reproduce high recall first.
6. Tighten thresholds to reduce false positives.
7. Validate on a later, untouched sample of trading days.
8. Keep separate settings for premarket, the opening hour and midday because volume behavior changes substantially.

Do not infer a threshold from a single day's minimum result. A scanner may include hidden conditions, stale fundamental data, delayed news classification or event-specific exceptions.

## TradingView implementation

The companion script `ross_style_momentum_scanner.pine` implements these clean-room formulas with editable inputs. It also exposes Pine Screener fields and renders entry, stop and target bands on the chart.
