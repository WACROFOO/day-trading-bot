# Momentum Workstation — dashboard plan (Steps 1–2)

> Answers the seven pre-coding deliverables in
> `CLAUDE_ROSS_TRADING_MASTERY_2026-08-31/references/dashboard-scanner-chart-knowledge.md` §27.
> Scope: static workstation shell + fully deterministic replay prototype.
> No paid feed, no Level 2, no broker, no external notifications.

Evidence labels are preserved throughout: **Confirmed visible**, **Confirmed course**,
**Clean-room design**, **Approximation**, **Unknown**.

## 1. Component tree

```text
DashboardShell
├── GlobalHeader
│   ├── MarketClockET            session badge + replay clock
│   ├── ReplayTransport          play/pause, speed, scrub, frame counter   [Clean-room]
│   ├── FeedHealthIndicator      state + age text, never colour alone      [Confirmed visible]
│   ├── SelectedSymbolHeader     symbol, last, change, spread, float+quality
│   └── GlobalAlertVolume        master mute + volume                      [Confirmed visible]
├── ScannerDock
│   ├── ScannerTile[]            list | alert architecture, per-tile state
│   │   ├── TileHeader           title, LIVE/STALE/OFFLINE/REPLAY, updated-age, freeze, sound
│   │   ├── TileColumns          sortable headers
│   │   └── TileRow[]            flame + symbol + values, expandable reasons
│   └── ScannerHistoryTile       one at a time, by scanner + date          [Confirmed visible]
├── ChartWorkspace
│   ├── ExecutionChart (A)       1m, extended hours, VWAP/EMA9/EMA20, volume, HOD
│   ├── ContextChart (B)         5m ⇄ daily toggle, 200 EMA on daily
│   └── RiskBandController       frozen entry/stop/target plan, R readout
├── SymbolContextDock
│   ├── QuoteCard                last, bid/ask, spread bps, range position
│   ├── NewsCatalystCard         headline, publishedAt + firstObservedAt, flame
│   ├── FundamentalsRiskCard     float + source quality, halt state, dilution slot
│   ├── Level2Tile               placeholder, licence-gated                [Phase 3]
│   └── TimeSalesTile            placeholder, licence-gated                [Phase 3]
├── AlertCenter
│   ├── ConsolidatedAlertTimeline grouped rows, expandable to raw events
│   └── NotificationSettings      per-tile sound, severity, cooldown, test
└── WorkspaceManager              layout save/restore, pop-out             [Step 5]
```

## 2. Selected-symbol contract and update sequence

Exactly one dashboard-level selection. Tiles render lists; every detail panel subscribes to
the store. No panel keeps a private ticker.

```ts
type SelectedInstrument = {
  instrumentId: string;      // stable id, survives symbol renames
  symbol: string;
  exchange: string;
  selectedAt: string;        // ISO
  source: { scannerId: string; eventId?: string; rowRank?: number };
  locked: boolean;           // Enter locks; incoming alerts cannot steal focus
};
```

Selection transaction (ordered, single publish):

1. `selectedInstrument.changed` published once;
2. every tile highlights the ticker where visible;
3. selection survives rank changes and temporary list exit;
4. QuoteCard repaints immediately from hot cache (no await);
5. Chart A switches symbol, **keeps** its 1-minute interval;
6. Chart B switches symbol, **keeps** its 5-minute/daily mode;
7. cached news renders, new-headline subscription rebinds;
8. float/fundamentals/halt context switches;
9. depth/tape streams unsubscribe then resubscribe (Phase 3 no-op);
10. URL updates (`?symbol=ABCD`) for deep-linkable alerts.

**Row-order freeze** — values keep updating, order is pinned, newly qualifying symbols queue in
a pending badge; unfreeze applies the newest ranking. Prevents misclicks at 09:30.

## 3. Tier-1 tile configuration

| Tile | Architecture | Rank / trigger | Cadence |
|---|---|---|---|
| Ross-style Five Pillars Scan | list | daily RVOL desc, technical 4/4 only | 30 s |
| Top Gappers | list, **frozen 09:30 ET** | gap % desc | 30 s until open |
| Top Gainers | list | change-from-close desc | 30 s |
| Top Relative Volume | list | RVOL desc | 30 s |
| Top Volume 5 Minutes | list | raw 5 m volume desc | 30 s |
| Running Up | alert | ≥5 % in 5 min + volume + liquidity | per event |
| Small Cap HOD Momentum | alert | new HOD + momentum + branch label | per event |
| Halt | alert | official status transition only | per event |

