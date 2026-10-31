# Crypto and options/volatility strategies that retail bots automate — evidence net of costs, and tail risks

Research date: 2026-10-31. Evidence tiers: **(A)** peer-reviewed / official index or regulator data; **(B)** practitioner or working-paper backtest with stated costs, or live product/exchange data; **(C)** forum, vendor or anecdote. "My computation" = a figure I computed this session from a public primary data API (I did not round the outputs). It is not a published number and is labelled as mine every time. Quotes are verbatim from fetched pages or extracted PDF text unless marked "paraphrase" or "search-snippet". Where a page could not be fetched (HTTP 403, or a bot wall), I say so.

## Q1 — Funding-rate / basis (cash-and-carry) arbitrage on crypto perpetual futures

### Takeaway
The carry was real and large: the BIS reports it averaging above 10% a year, with peaks up to 60%. A working paper finds a cost-adjusted convergence version earns very high Sharpe ratios through March 2024. Since then it has compressed hard. On public proxies, BTC funding on Deribit fell from 16.51% in 2021 to 1.91% cumulative in 2026 to date (my computation). The sUSDe mean APY fell from 17.47% in 2024 to 4.20% in 2026 to date (my computation). CME basis was about 5% against about 4.5% risk-free in April 2026, which the source calls "essentially zero incentive". The tail risks are not theoretical. FTX (Nov 2022) is the venue-failure case, and Oct 10–11, 2025 brought auto-deleveraging (ADL) plus a USDe print of about $0.65 on Binance.

