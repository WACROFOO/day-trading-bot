# Cross-Asset Trend Following and Tactical Asset Allocation (TAA): Out-of-Sample and Post-Publication Evidence (as of Nov 2026)

Research date: 2026-11-10. Investor context: France-based retail, EUR base, Interactive Brokers, UCITS ETFs + single stocks only (PRIIPs blocks US-domiciled ETFs), long-only, no leverage, daily-or-slower decisions, EUR 10k–200k.

How to read this file:
- **IS** = in-sample (the original backtest the author published). **OOS / post-pub** = data after the publication date, or live tracking.
- **Source-quality flags:** [VENDOR] = manager or product provider with a commercial interest (AQR, Man, iMGP/DBi, Cambria, Fulcrum, AlphaSimplex/Virtus). [TRACKER] = Allocate Smartly, a paid subscription service that sells TAA signals, so it has an interest in TAA looking good, though it often publishes self-critical analysis. [INDEPENDENT-BLOG] = an individual or small site of unknown rigor. [AI-WRITTEN] = the site says it uses AI-written content. [SNIPPET] = the figure comes from a search-result summary; the underlying page was not opened, so treat it as lower confidence.
- **Gross/net:** stated wherever the source says. Index returns (SG Trend, SG CTA, BTOP50) are **net of manager fees** because they are built from fund returns. Academic TSMOM backtests are usually **gross** unless noted otherwise.

---

## 1. Time-series momentum / managed futures: academic evidence, 2015–2026 performance, and decay

### Takeaway
The academic case (MOP 2012; Hurst-Ooi-Pedersen, data back to 1880) is strong in-sample: a net-of-2/20 Sharpe of about 0.77 over 1880–2013, with positive returns in 8 of the 10 worst 60/40 drawdowns. The live record since publication is much weaker and very regime-dependent. The SG Trend Index made roughly 1.8%/yr in the 2010s [SNIPPET], then +27.3% in 2022, followed by −4.2% (2023), +2.4% (2024) and +2.4% (2025). The 2025 calendar year hid a record −18.6% rolling 12-month loss to April 2025. 2026 has been strong: +15.8% YTD to end-September. Returns have been lower since 2000 (SG Trend CAGR about 5–6%, net of fees) than in the century backtest (about 11% net), but they have not gone to zero. Managers argue that the weak periods were cyclical (few large market moves), not structural decay. The academic critique (Huang et al. 2020) questions whether the effect is statistically robust at all.

### Cited Findings

