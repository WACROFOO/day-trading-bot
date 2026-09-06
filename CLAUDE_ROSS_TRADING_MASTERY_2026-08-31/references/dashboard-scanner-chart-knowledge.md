# Focused Knowledge: Momentum Dashboard, Scanner Tiles and TradingView Charts

> Prepared for Claude — 1 September 2026  
> Scope: the captured Warrior Day Trade Dash / Warrior Pro-style workstation behavior and a clean-room specification for rebuilding its scanner-and-chart workflow.

## 1. How Claude should use this file

Treat this file as the primary context when designing or implementing the dashboard UI. It is intentionally narrower than the full trading-strategy and backend specifications.

Use these evidence labels:

- **Confirmed visible**: directly observed in the authenticated platform or official support material before access ended.
- **Confirmed course**: explicitly taught in the captured Preview course.
- **Clean-room design**: recommended behavior for the new application.
- **Approximation**: independently selected scanner formula or threshold.
- **Unknown**: proprietary Warrior production logic that was not exposed.

Do not claim that a Clean-room design or Approximation is Warrior's source code or exact formula.

Load additional references only when needed:

- Exact formulas, APIs, notification architecture and database schema: `scanner-alert-platform-spec.md`
- Exact 29-widget field and branch inventory: `platform-filter-inventory.md`
- Scanner operation, flame colors, history and timing: `scanner-guide.md`
- Broader reconstruction, data feeds, Level 2 and licensing: `platform-rebuild-audit.md`
- Trading strategy and first-pullback rules: `strategy-playbook.md`
- Existing Pine approximation: `../assets/ross_style_momentum_scanner.pine`

## 2. Product objective

Build a scanner-first decision dashboard where one ticker selection assembles all relevant context immediately:

```text
scanner candidate
-> selected ticker
-> execution chart
-> context chart
-> headline and flame
-> catalyst/risk flags
-> Level 2 and tape later
-> entry/stop/target planning
```

The defining interaction is:

> Click one scanner row and both charts, quote header, news and all symbol-dependent panels switch to the same instrument while preserving their own timeframes.

The dashboard is for discovery and planning. A scanner match is never an automatic trade entry.

## 3. What was confirmed about the original dashboard

The prior authenticated walkthrough established these visible behaviors:

- a scanner menu exposing 29 scanner widgets;
- dockable scanner panels/tiles;
- list scanners presenting ranked current universes;
- alert scanners appending timestamped qualifying events;
- sortable columns;
- ticker cells linked to quote/chart/news context;
- recent-news flame icons;
- per-alert-tile audio configuration;
- selectable alert branches inside some alert tiles;
- grouped/consolidated alerts that can be expanded;
- global alert-volume control;
- green/red scanner-data health state;
- individual tile online/offline status;
- Scanner History by scanner and date;
- layout saving and panel pop-out/multi-window behavior;
- chart and quote panels reacting to the selected ticker.

### Important interpretation boundaries

- A visible column is not automatically an inclusion filter.
- An alert branch checkbox controls the user's sound selection; it does not reveal or modify the hidden server rule.
- A flame represents news recency, not overall Ross-criteria compliance.
- Hitting HOD alone was insufficient to produce every HOD Momentum alert.
- Exact production float bands, RVOL normalization and most momentum thresholds were not visible.

## 4. Recommended clean-room dashboard layout

```text
┌────────────────────────┬────────────────────────────────┬──────────────────────┐
│ SCANNER DOCK           │ CHART A — EXECUTION            │ SYMBOL CONTEXT       │
│                        │ default: 1 minute               │ quote / spread       │
│ Five Pillars Scan      │ extended hours                  │ float / short interest│
│ Top Gappers            │ VWAP + EMA 9/20 + volume       │ catalyst / risk tags │
│ Top Gainers            ├────────────────────────────────┤ headline + flame     │
│ Running Up             │ CHART B — CONTEXT              ├──────────────────────┤
│ HOD Momentum           │ default: 5 minute               │ LEVEL 2 — LATER      │
│ Top RVOL / 5m Volume   │ toggle: daily                   ├──────────────────────┤
│ Halt / Alert History   │ levels + planning bands         │ TIME & SALES — LATER │
└────────────────────────┴────────────────────────────────┴──────────────────────┘
```

