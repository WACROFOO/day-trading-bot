# Intraday / day-trading strategies with published, cost-aware evidence (US equities, ETFs, index futures)

Research notes compiled 2026-10-31. Scope: published intraday strategies, their exact rules, stated costs and results, and independent or post-publication evidence. Research, not advice.

How to read these notes:
- **Read in full this session**: Zarattini-Barbon-Aziz (Stocks in Play), Zarattini-Aziz-Barbon (Beat the Market, Feb 2025 version with FAQ), Zarattini-Aziz (QQQ ORB), Gao-Han-Li-Zhou (Dec 2015 working-paper version), Baltussen-Da-Lammers-Martens (JFE version), Boyarchenko-Larsen-Whelan (NY Fed SR 917, Aug 2022 revision), Vainio (2026 thesis). Quotes from these are copied from the extracted PDF text.
- **Read through a summarising fetch tool**: QuantConnect, MQL5, CXO Advisory, Concretum pages, EconPapers/IDEAS abstracts. Wording there may be the tool's paraphrase, not a verbatim quote.
- **Search snippet only**: marked "(snippet only)". These came from search-result summaries and the full text was not opened. Verify them before relying on them.
- Evidence tiers follow the brief: (A) peer-reviewed, or SSRN with an out-of-sample/post-publication test and explicit costs; (B) practitioner backtest with stated costs; (C) forum/anecdote.

## 1. Opening range breakout on "Stocks in Play" — Zarattini, Barbon & Aziz (2024)

### Takeaway
The paper is a long/short 5-minute ORB on the top 20 US stocks by first-5-minute relative volume, with price >$5, ADV >1M and ATR >$0.50. It reports 1,637% total return and Sharpe 2.81 net of commission over 2016–2023. It models **no slippage, no spread and no short-borrow cost**, and has **no out-of-sample test**. The same ORB without the relative-volume filter returned only 29% (Sharpe 0.48). The one independent replication found (QuantConnect) tested only 2016 and states no fee model. **Tier B**: an SSRN working paper with commission only and no out-of-sample period.

