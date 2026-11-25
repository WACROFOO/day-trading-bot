# OKX EU venue check (OKX Europe Ltd, Malta), as of 25 Nov 2026

Scope: a France-based retail investor running a small, spot-only, low-turnover BTC bot through an API. Everything was checked on 25 Nov 2026.

Tags:
- **[OFFICIAL]**: an OKX page or the OKX API docs.
- **[REG]**: a regulator.
- **[PRESS]**: press coverage.
- **[SNAPSHOT]**: my own pull from the public OKX and Kraken APIs at about 10:30 UTC on 25 Nov 2026.
- **[UNVERIFIED]**: not confirmed.

**The entity.**
- **ESMA register** [REG]: OKX Europe Limited, LEI 54930069NLWEIGLHXU42, supervised by the MFSA. Authorised 27/01/2025, with France in its passport list. Address: Piazzetta Business Plaza, Sliema, Malta. Source: [ESMA CASPS.csv](https://www.esma.europa.eu/sites/default/files/2024-12/CASPS.csv), downloaded 25 Nov 2026 (row last updated 28/11/2025).
- **AMF** [REG]: lists the same firm under its former name, "OKCoin Europe Limited", as a MiCA passport into France dated 15/02/2025, with 9 services including custody and operating a trading platform. Source: [AMF printout](https://www.amf-france.org/sites/institutionnel/files/pdf/75638/en/OKCoin_Europe_Limited.pdf), printed 5 Aug 2026.
- **The old French entity is gone.** OKX France Technology Company Ltd SAS (PSAN E2023-106) asked to be struck off on 17 Mar 2025, and the AMF decided on 28 Jul 2025. It had never started custody. French clients are therefore served from Malta. Source: [AMF decision](https://www.amf-france.org/sites/institutionnel/files/private/2025-07/decision_de_radiation_okx.pdf).
- **Access:** EU users register on my.okx.com and must use the API domain `eea.okx.com`.

---

## 1. Fees

- **Spot-only account, Regular tier, since 25 Sep 2026 10:00 CEST:**
  - 0.10% maker / 0.20% taker on all pairs.
  - 0.00% maker / 0.05% taker on stablecoin pairs.
  - VIP1 starts at €100k of assets or €100k of 30-day volume.
  - Source [OFFICIAL]: [OKX notice "Upcoming Spot Fee Adjustment EEA"](https://www.okx.com/en-eu/help/important-notice-upcoming-spot-fee-adjustment-eea), published 11 Sep 2026.
- **With a derivatives (X-Perps) account:** 0.08% / 0.10% [OFFICIAL] ([OKX EEA fees FAQ](https://www.okx.com/help/what-are-the-new-trading-fees-for-eea-users), updated 3 Sep 2026). This does not fit a spot-only plan, and I did not check whether X-Perps is open to French retail.
- **Before Sep 2026:** spot-only Regular was 0.20% / 0.35% from 22 Apr 2026 [OFFICIAL] ([April 2026 notice](https://www.okx.com/help/notice-updates-to-okx-eea-trading-fees)).
- **The EU schedule differs from global OKX.**
  - Global Regular spot: 0.08% / 0.10% from 14 Aug 2026 [OFFICIAL] ([consolidation notice](https://www.okx.com/help/important-notice-consolidation-token-pairs), published 30 Jul 2026).
  - US: 0.20% / 0.35% [PRESS] ([TokenPost, 9 Nov 2026](https://www.tokenpost.com/news/investing/52159)).
  - OKB fee discounts do not apply in the EEA [PRESS] ([Cryptoactu, 24 Oct 2026](https://cryptoactu.com/guides/frais-okx/)).
- **Fee group of BTC-EUR [UNVERIFIED].**
  - The public API gives BTC-EUR `groupId` 18, which is not in the documented list (11 = zero-fee, 12 = group one, 17 = stablecoin).
  - USDC-EUR is group 11, i.e. zero-fee.
  - Plan on 0.10% / 0.20% for BTC traded against EUR or EURC. Confirm with `GET /api/v5/account/trade-fee` once the account is open.
- **SEPA** [OFFICIAL]:
  - No OKX fee on EUR deposits, standard or Instant. Instant is limited to €100k. ([page](https://www.okx.com/en-eu/help/how-do-i-deposit-eur-with-sepa-bank-transfer), updated 20 Nov 2026.)
  - No OKX fee on SEPA withdrawals. The first withdrawal to a new bank account needs a deposit from that account first. ([page](https://www.okx.com/en-eu/help/how-do-i-withdraw-eur-with-sepa-bank-transfer), updated 1 Sep 2026.)

## 2. Pairs: BTC/EURC, BTC/EUR, BTC/USDC

- **There is no separate BTC-EURC instrument. Instead, OKX runs a unified EUR order book.**
  - EUR and EURC markets "share the same order book".
  - BTC-EUR carries `tradeQuoteCcyList: ["EURC","EUR"]`, so you can buy or sell BTC on the BTC-EUR book and settle in EURC by sending the API parameter `tradeQuoteCcy=EURC`. About 270 EUR pairs work the same way.
  - Sources: [OKX FAQ](https://www.okx.com/en-us/help/eea-eurc-orderbook-circle) [OFFICIAL] (published 11 Oct 2026, updated 4 Nov 2026); [The Paypers, 26 Oct 2026](https://thepaypers.com/crypto-web3-and-cbdc/news/okx-launches-unified-eur-order-book-combining-eur-and-eurc) [PRESS]; [SNAPSHOT] from `eea.okx.com/api/v5/public/instruments`.
- **BTC-EUR liquidity** [SNAPSHOT]:
  - 24h volume 130.5 BTC (about €7.1M).
  - Spread 0.3–2 bps.
  - Depth within 0.1% of mid: about €44k on the ask side and €61k on the bid side. Within 0.5%: about €122k and €175k.
  - OKX does not publish how the volume splits between EUR and EURC.
- **BTC-USDC** [SNAPSHOT]: live, listed 21 Aug 2025, 24h volume 696 BTC (about $41M). EEA access is backed by OKX's EU spot-margin launch on BTC/USDC ([The Block, 16 Dec 2025](https://www.theblock.co/post/382815/okx-spot-margin-trading-in-europe-offering-10x-leverage-on-btc-eth)).
- **EURC for EEA users:**
  - EEA users can hold EURC and convert EUR to EURC 1:1; "standard trading fees may apply" [OFFICIAL FAQ above].
  - The standalone EURC-USDC pair (listed 21 Sep 2026) is thin: about 27.5k EURC traded in 24h, spread about 18 bps [SNAPSHOT].
- **Caveat on the snapshot.** `eea.okx.com` returns the same global list of 1,250 instruments as `www.okx.com`, including USDT and TRY pairs. So it does not prove what an EEA account can trade. Check the account-level `GET /api/v5/account/instruments` after onboarding.
- **Kraken at the same time** [SNAPSHOT]:
  - XBT/EURC: 24h volume 0.32 BTC, spread about 10 bps.
  - XBT/EUR: 649 BTC.
  - EURC/EUR: 745k EURC.

## 3. API

- **Permissions and IP rules** [OFFICIAL] ([EU API docs](https://my.okx.com/docs-v5/en/), read 25 Nov 2026):
  - Read, Trade and Withdraw are separate permissions, so a key can be Read + Trade with no withdrawal.
  - "Trade" also allows internal funding transfers (between your own funding and trading accounts and to sub-accounts), not external withdrawals.
  - Each key can bind up to 20 IP addresses or ranges.
  - **Keys with trade or withdraw permission and no IP binding expire after 14 days of inactivity.**
  - Sub-account keys can be created as `read_only,trade` with an IP list.
- **Endpoints:**
  - REST: `https://eea.okx.com`.
  - WebSocket: `wss://wseea.okx.com/ws/v5/{public,private,business}`.
- **`tradeQuoteCcy` is mandatory for some regions.** The docs say: "For users in specific countries and regions, this parameter must be filled out for a successful order. Otherwise … error code 51000 will occur." The bot must send `tradeQuoteCcy=EURC` on every BTC-EUR order.
- **ccxt supports OKX.**
  - Two classes: `okx` (global) and `myokx` ("MyOKX (EEA)", hostname `eea.okx.com`, `mica: True`, not ccxt-"certified") ([ccxt myokx.py](https://github.com/ccxt/ccxt/blob/master/python/ccxt/myokx.py), master branch, 25 Nov 2026).
  - ccxt does not set `tradeQuoteCcy` itself. Its `create_order` passes extra params through, so `params={'tradeQuoteCcy': 'EURC'}` should work. **Not tested live [UNVERIFIED].**

## 4. Regulatory and compliance record

- **US DOJ guilty plea, 24 Feb 2025.**
  - Aux Cayes FinTech Co. Ltd, the Seychelles operator of OKX, pleaded guilty in the Southern District of New York to one count of operating an unlicensed money-transmitting business.
  - Penalties total more than **$504M**: an $84.4M fine plus $420.3M forfeiture.
  - It admitted more than $1T of US-based transactions from 2018 to early 2024. There was no money-laundering charge.
  - Sources: [DOJ release](https://www.justice.gov/usao-sdny/pr/okx-pleads-guilty-violating-us-anti-money-laundering-laws-and-agrees-pay-penalties) (the page blocked my automated fetch, so the breakdown comes from its search listing); [Claims Journal/Bloomberg, 25 Feb 2025](https://www.claimsjournal.com/news/national/2025/02/25/329137.htm).
- **Malta, both before MiCA:**
  - MFSA €304,000 settlement with Okcoin Europe Ltd over Article 41 of the Virtual Financial Assets Act ([Finance Magnates, 27 Mar 2024](https://www.financemagnates.com/cryptocurrency/crypto-exchange-okx-pays-304000-fine-in-malta-for-compliance-failures/)).
  - FIAU €1.1M anti-money-laundering fine, announced 3 Apr 2025, for "serious and systematic" failures found in a 2023 examination ([Cointelegraph, 4 Apr 2025](https://cointelegraph.com/news/malta-fines-okx-crypto-exchange-1-2-million-aml-breaches)).
  - **I found no MFSA or FIAU action since the MiCA authorisation.**
- **ESMA peer review of the MFSA, 10 Jul 2025.**
  - On the authorisation of one CASP, "some material issues where not fully resolved" when the licence was granted, and some risk areas were not adequately assessed [REG] ([ESMA](https://www.esma.europa.eu/press-news/esma-news/esma-identifies-opportunities-strengthen-mica-authorisations)).
  - ESMA does not name the CASP. Press attributes it to OKX ([Cointelegraph](https://cointelegraph.com/news/mica-regulator-alarm-malta-crypto-licensing-process)).
- **Netherlands:** DNB fined Aux Cayes €2.25M on 27 May 2025 for serving Dutch clients without registration from Jul 2023 to Aug 2024 [REG] ([DNB](https://www.dnb.nl/en/general-news/enforcement-measures-2025/fine-for-aux-cayes-fintech-co-ltd-for-offering-crypto-services-in-the-netherlands-without-the-legally-required-registration-from-july-2023-to-august-2024/)).
- **AMF:** no warning against OKX itself. Its blacklist covers impersonators only: [okx-exchange.fr](https://www.amf-france.org/en/warnings/blacklists/usurpation/okx-exchangefr) (26 May 2025) and [@okxtrade.net](https://www.amf-france.org/fr/espace-epargnants/proteger-son-epargne/listes-noires-et-mises-en-garde/usurpation/prenomnomokxtradenet) (28 Sep 2026) [REG].
- **DEX aggregator, linked to the Bybit hack.**
  - Bybit's CEO said about $100M of the roughly $1.5B February 2025 Bybit hack moved through OKX's Web3 DEX aggregator, and Bloomberg reported EU regulator scrutiny on 11 Mar 2025.
  - OKX suspended the aggregator on 17 Mar 2025, citing a "coordinated effort by Lazarus group" ([The Block, 17 Mar 2025](https://www.theblock.co/post/346538/okx-suspends-dex-aggregator-following-lazarus-misuse-and-heightened-eu-scrutiny)).
  - It relaunched on 5 May 2025 with abuse detection ([Cointelegraph](https://cointelegraph.com/news/okx-restart-dex-with-anti-abuse-upgrades-after-misuse-by-lazarus)).
  - The centralised exchange was not affected.
- **Outages, 2025–2026:** I found no major OKX outage or EU-specific incident. OKX's latest published failure reports date from 2023. The search was not exhaustive [UNVERIFIED].

## 5. Custody, investor protection, and French specifics

- **Custody** [OFFICIAL] ([Custody Policy – EEA](https://www.okx.com/en-eu/help/custody-policy-eea), OKX Europe Ltd C88193, updated 21 Mar 2025):
  - Client crypto is held separately on-ledger from OKX's own, possibly in omnibus pools in which each client has an undivided share.
  - It is "legally segregated from the estate of the Company".
  - Storage is split across hot, warm and cold wallets. There are no sub-custodians.
  - Client fiat sits in designated client-money accounts (bank not named) and is reconciled monthly.
  - MiCA provides no investor-compensation or deposit-guarantee scheme for crypto.
- **Product carve-outs:** OKX says some EEA products, such as Margin Reward, fall outside MiCA and its safeguarding rules ([agreement](https://www.okx.com/help/eea-margin-reward-user-agreement)). Keep the bot account to plain spot.
- **Proof of reserves** [OFFICIAL] ([PoR page](https://okx.com/proof-of-reserves), 49th report, Nov 2026):
  - $33.87B across 21 assets; BTC 108%, USDC 100%. EURC is not covered.
  - Self-published using zk-STARK and a Merkle tree, with no third-party auditor.
  - Group-wide figures with no EEA breakdown.
- **France: form 3916-bis.**
  - This is a Maltese account, so declare it on form 3916-bis every year.
  - The fine is €750 per undeclared account. Some sources say it rises to €1,500 above €50k; check the current CGI art. 1736 X ([impots.gouv](https://www.impots.gouv.fr/actualite/modalites-de-declaration-des-comptes-dactifs-numeriques-detenus-letranger)).
  - On the form, declare the current entity name (OKX Europe Limited). The AMF still shows the old name.
- **Tax-record risk [UNVERIFIED].**
  - A BTC→EURC trade appears as instrument "BTC-EUR" with `tradeQuoteCcy=EURC`.
  - Before going live, run a small round trip and check `GET /api/v5/account/bills`: only BTC and EURC legs should appear. A EUR leg could look like a taxable sale for euros.
  - Keep the fills, which carry `tradeQuoteCcy`, as tax evidence.

---

## Verdict vs Kraken (0.40% / 0.80% entry tier)

- **Cost and BTC/EURC: OKX is clearly better.**
  - Fees are 0.10% / 0.20%, against Kraken's 0.40% / 0.80% (about 0.5%/yr against 2%/yr maker-only at a turnover of 5), and SEPA is free.
  - EURC settles on the deep unified BTC-EUR book (about 130 BTC/day, about 2 bps), whereas Kraken's real XBT/EURC pair trades about 0.3 BTC/day at about 10 bps.
  - This holds only if a test trade books only BTC and EURC legs.
- **API safety: about equal.** Both offer read+trade keys with no withdrawal and IP binding, and both work with ccxt (`myokx` for OKX). OKX additionally needs `tradeQuoteCcy` on every order and deletes unbound keys after 14 days of inactivity.
- **Trust: Kraken is ahead.** OKX has a 2025 US criminal plea ($504M), Maltese AML penalties (2024–25), a Dutch fine (2025), ESMA criticism of how its Malta licence was granted, and the 2025 DEX laundering episode. On the positive side, it holds a MiCA passport, segregates client assets and publishes monthly proof of reserves.

**Open points:**
1. The BTC-EUR fee group (groupId 18).
2. That an EEA account sees BTC-EUR with EURC settlement.
3. That bills show no EUR leg.
4. A live ccxt `tradeQuoteCcy` test.
5. No search for 2025–26 outages was exhaustive.

All of these need an opened account and a small test trade.
