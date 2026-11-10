# Interactive Brokers (IBKR, via Interactive Brokers Ireland Ltd) as the CTO for a France tax resident (status: November 2026)

Research date: 10 Nov 2026. Method note: interactivebrokers.ie / .com / .co.uk pages returned HTTP 403 to the automated fetcher. Figures attributed to IBKR therefore come from (a) search-engine snippets of the official IBKR pages, (b) IBKR press releases as reproduced by wire services, or (c) French/EU comparison sites that restate IBKR's grid. Each item says which. **Anything marked "UNVERIFIED" could not be checked on an official page.**

**Biggest finding:** the brief assumes IBKR offers no PEA. That is out of date. IBKR has offered a **PEA Classique** to French tax residents since a July 2024 beta, with a formal launch announced 20 Nov 2024. The plan's premise ("PEA must be at a French broker") no longer holds. The investor can still choose a French broker for the PEA, and there are good reasons to (see sections 1, 3 and 8).

---

## 1. Does IBKR offer a PEA / PEA-PME to French residents? Can securities be moved from a CTO into a PEA?

### Takeaway
IBKR **does** offer a PEA (classic only). It has no PEA-PME and no PEA Jeune. It opened as a beta in July 2024 for existing CTO holders, was formally launched on 20 Nov 2024, and opened to all French tax residents as a stand-alone account in 2025. IBKR issues an IFU for the PEA but **not for the CTO**. As expected, securities cannot be moved from a CTO into a PEA. Only cash can go in: sell, then deposit the cash, within the €150k contribution cap.

