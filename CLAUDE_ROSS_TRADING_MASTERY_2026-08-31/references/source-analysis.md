# Warrior scanner source analysis and clean-room TradingView mapping

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
2 <= price <= 20
percentage change from prior close >= 10
daily relative volume >= 5
verified float <= 20 million
news/catalyst = manual external check
```

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
```

Transparent starting point: 3% in 2 minutes with five-minute RVOL of at least 2x.

### Explicit Squeeze branches

```text
5-minute squeeze  = move over approximately 5 minutes >= 5%
10-minute squeeze = move over approximately 10 minutes >= 10%
```

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

Transparent starting threshold: 50%. This is only a proxy for Warrior's private former-runner classification.

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
- low float + high ATR percentage;
- former-momentum proxy;
- medium float + medium/high RVOL;
- 5% in 5 minutes;
- 10% in 10 minutes;
- 52-week breakout.

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
