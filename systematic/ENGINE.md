# Backtest engine: design plan (ROADMAP Step 3)

The engine answers one question for each test in the roadmap: **if you had
followed these rules, with your real contributions, accounts, fees and French
tax, what would you have ended up with, and what would the worst stretches
have felt like?** It feeds Gates G4 (Tests 1 and 3) and G5 (Test 2).

This document is the plan. Code follows it milestone by milestone (§9), and
each milestone ships with its tests.

---

## 1. Design principles

1. **One rules module for everything.** `strategy.rules` turns "what the
   market looks like as of today" and "what you hold" into target weights and
   reasons. The backtest, the monthly advisor (Step 6) and the bot (Step 8)
   all call the same function. What gets tested is exactly what gets traded.
2. **The rules can't see the future.** They receive a `MarketView` truncated
   at the decision date. The data after that date is not hidden by
   convention; it is physically absent from the object (LESSONS C2).
3. **Simulate the plan as it will really run:** monthly contributions,
   stages, two accounts, the PEA lock, real broker fees, French tax, after-tax
   results. A lump-sum, tax-free backtest would answer a question you aren't
   asking.
4. **Only pre-registered variants run by default.** Variants come from
   STRATEGY.md §8. Anything else needs an `--exploratory` flag and counts
   against the family's trial budget. Every run is logged (§7).
5. **The hold-out is locked mechanically.** 2021–2026 can only be computed
   with an explicit unlock, which is recorded. A second unlock is refused
   without a written reason.
6. **Small, readable, tested.** Plain Python and pandas on monthly data. No
   framework: what we need (EUR, two accounts, French tax, contributions) is
   exactly what frameworks don't model.

## 2. Scope

| In | Out (and why) |
|---|---|
| Monthly decisions on month-end data, 1997 → 2026 | Intra-month dates: splitting rebalancing across four dates a month (R1, stage 4) needs daily data. Not needed for years. |
| Sleeves as index proxies (DATA.md) | Individual ETF quirks (tracking difference) are covered by a cost assumption until daily ETF prices exist |
| Two accounts (PEA, CTO), stages, contributions, the PEA lock | Whole-unit rounding: at a few euros per unit, the leftover is negligible |
| Broker fees, spreads, FX; French tax (PFU, PEA levies, carry-forward) | Tax law history: **today's rules are applied to all years**, to measure the strategy under the rules you'll actually face |
| Benchmarks run through the same engine | Behaviour (panic selling): the backtest assumes perfect discipline, which is the bot's job |

## 3. Architecture

```
systematic/src/portfolio_bot/
├── data/                 (Step 2, done) sources, catalog, sleeves in EUR
├── strategy/
│   ├── params.py         StrategyParams: every §8 parameter, defaults = spec, frozen + hashable
│   ├── signals.py        10-month filter, 12-month excess return, bonds-beat-cash
│   └── rules.py          target_plan(view, holdings, params) -> TargetPlan (targets per account + reasons)
├── engine/
│   ├── market.py         MarketData (all sleeve returns/levels) and MarketView (truncated at a date)
│   ├── accounts.py       Account (PEA / CTO): positions, cash, cost basis, eligibility, PEA lock
│   ├── costs.py          broker fee schedules, spreads, FX
│   ├── tax.py            French tax: CTO yearly PFU with carry-forward; PEA end-of-plan levies
│   ├── simulator.py      the monthly loop (§4)
│   ├── metrics.py        TWR, IRR, drawdowns, Sharpe/Sortino, rolling windows, DSR, PBO
│   └── experiments.py    run config, hashing, experiment log, hold-out lock
└── benchmarks.py         PEA world buy-and-hold; EUR 60/40
systematic/scripts/backtest.py   CLI: run a test, its variants and rolling starts; write the report
```

**Data flow for one month:**

```
MarketData ──view(as_of=t)──► rules.target_plan ──► targets per account
                                    ▲                      │
      Accounts (holdings at t) ─────┘                      ▼
                                              simulator: orders → costs → fills
                                                           │
                         returns of month t+1 ◄────────────┘ ──► tax (December) ──► record
```

## 4. The monthly loop

For each month-end *t*, from the start date to the end date:

1. **Contribution.** Add the monthly amount (€500 by default; initial lump
   sum at the start) as cash, in the account that rule R6 routes it to.
