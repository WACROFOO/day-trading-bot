# What forums say works for automated retail trading bots (2022–2026), and the evidence behind it

## Q1. Which strategy families recur as "working", and what evidence do posters show? (graded A–D)

### Takeaway
I could not read Reddit at all. reddit.com blocks this research tool: WebFetch returned "unable to fetch from www.reddit.com", and a domain-restricted search returned "domains are not accessible to our user agent". So none of the claims below come from r/algotrading, r/thetagang, r/Daytrading and the other subreddits. They come from Hacker News, Elite Trader, the Collective2, QuantConnect, Quantopian-archive and Option Alpha forums, practitioner blogs, and news coverage. On those sources, no strategy family had a multi-year, independently verified (grade A) retail *bot* record. The most substantial live records I found were these:
- a practitioner's own multi-rule futures system (trend following plus carry), live about 9 years, self-published and with no broker statements (B−);
- a vendor's aggregate of live user-bot 0DTE iron condor and iron butterfly trades (B, vendor-reported, returns measured on premium, fees not netted);
- one manual 0DTE iron condor trader's log of 9,100 trades over almost five years, with no statements (B−).

Everything else was backtests (C) or bare claims (D). That includes ETF mean reversion, opening range breakout (ORB) on stocks in play, Ross Cameron-style momentum automation, grid bots and funding-rate arbitrage.

### Cited Findings

