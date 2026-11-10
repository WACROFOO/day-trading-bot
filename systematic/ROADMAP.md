# Roadmap — from zero to a live system, step by step

Each step lists **what we build** (mostly me, in code), **what you do**, and a
**gate**: the test that has to pass before the next step starts. If a gate
fails, the step says what happens next. Sometimes the answer is "this part of
the strategy is dropped". That counts as a success: it costs time, not money.

This is v0.3 of the roadmap. It follows STRATEGY.md v0.3: one portfolio that
**grows into its sleeves in stages** (§2.1), because a small portfolio that
grows through monthly contributions cannot hold seven sleeves cheaply. The
evidence behind the sleeves is in the
[research report](research/reports/Retail%20systematic%20strategy%20candidates.md).

## Overview

| Step | What | Who | When | Gate |
|---|---|---|---|---|
| ▶ | **Start stage 1 now:** open the PEA and buy the world tracker every month | You | Nov 2026 | — |
| 0 | Remaining decisions | You | 15 Nov 2026 | Answers given (or defaults accepted) |
| 1 | Post-mortem of the Ross attempt | Both | 22 Nov | — |
| 2 | Data foundation: index, factor and trend histories in EUR | Me | 4 Dec | G2 |
| 3 | Backtest engine: contributions, stages, EUR, French tax | Me | 18 Dec | G3 |
| 4 | Test 1: does the trend filter help a growing portfolio? | Both | 15 Jan 2027 | G4 |
| 5 | Tests 2 and 3: momentum and the trend sleeve (they decide stage 2) | Both | 12 Feb | G5 |
| 6 | The advisor: monthly instructions, tracking, discipline checks | Me | Mar 2027 | G6 |
| 7 | Stage 2: open the CTO, route contributions to the new sleeves | You + advisor | Portfolio reaches €10k | — |
| 8 | Automation of the CTO sleeves: shadow run, then staged | Bot + you | Stage 3 (€30k) | G7, G8 |
| 9 | Operate and review | Ongoing | — | G9 |

**The brain first, the hands later.** In stages 1–2 there are one or two orders
a month. Automating them buys little, and it costs a lot relative to a small
portfolio: market data, a server, and a weekly IBKR login. So the decision
logic (the advisor) gets built and proven first. Automated order placement
waits until stage 3, when the CTO holds four or more sleeves. The PEA stays
manual for good, because no PEA broker offers an API.

---

## ▶ Start stage 1 now (no backtest needed)

Stage 1 is the benchmark itself: a world index fund, bought every month. It
doesn't need our backtest to justify it. Everything else gets tested against
it.

1. **Emergency fund first.** 3–6 months of expenses, kept outside the
   portfolio, in full.
2. **Open a PEA.** The 5-year tax clock starts at the first deposit, so every
   month of delay costs a month of waiting later. Pick a broker where the
   monthly order costs at most ~0.5% of its size. If the broker offers a free
   automatic monthly savings plan on the ETF inside the PEA, that's ideal.
3. **Buy a PEA-eligible MSCI World tracker every month.** Accumulating share
   class; candidates from the research are WPEA or DCAM (~0.20% a year).
   Confirm eligibility and fees on justETF and with the broker.
4. **That's all.** No filter, no timing, no extra sleeves, no selling. The
   advisor (Step 6) takes over the monthly decision once it exists.

---

## Step 0 — Decisions (done, 10 Nov 2026)

Your amounts stay out of git; the repo is public.

| # | Decision | Answer |
|---|---|---|
| 1 | Capital and contributions | Decided (kept in `private/`) |
| 2 | PEA | None yet, so **open one now** (see ▶ above) |
| 3 | Pain limit | **−20%** from peak |
| 4 | Trend sleeve (stage 2) | Only if **profitable** and **no leverage**. Managed-futures funds use leverage internally, so Test 3 tests both an S4a fund and an unlevered S4b basket (STRATEGY §2.2). You choose after seeing the results. |
| 5 | Broker for the CTO | Interactive Brokers (EU entity), opened when the portfolio approaches €10k |
| 6 | Your time | Steps 1–6: 3–5 h/week. Live: about 10 minutes a month. |

**Admin once the CTO exists (stage 2, France):**
- Declare the account every year on form 3916.
- Declare gains yourself (PFU 31.4% since 2026).
- Prefer accumulating share classes, which avoid the monthly 2778-DIV-SD
  prepayment.
- Sign the W-8BEN form.

This is not tax advice: confirm with an accountant.

