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

## Current next steps

1. Compile the Pine script in TradingView and resolve any compiler feedback.
2. Build appropriate US-stock watchlists for Pine Screener.
3. Gather at least 20 days of Warrior Scanner History.
4. Calibrate approximations by strategy and time of day.
5. Use the Preview mastery deck for spaced recall and scenario drills.
6. Continue with private Basics chapters 7-15 only when those lessons become accessible.
