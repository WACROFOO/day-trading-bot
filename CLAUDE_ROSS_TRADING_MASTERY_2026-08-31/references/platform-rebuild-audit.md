# Clean-room audit and build specification: scanner-first trading workstation

Prepared August 28, 2026.

## 1. Executive decision

Build a scanner-first decision workstation, not a clone of Warrior Trading source code, private formulas, branding or protected services. The useful workflow can be reproduced cleanly with:

1. a licensed real-time US-equities feed;
2. an event-driven feature and scanner engine;
3. a shared selected-symbol state;
4. two synchronized charts;
5. a catalyst/news panel;
6. a separately licensed Level 2 order book plus Time & Sales;
7. saved layouts, alert history and deterministic replay.

The defining interaction should be:

> Click a scanner row once → both charts, quote header, news, catalyst flags, Level 2 and Time & Sales all switch immediately to the same instrument.

The fastest sensible private MVP is React/TypeScript, TradingView Lightweight Charts, a SIP-capable L1 provider, a streaming news provider, PostgreSQL/TimescaleDB, Redis and a small event bus. Add true Level 2 after confirming exchange licensing and data cost.

## 2. Clean-room and legal boundary

### In scope

- Reproduce publicly observable product behavior with original code.
- Use the visible field vocabulary and scanner taxonomy in platform-filter-inventory.md.
- Implement original UI components, data contracts and transparent rules.
- Calibrate rules against results the user is legitimately allowed to view.

### Out of scope

- Copying Warrior JavaScript, CSS, imagery, private API responses or server rules.
- Extracting credentials, bearer tokens, signed links or private configuration.
- Bypassing authorization or administrator-only surfaces.
- Redistributing TradingView restricted libraries.
- Redistributing exchange data or article bodies without permission.
- Using Warrior, Ross Cameron or TradingView trademarks as product branding.

### Market-data compliance gate

Before development, classify the application as personal/nonprofessional display, internal firm display, non-display algorithmic use, external redistribution, or broker-connected order entry. These categories can have different agreements and fees.

Scanner computation is commonly non-display use. Level 2 shown on screen is display use. External users may require per-user entitlements and a distribution agreement. Obtain written confirmation from every provider. Do not assume a consumer subscription permits application development.

## 3. Observed product model

The prior complete live audit established:

- 29 scanner widgets;
- list scanners that publish ranked universes;
- alert scanners that append timestamped events;
- sortable tables with linked tickers;
- alert strategy names and audio selection;
- charts and quote panels that react to symbol selection;
- recent-news flame indicators;
- Scanner History by scanner and date;
- dockable layouts, panel pop-outs and global alert volume;
- online/offline status and scanner-feed health.

The complete field inventory is in platform-filter-inventory.md. The confirmed-versus-proprietary boundary is in source-analysis.md.

Interpretation rules:

- A displayed column is not automatically an inclusion filter.
- A flame means recent news exists; it is not a Ross-compliance score.
- Alert strategy checkboxes control audio, not production rules.
- A scanner match is a candidate, not an entry.
- Hidden thresholds must become editable, versioned formulas.

## 4. Target user experience

### Primary layout

~~~text
┌─────────────────────┬──────────────────────────────┬──────────────────────┐
│ Scanner stack       │ Chart A: execution           │ Catalyst / quote     │
│ Top Gainers         │ default 1 minute             │ headline + age       │
│ Five Pillars        ├──────────────────────────────┤ risk tags / float    │
│ Running Up          │ Chart B: context             ├──────────────────────┤
│ HOD Momentum        │ default 5 minute             │ Level 2              │
│ Alerts / history    │ toggle: daily                ├──────────────────────┤
│                     │                              │ Time & Sales         │
└─────────────────────┴──────────────────────────────┴──────────────────────┘
~~~

Recommended desktop proportions:

- scanners: 28–34%;
- two charts: 44–54%;
- catalyst, Level 2 and tape: 18–24%.

### Selection workflow

