# Equity factor / anomaly strategies after publication and costs, and how to select strategies without overfitting

Research date: 2026-11-10. Investor context: France-based retail, EUR base, Interactive Brokers, long-only, no leverage or shorting, daily or slower data, about €10k–€200k.

**How to read these notes**
- **Evidence windows.** Where possible each finding is tagged:
  - **[IS]**: pre-2015 or in-sample evidence.
  - **[OOS 2015–26]**: post-publication or out-of-sample realized evidence.
- **Author calculations.** Figures marked "(author calc.)" are my own computations from primary data files downloaded on 2026-11-10:
  - Ken French Data Library 5-factor and momentum CSVs, built from the 202609 CRSP file, so data run to Sep 2026.
  - AQR "Betting Against Beta" and "Quality Minus Junk" monthly datasets, data to 31 Aug 2026.
  - MSCI index factsheets dated 30 Oct 2026. MSCI factsheet "turnover" is for the last 12 months. Index data before each launch date is back-tested (MSCI USA Momentum launched 15 Feb 2013).
- **Long-short vs long-only.** Ken French, AQR and academic factor returns are **long-short, gross of costs** and need shorting. MSCI factor indexes are **long-only, net-dividend, before ETF fees and trading costs**. They are the closest proxy for what this investor can capture.

---

## 1. Replication studies: what share of anomalies replicate (especially after excluding microcaps and value-weighting)?

### Takeaway
How many anomalies "replicate" depends heavily on the test method:
- **Hou, Xue & Zhang (2020):** about 65% of 452 anomalies fail a plain t ≥ 1.96 test once microcaps are neutralized (NYSE breakpoints, value-weighting). About 82% fail a multiple-testing hurdle of t ≥ 2.78. Trading-friction and liquidity anomalies almost all fail.
- **Jensen, Kelly & Pedersen (2023):** testing CAPM alphas with capped value-weights, a Bayesian multiple-testing framework and 93 countries, they find about 82–85% of factors replicate. Out of 13 themes, size, seasonality and leverage are the ones that fail.
- **Common ground:** both studies agree that value, momentum, investment/profitability (quality) and low-risk are the robust families. Both also agree that effect sizes are much smaller than originally published.