News is a displayed column everywhere and a gate nowhere (Confirmed platform).

## 4. Chart synchronisation

- ticker: **always** shared unless the user unlocks Chart B;
- interval: independent — A stays 1 m, B stays 5 m/daily across selection changes;
- zoom/range: independent; crosshair sync optional;
- shared across both charts: HOD, premarket high, whole/half dollars, and the **plan id** of a
  frozen entry/stop/target band;
- drawings keyed `instrumentId + interval`;
- a stale or disconnected feed removes the `LIVE` label from both charts.

Renderer: a self-contained canvas renderer ships in this step so the shell has zero external
runtime dependency and works offline; TradingView Lightweight Charts remains the recommended
production swap (the bar contract below is already its shape).

## 5. Fixture schemas

```ts
type ChartBar = { t: epochSeconds; o,h,l,c: number; v: number;
                  session: "premarket"|"regular"|"afterhours"; final: boolean };

type ScannerRow = { scannerId, scannerVersion, rank, symbol, instrumentId, price,
                    changeClosePct?, gapPct?, volume?, dollarVolume?, floatShares?,
                    floatQuality: "verified"|"proxy"|"unknown", dailyRvol?, rvol5m?,
                    spread?, hodDistancePct?, news?: {flame, ageMinutes, headlineId},
                    reasons: {field, value, threshold?, passed, evidence}[],
                    dataStatus: "live"|"stale"|"historical"|"replay" };

type ScannerAlert = { eventId, idempotencyKey, symbol, scannerId, branch?, severity,
                      sourceTime, observedTime, definitionVersion, snapshot: ScannerRow,
                      groupedEventIds?: string[] };

type NewsItem = { id, symbol, publishedAt, firstObservedAt, headline, category };

type ReplayFrame = { ts, session, feed: {status, lastEventAgeSec},
                     lists: Record<scannerId, ScannerRow[]>, alerts: ScannerAlert[],
                     barIndex: Record<symbol, number> };
```

The session file is generated by production scanner code over a fixture, never hand-written, so
the prototype cannot drift from the engine.

## 6. Acceptance tests mapped to §25

| §25 criterion | Test |
|---|---|
| Tier-1 tiles open | `test_session_contains_tier1_lists` |
| Tile reports LIVE/STALE/OFFLINE/REPLAY | `test_frames_carry_feed_health`, UI `data-state` assertion |
| Row click changes both charts + news once | UI `test_row_click_links_everything` |
| A stays 1 m, B stays 5 m/daily | UI `test_intervals_survive_symbol_change` |
| Selection survives reordering | UI `test_selection_survives_rerank` |
| Freeze order prevents misclicks | UI `test_freeze_pins_row_order` |
| Five Pillars fields separate | `test_pillar_reasons_are_itemised` |
| Flame from news age only | `test_flame_matches_age_boundaries` |
| List vs alert tiles differ | `test_list_and_alert_tiles_distinct` |
| Branches select notification only | `test_branch_is_label_not_filter` |
| Dedupe + consolidation verified in replay | `test_replay_consolidates_same_symbol` |
| Top Gappers freezes at 09:30 | `test_gappers_frozen_after_open` |
| Historical row positions charts | UI `test_alert_click_seeks_charts` |
| Bands freeze when armed | `test_plan_bands_do_not_repaint` |
| Hidden thresholds labelled | `test_every_threshold_carries_evidence_label` |
| No secrets in the browser | `test_session_json_has_no_secrets` |

## 7. Unresolved decisions that genuinely block later phases

1. **Market-data provider** — gates real-time everything (Alpaca / Polygon / Databento /
   Intrinio). Nothing else in Phase 5 can start until entitlements and extended-hours coverage
   are chosen.
2. **News provider** — the flame is only as good as a licensed timestamped feed; free scraping
   cannot be redistributed and has no reliable publication time.
3. **Float source of record** — which vendor is `verified` versus `proxy`, and how often
   point-in-time snapshots refresh after offerings/splits.
4. **Deployment shape** — personal single-user localhost (current assumption) versus hosted;
   changes auth, secret storage and licence terms.
5. **Calibration data** — Scanner History samples are needed before any Approximation threshold
   (float bands, RVOL cutoffs, Running Up windows) stops being a guess.

None of these block Steps 1–2, which is why they are built replay-first.