**Original academic evidence (in-sample)**
- Moskowitz, Ooi & Pedersen, "Time Series Momentum", *Journal of Financial Economics* 2012 (vol. 104, issue 2, pp. 228–250): 58 liquid instruments (equity index, currency, commodity and bond futures) over 25+ years (roughly 1985–2009). Returns persist for 1–12 months and partially reverse over longer horizons. The canonical rule: long if the trailing 12-month excess return is positive, short if negative, monthly rebalance, volatility-scaled positions — [RePEc](https://econpapers.repec.org/RePEc:eee:jfinec:v:104:y:2012:i:2:p:228-250); [SSRN](https://papers.ssrn.com/abstract=2089463); [Quantpedia summary](https://quantpedia.com/strategies/time-series-momentum-effect/)
- Reported Sharpe ratios for diversified 12-month TSMOM differ by source: Quantpedia lists 1.31 Sharpe at about 15.7% volatility (citing the paper's Table 3), and a later AQR document ("Trends Everywhere", data extended to about 2017) reports a **gross** Sharpe of 1.17 for traditional assets. These are gross, in-sample figures — [Quantpedia](https://quantpedia.com/strategies/time-series-momentum-effect/); [AQR Trends Everywhere via Scribd](https://www.scribd.com/document/568229115/AQR-Trends-Everywhere) [SNIPPET]
- Hurst, Ooi & Pedersen, "A Century of Evidence on Trend-Following Investing" [VENDOR: AQR]. The whitepaper was first published Fall 2012 and the version read here runs Jan 1880 to Dec 2013. The final version appeared in *Journal of Portfolio Management* Fall 2017 (AQR page dated 31 Oct 2017). Method: equal-weighted 1-, 3- and 12-month TSMOM signals across up to 67 markets (29 commodities, 11 equity indices, 15 bond markets, plus currencies), each position volatility-scaled, with the portfolio targeting 10% ex-ante volatility. Results are after simulated transaction costs, with a hypothetical 2% management / 20% performance fee and a high-water mark — [AQR PDF (2014 version)](https://oxfordstrat.com/coasdfASD32/uploads/2016/03/A-Century-of-Evidence-on-Trend-Following-Investing.pdf); [AQR article page](https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing)
  - **1880–2013:** 14.9% annualized gross of fees and **11.2% net of 2/20**, 9.7% volatility, **Sharpe 0.77 net**, correlation 0.00 to the S&P 500 and −0.04 to US 10-year bonds — [AQR PDF](https://oxfordstrat.com/coasdfASD32/uploads/2016/03/A-Century-of-Evidence-on-Trend-Following-Investing.pdf)
  - **By decade (net Sharpe):** 1970s 1.70 (21.3% net), 1980s 0.96, 1990s 0.98, and **Jan 2000–Dec 2013 only 7.9% net, Sharpe 0.62**. The weakest decades were the 1910s (Sharpe 0.13) and 1880s (0.27). Every decade was positive — [AQR PDF](https://oxfordstrat.com/coasdfASD32/uploads/2016/03/A-Century-of-Evidence-on-Trend-Following-Investing.pdf)
  - Positive returns in **8 of the 10 largest 60/40 drawdowns** from 1880 to 2013. The average peak-to-trough length of those drawdowns was about 15 months, which gives trend followers time to reposition — [AQR PDF](https://oxfordstrat.com/coasdfASD32/uploads/2016/03/A-Century-of-Evidence-on-Trend-Following-Investing.pdf)
  - Moving 20% of a 60/40 portfolio into TSMOM over 1880–2013 changed return from 7.8% to 8.5%, volatility from 10.8% to 8.8%, max drawdown from −62.3% to −50.2%, and Sharpe from 0.38 to 0.54 — [AQR PDF](https://oxfordstrat.com/coasdfASD32/uploads/2016/03/A-Century-of-Evidence-on-Trend-Following-Investing.pdf)
  - The worst simulated TSMOM drawdown was **−26.3%** (Aug 1947–Dec 1948), with a 45-month peak-to-recovery. The second worst was −25.3% (1937–1940), taking 75 months to recover — [AQR PDF](https://oxfordstrat.com/coasdfASD32/uploads/2016/03/A-Century-of-Evidence-on-Trend-Following-Investing.pdf)
  - The paper itself acknowledges that "returns have been mixed since 2008" and discusses AUM growth (BarclayHedge estimates managed-futures AUM rose from $22bn in 1999 to over $280bn in 2014) and higher cross-market correlations as possible headwinds — [AQR PDF](https://oxfordstrat.com/coasdfASD32/uploads/2016/03/A-Century-of-Evidence-on-Trend-Following-Investing.pdf)

**Academic critique**
- Huang, Li, Wang & Zhou, "Time Series Momentum: Is It There?", *JFE* 2020 (vol. 135, issue 3, pp. 774–794): asset-by-asset regressions show "little evidence" of TSMOM both in- and out-of-sample. The pooled t-statistic falls below bootstrap critical values. TSMOM profits are "virtually the same" as a strategy based on each asset's historical sample mean, which needs no predictability. Sample: 55 contracts — [WashU profile](https://profiles.wustl.edu/en/publications/time-series-momentum-is-it-there/); [RePEc](https://econpapers.repec.org/RePEc:eee:jfinec:v:135:y:2020:i:3:p:774-794); [Alpha Architect summary](https://alphaarchitect.com/an-empirical-challenge-for-trend-following/)
- A February 2026 blog rebuttal concludes that some criticisms have merit but TSMOM "remains an appealing strategy" (not peer reviewed) — [Philosophical Multicore / mdickens](https://buttondown.com/mdickens/archive/contra-time-series-momentum-is-it-there/) [SNIPPET]

**Live index performance (net of manager fees)**

| Year | SG Trend Index | SG CTA Index | BTOP50 | DBMF (US replicator ETF, total return) | S&P 500 TR |
|---|---|---|---|---|---|
| 2008 | n/a | ~+13.1% [secondary] | Barclay CTA ~+14% [secondary] | — | ~−37% |
| 2009–2013 | −1.8% cumulative (Man) | | | | |
| 2014 | +19.7% (Man) / +15.7% (another source; conflict) | | | | |
| 2020 | not found | | | +1.80% | |
| 2021 | not found | | | +11.49% | |
| **2022** | **+27.3% (record)** | | | **+21.60%** | |
| 2023 | **−4.16%** | | −1.70% | −8.94% | |
| 2024 | **+2.42%** | | +4.44% | +7.24% | |
| 2025 | **+2.39%** | **−0.2%** | +2.81% | +13.84% | +17.89% |
| 2026 YTD (to 30 Sep) | **+15.80%** (trailing 12m +21.33%) | | +14.81% | | +12.75% |

Sources for the table:
- 2022 +27.3%, the best of the SG CTA indices that year — [Hedgeweek](https://www.hedgeweek.com/trend-followers-turn-leaders-ctas-deliver-record-returns-2022/)
- 2023: SG Trend −4.16%, BTOP50 −1.70% (TTU report, 20 Jan 2024) — [Top Traders Unplugged Dec 2023](https://www.toptradersunplugged.com/trend-following-performance-report-december-2023/)
- 2024: SG Trend +2.42%, BTOP50 +4.44% (TTU, 22 Jan 2025) — [TTU Dec 2024](https://www.toptradersunplugged.com/trend-following-performance-report-december-2024/)
- 2025: SG Trend +2.39%, BTOP50 +2.81%, S&P 500 TR +17.89%; SG Trend CAGR since 2000 5.33%, max drawdown 20.61% (TTU, 23 Jan 2026) — [TTU Dec 2025](https://www.toptradersunplugged.com/trend-following-performance-report-december-2025/)
- 2025 SG CTA −0.2%. Since Jan 2020: SG Trend +49.0% cumulative (6.9% CAGR), SG CTA +29.8% — [Aussie Turtles, Battle of the Trend Indexes Dec 2025](https://www.aussieturtles.com/battle-of-the-trend-following-indexes-december-2025/)
- 2026 YTD: SG Trend +15.80% to 30 Sep 2026 (September alone +4.26%), CAGR since 2000 5.75%, max drawdown 20.61%. BTOP50 +14.81% YTD; S&P 500 TR +12.75% YTD. Drivers: energy longs, short bonds, short precious metals (declining since February 2026), equity longs (TTU, 26 Oct 2026) — [TTU Sep 2026](https://www.toptradersunplugged.com/trend-following-performance-report-september-2026/)
- SG Trend YTD fell back to +14.97% by 16 Oct 2026 — [TTU Week in Review 16 Oct 2026](https://www.toptradersunplugged.com/trend-following-week-in-review-october-16-2026/) [SNIPPET]
- DBMF calendar-year total returns: 2020 +1.80%, 2021 +11.49%, 2022 +21.60%, 2023 −8.94%, 2024 +7.24%, 2025 +13.84%. Yahoo Finance gives nearly identical figures; price-only sources differ — [totalrealreturns](https://totalrealreturns.com/n/DBMF); [Yahoo](https://ca.finance.yahoo.com/quote/DBMF/performance/)
- 2008 SG CTA ~+13.1% and Barclay CTA ~+14% vs S&P 500 −37% come from secondary sources surfaced by search and were not verified against SG data — [The Hedge Fund Journal](https://thehedgefundjournal.com/the-convexity-of-trend-following/); [ryanoconnellfinance](https://ryanoconnellfinance.com/managed-futures-cta/) [SNIPPET]
- 2009–2013 SG Trend −1.8% and 2014 +19.7% — [Man Group, "Is This Time Different?"](https://www.man.com/insights/is-this-time-different) [VENDOR]. Another source gives 2014 as +15.7% (probably a different SG index) — [SNIPPET via search]

**The 2024–2025 drawdown**
- SG Trend rolling 12-month return was **−18.6% to 30 April 2025**. It is one of only two rolling 12-month windows worse than −15% since 2000; the previous worst was −16.0% in January 2019. The index peaked in May 2024. From the January 2019 low to May 2024 it returned +82.5%. After past rolling 12-month losses greater than 10%, the next 12 months averaged +9.8% (published around June 2025) — [Man Group](https://www.man.com/insights/is-this-time-different) [VENDOR]
- AlphaSimplex/Virtus: −18.7% over the 12 months to 30 April 2025, "the worst performance in the Index's 25-year history" — [Virtus, Kaminski & Wen, June 2025](https://www.virtus.com/assets/files/98p/2025.06---market-cycles-and-managed-futures---kaminski-and-wen.pdf) [VENDOR] [SNIPPET]
- Cambridge Associates: second-largest SG Trend drawdown since 2000, −20.4% from May 2024 to May 2025 — [Cambridge Associates](https://alumni.cambridgeassociates.com/news/1316922) [SNIPPET]
- WSJ (via AlphaMaven): trend CTAs were −9.6% in H1 2025, "tracking toward their worst annual performance since at least 1998". The year ended positive — [AlphaMaven/WSJ](https://alpha-maven.com/story/managed-futures/a-wild-year-for-markets-hits-trend-following-hedge-funds-wsj) [SNIPPET]
- Dispersion among managers was large in 2025: IASG Trend Index +6.7%, Fulcrum Trend +10.5%, TTU TF Index −0.6% — [Aussie Turtles](https://www.aussieturtles.com/battle-of-the-trend-following-indexes-december-2025/); [Fulcrum 2025 review](https://fulcrumasset.com/wp-content/uploads/2026/02/Fulcrum_Trend_Strategy_2025.pdf) [VENDOR]

**Long-run and decay evidence**
- SG Trend from Jan 2000 to May 2025: **4.9% annualized, 13.4% volatility**, versus MSCI ACWI 6.2% (15.6% volatility) and Bloomberg US Aggregate 4.0% (4.2% volatility). Average correlation −0.10 to global equities and +0.10 to long government bonds. Managed-futures AUM peaked at **$365bn in 2022**. As a share of hedge-fund AUM it peaked at about 23.5% in 2012 and fell to about 6.2% by June 2025 (Meketa, Dec 2025, consultant) — [Meketa](https://meketa.com/wp-content/uploads/2025/12/MEKETA_Trend-Following.pdf)
- Decade split for SG Trend: 2000–2009 8.2% annualized, **2010–2019 1.8%**, "2020–present" 17.9% (end date not verified; the AQR PDF returned 404 when fetched) — [AQR "Trend-Following: Why Now? A Macro Perspective"](https://www.aqr.com/-/media/AQR/Documents/Whitepapers/Trend-Following-Why-Now-A-Macro-Perspective.pdf?sc_lang=en) [VENDOR] [SNIPPET]
- "Between 2008 and 2018, Societe Generale's main trend-following index made only 3.7 percent" (cumulative) — [FA Magazine](https://www.fa-mag.com/news/one-of-wall-street-s-most-popular-trading-strategies-is-failing-43592.html?page=2) [SNIPPET]
- AQR, "You Can't Always Trend When You Want" (2019): the weak 2010s are attributed to a lack of large risk-adjusted market moves, not to an inability to monetize trends. Diversification across markets was not unusually low — [The Idea Farm summary](https://theideafarm.com/alternative-investment/you-cant-always-trend-when-you-want/); [blog review](https://rivershedge.blogspot.com/2019/05/aqr-on-trend-not-being-dead-yet.html) [VENDOR] [SNIPPET]
- Man (mid-2025) concedes that **short-term trend** and equity pairs trading have lost their edge, but argues medium/long-term trend has not decayed. Evidence offered: CTA share of futures volumes shows no overcrowding; correlation between trend performance and fund flows is −0.1. Man also estimates that a "drawdown-exit" rule underperformed a consistent allocation by about 2.2%/yr — [Man Group](https://www.man.com/insights/is-this-time-different) [VENDOR]
- Post-crisis periods: academic work finds trend returns in extended post-crisis periods are "less than half" of those in no-crisis periods — [UCC, "Is this time different? Trend following and financial crises"](https://research.ucc.ie/en/publications/is-this-time-different-trend-following-and-financial-crises-2/) [SNIPPET]

### Inferences
- **IS vs OOS gap:** the century backtest is about 11.2% net at 9.7% volatility (Sharpe 0.77). The live SG Trend from 2000 to 2025 is about 4.9–5.8% at 13.4% volatility (Sharpe roughly 0.25–0.35 after subtracting cash). A gap of this size is typical of post-publication decay plus real-world fees and costs, but some of it reflects 2000–2025 being a low-trend era (the 2010s). The 2022 and 2026 results show the strategy still delivers in macro/inflation regimes.
- **Crisis behaviour:** trend worked in 2008 (gradual bear market) and 2022 (rates/inflation shock, where short bonds and long commodities did the work, per Meketa). It was mixed in 2020: the crash was fast, with modest gains in March and a weak rebound. It lost money during the 2025 V-shaped tariff shock. Trend protects against slow, persistent bear markets, not sudden reversals.
- **Decay evidence:** I found no proof of structural decay in medium/long-horizon trend. The record since publication (2012 onward) is one weak sub-period (2012–2019 apart from 2014), then 2022 and 2026 strong, and a record drawdown in 2024–25. Fees (2/20 or about 0.75–1% for replicators) take a large share of a gross Sharpe that is probably 0.4–0.6 in live trading.
- **For a retail investor:** managed futures are best used as a diversifying sleeve (10–20%) rather than a standalone return engine. Expect multi-year stretches of flat-to-negative returns (2009–2013, 2023–mid-2025).

### Gaps
- SG Trend and SG CTA calendar-year returns for 2015–2021 were not found in an accessible primary source. Société Générale's index page and factsheets would be authoritative.
- The 2017 JPM final version of Hurst et al. (data to 2016) was not read; the figures above are from the 2014 whitepaper version.
- No independent (non-vendor) peer-reviewed study of post-2012 out-of-sample TSMOM decay was found.

---

## 2. ETF-based TAA models: rules, published backtests, and post-publication performance

### Takeaway
Most famous ETF TAA models beat 60/40 on drawdown in their in-sample backtests. After publication, they generally **lagged US equities and often matched or trailed a static 60/40 on Sharpe**. Their drawdown advantage was concentrated in 2008. 2022 was a regime they handled badly: TAA aggregate drawdown −12.1% vs −7.1% in 2007–08, because bonds failed as the defensive asset. Faber's GTAA held up reasonably out of sample to 2016 (on his own analysis), but underperformed stocks in 6 of the 8 years after 2009. Antonacci's GEM has lagged SPY by about 4.8–5 points a year since about 2010–2014 on independent replications. Keller's newer models (VAA, DAA, BAA) are tuned to recent history and carry explicit overfitting warnings; BAA (2022) has too little out-of-sample data. Risk parity lost about 22% in 2022. TAA as a group did well in 2025 and early 2026 relative to 60/40 [TRACKER].

### Cited Findings

**Faber GTAA / 10-month SMA ("A Quantitative Approach to Tactical Asset Allocation")**
- **History and rules:** drafted 2006 ("A Simple Approach to Market Timing"), published in the *Journal of Wealth Management* 2007, updated in a 2013 white paper (SSRN 962461), and revisited in *JPM* 2018 (Multi-Asset Special Issue, 44(2):156–167). Rule: hold an asset when its monthly close is above its 10-month SMA, otherwise hold T-bills. Five equal-weight sleeves: US stocks, foreign stocks, US 10-year Treasuries, REITs, commodities. Monthly updates; the paper calls this a "monthly version of the 200-day SMA". It became the most-downloaded paper on SSRN (~200,000 downloads) — [Faber JPM 2018 revisit](https://allocatortraining.com/wp-content/uploads/2023/06/A-Quantitative-Approach-to-Tactical-Asset-Allocation.pdf); [GTAA5 model description](https://edgetools-site.pages.dev/portfolio-models/gtaa5-live)
- **IS vs OOS (Faber's own revisit, 2018):** US stock timing improved compounded returns and reduced volatility and drawdown in both 1901–2005 (IS) and 2006–2016 (OOS). The timing system "outperformed by a significant amount during the 2008–2009 bear market" but "**went on to underperform stocks six of the next eight years**". For the five-asset QTAA portfolio, "timing results in a reduction of volatility to single-digit levels, as well as a single-digit maximum drawdown in both periods", and returns were lower for all assets OOS. On average about 30% of the portfolio sits in cash. Turnover: **3–4 round-trip trades per year for the portfolio, fewer than 1 per asset class per year**. The 2006–2016 parameter-stability exhibit shows other MA lengths would also have beaten buy-and-hold. Faber himself notes survivorship ("if QTAA had performed poorly... no one would be reading this article") and that ten years is too short to judge. Exact CAGR, Sharpe and drawdown numbers are in images and were not extractable — [Faber JPM 2018](https://allocatortraining.com/wp-content/uploads/2023/06/A-Quantitative-Approach-to-Tactical-Asset-Allocation.pdf) [VENDOR: Cambria CIO]
- **Independent test of the 10-month rule on SPY:** 23 round trips in 33 years. Out-of-sample: Sharpe 0.68 vs 0.63 for buy-and-hold, return **8.2%/yr vs 10.9%**, worst drawdown **25.6% vs 55.2%** (about Oct 2026) — [Empiricalab substack](https://empiricalab.substack.com/p/faber-10-month-average) [INDEPENDENT-BLOG] [SNIPPET]
- **Live fund record:** the AdvisorShares/Cambria Global Tactical ETF (GTAA), sub-advised by Faber and Richardson from 26 Oct 2010, was −4.87% from inception by late 2011. In 2011 the paper model returned +2.49% while the ETF lost −7.29%; a 2013 analysis said the fund "bears little resemblance" to the published strategy. Faber later left the sub-advisory role — [ETF Trends](https://www.etftrends.com/2011/10/etf-chart-of-the-day-absolute-returns/amp/); [Canadian Couch Potato 2013](https://canadiancouchpotato.com/2013/12/30/the-failed-promise-of-market-timing/); [etf.com](https://www.etf.com/node/74028.md) [SNIPPET]

**Antonacci Dual Momentum / Global Equities Momentum (GEM)** (book *Dual Momentum Investing*, 2014)
- **Rules:** monthly, 12-month total-return lookback. Absolute momentum: if US stocks beat T-bills, hold whichever of US or non-US stocks has the higher 12-month return; otherwise hold aggregate bonds. ETF proxies: SPY, VEU, AGG, BIL — [Quant for Free](https://quant4free.com/analysis/dual-momentum/)
- **Post-publication (independent; author "ridingyo", 31 Jul 2026; costs not stated):**
  - Since 2014 (OOS): **GEM CAGR 8.4%, Sharpe 0.70, max drawdown −20%** vs SPY 13.6% / 0.94 / −24% and static 60/40 9.1% / 0.95 / −20%.
  - 2008–2026: GEM 9.1% / 0.74 / −20% vs SPY 11.6% / 0.77 / −42%.
  - **30 switches in 18 years.** Whipsaws noted in 2011 and 2015–16. Defensive moves in 2020 and 2022 judged good calls.
  - Verdict: the drawdown edge "was mostly a 2008 story".
  - Source: [Quant for Free](https://quant4free.com/analysis/dual-momentum/) [INDEPENDENT-BLOG]
- **SSRN replication (Marius Petit), 1971–2026:** GEM 15.18% vs S&P 500 11.27% over the full sample, but GEM **has trailed a passive index by 4.8 points/yr since 2010**. Its deepest drawdown in 55 years came in 2021–2023 while it held its defensive asset (bonds). The author does not treat the full-sample record as evidence the rule will keep working — [SSRN 7427878](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7427878) [SNIPPET; page returned 403]
- **GEM in 2022:** **−17.53%, max drawdown −20.93%**. GEM rotated into AGG, which itself fell sharply. Hypothetical backtest with transaction costs, Tiingo data, published 21 Apr 2026 and revised 3 Oct 2026 — [BestFolio](https://bestfolio.app/blog/dual-momentum-2022-canary-models) [AI-WRITTEN]. This conflicts in tone with Quant for Free's "good call" for 2022; the difference is plausibly because the bond leg lost money.
- **Decomposition, 2008–2026:** the absolute-momentum gate did most of the work, and the international (relative-momentum) leg **cost 1.4–3.2 points/yr at every lookback tested** — [QuanterLab](https://quanterlab.com/research/antonacci-s-dual-momentum-taken-apart-gate-relative-leg-and-blends-across-four-l) [INDEPENDENT-BLOG] [SNIPPET]
- An advocate site shows GEM at 13.8% CAGR and −21.9% max drawdown from 1980 to Sep 2026, acknowledging a much thinner recent margin over buy-and-hold — [Dual Momentum Systems](https://dualmomentumsystems.com/strategies/global-equities-momentum) [SNIPPET]
- Antonacci's own extended backtest and claims — [Antonacci on Medium](https://medium.com/@garyantonacci_30463/extended-backtest-of-global-equities-momentum-dual-momentum-eb12902612e0) [VENDOR] (not opened)

**Keller family: PAA (2016), VAA (2017), DAA (2018), BAA (2022)**
- **VAA (Keller & Keuning, SSRN 3002624, 2017):**
  - Offensive assets: SPY, EFA, EEM, AGG. Defensive assets: LQD, IEF, SHY.
  - Momentum score "13612W" = 12×r1m + 4×r3m + 2×r6m + 1×r12m, so roughly 40% of the weight is on the last month.
  - If all four offensive assets have positive scores, hold 100% in the top one; otherwise hold 100% in the best defensive asset.
  - Allocate Smartly backtest from 1971, net of costs: **Sharpe 1.10, max drawdown −16.1%**. Without the AGG "spoiler", Sharpe 0.83 and max drawdown −25.2%; only 104 months support the AGG effect.
  - Results show "wide disparity" depending on which day of the month is traded. Single-asset concentration is flagged as dangerous.
  - Source: [Allocate Smartly VAA, 26 Jul 2017](https://allocatesmartly.com/vigilant-asset-allocation-dr-wouter-keller-jw-keuning/) [TRACKER]; [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3002624)
- **BAA (SSRN 4166845, Jul 2022):**
  - Canary assets: SPY, EFA, EEM, AGG, scored with 13612W; any negative canary means switching to defensive. That happens about 60% of the time.
  - Offensive (Aggressive variant): top 1 of QQQ, EEM, EFA, AGG. Offensive (Balanced variant): top 6 of 12 assets.
  - Defensive: top 3 of TIP, DBC, BIL, IEF, TLT, LQD, AGG, with anything weaker than BIL replaced by cash.
  - Allocate Smartly: "there is probably a **larger than usual helping of overfitting** built into BAA". Keller "mostly brute forced a single optimal combined solution" and tuned the asset universe. Expectations should be tempered.
  - BAA-Aggressive is "the most tax inefficient strategy we track".
  - Keller's strategies overall "remain among the top performers we track in real-time out-of-sample trading".
  - Source: [Allocate Smartly BAA, 29 Aug 2022](https://allocatesmartly.com/bold-asset-allocation/) [TRACKER]; [SSRN 4166845](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4166845)
- **2022 calendar-year backtests (hypothetical, with costs):**

  | Strategy | 2022 return | 2022 max drawdown |
  |---|---|---|
  | VAA-G4 | −11.24% | −11.83% |
  | DAA-G12 | −10.11% | −10.97% |
  | BAA-G4 | +2.78% | −9.29% |
  | BAA-G12 | +2.37% | −10.08% |
  | PAA | −16.21% | −19.19% |

  Note: BAA was published in July 2022, so most of its 2022 is not out of sample — [BestFolio](https://bestfolio.app/blog/dual-momentum-2022-canary-models) [AI-WRITTEN]
- One re-test found the BAA canary version had a Sharpe of 0.16 on 2022 windows, and that its breadth settings collapse to all-or-nothing — [QuanterLab](https://quanterlab.com/research/the-crash-switch-worked-and-the-strategy-starved-anyway-keller-s-menu-tested) [INDEPENDENT-BLOG] [SNIPPET]

**Adaptive Asset Allocation (Butler, Philbrick & Gordillo, ReSolve, 2012)**
- **Rules:** 10 asset classes; select the top 50% by 6-month (about 120-day) momentum; weight them by minimum variance with roughly a 20-day lookback for volatility and correlation.
- **IS result:** 16.9% vs 8.4% annualized for the equal-weight benchmark (Jan 1995–Mar 2012, **weekly** rebalancing).
- CXO flags only about 34 independent six-month momentum intervals and possible snooping in the lookback choices.
- A 2023 replication from late 1997 found the top-momentum equal-risk portfolio at 14.2% vs 13.7% for momentum equal-weight, against 14.0% vs 13.0% in the paper.
- Sources: [CXO Advisory](https://www.cxoadvisory.com/volatility-effects/agile-portfolio-theory/); [R-bloggers replication, Dec 2023](https://www.r-bloggers.com/2023/12/adaptive-asset-allocation-replication/); [Alpha Architect](https://alphaarchitect.com/digging-deeper-into-adaptive-asset-allocation/) [SNIPPET]

**Risk parity / All Weather / Permanent Portfolio in 2022**
- Bridgewater All Weather: about **−22% in 2022**; its retail 10%-volatility version also −22%. Investors pulled billions afterwards — [Fortune, Apr 2024](https://fortune.com/2024/04/23/lackluster-returns-ray-dalio-investing-strategy-investors-pull-billions/) [SNIPPET]
- RPAR Risk Parity ETF: **−32% from its Nov 2021 high** by late Sep 2022, a record drawdown — [Bloomberg, 28 Sep 2022](https://www.bloomberg.com/news/articles/2022-09-28/-perfect-storm-for-risk-parity-has-etf-posting-record-32-drop) [SNIPPET]
- Permanent Portfolio 2022: **−5.5%** for the PRPFX mutual fund per CAIA, vs −8.44% per a Substack backtest (vehicles differ) — [CAIA](https://caia.org/node/7312); [Schwoerer substack](https://martinschwoerer.substack.com/p/harry-browne-lives-in-my-head-but) [SNIPPET; conflicting]

**Volatility targeting**
- Cederburg, O'Doherty, Wang & Yan, *JFE* 2020 (vol. 138, pp. 95–117), testing Moreira-Muir across 103 equity strategies:
  - The in-sample spanning-regression alphas replicate.
  - In direct comparisons, volatility-managed versions win only **53 of 103** (originals win 50).
  - "Reasonable out-of-sample versions generally earn lower certainty equivalent returns and Sharpe ratios" than the unmanaged portfolios, which the authors attribute to structural instability.
  - Barroso & Detzel show these strategies do not survive transaction costs. DeMiguel et al. (JF 2024) find a conditional multifactor version can survive out of sample.
  - Sources: [RePEc](https://econpapers.repec.org/RePEc:eee:jfinec:v:138:y:2020:i:1:p:95-117); [Lehigh PDF](https://www.lehigh.edu/~xuy219/research/COWY.pdf); [Alpha Architect](https://alphaarchitect.com/does-portfolio-timing-based-on-volatility-signals-outperform-buy-and-hold/); [DeMiguel et al. RePEc](https://econpapers.repec.org/RePEc:bla:jfinan:v:79:y:2024:i:6:p:3859-3891)
- In TSMOM itself, volatility scaling is part of the construction: AQR targets 10% volatility, and most CTAs run 12–15% volatility — [AQR PDF](https://oxfordstrat.com/coasdfASD32/uploads/2016/03/A-Century-of-Evidence-on-Trend-Following-Investing.pdf); [Meketa](https://meketa.com/wp-content/uploads/2025/12/MEKETA_Trend-Following.pdf)

**Aggregate live TAA tracking (Allocate Smartly)** [TRACKER]
- Tracks 100+ published TAA strategies, many live since the site launched in late 2016 — [Allocate Smartly TAA performance archive](https://allocatesmartly.com/category/taa-performance/) [SNIPPET]
- **2022:** aggregate TAA month-end max drawdown was **−12.1%**, vs −2.8% in 2000–02 and −7.1% in 2007–08, and it lasted longer. The cause was defensive assets (long Treasuries), not late timing. Over the first 9 months of 2022, S&P 500 −23.9% and IEF −15.6%. Strategies with low rate sensitivity had a −8.0% max drawdown vs −17.3% for high rate sensitivity. Strategies that require positive momentum for defensive assets did better. 72 strategies analysed; 3 were published after the Sept 2022 trough. Posted 22 Sep 2023 — [Allocate Smartly](https://allocatesmartly.com/tactical-asset-allocation-performance-during-the-2022-bear-market/)
- "Over the last 15+ years, diversification has been a huge drag on TAA performance, to the tune of **2.1% per year** compared to the 60/40 benchmark." TAA "did reasonably well in 2025 and has done very well in these early days of 2026" relative to 60/40 — [Allocate Smartly TAA performance archive](https://allocatesmartly.com/category/taa-performance/) [SNIPPET]
- An early-2026 post attributes TAA outperformance in 2025: 57% from generally held assets and 43% from timing. Q2 2025 suffered from overly conservative positioning (after the April tariff crash); Q3–Q4 gained via gold and international exposure — [pulse.bot repost of Allocate Smartly](https://www.pulse.bot/stock-trading/news/why-taa-is-performing-well-now-outperformance-attribution-e6a9a396-10e3-4333-a41c-9ee43923f9cb/) [SNIPPET; page returned 503]

### Inferences
- **IS vs OOS summary:**

  | Model | Published | IS headline | Post-publication evidence |
  |---|---|---|---|
  | Faber GTAA | 2007 | Equity-like returns, bond-like volatility, single-digit max drawdown | Held up to 2016 per Faber; lagged stocks most years after 2009; likely hurt in 2022 because the bond sleeve fell and REITs/commodities whipsawed (not verified with numbers) |
  | GEM | 2014 | About 15% CAGR since 1971 | About 8.4% CAGR / 0.70 Sharpe since 2014, below SPY (13.6% / 0.94) and roughly equal to 60/40 |
  | VAA / DAA / PAA | 2016–2018 | Sharpe ~1.1 | Allocate Smartly says they rank well live (no numbers found); 2022 around −10% to −16% |
  | BAA | 2022 | — | Too new; explicit overfitting warning |

- **Defensive-asset design matters most after 2022.** Models that move into long-duration bonds unconditionally (GEM into AGG, the original VAA into LQD/IEF) did worse than models that require defensive assets to beat cash (BAA, DAA's cash option). This is the main lesson from 2022.
- **Benchmark choice drives conclusions.** Against SPY or MSCI World in a US-led bull market (2010–2024), almost every TAA model loses. Against 60/40 on drawdown-adjusted terms, most are roughly break-even after costs. Against EUR-denominated 60/40, the comparison is untested in the sources found.

### Gaps
- No primary source found for Allocate Smartly's per-strategy live (post-2016) CAGR, Sharpe or drawdown figures; these are behind its paywall.
- Faber's exact QTAA CAGR, Sharpe and drawdown figures for IS 1973–2005 and OOS 2006–2016 are in exhibit images in the JPM revisit and could not be extracted. Faber's 2013 update numbers were not found in a fetchable source.
- No independent GTAA5 performance calculation for 2017–2026 (including 2022) was found.
- Keller's PAA and DAA original-paper statistics were not retrieved.
- No source found for AAA's live performance after 2012 (ReSolve's live funds were not checked).
- No quantified turnover figures were found for GEM (only "30 switches in 18 years"), VAA or BAA.

---

## 3. Independent critiques: out-of-sample underperformance, whipsaw costs, rebalance timing luck, lookback overfitting

### Takeaway
The day of the month a strategy trades can move its returns by as much as its claimed edge. Faber's 10-month rule on SPY showed max drawdown ranging from 19% to 30% depending on a one-day shift. Allocate Smartly finds month-end trading added 0.57%/yr historically and recommends haircutting backtests by that amount. Tactical mutual funds have a poor long-run record against 60/40 (Morningstar). Lookback choices (12-month, 10-month, 13612W) are partly fitted, and Keller's newer papers stack fitted features. Tranching (splitting capital across several rebalance dates) is the main practical remedy.

### Cited Findings
- **Newfound Research (Hoffstein), 7 Aug 2013:** Faber's 10-month SMA on SPY with 21 one-day offsets (signal at the close, trade at the next open, no costs). A one-day shift changed max drawdown from **19.03% to 30.22%** and annualized return from **11.33% to 10.51%**. Total return across offsets ranged from 462.89% to 717.14%. The remedy was 21 tranches, each rebalanced on a different day: 10.98% annualized, 13.37% volatility, −19.03% max drawdown, with similar turnover — [Newfound Research](https://blog.thinknewfound.com/2013/08/the-luck-of-the-rebalance-timing/)
- **Hoffstein, Sibears & Faber, "Rebalance Timing Luck: The Difference Between Hired and Fired" (Oct 2018):** even an annually rebalanced 60/40 shows a 0.36% standard deviation of 12-month rolling returns across 12 rebalance months. The effect is not mean-reverting. Holding N staggered portfolios reduces the noise by roughly 1/N — [CXO summary](https://www.cxoadvisory.com/?p=32143); [Newfound "Quantifying Timing Luck" 2018](https://blog.thinknewfound.com/2018/01/quantifying-timing-luck/) [SNIPPET]
- **"The Dumb (Timing) Luck of Smart Beta" (Hoffstein, Faber & Braun, Nov 2019):** index timing luck "often exceed[s] 100 basis points annualized", and reaches about 4.4% for momentum portfolios. Timing luck rises with turnover, concentration and lower rebalance frequency — [Newfound](https://blog.thinknewfound.com/2019/11/the-dumb-timing-luck-of-smart-beta/) [SNIPPET]
- **Allocate Smartly, "Does the Day of the Month Matter?" (16 Nov 2021):** 55 TAA strategies with annual turnover of at least 50%, from 1970. Month-end trading added **+0.57%/yr** vs the average day. Since the site launched in late 2016 (mostly OOS), month-end outperformed by more than 0.96%/yr **including Q1 2020**, but slightly underperformed **excluding** Q1 2020. Executing an end-of-month signal one day late "significantly hurt performance". Recommendations: haircut backtests by 0.57%/yr for possible overfitting, and tranche across trading days — [Allocate Smartly](https://allocatesmartly.com/diving-deeper-does-the-day-of-the-month-matter/) [TRACKER]
- **VAA:** "wide disparity" in results across trading days ("timing luck") — [Allocate Smartly VAA](https://allocatesmartly.com/vigilant-asset-allocation-dr-wouter-keller-jw-keuning/)
- **BAA:** explicit "larger than usual helping of overfitting" from stacking features of PAA, VAA and DAA and tuning the asset universe — [Allocate Smartly BAA](https://allocatesmartly.com/bold-asset-allocation/)
- **AAA:** possible snooping in the lookback choices; only about 34 independent six-month intervals — [CXO Advisory](https://www.cxoadvisory.com/volatility-effects/agile-portfolio-theory/) [SNIPPET]
- **Huang et al. 2020:** TSMOM predictability is not statistically robust asset by asset (see Section 1) — [Alpha Architect](https://alphaarchitect.com/an-empirical-challenge-for-trend-following/)
- **Cederburg et al. 2020:** volatility-managed portfolios fail out of sample (see Section 2) — [Alpha Architect](https://alphaarchitect.com/does-portfolio-timing-based-on-volatility-signals-outperform-buy-and-hold/)
- **Morningstar on tactical mutual funds:** for the decade to April 2023, the average tactical allocation fund "badly underperformed" a US 60/40 mix. Morningstar's earlier "Why Tactical-Allocation Funds Failed—Again" makes the same point (could not be fetched; 403) — [Evidence Investor summary](https://evidenceinvestor.com/post/tactical-allocation-funds-have-been-stinkers-morningstar); [Morningstar](https://www.morningstar.com/funds/why-tactical-allocation-funds-failedagain) [SNIPPET]
- **Faber's own caveat:** "what if QTAA had performed poorly? Then likely no one would be reading this article" (survivorship of popular strategies) — [Faber JPM 2018](https://allocatortraining.com/wp-content/uploads/2023/06/A-Quantitative-Approach-to-Tactical-Asset-Allocation.pdf)
- **GEM:** the drawdown edge was "mostly a 2008 story"; GEM lost to 60/40 on risk-adjusted terms after 2014 — [Quant for Free](https://quant4free.com/analysis/dual-momentum/). The relative-momentum leg cost 1.4–3.2 points/yr — [QuanterLab](https://quanterlab.com/research/antonacci-s-dual-momentum-taken-apart-gate-relative-leg-and-blends-across-four-l) [INDEPENDENT-BLOG]
- **Man's argument against timing:** a rule that exits trend after drawdowns underperformed a consistent allocation by about 2.2%/yr — [Man Group](https://www.man.com/insights/is-this-time-different) [VENDOR]

### Inferences
- **Treat any single-date backtest as having ±0.5–1%/yr noise, and more for concentrated single-asset models** (GEM, VAA, BAA-Aggressive). A retail implementation should either tranche (for example, split capital into 2–4 sub-portfolios rebalanced on different days) or accept the variance.
- **Combine models rather than pick the best backtest.** Allocate Smartly explicitly recommends diversifying across strategies. Blending GTAA (slow, diversified), a dual-momentum model, and a trend-fund sleeve reduces both timing luck and parameter-overfitting risk.
- **Apply a haircut to published backtests.** A reasonable planning assumption is IS CAGR minus 1–3%/yr: 0.57% for timing luck, plus costs and taxes, plus the OOS decay seen in GEM.

### Gaps
- No independent study was found that quantifies **whipsaw cost in euros** (spread plus commissions plus FX) for a UCITS-ETF TAA on IBKR.
- No Reddit, Bogleheads or r/algotrading replication threads with numbers were retrieved; only blog and SSRN replications.

---

## 4. Simple trend filters on equity indices (200-day SMA, 10-month SMA): effect 2015–2026

### Takeaway
Over the last 15 years, a 200-day or 10-month SMA filter on the S&P 500 **cost roughly 2.5–3.7 points per year of return** while cutting max drawdown by about 14 points (daily) or roughly halving it over long samples. Sharpe was about equal or slightly better. The rule was **worse than buy-and-hold on the Nasdaq-100**. Major whipsaws came from V-shaped events: 2015–16 for multi-asset and dual-momentum models, late 2018, the 2020 COVID crash and rebound, the April 2025 tariff crash followed by new highs by late June, and a March 2026 break below the 200-day. 2022 was the one recent year where the filter clearly helped equity-only investors, because the decline was slow.

### Cited Findings
- **SPY, daily 200-day rule (price above the MA = hold, else cash, 1-day lag), Mar 2011–19 Aug 2026:** gave up **3.7 points/yr** of return, removed **14 points of max drawdown**, slightly higher Sharpe, about 16% of time in cash. On QQQ the rule underperformed buy-and-hold even before costs, and 150 days would have been better than 200 (a parameter-sensitivity warning). Author: Yimin Xu, 8 Sep 2026 — [The Long Trend substack](https://thelongtrend.substack.com/p/i-tried-to-debunk-the-200-day-moving) [INDEPENDENT-BLOG]
- **Faber 10-month rule on SPY:** 23 round trips in 33 years. OOS return 8.2% vs 10.9%, Sharpe 0.68 vs 0.63, worst drawdown 25.6% vs 55.2% — [Empiricalab](https://empiricalab.substack.com/p/faber-10-month-average) [INDEPENDENT-BLOG] [SNIPPET]
- **Faber's own 2006–2016 OOS:** timing beat buy-and-hold in 2008–09 but lagged stocks in 6 of the 8 following years — [Faber JPM 2018](https://allocatortraining.com/wp-content/uploads/2023/06/A-Quantitative-Approach-to-Tactical-Asset-Allocation.pdf)
- **2025 whipsaw:** the S&P 500 lost 4.84% on 3 April 2025 after the "Liberation Day" tariffs; the tariff pause was announced 9 April. In mid-April the index sat about 8% below its 200-day MA. It closed at an all-time high on 27 June 2025, so a 200-day exit in March/April re-entered at higher prices — [Wikipedia, 2025 stock market crash](https://en.wikipedia.org/wiki/2025_stock_market_crash); [StockCharts, Apr 2025](https://stockcharts.com/articles/mindfulinvestor/2025/04/200day-moving-average-confirms-619.html) [SNIPPET]
- **March 2026:** the S&P 500 closed below its 200-day SMA "for the first time since May 9, 2025", alongside the Dow and Nasdaq — [Benzinga, Mar 2026](https://www.benzinga.com/markets/equities/26/03/51358334/dow-sp500-nasdaq-200-day-breakdown-march-2026) [SNIPPET; page returned 403]. By end-September 2026 the S&P 500 TR was +12.75% YTD and the Nasdaq 100 had set new highs after a "spring advance", which suggests the March 2026 signal was another whipsaw for a daily rule — [TTU Sep 2026](https://www.toptradersunplugged.com/trend-following-performance-report-september-2026/)
- **Long-run conditional returns:** S&P 500 annualized returns are a little over 11% when above the 200-day vs 8.56% when below. Another analysis finds SPY's forward returns after 200-day breakdowns are historically positive, which argues against treating a breakdown as a sell signal — [Benzinga (search summary)](https://benzinga.com/z/45406180) [SNIPPET]
- **Whipsaws in multi-asset and dual-momentum models:** GEM had whipsaws in 2011 and 2015–16 between non-US stocks and bonds — [Quant for Free](https://quant4free.com/analysis/dual-momentum/)
- **TAA in 2025:** Q2 2025 suffered from "overly conservative positioning", consistent with being whipsawed out after the April crash — [pulse.bot / Allocate Smartly](https://www.pulse.bot/stock-trading/news/why-taa-is-performing-well-now-outperformance-attribution-e6a9a396-10e3-4333-a41c-9ee43923f9cb/) [SNIPPET]
- **Generic 50/200 crossover backtests on SPY:** less return than buy-and-hold, lower volatility and smaller worst drawdown — [GitHub decgagan/ma-crossover-spy](https://github.com/decgagan/ma-crossover-spy) [INDEPENDENT] [SNIPPET]

### Inferences
- **Net effect 2015–2026:** a lower-return, lower-drawdown trade-off rather than a free lunch. It helped clearly in 2022, and probably in Q4 2018 depending on timing. It hurt in 2016, early 2019, mid-2020, mid-2025 and probably spring 2026. Monthly (10-month) checks reduce the number of whipsaws versus daily 200-day checks, but each whipsaw costs more.
- **For a EUR investor holding S&P 500 or MSCI World UCITS ETFs:** a monthly 10-month filter means roughly one round trip every 1–2 years. In a French CTO account, each exit can realize a taxable gain, which adds a tax drag not captured in US backtests.

### Gaps
- No rigorous public backtest was found that covers exactly 2015–2026, with costs, and with year-by-year whipsaw attribution for a 200-day or 10-month rule. This is best computed directly from daily data.
- No published dates or counts were found for 200-day crossings in 2015–16, 2018 or 2020; only the 2025 and March 2026 events are sourced.
- No EUR-denominated test (e.g., MSCI World in EUR) was found. EUR/USD moves change the signals relative to USD-based studies.

---

## 5. Retail implementation in Europe (UCITS): managed-futures ETFs and building GTAA or Dual Momentum

### Takeaway
As of Nov 2026, a French retail investor on IBKR has **two UCITS ETF routes to trend following**:
1. **iMGP DBi Managed Futures Fund UCITS ETF** (launched Mar 2025 on Euronext Paris; EUR-hedged class added; $698m AUM in Sep 2026; TER about 0.75%). It replicates a basket of CTAs. The US twin DBMF returned +21.6% in 2022 and −8.9% in 2023.
2. **Man Active Trend Enhanced UCITS ETF** (launched 4 Nov 2026). This is MSCI World equity plus a trend overlay, not pure trend. TER about 0.95%. No track record.

GTAA, GEM and Keller-style models can be built by hand from standard UCITS ETFs. No UCITS ETF implements them directly.

### Cited Findings
- **iMGP DBi Managed Futures Fund R USD UCITS ETF:**
  - Announced 17 Mar 2025. Listed on Euronext Paris (ticker DBMF:FP), with a London listing planned.
  - Replicates the **pre-fee** performance of a basket of leading trend-following hedge funds.
  - The US twin DBMF had $1.26bn AUM at the time and was called the world's largest alternative ETF.
  - Source: [HedgeNordic, 17 Mar 2025](https://hedgenordic.com/2025/03/europe-gets-its-managed-futures-ucits-etf-with-imgp-dbi-launch/)
- **EUR-hedged share class (R EUR HP, ticker MFEH):**
  - Added to Euronext Paris (announced 21 Sep 2026), already on Xetra as MFEH:GY. The USD class trades on Xetra and LSE.
  - **UCITS ETF AUM USD 698m** on 18 Sep 2026; the strategy as a whole manages USD 6.59bn.
  - Calls itself "Europe's only managed futures UCITS ETF" (marketing claim).
  - Source: [RankiaPro, 23 Sep 2026](https://rankiapro.com/en/news/imgp-dbi-managed-futures-eur-hedged-etf-euronext-paris/); [iMGP press release](https://www.imgp.com/press-release/europes-only-managed-futures-ucits-etf-now-available-on-deutsche-borse-xetra/) [VENDOR]
- **Share-class identifiers:** the R EUR HP UCITS ETF ISIN is **LU3359622902**, with a listing date shown as 13 May 2026 and TER **0.75%** (third-party listing). The R USD ETF ISIN is **LU2951555585** — [finanzen.at](https://www.finanzen.at/etf/imgp-dbi-managed-futures-r-hp-etf-lu3359622902); [extraETF](https://extraetf.com/it/etf-profile/LU3359622902); [onvista](https://www.onvista.de/etf/IMGP-DBI-MANAGED-FUTURE-ETF-R-US-ETF-LU2951555585) [SNIPPET]
- **Non-ETF UCITS fund share classes** (e.g., R USD LU2572481948, I M LU2550556745, R GBP LU2604833231) predate the ETF. In June 2025 the R GBP class returned +2.8% for the month and −0.3% YTD — [iMGP factsheet](https://www.imgp.com/uploads/factsheets/LU2572481948_FACTSHEETS_EN.pdf); [June 2025 factsheet](https://extranet.imgp.com/api/attachments/preview/FACSHT-2025-06-30-EN-00-2025-07-11-LU2604833231-IMGP_DBI_MANAGED_FUTURES_FUND-R_GBP.pdf) [VENDOR] [SNIPPET]
- **Third-party trailing returns (dates unclear; not comparable across share classes):** R EUR Acc +10.52% YTD and +23.52% over 12 months, with max drawdown 6.84% in June 2025. R USD +27.18% over 1 year to Mar 2026 — [PortfoliosLab DBMFE.PA](https://portfolioslab.com/symbol/DBMFE.PA); [finanzen.at R USD](https://www.finanzen.at/fonds/imgp-dbi-managed-futures-r-lu2572481948) [SNIPPET]
- **DBi strategy record (older DBi page, probably before 2025):** 4.9% annualized since July 2016 vs 2.3% for the SG CTA Index — [iMGP DBi profile](https://www.imgp.com/wp-content/uploads/2024/07/iMGP_DBi_Profile.pdf) [VENDOR] [SNIPPET]
- **US DBMF calendar-year total returns** (best proxy for the UCITS version's behaviour, in USD before hedging): 2020 +1.80%, 2021 +11.49%, 2022 +21.60%, 2023 −8.94%, 2024 +7.24%, 2025 +13.84% — [totalrealreturns](https://totalrealreturns.com/n/DBMF)
- **Man Active Trend Enhanced UCITS ETF (tickers MATE / MAET):**
  - Announced 4 Nov 2026; Central Bank of Ireland authorised.
  - Equity exposure referencing the **MSCI World** plus a quantitative trend-following strategy across global futures.
  - Trades in EUR on **Xetra and Euronext Milan**, and in GBP/USD on LSE. PMs: Russell Korgaonkar and Giuliana Bordigoni.
  - No ISIN, TER or exposure split in the articles. The US versions date from late 2025.
  - Sources: [RankiaPro, 6 Nov 2026](https://rankiapro.com/en/news/man-group-launches-its-first-ucits-etfs-in-europe-featuring-active-trend-following-and-infrastructure-strategies/); [Trustnet, 4 Nov 2026](https://www.trustnet.com/news/13487918/man-group-expands-etf-offering-into-europe-with-two-launches) [VENDOR]
  - Annual costs of **0.95%** per Deutsche Börse listings, as reported in a search summary — [QuotedData, Nov 2026](https://quoteddata.com/2026/11/man-group-brings-trend-following-etf-to-london-as-ai-shares-tumble/) [SNIPPET]
- **No UCITS dual-momentum or GTAA ETF was found;** these must be built by hand — [search result summary; wikifolio example](https://www.wikifolio.com/en/int/w/wfdmglobal)
- **A German wikifolio dual-momentum adaptation** used a bond-market comparison, with 50% USD Treasury 7–10y and 50% EUR govt 7–10y UCITS ETFs as the defensive leg (2020) — [wikifolio](https://www.wikifolio.com/en/int/w/wfdmglobal) [SNIPPET]
- **Core UCITS building blocks confirmed in sources:** iShares Core MSCI World UCITS ETF Acc (IWDA/EUNL/SWDA), ISIN **IE00B4L5Y983**, TER 0.20%. iShares Core MSCI EM IMI UCITS ETF Acc (EIMI), ISIN **IE00BKM4GZ66**, TER 0.18% — [justETF comparison](https://www.justetf.com/en-nl/asset-comparisons/etf-comparisons/IE00B4L5Y983-ishares-core-msci-world-acc-vs-IE00BKM4GZ66-ishares-core-msci-em-imi-acc); [Freenance](https://freenance.io/etf/is-iwda-good-etf-2026-msci-world-developed-markets-vs-vwce-eunl-swda-review/)
- **Costs per Faber:** ETF management fees of 0.03–0.70% for a GTAA build; "many all-ETF portfolios can be formed for approximately 0.05% to 0.50%". Commissions are minimal at 3–4 round trips a year. The system produces many short-term capital losses and mostly long-term gains (a US tax framing) — [Faber JPM 2018](https://allocatortraining.com/wp-content/uploads/2023/06/A-Quantitative-Approach-to-Tactical-Asset-Allocation.pdf)

### Inferences
- **Practical GTAA5 / GEM build from UCITS ETFs.** The ISINs below for everything other than IWDA and EIMI are from general knowledge and were *not* verified in this research; check them on justETF before use.
  - US equity: iShares Core S&P 500 UCITS Acc (CSPX/SXR8, IE00B5BMR087)
  - Developed ex-US or world equity: IWDA (IE00B4L5Y983); EM: EIMI (IE00BKM4GZ66)
  - US Treasuries 7–10y: iShares $ Treasury 7–10yr (IBTM, IE00B1FZS798); or EUR govt: iShares Core € Govt Bond (IEGA, IE00B4WXJJ64)
  - Global REITs: iShares Developed Markets Property Yield (IWDP, IE00B1FZS350)
  - Commodities: iShares Diversified Commodity Swap (ICOM, IE00BDFL4P12)
  - Gold: a physical gold ETC (e.g., Invesco Physical Gold, IE00B579F325)
  - Cash proxy: Xtrackers II EUR Overnight Rate Swap (XEON, LU0290358497)
- **Currency matters.** For a EUR investor, signals computed on USD prices (as in the published backtests) and on EUR-converted prices can differ, especially around large EUR/USD moves. The defensive leg should be EUR cash or EUR short bonds unless the investor wants USD exposure. The EUR-hedged MFEH class removes USD exposure from the trend sleeve.
- **Sizing.** With EUR 10k–200k, a 5-ETF monthly GTAA on IBKR has trivial commission cost: IBKR Europe tiered commissions are a few euros per trade (not verified here). Bid-ask on liquid iShares UCITS ETFs is small. The bigger frictions are French taxation of realized gains in a CTO and the fact that most of these ETFs are not PEA-eligible (not verified in this research).
- **Trend-sleeve choice.** MFEH/DBMF is the only pure, liquid UCITS trend ETF with meaningful AUM. Its replication approach (a factor model of the top-20 CTAs) has tracked the index reasonably. It is a **single-provider dependency**, and its TER (about 0.75%) consumes a meaningful share of expected trend returns (about 3–6%/yr net historically). The Man ETF combines equity beta with trend, so it is not comparable as a pure diversifier.
- **A combined approach** (for example, core MSCI World plus a 10–20% MFEH sleeve, plus an optional monthly GTAA overlay using tranched rebalancing) is supported by the AQR 80/20 evidence and by Allocate Smartly's diversification advice. Whether it beats a plain MSCI World holding in EUR after taxes is not established by any source found.

### Gaps
- No official iMGP factsheet with full calendar-year UCITS returns since March 2025 inception was retrieved.
- No Man Active Trend Enhanced UCITS ISIN or verified TER was found, and no exposure split (for example, 100% equity plus X% trend notional).
- No other UCITS trend funds tradable on IBKR were checked (non-ETF UCITS funds such as Man AHL Trend Alternative, Aspect or Winton UCITS). Their IBKR availability and minimums are unknown.
- PEA eligibility, the French PFU rate for 2026, and IBKR France commission schedules were not verified in this research.
- No UCITS-ETF-based out-of-sample backtest of GTAA or GEM in EUR was found.
