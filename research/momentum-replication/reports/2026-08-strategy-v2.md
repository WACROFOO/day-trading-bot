# Strategy v2 — the exit was the whole thing

`2026-08-score-basket.md` tested the specified strategy (screen on the pillars,
score 0–100, weight by score, buy the open, sell the close) and it failed:
equal weight beat the score in 16 of 16 matched pairs, raising the score
threshold made it monotonically worse, and 15 of 17 sessions lost money.

This is what replaced it and why. `diagnostics/exit_rules.py`.

## The measurement that pointed the way

Across 130 qualifying symbol-days (price $2–20 at the open, gap ≥10%, no
splits):

| | mean | median |
|---|---|---|
| open → close | **+0.24%** | −2.20% |
| **open → high** | **+16.00%** | +6.06% |
| open → low | −10.88% | −8.34% |

**The average name offers +16% at its high and closes at +0.24%.** The move is
there; sell-at-the-close hands all of it back.

### And the features only carry risk

Correlation of every pre-market feature against each outcome:

| feature | vs open→close | vs open→high | vs open→low |
|---|---|---|---|
| gap % | −0.086 | +0.183 | **−0.543** |
| gap-high % | −0.136 | +0.062 | **−0.470** |
| pre-market bars | −0.004 | +0.185 | −0.385 |
| rvol5 | −0.124 | −0.002 | −0.361 |
| shares out | −0.108 | −0.138 | −0.043 |
| fade into the bell | +0.017 | −0.110 | **+0.417** |

**Nothing predicts the upside** (max |r| = 0.19). **Several things predict the
drawdown** (gap at −0.54). That is exactly why scoring for return failed — the
score was built out of features that only contain risk information.

## Why this had to be tested on minute bars

Daily OHLC cannot resolve which came first. These names routinely print −10%
and +16% on the same day, so any bracket must conservatively assume the stop
filled first — which forces a loss onto nearly every trade that would also have
been a winner. On daily data every stop/target pair looked *worse* than the
baseline; that was an artefact, not a result.

Re-run on the 1-minute bars in `data/bars_cache`, where the sequence is known:
**55 of the 130 qualifying symbol-days, 38 symbols, all 17 sessions.**

## Exit rules, same entry, same trades

| exit rule | mean% | median% | win% | worst% | stdev | m/sd |
|---|---|---|---|---|---|---|
| **sell at close (baseline)** | **−1.34** | −1.75 | 38 | −36.1 | 23.49 | −0.06 |
| flat at 11:30 | −0.94 | −3.39 | 40 | −40.4 | 19.34 | −0.05 |
| stop −10% only | −2.53 | −10.00 | 25 | −10.0 | 12.78 | −0.20 |
| target +10% only | +0.09 | +10.00 | 62 | −36.1 | 13.91 | +0.01 |
| trail 15% | +0.45 | −1.21 | 38 | −15.0 | 11.68 | +0.04 |
| ladder +10 / trail 15 | +0.93 | +2.37 | 55 | −10.0 | 9.48 | +0.10 |
| **bracket −15% / +8%** | **+2.18** | **+8.00** | **69** | **−15.0** | **8.89** | **+0.25** |

A 6×6 sweep of stop × target was **positive in 36 of 36 cells** (+0.11% to
+2.36%), against 12 of 32 for the score strategy.

## v2, as a daily basket

Same €100/session, same universe, equal weight — only the exit changed.

| | v1 sell at close | **v2 bracket exit** |
|---|---|---|
| total P/L | −€2.22 | **+€35.88** |
| % of capital deployed | −0.1% | **+2.1%** |
| mean day | −0.13% | **+2.11%** |
| **median day** | −0.23% | **+3.40%** |
| win days | 7/17 | **11/17** |
| worst day | −24.26% | **−14.16%** |
| daily stdev | **16.71%** | **5.78%** |

**Robustness:** drop the best day and it is still +€27.88; drop the best two
and it is still +€19.88. v1 went negative on removing a single day.

**Costs:** 23 of 55 stops triggered, of which 3 gapped through the level — the
effect on the mean is below 0.01pp. With a 1.0% round-trip cost the mean is
still **+1.18%** per trade at a 67% win rate.

## The specification

1. **Universe** — the full morning scan, not a curated list.
2. **Gates**, both hard: open price **$2–20**, gap **≥10%**. No score, no
   ranking, no weighting.
3. **Equal weight** across everything that passes.
4. **Entry** — the 09:30 open.
5. **Exit** — bracket: **stop −15%, target +8%**, otherwise sell at the close.

Two things are deliberately absent. There is no attempt to pick winners,
because nothing measured predicts the upside. And the stop is *wide* while the
target is *close* — the opposite of "cut losses short and let winners run" —
because the typical name here offers about +6% and dips about −8% before it
does. Once the stop bounds the risk, the features that predicted drawdown stop
mattering: filtering to gaps of 10–30% made it **worse** (+1.31% vs +2.18%).

## What this is not

- **n = 55 trades over 17 sessions.** The paired improvement over the baseline
  is +2.69pp with a t of **+1.00** — not statistically significant. This is a
  well-behaved hypothesis, not a proven edge.
- The 55 are the symbol-days the pipeline happened to cache, a subset chosen by
  pipeline history rather than outcome. Not a random sample of the 130.
- **Pillar 3 (news) is still unscored.** On 2026-08-05 four of six traps were
  visible only in filings.
- No borrow costs, no partial fills, fractional shares assumed.
- `+8%` is close to the measured median MFE of +6.06% on this same data, so
  some of it is fitted. It needs an out-of-sample month before it means
  anything.

## Next

Run it forward on August, which is out of sample for every number above.
