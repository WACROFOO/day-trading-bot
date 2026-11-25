# Crypto yield, carry and DeFi "passive income" strategies (2022 – Nov 2026): realised returns, tail risks, and access for a France-based retail investor under MiCA

Research date: 25 November 2026. Investor context: France-based retail, small account, no leverage, prefers regulated EU venues.

**How to read this file.** "DefiLlama-computed" means I pulled the daily yield history from DefiLlama's public yields API on 2026-11-25 and averaged the daily APY readings for each calendar year myself. Each DefiLlama daily APY is a trailing yield the protocol reports, so it reflects yield actually paid out, not an advertised forward rate. The averages are simple means, not compounded, and 2026 runs only to 25 Nov. The pool pages are at `https://defillama.com/yields/pool/<id>` and the raw series at `https://yields.llama.fi/chart/<id>`. Figures that come from vendor marketing, affiliate or review sites, or advertised APYs are flagged as such.

---

## 1. Funding-rate / cash-and-carry arbitrage (long spot, short perpetual), and products that package it (Ethena USDe)

### Takeaway
Funding on BTC perpetuals was very high in 2020–21 (17–31% a year gross on Binance). Since then it has collapsed: about 4% in 2022, 8% in 2023, 12% in the 2024 ETF/bull year, about 5% in 2025 and about 2.6% in 2026 to date. That puts it at or below euro money-market yields, even before fees, margin drag and counterparty risk. Ethena's sUSDe, which packages this trade, followed the same path: realised about 17.5% in 2024, 6.5% in 2025 and 4.3% in 2026 to date. The packaged trade also showed new tail risks: a $0.65 print on Binance (10 Oct 2025), a 67% fall in supply, and a BaFin-forced exit from the EU in 2025. EU retail can now reach perpetuals only through MiFID-licensed venues. Since ESMA's February 2026 statement, those are likely treated under CFD rules (leverage caps, margin close-out), which squeezes the capital efficiency of an unleveraged hedge.