1. Click or keyboard-select a scanner row.
2. Publish a global selectedInstrument event.
3. Switch both charts while retaining independent intervals.
4. Render quote data from hot cache.
5. Load cached news and subscribe to fresh headlines.
6. Unsubscribe Level 2 from the previous symbol and subscribe to the new one.
7. Switch Time & Sales.
8. Keep the selected row highlighted across rank changes.

Target perceived switch time is below 300 ms when quote/news metadata is cached. Depth may show loading until a fresh snapshot arrives.

### Keyboard workflow

- J/K or arrows: previous/next row.
- Enter: lock symbol.
- 1, 5, D: chart interval.
- N: news.
- L: Level 2.
- Space: freeze visible row order while ingestion continues.
- Esc: return focus to scanner.

Freeze-order mode is important because moving live rankings otherwise make selection difficult.

## 5. Charting decision

### Option A — recommended private MVP: TradingView Lightweight Charts

Use Lightweight Charts v5 for speed and control.

Advantages:

- open-source client library;
- pane support in v5;
- direct symbol and interval control;
- easy selected-symbol synchronization;
- custom entry, stop and target bands;
- no Broker API required for a separate custom DOM.

Limitations:

- not the full TradingView drawing/indicator experience;
- indicators and drawing persistence must be implemented;
- TradingView attribution is required.

Official documentation: https://tradingview.github.io/lightweight-charts/

### Option B — licensed Advanced Charts or Trading Platform

Use when the full TradingView interface justifies licensing and integration.

- The library contains no market data.
- Implement the Datafeed API for symbols, history and real-time bars.
- The package is private and non-redistributable.
- Trading Platform supports synchronized multi-chart layouts.
- Built-in DOM requires quote methods, subscribeDepth, unsubscribeDepth, Level 2 flags and Broker API work.

Official documentation:

- https://www.tradingview.com/charting-library-docs/latest/connecting_data/datafeed-api/
- https://www.tradingview.com/charting-library-docs/latest/trading_terminal
- https://www.tradingview.com/charting-library-docs/latest/trading_terminal/depth-of-market/

### Option C — free Advanced Chart embeds

Two free TradingView iframe widgets can prove the visual concept, but they are too constrained for a tightly synchronized custom scanner, news and Level 2 workstation.

Official documentation: https://www.tradingview.com/widget-docs/widgets/charts/advanced-chart/

### Two-chart defaults

- Chart A: 1-minute, extended hours, VWAP, EMA 9, EMA 20 and volume.
- Chart B: 5-minute, extended hours, VWAP, EMA 9, EMA 20 and volume.
- One-click Chart B toggle: daily with 20/50/200-day averages.
- Optional later Chart A: 10-second bars.
- Symbol synced by default; interval and crosshair sync independently switchable.

## 6. Market-data sourcing

### L1 trades and quotes

A free single-exchange feed is insufficient for a broad US momentum scanner. Use consolidated SIP or equivalent licensed market-wide data.

Alpaca documents separate IEX and SIP WebSocket feeds. IEX is one venue; SIP is consolidated. Reference: https://docs.alpaca.markets/us/docs/real-time-stock-pricing-data

Required events:

- trades with price, size, exchange, conditions and precise time;
- NBBO quote updates;
- market status and halts;
- corrections and cancel/error messages;
- bars or enough trades to build them;
- symbol definitions and corporate actions.

### Level 2

Level 2 is separate from SIP top-of-book. Nasdaq TotalView supplies Nasdaq depth. Databento exposes normalized L1/L2/L3 schemas including Nasdaq TotalView-ITCH.

References:

- https://www.nasdaqtrader.com/content/productsservices/dataproducts/totalview/totalviewfactsheet.pdf
- https://databento.com/docs/getting-started/live
- https://databento.com/docs/knowledge-base/datasets

Nasdaq TotalView is the Nasdaq book, not all US venues. Consolidated depth can require NYSE OpenBook/ArcaBook, Cboe depth, multiple licenses and an aggregation policy.