---

## Step 1 — Post-mortem of the Ross attempt (week of 16 Nov)

**You give me** whatever trade history exists: `data/paper_trading.db` and/or
broker statements, attached in chat or in `systematic/private/` (never
committed).

**I build:** `systematic/research/postmortem.py`. It reports gross vs. net
P&L, cost per trade, expectancy, P&L by time of day, how often the risk rules
tripped, and how concentrated the losses were.

Findings go into LESSONS.md §E. **Gate:** none.

---

## Step 2 — Data foundation (23 Nov → 4 Dec)

All free, apart from optional daily UCITS prices:

| Data | Source | Used for |
|---|---|---|
| MSCI World, World Momentum, World Quality, Europe Momentum (end-of-month, net) | MSCI index downloads; factor indexes are back-tested before launch | S1–S3, Tests 1–2 |
| Momentum, value and quality factors, US and international | Ken French library, AQR datasets | Long-history checks, hold-out region |
| Trend: AQR Time-Series Momentum (1985+), SG Trend Index (2000+), DBMF (2019+) | AQR, SG/BarclayHedge, fund data | Test 3 |
| Treasuries, gold, EUR/USD, EUR and USD short rates | Index/fund data, ECB Data Portal, FRED | S5–S7, EUR conversion, hedging cost |
| Daily UCITS ETF prices | EODHD (paid, from stage 3) or yfinance (free fallback) | Tracking checks, the advisor |

Also the **instrument map**: each sleeve → UCITS ETF (ISIN, accumulating,
hedged, PEA-eligible, TER).

**Gate G2:** MSCI World EUR annual returns match the factsheets within 0.5
points; each ETF's tracking difference against its index is ≤ ~0.5% a year;
no unexplained gaps.

---

## Step 3 — Backtest engine (7 Dec → 18 Dec)

The rules live in one module that outputs target weights. The **same code**
runs the backtest and the advisor (and later the bot), so what is tested is
exactly what is traded. `bt` serves as an independent cross-check.

**What the engine models, beyond a textbook backtest:**
- **Monthly contributions** and **stage transitions** (STRATEGY §2.1): the
  portfolio is simulated as it will really be built, not as a lump sum.
- **The PEA lock:** money never moves from the PEA to the CTO, so new sleeves
  are funded only by routed contributions.
- **Real costs:** order minimums (€1.25 at IBKR), spreads, FX, broker fees.
  Every run is repeated at 2× costs.
- **Tax:** the 31.4% PFU on gains realised in the CTO each year, and the 18.6%
  PEA levies at the end. Results are reported **after tax**.
- **Metrics:** after-tax ending wealth over rolling 10-year windows, Sharpe,
  max drawdown in euros and in %, time under water, turnover, cost drag,
  deflated Sharpe, and probability of backtest overfitting.
- **The experiment log**, `research/experiments.csv`, records every run.

**Gate G3:** buy-and-hold matches the index; a monthly 60/40 matches `bt`;
the contribution arithmetic matches a hand calculation; the lookahead test
passes; all tests run offline.

---

## Step 4 — Test 1: the trend filter for a growing portfolio (4 Jan → 15 Jan 2027)

**The question:** with monthly contributions, does the 10-month filter beat
plain monthly buying? It is tested in stages 1–2 (S1 only) and stage 3 (the
full portfolio), with the pre-registered variants in STRATEGY §8. The main
period runs from the mid-1990s to 2021; **2021–2026 is held out and run
once**.

**Gate G4:**
- **Stages 1–2:** the filter switches on only if it raises the after-tax
  Sharpe ratio *and* costs less than 5% of median ending wealth over rolling
  10-year windows, compared with plain monthly buying. Otherwise stage 1 stays
  plain buying.
- **Stage 3 portfolio:**
  - after-tax Sharpe ≥ the PEA world tracker's (no more than 0.2 below it in
    the hold-out);
  - max drawdown ≤ 60% of world equity's in 2000–02, 2008 and 2022, and
    inside your pain limit;
  - after-tax return ≥ a EUR 60/40's.

*If stage 3 fails:* the long-run portfolio becomes the PEA tracker plus a
cash/bond mix sized to your pain limit.

---

## Step 5 — Tests 2 and 3: momentum and the trend sleeve (18 Jan → 12 Feb)

These two sleeves are what stage 2 adds, so they must be settled before the
portfolio reaches €10k.