Recommended desktop width allocation:

- scanner dock: 28–34%;
- chart stack: 44–54%;
- context/depth/tape: 18–24%.

The user should be able to resize panels and save the resulting workspace.

## 5. Component hierarchy

```text
DashboardShell
├── GlobalHeader
│   ├── MarketClockET
│   ├── FeedHealthIndicator
│   ├── SelectedSymbolHeader
│   └── GlobalAlertVolume
├── ScannerDock
│   ├── ScannerTile[]
│   └── ScannerHistoryTile
├── ChartWorkspace
│   ├── ExecutionChart1m
│   ├── ContextChart5mOrDaily
│   └── RiskBandController
├── SymbolContextDock
│   ├── QuoteCard
│   ├── NewsCatalystCard
│   ├── FundamentalsRiskCard
│   ├── Level2TileFuture
│   └── TimeSalesTileFuture
├── AlertCenter
│   ├── ConsolidatedAlertTimeline
│   └── NotificationSettings
└── WorkspaceManager
    ├── SaveLayout
    ├── RestoreLayout
    └── PopOutPanel
```

## 6. Shared selected-symbol state

### Central rule

There must be exactly one dashboard-level selected symbol. Scanner tiles may display different lists, but all detail panels subscribe to the same selection.

```ts
type SelectedInstrument = {
  instrumentId: string;
  symbol: string;
  exchange: string;
  selectedAt: string;
  source: {
    scannerId: string;
    eventId?: string;
    rowRank?: number;
  };
  locked: boolean;
};
```

### Selection transaction

When the user selects a row:

1. publish `selectedInstrument.changed`;
2. highlight the ticker in every tile where visible;
3. preserve the selection even if list rank changes;
4. update the quote card immediately from hot cache;
5. switch Chart A while preserving its 1-minute interval;
6. switch Chart B while preserving its 5-minute/daily interval;
7. load cached news and subscribe to new headlines;
8. switch float/fundamental context;
9. unsubscribe previous depth/tape streams and subscribe to the new symbol later;
10. update the browser URL for deep linking.

Do not allow each chart or tile to maintain an independent ticker accidentally.

### Row-order freeze

Live rankings can move while the user is clicking. Provide a temporary `Freeze visible order` action:

- incoming values continue updating;
- row order remains stable;
- new candidates can appear in a small pending area;
- unfreezing applies the latest ranking.

## 7. Scanner tile architectures

### 7.1 Ranked list tile

**Confirmed visible behavior:** list scanners show a current ranked universe and refresh approximately every 30 seconds in the captured product. They do not expose scanner audio.

Required tile regions:

```text
┌─────────────────────────────────────────────────────────┐
│ Title   LIVE/OFFLINE   updated 08:14:30   ⋮  pop-out   │
├─────────────────────────────────────────────────────────┤
│ sortable column headers                                 │
├─────────────────────────────────────────────────────────┤
│ rank | symbol/flame | price | change | RVOL | float ...│
│ ...                                                     │
└─────────────────────────────────────────────────────────┘
```

Clean-room improvements:

- show refresh age;
- show formula/version tooltip;
- expand a row to show pass/fail reasons;
- retain selected-row highlighting across rank changes;
- display `STALE` rather than leaving old data looking live.

### 7.2 Alert tile

**Confirmed visible behavior:** alert scanners update roughly every second, append timestamped events and may play optional chimes.

Required tile regions:

```text
┌──────────────────────────────────────────────────────────┐
│ Title  LIVE  bell  branch menu  sound selector  pop-out │
├──────────────────────────────────────────────────────────┤
│ time | symbol/flame | price | strategy | key fields     │
│ latest events first                                      │
└──────────────────────────────────────────────────────────┘
```

Alert settings:

- master enabled/disabled;
- branch-level sound selection where branches exist;
- sound preview;
- volume;
- severity;
- cooldown;
- browser/push/Slack destinations;
- test-notification button.

The branch menu affects notifications only. Scanner qualification rules belong in a separate versioned rule configuration.

### 7.3 Alert consolidation

Multiple same-symbol alerts close together should display as one expandable group:

```text
ABCD  08:04:05  Five Pillars HOD  +2 more alerts  [expand]
```

The expanded group retains all raw events, times and branches. Consolidation is presentation/deduplication, not deletion.