### Float and short interest

Store source, as-of date and quality flags. Outstanding shares are not float.

Possible sources:

- Intrinio public float and short interest;
- SEC EDGAR submissions/XBRL as fallback;
- manual verified overrides for recent IPOs, splits and microcaps.

References:

- https://help.intrinio.com/public-float
- https://docs.intrinio.com/documentation/web_api/get_security_short_interest_v2
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces

## 7. News and catalyst system

Use a licensed streaming source for low-latency catalysts. Benzinga documents WebSocket streams for breaking news and financial events.

References:

- https://docs.benzinga.com/ws-reference/overview
- https://docs.benzinga.com/services/overview

### News record

~~~json
{
  "id": "provider-event-id",
  "symbols": ["ABCD"],
  "publishedAt": "2026-08-28T12:34:56.000Z",
  "receivedAt": "2026-08-28T12:34:56.120Z",
  "source": "licensed-provider",
  "headline": "...",
  "summary": "...",
  "url": "https://publisher.example/article",
  "categories": ["FDA", "PRESS_RELEASE"],
  "sentiment": "positive",
  "materiality": 0.82,
  "isCorrection": false,
  "dedupeKey": "hash"
}
~~~

Do not store or redistribute full article bodies unless licensed.

### Flame semantics

- red: newest qualifying headline is 0–2 hours old;
- orange: 2–12 hours;
- yellow: 12–24 hours;
- none: no qualifying headline within 24 hours.

The flame represents recency only. Use separate badges for catalyst type and risk.

### Catalyst categories

- earnings and guidance;
- FDA, clinical and regulatory;
- contracts, orders and customers;
- merger/acquisition;
- financing, shelf, ATM or offering;
- reverse split/corporate action;
- IPO, uplist, delist or compliance;
- analyst action;
- SEC filing;
- rumor/social-only;
- no material catalyst.

Risk tags:

- dilution/offering;
- reverse split;
- going concern;
- bankruptcy/restructuring;
- exchange non-compliance;
- warrant-heavy structure;
- stale headline;
- unverified source.

Use deterministic source/form/keyword rules first. An LLM may add classification but must never invent a catalyst without a source event.

## 8. Scanner engine

Implement two primitives:

1. Top list: publish a sorted snapshot of passing symbols.
2. Alert strategy: emit when state crosses false to true, with cooldown and re-arm.

Recommended cadence:

- feature updates: event-driven;
- alert evaluation: event-driven or 100–250 ms micro-batches;
- browser alert: immediate;
- ranked-list diffs: every second;
- optional compatibility snapshot: every 30 seconds.

### Universe rules

Each scanner explicitly defines:

- exchanges/MICs;
- common/ADR/ETF/warrant/unit/preferred handling;
- price and dollar-volume floors;
- maximum spread;
- allowed sessions;
- halted and stale-symbol handling;
- corporate-action adjustment;
- missing-float policy.

### Core formulas

~~~text
change_close_pct = 100 × (last / previous_regular_close - 1)
gap_pct = 100 × (premarket_last / previous_regular_close - 1)
change_open_pct = 100 × (last / regular_session_open - 1)
position_in_range_pct =
  100 × (last - session_low) / max(session_high - session_low, tick_size)
dollar_volume = sum(trade_price × trade_size)
move_5m_pct = 100 × (last / price_5_minutes_ago - 1)
move_10m_pct = 100 × (last / price_10_minutes_ago - 1)
hod_break =
  current_high > highest_session_high_before_current_event
atr_rate_pct = 100 × ATR_N / last
~~~

Expose HOD modes:

- intrabar: fastest, can trigger on a print;
- confirmed: one-minute close above prior HOD.

Time-normalized daily RVOL:

~~~text
daily_rvol =
  cumulative_volume_today_at_t
  / median(cumulative_volume_at_same_session_time over N comparable days)
~~~

Five-minute RVOL:

~~~text
rvol_5m =
  current_5m_volume
  / median(5m_volume_at_same_session_bucket over N comparable days)
~~~

Use separate premarket, regular and after-hours baselines. Version every formula.

### Rule DSL

~~~yaml
id: five_pillars_technical
version: 1
type: toplist
universe: us_equity_momentum
sessions: [premarket, regular]
where:
  all:
    - field: last
      op: between
      value: [2, 20]
    - field: change_close_pct
      op: gte
      value: 10
    - field: daily_rvol
      op: gte
      value: 5
    - field: float_shares
      op: lte
      value: 20000000
rank:
  field: daily_rvol
  direction: desc
limit: 100
newsPolicy: manual_confirmation
~~~

Every rule includes owner, timestamps, formula version, universe version, sessions, enabled state, cooldown/re-arm, output columns, alert settings and change log.

### Initial scanners

1. Top Gainers
2. Top Gappers
3. Low Float Top Gainers
4. Five Pillars Technical
5. Five Pillars HOD
6. Running Up
7. HOD Momentum
8. Squeeze 5% in 5 minutes
9. Squeeze 10% in 10 minutes
10. 52-week Breakout
11. Top Relative Volume
12. Top Volume 5 Minutes
13. Top Change Since Open
14. Halt

The full 29-widget backlog and exact visible columns are in platform-filter-inventory.md.

Confirmed public starting values:

- Five Pillars: $2–$20, gain at least 10%, daily RVOL around 5x, float below 20M;
- news is manual, not enforced by the technical scanner;
- squeeze: 5%/5m and 10%/10m;
- Penny HOD below $2;
- Penny Top Gappers below $5;
- recent IPO/uplist about 90 days;
- reverse split about 30 days and greater than 10:1.

Any additional thresholds are independent approximations and must be labeled.

## 9. Level 2 and Time & Sales

### Depth record

~~~json
{
  "symbol": "ABCD",
  "venue": "XNAS",
  "sequence": 918273645,
  "eventTime": "2026-08-28T14:31:22.123456789Z",
  "snapshot": false,
  "bids": [{"price": 4.21, "size": 12800, "orders": 7}],
  "asks": [{"price": 4.22, "size": 9400, "orders": 5}]
}
~~~

Book-builder requirements:

- load snapshot before deltas;
- enforce sequence numbers;
- detect gaps and rebuild;
- aggregate order-level data into price levels;
- retain venue/order count where licensed;
- expire state on disconnect/status change;
- process cancel, replace, execution and cross events.

DOM fields:

- price, displayed shares, cumulative shares;
- order count and venue/MMID where permitted;
- heat bar, best bid/ask, spread and last-trade marker;
- 10–20 levels per side.

Optional imbalance:

~~~text
top_n_imbalance =
  (sum_bid_size_n - sum_ask_size_n)
  / max(sum_bid_size_n + sum_ask_size_n, 1)
~~~

Displayed orders are not guaranteed support/resistance and can be cancelled.

Time & Sales fields:

- event time;
- price and size;
- exchange and conditions;
- relative-to-NBBO classification;
- odd-lot indicator;
- session volume.

Account for delayed quotes, crossed markets and trade conditions before labeling aggressor side.

## 10. Application architecture

~~~mermaid
flowchart LR
    A[L1 trades/quotes] --> G[Feed gateways]
    B[Depth feeds] --> G
    C[News/filings] --> N[News normalizer]
    D[Fundamentals/actions] --> F[Reference data]
    G --> E[Event bus]
    E --> R[Bars/features]
    E --> O[Order books]
    R --> S[Scanners/rankings]
    N --> K[Catalyst classifier]
    F --> R
    S --> W[API/WebSocket]
    R --> W
    O --> W
    K --> W
    W --> U[React workstation]
~~~

Services:

1. Instrument and symbol service.
2. L1 gateway.
3. Depth gateway.
4. Bar service.
5. Feature service.
6. Scanner service.
7. News service.
8. Catalyst service.
9. Reference-data service.
10. History/replay service.
11. API/WebSocket gateway.
12. Workspace/layout service.

