# Warrior Trading scanners: mastered reference

Source: Warrior Trading Support, **Scanners: How to Load & Use Them in the Chat Room**, modified January 8, 2026.

## Contents

1. System model
2. Access and data status
3. List scanners
4. Alert scanners
5. HOD Momentum branches
6. Alert consolidation
7. Layout and window management
8. Columns and visual encoding
9. Audio configuration
10. News indicators
11. Scanner History
12. Why a stock may not appear
13. Time-of-day workflow
14. TradingView replication map
15. Unknown proprietary details
16. Exact live platform inventory

## 1. System model

Treat Warrior scanners as real-time, preconfigured discovery tools. Ross Cameron and the Warrior team define the production settings. Members can open, position, sort, link and configure audio for scanner widgets, but they cannot fully edit the underlying market filters.

The platform has two scanner architectures:

| Architecture | Refresh behavior | Output form | Audio |
|---|---|---|---|
| List scanner | Approximately every 30 seconds | Ranked current universe | No scanner audio |
| Alert scanner | Approximately every second | Timestamped qualifying events | Optional chime |

Do not treat a scanner result as an entry. Use it to identify a candidate, then evaluate chart, catalyst, liquidity, risk and the applicable course setup.

## 2. Access and data status

- Scanner data is available from roughly 4:00 AM ET.
- Users must complete the scanner-specific market-data agreements. Simulator agreements are separate.
- Open scanners from the left-side **Scanners** menu in Day Trade Dash.
- A green dot beside Scanners indicates incoming live market data.
- A red dot indicates a scanner-data problem and possible stale results. Check platform announcements.
- Each widget also reports online/offline status in its title area.

Available user operations include:

- open selected scanner widgets;
- sort by columns such as float or volume;
- link ticker selections to quote/chart widgets;
- inspect connected news;
- arrange and save layouts;
- configure sounds for alert scanners;
- study up to six months of Scanner History.

## 3. List scanners

### 3.1 Top Gapper family

The broad Top Gappers system ranks the largest positive or negative gaps versus the prior close. These lists stop refreshing at 9:30 AM ET.

| Scanner | Confirmed behavior |
|---|---|
| Ross's 5 Pillar Scan List | Uses strict Five Pillars and momentum criteria, except news is not enforced automatically. |
| Penny Top Gappers | Restricts results to stocks below $5. |
| Ross's Top Gappers | Restricts toward small-cap momentum candidates. |
| Large Cap | Restricts toward large-cap momentum candidates. |
| Top Gappers | Minimal filtering; combines the three gap families and shows up to 100 leaders. |
| Large Cap Earnings with Gap | Finds large caps with recent earnings and a gap from the prior close. |

For the Five Pillars list, inspect the news flame manually. A stock can qualify before news appears or move because its sector is active.

### 3.2 Top Gainers and Losers family

These lists continue updating after 9:30 AM ET.

| Scanner | Confirmed behavior |
|---|---|
| Top Gainers | Ranks the largest upward moves for the day. |
| Top Losers | Ranks the largest downward moves for the day. |
| Low Float Top Gainers | Applies a low-float restriction to Top Gainers. |
| Penny Top Gainers | Tracks the strongest penny-stock moves. |
| Penny Top Losers | Tracks the weakest penny-stock moves. |
| After Hours Top Gainers | Gainers/losers view for 4:00–8:00 PM ET. |

### 3.3 Event and structural lists

| Scanner | Confirmed behavior |
|---|---|
| Recent IPO Top Moving | Recent IPOs or uplists that remain above/near their opening level within roughly 90 days. |
| Recent Reverse Split | Reverse splits within about 30 days when the ratio exceeds 10:1. A displayed value of 100 means 100:1. |
| Change Since Open | Percentage change measured from the 9:30 AM ET open rather than the previous close. |

### 3.4 Momentum and volume lists

| Scanner | Confirmed behavior and use |
|---|---|
| Top of Trend | Stocks showing momentum near the upper part of their daily range. Useful for anticipating HOD breaks and during 3:00–4:00 PM ET Power Hour. |
| Continuation | Stocks with the largest range that have held above that range over the preceding two weeks. |
| Top RSI Trend | Ranks 1-minute RSI strength or weakness. Warrior notes its displayed RSI may not match a conventional 1-minute RSI exactly. |
| Top Relative Volume | Ranks the highest relative-volume stocks. |
| Top Volume 5 Minutes | Ranks the greatest five-minute share volume. |
| Large Cap Highest Volume | Highest-volume large caps; intended around 10:00 AM ET or later for large-cap micro-scalping ideas. |

## 4. Alert scanners

### 4.1 Ross's Five Pillars Alert

Real-time alert version of the Five Pillars list. It uses strict selection and momentum filters, but does not automatically require news. Verify the flame separately.

### 4.2 Small Cap High of Day Momentum

