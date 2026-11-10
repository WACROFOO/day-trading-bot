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

One **rules-based portfolio** with seven sleeves, managed by **monthly** rules.
It does not trade intraday and it does not try to predict prices. Each sleeve
earns a return that has survived publication, costs, and testing in several
countries, and the sleeves are chosen to fail at different times, which is
where consistency comes from.

| Sleeve | Target | Role |
|---|---|---|
| World equity (in a PEA) | 35% | The equity premium |
| Momentum tilt | 15% | Return tilt (the best-evidenced one) |
| Quality tilt | 10% | Return tilt that partly offsets momentum crashes |
| Managed futures | 15% | Makes money in long bear markets |
| US Treasuries, EUR-hedged | 10% | Deflation hedge, held only while beating cash |
| Gold | 5% | Inflation and panic hedge |
| EUR cash | 10% | Dry powder; where filtered sleeves park |

A monthly trend filter moves the equity sleeves to cash while the world market
is below its 10-month average. Rebalancing is split across four dates a month.
The exact rules are in [STRATEGY.md](STRATEGY.md) (v0.2). Why these sleeves and
not others is in the
[research report](research/reports/Retail%20systematic%20strategy%20candidates.md).

## Files

| File | What it is |
|---|---|
| [ROADMAP.md](ROADMAP.md) | The step-by-step plan: what we build, what you do, and the go/no-go gate at the end of each step. |
| [STRATEGY.md](STRATEGY.md) | The rule spec (v0.2): every rule as a parameter we can backtest, plus the evidence funnel for adding new ones. |
| [LESSONS.md](LESSONS.md) | What we carry over from the Ross project: order handling, errors, data, process. |
| [research/](research/reports/Retail%20systematic%20strategy%20candidates.md) | The strategy-candidate research: ranked candidates, evidence, French costs and tax, and the selection method. |

Code will live here as it is built (`src/`, `tests/`, `research/`), with its
own dependencies, and will not import from `src/paper_trading/`. Patterns get
copied and adapted, so the two projects can never break each other.

## Status

**Step 0 of 9.** The plan, the research and rule spec v0.2 are written. There is no code and no backtest yet.

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
