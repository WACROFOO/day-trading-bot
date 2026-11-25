# Crypto track: finance and development plan

**Status:** plan, written 25 Nov 2026. Nothing tested yet.
**Verification status:** ❌ Not validated. Every rule below is a hypothesis
with a test attached.

You chose crypto as the development focus. The plan keeps your standing rules:

- **no leverage:** spot only, no derivatives, no borrowing;
- **the evidence funnel:** pre-registered variants, a trial budget, a locked
  hold-out (STRATEGY.md §7);
- **no real money before the gates pass.**

The PEA plan (stage 1) keeps running automatically through the broker's free
monthly plan and needs no development time. Until the crypto strategy passes
its gates, contributions keep going there. How money is split between the two
is decided at go-live (§11).

---

## 1. Three angles to attack crypto

A professional crypto strategy answers three separate questions. Most retail
attempts fail on the third (costs, tax, custody) even when the first two are
right.

| Angle | Question | Recommendation |
|---|---|---|
| **What to trade** | Bitcoin and Ether, or the wider coin universe? | **BTC and ETH only.** They are the most liquid, have the longest histories and the least survivorship bias. Thousands of smaller coins have died, which makes altcoin backtests flattering by construction. |
| **Which edge** | Trend, carry, arbitrage, on-chain signals, prediction? | **Trend-following with volatility targeting.** It has the best evidence in crypto, it can be done long-or-flat with no leverage, and it trades rarely (§2). |
| **How to hold** | Exchange-traded products in your IBKR account, or a regulated crypto exchange? | **A MiCA-licensed exchange with an API**, with EURC (a regulated euro stablecoin) as the risk-off asset. This depends on one tax point being confirmed (§5). |

---

## 2. Edge map: every family, and what we do with it

| Family | What it is | Evidence | Verdict |
|---|---|---|---|
| **Time-series trend / momentum on BTC and ETH** | Hold while the trend is up, go to cash (EURC) when it turns down | Strongest in crypto: time-series momentum and investor attention predict crypto returns (Liu & Tsyvinski, RFS 2021); moving-average rules predict bitcoin returns (Detzel et al., Financial Management 2021). The weak point is history: only 3–4 full cycles | **Build first** (C1–C3) |
| **Volatility targeting** | Size the position so the book's volatility stays near a target | Not an edge but sizing. In assets whose volatility swings 2–3×, it controls drawdowns. It failed as a return booster in equities (Cederburg et al. 2020), so we use it for risk only | **Build first**, as the sizing layer |
| **Cross-sectional momentum (top-10 rotation)** | Each week, hold the coins with the strongest recent returns | A momentum factor exists in the cross-section of coins (Liu, Tsyvinski & Wu, JF 2022), but results vary by period, and a fair test needs a point-in-time universe including dead coins | **Later** (C4), only if survivorship-free data can be found |
| **Rebalancing premium** | Keep fixed weights between crypto and other assets and rebalance; volatile, weakly correlated assets leave a rebalancing bonus | Sound mechanics, modest size; crypto's correlation with stocks has risen since 2020 | **Later**, as the bridge with the PEA portfolio |
| **On-chain and sentiment overlays** | Exchange flows, MVRV, funding rates, search trends as risk-off signals | Mixed, often vendor-sourced; good data is paid (Glassnode); very high overfitting risk | **Research only**, no money |
| **Staking yield** | Earn ~3%/yr staking ETH | A yield, not an edge; lock-ups, slashing and tax complexity | **Later**, once a position exists |
| **Funding / basis carry** | Long spot, short perpetual futures, collecting funding | Historically 5–20%/yr in bull markets, compressed since US spot ETFs (2024). Needs derivatives and margin at an exchange, the counterparty risk that sank FTX clients | **Excluded:** breaks the no-derivatives rule |
| **Arbitrage and market making** | Price gaps across exchanges | Taken by professional firms with sub-millisecond systems | **Excluded:** not winnable at retail |
| **Intraday and short-term trading** | Minutes to days | Same cost trap as the Ross attempt (LESSONS A1), at higher fees | **Excluded** |
| **Halving cycles, ML price prediction, DeFi yield** | — | 4 halvings is not a sample; ML has no verified edge (research report); DeFi adds smart-contract risk | **Excluded** |

