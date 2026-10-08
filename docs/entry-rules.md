# Every rule between a moving stock and a paper order — 2026-10-06

```
SOURCE · the code at the commit that adds this file: src/momentum_platform/pullback.py (the detector),
         src/momentum_platform/cascade.py (the gates), src/execution/intent.py and src/execution/runner.py
         (the refusals and the order; since 2026-10-08 their arithmetic lives in
         src/momentum_platform/order_math.py, which the desk's order panel reads too).
         Thresholds: knowledge-base/strategies/FILTERS.md wins any disagreement.
! A rule listed here as OFF or display-only places nothing. Changing any rule goes through
  docs/preregistration.md and a test first.
```

The order is the order the code applies them. A stock must clear every row of
stages ① to ③; the first failure decides what the log says.

## ① The detector arms a plan — `pullback.py`, on each completed 1-minute bar

| # | rule | value | origin |
|---|---|---|---|
| 1 | impulse | ≥ 2 consecutive green 1-minute bars (close > open), the last 6 kept | our approximation (the code says so). A one-bar impulse was tested 2026-10-06 and lost more (`detector_variants_output.txt`) |
| 2 | impulse size | the push spans ≥ 2 % from its first open to its high | our approximation |
| 3 | pullback | starts on the first bar that is not green (close ≤ open); 1 to 4 bars | FILTERS.md: "one red candle is enough for the pullback" |
| 4 | pullback holds | a pullback low under the impulse's low resets the search | — |
| 5 | trigger | the first bar to trade above the previous bar's high | FILTERS.md Layer 2, "the first candle to exceed the previous red candle's high … intrabar" |
| 6 | levels | entry = that high + 1¢ · stop = pullback low − 1¢ · reference target 2 R | — |
| 7 | volume flag | pullback mean volume < impulse mean volume, recorded on the plan | FILTERS.md `pullback_volume < impulse_volume` |
| 8 | after a plan | the machine waits for the plan's stop or 2 R target before searching again | known blind spot (IPDN 08:13). Searching at once was tested 2026-10-06 and lost more |

## ② The cascade judges the name — `cascade.py`, on the same bar

Layer 1 kills: the first failure rejects the name, and no plan is published.

| gate | rule |
|---|---|
| feed | a stale feed: no verdict |
| 1 price | $2.00–20.00 (`PRICE_MIN`, `PRICE_MAX`) |
| pillars (A5) | ≥ 4 of 5: price in band · up ≥ 10 % · RVOL ≥ 5× · float < 20 M · news today (an unknown counts as a fail). "News today" = the company's own headline after 16:00 ET of the previous trading day; roundups, reaction pieces, offerings and unread SEC filings do not count (fixed 2026-10-08: the date was never applied before) |
| 4 still rising | ≤ 25 % off the day's high (`FADE_MAX_PCT`) |
| 5 reverse split | the split test ran and the ratio is a clean integer → kill. Untested reads UNKNOWN, a warning |
| 6 instrument | IBKR's contract details say fund or ETF (the 2026-10-05 wiring maps ETNs, warrants, units and preferreds there too) → kill |
| 7 tick size | quoted in increments of 5¢ or more at this price → kill |
| 8 buyout | the company's own headline today says it is being acquired / going private → kill |
| halt | halted → WAIT |

Layer 2 does not kill; it decides WAIT, WATCH or REVIEW.

| gate | rule |
|---|---|
| VWAP | price above session VWAP (from 04:00, pre-market volume included) |
| 9 EMA | price above the 9 EMA of 1-minute closes (needs 9 bars) |
| MACD | 12/26/9 histogram > 0 (needs 35 bars since 04:00, or it is UNKNOWN) |

**Verdict:** a chart gate red → WAIT · a chart gate uncomputable → WATCH · outside the session window → LOG · all green → REVIEW.
Layer 3 only warns: session volume < 1 M, RVOL < 1.5×, pre-market volume > ~1 M.

## ③ The runner refuses or sends — `intent.refusals` and `Runner._act`, in this order

| # | refusal | value |
|---|---|---|
| 1 | the cascade forbade a plan (Layer 1 kill) | — |
| 2 | levels: a trigger and stop that are prices, stop below trigger, sub-penny | — |
| 3 | size: shares = $40 ÷ ((entry limit − stop) + spread + 1¢), A18 · no more than the account ($2,000) · planned risk ≤ 1.05 × $40 | A18, 2026-10-06 |
| 4 | clock: no new entry after 11:20 (A8), none after 11:30 | `ENTRY_CUTOFF`, `HARD_STOP` |
| 5 | session: regular hours 09:30–16:00 or pre-market **07:00**–09:30; before 07:00 refused | `PREMARKET_START`. A 04:00 start was tested 2026-10-06 and lost (436 trades, −0.29 R net) |
| 6 | the bar closed more than 120 s before the runner saw it | `max_age_s` |
| 7 | pre-market: allowed by phase C, the probe verdict and A1 | `policy.premarket_allowed` |
| 8 | the plan was armed on history loaded at start (backfill) | — |
| 9 | exercise phase A is log-only | — |
| 10 | the day is locked: −3 R, 3 losses in a row (scratches skipped), or 6 orders | `src/journal/risk.py` |
| 11 | the broker's positions disagree with the ledger | — |
| 12 | one position at a time | preregistration §2 |
| 13 | Layer 2: pullback volume not lighter than the impulse | FILTERS.md |
| 14 | Layer 2: the verdict is not REVIEW (VWAP, 9 EMA or MACD red or unknown). A MACD still inside its 35-bar warm-up is named as such: B30, OFF | 2026-10-06 |
| 15 | A13: stop ≥ 2 % of price · price ≥ $2 | `SELECTIVE_*` |
| 16 | a fresh desk quote exists (≤ 30 s) | — |
| 17 | A6: the stop is at least 4× the bid-ask spread | `SPREAD_K` |

## ④ The order — A10

| session | how |
|---|---|
| regular | a buy stop-limit at the trigger, limit + 0.3 % (1¢ minimum), bracketed with the stop, cancelled after 3 minutes unfilled |
| pre-market | the runner checks every 5 s and sends a limit only when the ask sits between the trigger and the +0.3 % limit, for up to 3 minutes; an ask that ran past is not chased (re-anchoring tested 2026-10-06: −0.008 R a plan) |

The exit is the A3 trail: the stop rises to the high since the fill minus 1 R, never down. Everything is flat by 11:30.

## What is shown and never ordered

EXTENDED and 5-MIN PB (the 5-minute state, E1 failed) · the green-run log (setup S, failed) · B30, the MACD warm-up, OFF · RA, re-anchoring a run-past entry, failed.
Each is scored every day by `scripts/daily_review.py` toward 200 prospective trades.