Suggested MVP stack:

- React, TypeScript, Vite or Next.js;
- Lightweight Charts v5;
- CSS Grid plus a docking library;
- Node.js/TypeScript or Go backend;
- NATS JetStream, Redpanda or Redis Streams;
- Redis hot state;
- PostgreSQL plus TimescaleDB;
- object storage with compressed columnar files;
- OpenTelemetry, Prometheus and Grafana;
- Docker Compose initially.

Do not introduce Kubernetes for a single-user MVP.
+
## 11. Canonical event contracts

### Instrument

~~~json
{
  "instrumentId": "figi-or-internal-id",
  "symbol": "ABCD",
  "mic": "XNAS",
  "type": "COMMON_STOCK",
  "currency": "USD",
  "timezone": "America/New_York",
  "tickSize": 0.01,
  "sessions": ["premarket", "regular", "afterhours"]
}
~~~

### Quote

~~~json
{
  "instrumentId": "...",
  "eventTime": "...",
  "receivedTime": "...",
  "bid": 4.21,
  "bidSize": 1400,
  "ask": 4.22,
  "askSize": 900,
  "bidVenue": "XNAS",
  "askVenue": "ARCX",
  "sequence": 12345
}
~~~

### Trade

~~~json
{
  "instrumentId": "...",
  "eventTime": "...",
  "price": 4.22,
  "size": 500,
  "venue": "XNAS",
  "conditions": ["REGULAR"],
  "tradeId": "...",
  "sequence": 12346
}
~~~

### Bar

~~~json
{
  "instrumentId": "...",
  "interval": "1m",
  "startTime": "...",
  "open": 4.10,
  "high": 4.25,
  "low": 4.08,
  "close": 4.22,
  "volume": 582100,
  "trades": 3912,
  "vwap": 4.17,
  "session": "regular",
  "final": false,
  "revision": 3
}
~~~

### Scanner result

~~~json
{
  "scannerId": "hod_momentum",
  "scannerVersion": 7,
  "instrumentId": "...",
  "symbol": "ABCD",
  "eventTime": "...",
  "state": "ENTERED",
  "strategy": "low_float_high_rvol",
  "score": 87.4,
  "fields": {
    "last": 4.22,
    "changeClosePct": 34.8,
    "floatShares": 8200000,
    "dailyRvol": 8.7,
    "rvol5m": 11.2,
    "gapPct": 18.4
  },
  "news": {"ageMinutes": 37, "flame": "RED"},
  "formulaVersion": "features-3.2.0",
  "universeVersion": "us-equities-2026-08-28"
}
~~~

## 12. API surface

### REST

~~~text
GET  /api/v1/instruments/search?q=
GET  /api/v1/instruments/{id}
GET  /api/v1/instruments/{id}/fundamentals
GET  /api/v1/instruments/{id}/bars?interval=1m&from=&to=
GET  /api/v1/instruments/{id}/news?from=&limit=
GET  /api/v1/scanners
GET  /api/v1/scanners/{id}
GET  /api/v1/scanners/{id}/snapshot
GET  /api/v1/scanners/{id}/history?date=
POST /api/v1/scanners
PUT  /api/v1/scanners/{id}
POST /api/v1/workspaces
PUT  /api/v1/workspaces/{id}
GET  /api/v1/workspaces/{id}
~~~

### WebSocket commands

~~~json
{"op":"subscribe","channels":["scanner:top_gainers","scanner:running_up"]}
{"op":"select","instrumentId":"..."}
{"op":"subscribe","channels":["quote:...","bars:...:1m","bars:...:5m","news:...","depth:...","trades:..."]}
{"op":"unsubscribe","channels":["depth:previous-id","trades:previous-id"]}
~~~

Requirements:

- heartbeat and reconnect;
- sequence-based resume where possible;
- snapshot-plus-delta;
- bounded queues and backpressure;
- per-channel authorization;
- deduplication by event ID;
- compressed frames for depth;
- vendor credentials never sent to browser.