### Cited Findings
- IBKR press release dated **20/21 Nov 2024**, "Interactive Brokers Launches Plan d'Epargne en Actions (PEA Classique) Accounts". IBKR calls it "une étape importante afin d'accélérer notre croissance en France" — [IBKR press release](https://interactivebrokers.ie/en/general/about/mediaRelations/11-21-24.php); [Business Wire FR, 20 Nov 2024](https://www.businesswire.com/news/home/20241120296817/fr); [Zacks, 21 Nov 2024](https://www.zacks.com/stock/news/2373452/interactive-brokers-enhances-offerings-unveils-pea-classique-account)
- The IBKR French PEA page (search snippet) says: "Pour ouvrir un PEA vous devez être un résident fiscal français et âgé d'au moins 18 ans". The English page says "A single tax declaration form (IFU) is available for your PEA" — [IBKR PEA page (FR)](https://www.interactivebrokers.ie/fr/accounts/plan-depargne-en-action-accounts.php?menu=B); [IBKR PEA page (EN)](https://interactivebrokers.ie/en/accounts/plan-depargne-en-action-accounts.php)
- Timeline: beta in **July 2024**, open only to clients who already had a CTO. In **2025** it opened to all French tax residents as a stand-alone account — [PEA.fr review, updated 15 Jan 2026](https://pea.fr/courtier/pea-interactive-brokers-avis-2026/); [Finary forum thread, Jul–Nov 2024](https://community.finary.com/t/pea-interactive-brokers-vos-avis/16234)
- IBKR PEA features (per Sinvestir, updated **7 Jul 2026**):
  - Fees: 0.05% per order (min €1.25, max €29) on the tiered plan, which must be chosen at opening. €0 custody, opening and closing fees. One free withdrawal per month, then €8.
  - Universe: European shares and PEA-eligible ETFs.
  - **Not available:** PEA-PME, PEA Jeune, scheduled (recurring) investments, fractional shares.
  - Incoming PEA transfers are supported.
  - Opening a PEA automatically opens an ordinary CTO.
  - IFU provided for the PEA. **Form 3916 still required each year.**
  - Source: [Sinvestir – Interactive Brokers avis](https://sinvestir.fr/interactive-brokers-avis/)
- PEA.fr (15 Jan 2026) adds:
  - Contracting entity is IBIE (Central Bank of Ireland).
  - IBKR is said to use French partner banks such as Société Générale Securities Services for some custody and EUR-flow functions. UNVERIFIED claim from a secondary source.
  - Incoming transfers are semi-manual and take about 3–6 weeks.
  - Source: [PEA.fr](https://pea.fr/courtier/pea-interactive-brokers-avis-2026/)
- **Outbound PEA transfer friction (pitfall):**
  - A Finary thread from **22 Sep – 6 Oct 2026** reports that an IBKR PEA could not be transferred to Trade Republic. TR's form demands an IBAN, and IBKR support says the PEA has none: it is "une poche fiscale mais pas un vrai compte", with cash flowing via the linked CTO.
  - The thread ends with no reported resolution.
  - Source: [Finary – Transfert PEA de IBKR -> Trade Republic impossible ?](https://community.finary.com/t/transfert-pea-de-interactive-brokers-trade-republic-impossible/39808)
- Inside IBKR, funding the PEA is an internal **cash** transfer from the CTO. Securities do not move — [Finary thread (2024)](https://community.finary.com/t/pea-interactive-brokers-vos-avis/16234)
- **CTO → PEA securities transfer:**
  - Cafedelabourse: it is impossible to transfer securities from a CTO into a PEA. The route is to sell on the CTO, transfer the cash to the PEA, and buy again — [Cafedelabourse](https://www.cafedelabourse.com/transfert-pea-compte-titre-pourquoi-comment-proceder)
  - MoneyVox (25 May 2025): a PEA can only be funded "par l'intermédiaire d'un virement depuis un compte ou d'un paiement par carte bancaire". It also restates the €150k PEA cap and the €225k combined PEA + PEA-PME cap — [MoneyVox](https://www.moneyvox.fr/bourse/actualites/103489/comment-transferer-des-actions-de-mon-compte-titres-a-mon-pea-et-inversement)
  - Nuance: a CMS Francis Lefebvre note describes a narrow tolerance for reclassifying securities bought outside the PEA by mistake. It requires that the PEA cash account hold the securities' market value, and it may trigger taxation of the latent gain. This is an edge case, not a funding route — [CMS](https://cms.law/en/fra/legal-updates/achats-de-titres-hors-du-pea-peut-on-se-raviser)

### Inferences
- The investor could hold the core MSCI World PEA ETF in an IBKR PEA. That gives one platform and one login, possibly API access to the PEA (UNVERIFIED).
- The trade-offs:
  - The IBKR PEA also triggers a form 3916 each year.
  - It has no recurring investment and no fractional shares.
  - Small orders hit the €1.25 minimum.
  - Outbound transfers have documented friction.
  - Against that, a French-broker PEA needs no 3916, and some offer a free monthly order (Fortuneo) or free orders on selected ETFs (see section 6).
- For a monthly DCA of a few hundred euros into one ETF, a French-broker PEA remains the lower-friction choice. The brief's two-broker split is still sensible, but for different reasons than "IBKR has no PEA".
- Anything bought in the IBKR CTO stays in the CTO. To shift money to the PEA later, sell first (taxable at the PFU), then deposit cash.

### Gaps
- Could not open IBKR's PEA page directly. The list of eligible PEA ETFs, including whether Amundi/iShares MSCI World PEA swap ETFs are tradable, could not be verified.
- Whether the IBKR PEA is reachable through the TWS API: not verified.
- Sinvestir lists the PEA's "domicile" as Germany while PEA.fr says the contracting entity is IBIE (Ireland). The custody arrangement is unclear.

---

## 2. Costs for this use case (€300–€1,000 UCITS ETF orders, monthly; €10k–€30k account)

### Takeaway
**Commissions:**
- Tiered: 0.05% of trade value, **minimum €1.25 per order**, plus exchange and clearing pass-through fees.
- Fixed: 0.05% with a **€3 minimum**, all-in.
- For €300–€1,000 orders the minimum always binds. Tiered costs roughly €1.3–€2.6 per order depending on venue; Fixed costs €3 flat. That is 0.13%–1.0% of the order, versus €0–€1 at the cheapest IFU brokers.

**Other costs:**
- No custody, inactivity or monthly fees since July 2021.
- FX is very cheap in percentage terms (0.002%) but carries a **$2 minimum**, so small conversions are expensive. Prefer EUR lines on Xetra or Euronext.
- **Recurring investment with fractional shares** works for European ETFs at IBIE. Since June 2026, **iShares UCITS ETFs bought through Recurring Investment are commission-free from €10** in the EEA.
- No interest is paid on the first €10k of EUR cash.
- Live market data is optional for manual trading. Each exchange is billed separately (for example Xetra ETFs €1/month non-pro).

### Cited Findings
- **Tiered:** 0.05%, **min €1.25**, third-party fees added on top; recommended for orders under €6,000.
- **Fixed:** 0.05%, **min €3.00**, third-party fees included.
- PEA.fr warns accounts are often set to Fixed by default and must be switched to Tiered manually, possibly effective the following month (UNVERIFIED on IBKR site).
- Source: [PEA.fr, 15 Jan 2026](https://pea.fr/courtier/pea-interactive-brokers-avis-2026/)
- Sinvestir (7 Jul 2026), French market on the CTO: 0.05% (min €1.25, max €29) on the tiered plan — [Sinvestir](https://sinvestir.fr/interactive-brokers-avis/)
- Signal Alpha (Jul 2026): IBKR Euronext order ~€500 = "1,25 € min (Tiered); 0,05 % min 1,25 €"; custody €0; FX 0.002% min $2 — [Signal Alpha CTO comparison](https://signal-alpha.fr/comparatif-choix-du-cto/)
- When IBKR introduced fixed pricing in Europe (2021), it advertised "€3 / £3 per trade" for Western European stocks, with 0.05% of trade value for trades over €6,000/£6,000. Tiered pricing remains available alongside — [Irish Times (2021)](https://www.irishtimes.com/business/financial-services/interactive-brokers-announces-new-flat-fee-structure-to-entice-european-investors-1.4624976); [Portfolio.hu, 22 Jul 2021](https://portfolio.hu/en/business/20210722/interactive-brokers-introduces-low-simple-stock-pricing-in-europe-493696)
- Xetra exchange fee (snippet of IBKR's Xetra fee page): 0.0072% of trade value on standard orders, **EUR 0.90 minimum per order**. This is charged on top of Tiered commission. UNVERIFIED: the page itself was not opened, and it may differ for ETFs or be updated — [IBKR Xetra (IBIS) fees](https://www.interactivebrokers.co.uk/en/accounts/fees/IBIS-StkFees.php)
- A 2026 third-party EU cost index snippet appears to show €500 orders at ~€1.30 vs €3.00 and ~€2.55 vs €3.00 (tiered vs fixed on two venues). Column labels were not visible, so treat this as indicative only — [Quantroutine EU broker cost index](https://quantroutine.com/studies/eu-broker-cost-index/)
- **FX conversion:** 0.002% with a minimum of $2 on the CTO. Sinvestir separately quotes 0.006% (min €1.20) inside the PEA — [Sinvestir](https://sinvestir.fr/interactive-brokers-avis/); [Signal Alpha](https://signal-alpha.fr/comparatif-choix-du-cto/). IBKR's own site banner (2026 snippets) advertises "low 0.03% FX rates". This does not match the 0.002% grid figure; the banner may be an all-in marketing number — [IBKR interest page snippet](https://www.interactivebrokers.ie/en/accounts/fees/pricing-interest-rates.php)
- **Inactivity / monthly fees:**
  - IBKR eliminated inactivity fees effective **1 July 2021**. The previous fee was USD 10/month for NAV < $100k — [IBKR communiqué Q3 2021 (EMEA)](https://interactivebrokers.ie/en/general/communiques/2021/2021-Q3-vol15-emea.php); [Finance Magnates](https://www.financemagnates.com/forex/brokers/interactive-brokers-eliminates-monthly-account-inactivity-fees/)
  - IBKR's minimums page lists inactivity fees at USD 0.00 for Pro and Lite — [IBKR Required Minimums](https://www.interactivebrokers.com/minimums)
  - That page also shows a "Starting the 9th month: USD 2,000/month" minimum-commission row. Its scope is unclear (likely specific account types such as advisor or broker accounts, not individual Pro) — UNVERIFIED.
  - PEA.fr: no custody fee and no inactivity fee — [PEA.fr](https://pea.fr/courtier/pea-interactive-brokers-avis-2026/)
- **Interest on cash:**
  - IBKR pricing page snippet (2026): "Clients with a NAV of more than USD 100,000 … earn an annual rate of 1.501% on their EUR cash balances above EUR 10,000 … Interest will not be payable on the first EUR 10,000."
  - The EUR benchmark was 2.241% on 17 Jul 2026.
  - Source: [IBKR interest rates](https://www.interactivebrokers.ie/en/accounts/fees/pricing-interest-rates.php); [IBKR benchmark rates](https://interactivebrokers.ie/en/pricing/reference-benchmark-rates-int.php)
  - Signal Alpha: "Cash interest only above 10,000 $" — [Signal Alpha](https://signal-alpha.fr/comparatif-choix-du-cto/)
- **Fractional shares and Recurring Investment:**
  - IBKR introduced fractional trading in European stocks and ETFs on **31 May 2022** — [Business Wire](https://www.businesswire.com/news/home/20220531005157/en/Interactive-Brokers-Introduces-Fractional-Shares-Trading-in-European-Stocks-and-ETFs)
  - IBKR knowledge base: Recurring Investment is available to clients with fractional trading enabled under IBLLC, IBUK, … **IBIE** …; it covers "US, Canadian and European stocks/ETFs", but only those tradable in fractions — [IBKR KB 4470](https://ibkb.interactivebrokers.com/de/node/4470)
  - **9 Jun 2026:** IBKR launched commission-free iShares UCITS ETFs within Recurring Investment across the EEA. Clients can pick single ETFs or portfolios "starting from just €10, without paying trading commissions" — [Business Wire, 9 Jun 2026](https://www.businesswire.com/news/home/20260609598644/en/Interactive-Brokers-Launches-Commission-Free-iShares-ETFs-from-BlackRock-through-Recurring-Investment-Feature-Across-Europe); [FX News Group](https://fxnewsgroup.com/forex-news/retail-forex/interactive-brokers-launches-commission-free-etfs-within-its-recurring-investment-feature-for-eligible-investors-across-eea/)
  - One secondary source says Belgian retail clients are excluded. France is not reported as excluded (UNVERIFIED).
  - Non-iShares recurring purchases pay normal commission. One guide says "EUR 1.25 min (Tiered)" — [Freenance](https://freenance.io/etf/ibkr-recurring-investment-2026-eu-investors-etf-stocks-fees-tax-vs-trade-republic-comparison/)
  - Recurring investment and fractional shares are available on the CTO but **not on the PEA** — [Sinvestir](https://sinvestir.fr/interactive-brokers-avis/)
- **Market data:**
  - IBKR European fee table (snippet): "German Indices & Xetra ETFs" **EUR 1.00/month non-pro** (EUR 6 pro); "LSE Level I+" **GBP 5.00/month non-pro** — [IBKR market data pricing](https://www.interactivebrokers.ie/en/index.php?f=39876)
  - Market data requires a **USD 500 minimum equity** for individual accounts (HK page; Irish page assumed similar, UNVERIFIED). The subscription cost must also be covered.
  - Clients get **100 free snapshot quotes per month**; further snapshots are charged per quote — [IBKR market data pricing (HK)](https://www.interactivebrokers.com.hk/en/pricing/market-data-pricing.php)
  - A 2026 developer blog says the API uses the same market data subscriptions as TWS (third-party) — [DEV Community](https://dev.to/xqliu/interactive-brokers-market-data-subscription-which-one-do-i-actually-need-in-2026-164g)

### Inferences
- **Worked examples, Tiered, Xetra EUR line:**
  - €300 order: commission €1.25 (0.05% = €0.15, so the minimum binds) + exchange fee about €0.90 if the snippet applies ≈ **€2.15 ≈ 0.7%**.
  - €1,000 order: ≈ €2.15 ≈ **0.2%**.
  - Fixed would be €3.00, i.e. 1.0% and 0.3%.
  - On Euronext, tiered appears closer to ~€1.30 all-in for €500 (indicative).
  - The minimum binds until about €2,500 per order (€1.25 / 0.05%).
- **The cheapest path at IBKR for this plan:**
  - Buy iShares ETFs through Recurring Investment (commission-free since June 2026). The iShares Edge MSCI World Momentum Factor UCITS ETF is an iShares product, as are iShares Treasury and Quality ETFs. Eligibility of each specific ISIN in IBKR's commission-free list must be checked.
  - Non-iShares lines (e.g. a managed-futures UCITS ETF) pay normal tiered commissions.
  - Batch purchases (e.g. quarterly instead of monthly per ETF) to dilute the €1.25 minimum.
- **Avoid FX:** the $2 minimum means converting €300 costs about 0.6%. Buy EUR-denominated listings (Xetra / Euronext Amsterdam) rather than USD/GBP LSE lines. Fund the account in EUR.
- **Cash interest:** with a €10k–€30k NAV, expect roughly zero interest. Nothing is paid on the first €10k, and NAV is below the $100k threshold, where a pro-rata reduction is commonly reported (UNVERIFIED). This also means there is usually no foreign interest to declare monthly (see section 3).
- **Market data:**
  - Not needed for monthly manual trading. Delayed or snapshot quotes suffice, and limit orders can be priced from external end-of-day data.
  - For an API system that decides on daily bars, prices can come from a separate end-of-day source. A paid real-time subscription (a few €/month per exchange) is optional but useful for marketable limit pricing.

### Gaps
- Exact current IBKR Ireland Tiered minimums by venue (Euronext vs Xetra vs LSE, including USD-line minimums on LSE) and the current pass-through exchange/clearing fees for ETFs: could not open the official pages.
- The pro-rata cash-interest rule for NAV < $100k: not verified for 2026.
- Euronext non-pro data price at IBKR: ambiguous in snippets.
- Whether the API can place orders with no market data subscription at all: not found.
- The full list of iShares ETFs eligible for commission-free recurring investment, and confirmation that French residents are eligible: not verified.

---

## 3. French tax handling with IBKR (no IFU on the CTO)

### Takeaway
IBKR issues **no IFU for the CTO**; it does for the PEA. The investor must:
1. Compute realised gains and losses themselves and report them on **form 2074**, with totals carried to the 2042 / 2042-C.
2. For any dividends or interest paid by IBKR, file the **2778-DIV-SD** (dividends) or 2778-SD (interest) **within the first 15 days of the month after payment**, with payment of the 12.8% prepayment plus social contributions, and declare the income on 2047 / 2042.
3. File **form 3916** every year for **each** IBKR account (CTO, and PEA if opened), **even if empty or unused**. The penalty is €1,500 per account per year.

The flat-tax rate is **31.4% in 2026** (12.8% income tax + 18.6% social contributions), up from 30%.

### Cited Findings
- **No IFU on the CTO:**
  - "Pour le CTO IBKR, l'IFU n'est pas fourni à ce jour". For the CTO, Sinvestir lists: "No IFU, so the investor must calculate gains and dividends from account statements". 3916 is required yearly for both accounts — [Sinvestir, 7 Jul 2026](https://sinvestir.fr/interactive-brokers-avis/)
  - Signal Alpha (Jul 2026): IBKR, French IFU = **No**; "Cerfa 3916-bis required" — [Signal Alpha](https://signal-alpha.fr/comparatif-choix-du-cto/)
  - One source (Rotek) says IBKR provides no IFU at all and transmits nothing to the tax office. This conflicts with IBKR's PEA IFU, so it likely describes the CTO or an older period — [Rotek](https://rotek.fr/tag/fiscalite/)
- **2074 and 2047:** "Comme tout courtier étranger, Interactive Brokers exige … la déclaration du compte à l'étranger chaque année via le formulaire 3916 / 3916-bis … la saisie manuelle des plus-values et dividendes dans la déclaration n°2074". Another review notes 2074 (gains) and 2047 (foreign income) must be filled from the broker's activity reports — [PEA.fr IBKR page](https://pea.fr/courtiers/interactive-brokers/); [Top10banques](https://www.top10banques.com/courtier/interactive-brokers)
- **Form 3916 (JeChange, 14 Oct 2026):**
  - Legal basis: art. 1649 A CGI. "Tout compte ouvert, détenu, utilisé ou clos dans l'année" at a non-French institution must be declared.
  - **Empty accounts must be declared** until closed. Accounts without income must still be declared. A closed account is declared one last time in the year of closure. The obligation repeats every year.
  - Penalties (art. 1736 CGI): **€1,500 per undeclared account per year**, €10,000 for a non-cooperative state. The tax-assessment period extends from 3 to 10 years for income from that account (art. L169 LPF).
  - IBKR (Irish entity) is named explicitly as an account to declare.
  - Source: [JeChange, 14 Oct 2026](https://www.jechange.fr/banques/news/compte-titres-etranger-degiro-etoro-3916-bis-amende-1500-euros)
- **2778-DIV-SD (official form):**
  - It is Cerfa 12658, used to declare dividends received outside France and subject to the flat prepayment — [Service-public](https://entreprendre.service-public.fr/vosdroits/R19114?lang=en)
  - The 2021 form notice: prepayment at **12.8%** plus social contributions (then 17.2%). The form "doit être déposée dans les quinze premiers jours du mois suivant celui" of payment, with payment. It may be filed by the taxpayer or by a mandated EU paying agent — [impots.gouv 2778-DIV-SD notice (2021)](https://www.impots.gouv.fr/portail/files/formulaires/2778-div-sd/2021/2778-div-sd_3467.pdf)
  - A **2026 version** of the form exists. It mentions payment in cash or by crossed cheque to the Trésor Public and must be made out in euros, which suggests a paper procedure (online filing not verified) — [impots.gouv 2778-DIV-SD (2026)](https://www.impots.gouv.fr/sites/default/files/formulaires/2778-div-sd/2026/2778-div-sd_5389.pdf)
  - JeChange (Oct 2026) mentions 2778-DIV for dividend prepayment and 2778 for interest prepayment, and 2047 for declaring dividends and interest in spring — [JeChange](https://www.jechange.fr/banques/news/compte-titres-etranger-degiro-etoro-3916-bis-amende-1500-euros)
- **2026 flat tax:** Finance Law 2026 summary: for "les dividendes, les plus-values de cession de valeurs mobilières … les intérêts", the rate goes "de 30% à 31,4% (12,8% d'impôt sur le revenu et 18,6% de prélèvements sociaux)" — [LF 2026 summary (Zoominvest PDF)](https://strapi-aws-s3-images-bucket-zoominvest.s3.amazonaws.com/Loi_de_Finances_pour_2026_focus_sur_les_mesures_phares_ab55cd6863.pdf)
- New French withholding guidance on art. 119 bis A II CGI (in force Jan 2026, guidelines 16 Mar 2026) concerns dividends under 0% treaty rates, not this use case — [International Tax Review](https://www.internationaltaxreview.com/article/2g68zj9igvia8dz4yhq0w/sponsored/withholding-on-0-french-treaty-dividends-a-procedural-shift-with-substantive-effects)
- IBKR "ne retient pas cette taxe pour toi. Tu devras la calculer et la déclarer toi-même" (secondary) — [Top10banques](https://www.top10banques.com/courtier/interactive-brokers)

### Inferences
- **Practical recipe for this plan:**
  - Hold only **accumulating** UCITS ETFs in the IBKR CTO, and keep EUR cash below €10k (which earns no interest anyway). Then there are no dividends or interest, so **no monthly 2778 filings**. The annual burden is the 3916 per account plus the 2074 in any year with a sale.
  - With a buy-and-hold or monthly-rebalance strategy, sales still occur (momentum rotation, rebalancing), so a 2074 will be needed most years once the strategy starts trading.
- **Gain computation:**
  - French rules compute gains on securities using the weighted-average acquisition price (PMP), in euros, with foreign-currency prices converted at each transaction date. IBKR's reports default to FIFO lots and the account's base currency.
  - Flex Queries (CSV/XML of trades with dates, prices and FX rates) should be set up from day one to rebuild PMP per ISIN. This is general knowledge and **UNVERIFIED this session** against BOFiP / art. 150-0 D CGI.
- For anyone who already holds an IBKR account, the 3916 obligation applies for every tax year it was open, even if unused. If a past year was missed, regularise it.
- If an IBKR PEA is opened, IBKR auto-opens a linked CTO. Each account number probably needs its own 3916 line (inference from "per account" rule).

### Gaps
- IBKR's official tax-document page and the exact names of its reports (Activity Statement, Realized P&L, Flex Query, PortfolioAnalyst): not opened; tools exist but are UNVERIFIED this session.
- Exact 2042 / 2042-C box numbers (e.g. 3VG for net gains, 2CK for prepayment credit, 2OP option): not verified on impots.gouv this session.
- The dispensation from the 12.8% prepayment for households under the income threshold (request by 30 Nov of year N-1; social contributions still due): not verified.
- Whether the 18.6% social-contribution rate applies to the 2778-DIV-SD in 2026, and whether online filing exists: not verified on official pages.

---

## 4. Investor protection, financial strength, reputation, incidents 2024–2026

### Takeaway
- **Statutory protection:** the Irish ICS pays **90% of net loss up to €20,000** per investor if the firm fails. That is much less than France's FGDR (€70,000 for securities).
- **Excess insurance:** IBKR says Irish-protected clients also fall under IB LLC's excess-SIPC Lloyd's policy, up to $30M with a $900k cash sub-limit (aggregate cap applies).
- **Size:** IBKR is very large and well capitalised: about 5.58M accounts and about $965bn customer equity in Q3 2026; about $15bn equity capital per a Jan 2026 review.
- **Regulatory record 2024–2026:** US fines only (OFAC $11.8M in July 2025; FINRA $2.25M in January 2025). No Central Bank of Ireland action was found.

### Cited Findings
- **ICS:** "90% of your net loss, limited to a maximum pay out of €20,000" when an authorised investment firm is liquidated or cannot meet investor claims. Market losses and bad advice are not covered. Eligibility depends on the firm, the investment and the circumstances — [CCPC (Irish government consumer agency)](https://www.ccpc.ie/consumers/money/investing/ics-protection)
- IBKR's Irish pages: only certain clients of Interactive Brokers Ireland Limited are covered by the ICS, which is administered by the Investor Compensation Company DAC under the Investor Compensation Act 1998. Irish-protected clients are additionally covered by IB LLC's **Excess SIPC policy placed with certain Lloyd's of London underwriters, up to $30 million (cash sub-limit $900,000)** — [IBKR Client Protection (EN)](https://interactivebrokers.ie/en/general/security-investor-protection.php); [IBKR (DE)](https://interactivebrokers.ie/de/general/security-investor-protection.php) (search snippets)
- An older IBUK disclosure cites an **aggregate** limit of $150M for the excess policy — [Lynx/IBUK disclosure PDF](https://www.lynxbroker.de/media/doc/47_ENG_IBUK_DISCLOSURE_REGARDING_CUSTOMER_ASSET_PROTECTION.pdf)
- Comparison: Signal Alpha cites FGDR coverage of **€70,000 for securities** for a French broker (Boursorama) — [Signal Alpha](https://signal-alpha.fr/comparatif-choix-du-cto/)
- **Scale:**
  - Q3 2026: **5.58M customer accounts (+35% y/y), customer equity $964.7bn (+27%)**, commission revenue +12% to about $600M (reported 16 Oct 2026) — [Webull transcript summary](https://www.webull.com/news/15760509186237440); [S&P Global preview, 14 Oct 2026](https://www.spglobal.com/market-intelligence/en/news-insights/research/2026/10/interactive-brokers-forecast-to-report-12-yoy-increase-in-q3-revenue)
  - PEA.fr cites about $15bn equity capital and a Nasdaq listing — [PEA.fr](https://pea.fr/courtier/pea-interactive-brokers-avis-2026/)
  - Sinvestir: founded 1978, listed, regulated by the Central Bank of Ireland for EU clients — [Sinvestir](https://sinvestir.fr/interactive-brokers-avis/)
- **Regulatory actions:**
  - **OFAC settlement ~$11.8M announced 15 Jul 2025** over sanctions violations spanning about five years — [GlobeGain, 4 Jan 2026](https://globegain.com/news/interactive-brokers-faces-fresh-scrutiny-over-ofac-settlement-as-2025-draws-to-a-close)
  - **FINRA $2.25M (Jan 2025)** for failing to detect "free-riding" violations, 2015–2022 — [GRC Report](https://grcreport.com/post/interactive-brokers-settles-with-finra-over-free-riding-violations); [Law360](https://law360.com/compliance/articles/2278836&read_main=1&nlsidx=0&nlaidx=4)
  - Older: $38M SEC/FINRA/CFTC AML penalty (date not shown in results; believed 2020, UNVERIFIED) — [Investment Executive](https://www.investmentexecutive.com/news/regulation/u-s-broker-fined-by-sec-cftc-and-finra/)
  - FCA fined IBUK just over £1M for suspicious-transaction reporting failures (date not shown; believed 2018, UNVERIFIED) — [Investment Week](https://www.investmentweek.co.uk/investment-week/news/3025243/fca-fines-uk-arm-interactive-brokers-gbp1m-failing-report-suspicious-trades)
- French users raised questions about the Irish domicile, the guarantee and the depositary in 2024 — [Finary 2024 thread](https://community.finary.com/t/pea-interactive-brokers-vos-avis/16234)

### Inferences
- For a €10k–€30k account, the €20k ICS cap plus the excess policy is adequate in practice. The real risk is operational (account lock, KYC freeze, platform error), not insolvency.
- The regulatory actions are AML/sanctions compliance failures at US entities. None concerns misuse of client assets.

### Gaps
- Could not open IBKR's client-asset segregation text for IBIE (Central Bank of Ireland Client Asset Requirements, sub-custodians).
- The official ICCL page and payout timelines: not checked.
- IBKR's exact Q3 2026 equity capital from its own press release: not found; figures are from secondary sources.
- No 2024–2026 incident specific to IBIE (outages, account freezes) was found. A focused search on outages was not done.

---

## 5. API practicalities (IBKR Pro, IB Gateway re-authentication, IBC retirement, ib_async)

### Takeaway
- The TWS API needs **IBKR Pro**; Lite lacks API access per multiple sources. No specific minimum equity for API use was found, beyond the USD 500 equity needed for market data subscriptions.
- IB Gateway can auto-restart daily, but a full **2FA login is required once a week**. Community sources put the reset at Sunday ~01:00 US/Eastern; an IBKR doc snippet describes a weekly cycle.
- **IBC** (the de facto tool for unattended Gateway login) was **retired and archived on 1 Sep 2026**. A community fork ("ibc2") exists on PyPI.
- **ib_async** (successor to ib_insync) is community-maintained by Matt Stancliff and appears active.

### Cited Findings
- **Lite vs Pro:** API access is listed as Pro-only, and a NinjaTrader forum thread notes "IBKR Lite accounts do not support connecting to an API" (third-party sources) — [IBKR FAQ aggregator](https://rithmic-html-css.pages.dev/broker-faq/ib-faq/); [Tradersunion](https://tradersunion.com/brokers/fond/view/interactive_brokers/ibkr-pro-vs-ibkr-lite); IBKR's own comparison page: [Compare IBKR Lite and Pro](https://www.interactivebrokers.com/en/general/compare-lite-pro.php) (not openable)
- **Re-authentication:**
  - IBKR has official pages on "Daily & Weekly Reauthentication" for TWS / IB Gateway. The snippet says the weekly authentication cycle starts each week and recommends IB Gateway for API use, since it is not locked by inactivity — [IBKR TWS API docs](https://www.interactivebrokers.com/docs/tws-api/doc/tws-settings/daily-weekly-reauthentication)
  - The IBC GitHub discussion says weekly 2FA credentials are invalidated "Sunday at 01:00 US/Eastern", that at least one full 2FA authentication per week is required with no workaround, and that a TOTP (Mobile Authenticator) method allows unattended weekly login — [IBC discussion #313](https://github-users.yhajoa.workers.dev/IbcAlpha/IBC/discussions/313)
  - QuantRocket: "the Sunday auto-restart will require two-factor authentication. On other days, the auto-restart will automatically log you back in" — [QuantRocket support](https://support.quantrocket.com/t/auto-restart-with-two-factor-authentication/2167)
- **IBC retirement:** "This project has been retired, as of 1 September 2026 … This repository was archived by the owner on Sep 1, 2026". Only work in progress and significant bug fixes will be completed; no replacement is named; users are pointed to the IBC User Group and may fork — [IbcAlpha/IBC on GitHub](https://github.com/IbcAlpha/IBC)
- **ibc2 fork:** "IBC … retired upstream in September 2026"; it works with standalone IB Gateway, and Gateway is recommended for always-on use — [PyPI ibc2](https://pypi.org/project/ibc2/)
- **ib_async:**
  - Maintained by Matt Stancliff, open to new committers. 857 commits, 29 open issues. It implements the IBKR binary protocol itself, so `ibapi` is not needed.
  - The README describes a stable Gateway (updated every few months) and a latest Gateway (weekly), and recommends 4096 MB Java memory.
  - ib_insync's author maintained it until his death in early 2024; the project was then renamed ib_async.
  - Source: [ib_async on GitHub](https://github.com/ib-api-reloaded/ib_async)
- One forum user claims the Client Portal Web API uses OAuth with no 2FA or GUI. This is anecdotal: for retail, the Web API usually still needs a Client Portal Gateway session — [Elite Trader thread](https://elitetrader.com/et/threads/2-factor-auth-with-automated-trading.368494/latest); related: [voyz/ibeam](https://github.com/voyz/ibeam)

### Inferences
- For **monthly** decisions, a fully unattended stack is unnecessary. Run the strategy once a month (or weekly): start IB Gateway, approve 2FA on the phone (IBKR Mobile), place orders via ib_async, check fills, shut down. This sidesteps IBC's retirement entirely.
- For always-on operation, choose between:
  - the ibc2 fork or a pinned IBC 3.x release, plus TOTP 2FA (more security-sensitive);
  - a Docker image that bundles Gateway and IBC.
  - Either way, expect a manual intervention roughly weekly when something breaks.
- Use a **cash account** (not margin) to enforce "no leverage". Then a buy in a currency you don't hold cannot silently create a loan (general IBKR behaviour, UNVERIFIED this session).
- Paper-trading accounts mirror the API and are free for testing (general knowledge, UNVERIFIED this session).

### Gaps
- Whether IBKR Lite is offered at all to IBIE (EU) clients, and the exact official wording on API access for Pro vs Lite: not verified on an official page.
- The exact official weekly reset time (Sunday vs Monday per time zone): the official page could not be opened.
- Whether placing API orders requires a live market data subscription: not found.
- The latest ib_async release number and date: not visible on GitHub page fetch.

---

## 6. Alternatives for a French CTO that issue an IFU and have low ETF costs

### Takeaway
French brokers (BoursoBank, Fortuneo, Bourse Direct) and Trade Republic or Saxo all provide an IFU and avoid most of the DIY tax work. Except for Trade Republic, none requires a 3916. Trade Republic's 3916 status is disputed.

They are cheap for small **Euronext** orders: €0–€1.99 for ≤€500 at Bourse Direct, Fortuneo or Boursorama; €1 at Trade Republic, €0 with a savings plan. They are **expensive or limited on foreign venues** such as Xetra and LSE, where niche UCITS ETFs like momentum or managed futures may be listed. They offer **no public trading API**, except Saxo (OpenAPI, UNVERIFIED this session).

### Cited Findings (Signal Alpha CTO comparison, updated Jul 2026, unless noted — [Signal Alpha](https://signal-alpha.fr/comparatif-choix-du-cto/))
- **Trade Republic:**
  - €1 per order (€0 via savings plan), "1 € on all venues incl. Xetra". Custody €0; FX about 0.25% in the spread.
  - **IFU: yes** ("dividend reporting should be checked manually"). About 2,000 ETFs and 7,500 stocks in savings plans; fractional shares; cash 2.00% gross.
  - TR's own support page describes an IFU available at the start of the tax season — [Trade Republic support – IFU](https://support.traderepublic.com/en-gr/3256-Imprim%C3%A9-Fiscal-Unique-(IFU)
  - Secondary sources conflict on whether TR withholds the PFU at source and whether a 3916 is needed — [Primebanque](https://www.primebanque.fr/guides/impots-trade-republic/); [Rotek](https://rotek.fr/trade-republic-declaration-impots-france/)
  - A Finary user found the TR tax statement differed from their own calculation. Another said it "isn't an official IFU" — [Finary](https://community.finary.com/t/pea-et-cto-finary/35240?page=2)
- **Saxo:**
  - Classic plan 0.08% (min €2 on Euronext). Custody €0; FX 0.25%. IFU pre-filled into the tax return. 50+ markets.
  - No fractional shares or savings plan. Transfer out €50 per ISIN, capped at €160.
- **Boursorama / BoursoBank:**
  - Découverte €1.99 (≤€500); Classic €5.50 (≤€1,000); US €6.95. FX 0.25%.
  - €5.95/month inactivity fee on Classic/Trader plans.
  - IFU "most reliable"; FGDR €70,000 for securities. About 15 markets; no fractional shares.
- **Fortuneo:**
  - Starter: first order each month ≤€500 free, then 0.35%. Progress: €4.90.
  - US: 0.20% (min €20) + €30 foreign broker fee. FX 0.12%. IFU pre-filled. Transfer out €15 per line.
- **Bourse Direct:**
  - €0.99 (≤€500) on Euronext; US €8.50. Custody 0.036% per year on foreign exchanges. FX 0.08%.
  - IFU yes. Transfer out €15 per line.
- Signal Alpha does not cover **API availability** for any broker.
- Another 2026 comparison: Bourse Direct €0 on 27 ETFs (incl. Amundi). Saxo's 0.08% is best for large orders or foreign exchanges. Fees cited for BoursoBank range from €1.99 to €6.95 depending on source and plan — [Sinvestir CTO comparison](https://sinvestir.fr/comparatif-courtiers-en-bourse-en-ligne)
- Finary users (2024) found Fortuneo or BoursoBank cheaper than IBKR for small regular purchases: Fortuneo's free first monthly order ≤€500, BoursoBank's free orders on selected ETFs — [Finary](https://community.finary.com/t/pea-interactive-brokers-vos-avis/16234)

### Inferences
- **Cost comparison for a €300–€1,000 monthly order:**
  - Euronext, French broker: €0–€5.50.
  - Trade Republic: €1 (or €0 via savings plan).
  - IBKR: about €1.3–€2.2 tiered, or €0 for iShares ETFs via Recurring Investment.
  - IBKR is not the cheapest for small single orders, except on iShares recurring plans.
- IBKR's advantage is **universe** (any UCITS ETF on any EU/UK venue at the same 0.05% grid), **FX cost**, and the **API**.
- The French brokers' advantages are the **IFU**, **no 3916** (except possibly TR), **FGDR €70k protection**, and simpler French-language support.
- Trade Republic is the closest cheap IFU-issuing substitute for monthly ETF buys. It has no official API (unofficial libraries only, UNVERIFIED), a narrower venue list, and its IFU reliability is debated.
- Saxo is the only IFU-issuing alternative with a public API (UNVERIFIED this session). Its 0.08% / min €2 fees and 0.25% FX are higher than IBKR's.

### Gaps
- Xetra/LSE order fees at French brokers for €500–€1,000: not stated in the comparison.
- Whether the specific UCITS ETFs (MSCI World Momentum, managed-futures UCITS) are tradable at each alternative: not checked.
- Saxo's OpenAPI retail availability in France in 2026: not verified.
- Trade Republic's 3916 status and withholding behaviour: sources conflict.
- Official broker grids were not opened; comparison-site figures may lag.

---

## 7. Practitioner opinions from French investors

### Takeaway
French forum and blog opinion is consistent:
- IBKR is serious, very cheap for large orders and international access, and has excellent FX.
- It is complex (TWS), support is "competent but cold", often in English and slow on complex issues, and Trustpilot sits around 3/5.
- For small monthly DCA, French brokers or Trade Republic are usually cheaper and simpler.
- The missing IFU and the yearly 3916 are the most cited drawbacks of the CTO.
- In September–October 2026, users reported trouble transferring an IBKR PEA out.

### Cited Findings
- **Finary, Jul–Nov 2024 thread:**
  - "IBKR est avantageux pour les (très) gros ordres" (Oliver82, 16 Nov 2024).
  - Seriousness "n'est plus à prouver" (26 Jul 2024).
  - Doubts about Irish domicile and guarantees, and "Je préfère un broker qui livre un produit fini" (Equilibrium, 2 Aug 2024).
  - No SYEP (securities lending) on the PEA.
  - Fortuneo and BoursoBank cheaper for small regular buys.
  - Source: [Finary – PEA IBKR vos avis](https://community.finary.com/t/pea-interactive-brokers-vos-avis/16234)
- **Finary, Sep–Oct 2026:** an outbound PEA transfer to TR was blocked by the IBAN requirement; no resolution — [Finary thread](https://community.finary.com/t/transfert-pea-de-interactive-brokers-trade-republic-impossible/39808)
- **Finary:** a user worried that the Finary–IBKR aggregation agreement grants trading permissions, and asked how to revoke it — [Finary](https://community.finary.com/t/supprimer-definitivement-finary-d-interactive-brokers/19079)
- **Sinvestir (7 Jul 2026):**
  - Platform rated 1/5: "powerful but complex, aimed at professional traders".
  - Trustpilot about 3.7/5 (PEA) and 3/5 (CTO).
  - Cons: no IFU on the CTO, annual 3916, slow handling of complex issues.
  - Pros: among the lowest fees if Tiered is chosen; very low FX.
  - Source: [Sinvestir](https://sinvestir.fr/interactive-brokers-avis/)
- **PEA.fr (15 Jan 2026):** support "competent but cold, often in English", replies in 24–48h; strict KYC and 2FA frustrate some users; the €1.25 minimum makes small monthly investing costly — [PEA.fr](https://pea.fr/courtier/pea-interactive-brokers-avis-2026/)

### Inferences
- A profile like this plan's (systematic, API, multi-venue UCITS, comfortable with DIY tax) is the profile these reviewers say IBKR fits. Their complaints mostly concern beginners and small DCA savers.

### Gaps
- MoneyVox and Bogleheads France opinions specific to IBKR CTO taxation were not retrieved. Reddit was not attempted.

---

## 8. Verdict: is IBKR a good choice for this plan?

### Takeaway
**Yes, IBKR is a good choice for the satellite CTO, especially once the strategy is API-driven.** It is a poor choice for anyone who wants zero tax paperwork. The brief's premise that IBKR has no PEA is wrong: an IBKR PEA exists. For a small monthly DCA into the core World ETF, however, a French-broker PEA remains preferable, because it means no extra 3916, cheaper or free small orders, an easy exit transfer, and FGDR cover.

### Cited Findings
- (Synthesis of sections 1–7; key sources: [Sinvestir](https://sinvestir.fr/interactive-brokers-avis/), [Signal Alpha](https://signal-alpha.fr/comparatif-choix-du-cto/), [PEA.fr](https://pea.fr/courtier/pea-interactive-brokers-avis-2026/), [JeChange](https://www.jechange.fr/banques/news/compte-titres-etranger-degiro-etoro-3916-bis-amende-1500-euros), [IBC](https://github.com/IbcAlpha/IBC), [CCPC/ICS](https://www.ccpc.ie/consumers/money/investing/ics-protection), [Business Wire 9 Jun 2026](https://www.businesswire.com/news/home/20260609598644/en/Interactive-Brokers-Launches-Commission-Free-iShares-ETFs-from-BlackRock-through-Recurring-Investment-Feature-Across-Europe))

### Inferences

**Good for:**
- Access to virtually any UCITS ETF on Xetra, LSE or Euronext at one 0.05% grid. This includes niche lines (managed futures, momentum, Treasuries, gold ETCs) that French brokers price badly or don't list.
- Very cheap FX for large conversions.
- €0 custody and no inactivity fee.
- Fractional shares and Recurring Investment on the CTO, with **commission-free iShares UCITS ETFs via Recurring Investment since June 2026**. The momentum, quality and Treasury sleeves may qualify if iShares lines are used.
- A mature API (TWS API + ib_async) with paper trading.
- A large, listed, well-capitalised firm.

**Not good for:**
- Single small orders: the €1.25 tiered minimum plus about €0.90 Xetra fee is roughly 0.4–0.7% on €300. Fixed is €3.
- Small FX conversions: the $2 minimum.
- Earning interest on a small cash balance: nothing on the first €10k.
- Tax simplicity: no IFU on the CTO.
- Strong statutory protection: €20k ICS versus €70k FGDR.
- Hands-off automation, since weekly 2FA remains and IBC is retired as of Sep 2026.
- Hosting the core PEA, if the priority is recurring buys, fractional shares and frictionless exit. The IBKR PEA has none of the first two, and exit friction was reported in Sep–Oct 2026.

**Obligations and pitfalls the investor must handle:**
1. **Form 3916 every year for every IBKR account**: CTO, and PEA if opened, which auto-creates a CTO. This applies **even if the account is empty or unused**, and already applies to the existing account. Penalty: €1,500 per account per year, and a 10-year reassessment window.
2. **Self-computed capital gains on form 2074** (carried to 2042 / 2042-C), at the PFU of **31.4% in 2026**.
   - Rebuild weighted-average cost in euros from IBKR Flex Query exports. IBKR reports FIFO in base currency; the PMP and FX-conversion rules are UNVERIFIED this session.
   - Set up the export from the first trade.
3. **Monthly 2778-DIV-SD / 2778-SD** (filed by the 15th of the following month, with payment) if the account ever receives dividends or interest.
   - Avoid it by holding **accumulating** ETFs only and keeping cash under the €10k no-interest threshold.
   - Declare any such income on 2047 / 2042.
4. **Configure costs deliberately:**
   - Switch from Fixed (possible default) to **Tiered**.
   - Buy **EUR-denominated listings** to avoid the $2 FX minimum.
   - Use Recurring Investment for eligible iShares ETFs, and batch other purchases to dilute the €1.25 minimum.
   - Market data is optional. Data subscriptions need USD 500 equity, and Xetra ETFs cost €1/month non-pro.
   - Use a cash (non-margin) account to enforce no leverage.
5. **API operations:**
   - Use an IBKR Pro account.
   - Plan for a weekly 2FA login on IB Gateway.
   - Don't build on IBC: it was retired on 1 Sep 2026. Use the ibc2 fork, or simply run the monthly rebalance with a manual login.
   - Pin ib_async and Gateway versions, and test on a paper account first.
- **Structural point:** money cannot move from the IBKR CTO to the PEA as securities. Rebalancing between the two accounts means selling (a taxable event) and depositing cash, so the PEA/CTO split should be decided up front.

### Gaps
- All IBKR fee figures should be re-checked on interactivebrokers.ie (blocked to the automated fetcher here). This covers Tiered minimums per venue, ETF exchange fees, the FX commission (0.002% grid vs "0.03%" banner), French eligibility for commission-free iShares recurring plans, and the cash-interest pro-rata rule.