### Cited Findings
**Funding levels by year (gross, before fees)**
- Funding a constant short collected on Binance's BTCUSDT perpetual, summed over each calendar year: **2020 17.2%; 2021 30.6%; 2022 4.2%; 2023 7.9%; 2024 12.0%; 2025 5.1%; 2026 2.6% (to 29 Oct)**. The source is Binance's public funding history, 7,820 settlements from 10 Sep 2019 to 29 Oct 2026. Funding was **negative (shorts paid longs) in 14% of settlements**, and below −0.05% in 0.2%. Article published 14 Apr 2026, updated 29 Oct 2026. Caveat: Altrady is a trading-tool vendor blog, but the data is public and the method is stated. — [Altrady, "Crypto Funding Rates Explained, With 7 Years of BTC Data"](https://www.altrady.com/blog/crypto-trading-strategies/crypto-funding-rates-explained)
- A Coinglass snapshot on the research date showed BTC perpetual funding near 0.0011% per 8 hours, about 1.2% annualised (point reading only, cited via search summary). — [Coinglass BTC futures](https://www.coinglass.com/currencies/BTC/futures)
- Academic benchmark: BIS Working Paper 1087, "Crypto carry" (Schmeling, Schrimpf and Todorov; first published Apr 2023, revised Oct 2025). Findings:
  - Crypto futures carry (the futures–spot basis) is "averaging above 10% annually" and can reach "up to 60% p.a."
  - It is driven by trend-chasing retail demand for leverage and by scarce arbitrage capital.
  - High carry predicts future price crashes.
  - The arbitrage is risky because margin spikes and liquidations happen during drawdowns.
  - Perpetuals made up more than 98% of BTC futures volume in their sample.
  - Sources: [BIS WP 1087 summary page](https://bis.org/publ/work1087.htm) and [PDF](https://www.bis.org/publ/work1087.pdf); the perpetual share is via the [arXiv 2510.14435 survey](https://arxiv.org/pdf/2510.14435)

**Compression after US spot ETFs (Jan 2024) and the 2025 regime**
- The CME annualised basis fell to about 4% in Feb 2025. That was the lowest since spot ETFs began trading in Jan 2024 and below the roughly 5% US risk-free rate. — [CoinDesk, 25 Feb 2025](https://www.coindesk.com/markets/2025/02/25/u-s-bitcoin-etfs-post-year-s-2nd-biggest-outflows-as-basis-trade-drops-below-5)
- The basis rebounded to nearly 9% annualised by May 2025. — [CoinDesk, 20 May 2025](https://www.coindesk.com/markets/2025/05/20/bitcoin-etf-inflows-surge-as-basis-trade-nears-9-signaling-renewed-demand)
- Late 2025: the 30-day annualised basis compressed from 6.63% to 4.46%, with 93% of recent days below a 5% breakeven. About $4B of Oct–Nov 2025 ETF outflows were attributed to basis-trade unwinds. — [CoinDesk, 4 Dec 2025](https://www.coindesk.com/markets/2025/12/04/usd4b-bitcoin-etf-outflows-in-oct-nov-reflect-basis-trade-unwind-not-capitulation-research-analyst)
- The CME basis reportedly hit −2.35% in late 2025 during a brief backwardation. This is low-quality, single-source glossary content and unverified. — [Spark glossary](https://www.spark.money/glossary/basis-trade)

**Exchange counterparty risk: FTX (Nov 2022)**
- The FTX plan repaid about 119% of claims to 98% of creditors. Claims were set in dollars at prices on the 11 Nov 2022 bankruptcy filing date (the "petition date"), so creditors received USD, not coins. — [PYMNTS, Oct 2024](https://www.pymnts.com/legal/2024/ftx-creditors-will-earn-119-profit-in-bankruptcy-settlement/)
- Major repayments began 30 May 2025. BTC claims were then worth only about 20% of BTC's market price because they had been dollarised at petition-date prices. — [The Block, 29 Mar 2025](https://www.theblock.co/post/348774/ftx-major-repayments-to-begin-may-30-btc-claims-currently-worth-just-20-of-market-price)

**Ethena USDe / sUSDe (the packaged carry trade)**
- DefiLlama-computed realised sUSDe APY (pool 66985a81, Ethereum):
  - **2024 (from 16 Feb): mean 17.47%, median 14.19%, max 55.87%**
  - **2025: mean 6.52%, median 5.37%, range 0.13–14.78%**
  - **2026 YTD: mean 4.27%, range 3.16–5.71%**
  - Latest reading 4.95% (25 Nov 2026); sUSDe TVL $1.14B
  - Source: [DefiLlama sUSDe pool](https://defillama.com/yields/pool/66985a81-9c51-46ca-9977-42b4fe7bc6df)
- The 2024 peak of about 55.9% in March 2024 and the August 2024 trough of about 4.3% match aggregator reports. The secondary sources disagree on the 2025 average: one says about 19%, which conflicts with the DefiLlama series and with others citing a 4–15% range. — [eco.com](https://eco.com/support/en/articles/14798653-susde-explained-ethena-s-yield-bearing-stablecoin); [StableCoinInsider Q1 2026](https://stablecoininsider.org/ethena-usde-q1-2026-report/)
- USDe supply (DefiLlama stablecoins): about $0.09B on 1 Jan 2024, $5.88B on 1 Jan 2025, **peak $14.82B on 4 Oct 2025**, $9.56B on 31 Oct 2025, $6.30B on 31 Dec 2025, and **$4.89B on 25 Nov 2026 (−67% from peak)**. — [DefiLlama USDe](https://defillama.com/stablecoin/ethena-usde)
- On 10 Oct 2025 (the "10/10" mass-liquidation day), USDe printed about **$0.65 on Binance**. It held near peg on-chain and on Curve, and minting and redemption kept working. Ethena blamed Binance's internal oracle; Binance blamed thin liquidity. Holders who had posted USDe as collateral on Binance were exposed to liquidations at the bad price. — [21Shares](https://www.21shares.com/en-eu/insights/why-did-ethenas-stablecoin-remain-stable-onchain-but-depegged-on-binance); [CoinGecko](https://www.coingecko.com/learn/october-10-crypto-crash-explained); [Cointelegraph](https://cointelegraph.com/news/ethena-usde-market-cap-drops-october-crash-deleveraging)
- OKX's CEO blamed a Binance **12% APY promotion on USDe** (an advertised, exchange-subsidised rate) for creating leverage loops; Binance disputes this. — [MEXC News summary](https://www.mexc.com/news/604192)
- sUSDe moved from a pre-crash average of 6.58% to a post-crash average of 4.15% (secondary source). — [cryptotether.com](https://cryptotether.com/articles/why-ethena-susde-yield-is/)
- **EU regulatory status:**
  - **21 Mar 2025:** BaFin barred Ethena GmbH from offering USDe, citing MiCA breaches, and froze its reserve assets.
  - **25 Jun 2025:** BaFin ordered a wind-down. Ethena said it would "no longer be pursuing the MiCAR authorization in Germany."
  - EU holders had until **6 Aug 2025** (42 days) to redeem through Ethena GmbH. After that, claims went to Ethena (BVI) Ltd offshore; secondary trading continued.
  - Sources: [The Block](https://www.theblock.co/post/347532/regulator-halts-ethenas-usde-stablecoin-offering-in-germany-over-concerns); [Cointelegraph](https://cointelegraph.com/news/ethena-bafin-usde-redemption-plan-eu-exit); [Invezz](https://invezz.com/news/2025/06/25/ethena-gmbh-to-shut-down-in-eu-after-bafin-orders-42-day-usde-redemption/)

**EU retail access to perpetuals**
- Perpetuals are financial instruments under MiFID II, not crypto-assets under MiCA. MiCA Art. 2(4) excludes crypto-assets that qualify as financial instruments, so a MiCA licence alone is not enough (affiliate-type comparison site). — [Cryptoticker, EU futures exchanges compared](https://cryptoticker.io/en/crypto-futures-exchanges-eu/)
- **Kraken, 20 May 2025:** rolled out perpetual and fixed-maturity futures to retail and institutional clients in the EEA under MiFID II, through Greenfield Wealth, a Cyprus (CySEC) investment firm it acquired. Leverage limits and France are not mentioned in the article. — [CoinDesk](https://www.coindesk.com/business/2025/05/20/kraken-rolls-out-regulated-crypto-derivatives-in-europe)
- **Coinbase, reportedly 9 Mar 2026:** launched regulated futures for 26 European countries through a Cypriot MiFID entity. This is from affiliate/review sites only and unverified. Bitpanda reportedly offers no perpetuals but offers crypto CFDs at the retail 2:1 cap. — [Datawallet](https://www.datawallet.com/crypto/best-crypto-futures-exchanges); [Coinperps](https://www.coinperps.com/learn/best-crypto-futures-platforms-in-europe)
- **ESMA public statement, 24 Feb 2026:** derivatives marketed as "perpetual futures/contracts", including crypto ones, are "likely to fall within the scope of the existing national product intervention measures on CFDs". Where they do, the following apply:
  - leverage limits
  - a mandatory risk warning
  - margin close-out
  - negative balance protection
  - a ban on monetary and non-monetary benefits
  - a narrow target market and an appropriateness assessment
  - a KID (PRIIPs)
  - Sources: [Regulation Tomorrow (Norton Rose Fulbright)](https://www.regulationtomorrow.com/2026/02/esma-reminds-firms-of-their-obligations-under-cfd-product-intervention-measures-amid-rising-offerings-of-perpetual-futures/); [MFSA circular, Mar 2026](https://www.mfsa.mt/wp-content/uploads/2026/03/Circular-on-ESMA-Public-Statement-Identifying-Derivatives-within-the-Scope-of-CFDs-National-Product-Intervention-Measures.pdf); [Paperjam](https://en.paperjam.lu/article/perpetual-does-not-mean-unregulated-esma)
- The **2:1 leverage cap** for crypto-referenced CFDs comes from secondary commentary on the CFD regime, not from the ESMA statement text I saw. — [Cryptoticker](https://cryptoticker.io/en/perpetuals-mifid-classification-leverage-cap/); [FX-Brokers.eu](https://fx-brokers.eu/blog/esma-perpetual-futures-cfd-rules-2026)

### Inferences
- **Net yield for an EU retail carry trader is probably below the euro risk-free rate in 2025–26.**
  - Gross BTC funding was 5.1% in 2025 and 2.6% in 2026 to date (Binance).
  - Under a CFD-style regime with a 2:1 cap, a €1,000 spot hedge needs at least about €500 of margin, so yield on total capital is roughly two-thirds of funding.
  - Then come trading fees, spreads and the 14% of periods with negative funding.
  - Spiko's euro T-bill fund paid about 2.35–2.43% net in Nov 2026 (section 5) with far less risk.
- **The short perpetual leg is a leveraged derivative even though the combined position is delta-neutral.** That conflicts in form with a "no leverage" preference. Margin close-out in a sharp rally can force the short shut and leave the investor unhedged long.
- **Carry is regime-dependent and pro-cyclical.** It pays most in euphoric bull phases (2021, Q1 2024), which BIS shows tend to precede crashes. A small investor cannot capture the 2021-type levels on a regulated EU venue today.
- **FTX lesson.** A delta-neutral carry trader at FTX lost the use of their capital for about 2.5 years, then got back about 119% of the petition-date USD value. That is less damaging than for coin holders, but liquidity and opportunity cost were total. My inference: delta-neutral equity is close to a USD claim.
- **Ethena (USDe/sUSDe) is not a MiCA-compliant product for EU retail after 2025.** Holding it means self-custody outside MiCA protections. Its 2025–26 realised yield (4–6.5%) offers a thin premium over T-bills for exposure to exchange custody, funding reversal, smart-contract and depeg/liquidity risk.

### Gaps
- I found no independent year-by-year ETH funding series. Binance and BitMEX APIs were geo-blocked (HTTP 451/403) from the research environment, so the BTC series rests on one vendor blog that used public Binance data.
- I could not verify Kraken EU's retail leverage cap on perpetuals, whether it serves French residents specifically, or the Coinbase EU futures launch details. The figures above come from affiliate comparison sites.
- No source quantified the realised net return of a retail-sized carry trade after fees in the EU.
- I did not confirm whether MiCA-authorised CASPs serving France list USDe.

---

## 2. Staking: ETH, SOL and liquid staking (Lido stETH); slashing and lock-up risk; EU exchange staking under MiCA; French tax

### Takeaway
Realised ETH staking yields have fallen every year: about 4.3–4.5% in 2022–23, 3.2% in 2024, 2.8% in 2025 and 2.4% in 2026 to date (Lido, DefiLlama). SOL liquid staking paid about 7–7.5% in 2025 and 5.4–5.8% in 2026, but much of that is inflation: real yield was about 2–3% in 2025. Staking does not hedge price risk. The tail events were liquidity events, not slashing: stETH traded about 5–6% below ETH in June 2022, and the ETH exit queue reached about 46 days in September 2025. Under MiCA, staking-as-a-service is legal for EU retail when done by a CASP authorised for custody, and rewards must be passed to clients. French tax treatment of staking rewards still has no specific official doctrine. Gains fall under the 31.4% PFU flat tax from 2026.

### Cited Findings
**ETH staking yields**
- DefiLlama-computed **Lido stETH** realised APY:
  - **2022 (from 3 May): mean 4.53%** (median 4.0%)
  - **2023: 4.32%**
  - **2024: 3.17%**
  - **2025: 2.82%**
  - **2026 YTD: 2.41%**
  - Latest 2.39%; stETH TVL about $15.99B (25 Nov 2026)
  - Source: [DefiLlama Lido stETH](https://defillama.com/yields/pool/747c1d2a-c668-4682-b9f9-296708a3dd90)
- DefiLlama-computed **Rocket Pool rETH**: **2023 3.84%; 2024 2.80%; 2025 2.56%; 2026 YTD 2.16%**. — [DefiLlama rETH](https://defillama.com/yields/pool/d4b3c522-6127-4b89-bedf-83641cdcd2eb)
- CoinDesk's Composite Ether Staking Rate (CESR) averaged **2.98%** over the 180 days to 28 Sep 2025. — [Grayscale Research, "Staking 101"](https://research.grayscale.com/reports/staking-101-secure-the-blockchain-earn-rewards)
- CESR was about 3.75% shortly after its 2023 launch. — [CoinDesk, 27 Sep 2023](https://www.coindesk.com/consensus-magazine/2023/09/27/how-ethereum-staking-stacks-up-in-the-proof-of-stake-landscape)

**SOL staking yields**
- DefiLlama-computed **JitoSOL**: **2025 (from 26 Mar) mean 6.95%; 2026 YTD 5.40%**; latest 5.02%. — [DefiLlama JitoSOL](https://defillama.com/yields/pool/0e7d0722-9054-4907-8593-567b353c0900)
- DefiLlama-computed **Marinade mSOL**: **2025 (from 26 Feb) 7.52%; 2026 YTD 5.77%**. — [DefiLlama mSOL](https://defillama.com/yields/pool/b3f93865-5ec8-4662-90a0-11808e0aa2bd)
- Real yield is nominal yield minus inflation. A 2025 forum estimate put it at about 2.3% (about 7% nominal against 4.7% inflation). Solana inflation decays about 15% a year toward a 1.5% floor. — [Blockworks Solana staking yields](https://blockworks.co/analytics/solana/solana-supply-staking-and-validators/solana-staking-yields); [Solana forum](https://forum.solana.com/t/proposal-for-introducing-a-programmatic-market-based-emission-mechanism-based-on-staking-participation-rate/3294?page=3)
- **SIMD-0228**, a proposal to cut SOL inflation from about 4.7% toward about 1.5%, **failed** its validator vote in March 2025, so the fixed schedule continues. — [CoinDesk, 13 Mar 2025](https://www.coindesk.com/business/2025/03/13/s); [Blockworks](https://blockworks.co/news/what-simd-0228-failing-means-for-solana)

**Liquidity and lock-up tail events**
- **June 2022 stETH discount:** stETH traded about 4–6% below ETH (5%+ on Curve on 14 Jun 2022).
  - The Curve stETH/ETH pool was skewed to 20% ETH / 80% stETH.
  - Curve pool liquidity fell from $1.7B (18 May) to $670M (21 Jun).
  - Celsius and Three Arrows Capital withdrew about $780M from the pool on 12 May 2022, and 3AC-linked wallets sold more than 56,000 stETH.
  - Sources: [Fortune, 17 Jun 2022](https://fortune.com/2022/06/17/steth-token-trading-pool-crypto-investors); [Fortune/Nansen, 29 Jun 2022](https://fortune.com/2022/06/29/crypto-winter-crash-nansen-three-arrows-capital-celsius-ether-staked-depeg/); [The Block, 10 Jun 2022](https://theblock.co/news/defi/2022-06-10-lido-staked-ether-steth-discount-drops-to-5-for-second-time-in-one-month-151380); [Kaiko](https://marketing.kaiko.com/celsius-reaches-boiling-point)
- **2025 ETH exit queue:** a record of about 2.5M ETH (about $12B) with waits of **43–46 days** in mid-September 2025. Exits are throttled to at most 57,600 ETH per day; validators keep earning while they wait. — [Figment](https://www.figment.io/insights/ethereums-exit-queue-hits-record-high-what-stakers-need-to-know/); [Cointelegraph](https://cointelegraph.com/news/ethereum-exit-queue-10b-record-selling-pressure)
- An earlier peak, during Celsius's 2024 unstaking, averaged a 5.6-day wait. — [The Block](https://www.theblock.co/amp/post/270578/ethereum-validator-exit-queue-celsius-figment)

**MiCA treatment of staking**
- ESMA's position:
  - MiCA has no staking-specific rules, and holders staking their own assets need no licence.
  - When a provider holds client assets and stakes them, ESMA treats this as **ancillary to custody and administration**, so it needs CASP authorisation (Art. 75).
  - **Rewards must be allocated to the clients** (the provider may charge a fee).
  - Explicit client consent is required.
  - Providers remain liable under Art. 75(8), and the assets must be returnable.
  - Sources: [ESMA Q&A 2067](https://www.esma.europa.eu/publications-data/questions-answers/2067); [FX News Group summary](https://fxnewsgroup.com/forex-news/cryptocurrency/esma-clarifies-treatment-of-crypto-staking-services-under-mica)
- ESMA's response to the Commission's MiCA review (Sep/Oct 2026) proposes enhanced disclosures on rewards, lock-up periods, slashing, validator selection, fees and insolvency treatment. This is a proposal, not law. — [ESMA response, ESMA75-113276571-1721](https://www.esma.europa.eu/sites/default/files/2026-09/ESMA75-113276571-1721_Response_to_the_EC_consultation_MiCA_regulation_review.pdf); [HSF Kramer note, Oct 2026](https://www.hsfkramer.com/notes/madrid/2026-posts/note-esma-response-ce-mica-october-2026)
- The European Commission ran a consultation on lending, borrowing and staking from May to 30 Sep 2026. — [CCSF Recommendation, 10 Nov 2026 (Banque de France)](https://www.banque-france.fr/system/files/2026-11/CCSF_Recommandation_crypto-actifs.pdf)
- **CCSF recommendation, 10 Nov 2026:**
  - It finds that lending, borrowing and staking are growing while "soulèvent des risques élevés de perte financière, de liquidité, de contrepartie ou de conflits d'intérêts pour les investisseurs particuliers".
  - It asks for specific consumer-protection rules.
  - It wants intermediaries to disclose each underlying service's provider and status, "afin d'éviter que l'agrément MiCA d'un prestataire soit perçu comme couvrant l'ensemble des activités accessibles sur sa plateforme".
  - It calls labels such as "épargne"/"livret sur crypto-actifs" misleading and proposes replacing "récompense" with "rémunération".
  - Source: [CCSF Recommendation](https://www.banque-france.fr/system/files/2026-11/CCSF_Recommandation_crypto-actifs.pdf)

**French tax**
- No specific BOFiP doctrine on staking or crypto lending has been published, and qualification is reasoned by analogy with mining. — [hashtagfinance.fr](https://hashtagfinance.fr/blog/fiscalite-du-staking-et-du-lending-crypto-en-france/)
- Other blogs claim taxation as **BNC on receipt** (non-commercial income) and then PFU on sale, or taxation at the progressive income-tax scale. These are conflicting secondary views. — [calculetontaux.fr](https://calculetontaux.fr/articles/staking-mining-nft-fiscalite-2026); [financetothetop.fr](https://www.financetothetop.fr/staking-fiscalite-francaise/)
- The **2026 social security financing law (LFSS 2026)** raised CSG on capital income from 9.2% to 10.6%. Social levies go from 17.2% to 18.6%, so the **PFU becomes 31.4%** (12.8% income tax + 18.6%), and this applies to crypto gains under CGI art. 150 VH bis.
  - Moneyvox says the increase applies retroactively to 2025 gains for digital assets; other sources say it starts with 2026 gains (conflict).
  - Sources: [Moneyvox](https://www.moneyvox.fr/impot/actualites/108257/impots-2026-une-hausse-de-la-csg-retroactive-qui-va-alourdir-la-revente-de-vos-cryptos); [La finance pour tous](https://www.lafinancepourtous.com/2026/01/20/csg-quels-sont-les-placements-concernes-par-la-hausse-de-la-contribution-sociale-generalisee/); [Meilleurtaux](https://placement.meilleurtaux.com/placement-financier/actualites/2026-avril/flat-tax-a-31-4-ce-qui-change-depuis-janvier-2026.html)

### Inferences
- **After tax, small-account ETH staking yields about 1.7–2% nominal**: about 2.4% gross minus the 31.4% PFU, if rewards are taxed when sold. That is below euro money-market funds, and the investor carries full ETH price risk. Staking is a marginal enhancement for someone who already wants to hold ETH or SOL long-term, not a standalone income strategy.
- **SOL's higher nominal yield is mostly dilution compensation.** Non-stakers are diluted by about 4–5% a year, so staking SOL is closer to "avoiding dilution" than earning income.
- **The main tail risk for retail is liquidity mismatch, not slashing.** This means LST discounts in a forced-selling cascade, as in June 2022, and exit queues of several weeks, as in September 2025.
- **Staking through a MiCA CASP is the most "regulated" crypto yield available to French retail.** Rewards are pass-through, the assets are under custody rules and liability applies. The tax treatment of rewards is still uncertain.

### Gaps
- I found no reliable statistics on slashing frequency or size for Lido, Coinbase or Kraken validators. Slashing events appear rare and small, but that is unsourced.
- I could not confirm which MiCA-authorised platforms offer ETH or SOL staking to French residents as of Nov 2026, or their fee take (for example, Coinbase, Kraken, Bitpanda, Coinhouse). The AMF white list shows authorisations but not staking availability.
- There is no official DGFiP or BOFiP guidance on when staking rewards are taxed. A tax adviser or rescrit (formal ruling) would be needed.
- The 2022 Lido figure starts in May 2022, and the 2022 SOL series is missing from DefiLlama for the LSTs checked.

---

## 3. Lending / "Earn" products: the 2022 CeFi collapses, regulated EU earn offers now, and DeFi lending (Aave, Compound)

### Takeaway
The 2022–23 CeFi "earn" collapses froze customer funds for one to three years, with very uneven recoveries:
- Gemini Earn/Genesis: 100% in kind after about 19 months.
- BlockFi: 100% of allowed claims, helped by FTX recoveries.
- Celsius: roughly 65% or more after several rounds (sources conflict).
- Voyager: roughly 36–72% (sources conflict).

MiCA does not regulate crypto lending. It bans CASPs from paying interest on e-money tokens such as USDC and EURC (Art. 50), and French authorities (CCSF, Nov 2026) are pushing for specific rules and warning against "savings"-style marketing. DeFi lending is the only open venue for stablecoin yield. Aave v3 USDC on Ethereum realised about 3.8% (2023), 7.2% (2024), 4.1% (2025) and 3.5% (2026 to date), which is unregulated and similar to or below money-market funds since 2025.

### Cited Findings
**CeFi collapses and recoveries**
- **Celsius:** paused withdrawals in mid-June 2022 and filed Chapter 11 on 13–14 Jul 2022. It owed **about $4.7B to customers**, with $5.5B of liabilities against $4.3B of assets (a $1.2B hole). — [Blockworks](https://blockworks.com/news/celsius-faces-heat-for-1-2b-balance-sheet-hole-customers-owed-4-7b); [Fortune, 13 Jul 2022](https://fortune.com/crypto/2022/07/13/celsius-files-bankruptcy-chapter-11-withdrawals/)
- Celsius recovery estimates conflict. One source gives 64.9% cumulative after three distributions (target 67–85%); another gives about 93% of eligible claim value; a third says about 70% or more of claims resolved by mid-2026 after a fourth distribution. All are secondary aggregators. — [Dropstab research](https://news.dropstab.com/research/crypto-bankruptcies); [cryptoandmoneysearch](https://cryptoandmoneysearch.com/celsius-claim)
- **Voyager:** froze withdrawals on 1 Jul 2022 and filed on 6 Jul 2022 after Three Arrows Capital defaulted on a $650M loan. — [CNBC, 17 Jul 2022](https://www.cnbc.com/2022/07/17/how-the-fall-of-celsius-dragged-down-crypto-investors.html)
- Voyager recovery is reported as low as about 36% (an early estimate) or about 65–72% (conflicting secondary sources). — [bestcryptoloans.org](https://bestcryptoloans.org/blog/why-celsius-blockfi-voyager-failed/); [Dropstab](https://news.dropstab.com/research/crypto-bankruptcies)
- **BlockFi:** in July 2024 the administrator announced 100% recovery on allowed customer claims. — [cryptolendingadvice.com](https://www.cryptolendingadvice.com/advice/what-happened-to-blockfi/)
- **Genesis / Gemini Earn (primary source):**
  - Genesis suspended Earn withdrawals on **16 Nov 2022** and filed for bankruptcy on **19 Jan 2023**.
  - **232,000 Earn users** were affected.
  - About 97% was returned in kind on 29 May 2024, with the final distribution on 20 Jun 2024: "100% of the assets owed to them in kind", or about 237% of value at the time of suspension. Gemini contributed $40–50M.
  - Source: [Gemini Earn updates](https://www.gemini.com/earn)
- FTX's dollarised recovery (about 119% of petition-date USD) is covered in section 1.

**MiCA rules relevant to "earn"**
- **MiCA Art. 50:** "Issuers of e-money tokens shall not grant interest", and CASPs "shall not grant interest when providing crypto-asset services related to e-money tokens". Any benefit tied to how long the token is held counts as interest. Art. 40 is the equivalent rule for asset-referenced tokens. — [ESMA Interactive Single Rulebook, Art. 50](https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/mica/article-50-prohibition-granting-interest); [Art. 40](https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/mica/article-40-prohibition-granting-interest)
- Commentary says spending-linked cashback is distinct from interest. Offshore venues advertise 7% USDT yields, arguing that USDT is not a MiCA-authorised EMT. These are promotional offers by non-EU platforms. — [Cryptoticker](https://cryptoticker.io/en/usdt-cashback-card-mica-interest-ban/); [CoinStats/MEXC](https://coinstats.app/news/9f479d40151ad6c6fc29dfb09ae01b130b0bb1a3916384ef75d82b26636ecfed_How-MEXC-sidesteps-the-MiCA-interest-ban-on-stablecoins-with-a-7-USDT-yield)
- One "major venue switched off stablecoin rewards for European clients on 1 December 2024" (the venue is unnamed in the snippet). — [CryptoDaily, Jun 2026](https://cryptodaily.co.uk/2026/06/stablecoin-rewards-mica-2-eu-payments)
- The CCSF (10 Nov 2026) lists crypto **lending, borrowing and staking** as activities "ne faisant pas l'objet d'un encadrement spécifique dans MiCA". It asks for disclosure of:
  - the risk of total loss if the borrower defaults (for uncollateralised loans)
  - payment of the return in the lent token, "l'investisseur pouvant ne percevoir qu'une rémunération de faible valeur, voire aucune valeur"
  - fees, and whether the return is fixed or variable
  - Source: [CCSF Recommendation](https://www.banque-france.fr/system/files/2026-11/CCSF_Recommandation_crypto-actifs.pdf)

**DeFi lending yields (realised)**
- DefiLlama-computed **Aave v3 USDC (Ethereum)** supply APY:
  - **2023 (from Feb): mean 3.82%, median 2.74%** (spikes to 56.7%)
  - **2024: mean 7.17%, median 6.57%**
  - **2025: mean 4.12%**
  - **2026 YTD: mean 3.45%**
  - Latest 2.67%; TVL $916M
  - Source: [DefiLlama Aave v3 aEthUSDC](https://defillama.com/yields/pool/aa70268e-4b52-42bf-a116-608b370f9501)
- DefiLlama-computed **Sky (ex-Maker) sUSDS** savings rate: **2025 (from Feb) 4.75%; 2026 YTD 3.73%**; currently 3.8%. — [DefiLlama sUSDS](https://defillama.com/yields/pool/d8c4eff5-c8a9-46fc-a888-057c4c668e72)
- A vendor blog claims a "2025 historical average 5.9%" for Aave USDC. That conflicts with the DefiLlama series and has no methodology. — [RebelFi](https://rebelfi.io/blog/usdc-yield-aave-v3-institutional-guide)
- Compound v3 USDC: the DefiLlama pools for WBTC and WETH show 0% supply APY (collateral only). I did not compute a Compound USDC series.

### Inferences
- **The CeFi "earn" trade-off was asymmetric.** Users earned a few years of above-market interest, then had principal frozen for 1.5–3 years with uncertain recovery. A single collapse could wipe out several years of excess yield.
- **No sanctioned "earn on USDC/EURC" product exists for French retail.** Under MiCA, an authorised CASP cannot pay interest on USDC or EURC holdings. Any remaining "earn" offer is crypto-lending outside MiCA's scope, typically on non-EU-pegged tokens or through DeFi connectors, and lacks MiCA protection, as the CCSF explicitly warns.
- **DeFi lending pays no premium after 2024.** Aave USDC paid less than or about the same as Spiko's USD T-bill fund in 2025–26 (about 3.4% USTBL in Oct 2026). Yet it carries smart-contract, oracle, stablecoin-depeg and gas costs, which matter for small accounts on Ethereum mainnet, plus USD/EUR currency risk.

### Gaps
- There are no official final recovery percentages for Celsius or Voyager; the court and claims-administrator sites (Stretto) were not checked.
- I did not find a list of current MiCA-authorised "earn" or lending offers available to French retail, if any exist.
- Aave/Compound 2022 USDC yields (Aave v2) are not in the current DefiLlama pool list, and no 2022 figure was obtained.
- I gathered no data on DeFi lending protocol losses (exploits or bad debt) for 2022–26.

---

## 4. Liquidity provision on AMMs (Uniswap v2/v3): profitability net of impermanent loss / LVR

### Takeaway
The academic evidence is consistently negative for passive LPs in major Uniswap v3 pairs:
- In v3's first months (2021), aggregate impermanent loss (IL) exceeded fees ($260M vs $199M), and 49.5% of LPs lost money relative to holding.
- Over 2022–23, fees covered only about 80% of arbitrage losses (LVR) in the flagship WETH-USDC 5bp pool.
- Some v2 and long-tail pools did better.

Advertised pool APRs of 20–70% are fee-only figures that ignore IL/LVR.

### Cited Findings
- **Loesch, Hindman, Richardson and Welch, "Impermanent Loss in Uniswap v3"** (arXiv 2111.09192, Nov 2021, Bancor-affiliated authors):
  - Across 17 pools (43% of TVL), Uniswap v3 generated **$199.3M in fees while LPs incurred $260.1M in impermanent loss**.
  - That left **49.5% of LPs with negative returns** relative to holding.
  - In aggregate, LPs would have been **$60.8M better off simply holding**.
  - Source: [arXiv 2111.09192](https://arxiv.org/abs/2111.09192v1)
- **Fritsch and Canidio, "Measuring Arbitrage Losses and Profitability of AMM Liquidity"** (ACM Web Conference 2024 companion; arXiv 2404.05803), simulating passive full-range positions from Jan 2022 to Dec 2023:
  - Fees fall short of arbitrage losses in "the majority of the largest Uniswap pools".
  - **WETH-USDC 5bp** fees "hover around 80%" of losses.
  - WETH-USDT 5bp and WBTC-USDC 30bp roughly broke even.
  - Less-liquid altcoin pairs (MATIC-ETH, LINK-ETH) sometimes had fees about 50% above losses.
  - **Uniswap v2 pools were more profitable than v3**: in the second year, fees were "consistently three times larger than losses".
  - The authors suggest active v3 LPs capture fees at the expense of passive ones.
  - Source: [arXiv 2404.05803v2](https://arxiv.org/html/2404.05803v2)
- On a Uniswap v3 WETH/USDC 5bp pool over 2023–24, **LVR was about 1.95% greater than realised fees** over overlapping 30-day windows. — [arXiv 2509.23222, "The Price of Liquidity"](https://arxiv.org/pdf/2509.23222)
- **Loss-versus-rebalancing (LVR)** is the framework from Milionis, Moallemi and Roughgarden: LP underperformance against a rebalancing portfolio caused by trading at stale prices with arbitrageurs. — [arXiv 2208.06046](https://arxiv.org/pdf/2208.06046v4)
- **Advertised APRs (marketing-style, fee-only).** DefiLlama on 25 Nov 2026 showed Uniswap v3 Base WETH-USDC at 70.9% APY (30-day mean 80.6%) and Ethereum WETH-USDT at 18.1% (30-day mean 54.5%). These figures exclude IL/LVR. — [DefiLlama yields API pools list](https://yields.llama.fi/pools); [DefiLlama Uniswap v3 Base WETH-USDC](https://defillama.com/yields/pool/b99bcdf5-1350-4269-981e-0e9b5cccb007)

### Inferences
- **Passive LPing in volatile major pairs is expected to be roughly zero to negative versus holding**, before gas and rebalancing costs. Concentrated (v3) ranges raise fee APR but also raise IL/LVR and need active management, which conflicts with "passive" and "small account".
- **The only plausibly positive niches are low-volatility or correlated pairs** (stable-stable, LST-ETH) or long-tail pairs with high fees. These carry depeg, smart-contract and token risk instead.
- **For a French retail investor, AMM LPing is fully outside MiCA** (DeFi, self-custody), and each swap or LP action is a potentially taxable event under 150 VH bis. That adds tax-tracking burden.

### Gaps
- I found no study covering 2025–26 LP returns or Uniswap v4 hooks performance.
- There are no retail-specific LP outcome statistics (for example, distribution of returns by position size, including gas).

---

## 5. Yield tokenisation (Pendle), stablecoin yields, and tokenised T-bills accessible in the EU

### Takeaway
Pendle's TVL grew from about $0.23B (Jan 2024) to a **$13.4B peak (19 Sep 2025)**, then collapsed **93% to $0.90B (Nov 2026)**. It was heavily concentrated in Ethena assets, and fixed PT yields now sit around 5%, with all of the underlying's depeg and smart-contract risk. The cleanest "on-chain yield" for a French retail investor is a **regulated tokenised money-market fund**. Spiko's AMF-approved UCITS T-bill funds paid about **2.35–2.43% (EUR)** and about **3.4% (USD)** net in late 2026. Midas (Liechtenstein) is another non-accredited option. Backed's bIB01 is restricted to professional or qualified investors.

### Cited Findings
**Pendle**
- DefiLlama TVL: 1 Jan 2024 $0.23B; 1 Apr 2024 $3.55B; 1 Jan 2025 $4.40B; 1 Oct 2025 $6.51B; **peak $13.39B on 19 Sep 2025**; 1 Jan 2026 $3.69B; 1 Jul 2026 $0.96B; **25 Nov 2026 $0.90B**. — [DefiLlama Pendle](https://defillama.com/protocol/pendle)
- Ethena assets reportedly fell from 67.6% to 5.1% of Pendle TVL; other sources cite about 69–70% Ethena concentration at the peak (secondary). — [Coinpaprika](https://coinpaprika.com/education/yield-tokenization-pendle/); [Datawallet](https://www.datawallet.com/es/cripto/what-is-pendle-finance)
- The PT-sUSDe-28JAN2027 market was priced at a **4.92% fixed** annualised yield on 16 Nov 2026.
- A PT holder carries Ethena's smart-contract, custody and basis risk for the full term: if sUSDe depegs, "the PT redeems to a depegged sUSDe, not par USD".
- Both points are from a secondary guide: [eco.com, "What is Pendle PT and YT"](https://eco.com/support/en/articles/15253995-what-is-pendle-pt-and-yt-tokens-explained-2026)
- Pendle's annualised revenue was reportedly down about 90% from a $77M peak in 2025 to $7.6M (low-quality social post). — [Gate post](https://www.gate.com/post/status/20275246)
- CoinGecko's article on Pendle–USDe fixed-term markets is **Pendle-sponsored content**. — [CoinGecko](https://www.coingecko.com/learn/pendle-usde-fixed-term-markets)

**Stablecoins (context)**
- Supply on 25 Nov 2026: USDT $174.2B, USDC $69.0B, USDe $4.89B, EURC $0.50B. — [DefiLlama stablecoins](https://defillama.com/stablecoins)
- The CCSF says stablecoins were about 8% of crypto market cap in 2025; USDT and USDC make up about 89% of stablecoin supply, and euro stablecoins (EURC, EURCV) remain marginal. — [CCSF Recommendation](https://www.banque-france.fr/system/files/2026-11/CCSF_Recommandation_crypto-actifs.pdf)

**Tokenised T-bills accessible in the EU**
- **Spiko** (France):
  - Structure: AMF-approved UCITS money-market funds; CACEIS Bank as depositary; Twenty First Capital as management company; PwC as auditor.
  - **EUTBL yields:** net 2.43% (trailing 31-day); 7-day and 30-day yields of 2.35% at the NAV of 19 Nov 2026.
  - **USTBL yield:** 3.37% net in USD (early Oct 2026).
  - Fees: 0.25% management fee plus about 0.05% operating expenses.
  - Minimum ticket: €1 per Spiko's site versus €1,000 per Bitquery (conflict).
  - Sources: [Spiko Treasury Bills Euro](https://www.spiko.io/spiko-treasury-bills-euro); [Spiko data EUTBL](https://data.spiko.io/eutbl/); [DefiLlama Spiko](https://defillama.com/rwa/platform/spiko); [Bitquery](https://bitquery.io/blog/tokenized-money-market-funds-on-chain)
- Spiko held about $3.0B of tokenised assets on 18 Nov 2026 (EUTBL about $470M, USTBL about $163M; trackers differ). — [Dune](https://dune.com/markets/rwa/spiko)
- Coinbase integrated stablecoin payment rails into Spiko's funds in June 2026, allowing subscriptions at weekends. — [Cointelegraph](https://cointelegraph.com/news/spiko-coinbase-stablecoin-payments-treasury-funds)
- **Midas** (mTBILL, mBASIS): Liechtenstein FMA approval in Oct 2024 to offer to non-accredited (retail) investors across the EU with no minimum. **mBASIS is itself a basis-trade product**, so it carries the risks in section 1. — [The Block, 8 Oct 2024](https://www.theblock.co/news/markets/2024-10-08-in-an-eu-first-tokenization-firm-midas-opens-mtbill-and-mbasis-tokens-to-retail-traders-320120); [Decrypt](https://decrypt.co/285128/midas-tokenized-products-europe-no-minimum)
- **Backed bIB01** (tracks the iShares $ Treasury Bond 0-1yr UCITS ETF): the product page limits eligibility to professional clients who are also qualified investors under the EU Prospectus Regulation (page updated 5 Feb 2026). — [Backed bIB01 product page](https://assets.backed.fi/products/bib01)

### Inferences
- **The regulated fallback.** For a no-leverage French retail investor, a tokenised UCITS money-market fund such as Spiko EUTBL is the benchmark "crypto-native passive yield". At about 2.4% gross before the 31.4% PFU, it is economically the same as a regular euro money-market fund. Any crypto-yield strategy must clear this hurdle after risk.
- **Pendle is a rate-trading layer, not a yield source.** A PT's fixed rate is only as safe as the underlying asset, and Pendle's 93% TVL drop shows that the 2024–25 yields came largely from Ethena points and incentives that are now gone.
- **USD-denominated products add EUR/USD currency risk** for a euro-based investor. That includes USTBL, USDC lending and sUSDe.

### Gaps
- I did not verify Pendle realised PT yields by year, or default and loss events on Pendle markets.
- I did not confirm whether Spiko funds are directly subscribable by French retail individuals today (rather than only via B2B partners), or the exact minimum.
- I did not find Ondo (USDY/OUSG) or BlackRock BUIDL eligibility for EU retail. BUIDL is generally institutional-only, but that is unverified here.

---

## 6. Airdrop farming and points programmes: realised payoffs 2023–2026, Sybil filtering, effort and cost

### Takeaway
Airdrop payoffs are extremely skewed. A few drops, notably Hyperliquid in November 2024 (about $1.2–1.6B at launch to about 94,000 users), produced life-changing sums. The typical 2024 airdrop was a loser: Keyrock found an **11% success rate** across 62 airdrops, with **88% of tokens declining**, mostly within 15 days. Projects increasingly filter Sybils (LayerZero flagged 803,093 addresses, 13% of those eligible). The effort, gas and capital costs of farming are poorly documented.

### Cited Findings
- **Keyrock, "Airdrops in the Barren Desert" (2024):** 62 airdrops across 6 chains, an **11% success rate**. Most price movement happens in the first days, and few tokens are positive after three months. Ethereum and Solana did better, with about 25% holding or rising after three months. — [Keyrock](https://keyrock.com/airdrops-in-the-barren-desert/)
- **88%** of 2024 airdrop tokens declined in price, most within 15 days (DL News); **88.7% were down after 90 days** (BeInCrypto). — [DL News](https://www.dlnews.com/articles/snapshot/keyrock-study-says-most-token-airdrops-crash-after-launch); [BeInCrypto](https://beincrypto.com/majority-airdrop-tokens-crash-within-15-days/)
- **Hyperliquid HYPE, 29 Nov 2024:**
  - 310M of a 1B maximum supply went to more than 94,000 users.
  - Eligibility came from points accumulated over about six months.
  - Value was about $1.2B (The Block) to $1.6B (Decrypt) at launch, and was later reported above $7B.
  - Allocations were highly skewed; one trader received about $800k.
  - Sources: [Decrypt](https://decrypt.co/294067/hyperliquid-airdrop-1-6-billion); [The Block](https://www.theblock.co/post/328769/hyperliquid-airdrops-over-1-2-billion-worth-of-tokens-to-users-as-hype-crosses-4-billion-fdv); [Cointelegraph](https://cointelegraph.com/news/how-hyperliquid-airdrop-changed-game); [Benzinga](https://benzinga.com/z/42242292)
- **LayerZero Sybil filtering (May–June 2024):**
  - Self-reported Sybils were offered 15% of their intended allocation, and about 100,000 addresses self-reported.
  - Bounty hunters earned 10% of a reported Sybil's allocation.
  - The preliminary list flagged **803,093 addresses, about 13% of roughly 6M eligible**.
  - Sources: [The Block](https://www.theblock.co/news/ecosystems/2024-05-14-layerzero-labs-ceo-says-up-to-100000-addresses-have-self-reported-as-airdrop-sybils-294230); [The Defiant](https://thedefiant.io/layerzero-labs-identifies-800-000-potential-sybil-addresses-in-public-list); [crypto.news](https://crypto.news/layerzero-spots-800k-sybil-addresses-airdrop-scheme/)

### Inferences
- **Airdrop farming is a lottery-like, effort-intensive activity, not passive income.** The expected value is dominated by rare winners (Hyperliquid) that were not predictable in advance. Recipients who held through typical post-airdrop declines gave back most of the value.
- **Multi-wallet (Sybil) farming is increasingly penalised.** Single-wallet genuine use is the realistic approach for a small account, which caps the upside.
- **Many 2024–26 points programmes sat on leveraged DeFi loops** (Ethena points via Pendle and similar), which conflicts with "no leverage". They are entirely outside MiCA. French tax treatment of airdropped tokens adds complexity, and I found no sourced guidance.

### Gaps
- I found no rigorous study of farmers' net returns after gas, capital opportunity cost and time, and no 2025–26 equivalent of the Keyrock study.
- I found no data on Arbitrum (Mar 2023) or other 2023 airdrop farmer profitability.
- I have no sourced French tax doctrine on airdrops.

---

## 7. Covered calls / option vaults (Ribbon/Aevo, Deribit-based): realised returns and drawdowns

### Takeaway
Systematic BTC covered calls on Deribit made roughly **zero over Oct 2021 – Apr 2026** in an unfiltered form (−0.1% annualised net yield). A filtered version added about 5% a year, according to Anchorage, a vendor study. Drawdowns stay essentially those of BTC (−73.5% vs −76.7%), so this is not a low-risk yield. DeFi option vaults (Ribbon) advertised high APYs, but they cap upside in rallies. Their legacy vaults were **exploited in Dec 2025** (about $2.7M, roughly 32% vault loss, with a proposed 19% haircut to users).

### Cited Findings
- **Anchorage Digital Research (D. Lawant), "Synthetic Yield on Bitcoin", 28 May 2026** (vendor research). It uses hourly Deribit implied-volatility data from Oct 2021 to Apr 2026.
  - **Unfiltered 20-delta, 30-day calls:**
    - Full period: **net yield −0.5% total (−0.1% annualised)**; 70 trades, 57 wins and 13 losses; profit factor 1.00.
    - Last 12 months: **+5.5%**, while BTC spot fell **−19.4%**.
  - **Filtered version** (trend and implied-volatility filters): **+23.7% total (+5.2% annualised)**.
  - **Spot vs spot plus filtered overlay:** total return 74.4% vs 98.1%; Sharpe 0.20 vs 0.30; **max drawdown −76.7% vs −73.5%**.
  - **Rolling 1-year windows:** positive 50–85% of the time, with mean yields of 0.2–4.6%.
  - Source: [Anchorage research](https://www.anchorage.com/research/synthetic-yield-on-bitcoin-implementation-discipline-and-performance-boundaries-of-systematic-covered-call-writing)
- **Ribbon's own backtest (protocol marketing):** +1,330% in USD but **−13.7% in ETH terms** over 60 weekly trades with a 93% win rate. Most of the gains were erased in a single week when ETH nearly doubled. — [Ribbon Research, "Theta Vault Backtest Results"](https://www.research.ribbon.finance/blog/theta-vault-backtest-results)
- A 2021 CoinDesk piece marketed DeFi options vaults as "retail-friendly" with 12–30% yields (advertised). — [CoinDesk, 30 Sep 2021](https://www.coindesk.com/markets/2021/09/30/move-over-carry-trade-these-retail-friendly-defi-options-strategies-yield-12-30)
- Unverified secondary claims: ETH vault yields above 40% in 2021–22 and single digits in 2023–24; the ETH Theta Vault underperformed holding ETH by 35% in the Q1 2024 rally; about 68% of weekly epochs were positive. — [Bitget Academy](https://www.bitget.com/amp/academy/rbn-token-ribbon)
- **Ribbon/Aevo exploit, 12 Dec 2025:** about **$2.7M** was drained from legacy Ribbon DOV vaults on Ethereum after a 6 Dec oracle upgrade let anyone set prices. Aevo estimated losses at about 32% of vault value, proposed capping user losses at 19%, and decommissioned the vaults. — [The Block, 14 Dec 2025](https://www.theblock.co/news/ecosystems/2025-12-14-aevos-legacy-ribbon-dov-vaults-exploited-for-2-7-million-following-oracle-upgrade-382461); [web3isgoinggreat](https://web3isgoinggreat.com/single/ribbon-finance-exploit)
- **Short-volatility return profile:** Deribit Insights notes these strategies have negatively skewed returns, so short samples look better than the true risk. A Jan–Aug 2024 weekend-volatility backtest showed +13.95% in BTC terms with an 8.8% max drawdown, which the author flags as likely understated. — [Deribit Insights](https://insights.deribit.com/?p=99807)

### Inferences
- **Covered calls change the shape of returns; they do not create a "yield".** Over a full cycle the premium roughly offset the upside given up unless timing filters were used, and filters add overfitting risk. Drawdown is essentially the underlying's, so a 5% "yield" on an asset that can fall 75% is not passive income in the savings sense.
- **For French retail, covered calls on BTC need options access.** Options are MiFID instruments and would also fall under derivatives distribution rules. Deribit is not shown in my sources as MiCA- or MiFID-authorised for EU retail. DeFi vaults carry smart-contract and oracle risk, as the Ribbon exploit shows.

### Gaps
- I found no independent, peer-reviewed full-cycle study of DeFi option vault realised returns, and no calendar-year (2022) realised figures for Ribbon vaults.
- I did not establish Deribit's licensing status or availability to French retail in 2026, or EU retail access to crypto options on regulated venues.

---

## 8. Cross-strategy summary and practical accessibility for a French retail investor under MiCA (as of Nov 2026)

### Takeaway
Since **1 July 2026**, only MiCA-authorised CASPs may serve French clients. The AMF counted 31 French authorisations and 283 across the EU on 6 Jul 2026; the AMF white list showed 36 French entities on 25 Sep 2026, and Binance was absent. Of the yield strategies, only these are inside a regulated perimeter:
- staking through an authorised custodian CASP
- tokenised UCITS money-market funds (Spiko)
- perpetuals through MiFID-licensed venues, under CFD-style rules

Lending/earn, DeFi lending, LPing, Pendle, Ethena, airdrops and DeFi option vaults are all outside MiCA protection. Realised 2025–26 yields across the board have compressed to roughly 2–6% gross, about the level of euro and US money-market funds, while each strategy retains a fat-tail loss history.

### Cited Findings
- **ESMA public statement, 23 Jun 2026 (ESMA75-113276571-1710):**
  - The MiCA transitional period ends on 1 Jul 2026.
  - Unauthorised CASPs must "immediately stop onboarding new EU clients" and limit services to selling, transferring or closing positions.
  - Non-EU CASPs "cannot provide MiCA services to EU clients or solicit EU clients", except under narrow reverse solicitation.
  - Clients of unauthorised CASPs "do not benefit from MiCA safeguards, including protections for client assets".
  - Source: [ESMA statement PDF](https://www.esma.europa.eu/sites/default/files/2026-06/ESMA75-113276571-1710_Public_Statement_MiCA_transitional_period_ends.pdf)
- **AMF release, 6 Jul 2026:** France has authorised **31** market participants, with more being finalised; **283** are authorised EU-wide. Clients should "use only the services of CASPs authorised to operate in the European Union", and "there is... no equivalence regime with third countries". — [AMF news release](https://www.amf-france.org/en/news-publications/news-releases/crypto-assets-end-pacte-law-and-european-mica-regulation-transitional-period-establishes-new-role)
- The AMF white list showed **36** French entities on 25 Sep 2026. **Binance** was absent from both the AMF white list and the ESMA register (updated 24 Sep 2026). — [Actu-Juridique](https://www.actu-juridique.fr/fiscalite/droit-fiscal/crypto-actifs-ce-que-le-regime-mica-a-change-le-1er-juillet/)
- The **CCSF (10 Nov 2026)** calls for tighter limits on reverse solicitation, and notes that some European activity still runs through non-EU platforms. — [CCSF Recommendation](https://www.banque-france.fr/system/files/2026-11/CCSF_Recommandation_crypto-actifs.pdf)
- **Euro risk-free benchmark:** Spiko EUTBL 7-day and 30-day net yield of 2.35% (NAV of 19 Nov 2026). — [Spiko data](https://data.spiko.io/eutbl/)

### Inferences
**Summary matrix.** This is a synthesis of sections 1–7; yields are gross before French tax (31.4% PFU on realised gains from 2026).

| Strategy | Realised yield 2022–26 (gross) | Worst historical loss / tail | Counterparty / smart-contract risk | Effort | French retail access under MiCA (Nov 2026) |
|---|---|---|---|---|---|
| BTC cash-and-carry (spot + short perp) | Binance BTC funding: 4.2% (2022), 7.9% (2023), 12.0% (2024), 5.1% (2025), 2.6% (2026 YTD); negative in 14% of settlements | FTX (Nov 2022): total freeze, about 119% of petition-date USD repaid from May 2025; liquidation of the short leg in spikes | Exchange custody (high) | Medium–high (monitoring, rebalancing) | Perps only via MiFID venues (Kraken CySEC since May 2025); likely CFD rules (leverage cap, close-out, KID) after ESMA Feb 2026; margin drag cuts yield on capital to about two-thirds of funding |
| Ethena sUSDe | 17.5% (2024), 6.5% (2025), 4.3% (2026 YTD) | $0.65 Binance print on 10 Oct 2025; supply −67% from peak; BaFin EU wind-down 2025 | Exchanges, custodians (Copper/Ceffu), smart contract, funding reversal | Low (hold token) | Not MiCA-authorised; self-custody/DeFi only; no MiCA safeguards |
| ETH staking (Lido / CASP) | 4.5% (2022), 4.3% (2023), 3.2% (2024), 2.8% (2025), 2.4% (2026 YTD) | stETH about 5–6% discount (Jun 2022); 46-day exit queue (Sep 2025); full ETH price risk | LST smart contract; CASP custody | Low | Allowed via custody-authorised CASP, rewards passed through (ESMA); tax timing of rewards unclear |
| SOL staking | about 7–7.5% (2025), 5.4–5.8% (2026 YTD), nominal; about 2–3% real after inflation | SOL price risk; LST depeg risk | LST / validator | Low | Same as ETH |
| CeFi earn / lending | Not measured here (pre-2022 advertised rates not verified) | Celsius, Voyager, BlockFi, Genesis freezes of 1.5–3 years; recoveries about 36% to 100% (conflicting) | Platform insolvency (very high) | Low | Not regulated by MiCA; interest on EMTs (USDC/EURC) banned for CASPs (Art. 50); CCSF warns against "épargne"/"livret" labels |
| DeFi lending (Aave USDC) | 3.8% (2023), 7.2% (2024), 4.1% (2025), 3.5% (2026 YTD) | Not quantified here (exploits, bad debt, USDC Mar 2023 depeg) | Smart contract, oracle, stablecoin | Low–medium (gas for small accounts) | Outside MiCA (self-custody); USD exposure |
| Uniswap LP (major pairs) | Fees < IL/LVR on average (WETH-USDC fees about 80% of LVR 2022–23) | 49.5% of v3 LPs negative versus holding (2021) | Smart contract + adverse selection | High if concentrated | Outside MiCA; heavy tax tracking |
| Pendle PT (fixed) | about 4.9% fixed (PT-sUSDe, Nov 2026); higher in 2024–25 (unverified) | TVL −93% from peak; PT inherits the underlying's depeg | Pendle + underlying stack | Medium | Outside MiCA |
| Tokenised UCITS money-market fund (Spiko) | EUTBL about 2.35–2.43%; USTBL about 3.4% (2026) | Money-market fund risk; no deposit guarantee | Regulated fund (CACEIS depositary) | Very low | AMF-approved UCITS; accessible (minimum €1–€1,000, conflicting) |
| Airdrop farming / points | Lottery: 11% of 2024 drops "successful"; Hyperliquid outlier | 88% of 2024 airdrop tokens fell | Protocol + Sybil exclusion | High | Outside MiCA; tax unclear |
| Covered calls (BTC) | −0.1%/yr unfiltered (Oct 2021–Apr 2026); +5.2%/yr filtered (vendor study) | Max drawdown −73.5% (≈ BTC); Ribbon vault exploit (about 32% loss, Dec 2025) | Venue or vault smart contract | Medium | Options are MiFID instruments; DeFi vaults outside MiCA; Deribit EU status unverified |

**Overall inferences**
- **Realised crypto yield across the board in 2025–26 (about 2–6%) is roughly the same as or below money-market funds.** Every alternative carries at least one documented loss episode much larger than a year of extra yield (FTX, Celsius, USDe 10/10, stETH 2022, Ribbon 2025). Yields were high when retail leverage demand was high (2021, 2024), which BIS shows is also when crash risk is highest.
- **"Passive" is mostly a misnomer.** The only genuinely low-effort, regulated, unleveraged options for French retail are (a) staking held assets through a MiCA custodian, which adds about 2–5% on top of directional price exposure, and (b) tokenised UCITS money-market funds, which are cash-like.
- **Separate claims from evidence.** Community "passive income" claims typically quote peak or advertised APYs: 55% sUSDe in March 2024, 12% Binance USDe promotions, 70% Uniswap fee APRs, 12–30% option-vault yields in 2021. The realised multi-year averages above are much lower.

### Gaps
- The full list of which MiCA-authorised CASPs offer staking or derivatives to French residents was not compiled. The AMF white list and ESMA register would need to be checked entity by entity.
- I found no consolidated, official cross-strategy dataset; the yearly figures above combine several sources and methods (Binance funding sums, DefiLlama trailing APYs, vendor backtests).
- French tax treatment of staking rewards, DeFi yields and airdrops lacks official doctrine in the sources found.
