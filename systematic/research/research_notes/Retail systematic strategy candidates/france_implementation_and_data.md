# France-based retail investor running a daily-bar systematic strategy through IBKR (2026): instruments, costs, taxes, data and backtesting tools

Research date: 2026-11-10. Unless a different date is given, every IBKR, justETF, PyPI and vendor figure below was read from the live page on 2026-11-10. Figures from secondary sources (press, blogs, forums) are labelled as such. Investor context assumed throughout: French tax resident, EUR base currency, Interactive Brokers Ireland (IBIE), retail client, decisions after the US close, no leverage, €10k–€200k.

Changes in 2025–2026 that matter most:
- **French social levies on capital income rose from 17.2% to 18.6%**, so the flat tax (PFU) went from 30% to **31.4%**. Source: LFSS 2026, Loi n° 2025-1403 du 30 décembre 2025, art. 12.
- **The French financial transaction tax (TTF) went from 0.3% to 0.4%** on 1 April 2025. ETFs are outside its scope.
- **IBC, the de facto tool for running IB Gateway unattended, was retired and archived on 1 September 2026.** A one-release fork, `ibc2`, appeared on 10 October 2026.
- **Stooq has required a CAPTCHA-obtained API key for CSV downloads since about March 2026.** This breaks pandas-datareader's Stooq reader.
- **New products**:
  - first managed-futures UCITS ETF (iMGP DBi, March 2025; on Xetra since February 2026);
  - Man Group trend-overlay UCITS ETF (announced 4 November 2026);
  - Amundi and iShares PEA ETFs: DCAM (March 2025), SPEA (May 2025), GPEA MSCI ACWI (July 2026);
  - new EUR overnight-swap ETFs from iShares and Invesco (late 2025);
  - an iShares EUR-hedged 7–10y Treasury accumulating share class (July 2025).

---

## 1. PRIIPs/KID: can an EU retail client buy US-domiciled ETFs at IBKR, and what exceptions exist?

### Takeaway
No. An EEA retail client at IBKR cannot open new positions in US-listed ETFs that have no PRIIPs KID, and US issuers generally do not produce KIDs. IBKR names three routes:
- European-issued (UCITS) equivalents;
- CFDs on US ETFs, issued by IBKR's European entities;
- reclassification as an elective professional client (2 of 3 MiFID tests).

Existing positions can be closed. Whether options on US ETFs are tradable for retail was not verified.

