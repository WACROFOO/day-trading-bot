# Crypto track: finance and development plan (v0.2)

**Status (25 Nov 2026):** the primary rule is **frozen**
([frozen_rules.json](frozen_rules.json)); its forward record starts on
**26 Nov 2026**.
**Verification status:** ❌ Not validated. The rule rests on published
evidence and a reconciled research backtest, not on a passed gate.

v0.2 rebuilds the plan from the community scan:
[research/reports/Crypto strategy community scan.md](../research/reports/Crypto%20strategy%20community%20scan.md).
That report draws on forums, bot communities, platforms, yield/DeFi and
academic research. v0.1 is in git history; §13 lists what changed.

Standing rules: **spot only, no leverage, no derivatives**; the evidence
funnel (STRATEGY.md §7); no real money before the gates. The PEA plan keeps
running on its own.

---

## 1. What the scan found, in one paragraph

Of 16 strategy families, only one has credible evidence of adding value
after costs while fitting spot-only, daily-or-slower decisions: a
**long-or-flat bitcoin trend rule sized by volatility**.

Its value is **drawdown control, not extra return**. Before the hold-out
(2021–23), the rule had a Sharpe ratio of 0.79 and a worst drop of −21.5%,
against 0.52 and −76.7% for buy-and-hold.

Most of what communities sell as profitable fails out of sample, after
costs, or for the followers:
- grid and martingale bots;
- copy trading: 97% of leaders are profitable on their own books, but only
  43.6% make money for their followers;
- signal groups and pump-and-dumps, which are negative-sum for members;
- mean reversion, on-chain top indicators, altcoin rotation, and ML or LLM
  bots.

Yield products have shrunk to about 2–6% gross, roughly money-market level,
and most need derivatives or custody outside MiCA.

## 2. Ranking (condensed from the report)