- **Test 2 · Momentum:** an MSCI World Momentum ETF against MSCI World. Sector
  rotation and GEM-style regional momentum run as alternative arms. Europe is
  the held-out region.
- **Test 3 · Trend sleeve:** S4a (managed-futures fund, using the AQR and SG
  Trend histories net of its 0.75% fee) and S4b (unlevered four-asset trend
  basket), each at 0, 10, 15 and 20% of the portfolio.

**Gate G5:**
- **Momentum** enters stage 2 only with a positive net excess return over MSCI
  World in the full history *and* in the held-out region, and a worst relative
  drawdown you have seen in advance and accept.
- **The trend sleeve** enters only if it is **profitable**: a positive return
  above cash after fees over the full history, a higher portfolio Sharpe ratio
  and a lower max drawdown, all at 2× costs as well. You also see its worst
  stretch in advance (S4a's index lost 18.6% in the 12 months to April 2025).
  S4a is used only if you accept leverage inside the fund; otherwise S4b.
- A sleeve that fails is not added; stage 2 holds only what passed.

---

## Step 6 — The advisor (Mar 2027)

The bot's brain, running on your own computer with free end-of-day data. On
the first trading day of each month it:
- reads your holdings (a file in `private/`, or your broker's CSV export);
- works out your stage, applies the rules (filters, bands, contribution
  routing), and **tells you exactly what to buy, in which account, for how
  much**;
- checks the discipline rules: the pain limit, results outside the backtest's
  range, and any manual deviation from last month's instructions;
- keeps the journal, and in January produces the tax pack (gains, form-3916
  reminder).

Built with the risk and ledger patterns from the old project (LESSONS B1–B5,
B10, C1–C4).

**Gate G6:** advisor output = the backtest's rules on the same dates, for 24
historical months; all tests offline.

---

## Step 7 — Stage 2 (when the portfolio reaches €10k)

Open the CTO (default: IBKR). Monthly contributions go to whichever passed
sleeves (momentum, trend sleeve) are most underweight, until they reach
target. The PEA keeps its holdings and receives contributions only once the
CTO sleeves are at target. The advisor handles the arithmetic.

---

## Step 8 — Automation of the CTO sleeves (from stage 3, €30k)

From stage 3, the CTO holds four or more sleeves and automation pays for its
fixed costs. **I build** the `broker` adapter (IBKR via `ib_async`), the
order lifecycle with client IDs and reconciliation, and the kill switch
(STRATEGY §5). IBC was retired in September 2026, so plan on IB Gateway's
auto-restart setting plus a weekly two-factor login.

- **Shadow run, 3 months:** the bot trades the IBKR paper account while you
  follow the advisor. **G7:** 100% agreement, zero unhandled errors for 4
  weeks, kill switch tested.
- **Staged automation:** smallest sleeves first for 2 months, then all CTO
  sleeves. **G8:** automated orders = proposals 100%; costs ≤ 1.5× the model;
  no manual overrides.

---

## Step 9 — Operate and review (ongoing)

| When | What |
|---|---|
| Monthly (about 10 minutes) | Read the advisor's instructions, place the order(s), confirm |
| January | Full rebalance check (with new money first); tax pack |
| Yearly | Strategy review; research-sleeve candidates through the funnel (from stage 4) |

**Review and stop rules (Gate G9):**
- **Pain limit hit** → stop and review.
- **Results outside the backtest's range** → review for bugs or a regime
  change. Not an automatic quit.
- **Never judge on 12 months against the S&P 500.** Short windows measure
  noise.
- **Never:** leverage, rule changes during a drawdown, or skipped
  contributions because the market "looks bad". Every rule change goes
  through the funnel → backtest → advisor.

---

## What the AI does, and what it doesn't

| Does | Doesn't |
|---|---|
| Writes and tests the code; runs the backtests and keeps the experiment log | Predict prices |
| Computes your monthly instructions | Trade your account from the chat |
| Reviews results and explains every alert | Promise returns |
| Challenges every rule change against the evidence funnel | Skip a gate because results look good |

## Realistic expectations

While the portfolio is small, **the monthly contribution is the main engine**:
in the early years, what you add matters far more than any strategy's extra
return. The strategy's job in that phase is to keep costs and taxes near zero
and to keep you buying through crashes. Strategy returns start to matter once
the portfolio is worth several years of contributions, which is when stages 3
and 4 bring in the protective and return-seeking sleeves.

---

## Next, I need from you

1. **Open the PEA** and make the first purchase (stage 1).
2. Your trade history from the Ross attempt, for Step 1.