---

## 3. The strategy to test: long-or-flat trend with volatility targeting

**Universe:** BTC and ETH against EUR. Risk-off asset: EURC.
**Decision:** once a day at 00:05 UTC, on the daily close.

### Pre-registered candidates

| ID | Signal | Sizing | Why it is on the list |
|---|---|---|---|
| **C1** | BTC above its **200-day** moving average → long; below → EURC | 100% when long | The classic published rule; the simplest benchmark for everything else |
| **C2** | BTC time-series momentum as an **ensemble**: the average of the signs of the 1-, 3-, 6- and 12-month returns, giving exposure in steps of 0, 25, 50, 75 or 100% | Ensemble weight | Averaging lookbacks instead of picking one is a standard defence against overfitting: one trial, not four |
| **C3** | C2's signal applied to BTC and ETH separately, equal **risk** weights | Volatility target: **25%** a year on the crypto book (60-day realised volatility), capped at 100% invested | The full design: diversified across two coins, drawdowns controlled by sizing |
| **C4** | *Later:* weekly cross-sectional momentum among the top 10 coins, held only when C2 is risk-on | Volatility target | Only with a survivorship-free universe |

**Pre-registered variants (and nothing else):** C1 with a 100-day average; C3
with a 20% or 30% volatility target; C3 rebalanced weekly instead of daily.
That is about **8 trials**, inside the family budget.

**Trading discipline built into the rules:**
- Position changes smaller than 10 points of exposure are skipped (a band),
  so volatility targeting doesn't trade daily for nothing.
- Orders are limit (maker) orders by default.
- Costs decide the design. At ~0.4% per trade plus spread, ten round trips a
  year cost about 8–10% a year. Turnover is reported for every candidate, and
  every candidate runs at 2× costs.

---

## 4. Risk framework

| Risk | Control |
|---|---|
| Market drawdown | Trend exits plus volatility targeting. **Crypto pain limit** (you decide, §11): breaching it stops the bot for review |
| Leverage | Spot only; never more than 100% invested; no margin, no derivatives |
| Exchange failure | MiCA-licensed exchange only; only the crypto book's capital on it; **API keys can trade but never withdraw**, restricted to the bot's IP address |
| Stablecoin failure | EURC only (MiCA-compliant e-money token). A **depeg check** stops buying if it trades more than 1% from €1; USDC fell to $0.87 in March 2023 |
| Bot errors | The kill switch from STRATEGY.md §5 (stale data, reconciliation, explained P&L, rejections), adapted for 24/7 markets |
| Key leakage | Keys only in `.env` (gitignored), never in the repo; 2FA on the exchange account; a separate sub-account for the bot |
| Behaviour | No manual trades on the bot's sub-account; every override is logged and reviewed |

---

## 5. Venue and tax: the decision that matters most after the strategy

| | Route A: crypto ETPs in your IBKR account | Route B: MiCA-licensed exchange with an API (e.g. Kraken, Coinbase, Bitstamp, Bitpanda) |
|---|---|---|
| What you hold | Physically backed BTC/ETH notes listed in Europe (CoinShares, 21Shares, WisdomTree, iShares) | BTC, ETH and EURC directly, in your exchange account |
| Hours | Exchange hours, weekdays only: weekend crashes can't be acted on | 24/7 |
| Costs | Fund fee 0.15–1.5%/yr plus commissions | Trading fees ~0.1–0.4% per trade plus spread; no annual fee |
| **Tax when the trend turns off** | Selling an ETP is a **taxable sale** at the flat tax, every time | Swapping BTC for EURC is **expected to be tax-neutral**: France taxes crypto only when converted to euros or goods (CGI art. 150 VH bis). **To verify for EURC specifically** (§10, Phase 1) |
| Counterparty risk | Regulated issuer, held at IBKR | Exchange custody (mitigated, §4) |
| Paperwork | Gains on form 2074 (as for any security) | Form 2086 for crypto gains; **form 3916-bis for each exchange account every year** |
| Automation | IBKR API (weekly 2FA login) | Exchange API through `ccxt`, the standard Python library |
| Availability | ETNs may be restricted for retail clients: **to verify** | Exchanges serving France must hold MiCA authorisation (French transition period ended 1 July 2026) |

