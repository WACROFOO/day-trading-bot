# Buy-the-open / sell-the-close, sized by a pillar score — it does not work

Specified strategy: screen the pool near the open on the five pillars, score
each survivor 0–100, distribute €100 in proportion to score, buy the open, sell
the close. Tested over the 17 cached sessions, 2026-07-09 to 2026-07-31.

`diagnostics/score_basket.py`.

## Setup

- **Universe**: `scan20_stats.json` — every symbol scanned that morning,
  ~1,500/day across 26,107 symbol-days. Not a list of known movers.
- **Look-ahead**: scored on pre-market fields only (gap, pre-market price,
  pre-market print count, shares outstanding). `rvol5` is confirmed at 09:35
  and is therefore excluded — using it to buy the 09:30 open would be trading
  on information from after the entry.
- **Hard gates**: price $2–20 and gap ≥ 10%, because the pillars are gates
  ("all five or it is not a trade"). Scoring them purely as weights admitted
  CJMB at $1.27 and KUST at $1.76 on 75/100.
- **Score**: four pillars × 25. **Pillar 3 (news) cannot be scored** — no feed.
  So this is an upper bound on what the screen knows.

## Headline

| | total P/L | of capital | win rate | median day |
|---|---|---|---|---|
| **Score-weighted** | **+€37.48** | +2.2% | 7/17 | **−2.71%** |
| **Equal-weighted (control)** | **+€52.65** | +3.1% | 7/17 | **−1.72%** |

**The control beats the strategy.** Across a 32-cell sweep of thresholds
(40/50/60/70) and basket sizes (3/5/8/15), **equal weight beat score weight in
16 of 16 matched pairs.** The score has negative information value.

## The score is anti-predictive

| min score | best total P/L at that threshold |
|---|---|
| 40 | +€20.16 |
| 50 | +€53.31 |
| 60 | −€33.94 |
| 70 | −€62.13 |

Raising the bar makes it monotonically worse above 50. A score that identified
better trades would do the opposite. **12 of 32 settings were profitable;
median across all settings −€34.18; the median day was negative in all 32.**

## The profit is two days

Best configuration (score ≥ 50, top 5, equal weight, +€53.31):

```
without 2026-07-09 (+57.75) → total −€4.44
top 2 days                  → +€80.03  (150% of the total)
the other 15 days           → −€26.72
median day                  → −€1.37
```

**It loses money on 15 of 17 sessions.** The result is one outlier, and a
strategy whose entire return is one session in seventeen has not been shown to
work — it has been shown to buy lottery tickets.

## Why it fails, mechanically

`2026-08-05-recap.md` measured the reason on a live session: **all twelve names
watched that day closed below their session high, median give-back ≈30%, the
three biggest runners −45% to −49%.** Sell-at-the-close structurally holds
through the entire fade. The same day's basket returned +24.5% only because one
name did +227%; the other eleven made +3.7% between them.

The entry selection is not what is broken. **The exit is.** That is the same
conclusion the July calibration reached from the opposite direction.

## A data defect found on the way

`scan20_stats` carries **split-adjusted** prices; `daily20` carries **raw**
ones. Taking the entry from one and the exit from the other manufactured a
−99% on DFNS — scan open 9.21 against a daily open of 0.074, exactly its 1:125
ratio — and the first run of this backtest returned −7.2% almost entirely on
that artefact. Entry and exit now both come from the same `daily20` row, and
any symbol with a split anywhere in the window is dropped (1,731 symbol-days).

Anything joining those two files must reconcile the convention first.

## What would have to change

1. **An intraday exit.** Any rule that banks the move before the close — a
   trailing stop, a scale-out at target 1, or simply a hard exit at 11:30 —
   addresses the actual failure. Untested here; it is the next thing to run.
2. **Pillar 3.** News is unscoreable without a feed, and it is the pillar that
   separated the real setups from the traps on 2026-08-05 (four of six traps
   were visible only in filings).
3. **A longer sample.** 17 sessions and one dominant day cannot distinguish a
   small edge from noise in either direction.

## Caveat

Requested as "the last 20 days"; the cached scan covers **17 sessions ending
2026-07-31**. Extending through August would require re-scanning ~1,500 names
per day and is not done here. No commissions, no slippage, no borrow, and
fractional shares are assumed — all of which flatter the result.