2. **Stage.** Work out the stage from the portfolio value (STRATEGY §2.1:
   €10k / €30k / €100k), which sets the sleeves allowed and the targets.
3. **Signals and targets.** `rules.target_plan(view(t), holdings, params)`
   returns target weights per account, with reasons ("equity filter off:
   MSCI World 4.1% below its 10-month average").
4. **Orders.**
   - New money is spent first, on the most underweight sleeves (R6).
   - Sells happen only when a filter flips or a band is breached; band
     checks run monthly, with a full rebalance every January.
   - **The PEA lock:** money never moves from the PEA to the CTO. If the CTO
     sleeves are underweight, only new money fixes it.
   - Orders below the minimum (C7) are skipped.
5. **Costs.** Each order pays its broker fee (§5) plus the spread. Cash is
   reduced accordingly.
6. **Fills.** Orders fill at the month-end *t* level. The new weights then
   earn month *t+1*'s returns. That is equivalent to trading at the close of
   the decision day.
   - *Real-life delay:* in practice orders fill the next session. A
     pre-registered robustness run lags every signal by one full month, as
     an upper bound on the cost of delay.
7. **Returns.** Positions grow by their sleeve's return. CTO cash earns the
   EUR cash rate; **PEA cash earns 0%**, as uninvested PEA cash does at the
   recommended broker.
8. **Tax.**
   - *December:* realised CTO gains and losses for the year are netted, past
     losses carried forward up to 10 years, and the PFU (31.4%) is computed
     on any net gain.
   - *Payment:* the tax is paid **from the portfolio** the following
     September. That is conservative: paying it from your salary would leave
     more invested.
9. **Record** values, flows, costs, taxes, orders and the reasons behind
   them.

**At the end:** liquidation values before tax, and after tax (CTO: PFU on
unrealised gains; PEA: 18.6% social levies on gains if the plan is 5+ years
old, 31.4% if younger).

**Cost basis** follows the French rule for fungible securities: weighted
average purchase price (PMP) per fund and per account.

## 5. Costs (from research/BROKERS.md)

| Where | Fee model | Default |
|---|---|---|
| PEA, Bourse Direct | Free monthly plan on WPEA/DCAM; manual order €0.99 up to €500, then per the schedule | Monthly contributions €0; other orders per the schedule |
| CTO, IBKR | Tiered: 0.05%, min €1.25, max €29, plus about €1 of exchange fees on Xetra; FX 0.002% (min $2) only if a USD listing is used | EUR listings, so no FX |
| Spread / market impact | Basis points per side, by sleeve: equity ETFs 5 bp, Treasuries and gold 5 bp, managed futures 15 bp, cash ETF 2 bp | Every test is also run at **2× costs** |
| Fund fees (TER) | Deducted monthly from each sleeve's return | From config/instruments.csv |

TERs matter: the index proxies are gross of fund fees, so the engine
subtracts each fund's TER (0.06–0.75% a year) to land on what the ETF would
have returned.

## 6. Metrics and outputs

**Per run:**
- **After-tax ending wealth** in euros, plus total contributions, so the
  gain is visible.
- **Time-weighted return** (TWR, the strategy's own return) and
  **money-weighted return** (IRR, your return given when your money went in).
  With monthly contributions the two differ, and both matter.
- **Risk:** max drawdown in % and in €; worst 12 months; time under water;
  months beyond the −20% pain limit and when they happened.
- **Quality:** Sharpe and Sortino on monthly TWR; deflated Sharpe ratio using
  the family's real trial count.
- **Friction:** turnover, number of orders, costs paid, taxes paid, cost and
  tax drag in %/yr.
- **By market regime** (STRATEGY §9): returns in 2000–02, 2008, 2020, 2022,
  and in bull and sideways stretches.

**Rolling starts.** Your result depends on when you start. The plan is run
from **every possible starting month**, over 10-year horizons (also 5 and 15),
giving a distribution of outcomes: median, worst 10%, worst case. Gate G4's
stage 1–2 test reads from this distribution. The windows overlap, so they are
not independent samples, and the report says so.

**Across variants:** the probability of backtest overfitting (PBO), by
combinatorial cross-validation on each family's variants.

**Outputs:**
- a markdown report per test;
- CSVs of the monthly paths;
- one row per run appended to `research/experiments.csv`.

Your personal configuration (your amounts) lives in `systematic/private/`, and
so do reports run with it. The repo carries an example configuration with
illustrative amounts.

## 7. Experiment log and hold-out lock

Every run appends a row to `research/experiments.csv`:

| Column | Meaning |
|---|---|
| `run_id` | Hash of parameters + data snapshot + code version (same inputs → same id) |
| `family` / `variant` | e.g. `test1` / `filter=12m_excess` |
| `registered` | Pre-registered in STRATEGY §8, or exploratory |
| `period` | `main` (1997–2020) or `holdout` (2021–2026) |
| key metrics | TWR, IRR, after-tax wealth, max DD, Sharpe, costs, taxes |
| `trial_count` | Running count for the family, used by the deflated Sharpe ratio |

The **hold-out** can only be computed with `--unlock-holdout`. The first
unlock is logged with a timestamp. Later unlocks are refused unless
`--reason "..."` is given, and those runs are flagged in the log as
**contaminated**.

The minimum-length arithmetic (STRATEGY §7) is checked automatically. The
main period runs about 24 years, which supports roughly 20 trials at a target
Sharpe ratio of 0.5. The engine warns when a family exceeds its budget.

## 8. Benchmarks

Benchmarks run through the same engine, with the same contributions, costs and
tax:

1. **PEA world tracker, buy and hold:** the real alternative and the main
   hurdle. Everything goes into the PEA world ETF via the free plan.
2. **EUR 60/40:** world equity in the PEA, EUR-hedged Treasuries in the CTO,
   rebalanced with new money and yearly.

STRATEGY v0.1 is **dropped as a benchmark**. Its sector and single-stock
sleeves are not in the data layer, and the research already rejected them.

## 9. Milestones

| # | Milestone | Proven by | Target |
|---|---|---|---|
| M1 | `params`, `signals`, `MarketView` | Signals on hand-computed series; a lookahead property test (changing data after *t* never changes the decision at *t*) | 28 Nov |
| M2 | `accounts`, `costs`, single-account simulator | Buy-and-hold equals the sleeve's compound return; monthly 60/40 equals an independent vectorised calculation | 2 Dec |
| M3 | Contributions, stages, routing, the PEA lock | Constant-return contributions match the annuity formula; stage switches at the thresholds; no euro ever moves PEA → CTO | 5 Dec |
| M4 | `tax` | Worked examples: PMP cost basis, yearly PFU, loss carry-forward, PEA levies before and after 5 years | 9 Dec |
| M5 | `metrics` | TWR/IRR on known cash flows; drawdowns and rolling windows on synthetic paths; DSR/PBO against published examples | 12 Dec |
| M6 | Experiment log, hold-out lock, CLI, report | A run is reproducible from its `run_id`; the hold-out refuses to open twice | 16 Dec |
| M7 | **Gate G3**: all known-answer tests pass; an end-to-end run of both benchmarks | Report reviewed together | 18 Dec |

Then Step 4 (Tests 1 and 3) starts in January as planned, with the engine
frozen. Any change to it after that is logged in the experiment log, because
changing the engine is also a trial.

## 10. Modelling defaults (open for you to change)

| Choice | Default | Why |
|---|---|---|
| Monthly contribution | Flat (the same amount every month) | Simplest. A variant indexes it to 2% inflation |
| Taxes | Paid from the portfolio | Conservative |
| PEA cash | Earns 0% | What uninvested PEA cash earns |
| Tax rules | Today's (PFU 31.4%, levies 18.6%), applied to all years | We are testing the plan you will run, under the rules you'll face |
| Rolling horizon | 10 years (also 5 and 15) | Matches the roadmap's gate |
| Start date | February 1997 (first month all main sleeves exist) | Gold and Treasuries go back further, momentum and quality don't |

## 11. Known limitations (stated in every report)

- **Monthly granularity:** no intra-month moves; a month-end-to-month-end
  view understates intra-month drawdowns.
- **Proxies:** the weak points are listed in DATA.md, especially the trend
  factor (halved), gold (monthly averages, to be replaced) and commodities
  (spot index).
- **MSCI factor histories before launch** are MSCI's own back-tests.
- **Perfect discipline:** the backtest never panics, skips a contribution or
  overrides a rule.
- **Tax law** is frozen at today's rules.
