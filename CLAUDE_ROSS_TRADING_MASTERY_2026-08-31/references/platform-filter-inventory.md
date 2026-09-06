# Live Day Trade Dash scanner and field inventory

Inspected directly in the user's logged-in Warrior Trading Day Trade Dash on August 17, 2026.

## What this inventory proves

- The member scanner menu exposes **29 scanner widgets**.
- The UI exposes scanner names, output columns, sortable fields, alert-strategy names, sound selections, and Scanner History controls.
- A displayed column is a data/output field, **not automatically an inclusion filter**.
- An alert widget's strategy checkbox menu controls which branches produce audio for that user. It does not reveal or edit the branch's server-side qualification logic.
- The member UI does not expose complete numeric conditions for the production strategies. Exact conditions are fetched as protected server-side scanner configuration and cannot be truthfully recovered from ordinary page HTML.

Use the labels **Confirmed**, **Observed**, **Approximation**, and **Unknown** from `SKILL.md`. Everything in the exact UI inventories below is **Confirmed visible in the platform** unless explicitly qualified.

## Scanner History and global controls

Scanner History exposes only:

- **Select Scanner**;
- **Select Date** with previous/next-day arrows;
- **Load full day's data** toggle;
- the selected scanner's historical results.

The left-side **Alert Volume** dialog contains a global minus/plus volume control. It is not a market-data filter.

## Exact scanner menu and visible output fields

The order below follows the live scanner menu.

### 1. Small Cap - High of Day Momentum

- Architecture: alert scanner.
- Columns: Time; Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Gap (%); Change From Close (%); Short Interest; Strategy Name.
- Selectable alert branches:
  - Former Momo Stock
  - Squeeze Alert - 52wk Breakout
  - Low Float - Med Rel Vol
  - Low Float - High Rel Vol - Price $20+
  - Low Float Volatility Hunter
  - Medium Float - High Rel Vol - Price under $20
  - Low Float - High Rel Vol
  - Medium Float - High Rel Vol - Price $20+
  - Medium Float - Med Rel Vol - Price $20+
  - Squeeze Alert - Up 10% in 10min
  - Squeeze Alert - Up 5% in 5min

### 2. Ross's 5 Pillars Alert

- Architecture: alert scanner.
- Columns: Time; Symbol / News; Price; Volume; Float; Relative Volume (5 min %); Relative Volume (Daily Rate); Gap (%); Change From Close (%); Short Interest; Strategy Name.
- Selectable branch: **5 Pillar HOD alert**.

### 3. Ross's 5 Pillars Scan

- Architecture: ranked list scanner.
- Columns: Relative Volume (Daily Rate); Symbol / News; Price; Volume; Float; Relative Volume (5 min %); Gap (%); Change From Close (%); Short Interest; Pos In Range (%).

### 4. Ross's Top Gappers

- Architecture: premarket ranked list; the live title reports that it stops updating at 9:30 AM ET.
- Columns: Gap (%); Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Change From Close (%); Short Interest.

### 5. Top Gappers

- Architecture: premarket ranked list; the live title reports that it stops updating at 9:30 AM ET.
- Columns: Gap (%); Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Change From Close (%); ATR (Rate); Short Interest.

### 6. Top Gainers

- Architecture: ranked list scanner.
- Columns: Change From Close (%); Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Gap (%); Short Interest.

### 7. Top Losers

- Architecture: ranked list scanner.
- Columns: Change From Close (%); Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Gap (%); Short Interest.

### 8. Recent Reverse Splits

- Architecture: ranked list scanner.
- Columns: Change From Close (%); Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Reverse Split - 4 Week; Recent Split.

### 9. After Hours Top Gainers

- Architecture: after-hours ranked list scanner.
- Columns: Change From Regular Close (%); Symbol / News; Gap (%); Price; Volume; Float; AH Volume; Avg AH $ Volume - 120 Min; Relative Volume (Daily Rate); Relative Volume (5 min %); Short Interest.

