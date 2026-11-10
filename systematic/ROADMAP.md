# Roadmap — from zero to a live system, step by step

Each step lists **what we build** (mostly me, in code), **what you do**, and a
**gate**: the test that has to pass before the next step starts. If a gate
fails, the step says what happens next. Sometimes the answer is "this part of
the strategy is dropped". That counts as a success: it costs time, not money.

Dates assume we start the week of **16 November 2026** at a part-time pace
(3–5 hours a week from you). They slip if a gate fails, and that's fine.

## Overview

| Step | What | Who | Target | Gate |
|---|---|---|---|---|
| 0 | Decisions and broker account | You | 15 Nov 2026 | Answers given (or defaults accepted) |
| 1 | Post-mortem of the Ross attempt | Both | 22 Nov | — (feeds the rules) |
| 2 | Data foundation | Me | 4 Dec | G2 · data checks pass |
| 3 | Backtest engine | Me | 18 Dec | G3 · known-answer tests pass |
| 4 | Core backtest → **core goes live, you click** | Both | 15 Jan 2027 | G4 |
| 5 | Swing research, out-of-sample | Both | 5 Feb | G5 |
| 6 | The bot: daily pipeline, broker, kill switch | Me | 5 Mar | G6 · fault-injection tests |
| 7 | Paper trading the swing engine | Bot + you | early Jun | G7 |
| 8 | Swing live at 25% → 50% → 100% | Bot + you | Oct 2027 | G8 at each step |
| 9 | Operate, review, quit test | Ongoing | Oct 2028 | G9 · beats the S&P 500 or stops |

There are **two tracks** after Step 4:

- **Track A, the core,** trades only a handful of times a year. Once its
  backtest passes (G4), it goes live in *advisor mode*: the system tells you
  what the rules say, and you place the few orders yourself. It does not need
  months of paper trading, because a twice-a-year rebalancer would barely trade
  in three months.
- **Track B, the swing engine,** trades every week and depends on the
  automation, so it goes through paper trading and a slow ramp first.

---

## Step 0 — Decisions (you, this week)

Answer these, or reply "defaults" to accept the right-hand column. Your actual
numbers stay in `systematic/private/`, never in git (the repo is public).

| # | Decision | Default |
|---|---|---|
| 1 | Tax residence and account type | France; a standard securities account (CTO) at the bot broker. A PEA is tax-advantaged after 5 years but only holds EU / PEA-eligible equity funds and has no trading API. It's worth revisiting for the core's equity part later. |
| 2 | Broker | Interactive Brokers (its EU entity): API, paper account, UCITS ETFs and US stocks in one place. **Open the account now**, because verification takes days to weeks; Step 2 needs it to check instruments and Step 6 to connect. |
| 3 | Capital | Total amount you will put in; the swing engine is capped at 30% and starts at a quarter of that. Your emergency fund (3–6 months of expenses) stays outside, in full. |
| 4 | Pain limits | Core: max −15% peak to trough. Swing: max −20% of its sleeve. These become gate thresholds and live stop rules. |
| 5 | Where the bot runs | Small VPS (~€5/month) or an always-on home PC. It needs to run at 23:00 Paris on trading days. |
| 6 | Alerts | Telegram (default) or email |
| 7 | Your time | Steps 1–6: 3–5 h/week. After launch: 2 min/day, 30–60 min/week. |

**Admin with a foreign broker (France):** declare the account every year
(form 3916), declare your gains and dividends yourself (the broker won't
withhold French tax), and sign the W-8BEN form so US dividends are withheld at
the treaty rate. Gains in a CTO are taxed at the flat tax (PFU) in the year you
sell, so turnover has a tax cost; the backtest reports after-tax results too.
This is not tax advice: confirm with an accountant.

---

## Step 1 — Post-mortem of the Ross attempt (week of 16 Nov)

**Why:** to find out where the money actually went, so the new rules fix the
real problem and not a guessed one.

**You give me:** whatever trade history exists:
`data/paper_trading.db` from the platform and/or broker statements (CSV).
Attach them in our chat, or put them in `systematic/private/` in your local
clone. Either way they never get committed.

**I build:** `systematic/research/postmortem.py`. It reports:
- gross vs. net P&L, and cost per trade measured in R
- win rate, expectancy, average win vs. average loss
- P&L by time of day and by price bucket
- how often the risk rules tripped, and what happened after
- what share of losses came from the worst 10% of trades

**Output:** a report in `systematic/private/` (it is your data, so it stays
local). Findings go into LESSONS.md §E and, where relevant, into the rule spec.

**Gate:** none. This step informs the design; it doesn't block anything.

---

## Step 2 — Data foundation (23 Nov → 4 Dec)