### Cited Findings
**Paper, sample and data**
- Paper: SSRN 4729284 (also Swiss Finance Institute Research Paper 24-98), dated "February 16, 2024". — [Zarattini, Barbon, Aziz PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content); [IDEAS listing](https://ideas.repec.org/p/chf/rpseri/rp2498.html)
- Abstract: "Using a large dataset that covered more than 7,000 US stocks traded from 2016 to 2023 ... A portfolio that consisted of the top 20 Stocks in Play achieved a total net performance of over 1,600%, with a Sharpe ratio of 2.81, and an annualized alpha of 36%. Passive exposure in the S&P 500 would have achieved a total return of 198% during the same period." — [PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- Universe and data: "all equities listed on US exchanges (both NYSE and Nasdaq) from January 1, 2016 to December 31, 2023 ... This universe comprised approximately 7,000 stocks and was free from survivorship bias. The data for these stocks were sourced from the Center for Research in Security Prices (CRSP). Intraday data for all stocks were obtained from IQFeed. Notably, this intraday data remained unadjusted for stock splits or dividends". — [PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)

**Rules**
- Filters, quoted exactly:
  1. "The opening price had to be above $5."
  2. "The average trading volume over the previous 14 days had to be at least 1,000,000 shares per day."
  3. "The ATR over the previous 14 days had to be more than $0.50."
  4. "The Relative Volume had to be at least 100%."
  5. "Trade the stocks with the top 20 Relative Volume."
  — [PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- Relative-volume definition: relative volume on day t is the stock's first-5-minute volume divided by the average first-5-minute volume over the previous 14 days. The paper says "ORVolume_t,j represents the volume traded in stock j during the first 5-minutes of trading in day t". For longer ranges, "the Relative Volume for a 15-minute ORB is measured in the first 15 minutes, and for a 30-minute ORB, it is compared with the first 30-minute average over the previous 14 days." — [PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- Entry and direction: "we placed a stop order (not to be confused with a stop loss order) at a level equal to the high/low of the 5-minute range, in the direction of the opening range. For example, if a stock had a bullish move within the first 5 minutes of trading (from 9:30 am until 9:35 am ET), we placed a stop order at the highest value of the 5-minute opening range ... In the case of a doji (open = close) forming in the first 5 minutes, no order was placed." — [PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- Stop and exit: "we placed a stop loss order at a 10% ATR distance from the executed entry price. If the stop loss was not reached intraday, we closed the position at the end of the trading session (i.e., 4:00 pm ET)." The ATR is the 14-day ATR. — [PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- Sizing and leverage: "Each stock was traded such that in case of the stop loss being hit, the resulting loss incurred on the capital deployed for that position would be 1%. We also set a maximum leverage constraint at 4x". Footnote: "The leverage constraint may imply that in some trades, the maximum loss per trade is less than 1%." — [PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)

**Costs**
- "We assumed a starting capital of $25,000 and incorporated a commission cost of $0.0035 per share (this figure represented the entry-level commission fee charged by Interactive Brokers Pro – Tiered as of December 31, 2023)." — [PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- The full extracted text contains no slippage, bid-ask spread, short-borrow or locate assumption, and no out-of-sample test. The words "slippage", "borrow" and "out-of-sample" do not occur. Fills are implicitly assumed at the stop-order level. — [PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)

**Results**
- Base ORB on all filtered stocks, without the relative-volume filter (Table 1): Total Return 29%, IRR 3.2%, Volatility 6.6%, Sharpe 0.48, Hit Ratio 41.4%, MDD 13%, Worst Day −0.8%, Alpha 3.3%, Beta 0.01. S&P 500 over the same period: 198%, 14.2%, 18.3%, 0.78, 54.9%, 34%, −10.9%. — [PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- Per-trade relationship with relative volume (net of commissions): "when the Relative Volume was below 100%, the average PnL of 5-minute ORB trades was notably low at -0.02R. However, this figure improved significantly to 0.08R per trade when the Relative Volume exceeded 100%. Remarkably, at a Relative Volume of over 30x (or more than 3,000%), the average profitability per trade soared to 0.38R." — [PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- ORB + relative volume (Table 2): Total Return 1,637%, IRR 41.6%, Volatility 14.8%, Sharpe 2.81, Hit Ratio 48.4%, MDD 12%, Worst Day −1.61%, Alpha 35.8%, Beta 0.00. The text says "an initial investment of $25,000 in this strategy would have grown to approximately $435,000". — [PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- Results by opening-range length, all with Relative Volume ≥100% (Table 3):

  | Range | Total Return | IRR | Vol | Sharpe | Hit | MDD | Alpha | Beta |
  |---|---|---|---|---|---|---|---|---|
  | 5m | 1,637% | 41.6% | 14.8% | 2.81 | 48.4% | 12% | 35.8% | 0.00 |
  | 15m | 272% | 17.4% | 12.2% | 1.43 | 44.7% | 11% | 16.9% | −0.01 |
  | 30m | 21% | 2.3% | 11.1% | 0.21 | 42.4% | 35% | 2.8% | 0.01 |
  | 60m | 39% | 4.1% | 10.2% | 0.40 | 42.3% | 21% | 4.4% | 0.01 |
  | COMBO | 234% | 15.8% | 7.9% | 1.99 | 47.3% | 7% | 15.0% | 0.00 |

  **No 1-minute opening range was tested.** — [PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- The authors on why 5 minutes wins: "The reason for the 5-minute ORB's superior performance is unclear and warrants further investigation." — [PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- Robustness claim, made without an out-of-sample test: "Considering that these returns were net of commission and the strategy's parameters were minimal and based on economic rationale rather than retrospective optimization, we are confident that these results could maintain their robustness and significance in future applications." — [PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- Per-stock win ratios in the best-performer table are roughly 17–24% for 5m-ORB (for example DDD 385R at 21%, NVDA 309R at 19%, TSLA 183R at 18%). This is a low-hit-rate, fat-right-tail system. — [PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- Conflict of interest: the authors are affiliated with Concretum Research and Peak Capital Trading / Bear Bull Traders, a trading-education business. — [PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)

**Independent replication (QuantConnect, Tier B/C)**
- Rules used: "the 1,000 most liquid US Equities that are trading above $5/share and have an Average True Range (ATR) > $0.50". It trades the 20 most "in play" stocks by first-5-minute relative volume against the 14-day average, with an entry stop at the OR high or low, an ATR-based stop, exit at close, and 1% risk sizing. The universe is smaller than the paper's. — [QuantConnect research 18444](https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/)
- Results: the backtest covers **2016 only** ("the first year of the paper's backtest period"). It reports Sharpe 2.396 versus 0.836 for SPY buy-and-hold, with beta −0.042. Of 25 parameter combinations (opening range 5–25 minutes, universe 500–1,500), "17 (68%) produced a greater Sharpe ratio than the benchmark". No fee or slippage model is described, and no CAGR or drawdown is reported. — [QuantConnect](https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/)
- Forum comments on the replication (Tier C):
  - "doesn't look good for other years" (Angus Li)
  - "completely collapses during dot com" (Jack Pizza)
  - Live-trading issues: stop-placement timing, duplicate orders, and broker rejections of stop orders as "wash trades".
  — [QuantConnect](https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/)

### Inferences
- **Look-ahead**: selection is clean. Relative volume uses only the first 5 minutes against the prior 14 days and is known at 9:35, and ATR and ADV use prior days. The weak points are fills and costs, not selection.
- **Unrealistic fills**:
  - Entries are stop orders assumed filled at the exact OR high or low, and stops are assumed filled at exactly 10% of ATR.
  - At the minimum allowed ATR of $0.50, the stop is $0.05 per share. A one-cent spread crossed on entry and on exit, plus any stop slippage, would take a double-digit percentage of R per trade. This is arithmetic on the stated rules, not a measured figure.
  - The headline 0.08R per trade, for relative volume >100%, is thin relative to plausible slippage.
- **Shorts**: roughly half the trades are shorts in high-attention names. Borrow availability and fees are not modelled, so hard-to-borrow names would be unavailable or costly in practice.
- **Leverage**: the 4x cap binds. With 20 positions each sized to risk 1% on a tight stop, the strategy wants very large notional, so the reported return depends on intraday margin.
- **The filter is the whole edge**: unfiltered ORB returns about 3.2% a year, and the edge exists only through the relative-volume ranking. That is the same "stocks in play" idea as the bot's gapper selection, but restricted to more liquid names priced above $5.
- **Replicable on the repo's data**: the rules can be run on Alpaca SIP 1-minute bars. Only first-5-minute volume, 14-day ATR and ADV are needed, and a full US-equity universe with survivorship-free delisted names is required to match the paper. A faithful replication should add per-share slippage, a spread proxy and borrow constraints, and should extend to 2024–2026 as a genuine post-publication period.

### Gaps
- No post-publication (2024–2026) performance from the authors or anyone else was found for this specific strategy.
- No long/short split was reported in the paper.
- No capacity analysis was found.
- No 1-minute opening-range variant exists in the paper.
- CXO Advisory's review exists, but its findings and critiques are paywalled. Only the rules were visible. — [CXO](https://www.cxoadvisory.com/individual-investing/intraday-trading-of-overactive-stocks-via-opening-range-breakout/)
- The QuantConnect replication's results outside 2016 were not published by its author.

## 2. Zarattini & Aziz (2023) QQQ 5-minute ORB; Zarattini, Aziz & Barbon (2024) "Beat the Market" SPY noise-area momentum; later Concretum work

### Takeaway
**QQQ ORB:**
- Reports Sharpe 1.12, 675% total return and 0.13R per trade at a 24% win rate (2016-01-01 to 2023-02-17).
- Assumes $0.0005/share commission and explicitly no slippage, with no out-of-sample period.
- A 2026 independent replication on five index CFDs (2015–2026) reproduced the gross edge on Nasdaq (+0.131R) but found **net ≈ 0** (+0.002R on NQ, negative elsewhere).
- Tier B, contradicted net of costs.

**Beat the Market (SPY):**
- The most cost-aware of the Concretum papers: $0.0035/share commission, $0.001/share slippage from >1,000 live trades, and an I-Star impact re-run (Sharpe 1.17).
- Reports 1,985% and Sharpe 1.33 for May 2007 to April 2024, using volatility-targeted leverage up to 4x.
- The authors publish a post-publication simulated update: 2024 +32.2%, January 2025 −1.2%.
- Formally Tier A by the brief's definition (SSRN, explicit costs, post-publication test). The post-publication test is author-run, short and simulated, and no independent replication with costs was found.

### Cited Findings
**QQQ ORB (Zarattini & Aziz, "Can Day Trading Really Be Profitable?", SSRN 4416622)**
- "First published April 10, 2023." The paper's abstract says the TQQQ portfolio "would have earned an outstanding return of 1,484% during the same period of 2016 to 2023, while an investment in the QQQ ETF would have earned 169% annualized". The body text says 1,485%, and the "169% annualized" is in fact a total return. — [Paper PDF (Wealth-Lab-hosted copy)](https://wealth-lab.com/api/discussion/download/pdf/6590-ORB-Strategy-pdf); [SSRN](https://papers.ssrn.com/abstract=4416622)
- Rules:
  - "if during the first 5 minutes the market moved up, we took a bullish position starting from the second candle's opening price. In contrast, if the first 5-minute candle was negative, we took a bearish position at the open of the second 5-minute candle. No positions were opened when the first 5-minute candle was a doji (open ~ close)."
  - "The stop loss was placed at the low of the day (which was the low of the first 5-minute candle) for a long trade, and at the high of the day ... for a short trade"
  - "We set the profit target at 10x the $R. Should the target not have been reached by the end of the day (EoD), we liquidated the position at market closure."
  - "We assumed a starting capital of $25,000, a maximum leverage of 4x, and a commission of $0.0005/share traded. The trading size was calibrated such that if a stop was hit, we lost 1% of our capital."
  — [Paper PDF](https://wealth-lab.com/api/discussion/download/pdf/6590-ORB-Strategy-pdf)
- Table 1 states: "Entry: Open of the second 5-minute candle. We assumed no slippage in fills.", with dates "1 January 2016" to "17 February 2023". The text adds: "aggregated data were provided by Interactive Brokers" and, on the benchmark, "We did not include any commission for this benchmark portfolio." — [Paper PDF](https://wealth-lab.com/api/discussion/download/pdf/6590-ORB-Strategy-pdf)
- QQQ results:
  - "a $25,000 day trading account on January 1, 2016 would be worth $192,806 (net of commissions) as of February 17, 2023. That is an outstanding total return of 675%."
  - "The annualized alpha was 33% (net of commissions) and is highly significant (p.value = 0.0025)."
  - "out of 1,795 trades, 51% were long trades while 49% were short. The annualized Sharpe Ratio was 1.12 while the annualized rate of return was 31%."
  - "The Win Rate of the strategy was 24%, which made the average PnL per trade equal to 0.13R."
  — [Paper PDF](https://wealth-lab.com/api/discussion/download/pdf/6590-ORB-Strategy-pdf)
- TQQQ results: "an astonishing total return of 1,485% was achieved during the 7-year period"; "The annualized alpha was 47% (net of commissions) (p.value = 0.0013) ... The Sharpe Ratio was 1.18"; "the resulting average PnL per trade was 0.18R". — [Paper PDF](https://wealth-lab.com/api/discussion/download/pdf/6590-ORB-Strategy-pdf)
- The authors flag their best variant themselves. A TQQQ version with a 5%-of-ATR stop "would have increased by 9,350% ... annualized alpha of 93% (net of commissions)", but "this result can under certain circumstances be considered unrealistic as our model assumed no slippage ... A stop placed at 5% of the 14-day ATR implies a stop width of $0.08. With a large account and a large share exposure, the stop will likely be exceeded." — [Paper PDF](https://wealth-lab.com/api/discussion/download/pdf/6590-ORB-Strategy-pdf)
- Independent replication (MQL5 blog, 2026, Tier B with stated costs):
  - Setup: CFDs on NQ, SPX, Dow, DAX and FTSE, cash session, January 2015 to June 2026. Spread and slippage were modelled in points (NQ 2.5, SPX 0.8, Dow 4.0, DAX 2.5, FTSE 1.5), and trades with risk below twice the round-trip cost were excluded.
  - Gross per trade: NQ +0.131R (t +2.9), SPX +0.119R, Dow +0.048R, DAX +0.116R, FTSE +0.050R.
  - Net per trade: NQ +0.002R (t 0.0), SPX −0.081R, Dow −0.081R, DAX −0.038R, FTSE −0.079R.
  - Sub-periods: "no market is distinguishable from zero". 2015–2017 was negative in every market, and the best 2021–2026 figure was +0.06R on NQ.
  - Conclusion: "The paper is right about the pattern and wrong about the trade". The author estimates spread plus slippage at 6–12% of risk per trade.
  - These figures come through a summarising fetch tool, so the wording may be paraphrased.
  — [MQL5 replication](https://www.mql5.com/en/blogs/post/776235)
- CXO Advisory's summary of the paper's assumptions: "They assume $25,000 starting capital, maximum 4X leverage and $0.0005/share commission". It also lists no bid-ask spread and no slippage among the test conditions. The findings section is paywalled. — [CXO Advisory](https://www.cxoadvisory.com/technical-trading/day-trading-with-an-opening-range-breakout-strategy)

**Beat the Market (Zarattini, Aziz & Barbon; first version May 10, 2024; version read: February 3, 2025)**
- Abstract: "From 2007 to early 2024, the resulting intraday momentum portfolio achieved a total return of 1,985% (net of costs), an annualized return of 19.6%, and a Sharpe Ratio of 1.33." — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Data: "1-minute OHLCV (Open, High, Low, Close, and Volume) data from IQFeed, covering the period from May 2007 to April 2024." — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Noise area, exact construction:
  - For each of the prior 14 days and each time of day HH:MM, take move = |Close(t−i, HH:MM) / Open(t−i, 9:30) − 1|, for i = 1..14.
  - σ(HH:MM) is the 14-day average of that move.
  - UpperBound = max(Open(t, 9:30), Close(t−1, 16:00)) × (1 + σ).
  - LowerBound = min(Open(t, 9:30), Close(t−1, 16:00)) × (1 − σ).
  - The paper explains the gap adjustment: "following a gap-down event, the Upper Boundary of the Noise Area is adjusted upward by a quantity equal to the gap size, and conversely for a gap-up event".
  — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Timing: "trading is restricted to semi-hourly intervals, specifically at HH:00 and HH:30"; "Positions are unwound either at market Close or if there is a crossover to the opposite boundary ... Stop losses can also be triggered only on semi-hourly intervals"; "the intraday momentum strategy we outline here takes its first position at 10:00". — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Trailing stop: "Long TrailingStop = max(UB, VWAP)"; "Short TrailingStop = min(LB, VWAP)"; "VWAP is computed only using market hours data." — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Sizing and leverage:
  - The base version allocates "exposure equal to 100% of the equity available at the beginning of each trading day".
  - The final version "targets a daily market volatility of 2% (σtarget = 2%)", with Shares = AUM(t−1) × min(4, σtarget/σSPY) / Open, where σSPY is the 14-day standard deviation of daily returns.
  - "the leverage for the active strategy is capped at 4x."
  — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Costs:
  - "a commission fee of $0.0035 per share, which represents the entry-level commission charged by Interactive Brokers. Additionally, we account for a slippage of $0.001 per share".
  - The slippage figure comes from a live test: "After executing over 1,000 trades, involving more than $50 million in notional value, the average slippage recorded is approximately $0.001, with a median value even lower at $0.0005." Slippage is measured against "the Open price of minute HH:MM".
  - On commission tiers: "on approximately 20% of the days, we benefit from lower commission fees due to a 1-month trailing volume exceeding 300,000 shares".
  — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Results (Tables 3 and A1):

  | Version | Total | IRR | Vol | Sharpe | Hit | MDD | Alpha | Beta |
  |---|---|---|---|---|---|---|---|---|
  | Opposite-band stop | 178% | 6.2% | 10.9% | 0.61 | 54% | 21% | 7.1% | −0.05 |
  | Current band + VWAP, 100% size | 380% | 9.7% | 7.7% | 1.24 | 43% | 12% | 9.9% | −0.03 |
  | Current band + VWAP, dynamic size | 1,985% | 19.6% | 14.3% | 1.33 | 43% | 25% | 19.6% | −0.07 |
  | SPY buy & hold | 227% | 7.2% | 20.2% | 0.45 | 54% | 56% | – | – |

  Trade-level figures: 7,668 trades, 1.8 per day, 37% trade-level hit ratio, and "Avg. PnL x Share" of 0.09. — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- In-sample losing years from the monthly table (FAQ Q4/Q24): 2016 −12.8% and 2017 −6.9%. Other years include 2008 +63.4%, 2018 +61.1%, 2022 +24.4% and 2023 +37.2%. — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Post-publication update (FAQ Q24), which is the authors' simulated continuation and not independent, not live P&L:
  - Monthly, May to December 2024: −4.3, 1.6, 8.2, −2.8, 4.1, 6.7, −2.6, 5.7.
  - "2024 ... 32.2" for the year; "2025 −1.2" for January only.
  - The paper says: "The green area highlights the post-publication period."
  — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Impact-model robustness (FAQ Q15), using Kissell's I-Star large-cap parameters: "The Sharpe Ratio stands at 1.17 (versus 1.33), with the yearly alpha remaining well above 15% (versus 20%)." — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Parameter sensitivity: "the best risk-adjusted returns are achieved with a VM of approximately 1.5". The lookback table shows Sharpe ratios of 1.23–1.50 across 5–90 days, with 90 days the best at "2,757 ... 1.50". — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Internal inconsistency to note: FAQ Q22, covering "May 2007 to December 2024", shows the dynamic version at "2382" total, IRR 19.9, Sharpe 1.35, and says "7,964" trades. That differs from the 1,985%, Sharpe 1.33 and 7,668 trades in the main tables, presumably because of the sample end. — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Extensions the authors report (FAQ Q13), all author-run with no costs detail given: "We applied the same rules to 33 different futures markets globally, covering 21 commodities and 12 equity indices, between January 2007 and September 2024. Of these, only 2 instruments produced a negative total return. The average Sharpe Ratio across all instruments was 0.60, while a well-diversified portfolio trading all assets simultaneously achieved an impressive Sharpe Ratio of 1.65." Most instruments are anonymised as "***". Named equity-index rows give Sharpe ratios of 1.23 for Nasdaq, 0.45 for Russell, 0.80 for the S&P 400 MidCap and 1.32 for the S&P 500. — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Other ETFs and stocks (FAQ Q12): "from 2018 until August 2024 ... A diversified portfolio would have produced a Sharpe Ratio that exceeds 2". This is shown as a chart only. — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Code: the paper says "We shared the Matlab and Python versions of the code", and it also cites the open-source TradingView "Concretum Bands" indicator. — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Third-party extension, a Maróy forum post (Tier C, snippet only): it reports Sharpe ratios "over 3.0" and annualized returns "over 50%" after optimising all parameters and exit rules. That is in-sample optimisation, and the post was not opened. — [Bear Bull Traders forum](https://forums.bearbulltraders.com/topic/4002-improvements-to-intraday-momentum-strategies-using-parameter-optimization-and-different-exit-strategies/)

### Inferences
- **The two Concretum ETF papers carry different evidential weight.**
  - The QQQ ORB is a 1,795-trade, 24%-hit-rate system assuming zero slippage and a commission seven times lower than the one the later papers use. An independent 2026 replication finds the gross pattern real but net expectancy about zero.
  - Beat the Market trades about 1.8 times a day in the most liquid ETF, has a live-measured slippage figure, survives an impact model in the authors' own re-run, and has a few post-publication months.
  - Of the Concretum work, BTM is the stronger candidate. It is still not independently confirmed.
- **The leverage effect in BTM**: the unlevered 100%-notional version returns 9.7% a year (Sharpe 1.24). The 1,985% headline comes from volatility-targeted leverage of up to 4x.
- **Look-ahead in BTM looks minimal**: bands use the prior 14 days, signals fire at HH:00/HH:30, and slippage is benchmarked to the next minute's open. One caveat: the max(Open, previous Close) term uses the 9:30 open print, which the backtest treats as known at 10:00. That is fine.
- **Replicable on the repo's data**: both strategies are directly testable on Alpaca SIP 1-minute SPY/QQQ bars. The open-source Concretum code would allow a like-for-like check, and the truly out-of-sample window is May 2024 to October 2026.

### Gaps
- No independent, cost-inclusive replication of Beat the Market was found. The forum extension is in-sample and was not read.
- No Concretum paper from 2025–2026 applying intraday momentum to other assets was found as a standalone SSRN paper. The futures, ETF and stock results exist only in the BTM FAQ.
- No post-January 2025 BTM performance figures were found.
- The SSRN abstract page for 4416622 returned HTTP 403, so the paper was read from a third-party-hosted copy.

## 3. Market intraday momentum — Gao, Han, Li & Zhou (2018, JFE); Baltussen, Da, Lammers & Martens (2021, JFE); post-publication evidence and tradability

### Takeaway
Two peer-reviewed papers establish that the return before 15:30 predicts the last 30 minutes.
- **Gao et al.**: SPY 1993–2013, out-of-sample R² 1.2%, timing Sharpe 1.08, and 6.52% a year after spread costs post-2005, assuming an exit at the closing price with no spread.
- **Baltussen et al.**: more than 60 futures 1974–2020, equity-index timing Sharpe 1.73 gross, linked to gamma hedging by options dealers and leveraged ETFs.

Baltussen et al. state explicitly that they do not deduct costs. They add only that S&P futures stay net positive at a one-tick cost. Post-2013 evidence is mixed and was only partly verified. **Tier A for existence; Tier A− for tradability**, since costs are partial: no commissions, and a close-auction exit assumed spread-free.

### Cited Findings
**Gao, Han, Li & Zhou (working paper, December 2015)**
- Version read: the Dec 2015 working paper. The published version is J. Financial Economics 129(2):394–414 (2018), and its numbers may differ slightly. — [WP PDF](https://c.mql5.com/forextsd/forum/173/intraday_momentum_-_the_first_half-hour_return_predicts_the_last_half-hour_return.pdf); [JFE record](https://econpapers.repec.org/RePEc:eee:jfinec:v:129:y:2018:i:2:p:394-414)
- Abstract: "Based on high frequency data of the S&P 500 ETF from 1993 – 2013, we document an intraday momentum pattern: the first half-hour return on the market predicts the last half-hour return. The predictability, both statistically and economically significant, is stronger on more volatile days, on higher volume days, on recession days, and on major macroeconomic news release days." — [WP PDF](https://c.mql5.com/forextsd/forum/173/intraday_momentum_-_the_first_half-hour_return_predicts_the_last_half-hour_return.pdf)
- Data and definitions: "SPY ... from the Trade and Quote database (TAQ) ... The sample period spans from February 1, 1993 through December 31, 2013"; "we calculate the first half-hour return using previous day's close price and the price at 10:00am Eastern time". The first half-hour return therefore includes the overnight gap. — [WP PDF](https://c.mql5.com/forextsd/forum/173/intraday_momentum_-_the_first_half-hour_return_predicts_the_last_half-hour_return.pdf)
- Predictability: "The predictive R2 of the first half-hour return on the last half-hour return is 1.6%"; "For out-of-sample (OOS) predictability, the R2 is 1.2% using the first half-hour return as the only predictor, and 1.8% when this predictor is combined with the twelfth half-hour return predictor." — [WP PDF](https://c.mql5.com/forextsd/forum/173/intraday_momentum_-_the_first_half-hour_return_predicts_the_last_half-hour_return.pdf)
- Timing strategy: "the average return of the timing strategy using the sign of the first half-hour return is 6.67% per annum with a standard deviation of 6.19%. The Sharpe ratio is thus 1.08, which is remarkable compared to a level of 0.29 of a daily Buy-and-Hold strategy". An always-long last half-hour earns "only −1.11%". The success rate is "54.37%". — [WP PDF](https://c.mql5.com/forextsd/forum/173/intraday_momentum_-_the_first_half-hour_return_predicts_the_last_half-hour_return.pdf)
- Transaction costs:
  - Entry is costed at the 3:30pm ask (bid) for longs (shorts). The exit has no spread: "Since the closing of the SPY is uniquely traded at the market clearing price for all the buys and sells, there will be no bid/ask spread effect for the price at 4:00pm".
  - Commissions are excluded: "We ignore the commission component of the transaction costs."
  - Post-decimalization: "the average return reduces to 4.46% per annum, 2.47% lower than the average return before transaction costs".
  - Post-2005: "The average return of market timing using the first half-hour return is 6.52% after transaction costs compared with 7.96% before transaction costs". The spread "stabilized at around 1.2 basis point after 2005".
  — [WP PDF](https://c.mql5.com/forextsd/forum/173/intraday_momentum_-_the_first_half-hour_return_predicts_the_last_half-hour_return.pdf)

**Baltussen, Da, Lammers & Martens (JFE 142(1):377–403, 2021)**
- Abstract: "Hedging short gamma exposure requires trading in the direction of price movements, thereby creating price momentum. Using intraday returns on over 60 futures on equities, bonds, commodities, and currencies between 1974 and 2020, we find strong market intraday momentum everywhere. The return during the last 30 minutes before the market close is positively predicted by the return during the rest of the day (from previous market close to the last 30 minutes). The predictive power is economically and statistically highly significant, and reverts over the next days. We provide novel evidence that links market intraday momentum to the gamma hedging demand from market participants such as market makers of options and leveraged ETFs." — [Paper PDF](https://academicweb.nd.edu/~zda/intramom.pdf)
- Coverage: "17 developed markets equity index futures ... 16 developed market bond futures ... 21 commodity futures ... and 8 currency futures. Our sample period covers almost 45 years from December 1974 to May 2020." The paper adds: "This effect is robust over time across our sample period of 1974 to 2020". — [Paper PDF](https://academicweb.nd.edu/~zda/intramom.pdf)
- On Gao et al.: "rROD has higher out-of-sample R-squares than rONFH". Here rROD is the return from the previous close to 30 minutes before the close, and rONFH is the first-half-hour return. — [Paper PDF](https://academicweb.nd.edu/~zda/intramom.pdf)
- Trading results (Table 6, equity index futures, 1/N portfolio):

  | Strategy | Avg return | Std dev | Sharpe | Success rate |
  |---|---|---|---|---|
  | η(rROD) | 6.86% | 3.96% | 1.73 | 0.55 |
  | η(rONFH) | 4.21% | 3.95% | 1.07 | 0.55 |
  | Always Long | 0.44% | 4.20% | 0.11 | – |
  | Buy & Hold | 8.76% | 17.29% | 0.51 | – |

  η(rROD) Sharpe ratios in other asset classes: government bonds 1.62, commodities 1.42, currencies 0.87. — [Paper PDF](https://academicweb.nd.edu/~zda/intramom.pdf)
- Costs: "Note that we do not consider transaction costs. Given that trading on market intraday momentum requires frequent rebalancing, the strategy as presented might not be exploitable to many investors after accounting for transaction costs ... exploiting the effect in the S&P 500 futures yields a positive net Sharpe ratio when we assume transaction cost equal to a tick (a cost level faced commonly by advanced investors in the S&P 500 futures market)." No net Sharpe number is given in the text. — [Paper PDF](https://academicweb.nd.edu/~zda/intramom.pdf)
- The most recent part of their sample: "the market intraday momentum strategy also performs strongly during the last four months of our sample (February to May, 2020)". — [Paper PDF](https://academicweb.nd.edu/~zda/intramom.pdf)

**Post-publication and replication evidence**
- Zarattini et al.'s characterisation of Rosa (2022), which is second-hand: "Rosa [7] analyzes additional data post-2013, noting a decline in predictability, which he attributes to market adaptations or the ephemeral nature of previously exploitable inefficiencies. His application of a Markov-switching model underlines how the intraday momentum's effectiveness is contingent upon volatile market regimes." — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Rosa, C. (2022), "Understanding intraday momentum strategies", J. Futures Markets 42(12):2218–2234 (snippet only, abstract level): evaluates the out-of-sample performance of using the overnight return to forecast the last half-hour. Paraphrased from a search summary, not quoted: calendar-time evaluation can mislead when returns are time-varying, and a strategy that uses thresholds earns more than one that is always active. — [IDEAS](https://ideas.repec.org/a/wly/jfutmk/v42y2022i12p2218-2234.html)
- Zarattini et al. argue that "a strategy confined to trading only after 15:30 may prove to be suboptimal". Their FAQ also says "trends tend to pause during lunchtime, they resume strongly from 14:00 until market close." — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)

### Inferences
- **The cleanest candidate for the repo's infrastructure.** The Gao/Baltussen rule runs on Alpaca SIP 1-minute SPY/QQQ/IWM bars: go long or short at 15:30 by the sign of the return from the previous close to 15:30, and exit at the close. It trades once a day in the most liquid instruments and is a single parameter-free rule.
- **Caveat: closing fill.** The papers' exit assumes the official closing (auction) price with no spread. A 1-minute bar's 15:59 close is not the auction print, and a market-on-close order has its own submission cutoffs. A replication should model an MOC fill or a spread on exit.
- **Caveat: commissions.** Gao et al. ignore commissions. At IBKR-style per-share rates, the per-trade edge of a few basis points needs checking: the 6.52% a year post-2005 corresponds to roughly 2.6 bp per day over about 252 trading days. That is derived arithmetic, not a stated figure.
- **Post-publication evidence is the key unknown.** The 2014–2026 window is post-sample for Gao et al., and June 2020 to 2026 is post-sample for Baltussen et al. The repo can measure both directly.

### Gaps
- No verified independent study of US SPY or ES intraday momentum after 2020 was found with net-of-cost results.
- The "0DTE era" effect is unknown. Searches found no study linking 0DTE options to the strength of last-half-hour momentum.
- Rosa (2022) was not read in full. The decline claim comes through Zarattini et al.'s summary.
- Search snippets mentioned cross-country replications: Li, Sakkas & Urquhart (2022, J. Financial Markets), and Limkriangkrai, Chai & Zheng (2023, Pacific-Basin Finance Journal), which reported a weaker effect in APAC. Neither was opened, so their numbers are unverified.

## 4. Overnight vs intraday returns — Lou, Polk & Skouras (2019); Boyarchenko, Larsen & Whelan (2023, RFS "The Overnight Drift"); tradability net of costs

### Takeaway
**Boyarchenko et al.**
- US equity-index returns concentrate in the 02:00–03:00 ET window around the European open: 3.7% a year, positive in 20 of 23 years since 1998.
- After bid-ask costs, the unconditional long in ES futures from 2:00 to 3:00 drops from Sharpe 1.1 to **−0.5**, and the window from 1:30 to 3:30 from 1.3 to 0.3.
- Only a conditional "buy-the-dip" version, triggered by negative closing order imbalance, keeps a net Sharpe of 1.1 over 2004–2020. It needs futures and signed order-flow data.

**Lou-Polk-Skouras** is a cross-sectional decomposition of anomaly returns, not a tradable intraday rule.

**NightShares**: a real-world ETF built to harvest the "night effect" closed in 2023, down since inception (snippet only).

**Tier A** for the phenomenon. Tradable only conditionally, and **not with an equity-only Alpaca account**.

### Cited Findings
**Boyarchenko, Larsen & Whelan (NY Fed Staff Report 917, revised August 2022; published RFS 36(9):3502–3547, 2023)**
- Abstract: "This paper documents that U.S. equity returns are large and positive during the opening hours of European markets. These returns are pervasive, economically large, and highly statistically significant. Consistent with models of inventory risk, we demonstrate a strong relationship with order imbalances at the close of the preceding U.S. trading day." — [NY Fed SR 917](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf); [RFS record](https://econpapers.repec.org/RePEc:oup:rfinst:v:36:y:2023:i:9:p:3502-3547.)
- Magnitude: "the largest positive returns are between 2:00 and 3:00 - the opening of European markets in U.S. Eastern Time terms (ET) - averaging 3.7% on an annualized basis (1.48 basis points per day)". Persistence: "they are positive in 20 out of 23 years since 1998 and statistically significant in 17 of these." — [NY Fed SR 917](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf)
- Tradability, with costs from bid-ask quotes: "Pre-transaction costs, a trading strategy that goes long the S&P 500 futures between 2:00 and 3:00 earns a Sharpe ratio of 1.1 and accounting for bid-ask spreads this reduces to −0.5. Extending the trading interval to the sub-period between 1:30 – 3:30 increases the pre-transaction cost Sharpe ratio to 1.3 but with an associated post-transaction Sharpe ratio equal to 0.3." The authors also state "the documented high frequency return patterns of this paper are not easily profitable". — [NY Fed SR 917](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf)
- Strategy definitions: "long CTO: t1 = 16:15 → t2 = 9:30"; "long OTC: t1 = 9:30 → t2 = 16:15"; "long OD+: t1 = 1:30 → t2 = 3:30".
  - BtD "holds the e-mini during the OD+ period but only on trading days following a negative order flow at market close (RSV close t−1 < 0). We report findings for the sample period 2004.1 — 2020.12".
  — [NY Fed SR 917](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf)
- Before costs: "Holding the ES contract continuously (the CTC strategy) since 2004.1 has yielded an average yearly return of 8.9% with a Sharpe ratio of 0.42 ... On an annualized basis, CTO returns averaged 4.6% and OTC returns averaged 4.2%." — [NY Fed SR 917](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf)
- After costs: "Returns on all simple strategies are significantly lower and only the OD+ strategy has a positive Sharpe ratio. However, the BtD strategy remains highly profitable (Sharpe ratio of 1.1) because it only pays the bid-ask spread on half the trading days when returns are higher." — [NY Fed SR 917](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf)

**Lou, Polk & Skouras (JFE 134(1):192–213, 2019)**
- Opening sentence of the abstract: "We link investor heterogeneity to the persistence of the overnight and intraday components of returns." The rest, paraphrased by the fetch tool: across 14 trading strategies, profits are earned either entirely overnight or entirely intraday, usually with opposite signs, and the authors call this a "tug of war". — [EconPapers](https://econpapers.repec.org/RePEc:eee:jfinec:v:134:y:2019:i:1:p:192-213)
- Snippet only: "profits are earned entirely overnight (for reversal and several momentum strategies) or entirely intraday". The patterns are "extremely robust across subsamples and are stronger for large-cap and high-price stocks". — [EconPapers](https://econpapers.repec.org/RePEc:eee:jfinec:v:134:y:2019:i:1:p:192-213); [Alpha Architect summary](https://alphaarchitect.com/2015/02/overnight-momentum-vs-intraday-momentum/)

**Real-world product test (Tier C, snippet only)**
- NightShares 500 ETF (NSPY): the last day of trading was July 31, 2023, with about $3.7 million in assets. It had "dropped 6.9% on a total return basis" since inception, against a 22% rise in the S&P 500. — [etf.com](https://www.etf.com/sections/news/2-nightshares-etfs-close-after-struggling-gain-traction); [SEC 497 supplement](https://www.sec.gov/Archives/edgar/data/1199046/000158064223003676/nightshares497s.htm); [Bloomberg](https://www.bloomberg.com/news/articles/2023-07-19/-night-effect-funds-to-shut-down-with-overnight-returns-elusive)

### Inferences
- **The 2:00–3:00 ET drift is out of scope for this bot.** It is an ES-futures phenomenon whose unconditional version loses money after spreads. Alpaca equity accounts cannot trade it, and 1-minute bars carry no signed closing order flow (RSV), which the profitable BtD variant needs.
- **Buy close / sell open in index futures**: CTO earned 4.6% a year before costs over 2004–2020, close to OTC's 4.2%. After costs, the paper reports only OD+ (and BtD) with positive Sharpe among the strategies tested. So a plain CTO hold in ES does not stand out net of costs in this source.
- **Not a day trade**: for equities or ETFs, a close-to-open hold is an overnight position with gap risk. The NightShares closure is weak real-world evidence that harvesting the overnight effect through an ETF wrapper did not pay over 2022–2023.

### Gaps
- The final RFS version's numbers may differ from SR 917, which is the only version read. A search summary of the EconPapers record also listed Stefano Giglio alongside the three authors. That is probably the handling-editor field, and it is unverified.
- No independent post-2022 test of the overnight drift or the BtD strategy was found.
- The NightShares figures are snippet-level and were not verified against the fund documents.

## 5. Pre-FOMC announcement drift (Lucca & Moench 2015) — did it persist after publication?

### Takeaway
The original result (1994–2011) was that the 24 hours before scheduled FOMC announcements produced more than 80% of the US equity premium. A peer-reviewed follow-up extending the sample to December 2019 finds that the drift "essentially disappeared after 2015". Later work is mixed and was only snippet-verified. **Tier A for decay**: this is a published anomaly whose post-publication evidence points to near-zero, and it was not costed.

### Cited Findings
- Lucca & Moench (NY Fed Staff Report 512; published J. Finance 70(1), 2015):
  - "Since the Federal Open Market Committee (FOMC) began announcing its policy decisions in 1994, U.S. stock returns have on average been more than thirty times larger on announcement days than on other days. Surprisingly, these abnormal returns are accrued before the policy announcement."
  - "The excess returns earned during the twenty-four hours prior to scheduled FOMC announcements ... account for more than 80 percent of the equity premium over the past seventeen years."
  - The abstract says similar results hold for major global equity indexes, but not for other asset classes or other macro announcements.
  — [EconPapers SR 512](https://econpapers.repec.org/RePEc:fip:fednsr:512)
- Kurov, Wolfe & Gilbert (Finance Research Letters 40, 2021, DOI 10.1016/j.frl.2020.101781): "Lucca and Moench (2015) document large average excess returns in U.S. equities before scheduled Federal Open Market Committee (FOMC) meetings from September 1994 to March 2011 ... We extend the sample to December 2019. We find that after first appearing before FOMC announcements accompanied by the Fed Chair press conferences, the pre-FOMC drift essentially disappeared after 2015 in both announcements accompanied by press conferences and announcements not accompanied by press conferences. We discuss a possible explanation for this change: reduced uncertainty." — [IDEAS](https://ideas.repec.org/a/eee/finlet/v40y2021ics1544612320315956.html)
- Snippet only:
  - Cujean (seminar abstract, 2023) reports the same disappearance and attributes it to "the rise of market noise" rather than better Fed guidance. — [USI seminar page](https://www.eco.usi.ch/en/node/9417)
  - Ignatieva & Ohashi (Applied Economics 57(17), 2025) still find a pre-FOMC drift in equities but describe the effect as short-lived. — [IDEAS](https://ideas.repec.org/a/taf/applec/v57y2025i17p2021-2037.html)
  - Indriawan, Jiao & Tse (J. Banking & Finance, 2021) report no pre-FOMC drift in long-term US and German bond futures. — [bepress](https://works.bepress.com/yiuman-tse/141)

### Inferences
- **Low priority**: with about 8 scheduled meetings a year and a post-2015 drift near zero, there is little to gain. It is cheap to verify on Alpaca SIP SPY 1-minute bars, since FOMC dates are public and the window is a defined pre-announcement intraday hold.

### Gaps
- The widely quoted "49 basis points" average 24-hour pre-FOMC S&P 500 return appeared only in search snippets and was not verified in a primary text this session.
- No 2020–2026 update with intraday SPY data was found.
- No study costed the trade.

## 6. Gap trading (fill vs continuation), VWAP reversion, intraday short-term reversal, late-day momentum

### Takeaway
- **Opening gaps (fade vs continuation)**: the best evidence read is a 2026 master's thesis (daily data, 2011–2024, Tier B/C). It finds a robust gap-reversal: large gap-ups give back intraday, strongest in **small, illiquid stocks**. That is a gross alpha of 1.5465% a day that turns to **−0.6564% a day net** of Corwin-Schultz spreads and 20 bp/day commission.
- **VWAP**: the only cost-stated VWAP evidence is the authors' own trend-following study, a VWAP cross on QQQ with no slippage stated (Tier B−). No rigorous evidence for VWAP *reversion* was found.
- **Late-day momentum**: this is the Gao/Baltussen effect in section 3.
- **Cross-sectional half-hour periodicity** (Heston-Korajczyk-Sadka) exists for single stocks but does not aggregate to the index level.

### Cited Findings
**Gap reversal (Vainio, University of Turku master's thesis, 25.5.2026)**
- Abstract:
  - "Using a large dataset of daily U.S. stock data from 2011 to 2024, the study tests whether overnight returns, measured from the previous closing price to the opening price, systematically predict the same-day intraday returns".
  - "stocks that gap up significantly overnight tend to give back a measurable fraction of that gain during the subsequent trading session, and vice versa"
  - "The reversal is strongest in small, illiquid stocks and intensifies during periods of elevated, market-wide uncertainty, as measured by the VIX"
  - "after estimating bid-ask spreads and trading commissions, the net alpha becomes clearly negative ... The reversal appears to be a structural feature of opening price formation in U.S. equity markets rather than an exploitable inefficiency."
  — [Vainio 2026 thesis PDF](https://www.utupub.fi/bitstreams/88057d2a-1ee8-4c05-9592-c535a21b502c/download)
- Strategy and costs (Table 7):
  - Long the lowest overnight-return centile (P1) and short the highest (P100), equal-weighted and rebalanced daily.
  - "Alpha (% per day) 1.5465*** (26.80)" gross versus "-0.6564*** (-12.58)" net, over 3,521 observations.
  - "Commission is modeled at 5 basis points per one-way trade ... for a total of 20 basis points per day across four one-way trades ... No borrow cost is assumed for the intraday short leg."
  — [Vainio 2026 thesis PDF](https://www.utupub.fi/bitstreams/88057d2a-1ee8-4c05-9592-c535a21b502c/download)
- Prior gap literature (snippet only, not read; the MDPI page returned HTTP 403): a 2025 J. Risk & Financial Management paper using 5-minute data for 2013–2023 notes "Some studies note the limited profitability once transaction costs and risk are fully accounted for," citing Plastun et al. (2020), which used daily US data for 1928–2018. — [MDPI JRFM 18(3):132](https://mdpi.com/1911-8074/18/3/132)

**Intraday periodicity and reversal**
- Baltussen et al. on Heston, Korajczyk & Sadka (2010): "The return of a stock over a half-hour trading interval today positively and significantly predicts its return during the same interval tomorrow and on subsequent days, potentially up to 40 days." At the market level, the coefficient on yesterday's last half-hour is "negative and significant among equity index futures, suggesting that intraday seasonality in the cross-section of individual stocks does not aggregate up to time-series intraday seasonality at the market level." — [Baltussen et al. PDF](https://academicweb.nd.edu/~zda/intramom.pdf)

**VWAP**
- Concretum VWAP paper (Zarattini & Aziz 2023), via the fetch tool:
  - Rule: it "enters long positions when price trades above the VWAP and opens short positions when it falls below it".
  - Sample: January 2, 2018 to September 28, 2023, with $25,000 starting capital.
  - QQQ: $192,656, 671% total, MDD 9.4%, Sharpe 2.1, "net of commissions". The commission rate and slippage are not stated on the page.
  - TQQQ: about $2,085,417, or 8,242%.
  - QQQ buy-and-hold: 126%, MDD 37%, Sharpe 0.7.
  — [Concretum VWAP page](https://concretumgroup.com/volume-weighted-average-price-vwap-the-holy-grail-for-day-trading-systems/)
- VWAP as a stop rather than a signal: in Beat the Market, adding a VWAP trailing stop raised the Sharpe ratio "from 0.61 to 1.24" and changed skewness "from -1.24 to 1.29". — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)

**Late-day and pattern conditioning**
- In BTM's pattern table, intraday momentum after a "Trend" day earned "-2" bp a day (t −0.24, n = 215), against unconditional 12 bp (t 5.34) and NR4 22 bp (t 5.14). — [BTM PDF](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)

### Inferences
- **Fading gappers**: the evidence says the gap-reversal is real in daily open-to-close data and strongest exactly where the bot operates (small, illiquid names), but negative after spreads.
  - The thesis also assumes fills at the open and close prints and no borrow cost, so the true net result for shorting gappers is likely worse than the reported −0.66% a day.
  - This is consistent with the bot's own negative result: in small illiquid gappers, the statistical pattern exists in both directions (continuation for the few, reversal on average), but costs dominate.
- **VWAP reversion has no rigorous published support** in the sources found. Published VWAP evidence is trend-following (price above or below VWAP), mostly author-run, and the QQQ result rests on unstated slippage.

### Gaps
- No peer-reviewed intraday (1-minute) gap-fill study of US stocks or ETFs with explicit costs was found. Plastun et al. (2020) and the 2025 JRFM paper were not read in full.
- No VWAP-reversion study was found.
- No independent replication of the Concretum VWAP result was found. QuantConnect backtest pages exist but were not read.

## 7. Academic evidence on day trading high-relative-volume small caps / momentum ignition / low-float runners

### Takeaway
No source found documents a cost-robust edge in day trading sub-$5, low-float runners. The best-supported intraday "stocks in play" result (section 1) explicitly excludes them (price >$5, ADV >1M). Population studies of actual day traders point the other way:
- **Taiwan**: fewer than 1% are predictably profitable net of fees.
- **Brazil**: 97% of persistent futures day traders lost money.
- **US Robinhood**: herding into attention stocks forecasts negative returns.

All three were snippet-verified only. They support, rather than contradict, the bot's negative after-cost result. No academic work on "momentum ignition" was found this session.

### Cited Findings
- Barber, Lee, Liu & Odean, "The Cross-Section of Speculator Skill: Evidence from Day Trading", J. Financial Markets 18 (2014), Taiwan, 1992–2006 (snippet only):
  - "less than 1% of the total population of day traders is able to predictably and reliably earn positive abnormal returns net of fees".
  - The top 500 traders earn 61.3 (37.9) bp a day before (after) fees.
  - A companion paper reports "the aggregate performance of day traders net of fees is negative in each of the 15 years that we study".
  — [Berkeley working paper](https://faculty.haas.berkeley.edu/odean/papers/day%20traders/Day%20Trading%20Skill%20110523.pdf); [EconPapers](https://econpapers.repec.org/RePEc:eee:finmar:v:18:y:2014:i:c:p:1-24)
- Chague, De-Losso & Giovannetti, "Day trading for a living?" (FGV EESP working paper 2019, updated 2020), Brazilian equity futures (snippet only):
  - Of individuals who started in 2013–2015 and persisted at least 300 days, "97% of them lost money, and only 0.4% earned more than a bank teller".
  - CXO Advisory: 19,646 individuals began, and 1,551 (7.9%) persisted more than 300 sessions.
  - Versions conflict on the bank-teller or minimum-wage share: 0.4% (EconPapers), 0.5% (CXO, June 2020 update) and 1.1% (Bloomberg).
  — [EconPapers](https://econpapers.repec.org/RePEc:spa:wpaper:2019wpecon47); [CXO](https://www.cxoadvisory.com/investing-expertise/day-trading-a-bust/); [BloombergQuint](https://www.bloombergquint.com/onweb/day-traders-in-brazil-study-would-ve-done-better-with-9-to-5-job)
- Barber, Huang, Odean & Schwarz, "Attention-Induced Trading and Returns: Evidence from Robinhood Users" (snippet only):
  - "intense buying by Robinhood users forecast negative returns".
  - One version: "average 20-day abnormal returns are -4.7% (-19.6%) for the top stocks purchased each day (extreme herding events)". Another version reports five-day figures of −3% (−6%).
  — [SSRN copy](https://www.smallake.kr/wp-content/uploads/2020/12/SSRN-id3715077.pdf)
- The Stocks in Play ORB universe requires "The opening price had to be above $5" and "at least 1,000,000 shares per day". Its strongest per-trade figure, "0.38R" at relative volume above 30x, is in that liquid universe and net of commission only. — [Zarattini, Barbon, Aziz PDF](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content)
- The overnight-to-intraday gap reversal "is strongest in small, illiquid stocks", and it is net negative after costs. — [Vainio 2026 thesis PDF](https://www.utupub.fi/bitstreams/88057d2a-1ee8-4c05-9592-c535a21b502c/download)

### Inferences
**Cross-strategy evidence tiers (synthesis from sections 1–7)**

| Strategy | Tier | Costs in source | Independent / post-publication evidence | Testable on Alpaca 1-minute bars? |
|---|---|---|---|---|
| Market intraday momentum (Gao; Baltussen) | A | Spread at entry; close assumed spread-free; no commission (Gao). None (Baltussen; qualitative "one tick") | Baltussen extends to 2020 across 60+ futures; Rosa (2022) reportedly weaker post-2013; nothing verified after 2020 | Yes (SPY/QQQ/IWM). Model the MOC fill |
| Beat the Market noise area + VWAP stop (SPY) | A/B | $0.0035/sh + $0.001/sh slippage; I-Star re-run | Author-run simulated continuation May 2024–Jan 2025; no independent replication found | Yes (open-source code exists) |
| 5-min ORB on Stocks in Play | B | $0.0035/sh commission only; no slippage, spread or borrow | QuantConnect, 2016 only, no fee model | Yes, with a full-universe 1-minute history |
| 5-min ORB on QQQ/TQQQ | B, contradicted | $0.0005/sh; "no slippage" | MQL5 2026: gross reproduced, net ≈ 0 | Yes |
| Overnight drift, 2–3am ET in ES | A | Bid-ask included: unconditional net Sharpe −0.5; BtD net 1.1 | None found after 2020 | No (futures plus order-flow data) |
| Pre-FOMC drift | A (decayed) | Not costed | Disappeared after 2015 (Kurov et al.) | Yes, but little remains to harvest |
| Gap fade in small/illiquid stocks | B/C | Spread + 20 bp/day: net −0.66%/day | Single 2026 thesis | Yes (gapper days) |
| VWAP cross on QQQ | B− | "net of commissions"; slippage unstated | None verified | Yes |

- **Pattern across the evidence**: wherever an independent party added realistic costs, the gross edge in single-name or small-instrument intraday rules shrank to zero or below (QQQ ORB on index CFDs, the unconditional overnight drift, the gap fade). The rules that keep positive net figures in the sources trade the most liquid index products once or twice a day: SPY/ES last-half-hour momentum and the BTM noise area. Both have a market-structure explanation (gamma hedging, leveraged-ETF rebalancing).
- **Fit with the bot's history**: this is consistent with the bot's measured negative expectancy in low-float runners, and none of the sources contradicts that result. The academic retail-trader evidence suggests skill-based profitability in day trading is rare (under 1% in Taiwan).

### Gaps
- No academic paper on "momentum ignition" or on low-float, sub-$5 intraday runners with a cost-inclusive strategy test was found this session.
- The Barber et al., Chague et al. and Robinhood figures are snippet-level and should be verified against the published versions before quoting.
- No study was found measuring short-borrow availability or cost for intraday shorts in high-relative-volume small caps. That is relevant to any fade strategy and to the short half of the Stocks in Play ORB.