### 10. Reversal

- Architecture: alert scanner.
- Columns: Time; Event; Symbol / News; Price; RSI - 2 Min; Consec Candles - 1 Min; Consec Candles - 5 Min; Volume; Relative Volume (Daily Rate); Relative Volume (5 min %); Short Interest; Strategy Name.
- Selectable alert branches:
  - Consecutive Candles (1min)
  - Top Reversal with Candle Outside Bollinger Bands with 1 min confirmation
  - Top Reversal with Candle Outside Bollinger Bands
  - Top Reversal with 1 min confirmation
  - Top Reversal
  - Bottom Reversal with Candle Outside Bollinger Bands with 1 min confirmation
  - Bottom Reversal with Candle Outside Bollinger Bands
  - Bottom Reversal with 1 min confirmation
  - Bottom Reversal
  - Consecutive Candles (5min)

### 11. Top Relative Volume

- Architecture: ranked list scanner.
- Columns: Relative Volume (Daily Rate); Symbol / News; Price; Volume; Float; Relative Volume (5 min %); Gap (%); Change From Close (%); Short Interest.

### 12. Continuation

- Architecture: ranked list scanner.
- Columns: Moving - 2 Week (%); Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Change From Close (%); Gap (%); Short Interest.

### 13. Low Float Top Gainers

- Architecture: ranked list scanner.
- Columns: Change From Close (%); Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Gap (%); Short Interest.

### 14. Top Volume 5 Minutes

- Architecture: ranked list scanner.
- Columns: Relative Volume (5 min %); Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Avg Volume - 5 Min; Gap (%); Change From Close (%); Short Interest.

### 15. Top Change Since Open

- Architecture: ranked list scanner.
- Columns: Change From Regular Open (%); Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Gap (%); Short Interest.

### 16. Halt

- Architecture: alert scanner.
- Columns: Time; Symbol / News; Halt Status Desc; Rel Range - 1 Min (%); Rel Range - ~5 Min (%); Price; Volume; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Gap (%); Change From Close (%); Short Interest; Strategy Name.
- Selectable branch: **Halt**.

### 17. Running Up

- Architecture: alert scanner.
- Columns: Time; Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Gap (%); Change From Close (%); Short Interest; Strategy Name.
- Selectable branch: **Running Up Alerts**.

### 18. Running Down

- Architecture: alert scanner.
- Columns: Time; Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Gap (%); Change From Close (%); Short Interest; Strategy Name.
- Selectable branch: **Running Down Alerts**.

### 19. Top of Trend

- Architecture: ranked list scanner.
- Columns: Pos In Range (%); Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Range Today; $ Volume; Change From Close (%); Gap (%).

### 20. Recent IPO Top Moving

- Architecture: ranked list scanner.
- Columns: Moving - 2 Week (%); Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Change From Close (%); Gap (%); Short Interest.

### 21. Large Cap - High Of Day Momentum

- Architecture: alert scanner.
- Columns: Time; Event; Symbol / News; Price; Relative Volume (Daily Rate); Relative Volume (5 min %); $ Volume - 5 Min; Short Interest.
- Selectable branch: **Large Cap Momentum**.

### 22. Large Cap - Earnings With Gap

- Architecture: premarket ranked list; the live title reports that it stops updating at 9:30 AM ET.
- Columns: Gap (%); Symbol / News; Price; Volume; Earnings Report Date; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Change From Close (%).

### 23. Large Cap - Top Gappers

- Architecture: premarket ranked list; the live title reports that it stops updating at 9:30 AM ET.
- Columns: Gap (%); Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Change From Close (%); Short Interest.

### 24. Large Cap Highest Volume

- Architecture: ranked list scanner.
- Columns: Volume; Symbol / News; Change From Close (%); Price; Float; $ Volume; Avg Volume - 5 Min; Volume In 5 Minutes; Short Interest.

### 25. Top RSI Trend

- Architecture: ranked list scanner.
- Columns: RSI - 1 Min; Gap (%); Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Change From Close (%); Short Interest.