**Recommendation: Route B,** if Phase 1 confirms that BTC→EURC swaps are
tax-neutral. A trend strategy exits several times a year. On Route A each exit
is taxed at 31.4%, while on Route B tax is due only when you withdraw euros to
your bank. Route A stays the fallback if that tax point fails, or if you prefer
regulated custody over 24/7 trading.

**Tax points to confirm with an accountant:**
- the flat tax rate on crypto gains in 2026 (31.4% if the 2026 social-levy
  increase applies, as for securities);
- the €305 annual exemption on disposals;
- whether a daily bot could be treated as **habitual trading** (taxed as
  professional income, BNC) rather than occasional gains.

---

## 6. Data plan

| Need | Candidate sources (to confirm in Phase 2) | Check |
|---|---|---|
| BTC daily, long history (2010+) | Coin Metrics community API (free reference rates) | Reconcile against a second source within 1% |
| BTC and ETH daily OHLCV with volume (2015+) | Exchange public APIs (Kraken, Coinbase, Bitstamp) through `ccxt`; CoinGecko | Two sources agree; no missing days (crypto trades every day) |
| EUR conversion | ECB EUR/USD (daily), or EUR pairs directly | Same conversion checks as DATA.md |
| EURC price, for the depeg check | Exchange order books | Live only |
| Top-10 universe by date, including dead coins (C4) | Hard: CoinGecko historical market caps, CoinMarketCap archives | If no survivorship-free source exists, **C4 is dropped** |

Everything is cached in the gitignored `systematic/data/`, like the stock data.

---

## 7. Engine: one engine, two tracks

The engine in ENGINE.md was planned for monthly bars. It becomes
**bar-agnostic**, so one engine serves both tracks:

| ENGINE.md piece | Crypto change |
|---|---|
| `MarketView` truncated at the decision time | Daily bars on a 24/7 calendar; decisions at the UTC daily close |
| `rules` | Long-or-flat signals, an ensemble, and volatility-target sizing with a band |
| `accounts` | An exchange account holding BTC, ETH and EURC |
| `costs` | Maker/taker fee tiers, spread, slippage |
| `tax` | The French crypto regime: the whole-portfolio gain formula, tax only on euro withdrawals, the €305 exemption, and Route A's securities regime |
| `metrics` | Same, plus results per crypto cycle and exposure statistics |
| Experiment log and hold-out lock | Same. **Hold-out: the last 24 months** (Dec 2024 → Nov 2026), opened once |

The first build milestone (rules, signals, `MarketView`) is shared, so no work
is lost whichever track goes first.

---

## 8. Validation gates

**Gate CG1, the backtest.** It runs on history before the hold-out, net of
costs and modelled tax, in EUR. It checks the following:
1. **Beats BTC buy-and-hold on risk:** higher Sharpe *and* a max drawdown
   under half of buy-and-hold's.
2. **Works across assets with the same parameters:** positive on BTC *and*
   ETH. A rule that only works on one coin is fitted to it.
3. **Works across cycles:** positive in at least 3 of the 4 cycles
   (2013–15, 2017–18, 2021–22, 2023–24), and never worse than buy-and-hold in
   a bear phase.