## 8. Scanner tile lifecycle

```text
CLOSED
-> LOADING_DEFINITION
-> CONNECTING
-> LIVE
-> STALE
-> OFFLINE
-> RECONNECTING
-> LIVE
```

Every tile must display:

- current state;
- last server heartbeat;
- last scanner update;
- definition version;
- whether displayed results are live, replayed or historical;
- an error action when stale/offline.

The original dashboard used green/red indicators for data health. The replacement should also provide readable text and age, not color alone.

## 9. Priority scanner tiles for the first dashboard

The original platform exposed 29 widgets, but the first useful dashboard should open only the highest-value tiles.

### Tier 1 — default workspace

| Tile | Architecture | Role in workflow |
|---|---|---|
| Ross-style Five Pillars Scan | Ranked list | Strict technical candidates; verify news manually |
| Top Gappers | Ranked list until 09:30 ET | Premarket watchlist discovery |
| Top Gainers | Ranked list | Current leaders throughout the day |
| Running Up | Alert | Early acceleration that does not require HOD |
| Small Cap HOD Momentum | Alert | New-high momentum with volume/branch qualification |
| Top Relative Volume | Ranked list | Unusual activity ranking |
| Top Volume 5 Minutes | Ranked list | Immediate share-volume leaders |
| Halt | Alert | Halt/resumption awareness |

### Tier 2 — secondary workspace

- Five Pillars HOD Alert;
- Low Float Top Gainers;
- Top Change Since Open;
- Top of Trend;
- Continuation;
- Recent Reverse Splits;
- Recent IPO Top Moving;
- After Hours Top Gainers.

### Tier 3 — specialized layouts

- Reversal;
- Top RSI Trend;
- Large Cap HOD Momentum;
- Large Cap Earnings With Gap;
- Large Cap Top Gappers;
- Large Cap Highest Volume;
- Penny Gappers/Gainers/Losers/HOD.

This tiering is a Clean-room product priority, not a Warrior ranking.

## 10. Exact captured 29-widget inventory

| # | Scanner tile | Type | Primary visible fields / branches |
|---:|---|---|---|
| 1 | Small Cap - High of Day Momentum | Alert | Time, Symbol/News, Price, Volume, Float, daily/5m RVOL, Gap, Change, Short Interest, Strategy; 11 branches |
| 2 | Ross's 5 Pillars Alert | Alert | Same momentum fields; branch `5 Pillar HOD alert` |
| 3 | Ross's 5 Pillars Scan | List | Daily RVOL, Symbol/News, Price, Volume, Float, 5m RVOL, Gap, Change, Short Interest, Position in Range |
| 4 | Ross's Top Gappers | Premarket list | Gap, Symbol/News, Price, Volume, Float, daily/5m RVOL, Change, Short Interest |
| 5 | Top Gappers | Premarket list | Same plus ATR; up to 100 broad leaders |
| 6 | Top Gainers | List | Change from Close, Symbol/News, Price, Volume, Float, RVOL, Gap, Short Interest |
| 7 | Top Losers | List | Same fields ranked downward |
| 8 | Recent Reverse Splits | List | Change, Symbol/News, Price, Volume, Float, daily RVOL, four-week/recent split fields |
| 9 | After Hours Top Gainers | After-hours list | Change from regular close, Gap, Price, Volume, Float, AH Volume, average AH dollar volume, RVOL |
| 10 | Reversal | Alert | Time, Event, Symbol, Price, RSI 2m, consecutive candles 1m/5m, RVOL, 10 branches |
| 11 | Top Relative Volume | List | Daily RVOL, Symbol, Price, Volume, Float, 5m RVOL, Gap, Change |
| 12 | Continuation | List | Two-week movement, Symbol, Price, Volume, Float, RVOL, Change, Gap |
| 13 | Low Float Top Gainers | List | Change, Symbol, Price, Volume, Float, RVOL, Gap |
| 14 | Top Volume 5 Minutes | List | 5m RVOL, Symbol, Price, Volume, Float, daily RVOL, average 5m volume, Gap, Change |
| 15 | Top Change Since Open | List | Change from 09:30 open, Symbol, Price, Volume, Float, RVOL, Gap |
| 16 | Halt | Alert | Time, Symbol, Halt status, 1m/~5m relative range, Price, Volume, Float, RVOL, Gap, Change |
| 17 | Running Up | Alert | Time, Symbol, Price, Volume, Float, RVOL, Gap, Change, Strategy |
| 18 | Running Down | Alert | Same negative-acceleration context |
| 19 | Top of Trend | List | Position in Range, Symbol, Price, Volume, Float, daily RVOL, Range Today, Dollar Volume, Change, Gap |
| 20 | Recent IPO Top Moving | List | Two-week movement, Symbol, Price, Volume, Float, RVOL, Change, Gap |
| 21 | Large Cap - High Of Day Momentum | Alert | Time, Event, Symbol, Price, daily/5m RVOL, 5m Dollar Volume, Short Interest |
| 22 | Large Cap - Earnings With Gap | Premarket list | Gap, Symbol, Price, Volume, Earnings Date, Float, RVOL, Change |
| 23 | Large Cap - Top Gappers | Premarket list | Gap, Symbol, Price, Volume, Float, RVOL, Change, Short Interest |
| 24 | Large Cap Highest Volume | List | Volume, Symbol, Change, Price, Float, Dollar Volume, average/actual 5m volume |
| 25 | Top RSI Trend | List | RSI 1m, Gap, Symbol, Price, Volume, Float, RVOL, Change |
| 26 | Penny - Top Gappers | Premarket list | Gap, Symbol, Price, Volume, Float, RVOL, Change |
| 27 | Penny - Top Gainers | List | Change, Symbol, Price, Volume, Float, RVOL, Gap |
| 28 | Penny - Top Losers | List | Change, Symbol, Price, Volume, Float, RVOL, Gap |
| 29 | Penny High of Day Momentum | Alert | Time, Symbol, Price, Volume, Float, RVOL, Change; 52-week, Squeeze and Volatility Hunter branches |