## 13. Storage and retention

### PostgreSQL/TimescaleDB

Persist:

- instrument master and symbol history;
- minute/second bars;
- feature snapshots at alert time;
- scanner definitions and versions;
- alerts and list snapshots;
- headline metadata and catalyst labels;
- fundamental values with source/as-of date;
- layouts and preferences.

### Redis

Maintain:

- latest quote/trade;
- current session OHLCV;
- rolling feature windows;
- scanner sorted sets;
- news cache;
- subscription registry.

### Object storage

Archive normalized trades/depth only when the license permits retention. Partition by date, venue and symbol.

## 14. Reliability and latency targets

These are proposed targets, not observed Warrior measurements.

| Flow | Target |
|---|---:|
| L1 received → feature updated, p95 | <100 ms |
| Qualifying event → browser, p95 | <500 ms |
| Row click → cached quote, p95 | <150 ms |
| Row click → both charts, p95 | <300 ms |
| Depth delta → DOM, p95 | <100 ms |
| Headline → flame/catalyst, p95 | <1 s |

Health indicators:

- feed connection and last-event age;
- scanner engine lag;
- dropped/out-of-order messages;
- depth sequence gaps;
- news lag;
- stale fundamental count;
- browser queue depth.

Fail closed: stale scanner inputs show STALE/OFFLINE instead of old results marked live.

## 15. Testing strategy

### Deterministic tests

- feature unit tests;
- session boundaries at 4:00, 9:30, 16:00 and 20:00 ET;
- DST and holidays;
- split/reverse-split adjustment;
- out-of-order corrections;
- missing/stale float;
- DSL parsing and migrations;
- cooldown and re-arm;
- depth snapshot/delta and gap recovery.

### Market replay

Replay recorded events through production feature/scanner code under a controlled event clock.

Report:

- candidates and alerts by session;
- precision/recall against labeled references;
- false positives/negatives;
- feature distributions at alert;
- latency and duplicates.

### Load tests

- full-universe L1;
- opening-bell burst;
- many scanner subscriptions;
- repeated symbol switching;
- selected-symbol depth;
- reconnect storms;
- news bursts and dedupe.

## 16. Security

- Vendor secrets only in a server-side secret manager.
- Short-lived browser WebSocket tokens.
- Channel authorization and subscription limits.
- Audit log for rule changes.
- External schema validation.
- REST/WebSocket rate limits.
- Encryption at rest.
- Strict Content Security Policy.
- Never log authorization headers/tokens.
- Isolate future broker credentials from market-data services.

## 17. Delivery plan

### Phase 0 — contracts and spike, 1–2 weeks

- classify data use;
- choose L1, news, fundamentals and depth vendors;
- confirm retention/display rights;
- test throughput and coverage;
- prove two charts and selected-symbol flow.

Exit: one symbol has live quote, two charts and news.

### Phase 1 — scanner MVP, 3–5 weeks

- instrument master;
- L1 and bars;
- feature engine;
- first seven scanners;
- tables and selected-symbol bus;
- two charts;
- quote/news panels;
- feed health.

Exit: scanner click switches charts and news reliably.

### Phase 2 — catalyst, history and UX, 2–4 weeks

- catalyst/risk tags;
- flame recency;
- alert consolidation;
- history by date;
- saved layouts;
- sounds and notifications;
- keyboard navigation and freeze-order mode.

Exit: full discovery workflow works without another scanner.

### Phase 3 — Level 2 and tape, 3–5 weeks

- licensed depth gateway;
- book builder;
- DOM, imbalance and Time & Sales;
- sequence-gap monitoring;
- load/disconnect tests.

Exit: selected symbol has a verified gap-free book and tape.

### Phase 4 — continuing

- remaining scanner families;
- replay calibration;
- advanced alerts;
- optional licensed TradingView migration;
- optional broker integration after separate review.

### Effort

