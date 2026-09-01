# Master context

## Objective

Help the user master Ross Cameron/Warrior Trading education and independently reproduce the useful scanner behavior in TradingView without claiming access to proprietary server rules.

## Confirmed platform context

- The user has a Warrior Pro Preview trial and access to Day Trade Dash, course material, chat-room observation, scanners, charting and news.
- Market-data agreements are required for live scanner/chart data.
- The live Small Cap room normally opens around 7:00 AM ET on market days; room status is unrelated to scanner data status.
- Day Trade Dash scanners are preconfigured to Ross/Warrior settings rather than fully user-customizable.
- List scanners update about every 30 seconds; alert scanners update every second.
- Scanner access can begin at 4:00 AM ET.
- A green scanner status dot means live market data is arriving; red indicates a data problem and potentially stale scanners.
- The official scanner guide used as the principal taxonomy source was modified January 8, 2026.

## Public-site and curriculum audit

- The public Warrior site and official support portal were structurally audited on August 28, 2026.
- The June 2026 support position is that the current teaching focus is long-biased day trading of small-cap stocks.
- Warrior states that it does not trade Forex, cryptocurrency or CFDs.
- The May 2026 syllabus lists a 15-chapter `Day Trading: The Basics` course and a 20-chapter `Day Trading: Strategies & Scaling` course, plus IRA, Algo Scalping, Trader Rehab, Trading Psychology, archives and graduate-taught courses.
- The complete public-site topic map, core methodology, setup summaries, risk framework, tools and coverage ledger live in `references/warrior-public-site-map.md`.
- The authenticated Warrior Pro Preview chapters 1-6 were inspected in full on August 28, 2026: 19 videos, about 12.91 hours, 28,986 transcript segments, and all 153 visible quiz questions. Detailed derived notes live in `references/day-trading-basics-preview-mastery.md`.
- Only the Chapter 1 answer-key PDF was accessible. Chapters 2-6 answer keys require completing each quiz with at least 60% and were not bypassed.
- Do not claim the private Basics chapters 7-15, Strategies & Scaling videos, live archives, or full historical blog archive are mastered until each item is actually inspected.

## Active Ross-style layout inspected

The inspected layout contained:

1. Top Gainers
2. Running Up
3. Small Cap – High of Day Momentum
4. Low Float Top Gainers
5. Ross's 5 Pillars Scan
6. Ross's 5 Pillars Alert

## Five Pillars working model

Publicly described starting criteria:

- ideal price: $2–$20;
- gain from prior close: at least 10%;
- relative volume: approximately 5x minimum;
- float: below 20 million shares, lower preferred;
- news/catalyst: manually verify.

Warrior's Five Pillars scanner does not automatically require news. Treat the flame/news indicator as a separate check.

## HOD sub-strategies confirmed by the platform

- Low Float – Medium Relative Volume
- Low Float – High Relative Volume
- Low Float – High Relative Volume – Price $20+
- Low Float Volatility Hunter
- Former Momo Stock
- Medium Float – Medium Relative Volume – Price $20+
- Medium Float – High Relative Volume – Price $20+
- Medium Float – High Relative Volume – Price under $20
- Squeeze – Up 10% in 10 minutes
- Squeeze – Up 5% in 5 minutes
- Squeeze – 52-week Breakout

The numeric definitions of low/medium float, relative-volume bands, volatility hunter, former momo, and Running Up are not exposed publicly.

## Operational facts now mastered

- Top Gapper lists stop updating at 9:30 AM ET; Top Gainers and Top Losers continue during the day.
- Alert scanners consolidate multiple alerts occurring close together; expand the grouped row to see earlier alerts.
- Ross's Small Cap HOD audio preference selects every strategy except the medium-float branches.
- Alert-scanner news flames may update as late as five minutes after an alert; list-scanner news updates with the 30-second list refresh.
- Scanner History covers approximately six months and allows only one history widget at a time.
- HOD Momo requires both HOD and momentum criteria; it intentionally does not alert on every high-of-day print.
- Five Pillars candidates can disappear when momentum or another condition fails and reappear when they qualify again.
- Full taxonomy, column definitions, operating procedures and TradingView mappings live in `references/scanner-guide.md`.

## Source-code inspection conclusion

The downloadable application bundle contains scanner UI and protected API routes, not the production filter values. The client model supports data-point IDs, conditions, match-any logic, top-list sorting, alert event IDs, colors, and enable/disable state. Exact strategies are loaded from bearer-protected server endpoints. Do not attempt to extract or use authentication secrets.

## TradingView implementation status

The bundled `assets/ross_style_momentum_scanner.pine` is a Pine v6 clean-room approximation with:

- technical Five Pillars scoring;
- manual catalyst confirmation;
- HOD Momentum, Running Up, squeeze, 52-week breakout, and former-runner proxies;
- Pine Screener outputs;
- alerts;
- a PASS/FAIL dashboard;
- cyan entry, red stop, and green target bands.

Default planning model:

- entry above signal-bar high by $0.01;
- stop below signal-bar low by $0.01, or configurable ATR stop;
- target at 2R;
- band half-width of $0.02.

The script has received structural review but must be compiled in TradingView before being called production-ready.

## YouTube-corpus knowledge merged (September 1, 2026)

