# Master context

## Objective

Help the user master Ross Cameron/Warrior Trading education and independently reproduce the useful scanner behavior in TradingView without claiming access to proprietary server rules.

## Confirmed platform context

- The user has a Warrior Pro Preview trial and access to Day Trade Dash, course material, chat-room observation, scanners, charting and news.
- Market-data agreements are required for live scanner/chart data.
- The live Small Cap room normally opens around 7:00 AM ET on market days; room status is unrelated to scanner data status.
- Day Trade Dash scanners are preconfigured to Ross/Warrior settings rather than fully user-customizable.
- List scanners generally update periodically; alert scanners react in real time.

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
5. Continue the course chapter by chapter using transcripts and mastery checks.

