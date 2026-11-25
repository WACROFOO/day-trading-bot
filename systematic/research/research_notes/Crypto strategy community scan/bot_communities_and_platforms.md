# Automated crypto strategies in bot communities and retail bot / copy-trading platforms (2022 – Nov 2026)

Scope note: researched 2026-11-25. Evidence quality is uneven. Almost no platform publishes audited aggregate outcome statistics (share of profitable bots or copiers). Most of the "performance" material online is vendor marketing, affiliate reviews or single-author anecdotes. Each finding below is tagged as one of: **[primary doc]** (framework docs or repo), **[academic]**, **[vendor]** (platform or company with a commercial interest), **[independent/anecdotal]** (single author, small sample), or **[news]**.

---

## 1. Freqtrade: which strategy types dominate, and what the community documents about live results and pitfalls

### Takeaway
The official community repo (freqtrade/freqtrade-strategies) is mostly short-timeframe, indicator-based, long-only spot strategies: RSI/MACD/Bollinger/ADX/EMA signals, scalpers, dip-buyers and some hyperopt-generated ones. About 60% of them run on 15-minute candles or faster, and only two run on 12h or slower. Neither the project nor its flagship community strategy (NostalgiaForInfinity) publishes verified live results. Instead, Freqtrade's own documentation says that backtests are biased, that lookahead bias makes strategies look profitable "sometimes to extremes", and that "only forward-testing (dry-mode) can really confirm a strategy".

### Cited Findings
**Composition of the community strategy repo**