**I build:**
- Daily price history with dividends (total return), cached locally as parquet.
- Long-history stand-ins for the years before an ETF existed (indices, mutual
  funds, gold futures), so we can test 2000–02.
- EUR/USD history, so every result is in euros; EUR short rates for the cash
  bucket (ECB data portal).
- A US exchange calendar for holidays and half-days.
- The **instrument map**: each backtest series → its live UCITS instrument
  (name, ISIN, exchange, currency, accumulating vs. distributing,
  hedged vs. unhedged).

**You do:** check in your IBKR account that each UCITS instrument on the map is
actually tradable for you.

**Gate G2:**
- No missing days against the calendar; splits and >25% jumps reviewed.
- SPY's 2008 and 2022 drawdowns reproduced within 1 point of published figures.
- Each UCITS/US pair has a weekly-return correlation ≥ 0.95 over the period
  where both exist.

*If it fails:* fix the source or swap the instrument. Nothing downstream starts
on bad data.

---

## Step 3 — Backtest engine (7 Dec → 18 Dec)

**Why our own engine:** the rules go in one shared module that emits target
weights, and the **same code** runs the backtest, the paper account and the
live account. What gets tested is exactly what gets traded. We also need EUR
accounting, resting limit orders and broker-side stops, which off-the-shelf
libraries handle awkwardly.

**I build:**
- A daily event loop. The signal is taken at day *t*'s close and filled at
  *t+1* at the earliest. Limits rest until the price trades through them;
  stops that gap fill at the open (LESSONS B8–B9).
- Costs: commission, spread/slippage per instrument, FX conversion, minimums.
  Every run also reports results at 2× costs.
- Cash earns the short rate. Optional after-tax view: flat tax on realized
  gains, paid yearly.
- Metrics, all in EUR: annual return (CAGR), volatility, max drawdown, Sharpe,
  Sortino, worst month and year, time under water, turnover, number of trades,
  cost drag.
- **Experiment log:** every run appends its config, data range and results to
  `systematic/research/experiments.csv` (LESSONS C5).

**Gate G3:**
- Buy-and-hold SPY equals the data's own total return.
- A monthly-rebalanced 60/40 matches a hand calculation.
- A lookahead test proves no signal can see day *t+1*.
- All tests run offline on fixtures.

---

## Step 4 — Core backtest, then the core goes live (4 Jan → 15 Jan 2027)

**We test** Engine 1 (STRATEGY.md §1) in EUR over:
- the full period, 2003 → 2026
- four stress windows: **2000–02** (stand-ins), **2007–09**, **2020** and
  **2022** (stocks and bonds fell together)
- against three benchmarks: S&P 500 in EUR, a 60/40 portfolio, and 100%
  Nasdaq-100

**We also test these variants,** and only these, to avoid fitting:
- Treasuries hedged vs. unhedged
- with vs. without the crash ladder
- with vs. without the trend filter

**Gate G4:**
1. In every stress window, the core's max drawdown is **≤ 60% of the
   S&P 500's**, and within your Step 0 pain limit.
2. Over the full period, its annual return is **no more than 2 points a year
   behind 60/40**.
3. The ladder adds value in at least 3 of the 4 crash windows. If not, it's
   removed.

*If 1 or 2 fails:* one revision of the weights, then re-test. If it fails
again, the core becomes something simpler and proven: a world-equity ETF plus
bonds plus cash.

**When G4 passes, Track A starts:** I add a `core-advisor` command. It reads
your holdings from a file in `private/` and prints what the rules say to do
today. You deploy the core in **three monthly tranches** (January, February,
March), so the entry date doesn't hinge on a single day.

---

## Step 5 — Swing research, out-of-sample (18 Jan → 5 Feb)

**Method:**
- **In-sample, 2003–2016:** build and tune Setups A and B (STRATEGY.md §2) here
  only.
- **Out-of-sample, 2017–2026:** locked. Run **once**, at the end, with the
  final parameters.
- **Plateau check:** every chosen parameter's neighbours (the §5 ranges) must
  also be profitable. A sharp peak means it was fitted to noise.
- **Cost stress:** results at 2× costs.

**Gate G5** (out-of-sample, net of costs, in EUR):
1. Annual return at least the S&P 500's (in EUR), **or** a similar return with
   a max drawdown no more than 60% of the S&P 500's.
2. Still profitable at 2× costs.
3. Parameters sit on a plateau.
4. Max drawdown ≤ 20% of the sleeve.
5. At least 100 trades, so the result means something.

*If it fails:* **Engine 2 is not built.** Its 30% goes to the core, and the
plan simplifies to Track A only. Be ready for this. Sector momentum and short
pullback strategies are well known, and published edges tend to shrink. One
re-design is allowed (for example a different universe), with a fresh
out-of-sample period and no peeking.