### 26. Penny - Top Gappers

- Architecture: premarket ranked list; the live title reports that it stops updating at 9:30 AM ET.
- Columns: Gap (%); Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Change From Close (%); Short Interest.

### 27. Penny - Top Gainers

- Architecture: ranked list scanner.
- Columns: Change From Close (%); Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Gap (%); Short Interest.

### 28. Penny- Top Losers

- Architecture: ranked list scanner.
- Columns: Change From Close (%); Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Gap (%); Short Interest.

### 29. Penny High of Day Momentum

- Architecture: alert scanner.
- Columns: Time; Symbol / News; Price; Volume; Float; Relative Volume (Daily Rate); Relative Volume (5 min %); Change From Close (%); Strategy Name.
- Selectable alert branches:
  - Penny Squeeze Alert- 52wk Breakout
  - Penny Squeeze Alert
  - Penny Volatility Hunter

## Distinct visible data fields

Across all 29 widgets, the platform visibly uses the following market or event fields:

- symbol and linked news;
- event time and event description;
- strategy name;
- last price;
- total volume;
- five-minute volume and average five-minute volume;
- dollar volume and five-minute dollar volume;
- after-hours volume and 120-minute average after-hours dollar volume;
- float;
- daily-rate relative volume;
- five-minute relative volume percentage;
- gap percentage;
- change from prior close;
- change from the regular-session open;
- change from the regular-session close in after hours;
- short interest;
- ATR rate;
- position within the current range;
- current range;
- two-week movement;
- one- and two-minute RSI fields;
- one- and five-minute consecutive-candle counts;
- one- and approximately five-minute relative range;
- halt status description;
- recent split and four-week reverse-split fields;
- earnings report date.

These fields define the available clean-room replication vocabulary. They do not prove that every displayed field participates in each scanner's inclusion rule.

## Confirmed public numerical rules

Only the following numerical values are currently confirmed by official Warrior material or explicit strategy names:

- Five Pillars working criteria: price **$2–$20**, gain from close **at least 10%**, daily relative volume around **5x**, float below **20 million**, and a catalyst/news check performed manually because the scanner does not enforce news.
- Penny High of Day Momentum: stock price below **$2**.
- Penny Top Gappers: stock price below **$5**.
- Squeeze alert branches: **5% in 5 minutes** and **10% in 10 minutes**.
- Recent IPO/uplist window: roughly **90 days**.
- Recent reverse split: within about **30 days** and greater than **10:1**.
- Top Gappers: up to **100** leaders and stops refreshing at **9:30 AM ET**.
- Top Change Since Open measures from the **9:30 AM ET** regular-session open.
- After-hours session: **4:00–8:00 PM ET**.
- Continuation evaluates a preceding **two-week** period, but the exact formula remains undisclosed.

## Server-side unknowns

The following conditions are not exposed by the ordinary member UI and must stay labeled **Unknown**:

- exact low-float and medium-float boundaries for each HOD branch;
- medium/high daily and five-minute relative-volume thresholds;
- Running Up and Running Down lookback windows and percentage thresholds;
- the common HOD momentum formula and whether every test is intrabar or close-confirmed;
- Volatility Hunter calculations;
- Former Momo membership and lookback window;
- Reversal thresholds, Bollinger settings, candle-count requirements, and confirmation implementation;
- Large Cap Momentum capitalization, liquidity, and dollar-volume thresholds;
- Penny Volatility Hunter and Penny Squeeze shared conditions beyond the branch names;
- exact Top of Trend, Continuation, RSI, and range calculations;
- provider-specific relative-volume baselines and normalization;
- exchange, security-type, liquidity, price, spread, and data-quality exclusions not explicitly documented.

Do not describe TradingView approximations for these items as Ross Cameron's exact filters. Calibrate transparent proxies against Scanner History and retain the distinction between a displayed field, a named branch, and a proven inclusion condition.