### Cited Findings
**Mechanism**
- [A, working paper] Funding mechanism, stated in the abstract: "To minimize the gap between perpetual and spot prices, long investors periodically pay shorts a funding rate proportional to this gap." A cash-and-carry bot is long spot and short the perp, and it collects that payment. — [He, Manela, Ross & von Wachter, "Fundamentals of Perpetual Futures", arXiv 2212.06888 v7, Sep 2026](https://arxiv.org/abs/2212.06888)

**Documented yields (as stated)**
- [A, official working paper; peer review not indicated] BIS Working Paper 1087, "Crypto carry", by Schmeling, Schrimpf & Todorov, published 04 April 2023: "We document that the carry of crypto futures, i.e. the difference between futures and spot prices, can become very large (up to 60% p.a.) and varies strongly over time." — [BIS WP 1087](https://www.bis.org/publ/work1087.htm)
- [A] BIS, same page: "A striking feature of crypto carry is its size, averaging above 10% annually". — [BIS WP 1087](https://www.bis.org/publ/work1087.htm)
- [A] BIS on the risk: "Engaging in the latter [cash and carry] is risky due to spikes in margins and liquidations amid drawdowns", and the findings section says "a high crypto carry predicts future price crashes". — [BIS WP 1087](https://www.bis.org/publ/work1087.htm)
- [B+, working paper with stated costs] He et al. test a random-maturity convergence strategy, which opens only when the futures–spot gap exceeds a cost bound. "For Bitcoin perpetual futures, the strategy generates a Sharpe ratio of 3.35 under high trading costs typical of retail investors, and up to 11.65 for highly active market makers who pay no such fees. After additionally accounting for effective bid-ask spreads, the corresponding Sharpe ratios remain 3.27 and 10.46." Costs are Binance fee tiers plus effective spreads built "from Binance transaction records". The sample for BTC/ETH is 2020-01-08 to 2024-03-11, and the paper notes the "data ends on 2024-03-11, covering the FTX fallout." — [arXiv 2212.06888 v7](https://arxiv.org/abs/2212.06888)
- [B+] He et al., interim risk: "maximum drawdowns do not exceed 3.90% for BTC, 2.67% for ETH, and 2.26% for BNB. They are larger for DOGE and ADA, reaching 13.90% and 5.69%". Also: "liquidations also depend on leverage, maintenance-margin requirements, available collateral, and the applicable margining regime." — [arXiv 2212.06888](https://arxiv.org/abs/2212.06888)

**Compression, 2021→2026**
- [B+] He et al.: "Deviations decline on average about 22 percentage points a year, consistent with an increase in arbitrage capital and competition among arbitrageurs." On Binance's April 2022 portfolio margining, which let arbitrageurs net collateral across spot and futures: "Deviations compress significantly following its introduction." — [arXiv 2212.06888](https://arxiv.org/abs/2212.06888)
- [B, my computation from exchange data] Deribit BTC-PERPETUAL funding, summed over each calendar year from the public hourly series `interest_1h`. Gross: no fees, no spread, no collateral yield, no margin drag.
  - 2021: 16.51% (18.6% of hours negative)
  - 2022: −2.26% (33.4% negative)
  - 2023: 6.88% (10.9% negative)
  - 2024: 10.30% (14.3% negative)
  - 2025: 5.39% (13.5% negative)
  - 2026, 1 Jan–31 Oct: 1.91% cumulative, 2.30% annualized (13.6% negative)

  Months with negative or near-zero annualized funding: 2025-03 −1.6%, 2025-11 0.1%, 2026-02 −1.4%, 2026-04 −0.1%, 2026-06 −0.2%. — [Deribit public API, get_funding_rate_history](https://www.deribit.com/api/v2/public/get_funding_rate_history?instrument_name=BTC-PERPETUAL). Caveats: this is one venue (an inverse contract) with its own funding formula. The Binance API (HTTP 451) and BitMEX API (HTTP 403) were blocked from this environment, and Coinglass was not reachable, so I could not cross-check across venues.
- [B, my computation from live product data] Ethena sUSDe APY from DefiLlama's daily series (pool 66985a81…), my computation:
  - 2024 (from 2024-02-16, n=320): mean 17.47%, median 14.19%, max 55.87%
  - 2025: mean 6.52%, median 5.37%
  - 2026 to 31 Oct: mean 4.20%, median 4.09%, range 3.16–5.71%
  - Daily snapshots: 2024-04-01 29.58%; 2025-01-01 12.12%; 2025-07-01 3.53%; 2026-04-01 3.55%; 2026-10-31 5.049%

  — [DefiLlama sUSDe pool](https://defillama.com/yields/pool/66985a81-9c51-46ca-9977-42b4fe7bc6df) ([API](https://yields.llama.fi/chart/66985a81-9c51-46ca-9977-42b4fe7bc6df))
- [B, my readout of DefiLlama data] USDe circulating supply:
  - Peak $14,819,842,076 on 2025-10-04
  - $12,700,706,819 on 2025-10-12
  - $6,303,188,836 on 2025-12-31
  - $5,921,266,702 on 2026-03-15
  - $4,519,580,111 on 2026-10-31

  — [DefiLlama stablecoin id 146](https://stablecoins.llama.fi/stablecoin/146). This agrees with a secondary Q1-2026 report headlined "$5.92B Supply". — [Stablecoin Insider](https://stablecoininsider.org/ethena-usde-q1-2026-report/)
- [B, press] CME basis, The Block, 9 April 2026:
  - "The annualized basis compressed in recent months as BTC fell from its highs above $120,000 to under $70,000."
  - "At ~5% basis versus ~4.5% risk-free, there's essentially zero incentive to run the trade"
  - "Average daily CME Bitcoin futures open interest (OI) fell to under $8 billion in March and $7.2 billion in early April"

  — [The Block](https://www.theblock.co/post/396722/cme-bitcoin-futures-activity-slumps-to-14-month-low-as-basis-trade-unwind-drains-institutional-demand)

**Tail-risk record (named events)**
- [B+] FTX, November 2022: "The FTX collapse led to significant negative funding rates on all solvent exchanges. Thus, the perpetual futures prices were lower than the spot prices on the solvent exchanges. Vice versa on the insolvent FTX." — [He et al.](https://arxiv.org/abs/2212.06888). The same paper links the narrowing carry to the downfall of Alameda Research and Three Arrows Capital, which it says pivoted away from the arbitrage around late 2021–early 2022: "The large declines in crypto prices in 2022 subsequently exhausted their capital and led to their bankruptcies." — [He et al.](https://arxiv.org/abs/2212.06888)
- [B, research note] Oct 10–11, 2025 crash, Galaxy Research (T. Pinakiewicz, 15 Oct 2025):
  - "more than $19B liquidated in ~24h"
  - ADL "kicked in on multiple venues, forcibly reducing user positions" and "ADL trims winners"
  - USDe traded "as low as ~$0.65 on Binance" while at par elsewhere, with Ethena's mint/redeem still live
  - wBETH fell to about $430 and BNSOL to about $34.90

  — [Galaxy](https://www.galaxy.com/insights/research/cryptos-flash-crash-liquidation-binance-adl-auto-deleveraging)
- [B, press headline] "Binance pays $283 million in compensation following Friday's depegs, covering user losses" (Oct 2025). — [The Block](https://theblock.co/post/374295/binance-pays-283-million-in-compensation-following-fridays-depegs-covering-user-losses)
- [B+] He et al. on Hyperliquid's "ability to process large-scale liquidations during the October 2025 crypto flash crash". — [arXiv 2212.06888](https://arxiv.org/abs/2212.06888)

**Access for a French retail resident**
- [A, regulator] AMF, 05 Feb 2026: PSANs had "jusqu'au 1er juillet 2026" to obtain MiCA authorisation. Unauthorised providers "devront cesser leur activité en France" and face "une peine de deux ans d'emprisonnement et 30 000 euros d'amende". The whitelist is official: "La liste blanche des PSCA autorisés est disponible sur le site de l'AMF." — [AMF](https://www.amf-france.org/fr/actualites-publications/actualites/lamf-rappelle-que-la-periode-transitoire-pour-les-psan-pour-continuer-de-fournir-des-services-sur)
- [B, press; search-snippet] Binance withdrew derivatives for French residents in 2022: "Dès le 2 août 2022, les Français ne seront plus autorisés à ouvrir de nouvelles positions". This covered futures, options, leveraged tokens and Dual Investment. — [Cryptoast](https://cryptoast.fr/binance-abandonne-produits-derives-double-investissement-france/)
- [B, press] Coinbase, 9 Mar 2026: regulated futures under its MiFID II licence across 26 European countries "including Germany, France, and the Netherlands", with perpetual-style and dated contracts. "Leverage of up to 10 times is available on selected contracts such as Bitcoin and Ethereum." — [Decrypt](https://decrypt.co/360420/coinbase-debuts-crypto-futures-european-traders-bitcoin-ethereum)
- [B, press; search-snippet] Kraken launched EEA perpetuals and fixed-maturity futures in May 2025 through its CySEC MiFID II subsidiary. — [Cointelegraph](https://cointelegraph.com/news/kraken-launches-regulated-crypto-derivatives-europe). One Trading launched MiFID II perpetuals in 2025 under a Dutch AFM OTF licence, with retail first in DE/NL/AT. — [Finance Magnates](https://www.financemagnates.com/cryptocurrency/exchange/this-dutch-exchange-debuts-first-eu-regulated-crypto-perpetuals-targets-retail-traders-next/)
- [B, press; search-snippet] France wants on-chain perps such as Hyperliquid brought under MiFID. Platforms would have to "Soit se conformer au cadre MiFID … soit géobloquer activement les résidents de l'Union européenne." — [Cryptoast](https://cryptoast.fr/perps-on-chain-france-mifid-hyperliquid-mica/)

### Inferences
- The passive carry premium has largely been arbitraged away, consistent with the 22-points-a-year decline He et al. document. For 2026 to date, both public proxies sit at or below the roughly 4.5% risk-free rate The Block cites: Deribit funding at 2.30% annualized and sUSDe at a mean 4.20%. Both are gross of the bot's own fees and spreads.
- Funding accrues on the short notional, but the bot's capital is spot notional plus perp margin. The yield on deployed capital is therefore below the funding rate, before fees.
- The 3.35 Sharpe that He et al. report is for an opportunistic convergence strategy, active only part of the time, through March 2024. It is not the passive always-on carry, and its period ends before the 2025–26 compression. It shows the trade could survive retail fees then. It does not show that it does now.
- Venue concentration is the dominant tail. In each named event the hedge failed through the venue, not through price:
  - FTX: the venue failed, and funding flipped negative on every other exchange.
  - Oct 2025: ADL closed winning shorts, and USDe collateral printed at $0.65 on one venue.
- A French bot would need a MiCA-authorised CASP for the spot leg and a MiFID-licensed venue for the perp leg, such as Coinbase or Kraken EU at up to 10x. Neither of the venues where the documented carry was largest, Binance futures and FTX, is or was open to French residents after Aug 2022.

### Gaps
- BIS sample period, exchanges, costs and any Sharpe or return figures: the PDF was behind a bot wall (it returned JavaScript), so only landing-page text was read.
- He et al. Table 9 annualized returns: only Sharpe ratios and drawdowns were extracted.
- Coinglass, Kaiko and Glassnode funding series were not accessible. Binance's own funding history (the largest venue) was blocked (HTTP 451), so my Deribit figures are a single-venue proxy.
- The FTX customer shortfall in dollars was not verified against court filings: secondary explainers cite about $8bn to $8.9bn.
- I did not verify sUSDe's regulatory availability to EU residents, or whether its quoted APY is net of protocol fees. Ethena's own transparency page was not fetched; it is JS-rendered.
- No source gave a minimum capital for a retail cash-and-carry bot.
- No retail-specific evidence of realised carry returns after costs was found.

## Q2 — Crypto time-series momentum / trend following

### Takeaway
Peer-reviewed evidence for crypto momentum exists, but the headline numbers are gross of costs and come from 2011–2018-era samples. Liu & Tsyvinski (RFS 2021) find time-series momentum. Liu, Tsyvinski & Wu (JF 2022) find cross-sectional momentum of about 3% a week, again gross. The only net-of-cost study found is practitioner work by Zarattini, Pagani & Barbon (SFI WP 25-80). It reports a net-of-fees Sharpe "above 1.5" through mid-March 2025 on a top-20 coin rotation, but the authors are commercially affiliated and it is a backtest. I found no independent post-2022 out-of-sample record.

### Cited Findings
- [A, peer-reviewed; NBER version quoted] Liu & Tsyvinski, "Risks and Returns of Cryptocurrency", RFS 34(6):2689–2727 (2021), NBER w24877 (Aug 2018).
  - Abstract: "we determine that there is a strong time-series momentum effect and that proxies for investor attention strongly forecast cryptocurrency returns."
  - "A one-standard-deviation increase in the current day's Bitcoin return predicts a 0.33 percent increase in the daily return over the next day."
  - "At the 1-week horizon, the average return of the top quintile is 11.22 percent per week with the Sharpe ratio of 0.45 while the average return of the bottom quintile is 2.60 percent per week with the Sharpe ratio of 0.19. However, for Ethereum, the momentum effect is less significant than for Bitcoin and Ripple."
  - Costs: not stated in these results.

  — [NBER w24877 PDF](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf); [RePEc record of RFS version](https://ideas.repec.org/a/oup/rfinst/v34y2021i6p2689-2727..html)
- [A, peer-reviewed] Liu, Tsyvinski & Wu, "Common Risk Factors in Cryptocurrency", JF 77(2):1133–1177 (April 2022). Abstract: "We find that three factors—cryptocurrency market, size, and momentum—capture the cross‐sectional..." The published version says ten characteristics form significant long-short strategies; the 2019 NBER version said nine. — [IDEAS/RePEc](https://ideas.repec.org/a/bla/jfinan/v77y2022i2p1133-1177.html)
- [A] LTW, NBER w25882 (May 2019); this is cross-sectional, not time-series.
  - "A zero-investment long-short strategy that longs the coins with comparatively large price increases and shorts the coins with comparatively small increases generates about 3 percent excess weekly returns (2.7 percent for one-week momentum, 3.3 percent for two-week momentum, 4.1 percent for three-week momentum, and 2.5 percent for four-week momentum strategies)."
  - "The momentum strategy in the below median size group generates statistically insignificant 0.6 percent weekly excess returns; the momentum strategy in the above median size group generates statistically significant 4.2 percent weekly returns."
  - Sample "beginning of 2014 to the end of 2018", with coins growing "from 109 in 2014 to 1,583 in 2018".
  - Costs: "Of course, this strategy does not take into account trading costs and the feasibility of short selling." When the short leg is Bitcoin instead, "The results virtually do not change."

  — [NBER w25882 PDF](https://www.nber.org/system/files/working_papers/w25882/w25882.pdf)
- [B, practitioner working paper; authors run Concretum Group] Zarattini, Pagani & Barbon, "Catching Crypto Trends; A Tactical Approach for Bitcoin and Altcoins", SFI Research Paper 25-80 (paper dated April 2025).
  - Results: "Sharpe ratio above 1.5" and "Annualized alpha of 10.8% relative to Bitcoin", described as "strong net-of-fees performance". — [Concretum page](https://concretumgroup.com/catching-crypto-trends-a-tactical-approach-for-bitcoin-and-altcoins/); [RePEc](https://ideas.repec.org/p/chf/rpseri/rp2580.html)
  - Data: survivorship-bias-free, 21,616 crypto-assets, January 2010 through mid-March 2025. Costs of 0.10%, 0.25% and 0.50% are tested, and the authors "propose a way to mitigate impact of these costs". — [CXO Advisory, 29 May 2025](https://www.cxoadvisory.com/technical-trading/crypto-asset-trend-following-strategies/)
  - Search-snippet, not confirmed on the fetched page: an ensemble of Donchian channels, a 25% volatility target, leverage capped at 200%.
- [C/B, search-snippet] A separate Concretum intraday BTC trend study reports a gross-of-fees Sharpe of about 1.6 over 2018–2025, against just below 0.8 for volatility-targeted long-only BTC. — [Concretum](https://concretumgroup.com/seasonality-in-bitcoin-intraday-trend-trading/)
- [B, search-snippet] Monash Centre for Financial Studies: shorter lookbacks can give high Sharpe ratios, but frequent rebalancing means costs can erode profits. — [Monash](https://www.monash.edu/business/monash-centre-for-financial-studies/our-research/all-projects/investment-strategy/trend-following-strategies-for-crypto-investors)
- [B, press] Context for 2025–26: BTC fell "from its highs above $120,000 to under $70,000" by April 2026. — [The Block](https://www.theblock.co/post/396722/cme-bitcoin-futures-activity-slumps-to-14-month-low-as-basis-trade-unwind-drains-institutional-demand)

### Inferences
- The academic tier-A results are gross and come from an early, small, illiquid market: 109 to 1,583 coins over 2014–2018. LTW find momentum is insignificant below median size, which is where shorting and costs bite hardest.
- The net-of-fees evidence rests on one commercially affiliated backtest. It is plausible, and it is the only crypto strategy here with stated cost sensitivity. It is still a backtest, not a live record.
- Trend following is the only crypto family reviewed whose mechanism benefits from one-directional moves. That makes it the natural hedge for the failure mode of grid bots.

### Gaps
- Liu & Tsyvinski's exact sample period and any cost-adjusted figures were not extracted; the published RFS text is paywalled.
- No independent post-2022 out-of-sample performance was found, by calendar year or after the Zarattini et al. publication.
- Zarattini et al.'s max drawdown, annualized return and per-cost-level results were not retrieved; the SSRN and CXO full results are paywalled.
- No live fund or ETP record of crypto trend following net of fees was found.

## Q3 — Grid bots and market-making bots popular with retail (Pionex, 3Commas, Binance grid)

### Takeaway
No independent, measured evidence of positive net performance for retail grid bots was found. The one academic-style analysis, an arXiv preprint from June 2025, shows plain grid trading has an expected return of "essentially zero" under simple assumptions, before fees. The documented failure modes are one-directional trends and third-party API-key compromise: the 3Commas leak of December 2022.

### Cited Findings
- [B/C, preprint; authors propose their own variant] Chen, Chen & Jang, "Dynamic Grid Trading Strategy: From Zero Expectation to Market Outperformance", arXiv 2506.11921, 13 Jun 2025: "we show that under simple assumptions, its expected return is essentially zero." The data are minute-level BTC and ETH, January 2021 to July 2024. Whether fees are included is not stated in the abstract. — [arXiv](https://arxiv.org/abs/2506.11921)
- [C, vendor/education; search-snippet] Strong trends are the failure mode: "during strong trends, buy-and-hold typically outperforms grid trading." — [KoinX](https://www.koinx.com/blog/what-is-a-grid-trading-bot). A bot vendor lists losses from "abrupt changes in market trends" and from poor grid parameters. — [Gainium](https://gainium.io/grid-bot)
- [C, vendor research; search-snippet] A grid-bot vendor's walk-forward study, May 2026, classified 61 of 85 folds (71.8%) as trending regimes, in which its gate held cash. The study is not independent. — [Yodacom Research](https://yodacom-site.pages.dev/research/grid-trading-walk-forward-2026)
- [B, press] 3Commas API-key leak, Dec 2022:
  - "Binance warns about 3Commas API leak, says users should disable keys" (28 Dec 2022). — [The Block](https://www.theblock.co/news/ecosystems/2022-12-28-binance-warns-about-3commas-api-leak-says-users-should-disable-keys-198295)
  - "3Commas CEO confirms API key leak following warning from CZ". — [Cointelegraph](https://cointelegraph.com/news/3commas-ceo-confirms-api-key-leak-following-warning-from-cz)
  - "Crypto platform 3Commas admits hackers stole API keys". — [BleepingComputer](https://www.bleepingcomputer.com/news/security/crypto-platform-3commas-admits-hackers-stole-api-keys)
  - Headline: "Binance and KuCoin users connected to trading bot 3Commas hit by 100,000 API leak". — [FXStreet](https://fxstreet.com/amp/cryptocurrencies/news/binance-and-kucoin-users-connected-to-trading-bot-3commas-hit-by-100-000-api-leak-202212290644)

### Inferences
- A grid is a short-volatility, mean-reversion position. It harvests small range-bound gains and accumulates inventory against a trend, much like short options without the premium-pricing discipline. With zero gross expectancy, exchange fees make the expected net return negative.
- Hosted bot platforms add counterparty risk on top of exchange risk. The 3Commas leak shows that API keys with trade rights can be abused, even without withdrawal rights. A self-hosted bot with IP-whitelisted keys removes one layer of that risk.
- "Evidence" from Pionex, 3Commas or Binance consists of marketing claims and selectively displayed bot leaderboards. No audited aggregate statistics exist.

### Gaps
- No independent study of live retail grid-bot outcomes (Pionex, 3Commas or Binance) was found.
- Total losses from the 3Commas leak are unverified: secondary sources cite individual claims and a $22M total without primary confirmation.
- No grid-bot evidence was found from the 2022 LUNA/FTX drawdowns or the Oct 2025 crash.

## Q4 — Options: volatility risk premium, put-writing, covered calls, short-vol ETPs, the wheel, 0DTE, costs and margin

### Takeaway
Tier-A index data show that systematic put-writing (Cboe PUT) roughly matched the S&P 500 with about two-thirds of its volatility over 1986–2023. The figures are gross of costs, and PUT has lagged in compound return since 2006. Covered calls embed an uncompensated equity-reversal exposure (Israelov & Nielsen). The short-vol tail is well documented: XIV lost 96.3% on 5 Feb 2018 and LJM fell from $9.82 to $1.94 NAV in five days. Retail 0DTE trading lost money in aggregate in 2021–2023, with more than $50M of over $70M lost attributed to transaction costs. Retail selling was profitable and buying carried the losses. No rigorous evidence for "the wheel" beyond its put-writing core was found. IBKR's portfolio margin requires USD 110,000.

### Cited Findings
**Cboe PutWrite (PUT) vs S&P 500**
- [A/B, Cboe-hosted guest post, 6 Oct 2023, Stephen Solaka, Belmont Capital] The window is "Since Inception, July 1986 – August 31, 2023".
  - Return: "Annualized returned: PUT Index +9.40% vs. the S&P 500 of +9.91%"
  - Volatility: "Standard deviation of returns: PUT Index 10.26% vs. 15.38% for the S&P 500"
  - Drawdown: "Maximum drawdown: PUT Index -32.66%, vs. -50.96% for the S&P 500."
  - Recovery: "Longest drawdown and recovery: PUT Index 30 months vs. 66 months for the S&P 500"
  - Costs: not stated. Whether the S&P 500 series is total return: not stated.

  — [Cboe Insights](https://www.cboe.com/insights/posts/generating-income-and-managing-risk-cash-secured-put-writing-in-a-low-equity-return-environment)
- [A, index data via CXO Advisory, 6 Apr 2016; gross] "Performance data are gross, not net."
  - Feb 2006–Dec 2015, PUT vs S&P 500 TR: annual compound return 6.6% vs 7.1%; SD 11.5% vs 15.1%; Sharpe 0.52 vs 0.46; max drawdown −33% vs −51%.
  - Jul 1986–Dec 2015: 10.1% vs 9.8%; SD 10.1% vs 15.3%; Sharpe 0.67 vs 0.47.
  - CXO notes that pre-launch index history was constructed retroactively.

  — [CXO Advisory](https://www.cxoadvisory.com/equity-options/performance-of-cboe-putwrite-indexes)

**Covered calls**
- [A, peer-reviewed; read via abstracts and search-snippets] Israelov & Nielsen, "Covered Calls Uncovered", FAJ 71(6):44–57 (2015). The brief cites 2014; the 2014 FAJ piece by the same authors is "Covered Call Strategies: One Fact and Eight Myths", FAJ 70(6).
  - "Typical covered call strategies collect the equity and volatility risk premiums but also embed exposure to a naive equity reversal strategy that is uncompensated."
  - The short-volatility exposure "realized a Sharpe ratio of nearly 1.0 but contributed only 10% of the risk".
  - The equity-reversal exposure contributed about 25% of the risk "but provided little return".
  - Their risk-managed version shows a "superior Sharpe ratio, reduced volatility, and reduced downside equity beta".
  - Sample period and costs were not stated in the parts read. The authors are AQR managers.

  — [AQR](https://www.aqr.com/Insights/Research/Journal-Article/Covered-Calls-Uncovered); [CFA Institute](https://rpc.cfainstitute.org/research/financial-analysts-journal/2015/covered-calls-uncovered); [EconPapers](https://econpapers.repec.org/RePEc:taf:ufajxx:v:71:y:2015:i:6:p:44-57)

**Short-volatility blow-ups**
- [B, press; etf.com fetch returned 403, so this is search-snippet text] XIV, 5 Feb 2018:
  - XIV "lost 96.3% of its value", and the issuer redeemed early.
  - The acceleration trigger was that the intraday indicative value on Feb 5, 2018 "was equal to or less than 20% of the prior day's closing indicative value".
  - The VIX rose about 115.6% that day.

  — [etf.com](https://www.etf.com/sections/news/inverse-vix-etn-shuts-down). Litigation: an appeals court revived the fraud suit against Credit Suisse in April 2021. — [Cohen Milstein / Reuters](https://cohenmilstein.com/credit-suisse-must-face-lawsuit-over-us-volatility-crash-reuters). Loss estimate in a paper title: "Material Misrepresentations in XIV Prospectus Led to $700 Million in Losses". — [SLCG](https://www.slcg.com/pdf/workingpapers/Material%20Misrepresentations%20in%20XIV%20Prospectus%20Led%20to%20$700%20Million%20in%20Losses.pdf)
- [B, search-snippet from a court complaint and SEC filing] LJM Preservation & Growth Fund, a seller of OTM S&P 500 futures options: NAV "plunged from $9.82 on February 2, to $1.94 on February 7" (2018). — [MFDF](https://www.mfdf.org/news-resources/news/2018/02/21/Trustees-Adviser-Named-in-Suit-after-Fund-Collapses-Amid-Market-Volatility-2795). The SEC (complaint filed May 2021) alleged the disclosed 20% worst-case daily loss came from taking the worst single day, "approximately 9%, doubled it, and then rounded up". — [SEC complaint](https://www.sec.gov/file/sec-complaint-2095); headline: "Risky Business Leads to $1 Billion Trading Loss". — [ai-CIO](https://www.ai-cio.com/news/risky-business-leads-to-1-billion-trading-loss-charges-for-fund-execs/)

**The wheel**
- [C, practitioner blog; search-snippet; costs not stated] A SPY wheel backtest (2010–2025, 30-delta) found it "consistently trails buy-and-hold in strongly trending bull markets". Its max drawdown was about 18%, against 34% for SPY in March 2020. — [LambdaFin](https://www.lambdafin.com/articles/wheel-strategy-spy-backtest)
- [C, open-source report; its own Sharpe figures flagged as buggy] 2015–2025: wheel CAGR 1.03% with a 15.08% max drawdown, against SPY 11.43% and 34.10%. — [Quant Companion report](https://glama.ai/mcp/servers/@Ademscodeisnotsobad/Quant-Companion-MCP/blob/69bda03318a3adee9cb1ed6be22eee58b031542c/backtest_results/OPTIONS_STRATEGIES_REPORT.md)

**0DTE**
- [A−/B, working paper; SSRN fetch returned 403, quotes via secondary sources] Beckmeyer, Branger & Gayda, "Retail Traders Love 0DTE Options… But Should They?", SSRN 4404704, March 2023.
  - Abstract as quoted: "Between February 2021 and February 2023, retail investors lost $184,000 on the average day; since the introduction of a daily expiration calendar in May of 2022, this number has grown to average losses of $358,000 per day." — [Bonus.com, search-snippet](https://www.bonus.com/news/zero-days-to-expiration-options-investment-or-gambling/)
  - "Across our sample period spanning a little over two years, retail investors together lost more than $70 million. More than 50 million of these losses are the result of the transaction costs they have to pay." — [Medium summary](https://medium.com/@y125789/retail-traders-love-0dte-options-paper-summary-6da4a7ff7d72)
  - "All in all, we find that retail investors' selling decisions are profitable. In contrast, their buying decisions are particularly troublesome and carry most of their aggregate losses." — [Medium summary](https://medium.com/@y125789/retail-traders-love-0dte-options-paper-summary-6da4a7ff7d72)
  - Bloomberg headline, 21 Apr 2023: "Day Traders Lose $358,000 Per Day Gambling on Zero-Day Options". — [Bloomberg](https://www.bloomberg.com/news/articles/2023-04-21/day-traders-lose-358-000-per-day-gambling-on-zero-day-options)
  - Conflict: CXO gives the sample as "January 2021 through February 2023", while the abstract quote says February 2021. — [CXO, 27 Apr 2023](https://cxoadvisory.com/individual-investing/retail-0dte-option-trader-performance)
- [B/C, literature review, 19 Mar 2024; study not named on the page] "Retail traders have lost an aggregated $125m and an average of $350k/day since the introduction of weekday expiration"; "0DTE contracts comprised more than 75% of retail trade volume for all SPX contracts." — [Neudata](https://neudata.co/literature-reviews/zero-day-to-expiry-options-a-losing-bet-for-retail-traders)
- [B, exchange research; the exchange has a commercial interest] Cboe, 2 May 2025: "retail now makes up around 50-60% of SPX 0DTE trading"; "customer activity continues to be extremely balanced in 0DTE options"; SPX 0DTE is "now averaging almost 2M contracts a day". The post makes no statement on retail profit and loss. — [Cboe](https://www.cboe.com/insights/posts/0-dt-es-decoded-positioning-trends-and-market-impact)
- [A−, working paper; search-snippet] Bandi, Fusari & Renò, "0DTE Option Pricing" (SSRN 4503344, 2023), estimate 0DTE return and variance risk premia, on intraday data from 2 Jan 2014 to 11 May 2023. Carey reports 0DTE at over 43% of daily option volume. — [JHU Carey](https://carey.jhu.edu/articles/risk-reward-insights-0dte-option-trading); [Liverpool seminar abstract](https://liverpool.ac.uk/management/conferences-and-events/0dte-option-pricing-seminar)
- [A−, working paper, 2025] India: retail traders "dominate index options trading" and "make significant losses", in "a market with an 80% share in option contracts traded worldwide". — [Agarwal, Ghosh, Prabhala & Zhao, CFR WP 25-09](https://econpapers.repec.org/RePEc:zbw:cfrwps:327125)

**Costs and margin for small accounts**
- [A, broker documentation] "An existing account must have at least USD 110,000 (or USD equivalent) in Net Liquidation Value to be eligible to upgrade to a Portfolio Margin account (in addition to being approved for uncovered option trading)." — [IBKR Campus glossary](https://www.interactivebrokers.com/campus/wp-json/wp/v2/glossary-terms/180035). IBKR's knowledge base gives USD 100,000 to maintain once enabled (search-snippet). — [IBKR KB](https://ibkb.interactivebrokers.com/de/node/3560)

### Inferences
- **Put-writing.** The two windows imply PUT's long-run edge reversed after 2015: about +0.3 points a year over 1986–2015, about −0.5 a year over 1986–Aug 2023. The sources and S&P series differ, so treat this as directional. Since every index figure is gross, net retail returns would be lower still, while the drawdown profile (−32.66%) stays equity-like.
- **0DTE.** This is the clearest "costs eat the edge" case. More than $50M of over $70M in retail losses was transaction costs. The paper finds selling profitable in aggregate, which is consistent with a VRP. Whether a small-account seller keeps it after commissions, spreads and assignment or gap risk is not established by these sources.
- **Short-vol tail.** XIV and LJM are the template. Positions that look steady for years can lose 80–96% in one to five sessions, and the stated worst-case loss estimates were far too low.
- **The wheel.** It is put-writing plus covered calls after assignment, so the PUT and covered-call evidence is the relevant tier-A proxy. The practitioner backtests do not establish an edge over buy-and-hold.
- **Account size.** Under USD 110,000, a retail account runs naked or cash-secured options under Reg-T-style margin. That caps how much premium a small account can sell per unit of capital.

### Gaps
- No Cboe official 10-year PUT vs S&P 500 TR figure through 2025–2026 was retrieved; the Cboe index dashboard was not fetched.
- The Beckmeyer et al. primary text, and any 2024–2026 update with seller-side net returns, could not be fetched (SSRN 403).
- No peer-reviewed wheel study was found.
- Rules for EU retail on US-listed options at IBKR (Ireland entity), such as PRIIPs/KID or approval tiers, were not verified, nor portfolio-margin availability for EU clients.
- AQR / Alpha Architect VRP primers were not fetched.
- Other short-vol blow-ups (OptionSellers.com, Nov 2018; Malachite, Mar 2020) were not verified.

## Q5 — Retail forex/CFD expert advisors (EAs)

### Takeaway
Regulator base rates are unambiguous:
- ESMA (27 Mar 2018): "74-89%" of retail CFD accounts lose money, with average losses of €1,600 to €29,000 per client.
- AMF (Oct 2014): more than 89% of 14,799 French active retail forex/CFD clients lost money over 2009–2012, about €10,900 each on average. The AMF noted that ads promote placing orders "de manière automatique".
- AMF (Dec 2023): 7 to 8 clients in 10 lose money on average.

Current broker disclosures, self-reported and compiled in 2026 by an aggregator, average about 71%, ranging from 51% to 81%. No independent, methodologically sound Myfxbook/EA survival study exists that I could find.

### Cited Findings
- [A, regulator] ESMA, 27 Mar 2018: "74-89% of retail accounts typically lose money on their investments", with "average losses per client ranging from €1,600 to €29,000". Measures:
  - Leverage caps from 30:1 down to 2:1, depending on the underlying's volatility
  - Negative-balance protection per account
  - A standardised warning showing the provider's percentage of losing retail accounts

  — [ESMA](https://www.esma.europa.eu/press-news/esma-news/esma-agrees-prohibit-binary-options-and-restrict-cfds-protect-retail-investors)
- [A, regulator study, text extracted from the PDF] AMF, *Lettre de l'Observatoire de l'épargne* n°10, Oct 2014:
  - Population and period: "14 799 investisseurs particuliers actifs", 2009–2012.
  - Results: "un taux de clients perdants de plus de 89 %" and "un résultat négatif moyen de près 10 900 euros par client".
  - Totals: "Sur 4 ans, 13 224 clients ont perdu au total près de 175 millions d'euros, tandis que les 1 575 clients restants ont gagné au total 13,8 millions d'euros."
  - By provider: "le pourcentage de clients perdants varie, selon les prestataires et les années, de 75 % à 89 %".
  - On automation, under the heading "Trader plus pour perdre plus": "Les publicités affichent souvent la possibilité de passer de nombreux ordres, parfois de manière automatique, ou de pouvoir passer des ordres d'une taille importante avec un dépôt minimum, grâce à un effet de levier maximum."
  - The AMF found the most active and largest-order clients lost more (paraphrase).

  — [AMF PDF](https://www.amf-france.org/sites/institutionnel/files/contenu_simple/lettre_ou_cahier/lettre_observatoire/La%20lettre%20de%20l%27Observatoire%20de%20l%27epargne%20de%20l%27AMF%20-%20ndeg%2010%20-%20Octobre%202014.pdf)
- [A, regulator] AMF fact sheet "Forex : attention danger", Dec 2023: brokers' published share of losing clients is "élevé, entre 7 et 8 clients sur 10 en moyenne". Also: "depuis le 1er août 2018 : il n'est pas possible d'utiliser un effet de levier supérieur à 30 sur les principales paires". — [AMF PDF](https://amf-france.org/sites/institutionnel/files/private/2023-12/2023_forex_attention_danger.pdf)
- [C, aggregator of self-reported broker disclosures; "Updated 2026"] "71.0% of retail accounts lose money". Lowest eToro 51.00%, highest FXTM 81.00%; IG 70%, XTB 74%, Saxo 65%, Plus500 80%. The page is inconsistent on whether it covers 49 or 50 brokers. — [BrokerRank](https://brokerrank.net/research/retail-loss-rates). An April 2026 UK sample lists eToro 51%, XTB 71% and Saxo 59% (search-snippet). — [The Investors Centre](https://www.theinvestorscentre.co.uk/trading/statistics/cfd-trading/)
- [B, broker's own mandated disclosure; undated] Libertex's French pages show losing-account rates of 79% to 84%, varying by page (search-snippet). — [Libertex](https://libertex.com/fr/risk-warning)
- [B, press headline] Poland 2025: "Forex and CFD Trader Pool Climbs 50% in 2025 as Total Losses Hit Record 2.7B Zlotys". — [Finance Magnates](https://www.financemagnates.com/forex/analysis/polands-forex-and-cfd-trader-pool-climbs-50-in-2025-as-total-losses-hit-record-268b-zlotys)

### Inferences
- The losing-account share has stayed around 70–90% from 2009–2012 (AMF) through 2018 (ESMA) to 2023 (AMF) and 2026 (broker disclosures), despite the 2018 leverage caps. Retail CFD/FX automation starts from a strongly negative base rate.
- The AMF explicitly ties "automatic" order placement and high activity to marketing and to larger losses. An EA raises activity, so it raises cost drag.
- Spread and financing costs make the CFD wrapper itself the main obstacle. Even a zero-edge EA loses its turnover times the spread.

### Gaps
- No independent study of Myfxbook-verified or MQL5-signal EA survival was found. The figures circulating, such as "8% remain profitable after 12 months", have no methodology and are not cited here.
- No AMF study after 2014 on retail CFD, forex or crypto-derivative outcomes was found. The 2023 fact sheet gives only a range.
- Broker percentages are self-reported, use different periods, and come from aggregator compilations. IG's French homepage, as fetched, showed no percentage.
