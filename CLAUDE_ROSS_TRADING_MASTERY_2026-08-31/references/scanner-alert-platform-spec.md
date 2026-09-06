# Clean-room Momentum Scanner and Alert Platform

> Implementation specification — 1 September 2026  
> Purpose: reproduce the useful workflow of a small-cap momentum discovery platform without copying proprietary Warrior Trading code, hidden formulas, credentials or protected content.

## 1. Desired outcome

Build a private workstation that continuously monitors US-listed equities and provides:

1. ranked scanner lists;
2. real-time momentum alerts;
3. fresh-news and halt indicators;
4. linked 1-minute, 5-minute and daily charts;
5. transparent Five Pillars scoring;
6. entry, structural-stop and target planning bands;
7. alert history and deterministic market replay;
8. browser/audio/push/Slack notifications;
9. an explanation of exactly why every symbol appeared;
10. clear data-health and stale-feed warnings.

The application is a discovery and planning tool. It must never interpret a scanner event as an automatic trade order.

## 2. Clean-room boundary

### Permitted

- implement independently defined formulas from market data;
- reproduce generic product behaviors such as ranked tables, linked symbols, alert streams and layouts;
- use confirmed public scanner names as inspiration while labeling the formulas independently;
- calibrate transparent parameters against the user's own recorded observations;
- use licensed APIs, official SEC data and official halt feeds;
- implement the Five Pillars thresholds confirmed in the captured course material.

### Prohibited or unavailable

- copying Warrior frontend bundles or server code;
- extracting or reusing session tokens, signed URLs, credentials or private endpoints;
- claiming that approximations are Ross's hidden production formulas;
- bypassing entitlements or redistributing exchange/news data without permission;
- reproducing proprietary transcripts or locked course content;
- using TradingView Advanced Charts code obtained outside its official access process.

## 3. Evidence labels used in this specification

- **Confirmed course**: taught in the authenticated Preview material.
- **Confirmed platform**: documented/visible scanner behavior captured before access ended.
- **Independent formula**: clean-room definition proposed for this application.
- **Configuration**: editable personal value requiring replay validation.
- **Unknown**: Warrior's exact production value or formula was not exposed.

## 4. MVP versus later phases

### MVP — build first

- US equity reference universe;
- premarket, regular and after-hours session handling;
- trade/quote or aggregate ingestion;
- Top Gappers, Top Gainers, Top Losers and Low Float Top Gainers;
- transparent Five Pillars candidate list and alert;
- HOD Momentum, Running Up/Down, 5-in-5, 10-in-10 and 52-week breakout;
- fresh-news indicator and Nasdaq halt status;
- real-time browser table, linked charts and alert timeline;
- local audio, browser notifications and Slack webhook;
- scanner history, replay and audit logs;
- stale-data and connection alarms.

### Phase 2

- first-pullback state machine and frozen entry/stop/target bands;
- SEC dilution-risk enrichment;
- recent IPO, reverse-split, Former Momo and continuation datasets;
- mobile/web push through FCM;
- strategy statistics and false-positive/false-negative calibration.

### Phase 3

- licensed Level 2/market-depth data;
- Time & Sales visualization;
- broker/order integration only after simulator validation, security review and explicit authorization;
- multi-user permissions and commercial redistribution only after licensing review.

## 5. Recommended reference architecture

```text
                    +----------------------+
                    | Reference / Float DB |
                    +----------+-----------+
                               |
+-------------+      +---------v----------+      +----------------+
| Market Data |----->| Normalizer / Bars  |----->| Hot State      |
| WS / TCP    |      | Sessions / Quality |      | Redis / Memory |
+-------------+      +---------+----------+      +--------+-------+
                               |                          |
+-------------+      +---------v--------------------------v-------+
| News / SEC  |----->| Scanner Workers + Catalyst Enrichment      |
+-------------+      +------------------+-------------------------+
                                          |
                               +----------v-----------+
                               | Canonical Event Bus  |
                               +----+-------------+---+
                                    |             |
                          +---------v--+     +----v----------------+
                          | Event Store |     | Notification Router |
                          | PostgreSQL  |     | Dedupe / Cooldown   |
                          +------+-----+     +----+-----+----------+
                                 |                |     |
                      +----------v------+   Audio/Push  Slack/Email
                      | API + WebSocket |
                      +----------+------+
                                 |
                      +----------v----------------------+
                      | Dashboard / Charts / News / L2  |
                      +---------------------------------+
```

## 6. Practical technology stack

### Default single-user stack

| Layer | Recommended starting point | Why |
|---|---|---|
| Backend | Python 3.12 + FastAPI + asyncio | Strong market-data ecosystem, WebSocket support and fast iteration |
| Hot state | Redis | Symbol snapshots, sorted sets, cooldown keys and pub/sub/streams |
| Durable data | PostgreSQL; TimescaleDB optional | Scanner events, news, configuration, audit and bar history |
| Worker execution | asyncio services initially; Redis Streams/Celery later | Avoid premature distributed complexity |
| Frontend | React/Next.js + TypeScript | Real-time dashboard and modular widgets |
| Charts | TradingView Lightweight Charts for MVP | Open charting library; follow attribution/license requirements |
| Transport | WebSocket for live UI; REST for history/config | Efficient push plus simple CRUD |
| Packaging | Docker Compose | Reproducible local deployment |
| Observability | Structured JSON logs + Prometheus/Grafana later | Latency, disconnect and scanner-health evidence |