---

## Step 6 — The bot (8 Feb → 5 Mar)

**I build**, in `systematic/src/`:

| Module | Job |
|---|---|
| `data` | Daily fetch, cache, data checks (STRATEGY §3) |
| `strategy` | The rules → target weights. The same module the backtest uses. |
| `portfolio` | Targets vs. holdings → proposed orders |
| `risk` | Pre-trade checks and the kill-switch latch (LESSONS B2–B4) |
| `broker` | Adapters for the local simulator and IBKR (paper/live, via `ib_async`) |
| `ledger` | SQLite: order lifecycle with client IDs, fills, positions, equity (LESSONS B5) |
| `runner` | The 17:00 New York daily job: fetch → check → signal → reconcile → orders → journal → alert |
| `alerts` / `report` | Daily summary, immediate alerts, weekly review report |

**Three modes, one codebase:**
- `advisor`: proposes, sends nothing
- `paper`
- `live`: needs an explicit flag plus a confirmation in the config file

**Operational note:** IBKR's API runs through IB Gateway, which needs periodic
re-login with two-factor auth. Plan on a weekly login from your phone; we
automate the daily restart.

**Gate G6:** fault-injection tests pass for all of these:
- stale data
- broker unreachable
- partial fill
- rejected order
- the job run twice (it must not double-buy)
- a crash mid-run, then restart
- a reconciliation mismatch
- a DST-change date

Then 2 weeks of dry runs against the paper account with zero unhandled errors.

---

## Step 7 — Paper trading the swing engine (8 Mar → early Jun)

At least **3 months and 20 trades**, whichever comes later.

**Daily (you, 2 min):** read the summary. Don't touch anything.

**Weekly (me, with you):**
- Re-run the backtest over the same dates. Signals must match **100%**; any
  mismatch is a bug, and it gets fixed before the clock continues.
- Compare actual fills with the cost model.
- Review errors and alerts.
- Once, trigger the kill switch on purpose to prove it works end to end.

**Gate G7:**
- 100% signal match.
- Slippage ≤ 1.5× the model.
- Zero unhandled errors in the last 4 weeks.
- Kill switch tested.

---

## Step 8 — Swing live, slow ramp (Jun → Oct 2027)

| Size | Duration | Move up only if |
|---|---|---|
| 25% of the sleeve (7.5% of capital) | 2 months | Drawdown inside the backtest's worst, slippage ≤ 1.5× model, **no manual overrides** |
| 50% | 2 months | Same |
| 100% | — | — |

Any step that fails goes back one size step, or to paper if it was a bug.

The core can stay in advisor mode permanently. At 4–8 trades a year, clicking
them yourself is cheap insurance. Switching it to automatic is optional.

---

## Step 9 — Operate and review (ongoing)

| When | What |
|---|---|
| Daily | 2-minute summary; alerts only if something tripped |
| Weekly | 30–60 min journal review with me: trades, fills vs. model, rule adherence |
| Monthly | Performance vs. benchmarks, in EUR, net of costs |
| January / July | Calendar rebalance (C3); tax summary for the year |
| Yearly | Strategy review: do the rules still hold? |

**Quit rules (Gate G9):**
- **Swing engine:** 12 months after reaching full size (about Oct 2028), if it
  has not beaten the S&P 500 in EUR, net of costs and taxes, it shuts down and
  its money moves to the core.
- **Any sleeve** that hits its Step 0 pain limit stops completely until we have
  reviewed it.
- **Never:** add leverage, change rules during a drawdown, or override the bot
  by hand. Every rule change goes through backtest → paper again.

---

## What the AI does, and what it doesn't

| Does | Doesn't |
|---|---|
| Writes and tests all the code; runs backtests and keeps the experiment log | Predict prices |
| Reviews the journal weekly and explains every alert | Trade your account from the chat |
| Challenges any rule change against the data | Promise returns |
| Keeps STRATEGY.md and the code in sync | Skip a gate because results look good |

## Realistic expectations

The return figures from our chat (roughly 8–11% a year long-run for the core,
more if a crash lets the ladder work) are **judgment, not results**. Step 4
replaces them with backtested numbers, and Steps 7–8 test those live. Expect
losing quarters, and expect to trail an all-tech portfolio in strong bull
markets. That's the price of the protection.

---

## To start Step 1, I need from you

1. Your Step 0 answers, or "defaults".
2. Your trade history from the Ross attempt: attached in chat, or in
   `systematic/private/`.
3. Any lessons for LESSONS.md §E: rejections, order mistakes, rule breaks.
