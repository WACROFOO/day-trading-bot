# Daily-to-monthly systematic strategies for a small retail bot: evidence, post-publication record, critiques

Provenance key, used on every line below: **[F]** means I read the passage in the fetched page or PDF this session (PDFs were converted with pdftotext and the quoted lines read directly). **[S]** means the wording comes only from a search-result snippet or summary. I did not open the page itself, so treat it as unverified until someone reads the original. Quotes are verbatim. Where a figure was not given, I wrote "not stated". Research date: 2026-10-31. Evidence tiers follow the brief: (A) peer-reviewed or SSRN with an out-of-sample or post-publication test and explicit costs; (B) practitioner backtest with stated costs, or live tracking; (C) forum or anecdote.

---

## 1. Time-series momentum / trend following (MOP 2012; Hurst-Ooi-Pedersen; CTA index record 2015-2025; small-account implementability)

### Takeaway
Trend following has the longest out-of-sample record of any family here. The pre-1985 data gives out-of-sample evidence relative to MOP (2012), and AQR's simulation reaches back to 1880 with costs and 2/20 fees. The live record, net of fees and after publication, is uneven. 2022 was strong (+27.4%). Then the SG Trend Index lost 4.16% in 2023, gained 2.42% in 2024 and gained 2.39% in 2025, with a 20.4% drawdown from May 2024 to May 2025. One peer-reviewed critique (Huang et al. 2020) disputes that the predictability exists asset by asset. Tier: **A** for the academic evidence (simulated costs and fees, long out-of-sample span) and **B** for live index tracking. Implementability for a small account depends on contract granularity: Carver's numbers put meaningful diversification at around $100k.

### Cited Findings
**Moskowitz, Ooi & Pedersen (2012), "Time series momentum", JFE 104, 228–250** [F], [PDF](https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf)
- Abstract: "We document significant 'time series momentum' in equity index, currency, commodity, and bond futures for each of the 58 liquid instruments we consider. We find persistence in returns for one to 12 months that partially reverses over longer horizons."
- Abstract: "A diversified portfolio of time series momentum strategies across all asset classes delivers substantial abnormal returns with little exposure to standard asset pricing factors and performs best during extreme markets."
- Sample: "Sample period is January 1985 to December 2009" (figure and table captions). Some series begin earlier: "sample from January 1965 to December 2009".
- Alpha: "TSMOM delivers a large and significant alpha or intercept with respect to these factors of about 1.58% per month or 4.75% per quarter. The TSMOM strategy does not exhibit significant betas on the market, SMB, or HML but loads significantly positively on UMD." In Table 3 the monthly intercept of 1.58% carries t = 7.99.
- Out-of-sample on older data: "We can also compute the return of the time series momentum factor from 1966 to 1985, despite the limited number of instruments with available data. Over this earlier sample, time series momentum has a statistically significant return and an annualized Sharpe ratio of 1.1, providing strong out-of-sample evidence of time series momentum." Footnote 9 adds: "We thank the referee for asking for this out-of-sample study of old data."
- Crisis behaviour: "time series momentum profits are large in October, November, and December of 2008". The strategy "suffers sharp losses when the crisis ends in March, April, and May of 2009. The ending of a crisis constitutes a sharp trend reversal that generates losses on a trend following strategy such as TSMOM."
- Construction: positions are scaled by 40%/σ (ex-ante volatility). Fig. 2 reports the "annualized gross Sharpe ratio". In the text I extracted I found no headline net-of-transaction-cost figure, so costs are **not stated** for the main results.