### Cited Findings
**Hou, Xue & Zhang**
- [IS] Published *RFS* 2020 abstract (33(5):2019–2133):
  - Universe: 452 anomalies. Microcaps are limited via NYSE breakpoints and returns are value-weighted.
  - 65% cannot clear |t| ≥ 1.96, including 96% of the trading-frictions category.
  - At the multiple-testing hurdle of 2.78 the failure rate rises to 82%.
  - Replicated anomalies have economic magnitudes "much smaller than originally reported".
  - Sources: [IDEAS/RePEc RFS record](https://ideas.repec.org/a/oup/rfinst/v33y2020i5p2019-2133..html); summary at [Alpha Architect, "Replicating anomalies"](https://alphaarchitect.com/replicating-anomalies/).
- [IS] NBER working-paper version (w23394, 2017), based on 447 variables. The numbers differ slightly from the published version, so cite the version you use:
  - 286 anomalies (64%) are insignificant at 5%, including 95 of 102 liquidity variables (93%).
  - A t-cutoff of 3 raises insignificance to 380 (85%).
  - Of the 161 significant anomalies, the q-factor model leaves 115 alphas insignificant (150 with t < 3).
  - The paper opens: "The anomalies literature is infested with widespread p-hacking."
  - Source: [NBER w23394 PDF](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf).
- Microcaps are about 60% of the number of NYSE/AMEX/NASDAQ CRSP stocks but only about 3% of total market cap. Much of the anomaly literature's significance came from these stocks. This figure comes from secondary summaries of HXZ surfaced by search; I did not check which of the two pages carries it. Sources: [Alpha Architect](https://alphaarchitect.com/replicating-anomalies/); [CXO Advisory](https://www.cxoadvisory.com/big-ideas/most-stock-anomalies-fake-news/). One commentary argues HXZ mainly re-confirms that anomalies concentrate in micro and small caps.
- [IS] Robust categories in HXZ: value, momentum, investment and profitability tend to replicate. Source: [Alpha Architect summary](https://alphaarchitect.com/replicating-anomalies/).

**Jensen, Kelly & Pedersen**
- Publication: NBER WP 28432, Feb 2021; *Journal of Finance* 78(5):2465–2518, 2023. Scope: 153 factors, 93 countries, 13 themes. Abstract claims: the majority of factors "(1) can be replicated, (2) can be clustered into 13 themes… (3) work out-of-sample in a new large data set covering 93 countries, and (4) have evidence that is strengthened (not weakened) by the large number of observed factors." Sources: [NBER w28432 PDF](https://nber.org/system/files/working_papers/w28432/w28432.pdf); [RePEc record](https://econpapers.repec.org/RePEc:nbr:nberwo:28432).
- How JKP get from HXZ's 35% to their own rates (working paper, Figure 1). Source: [NBER w28432 PDF](https://nber.org/system/files/working_papers/w28432/w28432.pdf).

  | Step | Replication rate |
  |---|---|
  | HXZ headline | 35% |
  | JKP baseline (OLS t on raw returns) | 56.9% |
  | Excluding 34 factors that were insignificant in their own original papers | 64.7% |
  | Testing CAPM alpha instead of raw return | 84.9% |
  | Benjamini–Yekutieli multiple-testing correction | 77.3% |
  | Final, Bayesian with global data | about 84.9% |

  - The baseline gap of 21.9 points decomposes as: longer sample +4.3; using only 1-month holding periods +4.0; capped value-weights +8.5; 15 added factors +2.4; other construction details +2.7.
  - Capped value-weighting means market caps are winsorized at the NYSE 80th percentile.
  - HXZ's own rate falls from 35% to 18% after a multiple-testing correction.
  - With straight (uncapped) value weights, JKP's final rate is 77.3%.
  - For HXZ's "trading frictions" group (4% replication in HXZ), JKP find 63% using CAPM alphas.
- JKP report a replication rate above 75% in 10 of 13 themes. The exceptions are **seasonality, leverage and size**. Source: [NBER w28432](https://nber.org/system/files/working_papers/w28432/w28432.pdf); [AEA 2022 listing](https://www.aeaweb.org/conference/2022/preliminary/paper/inGsbYZh).
- In JKP's ex-post tangency portfolio, 10 of 13 themes get significant positive weight. "Profitability", "investment" and "size" are displaced. Source: [NBER w28432](https://nber.org/system/files/working_papers/w28432/w28432.pdf).
- JKP construction choices: tercile spreads; breakpoints from stocks above the NYSE 20th percentile (non-microcaps); accounting data lagged 4 months. Source: [NBER w28432](https://nber.org/system/files/working_papers/w28432/w28432.pdf). Code and data: https://github.com/bkelly-lab/GlobalFactor (cited in the paper).

**Chen & Zimmermann (Open Source Asset Pricing) and related**
- The open-source dataset reproduces the published predictors; it was published in *Critical Finance Review* 11(2):207–264 (2022). Source: [RePEc record](https://econpapers.repec.org/RePEc:now:jnlcfr:104.00000112).
- Chen & Zimmermann, "Publication Bias and the Cross-Section of Stock Returns" (*RAPS* 2020): the bias from publication selection is "much smaller than post-publication decay (p-value .0001), suggesting mispricing is important". Source: [RePEc RAPS record](https://econpapers.repec.org/RePEc:oup:rasset:v:10:y:2020:i:2:p:249-289.).
- Chen, Lopez-Lira & Zimmermann, "Does peer-reviewed research help predict stock returns?" (search summary, not verified in full text):
  - About 200 published predictors decay by about 50% post-sample.
  - Data-mined accounting-ratio benchmarks show similar out-of-sample performance, so theory adds little over naive backtesting.
  - Risk-based predictors decay about 65% post-publication versus about 50% for mispricing-based ones.
  - Source: [arXiv 2212.10317](https://ar5iv.labs.arxiv.org/html/2212.10317).

**Pre-sample evidence and older summaries**
- [Pre-sample OOS] Linnainmaa & Roberts (*RFS* 2018), using hand-collected accounting data:
  - 28 of 36 accounting anomalies are insignificant in the pre-1963 sample.
  - There is no reliable profitability or investment premium before 1963.
  - Average 1-factor alpha is 0.32%/month in the discovery sample versus 0.13% before and 0.14% after it.
  - Their conclusion: most accounting anomalies are "most likely an artifact of data snooping".
  - Sources: [Linnainmaa & Roberts PDF](https://finance.wharton.upenn.edu/~mrrobert/resources/Publications/anomaliesRFS2017.pdf); [CXO summary](https://cxoadvisory.com/big-ideas/robustness-of-accounting-based-stock-return-anomalies).
- [OOS] "Factor Premia and Factor Timing: A Century of Evidence" (2019, summarized by Alpha Architect): factors exist out of sample but with muted magnitudes. Overfitting may explain about a 30% decline in out-of-sample efficacy. Source: [Alpha Architect, June 2019](https://alphaarchitect.com/2019/06/factor-investing-research-on-steroids/).

### Inferences
- The real disagreement between HXZ and JKP is mostly methodological: raw return vs CAPM alpha, decile vs tercile, holding periods, weighting, and frequentist vs Bayesian handling of multiple tests. Neither study supports trading microcap-driven or liquidity/friction anomalies.
- The families both studies treat as robust (value, momentum, quality/profitability, low-risk/BAB, investment) are also the ones with long-only index and ETF implementations. Size, seasonality and leverage are the weakest themes and should be excluded or deprioritized.
- "Replicates" means "the historical t-stat survives". It does not mean "earns a tradeable premium today". The magnitude question is covered in sections 2–4.

### Gaps
- I used the NBER working-paper version of JKP for the numeric decomposition. Exact numbers in the 2023 *JF* version (the US replication rate is about 82–85% depending on the table) were not verified line by line.
- Chen & Zimmermann's exact post-publication decay statistics come from search-result summaries, not the full papers.

---

## 2. Post-publication decay: how much do anomaly returns shrink, and which families decayed least?

### Takeaway
- **McLean & Pontiff (2016):** across 97 US predictors, returns are about 26% lower out-of-sample (the upper bound on data-mining bias) and about 58% lower after publication.
- **Later estimates of net expected returns:** Chen & Velikov (2023) account for trading costs, publication and the post-2005 trading era together. They find the average anomaly's net expected return is near zero (4–8 bps/month), and only the strongest anomalies or combinations net about 10–20 bps/month.
- **Where decay is largest:** decay is concentrated in the US. Jacobs & Müller find the US is the only country with a reliable post-publication decline.
- **Where decay is smallest:**
  - In the realized 2015–2026 data, momentum and (global) low-risk/quality held up best outside the US.
  - US value, size and investment had zero or negative long-short returns.
  - In McLean–Pontiff, decay was larger for anomalies with large in-sample returns and those in liquid, low-idiosyncratic-risk stocks, i.e. the easiest to arbitrage.

### Cited Findings
**McLean & Pontiff (2016)**
- [IS→OOS] *JF* 71(1), 2016: predictor portfolio returns are 26% lower out-of-sample and 58% lower post-publication. That implies about 32 points (58 − 26) from publication-informed trading. Sources: [JF paper PDF](https://Www.Gwern.net/doc/economics/2016-mclean.pdf); [AFA issue page](https://afajof.org/issue/volume-71-issue-1/).
- Average monthly returns across the 97 portfolios:
  - In-sample: 0.582%.
  - Out-of-sample but pre-publication: 0.402%.
  - Post-publication: 0.264%.
  - Average gap between sample end and publication: 56 months.
  - Source: [McLean & Pontiff PDF](https://Www.Gwern.net/doc/economics/2016-mclean.pdf).
- Heterogeneity in decay:
  - Larger decay for predictors with higher in-sample returns and t-stats.
  - Post-publication returns are lower for predictors concentrated in liquid, low-idiosyncratic-risk stocks.
  - After publication, predictor portfolios become more correlated with other published predictors.
  - Source: [McLean & Pontiff PDF](https://Www.Gwern.net/doc/economics/2016-mclean.pdf).

**Chen & Velikov**
- [OOS + costs] FEDS 2020-039 (first posted Nov 2017; 120 anomalies). The average anomaly's monthly return under progressively stricter assumptions:

  | Assumption | Return, bps/month |
  |---|---|
  | Gross, in-sample | 66 |
  | Net of effective bid-ask spreads | 38 (about 4.6%/yr) |
  | Also post-publication | 13 |
  | Also post-2005 only | 8 |

  - These figures exclude price impact and short-sale fees. Short-sale fees of 10–20 bps/month "would wipe out the remaining profits".
  - The strongest anomalies return only 10–20 bps after data-mining adjustments.
  - Source: [Federal Reserve FEDS PDF](https://www.federalreserve.gov/econres/feds/files/2020039pap.pdf).
- [OOS + costs] Published *JFQA* 58(3), 2023, with 204 anomalies:
  - The average anomaly's net expected return is "a measly 4 bps per month".
  - The strongest anomalies net at best about 10 bps after controlling for data mining.
  - Combinations of anomalies net about 20 bps.
  - Source: [Cambridge JFQA page](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/zeroing-in-on-the-expected-returns-of-anomalies/945133D5A3ECEEAF466AEE91551FD225).

**International and Bayesian evidence**
- [OOS international] Jacobs & Müller (2020), quoted in JKP: "the United States is the only country with a reliable post-publication decline in long-short returns." Source: [JKP NBER w28432](https://nber.org/system/files/working_papers/w28432/w28432.pdf).
- JKP: a positive but attenuated post-publication alpha is what Bayesian learning predicts, not evidence of failure. Factors with higher in-sample alpha generally have higher out-of-sample alpha. Source: [JKP NBER w28432](https://nber.org/system/files/working_papers/w28432/w28432.pdf).

**Ken French US long-short factors (author calc.).** Source: [Ken French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html). Arithmetic annualized mean, Sharpe ratio and t-stat by period:

| Factor | 1963-07 to 2014-12 [IS] | 2000–2014 | 2015-01 to 2026-09 [OOS] |
|---|---|---|---|
| HML (value) | 4.45%/yr, SR 0.46, t 3.32 | 5.09%/yr | −0.69%/yr, SR −0.05, t −0.19 |
| MOM (momentum) | 8.20%/yr, SR 0.56, t 4.02 | 2.03%/yr, SR 0.10 | 3.09%/yr, SR 0.22, t 0.74 |
| RMW (profitability) | 3.17%/yr, SR 0.41, t 2.93 | 5.84%/yr | 2.05%/yr, SR 0.24, t 0.81 |
| CMA (investment) | 3.79%/yr, SR 0.55, t 3.95 | n/a | −0.79%/yr |
| SMB (size) | 3.16%/yr, SR 0.30, t 2.15 | n/a | −2.22%/yr, SR −0.22 |
| Mkt-RF (market) | 6.12%/yr, SR 0.40 | n/a | 11.91%/yr, SR 0.77 |

- Momentum was 10.74%/yr (SR 0.91) over 1963–1999.

**AQR US and international long-short factors (author calc.).** Source: [AQR datasets, Betting Against Beta: Equity Factors, Monthly](https://www.aqr.com/Insights/Datasets/Betting-Against-Beta-Equity-Factors-Monthly) (file includes SMB, HML FF, HML Devil and UMD by country/region). Arithmetic annualized mean by period:

| Factor and region | 1990–2014 [IS] | 2015-01 to 2026-08 [OOS] |
|---|---|---|
| UMD Europe | 11.85%/yr, SR 0.83 | 11.46%/yr, SR 1.10, t 3.74, MDD −19.1% |
| UMD Global ex-US | 8.97%/yr | 9.68%/yr, SR 1.04, t 3.55 |
| UMD France | 9.23%/yr | 11.29%/yr, SR 0.93, t 3.18 |
| UMD USA | 7.29%/yr | 3.57%/yr, SR 0.25, t 0.84 |
| HML FF Global ex-US | 6.68%/yr, t 4.71 | 5.04%/yr, SR 0.68, t 2.31 |
| HML FF Europe | 5.12%/yr | 3.20%/yr, t 1.41 |
| HML FF France | 5.17%/yr | 0.06%/yr |
| HML FF USA | 2.06%/yr | −1.80%/yr |
| HML Devil (timely price) Europe | 3.56%/yr | 0.74%/yr |
| SMB, all of USA / Global ex-US / Europe / France | mixed | −1.2% to −2.5%/yr |

**AQR BAB and QMJ (author calc.).** Sources: [AQR BAB dataset](https://www.aqr.com/Insights/Datasets/Betting-Against-Beta-Equity-Factors-Monthly); [AQR QMJ dataset](https://www.aqr.com/Insights/Datasets/Quality-Minus-Junk-Factors-Monthly).

| Factor and region | Pre-2015 [IS] | 2015-01 to 2026-08 [OOS] |
|---|---|---|
| BAB USA (1957–2014) | 10.40%/yr, SR 0.93, t 7.08 | 4.10%/yr, SR 0.45, t 1.53 |
| BAB Global ex-US | 9.43%/yr | 8.39%/yr, SR 1.24, t 4.23 |
| BAB Europe | 9.97%/yr | 7.89%/yr, SR 0.90 |
| QMJ USA (1957–2014) | 4.15%/yr, SR 0.56 | 2.61%/yr, SR 0.24 |
| QMJ Europe | 5.24%/yr | 5.29%/yr, SR 0.75, t 2.57 |
| QMJ Global ex-US | 6.30%/yr | 4.35%/yr, SR 0.75 |

- QMJ USA calendar years 2024: −9.7%; 2025: −11.3%.

**Long history of momentum**
- Momentum has had seven other decade-long periods of negative returns in data extended back to 1801. One of them was 2004–2013. Source: [Swedroe, "Is 'Momentum' Faltering? Part II", etf.com](https://www.etf.com/sections/index-investor-corner/swedroe-momentum-faltering-part-ii).

### Inferences
- **A planning haircut.** For a published long-short factor, a reasonable planning assumption is a post-publication premium of roughly 40–60% of the in-sample estimate (McLean–Pontiff 58% decline; Chen–Lopez-Lira–Zimmermann about 50%). Net of costs, assume much less, approaching zero for high-turnover or small-cap anomalies (Chen–Velikov).
- **Families that decayed least, 2015–2026:**
  - Momentum outside the US (Europe/France UMD about 11%/yr, SR about 1).
  - Low-risk/BAB outside the US.
  - Quality/QMJ in Europe.
- **Families that decayed most:** US value (HML), size (SMB), investment (CMA) and US BAB/QMJ.
  - This US-vs-rest pattern is consistent with Jacobs & Müller's finding.
  - It is relevant for a EUR investor who can tilt toward European implementations.
- **Statistical power is low.** Even 11–12 years of OOS data gives t-stats around 1–3. The 2015–2026 window alone cannot tell "decayed" apart from "bad luck" for any single factor. Treat it as a realized-experience check, not proof.

### Gaps
- McLean–Pontiff Table IV gives decay by category (event, market, valuation, fundamentals), but the coefficients could not be reliably parsed from the PDF text, so category-level decay percentages are not reported here.
- I did not obtain Jacobs & Müller's full-text numbers directly. The quote comes via JKP.

---

## 3. Realized 2015–2026 performance of the main factors (US, developed and Europe), including the value drawdown, momentum crashes and 2023–2026

### Takeaway
- **Long-short (paper) factors in the US were poor over 2015–2026:**
  - Value: about −0.7%/yr, with a −51% drawdown from Dec 2016 to Sep 2020.
  - Size: −2.2%/yr.
  - Investment: −0.8%/yr.
  - Momentum: +3.1%/yr.
  - Profitability: +2.1%/yr, with sharp losses in 2025–26.
  - The market itself returned about 11.9%/yr in excess of cash.
- **Long-only MSCI factor indexes (what a long-only investor can actually hold):**
  - 2015–2025 vs MSCI World: World Momentum +2.0 pp/yr and World Quality +2.1 pp/yr; World Value −3.1 pp/yr; World Min Vol −3.3 pp/yr.
  - In Europe (EUR): Momentum +3.0 pp/yr; Value and Quality about +0.4 pp/yr; Min Vol −1.1 pp/yr.
- **2025–2026 reversals:**
  - Value came roaring back. MSCI USA Enhanced Value returned +31.9% in 2025 and +44% YTD to Oct 2026, driven by memory and semiconductor stocks.
  - Momentum led H1 2026 but crashed in Jul–Aug and Oct 2026.
  - Quality and low-vol lagged in 2025–26.

### Cited Findings
**Value: the 2017–2020 drawdown and the 2021–2022 recovery**
- Ken French official annual HML (difference of compounded legs), 2015 to 2025: −9.48, +22.80, −13.42, −9.63, −10.36, **−46.94 (2020)**, +25.60, +25.70, −13.98, −8.43, +8.71. Source: [Ken French Data Library, F-F 5 Factors 2x3](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).
- HML peak-to-trough drawdown, compounded monthly long-short (author calc.): **−57.8% from Dec 2006 to Sep 2020**, of which **−51.4% from Dec 2016 to Sep 2020**. Source: [Ken French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).
- BlackRock (vendor) on the value drawdown:
  - Jan 2017 to Jun 2020 was "the worst peak to trough drawdown for value on record" in data back to the 1920s.
  - A later piece puts the trough in Nov 2020, at roughly −55% from peak.
  - Value "had a ripper of a year in 2022".
  - Sources: [BlackRock, Trends in factors](https://www.blackrock.com/us/individual/investment-ideas/what-is-factor-investing/factor-commentary/andrews-angle/trends-in-factors); [BlackRock, The Sleeping Giant: Value's Dormant not Dead](https://www.blackrock.com/ca/investors/en/market-insights/values-dormant-not-dead).
- AXA IM (vendor): after its worst year on record in 2020, value delivered its best quarterly return since 1943 in Q1 2021. Source: [AXA IM](https://www.axa-im-usa.com/investment-strategies/equities/insights/value-returns-bringing-multi-back-multi-factor).
- Research Affiliates (vendor) attributes the whole drawdown to valuation-spread widening between growth and value. It also argues that capitalizing intangibles improves the value measure. Source: [Research Affiliates, "Reports of Value's Death May Be Greatly Exaggerated"](https://originpreprod.researchaffiliates.com/publications/journal-papers/reports-of-values-death-may-be-greatly-exaggerated).
- Long-only relative performance (author calc. from MSCI factsheets):

  | Index | 2017–2020 cumulative vs parent | 2021–2022 vs parent |
  |---|---|---|
  | MSCI USA Value | −27.8% | +15.9% |
  | MSCI World Value | −24.0% | +14.3% |
  | MSCI USA Enhanced Value | −26.4% | n/a |
  | MSCI Europe Enhanced Value | −12.9% | n/a |

  - Sources: [MSCI USA Value factsheet](https://www.msci.com/documents/10199/255599/msci-usa-value-index-usd-net.pdf); [MSCI World Value factsheet](https://www.msci.com/documents/10199/255599/msci-world-value-index-usd-net.pdf); [MSCI USA Enhanced Value factsheet](https://www.msci.com/documents/10199/255599/msci-usa-enhanced-value-index-usd-net.pdf); [MSCI Europe Enhanced Value factsheet](https://www.msci.com/documents/10199/255599/msci-europe-enhanced-value-index-eur-net.pdf).
- AQR (2021) put the value spread above the 90th percentile globally and reported a 0.89 correlation between the spread and future value premiums over 1950–2020. Source: [AQR, "Are Value Stocks Cheap for a Fundamental Reason?"](https://www.aqr.com/Insights/Perspectives/Are-Value-Stocks-Cheap-for-a-Fundamental-Reason).
- A Nov 2025 secondary report quotes Asness putting the spread around the 75th–80th percentile; this is unverified. Source: [Mammoth Times, 10 Nov 2025](https://business.mammothtimes.com/mammothtimes/article/marketminute-2025-11-10-cliff-asness-the-stock-market-is-expensive-not-a-bubble-a-call-for-rationality-in-a-less-efficient-market).

**Momentum crashes**
- [IS] Daniel & Moskowitz, "Momentum Crashes" (NBER w20439; *JFE* 2016):
  - The worst two months for top-minus-bottom-decile momentum were Jul–Aug 1932: losers +232% versus winners +32%.
  - In Mar–May 2009 the loser decile rose +163% while winners gained +8%.
  - Crashes occur in "panic" states after market declines, when volatility is high, and coincide with market rebounds.
  - A dynamic, volatility-scaled momentum strategy "approximately doubles the alpha and Sharpe ratio".
  - Source: [NBER w20439 PDF](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf).
- Ken French MOM monthly figures (author calc.):
  - Apr 2009: −34.36%. Mar–May 2009: −11.80%, −34.36%, −12.54%.
  - Peak-to-trough drawdown −57.8% from Nov 2008 to Sep 2009.
  - Worst months on record: Aug 1932 −52.61% and Jul 1932 −45.63%.
  - Full-history max drawdown since 1927: −78.4% from Jun 1932 to Sep 1939.
  - Source: [Ken French Data Library, Momentum factor](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).
- **November 2020 vaccine rotation:**
  - Ken French MOM returned −12.60% in Nov 2020 and fell −25.4% peak-to-trough from Sep 2020 to Mar 2021 (author calc.).
  - Bloomberg reported "Momentum Trade Plunges the Most on Record in Rotation Frenzy".
  - Some commentators argue it was not a classic momentum crash.
  - Sources: [Ken French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html); [BloombergQuint](https://www.bloombergquint.com/onweb/momentum-trade-plunges-the-most-on-record-in-rotation-frenzy); [Advisor Perspectives, 16 Nov 2020](https://www.advisorperspectives.com/commentaries/2020/11/16/a-look-at-previous-momentum-crashes); [Zawya/Klement](https://www.zawya.com/en/sponsored-content/momentum-crash-warnings-flash-red.-heres-how-you-might-survive-joachim-klement-329261).
- **2026 momentum reversals:**
  - Ken French MOM in 2026: Jan to Jun all positive (Apr +9.51%); then **Jul −12.21%, Aug −5.60%** (−17.1% peak-to-trough, Jun–Aug 2026); Sep +6.70% (author calc.).
  - In Oct 2026 alone, MSCI USA Momentum returned **−10.87% vs −0.99%** for MSCI USA, and MSCI World Momentum −8.33% vs −0.77%.
  - In late July 2026, WisdomTree flagged the winner-loser gap as "very wide by historical standards", implying elevated reversal risk.
  - Sources: [Ken French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html); [MSCI USA Momentum factsheet, 30 Oct 2026](https://www.msci.com/documents/10199/255599/msci-usa-momentum-index-usd-net.pdf); [MSCI World Momentum factsheet](https://www.msci.com/documents/10199/255599/msci-world-momentum-index-usd-net.pdf); [WisdomTree Q2 2026 factor review, 28 Jul 2026](https://www.wisdomtree.com/gb/insights/blog/looking-back-at-equity-factors-in-q2-2026-with-wisdomtree).

**Long-only MSCI factor indexes vs parent.** Net returns as of 30 Oct 2026, before ETF fees. 2015–2025 CAGR difference and years beating the parent are author calculations from the factsheet annual tables. Sources: the MSCI factsheets linked in the table.

| Index | 2015–25 CAGR vs parent | Yrs beat (of 11) | 10y ann. to Oct-2026 vs parent | 10y Sharpe vs parent | 12m turnover | Max DD (since inception) |
|---|---|---|---|---|---|---|
| [MSCI USA Momentum](https://www.msci.com/documents/10199/255599/msci-usa-momentum-index-usd-net.pdf) | 13.25% vs 12.91% (+0.34pp) | 7 | 14.75% vs 14.86% | 0.70 vs 0.81 | 112.7% | −56.2% (Dec 2007–Mar 2009) |
| [MSCI USA Quality](https://www.msci.com/documents/10199/255599/msci-usa-quality-index-usd-net.pdf) | 14.59% vs 12.91% (+1.68pp) | 7 | 16.54% vs 14.86% | 0.92 vs 0.81 | 21.7% | −44.6% vs −55.4% |
| [MSCI USA Enhanced Value](https://www.msci.com/documents/10199/255599/msci-usa-enhanced-value-index-usd-net.pdf) | 8.64% vs 12.91% (−4.27pp) | 5 | 13.86% vs 14.86% | 0.64 vs 0.81 | 36.3% | −60.0% |
| [MSCI USA Min Vol](https://www.msci.com/documents/10199/255599/msci-usa-minimum-volatility-index-usd-net.pdf) | 9.46% vs 12.91% (−3.46pp) | 3 | 10.27% vs 14.86% | 0.65 vs 0.81 (vol 12.3% vs 15.6%) | 20.4% | −47.2% |
| [MSCI USA Diversified Multiple-Factor](https://www.msci.com/documents/10199/255599/msci-usa-diversified-multiple-factor-index-usd-net.pdf) | 10.69% vs 12.91% (−2.23pp) | 3 | 13.41% vs 14.86% | 0.71 vs 0.81 | 40.5% | −56.7% |
| [MSCI World Momentum](https://www.msci.com/documents/10199/255599/msci-world-momentum-index-usd-net.pdf) | 12.88% vs 10.92% (+1.97pp) | 8 | 14.88% vs 12.95% | 0.77 vs 0.73 | 114.7% | −55.8% |
| [MSCI World Quality](https://www.msci.com/documents/10199/255599/msci-world-quality-index-usd-net.pdf) | 12.99% vs 10.92% (+2.08pp) | 7 | 14.78% vs 12.95% | 0.83 vs 0.73 | 25.5% | −48.4% vs −57.8% |
| [MSCI World Value (style)](https://www.msci.com/documents/10199/255599/msci-world-value-index-usd-net.pdf) | 7.87% vs 10.92% (−3.05pp) | 3 | 10.42% vs 12.95% | 0.58 vs 0.73 | 28.3% | −61.2% |
| [MSCI World Value Weighted (gross)](https://www.msci.com/documents/10199/255599/msci-world-value-weighted-index.pdf) | 10.68% vs 11.49% (−0.81pp) | 4 | 13.15% vs 13.50% | 0.72 vs 0.76 | 20.0% | −61.6% |
| [MSCI World Min Vol (USD, gross)](https://www.msci.com/documents/10199/255599/msci-world-minimum-volatility-index.pdf) | 8.21% vs 11.49% (−3.28pp) | 4 | 8.70% vs 13.50% | 0.58 vs 0.76 | 20.5% | −47.7% |
| [MSCI World Min Vol (EUR)](https://www.msci.com/documents/10199/255599/msci-world-minimum-volatility-index-eur-net.pdf) | 8.13% vs 11.22% (−3.08pp) | 3 | 8.16% vs 12.74% | 0.74 vs 0.90 | 20.4% | −39.9% vs −53.4% |
| [MSCI Europe Momentum (EUR)](https://www.msci.com/documents/10199/255599/msci-europe-momentum-index-eur-net.pdf) | 10.75% vs 7.73% (+3.02pp) | 8 | 11.37% vs 9.37% | 0.89 vs 0.68 | 104.9% | −59.5% (2000–03) |
| [MSCI Europe Quality (EUR)](https://www.msci.com/documents/10199/255599/msci-europe-quality-index-eur-net.pdf) | 8.13% vs 7.73% (+0.40pp) | 6 | 9.16% vs 9.37% | 0.66 vs 0.68 | 17.7% | −50.3% |
| [MSCI Europe Enhanced Value (EUR)](https://www.msci.com/documents/10199/255599/msci-europe-enhanced-value-index-eur-net.pdf) | 8.12% vs 7.73% (+0.39pp) | 5 | 10.26% vs 9.37% | 0.64 vs 0.68 | 24.0% | −62.3% |
| [MSCI Europe Min Vol (EUR)](https://www.msci.com/documents/10199/255599/msci-europe-minimum-volatility-index-eur-net.pdf) | 6.61% vs 7.73% (−1.12pp) | 3 | 7.82% vs 9.37% | 0.68 vs 0.68 | 20.0% | −50.5% |
| [MSCI World Small Cap (gross)](https://www.msci.com/documents/10199/255599/msci-world-small-cap-index.pdf) | n/a | n/a | 10.62% vs 12.63% (ACWI IMI) | 0.51 vs 0.71 | n/a | −61.1% |

**Calendar-year and YTD detail**
- Defensive factors in 2022, a down market:
  - MSCI USA Min Vol −9.67% vs −19.85%; MSCI World Min Vol (EUR) −4.74% vs −12.78%.
  - MSCI USA Quality −22.97%, worse than the market.
- Value in 2025 and 2026:
  - MSCI USA Enhanced Value: 2025 +31.85% vs +17.31%; 1-yr to Oct 2026 +51.67% vs +11.21%; YTD 2026 +44.00% vs +11.24%.
  - Its forward P/E is 8.85 vs 18.70 for MSCI USA.
  - MSCI Europe Enhanced Value 2025: +34.68% vs +19.39% (EUR).
  - Sources: [MSCI USA Enhanced Value factsheet](https://www.msci.com/documents/10199/255599/msci-usa-enhanced-value-index-usd-net.pdf); [MSCI Europe Enhanced Value factsheet](https://www.msci.com/documents/10199/255599/msci-europe-enhanced-value-index-eur-net.pdf).
- Profitability (Ken French RMW): 2025 −10.85% (official annual); Jan–Sep 2026 −12.6% (author calc.); drawdown −25.9% from Oct 2023 to Jun 2026. Source: [Ken French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).

**2026 commentary (vendors)**
- WisdomTree (vendor), H1 2026 review, 28 Jul 2026, using MSCI factor indexes:
  - Q2 2026 outperformance: US Momentum +31.4%; EM Momentum +40.7%; US Value +26.3%; World Value +16.1%.
  - Value YTD: World 24.2%, Europe 4.5%. Size YTD: US +12.7%, World +6.9%.
  - YTD in Europe: Momentum −0.5%, Quality −3.0%.
  - Min Vol and High Dividend gave back their Q1 gains.
  - Value's strength partly reflects heavy weights in Micron, SK Hynix and Samsung.
  - Long-run Ken French data (1963–2026): Quality beat the market in 74% of rolling 3-year periods and 89% of rolling 10-year periods. Value, low-vol and high-dividend beat it in about 57–63% of 3-year periods; small caps in 48%.
  - Source: [WisdomTree](https://www.wisdomtree.com/gb/insights/blog/looking-back-at-equity-factors-in-q2-2026-with-wisdomtree).
- Morningstar Indexes Q2 2026: momentum reclaimed top spot and leads YTD; the Global Low Volatility index was the weakest factor in Q2; quality was the weakest factor in Q1 2026. Source: [Morningstar Indexes Q2 2026 review](https://indexes.morningstar.com/insights/markets-review/blt49b23cb4e87c0d8d).
- Counterpoint, YTD to 11 Mar 2026: the North American low-risk stability factor was the worst factor globally at −13.13%. Source: [Counterpoint, Mar 2026 PDF](https://counterpointfunds.com/wp-content/uploads/2026/03/Momentum-Leads-While-Defensive-Factors-Lag-YTD-March-2026.pdf).
- Cboe Canada, May 2025: momentum had the best YTD performance and quality the worst. Source: [Cboe Canada](https://etfmarket.cboe.com/canada/en/news/factor-investing-in-focus-what-etfs-say-about-mark).

### Inferences
- **Long-only results can differ in sign from paper factors.**
  - Long-only US/World Quality beat the market over 2015–2025 while US long-short RMW and QMJ were weak. This suggests the long-only quality edge came largely from overweighting mega-cap tech and growth, a market-structure tilt, rather than the long-short quality premium.
  - Long-only Value lagged badly in the US even though Value was positive outside the US on a long-short basis.
- **What has worked most consistently for a EUR long-only investor:**
  - Momentum in Europe and World (+2–3 pp/yr, beat its parent in 8 of 11 years). But it has about 105–115% annual index turnover and brutal crash risk (Apr 2009 −34% in a month long-short; Oct 2026 −10% relative in a month long-only).
  - Quality, which acts as a lower-drawdown core (max DD −44% to −48% vs −55% to −58% for the market).
- **Min Vol and Low-Vol** lagged in every region during the 2015–2026 bull market. They delivered as designed in 2022: −9.7% vs −19.9% in the US, with roughly 0.62–0.72 beta. Their value is risk reduction, not excess return.
- **Multi-factor (MSCI USA DMF)** underperformed by −2.2 pp/yr over 2015–2025, which shows that "diversified" factor tilts do not guarantee a positive tilt return over a decade.
- **Size (small caps)** has had a negative premium since 2015 in all regions tested. That is consistent with JKP's finding that size fails replication.

### Gaps
- The MSCI World Enhanced Value and MSCI World Diversified Multi-Factor factsheets returned 404 under the URL pattern used. World value figures therefore use MSCI World Value (style) and Value Weighted instead.
- No full-year 2026 numbers exist yet. Ken French data end Sep 2026, AQR Aug 2026, MSCI 30 Oct 2026.
- Dimensional, Research Affiliates and Alpha Architect 2015–2026 realized summaries were not retrieved. These notes rely on primary data instead.
- No verified 2026 AQR value-spread percentile was found.

---

## 4. Gap between paper factor returns and investable (long-only, ETF) returns; which factors survive costs at retail scale; shorting vs long-only

### Takeaway
- **Trading costs:** Novy-Marx & Velikov (2016) show costs cut realized spreads by roughly ≥1% of one-sided monthly turnover.
  - Anomalies with less than 50%/month turnover (value, profitability, investment, net issuance, and momentum when cost-mitigated) can survive.
  - Few high-turnover anomalies survive.
  - Value + momentum + profitability combined was the best net strategy (99 bps/month, t 5.18, in-sample).
  - Equal-weighted versions cost 2–3 times more.
- **The long side carries most of the premium for the main factors:** almost all of size, about 60% of value and about half of momentum (Israel & Moskowitz 2013). Long-only capture is therefore feasible but captures less than the paper long-short premium, and comes with full market beta.
- **BAB as published** relies on leverage plus near-equal weighting of tiny stocks. A long-only Min Vol index is a different, weaker product.
- **For a retail investor at €10k–€200k:** factor UCITS ETFs cost about 0.25%/yr TER. Self-built portfolios of liquid large and mid caps with annual or quarterly rebalancing and buy/hold bands are the realistic way to implement.

### Cited Findings
**Novy-Marx & Velikov (2016)**
- [IS] "A Taxonomy of Anomalies and Their Trading Costs" (*RFS* 29(1), 2016; NBER w20721, 2014). Source for all bullets in this group: [Novy-Marx & Velikov PDF](https://mysimon.rochester.edu/novy-marx/research/ToAatTC.pdf); [NBER w20721](https://www.nber.org/papers/w20721).
  - Round-trip costs for typical value-weighted strategies average over 50 bps.
  - Costs reduce realized spreads by more than 1% of monthly one-sided turnover. A strategy whose long side turns over 20% a month loses at least 20 bps/month.
  - Equal-weighted strategies' costs are generally 2–3 times higher.
  - A buy/hold spread (stricter rules to enter a position than to keep it) is the most effective cost mitigation.
- Results by turnover group, same source:
  - **Low-turnover strategies** (annual rebalancing): costs are often under 10 bps/month.
  - **Mid-turnover strategies** (14–35% monthly turnover per side): costs of 20–57 bps/month, often more than half the gross spread. Only net issuance, PEAD (CAR3), momentum and its combinations (ValMom, ValMomProf) are significant net.
  - The best net strategy, combining value, momentum and gross profitability, earns **99 bps/month net (t 5.18)**, up from 51 bps for value+momentum alone.
  - **High-turnover strategies** (more than 90%/month) cost more than 1%/month. Only 2 have significant net returns: industry-momentum/reversal combos and low-volatility industry-relative reversals.
  - Idiosyncratic volatility and distress are only marginally profitable net.
- Capacity, same source:
  - Size and profitability could absorb more than $100bn per side; value about half that.
  - Momentum's profitability disappears at about $5bn per side.
  - High-frequency strategies have capacity of only a few hundred million.
  - Many strategies stay significant at t > 2 net of costs, but "far fewer" at t > 3.
- Alpha Architect summary: "Trading costs destroy factor investing?" (May 2017). Source: [Alpha Architect](https://alphaarchitect.com/2017/05/trading-costs-destroy-factor-investing/).

**Chen & Velikov**
- Short-sale fees average 10–20 bps/month and would wipe out the average anomaly's remaining net return. That return is already only about 8 bps/month after spreads, publication effects and the post-2005 period. Source: [Chen & Velikov FEDS 2020-039](https://www.federalreserve.gov/econres/feds/files/2020039pap.pdf).

**Long side vs short side**
- [IS] Israel & Moskowitz (*JFE* 108(2), 2013), 86 years of US data plus about 40 years of international data:
  - The long side provides almost all of size, 60% of value and half of momentum profits.
  - The value premium decreases with firm size and is weak among the largest stocks; momentum shows no reliable relation with size.
  - There is little evidence that the premiums changed with trading costs or institutional ownership over time.
  - Sources: [RePEc JFE record](https://econpapers.repec.org/RePEc:eee:jfinec:v:108:y:2013:i:2:p:275-301); [Swedroe summary, etf.com](https://www.etf.com/sections/index-investor-corner/swedroe-look-ways-3-factors-work).
- Robeco (vendor research note, Dec 2019), "When equity factors drop their shorts": the long side of factor strategies performs more strongly and "subsumes the shorts". It suggests hedging the market beta of a long-only factor portfolio with index derivatives instead of shorting stocks; that option is not available to this investor. Source: [Robeco PDF](https://cdn.uc.assets.prezly.com/deef963e-b0fa-4559-a792-26423840ff32/-/inline/no/20191210%20GB%20When%20equity%20factors%20drop%20their%20shorts.pdf).

**Betting against beta**
- Novy-Marx & Velikov, "Betting Against Betting Against Beta" (*JFE* 143(1), 2022):
  - BAB's performance is driven by non-standard procedures that "effectively, but non-transparently, equal weight stock returns".
  - Per dollar invested, BAB commits on average $1.05 to stocks in the bottom 1% of market cap.
  - Biased beta estimation drives the supporting evidence.
  - Secondary summaries say transaction costs cut BAB profitability by almost 60%, and a value-weighted BAB still earns about 56 bps/month; these two figures are not verified against the paper.
  - Sources: [RePEc JFE record](https://econpapers.repec.org/RePEc:eee:jfinec:v:143:y:2022:i:1:p:80-106); [working paper PDF](https://mysimon.rochester.edu/novy-marx/research/BABAB.pdf); [Alpha Architect](https://alphaarchitect.com/?p=72472); [Quantpedia](https://quantpedia.com/biased-betting-against-beta/).

**Paper vs product returns**
- Research Affiliates (vendor), "The Incredible Shrinking Factor Return" (2017):
  - Compared 1991–2016 mutual fund factor exposures with paper long-short factors and found substantial slippage.
  - It attributes the slippage to trading costs, missed trades, illiquid stocks, shorting costs and commissions.
  - Newfound Research disputes the regression method, saying it biases the estimate.
  - Sources: [Research Affiliates](https://originpreprod.researchaffiliates.com/publications/articles/601-the-incredible-shrinking-factor-return); [etf.com summary](https://www.etf.com/sections/news/research-affiliates-incredible-shrinking-factor-return); [Newfound critique via Advisor Analyst](https://advisoranalyst.com/?p=90198).
- SKKU working paper (2018), Bayesian study: investors should be skeptical of smart-beta ETFs' ability to capture factor premiums. Long-only construction "hinders their ability to capture full factor premiums". Source: [SKKU WP 2018-05](https://sier.skku.edu/_res/sier/etc/WP_2018-05.pdf).
- FactorResearch-sourced piece: the long-short value factor outperformed its smart-beta version, and low volatility shows the largest gap between smart-beta excess returns and factor returns. Source: [etf.com](https://www.etf.com/node/95640.md).

**UCITS factor ETF costs (EUR investor)**
- iShares Edge MSCI World Momentum Factor UCITS ETF (IE00BP3QZ825): TER 0.25%. Source: [extraETF](https://extraetf.com/etf-profile/IE00BP3QZ825).
- iShares Edge MSCI World Quality Factor: 0.25% (one aggregator shows 0.26%). Source: [Hargreaves Lansdown](https://www.hl.co.uk/shares/shares-search-results/BP3QZ71).
- iShares Edge MSCI World Value Factor: 0.25%. Source: [finanzfluss](https://www.finanzfluss.de/informer/fonds/ie00bp3qzb59/).
- Xtrackers MSCI World Momentum 1C: ongoing charges 0.25% (FY2023 KIID). Source: [DWS KIID](https://etf.dws.com/en-gb/AssetDownload/Index/e9ff1744-7e4c-42d2-8464-ddf9001a92ad/DWS-UKKIID-IE00BL25JP72-GB-en-2024-02-15.pdf).
- Index turnover drives hidden trading costs inside these ETFs (MSCI factsheets, last 12 months):

  | Index family | Annual turnover |
  |---|---|
  | Momentum (USA 112.7%, World 114.7%, Europe 104.9%) | about 105–115% |
  | Enhanced Value | 24–36% |
  | Quality | 18–25% |
  | Min Vol | about 20% |
  | MSCI USA Diversified Multiple-Factor | 40.5% |

  Source: [MSCI factsheets](https://www.msci.com/documents/10199/255599/msci-world-momentum-index-usd-net.pdf).

### Inferences
- **Which factors need shorting?**

  | Factor | Paper premium needs shorting? | Long-only capture |
  |---|---|---|
  | Value, profitability/quality, investment | Yes | Partial: the long leg carries most of the premium |
  | Momentum | Yes | Partial: about half the premium is on the long side; momentum also has crash risk on the long side |
  | BAB | Yes, plus leverage | Not capturable as published; Min Vol / Low-Vol is only a weak substitute |
  | Size | Yes | Nothing to capture recently: the premium was negative 2015–2026 |

- **Rough cost of self-implemented momentum.** A self-built long-only portfolio of liquid large and mid caps (IBKR) rebalanced monthly at about 100% annual turnover, with an assumed 10–30 bps round-trip all-in cost (spread plus commission), would cost roughly 0.1–0.3%/yr. That is comparable to an ETF TER.
  - The bigger risks for a small account are the fixed minimum commissions per ticket and the concentration needed to keep ticket count low.
  - This is an estimate; IBKR fee specifics are outside this note's scope.
- **Design rules from Novy-Marx & Velikov for a retail build:**
  - Value-weight or cap-tilt rather than equal-weight.
  - Exclude microcaps (for example, below the NYSE 20th percentile or a €1–2bn floor).
  - Use annual or quarterly rebalancing for value, quality and profitability.
  - Use buy/hold bands (for example, buy in the top 10%, hold until the stock drops out of the top 20–30%) for momentum.
- **What a realistic long-only tilt can add.** Based on 2015–2026 MSCI evidence and the long-short haircuts above, expect about 0 to +2 pp/yr before ETF fees for the best long-only tilts (momentum and quality in World/Europe). Tracking error is about 4–9%/yr, and multi-year relative drawdowns of 15–40% are possible. Expected net excess return per unit of tracking error is therefore modest, an information ratio of roughly 0.1–0.3.

### Gaps
- I found no rigorous study quantifying realized UCITS factor ETF returns against their MSCI indexes (tracking difference) for 2015–2026.
- PEA eligibility of factor ETFs and French tax treatment were not researched. Most MSCI World factor UCITS ETFs are Irish-domiciled and likely not PEA-eligible; this needs verification.
- I did not quantify costs at €10k–€200k scale on IBKR (minimum commission per order, FX conversion costs EUR→USD). Another research thread should cover this.

---

## 5. Selection methodology: multiple testing, deflated Sharpe ratio, PBO, minimum backtest length, walk-forward. Concrete rules for a retail researcher

### Takeaway
- **Harvey, Liu & Zhu (2016):** given more than 300 published factors, a new factor needs t > 3.0, not 2.0.
- **Bailey, Borwein, López de Prado & Zhu (2014):** the expected maximum Sharpe ratio of skill-less strategies grows with the number of trials. With 5 years of data, trying only 45 independent configurations is enough to "find" an in-sample annualized Sharpe ratio of 1.0 with an expected out-of-sample Sharpe ratio of 0.
- **Tools to use:** Bailey & López de Prado's Deflated Sharpe Ratio, the Probability of Backtest Overfitting via CSCV, and Harvey & Liu's Sharpe haircuts. All of them require recording every trial.
- **Implication for this investor:** factor Sharpe ratios are about 0.2–0.6, so honest backtests need decades of data and a very small, pre-specified set of hypotheses.

### Cited Findings
**Harvey, Liu & Zhu (2016)**
- "…and the Cross-Section of Expected Returns" (*RFS* 29(1):5–68, 2016; NBER w20592):
  - Catalogues at least 316 factors (some summaries say 315).
  - "A newly discovered factor needs to clear a much higher hurdle, with a t-ratio greater than 3.0."
  - "It does not make any economic or statistical sense to use the usual significance criteria for a newly discovered factor, e.g., a t-ratio greater than 2.0."
  - Sources: [NBER w20592](https://nber.org/papers/w20592); [CXO summary](https://www.cxoadvisory.com/big-ideas/taming-the-factor-zoo/).
  - A third-party doc citing 3.4 and 3.78 thresholds does not match the paper; do not rely on it.

**Harvey & Liu, "Backtesting"**
- Proposes a multiple-testing haircut for any reported Sharpe ratio and a profit hurdle. Source: [Duke PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF); [CME Group copy](https://www.cmegroup.com/content/dam/cmegroup/education/files/backtesting.pdf).
  - "It is a serious mistake to use the rule of thumb 50% haircut."
  - The haircut is nonlinear: the highest Sharpe ratios are only moderately penalized, while marginal Sharpe ratios are heavily penalized.
  - The method needs an assumed number of prior tests; the paper uses HLZ's at least 315 factors.
  - R code for the haircut exists in the quantstrat sandbox: [rdrr.io](https://rdrr.io/github/marsanul/quantstrat/man/SharpeRatio.haircut.html).

**Bailey, Borwein, López de Prado & Zhu (2014), "Pseudo-Mathematics and Financial Charlatanism"** (Notices of the AMS; PDF dated 1 Apr 2014). Source for all bullets in this group: [PDF](https://carmamaths.org/jon/backtest.pdf).
- **MinBTL (Minimum Backtest Length), in years:**
  - MinBTL ≈ [((1−γ)·Z⁻¹(1−1/N) + γ·Z⁻¹(1−1/(N·e))) / E[max_N]]², where γ is the Euler–Mascheroni constant.
  - Simple upper bound: **MinBTL < 2·ln(N) / E[max_N]²**.
  - It is "a necessary, non-sufficient condition to avoid overfitting".
- **Numerical examples:**
  - With 5 years of data, no more than 45 independent configurations should be tried, otherwise an in-sample Sharpe ratio of 1 with an expected out-of-sample Sharpe ratio of 0 is almost guaranteed.
  - With a 2-year backtest, only 7 trials give an expected maximum in-sample Sharpe ratio of 1.
  - A strategy with 7 binary parameters (2⁷ = 128 trials) has an expected maximum Sharpe ratio above 2.6 on noise.
  - With 20 trials, one specification is expected to pass a 5% Akaike information criterion (AIC) overfitting test by chance.
- "A researcher that does not report the number of trials N used to identify the selected backtest configuration makes it impossible to assess the risk of overfitting."
- Technical-analysis filters, neural networks and kernel estimators warrant extra caution.
- If trials are correlated, estimate the effective N via PCA. Assuming independence is conservative.

**Deflated Sharpe Ratio**
- Bailey & López de Prado, "The Deflated Sharpe Ratio" (*JPM* 40(5), 2014). Source for all bullets in this group: [SSRN 2460551](https://papers.ssrn.com/abstract=2460551); [PDF](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf).
- **What it corrects:** the DSR corrects for "selection bias under multiple testing and non-Normally distributed returns".
- **How it works:** it is a Probabilistic Sharpe Ratio whose benchmark is the expected maximum Sharpe ratio given N trials and the variance of the trials' Sharpe ratios.
- **Inputs it needs:** the number of independent trials N, the variance of trial Sharpe ratios, the sample length T, and skewness and kurtosis.
- **The paper's worked example:**
  - Setup: a strategy with an annualized Sharpe ratio of 2.5 over 5 years of daily data (T = 1250), chosen among many configurations, with negatively skewed, fat-tailed returns.
  - Result: DSR ≈ 0.90, below 0.95, so it was rejected.
  - Had it been found after only N = 46 independent trials, DSR = 0.9505 and it would have passed.
  - With Normal returns, it would have passed up to N = 88.
  - The exact N, variance, skewness and kurtosis in the example are garbled in the PDF text extraction.

**Probability of Backtest Overfitting**
- Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting" (*J. Computational Finance* 20(4), 2017). It estimates PBO non-parametrically via combinatorially symmetric cross-validation (CSCV): split the data into S blocks, form all combinations of half for in-sample and half for out-of-sample, and measure how often the in-sample-best configuration ranks below the median out-of-sample. Sources: [SSRN 2326253](https://papers.ssrn.com/abstract=2326253); [Bailey overfit tools](https://www.davidhbailey.com/dhbpapers/overfit-tools-at.pdf).
- The plain hold-out method "does not take into account the number of trials". Source: [Pseudo-Mathematics PDF](https://carmamaths.org/jon/backtest.pdf).

**Backtesting protocol and other guardrails**
- Arnott, Harvey & Markowitz, "A Backtesting Protocol in the Era of Machine Learning" (*J. Financial Data Science* 1(1):64–74, 2019; SSRN Nov 2018). Seven-point protocol, starting with a prior economic hypothesis before testing. It also notes that financial datasets are small relative to machine-learning data needs. Sources: [SSRN 3275654](https://papers.ssrn.com/abstract=3275654); [CXO summary](https://www.cxoadvisory.com/?p=31829); [Alpha Architect summary](https://alphaarchitect.com/protocol-to-prevent-quants-gone-wild/).
- Linnainmaa & Roberts recommend testing models on out-of-sample (pre-sample) data. Where that is not feasible, check whether a model explains half of the in-sample alpha, a natural haircut. Source: [CXO summary](https://cxoadvisory.com/big-ideas/robustness-of-accounting-based-stock-return-anomalies).

### Inferences
**Concrete rules for a retail researcher.** These are synthesized from the sources above. The numerical examples are author calculations using the MinBTL bound.

1. **Restrict the hypothesis space before touching data.**
   - Only test factor families with replicated, multi-country, post-publication evidence: momentum, value, quality/profitability, low-risk; investment is weak post-2015.
   - Exclude size, seasonality, leverage, liquidity/friction, microcap-driven and short-horizon reversal anomalies (HXZ and JKP failures; costs).
   - Write the rule definitions, universe, rebalance frequency and cost model down first, as in Arnott-Harvey-Markowitz.
2. **Count every trial.**
   - Log every parameter combination, universe and look-back tried, including informal "quick looks".
   - Collapse highly correlated variants via PCA or clustering to get an effective N.
   - Literature-mined ideas inherit the literature's trials: HLZ's at least 316 factors is why the t > 3 hurdle applies to any "new" signal.
3. **Apply the MinBTL bound.** Years needed ≈ 2·ln(N)/SR², where SR is the in-sample annualized Sharpe ratio you are claiming. Author calculations:

   | Trials N | Target annual SR | Years of data needed |
   |---|---|---|
   | 10 | 0.5 | about 18 |
   | 20 | 1.0 | about 6 |
   | 100 | 0.5 | about 37 |
   | 10 | 0.3 (typical long-short factor) | about 51 |

   - Daily data does not shorten this: MinBTL is in years.
   - Implication: use the longest histories available (Ken French US from 1926/1963, AQR international from about 1990, MSCI from 1994–1998). Keep N in single digits.
4. **Significance hurdle.**
   - Require t ≥ 3 (equivalently, full-sample SR × √years ≥ 3) for any novel signal.
   - For an established factor, a t of about 2 is acceptable only with out-of-sample confirmation in other regions or periods.
   - Report the DSR and require DSR ≥ 0.95 using the actual N, the variance of trial Sharpe ratios, and skewness and kurtosis; momentum is strongly negatively skewed.
5. **Out-of-sample design.**
   - (a) Keep a true hold-out, for example the last 5 years plus one untouched region such as Europe or Japan, and look at it once.
   - (b) Use walk-forward or expanding-window estimation for any fitted parameter.
   - (c) Run CSCV to estimate PBO and reject if PBO is above about 0.2–0.3. This threshold is a judgement call; the papers give no universal cutoff.
   - (d) Run pre-sample and cross-country tests: a US-discovered rule should also work in Europe (AQR or JKP country data).
6. **Haircut before sizing expectations.**
   - Assume a post-publication premium of about 40–60% of the backtest, and subtract costs at 1× one-sided turnover per month (Novy-Marx & Velikov).
   - Subtract the ETF TER (about 0.25%) or own trading costs.
   - Never extrapolate a backtest Sharpe ratio above about 1 for a single long-only equity factor tilt.
   - Realized 2015–2026 long-only excess returns were about −4.6 to +3.0 pp/yr.
7. **Evaluate on relative-drawdown tolerance, not just CAGR.**
   - Plan for 3–4-year relative drawdowns of 25–30% for long-only value (2017–2020) and about 50–58% for long-short value (2006/2016–2020).
   - Plan for one-month momentum losses of 10–35%.
   - Decide in advance what evidence would cause abandonment, so you neither capitulate at the bottom nor keep re-optimizing (re-optimizing silently increases N).
8. **Prefer simple, combined, low-turnover implementations.**
   - Combining value, momentum and profitability was the best net-of-cost strategy in Novy-Marx & Velikov.
   - Use volatility scaling or crash filters for momentum only if specified ex ante (Daniel & Moskowitz). Each added filter increases N.
9. **Be careful with vendor material.** MSCI, BlackRock, WisdomTree, Research Affiliates, AQR and Robeco all sell factor products. Index histories before launch dates (for example MSCI USA Momentum before Feb 2013) are back-tests, and survivorship applies to which indexes and ETFs still exist.

### Gaps
- No universal PBO threshold is published. The 0.2–0.3 suggestion above is a practitioner judgement, not sourced.
- I could not extract the exact DSR example parameters from the PDF text.
- I found no source that sets a minimum backtest length specifically for daily-rebalanced retail equity strategies beyond the general MinBTL formula.