Premarket gapper lists visibly stopped updating at 09:30 ET.

## 11. Small Cap HOD Momentum branches

Confirmed visible branch names:

1. Former Momo Stock
2. Squeeze Alert - 52wk Breakout
3. Low Float - Med Rel Vol
4. Low Float - High Rel Vol - Price 20+
5. Low Float Volatility Hunter
6. Medium Float - High Rel Vol - Price under 20
7. Low Float - High Rel Vol
8. Medium Float - High Rel Vol - Price 20+
9. Medium Float - Med Rel Vol - Price 20+
10. Squeeze Alert - Up 10% in 10min
11. Squeeze Alert - Up 5% in 5min

Unknown:

- low/medium float boundaries;
- medium/high RVOL thresholds;
- common HOD momentum conditions;
- Volatility Hunter formula;
- Former Momo membership and lookback;
- intrabar versus close-confirmation details.

The replacement should make every one of these independent inputs editable and visibly labeled as Approximation until calibrated.

## 12. Visible field dictionary

| Field | Dashboard meaning | Important caveat |
|---|---|---|
| Symbol / News | Ticker plus news interaction | Flame indicates recency only |
| Price | Latest eligible trade/mark | Show timestamp and stale status |
| Volume | Cumulative applicable-session/day shares | Define extended-hours inclusion |
| Float | Estimated freely tradable shares | Never silently replace with shares outstanding |
| Daily RVOL | Activity relative to provider baseline | Vendor normalization was proprietary |
| 5m RVOL | Recent activity relative to 5m baseline | Formula must be versioned |
| Gap % | Difference versus prior regular close | Premarket and opening reference must be explicit |
| Change From Close % | Current move versus prior close | Distinct from gap and change from open |
| Change Since Open % | Move versus 09:30 regular open | Null before regular open |
| Short Interest | Reported short exposure | Show source and as-of date |
| ATR Rate | Volatility field | Exact captured provider implementation unknown |
| Position in Range | Location inside current session range | Define session high/low |
| Range Today | Current session high-low | Show dollars and/or percentage explicitly |
| Dollar Volume | Sum of trade price × size | Better liquidity context than shares alone |
| Moving 2 Week % | Two-week movement/continuation context | Exact continuation formula unknown |
| RSI 1m/2m | Short-term trend/reversal field | Captured RSI could differ from conventional RSI |
| Relative Range 1m/~5m | Halt/volatility context | Exact denominator unknown |
| Strategy Name | Branch that generated an alert | Branch name is not the full formula |