**Hurst, Ooi & Pedersen, "A Century of Evidence on Trend-Following Investing", JPM Fall 2017 (vol. 44 no. 1)** [F], [PDF](https://fairmodel.econ.yale.edu/ec439/hurst.pdf)
- "We find that time-series momentum has been consistently profitable throughout the past 137 years." The data cover "67 markets across four major asset classes", and "our sample of simulated strategy returns runs from 1880 to the end of 2016."
- The portfolio is "scaled such that the combined portfolio has an annualized ex ante volatility target of 10% annualized."
- Costs and fees: "Finally, we subtract transaction costs and fees." On fees: "To simulate fees, we apply a 2% management fee and a 20% performance fee subject to a high-water mark." On cost caveats: "transaction costs are estimated with a significant amount of uncertainty, and the strategy may also be subject to other costs such as the costs of 'rolling' futures contracts, which are not accounted for in our simulations."
- Out-of-sample claim: "the first 10 decades of data is out-of-sample evidence relative to the literature, and the performance remains strong during this period."
- Per-market: "the strategy has delivered positive average returns in each market, with an average Sharpe ratio of approximately 0.4" (gross).
- Drawdowns: "the strategy has experienced significant drawdowns, losing up to 25%, over extended time periods."
- The 2017 version's Exhibit 1 table did not extract as text, so the 1880–2016 headline numbers are **not captured** here.

**Hurst, Ooi & Pedersen, 2014 AQR version (sample Jan 1880–Dec 2013), Exhibit 1, "Hypothetical Performance of Time Series Momentum… after simulated transaction costs both gross and net of hypothetical 2-and-20 fees"** [F], [PDF](https://oxfordstrat.com/coasdfASD32/uploads/2016/03/A-Century-of-Evidence-on-Trend-Following-Investing.pdf)
- Full sample, Jan 1880–Dec 2013: gross of fee 14.9%; net of 2/20 fee 11.2%; realized volatility 9.7%; Sharpe ratio net of fees 0.77; correlation to S&P 500 0.00; correlation to US 10-year bonds -0.04.
- Most recent sub-period, Jan 2000–Dec 2013: gross 11.3%; net 7.9%; volatility 9.6%; net Sharpe 0.62; correlation to S&P -0.30.
- Weakest decade, Jan 1910–Dec 1919: gross 8.3%, net 5.7%, net Sharpe 0.13. The table is labelled "Source: AQR… hypothetical performance."

**Critique: Huang, Li, Wang & Zhou (2020), "Time series momentum: Is it there?", JFE 135(3), 774–794** [S], [IDEAS](https://ideas.repec.org/a/eee/jfinec/v135y2020i3p774-794.html)
- Abstract wording as returned by search: "asset-by-asset time series regressions reveal little evidence of TSM, both in- and out-of-sample". The summary says the pooled regression's t-statistic falls short of bootstrap critical values, and that the strategy's profits roughly match a strategy built on historical sample means, which needs no predictability. The search summary gives the out-of-sample test window as 2000–2015 on the MOP dataset of 55 assets. I have not read this paper in full.

**Critique / defence: AQR, "You Can't Always Trend When You Want"** [S], [thread](https://threadreaderapp.com/thread/1215121710736793600.html)
- The thread quotes the paper: "While this could persist, there is little reason to believe that the fundamental dynamics of markets have changed permanently." The summary attributes weak post-2009 trend returns to unusually small market moves. The author list is inconsistent across sources and the abstract was not fetched.

**Live CTA index record, net of fees, post-publication**
- 2008 and 2022 [F], [Cambridge Associates, 19 Aug 2025, updated 26 Nov 2025](https://www.cambridgeassociates.com/insight/does-trend-followings-recent-struggle-signal-that-the-strategy-is-structurally-broken/): "The SG Trend Index returned 20.9% in 2008 and 27.4% in 2022." In those years the MSCI ACWI "posted losses of 42.2% and 18.4%, respectively."
- 2024–2025 drawdown, same source [F]: the index "experienced its second largest drawdown since inception in 2000, declining 20.4% from May 2024 through May 2025". Since 2000 it has had "16 drawdowns greater than 10%… occurring roughly every 18–24 months". The source's verdict on whether trend is structurally broken: "No". It calls the strategy "inherently cyclical". The causes it cites: "abrupt reversals, range-bound price action, and a lack of persistent trends", including the April 2025 tariff shock.
- 2023 [F], [TTU December 2023 report](https://www.toptradersunplugged.com/trend-following-performance-report-december-2023/): SG Trend Index "with a decrease of -0.32% in December, ultimately resulting in a YTD loss of -4.16%". BTOP50: "a relatively modest YTD loss of -1.70%."
- 2024 [F], [TTU December 2024 report](https://www.toptradersunplugged.com/trend-following-performance-report-december-2024/): SG Trend Index "lifting its final YTD performance to 2.42%". BTOP50: "closing the year with a YTD gain of 4.44%."
- 2025 [F], [TTU December 2025 report](https://www.toptradersunplugged.com/trend-following-performance-report-december-2025/): "The TTU TF Index ended the year at +1.78 percent, the SG Trend Index at +2.39 percent, and the BTOP50 at +2.81 percent." The fetch tool paraphrased the same report as giving the S&P 500 TR at +17.89% over the trailing 12 months. Index definition from the same report: "The SG Trend Index, which tracks the ten largest institutional trend-following CTAs, advanced 1.92 percent in December."
- [S] A search summary attributed to Virtus AlphaSimplex reports a 12-month loss through April 2025 of -18.7%, "the worst performance in the Index's 25-year history". A May 2025 SG CTA update reportedly showed -9.3% YTD after April ([SG](https://content.sgmarkets.com/CTA_UPDATE_KEEPING_UP_WITH_THE_TRENDFOLLOWERS_2025)). I verified neither.
- [S] A search snippet of an AQR whitepaper gives SG Trend Index period averages of "8.2% for 2000–2009, 1.8% for 2010–2019, and 17.9% for 2020–present" and a best calendar year of 26.1% ([AQR](https://www.aqr.com/-/media/AQR/Documents/Whitepapers/Trend-Following-Why-Now-A-Macro-Perspective.pdf?sc_lang=en)). The URL returned "page not found" when I fetched it, so these figures are unverified.

**Implementability for a small account**
- [F] Carver, "Diversification and small account size" ([qoppac, March 2016](https://qoppac.blogspot.com/2016/03/diversification-and-small-account-size.html)), at a 20% volatility target with equal weights:
  - At $5,000: "This is just enough to get to a single contract on both the KR3 and V2X futures".
  - At larger sizes: "With a capital of $2.2 million you could hold 37 instruments with a maximum position of at least 2 contracts in each."
  - On the Sharpe cost of coarse positions: "There is around a 20% penalty to Sharpe if you can only hold one contract; around 5% with a maximum position of two… This falls to zero if you can hold 3 or 4 contracts." A baseline SR of 0.36 "will become 0.29 or 0.34".
  - His advice for small accounts: "if you can only hold one or two contracts then you should use a threshold filter for your forecasts", and trade "with as wide a range of instruments as you can manage", at least until about "$100K or so."
- [S] His publisher says Carver "suggests a minimum account size of $100,000 for trading futures" ([Harriman House](https://harriman.house/?p=1768634)).
- [S] Micro futures are "scaled at 1/10th the size of standard E-mini futures" ([NinjaTrader, vendor](https://ninjatrader.com/Futures/Blogs/futures-trading-account-size)). The CME contract-spec page returned HTTP 503, so I could not confirm it from CME.
- French and EU retail [S]: the [European Parliament written question E-9-2021-004745](https://www.europarl.europa.eu/doceo/document/E-9-2021-004745_EN.html) notes that retail investors' "ability to invest in US ETFs, which have significantly lower fees than European UCITS funds, may become restricted". The mechanism is the PRIIPs KID requirement, which US ETFs do not meet ([myetfjourney](https://myetfjourney.com/blog/priips-kid-regulation)). US-listed managed-futures ETFs are therefore generally unavailable to a French retail account, which leaves futures, micro futures, or UCITS vehicles.

### Inferences
- The in-sample to out-of-sample record ranks this way: MOP Sharpe 1.1 out-of-sample on 1966–1985 data (gross), then the AQR simulation at net Sharpe 0.77 over 1880–2013 after 2/20 fees and simulated costs, then 0.62 net over 2000–2013. The live, investable 2023–2025 index record is roughly flat over three years: -4.16%, +2.42%, +2.39%. That fits a positive but modest and highly cyclical premium. It does not fit a dependable annual edge.
- For a bot without 2/20 fees, the gross-of-fee simulated numbers are the relevant ceiling. Even so, Carver's granularity penalty (about 20% of Sharpe at one contract) and the capital needed for 30+ markets mean a sub-$100k account trades a concentrated, noisier version than the one in the papers.
- The 2008 and 2022 crisis payoffs ("smile") are the real diversifying feature. The cost is long flat or losing stretches: the 2010s, and May 2024 to May 2025. A bot operator has to be able to sit through drawdowns of more than 10% roughly every 18–24 months, per Cambridge Associates.

### Gaps
- SG Trend Index calendar-year returns for 2015–2021: no fetched source gave them.
- Whether SG Trend Index returns are net of fees: not stated in the sources I read.
- The 1880–2016 Exhibit 1 headline numbers in the 2017 JPM version could not be extracted, since the table is an image.
- The CME micro contract specifications, and whether EU retail clients get PRIIPs KIDs for CME micros, were not verified. That belongs to the regulation researcher.
- MOP's net-of-cost Sharpe and turnover were not found in the extracted text.

---

## 2. Cross-sectional equity momentum and crashes; dual momentum; published TAA out-of-sample records

### Takeaway
Cross-sectional stock momentum is robust in peer-reviewed long samples (WML Sharpe 0.71 over 1927–2013), but it crashes in rebounds after bear markets. In 1932 and 2009 the loser decile rose 232% and 163% over a few months. The improvement from dynamic, volatility-managed momentum is documented (roughly doubling the Sharpe), but it is in-sample to that paper. Published TAA systems decayed out of sample: Faber's GTAA went from an 11.7% CAGR in-sample to 6.05% out of sample over 2006–2025. I found no verifiable post-publication record for Antonacci's GEM. Tier: **A** for cross-sectional momentum's existence and crash risk. **B** for TAA out-of-sample records (Concretum replication; Allocate Smartly tracking, which is not split out-of-sample). **B/C** for dual momentum.

### Cited Findings
**Daniel & Moskowitz, "Momentum Crashes" (NBER w20439; JFE 2016)** [F], [NBER PDF](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf), [abstract page](https://www.nber.org/papers/w20439)
- Abstract: "momentum strategies can experience infrequent and persistent strings of negative returns". The crashes "occur in panic states, following market declines and when market volatility is high, and are contemporaneous with market rebounds".
- Abstract on the fix: a dynamic strategy based on forecasts of momentum's "mean and variance approximately doubles the alpha and Sharpe Ratio of a static momentum strategy".
- Sample and Sharpe: Table 1 covers "1927:01-2013:03". "The Sharpe ratio of the WML portfolio is 0.71, and that of the market is 0.40."
- The 1932 crash: "In our 1927 to 2013 U.S. equity sample, the two worst months for a momentum strategy that buys the top decile of past 12-month winners and shorts the bottom decile of losers are consecutive: July and August of 1932. Over this short period, the past-loser decile portfolio returned 232%, while the past-winner decile portfolio had a gain of only 32%."
- The 2009 crash: "over the three-month period from March to May of 2009, the past-loser decile rose by 163%, while the decile portfolio of past winners gained only 8%."
- Where the losses come from: "the crash performance is mostly attributable to the short side or the performance of losers."
- Timing: "Fourteen of the 15 worst momentum returns occur when the lagged two-year market" … (the sentence continues with the bear-market condition; I extracted only this fragment).

**Faber GTAA (published 2006/2007), 20-year out-of-sample replication** [F], [Concretum Group](https://concretumgroup.substack.com/p/global-tactical-asset-allocation)
- Out-of-sample, 2006 to March 2025: "Sharpe ratio of 0.68", "CAGR of 6.05%", "maximum drawdown of 11.7%".
- In-sample, 1972–2005: the original backtest "produced a Sharpe ratio of 0.81, a CAGR of 11.7%, and a maximum drawdown of 9.5%."
- Volatility, the buy-and-hold comparison and the cost assumptions were not stated in the excerpt.

**Allocate Smartly (live tracking of published TAA)**
- [F] [Allocate Smartly, "Why TAA Is Performing Well Now: Outperformance Attribution" (early 2026)](https://allocatesmartly.com/why-taa-is-performing-well-now-outperformance-attribution/): "We track 100+ published Tactical Asset Allocation (TAA) strategies." "In total, 57% of outperformance has been from generally held assets, and 43% from timing."
  - The method uses "the average asset allocation of all TAA strategies over their entire history". That means full history, not a post-publication-only split.
  - Composite CAGR, drawdown, Sharpe and cost assumptions were not stated in the fetched text.
- [S] In Allocate Smartly's 2017 guest post on Alpha Architect: "TAA has underperformed in the recent past relative to common benchmarks like the US 60/40 portfolio", and "60/40's outperformance since the GFC arguably benefits from 20/20 hindsight" ([Alpha Architect](https://alphaarchitect.com/tactical-asset-allocation-us-6040-benchmark/)). The page returned 403 to the fetch tool.

**Dual momentum / GEM (Antonacci)**
- [S] ReSolve, "Global Equity Momentum: A Craftsman's Perspective" (2019) tested 1950–2018, with out-of-sample windows of 1950–1973 and 2012–2018. Per the search summary, the original specification "regressed to the median out of sample", and specification choice "introduces an uncompensated source of risk" ([Advisor Perspectives](https://www.advisorperspectives.com/articles/2019/05/06/global-equity-momentum-a-craftsmans-perspective)). The page returned 403 to the fetch tool.
- [F] Michael Harris, "Dual Momentum Post-Publication Performance" (10 March 2023) is paywalled. Its figures are **not stated** in the accessible text ([Price Action Lab](https://priceactionlab.com/Blog/?p=68274)). A search-engine summary claimed a post-2018 annualized return of about a third of the pre-publication level; that is unverified.

### Inferences
- Momentum's crash risk sits on the short side, in rebounds after bear markets. A long-only small account avoids the loser-short leg that drives the 1932 and 2009 crashes, but then it is not running the paper's WML portfolio. Long-only results should not be taken from WML statistics. This is an inference; no source above tests long-only.
- Faber's GTAA shows the typical shape of a published TAA after publication: about half the CAGR (6.05% against 11.7%), a lower Sharpe (0.68 against 0.81), and a slightly deeper drawdown. Allocate Smartly's split (43% timing, 57% asset mix) suggests that much of TAA's edge over 60/40 is diversification rather than timing skill.
- For a French retail investor, the TAA ETFs in these papers (SPY, EFA, IEF, GLD and similar) are US-domiciled, so a bot would have to map each to a UCITS equivalent. Tracking differences and listing hours then change the backtest. This is an inference, and the regulation itself belongs to the other researcher.

### Gaps
- No verifiable GEM performance figures after 2013, from Antonacci or independent trackers.
- No Allocate Smartly aggregate split into before and after each strategy's publication date was found.
- Cost and turnover figures for Daniel & Moskowitz's dynamic strategy were not extracted.

---

## 3. Short-term mean reversion on equity indices and ETFs (Connors RSI(2), IBS, "N down days")

### Takeaway
No peer-reviewed post-publication test with explicit costs turned up for RSI(2), IBS or N-down-days on SPY or QQQ. The record is practitioner and forum material only. What exists points to decay. One vendor test of RSI(2) on the S&P 500 over October 2016 to October 2026, with 0.02% per side commission, produced a +1.7% CAGR against +13.5% for buy and hold. IBS on SPY returned about 13% CAGR before costs over 1999–2016, but returns "turning negative in 2015 and 2016". Tier: **B/C**.

### Cited Findings
**RSI(2)**
- [F] [Backtrex, "Does the RSI(2) strategy work on the S&P 500?"](https://backtrex.com/en/backtests/connors-rsi-2-sp-500)
  - Instrument and period: "SPX500/USD, Daily chart, Oct 3, 2016 to Oct 1, 2026."
  - Rules: long when "RSI(2) below 5 and the close above the 200-day simple moving average (SMA)"; exit when "the close is back above the 5-day SMA, or below the 200-day SMA". Mirror-image shorts below the 200-day SMA.
  - Results: CAGR +1.7% a year against +13.5% for buy and hold; max drawdown -21.5% against -35%; 73 trades; win rate 71.23%.
  - Costs: commission "0.02% per side". Slippage and spread not stated.
  - Verdict: "Only just", and the edge is "far too small to compete with simply owning the index." The test uses a CFD, which is a vendor setting rather than SPY.
- [F] Quantified Strategies, "SPY trading strategy using RSI" (31 Jul 2024) is paywalled. Rules, trade count, CAGR, drawdown and costs are **not stated** in the accessible text ([substack](https://quantifiedstrategies.substack.com/p/spy-trading-strategy-using-rsi)).
- [S] Two pulse.bot summaries attributed to Quantified Strategies (AI-generated) give a 9% CAGR at about 28% time invested since 1993 with a 34% max drawdown, and, for a pullback variant, 184 trades, 0.7% average, 78% win rate and 3.9% CAGR ([pulse.bot](https://www.pulse.bot/stock-trading/blogs/rsi-2-strategy-explained-larry-connors-2-period-rsi-trading-rules-c24def76-2466-424f-84fa-6cdac590eab2)). Unverified, and they conflict with each other.
- [S] Forum and blog claims that RSI(2) "has survived more than 17 years out of sample" ([Alpha Algo Trading Research](https://algotr.substack.com/p/this-simple-mean-reversion-strategy)) come without verifiable figures. Tier C.

**IBS (internal bar strength)**
- [F] [Jonathan Kinlay, "The Internal Bar Strength Indicator" (2 July 2019)](https://jonathankinlay.com/?p=2199)
  - Definition: "IBS = (Close – Low) / (High – Low)". The rule "buys at the close when IBS is below 0.2" and "sells at the close when IBS exceeds 0.8".
  - Sample: "SPDR S&P 500 ETF Trust (SPY) and iShares MSCI Singapore ETF (EWS)" over "the period from 1999 to 2016".
  - Results: CAGR "of the order of 13% for SPY" and "as high as 40% for EWS", "ignoring transaction costs".
  - Decay: returns "have diminished in recent years, turning negative in 2015 and 2016 YTD".
  - Costs used for his QQQ variant: "commissions of $0.005 per share and slippage of a further $0.02 per share."
- [F] Pandey & Joshi (2023, arXiv, not peer-reviewed): "analyze historical price data for a bucket of country ETFs over a period of 10 years". They conclude "IBS can be a useful technical indicator for predicting short-term price movements" ([arXiv 2306.12434](https://arxiv.org/abs/2306.12434v1)). Returns, Sharpe and costs are not stated in the abstract. [S] The search summary adds that "the 1-day IBS indicator does not seem to have an effect beyond horizons of one day".
- [S] The original paper is Pagonidis, "The IBS Effect: Mean Reversion in Equity ETFs" (NAAIM, about 2013–2014). Per a later study its thresholds were IBS < 0.2 and > 0.8. I did not retrieve the paper ([NAAIM listing](https://naaim.org/wpyear/2014/page/2)).
- [S] On QuantConnect, a QQQ IBS strategy showed about 15% CAGR and 28% drawdown in Amibroker but about 5.5% CAGR and 33% drawdown when rebuilt in QuantConnect, which suggests execution assumptions dominate ([QuantConnect forum](https://www.quantconnect.com/forum/discussion/12403)). Tier C.

**N down days**
- [S] Quantified Strategies' "3 days down" rules: buy SPY at the close of the third consecutive down day and exit at the next open, backtested from 1993. Results were not visible ([substack](https://quantifiedstrategies.substack.com/p/3-days-down-overnight-trading-strategy-1db)).
- [S] An AI summary of a Quantified Strategies post claims a "75% win rate with 0.5% avg gain… CAGR of 3.9% with only 10% market exposure" ([pulse.bot](https://www.pulse.bot/stock-trading/news/multiple-days-up-and-multiple-days-down-trading-strategy-ab17ed5a-8959-4d92-b78f-b8f47bdb7985/)). Unverified, tier C.

### Inferences
- These strategies depend on getting filled at or near the close: buy at the close, exit at the close or next open. The cost line items are commission, spread and the market-on-close fill. Kinlay's SPY numbers exclude all three. The only test that includes costs (Backtrex, 0.02% per side) returned roughly 1.7% a year over the last ten years.
- High win rates (71–78%) with low exposure combine into small CAGRs. Even the favourable figures quoted (3.9% to 9% CAGR) trail buy and hold on SPY. Their selling point is lower drawdown and less time in the market, not excess return.
- For a French retail account, SPY and QQQ are US-domiciled ETFs and are generally blocked under PRIIPs (see section 1). Running these rules on UCITS S&P 500 ETFs listed in Europe changes the "close" (European closing auction against the US close) and the intraday high and low used by IBS. Micro E-mini futures avoid the ETF problem but have a different session and settlement. Any published SPY result would need re-testing on the instrument actually traded. This is an inference.

### Gaps
- No peer-reviewed, cost-inclusive post-publication study of RSI(2), IBS or N-down-days on SPY or QQQ for 2015–2025 was found.
- Alvarez Quant Trading's own post-publication numbers were not found.
- Quantpedia's IBS and mean-reversion pages could not be fetched (HTTP 500 on its turn-of-the-month page).

---

## 4. Calendar effects (turn-of-the-month, pre-holiday): post-publication behaviour

### Takeaway
The turn-of-the-month effect is well documented through 2005 (McConnell & Xu, FAJ 2008: 31 of 35 countries). Evidence after publication conflicts: one Fed working paper finds the last-day effect in S&P 500 futures disappeared after 1990, and post-2005 support is mostly practitioner material. The pre-holiday premium in large US stocks became insignificant after 1990 and now survives only in small firms (Ko & Yang, CFR). Tier: **A** for the history and the pre-holiday decay; **C** for TOM after 2005.

### Cited Findings
- [F] [McConnell & Xu, "Equity Returns at the Turn of the Month", FAJ 64(2), 2008](https://econpapers.repec.org/RePEc:taf:ufajxx:v:64:y:2008:i:2:p:49-64)
  - Sample: "Using CRSP daily returns for the 80-year period of 1926–2005".
  - The four-day turn of the month averaged "0.15 percent (0.22 percent)" daily, value-weighted (equal-weighted), against "–0.001 percent (0.04 percent)" over the other 16 trading days.
  - Breadth: "it occurs in 31 of the 35 countries that we examined". Conclusion: "the turn-of-the-month pattern in equity returns remains a puzzle in search of an answer."
- [F] [Maberly & Waggoner, Atlanta Fed WP 2000-11](https://econpapers.repec.org/RePEc:fip:fedawp:2000-11): defines TOTM as "unusually high returns on the last trading day of the month" in "the S&P 500 futures contract". The effects "disappear after 1990", and the result "carries over to the S&P 500 spot market". The exact sample dates are not stated in the abstract.
- Conflict: McConnell & Xu use a four-day window and CRSP data through 2005 and find the effect persisting. Maberly & Waggoner use the last day only, in futures, and find it gone after 1990. The two definitions and samples differ.
- [S] A blog claim says TOM "has held up well out of sample" ([Hull Tactical](https://www.hulltactical.com/?p=1317)), and a study of SPY 2001–2011 found the effect "still exists… but the dates of its occurrence have moved earlier". Tier C/B; neither was fetched.
- [F] [Ko & Yang, "The Pre-Holiday Premium of Ariel (1990) Has Largely Become A Small-Firm Effect Out of Sample", Critical Finance Review](https://cfr.ivo-welch.org/published/papers/ko2021pre.pdf)
  - Abstract: "Arial (1990) showed that the average returns of U.S. market indices on trading days prior to holidays are 9 to 14 times higher… Extending the sample to 1983-2019, we find that the pre-holiday effect now exists only among small firms. For large firms, the differences in returns between pre-holidays and non-pre-holidays have become insignificant, and especially after 1990."
  - In the body: "completely vanished after 1990 without controlling for other day effects". [S] The search summary gives the context as the pre-holiday premium of the CRSP VW index. The authors tie the small-firm survival to "the argument of limits of arbitrage."

### Inferences
- The tradable large-cap pre-holiday premium appears gone since about 1990. What is left sits in small firms, where costs are higher. That is the same structural trap the reader's small-cap intraday bot hit.
- A TOM rule on index futures or a UCITS S&P 500 ETF is cheap to run: about 4 days a month, roughly 12 round trips a year. But the post-publication evidence conflicts, so it should be treated as a hypothesis to test rather than an established edge.

### Gaps
- No rigorous peer-reviewed post-2005 out-of-sample test of TOM on SPY or S&P futures with costs was found.
- Quantpedia's TOM page returned HTTP 500.
- The publication year and volume of Ko & Yang are not confirmed. The PDF filename says 2021; a search listing suggested CFR 2024.

---

## 5. Post-earnings-announcement drift (PEAD): has it disappeared, and where are the remaining pockets?

### Takeaway
Martineau (CFR 2022) finds PEAD "non-existent since 2006" in large stocks and gone recently in microcaps, using data through 2019. Two 2025 papers argue drift survives, but a replication finds the evidence concentrated in microcaps: t = 2.18 with all stocks against 1.43 excluding microcaps. Text-based surprise measures (PEAD.txt) produce a larger drift than classic SUE, but I found no evidence on whether it persists after publication. Tier: **A**, with the evidence contested.

### Cited Findings
- [F] [Martineau, "Rest in Peace Post-Earnings Announcement Drift", Critical Finance Review (2022)](https://cfr.ivo-welch.org/published/papers/martineau2021rest.pdf)
  - Abstract: "In modern financial markets, stock prices fully reflect earnings surprises on the announcement date, leading to the disappearance of post-earnings announcement drifts (PEAD). For large stocks, PEAD have been non-existent since 2006 but has only disappeared recently for microcap stocks."
  - Detail: "since 2006, I show, analyst earnings surprises fail to positively predict post-announcement returns over 60 days for all-but-microcap stocks, and since 2016 for microcap stocks. In addition, PEAD does not now hide in more 'subtle' ways, e.g., PEAD is not present for the smallest 'all-but-microcap' stocks and at shorter horizon."
  - Sample: "The sample periods for the Compustat sample and the I/B/E/S sample begin in 1973 and 1984, respectively, and both end on December 31, 2019." The counts are "593,654 for the Compustat sample… and 312,462 for the I/B/E/S sample."
  - Microcaps are defined as stocks below the NYSE 20th percentile of market cap. Announcement-date responsiveness: "Prices of all-but-microcap and microcap stocks are respectively six and three times more responsive to earnings surprises on announcement date in the latter part of the sample (2016-2019) than in the early part of the sample (1984-1990)."
  - [S] Journal details: CFR vol. 11, issues 3–4, pp. 613–646 ([IDEAS](https://ideas.repec.org/a/now/jnlcfr/104.00000122.html)).
- [F] [UCLA Anderson Review, "Is post-earnings announcement drift a thing again?" (2025)](https://anderson-review.ucla.edu/is-post-earnings-announcement-drift-a-thing-again/)
  - Dickerson, Julliard & Mueller, "The co-pricing factor zoo" (JFE, in press), concludes "earnings drift remains a major market factor". Its earnings factor is "computed in a nonstandard way".
  - Hirshleifer, Peng & Wang, RFS 38(3) 2025, finds "drift exists in the market with extremely high statistical confidence", with t around 14.
  - Neither paper filtered microcaps. Subrahmanyam's replication: t = 2.18 with all stocks, 1.43 excluding microcaps. He says the social-connection result "appears to just be a market cap effect." The article reports no return magnitudes and no transaction-cost analysis.
- [F] [Meursault, Liang, Routledge & Scanlon, "PEAD.txt: Post-Earnings-Announcement Drift Using Text" (JFQA 58(6), 2023; Philadelphia Fed WP 21-07)](https://ideas.repec.org/p/fip/fedpwp/89938.html): "SUE.txt generates a text-based post-earnings announcement drift (PEAD.txt) larger than the classic PEAD", and the measure "can be used to create a profitable trading strategy". The sample period and recent decay are not stated in the abstract.

### Inferences
- For a small bot, classic SUE-based PEAD on liquid stocks looks dead by Martineau's 2006–2019 evidence. The contested remainder is concentrated in microcaps, where the reader's own small-cap work found costs decisive.
- PEAD.txt is a possible remaining pocket, but it needs earnings-call transcripts and an NLP pipeline, and I found no post-publication record for it.

### Gaps
- Return magnitudes, Sharpe ratios and cost analysis for the 2025 pro-PEAD papers were not available in the source read.
- PEAD.txt's sample period, post-2019 performance and cost treatment were not obtained; the Cambridge PDF download failed with a 502.

---

## 6. Pairs trading / statistical arbitrage (Gatev-Goetzmann-Rouwenhorst 2006; Do & Faff 2010, 2012)

### Takeaway
The 2006 RFS distance-method results (up to 11% annualized excess over 1962–2002) have decayed. Do & Faff document a "continuing downward trend in profitability". After commissions, market impact and short-selling fees, the refined version earns about 30 bp a month. Tier: **A**, with explicit costs in Do & Faff 2012. The current edge is modest, and it requires shorting individual stocks.

### Cited Findings
- [F] [Gatev, Goetzmann & Rouwenhorst, RFS 19(3) 797–827 (2006)](https://econpapers.repec.org/RePEc:oup:rfinst:v:19:y:2006:i:3:p:797-827)
  - Sample: "daily data over 1962--2002". The trading rule "yields average annualized excess returns of up to 11% for self-financing portfolios of pairs."
  - Costs: "The profits typically exceed conservative transaction-cost estimates." On reversal: "Bootstrap results suggest that the 'pairs' effect differs from previously documented reversal profits."
- [F] The earlier NBER WP 7032 version uses 1962 through 1997 and finds "average annualized excess returns of up to 12 percent for a number of self-financing portfolios of top pairs". It states: "Our historical trading profits exceed a conservative estimate of transaction costs through most of the period", and "Part of these profits may be due to market microstructure effects" ([NBER](https://www.nber.org/papers/w7032)).
- [F] [Do & Faff, "Does Simple Pairs Trading Still Work?", FAJ 66(4) 2010](https://research.bond.edu.au/en/publications/does-simple-pairs-trading-still-work/) confirm "the continuing downward trend in profitability of pairs trading". The strategy "performs strongly during periods of prolonged turbulence", and "alternative algorithms combined with other measures enhance trading profits considerably, by 22 bps a month for bank stocks."
- [S] Search summaries of the same paper say the 2003–2009 return was 0.24 percent and that worsening arbitrage risks explain "up to 70 percent" of the decline. Neither was verified against the paper.
- [S] [Do & Faff, "Are pairs trading profits robust to trading costs?", J. Financial Research 35(2) 2012](https://strathprints.strath.ac.uk/41722/), abstract text as returned by search: "After controlling for commissions, market impact, and short selling fees, pairs trading remains profitable, albeit at much more modest levels. Specifically, we document a risk-adjusted return of about 30 basis points per month among portfolios of well-matched pairs that are formed within refined industry groups." The sample is 1963–2009.
- [S] A CXO summary cites one-way frictions of about 0.81% for 1963–1988 and 0.33% for 1989–2009, and says the baseline strategy is unprofitable after frictions ([CXO](https://www.cxoadvisory.com/technical-trading/pairs-trading-net-profitability/)). Unverified.

### Inferences
- About 30 bp a month risk-adjusted, before the costs of borrowing hard-to-borrow names and before any further post-2009 decay, is a thin edge for a retail bot. Equity pairs also need stock shorting and borrow availability that a small French retail account may not have.

### Gaps
- No evidence on pairs-trading profitability after 2009 was found in this pass.
- No ETF- or futures-pair evidence was found.

---

## 7. Simple factor tilts (value, quality, low volatility) and their recent records

### Takeaway
Value went through a 55% drawdown against growth from 2007 to mid-2020. Its defenders attribute the whole drawdown to valuation-spread changes rather than a dead premium, but the drawdown alone shows how hard the strategy is to hold. Low-volatility is described as "highly persistent", with little sign of being arbitraged away and low turnover. Its stated risk is crowding in index products. I did not obtain recent quality-factor or factor-index return figures. Tier: **A** for the literature. Recent returns are a gap.

### Cited Findings
- [F] [Arnott, Harvey, Kalesnik & Linnainmaa, "Reports of Value's Death May Be Greatly Exaggerated", FAJ 77(1) 2021](https://econpapers.repec.org/RePEc:taf:ufajxx:v:77:y:2021:i:1:p:44-67)
  - Value "has underperformed growth investing since 2007, producing a drawdown of 55% as of mid-2020."
  - On HML: "The HML book-value-to-price definition fails to capture increasingly important intangible assets." On the cause: "changes in the valuation spread between the growth and value portfolios explain the entire drawdown, with room to spare." The authors disclose that Research Affiliates has a commercial interest in the subject.
- [F] [Blitz, van Vliet & Baltussen, "The Volatility Effect Revisited", JPM 46(2) 2020](https://repub.eur.nl/pub/131601)
  - "High-risk stocks do not have higher returns than low-risk stocks in all major stock markets." The effect is "highly persistent over time and across markets" and "cannot be explained by other factors such as value, profitability, or exposure to interest rate changes."
  - Implementation: "Low-risk investing requires little turnover". Risks: "Low-risk indexes are suboptimal and vulnerable to overcrowding". On arbitrage: "there is little evidence that the low-risk effect is being arbitraged away."
- [S] Blitz & van Vliet (2007) reported "an annual alpha spread of global low versus high volatility decile portfolios amounts to 12% over the 1986-2006 period" (search snippet; not fetched).
- [F] Hou, Xue & Zhang (2020) on replicated anomalies in general: "Even for replicated anomalies, their economic magnitudes are much smaller than originally reported" ([EconPapers](https://econpapers.repec.org/RePEc:oup:rfinst:v:33:y:2020:i:5:p:2019-2133.)).

### Inferences
- Low volatility has the best implementation profile of these tilts for a small account: low turnover, long-only. That fits a monthly-rebalanced bot using UCITS minimum-volatility ETFs or a self-built low-volatility basket. Value's 13-year drawdown shows a single-factor tilt can underperform for longer than most operators can tolerate.
- None of these tilts is a "bot" edge in the intraday sense. They are slow premia that need years to show up and are exposed to long stretches of underperformance.

### Gaps
- Recent returns (2015–2026) for quality, value and low-volatility indices, for example the S&P 500 or MSCI factor indices, were not obtained. The S&P DJI factor dashboard returned 403 to the fetch tool and HTML to curl.
- No source for quality-minus-junk post-publication performance was read.

---

## 8. Anomaly decay and data mining (McLean & Pontiff 2016; Harvey, Liu & Zhu 2016; Hou, Xue & Zhang 2020; Jensen, Kelly & Pedersen 2023)

### Takeaway
The headline numbers: published predictors earn 26% less out of sample and 58% less after publication (McLean & Pontiff). A new factor needs t > 3.0 (Harvey, Liu & Zhu). 65% of 452 anomalies fail at |t| = 1.96 and 82% at 2.78 (Hou, Xue & Zhang). Jensen, Kelly & Pedersen counter that most factors replicate: about 85% in their NBER-version Bayesian or CAPM-alpha tests. They also read post-publication attenuation as expected under Bayesian shrinkage, not as failure, and note that the US is the only country with a reliable post-publication decline. Practical reading: halve a published backtest before trusting it, and expect the most decay where in-sample returns were highest.

### Cited Findings
- [F] [McLean & Pontiff, "Does Academic Research Destroy Stock Return Predictability?", J. Finance 2016](https://www.gwern.net/doc/economics/2016-mclean.pdf)
  - Abstract: "We study the out-of-sample and post-publication return predictability of 97 variables shown to predict cross-sectional stock returns. Portfolio returns are 26% lower out-of-sample and 58% lower post-publication. The out-of-sample decline is an upper bound estimate of data mining effects. We estimate a 32% (58%–26%) lower return from publication-informed trading."
  - On which predictors decay most: "Post-publication declines are greater for predictors with higher in-sample returns, and returns are higher for portfolios concentrated in stocks with high idiosyncratic risk and low liquidity. Predictor portfolios exhibit post-publication increases in correlations with other published-predictor portfolios."
- [F] [Harvey, Liu & Zhu, "...and the Cross-Section of Expected Returns", RFS 29(1) 5–68, 2016 (NBER w20592)](https://www.nber.org/papers/w20592): a new factor "needs to clear a much higher hurdle, with a t-ratio greater than 3.0", and "most claimed research findings in financial economics are likely false." The method gives "a time series of historical significance cutoffs from the first empirical tests in 1967".
- [F] [Hou, Xue & Zhang, "Replicating Anomalies", RFS 33(5) 2019–2133, 2020](https://econpapers.repec.org/RePEc:oup:rfinst:v:33:y:2020:i:5:p:2019-2133.)
  - With microcaps mitigated via NYSE breakpoints and value-weighted returns: "65% of the 452 anomalies in our extensive data library, including 96% of the trading frictions category, cannot clear the single test hurdle of the absolute t-value of 1.96."
  - "Imposing the higher multiple test hurdle of 2.78 at the 5% significance level raises the failure rate to 82%."
  - "Even for replicated anomalies, their economic magnitudes are much smaller than originally reported."
- [F] The 2017 working-paper version (NBER w23394) gives different figures: "The anomalies literature is infested with widespread p-hacking", and "286 anomalies (64%) including 95 out of 102 liquidity variables (93%) are insignificant at the conventional 5% level." It adds: "Imposing the cutoff t-value of three raises the number of insignificance to 380 (85%)" ([NBER](https://www.nber.org/papers/w23394)). Cite the RFS version's numbers.
- [F] [Jensen, Kelly & Pedersen, "Is There a Replication Crisis in Finance?" (NBER WP 28432; J. Finance 2023)](https://www.nber.org/system/files/working_papers/w28432/w28432.pdf), numbers from the NBER working-paper text:
  - Baseline: "we find a baseline replication rate of 56.9%, a difference of 21.9 percentage points" against Hou et al.'s comparable 35%. After an adjustment, "the replication rate rises to 64.7%".
  - CAPM alpha: "the replication rate rises to 84.9% based on tests of factors' CAPM alpha". Bayesian multiple-testing: "our estimated replication rate rises to 84.0%". Global sample: "the final replication rate rises slightly to 84.9%". With straight rather than capped value weights: "Our ultimate replication rate in this case is 77.3%".
  - Data: "global data set of 153 factors across 93 countries". The factors cluster "into 13 themes".
  - Post-publication: "a positive but attenuated post-publication alpha is the expected outcome based on Bayesian learning, rather than a sign of non-reproducibility", and "factors with higher in-sample alpha generally have higher out-of-sample alpha".
  - The paper quotes Jacobs & Müller (2020): "the United States is the only country with a reliable post-publication decline in long-short returns."
  - Conflict: [S] search summaries of the published JF version cite a 55.6% baseline and about 82% Bayesian or global rates ([Alpha Architect](https://alphaarchitect.com/is-there-a-replication-crisis-in-finance/)). Those differ from the NBER-version figures above. I did not read the published version.

### Inferences
- **Cross-family evidence summary.** This table is my synthesis of the sections above, not a source claim.

| family | tier | out-of-sample / post-publication record | small-account fit |
|---|---|---|---|
| Trend following (futures) | A (simulated costs and fees, pre-1985 out-of-sample); B (live index, net) | Out-of-sample Sharpe 1.1 on 1966–1985 (gross); 0.62 net over 2000–2013 (AQR simulation); live SG Trend -4.16% / +2.42% / +2.39% for 2023–2025; +27.4% in 2022 | Needs about $100k for diversification (Carver); micros help |
| Cross-sectional momentum | A | Robust long sample; crash risk on the short side | Poor: many names, shorting |
| Published TAA (GTAA, GEM) | B / C | GTAA CAGR 11.7% in-sample, 6.05% out of sample 2006–2025 | Good: monthly, a few ETFs (UCITS mapping needed) |
| RSI(2) / IBS / N-down | B / C | Weak since about 2015 (IBS negative 2015–16; RSI(2) +1.7% CAGR 2016–2026 with costs) | Easy to run; edge doubtful |
| Turn of month | A history / C after 2005 | Conflicting (gone after 1990 in futures, last-day definition) | Cheap, low turnover |
| Pre-holiday | A | Gone in large caps after 1990 | Not useful in liquid names |
| PEAD | A, contested | Gone in large caps since 2006; residual in microcaps | Same cost trap as small-cap intraday |
| Pairs (distance) | A | Decayed; about 30 bp a month after costs to 2009 | Needs stock shorting |
| Low volatility / value | A | Low-vol persistent; value -55% from 2007 to 2020 | Low turnover; long-only |

- McLean & Pontiff's finding that decay is largest where in-sample returns were highest, together with Hou, Xue & Zhang's 96% failure rate for trading-frictions anomalies, means that strategies whose backtests depend on illiquid names or very high in-sample returns should be haircut hardest. That fits the PEAD, pre-holiday and pairs records above.

### Gaps
- The exact replication rates in the published J. Finance 2023 version of Jensen, Kelly & Pedersen were not verified. The figures above are from NBER WP 28432.
- No source here quantifies anomaly decay specifically for time-series or asset-class strategies such as trend or TOM, as opposed to cross-sectional stock anomalies.