| Tier | Families | Role here |
|---|---|---|
| **Use** | Trend ensemble × volatility target (BTC); plain DCA as the contribution habit | The design (§3) |
| Benchmark | 200-day average (C1); BTC buy-and-hold; plain monthly DCA | Run alongside, never traded |
| Variant only | BTC+ETH at equal risk (ETH's correlation with BTC is 0.78–0.90, so it cuts volatility only 3–6%); weekly rebalancing | Two pre-registered variants |
| Outside the bot | Tokenised euro money-market funds (~2.4% net) for idle savings | Not in the bot |
| Dropped | Staking (taxed as BNC; unstaking queues up to 46 days); cross-sectional rotation (audit cut its Sharpe from 2.08 to 0.01); Fear & Greed and on-chain tilts | — |
| Excluded | Grid/martingale bots, copy trading, signal groups, memecoins, airdrops; carry, Ethena, covered calls, DeFi lending, liquidity provision; short-horizon rules; ML/LLM and hyperopt bots | — |

---

## 3. The design: a trend-gated bitcoin accumulator

Four pieces, each covering a weakness in another:

| Piece | Rule | Why |
|---|---|---|
| **Signal** | Average of the signs of bitcoin's 30-, 91-, 182- and 365-day returns, giving 0/25/50/75/100% (long or flat) | Ensembles beat any single lookback; single rules whipsaw (the 200-day rule switched 19 times in 2021) |
| **Sizing** | × min(1, 25% ÷ 60-day realised volatility); never above 100%; skip changes under 10 points, except a full exit when the target is 0 | Keeps drawdowns near −20% to −30%; cuts turnover from 12 to ~5 a year, which matters at 0.40% fees and for the habitual-trading test |
| **Contributions** | Each monthly deposit joins the next rebalance and buys BTC only up to the current target weight; the rest waits in EUR/EURC | DCA is the community's one robust habit; gating it with the trend avoids buying all the way through a 2022-style bear market |
| **Risk-off leg** | Exits swap BTC **directly into EURC**, never through EUR | Tax-deferred under current French law (§5) |

**Execution:** post-only limit orders, with a timed fallback to a market
order. **Decision time:** 00:05 UTC on the completed daily close.
**Data:** Bitstamp BTC/EUR daily closes.

**Frozen:** every parameter above is in [frozen_rules.json](frozen_rules.json)
and implemented in `src/portfolio_bot/crypto/rules.py`. A test enforces that
the code equals the file. Changing anything restarts the forward record and
adds a trial.

**Implementation check:** our code reproduces the research replication on
BTC/USD for 2015–2026 at 0.25% per trade: CAGR 26.6% vs 26.5%, Sharpe 1.25
vs 1.25, max drawdown −30.7% vs −30.7%, turnover 5.0 vs 5.0 a year. That
configuration was already logged, so this is not a new trial.

**State on 24 Nov 2026:** all four trend votes are down, so the rule holds
**0% BTC and 100% EURC**. A bot started now would sit in EURC until the next
uptrend. Its first real test is a re-entry.

---

## 4. Risk framework

| Risk | Control |
|---|---|
| Market drawdown | Trend exits plus volatility sizing. **Crypto pain limit** (you decide; default −30%): breaching it stops the bot for review |
| Leverage | Spot only, never more than 100% invested |
| Exchange failure | MiCA-licensed exchange only; only the crypto book on it; a dedicated sub-account |
| Key abuse | Trade-only API keys (no withdrawals), locked to the bot's IP address, held in `.env` only. **The bot halts on any order or trading pair it did not send itself**: a trade-only key can still be abused, as the 3Commas leak showed |
| Stablecoin | EURC only; stop buying if it drifts more than 1% from €1 (USDC traded at $0.88 in March 2023) |
| Bot errors | The STRATEGY.md §5 kill switch, adapted for 24/7 markets: stale data (already enforced in `crypto_signal.py`), reconciliation, explained P&L, rejections |
| Behaviour | No manual trades in the bot's sub-account; every override is logged |

---

## 5. Venue and tax

**Fees went up in 2026:**

| Exchange | Fees at entry level (maker / taker) | Status |
|---|---|---|
| Kraken Pro | 0.40% / 0.80% (since 9 July 2026) | Official |
| Coinbase Advanced | 0.25% / 0.50% (EU, reported since September 2026) | Press only |
| Bitstamp | ~0.30% / 0.40% | Unconfirmed |

All four (Kraken, Coinbase, Bitstamp, Bitpanda) are MiCA-licensed for
France; Binance is not. The cost model is therefore 0.40% maker, a 0.80%
taker fallback and 0.02% spread, with a stress test at 2× and a turnover
budget of about 5 a year.

**Choosing the exchange.** The exchange is chosen on four things:
1. A **direct BTC/EURC pair** with real depth. Selling BTC for EUR and then
   buying EURC would be a taxable sale.
2. The fee actually charged at your size, as shown in the order preview.
3. Trade-only, IP-locked keys (verified for Kraken and Coinbase).
4. How stablecoin pairs are billed (Kraken uses a separate 0.20% schedule).

**French tax (2026):**
- **Rate:** flat tax of **31.4%** on crypto gains, paid when you convert to
  euros. Gains are computed on the whole portfolio; the €305 exemption
  applies to total sale proceeds, not gains.
- **No loss carry-forward** for crypto.
- **Paperwork:** form 3916-bis every year for each exchange account (€750
  fine per undeclared account), and form 2086 for gains.
- **BTC→EURC swaps are tax-neutral today.** The 2027 budget nearly ended that
  (adopted 38–37, then lapsed, then rejected by the Senate on 24 Nov). The
  budget is finalised around **17 December 2026: re-check then.**
- **Habitual-trading risk (BNC):** frequent automated trading can be
  reclassified as professional income, with no numeric threshold. Low
  turnover is the protection.

**Route A (crypto ETPs in your IBKR account)** stays a computed alternative:
fund fees of 0.10–0.15% a year, every exit taxable, but losses carry
forward. If BTC→EURC swaps become taxable, Route A probably wins. The engine
computes both routes, so the choice rests on numbers.

---

## 6. Data (built)

| Series | Source | Coverage | Status |
|---|---|---|---|
| BTC/EUR daily | Bitstamp | Apr 2016 → yesterday | Built, freshness-checked |
| BTC/USD daily | Bitstamp | Aug 2011 → yesterday | Built; used for the longer history (pre-2016 EUR via ECB rates) and the reconciliation |
| ETH/EUR daily | Bitstamp | 2017 → | Variant V1 |

No USDT pairs are used anywhere. Downloads are cached in the gitignored
`systematic/data/`.

## 7. Engine additions for crypto

These go on top of ENGINE.md (bar-agnostic):
- **Contributions:** the gated-DCA rule, plus a plain-DCA benchmark fed the
  same money.
- **Execution model:** maker first, unfilled orders, a taker fallback, and
  slippage measured against the model.
- **Tax:** portfolio value logged at every euro withdrawal; no loss
  carry-forward; Route A vs Route B; a scenario where EURC swaps are taxed.
- **Reporting:** results by window (2015–2020, 2021–2023), because
  whole-sample statistics are dominated by 2016–17 and 2020.

---

## 8. Validation, after the hold-out was spent

**What happened.** To answer "does it still work after 2024?", the research
ran its own backtest over Jan 2024 – Nov 2026. That covered almost all of the
Dec 2024 – Nov 2026 hold-out this plan had reserved. **The hold-out is spent.
The only unseen data left is the future.**

1. **Contamination recorded.** The research's 8 bitcoin rule configurations
   are logged in [research/experiments.csv](../research/experiments.csv) as
   spent trials. The candidate list is **frozen**: primary, C1 benchmark, and
   two variants. The honest trial count is **10**, at the budget limit, so
   nothing else gets added.
2. **CG1, the backtest:** run on data up to November 2024, net of the
   §5 cost model, with results by window.
   - Primary test: **drawdown under half of buy-and-hold's** in each window.
     That is the large, consistent effect; the Sharpe gain (+0.16 to +0.19)
     is too small to prove on crypto's short history.
   - Also: the deflated Sharpe ratio at 10 trials, and the 2× cost test.
3. **CG2, a reconciliation check:** our engine must reproduce the research
   replication. It can fail a candidate but can no longer pass one.
   *Started:* `crypto_signal.py --reconcile` matches on CAGR, Sharpe, max
   drawdown and turnover.
4. **CG3, the forward test** (the true out-of-sample test):
   - **Engineering gate (8 weeks of paper trading):** signals match a
     backtest re-run 100%, slippage ≤ 1.5× the model, no unhandled errors.
   - **Forward record (≥ 12 months, from 26 Nov 2026):** judged against the
     bands frozen in `frozen_rules.json`:
     - the exposure path matches a re-run;
     - realised costs ≤ 1.5× the model;
     - in any bitcoin decline of 20% or more, the strategy's drawdown is
       under half of bitcoin's.
   - Any rule change restarts the clock and adds a trial.
5. **CG4, live:** small capital from the end of the engineering gate; the
   stake grows only after the forward record passes.

**What the forward test can't do:** prove an edge. After one year the
standard error of a Sharpe ratio is about 1.0. It *can* falsify the
mechanics: exposure, costs, and drawdown behaviour in a real decline. Going
live rests on the published mechanism, realistic costs and small initial
capital.

---

## 9. Bot architecture

| Module | Job |
|---|---|
| `crypto.rules` | **Built:** the frozen rule, C1, simulation |
| `scripts/crypto_signal.py` | **Built:** today's decision, the forward record, the reconciliation |
| `broker.ccxt_adapter` | Exchange connection via `ccxt`: balances, maker-first orders, fills; paper mode |
| `runner.crypto` | 00:05 UTC daily job: fetch → freshness check → signal → size → reconcile → orders → journal → alert |
| `risk` | Kill switch, pain limit, EURC depeg, unexpected-order halt |
| `alerts` | Telegram: daily summary, plus an immediate alert on any trip |

**Modes:**
- `advisor`: the target, for example "BTC 0%, EURC 100%", is sent to you;
- `paper`;
- `live`.

It starts on your computer or a free-tier machine, because recurring costs
must stay ≤ 0.5%/yr.

## 10. Timeline

| Phase | What | When |
|---|---|---|
| ✅ | Community scan, ranking, rule frozen, data built, reconciliation | 25 Nov 2026 |
| ▶ | **Forward record running** | from 26 Nov 2026 |
| 1 | Re-check the French budget (EURC swaps); choose the venue | after ~17 Dec 2026 |
| 2 | Engine additions (§7); CG1 on data to Nov 2024 | Dec 2026 – Jan 2027 |
| 3 | Bot: `ccxt` adapter, runner, risk, alerts; fault-injection tests | Jan – Feb 2027 |
| 4 | Engineering gate (8 weeks of paper trading) | Feb – Apr 2027 |
| 5 | Small live trading (CG4) | from ~Apr 2027 |
| 6 | Forward-record review (12 months) | late Nov 2027 |

## 11. Decisions still needed

| # | Decision | Default |
|---|---|---|
| 1 | Venue | Route B (MiCA exchange + EURC) if swaps stay tax-neutral after the budget; otherwise compare with Route A |
| 2 | Crypto pain limit | −30% |
| 3 | PEA / crypto split at go-live | The crypto book sits about half in EURC on average, so size it at **about twice** the bitcoin exposure you want |

## 12. Expectations

- **Post-ETF estimate** (partly informed by the spent hold-out): Sharpe about
  0.5–0.8, CAGR about 8–20%, max drawdowns about −18% to −35%, net of retail
  costs.
- **Long flat spells,** and large lags in bull years: Bitwise's trend ETF
  lagged bitcoin by about 97 points over three years to March 2026.
- **EURC earns nothing:** MiCA bans interest on e-money tokens.
- **The goal is to keep the book alive through −75% crashes,** not to
  out-earn bitcoin.

## 13. Changes from v0.1

| v0.1 | v0.2 | Basis |
|---|---|---|
| Candidates C1–C4, ~8 trials | Primary = BTC-only ensemble × 25% vol target (frozen); C1 benchmark; BTC+ETH and weekly variants; C4 dropped; 100-day and 20%/30% variants dropped | Pre-2024 evidence; trial budget |
| BTC+ETH by default | BTC only; ETH as a variant | Correlation 0.78–0.90 |
| Fees ~0.1–0.4% | 0.40% maker / 0.80% taker fallback, 2× stress, turnover budget ~5/yr | 2026 fee schedules |
| Staking "later" | Dropped | BNC tax, unstaking queues |
| Hold-out Dec 2024 – Nov 2026 | Spent; replaced by a frozen forward record of at least 12 months | Research contamination |
| No contribution rule | Gated DCA, plus a plain-DCA benchmark | Community evidence |
| — | Unexpected-order halt, portfolio-value logging, Route A computed alongside, venue criteria | Report §5–6 |