### Cited Findings
- **Legal basis**: the PRIIPs Regulation (EU) No 1286/2014 has applied since 1 January 2018 and requires a Key Information Document for EEA retail investors — [IBKR Knowledge Base, "PRIIPs Regulation"](https://ibkb.interactivebrokers.com/node/2993) (via search summary; the KB now redirects to ibkr.info, which returned 403 to direct fetch).
- **Why US ETFs are blocked**: per IBKR, "U.S. clients are not impacted by PRIIPs, so the issuers of U.S. listed ETFs do not as a rule create KIDs. This means that EEA and UK Retail clients may not purchase the product." Also: "As a broker, IBKR is required to block trading in a PRIIP if a KID is not available." Rejected orders return a "product unavailable to retail clients" message — [IBKR KB node 2993](https://ibkb.interactivebrokers.com/node/2993); [IBKR KB "PRIIPs Overview"](https://ibkb.interactivebrokers.com/de/node/3324).
- **Workarounds IBKR lists**:
  - "Many US ETF issuers have equivalent ETFs issued by their European entities. European-issued ETFs have KIDs and are therefore freely tradable."
  - Clients "can trade most large US ETFs as CFDs. The CFDs are issued by IBKR's European entities and as such meet all KID requirements." IBKR adds that a CFD tracking a US ETF means the investor "may be indirectly investing in that underlying asset."
  - "Clients may be eligible for re-classification as a professional client, for whom KIDs are not required."
  - Source: [IBKR KB node 2993](https://ibkb.interactivebrokers.com/node/2993); [IBKR KB tag "cfds"](https://ibkb.interactivebrokers.com/tag/cfds).
- **Existing holdings**: the restriction "does not apply to existing positions subject to the KID requirement that you are attempting to close." An IBKR reply quoted on a forum says clients can close any open position, and if the platform refuses, "you can call the IB Trade Desk and they can place a closing marketable order" — [Mustachianpost forum thread quoting IBKR](https://forum.mustachianpost.com/t/confused-about-the-new-law-and-us-etfs-will-ib-still-let-me-buy-them/2979?page=2). This is a secondary forum source.
- **Elective professional criteria at an IBKR EU entity** (IB Luxembourg policy; MiFID II framework):
  - (a) traded in significant size at an average of 10 trades per quarter over the last four quarters (spot FX excluded);
  - (b) a portfolio of financial instruments, including cash, above EUR 500,000;
  - (c) at least one year working in the financial sector in a professional position.
  - IBLUX may also grant status after a qualitative assessment of expertise, experience and knowledge. The "two of three" rule is the standard MiFID formulation. Sources: [IBKR KB "Interactive Brokers Luxembourg SARL – MiFID Categorisation"](https://ibkb.interactivebrokers.com/de/node/3552); [Swissquote elective professional status](https://swissquote.com/en-lu/tradable-products/elective-professional-status).
- **Which entity serves French clients**: IBIE describes itself as "regulated by the Central Bank of Ireland (CBI, reference number C423427)… member of the Irish Investor Compensation Scheme (ICS)" — [IBKR Ireland pricing page footer](https://www.interactivebrokers.ie/en/pricing/commissions-stocks-europe.php).

### Inferences
- **The universe is effectively UCITS ETFs/ETCs plus individual stocks.** For a €10k–€200k investor the EUR 500k portfolio test fails. Professional status would need test (a) plus test (c). "Significant size" is undefined in the sources, so a small-ticket daily strategy is unlikely to qualify on trading frequency alone.
- **Backtests can use US ETF histories as proxies, but live trading must map each one to a UCITS equivalent.** The mapping is listed in section 2. Expect TER, tracking, currency (USD vs EUR listing) and trading-hour differences, and model them explicitly.
- **CFDs on US ETFs are not a clean substitute for an unlevered investor.** A CFD is a derivative with financing charges and counterparty exposure to IBKR. Its French tax treatment was not researched here.

### Gaps
- **Options on US ETFs** (for example SPY options) for EEA retail at IBIE: no source found confirming or denying. Check IBKR's PRIIPs KB or ask IBKR.
- **AMF guidance**: its position on US packaged products bought before 2018 exists ([AMF PDF title](https://www.amf-france.org/sites/institutionnel/files/pdf/70135/en/Application_of_the_PRIIPs_Regulation_what_happens_to_US_packaged_products_subscribed_before_the_regulation_came_into_force_.pdf?1713518203)) but was not read.
- **IBIE's own categorisation policy** was not retrieved; the criteria above come from the IBLUX policy page.

---

## 2. UCITS building blocks available to a French retail client

### Takeaway
Every building block a typical daily multi-asset or factor-rotation strategy needs exists in UCITS form:
- MSCI World momentum, value, quality, min-vol and multifactor;
- 10 of 11 S&P 500 sectors from iShares (physical), and all 11 from Invesco (synthetic, including Real Estate);
- US Treasury 7–10y, unhedged and EUR-hedged, at 0.06–0.10% TER;
- physical gold ETCs at 0.11–0.12% (EUR-hedged at 0.25–0.34%);
- EUR overnight/€STR swap ETFs at 0.10%;
- one managed-futures UCITS ETF (iMGP DBi, 0.75%).

Most factor and sector funds trade on Xetra and LSE rather than Euronext Paris. Fund histories are shorter than the US equivalents: sectors from 2009–2018, factors from 2012–2014, managed futures from 2025.

### Cited Findings
All rows come from the justETF profile for each ISIN (`https://www.justetf.com/en/etf-profile.html?isin=<ISIN>`), retrieved 2026-11-10. AUM is in EUR as displayed that day. Tickers are the listing codes justETF shows (Xetra / LSE / Euronext Paris / Borsa Italiana). Each ISIN below links to its profile.

**A. MSCI World factor ETFs** (all Irish-domiciled, physical, accumulating, unhedged; justETF momentum, value, quality, low-volatility and multi-factor lists)

| ISIN | Fund | TER | Inception | AUM | Main tickers |
|---|---|---|---|---|---|
| [IE00BP3QZ825](https://www.justetf.com/en/etf-profile.html?isin=IE00BP3QZ825) | iShares Edge MSCI World Momentum Factor (Acc) (optimised sampling) | 0.25% | 3 Oct 2014 | €4,948m | Xetra IS3R; LSE IWMO (USD) / IWFM (GBX); Borsa IWMO |
| [IE00BL25JP72](https://www.justetf.com/en/etf-profile.html?isin=IE00BL25JP72) | Xtrackers MSCI World Momentum 1C | 0.25% | 5 Sep 2014 | €1,791m | Xetra XDEM; LSE XDEM |
| [IE0001FQFU60](https://www.justetf.com/en/etf-profile.html?isin=IE0001FQFU60) | Amundi MSCI World Momentum Advanced Acc | 0.25% | 30 Oct 2024 | €566m | Xetra WMSE; LSE WMAG |
| [IE00BP3QZB59](https://www.justetf.com/en/etf-profile.html?isin=IE00BP3QZB59) | iShares Edge MSCI World Value Factor (Acc) | 0.25% | 3 Oct 2014 | €6,083m | Xetra IS3S; LSE IWVL / IWFV |
| [IE00BL25JM42](https://www.justetf.com/en/etf-profile.html?isin=IE00BL25JM42) | Xtrackers MSCI World Value 1C | 0.25% | 11 Sep 2014 | €3,649m | Xetra XDEV |
| [IE00BP3QZ601](https://www.justetf.com/en/etf-profile.html?isin=IE00BP3QZ601) | iShares Edge MSCI World Quality Factor (Acc) | 0.25% | 3 Oct 2014 | €5,845m | Xetra IS3Q; LSE IWQU / IWFQ |
| [IE00BL25JL35](https://www.justetf.com/en/etf-profile.html?isin=IE00BL25JL35) | Xtrackers MSCI World Quality 1C | 0.25% | 11 Sep 2014 | €2,663m | Xetra XDEQ |
| [IE00B8FHGS14](https://www.justetf.com/en/etf-profile.html?isin=IE00B8FHGS14) | iShares Edge MSCI World Minimum Volatility (Acc) | 0.30% | 30 Nov 2012 | €2,536m | Xetra IQQ0; LSE MVOL / MINV |
| [IE00BL25JN58](https://www.justetf.com/en/etf-profile.html?isin=IE00BL25JN58) | Xtrackers MSCI World Minimum Volatility 1C | 0.25% | 5 Sep 2014 | €1,280m | Xetra XDEB |
| [IE0001DKJVC2](https://www.justetf.com/en/etf-profile.html?isin=IE0001DKJVC2) | Amundi MSCI World Minimum Volatility Advanced Acc | 0.25% | 30 Oct 2024 | €627m | Xetra WMMV |
| [IE00BZ0PKT83](https://www.justetf.com/en/etf-profile.html?isin=IE00BZ0PKT83) | iShares STOXX World Equity Multifactor (Acc) | 0.30% | 4 Sep 2015 | €795m | Xetra IBCZ; LSE IFSW |
| [IE00BJRCLL96](https://www.justetf.com/en/etf-profile.html?isin=IE00BJRCLL96) | JPMorgan Global Equity Multi-Factor (acc) | 0.19% | 9 Jul 2019 | €272m | Xetra JPGL; LSE JPGL |
| [IE0009Y1MQJ2](https://www.justetf.com/en/etf-profile.html?isin=IE0009Y1MQJ2) | iShares World Equity Factor Rotation Active (Acc) | 0.30% | 16 Jan 2025 | €174m | Xetra FCRN; Euronext Amsterdam FACT |

- **The iShares Edge World momentum, value and quality funds now carry a 0.25% TER** (justETF profiles above). Older sources often cite 0.30%.
- **Other share classes**:
  - USD-hedged and "Advanced" (ESG-screened) variants exist, e.g. iShares MSCI World Momentum Factor Advanced IE000L5NW549 (0.25%);
  - a distributing value class IE00BFYTYS33 (0.25%);
  - a distributing min-vol class IE00BMCZLJ20 (0.30%);
  - Source: [justETF momentum list](https://www.justetf.com/en/how-to/invest-in-momentum-etfs.html); [justETF value list](https://www.justetf.com/en/how-to/invest-in-value-etfs.html); [justETF low-volatility list](https://www.justetf.com/en/how-to/invest-in-low-volatility-etfs.html).
- **Other multi-factor or "enhanced" UCITS options** include HSBC Multi-Factor Worldwide Equity (IE00BKZGB098, 0.25%), L&G Gerd Kommer Multifactor (IE0001UQQ933, 0.45%) and Avantis Global Equity (IE000RJECXS5, 0.22%) — [justETF multi-factor list](https://www.justetf.com/en/how-to/invest-in-multi-factor-etfs.html); [justETF value list](https://www.justetf.com/en/how-to/invest-in-value-etfs.html).

**B. S&P 500 sector UCITS ETFs**
- **iShares: 10 of the 11 GICS sectors, no Real Estate.** All are physical, accumulating, Irish, TER 0.15%.

  | Sector | ISIN | Inception | AUM | Xetra / LSE (USD) |
  |---|---|---|---|---|
  | Consumer Discretionary | [IE00B4MCHD36](https://www.justetf.com/en/etf-profile.html?isin=IE00B4MCHD36) | 20 Nov 2015 | €696m | QDVK / IUCD |
  | Consumer Staples | [IE00B40B8R38](https://www.justetf.com/en/etf-profile.html?isin=IE00B40B8R38) | 20 Mar 2017 | €500m | 2B7D / IUCS |
  | Energy | [IE00B42NKQ00](https://www.justetf.com/en/etf-profile.html?isin=IE00B42NKQ00) | 20 Nov 2015 | €1,643m | QDVF / IUES |
  | Financials | [IE00B4JNQZ49](https://www.justetf.com/en/etf-profile.html?isin=IE00B4JNQZ49) | 20 Nov 2015 | €2,161m | QDVH / IUFS |
  | Health Care | [IE00B43HR379](https://www.justetf.com/en/etf-profile.html?isin=IE00B43HR379) | 20 Nov 2015 | €3,219m | QDVG / IUHC |
  | Industrials | [IE00B4LN9N13](https://www.justetf.com/en/etf-profile.html?isin=IE00B4LN9N13) | 20 Mar 2017 | €609m | 2B7C / IUIS |
  | Information Technology | [IE00B3WJKG14](https://www.justetf.com/en/etf-profile.html?isin=IE00B3WJKG14) | 20 Nov 2015 | €15,998m | QDVE / IUIT |
  | Materials | [IE00B4MKCJ84](https://www.justetf.com/en/etf-profile.html?isin=IE00B4MKCJ84) | 20 Mar 2017 | €177m | 2B7B / IUMS |
  | Utilities | [IE00B4KBBD01](https://www.justetf.com/en/etf-profile.html?isin=IE00B4KBBD01) | 20 Mar 2017 | €1,046m | 2B7A / IUUS |
  | Communication | [IE00BDDRF478](https://www.justetf.com/en/etf-profile.html?isin=IE00BDDRF478) | 17 Sep 2018 | €1,036m | IU5C / IUCM |

  Source: justETF profiles; [justETF iShares provider list](https://www.justetf.com/en/etf-provider/ishares-etfs.html).
- **Invesco: all 11 sectors, including Real Estate.** All are synthetic (swap), accumulating, Irish, TER 0.14%, tracking S&P Select Sector Capped 20% indices. The original nine started 16 Dec 2009. justETF showed LSE and Borsa listings and no Xetra line for these.

  | Sector | ISIN | Inception | AUM | LSE (USD) |
  |---|---|---|---|---|
  | Consumer Discretionary | [IE00B449XP68](https://www.justetf.com/en/etf-profile.html?isin=IE00B449XP68) | 16 Dec 2009 | €135m | XLYS |
  | Consumer Staples | [IE00B435BG20](https://www.justetf.com/en/etf-profile.html?isin=IE00B435BG20) | 16 Dec 2009 | €37m | XLPS |
  | Energy | [IE00B435CG94](https://www.justetf.com/en/etf-profile.html?isin=IE00B435CG94) | 16 Dec 2009 | €123m | XLES |
  | Financials | [IE00B42Q4896](https://www.justetf.com/en/etf-profile.html?isin=IE00B42Q4896) | 16 Dec 2009 | €340m | XLFS |
  | Health Care | [IE00B3WMTH43](https://www.justetf.com/en/etf-profile.html?isin=IE00B3WMTH43) | 16 Dec 2009 | €565m | XLVS |
  | Industrials | [IE00B3YC1100](https://www.justetf.com/en/etf-profile.html?isin=IE00B3YC1100) | 16 Dec 2009 | €121m | XLIS |
  | Technology | [IE00B3VSSL01](https://www.justetf.com/en/etf-profile.html?isin=IE00B3VSSL01) | 16 Dec 2009 | €2,066m | XLKS |
  | Materials | [IE00B3XM3R14](https://www.justetf.com/en/etf-profile.html?isin=IE00B3XM3R14) | 16 Dec 2009 | €15m | XLBS |
  | Utilities | [IE00B3VPKB53](https://www.justetf.com/en/etf-profile.html?isin=IE00B3VPKB53) | 16 Dec 2009 | €167m | XLUS |
  | Communications | [IE00BG7PP820](https://www.justetf.com/en/etf-profile.html?isin=IE00BG7PP820) | 14 Sep 2018 | €135m | XLCS |
  | Real Estate | [IE00BYM8JD58](https://www.justetf.com/en/etf-profile.html?isin=IE00BYM8JD58) | 17 Feb 2016 | €126m | XRES |

  Source: justETF profiles; [justETF Invesco provider list](https://www.justetf.com/en/etf-provider/invesco-etfs.html).
- **State Street SPDR: 10 "Select Sector" UCITS ETFs**, no Real Estate in justETF's SPDR list:
  - ISINs: Technology IE00BWBXM948 (0.15%, 7 Jul 2015, €1,784m, Xetra ZPDT, Euronext Amsterdam SXLK), Energy IE00BWBXM492, Health Care IE00BWBXM617, Consumer Staples IE00BWBXM385, Materials IE00BWBXM831, Consumer Discretionary IE00BWBXM278, Utilities IE00BWBXMB69, Communication Services IE00BFWFPX50, Financials IE00BWBXM500, Industrials IE00BWBXM724;
  - Source: [justETF SPDR provider list](https://www.justetf.com/en/etf-provider/spdr-etfs.html); [justETF profile IE00BWBXM948](https://www.justetf.com/en/etf-profile.html?isin=IE00BWBXM948).

**C. US Treasury 7–10y UCITS ETFs**

| ISIN | Fund | TER | Inception | AUM | Hedged | Dist | Main tickers |
|---|---|---|---|---|---|---|---|
| [IE00B1FZS798](https://www.justetf.com/en/etf-profile.html?isin=IE00B1FZS798) | iShares USD Treasury Bond 7-10yr (Dist) | 0.07% | 8 Dec 2006 | €3,549m | No | Dist | Xetra IUSM; LSE IBTM (GBP) / IDTM (USD); Euronext Amsterdam BTMA |
| [IE00B3VWN518](https://www.justetf.com/en/etf-profile.html?isin=IE00B3VWN518) | iShares USD Treasury Bond 7-10yr (Acc) | 0.07% | 3 Jun 2009 | €4,650m | No | Acc | Xetra SXRM; LSE CBU0 |
| [IE00BGPP6697](https://www.justetf.com/en/etf-profile.html?isin=IE00BGPP6697) | iShares $ Treasury Bond 7-10yr EUR Hedged (Dist) | 0.10% | 25 Feb 2019 | €1,448m | EUR | Dist | Xetra IBB1 |
| [IE000K1VI152](https://www.justetf.com/en/etf-profile.html?isin=IE000K1VI152) | iShares USD Treasury Bond 7-10yr EUR Hedged (Acc) | 0.10% | 25 Jul 2025 | €227m | EUR | Acc | Xetra CEMF |
| [IE00BF2FN752](https://www.justetf.com/en/etf-profile.html?isin=IE00BF2FN752) | Invesco US Treasury Bond 7-10 Year Acc | 0.06% | 20 Feb 2024 | €57m | No | Acc | Xetra TRXA |
| [IE00BF2FN869](https://www.justetf.com/en/etf-profile.html?isin=IE00BF2FN869) | Invesco US Treasury Bond 7-10 Year EUR Hedged Dist | 0.10% | 12 Mar 2019 | €497m | EUR | Dist | Xetra TRDE |
| [LU1407887915](https://www.justetf.com/en/etf-profile.html?isin=LU1407887915) | Amundi US Treasury Bond 7-10Y Acc | 0.06% | 2 Jun 2023 | €417m | No | Acc | Xetra USB7 |
| [LU1407888137](https://www.justetf.com/en/etf-profile.html?isin=LU1407888137) | Amundi US Treasury Bond 7-10Y EUR Hedged Acc | 0.06% | 2 Jun 2023 | €670m | EUR | Acc | Xetra 7USH |
| [IE000K22VCJ6](https://www.justetf.com/en/etf-profile.html?isin=IE000K22VCJ6) | SPDR Bloomberg 7-10 Year U.S. Treasury (Acc) | 0.05% | 23 Feb 2026 | €1m | No | Acc | LSE TRAX |

- **Other maturity buckets** exist in the same families: 0–1y, 1–3y, 3–7y, 10–20y and 20+y (iShares, Invesco, Amundi, SPDR), many with EUR-hedged classes — [justETF iShares list](https://www.justetf.com/en/etf-provider/ishares-etfs.html); [Invesco list](https://www.justetf.com/en/etf-provider/invesco-etfs.html); [Amundi list](https://www.justetf.com/en/etf-provider/amundi-etfs.html).

**D. Physical gold ETCs**

| ISIN | Product | TER | Inception | AUM | Tickers |
|---|---|---|---|---|---|
| [IE00B4ND3602](https://www.justetf.com/en/etf-profile.html?isin=IE00B4ND3602) | iShares Physical Gold ETC | 0.12% | 8 Apr 2011 | €33,660m | Xetra PPFB; Euronext Paris SLGN (as shown); LSE SGLN (GBX) / IGLN (USD) |
| [IE00B579F325](https://www.justetf.com/en/etf-profile.html?isin=IE00B579F325) | Invesco Physical Gold ETC | 0.12% | 25 Jun 2009 | €25,631m | Xetra 8PSG; LSE SGLD |
| [FR0013416716](https://www.justetf.com/en/etf-profile.html?isin=FR0013416716) | Amundi Physical Gold ETC (C) | 0.12% | 21 May 2019 | €10,770m | Euronext Paris GOLD; Xetra GLDA |
| [JE00BN2CJ301](https://www.justetf.com/en/etf-profile.html?isin=JE00BN2CJ301) | WisdomTree Core Physical Gold | 0.12% | 30 Nov 2020 | €2,045m | Xetra and Paris WGLD |
| [DE000A2T0VU5](https://www.justetf.com/en/etf-profile.html?isin=DE000A2T0VU5) | Xtrackers IE Physical Gold ETC | 0.11% | 22 Apr 2020 | €5,724m | Xetra XGDU |
| [DE000A0S9GB0](https://www.justetf.com/en/etf-profile.html?isin=DE000A0S9GB0) | Xetra-Gold | 0.00% (as shown) | 27 Nov 2007 | €20,672m | Xetra 4GLD |
| [IE0009JOT9U1](https://www.justetf.com/en/etf-profile.html?isin=IE0009JOT9U1) | iShares Physical Gold EUR Hedged ETC | 0.25% | 5 Jul 2022 | €627m | Xetra and Paris IGLD |
| [XS2183935274](https://www.justetf.com/en/etf-profile.html?isin=XS2183935274) | Invesco Physical Gold EUR Hedged ETC | 0.34% | 9 Jul 2020 | €1,496m | Xetra 8PSE |

**E. EUR money-market / overnight-rate ETFs** (all synthetic, accumulating)

| ISIN | Fund | TER | Inception | AUM | Tickers |
|---|---|---|---|---|---|
| [LU0290358497](https://www.justetf.com/en/etf-profile.html?isin=LU0290358497) | Xtrackers II EUR Overnight Rate Swap 1C | 0.10% | 25 May 2007 | €23,569m | Xetra XEON |
| [LU1190417599](https://www.justetf.com/en/etf-profile.html?isin=LU1190417599) | Amundi Smart Overnight Return Acc | 0.10% | 2 Mar 2015 | €7,410m | Euronext Paris CSH2; Xetra LYOR |
| [FR0010510800](https://www.justetf.com/en/etf-profile.html?isin=FR0010510800) | Amundi EUR Overnight Return Acc | 0.10% | 13 Sep 2007 | €3,359m | Euronext Paris CSH; Xetra L8I3 |
| [IE0005RKXDO7](https://www.justetf.com/en/etf-profile.html?isin=IE0005RKXDO7) | iShares EUR Overnight Rate Swap (Acc) | 0.10% | 11 Dec 2025 | €7m | Xetra ONSW |
| [IE000YPOHA39](https://www.justetf.com/en/etf-profile.html?isin=IE000YPOHA39) | Invesco EUR Overnight Return Swap Acc | 0.10% | 27 Oct 2025 | €4m | Xetra RONS |

- A distributing XEON class also exists: Xtrackers II EUR Overnight Rate Swap 1D, LU0335044896 — [justETF Xtrackers list](https://www.justetf.com/en/etf-provider/xtrackers-etfs.html).

**F. Managed-futures / trend UCITS ETFs**
- **iMGP DBi Managed Futures Fund R USD UCITS ETF**, ISIN LU2951555585: active, synthetic, accumulating, Luxembourg, TER 0.75% p.a., launched 7 March 2025. It invests long and short in futures and forwards across equities, bonds and commodities. Source: [justETF profile (via search)](https://www.justetf.com/en/etf-profile.html?isin=LU2951555585).
  - It aims to replicate the pre-fee performance of a basket of leading managed-futures hedge funds (DBi replication), mirrors the US DBMF, and launched on Euronext Paris — [HedgeNordic, March 2025](https://hedgenordic.com/2025/03/europe-gets-its-managed-futures-ucits-etf-with-imgp-dbi-launch).
  - It was listed on Xetra (Bloomberg DBMF:GY) on 3 February 2026 — [ETF Express, 3 Feb 2026](https://etfexpress.com/2026/02/03/imgp-dbi-now-available-on-deutsche-borse-xetra/); [iMGP press release](https://www.imgp.com/press-release/europes-only-managed-futures-ucits-etf-now-available-on-deutsche-borse-xetra).
  - A EUR-hedged class (R EUR HP, LU3359622902) started 13 May 2026 at 0.75% — [finanzen.ch (via search)](https://script.finanzen.ch/etf/daten-gebuehr/imgp-dbi-managed-futures-r-hp-etf-lu3359622902).
  - An ex-commodities, SFDR Article 8 sibling launched in April 2025 — [HedgeNordic, April 2025](https://hedgenordic.com/2025/04/dbi-secures-nordic-backing-for-ex-commodities-managed-futures-etf).
- **Man Active Trend Enhanced UCITS ETF** (tickers MATE / MAET): announced 4 November 2026. It combines systematic MSCI-World-benchmarked equity exposure with a quantitative trend-following overlay across global futures, so it is not pure trend. Planned listings are LSE, Euronext Milan and Xetra. Source: [RankiaPro, Nov 2026](https://rankiapro.com/en/news/man-group-launches-its-first-ucits-etfs-in-europe-featuring-active-trend-following-and-infrastructure-strategies/). A Spanish outlet describes the funds only as registered in Ireland, so first trading is unconfirmed — [Finantres](https://finantresnoticias.com/etfs/man-group-etf-ucits-activos-trend-infraestructura/).

**G. PEA-eligible synthetic ETFs on US/global indices** (all accumulating; listed on Euronext Paris)

| ISIN | Fund | Index | TER | Inception | AUM | Ticker |
|---|---|---|---|---|---|---|
| [FR001400U5Q4](https://www.justetf.com/en/etf-profile.html?isin=FR001400U5Q4) | Amundi PEA Monde (MSCI World) | MSCI World | 0.20% | 4 Mar 2025 | €1,784m | DCAM |
| [IE0002XZSHO1](https://www.justetf.com/en/etf-profile.html?isin=IE0002XZSHO1) | iShares MSCI World Swap PEA | MSCI World | 0.20% | 26 Mar 2024 | €2,339m | WPEA |
| [LU1681043599](https://www.justetf.com/en/etf-profile.html?isin=LU1681043599) | Amundi MSCI World Swap EUR Acc | MSCI World | 0.38% | 16 Jun 2009 | €6,736m | CW8 |
| [FR0011550185](https://www.justetf.com/en/etf-profile.html?isin=FR0011550185) | BNP Paribas Easy S&P 500 EUR | S&P 500 | 0.14% | 16 Sep 2013 | €3,693m | ESE |
| [FR0011871128](https://www.justetf.com/en/etf-profile.html?isin=FR0011871128) | Amundi PEA S&P 500 | S&P 500 | 0.12% | 20 May 2014 | €1,256m | PSP5 |
| [IE000DQLYVB9](https://www.justetf.com/en/etf-profile.html?isin=IE000DQLYVB9) | iShares S&P 500 Swap PEA | S&P 500 | 0.10% | 29 May 2025 | €59m | SPEA |
| [FR0011871110](https://www.justetf.com/en/etf-profile.html?isin=FR0011871110) | Amundi PEA Nasdaq-100 | Nasdaq-100 | 0.30% | 20 May 2014 | €1,196m | PUST |
| [FR0014017NX3](https://www.justetf.com/en/etf-profile.html?isin=FR0014017NX3) | Amundi PEA Global (MSCI ACWI) | MSCI ACWI | 0.30% | 6 Jul 2026 | €94m | GPEA |
| [FR001400KH45](https://www.justetf.com/en/etf-profile.html?isin=FR001400KH45) | Amundi PEA MSCI USA Value Advanced | MSCI USA Value | 0.50% | 18 Jan 2024 | €42m | USVE |

- **Other PEA products** in the Amundi range include PEA S&P US sector "Screened" funds (e.g. Industrials FR0011869270, Consumer Staples FR001400KE06) and EUR-hedged S&P 500 classes — [justETF Amundi list](https://www.justetf.com/en/etf-provider/amundi-etfs.html).
- **Ticker caution**: FR0013412269 (ticker PANX) is now "Amundi PEA US Tech Screened", not a Nasdaq-100 tracker — [justETF profile](https://www.justetf.com/en/etf-profile.html?isin=FR0013412269). Press sources mix up PEA tickers and ISINs — [Finary PEA ETF article](https://finary.com/en/blog/bourse/etf/etf-pea).
- **Why these must be synthetic**: a global index can be PEA-eligible only through synthetic replication, because the fund must hold at least 75% European shares — [Finary](https://finary.com/en/blog/bourse/etf/etf-pea); [finance-et-compagnies](https://finance-et-compagnies.com/bourse/etf/msci-world-pea/).

### Inferences
- **US-ETF to UCITS mapping for backtests**:

  | US ETF | UCITS equivalent |
  |---|---|
  | MTUM / VLUE / QUAL / USMV | IS3R or XDEM / IS3S or XDEV / IS3Q or XDEQ / IQQ0 or XDEB (MSCI World rather than MSCI USA) |
  | XLK…XLRE | iShares S&P 500 sector funds (QDVE etc.) or Invesco XL*S funds (Real Estate only via Invesco XRES) |
  | IEF | IUSM/IBTM (USD) or IBB1/CEMF/7USH (EUR-hedged) |
  | GLD / IAU | SGLN/IGLN, 4GLD, GOLD |
  | BIL / SHV | XEON or CSH2 |
  | DBMF | LU2951555585 |
- **UCITS live histories are short.** Factor funds start 2012–2014, the communication sector 2018, EUR-hedged Treasury accumulating 2025, managed futures 2025. Long backtests will need index or US-ETF proxies spliced to UCITS prices, with explicit currency conversion.
- **Many small funds carry closure and liquidity risk.** Examples: Invesco US Materials €15m, Invesco US Consumer Staples €37m, SPDR 7–10y Treasury €1m, the new iShares and Invesco € overnight ETFs under €10m. Prefer the large share class per exposure.
- **Exchange choice**: most factor and sector UCITS funds are not listed on Euronext Paris, so execution would mostly be on Xetra (EUR) or LSE (USD/GBX). This determines commission schedule and market-data needs (section 3).

### Gaps
- iShares' MSCI-based "Edge MSCI World Multifactor" product appears to have been re-indexed or renamed as "iShares STOXX World Equity Multifactor" (same ISIN, IE00BZ0PKT83). Date and reason not verified.
- An Amundi or Lyxor S&P 500 sector UCITS range outside the PEA "Screened" funds was not checked.
- Whether Invesco sector ETFs have Xetra lines was not verified (justETF showed LSE and Borsa only).
- PEA-eligibility flags were taken from fund names and press. The justETF "PEA eligible" attribute was not individually checked; CW8 and ESE are cited as PEA-eligible by press only.
- The French tax treatment of gold ETCs (debt securities backed by bullion) was not found in official sources. See section 4.

---

## 3. IBKR Ireland costs and API operations

### Takeaway
On EUR-listed European ETFs:
- **Tiered**: 0.05% of trade value, minimum €1.25, capped at €29 per order, plus exchange and clearing fees.
- **Fixed**: 0.05% with a €3 minimum and no cap, third-party fees included except a €0.75 per-execution Euronext ETF fee.

US stocks cost USD 0.005/share fixed (USD 1 minimum) or USD 0.0035/share tiered (USD 0.35 minimum). FX conversion is 0.2 bp with a USD 2 minimum.

API trading has fixed costs and constraints:
- an IBKR Pro account, market-data subscriptions and USD 500 of equity;
- a daily Gateway restart and a manual weekly re-login (cycle starts Monday);
- IBC, the usual automation layer, has been retired since 1 September 2026;
- ib_async 2.1.0 (December 2025) is the maintained Python client.

### Cited Findings

**Commissions: European stocks and ETFs** (IBIE, monthly trade value up to €50m) — [IBKR Ireland, Commissions Stocks/ETFs (Europe tab)](https://www.interactivebrokers.ie/en/pricing/commissions-stocks-europe.php)

| | France (Euronext Paris), EUR | Germany (incl. Xetra), EUR | UK, GBP lines | UK, USD lines |
|---|---|---|---|---|
| Tiered | 0.05%, min €1.25, max €29.00, plus exchange and clearing fees | 0.05%, min €1.25, max €29.00, plus exchange, clearing and regulatory fees | 0.05%, min GBP 1.00, no max | 0.05%, min USD 1.70, max USD 39 |
| Fixed, Smart-routed | 0.05%, min €3.00, no max | 0.05%, min €3.00, no max | min GBP 3.00 | min USD 4.00 |
| Fixed, direct-routed | 0.10%, min €4.00 | 0.10%, min €4.00; SWB 0.12% min €6.00; GETTEX 0.05% min €3.00 | min GBP 4.00 | min USD 6.00 |

- UK EUR-denominated lines follow the EUR schedule (tiered min €1.25, max €29).
- Volume tiers drop to 0.03% / 0.02% / 0.015% above €50m / €100m / €500m per month.
- IBKR's summary: "Commissions on Western European stocks is just £3/€3 per trade for typical trade sizes. For larger trades (those over £6000/€6000) the cost is .05% of trade value."
- Disclosure: "Euronext (FR/NL/BE) – EUR 0.75 per execution exchange fee passed through on ETF products only."
- Tiered volume breaks are computed once daily on monthly cumulative value.

**Commissions: US stocks and ETFs** — [IBKR Ireland, Commissions Stocks/ETFs (Americas tab)](https://www.interactivebrokers.ie/en/pricing/commissions-stocks.php)

| | Rate | Minimum | Maximum |
|---|---|---|---|
| Fixed | USD 0.005/share | USD 1.00 | 1% of trade value |
| Tiered | USD 0.0035/share (≤300k shares/month), falling to 0.0020 / 0.0015 / 0.0010 / 0.0005 | USD 0.35 | 1% of trade value; a note elsewhere says "Tiered commissions will be capped at 0.5% of trade value" |

- Fixed example: 100 shares at USD 25 costs USD 1.00.
- Third-party fees:
  - SEC fee USD 0.0000206 × value of sales;
  - FINRA CAT USD 0.000003 × quantity;
  - "Fee Holiday of Trading Activity Fee for trades from Oct 1, 2026 through Dec 31, 2026";
  - tiered clearing (NSCC/DTC) USD 0.00020/share;
  - pass-through fees: NYSE 0.000175 × commission, FINRA 0.00056 × commission.

**FX, withdrawals and other fees**
- **FX conversion**: "0.20 basis point * Trade Value" for monthly volume ≤ USD 1bn, minimum USD 2.00 per order (Tier I). IBKR says it charges a commission instead of marking up quotes — [IBKR Ireland, Spot Currencies commissions](https://www.interactivebrokers.ie/en/pricing/commissions-spot-currencies.php).
- **Withdrawals**: "IBKR allows two free withdrawal requests per calendar month." After that, EUR 8.00 by bank transfer or EUR 1.00 by SEPA — [IBKR Ireland, Other Fees](https://www.interactivebrokers.ie/en/pricing/other-fees.php).
- **Inactivity fee**: none appears on the Other Fees page (searched for "inactiv", no hit) — [IBKR Ireland, Other Fees](https://www.interactivebrokers.ie/en/pricing/other-fees.php).

**Market data needed for API trading**
- **Requirements for API market data**:
  1. an opened account (demo accounts cannot subscribe);
  2. "Must use an IBKR PRO account type";
  3. "$500 USD in their account in addition to the cost of all market data subscriptions";
  4. subscribe through the Client Portal;
  5. "enable Market Data API access".
  - Source: [IBKR docs, Market Data Requirements](https://www.interactivebrokers.com/docs/general/market-data-subscriptions/market-data-requirements.md).
- **Minimum equity**: USD 500 for individual accounts, and data is terminated after a violator notice if equity falls below USD 500. Market-data compliance questionnaires must be completed, "otherwise your user will automatically be set to deny API market data access" — [IBKR docs, Minimum Equity](https://www.interactivebrokers.com/docs/general/market-data-subscriptions/market-data-subscription-minimum-equity-balance-requirements.md); [IBKR docs, API market data compliance](https://www.interactivebrokers.com/docs/general/market-data-subscriptions/compliance-requirements-for-api-market-data/introduction.md).
- **Free data**: free non-consolidated US streaming from Cboe One and IEX, free delayed data elsewhere, and 100 free snapshot quotes per month. Subscriptions "will not be pro-rated." All clients get at least 100 concurrent market-data lines — [IBKR Ireland, Market Data Pricing](https://www.interactivebrokers.ie/en/pricing/market-data-pricing.php).
- **Monthly prices**, read as non-professional / professional columns:
  - **US Securities Snapshot and Futures Value Bundle**: USD 10.00, waived at USD 30 of monthly commissions;
  - **NYSE (Network A/CTA) L1, Network B L1, NASDAQ (Network C/UTP) L1**: USD 1.50 each / USD 45, 25, 25;
  - **Spot Market Germany (Frankfurt/Xetra) L1**: EUR 16.25 / EUR 78.50;
  - **Deutsche Boerse ETFs**: "Fee Waived" / EUR 5.50;
  - **Cboe EU Equities L1**: "Fee Waived" / GBP 39;
  - **LSE UK L1**: GBP 1.00 / GBP 56; LSE International L1 GBP 1.00 / GBP 31;
  - **Euronext Cash L1**: a single value, EUR 91.50;
  - **Europe Equity and Derivative Display Value Bundle**: EUR 12.50 "Base Waived for Activity". Includes top-of-book from Borsa Italiana, Eurex Retail Europe, Euronext Basic, Cboe Global Markets Europe, Nordic, Tradegate and Turquoise.
  - Source: [IBKR Ireland, Market Data Pricing](https://www.interactivebrokers.ie/en/pricing/market-data-pricing.php).

**API operations: TWS / IB Gateway**
- **Daily**: in "Global Configuration – Lock and Exit… For API users, it is recommended to choose 'Never lock Trader Workstation' and 'Auto restart'." **Weekly**: "The weekly authentication cycle starts on every Monday." The error "Login failed = Soft token=0 received instead of expected permanent…" means a manual login is needed — [IBKR TWS API docs, Daily & Weekly Reauthentication](https://www.interactivebrokers.com/docs/tws-api/doc/tws-settings/daily-weekly-reauthentication.md).
  - A third-party guide places the forced weekly login at the first start after Sunday 01:00 New York time, which conflicts with IBKR's "Monday" wording — [pickmytrade guide](https://blog.pickmytrade.io/interactive-brokers-tws-gateway-automation-setup-guide/).
- **TWS API requirements**: "A funded and opened IBKR Pro account", the current Stable or Latest TWS/Gateway and TWS API, and "Minimum supported Python release is version 3.11.0." The API "migration to Protobuf" is noted. A paper-trading account is available, but it "relies on more simulated technologies" and execution may differ — [IBKR docs, Requirements](https://www.interactivebrokers.com/docs/tws-api/doc/notes-limitations/requirements.md); [IBKR docs, TWS API Limitations](https://www.interactivebrokers.com/docs/tws-api/doc/notes-limitations/tws-api-limitations.md).
- **2FA during the week (forum reports)**: weekday auto-restarts normally do not ask for 2FA, "But if Gateway should crash or… a permanent data freeze, you will be asked for 2FA" — [EliteTrader "Questions on automating IB"](https://elitetrader.com/et/threads/questions-on-automating-ib.372642). If the IBKR Mobile 2FA prompt times out, "you have to intervene manually at TWS/Gateway" — [IBC GitHub issue #194](https://github.com/ibcalpha/ibc/issues/194).
- **IBC is retired**: "This repository was archived by the owner on Sep 1, 2026. It is now read-only… This project has been retired, as of 1 September 2026." There will be no new development beyond in-progress work and significant bug fixes. Its features included participating in 2FA via IBKR Mobile and weekday auto-restart; it cannot complete logins that need a physical card or device code — [IbcAlpha/IBC GitHub](https://github.com/IbcAlpha/IBC).
- **Fork**: `ibc2` 0.1.0 (first and only PyPI release, 10 October 2026, GPL-3.0) calls itself "a maintained fork of IBC". It adds a watchdog, alerts, a weekly re-login reminder and a Docker image — [PyPI ibc2](https://pypi.org/project/ibc2/).
- **Python client**:
  - `ib_async` latest is 2.1.0 (8 December 2025; first release March 2024), BSD, Python ≥3.10. It continues ib_insync after its author Ewald de Wit's "unexpected passing in early 2024" and is maintained by Matt Stancliff — [PyPI ib_async](https://pypi.org/project/ib_async/).
  - `ib_insync` last released 0.9.86 on 2 July 2023 — [PyPI ib_insync](https://pypi.org/project/ib_insync/).
  - QuantConnect's IBAutomater handles restarts "requiring full authentication only weekly" — [awesome.ecosyste.ms entry](https://awesome.ecosyste.ms/projects/github.com%2FQuantConnect%2FIBAutomater).

### Inferences
- **Worked cost examples** (my arithmetic from the IBIE schedule; tiered third-party exchange and clearing fees not included):

  | Order | Tiered | Fixed |
  |---|---|---|
  | €2,000 Xetra ETF | €1.25 (minimum, 6.3 bp) | €3.00 (15 bp) |
  | €10,000 | €5.00 | €5.00 |
  | €100,000 | €29 (cap, 2.9 bp) | €50 |
  | Euronext Paris ETF, any size | as above | add €0.75 per execution |

  - With €10k–€50k and frequent rebalancing of small slices, the tiered minimum (€1.25) beats the fixed minimum (€3). For a monthly rebalance of 10 lines at €2k each, that is ~€12.5 (tiered) vs ~€30 (fixed) per rebalance.
- **FX is negligible per conversion.** €10,000 to USD costs 0.2 bp = ~USD 0.20, so the USD 2 minimum applies. Trading USD-denominated LSE lines, or holding USD cash, adds currency exposure but little cost.
- **Minimum realistic market-data budget for an API strategy on Xetra ETFs**: roughly €0–16/month.
  - Deutsche Boerse ETFs and Cboe EU are shown as fee-waived for non-professionals.
  - Spot Market Germany L1 is EUR 16.25.
  - Adding US L1 for signals costs about USD 4.50 (3 × USD 1.50) or the USD 10 snapshot bundle.
  - The USD 500 minimum equity is not binding for €10k+.
- **Signal timing**: a signal computed after the US close (about 22:00 CET) can only execute at the next European session. The backtest should assume next-day execution, on the open or a VWAP proxy, for UCITS lines.
- **Operational risk is material**:
  - with IBC archived, unattended operation relies on IBKR's built-in auto-restart, an unproven fork (`ibc2`), or IBAutomater;
  - a human must approve the IBKR Mobile prompt at least weekly, and after any crash;
  - a daily-bar strategy tolerates this if orders are sent with a margin before the open and failures alert the operator.

### Gaps
- **Tiered third-party fees** per Xetra and Euronext execution were not quantified (behind a sub-page).
- **Euronext Cash L1 non-professional price is ambiguous** (single value EUR 91.50 shown). It is unclear whether the "Display" value bundle is usable through the API: the page notes the service is "not eligible for use in alternative display formats". The bundle's activity-waiver threshold is also unclear: a nearby footnote mentions "at least USD 35 in commissions per month", attribution uncertain.
- **Whether historical-bar API requests need the same L1 subscription** as streaming for each exchange is not confirmed from IBKR text retrieved here. The historical-data docs pages did not load.
- **Compatibility of ib_async 2.1.0 with IBKR's Protobuf-migrated TWS API** (newest Gateway builds) was not verified.
- **IBKR interest on idle EUR cash** at IBIE (an alternative to XEON) was not checked.

---

## 4. French taxation in 2026 (CTO at IBKR vs PEA)

### Takeaway
Capital gains and dividends in a CTO are taxed under the PFU at **31.4%** (12.8% income tax + 18.6% social levies) since the LFSS 2026 raised CSG from 9.2% to 10.6% (Loi n° 2025-1403, art. 12). The barème progressif remains optional. Losses carry forward 10 years against same-nature gains.

An IBKR account is a foreign account:
- it must be declared every year on form 3916 (€1,500 fine per undeclared account per year);
- the investor self-reports gains (form 2074);
- the investor self-pays the 12.8% dividend prepayment via form 2778-DIV-SD.

The PEA (€150k ceiling, 5-year rule, only 18.6% social levies on gains after 5 years) is far more tax-efficient but cannot be held at IBKR, and no broker was confirmed to offer retail API trading on a PEA.

### Cited Findings
- **PFU at 31.4%**: "La plus-value réalisée est soumise au prélèvement forfaitaire unique au taux de 31,4 % (12,8 % d'impôt sur le revenu et 18,6 % de prélèvements sociaux). Cependant, vous pouvez choisir le barème progressif." New for 2026 income: "Pour vos revenus de 2026 (à déclarer en 2027)… vous pourrez renoncer à votre option pour le barème progressif (dans le délai de réclamation ou en cours de contrôle)" — [service-public.fr F21618, verified 15 April 2026](https://www.service-public.gouv.fr/particuliers/vosdroits/F21618).
- **Social levies, official breakdown**:
  - **general case for revenus du patrimoine**: CSG 10.6% + CRDS 0.5% + prélèvement de solidarité 7.5% = 18.6%;
  - **revenus de placement**: 2025 income 17.2%, 2026 income 18.6% (general case);
  - **revenus fonciers and plus-values immobilières**: still 9.2% CSG, 17.2% total;
  - **legal basis**: "Loi n° 2025-1403 du 30 décembre 2025 de financement de la sécurité sociale pour 2026, Article 12 (hausse de la CSG)";
  - PEA gains on withdrawal or closure are subject to social levies;
  - Source: [service-public.fr F2329, verified 30 June 2026](https://www.service-public.gouv.fr/particuliers/vosdroits/F2329).
- **LFSS 2026 text and timing**: article 12 amends art. L.136-8 CSS to 10.6% for certain capital income, published in the JO on 31 December 2025, in force 1 January 2026, expected yield about €1.2bn (search summary of [Simon Associés, Lettre de la Fiscalité Jan. 2026](https://simonassocies.com/wp-content/uploads/2026/01/Lettre-de-la-Fiscalite-Janvier-2026-1.pdf) and [Sénat report](https://www.senat.fr/rap/a25-747/a25-7474.html)).
  - The parliamentary path was contested: the Senate deleted the increase in first reading on 21 November 2025 before it was reinstated — [Legifiscal](https://www.legifiscal.fr/actualites-fiscales/4338-plfss-2026-senat-annule-hausse-flat-tax.html); [Fiscalonline](https://fiscalonline.com/outils-fiscaux/PLFSS2026-la-hausse-de-CSG-sur-les-revenus-du-capital-de-1-4-point-definitivement-supprimee-au-Senat).
- **What stays at 9.2% CSG and what pays 10.6%** (secondary source):
  - stays at 9.2%: PEL interest, life insurance, real-estate gains and rental income;
  - pays 10.6% (PFU 31.4%): stock-market income, gains on sales of securities, savings accounts, PER;
  - a "rétroactivité" applies to certain 2025 income, including gains on shares;
  - Source: [Meilleurtaux, April 2026](https://placement.meilleurtaux.com/placement-financier/actualites/2026-avril/flat-tax-a-31-4-ce-qui-change-depuis-janvier-2026.html).
  - Sources disagree on exactly what applies to 2025 income — [Moneyvox](https://www.moneyvox.fr/impot/actualites/108354/declaration-impots-2026-le-casse-tete-de-la-hausse-de-la-csg-a-10-6-sur-les-placements); [actu-juridique (title/snippet)](https://www.actu-juridique.fr/fiscalite/fiscal-finances/la-csg-en-hausse-sur-les-revenus-du-capital/).
- **Possible further rise**: a further increase toward 36% was still being discussed in 2026 — [MeilleureSCPI](https://www.meilleurescpi.com/actualites/flat-tax-vers-un-bond-de-30-a-36-en-2026/). This is speculative and not enacted per the sources found.
- **Capital-loss carryforward**: losses cannot be deducted from global income. They must first offset same-year gains of the same nature; any excess "vous pourrez le déduire des plus-values que vous réaliserez au cours des 10 années suivantes", oldest losses first — [service-public.fr F21618](https://www.service-public.gouv.fr/particuliers/vosdroits/F21618).
- **PEA rules** ([service-public.fr F2385, verified 22 May 2026](https://www.service-public.gouv.fr/particuliers/vosdroits/F2385)):
  - **ceiling**: €150,000 of contributions, gains excluded; €20,000 for an attached adult child; PEA + PEA-PME combined capped at €225,000;
  - **eligibility**: French tax domicile required; one PEA per person;
  - **eligible funds**: UCITS and similar funds investing more than 75% in shares of companies within the EU/EEA rules;
  - **before 5 years**: any withdrawal generally closes the plan, with exceptions for dismissal, invalidity, early retirement, liquidation and business creation;
  - **after 5 years**: a partial withdrawal does not close the plan, and new deposits remain possible;
  - **inside the plan**: gains reinvested in the PEA are exempt from income tax and social levies;
  - **on withdrawal**: gains always bear social levies, and income tax is exempt after year 5.
  - Before 5 years, gains bear 12.8% IR + 18.6% social levies (31.4%) per secondary sources — [Nalo](https://blog.nalo.fr/fiscalite-pea/); [Finary](https://finary.com/fr/blog/epargne/plans/pea/fiscalite-pea).
  - PEA gains bear the 18.6% rate in 2026 — [Bourseinside](https://bourseinside.fr/patrimoine/pea-la-hausse-des-cotisations-sociales-a-186-en-2026-va-t-elle-grignoter-des-centaines-deuros-sur-vos-gains-sans-que-vous-layez-prevu/).
- **PEA and API trading**:
  - Saxo Banque France offers PEA, PEA-PME and CTO — [Moneyvox review of Saxo](https://www.moneyvox.fr/bourse/actualites/107162/ai-teste-saxo-banque-avis-de-moneyvox-sur-le-pea-et-le-cto-du-courtier-en-bourse).
  - Saxo also offers OpenAPI (contact openapisupport@saxobank.com) — [Saxo France API page](https://www.home.saxo/fr-fr/platforms/api).
  - No source confirms that OpenAPI can trade a PEA account.
- **Form 3916**:
  - foreign accounts opened, held, used or closed, including at investment-service providers, must be declared with the income return;
  - fine of €1,500 per undeclared account per year (art. 1736 IV-2 CGI), €10,000 if the state has no administrative-assistance agreement with France;
  - alternatively an 80% surcharge on resulting reassessments (art. 1729-0 A);
  - reassessment period extended to 10 years (art. L.169 LPF);
  - undeclared funds presumed to be income (art. 1649 A);
  - Source: [Fiscaloo, updated 20 April 2026](https://www.fiscaloo.fr/1280-declaration-de-compte-a-letranger-comment-faire-et-sanctions-encourues/) (secondary); [JeChange](https://www.jechange.fr/banques/news/compte-titres-etranger-degiro-etoro-3916-bis-amende-1500-euros).
- **Dividends received through a foreign broker**:
  - they bear a 12.8% "prélèvement forfaitaire obligatoire non libératoire", which the taxpayer pays using form 2778-DIV-SD (2026 version published) and reports in box 2CK — [impots.gouv.fr form 2778-DIV-SD (2026)](https://www.impots.gouv.fr/sites/default/files/formulaires/2778-div-sd/2026/2778-div-sd_5389.pdf);
  - payment is due within the first 15 days of the month after the dividend (art. 1671 C CGI), and the prepayment is credited against final tax — [Maxcompta](https://maxcompta.com/blogs/investissement/dividendes-etrangers-compte-titres-credit-impot) (secondary).
- **US dividends**:
  - the France–US treaty (art. 10) caps US withholding at 15% for French residents with a valid W-8BEN; otherwise 30% applies;
  - France grants a tax credit capped at the 15% treaty withholding (form 2047, box 8VL);
  - Source: [Rotek (secondary)](https://rotek.fr/convention-fiscale-france-usa-dividendes-interets-plus-values/); [TD W-8BEN instructions (FR)](https://www.td.com/francais/document/PDF/W8BEN%20Instructions_FRE.pdf).
- **French financial transaction tax (TTF)**:
  - 0.4% on purchases of French companies with market capitalisation above €1bn, since 1 April 2025 (art. 98, LF 2025, loi n° 2025-127);
  - 121 companies are in scope for 2026 (BOFiP list of 17 December 2025);
  - ETFs, bonds and derivatives are out of scope;
  - the tax applies in both PEA and CTO;
  - Source: [Legifiscal TTF page](https://www.legifiscal.fr/placements/epargne/bourse-pea/taxe-transactions-financieres.html); [Legifiscal 1 Dec 2025 list](https://www.legifiscal.fr/actualites-fiscales/4362-taxe-transactions-financieres-liste-societes-concernees-1er-decembre-2025.html).
- **Accumulating vs distributing ETFs in a CTO**: justETF France (15 Jan 2026) says dividends must be declared "même s'ils sont réinvestis" and gives the PFU as 31.4%. It does not mention any annual deemed-distribution tax on accumulating funds — [justETF FR, "Fiscalité des ETF en compte-titres"](https://www.justetf.com/fr/academy/etf-et-fiscalite.html). The statement appears to refer to distributions an investor reinvests, not to fund-level accumulation.

### Inferences
- **Tax drag from turnover** (my arithmetic; illustrative, ignores the 12.8% barème option and loss offsets). Assume 10%/yr pre-tax over 10 years at the 31.4% PFU:
  - **all gains realised every year** (high turnover, CTO): (1 + 0.10 × 0.686)^10 = 1.935, i.e. 6.86%/yr;
  - **gains deferred to year 10** (buy-and-hold accumulating fund, CTO): 1 + 1.594 × 0.686 = 2.093, i.e. 7.67%/yr;
  - **same deferral inside a PEA over 5 years old** (18.6% levies only): 1 + 1.594 × 0.814 = 2.297, i.e. 8.66%/yr.
  - A high-turnover daily or weekly strategy in a CTO gives up roughly 0.8 pp/yr against deferral at these assumptions. The gap grows with return and horizon.
- **France has no annual tax on unrealised gains** in a CTO per the sources found, and none of the sources mentions a deemed-distribution regime for accumulating funds. Accumulating UCITS ETFs therefore defer tax until sale, and distributing funds trigger tax (12.8% prepayment + 18.6% levies) at each distribution. For a self-declaring IBKR client, accumulating share classes also avoid the monthly 2778-DIV-SD paperwork.
- **Irish ETFs holding US stocks**: they suffer US withholding at fund level, which the investor cannot reclaim. Holding Irish-domiciled accumulating funds avoids the investor-level 15% US withholding and the 2047 credit mechanics. The fund-level rate was not verified in this session.
- **Account choice**: a PEA (at a French broker, without API) is best for slow, equity-only strategies using PEA-eligible synthetic ETFs (WPEA/DCAM/ESE/PSP5/PUST/GPEA/USVE). A CTO at IBKR is needed for API automation, bonds, gold, managed futures and non-PEA factor ETFs.
- **Compliance burden of a CTO at IBKR**:
  - an annual 3916;
  - self-computed gains on form 2074 (IBKR is not a French paying agent; no IFU was found to be issued);
  - monthly 2778-DIV-SD for any distribution;
  - 2047 for foreign withholding;
  - EUR conversion of USD trades at the transaction date.

### Gaps
- **2025 vs 2026 split**: whether gains realised in 2025 bear 17.2% or 18.6% (service-public's "revenus du patrimoine, cas général 18.6%" suggests 18.6% for 2025 gains declared in 2026, but press sources conflict). The legislative text of art. 12 was not read (Légifrance returned 403).
- **5%-of-balance fine**: a proportional fine for undeclared foreign accounts above €50k could not be confirmed in current law. The Conseil constitutionnel history is contradictory in sources.
- **2778-DIV-SD and social levies**: whether the form also collects the 18.6% at payment (or whether levies go through the annual return) was not confirmed from the official notice text.
- **Gold ETCs**: French tax treatment of physical-gold ETCs (PFU on securities vs the precious-metals regime) was not found in any official source.
- **PEA at foreign brokers**: no official confirmation that a PEA cannot be opened at a foreign broker such as IBKR (Code monétaire et financier L221-30 not read). No broker was found offering retail API trading on a PEA.
- **Wash sales**: no French wash-sale rule or anti-abuse doctrine on repurchases after loss harvesting was researched.

---

## 5. Data sources for backtesting daily strategies

### Takeaway
- **US equities, survivorship-bias-free**: Norgate is the clear choice. Platinum costs USD 630/yr (history from 1990, delisted stocks, historical index constituents) and Diamond USD 787.50/yr (from 1950). The updater is Windows-centric.
- **Global and UCITS ETF end-of-day**: EODHD covers 150k+ tickers from USD 19.99/month.
- **Free sources**: yfinance (unofficial, rate-limited, personal use only) and Stooq (now behind a CAPTCHA key) are convenient but fragile.
- **Factor and macro series**: Ken French, AQR, the ECB Data Portal (SDMX REST) and FRED are free.

### Cited Findings
- **Norgate Data (US Stocks)**:

  | Package | 12 months | 6 months | History | Delisted / historical constituents |
  |---|---|---|---|---|
  | Silver | USD 270 | USD 148.50 | Last 10 years | No |
  | Gold | USD 360 | USD 198 | Last 20 years (plus fundamentals/extras) | No |
  | Platinum | USD 630 | USD 346.50 | Back to 1990 | Yes |
  | Diamond | USD 787.50 | USD 433.13 | Back to 1950 | Yes |

  - Platinum and Diamond are marked "Suitable for backtesting". Integrations listed include "Python (Windows)" and "Zipline (Windows)". Australian (from 1992) and Canadian (from 1990) packages exist.
  - Source: [Norgate stock market packages](https://norgatedata.com/stockmarketpackages.php); [Norgate subscribe page](https://norgatedata.com/subscribe/subscribe.php).
- **EODHD**:
  - plans: Free (20 API calls/day), "EOD Historical All-World" USD 19.99/mo or USD 199/yr, EOD+Intraday USD 29.99/mo, Fundamentals USD 59.99/mo, All-in-one USD 99.99/mo;
  - paid plans allow 100,000 calls/day; an EOD request costs 1 call and bulk 100+;
  - coverage: "End-of-day covers 150,000+ tickers worldwide, US from the earliest available (Ford Motors from June 1972)"; fundamentals from 1985 (US) and 2000 (non-US);
  - Source: [EODHD pricing](https://eodhd.com/pricing).
- **Alpha Vantage**: "standard API usage limit (25 API requests per day)". Premium runs from USD 49.99/mo (75 requests/min) to USD 249.99/mo (1,200/min) — [Alpha Vantage premium](https://www.alphavantage.co/premium/).
- **Tiingo** (secondary sources): free tier about 50 requests/hour, 1,000/day, 500 unique symbols/month; "Power" about USD 30/mo for individuals (older reviews say USD 10) — [FitGap](https://us.fitgap.com/products/022556/tiingo); [Findmymoat comparison](https://www.findmymoat.com/vs/tiingo-vs-trendlyne); [QuantStart on Tiingo coverage](https://www.quantstart.com/articles/evaluating-data-coverage-with-tiingo/).
- **yfinance**:
  - latest release 1.8.0 (3 November 2026) — [PyPI yfinance](https://pypi.org/project/yfinance/);
  - its README says: "not affiliated, endorsed, or vetted by Yahoo… intended for research and educational purposes… the Yahoo! finance API is intended for personal use only" — [PyPI yfinance](https://pypi.org/project/yfinance/);
  - 2025 issues report `YFRateLimitError` "Too Many Requests" across IPs (versions 0.2.57–0.2.59), alongside the warning that `download()` "has changed argument auto_adjust default to True" — [yfinance issue #2422](https://github.com/ranaroussi/yfinance/issues/2422); [discussion #2431](https://github.com/ranaroussi/yfinance/discussions/2431);
  - a vendor blog claims Yahoo restricted historical downloads to paid users in early 2025 (unverified) — [dev.to](https://dev.to/kevin_menesesgonzlez/i-replaced-yahoo-finance-with-eodhd-heres-what-changed-1c8k).
- **Stooq**:
  - "as of March 2026, Stooq requires an API key for data downloads". pandas-datareader's reader then fails because Stooq returns HTML; the issue is open — [pandas-datareader issue #1012](https://github.com/pydata/pandas-datareader/issues/1012);
  - the key is obtained by solving a CAPTCHA on stooq.com — [Qiita write-up](https://qiita.com/katafuchix/items/c74793e5041e1b5e3051);
  - pandas-datareader's latest release is 0.11.1 (24 June 2026) — [PyPI pandas-datareader](https://pypi.org/project/pandas-datareader/).
- **Ken French Data Library**:
  - free; data shown through September 2026;
  - includes daily and monthly Momentum factor files and size/momentum portfolios;
  - from the January 2025 release, US returns use CRSP's CIZ format, in which "monthly returns are compounded daily returns with dividends reinvested on their ex-dates" (the legacy FIZ format was discontinued after December 2024);
  - Source: [Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).
- **AQR Data Sets** (free, listed with as-of dates):
  - AQR Momentum Indices, monthly (31 Oct 2026);
  - Betting Against Beta, monthly and daily (31 Aug 2026; US plus 23 international markets);
  - The Devil in HML's Details, daily and monthly (31 Aug 2026);
  - Quality Minus Junk (31 Aug 2026; US sample from 1956, global from 1986);
  - Value and Momentum Everywhere factors and portfolios, monthly (31 Aug 2026; eight markets and asset classes);
  - Source: [AQR Datasets](https://www.aqr.com/Insights/Datasets).
- **ECB Data Portal**: "The ECB SDMX 2.1 RESTful web service offers programmatic access to the statistical data and metadata disseminated via the ECB Data Portal", for example the USD/EUR exchange-rate series — [ECB Data Portal API overview](https://data.ecb.europa.eu/help/api/overview).
- **IBKR as a data source**: API market data requires a Pro account, USD 500 equity and subscriptions — [IBKR docs](https://www.interactivebrokers.com/docs/general/market-data-subscriptions/market-data-requirements.md). ib_async shows daily bars via `reqHistoricalData(..., durationStr='1 Y', barSizeSetting='1 day', whatToShow='TRADES', useRTH=True)` — [PyPI ib_async README](https://pypi.org/project/ib_async/).

### Inferences
- **Recommended stack for the stated use case** (daily multi-asset ETF strategy, EUR accounting):
  - Signal research on US ETF and index proxies with long history:
    - **US ETF prices**: Norgate (if Windows is acceptable) or Tiingo/EODHD;
    - **factor history**: Ken French and AQR monthly/daily factors back to 1926/1956;
    - **EUR/USD**: ECB reference rates;
    - **€STR or a cash proxy**: ECB Data Portal.
  - Implementation-level backtests on UCITS lines (Xetra/LSE tickers): EODHD All-World or IBKR historical bars for the exact listed instruments.
- **Survivorship bias** matters only for single-stock universes. ETF-only strategies need total-return (dividend-adjusted) series and care with fund closures. Yahoo's adjusted prices change retroactively, so snapshot and version any downloaded data.
- **Don't build a production pipeline on yfinance or Stooq** given the 2025–2026 instability. Use them only for quick cross-checks.

### Gaps
- **Not verified**: Tiingo's official price and EOD history depth (JS page), Nasdaq Data Link/Sharadar pricing and delisted coverage (JS page), FRED API terms and rate limits (fetch failed).
- **EODHD delisted coverage** and its UCITS ETF adjustment quality were not verified.
- **Norgate on Linux**: whether its data can be used from Linux without Windows (e.g. via export) was not confirmed. Its integrations list says "Python (Windows)".
- **AQR**: whether the "Time Series Momentum" and "Century of Factor Premia" data sets remain on the page was not confirmed (the page excerpt listed other sets).
- **History length on UCITS ETFs** in EODHD and Tiingo was not checked per ticker.

---

## 6. Backtesting tools for a daily multi-asset portfolio with EUR accounting

### Takeaway
For a daily multi-asset, weight-based (rebalancing) strategy:
- **bt** (MIT, 1.4.1, Oct 2026) and **vectorbt** (1.2.0, Oct 2026) fit best for research;
- **QuantConnect LEAN** (CLI 1.0.233, Oct 2026) is the only mainstream option with native multi-currency cash and IBKR live integration, with `SetAccountCurrency("EUR")`;
- **zipline-reloaded** (3.2.1, Oct 2026) is maintained but US-calendar and bundle-centric;
- **backtrader** has had no release since April 2023;
- **Backtesting.py** (0.6.6, July 2026, AGPL) is single-instrument.

### Cited Findings
- **Release status (PyPI, retrieved 2026-11-10)**:

  | Package | Latest release | First release | Python | Licence / notes |
  |---|---|---|---|---|
  | vectorbt | 1.2.0, 19 Oct 2026 | Dec 2020 | ≥3.11, <3.15 | |
  | backtrader | 1.9.78.123, 19 Apr 2023 | | | No release since |
  | zipline-reloaded | 3.2.1, 25 Oct 2026 | | 3.11–<3.15 | |
  | lean (QuantConnect CLI) | 1.0.233, 27 Oct 2026 | | ≥3.9 | |
  | bt | 1.4.1, 10 Oct 2026 | 2014 | ≥3.9 | |
  | backtesting (Backtesting.py) | 0.6.6, 22 Jul 2026 | | ≥3.9 | AGPL-3.0 |
  | nautilus_trader | 1.231.0 stable, 2.0.0rc8 on 29 Oct 2026 | | ≥3.12 | |

  Sources: [PyPI vectorbt](https://pypi.org/project/vectorbt/); [PyPI backtrader](https://pypi.org/project/backtrader/); [PyPI zipline-reloaded](https://pypi.org/project/zipline-reloaded/); [PyPI lean](https://pypi.org/project/lean/); [PyPI bt](https://pypi.org/project/bt/); [PyPI backtesting](https://pypi.org/project/backtesting/); [PyPI nautilus_trader](https://pypi.org/project/nautilus_trader/).
- **vectorbt**: "the open-source community edition of VectorBT PRO". The README advertises analysing multiple assets "with flexible array broadcasting" and portfolio backtesting. PRO adds "parallelization, additional data integrations, portfolio optimization… limit orders, leverage, and over 100 other features" — [PyPI vectorbt README](https://pypi.org/project/vectorbt/).
- **bt**: lets you "combine algorithms for scheduling, security selection, weighting, and rebalancing", "nest strategies and securities in a common tree", and "configure commissions and transaction cost models", with statistics via ffn — [PyPI bt README](https://pypi.org/project/bt/).
- **zipline-reloaded**: uses `exchange_calendars` ≥ 4.2 and constrains pandas below 3.0. Python 3.14 needs pandas 2.3.3 / NumPy 2.3.3+, and Python 3.15 is not supported — [PyPI zipline-reloaded README](https://pypi.org/project/zipline-reloaded/). Norgate lists a "Zipline (Windows)" integration — [Norgate subscribe page](https://norgatedata.com/subscribe/subscribe.php).
- **QuantConnect LEAN, EUR accounting**:
  - `SetAccountCurrency` is called in `Initialize` and can be set only once ("LEAN ignores each additional call");
  - portfolio values are reported in the account currency, and LEAN "may add internal security subscriptions" to convert;
  - Source: [QuantConnect docs, Cashbook](https://www.quantconnect.com/docs/v2/writing-algorithms/portfolio/cashbook).
  - Forum history conflicts on how well EUR works: a staff post says if the IB base currency is EUR, LEAN sets AccountCurrency to EUR; other posts say only USD is fully supported — [QC forum "Hacking LEAN to use EUR… with IBKR"](https://www.quantconnect.com/forum/discussion/10518/hacking-lean-to-use-eur-instead-of-usd-with-ibkr/); [QC forum "Interactive Brokers doubts"](https://www.quantconnect.com/forum/discussion/17309/interactive-brokers-doubts/).
- **Backtesting.py**: a user running ~12 instruments separately said the next step, "rebalancing and optimizing the portfolio among multiple instruments", would need source changes. Portfolio-level multi-asset backtests are not supported out of the box — [kernc/backtesting.py discussion #254](https://github.com/kernc/backtesting.py/discussions/254).

### Inferences
- **Suggested pipeline**:
  1. Convert all USD series to EUR with ECB reference rates (or IBKR FX) before the backtest. vectorbt, bt and Backtesting.py have no documented native multi-currency cash book.
  2. Run weight-based rebalancing in bt (simplest for allocation and rotation) or vectorbt (fast parameter sweeps; use grouped or cash-sharing portfolios for multi-asset).
  3. Model IBIE costs per order: tiered 0.05% with €1.25 minimum and €29 cap, plus about €0.75 per Euronext ETF execution and FX 0.2 bp (USD 2 minimum).
  4. Apply PFU 31.4% in a post-processing tax layer: realised gains per calendar year, with 10-year loss carryforward.
- **LEAN is worth the complexity only** if one engine should cover backtest plus IBKR live. Validate EUR-base behaviour on paper trading first, given the conflicting forum reports.
- **Avoid for new work**: backtrader (unmaintained since 2023) and Backtesting.py (single asset, AGPL). Zipline-reloaded is viable but its US-centric calendars and bundles add friction for Xetra/LSE UCITS lines.

### Gaps
- **Not verified**: vectorbt's current handling of cash sharing and rebalancing across groups in 1.2.0 (docs not fetched), and LEAN's support for Xetra/LSE UCITS ETF data and order routing for IBIE accounts.
- **GitHub activity** (commits, open issues) could not be queried; GitHub API access was unavailable in this session. Maintenance status rests on PyPI release dates only.
- **nautilus_trader**: whether its Interactive Brokers adapter supports EUR-base IBIE accounts was not researched.