The repository's earlier knowledge base (257 public YouTube transcripts, 7,937 claims, 2,050 mechanical rules in `knowledge-base/`) was reconciled with this bundle. The merged reference is `references/youtube-corpus-integration.md`. Highlights:

- Both sources agree on the Five Pillars, first-pullback trigger/stop/2R structure, light-volume pullback rule, minimal indicator set and R-based review.
- The corpus adds (Observed, untested): session windows (blackout 09:30–09:35, prime to 10:30, hard stop 11:30), entry gates (above VWAP/9 EMA, MACD positive, pullback index ≤2, support confluence ≥2), scale-out 50/25/25 with breakeven move, daily limits (6% max loss, 50% giveback, green-to-red, 3 strikes, 1–2 trades), LULD halt-band arithmetic, hotkey schemes, extra setups (Gap and Go, dip-and-rip, VWAP reclaim, ABCD, reverse-split bounce).
- Parameters are distributions, not constants (RVOL 2x–100x, float <1M–<50M with 10–20M reportedly best-performing, gain 2–30%) — sweep in backtests.
- The flame does not exist in the YouTube corpus (bundle/platform-only concept).
- FTC 2022 settlement ($3M) noted; treat claimed performance as marketing to be disproved.
- Bundle wins all conflicts (authenticated course > public video paraphrase); both versions preserved in the integration file.

## Platform build status (September 1, 2026)

`src/momentum_platform/` implements the replay-first backend from `references/scanner-alert-platform-spec.md` (stdlib-only): session calendar, hot state with 1m bar building, clean-room formulas, scanners (Top Gainers/Losers/Gappers with 09:30 freeze, Low Float, Top RVOL, Five Pillars list + rising-edge alert, HOD Momentum with branch labeling, Running Up/Down, 5-in-5, 10-in-10, 52-week breakout), canonical event envelope with reasons and definition versions, notification router (idempotency, cooldown with price-tier override, consolidation, console/JSONL/webhook channels), SQLite event store + watchlist. The older `src/paper_trading` package remains the manual simulator; its audited gaps and bugs are listed in `references/youtube-corpus-integration.md` §7.

## Dashboard knowledge added (September 1, 2026)

`references/dashboard-scanner-chart-knowledge.md` captures the authenticated Day Trade Dash
walkthrough as a focused UI specification. New Confirmed-visible material beyond the earlier
references:

- the exact 29-widget inventory with each tile's visible fields and type (list vs alert);
- the 11 Small Cap HOD Momentum branch names, with float bands / RVOL cutoffs / Volatility
  Hunter / Former Momo still Unknown;
- tile-level behaviors: dockable panels, per-tile audio and branch-sound menus, global alert
  volume, grouped/expandable alerts, per-tile online/offline plus green/red feed health,
  Scanner History (one widget at a time, ~6 months, by scanner and date), layout save and
  pop-out;
- flame interactions: hover for headline preview, click to open the story; alert-row flames can
  arrive minutes after the alert while list flames refresh on the list cycle;
- premarket gapper lists visibly stop updating at 09:30 ET.

Clean-room design added by the same document: shared single selected-symbol state with a
ten-step selection transaction, row-order freeze during fast re-ranking, tile lifecycle
CLOSED->LOADING->CONNECTING->LIVE->STALE->OFFLINE->RECONNECTING, Tier 1/2/3 tile priority,
two-chart workspace (Chart A 1m execution, Chart B 5m/daily context) with independent
intervals but a shared ticker, keyboard model, and the Section 25 MVP acceptance criteria.

The uploaded `SCANNER_ALERT_PLATFORM_IMPLEMENTATION_SPEC.md` was byte-identical to the bundled
`references/scanner-alert-platform-spec.md`; no merge was required.

## Workstation dashboard built (September 1, 2026)

`src/momentum_platform/dashboard/` implements Steps 1-2 of the dashboard
specification: the static workstation shell and a fully deterministic replay
prototype. Nine Tier-1 tiles, one shared selected symbol, two charts with
independent intervals, row-order freeze, expandable pass/fail reasons, frozen
planning bands, alert timeline with consolidation groups, and honest float /
news-latency / halt / Level-2 surfaces. `docs/dashboard-plan.md` answers the
seven pre-coding deliverables. 77 tests pass, including Chromium-driven
acceptance tests mapped to the specification's Section 25 criteria (skipped
automatically when no browser is available).

Engine changes the dashboard work surfaced:

- HOD Momentum now requires a configurable minimum advance over the prior high
  (0.25% default, an independent approximation) so it stops alerting on every
  high-of-day print, matching the confirmed platform description;
- the notification router builds a real consolidation group that keeps filling
  as later same-symbol alerts arrive, so a consumer can show "+N more" without
  losing any raw event;
- ranked rows now carry their own captured values, so a frozen list freezes its
  numbers as well as its order.

Still not built, by design: live provider adapter, news/SEC/halt feeds, Level 2
and Time & Sales, external notification channels, broker integration.

## Current next steps

1. Compile the Pine script in TradingView and resolve any compiler feedback.
2. Build appropriate US-stock watchlists for Pine Screener.
3. Gather at least 20 days of Warrior Scanner History.
4. Calibrate approximations by strategy and time of day.
5. Use the Preview mastery deck for spaced recall and scenario drills.
6. Continue with private Basics chapters 7-15 only when those lessons become accessible.