## 13. News flame and ticker interactions

### Confirmed flame ages

| Indicator | Latest qualifying headline age |
|---|---:|
| Red | 0–2 hours |
| Orange | 2–12 hours |
| Yellow | 12–24 hours |
| None | More than 24 hours or no qualifying headline |

Confirmed interactions:

- hover the flame for a headline preview;
- click the flame to open the latest story;
- click the ticker to populate linked quote/news context.

Captured latency caveat:

- an alert-row flame could appear/change up to several minutes after the original alert;
- list flames refreshed with the list cycle.

Clean-room improvement: show both `publishedAt` and `firstObservedAt`, plus `newsFeedAge`, so missing news and delayed classification are distinguishable.

## 14. Two-chart TradingView workspace

### Chart A — execution

Default configuration:

- interval: 1 minute;
- extended hours enabled;
- ordinary candlesticks;
- volume;
- VWAP;
- EMA 9 and EMA 20;
- HOD and premarket-high lines;
- cyan entry, red stop and green target bands;
- optional later 10-second interval for micro pullbacks.

Chart A owns precise entry and risk structure.

### Chart B — context

Default configuration:

- interval: 5 minutes;
- extended hours enabled;
- volume, VWAP and EMA 9/20;
- one-click daily toggle;
- daily mode shows important moving averages, including 200 EMA;
- recent daily resistance, gaps/windows and whole/half-dollar levels.

Chart B owns context and room-to-target, not the exact trigger.

### Synchronization rules

- ticker synchronized always unless explicitly unlocked;
- intervals independent;
- zoom/range independent by default;
- optional crosshair synchronization;
- drawings stored by `instrumentId + interval`;
- price levels shared across charts when meaningful;
- entry/stop/target plan ID shared across both charts;
- stale or disconnected data visibly blocks a `LIVE` label.

## 15. Charting implementation choices

### Recommended MVP: TradingView Lightweight Charts

Use for the private custom dashboard because it supports direct control over symbol data, real-time updates, panes and custom overlays. Indicators, drawings and persistence must be implemented by the application.

Official documentation: `https://tradingview.github.io/lightweight-charts/`

### Licensed Advanced Charts

Use only if TradingView grants access and the full charting experience justifies the integration. It provides no market data; implement a Datafeed API for symbol search, historical bars and subscriptions. The library is not freely redistributable.

Official datafeed documentation: `https://www.tradingview.com/charting-library-docs/latest/connecting_data/datafeed-api/`

### Free iframe widgets

Suitable only for a visual prototype. They are too constrained for tightly controlled two-chart synchronization, custom scanner state, planning bands and future Level 2 integration.

## 16. Chart data contract

```ts
type ChartBar = {
  instrumentId: string;
  interval: "10s" | "1m" | "5m" | "1D";
  startTime: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  trades?: number;
  vwap?: number;
  session: "premarket" | "regular" | "afterhours";
  final: boolean;
  revision: number;
};
```

The chart subsystem needs:

- historical range loading;
- real-time subscribe/unsubscribe;
- snapshot then deltas;
- bar revisions for late trades/corrections;
- split-adjusted daily history;
- exchange calendar and DST handling;
- extended-hours styling;
- whitespace handling when no eligible trades occur.

## 17. Entry, stop and target planning bands

Confirmed course model for a first pullback:

```text
impulse
-> 2–4 candle pullback with lighter volume
-> first candle to make a new high

entry      = trigger high + configurable buffer
stop       = complete pullback low - configurable buffer
risk/share = entry - stop
target 2R  = entry + 2 × risk/share
```

Planning-band rules:

- freeze levels when the setup is armed;
- store signal bar and complete pullback range;
- do not recalculate the bands with every new candle;
- show HOD and nearby daily resistance separately;
- invalidate when stop is not below entry or room is inadequate;
- bands visualize a plan and do not submit orders.

## 18. Scanner-row contract

