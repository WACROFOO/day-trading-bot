# Roadmap — from zero to a live system, step by step

Each step lists **what we build** (mostly me, in code), **what you do**, and a
**gate**: the test that has to pass before the next step starts. If a gate
fails, the step says what happens next. Sometimes the answer is "this part of
the strategy is dropped". That counts as a success: it costs time, not money.

This is v0.2 of the roadmap, rebuilt around STRATEGY.md v0.2 (one portfolio,
seven sleeves, monthly rules) and the
[research report](research/reports/Retail%20systematic%20strategy%20candidates.md).

Dates assume we start the week of **16 November 2026** at a part-time pace
(3–5 hours a week from you).

## Overview

| Step | What | Who | Target | Gate |
|---|---|---|---|---|
| 0 | Decisions: PEA, broker, capital, pain limit | You | 15 Nov 2026 | Answers given (or defaults accepted) |
| 1 | Post-mortem of the Ross attempt | Both | 22 Nov | — (feeds the rules) |
| 2 | Data foundation: index, factor and trend histories in EUR | Me | 4 Dec | G2 · data checks pass |
| 3 | Backtest engine: monthly, split dates, EUR, French tax | Me | 18 Dec | G3 · known-answer tests pass |
| 4 | Tests 1 and 3: the portfolio and the managed-futures sleeve | Both | 15 Jan 2027 | G4 |
| 5 | Test 2: the momentum sleeve | Both | 29 Jan | G5 |
| ▶ | **Portfolio goes live in advisor mode**: the system says what to do, you place the orders | You | Feb → Apr 2027 | — |
| 6 | The bot: daily pipeline, IBKR, kill switch | Me | 5 Mar | G6 · fault-injection tests |
| 7 | Shadow run: the bot proposes alongside your live portfolio | Bot + you | Mar → May | G7 |
| 8 | Automation of the CTO sleeves, smallest first | Bot + you | Jun → Sep 2027 | G8 |
| 9 | Operate, review, research sleeve | Ongoing | — | G9 |

**Why the portfolio can go live before the bot exists.** v0.2 trades monthly,
in a handful of orders. Placing them yourself from the system's instructions
(advisor mode) is cheap and safe. The bot is then built and proven alongside
the live portfolio, and automation takes over the CTO sleeves only once it has
matched your manual orders for months. The PEA stays manual permanently,
because no PEA broker offers an API.

---

## Step 0 — Decisions (you, this week)

Answer these, or reply "defaults" to accept the right-hand column. Your actual
numbers stay in `systematic/private/`, never in git (the repo is public).

| # | Decision | Default |
|---|---|---|
| 1 | **PEA:** do you have one, since when, and how much room is left under the €150k ceiling? | Use one for the world-equity sleeve (S1). If you don't have one, **open it now, even with a small deposit**: the 5-year tax clock starts at the first deposit. |
| 2 | Broker for the CTO | Interactive Brokers (EU entity). **Open the account now**: verification takes days to weeks, and Step 2 needs it to check that the instruments are tradable for you. |
| 3 | Capital, and monthly contributions | Your emergency fund (3–6 months of expenses) stays outside, in full. Monthly contributions are useful: rule R6 uses them to rebalance without selling. |
| 4 | Pain limit: the largest portfolio drawdown you can live through without abandoning the plan | −20% from peak. This sets the gate in Step 4 and the stop-and-review rule live. |
| 5 | Managed futures: the S4 fund uses futures *inside* the fund. You can't lose more than you put in. Acceptable? | Yes |
| 6 | Where the bot runs; how alerts reach you | Small VPS (~€5/month) or an always-on PC; Telegram |
| 7 | Your time | Steps 1–6: 3–5 h/week. Live: 2 min/day, about 15 min per tranche date for PEA orders, 30–60 min/month review. |

**Admin with a foreign broker (France):**
- Declare the IBKR account every year on form 3916 (€1,500 fine per
  undeclared account per year).
- Declare gains yourself; the CTO flat tax (PFU) is **31.4%** since the 2026
  social-security law.
- Distributions need the monthly 12.8% prepayment form (2778-DIV-SD). Prefer
  **accumulating** share classes, which avoid it and defer tax.
- Sign the W-8BEN form for US dividends.

This is not tax advice: confirm with an accountant.

---

## Step 1 — Post-mortem of the Ross attempt (week of 16 Nov)

**Why:** to find out where the money actually went. It also produces the
lessons that become kill-switch triggers.

**You give me** whatever trade history exists: `data/paper_trading.db` and/or
broker statements (CSV). Attach them in chat, or put them in
`systematic/private/` in your local clone. They never get committed.

**I build:** `systematic/research/postmortem.py`. It reports:
- gross vs. net P&L, and cost per trade in R
- win rate and expectancy
- P&L by time of day and by price bucket
- how often the risk rules tripped
- what share of losses came from the worst 10% of trades

**Output:** a report kept in `private/`. Findings go into LESSONS.md §E.
**Gate:** none.

---

## Step 2 — Data foundation (23 Nov → 4 Dec)