4. **2× costs:** still beats buy-and-hold on Sharpe.
5. **Statistics:** deflated Sharpe ≥ 0.95 given the real trial count.
6. **Inside your crypto pain limit.**

**Gate CG2, the hold-out.** Run once: there is no collapse relative to the
backtest. A Sharpe ratio more than 0.5 below it means stop and diagnose.

**Gate CG3, paper trading.** At least 8 weeks of the bot paper trading against
live prices. Its signals must match a backtest re-run 100%, slippage must stay
at or below 1.5× the model, and there must be no unhandled errors for 4 weeks.

**Gate CG4, live.** Small real capital first (a few hundred euros), ramping
up only if live results track paper trading.

---

## 9. Bot architecture (crypto)

| Module | Job |
|---|---|
| `broker.ccxt_adapter` | Exchange connection via `ccxt`: balances, orders, fills; paper mode simulated on live prices |
| `runner.crypto` | 00:05 UTC daily job: fetch → check → signal → size → reconcile → orders → journal → alert |
| `risk` | Kill switch, pain limit, EURC depeg check, max exposure, stale-data check |
| `alerts` | Telegram: a daily summary, plus an immediate alert on any trip |

**Modes:**
- `advisor`: it messages you the target, for example "BTC 40%, ETH 20%, EURC
  40%", and you trade by hand;
- `paper`;
- `live`.

**Where it runs:** at this account size a paid server (~€5/month) would cost
about 2% a year. Start on your own computer in advisor mode, or on a
free-tier cloud machine, and move to a paid server only once the book is
large enough (recurring costs ≤ 0.5%/yr, the STRATEGY.md §2.1 rule).

---

## 10. Phases and timeline

| Phase | What | Who | When |
|---|---|---|---|
| 0 | Decisions (§11) | You | by 30 Nov 2026 |
| 1 | Focused research: crypto trend evidence after publication, the post-2024 market regime (ETFs), French crypto tax 2026 (**EURC neutrality**, habitual-trading risk), MiCA exchanges available to you, fees | Me (research) | 1 → 7 Dec |
| 2 | Crypto data layer and checks (§6) | Me | 1 → 10 Dec |
| 3 | Engine, bar-agnostic, with crypto costs and tax (§7) | Me | 8 → 23 Dec |
| 4 | Tests C1–C3, then Gate CG1; hold-out opened once (CG2) | Both | 4 → 22 Jan 2027 |
| 5 | Bot: `ccxt` adapter, runner, risk, alerts; fault-injection tests | Me | 18 Jan → 12 Feb |
| 6 | Paper trading (CG3), ≥ 8 weeks | Bot + you | 15 Feb → mid-Apr |
| 7 | Live, small, then ramp (CG4) | Bot + you | from mid-Apr 2027 |

If CG1 or CG2 fails, the crypto track stops there. No money will have been
risked, and the PEA plan will have kept running the whole time.

---

## 11. Decisions needed from you

| # | Decision | Default |
|---|---|---|
| 1 | Venue | Route B (MiCA exchange + EURC), subject to the tax check; Route A as fallback |
| 2 | Universe | BTC + ETH |
| 3 | **Crypto pain limit:** the largest drop of the crypto book you'd live through without abandoning it | −30%. Your −20% portfolio limit would force very low exposure, and BTC buy-and-hold has fallen 75–85% |
| 4 | Split of money between PEA and crypto, from go-live | Decided at Phase 7, once you have seen the backtest |

## 12. Expectations

The aim is **not** to beat bitcoin in bull markets. Trend rules enter late and
exit late, so they give up part of every rally. The aim is to capture a
meaningful share of crypto's upside while avoiding most of its −75% to −85%
crashes, so the book survives long enough to compound.

Whether a trend rule still does that after 2024 is an open question. Spot
bitcoin ETFs brought institutional money, lower volatility and higher
correlation with stocks, and an edge can shrink in such a regime. The
hold-out (Dec 2024 → Nov 2026) is exactly that period, which is why it stays
locked until the end.
