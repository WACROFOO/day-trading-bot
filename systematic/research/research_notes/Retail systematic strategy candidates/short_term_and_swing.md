# Short-horizon systematic, calendar/seasonal and options-income strategies: post-publication and net-of-cost evidence (as of Nov 2026)

Scope note: notes compiled 2026-11-10. Gross vs net is called out explicitly for each figure. "Vendor" means the author sells courses, signals, software or funds tied to the strategy. The investor context throughout is a France-based retail account at Interactive Brokers: EUR base, UCITS ETFs only (US-domiciled ETFs such as SPY/QQQ blocked by PRIIPs; US single stocks and US-listed options allowed), long-only, no leverage, end-of-day decisions, €10k–€200k.

## Q1. Index/ETF mean reversion (Connors RSI(2), IBS, "buy after down days" on SPY/QQQ): original results vs since publication

### Takeaway
The daily mean-reversion edge on US index ETFs still shows up after publication, but it is smaller. The best dated independent-style test (Oct 2026) finds RSI(2) on SPY fell from Sharpe 0.97 before the 2008 book to 0.68 afterwards, below buy-and-hold's 0.87 over the same post-2009 years. The strategy is in the market only ~11% of the time, earns ~5% CAGR vs ~11% for SPY, and trailed badly in 2023–2026. Its value now is as a low-exposure, low-drawdown sleeve or overlay, not as a source of alpha over buy-and-hold. The evidence for IBS is mostly vendor or anecdotal.