```ts
type ScannerRow = {
  scannerId: string;
  scannerVersion: string;
  eventId?: string;
  rank?: number;
  eventTime?: string;
  symbol: string;
  instrumentId: string;
  price: number;
  changeClosePct?: number;
  gapPct?: number;
  volume?: number;
  dollarVolume?: number;
  floatShares?: number;
  floatQuality: "verified" | "proxy" | "unknown";
  dailyRvol?: number;
  rvol5m?: number;
  shortInterest?: number;
  strategy?: string;
  news?: {
    flame: "red" | "orange" | "yellow" | "none";
    ageMinutes?: number;
    headlineId?: string;
  };
  reasons: Array<{
    field: string;
    value: unknown;
    threshold?: unknown;
    passed: boolean;
    evidence: "confirmed" | "approximation";
  }>;
  dataStatus: "live" | "stale" | "historical" | "replay";
};
```

Every row should be explainable without opening backend logs.

## 19. Alert event and notification behavior

```ts
type ScannerAlert = {
  eventId: string;
  idempotencyKey: string;
  symbol: string;
  scannerId: string;
  branch?: string;
  severity: "critical" | "high" | "medium" | "low";
  sourceTime: string;
  observedTime: string;
  definitionVersion: string;
  snapshot: ScannerRow;
  groupedEventIds?: string[];
};
```

Required notification logic:

1. evaluate rising edge;
2. store unique event;
3. deduplicate by idempotency key;
4. consolidate close same-symbol alerts;
5. apply branch/user sound settings;
6. apply cooldown/re-arm;
7. deliver to in-app stream;
8. optionally fan out to browser, push or Slack;
9. record delivery result;
10. never block scanner ingestion while notifying.

## 20. Time-of-day dashboard modes

| ET time | Default tile emphasis | Chart/context behavior |
|---|---|---|
| 04:00–07:00 | Top Gappers, Top Gainers, Five Pillars, news | Extended-hours charts; expect thinner liquidity |
| Around 07:00/08:00/09:00 | Running Up, HOD/Squeeze, news | Rapid symbol switching and catalyst verification |
| 09:30 | Freeze Top Gapper snapshots | Shift attention to HOD, Running Up, Top Gainers and Change Since Open |
| 10:00 onward | RVOL, HOD, continuation; large-cap volume if used | More regular-session structure |
| 15:00–16:00 | Top of Trend and Top Gainers | Power-hour context |
| 16:00–20:00 | After Hours Top Gainers | After-hours baseline and news |

This is a discovery layout, not an instruction to enter trades at those times.

## 21. Keyboard and interaction specification

- `J/K` or arrows: previous/next scanner row;
- `Enter`: lock selected ticker;
- `Space`: freeze/unfreeze current tile ordering;
- `1`: focus/set Chart A to 1 minute;
- `5`: set/focus 5 minute;
- `D`: daily context;
- `N`: open headline/news panel;
- `A`: toggle alert sound for focused tile;
- `H`: open alert history;
- `Esc`: return focus to the originating scanner.

Never execute a broker order from an unmodified single-key shortcut in the dashboard MVP.

## 22. Scanner History

Captured behavior:

- one Scanner History widget at a time;
- select scanner;
- select date with previous/next arrows;
- load full day's data for alert scanners;
- approximately six months of history;
- historical flames relative to the selected date;
- list scanners show their relevant snapshot time.

Clean-room implementation:

- `LIVE`, `HISTORICAL` and `REPLAY` modes must be unmistakable;
- replay uses an event clock and the same production scanner code;
- selecting a historical row loads both charts around the alert timestamp;
- expanding grouped alerts reveals raw constituent events;
- save the exact scanner-definition version used at the time.

## 23. Data and visual-quality rules

- Show timestamp on every price-sensitive tile.
- Mark stale values rather than retaining a green live indicator.
- Show source/as-of date for float and short interest.
- Treat float zero on a new listing as unknown until verified.
- Use color gradients only as comparative encoding; retain numeric values.
- Do not rely on red/green alone for accessibility.
- Preserve selected ticker when its row moves or temporarily leaves a list.
- Do not allow a delayed news flame to rewrite the original alert timestamp.
- Keep list snapshots and alert events conceptually separate.

## 24. Unknown proprietary dashboard logic

Claude must not invent these items:

- exact production Five Pillars momentum qualifiers beyond the confirmed public thresholds;
- low/medium float boundaries for HOD branches;
- medium/high daily or 5-minute RVOL cutoffs;
- Running Up/Down percentage and time windows;
- shared HOD qualification and confirmation timing;
- Volatility Hunter and Former Momo formulas;
- Reversal Bollinger/candle/RSI thresholds;
- exact Top of Trend, Continuation or RSI implementations;
- provider-specific RVOL baselines;
- security-type, spread, liquidity and exchange exclusions;
- internal alert cooldown or grouping durations.