**Trend following / multi-rule systematic futures**
- **Rob Carver, practitioner blog, 5 May 2023**, "Trading and investing performance year nine – part 2: Futures trading":
  - **Result for the year:** "Net futures trading: -8.7%" (the table shows "-8.71%" for 2022–2023, against Bench1 5.0% and Bench2 -1.30%).
  - **Whole record:** "SR 0.58" for the full 2014–2023 track record.
  - **Rules traded:** trend following, carry, skew, mean reversion and relative carry.
  - **Live costs vs backtest:** "total costs of 90bp", against a backtest of "around 1% a year". On the live curve against the backtest: "you can see when I went on holiday, but interestingly we end up in exactly the same place."
  - **Basis of the figures:** "All figures are as a % of my notional capital, which will usually be more than I have in my account". No broker statement is mentioned.
  - **Setup:** he currently trades "dynamic optimisation with over 100 instruments", against an earlier "static optimisation with less than 30".
  - Source: [qoppac.blogspot.com, 2023-05-05](https://qoppac.blogspot.com/2023/05/trading-and-investing-performance-year.html)
- **Carver on short records (2016 post, quoted via a search summary; I did not open the page):** "even a few years worth of live trading performance may not tell you with much statistical significance whether you are good or just lucky (or both)." — [qoppac 2016/04 archive](https://qoppac.blogspot.com.es/2016/04/)
- **HN user module0000 (April 2018, before the 2022 window), on commodity futures:** "Short answer: yes … not in the beginning, then a long period of breaking even, and eventual profitability." There are no numbers, so this is grade D. — [Ask HN: Anyone making money through algorithmic trading?, 2018-04-25](https://news.ycombinator.com/item?id=16922538)
- **Academic context, not a forum record:** "Two centuries of trend following" reports that the drift correction "decreases slightly the overall t-stat of the trend following performance to 5.0" (search snippet). — [arXiv 1404.3274](https://arxiv.org/pdf/1404.3274)
- **Elite Trader search:** a domain-restricted search for live retail trend-following journals turned up only an old S&P trend-system thread with a 1990–2000 backtest. Its poster said the system has no edge "so it could fall apart at anytime". — [Elite Trader thread 9828](https://www.elitetrader.com/et/threads/sp-trend-following-system.9828/)

**ETF mean reversion (RSI(2), IBS)**
- **Pagonidis (NAAIM paper), search snippet:** IBS is "a strong and consistent predictor of close-to-close returns for equity ETFs trading in the U.S.", and these results are "generally not present in overseas markets". Grade C (research backtest). — [NAAIM PDF](https://www.naaim.org/wp-content/uploads/2014/04/00V_Alexander_Pagonidis_The-IBS-Effect-Mean-Reversion-in-Equity-ETFs-1.pdf)
- **QuantifiedStrategies RSI mean reversion on QQQ (search snippet, page not opened):** a backtested CAGR of "about 12.7%" against "about 9%" for buy-and-hold, with a 19.5% max drawdown. Grade C. — [quantifiedstrategies.com](https://www.quantifiedstrategies.com/rsi-mean-reversion-trading-strategy/)
- **QuantConnect forum, "Mean-Reversion effect in ETF price series":** a discussion of the IBS concept. The search showed no live results. — [QuantConnect forum 5675](https://www.quantconnect.com/forum/discussion/5675/mean-reversion-effect-in-etf-price-series/)
- **No live record found:** I found no thread with a multi-year live or brokerage-verified record for RSI(2) or IBS ETF bots (search across forums and blogs).

**Opening range breakout (ORB) on "stocks in play"**
Full detail is under Q4. In short, the evidence is the paper's backtest and a one-year QuantConnect replication. One forum member says he is paper trading it, and no results are posted. Grade C.

**Options premium selling (0DTE, iron condors, iron butterflies, the wheel)**
- **Option Alpha, "0DTE Options Strategies: Insights from 25k Trades"** (first published 18 Aug 2022, updated 18 Oct 2024 and 8 Feb 2025; authors Robert Cernera, Kirk Du Plessis, Steve Henry). Source: [optionalpha.com/blog/0dte](https://optionalpha.com/blog/0dte)
  - **Dataset:** "We analyzed over 25,000 0DTE option positions traded in the autotrading platform", described as "real trades in live markets".
  - **Iron butterflies:** 4,959 opened, 72% win rate, average return 4.62% of initial premium.
  - **Iron condors:** 3,170 opened, 63% win rate, average return 7.94% of initial premium.
  - **By entry time:** iron condors opened within two hours of the open averaged -0.36%. The 759 opened more than two hours after the open averaged a 37% return, and 67% of them expired worthless.
  - **What it does not say:** fees are not discussed, returns are measured on premium rather than on capital at risk, and there is no statement on whether users were profitable in aggregate. No date range is given.
- **Option Alpha community thread, "0DTE Iron Condor w Iron Fly Hedging" (search snippet, year not stated):** a poster "has been running this bot live since the beginning of April", with a live return "about 8%" (on SPY). Another poster says "SPX data still sucks". Grade D (self-reported, no statement). — [Option Alpha community](https://app.optionalpha.com/community/posts/0dte-iron-condor-w-iron-fly-hedging)
- **Option Alpha backtester page for an SPX iron condor (search snippet):** -$4,827.00 total P/L on $4,960.00 capital at risk, 52.3% win rate, profit factor 0.8. Grade C, and negative. — [Option Alpha backtest](https://app.optionalpha.com/zdte/backtester/test/ZT21740081074387151342)
- **Theta Profits, John Einar Sandvand** (dated 22 Feb 2026, originally published 2024). Grade B− for manual trading: self-reported live, no statements. Source: [thetaprofits.com](https://www.thetaprofits.com/my-most-profitable-options-trading-strategy-0dte-breakeven-iron-condor/)
  - **Size and period:** "a total of 9,100 trades with this strategy from April 2021 until February 2026".
  - **Win/loss profile:** "40% of the trades are wins and 60% are losses", and "the average win is more than double the average loss".
  - **Per-trade and monthly results:** "The average P/L per trade is 0.28%" (of risk), and "49 of 57 months have been profitable". Both stops were hit in "8.6% of my trades".
  - **Execution:** manual (stops set in Thinkorswim). On automation he says "I have been planning to test automation, but haven't gotten around to it yet."
  - **Not stated:** account size, drawdown figures, broker statement or third-party verification.
- **HN user thrwyaltdata (April 2018):** "My algorithm earned about 127% on an initial outlay of $30,000 from August of 2016 to the beginning of January 2018" (options selling on equities). Grade D. — [HN 16922538](https://news.ycombinator.com/item?id=16922538)
- **Wheel backtest (Dec 2025 report, low-quality source; search snippet):** 30-delta puts, 30-day expirations, 2015–2025. Result "Final $106,871, CAGR 1.03%, Max DD 15.08%". The report notes "0.00 sharpes are a bug". Grade C. — [glama.ai Quant-Companion report](https://glama.ai/mcp/servers/@Ademscodeisnotsobad/Quant-Companion-MCP/blob/69bda03318a3adee9cb1ed6be22eee58b031542c/backtest_results/OPTIONS_STRATEGIES_REPORT.md)
- **Wheel educator's claim (search snippet; one of two pages on the same Substack, I did not check which):** "most disciplined Wheel traders target 1–3% per month on deployed capital", and the strategy underperforms in a strong bull market. Grade D. — [wheelstrategy.substack FAQ](https://wheelstrategy.substack.com/p/the-wheel-strategy-faq) / [wheelstrategy.substack capital](https://wheelstrategy.substack.com/p/how-much-money-do-you-really-need)

**Crypto grid bots and arbitrage**
- **Grid bots, Coinmonks/Medium (search snippet):** a first-person account of testing grid bots from mid-2021. It reports losses from leveraged futures grid bots on 3Commas, and an unrealized loss after price fell back below the grid. Grade D. — [Medium/Coinmonks](https://medium.com/coinmonks/grid-bots-how-they-really-work-how-to-make-money-with-them-948b4439fa5f)
- **Grid bots, vendor and affiliate reviews:** these are favorable and are not performance tests. — [Benzinga Pionex review](https://www.benzinga.com/money/pionex-review)
- **HN, April 2018, all grade D and before the 2022 window** — [HN 16922538](https://news.ycombinator.com/item?id=16922538):
  - jmhyer123: "Over the last 3 months, January to March, I've had a return of just under 50% … I only turned it loose on about $250".
  - iliicit: "I made some good money (millions) in 2017 by algo trading crypto".
  - headmelted, on an abandoned arbitrage bot: "far too little juice in it for it to be worth the squeeze".
  - herve76, on an arbitrage bot: "It can make up to 500-1000 usd per day but not really much more" (no capital given).
  - lisbakke: "I've been working on it for 3 months and so far the bot is profitable".

**Funding-rate (delta-neutral) arbitrage**
- **Zipmex blog (search snippet):** "average annual returns of 19.26% with maximum drawdowns under 2% in 2025", attributed to professional delta-neutral strategies. The data source is not named. Grade D. — [zipmex.com](https://zipmex.com/blog/how-to-analyze-funding-rates-in-crypto/)
- **Medium guide (2026; search snippet):** cites a 2025 study in *Blockchain Research and Applications* reporting returns "up to 115.9% over 6 months". I did not verify the study, and the figure is a best case. Grade D. — [Medium @arbitrageghost](https://medium.com/@arbitrageghost/funding-rate-arbitrage-in-2026-the-complete-guide-with-real-calculations-40e6cf341e52)
- **Hummingbot:** its v1.27 release (April 2024) added a Funding Rate Arbitrage strategy template. That is tooling, not results. — [Hummingbot newsletter Apr 2024](https://hummingbot.substack.com/p/hummingbot-newsletter-april-2024)
- **Tutorial pages:** they present modelled, not live, yields. — [dev.to tutorial](https://dev.to/dead1786/how-to-build-a-funding-rate-arbitrage-bot-with-python-1ehh)

**LLM / "AI" bots (the 2025 version of news and sentiment bots)**
- **nof1 "Alpha Arena" Season 1** (ended 3 Nov 2025): six frontier models each traded crypto perpetuals with real money on Hyperliquid.
  - **Winner:** Qwen 3 Max finished first, +22.32% on its US$10,000 stake.
  - **Others (aggregator table):** DeepSeek V3.1 +4.89%, GPT-5 -62.66%, Gemini 2.5 Pro -56.71%.
  - **Losses overall:** the nof1 founder said "More than half ended up in the red", and nof1 called the season exploratory.
  - **Duration:** one write-up's title says "$60,000 in real money for 17 days".
  - **Caveat:** I took these figures from news and aggregators and did not check them against nof1.ai.
  - Sources: [Forklog](https://forklog.com/en/four-out-of-six-ai-models-suffer-losses-in-trading-tournament/); [Aurpay](https://aurpay.net/?p=23782); [Brainsum](https://san-1510.aid.brainsum.com/news/top-news/alibabas-qwen3-max-wins-nof1-ai-crypto-trading-challenge-22-gain); [Towards AI title](https://pub.towardsai.net/six-frontier-ai-models-traded-60-000-in-real-money-for-17-days-the-leaderboard-lied-to-everyone-9f73591a8d4b)

**Machine-learning and prediction bots**
- **HN user simonhughes22 (2018), who built arbitrage and prediction systems:** "once you factor in the trading fees, slippage and the spread, you will almost always lose money." — [HN 16922538](https://news.ycombinator.com/item?id=16922538)
- **Quantopian:** the paper shows ML used on backtest *features* to pick strategies, not ML trading signals. Nonlinear classifiers predicted out-of-sample performance at "R² = 0.17" (see Q3). — [Quantopian archive](https://quantopian-archive.netlify.app/forum/threads/q-paper-all-that-glitters-is-not-gold-comparing-backtest-and-out-of-sample-performance-on-a-large-cohort-of-trading-algorithms)

**Generic "my automated system makes money" claims (Elite Trader, 2024)**
- **Dna7272, 20 Sep 2024:** "I have an automated strategy that makes money 100% of cases." Grade D. No reply in that thread gives account size, years live, returns or drawdown. — [Elite Trader 381244](https://www.elitetrader.com/et/threads/do-automated-strategies-that-can-generate-consistent-profits-really-exist-worth.381244/)

### Inferences
- **Evidence grade by family** (my synthesis of the findings above):

| Family | Best evidence located | Grade |
|---|---|---|
| Trend following / multi-rule futures | Carver: about 9 years self-published live, SR 0.58 (2014–2023), -8.71% in 2022–23, % of notional, no statements | B− (live, no statements); C (academic) |
| ETF mean reversion (RSI(2) / IBS) | research and blog backtests only | C |
| ORB on stocks in play | paper backtest plus a 1-year QuantConnect replication; one member paper trading, no results posted | C |
| Ross-style small-cap momentum automation | code repos and Pine scripts, no results (Q4) | D |
| 0DTE iron condor / iron butterfly via bots | Option Alpha aggregate of live user bots (vendor; on premium; fees not netted) | B (vendor aggregate) |
| 0DTE breakeven iron condor (manual) | 9,100 trades, Apr 2021–Feb 2026, no statements | B− |
| Wheel | backtest (CAGR 1.03%); educator targets | C / D |
| Crypto grid | loss anecdote; vendor reviews | D |
| Crypto spatial arbitrage | 2018 HN anecdotes | D |
| Funding-rate arbitrage | vendor and blog yields, tutorials | D (C for models) |
| LLM bots | third-party-run live contest, 17 days, n=6, 4 of 6 lost | live, but statistically meaningless |
| ML prediction | cost warnings only | D |
| Pairs trading, momentum rotation | nothing located | — |

- **The families with real live data share a structure.** Both are diversified across many instruments (the 100+ futures) or across many trades with a defined payoff (0DTE spreads with stops). Neither is concentrated single-name intraday momentum. This is an observation from two records, not a test.
- **Even the best records have weak years.** Carver lost -8.71% in 2022–23. In the Option Alpha data, iron condors opened within two hours of the open averaged -0.36%. Entry-time effects are large, so a bot's timing rules matter as much as the strategy label.

### Gaps
- **No Reddit content of any kind.** Neither direct fetch nor domain-restricted search reached reddit.com. I made no attempt to get around this, and an archive-API attempt was blocked by the sandbox as bot-check circumvention. As a result:
  - no r/algotrading, r/thetagang, r/Daytrading, r/options, r/CryptoCurrency or r/BitcoinMarkets quotes;
  - no upvote counts;
  - no yearly "results" threads from r/thetagang.
- **Families with no forum evidence located:** momentum or sector rotation, pairs trading, and news/sentiment bots other than LLMs.
- **Elite Trader leads I did not open.** A search summary mentioned these claims but did not tie them to specific threads, so I have not cited them as findings: a live system producing "about 60% of its backtested average per trade over roughly 55 live trades"; an intraday momentum system with a "45% mean annual return" backtest that went live in June 2018; and an IBKR-API system with a "43% average annual return in backtests". Candidate threads: [Fully Automated Day Trading](https://www.elitetrader.com/et/threads/fully-automated-day-trading.322750/), [Automated Day Trading](https://www.elitetrader.com/et/threads/automated-day-trading.321589/), [T-REX 1.25+ profit factor](https://www.elitetrader.com/et/threads/automated-trading-system-with-1-25-profit-factor-im-t-rex.378941/), [If You Had a Profitable EA](https://www.elitetrader.com/et/threads/if-you-had-a-profitable-expert-advisor-ea-how-would-you-use-it.383095/).
- **Carver's later years not found.** His 2024 and 2025 annual reviews (years ten and eleven) did not appear in search, so his record after April 2023 is not stated here.
- **No France-specific forum evidence**, for example French broker access to US 0DTE options.

## Q2. Recurring failure causes in "lessons learned" posts and post-mortems, the r/algotrading wiki, and member surveys

### Takeaway
The r/algotrading wiki and FAQ, and the subreddit's top post-mortems, were not reachable. In the forums I could read (Hacker News, Elite Trader, Collective2, Quantopian), the recurring failure causes are these: overfitting and backtest Sharpe that does not persist; costs, slippage and spread swamping small edges; alpha decay and crowding as an edge becomes known or as capital scales; and psychological interference with the bot. I found no member survey of profitability for r/algotrading or any other forum.

### Cited Findings
- **Overfitting (Quantopian paper, 9 Mar 2016).** Backtest Sharpe "offer[s] little value in predicting" out-of-sample performance "(R² < 0.025)", and "the more backtesting a quant has done for a strategy, the larger the discrepancy". Forum replies on the same page:
  - Grant Kiehne: "the contest rules at the time strongly incentivized over-fitting backtests and long-only strategies."
  - Burrito Dan: "If you're getting a huge Sharpe ratio, then it's probably overfitting."
  - Jessica Stauth: "you really can't trust a model until you validate on hold out data."
  - Several commenters recommended holding out recent data, such as the last 6 months or 2 years, and testing on it once.
  - Source: [Quantopian archive thread](https://quantopian-archive.netlify.app/forum/threads/q-paper-all-that-glitters-is-not-gold-comparing-backtest-and-out-of-sample-performance-on-a-large-cohort-of-trading-algorithms)
- **The paper is still discussed on Reddit.** A search index lists an r/quant post dated "Apr 15 '25" with the slug "research_paper_from_quantopian_showing_most_of", seen on a mirror. I did not open it. — [listing (mirror URL)](https://redlib.hbubli.cc/r/quant/comments/1k05dp4/research_paper_from_quantopian_showing_most_of)
- **Costs (HN, 2018), simonhughes22:** "once you factor in the trading fees, slippage and the spread, you will almost always lose money." iliicit estimated "it will cost between 10k and 100k a month to run an HFT strategy fast enough" to compete in stocks. — [HN 16922538](https://news.ycombinator.com/item?id=16922538)
- **Not trusting the bot (HN, 2018), pfarnsworth:** "I lost about $100k doing algorithmic trading", with bets of a few thousand dollars per trade. A search summary attributes the loss mainly to not trusting the algorithm and cutting trades short. — [HN 16922538](https://news.ycombinator.com/item?id=16922538); [comment 16923294](https://news.ycombinator.com/item?id=16923294)
- **Alpha decay, crowding and scale (Elite Trader, 20 Sep 2024)** — [Elite Trader 381244](https://www.elitetrader.com/et/threads/do-automated-strategies-that-can-generate-consistent-profits-really-exist-worth.381244/):
  - d08: "Nothing works forever. If you have limited capital then by the time you scale it up, it will stop working", and "every niche gets more crowded over time as others discover your "edge"".
  - 2rosy: "But there's alpha decay which is the consistent part".
  - Amos.davis (the original poster): "Backtesting may "cater" to the market."
- **Degradation of listed strategies (Collective2 forum, Aug 2023)** — [C2 forum 16231](https://forums.collective2.com/t/are-there-any-c2-strategies-that-stay-profitable/16231):
  - Trillian (18 Aug): "I've watched some strategies make money for a few months, it's _always_ followed by substantial losses".
  - Matthew Klein of C2 (18 Aug): strategies "can be good for a while, but they inevitably tend to degrade over time."
- **Execution modelling (QuantConnect forum, ORB replication).** Yuri Lopukhov notes that stop placement timing differs between minute-resolution backtests and live trading. — [QuantConnect research 18444](https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/)
- **Blog post-mortems (search snippets; which claim belongs to which blog was not checked):**
  - A team's strong backtest failed live. After two years they had "3-4 strategies that are performing reliably (at least till now)".
  - Another developer lost money within about three months after tuning parameters on seen data, then adopted walk-forward testing on 5–6 years of data.
  - Sources: [venkatkunisetty substack](https://venkatkunisetty.substack.com/p/how-we-built-algorithmically-traded); [smartcrypto substack](https://smartcrypto.substack.com/p/how-i-developed-a-profitable-trading)
- **Surveys:** I found no profitability survey of r/algotrading members. A third-party stats page lists the subreddit at about 1.9 million members (search snippet). — [GummySearch r/algotrading](https://gummysearch.com/r/algotrading/)

### Inferences
- Across sources from 2016 to 2024, the failure causes named most often are the same three: overfitting, costs and slippage, and decay or crowding. Regime change appears mainly as "strategies degrade over time" rather than as a named cause. Data errors and look-ahead bias were not prominent in the forum pages I could read.

### Gaps
- **r/algotrading wiki and FAQ:** content not retrieved because of the Reddit block.
- **Most-upvoted Reddit post-mortems:** titles, dates and scores not retrieved.
- **Member polls:** none found on any forum.

## Q3. Community-level survival statistics (Collective2, Darwinex, Myfxbook/MQL5, Quantopian, other platforms)

### Takeaway
No platform publishes an official "share of strategies still profitable after N years" figure that I could find. The hard numbers available are these:
- **Quantopian (888 algorithms):** backtest Sharpe explains out-of-sample performance with R² < 0.025.
- **Collective2, 2009 snapshot:** median system -1.9% against +3.4% for the S&P 500 over 30 days; about 18% matched or beat it.
- **Collective2, 2023 member count:** of 19 strategies five or more years old on the Old Timers leaderboard, none was without a losing calendar year.
- **Alpha Arena:** 4 of 6 AI models lost money.
- **Darwinex, Myfxbook, MQL5:** no survival statistics located.

### Cited Findings
- **Quantopian, Wiecki, Campbell, Lent and Stauth, "All that Glitters Is Not Gold" (9 Mar 2016)** — [Quantopian archive](https://quantopian-archive.netlify.app/forum/threads/q-paper-all-that-glitters-is-not-gold-comparing-backtest-and-out-of-sample-performance-on-a-large-cohort-of-trading-algorithms):
  - **Data:** "a unique dataset of 888 algorithmic trading strategies developed and backtested on the Quantopian platform" with "at least 6 months of out-of-sample performance".
  - **Sharpe:** backtest Sharpe offers "little value in predicting" out-of-sample performance "(R² < 0.025)".
  - **Overfitting:** "the more backtesting a quant has done for a strategy, the larger the discrepancy".
  - **What did predict:** "higher order moments, like volatility and maximum drawdown", plus hedging, "show significant predictive value".
  - **ML selection:** nonlinear classifiers reach "R² = 0.17" on hold-out data, and a portfolio built on those predictions "performed significantly better out-of-sample".
  - **Data window (secondary summary):** 2010–2015, with "at least 6 to 12 months of true OOS". — [HedgeFundAlpha](https://hedgefundalpha.com/strategies/comparing-backtest-sample-performance-large-cohort-trading-algorithms/)
- **Collective2 forum, "Are there any C2 strategies that stay profitable?" (Aug 2023)** — [C2 forum 16231](https://forums.collective2.com/t/are-there-any-c2-strategies-that-stay-profitable/16231):
  - InteractiveAssets (18 Aug 2023), reviewing Old Timers strategies five or more years old: "There were zero strategies that didn't have at least one calendar year with a net loss … That was out of 19 strategies that survived to make it to the leaderboard."
  - newt (29 Aug 2023), who simulated "about 10-20 new strategies every month": "That would be more than 700-800 strategies in the last few years… all of them failed. There are just a handful of oldtimer strategies that still perform well after a few years." These are his own estimates.
  - Trillian (24 Aug 2023): "it's been a year and not a single strategy has turned a profit. Not one."
  - Matthew Klein of C2 (25 Aug 2023): "We have strategies on this site that have been around for 15 years", with drawdowns, but "they're generally positive". He gave no aggregate statistic.
- **CXO Advisory snapshot of Collective2 (31 Jul 2009, Steve LeCompte)** — [CXO Advisory](https://www.cxoadvisory.com/investing-expertise/collective2-a-marketplace-of-trading-systems/):
  - **Sample:** 193 active stock trading systems, returns through 29 Jul 2009.
  - **Returns:** the median 30-day return was -1.9%, against +3.4% for the S&P 500. About 18% matched or beat the index.
  - **Mortality:** "young systems appear to have a high mortality rate due to poor performance."
  - **Basis:** results are hypothetical ("All performance claims on this web site must be regarded as hypothetical") and exclude fees.
- **MQL5 Traders' Blog (19 Oct 2026), "Every signal list has already been filtered: survivorship in plain numbers" (search snippet).** It uses an *illustrative* 20-signal example in which 16 blow up and 4 remain. It suggests treating the share of signals older than two years as the rough survival rate "you are buying into". This is not an empirical count. — [MQL5 blog 777995](https://www.mql5.com/en/blogs/post/777995)
- **Darwinex: mechanics only, no survival rate (search snippets).**
  - All DARWINs are risk-normalised to 3.25–6.5% monthly VaR at 95%. — [help.darwinex.com](https://help.darwinex.com/the-risk-in-a-portfolio-of-darwins)
  - The Experience attribute needs at least 12 D-Periods to score 10/10. — [help.darwinex.com experience](https://help.darwinex.com/experience-attribute)
  - A third-party review says a DARWIN becomes investable after an 8-month track record (secondary source; may be outdated). — [propfirm201](https://propfirm201.com/firms/darwinex-zero)
- **Option Alpha (vendor aggregate of live user-bot trades):** see Q1. It gives win rates and average return on premium by structure, but no share of profitable users. — [optionalpha.com/blog/0dte](https://optionalpha.com/blog/0dte)
- **Alpha Arena Season 1:** Forklog headline "Four out of six AI models suffer losses in trading tournament". — [Forklog](https://forklog.com/en/four-out-of-six-ai-models-suffer-losses-in-trading-tournament/)
- **Strategy incubation as a filter (search snippets).** A NexusFi member: "incubation period is completed for 6 of my strategies. 3 of them failed and 3 of them passed". A secondary write-up says Kevin Davey cites a student survey in which 85–90% credit incubation with avoiding bad strategies or confirming good ones. That is a student opinion, not a pass rate. — [NexusFi](https://nexusfi.com/vendors-product-reviews/37240-kj-trading-systems-strategy-factory-2.html); [Algo Advantage podcast notes](https://algoadvantage.substack.com/p/036-kevin-davey-part-i-its-all-about)

### Inferences
- The figures point the same way. On Quantopian, backtest Sharpe barely predicts live performance. In 2023, Collective2's long-lived strategies all had losing years, and one member's forward simulations all failed. Listed-signal populations are survivor-filtered. So a published track record of under a few years says little, which matches Carver's own warning in Q1.

### Gaps
- **No official survival or failure rate found for:** Collective2, Darwinex, Myfxbook or MQL5 Signals.
- **No academic study found** of persistence among Collective2 or Myfxbook signal providers.
- **Option Alpha's later "230k trades" update** is referenced but was not read. — [optionalpha.com/blog/0dte](https://optionalpha.com/blog/0dte)

## Q4. Ross Cameron / Warrior Trading-style small-cap momentum automation, and ORB on "stocks in play" (Zarattini/Barbon/Aziz): any live results?

### Takeaway
I found no forum post in any accessible venue reporting live results for an automated Ross Cameron-style bot. Public artefacts are GitHub repos and TradingView scripts with single-day or idealised backtests and explicit slippage caveats. For ORB on stocks in play, the evidence is the authors' 2016–2023 backtest and a QuantConnect replication that tests only 2016. One forum member says he is paper trading it and posts no results, and other members report poor results in other years. I found no live or forward results.

### Cited Findings
- **GitHub "ross-cameron-trading-strategy" (search snippet):** describes itself as a fully automated system implementing "Ross Cameron's proven pullback strategy" for IBKR paper and live trading. Its backtester runs on a single trading day of 10-second bars. No results. — [GitHub woshishuaige2](https://github.com/woshishuaige2/ross-cameron-trading-strategy)
- **GitHub "Ross-Cameron-Trading-Strategy":** "Automated implementation of Ross Cameron day trading strategy - 3838 ticker scan, real catalyst detection, production-ready". Its backtest "assumes ideal conditions; live trading will have slippage/gaps" (search snippet). No results. — [GitHub stevesiow85](https://github.com/stevesiow85/Ross-Cameron-Trading-Strategy/tree/main)
- **TradingView "Warrior Trading Momentum Strategy" (search snippet):** gap-ups of 2% or more with volume confirmation. Its description says backtests differ from live because of slippage and execution delays. No results. — [TradingView](https://ru.tradingview.com/script/RuvGSExs-Warrior-Trading-Momentum-Strategy)
- **TradingView "Ross Cameron-Inspired Day Trading Strategy" (search snippet):** aimed at NSE/BSE indices, not US small caps. No figures. — [TradingView](https://kr.tradingview.com/script/TcCkGnoS-Ross-Cameron-Inspired-Day-Trading-Strategy)
- **TradingView "Ross Cameron 5 Pillars Filter":** checks relative volume ≥5x and daily change ≥10%. The author states they are not Ross Cameron. No results. — [TradingView](https://www.tradingview.com/script/mbqMf3pF-Ross-Cameron-5-Pillars-Filter/)
- **Warrior Trading's own claim, for discretionary trading rather than a bot (search snippet):** over "$20 million in profits (view broker statements)". This is the company's claim about Ross's manual trading. — [warriortrading.com](https://www.warriortrading.com/warrior-pro-info/)
- **A 2026 review (search snippet; I did not check whether it was Traders Union or Bullish Bears):** says Ross Cameron's approach needs over $25,000 to follow effectively. — [Traders Union](https://tradersunion.com/interesting-articles/warrior-trading-review/) / [Bullish Bears](https://bullishbears.com/warrior-trading-review/)
- **ORB on stocks in play, the paper (Zarattini, Barbon & Aziz, 2024), as summarised by the DanFin review (updated 29 Jul 2026)** — [DanFin](https://danfin.net/opening-range-breakout-research); [RePEc listing](https://ideas.repec.org/p/chf/rpseri/rp2498.html):
  - **Universe and period:** 2016–2023, "More than 7,000 US stocks".
  - **Costs:** commission $0.0035 per share.
  - **Base 5-minute ORB:** 29% total return, Sharpe 0.48.
  - **Top 20 by opening relative volume:** 1,637% total return, 41.6% annualised, Sharpe 2.81, 12% max drawdown, 48.4% hit ratio.
  - **What drives it:** the review says the paper "attributes most of the apparent edge to stock selection based on abnormal opening participation, not to the ORB rule in isolation".
  - **Validation:** "No clearly separated out-of-sample period". Neither paper "proves the returns reproduce unchanged in live trading". No live, forward or independent replication is reported.
- **Companion QQQ/TQQQ paper (Zarattini & Aziz), same review:**
  - **Period and costs:** Jan 2016–Feb 2023, commission $0.0005 per share, no slippage.
  - **QQQ:** 676% total, 33% annualised, Sharpe about 1.13, 22% max drawdown, 24% win rate.
  - **Caveat:** the 9,350% variant "may be unrealistic because the model assumes no slippage".
  - Source: [DanFin](https://danfin.net/opening-range-breakout-research)
- **QuantConnect replication ("Opening Range Breakout for Stocks in Play")** — [QuantConnect research 18444](https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/):
  - **Universe:** "The universe consists of the 1,000 most liquid US Equities that are trading above $5/share", with ATR above $0.50. It trades the 20 most "in play" names by relative volume.
  - **Entry at 9:35:** a stop-market order in the direction of the first 5-minute bar.
  - **Period and result:** only 2016 is tested. Sharpe 2.396 against 0.836 for SPY, beta -0.042.
  - **Not stated:** returns, drawdown, cost and slippage assumptions, and any out-of-sample test.
  - **Sensitivity:** 17 of 25 opening-range and universe combinations beat the benchmark Sharpe.
  - **Comments:**
    - Lars Klawitter: "I'm paper trading with this set of parameters right now" (no results posted).
    - Angus Li: "The backtest doesn't look good for other years."
    - Jack Pizza reports collapses during the dot-com period.
    - Mark Kust cites a win rate of roughly 17%.
- **An open-source ORB "stocks in play" bot** following the 2023 paper exists, with no results published. — [GitHub jlmn-code/bot_intradia_orb](https://github.com/jlmn-code/bot_intradia_orb)

### Inferences
- **Forums treat Ross-style automation as a coding project, not a proven strategy.** Every artefact found stops at code plus an idealised or single-day test, and the authors themselves flag slippage and gaps. The absence of posted live results is itself the finding, within the limits of the Reddit block.
- **ORB on stocks in play is the nearest "researched" cousin of small-cap momentum.** The review attributes the edge mainly to *selection by abnormal opening volume*, not to the breakout rule. QuantConnect members report weak results outside 2016 and a low win rate. Its evidence is therefore C-grade, and parts of it are contested.
- **The replication and the user's bot use different universes.** QuantConnect used the 1,000 most liquid stocks above $5. That is a different universe from sub-$20 low-float small caps, so the replication says little about the user's halting, thin-book names.

### Gaps
- **Reddit coverage missing:** no r/algotrading or r/Daytrading threads on automating Warrior Trading or Ross Cameron setups, or on ORB live results.
- **No independent live or forward record** of the Zarattini/Aziz ORB on stocks in play was found anywhere.
- **The authors' later papers, and any live track record from their firm (Concretum Group), were not checked.** — [Concretum papers](https://concretumgroup.com/papers/)

## Q5. What credible practitioners recommend for a small retail account that wants automation

### Takeaway
Direct, sourced recommendations were sparse in the forums I could reach. The consistent themes are four:
- treat short live records as statistically weak;
- hold out data and incubate a strategy before funding it;
- expect a long break-even period;
- accept that costs and slippage decide small-account viability.

There is one nuance: some niches are viable *only* at small size.

### Cited Findings
- **Carver (2016, quoted via search):** "even a few years worth of live trading performance may not tell you with much statistical significance whether you are good or just lucky (or both)." His own live setup, as of the 5 May 2023 post, is "dynamic optimisation with over 100 instruments", with figures stated as "% of my notional capital". — [qoppac 2016/04](https://qoppac.blogspot.com.es/2016/04/); [qoppac 2023-05](https://qoppac.blogspot.com/2023/05/trading-and-investing-performance-year.html)
- **Quantopian thread advice:** hold out recent data, for example the last 6 months or 2 years, and test on it once at the end. Wiecki: "you can't take a backtest Sharpe ratio at face value". — [Quantopian archive](https://quantopian-archive.netlify.app/forum/threads/q-paper-all-that-glitters-is-not-gold-comparing-backtest-and-out-of-sample-performance-on-a-large-cohort-of-trading-algorithms)
- **Kevin Davey's process (secondary summaries; some pages look auto-generated, so treat as low reliability):**
  - at least 100 independent trades in test plus out-of-sample before going live;
  - incubation of 6–12 months, or three to six months by other accounts;
  - a "sweet spot" of 20–30 algorithms for manageability.
  - Sources: [forex.in.rs](https://www.forex.in.rs/algorithmic-rules-blueprint); [Algo Advantage 036](https://algoadvantage.substack.com/p/036-kevin-davey-part-i-its-all-about)
- **Capacity favours small accounts in some niches (HN, 2018), andr:** some strategies are "only profitable with a small amount of money (up to a few millions)". — [HN 16922538](https://news.ycombinator.com/item?id=16922538)
- **Break-even period (HN, 2018), module0000:** "a long period of breaking even, and eventual profitability" (commodity futures). — [HN 16922538](https://news.ycombinator.com/item?id=16922538)
- **Scale-up decay (Elite Trader, 2024), d08:** "If you have limited capital then by the time you scale it up, it will stop working." — [Elite Trader 381244](https://www.elitetrader.com/et/threads/do-automated-strategies-that-can-generate-consistent-profits-really-exist-worth.381244/)
- **Entry timing (Option Alpha, vendor data):** iron condors entered later than two hours after the open did far better (+37% average return on premium, n=759) than those entered in the first two hours (-0.36%). — [optionalpha.com/blog/0dte](https://optionalpha.com/blog/0dte)

### Inferences
- **For a small automated account, the only practitioner-backed pattern with live data** (Carver's) is the opposite of a concentrated single-name intraday bot: many instruments, slower holding periods, and costs modelled and then confirmed live (90bp live against about 1% a year in backtest). This is one practitioner's record, not a consensus measurement.
- **For a France-based trader the timing is awkward.** The Option Alpha timing finding means a later-in-the-day entry window for SPY/SPX 0DTE structures. That lands in the European late afternoon or evening. Whether a French retail broker offers 0DTE SPX/SPY options was not researched.

### Gaps
- **Missing practitioner voices:** I found no sourced recommendations from the most-upvoted r/algotrading members on time frame, markets or position count, because of the Reddit block.
- **No sourced capital minimums** per family. A funding-arbitrage guide's "$10,000–$50,000" minimum appeared only in an unattributed search summary, so I have excluded it.
