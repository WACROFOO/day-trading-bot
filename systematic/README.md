# Systematic strategy — fresh start

A new strategy project, started from zero and kept separate from the Ross
Cameron day-trading work in the rest of this repo. Nothing outside this folder
is changed by it. The old work stays as it is: an archive and a source of
lessons.

## Why a fresh start

The small-cap intraday approach could not be made profitable. The reasons are
structural, not a lack of effort: costs ate a large share of every trade, free
data is 15 minutes late for intraday decisions, and the edge depended on inputs
(float, news, "support", tape reading) that cannot be computed reliably. The
details, with the numbers from this repo, are in [LESSONS.md](LESSONS.md).

What does carry over is the engineering: one guarded path for every order, a
risk lockout that survives restarts, net-of-cost fills, and the research rule
that a claim is not evidence until we have reproduced it.

## What the new system is

A **daily-bar, rules-based** portfolio in two engines. It makes decisions once
a day, after the US close, from end-of-day data. It does not trade intraday and
it does not try to predict prices.

| Engine | Share of capital | What it does |
|---|---|---|
| 1 · Core | 70% | Defensive barbell allocation, mechanical rebalancing, and a crash-buying ladder that deploys cash in steps when the Nasdaq falls 20/30/40%. |
| 2 · Swing | 30% | Momentum rotation and pullback trades on liquid ETFs, with stops held at the broker and fixed risk per trade. Has to earn its place, or it is shut down and its money moves to the core. |

The exact rules are in [STRATEGY.md](STRATEGY.md).

## Files

| File | What it is |
|---|---|
| [ROADMAP.md](ROADMAP.md) | The step-by-step plan: what we build, what you do, and the go/no-go gate at the end of each step. |
| [STRATEGY.md](STRATEGY.md) | The rule spec (v0.1): every rule as a parameter we can backtest. |
| [LESSONS.md](LESSONS.md) | What we carry over from the Ross project: order handling, errors, data, process. |

Code will live here as it is built (`src/`, `tests/`, `research/`), with its
own dependencies, and will not import from `src/paper_trading/`. Patterns get
copied and adapted, so the two projects can never break each other.

## Status

**Step 0 of 9.** The plan is written. There is no code and no backtest yet.

**Verification status:** ❌ Not validated. Every number in this folder is a
starting value to test, not a result.

## Ground rules

1. **No money before the gates.** Every step in the roadmap ends with a test.
   We only move on when it passes.
2. **Profit is something we test for, never assume.** The plan is built to
   find out cheaply whether an edge exists, and to kill whatever does not work
   before it costs money.
3. **The repo is public.** Trade logs, statements, account numbers, capital
   amounts and API keys never get committed. They live in `systematic/private/`
   (gitignored) or in `.env`.
4. The knowledge base's standing rules apply here too
   (`knowledge-base/README.md`): claims are separate from evidence, survivorship
   bias is the default, and nothing is validated until it has been run
   out-of-sample with realistic costs.

Not financial advice. Trading involves substantial risk of loss.