### Cited Findings
- **RSI(2) on SPY, pre vs post publication (practitioner replication, Oct 2026).** Rules: buy at the close when RSI(2) < 10 and close > 200-day SMA; sell at the close when close > 5-day SMA; no stop; cash earns 0. Data: Yahoo SPY Jan 1993–Sep 2026, 2 bp per side.
  - **Full sample:** CAGR 5.0% vs 10.8% buy-and-hold. Sharpe 0.81 vs 0.65. Max drawdown 14.8% vs 55.2%. 265 trades, ~77% winners, average trade +0.63%, ~11% time in market. $1 grew to $5.18 vs $31.71.
  - **Pre-2009:** Sharpe 0.97 (buy-and-hold 0.42), 116 trades, 81% winners, average trade +0.79%, max drawdown 7.0%.
  - **Post-2009:** Sharpe 0.68 (buy-and-hold 0.87), 149 trades, 74% winners, average trade +0.51%, max drawdown 14.8% (SPY 33.7%).
  - **Last three years:** 8.8% a year vs 22.3% for SPY.
  - **Cost sensitivity:** 5.3% a year at zero cost, 4.4% at 6 bp, 3.7% at 10 bp per side.
  - **Robustness:** all 15 neighbouring parameter sets were positive (Sharpe 0.13–0.92). On five other equity ETFs the Sharpe was only 0.38–0.53; SPY was the best of the six.
  - Source: [Empirica Lab, "Connors' RSI(2) had a Sharpe of 0.97 before the book. Since then: 0.68.", 2026-10-11](https://empiricalab.substack.com/p/connors-rsi2-spy). Anonymous blog; not peer-reviewed.
- An older independent RSI(2) test on the S&P 500 found the system did poorly in 2011, 2013 and 2014 and recovered in 2015. Its best performance came early in the test period — [Decoding Markets / StockSoft Research, "Testing the RSI 2 trading strategy" (c. 2019–2020, undated)](https://decodingmarkets.com/rsi-2-trading-strategy/); see also [stocksoftresearch.com](https://stocksoftresearch.com/rsi-2-trading-strategy/).
- QuantifiedStrategies claims that out-of-sample validation over 2015–2025 shows "slight performance decay from increased HFT competition" while the core edge remains profitable. The methodology is not shown. QuantifiedStrategies is a practitioner/vendor site that sells strategies — [QuantifiedStrategies RSI-2 guide](https://www.quantifiedstrategies.com/rsi-2-strategy/), via search snippet; the page was blocked behind a bot check.
- **ConnorsRSI (CRSI).** Concretum Research, a vendor-affiliated research firm, posted in Jan 2025 that the 2014 ConnorsRSI composite has shown reduced effectiveness out of sample. CRSI is a different indicator from plain RSI(2) — [Concretum Research on X, Jan 2025](https://x.com/ConcretumR/status/1879572346362593308?lang=en).
- **Practitioners report a shrinking edge.** Cesar Alvarez, formerly Connors' research director, reportedly wrote that "the edge of mean reversion trading is shrinking. Still profitable but much more difficult." This is a secondhand, undated forum quote — [The Chartist forum](https://thechartist.com.au/forums/users/lmzirmdgmail-com/replies/page/6). One newsletter reports its SPY mean-reversion strategy underperformed from 2022 and that it was considering replacing it — [Setup4Alpha, strategy performance review](https://setup4alpha.substack.com/p/strategy-performance-review-october).
- **IBS (Internal Bar Strength), all vendor or anecdotal:**
  - QuantifiedStrategies (Mar 2026 summary): QQQ, buy when IBS < 0.1, exit when IBS > 0.9, ~14% annualized over 30 years; the edge is said to be stronger in bear or high-volatility markets. No cost or out-of-sample detail. Vendor — [QuantifiedStrategies substack](https://quantifiedstrategies.substack.com/p/the-classical-mean-reversion-strategy).
  - WealthLab blog (Dec 2025) claims ">300% in the past decade on QQQ" with no drawdown or cost data. Software vendor — [WealthLab](https://wealth-lab.com/blog/build-a-profitable-mean-reversion-strategy-using-the-ibs-indicator).
  - A Reddit r/algotrading user (Mar 2026) reported a ~70% win rate and profit factor ~2.0 on SPY/QQQ/AAPL with 16–25% time invested. Commenters flagged curve-fitting and the bull-market sample — [Reddit snapshot, 2026-03-06](https://reddit.sentinel-team.org/posts/1rjvxjy/snapshots/2026-03-06T19%3A00%3A34.508482Z).
  - QuantifiedStrategies' "S&P 500 mean reversion using IBS and RSI … 2024 and beyond" (2024-03-04) is paywalled. Only an equity curve since 2000 is visible — [link](https://quantifiedstrategies.substack.com/p/s-and-p-500-mean-reversion-using-19a).
- **Regime view.** Michael Harris (Price Action Lab) argues the S&P 500 moved into a mean-reversion regime in late 1997, when the 252-day lag-1 autocorrelation of daily returns turned negative. He sees a sudden switch back to momentum as the main risk, and says widely known mean-reversion edges tend to fade. His posts are undated and he sells software and analysis — [Price Action Lab blog](https://priceactionlab.com/Blog/?p=53291); [QuantInsti webinar on regime changes, 2020-10-08](https://blog.quantinsti.com/regime-changes-webinar-michael-harris-8-october-2020).
- **Parameter-mining caution.** StatOasis ran 15,552 RSI(2) filter backtests on SPY and futures and notes that agreement between them is a consistency check, not out-of-sample evidence — [StatOasis](https://statoasis.com/overfit/research/boost-your-rsi2-strategy-for-sp500-by-48-with-this-volume-filter).

### Inferences
- RSI(2)'s post-2009 average trade of ~0.5% across ~150 trades in ~17 years (~9 trades a year) is large relative to retail costs. Costs are not what kills it. The problem is low exposure: ~11% time in market means the rule earns cash-like returns most of the year. Paired with a buy-and-hold core it changes little; on its own it lags equities in bull markets.
- **Implementation mismatch.** SPY/QQQ cannot be bought by this investor. A UCITS S&P 500 ETF on Xetra or LSE closes at 17:30 CET, about 4.5 hours before the US close. "Signal at the US close, fill at the close" would therefore have to be adapted: signal on the US close and fill on the next European session, or trade the UCITS ETF's own European close. Either change could materially alter the backtested edge, and it must be re-tested.
- Alternatives under the investor's constraints are a basket of US single stocks (not an index) or US options (e.g., buying SPY or XSP calls on signal). Both change the risk and cost profile and need separate testing.
- Expect the post-publication results (Sharpe ~0.7, CAGR ~4–5%, max drawdown ~15%) rather than the book-era figures.

### Gaps
- I found no peer-reviewed out-of-sample study of RSI(2), IBS or "buy after N down days" on SPY/QQQ. All the evidence is practitioner backtests.
- I found no independent decay study for IBS specifically, and no dated test of "SPY down 3 days in a row → buy" since 2010.
- I found no tests on UCITS S&P 500 or Nasdaq-100 ETFs with European closing prices.

## Q2. Short-term (1-week/1-month) reversal in individual stocks: does it survive costs?

### Takeaway
Classic short-term reversal is largely unprofitable net of costs across a broad universe, and it has weakened over time ("vanished entirely in most regions" per Robeco, 2023). It survived costs only in the largest, most liquid stocks in older samples (1990–2009: ~29 bp/week net in the top 100 US stocks), and with careful turnover control. Enhanced versions (residual or industry-adjusted) are an institutional, long-short, high-turnover game. A long-only retail implementation is unlikely to keep a meaningful edge.

### Cited Findings
- **de Groot, Huij & Zhou (Journal of Banking & Finance 2012), "Another Look at Trading Costs and Short-Term Reversal Profits".**
  - Using Nomura cost estimates (spread plus market impact) plus 3–5 bp commissions, weekly reversal in the 100 largest US stocks earned ~0.29%/week net over 1990–2009. Quantpedia annualises this to ~16.25%, volatility ~14.9%, Sharpe ~1.09; it also lists a −52.9% max drawdown of unclear provenance.
  - Net returns fall with breadth: 100 stocks +29.0 bp/week, 500 stocks +10.6 bp/week, 1,500 stocks −31.4 bp/week.
  - Sources: [Quantpedia, Short-Term Reversal in Stocks](https://quantpedia.com/strategies/short-term-reversal-in-stocks); [EconPapers record](https://econpapers.repec.org/RePEc:eee:jbfina:v:36:y:2012:i:2:p:371-382).
- **Decay.** Blitz, van der Grient & Honarvar (Robeco, Oct 2023) say the classic reversal effect "has steadily weakened over time" and has "vanished entirely in most regions." They revive it by neutralising short-term industry and factor momentum, which Robeco's marketing summary says doubles risk-adjusted returns. Robeco runs a "Quantum short-term alpha" product built on this, so the source is vendor-affiliated — [Robeco insight, Oct 2023](https://www.robeco.com/en-uk/insights/2023/10/reversing-the-trend-of-short-term-reversal); [Quantpedia summary](https://quantpedia.com/strategies/short-term-reversal-in-stocks).
- **Medhat & Schmeling (Review of Financial Studies 2022), "Short-term Momentum".**
  - The monthly reversal effect is concentrated in low-turnover stocks. Among high-turnover stocks the one-month signal flips to *momentum*, which they say survives conservative cost estimates.
  - Search summaries also report: reversal of 0.84%/month in large caps (t=5.45) vs 1.41%/month in small caps, and an average monthly transaction cost of 1.94% for the standard STREV strategy that subsumes its gross return. I could not verify these figures in the paper text.
  - Sources: [EconPapers RFS record](https://econpapers.repec.org/RePEc:oup:rfinst:v:35:y:2022:i:3:p:1480-1526.); [CEPR DP15857](https://repec.cepr.org/repec/cpr/ceprdp/DP15857.pdf); [City Research Online](https://openaccess.city.ac.uk/id/eprint/31278/).
- A European study finds short-term reversal profits can be mainly explained by transaction costs — [Reversal and momentum patterns in weekly stock returns: European evidence](https://law-journals-books.vlex.com/vid/reversal-and-momentum-patterns-855637453).
- **Productisation.** Vesper's UTRN ETF holds 25 S&P 500 stocks selected on short-term reversal. This is vendor marketing, not independent evidence — [ETF Stream](https://etfstream.com/articles/short-term-reversal-etf).

### Inferences
- A retail long-only version (buy last week's biggest large-cap losers) captures only the long leg. Some evidence holds that most of the anomaly sits in the short leg and in illiquid names, though I did not source this here.
- With IBKR US-stock commissions low but spread costs of a few bp per side in large caps, weekly turnover of ~200% per week means roughly 10+% a year in round trips on the traded book. That would consume most of a 10–30 bp/week gross edge. Treat this as a candidate only for paper testing.
- The high-turnover short-term momentum finding (Medhat & Schmeling) implies naive "buy the losers" can be on the wrong side in heavily traded names. That is relevant to retail favourites.

### Gaps
- I found no post-2010 net-of-cost out-of-sample figures for large-cap reversal in a public source; Robeco's 2023 paper tables were not accessed.
- I found no evidence on long-only versions of reversal for retail.

## Q3. Post-earnings announcement drift (PEAD): dead in large caps? Survives in small caps or with better surprise signals?

### Takeaway
On standard analyst-surprise (SUE) sorts, PEAD in non-microcap US stocks has been absent since ~2006, and in microcaps since ~2016 (Martineau, Critical Finance Review 2022). A 2025 rebuttal literature claims drift persists, but Subrahmanyam (2025) shows those results collapse once microcaps are excluded (t = 1.43, 2001–2024). For a retail trader, classic PEAD is not a credible net-of-cost edge in investable stocks. Any residual sits in microcaps where spreads are large.

### Cited Findings
- **Martineau, "Rest in Peace Post-Earnings Announcement Drift", Critical Finance Review 11(3–4), 2022, pp. 613–646.**
  - Sample: I/B/E/S 1984–2019 (593,654 earnings announcements); Compustat 1973–2019.
  - Since 2006, analyst surprises fail to positively predict 60-day post-announcement returns for "all-but-microcap" stocks (above the NYSE 20th percentile). For microcaps the same holds since 2016.
  - Prices respond to surprises on the announcement date about 6x (non-microcap) and 3x (microcap) more in 2016–2019 than in 1984–1990.
  - PEAD does not "hide" in the smallest non-microcaps or at shorter horizons.
  - Sources: [paper PDF](https://cfr.ivo-welch.org/published/papers/martineau2021rest.pdf); [EconPapers](https://econpapers.repec.org/RePEc:now:jnlcfr:104.00000122).
- **UCLA Anderson Review (2026-01-21), summarising the debate.**
  - Martineau ties the decline to decimalisation (2001) and the 2005 regulation that accelerated HFT.
  - Dickerson, Julliard & Mueller (JFE, in press 2025) find "earnings drift" remains a key pricing factor, but their factor is built from abnormal announcement returns rather than accounting surprises.
  - Hirshleifer, Peng & Wang (RFS 2025) find drift with t≈14, but did not exclude microcaps.
  - Subrahmanyam (SSRN 5930255, 2025) rebuilds the drift factor for Feb 2001–Dec 2024. All stocks: t = 2.18. Excluding microcaps (bottom NYSE 20%, ~3% of market cap): t = 1.43, not significant.
  - No Sharpe ratios or return magnitudes are given.
  - Source: [UCLA Anderson Review, "Is Post-Earnings Announcement Drift a Thing? Again?", 2026-01-21](https://anderson-review.ucla.edu/is-post-earnings-announcement-drift-a-thing-again/).
- **General decay context.** McLean & Pontiff (Journal of Finance 2016), across 97 anomalies: returns are 26% lower out-of-sample and 58% lower post-publication, implying ~32% attributable to publication-informed trading — [vLex abstract](https://law-journals-books.vlex.com/vid/does-academic-research-destroy-855658380); [PDF copy](https://tevgeniou.github.io/EquityRiskFactors/bibliography/AcademicReviewFactor.pdf).

### Inferences
- For investable US stocks a retail trader would buy (above roughly $1–2bn market cap), a simple "buy after a positive earnings surprise and hold 60 days" rule has had no measurable post-announcement edge for ~20 years.
- Surprise-based or text-based refinements are claimed in the 2025 papers, but their significance appears to depend on microcaps and on non-standard factor construction.
- Microcap PEAD, even where it existed, faced wide spreads. Martineau finds it has disappeared there too since 2016.

### Gaps
- I found no public, dated net-of-cost backtest of PEAD variants after 2019, e.g., revenue surprises, analyst-revision drift or SUE in mid-caps; the Martineau sample ends in 2019.
- The Subrahmanyam working paper itself was not accessed, only the summary.

## Q4. Calendar and seasonal anomalies: post-publication performance and tradability after costs

### Takeaway
Most calendar effects have weakened since publication. Turn-of-the-month (TOM) for US ETFs is "largely disappeared over the past decade" for the classic window and declining for wider windows; it now mainly cuts drawdowns rather than adding return. Pre-holiday largely faded after 1987. The overnight-vs-intraday split is real gross but does not survive ~1 cent per share of cost. The January effect has faded in large caps and indices. Pre-FOMC drift persisted after 2011 only on press-conference days (~40 bp). Halloween / Sell-in-May survived out-of-sample to ~2012 on average across 37 markets but is contested (driven by 1987/1998 outliers). None looks like a strong stand-alone retail edge; a few are cheap enough to use as overlays.

### Cited Findings
- **Turn-of-the-month:**
  - QuantSeeker (2025-02-09) tested SPY, QQQ, IWM, 11 sector SPDRs, 9 country ETFs and others at 5 bp one-way cost. The holding window runs from the close of day −4 to the close of day +3, about 7 of ~21 trading days (my calculation).
  - US ETFs: TOM shows a "noticeable drop in CAGR" vs buy-and-hold and similar or lower Sharpe, but significantly smaller drawdowns.
  - The classic [0:+3] window "has largely disappeared over the past decade"; the [−3:+3] window "has declined substantially."
  - Some international ETFs (EWZ, EWD, EWH) showed higher CAGR and Sharpe than buy-and-hold in the TOM window.
  - Practitioner blog; the numeric tables are images — [QuantSeeker, "Turn-of-the-Month Strategies: Do They Still Work?", 2025-02-09](https://www.quantseeker.com/p/turn-of-the-month-strategies-do-they).
- Maberly & Waggoner (Atlanta Fed WP 2000-11) found TOM effects in S&P 500 futures disappeared after 1990, carrying over to spot. They warn about out-of-sample inference from in-sample regularities — [Atlanta Fed WP 2000-11](https://www.atlantafed.org/research/publications/wp/2000/11.aspx).
- Contrary evidence: McConnell & Xu (2008) found TOM persisted 1987–2005 in the US and internationally. Kinlay's blog found a seasonal S&P 500 allocation beat buy-and-hold by ~88 bp/yr gross since 1980 — [Quantpedia TOM page](https://quantpedia.com/strategies/turn-of-the-month-in-equity-indexes); [Jonathan Kinlay blog](https://jonathankinlay.com/?p=2110).
- **Pre-holiday:**
  - Keef & Roush (Applied Financial Economics 2005; 1930–1999): a strong pre-holiday effect up to 1987, largely gone afterwards — [EconPapers](https://econpapers.repec.org/RePEc:taf:apfiec:v:15:y:2005:i:2:p:107-119).
  - A 2024 conference paper on S&P 500 Dec 2013–Dec 2023 reports low volatility and high returns in the 5-day pre-holiday window. The sample is short — [SciTePress 2024](https://www.scitepress.org/PublishedPapers/2024/132703).
  - CXO Advisory finds Thanksgiving pre/post-holiday gains "markedly less so in recent data"; its Christmas subsamples for 1990–2024 "mostly confirm" pre-holiday strength — [CXO Thanksgiving](https://www.cxoadvisory.com/calendar-effects/stock-returns-around-thanksgiving); [CXO Christmas](https://cxoadvisory.com/calendar-effects/stock-returns-around-christmas).
- **Overnight vs intraday:**
  - On SPY 1993–2020, gross cumulative returns were overnight +717%, buy-and-hold +627%, intraday +12%. Most of the excess came before the dot-com bust, and outperformance has "waned" — [Alpha Architect, "Trading Costs Wipe Out the Overnight Return Anomaly", 2020-06-16](https://alphaarchitect.com/trading-costs-wipe-out-the-overnight-return-anomaly/).
  - Nasdaq's analysis found adding just 1 cent per trade "almost totally eliminates" the overnight strategy's historic gains — [Nasdaq, "Night and Day"](https://www.nasdaq.com/articles/night-and-day).
  - In the cross-section, Lou, Polk & Skouras find momentum returns accrue overnight and value/size intraday. Results are gross, and CXO notes daily switching would generate very large frictions — [CXO Advisory](https://www.cxoadvisory.com/calendar-effects/momentum-happens-at-night/).
- **Pre-FOMC drift:**
  - Lucca & Moench originally found ~50 bp from the open of the day before an FOMC announcement to the announcement-day close, over 1994–Mar 2011.
  - Apr 2011–Jun 2018: ~40 bp (day-before open → about lunchtime on announcement day) plus ~30 bp more by the end of the press conference on press-conference days. No significant pre-announcement excess return on non-press-conference days.
  - Sources: [Liberty Street Economics, Lucca & Moench, 2018-11-26](https://libertystreeteconomics.newyorkfed.org/2018/11/the-pre-fomc-announcement-drift-more-recent-evidence.html); [NY Fed Staff Report 512](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr512.pdf).
  - A later stock-level study (British Journal of Management, vol. 35) describes the drift as having "recently declined," mainly ahead of press-conference announcements, and links part of it to lottery-like stocks — [Wiley abstract](https://onlinelibrary-wiley-com-443.webvpn.zafu.edu.cn/doi/abs/10.1111/1467-8551.12755).
- **Halloween / Sell-in-May:**
  - Bouman & Jacobsen (2002): November–April returns beat May–October in 36 of 37 countries — [TIAS PDF](https://www.tias.edu/docs/default-source/Kennisartikelen/ssrn-id76248.pdf?sfvrsn=2).
  - Out-of-sample over Nov 1998–Apr 2012, the winter–summer gap was still ~10 percentage points on average across the 37 markets (Andrade, Chhaochharia & Fuerst, FAJ 2013) — [CFA Institute blog](https://rpc.cfainstitute.org/blogs/enterprising-investor/2013/sell-in-may-and-go-away-just-wont-go-away-podcast/).
  - Jacobsen & Zhang: November–April mean returns are higher in 81 of 108 markets; out-of-sample Sep 1998–Apr 2011 the effect holds in all 37 original countries — [Jacobsen & Zhang PDF](https://www.bnains.org/backtest/periode/The_Halloween_Indicator_everywhere_and_all_the_time_-_Ben_Jacobsen_%26_Cherry_Y._Zhang.pdf).
  - Contrary: Maberly & Pierce (Econ Journal Watch 2004) find the US effect insignificant once Oct 1987 and Aug 1998 are dummied, and no exploitable effect in S&P 500 futures Apr 1982–Apr 2003 — [Econ Journal Watch](https://econjwatch.org/articles/stock-market-efficiency-withstands-another-challenge-solving-the-sell-in-may-buy-after-halloween-puzzle).
- **January effect:**
  - International data 1997–2014: the effect "no longer exists in recent years." A 2024 international paper finds no significant January vs other-month difference in the latest five years — [Clute Journals, JABR](https://clutejournals.com/index.php/JABR/article/view/9540).
  - CXO finds the small-cap January effect persisted through 1946–2007 but shrank after 1963–1979, "reverting to pre-existing levels" — [CXO Advisory](https://www.cxoadvisory.com/size-effect/persistence-of-the-january-effect).

### Inferences
- **TOM is cheap to trade** (about 12 round trips a year in a UCITS S&P 500 ETF). It is mostly a drawdown-reduction/exposure-timing tool now, not an alpha source vs buy-and-hold for US equity. Best treated as a filter: be invested around month-end, de-risk mid-month, rather than as a stand-alone strategy.
- **Pre-FOMC:** I believe the Fed has held a press conference after every FOMC meeting since 2019, which would make every meeting "press-conference" style; I did not verify this in this session. The ~8 events a year with a ~40 bp historical drift are low frequency, and the post-2018 magnitude is unsourced here.
- **Overnight:** not implementable cost-effectively by a retail trader. It needs two trades a day, and UCITS ETFs trade on European hours, which misalign with the US overnight session.
- **Sell-in-May** on a UCITS ETF is cheap (two trades a year), but it gives up equity premium in the summer. Its long-run outperformance claims are contested and depend on outliers. Expect higher risk-adjusted returns at best, not higher absolute returns.

### Gaps
- I found no published post-2012 out-of-sample update of Halloween with costs, and no post-2018 quantification of the pre-FOMC drift.
- QuantSeeker's numeric CAGR, Sharpe and drawdown tables were not readable.
- I found no peer-reviewed post-2000 study isolating the US pre-holiday effect net of costs.

## Q5. Sector/industry momentum rotation (monthly) and 52-week-high momentum: post-2015 results

### Takeaway
Evidence after 2015 is thin. Sector-ETF momentum rotation mainly reduces drawdowns, especially with a trend filter; risk-adjusted outperformance vs SPY is weak or insignificant once dynamic factor exposures and costs are accounted for. The 52-week-high strategy had a significantly *negative* return in 2001–2014 in one study, which casts doubt on its post-publication robustness.

### Cited Findings
- **Industry momentum:** after risk-adjusting for time-varying factor exposures, industry momentum profitability "diminishes and becomes insignificant" for strategies based on recent past returns — [Expected versus Ex Post Profitability in the Cross-Section of Industry Returns (vLex)](https://law-journals-books.vlex.com/vid/expected-versus-ex-post-855621482).
- **Out-of-sample industry rotation, 30 US industries, 1970–2016, gross:** a regression-based rotation vs relative momentum, 8.2% vs 7.3% annualised and Sharpe 0.65 vs 0.50. The search summary listed the return figures in reversed order, so the pairing is uncertain. The source warns that the costs of converting to funds and of monthly rebalancing would reduce performance — [CXO Advisory summary](https://www.cxoadvisory.com/?p=30896).
- **Sector ETF momentum with an S&P 500 SMA10 timing overlay:** net CAGR 9.7% vs 10.8% for a related fund-based system. CXO cautions that the ETF version embeds data-snooping bias — [CXO Advisory](https://www.cxoadvisory.com/?p=24699).
- **Arthur Hill (StockCharts, 2017)** tested 26- and 13-week ROC rotation on the nine sector SPDRs and noted "momentum systems do not perform as well with ETFs" because of lower beta and volatility. A SPY trend-timing system returned 7.53% a year with a 17% max drawdown — [StockCharts, 2017-02](https://articles.stockcharts.com/article/articles-arthurhill-2017-02-systemtrader---testing-a-trend-timing-system-and-momentum-rotation-system-for-the-nine-sector-spdrs/).
- **Quantpedia's sector momentum backtest** (1928–2009) shows ~4%/yr outperformance vs buy-and-hold. This is in-sample and pre-2010 — [Quantpedia Sector Momentum](https://quantpedia.com/strategies/sector-momentum-rotational-system).
- **52-week high:**
  - George & Hwang (Journal of Finance 2004): nearness to the 52-week high dominates past returns in forecasting, without long-run reversal — [Alpha Architect summary, 2014-11-11](https://alphaarchitect.com/the-secret-to-momentum-is-the-52-week-high/).
  - Lobão & Fernandes (2017): positive but insignificant return over 1980–2014. Significantly positive in 1980–2000 and significantly *negative* in 2001–2014 — [EconPapers](https://econpapers.repec.org/RePEc:cuf:journl:y:2017:v:18:i:2:lobao).
  - An SSRN working paper reports both 52-week-high and standard momentum decayed over time, the 52-week-high less so. Authorship and status are unverified — [Scribd copy of SSRN 4587697](https://www.scribd.com/document/694152012/SSRN-id4587697).
  - Hsieh's global study finds George & Hwang (2007) results "not significant around the world"; Gupta, Locke & Scrimgeour (2010) found profits in 10 of 16 international markets — [search summary sources](https://ideas.repec.org/a/eee/finlet/v46y2022ipbs1544612321004256.html).

### Inferences
- A monthly sector rotation implemented with UCITS sector ETFs is feasible and low-cost for this investor (iShares and SPDR have S&P 500 and MSCI World sector UCITS lines). The evidence suggests treating it as a drawdown-management or trend tool, with modest expected outperformance at best.
- The 52-week-high signal looks unreliable as a stand-alone after 2000.

### Gaps
- I found no rigorous post-2015 out-of-sample test of sector ETF momentum vs SPY with Sharpe and drawdown, and no post-2014 net-of-cost 52-week-high results.
- I found no tests on UCITS sector ETFs.

## Q6. Breakout/Turtle-style trend systems on stocks/ETFs and Minervini/O'Neil-style momentum swing trading: independent evidence

### Takeaway
The main stock trend-following evidence, buying all-time-high breakouts with wide ATR trailing stops, comes from authors linked to trading firms (Blackstar 2005; Concretum 2025). It shows positive expectancy driven by under 7% of trades, with a win rate around 49%, and heavy sensitivity to transaction costs; the base strategy is "difficult to implement under $1M." For CAN SLIM and Minervini there is essentially no rigorous independent evidence. The handful of small academic CAN SLIM studies are weak, and the CAN SLIM mutual fund ranked in the worst 5% of its category over 5 years.

### Cited Findings
- **Wilcox & Crittenden (Blackstar Funds, 2005), "Does Trend Following Work on Stocks?"**
  - Long-only, survivorship-adjusted US universe of more than 24,000 securities over 22 years. Entry on an all-time high, 10-ATR trailing stop.
  - More than 18,000 trades, 49.3% winners, 0.5% round-trip costs assumed.
  - Critics note no significance tests and the inclusion of names trading under $250k/day — [PDF (UPenn copy)](https://www.cis.upenn.edu/~mkearns/finread/trend.pdf); [Niederhoffer critique](https://dailyspeculations.com/vic/trend.html).
- **Zarattini, Pagani & Wilcox, "Does Trend-Following Still Work on Stocks?" (Concretum Group; SSRN 5084316; c. 2025, PDF dated Feb 2026).**
  - Survivorship-bias-free liquid US stocks, 1950–Nov 2024, with more than 66,000 trades. Under 7% of trades generate the majority of profits; the distribution is stable out-of-sample over 2005–2024.
  - Portfolio CAGR 15.19% gross over 1991–2024, annualised alpha 6.18%.
  - The base strategy is "difficult to implement for portfolios under $1 million AUM" because of costs; a turnover-control algorithm is proposed.
  - Concretum sells trading research and services — [Concretum page](https://concretumgroup.com/does-trend-following-still-work-on-stocks/); [CXO summary](https://cxoadvisory.com/momentum-investing/all-time-high-trend-following).
- **AAII** notes all-time-high trend strategies are "not without costs and risks" — [AAII Investor Update](https://www.aaii.com/investor-update/article/277265-all-time-high-trend-strategies-are-not-without-costs-and-risks).
- **CAN SLIM:**
  - Lutey, Crum & Rayome tested a simplified screen and report +0.94%/month vs the Nasdaq-100 in 2010. This is a very short sample in a small journal — [Scribd copy](https://www.scribd.com/document/476404128/CANSLIM).
  - A live out-of-sample follow-up exists in the Journal of Accounting and Finance; its results were not accessed — [JAF article](https://mail.articlegateway.com/index.php/JAF/article/view/5134).
  - The AAII CAN SLIM screen has been strong since 1997 per AAII's own backtest (publisher test) — [AAII](https://www.aaii.com/journal/article/a-can-slim-screen-with-no-float-but-plenty-of-lift).
  - The CAN SLIM-based mutual fund's 5-year investor returns ranked in the worst 5% of its category — [A Wealth of Common Sense](https://awealthofcommonsense.com/?p=5829).
  - O'Neil's rules were derived from 500 past big winners (1953–1993), a sample with clear selection bias — [Stockopedia](https://www.stockopedia.com/content/how-does-can-slim-investing-work-55881).
- **Minervini (SEPA/VCP):** I found no independent, non-vendor backtest or audited track record of the systematic rules. Claims come from books, courses and championship results; the absence of evidence is noted.

### Inferences
- An all-time-high or 52-week breakout system on US single stocks is implementable at IBKR (long-only, end-of-day, no leverage). Because the edge is concentrated in rare outliers, it needs a broad universe and many concurrent positions: 20–40 names, so €2–10k per position at €100k. Small accounts will suffer from minimum commissions and lumpy sizing.
- Expect long flat or negative stretches and a ~50% or lower win rate. Costs and turnover control are decisive, per the authors' own warnings.
- Minervini/O'Neil-style discretionary swing trading cannot be evaluated as a systematic edge from the public evidence.

### Gaps
- I found no fully independent (non-trading-firm) replication of stock trend-following after 2005 with retail costs.
- Drawdown and Sharpe for the Concretum portfolio were not on the summary page.
- I found no independent evidence for Minervini.

## Q7. Pairs trading / statistical arbitrage: decay since Gatev, Goetzmann & Rouwenhorst (2006); retail feasibility

### Takeaway
Distance-method pairs trading on US equities has decayed sharply. It has been largely unprofitable after costs since ~2002 (Do & Faff 2012), with trading opportunities sharply reduced after 2009 (Rad, Low & Faff 2016). Remaining profits cluster in high-volatility periods. Retail implementation also requires shorting, which conflicts with the long-only preference. Low priority.

### Cited Findings
- Do & Faff (2012) show the distance method is largely unprofitable after 2002 once trading costs are counted — cited in [Rad, Low & Faff 2016, Quantitative Finance (author PDF)](https://randlow.github.io/2016_QF_PairsTrading.pdf).
- **Rad, Low & Faff (Quantitative Finance 2016), US equities 1962–2014:** from 2009 the frequency of trading opportunities for the distance and cointegration methods "is reduced considerably," while copula-based opportunities remain stable. The distance method's significantly positive risk-adjusted returns "largely disappear in recent years" once costs are properly included — [Bond University record](https://research.bond.edu.au/en/publications/the-profitability-of-pairs-trading-strategies-distance-cointegrat/); [author PDF](https://randlow.github.io/2016_QF_PairsTrading.pdf).
- **US equities 1990–2020 including Covid:** distance-method profitability "has dropped significantly in recent periods" — [arXiv 2010.01157, "Gold Standard Pairs Trading Rules: Are They Valid?"](https://arxiv.org/pdf/2010.01157).
- **ETF pairs 2007–2020** (Copenhagen Business School student thesis): no statistically significant alpha after costs, net profits only in highly volatile periods — [CBS](https://research.cbs.dk/en/studentProjects/pairs-trading-with-etfs-backtested-from-2007-2020/).
- **China 2005–2024:** distance-method decline attributed to market efficiency or crowding of a simple method — [MDPI JRFM 18(9):506, 2025](https://mdpi.com/1911-8074/18/9/506).

### Inferences
- **Not compatible with long-only/no-leverage constraints.** Shorting US stocks at IBKR incurs borrow fees and margin. The decayed, cost-sensitive edge leaves little room for retail frictions.

### Gaps
- I did not retrieve the exact GGR (2006) original return figures in this session.
- I found no recent (2020s) net-of-cost US equity pairs results from a peer-reviewed source.

## Q8. Intraday strategies (opening-range breakout, market intraday momentum): brief

### Takeaway
Intraday momentum on SPY (first half-hour predicts last half-hour) was published in 2018. A Concretum-affiliated 2024 SPY intraday momentum strategy claims 19.6%/yr net and Sharpe 1.33 over 2007–2024. The 5-minute ORB "Stocks in Play" paper claims Sharpe 2.81 over 2016–2023. An independent replication on index CFDs (Sep 2026) reproduces the gross ORB edge but finds it net zero after spread and slippage, and negative in 2015–2017. All of these require real-time data and intraday execution, which conflicts with this investor's end-of-day, delayed-data setup. Exclude.

### Cited Findings
- **Gao, Han, Li & Zhou (JFE 2018), "Market Intraday Momentum":** SPY 1993–2013, first half-hour return predicts last half-hour return, out-of-sample R² ≈ 1.6% — [Alpha Architect, 2014-08](https://alphaarchitect.com/2014/08/attention-prop-traders-the-first-half-hour-of-trading-predicts-the-last-half-hour/).
  - CXO out-of-sample check Aug 2012–May 2014 (441 days): R² ≈ 0.014 — [CXO Advisory](https://cxoadvisory.com/calendar-effects/first-and-last-half-hours-of-trading-linked).
  - Significant in 12 of 16 developed markets — [Nottingham repository](https://nottingham-repository.worktribe.com/OutputFile/5273196).
- **Zarattini, Aziz & Barbon, "Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)"** (SFI WP 24-97, May 2024; revised Feb 2025): 2007–early 2024, total return 1,985% net of costs, 19.6% annualised, Sharpe 1.33. CXO cites a −25% max drawdown. Authors are affiliated with Concretum and Bear Bull Traders, which are vendors — [SFI](https://www.sfi.ch/fr/publications/n-24-97-beat-the-market-an-effective-intraday-momentum-strategy-for-s-p500-etf-spy); [CXO summary](https://www.cxoadvisory.com/momentum-investing/complex-intraday-time-series-momentum-strategy-applied-to-spy/).
- **Zarattini, Barbon & Aziz, "A Profitable Day Trading Strategy for the U.S. Equity Market"** (5-minute ORB on "Stocks in Play"): 7,000+ US stocks 2016–2023. The top-20 by relative volume gained more than 1,600% net with Sharpe 2.81 and 36% annualised alpha — [IDEAS/RePEc](https://ideas.repec.org/p/chf/rpseri/rp2498.html).
  - A QuantConnect replication got Sharpe 2.40 — [QuantConnect](https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/).
  - A Reddit user extending it to the present reports Sharpe ~1.4 with weak raw returns — [r/algotrading](https://axebps-redlib.hf.space/r/algotrading/comments/1hezqql/opening_range_breakout_for_stocks_in_play_code).
- **Independent ORB replication** (MQL5 blog, 2026-09-25) of Zarattini & Aziz "Can Day Trading Really Be Profitable?" (QQQ 5-minute ORB; the paper reports a 24% hit rate, +0.13R a trade and 33%/yr with 4x leverage, commission-only costs):
  - Markets: NQ, SPX, Dow, DAX and FTSE CFDs, Jan 2015–Jun 2026.
  - Gross is positive in all five markets (NQ +0.131R, t=2.9). Net of spread and slippage, none is distinguishable from zero and four of five are negative (e.g., SPX −0.081R).
  - The rule was negative in every market in 2015–2017 — [MQL5 blog](https://www.mql5.com/en/blogs/post/776235).

### Inferences
- These strategies need live intraday data, intraday order management and, in the published versions, leverage (4x). That conflicts with no leverage, end-of-day decisions and ~15-minute-delayed free data.
- Headline Sharpe ratios come from vendor-affiliated authors over favourable samples. The one independent cost-inclusive replication finds no net edge.

### Gaps
- I found no independent post-2024 live or out-of-sample results for the SPY intraday-momentum strategy.

## Q9. Options income / volatility risk premium: PUT and BXM vs S&P 500 (esp. 2015–2026), covered-call ETFs, tail risk

### Takeaway
Since 2015 the Cboe PutWrite (PUT) and BuyWrite (BXM) indexes have badly lagged the S&P 500 on absolute return: 2015–2025 CAGR ~7.8% (PUT) and ~7.1% (BXM) vs ~13.5% (S&P 500 TR), computed from Cboe calendar-year data, all gross of costs. Over their full histories risk-adjusted returns are similar or lower: PUT Sharpe 0.52 vs 0.61 since 2007; BXM 0.56 vs 0.56 since 1989. Their main benefit is lower volatility and drawdown. Covered-call ETFs trail even their benchmark indexes (CXO, May 2026). JEPI and QYLD returned ~10–11%/yr vs ~17%/yr for SPY from May 2020 to Nov 2026. In crashes they cushion only slightly (2020: BXM −2.8%, PUT +2.1% vs S&P 500 +18.4% for the year). Options selling is not an edge over equity beta for a long-horizon investor. It is a lower-volatility equity substitute with capped upside.

### Cited Findings
- **Cboe PUT factsheet (as of 2026-09-30).** Monthly ATM SPX puts sold over T-bills.
  - Calendar returns, PUT vs S&P 500 TR:

    | Year | PUT | S&P 500 TR |
    |---|---|---|
    | 2015 | 6.4% | 1.4% |
    | 2016 | 7.8% | 12.0% |
    | 2017 | 10.8% | 21.8% |
    | 2018 | −5.9% | −4.4% |
    | 2019 | 13.5% | 31.5% |
    | 2020 | 2.1% | 18.4% |
    | 2021 | 21.8% | 28.7% |
    | 2022 | −7.7% | −18.1% |
    | 2023 | 14.3% | 26.3% |
    | 2024 | 17.8% | 25.0% |
    | 2025 | 9.2% | 17.9% |

  - PUT annualised: 1 year 15.2%, 3 years 13.9%, 5 years 9.8%, 10 years 8.5%.
  - Since Jan 2007: PUT 7.2%/yr, volatility 10.7%, max drawdown −32.7%, beta 0.6, Sharpe 0.52, Sortino 0.69. S&P 500 TR: 11.0%, 15.4%, −50.9%, Sharpe 0.61, Sortino 0.91.
  - Source: [Cboe PUT factsheet PDF](https://cdn.cboe.com/resources/indices/factsheet/CboeGlobalIndices_PUT-Index.pdf).
- **Cboe BXM factsheet (as of 2026-09-30).** S&P 500 with monthly ATM calls sold.
  - Calendar returns: 2015 5.2%, 2016 7.1%, 2017 13.0%, 2018 −4.8%, 2019 15.7%, 2020 −2.8%, 2021 20.5%, 2022 −11.4%, 2023 11.8%, 2024 20.1%, 2025 8.9%.
  - BXM annualised: 1 year 18.2%, 3 years 14.8%, 5 years 9.0%, 10 years 8.0%.
  - Since Jun 1986: BXM 8.6%/yr, volatility 10.6%, max drawdown −35.8%, beta 0.62, Sharpe 0.56 (from Jul 1989). S&P 500 TR: 11.2%, 15.2%, −50.9%, Sharpe 0.56.
  - Source: [Cboe BXM factsheet PDF](https://cdn.cboe.com/resources/indices/factsheet/CboeGlobalIndices_BXM-Index.pdf).
- **My computation from the factsheet calendar returns, 2015–2025 (11 years):**
  - PUT CAGR 7.83% (×2.29)
  - BXM CAGR 7.11% (×2.13)
  - S&P 500 TR CAGR 13.53% (×4.04)
  - Source data: Cboe factsheets above.
- **Earlier period (CXO Advisory, 2016-04-06).** Over Feb 2006–Dec 2015:
  - PUT: 6.6%/yr gross, volatility 11.5%, Sharpe 0.52, max drawdown −33%.
  - WPUT (weekly): 5.6%, 9.8%, 0.50, −24%.
  - S&P 500 TR: 7.1%, 15.1%, 0.46, −51%.
  - Over Jul 1986–Dec 2015: PUT 10.1%/yr (Sharpe 0.67) vs S&P 500 TR 9.8% (Sharpe 0.47).
  - All gross. Options have "high trading frictions," and ETFs tracking BXM "substantially underperform BXM."
  - Source: [CXO Advisory, "Performance of CBOE PutWrite Indexes", 2016-04-06](https://www.cxoadvisory.com/equity-options/performance-of-cboe-putwrite-indexes/).
- **PUT vs BXM:** PUT beat BXM by ~1.1%/yr over 1986–2015, partly due to index construction timing on expiration mornings — [Quantpedia, "PutWrite vs. BuyWrite Index Differences"](https://quantpedia.com/putwrite-vs-buywrite-index-differences/).
- **Bondarenko (Cboe-sponsored study, 2019):**
  - 2006–2018 max drawdown: WPUT −24.2%, PUT −32.7%, S&P 500 −50.9%. Longest drawdown: 22, 29 and 52 months respectively.
  - Since 1986, PUT 9.54%/yr (volatility 9.95%) vs the put-buying index PPUT 6.64% (volatility 12.08%).
  - Sponsored by Cboe, which has a commercial interest — [Bondarenko 2019 PDF (Cboe)](https://cdn.cboe.com/resources/education/research_publications/PutWriteCBOE19_v14_by_Prof_Oleg_Bondarenko_as_of_June_14.pdf); [Cboe insight post](https://www.cboe.com/insights/posts/white-paper-shows-volatility-risk-premium-facilitated-higher-risk-adjusted-returns-for-put-index/).
- **S&P DJI research:** in years when the S&P 500 rose more than 10%, BXM underperformed by an average 9.3% (with lower volatility); BXM outperformed in down years — [S&P DJI, "Defining Paths with Options-Based Index Strategies"](https://www.spglobal.com/spdji/en/documents/research/research-defining-paths-with-options-based-index-strategies.pdf).
- **Covered-call ETFs vs their benchmarks (CXO, 2026-05-22):** PBP, XYLD, QYLD, FTHI and RYLD all have lower average monthly returns and CAGRs than their BuyWrite benchmark indexes (BXM, BXN/BXNT, BXRC), inception–Apr 2026. Figures are paywalled — [CXO Advisory, "Are Equity Index Covered Call ETFs Working?", 2026-05-22](https://www.cxoadvisory.com/equity-options/are-equity-index-covered-call-etfs-working/).
- **Put-write ETFs:** CXO's "Are Equity Put-Write ETFs Working?" uses data through Oct 2025 and notes some funds are now defunct (HVPW, PUTX). Results are paywalled. A related Dec 2025 CXO item reportedly gives equity put-write ETFs an average 5.5% CAGR vs 14.3% for SPY (secondhand via WebFetch summary) — [CXO Advisory](https://cxoadvisory.com/equity-options/are-equity-put-write-etfs-working).
- **JEPI / QYLD vs SPY, total return with dividends reinvested, 2020-05-21 to 2026-11-09:**

  | Fund | Annualised | Cumulative | Max drawdown |
  |---|---|---|---|
  | JEPI | 11.29% | +99.8% | −13.7% |
  | QYLD | 10.29% | +88.5% | −24.6% |
  | SPY | 17.19% | +179.1% | −24.5% |

  Source: [TotalRealReturns](https://totalrealreturns.com/n/JEPI,SPY,QYLD).
- **Capture of S&P 500 return:** JEPI captured ~37% of the S&P 500's total return in 2023 (9.8% vs ~26%) and XYLD ~42% (11.0%) — [Benzinga, Oct 2024](https://benzinga.com/opinion/24/10/41338397/my-100-000-dividend-portfolio-decision-jepi-spyi-or-xyld).
- **Tail years, from the Cboe factsheets:**
  - 2018 (Feb 2018 "Volmageddon" year): PUT −5.9%, BXM −4.8%, S&P 500 TR −4.4%.
  - 2020 (Covid crash): PUT +2.1%, BXM −2.8%, S&P 500 TR +18.4%. Options-selling lagged badly in the V-shaped rebound.
  - 2022: PUT −7.7%, BXM −11.4%, S&P 500 TR −18.1%.

### Inferences
- **For a long-horizon investor**, systematic ATM put-writing or buy-writing has cost ~5–6 percentage points a year vs the S&P 500 since 2015, gross of option costs. Lower volatility (~10.6–10.7% vs ~15%) and smaller drawdowns are the main benefit. Risk-adjusted returns are roughly equal over the full histories, and the post-2015 period looks worse (my inference from the calendar data).
- **Feasibility for this investor.** US-domiciled covered-call and put-write ETFs (JEPI, QYLD, XYLD, PUTW) are blocked by PRIIPs. Self-managed options on US underlyings are allowed.
  - Contract sizing: SPX options are 100× the index and XSP (Mini-SPX) is 1/10 of SPX. At an assumed SPX level of ~6,500, one cash-secured ATM XSP put needs ~$65k of collateral. That gives coarse sizing for a €10k–€200k account. This is an inference; the index level is assumed, not sourced.
  - Single-stock cash-secured puts or covered calls need 100 shares per contract.
  - Execution: options spreads plus IBKR per-contract fees (not verified in this session) reduce the gross index returns.
- UCITS covered-call ETFs exist (e.g., JPMorgan and Global X UCITS lines). The CXO evidence that US covered-call ETFs lag their indexes suggests similar or worse frictions; not verified for UCITS.
- **Tail risk:** a monthly ATM put-write loses roughly like equities in a fast crash, then lags the rebound because the upside is capped. The 2020 calendar result (+2.1% vs +18.4%) illustrates the asymmetry.

### Gaps
- Exact intra-month PUT/BXM drawdowns for Feb 2018 and Feb–Mar 2020 were not found; the Cboe factsheets give calendar years only.
- CXO paywalled tables on covered-call and put-write ETFs (per-fund CAGR and max drawdown) were not accessible.
- I found no performance data for UCITS covered-call ETFs.
- I could not verify IBKR options commission schedules in this session (IBKR pricing page returned 403).

## Q10 (cross-cutting). How much do published anomalies decay, and what does that imply for ranking these strategies for this investor?

### Takeaway
Across the academic literature, US anomaly returns fall ~26% out-of-sample and ~58% after publication (McLean & Pontiff 2016). One replication finds the decay rises to ~72% when restricted to post-2005 data, and the US is the market with the most reliable post-publication decline. Every strategy above fits that pattern. For an end-of-day, long-only, UCITS-constrained retail investor, the strategies that still have some positive net evidence are mostly drawdown-reducers (RSI(2)/mean-reversion overlays, TOM timing, sector or trend rotation, all-time-high trend following on US stocks) rather than return-enhancers. PEAD, short-term reversal, pairs trading, overnight, January and pre-holiday effects and intraday ORB show little or no net edge for this profile.

### Cited Findings
- McLean & Pontiff (Journal of Finance 2016), 97 predictors: returns 26% lower out-of-sample and 58% lower post-publication. About 32 percentage points are attributed to publication-informed trading — [vLex](https://law-journals-books.vlex.com/vid/does-academic-research-destroy-855658380).
- Jacobs & Müller (JFE 2020), 241 anomalies in 39 markets: the US is the only country with a reliable post-publication decline in long-short returns — [EconPapers](https://econpapers.repec.org/RePEc:eee:jfinec:v:135:y:2020:i:1:p:213-230).
- A replication reports that limiting post-publication data to post-2005 raises the decay to ~72% — [arXiv 2105.01380](https://arxiv.org/pdf/2105.01380). This is from the search summary; the exact paper attribution is unverified.
- Martineau (2022) frames the death of PEAD as consistent with the adaptive markets hypothesis: efficiency is dynamic as trading costs fall — [paper PDF](https://cfr.ivo-welch.org/published/papers/martineau2021rest.pdf).

### Inferences
Summary ranking for this investor (France, IBKR, UCITS, long-only, EOD, €10k–200k). These are my judgement calls from the evidence above.

1. **Still a modest net edge, best as a low-exposure or risk-reducing sleeve:**
   - RSI(2)-type pullback buying in an uptrend (post-publication Sharpe ~0.7, ~11% exposure). It must be re-tested on UCITS ETF closes or US stocks.
   - All-time-high breakout trend following on US stocks (positive expectancy, cost-sensitive, skewed). Evidence is from trading-firm-affiliated authors.
2. **Weak or decayed, usable only as filters or overlays:** turn-of-the-month, Sell-in-May/Halloween, sector momentum rotation, pre-FOMC (low frequency).
3. **Not supported net of cost or incompatible with the constraints:** PEAD in investable stocks, classic short-term reversal (long-only), pairs trading (needs shorting), overnight strategy, January and pre-holiday effects, intraday ORB and intraday momentum (need real-time data and leverage), and Minervini/CAN SLIM (no independent evidence).
4. **Options income (PUT/BXM-style)** works as a lower-volatility equity substitute, not as excess return. Since 2015 it lagged the S&P 500 by ~5–6 percentage points a year gross. It is feasible via self-managed US options (XSP or single stocks) but coarse at this account size.

### Gaps
- I found no source testing any of these strategies specifically on UCITS ETFs with EUR-based costs and European trading hours, and none with French tax treatment (PFU flat tax on realised gains every trade).
- The cost impact of PFU on high-turnover strategies vs buy-and-hold in a PEA/CTO wrapper is not covered here.