Source: my own inspection of a shallow clone on 2026-11-25; latest commit 2026-09-08 (merge of PR #341). [primary doc]
- 68 strategy `.py` files: 24 at the top level, 30 in `berlinguyinca/`, 8 in `futures/` and 4 in `lookahead_bias/`. — [freqtrade/freqtrade-strategies](https://github.com/freqtrade/freqtrade-strategies)
- Declared timeframes across the 67 that declare one:
  - 5m: 29
  - 1h: 15
  - 4h: 9
  - 1m: 6
  - 15m: 5
  - 30m: 1
  - 12h: 1
  - 1d: 1

  So 40 of 67 (about 60%) are at 15m or faster, and only 2 are at 12h or slower. — [freqtrade/freqtrade-strategies](https://github.com/freqtrade/freqtrade-strategies)
- Strategy archetypes by file name and content:
  - Indicator signals: ADXMomentum, AwesomeMacd, BbandRsi, CCIStrategy, MACDStrategy, MultiRSI, UniversalMACD, Supertrend, MultiMa
  - Scalpers: Scalp, SmoothScalp, ReinforcedSmoothScalp, Quickie
  - Bollinger dip-buy / mean reversion: BinHV45, ClucMay72018, CombinedBinHAndCluc, Low_BB
  - Trend following: TrendRiderStrategy, SwingHighToSky; futures TrendFollowingStrategy and FSupertrendStrategy
  - Hyperopt-generated: GodStra, Heracles, mabStra, Diamond, PowerTower
  - Execution/utility examples: TWAPStrategy, AlmgrenChrissStrategy, FixedRiskRewardLoss, CustomStoplossWithPSAR

  — [freqtrade/freqtrade-strategies](https://github.com/freqtrade/freqtrade-strategies)
- Hard-coded stoplosses cluster at −5% (14 files), −10% (10) and −25% (7). A few use −0.9 or −1, which in practice means no stop. — [freqtrade/freqtrade-strategies](https://github.com/freqtrade/freqtrade-strategies)
- The README says each strategy ships with "Minimal ROI optimized for the strategy", an "Optimal stoploss", and buy/sell signals that are the "Result from Hyperopt or based on existing trading strategies". So the parameters are in-sample optimised by construction. — [freqtrade-strategies README](https://github.com/freqtrade/freqtrade-strategies)
- The README disclaimer reads: "These strategies are for educational purposes only… USE THE SOFTWARE AT YOUR OWN RISK." It adds that the strategies "mostly should serve as a starting point… not as 'ready to use' strategies" and "results will heavily depend on the pairs, timeframe and timerange used to backtest". — [freqtrade-strategies README](https://github.com/freqtrade/freqtrade-strategies)
- The repo includes a `lookahead_bias/` folder (DevilStra, GodStraNew, Zeus, wtc) as a teaching set. The readme explains the bugs:
  - `normalize()` uses `.min()`/`.max()` over the full dataframe.
  - A scikit-learn `MinMaxScaler` "will automatically take the absolute maximum and minimum of a series".

  Hyperopt-derived community favourites such as GodStra have biased variants of this kind. — [lookahead_bias readme](https://github.com/freqtrade/freqtrade-strategies/tree/main/user_data/strategies/lookahead_bias)
- The futures sub-folder says "all strategies are tested against this config. Tests only done on binance futures" (isolated margin, $100 stake, dry_run). — [futures/Readme.md](https://github.com/freqtrade/freqtrade-strategies/tree/main/user_data/strategies/futures)

**Flagship community strategy: NostalgiaForInfinity (NFI)**
- The NFI README describes a 5m-timeframe strategy ("must be 5m"). It recommends:
  - "between 6 and 12 open trades, with unlimited stake"
  - "A pairlist with 40 to 80 pairs. Volume pairlist works well"
  - stablecoin quote pairs
  - blacklisting leveraged tokens

  — [NostalgiaForInfinity README](https://github.com/iterativv/NostalgiaForInfinity) [primary doc]
- NFI's only published performance evidence is backtests: "For backtesting results, check out the comments in the individual commit page". The project also runs an auto-updater that pulls new strategy and blacklist versions daily, with blacklist changes checked every 60 seconds. So the live strategy is a moving target rather than a fixed, testable rule set. — [NostalgiaForInfinity README](https://github.com/iterativv/NostalgiaForInfinity) [primary doc]

**Freqtrade documentation on bias and backtest realism** [primary doc]
- Lookahead bias:
  - The docs call it "the bane of any strategy". It "typically makes the strategy backtest look profitable, sometimes to extremes".
  - "Removing conditions or indicators that push the profits up from bias will usually make the strategy significantly worse."
  - The `lookahead-analysis` tool can give false negatives (when signals never trigger) and false positives.

  — [Freqtrade docs: Lookahead analysis](https://www.freqtrade.io/en/stable/lookahead-analysis/)
- Backtesting assumptions include:
  - "All orders are filled at the requested price (no slippage) as long as the price is within the candle's high/low range"
  - "Stoploss exits happen exactly at stoploss price, even if low was lower"
  - Fees use the exchange's default fees.
  - "backtesting will never replace running a strategy in dry-run mode"
  - "only forward-testing (dry-mode) can really confirm a strategy"
  - Accuracy "can never be perfect, and will always be biased in one way or the other"

  — [Freqtrade docs: Backtesting](https://www.freqtrade.io/en/stable/backtesting/)
- Hyperopt:
  - Overly precise parameter values "will usually result in overfitted results".
  - "best results are usually not improving much after 500-1000 epochs".
  - Runs with different random states "will most likely produce different results".
  - Different loss functions "can generate completely different results".
  - The page does not prescribe out-of-sample or walk-forward testing; it only says to backtest after optimising.

  — [Freqtrade docs: Hyperopt](https://www.freqtrade.io/en/stable/hyperopt/)
- The FAQ says the bot "will _always_ be a gamble", "you can't say much from few trades", and any edge shows only "after thousands of trades". It sets an expectation of "modest wins on monthly basis". — [Freqtrade FAQ](https://www.freqtrade.io/en/stable/faq/)
- The strategy template docs say a template "will most likely not be profitable out of the box". This is quoted via a docs mirror in a fork. — [strategy-customization.md (fork mirror)](https://github.com/glonlas/freqtrade/blob/develop/docs/strategy-customization.md)

**Community "backtesting traps" write-up** (Freqtrade contributor blog, April 2021, still widely referenced) [independent]
- An "always buy" 1h strategy with a 0.1% trailing stop showed +2,506% in 11 days ($2,500 to $65,150) in backtest. The result was purely an artefact of OHLC-only candle assumptions.
- A simple EMA-crossover strategy showed about 11% profit on 1h candles; the profit "vanished" when re-tested on 5m candles.
- The author warns against strategies whose average profit per trade is below 0.5%, because slippage and unfilled limit orders erase them.

— [Backtesting Traps, brookmiles.github.io](https://brookmiles.github.io/freqtrade-stuff/2021/04/12/backtesting-traps)

**"strat.ninja"-style leaderboards**
- I could not locate or verify any strat.ninja leaderboard data through search. Searches returned nothing linking strat.ninja to Freqtrade results. — [search attempt; no source found]

**Anecdotal developer posts (dev.to, 2025–2026)** [anecdotal]
- One developer reports "+740% in the backtest. When it actually traded, it made about $2.81". Another post is titled "Why your backtest lies: I got 491% returns in testing then broke even in production". — [dev.to/maymay5692](https://dev.to/maymay5692/why-your-backtest-lies-i-got-491-returns-in-testing-then-broke-even-in-production-62a); [dev.to search results summary](https://dev.to/trendrider/crypto-trading-bot-profitability-real-numbers-not-marketing-hype-1pf0)
- A dry-run on Coinbase ran for 44 days with "zero trades fired" despite a quoted 75% backtest win rate. This is self-reported. — [dev.to feed (francis_oyakhire)](https://dev.to/feed/francis_oyakhire_fe2eefae)

### Inferences
- The community repo's centre of gravity (5m–1h, hyperopt-tuned ROI tables and stoplosses, many simultaneous pairs) is the opposite of the investor's preference for daily-or-slower, low-turnover spot trading. Only 2 of 67 community strategies run at ≥12h, so the community offers little ready-made daily-timeframe material. A daily-bar trend or momentum rule would have to be written and validated from scratch, which is easy in Freqtrade.
- No verifiable live track record exists for any popular Freqtrade community strategy. In practice, the community's best evidence is the framework authors' own warnings that backtests are biased upward.
- NFI's design (40–80 pairs, 6–12 concurrent trades, 5m bars, continuously changing code and blacklists) implies high turnover and fee drag. It also needs a minimum account size per trade slot that is awkward for a low-thousands-of-euros account. With €2,000 split over 8–12 slots, each trade is about €170–250.

### Gaps
- No public dataset of Freqtrade live results exists. Discord is private, and NFI publishes only backtests in commit comments.
- I could not access GitHub Discussions or issues via the API in this session, so I did not quantify how often "backtest ≠ live" threads appear.
- I could not verify a strat.ninja leaderboard (existence, methodology, or whether it ranks by dry-run or by backtest).

---

## 2. Other frameworks: Jesse, Hummingbot, OctoBot, Superalgos, QuantConnect, Backtrader / vectorbt

### Takeaway
The other frameworks offer tooling but almost no outcome data. Hummingbot's market-making community has activity metrics: $837m of filled volume and $376k of rewards across 1,622 miners in liquidity mining's first year (2020–21). It has never published what share of retail market makers profit after inventory losses. The available interviews describe early losses and heavy parameter tuning. Jesse's docs repeat the overfitting warnings. OctoBot's community centres on DCA, grid and TradingView-signal automation. I found no independent evidence that any of these frameworks yields better live outcomes than another.

### Cited Findings
**Hummingbot** (market making / arbitrage)
- The current README claims "Hummingbot users have generated over $34 billion in trading volume across 140+ unique trading venues over the past year". The claim is undated, self-reported and opt-in. — [hummingbot/hummingbot README](https://github.com/hummingbot/hummingbot) [vendor/primary]
- Strategy families listed:
  - Pure Market Making
  - Avellaneda-Stoikov Market Making
  - Cross-Exchange Market Making (all legacy V1)
  - V2 "controllers" and script-based strategies

  — [hummingbot/hummingbot README](https://github.com/hummingbot/hummingbot) [primary doc]
- Hummingbot Miner first-year recap (March 2021):
  - 18 token-issuer campaigns
  - 1,622 unique miners
  - $376k-equivalent rewards paid in total
  - $837m cumulative filled volume ($819.8m on Binance)
  - a daily average of 526 active bots

  The recap gives no miner ROI or loss data and notes liquidity mining "does not guarantee a certain amount of filled order volume". — [Hummingbot Miner Year 1 Recap (2021-03-02)](https://hummingbot.org/blog/hummingbot-miner-year-1-recap/) [vendor]
- The liquidity mining whitepaper's simulations suggested miners "could potentially earn 10-50%" annualised. This is a model output, not observed returns. The paper concedes that market making "can carry more risk than alternative uses of capital". — [Hummingbot liquidity mining whitepaper](https://hummingbot.org/liquidity-mining.pdf) [vendor]
- Miner interviews (2020–21):
  - One top miner's monthly return was "around 3-5%".
  - Another miner "initially lost money during volatile markets" and only became profitable after re-tuning. He advised starting with wide spreads and narrowing them.

  These are self-selected success stories. — [Hummingbot Bi-weekly #34](https://hummingbot.substack.com/p/hummingbot-bi-weekly-34); [Interview with Liquidity Miner MrBig](https://hummingbot.org/blog/interview-with-liquidity-miner-mrbig/); [Interview with Neohowie](https://hummingbot.org/blog/interview-with-liquidity-miner-neohowie/) [vendor/anecdotal]
- The Miner app is now "not maintained by nor affiliated with Hummingbot Foundation". — [Hummingbot Academy: Liquidity Mining with Hummingbot](https://hummingbot.org/academy-content/liquidity-mining-with-hummingbot/) [primary doc]
- 2025 activity has shifted to DEX and XRPL reward programmes. For example, "XRPLiquid" (built by a Botcamp-affiliated company) had about $4M total volume and 1,250 XRP distributed across 6 pairs by July 2025. — [Hummingbot Newsletter July 2025](https://hummingbot.substack.com/p/hummingbot-newsletter-july-2025); [May/June 2025](https://hummingbot.substack.com/p/hummingbot-newsletter-mayjune-2025) [vendor]

**Jesse**
- The optimisation docs warn "Be aware of overfitting!" and "Do not let the word 'optimization' trick you into thinking it can merely improve your strategies… Past performance is no guarantee of future results!" — [Jesse docs: Optimize](https://docs.jesse.trade/docs/optimize/) [primary doc]

**OctoBot**
- OctoBot positions itself as a visual-interface open-source bot to "run multiple automations (DCA, grids, crypto baskets, TradingView, and more)". It supports Binance, Coinbase, Kraken, OKX, KuCoin, Bybit, Hyperliquid and others. Some features (cloud strategies, mobile app, Strategy Designer) sit behind octobot.cloud or a paid extension. — [Drakkar-Software/OctoBot](https://github.com/drakkar-software/octobot); [OctoBot Telegram channel](https://t.me/s/OctoBot_Project) [vendor/primary]

**Superalgos**
- Superalgos is described as integrated charting, data-mining, backtesting, paper trading and multi-server deployment. I found no outcome evidence. — [search summary via dev.to listing](https://dev.to/trendrider/crypto-trading-bot-profitability-real-numbers-not-marketing-hype-1pf0) [vendor description]

**Academic grid / market-making framework results**
- A Stevens Institute (Bybit-focused) project concluded that "machine learning-based strategies did not offer significant improvements over traditional grid trading". A hedging variant performed better. — [Stevens FSC: Cryptocurrency Market Making & Grid Trading](https://fsc.stevens.edu/cryptocurrency-market-making-improving-grid-trading-strategies-in-bitcoin/) [academic, student/centre project]

### Inferences
- Rewards per miner averaged roughly $232 for the year ($376k / 1,622). Rewards were about 4.5 bps of filled volume ($376k / $837m), which is similar to one taker fee. This is consistent with retail market making being a thin, competitive business, where adverse selection (getting filled just before the price moves against you) can easily exceed rewards. It also needs continuous uptime and fast reactions, so it fits poorly with a daily-decision, spot-only, small-account profile.
- None of these frameworks changes the economics of a strategy. They only change tooling. Community material is overwhelmingly tutorials and backtests, not audited live results.

### Gaps
- No public statistic on the share of Hummingbot users (or miners) who were net profitable after inventory P&L and fees.
- I did not find substantive community-performance material for Jesse, Superalgos, QuantConnect crypto, Backtrader or vectorbt. There is no evidence beyond generic tutorials, and I did not investigate further due to time limits.

---

## 3. Retail bot platforms: grid and DCA bots (Pionex, Binance, Bybit, Bitget, KuCoin, 3Commas, Bitsgap, Cryptohopper), platform statistics, and the 3Commas API-key incident

### Takeaway
No major exchange or bot platform publishes audited statistics on what share of grid or DCA bots, or their users, are net profitable. "Grid profit" shown in apps excludes the mark-to-market loss on coins the grid accumulates. Independent backtests agree on a pattern:
- Grids beat holding in sideways months.
- They lose almost as much as holding in crashes.
- They capture only a small fraction of rallies.
- Fees punish tight grids.

A peer-reviewed-style derivation suggests the expected return of a static grid is "essentially zero" under simple random-walk assumptions. Exchange "DCA bots" are martingale averaging-down bots, not recurring buys. The 3Commas incident (October–December 2022) showed that third-party API keys are a direct theft vector: HAPI's analysis found $27.3M of verified losses across 86 victims.

### Cited Findings
**Platform statistics (or lack of them)**
- Searches for official Binance, KuCoin, Bitget, Bybit or Pionex statistics on profitable grid-bot share found none. What exists is marketing, help pages and user posts. — [search summary: KuCoin/Bitget/Bybit](https://www.gncrypto.news/trading-bots/kucoin-trading-bot-review/); [Binance Square #gridbot](https://www.binance.com/en-BH/square/hashtag/gridbot) [gap confirmed]
- Bitget, Bybit and KuCoin bots carry no extra subscription charge; users pay normal trading fees per fill. Pionex advertises a 0.05% trading fee. — [cryptoticker.io Bitget bot guide](https://cryptoticker.io/en/bitget-trading-bot/); [botverdict Pionex review 2026](https://botverdict.com/articles/pionex-review-2026-grid-trading-bot-platform-with-built-in-exchange-features/) [affiliate/review]
- Binance Square posts (user-generated, anecdotal):
  - A SUI/USDT grid backtest showed "378 trades executed, Grid Profit +197.52 USDT, Total ROI −33.31%, Max Drawdown 45.59%". This is the gap between grid profit and account profit.
  - A BTC grid in April 2025 returned 7.35% while BTC rose 14.15%.
  - A SOL grid was "paused" below range at −23%.

  — [Binance Square #gridbot](https://www.binance.com/en-BH/square/hashtag/gridbot) [anecdotal]
- One reviewer ran a KuCoin BTC/USDT spot grid with 150 USDT for 18 days. It made about $3.90 of grid profit before fees (about 2.6%) and about $2.70 after estimated 0.1% taker fees. — [GNcrypto KuCoin bot review](https://www.gncrypto.news/trading-bots/kucoin-trading-bot-review/) [independent, tiny sample]
- An illustrative Bitget fee calculation: net profit per grid round falls from 2.66% with 10 grids to 0.09% with 100 grids and turns negative with 200 grids in the same range. This is arithmetic, not measured performance. — [inetkemp substack: Bitget grid trading](https://inetkemp.substack.com/p/bitget-grid-trading-spot-futures) [independent]

**Theory and backtests of grids in trends vs ranges**
- Chen, Chen and Jang (arXiv, 13 June 2025) show that "under simple assumptions, its [traditional grid's] expected return is essentially zero". Their dynamic, re-centring grid outperformed static grids and buy-and-hold on IRR in minute-level BTC/ETH backtests from January 2021 to July 2024. The search summary notes the authors attribute strong results largely to the price rise of the period. — [arXiv:2506.11921](https://arxiv.org/abs/2506.11921) [academic preprint]
- A monthly-reset BTC grid backtest (Binance spot, 1-min candles, Jan 2022 – Oct 2026):
  - Setup: 58 months, ±10% range, 20 geometric levels, 0.1% fee per fill, $10k reset monthly.
  - Positive months: 64% for the grid vs 55% for holding.
  - Average month: −0.39% vs +2.03%.
  - Best month: +8.01% vs +43.57%. Worst month: −34.04% vs −37.29%.
  - Cumulative: −$2,283 for the grid vs +$11,779 for holding, while BTC rose about 68%.
  - A narrow ±5% grid lost $4,753; a wide ±20%/40-level grid made +$648.
  - The author found that more levels in the same range made results worse.
  - Caveat: the author sells backtesting tools (Edgoro), and touch-fills are generous.

  — [DEV: Grid trading bot backtest, 58 months (Nov 2026)](https://dev.to/walid_koussa_0941941b1fdb/grid-trading-bot-backtest-a-fresh-bitcoin-grid-every-month-for-58-months-3n7a) [independent but vendor-linked]
- In June 2022, BTC fell 37% and the monthly grid lost about 34%. — [same DEV article, via search summary](https://dev.to/walid_koussa_0941941b1fdb/grid-trading-bot-backtest-a-fresh-bitcoin-grid-every-month-for-58-months-3n7a)
- Vendor-linked backtests:
  - A sideways BTC grid (June–August 2025) made about 8.2% in three months and stayed in range 89% of the time.
  - In October–December 2025 the same grid "stopped generating new fills" after price broke above range.
  - A 6-month ETH Bollinger-band grid (Dec 2025 – Jun 2026) lost 29.7% with a −43% max drawdown despite a 56% win rate.

  — [Coinquant: Grid trading on Ethereum](https://www.coinquant.ai/blog/grid-trading-on-ethereum-6-months-of-backtest-data-in-a-ranging-market); [Coinquant: Grid strategy explained](https://www.coinquant.ai/blog/grid-trading-strategy-explained-how-to-set-it-up-and-backtest-it); [decentralised.news Pionex 90-day sideways](https://decentralised.news/pionex-grid-bot-90-day-sideways-market-strategy) [vendor-linked]
- A practitioner who ran 30–40 grid bots warned that "most of the grids… will be buying and selling the same levels, which isn't profitable". Another two-year test with $1,000 per bot found 7–12% returns "not enough to be attractive". — [Medium/Coinmonks: Grid-bots, how they really work](https://medium.com/coinmonks/grid-bots-how-they-really-work-how-to-make-money-with-them-948b4439fa5f); [Automated Income Lifestyle: Parallel testing](https://automatedincomelifestyle.substack.com/p/parallel-testing-crypto-trading-bot-strategies-7fa76c20fe85) [anecdotal]

**DCA / martingale bots**
- Exchange "DCA bots" are martingale averaging-down bots. OKX labels its product "Spot DCA (Martingale)". These bots add "safety orders" as price falls and sell on a rebound to a take-profit. — [OKX Help: Spot DCA (Martingale)](https://www.okx.com/help/iii-spot-dca-martingale); [Bybit Learn: Martingale strategy risks](https://www.bybit.com/en/learn/strategies/martingale-strategy-risks-crypto) [vendor]
- One review estimates a BTC DCA bot without a stop loss loses 5–15% in a bear market, with "all safety orders trigger[ed], maximum capital deployed at worst prices". The basis is "community-reported results" without a dataset. — [TradeAlgo 3Commas review](https://www.tradealgo.com/trading-guides/crypto/3commas-review) [affiliate/unverified]
- I found no dataset measuring how 3Commas, Cryptohopper or Bitsgap DCA users fared in the 2022 crashes (LUNA in May 2022, FTX in November 2022). — [gap]

**3Commas API-key incident (2022)**
- On 20 October 2022, FTX API keys connected to 3Commas were used for unauthorised trades on DMG pairs. 3Commas blamed phishing sites impersonating 3Commas and said "there has been no breach of either 3Commas account security databases or API keys". One user claimed about $1.5M lost (unverified). — [The Block, 2022-10-23](https://www.theblock.co/post/179237/ftx-api-keys-3commas-exploited) [news]
- HAPI's analysis (published 19 January 2023):
  - Timeline:
    - October 2022: 4 cases, about $470k lost.
    - November 2022: 24 victims, about $14.9M.
    - 11 December 2022: 3Commas still denied a leak.
    - 28 December 2022: 3Commas confirmed the leaked data was genuine.
    - 29 December 2022: the FBI reportedly joined the investigation.
  - By 10 January 2023: 86 victims in 32 countries, with $27,285,845 in verified losses.
  - Six victims lost over $1M each, together about 67% of the total.
  - Attackers reportedly held about 100,000 keys and published 10,000.
  - By exchange: Binance 47 victims and about $23.5M; KuCoin 28 and about $2.1M; Coinbase Pro 10 and about $1.5M.
  - Some leaked keys were over three years old. Stolen keys bypassed 2FA.

  — [ForkLog: HAPI analysis of the 3Commas incident](https://forklog.com/en/news/api-key-leaks-and-exchange-inaction-a-hapi-analysis-of-the-3commas-incident) [news/security analysis]
- Binance and 3Commas declined to reimburse at least one victim, saying it was impossible to verify whether the key had been stolen. The FBI investigation was reported by CoinDesk via secondary outlets. — [Cointelegraph: 3Commas CEO confirms API key leak](https://cointelegraph.com/news/3commas-ceo-confirms-api-key-leak-following-warning-from-cz); [Finance Magnates: FBI investigating](https://www.financemagnates.com/cryptocurrency/fbi-is-reportedly-investigating-3commas-api-leak/) [news]

**Exchange stress events relevant to bots**
- On 10 October 2025, more than $19B of leveraged positions were liquidated in about a day, the largest liquidation event on record. Binance paid about $283M in compensation, with later reports of over $328M plus a $300M goodwill programme. Payouts covered losses tied to depegs and platform issues, not ordinary market moves. Commentators said mean-reversion bots "kept feeding cash into a shredder". — [Yahoo Finance: Binance to compensate users](https://finance.yahoo.com/news/binance-compensate-users-technical-snag-161522868.html); [Decrypt: Binance reimburses $283M](https://decrypt.co/344026/binance-reimburses-283m-after); [CoinGecko: Oct 10 crash explained](https://www.coingecko.com/learn/october-10-crypto-crash-explained); [crypto.news: ADL at the core](https://crypto.news/adl-was-at-the-core-of-fridays-crypto-bloodbath) [news]

### Inferences
- A spot grid is effectively a short-volatility, long-the-coin position. It harvests chop, holds a growing bag in a downtrend, and sells its exposure early in an uptrend. Over 2022–2026 (BTC +68%) a monthly BTC grid trailed holding by about $14k on $10k. This matches the "zero expectation" result: grid returns depend on regime, not on edge.
- For a small spot account, the fee arithmetic dominates: 0.1% per fill on both sides means levels closer than about 0.5–1% are mostly fee transfer. Wide, few-level grids or simple holding/DCA beat dense grids in the cited tests.
- Martingale "DCA bots" have negatively skewed outcomes: frequent small wins and rare large losses when all safety orders fill in a crash. Pure recurring-buy DCA (fixed amount on a schedule) is a different, much lower-risk thing. Platform naming blurs the two.
- The API-key lesson: use trade-only keys with withdrawals disabled, IP whitelisting and periodic rotation, and avoid closed-source third-party custody of keys where possible. Note that trade-only keys still allowed theft in 2022 via pump-and-dump trades into illiquid pairs (DMG on FTX).

### Gaps
- No exchange-published share of profitable grid or DCA bots was found for Pionex, Binance, Bybit, Bitget, KuCoin, 3Commas, Bitsgap or Cryptohopper. Strategy "marketplace" leaderboards on these platforms show only top bots by ROI (survivorship) and could not be retrieved as a dataset.
- No independent dataset of DCA/martingale bot outcomes through the 2022 crashes.
- The Cointelegraph HTX 2025 recap on trading bots returned 404, so I could not retrieve its statistics.

---

## 4. Copy trading and leaderboards (Binance, Bybit, Bitget, eToro, OKX, Hyperliquid)

### Takeaway
The best available evidence is an October 2025 snapshot of 1,486 leaders and 100,236 copier outcomes across Binance, Bybit and MEXC, published by YieldFund (a firm that does not sell copy trading). In it, 97% of lead traders showed positive own PnL but only 43.6% made money for their followers, and only 48.5% of copier outcomes were profitable. Experimental academic work (Management Science 2020) finds that seeing others' success, and especially being able to copy them, raises risk-taking. Social-trading portfolios (wikifolio) do not outperform the market on average. Leaderboard "blow-ups" on Hyperliquid were mostly sudden and not predictable from behaviour.

### Cited Findings
**YieldFund 90-day multi-exchange study** (published 24 November 2025; data October 2025)
- Sample: 1,486 leaders and 100,236 copier event outcomes on Binance, Bybit and MEXC.
- Copiers: 48,592 winning vs 51,644 losing events, a 48.48% profitable rate, which is below break-even after costs.
- Leaders: 97.04% had positive own PnL, but only 43.61% produced positive follower PnL.
- Aggregate follower PnL: +709,045 USDT, concentrated in a minority of leaders.
- By platform:
  - Binance: 66.50% copier win rate, 72.45% of leaders profitable for followers, +572,980 USDT.
  - Bybit: 43.65% copier win rate, 40.34% of leaders profitable for followers, +346,106 USDT.
  - MEXC: 57.79% copier win rate, but −210,041 USDT aggregate.
- Limitations stated: event-weighted, fees/funding/slippage not broken out, inconsistent platform PnL definitions, no leverage or drawdown statistics.
- Selection bias noted: platforms promote top 30-day performers.
- YieldFund is a Dutch bond-based investment platform, not supervised by the AFM, and is not a copy-trading vendor.

— [YieldFund: Is copy trading profitable? A 90-day multi-exchange study](https://www.yieldfund.com/news/is-copy-trading-profitable-a-90-day-multi-exchange-study) [non-academic, self-published; not independently verified]

**Academic evidence**
- Apesteguia, Oechssler and Weidenholzer, "Copy Trading", *Management Science* 66(12):5608–5622 (2020), DOI 10.1287/mnsc.2019.3508. In an experimental asset market, "providing information on the success of others leads to a significant increase in risk taking", and the increase "is even larger when subjects are provided with the option to directly copy others". They conclude that copy trading leads to excessive risk-taking, because the most successful traders are often those who took the most risk. — [EconPapers record](https://econpapers.repec.org/RePEc:inm:ormnsc:v:66:y:12:i:2020:p:5608-5622); [BSE publication page](https://bse.eu/research/publications/copy-trading) [academic, peer-reviewed]
- Oehler, Horn and Wendt (2016), *International Review of Financial Analysis* 46:202–210. A study of 1,084 wikifolio social-trading certificates (2012–2013) found that "on average, wikifolios do not outperform the market". Geographically focused ones did better. This is equities, not crypto, but it is the best peer-reviewed evidence on following retail "signal providers". — [IDEAS/RePEc abstract](https://ideas.repec.org/a/eee/finana/v46y2016icp202-210.html) [academic, peer-reviewed]
- Peng, arXiv:2611.27988 (q-fin.TR). A pre-registered study of the full public Hyperliquid perps leaderboard:
  - 37,895 addresses, filtered to 10,395 "master-worth-copying" accounts.
  - 2,621 loss-driven blow-ups across 48 crash-days.
  - Behavioural drift preceded equity decline for only 9% of blown-up masters, and 69% blew up with no gradual behavioural signal. The median lead was −8 days, meaning behaviour lagged equity.
  - The best detector reached AUC 0.49, which is chance.
  - Conclusion: behavioural early warning is "not a viable general safety net"; a plain equity/drawdown stop fires as early.

  Date caveat: the arXiv listing shows submission on 1 June 2026, while the identifier and paper header imply November 2026. — [arXiv:2611.27988](https://arxiv.org/abs/2611.27988) [academic preprint, single author]

**Platform mechanics** [vendor]
- Bitget elite-trader profit share:
  - Tiered from 10% (Bronze) to 20% (Legend); the spot cap is 10%.
  - High-water-mark settlement, settled daily at 00:00 UTC+8.
  - Copiers can follow up to 10 traders.
  - Lead-trader dashboards emphasise follower count, AUM and retention, which gives lead traders an incentive to grow AUM.

  — [Bitget support: elite trader profit share](https://www.bitget.com/support/articles/12560603838677); [Bitget support: copy trading](https://www.bitget.com/support/articles/12560603777069)
- "The lead trader is always filled first, before their followers." This execution-order disadvantage for followers appears in industry commentary. — [KuCoin blog: Is crypto copytrading profitable in 2026](https://www.kucoin.com/blog/is-crypto-copytrading-profitable-in-2026) [vendor]

**EU regulatory framing** (relevant to a France-based investor)
- ESMA's Supervisory Briefing on Copy Trading (30 March 2023, ESMA35-42-1428) says automatic execution of copied trades generally qualifies as portfolio management under MiFID II, even if clients can set "leverage limits, stop-loss instructions or closing of open positions". Copied traders' remuneration can fall under MiFID inducement and remuneration rules. Firms must give "clear and understandable information on the method used to calculate and present information on past performance". The briefing applies to financial instruments (CFDs and similar), not spot crypto. — [ESMA Supervisory Briefing on Copy Trading (PDF)](https://www.esma.europa.eu/sites/default/files/2023-03/ESMA35-42-1428_Supervisory_Briefing_on_Copy_Trading.pdf) [regulator]
- The joint European Supervisory Authorities' crypto warning (updated 2025) says that under MiCA (applicable since December 2024) "the level of protection remains limited depending on the product". The AMF endorsed ESMA's 2021 warning on "social trading" (tips and shared trade intentions on social networks). — [ESMA: Warning on crypto-assets (Dec 2024)](https://www.esma.europa.eu/document/warning-crypto-assets); [AMF: ESAs warn consumers on crypto risks](https://www.amf-france.org/en/news-publications/news/eba-esma-and-eiopa-warn-consumers-risks-crypto-assets); [AMF backs ESMA reminder on social media recommendations](https://www.amf-france.org/sites/institutionnel/files/pdf/68984/en/Investment_recommendations_on_social_media_the_AMF_backs_ESMA%27s_reminder.pdf?1765254849) [regulator]

### Inferences
- The leader-vs-follower gap (97% vs 44%) is what survivorship plus promotion bias predicts. Leaderboards rank by recent ROI, which selects for high-variance, often leveraged, traders. Followers join after the run-up, get filled later at worse prices, and pay profit share on gains with no rebate on losses.
- Crypto copy trading on these exchanges is overwhelmingly futures and leverage based. That conflicts with a spot-only, no-leverage mandate. Any spot copy product inherits the same selection and timing problems.
- The Hyperliquid result implies followers cannot rely on spotting a lead trader "going off the rails". Only hard equity or drawdown stops on the copied allocation offer protection.

### Gaps
- No exchange publishes the share of followers who are net profitable, or long-run survival rates of lead traders. I found no peer-reviewed study of Binance, Bybit, Bitget or OKX copy-trading outcomes specifically.
- No leverage statistics for lead traders were found in any dataset.
- I did not find eToro crypto-specific CopyTrader outcome data. The search summary mentioned a *Journal of Business Research* study of 16,964 eToro observations, but I could not retrieve its findings.

---

## 5. Recurring failure lessons: overfitting, hyperopt curve-fitting, coin-universe survivorship, fees and slippage, outages, API security

### Takeaway
The lessons are consistent across framework docs, academic benchmarks and practitioner posts. Backtests overstate live results, often by a lot. Hyperparameter search finds noise. Short timeframes and dense grids turn fee and slippage costs into a dominant expense. Infrastructure failures (exchange incidents, API-key theft) cause losses outside the strategy logic. The newest academic benchmark ran on OKX through live trading in August–September 2026. None of its ML, RL or LLM strategies beat buy-and-hold live, and live execution price slippage was about six times the paper-trading level.

### Cited Findings
**Backtest-to-live gap (academic, 2026)**
- Yu et al., "Can AI Make Money in Crypto? Measuring the Gap from Backtests to Real Markets", arXiv:2609.34510, submitted 28 September 2026. Setup: OKX, 10 large-cap coins, 0.10% spot taker fee, isolated 2× leverage with shorts allowed (not spot-only).
  - **Backtest (2025):** 23 of 24 ML methods were profitable, with a median ML return of +36.0%. Buy-and-hold returned −7.63%.
  - **Paper trading (4 June – 21 September 2026):** only 2 of 8 ML methods stayed profitable, and the median ML return was −9.8%.
  - **Live trading (24 August – 21 September 2026):**
    - Returns: LSTM −0.33%, TRA −14.74%, XGBoost −0.79%, Qwen-LLM +3.72%.
    - Buy-and-hold returned +11.63% over the same period.
    - All four methods had negative alpha.
    - The average absolute alpha gap from backtest to live was 58.85 pp.
    - Execution price difference rose from about 0.31‰ in paper trading to 1.86‰ live, about 6×.
  - Authors' conclusion: "No evaluated method sustained market-beating performance in live trading."
  - Short live window; Section 3.3 says five methods went live but tables report four.

  — [arXiv:2609.34510 (HTML)](https://arxiv.org/html/2609.34510); [abstract](https://arxiv.org/abs/2609.34510) [academic preprint]

**Overfitting and hyperopt**
- Freqtrade warns that overly precise parameters "will usually result in overfitted results". Different random states and loss functions produce "completely different results". Optimisation gains plateau after 500–1,000 epochs. — [Freqtrade docs: Hyperopt](https://www.freqtrade.io/en/stable/hyperopt/) [primary doc]
- The community repo itself ships hyperopt-derived ROI tables, stoplosses and signals. Several hyperopt-born strategies (GodStra family, Zeus) have lookahead-biased versions kept as teaching examples. — [freqtrade-strategies README](https://github.com/freqtrade/freqtrade-strategies); [lookahead_bias readme](https://github.com/freqtrade/freqtrade-strategies/tree/main/user_data/strategies/lookahead_bias) [primary doc]
- Jesse: "Be aware of overfitting!… Do not let the word 'optimization' trick you." — [Jesse docs: Optimize](https://docs.jesse.trade/docs/optimize/) [primary doc]

**Lookahead and candle-assumption artefacts**
- Full-series normalisation (`.min()`/`.max()`, MinMaxScaler) is the canonical community lookahead bug. — [lookahead_bias readme](https://github.com/freqtrade/freqtrade-strategies/tree/main/user_data/strategies/lookahead_bias)
- Trailing stops and ROI targets on long candles produce fake profits: +2,506% in 11 days in a backtest, and an EMA-cross profit that disappears on 5m data. — [Backtesting Traps](https://brookmiles.github.io/freqtrade-stuff/2021/04/12/backtesting-traps) [independent]
- Freqtrade's backtester assumes no slippage within the candle range and stoploss fills exactly at the stop price "even if low was lower". — [Freqtrade docs: Backtesting](https://www.freqtrade.io/en/stable/backtesting/) [primary doc]

**Fees and slippage on small accounts**
- Strategies averaging under 0.5% profit per trade tend to turn unprofitable live once slippage and unfilled orders are included. — [Backtesting Traps](https://brookmiles.github.io/freqtrade-stuff/2021/04/12/backtesting-traps)
- In grid trading, smaller grid spacing has lower volatility but is "more susceptible to transaction fees". — [arXiv:2506.11921 via search summary](https://arxiv.org/abs/2506.11921)
- In the 58-month BTC test, a narrow ±5% grid lost $4,753 vs a wide ±20% grid's +$648, with fees the main driver. — [DEV 58-month grid backtest](https://dev.to/walid_koussa_0941941b1fdb/grid-trading-bot-backtest-a-fresh-bitcoin-grid-every-month-for-58-months-3n7a)
- Fees deducted in the received coin leave unsellable "dust". Using an exchange fee token avoids this. — [Freqtrade FAQ](https://www.freqtrade.io/en/stable/faq/)

**Coin-universe survivorship**
- NFI recommends volume-based pairlists of 40–80 pairs and maintains auto-updated blacklists. The coin universe therefore changes over time, and a backtest on today's list of liquid coins uses information not available in the past. — [NostalgiaForInfinity README](https://github.com/iterativv/NostalgiaForInfinity)
- No source in this scan quantified coin-universe survivorship bias for crypto bots. — [gap]

**Exchange outages and stress events**
- Binance compensated users with about $283M (later reported as over $328M) after depeg and technical issues during the 10 October 2025 crash (>$19B liquidated). Compensation excluded ordinary market losses. — [Decrypt](https://decrypt.co/344026/binance-reimburses-283m-after); [Yahoo Finance](https://finance.yahoo.com/news/binance-compensate-users-technical-snag-161522868.html)
- Practitioners note that a live bot that crashes mid-order "might leave you with an open position and no stop loss". — [dev.to search summary](https://dev.to/maymay5692/-i-built-a-crypto-trading-bot-in-python-every-trade-lost-money-21em) [anecdotal]

**API-key security**
- 3Commas 2022: $27.3M of verified losses and 86 victims. Keys were up to 3+ years old, and 2FA was bypassed via the keys. — [ForkLog/HAPI](https://forklog.com/en/news/api-key-leaks-and-exchange-inaction-a-hapi-analysis-of-the-3commas-incident)
- An October 2022 phishing vector: fake 3Commas sites harvested keys and used them for wash and pump trades on illiquid FTX pairs. — [The Block](https://www.theblock.co/post/179237/ftx-api-keys-3commas-exploited)
- Freqtrade's FAQ notes keys need specific "Spot Trading" permission and IP allow-listing. — [Freqtrade FAQ](https://www.freqtrade.io/en/stable/faq/)

**Copy-trading behavioural risk**
- Seeing others' success raises risk-taking, and copying raises it further. — [Apesteguia et al. 2020](https://econpapers.repec.org/RePEc:inm:ormnsc:v:66:y:12:i:2020:p:5608-5622)

### Inferences
- For the investor profile (small spot account, daily-or-slower, EU venue), the evidence favours:
  - few trades per month
  - simple rules with few parameters, validated out-of-sample and in dry-run before going live
  - self-hosted open-source execution (e.g., Freqtrade) with withdrawal-disabled, IP-restricted keys, rather than closed-source cloud bots holding keys
- The evidence argues against:
  - dense grids and martingale DCA bots
  - copy trading (futures-centric, leverage-heavy, survivorship-selected)
  - hyperopt-tuned 5m community strategies
- A realistic expectation from the evidence is that most automated strategies fail to beat buy-and-hold of BTC/ETH after costs in trending markets. The burden of proof should sit on any strategy claiming otherwise. Benchmark every candidate against simple holding and recurring-buy DCA, net of 0.1–0.2% round-trip fees.

### Gaps
- No quantified study of crypto coin-universe survivorship bias for bot backtests was found in this scan. Another researcher may cover this from the academic side.
- No systematic data on how bots behaved during specific exchange outages (e.g., which grid or DCA bots were liquidated or stuck on 10 October 2025).
- MiCA-licensed venue availability of native bots (Binance France, Bybit EU, OKX EU, Bitget EU, Kraken) was not verified in this scan.