The replacement must expose its own choices as versioned configuration.

## 25. Focused MVP acceptance criteria

- [ ] Dashboard opens the eight Tier-1 tiles.
- [ ] Every tile visibly reports LIVE/STALE/OFFLINE/HISTORY/REPLAY.
- [ ] Clicking any row changes both charts and news context once.
- [ ] Chart A remains 1 minute while Chart B remains 5 minute/daily.
- [ ] Selected ticker remains highlighted across row reordering.
- [ ] A freeze-order mode prevents misclicks during fast ranking changes.
- [ ] Five Pillars fields are displayed separately.
- [ ] Flame colors are based only on news age.
- [ ] List tiles and alert tiles have distinct behavior.
- [ ] Alert branches control notification selection, not scanner definitions.
- [ ] Alert deduplication and consolidation are verified in replay.
- [ ] Top Gappers freezes/records its 09:30 snapshot.
- [ ] Historical alert selection positions charts around the event time.
- [ ] Entry/stop/target bands freeze on an armed setup.
- [ ] Hidden thresholds are labeled Approximation or Unknown.
- [ ] No provider token, news key or webhook secret reaches the browser.

## 26. Focused implementation order

### Step 1 — static workstation shell

- component grid;
- scanner tile component;
- selected-symbol store;
- two chart placeholders;
- news and quote cards;
- keyboard focus model.

### Step 2 — replay data

- deterministic scanner snapshots/events;
- chart bar fixtures;
- news/flame fixtures;
- symbol-selection transaction;
- row-order freeze.

### Step 3 — Tier-1 scanners

- Five Pillars;
- Top Gappers/Gainers;
- Running Up;
- HOD Momentum;
- Top RVOL/5m volume;
- Halt.

### Step 4 — notifications and history

- alert timeline;
- dedupe/consolidation;
- per-tile sounds;
- Scanner History and replay clock.

### Step 5 — live provider adapter

- snapshot plus streaming;
- feed health;
- reconnect/recovery;
- data entitlements and secret isolation.

### Step 6 — planning bands

- first-pullback state machine;
- frozen plan IDs;
- cross-chart levels.

### Step 7 — Level 2 and tape

Add only after licensed data and sequence-gap recovery are proven.

## 27. Focused prompt to give Claude

```text
Use WARRIOR_PRO_DASHBOARD_SCANNERS_CHARTS_KNOWLEDGE.md as the primary product
context for building my private scanner-first trading dashboard.

First read the file completely. Then consult scanner-alert-platform-spec.md for
backend formulas/events/APIs, platform-filter-inventory.md for exact widget
fields and branches, and platform-rebuild-audit.md for data feeds and licensing.

Preserve the evidence labels Confirmed visible, Confirmed course, Clean-room
design, Approximation and Unknown. Do not claim access to Warrior's proprietary
scanner code or hidden thresholds.

The core UX requirement is one selected ticker shared by scanner rows, two
TradingView-style charts and the news/context panels. Chart A is 1 minute for
execution. Chart B is 5 minute with a daily toggle. Scanner list tiles, alert
tiles, news flames, audio settings, consolidation, history and feed health must
follow this focused specification.

Start with Steps 1 and 2 only: create the static workstation shell and a fully
deterministic replay-data prototype. Do not connect a paid live feed, Level 2,
broker or external notifications yet.

Before coding, return:
1. the proposed component tree;
2. the selected-symbol state contract and update sequence;
3. the Tier-1 tile configuration;
4. the chart synchronization design;
5. fixture schemas for scanner rows, alerts, bars and news;
6. acceptance tests mapped to Section 25;
7. unresolved decisions that genuinely block implementation.

Then implement Steps 1 and 2, run the tests, and stop for review.
```

## 28. Final dashboard principle

The original platform's value was not any single tile. Its value was reducing context-switching:

```text
discover -> select -> see both charts -> understand catalyst -> plan risk
```

The replacement succeeds when that path is fast, explainable, replayable and honest about what is known versus approximated.