Also called **HOD Momo**. Requires a new intraday-high condition plus above-average momentum/volume logic and a qualifying branch. It is intentionally not a traditional alert on every HOD print.

### 4.3 Penny High of Day Momentum

HOD system for stocks below $2, with these named branches:

- Penny 52-week High
- Penny Volatility Hunter
- Penny Squeeze Alert

### 4.4 Running Up and Running Down

- **Running Up:** rapid positive percentage moves meeting Warrior momentum logic. It does not require a new HOD and can alert before HOD Momo. Ross watches it particularly around 7:00, 8:00 and 9:00 AM ET news-release periods.
- **Running Down:** corresponding rapid negative moves meeting momentum logic.

### 4.5 Other alert scanners

| Scanner | Confirmed behavior |
|---|---|
| Reversal | Stocks recovering from or reacting after a substantial turn in price. |
| Large Cap HOD Momentum | New large-cap highs with above-average momentum. |
| Halt | Current and earlier halted stocks for the trading day. |

## 5. Small Cap HOD Momentum branches

The combined Small Cap HOD widget includes:

1. Low Float – Medium Relative Volume
2. Low Float – High Relative Volume
3. Low Float – High Relative Volume – Price $20+
4. Low Float Volatility Hunter – HOD breakout
5. Former Momo Scanner
6. Medium Float – Medium Relative Volume – Price $20+
7. Medium Float – High Relative Volume – Price $20+
8. Medium Float – High Relative Volume – Price under $20
9. Squeeze – Up 10% in 10 minutes
10. Squeeze – Up 5% in 5 minutes
11. Squeeze – 52-week Breakout

Treat these names as confirmed branch descriptions, not complete formulas. Warrior does not publish the exact float bands, RVOL cutoffs, volatility formula, former-runner qualification or every shared momentum condition.

Ross's documented HOD audio preference: enable all branches except the medium-float branches. This controls sound only; the medium-float alerts can remain visible.

## 6. Alert consolidation

Alert scanners group multiple triggers that occur close together.

- The collapsed row displays the most recent alert.
- The row reports how many alerts were grouped and the short elapsed period.
- Expand the arrow to inspect the earlier events.
- Do not count a consolidated row as only one raw signal during backtesting.

## 7. Layout and window management

- Position scanner widgets like other Day Trade Dash widgets.
- Use the upper-right pop-out control to create another window group or move widgets to another monitor.
- Save the resulting arrangement as a layout.
- The platform currently limits users to three separate browser windows, while the main window can contain many widgets.

## 8. Columns and visual encoding

Not every scanner contains every field. Common columns are:

| Field | Meaning |
|---|---|
| Symbol / News | Ticker plus access to news/quote behavior. |
| Price | Last traded price at the list refresh or alert. |
| Volume Today | Total shares traded during the applicable session/day. |
| Relative Volume – Daily | Activity relative to the provider's daily baseline. |
| Relative Volume – 5 minute | Recent five-minute activity relative to its baseline. |
| Gap % | Difference from the prior close. |
| ATR | Average True Range field where included. |
| Change From Close % | Current change versus the prior close. |
| Short Interest | Reported short shares/interest. |
| Short Ratio | Short interest divided by average daily volume. |
| Float | Estimated freely tradable shares. |
| Strategy | HOD branch that produced the alert. |

Volume, float and gap cells use gradients:

- greater volume produces a darker volume shade;
- greater float produces a brighter float shade;
- larger positive/negative gaps produce deeper green/red coloring.

Color intensity is comparative visual encoding, not a pass/fail rule.

### Float-data caveat

New IPOs and recently listed companies can temporarily show float as zero or **Check Filings**. The data provider may need 24–48 hours. Review recent filings and distinguish total shares, restricted shares and freely tradable float before making a low-float classification.

## 9. Audio configuration

Audio exists only for alert scanners.

Status appearance:

- crossed-out red bell: audio disabled;
- green bell: audio enabled.

Procedure:

1. Click the alert widget's bell.
2. Select individual strategies or use Select/Unselect All.
3. Use the music-note control to choose and preview a sound.
4. Confirm with **OK**.
5. Click outside the strategy menu to close it.
6. Use the left-side **Alert Volume** control for overall chatroom notification volume.

If no sound plays, inspect browser audio permissions and Warrior's audio troubleshooting guidance.

## 10. News indicators

News flames appear under Symbol / News and cover headlines from the preceding 24 hours.

Interactions:

- hover to preview the headline;
- click the flame to open the latest article;
- click the ticker to populate/link the quote widget for broader news and fundamentals.

Color-age mapping:

| Indicator | Headline age |
|---|---|
| Red flame | 0–2 hours |
| Orange flame | 2–12 hours |
| Yellow flame | 12–24 hours |
| No flame | More than 24 hours or no qualifying recent item |

Latency matters:

- Alert-scanner flames can appear or change up to five minutes after the original alert.
- List-scanner flames refresh with the approximately 30-second list update.