The Ross data cannot be used here (research report): it has the wrong horizon,
the wrong universe, and no stored prices. v0.2 needs **long monthly histories**,
because the trial budget requires roughly 18+ years of data.

**I build:**

| Data | Source (cost) | Used for |
|---|---|---|
| MSCI World, World Momentum, World Quality, Europe Momentum (end-of-month, net) | MSCI index downloads (free); factor indexes are back-tested before launch | S1–S3, Test 2 |
| Momentum, value and quality factors, US and international | Ken French library, AQR datasets (free) | Long-history cross-checks, hold-out region |
| Trend: AQR Time-Series Momentum (from 1985), SG Trend Index (from 2000), DBMF (from 2019) | AQR, SG/BarclayHedge, fund data | S4, Test 3 |
| 7–10y Treasury total return; EUR/USD; EUR and USD short rates (for hedging cost) | Index/fund data, ECB Data Portal, FRED (free) | S5, EUR conversion |
| Gold in EUR | Free price series | S6 |
| EUR short rate | ECB Data Portal (free) | S7, cash yield |
| Daily UCITS ETF prices for the live period | EODHD (~USD 20/month); yfinance only as a fallback (rate limits); Stooq is out (CAPTCHA since Mar 2026) | Tracking checks, the bot |
| Exchange calendars | Library | Tranche dates, data freshness |

Also the **instrument map**: each sleeve → UCITS ETF (ISIN, exchange, currency,
accumulating, hedged, PEA-eligible yes/no, TER).

**You do:** confirm in IBKR (and your PEA broker) that each instrument is
tradable for you.

**Gate G2:**
- MSCI World EUR annual returns match the published factsheets within 0.5
  points.
- Each UCITS ETF's tracking difference against its index is ≤ ~0.5% a year
  over the overlap.
- No unexplained gaps or jumps.

---

## Step 3 — Backtest engine (7 Dec → 18 Dec)

**Why our own engine:** the rules live in one module that outputs target
weights, and the **same code** runs the backtest, the advisor, the shadow run
and the automation. What is tested is exactly what is traded. `bt` (maintained,
weight-based) serves as an independent cross-check for the known-answer tests.

**I build:**
- Monthly decisions on 4 split dates (R1), all accounting in EUR, hedging
  cost for EUR-hedged sleeves, and cash earning the EUR short rate.
- Costs: IBKR commissions with minimums, spreads, FX conversion. Every run is
  repeated at 2× costs.
- **Tax layer:** the 31.4% PFU on gains realised in the CTO each year, with a
  10-year loss carry-forward; PEA levies (18.6%) at the end. Results are
  reported **after tax**, against an MSCI World tracker held in a PEA.
- Metrics: CAGR, volatility, Sharpe, max drawdown, worst year, time under
  water, turnover, cost and tax drag, **deflated Sharpe ratio**, and
  **probability of backtest overfitting**.
- The experiment log, `research/experiments.csv`, records every run.

**Gate G3:**
- Buy-and-hold matches the index.
- A monthly 60/40 matches `bt` and a hand calculation.
- A lookahead test passes.
- All tests run offline on fixtures.

---

## Step 4 — Tests 1 and 3: the portfolio and managed futures (4 Jan → 15 Jan 2027)

**Test 1** runs the v0.2 portfolio (STRATEGY.md §2–3) and its pre-registered
variants (§8: filter type, filter scope, bond rule, hedging, crash ladder).
**Test 3** runs the managed-futures weight at 0, 10, 15 and 20%.

- **Comparison:** the PEA world tracker after tax, a EUR 60/40, and STRATEGY v0.1.
- **Periods:** from the mid-1990s (the factor-index history) to 2021,
  covering 2000–02, 2008 and 2020. **2021–2026 is held out and run once**, and
  it includes 2022 and 2025.
- **Timing luck:** every variant also runs with a single rebalance date, to
  show how much luck that carries.

**Gate G4:**
1. After-tax Sharpe ≥ the PEA world tracker's over the main period, and no
   more than 0.2 below it in the hold-out.
2. Max drawdown ≤ 60% of world equity's in 2000–02, 2008 and 2022, and inside
   your pain limit.
3. After-tax return ≥ the EUR 60/40's over the full period.
4. **Managed futures stay** only if they raise the Sharpe ratio and reduce max
   drawdown versus 0%, at 2× costs as well.

*If it fails:* simplify to the robust fallback: the PEA world tracker plus a
cash/bond mix sized to your pain limit. That is a fine portfolio, and the bot
still enforces the rebalancing.

---

## Step 5 — Test 2: the momentum sleeve (18 Jan → 29 Jan)

**Arms**, under identical guardrails:
1. MSCI World Momentum ETF buy-and-hold (the default S2)
2. Sector-ETF rotation
3. GEM-style regional momentum
4. Quality weight 10% vs. 0%

**Hold-out:** Europe (MSCI Europe Momentum, AQR European factors), looked at
once.

**Gate G5:**
- The momentum ETF arm has a **positive net excess return over MSCI World**
  in the full history *and* in the held-out region.
- Its worst relative drawdown is one you have seen in advance and accept.
- An alternative arm replaces it only if it beats it on the same rules.