TradingView's Lightweight Charts documentation provides React examples, real-time update examples and multi-pane support. Follow its current attribution requirements: [official Lightweight Charts documentation](https://tradingview.github.io/lightweight-charts/).

### Advanced Charts alternative

TradingView Advanced Charts is richer, but access is controlled and the library does **not** include market data. The application must implement its own Datafeed API and use officially granted library access; TradingView states that the library is non-redistributable. See the [official Datafeed API](https://www.tradingview.com/charting-library-docs/latest/connecting_data/datafeed-api/) and [official access instructions](https://www.tradingview.com/charting-library-docs/latest/getting_started/quick-start/).

## 7. Data sources and entitlements

### 7.1 Market-data capability matrix

Choose one primary market-data provider. Do not mix last price from one vendor with volume/reference values from another until symbol mapping and timestamp behavior are validated.

| Option | Appropriate use | Official capability evidence | Caution |
|---|---|---|---|
| Alpaca Market Data | Simple MVP using WebSocket trades/quotes/bars | Supports `v2/sip`, `v2/iex` and delayed SIP WebSocket feeds: [Alpaca real-time stock data](https://docs.alpaca.markets/us/docs/real-time-stock-pricing-data) | Verify subscription, symbol coverage and display/non-display terms |
| Polygon/Massive-style API | Broad US trade/quote/reference/news integration | Official stocks overview describes REST, WebSocket and flat-file access across US venues: [stocks overview](https://polygon.io/docs/rest/stocks/overview) | Verify current branding, plan latency, exchange agreements and redistribution rights |
| Databento | Higher-fidelity replay, direct feeds and eventual L2/L3 | Supports L1, L2, L3, OHLCV, premarket and reference schemas: [equities documentation](https://databento.com/equities) | Full-market consolidated logic and venue licensing require careful product selection |
| Intrinio | Combined real-time, fundamentals, news and mover endpoints | Official docs expose prices, movers, status, replay and company news: [Intrinio documentation](https://intrinio.com/docs) | Confirm latency, exchange scope and dataset-specific entitlements |

Do not select solely by price. Evaluate:

- SIP versus single-venue coverage;
- 4:00–20:00 ET extended-hours coverage;
- corrections, cancels and trade-condition handling;
- quote/NBBO availability;
- timestamp precision and clock source;
- snapshot plus streaming recovery;
- historical tick/minute replay;
- rate limits and concurrent subscriptions;
- reference data and corporate actions;
- personal display versus non-display calculations;
- redistribution and commercial-use rights.

### 7.2 News

The alert system needs timestamped, symbol-mapped headlines. A licensed real-time feed such as Benzinga can stream news and other events through WebSocket; its documentation describes push updates, unique IDs and replay/deduplication concepts: [Benzinga WebSocket overview](https://docs.benzinga.com/ws-reference/overview).

Store at minimum:

- provider article ID;
- published, updated and first-observed timestamps;
- symbols;
- headline, summary and source URL;
- event category;
- correction/update/delete state;
- catalyst classification and confidence;
- license-permitted display fields.

Never expose the provider token to the browser.

### 7.3 SEC filings

Use `data.sec.gov` submissions and company facts to enrich dilution and catalyst analysis. The SEC's official API page covers company submissions and extracted XBRL facts: [EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).

Required safeguards:

- descriptive `User-Agent` with contact information;
- cache by accession number and CIK;
- global request limiter;
- current SEC guideline of no more than 10 requests/second;
- retry with backoff for transient failures;
- no repeated downloading of unchanged filings.

See [SEC Developer Resources](https://www.sec.gov/about/developer-resources).

### 7.4 Trading halts

Nasdaq Trader exposes a free RSS halt feed covering Nasdaq and other exchange-listed securities. The official page says it updates once per minute and should not be queried more frequently: [Nasdaq Trade Halt RSS](https://nasdaqtrader.com/Trader.aspx?id=TradeHaltRSS).

Treat the one-minute RSS cadence as a status source, not a sub-second execution feed. A market-data provider's trading-status messages may be faster if included in the selected license.

### 7.5 Float and fundamentals

Store three distinct supply fields:

- `verified_float_shares`;
- `shares_outstanding`;
- `supply_value_used` plus `supply_source`.

Never silently substitute shares outstanding for float. If float is unknown, show `UNKNOWN` or an explicitly labeled proxy. Preserve point-in-time snapshots because float and shares outstanding change after offerings, splits and conversions.

## 8. Canonical market model

### 8.1 Sessions

All scanner logic must use `America/New_York`, not a fixed UTC offset.

| Session | ET interval |
|---|---|
| Premarket | 04:00–09:30 |
| Regular | 09:30–16:00 |
| After-hours | 16:00–20:00 |

Handle weekends, exchange holidays, early closes and daylight-saving changes with an exchange calendar.

### 8.2 Symbol snapshot

Maintain one hot snapshot per symbol:

```json
{
  "symbol": "ABCD",
  "exchange": "NASDAQ",
  "event_ts": "2026-09-01T12:04:05.125Z",
  "ingest_ts": "2026-09-01T12:04:05.149Z",
  "last": 6.75,
  "bid": 6.73,
  "ask": 6.76,
  "prev_close": 5.10,
  "regular_open": null,
  "session_high": 6.80,
  "session_low": 5.42,
  "volume_today": 8425000,
  "volume_5m": 916000,
  "trades_1m": 487,
  "float_shares": 12000000,
  "float_quality": "verified",
  "latest_news_ts": "2026-09-01T11:58:10Z",
  "halt_status": "trading",
  "data_status": "live"
}
```

### 8.3 Data-quality rules

Reject or quarantine events when:

- price is non-positive;
- timestamps move backward beyond an allowed correction window;
- bid exceeds ask without a documented crossed-market condition;
- price jump is an obvious bad tick confirmed by adjacent events/provider status;
- corporate-action adjustment is missing;
- the stream is stale;
- symbol mapping is unresolved;
- a cancel/correction invalidates the originating trade.

Every snapshot should retain `event_ts`, `ingest_ts` and `scan_ts` so latency can be measured rather than guessed.

## 9. Core clean-room formulas

The formulas below are independent definitions. Warrior's vendor-specific normalization is unknown.

### 9.1 Price changes

```text
change_from_close_pct = 100 × (last / previous_regular_close - 1)
change_from_open_pct  = 100 × (last / regular_session_open - 1)
gap_pct_at_t          = 100 × (reference_price_at_t / previous_regular_close - 1)
```

For a premarket gap list, `reference_price_at_t` is the latest eligible premarket trade. Freeze the final Top Gappers snapshot at 09:30 ET if reproducing the captured platform behavior.

### 9.2 Simple relative volume

```text
simple_daily_rvol = cumulative_volume_today / mean(full_day_volume, prior N sessions)
```

This is easy but understates early-session pace because a partial day is compared with full days.

### 9.3 Recommended time-of-day RVOL

```text
rvol_tod(t) = cumulative_volume_today_through_t
              / median(cumulative_volume_through_same_session_minute,
                       prior N comparable sessions)
```

Recommended initial configuration: `N = 20`, median rather than mean, separate premarket and regular-session baselines. Validate against replay before using live.

### 9.4 Five-minute RVOL

```text
rvol_5m(t) = volume(t-5m, t)
             / median(volume(same five-minute clock window), prior N sessions)
```

Fallback when same-clock history is unavailable:

```text
rvol_5m_fallback = current_5m_volume / mean(previous 20 completed 5m bars)
```

Display which definition produced the value.

### 9.5 Spread and liquidity

```text
spread_abs = ask - bid
mid        = (ask + bid) / 2
spread_bps = 10,000 × spread_abs / mid
dollar_volume_1m = sum(trade_price × trade_size, last 1m)
trades_per_minute = count(eligible trades, last 1m)
```

Liquidity guards are Configuration values, not confirmed Ross thresholds. Make them price-bucket specific.

### 9.6 Day-range position

```text
range_position = (last - session_low) / (session_high - session_low)
```

Clamp to `[0,1]`; return null when the range is zero.

### 9.7 HOD event

```text
prior_hod = maximum eligible trade high before current evaluation event
new_hod   = current_high > prior_hod + minimum_tick_buffer
```

Choose and expose one evaluation mode:

- intratrade/intrabar for speed;
- 1-minute close confirmation for stability;
- both, with distinct event names.

### 9.8 Running Up/Down

```text
move_Nm_pct = 100 × (last / reference_price_N_minutes_ago - 1)
running_up  = move_Nm_pct >= configured_threshold
              AND recent_volume_condition
              AND liquidity_guard
running_down = move_Nm_pct <= -configured_threshold
               AND recent_volume_condition
               AND liquidity_guard
```

The exact Warrior percentage/window formula is Unknown. Start with configurable windows such as 1, 2 and 5 minutes and calibrate from replay.

### 9.9 Squeeze alerts

```text
squeeze_5_in_5   = move_5m_pct  >= 5%  AND volume/liquidity confirmation
squeeze_10_in_10 = move_10m_pct >= 10% AND volume/liquidity confirmation
```

The named percentages/windows are Confirmed platform branch descriptions; the shared volume and exclusion logic remains Unknown.

### 9.10 52-week breakout

```text
prior_52w_high = max(adjusted_daily_high, preceding 252 sessions)
breakout_52w   = current_high > prior_52w_high
```

Exclude the current session from the historical maximum and handle split-adjusted history consistently.

## 10. Scanner definitions

Every scanner definition must be versioned and store its parameter snapshot with each event.

### 10.1 Top Gappers

**Type:** ranked list.  
**Refresh:** every 30 seconds until 09:30 ET.  
**Sort:** `gap_pct_at_t` descending for gainers, ascending for losers.

Base filters:

- active US-listed common stocks/ADRs as configured;
- eligible premarket trade;
- previous close available;
- price and liquidity data valid.

Variants:

- Penny Top Gappers: price under 5 USD;
- Small Cap Top Gappers: configurable market-cap/float universe;
- Large Cap Gappers: configurable market-cap universe;
- unfiltered Top Gappers: first 100 ranked results;
- earnings-with-gap: joins a scheduled/reported earnings event.

### 10.2 Top Gainers and Losers

**Type:** ranked list.  
**Refresh:** 15–30 seconds continuously.

```text
rank_metric = change_from_close_pct
```

Variants: Top Gainers, Top Losers, Low Float Top Gainers, Penny Top Gainers/Losers and After Hours Top Gainers.

### 10.3 Transparent Five Pillars candidate

Confirmed working thresholds:

```text
price_ok = 2 <= last <= 20
gain_ok  = change_from_close_pct >= 10
rvol_ok  = selected_daily_rvol >= 5
float_ok = verified_float_shares < 20,000,000
news_ok  = catalyst confirmed manually or by licensed classified news
```

Store technical and full scores separately:

```text
technical_score = price_ok + gain_ok + rvol_ok + float_ok   # 0..4
full_score      = technical_score + news_ok                 # 0..5
technical_candidate = technical_score == 4
full_candidate      = full_score == 5
```

Do not fail a technical candidate solely because news is absent; the captured Warrior scanner also did not automatically enforce news.

### 10.4 Five Pillars alert

Emit on the **rising edge** from non-qualifying to qualifying, not on every tick:

```text
event = technical_candidate_now AND NOT technical_candidate_previous
```

Re-arm only after a configurable non-qualifying period. Attach each pillar's raw value and pass/fail state.

### 10.5 HOD Momentum

Independent base formula:

```text
hod_momentum = new_hod
               AND selected_recent_rvol >= hod_rvol_min
               AND change_from_close_pct >= hod_gain_min
               AND liquidity_guard
```

Create configurable branches corresponding to the captured visible names:

1. Low Float – Medium Relative Volume
2. Low Float – High Relative Volume
3. Low Float – High Relative Volume – Price 20+
4. Low Float Volatility Hunter – HOD breakout
5. Former Momo
6. Medium Float – Medium RVOL – Price 20+
7. Medium Float – High RVOL – Price 20+
8. Medium Float – High RVOL – Price under 20
9. Squeeze – Up 10% in 10 minutes
10. Squeeze – Up 5% in 5 minutes
11. Squeeze – 52-week Breakout

The exact float bands, medium/high RVOL values, Volatility Hunter calculation and Former Momo database are Unknown. Keep defaults in configuration with an `independent_approximation` label.

### 10.6 Running Up and Running Down

**Type:** event alert independent of HOD.  
**Purpose:** detect rapid acceleration before a new HOD occurs.

Use separate parameter sets for premarket, regular open and midday because volume distributions differ. Suppress repeated alerts until price advances another configured increment or the cooldown expires.

### 10.7 Top Relative Volume

**Type:** ranked list.  
**Sort:** selected `rvol_tod` or explicitly chosen RVOL field.

The UI must show the formula name and baseline window so values are reproducible.

### 10.8 Top Volume 5 Minutes

Rank raw `volume_5m` descending. Add optional `rvol_5m`, dollar volume and trade-count columns; do not silently replace raw volume with RVOL.

### 10.9 Top of Trend approximation

```text
top_of_trend_score = weighted(
  range_position,
  change_from_close_pct,
  rvol_tod,
  distance_above_vwap,
  proximity_to_hod
)
```

All weights are Configuration. The captured platform description is Confirmed; its exact formula is Unknown.

### 10.10 Continuation approximation

Candidate condition:

- large two-week range;
- current price holds above a configurable portion of that range;
- current volume/liquidity valid;
- optional recent-runner flag.

Do not present this as Warrior's exact continuation formula.

### 10.11 Recent IPO and reverse split

- Recent IPO/uplist: maintain listing date and opening/reference level; initial window around 90 days based on captured platform description.
- Recent reverse split: corporate action within roughly 30 days and ratio greater than 10:1, matching the captured descriptive behavior.

Corporate-action data must be point-in-time and applied consistently to historical bars.

### 10.12 Halt scanner

Emit distinct events:

- `halt.started`;
- `halt.updated`;
- `halt.resume_time_announced`;
- `halt.resumed`.

Never infer a halt solely from missing trades. Require an official/provider status event.

## 11. First-pullback detector and planning bands

### 11.1 State machine

```text
SEEKING_IMPULSE
    -> PULLBACK_1
    -> PULLBACK_2_TO_4
    -> ARMED
    -> TRIGGERED
    -> TARGET_HIT / STOPPED / EXPIRED

Any invalid condition -> REJECTED
```

### 11.2 Independent detection proposal

Impulse candidate:

- strong green price expansion;
- elevated volume relative to recent bars;
- candidate meets at least four pillars;
- near HOD and not beyond configured extension limit.

Pullback:

- 2–4 completed candles for the standard setup;
- one candle for the micro-pullback variant;
- pullback volume generally declines from impulse volume;
- structure retains a logical low;
- five or six pullback candles normally expire the standard setup.

Trigger:

```text
trigger_high = high of the last completed pullback/signal candle
entry        = trigger_high + entry_buffer
stop         = minimum low of the complete pullback - stop_buffer
risk_share   = entry - stop
target_2r    = entry + 2 × risk_share
```

Validate target against HOD, half/whole dollars, daily levels and 200 EMA. Do not emit a qualified plan when the first meaningful resistance prevents the configured minimum reward/risk.

### 11.3 Freeze and version bands

Once ARMED:

- persist entry, stop and target;
- store the exact signal bar and scanner-definition version;
- do not move bands with subsequent candles;
- expire after a configured time or structural invalidation;
- create a new plan ID for a later setup.

## 12. News-flame and catalyst engine

### 12.1 Flame mapping

Captured platform behavior:

```text
red flame    = headline age 0–2h
orange flame = 2–12h
yellow flame = 12–24h
no flame     = older than 24h or no item
```

Calculate age from the provider's original publication time and retain first-observed time to measure latency.

### 12.2 Catalyst classifications

Support these families:

- earnings;
- FDA/clinical result;
- buyout;
- split/reverse split;
- analyst rating/target;
- activist stake;
- order/contract/partnership;
- secondary offering;
- private placement;
- IPO/uplist/delist;
- patent/trademark;
- merger/SPAC/acquisition;
- lawsuit/regulatory event;
- short-interest/squeeze theme;
- sympathy/theme;
- pure technical momentum.

Store classification confidence and allow manual correction. A flame means recent news, not positive news and not full Five Pillars compliance.

### 12.3 Dilution flags

Enrichment flags:

- active/recent S-3 shelf;
- offering or placement headline;
- warrants/converts;
- low cash runway;
- recent reverse split;
- large increase in shares outstanding;
- resale registration.

Do not automatically reject solely because a shelf exists; treat it as risk context.

## 13. Canonical scanner-event envelope

Every scanner emits the same event structure:

```json
{
  "event_id": "01J...",
  "event_version": 1,
  "idempotency_key": "ABCD|hod_momentum|low_float_high_rvol|20260901T080405",
  "symbol": "ABCD",
  "scanner": "hod_momentum",
  "branch": "low_float_high_rvol",
  "event_type": "qualified",
  "severity": "high",
  "session": "premarket",
  "source_ts": "2026-09-01T12:04:05.125Z",
  "scan_ts": "2026-09-01T12:04:05.172Z",
  "definition_version": "hod_momentum@1.3.0",
  "values": {
    "last": 6.75,
    "change_pct": 32.35,
    "rvol_tod": 8.4,
    "rvol_5m": 6.2,
    "float_m": 12.0,
    "spread": 0.03
  },
  "reasons": [
    {"filter": "new_hod", "value": true, "passed": true},
    {"filter": "rvol_5m", "value": 6.2, "threshold": 5.0, "passed": true}
  ],
  "news": {
    "age_minutes": 6,
    "flame": "red",
    "category": "contract",
    "headline_id": "provider-id"
  },
  "data_quality": "live"
}
```

Never make the UI reverse-engineer qualification from a text message; ship raw values and reasons.

## 14. Notification engine

### 14.1 Delivery pipeline

```text
scanner event
-> validation
-> idempotency check
-> consolidation/grouping
-> severity and user-rule evaluation
-> cooldown/re-arm logic
-> channel fan-out
-> delivery receipt/retry
-> audit log
```

### 14.2 Notification levels

| Level | Typical events | Default behavior |
|---|---|---|
| Critical | data outage, order-state uncertainty, halt/resume for held/watchlisted symbol | persistent banner + distinct sound + push |
| High | Five Pillars HOD, qualified first pullback, fresh catalyst plus momentum | sound + browser/push + alert stream |
| Medium | Running Up, squeeze, 52-week breakout | alert stream + optional sound |
| Low | list-rank changes, informational news | table update only |

Severity is independent Configuration, not a claim about trade quality.

### 14.3 Deduplication

Use a stable idempotency key based on symbol, scanner, branch and source event/bucket. Store it with TTL.

Do not alert repeatedly on every qualifying tick. Emit on:

- rising edge;
- a new qualifying branch;
- a meaningful new price tier;
- a new catalyst;
- re-arm after a documented reset/cooldown.

### 14.4 Consolidation

Group multiple same-symbol alerts arriving within a configurable 2–5 second window:

```json
{
  "symbol": "ABCD",
  "primary": "five_pillars_hod",
  "also_triggered": ["running_up", "squeeze_5_in_5"],
  "first_ts": "...",
  "latest_ts": "...",
  "count": 3
}
```

Keep every raw event in history even when the UI displays one consolidated row.

### 14.5 Cooldowns

Initial configurable defaults for testing, not production truths:

- HOD Momentum: 30–60 seconds per symbol/branch unless price advances a new tier;
- Running Up: 60–180 seconds unless acceleration increases materially;
- list rank: no audio;
- news: one alert per provider article ID, with update alerts only for material changes;
- halt/resume: never suppress a state transition.

### 14.6 Channels

#### In-app audio

- pre-load sounds after a user gesture to satisfy browser autoplay rules;
- one sound family per severity or strategy;
- master volume plus per-scanner enable/disable;
- rate-limit simultaneous sounds;
- show a visual alert even if audio permission fails.

#### Browser notifications

- request permission only after the user enables alerts;
- include ticker, scanner, price, change, RVOL and news-age summary;
- click opens the symbol workspace;
- never place secrets in the notification payload.

#### Mobile/web push

Firebase Cloud Messaging supports browser background notifications through service workers and requires HTTPS for web clients: [FCM web setup](https://firebase.google.com/docs/cloud-messaging/web/get-started). Store device tokens securely and allow per-device revocation.

#### Slack

Slack incoming webhooks accept JSON payloads tied to a channel. The webhook URL is a secret and must remain server-side: [Slack incoming webhooks](https://api.slack.com/messaging/webhooks).

#### Email

Use only for low-frequency summaries, system failures or end-of-day reports; email latency makes it unsuitable as the primary momentum alert channel.

### 14.7 Retries and delivery state

Delivery states:

```text
queued -> sending -> delivered
                  -> retry_wait -> delivered
                                -> dead_letter
```

Use exponential backoff with jitter. Do not retry permanent 4xx configuration failures blindly. Record provider response code, attempts and final state.

## 15. Dashboard specification

### 15.1 Layout

```text
+----------------------+----------------------+----------------------+
| Scanner lists        | 1-minute chart       | News / catalyst      |
| Top Gappers/Gainers  |                      | SEC flags            |
| Five Pillars         +----------------------+----------------------+
| RVOL / Top of Trend  | 5-minute chart       | Level 2 (later)      |
+----------------------+----------------------+----------------------+
| Alert timeline       | Daily chart          | Time & Sales (later) |
+----------------------+----------------------+----------------------+
```

### 15.2 Linked-symbol behavior

Clicking a ticker updates:

- all chart timeframes;
- news/catalyst panel;
- fundamentals/float;
- daily levels;
- Level 2/tape if licensed;
- current scanner reasons;
- planning-band form.

Preserve the selected ticker in the URL so alerts can deep-link into the workspace.

### 15.3 Scanner table columns

Core columns:

- symbol and flame;
- last price;
- change versus close;
- gap percentage;
- volume today;
- daily/time-of-day RVOL;
- five-minute volume and RVOL;
- float plus source quality;
- spread;
- HOD distance;
- scanner/branch;
- alert time;
- pass/fail reason expansion.

Color gradients are comparative visual aids, not rules. Always retain numeric values and accessible text.

### 15.4 Data-health UI

Display:

- provider connection state;
- time since last market event;
- event-to-scan and scan-to-browser latency;
- active subscription count;
- rejected/bad-tick count;
- news and halt-feed age;
- red stale state when thresholds are exceeded.

## 16. Data model

### Core tables

```sql
symbols(
  symbol primary key,
  exchange, name, security_type, active,
  listing_date, cik, updated_at
)

fundamental_snapshots(
  symbol, effective_at, observed_at,
  float_shares, shares_outstanding, market_cap,
  source, quality, primary key(symbol, effective_at, source)
)

corporate_actions(
  id primary key, symbol, action_type, ex_date,
  ratio, source, observed_at
)

bars(
  symbol, timeframe, session, ts,
  open, high, low, close, volume, trade_count, vwap,
  primary key(symbol, timeframe, session, ts)
)

news_items(
  provider, provider_id, published_at, updated_at,
  first_observed_at, headline, summary, url,
  category, confidence, correction_state,
  primary key(provider, provider_id)
)

news_symbols(provider, provider_id, symbol)

scanner_definitions(
  scanner_id, version, name, type,
  parameters_json, status, created_at,
  primary key(scanner_id, version)
)

scanner_events(
  event_id primary key, idempotency_key unique,
  symbol, scanner_id, definition_version, branch,
  event_type, severity, source_ts, scan_ts,
  values_json, reasons_json, news_json, data_quality
)

notification_rules(
  rule_id primary key, user_id, enabled,
  scanners_json, symbols_json, sessions_json,
  severities_json, channels_json, cooldown_json
)

notification_deliveries(
  delivery_id primary key, event_id, channel,
  destination_id, status, attempts,
  last_error, queued_at, delivered_at
)

watchlists(user_id, list_id, symbol, tags_json)
levels(user_id, symbol, level_type, price, source, created_at)
audit_log(id, actor, action, object_type, object_id, details_json, ts)
```

Use migrations and retain scanner-definition versions so historical results remain reproducible.

## 17. API and WebSocket contract

### REST

```text
GET  /api/v1/health
GET  /api/v1/data-health
GET  /api/v1/symbols/{symbol}/snapshot
GET  /api/v1/symbols/{symbol}/bars?timeframe=1m&session=extended
GET  /api/v1/symbols/{symbol}/news
GET  /api/v1/scanners
GET  /api/v1/scanners/{id}/results
GET  /api/v1/scanner-events?from=&to=&symbol=&scanner=
POST /api/v1/scanner-definitions/{id}/validate
POST /api/v1/scanner-definitions/{id}/activate
GET  /api/v1/notification-rules
PUT  /api/v1/notification-rules/{id}
POST /api/v1/notifications/test
GET  /api/v1/replay/sessions
POST /api/v1/replay/run
```

### WebSocket topics

```text
market.snapshot.{symbol}
scanner.list.{scanner_id}
scanner.event
news.event.{symbol}
halt.event
data.health
notification.delivery
```

On reconnect, the client sends its last sequence number. The server returns missed events from durable storage, then resumes live streaming.

## 18. Scanner engine interface

Pseudocode:

```python
class Scanner:
    scanner_id: str
    definition_version: str

    async def on_snapshot(self, current, previous, context) -> list[ScannerEvent]:
        """Return zero or more explainable, idempotent events."""

    async def rank(self, universe, context) -> list[RankedResult]:
        """Return a deterministic list with raw values and reasons."""
```

Evaluation loop:

```text
receive normalized event
-> update bars and symbol snapshot atomically
-> evaluate only scanners affected by changed fields
-> persist unique events
-> publish list deltas/events
-> route notifications asynchronously
```

Do not block market-data ingestion while Slack, email or push delivery occurs.

## 19. Configuration design

Example versioned YAML:

```yaml
scanner_id: hod_momentum
version: 1.0.0
status: simulation
sessions: [premarket, regular]
universe:
  security_types: [common_stock, adr]
  min_price: 1.00
  max_price: 50.00
conditions:
  new_hod: intrabar
  min_change_pct: 10.0
  recent_rvol_field: rvol_5m_tod
  min_recent_rvol: 3.0
liquidity:
  max_spread_bps: 150
  min_trades_1m: 20
notifications:
  rising_edge_only: true
  cooldown_seconds: 60
  consolidate_seconds: 3
classification: independent_approximation
```

All parameter changes create a new immutable version. Only one version should be active per environment unless running an explicit A/B comparison.

## 20. Testing and calibration

### 20.1 Unit tests

Test:

- session boundaries and daylight-saving transitions;
- previous-close and gap calculations;
- corporate-action adjustment;
- time-of-day RVOL baselines;
- HOD rising-edge behavior;
- 5-in-5 and 10-in-10 windows;
- float unknown/proxy handling;
- flame age boundaries at exactly 2, 12 and 24 hours;
- duplicate event suppression;
- cooldown/re-arm logic;
- halt state transitions;
- first-pullback state transitions and band freeze;
- reconnect and missed-event replay.

### 20.2 Golden replay fixtures

Create small deterministic sessions containing:

1. qualifying Five Pillars candidate;
2. same chart without RVOL;
3. HOD event followed by repeated HOD ticks;
4. Running Up before HOD;
5. fresh-news correction/update;
6. reverse split and adjusted history;
7. halt and resumption;
8. bad tick/correction;
9. spread blowout;
10. valid and invalid first pullbacks.

Expected events must be stored as fixtures and compared exactly.

### 20.3 Historical calibration

For each scanner:

- collect symbol, source timestamp and observed Warrior-style category where available;
- replay identical market periods;
- compare hits and misses;
- separate premarket, opening hour, midday and after-hours;
- tune on a training period;
- freeze parameters;
- validate on a later untouched period;
- report precision, recall, false positives and false negatives.

The goal is useful discovery, not pretending to reverse-engineer an unknowable formula exactly.

### 20.4 Load and failure testing

Simulate:

- full supported universe during the 09:30 burst;
- provider disconnect and reconnect;
- duplicate/out-of-order messages;
- Redis/PostgreSQL temporary outage;
- slow Slack/FCM endpoint;
- browser reconnect after sleep;
- clock drift;
- news flood and market-wide volatility.

## 21. Operational objectives

Initial single-user targets:

- market event to scanner decision: p95 under 500 ms for tick alerts;
- scanner event to browser display: p95 under 1 second;
- ranked lists refreshed within 30 seconds;
- zero duplicate notifications for the same idempotency key;
- every event includes raw reasons and definition version;
- stale-feed detection within a configured threshold appropriate to the session;
- no lost scanner events after a notification-channel failure.

These are engineering targets, not exchange guarantees.

## 22. Security and licensing checklist

- keep provider, news, FCM and Slack secrets server-side;
- use a secret manager or protected environment variables;
- never commit `.env`, API keys or webhook URLs;
- encrypt external tokens at rest where practical;
- use HTTPS/WSS;
- validate all WebSocket and webhook payloads;
- rate-limit configuration and test-notification endpoints;
- use least-privilege database roles;
- maintain audit logs for rule changes;
- back up PostgreSQL and configuration;
- review exchange display/non-display agreements;
- review news headline/content display rights;
- review chart-library license/attribution;
- prohibit public redistribution until licensing explicitly allows it.

## 23. Build sequence

### Phase 0 — decisions and contracts

- choose primary data provider;
- confirm SIP/extended-hours/historical entitlements;
- choose news provider;
- decide personal-only versus multi-user deployment;
- define security types and exchanges in scope;
- document cost ceiling and retention period.

**Exit:** signed-off data contract and normalized schema.

### Phase 1 — replay-first backend

- repository, Docker Compose, PostgreSQL and Redis;
- provider-independent event schemas;
- historical/replay adapter;
- session calendar and bar builder;
- unit/golden tests.

**Exit:** deterministic replay builds identical snapshots and bars.

### Phase 2 — ranked scanners

- Top Gappers;
- Top Gainers/Losers;
- RVOL lists;
- float enrichment;
- Five Pillars table;
- REST results and simple frontend.

**Exit:** every ranked row explains its values and data freshness.

### Phase 3 — event alerts

- HOD, Running Up/Down, squeezes and 52-week breakout;
- canonical event envelope;
- dedupe, consolidation, cooldown and event history;
- local audio and browser alerts.

**Exit:** replay produces exactly one expected notification per logical event.

### Phase 4 — news, SEC and halts

- news stream and flame mapping;
- SEC filing cache and dilution flags;
- halt/resumption feed;
- catalyst and risk panels.

**Exit:** headline age, correction state and halt transitions are auditable.

### Phase 5 — linked workstation

- scanner tables;
- two or three linked charts;
- news panel;
- alert timeline;
- saved layout and watchlists;
- deep links from notifications.

**Exit:** one click changes all widgets to the same symbol.

### Phase 6 — first pullback and risk bands

- state machine;
- volume-profile checks;
- structural entry/stop/2R calculation;
- frozen bands and scenario journal.

**Exit:** valid/invalid fixtures pass and bands never repaint after arming.

### Phase 7 — external notifications and resilience

- Slack and FCM;
- retry/dead-letter handling;
- monitoring, backups and outage runbook;
- live shadow mode beside replay results.

**Exit:** notification failure never blocks scanning or loses stored events.

### Phase 8 — optional L2/tape

- choose licensed depth feed;
- implement order-book normalization;
- visualize depth and prints;
- measure latency and dropped sequences.

**Exit:** sequence gaps are detected and book state can recover from snapshot.

## 24. MVP definition of done

- [ ] Live or replay data covers the intended US universe and extended hours.
- [ ] Data status and latency are visible.
- [ ] Top Gappers freezes at 09:30 ET.
- [ ] Top Gainers/Losers and RVOL lists continue updating.
- [ ] Five Pillars fields are independent and news is not hidden inside the technical score.
- [ ] HOD, Running Up/Down, 5-in-5, 10-in-10 and 52-week alerts work in replay.
- [ ] Every alert contains raw values, reasons and definition version.
- [ ] Dedupe, consolidation, cooldown and history are verified.
- [ ] Fresh-news flame colors use publication time and show latency.
- [ ] Halt/resume status comes from an official/provider source.
- [ ] Ticker clicks link scanners, charts and news.
- [ ] Browser/audio/Slack notifications can be individually tested.
- [ ] No credentials reach the frontend or repository.
- [ ] Historical replay reproduces expected events.
- [ ] All unconfirmed thresholds are visibly labeled approximations.

## 25. What not to build first

- broker order routing;
- automatic trade execution;
- full Level 3 order book;
- social/chat room features;
- AI-generated buy/sell signals;
- dozens of speculative scanners;
- multi-tenant billing;
- pixel-perfect copying of the Warrior UI.

These features delay the part that creates value: timely, explainable discovery with reliable alerts.

## 26. Starter repository structure

```text
momentum-workstation/
|-- apps/
|   |-- api/
|   `-- web/
|-- services/
|   |-- market_ingest/
|   |-- news_ingest/
|   |-- reference_ingest/
|   |-- bar_builder/
|   |-- scanner_engine/
|   `-- notification_router/
|-- packages/
|   |-- event_schemas/
|   `-- scanner_definitions/
|-- migrations/
|-- fixtures/
|   |-- market_replay/
|   `-- expected_events/
|-- tests/
|   |-- unit/
|   |-- replay/
|   `-- load/
|-- config/
|   |-- scanners/
|   `-- sessions/
|-- infra/
|   `-- docker-compose.yml
|-- docs/
|   |-- data-contract.md
|   |-- licensing-register.md
|   `-- outage-runbook.md
|-- .env.example
`-- README.md
```

## 27. Build prompt for Claude or another coding agent

```text
Use SCANNER_ALERT_PLATFORM_IMPLEMENTATION_SPEC.md as the authoritative product
and architecture specification. Build only Phase 1 first: a replay-first backend.

Before coding, produce:
1. assumptions and unresolved decisions;
2. normalized event and symbol-snapshot schemas;
3. repository tree;
4. database migration plan;
5. unit and golden-replay test plan.

Default stack: Python 3.12, FastAPI, asyncio, PostgreSQL, Redis and Docker Compose.
Keep provider adapters behind interfaces. Do not require a paid API key for tests;
use deterministic local fixtures. Every scanner output must include raw values,
pass/fail reasons and a definition version. Never present independent formulas as
Warrior's proprietary settings.

Implement Phase 1, run all tests, and stop for review before starting live data,
notifications, frontend, broker integration or paid-provider setup.
```

## 28. Final product principle

The platform should make the reasoning more transparent than the product it replaces:

```text
Why did the ticker appear?
Which data and formula were used?
How fresh is the information?
Has this logical event already alerted?
What would invalidate the candidate?
Can the result be reproduced in replay?
```

If the system cannot answer those questions, it is not ready for live decision support.
