# Academic and institutional evidence on systematic crypto strategies (as of 25 Nov 2026)

Scope: peer-reviewed and institutional evidence on crypto strategy families, with in-sample results kept apart from out-of-sample and post-publication results. The focus is 2021–2026, including the post-spot-ETF period (US spot bitcoin ETFs began trading on 11 Jan 2024).

Investor lens: a France-based retail investor with a small EUR account. Spot only, no leverage, decisions daily or slower. Retail costs run about 0.1–0.6% per trade plus spread.

**Reading guide**
- **Evidence labels.** Each finding is tagged **[IS]** (in-sample, i.e. inside the original paper's data window), **[OOS]** (an out-of-sample test reported by the authors), **[POST]** (data after the original publication or sample end), **[VENDOR]** (an exchange, fund or product issuer with a commercial interest) or **[OWN]** (my own computation, described below).
- **[OWN] computation.** I built a small replication on public data, because no peer-reviewed study covers 2024–2026 for simple BTC and ETH rules.
  - Data: Bitstamp daily candles (UTC closes) from the public API ([Bitstamp OHLC API](https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=1000)). BTC/USD runs from 2011, BTC/EUR from Apr 2016, and ETH/USD and ETH/EUR from 16 Aug 2017. All series end on 24 Nov 2026.
  - Perpetual funding: Deribit public API ([Deribit funding history](https://www.deribit.com/api/v2/public/get_funding_rate_history?instrument_name=BTC-PERPETUAL)).
  - Implied volatility: Deribit's DVOL index ([Deribit DVOL](https://www.deribit.com/api/v2/public/get_volatility_index_data?currency=BTC&resolution=1D)).
  - Timing: each signal is computed on day t's close and the position is held from close t to close t+1, so there is no look-ahead.
  - Positions are long-only with a 100% maximum (no leverage). Cash earns 0%, which is conservative.
  - Costs: 0%, 0.25% or 0.5% per unit of one-way turnover.
  - Sharpe ratios use rf = 0 and √365 annualisation.
  - "Turnover/yr" is the sum of absolute position changes per year, so one full round trip = 2.0.
  - The rules were fixed in advance as the canonical published ones, not optimised.
  - Limitations: one venue; costs are modelled as a flat fee+spread with no extra slippage; these are backtests, not live results.
- **Which windows count as post-publication.**
  - Detzel et al.'s sample ends Dec 2017, Liu & Tsyvinski's ends May 2018, and Liu, Tsyvinski & Wu's ends 2018 in the working paper (2020 reportedly in the published JF version).
  - So **2015–2020 is roughly the literature's in-sample era**, and **2021–2023 and 11 Jan 2024–24 Nov 2026 are post-publication windows** for simple trend rules.

---

## 1. Time-series momentum and trend-following on BTC and ETH

### Takeaway
Simple long-or-flat trend rules have the best evidence of any crypto strategy family available to a spot-only investor. The evidence is peer-reviewed in-sample, has one net-of-cost out-of-sample study (Deprez & Frömmel 2024), and is consistent in practitioner work.

In post-publication data (2021–2026) the rules did not deliver the large Sharpe ratios of the early studies. Absolute performance collapsed along with BTC's own returns: BTC buy-and-hold Sharpe fell from 1.38 in 2015–2020 to 0.41–0.52 after that.

What persisted is **drawdown control**. In 2022 and in the 2025–26 bear market, the trend rules roughly halved maximum drawdowns, and the better rules improved Sharpe by about 0.05–0.30 over buy-and-hold. The 50/200-day crossover was the clear post-ETF failure, and the 200-day SMA suffered heavy whipsaw in 2021 and 2025.

### Cited Findings

**Peer-reviewed foundations (in-sample unless stated)**
- **Liu & Tsyvinski, "Risks and Returns of Cryptocurrency" (RFS 2021; NBER WP w24877).**
  - Data run to 31 May 2018. The paper finds "a strong time-series momentum effect" and that "proxies for investor attention strongly forecast cryptocurrency returns"; crypto returns have no exposure to most stock-market and macro factors [IS] — [NBER w24877 PDF](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf)
  - The momentum is **short-horizon**. A one-standard-deviation rise in today's BTC return predicts +0.33% the next day. For weekly returns, a one-standard-deviation rise predicts +3.16%, +3.66%, +3.49% and +1.50% over the next 1–4 weeks [IS] — [NBER w24877 PDF](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf)
  - Weekly quintile sort: the top quintile returned 11.22%/week (Sharpe 0.45) against 2.60%/week (Sharpe 0.19) for the bottom quintile. The effect is "somewhat smaller" from 2013 onward and weaker for Ethereum. A pseudo-out-of-sample test that sets the quintile cut-offs on the first two years "find[s] strong momentum effect as well" [IS/OOS within sample] — [NBER w24877 PDF](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf)
  - BTC buy-and-hold Sharpe ratios in that sample were 0.09 daily, 0.23 weekly and 0.31 monthly (not annualised) [IS] — [NBER w24877 PDF](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf)
- **Detzel, Liu, Strauss, Zhou & Zhu, "Learning and Predictability via Technical Analysis: Evidence from Bitcoin and Stocks with Hard-to-Value Fundamentals"** (Financial Management 50(1):107–137, 2021; DOI 10.1111/fima.12310).
  - "Ratios of prices to their moving averages forecast daily Bitcoin returns in and out of sample" — [EconPapers record](https://econpapers.repec.org/RePEc:bla:finmgt:v:50:y:2021:i:1:p:107-137)
  - Working-paper version, sample 18 Jul 2010 – 12 Dec 2017, with 5/10/20/50/100-day SMA rules (hold BTC above the SMA, T-bills below):
    - Gross annual returns 203–216% against 224% for buy-and-hold.
    - Volatility 84–97% against 111%.
    - Sharpe 2.6 (5-day) to 2.2 (100-day) against 2.0.
    - Max drawdown −66% to −70% against −89.5%.
    - Breakeven switching cost 1.1% (5-day) to 4.5% (100-day).
    - All results are **gross of costs**, and CXO flags data snooping [IS] — [CXO Advisory summary](https://www.cxoadvisory.com/currency-trading/timing-bitcoin-with-smas/)
- **Deprez & Frömmel, "Are simple technical trading rules profitable in bitcoin markets?"** (Int. Review of Economics & Finance 93, 2024).
  - They test 75,360 rules in six families at daily and intraday frequencies. A multiple-hypothesis procedure selects rules *after transaction costs*, and the selected rules are combined into portfolios and tested out-of-sample.
  - The rules "can outperform a buy-and-hold strategy in the bitcoin market out-of-sample, especially risk–return wise" [OOS, net of costs]. The sample dates and magnitudes were not visible in the abstract — [EconPapers](https://econpapers.repec.org/RePEc:eee:reveco:v:93:y:2024:i:pb:p:858-874)

**Practitioner and institutional studies**
- **Zarattini, Pagani & Barbon, "Catching Crypto Trends: A Tactical Approach for Bitcoin and Altcoins"** (Swiss Finance Institute RP 25-80; SSRN 5209907; posted May 2025, revised Oct 2025; Concretum Group).
  - Data: 2010 to mid-Mar 2025 across 21,616 assets; strategy results run Jan 2015 – Mar 2025 on a survivorship-bias-free universe (≥$2m median daily volume, up to 20 coins).
  - Rules: an ensemble of Donchian breakouts with 5–360-day lookbacks, trailing stops, 25% volatility target and **leverage up to 200%**.
  - Costs were tested at 0.10%, 0.25% and 0.50%. The headline at 0.10%: about 18% CAGR net and about 11% annual alpha against BTC [IS; the whole result is in-sample to Mar 2025] — [CXO Advisory, 29 May 2025](https://www.cxoadvisory.com/technical-trading/crypto-asset-trend-following-strategies/)
  - Concretum reports "Sharpe ratio above 1.5" net of fees and 10.8% annual alpha against BTC, and says crypto trend returns differ significantly from traditional trend-following [IS, VENDOR-adjacent] — [Concretum](https://concretumgroup.com/catching-crypto-trends-a-tactical-approach-for-bitcoin-and-altcoins/); [IDEAS listing](https://ideas.repec.org/p/chf/rpseri/rp2580.html)
  - Caveat for this investor: the 200% leverage cap breaks the spot/no-leverage constraint. I found no published post-Mar-2025 update.
- **Concretum follow-up, "Seasonality in Bitcoin Intraday Trend Trading"** (Pagani; figures dated Jan 2026).
  - A long-short, high-frequency trend ensemble at a 20% volatility target had a **gross** Sharpe of about 1.6 over 2018–2025.
  - A volatility-targeted **long-only BTC** portfolio had a Sharpe "just below 0.8" [IS, gross] — [Concretum](https://concretumgroup.com/seasonality-in-bitcoin-intraday-trend-trading/)
- **Le & Ruthbah, "Trend-following Strategies for Crypto Investors"** (SSRN, Aug 2024; Monash).
  - Assets: BTC from 2016, ETH from 2017 and the S&P Crypto LargeCap ex-MegaCap index from 2019, all to Jan 2023. Rules: price above its 20/65/150/200-day SMA, otherwise cash.
  - The 20-day SMA on BTC had a gross Sharpe of **1.68** and **1.25 net of 0.5% frictions**. The authors note that shorter lookbacks give higher Sharpe but costs eat profits [IS] — [CXO Advisory, 16 Aug 2024](https://cxoadvisory.com/technical-trading/applying-simple-trend-following-rules-to-cryptocurrencies); [Monash project page](https://www.monash.edu/business/mcfs/our-research/all-projects/investment-strategy/trend-following-strategies-for-crypto-investors)
- **Grayscale Research, "The Trend is Your Friend: Managing Bitcoin's Volatility with Momentum Signals"** (last updated 9 Aug 2023).
  - Tests holding BTC above its 50-day MA and cash below, plus MA crossovers and EMAs, and reports favourable backtests that reduce drawdowns.
  - I could not retrieve the full numbers (HTTP 429) [IS, VENDOR] — [Grayscale Research](https://research.grayscale.com/reports/the-trend-is-your-friend-managing-bitcoins-volatility-with-momentum-signals)
- **Rozario, Holt, West & Ng, "A Decade of Evidence of Trend Following Investing in Cryptocurrencies"** (arXiv 2009.12155, 2020).
  - Hourly Bitstamp data, Sep 2011 – Dec 2019, with optimised MA crossovers.
  - In-sample optimal Sharpe: SMA 1.09, EMA 1.35, DEMA 1.32. **Costs, spreads and slippage are assumed negligible** and parameters are optimised, so this is the weakest-quality evidence [IS, gross] — [arXiv/ar5iv](https://ar5iv.labs.arxiv.org/html/2009.12155)
- **Quantpedia, "Revisiting Trend-following and Mean-reversion Strategies in Bitcoin"** (12 Sep 2024).
  - Re-tests its 2022 "MAX" rule (buy BTC at a 10–50-day high) and "MIN" rule (buy at a 10–50-day low) on a **true post-publication sample, 4 Feb 2022 – 20 Aug 2024**.
  - MAX (trend) "held up" and was "very effective". MIN (mean reversion) "deteriorated" with low or negative 2022–24 returns. Overall results were "slightly less effective" than originally. No costs are reported [POST] — [Quantpedia](https://quantpedia.com/revisiting-trend-following-and-mean-reversion-strategies-in-bitcoin/)
- **Live product record: Bitwise Trendwise Bitcoin & Treasuries Rotation ETF (BITC).**
  - Launched Mar 2023. It holds CME BTC futures in uptrends and Treasuries in downtrends. The expense ratio is listed as 0.88% or 1.43% depending on the source [VENDOR] — [Investing.com](https://www.investing.com/etfs/bitc-nyse); [ETF Central](https://www.etfcentral.com/fund/BITC)
  - Seeking Alpha snapshot at 31 Mar 2026: 3-year price performance +42.51% and 1-year −12.32% — [Seeking Alpha](https://seekingalpha.com/symbol/BITC/momentum/performance)
  - Over the same windows, Bitstamp BTC/USD returned **+139.6%** (31 Mar 2023 → 31 Mar 2026) and **−17.4%** (31 Mar 2025 → 31 Mar 2026) [OWN] — [Bitstamp OHLC API](https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=1000)
  - Caveat: these are price returns from a snippet, so distributions may be excluded.

**[OWN] post-publication replication, BTC/USD (Bitstamp)**
Figures are CAGR / Sharpe / max drawdown, net of 0.25% per trade unless stated — [Bitstamp OHLC API](https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=1000)

| Rule (BTC) | 2015–2020 (in-sample era) | 2021–2023 | 2022 only | Post-ETF, 11 Jan 2024 – 24 Nov 2026 | Full, 2015–Nov 2026 | Turnover/yr (full) |
|---|---|---|---|---|---|---|
| Buy & hold | 111.6% / 1.38 / −83.4% | 13.3% / 0.52 / −76.7% | −64.3% | 8.9% / 0.41 / −53.1% | 55.1% / 0.99 / −83.4% | ~0 |
| Price > 200-day SMA | 111.5% / 1.55 / −67.7% | 13.8% / 0.51 / −65.0% | 0.0% (flat all year) | 10.6% / 0.46 / −32.7% | 55.8% / 1.12 / −67.7% | 6.2 |
| 50/200 SMA crossover | 99.2% / 1.41 / −71.6% | 13.6% / 0.50 / −57.0% | −7.2% | **−2.4% / 0.12 / −53.4%** | 46.6% / 0.98 / −71.6% | 1.8 |
| Price > 50-day SMA | 108.0% / 1.62 / −62.3% | 33.9% / 0.88 / −60.2% | −52.5% | 20.5% / 0.74 / −28.3% | 64.4% / 1.28 / −62.3% | 18.3 |
| Price > 20-day SMA | 102.6% / 1.63 / −51.7% | **−6.5% / 0.06 / −70.8%** | −47.9% | 7.3% / 0.38 / −35.0% | 43.1% / 1.01 / −70.8% | 38.3 |
| TSMOM ensemble (signs of 1/3/6/12-month returns, 0–100%) | 103.5% / 1.54 / −67.0% | 23.2% / 0.71 / −48.2% | −29.0% | 19.5% / 0.71 / −26.7% | 58.6% / 1.20 / −67.0% | 12.0 |
| TSMOM ensemble × 25% vol target | 41.8% / 1.65 / −30.7% | 13.0% / 0.79 / −21.5% | −11.0% | 10.6% / 0.64 / −18.6% | 26.5% / 1.25 / −30.7% | 5.0 |
| 200-day SMA × 25% vol target | 50.5% / 1.80 / −23.9% | 13.8% / 0.75 / −28.7% | 0.0% | 7.9% / 0.47 / −18.2% | 29.9% / 1.28 / −28.7% | 3.6 |

- Cost sensitivity, post-ETF BTC, net CAGR at 0% / 0.25% / 0.5% per trade [OWN] — [Bitstamp OHLC API](https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=1000):

  | Rule | 0% | 0.25% | 0.5% |
  |---|---|---|---|
  | 200-day SMA | 13.5% | 10.6% | 7.7% |
  | TSMOM ensemble | 23.6% | 19.5% | 15.7% |
  | 50-day SMA | 28.1% | 20.5% | 13.4% |
  | 20-day SMA | 18.3% | 7.3% | — |

  The 20-day SMA turns over 39 times a year, which costs about 10%/yr at 0.25%.
- Calendar-year net returns, BTC, 0.25% per trade [OWN] — [Bitstamp OHLC API](https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=1000):

  | Rule | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 YTD (to 24 Nov) |
  |---|---|---|---|---|---|---|
  | Buy & hold | +59.0% | −64.3% | +155.0% | +120.0% | −6.5% | −31.8% |
  | 200-day SMA | **−23.4%** | 0.0% | +92.6% | +77.7% | **−19.3%** | +2.5% |
  | 50/200 crossover | +16.7% | −7.2% | +35.1% | +90.9% | −29.3% | −24.0% |
  | TSMOM ensemble | +55.6% | −29.0% | +69.3% | +86.1% | +4.4% | −7.0% |
  | TSMOM ensemble × 25% vol target | +15.6% | −11.0% | +40.3% | +44.2% | −0.9% | −2.3% |

- Whipsaw: the BTC 200-day SMA rule switched **19 times in 2021** and **17 times in 2025** (10 times in Mar 2025 and 7 in Oct–Nov 2025), against 0 in 2022 and 2 in 2026 YTD. On 24 Nov 2026 BTC ($58,910) was **below** its 200-day SMA (~$72,000) [OWN] — [Bitstamp OHLC API](https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=1000)
- ETH/USD, net of 0.25%, as CAGR / Sharpe / max drawdown [OWN] — [Bitstamp OHLC API](https://www.bitstamp.net/api/v2/ohlc/ethusd/?step=86400&limit=1000):

  | Rule (ETH) | 2021–23 | Post-ETF | Full, Aug 2018 – Nov 2026 |
  |---|---|---|---|
  | Buy & hold | 45.6% / 0.87 / −79.3% | **−14.0% / 0.11 / −67.6%** | 17.7% / 0.62 / −80.3% |
  | 200-day SMA | 72.0% / 1.14 / −57.9% | 5.3% / 0.34 / −42.7% | — |
  | 50/200 crossover | — | −21.2% / −0.28 / −69.0% | — |
  | TSMOM ensemble | — | 0.3% / 0.20 / −44.3% | — |
  | TSMOM ensemble × 25% vol target | 19.1% / 1.04 / −16.6% | 1.6% / 0.18 / −18.9% | 13.2% / 0.79 / −19.9% |

  - ETH's 50-day SMA returned an outsized 32.0% net post-ETF. That is one of about 10 variants, so treat it as luck or data-mining.
- BTC/EUR, post-ETF, net of 0% costs [OWN] — [Bitstamp OHLC API](https://www.bitstamp.net/api/v2/ohlc/btceur/?step=86400&limit=1000):
  - Buy & hold: 9.0% / Sharpe 0.42 / max drawdown −51.8%.
  - 200-day SMA: 11.2% / 0.48 / −33.5%.
  - TSMOM ensemble: 20.4% / 0.74 / −25.6%.
  - TSMOM ensemble × 25% vol target: 11.5% / 0.68 / −18.9%.
  - 2025–26 YTD: buy & hold −23.2%/yr; the 200-day SMA did worse than in USD (−13.8%/yr).
  - EUR results track USD closely, but EUR/USD moves shift individual years (for example BTC 2025: −6.3% in USD, −17.4% in EUR).

### Inferences
- **Decay in what, exactly.**
  - Absolute Sharpe and return of trend rules decayed sharply after 2020, but buy-and-hold decayed just as much.
  - The *increment* over buy-and-hold for the TSMOM ensemble did not obviously decay: Sharpe +0.16 in 2015–20, +0.19 in 2021–23 and +0.30 post-ETF.
  - The single 200-day SMA's increment shrank to about zero in 2021–23 because of whipsaw.
  - Single-parameter rules are fragile: the 50/200 crossover worked in 2022 but failed post-ETF, and the 20-day SMA failed in 2021–23 after costs. Ensembles are more stable.
- **Main benefit is drawdown.** In every post-publication window the trend rules cut max drawdown from about −53% to −77% (buy-and-hold) down to about −27% to −65%. Only combining with volatility targeting reached about −18% to −30%. A trend filter alone does not prevent a −60% drawdown, because crashes start before the 200-day SMA is crossed (for example, the 2015–2020 drawdown was still −67.7% with the 200-day SMA).
- **Cost load is manageable at daily or slower frequency.** Turnover of 4–14 per year, about 2–7 round trips, costs 1–3.5%/yr at 0.25% per trade. Lookbacks of 20 days or less are not viable at retail fees.
- **Behavioural cost.** Trend rules lag badly in strong bull years. In 2021 the 200-day SMA lost 23% while BTC gained 59%, and BITC lagged BTC by about 97 percentage points over three years. That is the realistic failure mode in live use.
- **Published headline numbers (Sharpe 1.5–2.6) come from in-sample periods dominated by 2013–2020 bull runs.** Expected post-ETF Sharpe for long-only trend rules is more like 0.4–0.8, with drawdowns of −20% to −35%.

### Gaps
- No peer-reviewed paper tests simple BTC/ETH trend rules on 2024–2026 data. The post-ETF numbers above are my own replication on one venue.
- I could not access Zarattini et al.'s yearly table, max drawdown or post-March-2025 performance, nor Grayscale's numeric backtest.
- I found no AQR, Fidelity Digital Assets, Robeco or Kaiko study with crypto trend numbers. Man Group's crypto note covers volatility scaling, not trend (see §3).
- BITC's total-return series and fund-level figures were not verified against the issuer.

---

## 2. Cross-sectional momentum and reversal among coins

### Takeaway
A cross-sectional momentum factor exists in the published in-sample data (Liu, Tsyvinski & Wu, JF 2022: about 3% per week long-short, mainly in large coins). The evidence then becomes horizon-sensitive (2–4-week momentum, reversal beyond about one month), crash-prone, costly, and partly reliant on short legs.

Peer-reviewed replications stop around 2022. The only post-2022 evidence is informal and points to flat performance in 2023–24. A 2026 audit of the JFQA crypto trend factor (CTREND) found its Sharpe of 2.08 falls to about 0.01 after corrections.

For a spot-only, long-only retail investor without a survivorship-free coin universe, this family is weak.

### Cited Findings
- **Liu, Tsyvinski & Wu, "Common Risk Factors in Cryptocurrency"** (WP Apr 2019, published JF 77(2), 2022).
  - Coins with market cap above $1m, 2014–2018; the universe grew from 109 to 1,583 coins.
  - Long-short weekly excess returns: 2.7% (1-week momentum), 3.3% (2-week), 4.1% (3-week) and 2.5% (4-week). 8–100-week momentum is not significant [IS] — [Cowles/Yale PDF](https://cowles.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf); [NBER w25882](https://www.nber.org/papers/w25882.pdf)
  - Momentum is concentrated in large coins: an insignificant 0.6%/week below median size against 4.2%/week above. Results "virtually do not change" when the short leg is BTC [IS] — [Cowles/Yale PDF](https://cowles.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf)
  - An independent replication matches the published market factor (CMKT) with 99.7% correlation in the CoinMarketCap era — [Stöckl replication](https://sstoeckl.github.io/crypto_data/replication.html)
- **Momentum crashes, Financial Markets and Portfolio Management (2025).**
  - In large-cap, equal-weighted samples, crypto momentum shows severe crashes, including a December 2020 drawdown of about 255% (long-short). Risk-adjusted intercepts remain significant.
  - Earlier monthly studies (2014–2018) found no momentum, so weekly results are "inconclusive" across studies [IS/POST mixed; search snippet, full text paywalled] — [Springer FMPM](https://link.springer.com/article/10.1007/s11408-025-00474-9)
- **Dobrynskaya, "Cryptocurrency Momentum and Reversal"** (J. Alternative Investments 26, 2023).
  - Sample: the 2,000 largest coins, 2014–2020. Momentum appears at 2–4 weeks (strongest with 2-week sort and hold), and there is significant **reversal beyond one month** (4–6 weeks onward), driven by past losers [IS] — [HSE publications](https://publications.hse.ru/en/articles/811744977); [HSE news](https://spb.hse.ru/en/news/559533243.html)
- **Fičura (2023).** Weekly reversal appears only in small, illiquid coins; large, liquid coins show momentum [IS] — [IDEAS](https://ideas.repec.org/p/prg/jnlwps/v5y2023id5.003.html)
- **"Cryptocurrency factor momentum"** (Quantitative Finance 23(12), 2023). 3,900+ coins, 2014–2022, 34 anomalies replicated. Past winning factors beat losers across subperiods, mainly through size and volatility anomalies [IS to 2022] — [Taylor & Francis](https://www.tandfonline.com/doi/abs/10.1080/14697688.2023.2269999)
- **"Cryptocurrency anomalies and economic constraints"** (Int. Rev. Financial Analysis, 2024). 3,956 coins, 2014–2022. Momentum prevails in larger coins but "incurs substantial trading costs" and gets its alpha "largely from short positions" [IS to 2022] — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1057521924001509)
- **"Cross-sectional interactions in cryptocurrency returns"** (2024). 40 signals, 2017–2023. An out-of-sample long-short strategy built on signal interactions reaches Sharpe above 1, gross [OOS within sample] — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1057521924007415)
- **Lasso-type factor model, 49 anomalies (2026).** The market-value (size) effect "diminished in significance during the out-of-sample phase" [OOS] — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0275531926000255)
- **Fieberg, Liedtke, Poddig, Walker & Zaremba, "A Trend Factor for the Cross-Section of Cryptocurrency Returns"** (JFQA, 2024/25). CTREND, built from price and volume technical indicators across more than 3,000 coins, "reliably predicts" returns [IS] — [Cambridge/JFQA](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/trend-factor-for-the-cross-section-of-cryptocurrency-returns/4C1509ACBA33D5DCAF0AC24379148178)
- **Wang & Pang, "The Cryptocurrency Trend Factor Revisited"** (arXiv 2611.01951, 1 Nov 2026; not peer-reviewed).
  - A code audit finds problems with information timing, indicators, forecast coverage, portfolio formation and return accounting.
  - After comprehensive correction:
    - Mean weekly gross return falls from 4.07% to 0.05%.
    - Annualised Sharpe falls from 2.08 to **0.01**.
    - Weekly alpha goes from 2.77% to −1.38% (not significant).
    - The long-short weekly **net** return at the lowest assumed costs goes from 2.93% to −0.87%.
    - The largest-100-coin mean weekly return falls from 2.93% to 1.00% — [arXiv](https://arxiv.org/abs/2611.01951)
- **Informal post-2022 evidence (not peer-reviewed).** One GitHub backtest reports momentum strong in 2020–2022 and flat in 2023–2024 (validation t-stat 1.08). It attributes the decline to a 38% collapse in cross-sectional dispersion after 2022 [POST, low quality] — [GitHub prams2104](https://github.com/prams2104/crypto-momentum-backtest)

### Inferences
- The core in-sample effect (LTW) is mainly a **2–4-week horizon among the larger coins**, which means weekly rebalancing. At retail costs of 0.2–1.2% per round trip plus altcoin spreads, a 3%/week gross long-short premium shrinks fast. Spot-only investors also lose the short leg, which several papers identify as the source of much of the alpha.
- Survivorship bias is acute: LTW's universe grew from 109 to 1,583 coins, and thousands later died. Only survivorship-free datasets (such as Zarattini et al.'s) give fair tests.
- The CTREND audit is a warning that high-Sharpe crypto factor papers can be implementation artefacts. Cross-sectional crypto results should be treated as unproven until independently replicated on a point-in-time universe.
- Short-term reversal at the 1-week horizon is concentrated in small, illiquid coins, so it is untradeable for retail after spreads. Reversal beyond one month (Dobrynskaya) argues against long holding periods for coin rotation.

### Gaps
- I found no peer-reviewed post-publication (2023–2026) test of LTW momentum.
- I found no study of long-only top-10 crypto rotation net of retail costs in 2024–2026.
- The FMPM 2025 paper's full numbers were behind a paywall.

---

## 3. Volatility targeting and risk management

### Takeaway
Volatility scaling reliably cuts drawdowns and stabilises risk in crypto: BTC volatility ranged from 20% to 130% in the 2010s and about 30–60% in the 2020s.

Man Group reports about +0.40 Sharpe from scaling to a 30% target over 2012–2024, but that test allows exposure above 100%. In my no-leverage replication (cap 100%), volatility targeting **alone** did not raise BTC's Sharpe overall (0.99 → 1.01) and hurt post-ETF (0.41 → 0.27), while cutting max drawdown from −83% to −45%.

Combined with a trend filter, it produced the best risk-adjusted and shallowest-drawdown profile in every window (max drawdown −18% to −31%), at the cost of much lower CAGR.

### Cited Findings
- **Man Group, "Crypto: Too Hot to Handle?"** (data to 31 Dec 2024 and 31 Jan 2025; published 2025–26).
  - BTC volatility ranged from 20–130% in the 2010s and about 30–60% in the 2020s.
  - At 30–60% volatility the expected drawdown could be "up to 50%"; drawdowns approached about 70% when volatility neared 130%.
  - Ex-ante scaling to a **30% volatility target** adds "around 40 Sharpe points in each instance" (likely +0.40 Sharpe) over 1 Sep 2012 – 31 Dec 2024. The benefit is robust to the half-life of the volatility estimate.
  - With a 1% BTC allocation in a 60/40 portfolio, the unscaled BTC share of portfolio risk oscillates between 0% and 6%; scaling keeps it stable [IS, institutional] — [Man Group](https://www.man.com/insights/crypto-too-hot-to-handle)
- **Concretum:** a volatility-targeted long-only BTC portfolio had a Sharpe "just below 0.8" over 2018–2025, gross [IS] — [Concretum](https://concretumgroup.com/seasonality-in-bitcoin-intraday-trend-trading/)
- **Crypto-specific academic evidence is thin.**
  - A 2026 arXiv preprint using stablecoin flows reports a 20% volatility-target benchmark with 40.8% return and −15.8% max drawdown, against −33.0% for buy-and-hold [IS, unverified] — [arXiv 2603.23480](https://arxiv.org/pdf/2603.23480)
  - A Medium practitioner piece claims more than 3× the Sharpe and one third of the drawdowns for volatility-managed against equal-weight crypto portfolios, with nearly identical average returns [low quality] — [Medium/Coinmonks](https://medium.com/coinmonks/whats-vol-got-to-do-with-it-886b57c2d762)
- **[OWN] BTC/USD, 25% target on 60-day realised volatility, capped at 100%, 10-point rebalancing band, net of 0.25%** — [Bitstamp OHLC API](https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=1000):

  | Window | Buy & hold, vol-targeted | Plain buy & hold |
  |---|---|---|
  | Full 2015–2026 | 28.3% CAGR / Sharpe 1.01 / max DD −45.3% (average exposure 47%) | 55.1% / 0.99 / −83.4% |
  | 2021–23 | 17.5% / 0.73 / −41.5% | 13.3% / 0.52 / −76.7% |
  | Post-ETF | 3.6% / **0.27** / −43.7% | 8.9% / 0.41 / −53.1% |

  - Adding the trend filter (TSMOM ensemble × volatility target) gave 26.5% / 1.25 / −30.7% over the full period and 10.6% / 0.64 / −18.6% post-ETF.
  - Turnover from volatility targeting alone was only about 1.2/yr with the 10-point band.

### Inferences
- Under a no-leverage constraint, volatility targeting is a **de-risking rule, not a Sharpe enhancer**. With BTC realised volatility at 40–55% in 2023–2026 and a 25% target, the book sits about 45–60% invested most of the time. It cannot lever up in calm periods, which is where Man-style results gain much of their Sharpe.
- Volatility targeting alone does not avoid slow bear markets: in 2022 a vol-targeted buy-and-hold still lost 32% against −64% unscaled. The trend filter does the "exit"; the volatility target trims the size of losses before the exit triggers.
- Since BTC and ETH daily returns are 0.78–0.92 correlated (see §8), "equal risk" across BTC and ETH gives limited diversification. Book-level volatility targeting matters more than per-coin weighting.

### Gaps
- I found no peer-reviewed crypto-specific volatility-managed portfolio study with post-2021 out-of-sample results.
- Man Group's exact Sharpe levels (before and after scaling) are only shown in a figure.

---

## 4. Seasonality and calendar effects

### Takeaway
Calendar effects in crypto are statistically fragile, sample-dependent and mostly decayed or reversed after publication.

The surviving patterns are mainly **intraday** (returns concentrated in overnight and non-US hours since about 2021, and around the Sunday-evening/Monday Asia open). These require hourly trading and their costs are not reported.

At daily resolution, only a Monday effect shows modest persistence. My own turn-of-month test reversed sign post-ETF. Weekend volatility and volume collapsed after spot ETFs.

### Cited Findings
- **Caporale & Plastun, "The day of the week effect in the cryptocurrency market"** (Finance Research Letters 31, 2019; CESifo WP 6716, 2017).
  - BTC Monday returns are "significantly higher" than on other days; LTC, XRP and DASH show no effect.
  - Trading-simulation profits are mostly "not significantly different from the random ones" [IS] — [IDEAS](https://ideas.repec.org/p/ces/ceswps/_6716.html); [Brunel repository](https://bura.brunel.ac.uk/handle/2438/17208)
- **Liu & Tsyvinski (to May 2018):** BTC Saturday mean of 0.33%/day against a 0.52%/day overall average [IS] — [NBER w24877 PDF](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf)
- **Quantpedia, intraday (Gemini hourly, 9 Oct 2015 – 3 Feb 2022).**
  - The strongest hours are 22:00–23:00 UTC; the worst are 03:00–04:00 UTC (none significantly negative).
  - Holding 22:00–00:00 UTC gave about 33%/yr. An extended sample showed 40.64%/yr with Calmar 1.79.
  - Transaction costs are "Not Reported" [IS] — [Quantpedia](https://quantpedia.com/are-there-seasonal-intraday-or-overnight-anomalies-in-bitcoin/); [Quantpedia strategy page](https://quantpedia.com/strategies/intraday-seasonality-in-bitcoin)
- **Quantpedia, "How To Profitably Trade Bitcoin's Overnight Sessions?"** (12 Nov 2024; out-of-sample from Oct 2021, when the BITO futures ETF launched).
  - "Since 2021 … most BTC returns have been realized in overnight sessions" (outside 10:00–16:00 ET); US day-session returns before 2021 were significantly positive.
  - MAX(10) overnight variant, out-of-sample: "over 35%" with about −12% max drawdown. No costs [POST] — [Quantpedia](https://quantpedia.com/?p=36811)
- **Concretum (2018–2025):** trend returns are strongly positive from about 19:00 New York time on Sunday for about 24 hours, aligned with the Tokyo open (the "Monday Asia Open Effect"). The effect is much stronger after mid-2020; returns are gross [IS] — [Concretum](https://concretumgroup.com/seasonality-in-bitcoin-intraday-trend-trading/)
- **Quantpedia 2024 revisit:** no significant day-of-week effect for BTC MAX/MIN strategies [POST] — [Quantpedia](https://quantpedia.com/revisiting-trend-following-and-mean-reversion-strategies-in-bitcoin/)
- **Kaiko (via press).**
  - The weekend share of BTC volume hit an all-time low of about 16% in mid-2024, against up to 28% in 2019; another reading put it at 13% in early 2024, against about 25% in 2018–2021.
  - Kaiko calls the decline a long-running trend "exacerbated by ETFs", also linked to the 2023 failures of crypto-friendly banks.
  - Weekend volatility had "generally declined since 2021", but thin liquidity raises the risk of weekend gaps — [The Block, 30 Jun 2024](https://www.theblock.co/news/ecosystems/2024-06-30-bitcoin-sees-all-time-low-weekend-trading-levels-following-etf-approvals-kaiko-302705); [The Block, 27 Feb 2024](https://www.theblock.co/news/markets/2024-02-27-bitcoin-weekend-trading-279353)
- **[OWN] BTC/USD daily (Bitstamp UTC days), mean log return by weekday, Monday to Sunday, in basis points/day** — [Bitstamp OHLC API](https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=1000):

  | Window | Mon | Tue | Wed | Thu | Fri | Sat | Sun | Notable |
  |---|---|---|---|---|---|---|---|---|
  | 2015–2020 | **+64 (t = 2.93)** | +6 | +3 | +17 | +33 | +28 | −7 | — |
  | 2021–2023 | −4 | +13 | +25 | −26 | +2 | +1 | +13 | all \|t\| < 1 |
  | 2024–Nov 2026 | **+44 (t = 1.94)** | −31 (t = −1.5) | +34 | −37 (t = −1.7) | +1 | −3 | +13 | — |

  - That is 21 tests, so one or two |t| near 2 are expected by chance.
  - Annualised volatility by weekday, 2024–26: Saturday **25%** and Sunday 39%, against 48–54% on weekdays. In 2015–20 it was Saturday 64% and Sunday 60%, against 70–101% on weekdays.
- **[OWN] Turn of month (last day plus first three days), BTC mean in basis points/day** — [Bitstamp OHLC API](https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=1000):
  - 2015–20: +62.6 against +14.2 on other days.
  - 2021–23: +26.2 against 0.0.
  - **2024–26: −14.7 against +5.8 (reversed).**

### Inferences
- Daily-or-slower calendar rules (Monday, turn of month, weekend) offer no reliable edge after 2020. The only daily-resolution effect with some persistence (Monday) is within multiple-testing noise.
- Intraday patterns appear real and shifted with institutionalisation: US-hours returns faded after 2021 and Asia-open/overnight returns strengthened. But exploiting them needs intraday execution, they are reported gross, and they fall outside the investor's daily-or-slower constraint.
- Practical relevance: execution timing. Lower weekend volatility and liquidity mean weekend fills carry gap risk. A daily 00:05 UTC decision lands in the thin Asia session.

### Gaps
- I found no peer-reviewed post-2021 out-of-sample test of BTC day-of-week or turn-of-month effects.
- Hourly post-ETF evidence comes only from Quantpedia and Concretum, gross of costs.
- The primary Kaiko reports were not retrieved.

---

## 5. Carry, basis and funding rates

### Takeaway
Crypto carry is large and well documented: Schmeling, Schrimpf & Todorov (BIS) find it averages above 10% a year and reaches up to 60%. It is driven by leveraged retail demand and limited arbitrage capital, and high carry predicts crashes.

But it requires derivatives. The trade is exposed to margin spikes, liquidations and exchange failure (2022), and it **compressed sharply after spot ETFs**:
- CME basis fell to about 4–5% (below T-bills) through 2025–26, from about 17% a year earlier.
- Deribit BTC perpetual funding averaged 10.3% in 2024, 5.4% in 2025 and 2.3% in 2026 YTD [OWN].

For a spot-only EUR retail investor this is excluded. Post-2024 the excess over cash is roughly zero or negative.

### Cited Findings
- **Schmeling, Schrimpf & Todorov, "Crypto Carry"** (BIS WP 1087, Apr 2023, revised Oct 2025; also CEPR DP 20719).
  - Carry (long spot, short futures) "can become very large (up to 60% p.a.)", averages "above 10% annually" and varies strongly over time.
  - Interest-rate differentials explain "very little". The carry is driven by trend-chasing small investors seeking leverage and limited arbitrage capital.
  - "High carry predicts future price crashes", and the trade "is risky because margins spike and liquidations occur during drawdowns" [IS] — [BIS WP 1087 page](https://www.bis.org/publ/work1087.htm); [BIS PDF](https://www.bis.org/publ/work1087.pdf); [IDEAS CEPR DP 20719](https://ideas.repec.org/p/cpr/ceprdp/20719.html)
- **He, Manela, Ross & von Wachter, "Fundamentals of Perpetual Futures"** (arXiv 2212.06888; last revised Aug 2024).
  - Perpetual–spot deviations are "considerably larger" than in traditional currency markets, comove across coins and "shrink over time as markets mature".
  - An implied arbitrage strategy earns high Sharpe ratios even at the highest Binance fee tier, but "even arbitrage opportunities that appear riskless in theory may be risky in practice" [IS] — [arXiv](https://arxiv.org/abs/2212.06888)
- **Post-ETF compression (news and vendor data).**
  - Feb 2024: annualised funding on Binance BTC perpetuals exceeded 100% for the first time in at least a year — [FXStreet, 27 Feb 2024](https://www.fxstreet.com/cryptocurrencies/news/bitcoin-funding-rates-jump-to-100-sparking-opportunity-for-savvy-traders-202402270607)
  - Feb 2025: CME annualised basis about 4% (Velo data), the lowest since ETF launch and below the 5% risk-free rate — [CoinDesk, 25 Feb 2025](https://dev.coindesk.com/nl/markets/2025/02/25/u-s-bitcoin-etfs-post-year-s-2nd-biggest-outflows-as-basis-trade-drops-below-5)
  - Jul 2025: CME basis about 4.3% and perpetual funding about 1% — [Mitrade, 2 Jul 2025](https://www.mitrade.com/insights/news/live-news/article-3-931094-20250702)
  - Jan 2026: Amberdata's Greg Magadini says the basis was "closer to 17%" a year earlier and "now sits near 4.7%"; CME BTC futures open interest is below $10bn, from a peak above $21bn — [Advisor Perspectives/Bloomberg, 22 Jan 2026](https://www.advisorperspectives.com/articles/2026/01/22/wall-street-pulls-back-bitcoin-trade) (snippet; page returned 403)
  - Apr 2026: CME BTC futures activity at a 14-month low as the basis trade unwound — [The Block, 9 Apr 2026](https://www.theblock.co/news/business/2026-04-09-cme-bitcoin-futures-activity-slumps-to-14-month-low-as-basis-trade-unwind-drains-institutional-demand-396722)
  - May 2026: BTC's 30-day average funding (venue aggregate) was negative for 66 days, "the longest streak this decade", with shorts paying about 12% annualised. A K33 "83–96% win rate" for buying in negative-funding regimes rests on only six episodes — [Decrypt, May 2026](https://decrypt.co/366768/bitcoins-81k-rally-comes-amid-66-day-negative-funding-streak-heres-why)
  - Aug 2026 headline: "The Bitcoin futures yield collapse: once over 20%, now less than Treasury notes" (body not retrieved) — [FXStreet, 3 Aug 2026](https://www.fxstreet.com/cryptocurrencies/news/the-bitcoin-futures-yield-collapse-once-over-20-now-less-than-treasury-notes-202608031149)
  - Conflicting reading: on one 7 August CME settlement check (the snippet did not give the year; probably 2026), gross carry was 5.69–7.89% against a 4.19% Treasury yield, before funding, margin and fees — [CryptoSlate](https://cryptoslate.com/?p=553728)
- **[OWN] Deribit perpetual funding**, annualised mean (hourly funding summed) and share of hours with negative funding — [Deribit API](https://www.deribit.com/api/v2/public/get_funding_rate_history?instrument_name=BTC-PERPETUAL):

  | Year | BTC-PERP | ETH-PERP |
  |---|---|---|
  | 2019 (from 30 Apr) | 14.6% (36% hours negative) | 9.9% |
  | 2020 | 9.2% (27%) | 6.3% |
  | 2021 | **16.5%** (22%) | **17.3%** |
  | 2022 | **−2.3%** (49%) | **−6.1%** (59%) |
  | 2023 | 6.9% (17%) | 7.9% |
  | 2024 | 10.3% (16%) | 8.4% |
  | 2025 | 5.4% (21%) | 1.0% (43%) |
  | 2026 YTD | **2.3%** (22%) | 1.4% |

  - BTC 2026: H1 1.0% and H2 3.9% annualised.
  - Monthly extremes for BTC: +49.5% (Jun 2019) and −39.3% (Mar 2020). ETH reached +58.9% in Jan 2021.
  - These are gross funding receipts for a short-perpetual leg, before fees, basis mark-to-market, margin and venue risk.
- **Context on cash.** USD T-bills yielded about 4–5% over 2023–2025, so 2025–26 funding of 1–5% is at or below cash — [CoinDesk, 25 Feb 2025](https://dev.coindesk.com/nl/markets/2025/02/25/u-s-bitcoin-etfs-post-year-s-2nd-biggest-outflows-as-basis-trade-drops-below-5)

### Inferences
- Carry is a **bull-market, leverage-demand premium**. It was large in 2019–2021 and 2024, negative in 2022, and roughly at cash level from 2025. ETF-era arbitrage capital (CME basis traders) competed most of it away.
- For this investor it is doubly excluded: it needs derivatives and a margin account at an exchange, which is the counterparty risk that hit FTX customers in 2022, and its post-2024 excess return over EUR cash is close to zero.
- A possible use is as a **risk signal**. Very high funding or basis (for example above 30% annualised) has historically coincided with crowded leverage and crash risk (BIS). This is in-sample evidence only and adds a parameter.

### Gaps
- I did not retrieve the BIS paper's Sharpe ratio, standard deviation or CME vs offshore breakdown (the PDF was bot-protected), nor the Oct 2025 revision's post-ETF results.
- I found no rigorous study of realised cash-and-carry losses in 2022 (FTX, Celsius, 3AC).
- Binance and Bybit funding histories could not be downloaded here (geo-blocked). Deribit funding may differ from aggregate funding (for example, the May 2026 "negative 66 days" aggregate reading against Deribit's slightly positive H1 2026).

---

## 6. On-chain and sentiment factors

### Takeaway
Rigorous out-of-sample evidence is thin.

Attention and sentiment (Google searches, Twitter counts, Fear & Greed) predict BTC returns in-sample at **1-day to 2-week horizons**. One Finance Research Letters paper reports out-of-sample predictability for the Fear & Greed index at 1-day to 1-week horizons. These horizons are too short to survive retail costs at daily-or-slower cadence.

On-chain cycle indicators (MVRV, NUPL, Puell, Mayer, Pi-cycle) are fitted on 3–4 cycles. A 2026 SSRN paper documents their monotonic decay: none fired at the Oct 2025 top. A broad 2026 thesis finds only 4 of 67 in-sample-significant predictors beat a random walk out-of-sample.

### Cited Findings
- **Liu & Tsyvinski (to May 2018).** A one-standard-deviation rise in Google searches for "Bitcoin" brings +2.3% two-week-ahead returns. A one-standard-deviation rise in Twitter counts brings +2.50% the next week. A one-standard-deviation rise in the "Bitcoin hack"/"Bitcoin" search ratio brings −2.75% the next week. The price-to-"dividend" proxy and realised volatility do not predict BTC [IS] — [NBER w24877 PDF](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf)
- **Finance Research Letters 58 (2023), reported as He et al.** The Crypto Fear & Greed Index has significant in-sample and out-of-sample predictive power for crypto returns at 1-day to 1-week horizons [OOS within sample; details not verified] — [IDEAS](https://ideas.repec.org/a/eee/finlet/v58y2023ipas154461232300778x.html)
- **Guidolin & Ionta (JIFMIM 2026).** An out-of-sample forecasting framework with Google Trends sentiment and blockchain fundamentals, data to Apr 2025; the Google-specific result was not visible — [Bocconi IRIS PDF](https://iris.unibocconi.it/retrieve/ca0d5636-301d-4177-b28c-1e88a6b6cdb1/Guidolin%20and%20Ionta%20JIFMIM%202026.pdf)
- **Sanhueza (doctoral thesis, Universidad Diego Portales, 2026).** Of 67 variables significant in-sample, only 29 improve out-of-sample performance at any horizon, and just **4 beat the random walk consistently** [OOS] — [UDP thesis PDF](https://doctorados.udp.cl/cms/wp-content/uploads/2026/06/Tesis_Doctoral_Aliro_Sanhueza.pdf)
- **Stock-to-flow and Metcalfe's Law** explain BTC returns in-sample but have "limited to no ability" out-of-sample (J. Risk & Financial Management 17(10), 2024) [OOS] — [IDEAS](https://ideas.repec.org/a/gam/jjrfmx/v17y2024i10p443-d1490211.html)
- **Grobys, Näsman & Sandretto, "Using on-chain data to predict Bitcoin cycles"** (Univ. of Vaasa). The MVRV Z-score was the best trading signal, beating buy-and-hold and NUPL/CVDD on returns and risk-adjusted terms. The test uses historical cycles plus Monte Carlo, so the out-of-sample design is unverified [IS] — [Osuva/UWasa](https://osuva.uwasa.fi/bitstreams/6575b90c-6140-44e7-a798-011a1793d134/download)
- **Molnar, "Bitcoin Runs on a Clock: Why Every Price Indicator Dies and the Halving Clock Doesn't"** (SSRN 6977940; Quantpedia summary 19 Oct 2026).
  - Pi-cycle, MVRV, Mayer, Puell and the 200-week MA degraded "precise → early → silent".
  - Pi-cycle marked the Apr 2021 top within a day but did not fire at the Oct 2025 top, and neither did MVRV, Mayer or Puell.
  - MVRV cycle peaks fell from 5.88 to 4.72, 3.96 and then 2.74. Short-horizon price indicators decay toward zero or invert.
  - The halving-timing result rests on three tops identified retrospectively, and the paper calls its own p-values unreliable [POST evidence of decay] — [Quantpedia](https://quantpedia.com/bitcoin-runs-on-a-clock-why-every-price-indicator-dies-and-the-halving-clock-doesnt/)
- **Cycle context [OWN].** The BTC close peaked at $124,728 on 6 Oct 2025 (Bitstamp) and stood at $58,910 on 24 Nov 2026 (−52.8%). ETH peaked at $4,830 on 22 Aug 2025 and stood at $1,640 (−66.0%) — [Bitstamp OHLC API](https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=1000)

### Inferences
- On-chain valuation oscillators look like curve-fits to a shrinking number of cycles. Their thresholds drift as volatility and cycle amplitude fall, which is exactly what decay looks like. Any use needs thresholds that adapt with the regime and a locked hold-out, and still carries high overfitting risk.
- Sentiment predictability lives at 1–14 days, which overlaps with short-term TSMOM and trades too often for retail fees. At weekly-or-slower frequency it is mostly subsumed by price trend.
- Good on-chain data (Glassnode) is paid and revised after the fact, which adds look-ahead risk in backtests.

### Gaps
- I found no peer-reviewed out-of-sample study of MVRV, NUPL or exchange-flow signals covering 2022–2026.
- I found no rigorous out-of-sample study of the Fear & Greed index after 2023.
- I found no Glassnode, Coin Metrics or CryptoQuant study with out-of-sample trading results.

---

## 7. Options and the volatility risk premium (Deribit)

### Takeaway
BTC carries a sizeable volatility risk premium: implied volatility (DVOL) exceeded subsequent 30-day realised volatility by about 18 points in 2021, about 6–7 points in 2023–2025, and about **0 in 2026** [OWN]. Its upside (call) premium was 2–3× that of SPY/QQQ (Anchorage).

But systematic covered calls produced about −0.1%/yr net over Oct 2021 – Apr 2026 unfiltered. Filtered versions earned about +5%/yr. Neither reduced the worst drawdown, and covered calls cap the upside.

Puts and covered calls require an options account, which falls outside spot-only.

### Cited Findings
- **Almeida, Grith, Miftachov & Wang, "Risk Premia in the Bitcoin Market"** (arXiv 2410.15195, Deribit options).
  - BTC's variance risk premium is higher than the S&P 500's (about 2% benchmark).
  - Returns between −60% and −20% account for 33% of the BTC premium, with a price of risk of 1.33 against 2.63 for the S&P 500, so left-tail pricing is weaker than in equities.
  - Out-of-the-money calls are expensive, reflecting demand for right-tail exposure [IS] — [arXiv HTML](https://arxiv.org/html/2410.15195v2)
- **Anchorage Digital (David Lawant), "Synthetic Yield on Bitcoin"** (28 May 2026). Deribit implied-volatility surfaces via CoinMetrics, 1 Oct 2021 – 30 Apr 2026, Black-76, one volatility point of slippage per leg; vendor research [VENDOR]:
  - Unfiltered 20-delta, 30-day calls, full period: net yield −0.5% (−0.1%/yr), profit factor 1.00, 57 of 70 trades won, Sharpe 0.20 → 0.25.
  - With regime and implied-volatility filters: +5.2%/yr overlay yield, in the market 44% of the time. Total return was +98.1% against +74.4% for spot, but max drawdown was −73.5% against −76.7%, so it was **not reduced**.
  - Last 12 months (Apr 2025 – Apr 2026): +5.5% overlay against −19.4% spot; max drawdown −44.5% against −49.7%.
  - Deltas of 15–25 and tenors of at least 21 days worked best. Deltas of 30–35 often lost; 7–14-day tenors underperformed.
  - BTC's upside volatility risk premium averaged about **2–3× SPY/QQQ**, with negative excursions such as Jan 2026 — [Anchorage Digital](https://www.anchorage.com/research/synthetic-yield-on-bitcoin-implementation-discipline-and-performance-boundaries-of-systematic-covered-call-writing)
- **Alexander & Imeraj, "The Bitcoin VIX and its variance risk premium"** (published, Sussex repository). I did not retrieve figures — [Sussex SRO](https://sro.sussex.ac.uk/id/eprint/91094/)
- **[OWN] BTC DVOL against realised volatility over the next 30 days**, in volatility points (DVOL from 24 Mar 2021) — [Deribit DVOL API](https://www.deribit.com/api/v2/public/get_volatility_index_data?currency=BTC&resolution=1D); [Bitstamp OHLC API](https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=1000):

  | Year | Mean DVOL | Next-30-day realised vol | Premium | Days positive |
  |---|---|---|---|---|
  | 2021 | 91.8 | 73.9 | **+17.9** | 88% |
  | 2022 | 73.6 | 61.6 | +12.0 | 67% |
  | 2023 | 49.6 | 43.1 | +6.6 | 72% |
  | 2024 | 57.7 | 50.9 | +6.8 | 72% |
  | 2025 | 46.0 | 39.8 | +6.2 | 70% |
  | 2026 (to Oct) | 42.5 | 42.8 | **−0.3** | 59% |

  - Worst day: −45.4 points on 28 Jan 2026, ahead of a volatile Feb 2026.
  - ETH's premium was smaller: +11.4 (2021), +8.7, +5.3, +3.2, **−2.7 (2025)** and +1.1 (2026).
  - This is a volatility-point premium, not option-strategy P&L.

### Inferences
- The premium has shrunk in step with BTC's volatility. It was about zero for BTC in 2026 and negative for ETH in 2025, so systematic short-volatility no longer has a large cushion.
- The premium is concentrated on the **call side** (demand for upside). Covered calls harvest it, but give up exactly the right tail that drives long-run crypto returns. Selling puts adds left-tail exposure, and crash-day losses are severe.
- Not implementable under spot-only, no-derivatives rules. If anything, implied volatility (DVOL) is useful as a forward-looking input for volatility targeting instead of realised volatility. That idea is untested here.

### Gaps
- I found no independent academic backtest of BTC covered calls or put selling net of Deribit fees post-2022.
- I did not verify the EU/French retail accessibility of Deribit options.
- I found no data on BTC covered-call ETF live performance (for example, IBIT-option income funds).

---

## 8. Regime change: spot ETFs, institutional flows, equity correlation, and volatility and drawdowns by year

### Takeaway
Since Jan 2024, BTC volatility has fallen to record lows: about 42% annualised in 2025, against 65–93% in 2017–2022. Weekend activity collapsed, and BTC trades more like a high-beta tech/risk asset, with episodic 0.8 correlations to the S&P 500/Nasdaq in 2026.

Academic event studies disagree on whether ETFs *caused* lower volatility. Lower volatility did not mean shallow drawdowns: the Oct 2025 – Nov 2026 BTC drawdown is −53% and ETH's is −66%.

Trend rules kept working as drawdown control post-ETF, but with lower absolute returns and more whipsaw in range-bound phases (2025).

### Cited Findings
- **[OWN] BTC/USD by calendar year (Bitstamp UTC closes, annualised volatility with √365)** — [Bitstamp OHLC API](https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=1000):

  | Year | Return | Realised vol | Intra-year max DD | Worst DD from ATH |
  |---|---|---|---|---|
  | 2015 | +34.2% | 71.1% | −45.7% | −84.9% |
  | 2016 | +124.3% | 48.3% | −29.6% | −68.2% |
  | 2017 | +1336% | 92.9% | −35.1% | −35.1% |
  | 2018 | −73.4% | 84.6% | −81.5% | −83.4% |
  | 2019 | +94.1% | 70.1% | −48.8% | −82.5% |
  | 2020 | +304.5% | 81.0% | −53.3% | −74.8% |
  | 2021 | +59.4% | 81.1% | −53.1% | −53.1% |
  | 2022 | −64.2% | 64.6% | −67.0% | −76.7% |
  | 2023 | +155.7% | 43.6% | −20.1% | −75.4% |
  | 2024 | +121.0% | 53.1% | −26.2% | −41.5% |
  | 2025 | −6.3% | **41.9%** | −32.1% | −32.1% |
  | 2026 YTD (to 24 Nov) | −32.7% | 45.4% | −39.6% | −53.1% |

- **[OWN] ETH/USD by calendar year** (2017 from 16 Aug; Bitstamp has no ETH before Aug 2017) — [Bitstamp OHLC API](https://www.bitstamp.net/api/v2/ohlc/ethusd/?step=86400&limit=1000):

  | Year | Return | Realised vol | Intra-year max DD | Worst DD from ATH |
  |---|---|---|---|---|
  | 2018 | −82.4% | 111.2% | −94.0% | −94.0% |
  | 2019 | −1.6% | 82.7% | −63.6% | −92.5% |
  | 2020 | +473% | 104.9% | −61.7% | −92.1% |
  | 2021 | +399% | 108.8% | −57.3% | −57.3% |
  | 2022 | −67.5% | 87.7% | −74.0% | −79.3% |
  | 2023 | +90.9% | 46.5% | −27.4% | −75.1% |
  | 2024 | +46.1% | 64.3% | −45.3% | −54.1% |
  | 2025 | −10.9% | 74.6% | −60.1% | −69.4% |
  | 2026 YTD | −44.7% | 61.2% | −53.3% | −67.6% |

- **[OWN] BTC–ETH daily-return correlation by year:** 0.82 (2018), 0.83, 0.87, 0.78 (2021), 0.90 (2022), 0.83, 0.80 (2024), 0.82 (2025), **0.92 (2026)** — [Bitstamp OHLC API](https://www.bitstamp.net/api/v2/ohlc/ethusd/?step=86400&limit=1000)
- **Cross-check, K33 Research:** 2025 BTC daily realised volatility was 2.24%, the lowest annual reading on record, against a 7.58% peak in 2013 — [CryptoSlate](https://cryptoslate.com/?p=513516). That is about 42.8% annualised with √365, matching my 41.9%.
  - K33 also estimates net ETF buying at about 630,000 BTC in 2024 against about 160,000 in 2025, so volatility kept falling even as inflows slowed — [MEXC/K33](https://www.mexc.com/news/400085)
- **Block Scholes/Bybit [VENDOR]:** the BTC volatility decline correlates with the Jan 2024 ETF launch and accelerated after Jan 2025, while ETH volatility stayed near usual levels — [Bybit/Block Scholes](https://www.bybit.com/en/learn/crypto-insight/bitcoin-volatility-enters-a-historically-low-area-due-to-spot-etf-inflows)
- **Academic event studies disagree.**
  - A 2025 Quarterly Review of Economics & Finance GARCH event study finds BTC and XRP volatility fell after ETF approval, supporting stabilisation. Its working-paper version (Univ. of Pretoria 2024) found effects mainly on other coins' volatility — [UP repository](https://repository.up.ac.za/items/f5a1d464-7b26-41bb-949c-f434d4ddd43e); [UP WP 2024/16](https://www.up.ac.za/media/shared/61/WP/wp_2024_16.zp249956.pdf)
  - Pastorek et al., using a control group of other coins, report an *increase* in BTC's relative daily volatility — [SAV journal PDF](https://www.sav.sk/journals/uploads/082709295-6%2026%20Pastorek%20+%20SR.pdf)
  - A FIMM 2025 proceedings paper finds abnormal returns around the Jan 2024 approval insignificant ("buy the rumor, sell the news") — [Atlantis Press](https://www.atlantis-press.com/article/126017212.pdf)
- **Equity correlation.**
  - CME Group: since 2020 BTC has moved from no meaningful relationship with equities to a largely positive correlation — [CME Group, 2025](https://www.cmegroup.com/insights/economic-research/2025/why-is-bitcoin-moving-in-tandem-with-equities.html)
  - Man Group: rolling 20-day BTC–S&P 500 futures correlation has risen (to Jan 2025) — [Man Group](https://www.man.com/insights/crypto-too-hot-to-handle)
  - 30-day BTC–S&P 500 correlation: −0.299 in Dec 2025, about 0.18 in Jan 2026; long-run average about 0.25–0.32 — [Crypto Briefing](https://cryptobriefing.com/bitcoin-equity-correlation-two-year-low/)
  - 30-day BTC–Nasdaq-100 correlation about 0.80 in early 2026, the highest in about four years — [crypto.news](https://crypto.news/bitcoin-trading-like-tech-stock-not-gold/)
  - 30-day BTC–S&P 500 correlation 0.81 in May 2026, a multi-year high — [cash-online.de](https://www.cash-online.de/a/bitcoin-und-sp-500-hohe-korrelation-aber-kein-verlaessliches-muster-719835/)
- **Market structure:** the weekend share of volume fell to about 13–16% in 2024 from about 25–28% in 2018–2021 (Kaiko) — [The Block](https://www.theblock.co/news/ecosystems/2024-06-30-bitcoin-sees-all-time-low-weekend-trading-levels-following-etf-approvals-kaiko-302705)
- **Effect on trend strength [OWN].**
  - BTC buy-and-hold Sharpe: 1.38 (2015–20), 0.52 (2021–23), 0.41 (post-ETF). The TSMOM ensemble went 1.54, 0.71 and 0.71 (net of 0.25%).
  - The trend-over-buy-and-hold Sharpe increment rose post-ETF (+0.30), but absolute trend returns post-ETF (about 10–20% CAGR) are an order of magnitude below 2015–2020 (about 100%).
  - In 2025–26 YTD every BTC trend rule net of costs was flat to slightly negative, except the 50-day SMA (+5.8%/yr), against buy-and-hold at −21%/yr — [Bitstamp OHLC API](https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=1000)

### Inferences
- The post-ETF regime looks like "lower volatility, still deep drawdowns, more range-bound chop". That combination hurts single-lookback trend rules through whipsaw (2025) but rewards drawdown avoidance (2022, 2026).
- ETH did not share BTC's volatility compression: 61–75% in 2025–26 against BTC's 42–45%. ETH has also underperformed BTC sharply (−14%/yr post-ETF against +9%). Adding ETH did not diversify, given 0.8–0.9 correlation, and ETH has been the weaker trend asset post-ETF.
- Higher and unstable equity correlation (from −0.3 to 0.8 within months in 2025–26) reduces crypto's diversification value against a PEA equity portfolio during sell-offs. That supports book-level volatility targeting.

### Gaps
- I found no peer-reviewed study of trend/momentum strength before and after spot ETFs.
- My BTC/ETH yearly series come from one venue (Bitstamp), and ETH 2015–2017 is missing.
- I found no authoritative BTC–equity correlation series for H2 2026.

---

## 9. Ranking of strategy families (evidence quality × recent performance × fit for a spot-only EUR retail investor)

### Takeaway
1. **Long-or-flat time-series trend on BTC, using lookback ensembles, with volatility targeting as the sizing layer.** This is the only family with peer-reviewed support, one net-of-cost out-of-sample paper, consistent practitioner results, and post-publication survival as drawdown control.
2. Volatility targeting as a risk layer (not alpha).
3. Cross-sectional momentum: weak to unproven for long-only spot.
4. On-chain and sentiment: decaying, overfit.
5. Calendar effects: decayed or intraday-only.

Carry and options premia are real but derivatives-only, and compressed post-2024.

### Cited Findings
| Rank | Family | Evidence quality | Post-2021 / post-ETF performance | Fit (spot, no leverage, daily+) | Key sources |
|---|---|---|---|---|---|
| 1 | TSMOM and trend (BTC; ETH secondary) | Peer-reviewed in-sample (RFS 2021, FM 2021); out-of-sample net of costs (IREF 2024); practitioner (Concretum 2025, Le & Ruthbah 2024, Quantpedia 2024 post-publication) | [OWN] Post-ETF BTC ensemble 19.5% CAGR / Sharpe 0.71 / max DD −26.7% against buy & hold 8.9% / 0.41 / −53.1%; 2022: −29% against −64%; 200-day SMA flat in 2022 but −23% in 2021 and −19% in 2025 (whipsaw); 50/200 crossover failed post-ETF | High: 4–14 trades/yr, costs 1–3.5%/yr at 0.25% | [NBER](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf); [EconPapers FM](https://econpapers.repec.org/RePEc:bla:finmgt:v:50:y:2021:i:1:p:107-137); [EconPapers IREF](https://econpapers.repec.org/RePEc:eee:reveco:v:93:y:2024:i:pb:p:858-874); [CXO](https://www.cxoadvisory.com/technical-trading/crypto-asset-trend-following-strategies/); [Quantpedia](https://quantpedia.com/revisiting-trend-following-and-mean-reversion-strategies-in-bitcoin/) |
| 2 | Volatility targeting (sizing) | Institutional (Man 2012–2024: +~0.4 Sharpe, leverage allowed); little peer-reviewed crypto work | [OWN] No-leverage: Sharpe roughly unchanged, max DD about halved; with trend: post-ETF max DD −18.6% | High (low turnover with a band) | [Man Group](https://www.man.com/insights/crypto-too-hot-to-handle) |
| 3 | Cross-sectional momentum (coin rotation) | Peer-reviewed in-sample (JF 2022), mixed replications to 2022, crash-prone; CTREND audit (2026) collapses Sharpe 2.08 → 0.01 | Informal: flat 2023–24 | Low: weekly turnover, altcoin spreads, short-leg alpha, survivorship | [Cowles PDF](https://cowles.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf); [arXiv 2611.01951](https://arxiv.org/abs/2611.01951); [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1057521924001509) |
| 4 | On-chain and sentiment | In-sample; few out-of-sample tests, short horizons; 4 of 67 predictors survive out-of-sample | Decay: MVRV/Pi-cycle silent at the Oct 2025 top | Low (paid data, overfitting) | [Quantpedia/Molnar](https://quantpedia.com/bitcoin-runs-on-a-clock-why-every-price-indicator-dies-and-the-halving-clock-doesnt/); [UDP thesis](https://doctorados.udp.cl/cms/wp-content/uploads/2026/06/Tesis_Doctoral_Aliro_Sanhueza.pdf) |
| 5 | Calendar and seasonality | Daily: weak (FRL 2019, mostly not beating random); intraday: practitioner only, gross | [OWN] Turn of month reversed in 2024–26; Monday t ≈ 1.9 (multiple testing) | Low (intraday needed) | [IDEAS](https://ideas.repec.org/p/ces/ceswps/_6716.html); [Quantpedia](https://quantpedia.com/?p=36811) |
| Excluded | Carry, basis, funding | Strong (BIS 2023/2025; He et al. 2024) | [OWN] Deribit BTC funding 10.3% (2024), 5.4% (2025), 2.3% (2026); CME basis about 4–5%, below T-bills | Not allowed (derivatives, venue risk) | [BIS](https://www.bis.org/publ/work1087.htm); [arXiv](https://arxiv.org/abs/2212.06888) |
| Excluded | Options volatility premium (covered calls, put selling) | Academic (premium exists); vendor backtests | Unfiltered covered calls −0.1%/yr (Oct 2021 – Apr 2026); BTC premium about 0 in 2026 [OWN] | Not allowed (options) | [Anchorage](https://www.anchorage.com/research/synthetic-yield-on-bitcoin-implementation-discipline-and-performance-boundaries-of-systematic-covered-call-writing); [arXiv](https://arxiv.org/html/2410.15195v2) |

### Inferences
- **Realistic expectations for a trend-plus-volatility-target BTC sleeve in the post-ETF regime:** Sharpe of about 0.5–0.8, CAGR of about 8–20%, and max drawdown of about −18% to −35% net of retail costs, with long flat spells and large bull-market lag. Not the 1.5–2.5 Sharpe of in-sample papers.
- **Design implications** from the evidence:
  - Prefer **ensembles of lookbacks** (1–12 months) over a single 200-day SMA or a 50/200 crossover.
  - Add a **band or buffer** to cut whipsaw (17–19 switches a year in 2021 and 2025 for the 200-day SMA).
  - Avoid lookbacks of 20 days or less at retail fees.
  - Treat ETH as optional: it is highly correlated and was weaker post-ETF.
  - Report results by sub-period (2015–20, 2021–23, post-ETF), because whole-sample statistics are dominated by 2016–2017 and 2020.
- Any strategy whose published headline Sharpe exceeds 1.5 in crypto should be presumed in-sample or gross until shown otherwise. CTREND (2.08 → 0.01 after audit), Rozario et al. (zero costs) and Detzel et al. (gross, through 2017) are examples.

### Gaps
- I found no independent, peer-reviewed post-ETF evaluation of any crypto strategy family. The post-2024 performance figures here are my own single-venue replication, and they should be re-run in the project's own engine with point-in-time EUR prices, EURC cash yield (assumed 0% here) and actual venue fees.
- French tax treatment of BTC→EURC switches (crypto-to-crypto exchanges are generally tax-neutral in France) affects net results but was out of scope and not verified here.