A capable two-person frontend/full-stack plus streaming/data team needs roughly 9–16 weeks after data contracts. A solo build is more realistically 4–6 months. Provider onboarding and exchange approval can dominate timing. These are engineering estimates, not vendor quotes.

## 18. Acceptance criteria

MVP:

- documented, versioned scanner formulas;
- visible stale-feed state;
- row selection updates both charts, quote and news;
- separate chart intervals persist;
- correct premarket/regular/after-hours sessions;
- flame derives only from headline age;
- float/short interest show source and date;
- history reproduces alerts;
- disconnects do not create false alerts;
- no vendor secret in client code;
- data use complies with display/non-display/retention rights.

Level 2 additionally:

- snapshot before deltas;
- sequence-gap recovery;
- correct bid/ask sorting;
- venue labels where licensed;
- DOM and tape switch with symbol;
- latency measured under opening load.

## 19. Build-versus-buy recommendation

Recommended initial combination:

- charts: Lightweight Charts v5;
- L1: licensed SIP WebSocket;
- news: Benzinga streaming or equivalent;
- float/short interest: Intrinio plus SEC fallback and overrides;
- Level 2: Databento Nasdaq TotalView-ITCH after licensing;
- frontend: React/TypeScript;
- backend: TypeScript/Node.js or Go;
- storage: Redis + PostgreSQL/TimescaleDB + object storage;
- deployment: Docker Compose on one secured server.

Consider TradingView Trading Platform when:

- the full drawing/indicator experience is essential;
- built-in multi-chart sync/DOM is desired;
- the team can implement Datafeed and Broker APIs;
- TradingView grants the license;
- data providers permit intended display/distribution.

## 20. Immediate backlog

1. Write data-use classification.
2. Obtain trial keys and contractual answers.
3. Define canonical instrument IDs/symbol mapping.
4. Build L1 normalizer and session calendar.
5. Build bars with replay tests.
6. Implement feature formulas.
7. Implement DSL and version store.
8. Build Top Gainers and Five Pillars first.
9. Build selectedInstrument event bus.
10. Render two Lightweight Charts.
11. Add news and flame age.
12. Add catalyst/risk tags.
13. Add history and workspace save.
14. Add Level 2 only after licensing.

## 21. Official source index

- TradingView Datafeed API: https://www.tradingview.com/charting-library-docs/latest/connecting_data/datafeed-api/
- TradingView subscriptions: https://www.tradingview.com/charting-library-docs/latest/connecting_data/datafeed-api/datafeed-subscriptions/
- TradingView Trading Platform: https://www.tradingview.com/charting-library-docs/latest/trading_terminal
- TradingView DOM: https://www.tradingview.com/charting-library-docs/latest/trading_terminal/depth-of-market/
- Lightweight Charts: https://tradingview.github.io/lightweight-charts/
- Advanced Chart widget: https://www.tradingview.com/widget-docs/widgets/charts/advanced-chart/
- Alpaca real-time stocks: https://docs.alpaca.markets/us/docs/real-time-stock-pricing-data
- Nasdaq TotalView: https://www.nasdaqtrader.com/content/productsservices/dataproducts/totalview/totalviewfactsheet.pdf
- Databento live schemas: https://databento.com/docs/getting-started/live
- Benzinga streaming overview: https://docs.benzinga.com/ws-reference/overview
- Intrinio public float: https://help.intrinio.com/public-float
- Intrinio short interest: https://docs.intrinio.com/documentation/web_api/get_security_short_interest_v2
- SEC EDGAR APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces

## 22. Conclusion

Design around one-click context assembly: the scanner finds a symbol and every decision surface is ready. The difficult work is not panel rendering; it is universe-wide real-time computation, symbol mapping, exchange licensing, depth-book correctness, data quality and replayable logic.

Start with L1 scanners, two charts and catalyst metadata. Add Level 2 after the workflow proves useful and licensing is settled. Keep every formula visible, editable and versioned so the product improves through evidence rather than opaque imitation.