*If it fails:* S2's weight moves to S1, and the portfolio gets simpler.

---

## ▶ Live in advisor mode (Feb → Apr 2027)

Once G4 and G5 pass, I add a `portfolio-advisor` command. It reads your
holdings from a file in `private/` and prints, for each tranche date, exactly
which orders to place in which account. You deploy the capital in **three
monthly instalments** (February, March, April), so the entry date doesn't
hinge on a single day.

---

## Step 6 — The bot (8 Feb → 5 Mar)

**I build**, in `systematic/src/`:

| Module | Job |
|---|---|
| `data` | Daily fetch, cache, data checks (STRATEGY §5) |
| `strategy` | The rules → target weights. The same module as the backtest. |
| `portfolio` | Targets vs. holdings → orders, per tranche and per account |
| `risk` | Pre-trade checks, kill switch, pain-limit monitor (LESSONS B2–B5) |
| `broker` | Local simulator and IBKR paper/live (via `ib_async`); the PEA is always advisor-only |
| `ledger` | SQLite: order lifecycle with client IDs, fills, positions, tax lots |
| `runner` | The daily 17:00 New York job; trades only on tranche dates |
| `alerts` / `report` | Daily summary, tranche-date instructions, monthly report |

**Modes:** `advisor` (instructions only), `paper`, `live` (explicit flag plus
a config confirmation).

**Operations:** IBC, the usual tool for running IB Gateway unattended, was
retired in September 2026. Plan on IB Gateway's auto-restart setting plus a
**weekly two-factor login on Monday** from your phone. A monthly strategy
tolerates a missed day; the daily job alerts if the gateway is down.

**Gate G6:** fault-injection tests pass for all of these:
- stale data
- broker unreachable
- partial fill
- rejected order
- the job run twice (it must not double-buy)
- a crash mid-run, then restart
- a reconciliation mismatch
- a DST-change date
- a tranche date that falls on a holiday

---

## Step 7 — Shadow run (Mar → May 2027)

For 3 months the bot runs daily against the IBKR **paper** account while you
run the real portfolio in advisor mode.

**Weekly (me, with you):**
- The bot's orders, the advisor's instructions and a backtest re-run over the
  same dates must agree **100%**. A mismatch is a bug, fixed before the clock
  continues.
- Paper fills are compared with the cost model.
- Once, trigger the kill switch on purpose to prove it works end to end.

**Gate G7:**
- 100% agreement.
- Zero unhandled errors in the last 4 weeks.
- Kill switch tested.

---

## Step 8 — Automation of the CTO sleeves (Jun → Sep 2027)

| Stage | Sleeves the bot trades | Duration | Move on only if |
|---|---|---|---|
| 1 | Gold and managed futures (the smallest) | 2 months | Automated orders = proposals 100%; costs ≤ 1.5× the model; no manual overrides |
| 2 | All CTO sleeves | — | Same |

The PEA sleeve stays in advisor mode for good. Any failure goes back a stage.

---

## Step 9 — Operate and review (ongoing)

| When | What |
|---|---|
| Daily | 2-minute summary; alerts only if something tripped |
| Tranche dates (4 a month) | The bot trades the CTO; you place any PEA orders it sends |
| Monthly | Performance vs. benchmarks, in EUR, after costs and tax |
| January | Full rebalance; tax pack (form 3916, gains, prepayments) |
| Yearly | Strategy review; candidates for the research sleeve go through the funnel (STRATEGY §7) |

**Review and stop rules (Gate G9):**
- **Pain limit hit** → everything stops for a review.
- **Live results outside the backtest's range** (for example, a 12-month
  return below the backtest's 5th percentile for that kind of market) → review
  for bugs or a regime change. This is not an automatic quit.
- **Never judge the strategy on 12 months against the S&P 500.** A realistic
  tilt needs decades to prove itself statistically (research report); short
  windows measure noise.
- **Never:** leverage, rule changes during a drawdown, or manual overrides.
  Every change goes through the funnel → backtest → shadow run.

---

## What the AI does, and what it doesn't

| Does | Doesn't |
|---|---|
| Writes and tests all the code; runs backtests and keeps the experiment log | Predict prices |
| Computes your instructions on every tranche date | Trade your account from the chat |
| Reviews results monthly and explains every alert | Promise returns |
| Challenges every rule change against the evidence funnel | Skip a gate because results look good |

## Realistic expectations

v0.2 is designed for **consistency**: returns close to equities over a full
cycle, with drawdowns roughly half as deep. That is a hypothesis; Step 4
replaces it with backtested, after-tax numbers per market type. Expect to
trail a 100% equity portfolio in strong bull years, to lose money in sudden
crashes, and to live through a managed-futures sleeve's flat years. Following
the rules through those periods is where the long-run result comes from.

---

## To start Step 1, I need from you

1. Your Step 0 answers, or "defaults". Above all: **do you have a PEA?**
2. Your trade history from the Ross attempt, attached in chat or in
   `systematic/private/`.
3. Any lessons for LESSONS.md §E: rejections, order mistakes, rule breaks.