Therefore, absence of a flame on the first alert is not proof that no catalyst exists.

## 11. Scanner History

- Historical lookup covers approximately six months.
- Only one Scanner History widget can be used at a time.
- Select scanner and date to review prior alerts/lists.
- Historical flames correspond to news relative to the selected date.
- List scanners display the timestamp of the latest list refresh.
- **Load full day's data** accelerates loading all event data for an alert scanner so the user can navigate directly to a desired time.
- Full-day loading is not shown for list scanners such as Top Gappers.

Use History for backtesting, but expand consolidated alerts and record news latency separately.

## 12. Why a stock may not appear

### HOD Momentum

- Hitting HOD alone is insufficient.
- The stock must also satisfy momentum/volume conditions.
- A stock may trigger on the next minute close after momentum reaches the threshold.
- Fewer alerts are expected in premarket and postmarket when volume is lower.
- Use Top Gainers, Top Relative Volume or Continuation to build a watchlist when a pure HOD alert is too restrictive.

### Running Up

Running Up is not tied to HOD. It can discover a rapid move before the stock reaches HOD or qualifies for HOD Momo.

### Five Pillars

- News is the deliberate exception: a stock may display without a flame.
- Momentum is dynamic. If any required condition fails, the ticker can leave the list.
- The ticker can return if momentum and all conditions qualify again.

When a clear high-volume momentum event appears to be missing, record ticker and timestamp for support review rather than guessing the hidden threshold.

## 13. Time-of-day workflow

| Time | Scanner emphasis |
|---|---|
| 4:00–7:00 AM ET | Top Gappers, Top Gainers, Five Pillars list, news checks. Expect fewer HOD signals. |
| Around 7:00, 8:00, 9:00 AM ET | Running Up for news-driven acceleration; watch HOD/Squeeze branches. |
| 9:30 AM ET | Top Gapper lists stop refreshing. Shift emphasis toward HOD, Running Up, Top Gainers and change since open. |
| Around 10:00 AM ET onward | Large Cap Highest Volume becomes more useful. |
| 3:00–4:00 PM ET | Top of Trend and Top Gainers for Power Hour strength. |
| 4:00–8:00 PM ET | After Hours Top Gainers. |

This is a discovery workflow, not an instruction to enter trades at those times.

## 14. TradingView replication map

| Warrior scanner | TradingView clean-room implementation |
|---|---|
| Top Gappers | Prior-close gap %, sorted descending; freeze or record 9:30 AM snapshot. |
| Top Gainers / Losers | Change from prior close %, sorted descending/ascending. |
| Low Float Top Gainers | Verified float ceiling plus gain ranking. Avoid treating shares outstanding as true float without labeling the proxy. |
| Penny variants | Add price ceiling of $5 for penny gapper lists or $2 for Penny HOD. |
| Change Since Open | Change from the 9:30 AM opening price. |
| Top of Trend | Position in day's range plus momentum and RVOL. |
| Continuation | Two-week range and hold-above-range approximation. |
| Top RSI Trend | Consistent 1-minute RSI implementation; expect vendor differences. |
| Top Relative Volume | Chosen RVOL formula, sorted descending and documented. |
| Top Volume 5 Minutes | Five-minute share volume, sorted descending. |
| Running Up / Down | Percentage move over configurable N minutes plus volume confirmation, independent of HOD. |
| HOD Momentum | Break previous intraday high plus volume/momentum confirmation. |
| Squeeze 5/5 and 10/10 | Explicit percentage move over approximately five/ten minutes, with liquidity guard. |
| 52-week breakout | Break the highest high of the preceding 252 daily sessions, excluding the current day. |
| Five Pillars list | Price, daily gain, RVOL and float proxy; manual external news confirmation. |
| Five Pillars HOD | Five Pillars technical candidate plus HOD and recent-volume confirmation. |
| Halt | Not reliably reproducible from ordinary Pine OHLCV; use a halt-status data source or TradingView-native market status where available. |
| News flame | Not available as a native Pine news-age field; perform external/manual confirmation. |

## 15. Unknown proprietary details

Keep these labeled **Unknown** until official material supplies them:

- low-float and medium-float boundary values used by each production branch;
- medium/high daily and five-minute RVOL cutoffs;
- Running Up/Down percentage and timing logic;
- full HOD momentum formula and close-vs-intrabar evaluation rules;
- Volatility Hunter calculation;
- Former Momo database and qualification window;
- Reversal logic;
- exact Top of Trend and Continuation formulas;
- vendor-specific RVOL normalization;
- every exchange, security-type, liquidity and data-quality exclusion.

Calibrate approximations against Scanner History without claiming the resulting settings are Ross's source code.

## 16. Exact live platform inventory

For the live 29-widget scanner menu, the exact visible columns for every widget, all selectable alert-strategy names, Scanner History controls, distinct data-field vocabulary, and the confirmed-vs-unknown threshold boundary, read `platform-filter-inventory.md`.
