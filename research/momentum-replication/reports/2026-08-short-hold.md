# Shortening the hold: cuts the risk, does not create an edge

Requested: buy just before the open, sell 30 minutes after it, equal weight,
tested on every period available.

## The coverage limit, first

**A 30-minute exit needs the price 30 minutes after the open, and that requires
intraday data.** Yahoo serves 1-minute bars for the **last 30 days only**. There
is no free source for historical intraday on these names.

So this is testable on **20 sessions, 2026-07-07 to 2026-08-05, 171 qualifying
symbol-days** (152 where all four reference prints exist). **March 2024 and
everything before July 2026 cannot be tested for this at all** — the 894-session
daily history in `2026-08-regime-filter.md` has no intraday component.

Universe and gates unchanged: open $2–20, gap ≥10%, no splits. Equal weight.
Every price below is a real print, never an interpolation.

## Buying before the open costs you

| variant | mean% | median% | win% | stdev | worst% |
|---|---|---|---|---|---|
| **buy 09:29 → sell 10:00** | **−1.21** | −2.35 | 40 | 14.37 | −38.7 |
| buy 09:30 open → sell 10:00 | −1.05 | −1.29 | 42 | 12.33 | −34.3 |
| buy 09:29 → sell at close | −1.11 | −3.67 | 38 | 35.48 | −63.4 |
| buy 09:30 open → sell at close | −0.97 | −1.86 | 43 | 31.98 | −65.3 |
| **the 09:29 → 09:30 leg alone** | **−0.20** | **−1.50** | **34** | 6.70 | −13.5 |

The pre-open entry is worse than the open entry in **every** pairing, and the
isolated leg explains why: holding through the opening print is a −0.20% mean,
−1.50% median trade that is positive only 34% of the time. Whatever the gap has
to give, it has largely given by 09:30.

**Recommendation: enter at the open, not before it.** Everything below uses the
09:30 open.

## Holding period sweep

| hold | n | mean% | median% | win% | **stdev** | worst% | mean/sd |
|---|---|---|---|---|---|---|---|
| 5m | 163 | +0.33 | −1.02 | 44 | **7.48** | −15.4 | +0.045 |
| 10m | 156 | +0.63 | −1.46 | 41 | 9.11 | −21.4 | +0.069 |
| 15m | 162 | +0.06 | −1.27 | 44 | 10.79 | −23.3 | +0.005 |
| 20m | 156 | −0.98 | −2.15 | 39 | 10.46 | −23.3 | −0.094 |
| **30m** | 157 | **−0.84** | −1.50 | 41 | **12.93** | −35.3 | −0.065 |
| 45m | 156 | +0.30 | −0.98 | 46 | 18.28 | −44.9 | +0.016 |
| 60m | 162 | +0.32 | −1.15 | 44 | 18.63 | −51.4 | +0.017 |
| 90m | 155 | −1.73 | −2.43 | 38 | 17.16 | −50.4 | −0.101 |
| 120m | 155 | −0.11 | −2.66 | 38 | 27.03 | −60.2 | −0.004 |
| to close | 165 | −0.58 | −1.79 | 45 | **31.23** | −65.3 | −0.018 |

## What the sweep says

**1. The mean is noise.** It oscillates +0.33, +0.63, +0.06, −0.98, −0.84,
+0.30, +0.32, −1.73, −0.11, −0.58 with no structure. Best mean/stdev is +0.069
at ten minutes, which is indistinguishable from zero on n=156.

**2. The median is negative at every single horizon** — −0.98% to −2.68%. There
is no holding period at which the typical trade makes money.

**3. Win rate never reaches 50%** at any horizon (38–46%).

**4. Risk falls monotonically with holding time, and that is the only real
relationship in the table.** Standard deviation goes from **31.23% at the close
to 12.93% at 30 minutes to 7.48% at 5 minutes** — a 4× reduction. Worst case
goes from −65.3% to −35.3% to −15.4%.

## Verdict

**The 30-minute exit does what was hoped on risk and nothing on return.**
Against holding to the close it cuts volatility by **59%** and the worst case by
**46%**, at a mean that is statistically the same (−0.84% vs −0.58%) and a
median that is slightly better (−1.50% vs −1.79%).

That is a real improvement in the *shape* of the outcome. It is not an edge.
You are losing the same amount with far less variance, which matters for
survival but does not make the strategy profitable.

This is consistent with everything measured so far: the daily-bar entry has no
edge, and no exit — bracket, trail, ladder, time stop, regime filter, or now a
30-minute clock — has produced one.

## Caveats

- **20 sessions, 157 trades.** Nothing here is significant; the mean's sign
  flips between adjacent holding periods on the same data.
- **One month, one regime.** `2026-08-regime-filter.md` measured 2026 as having
  a mean open→close of −3.02%, the second worst of five years, so this window
  is unfavourable in a way the older data says is not permanent.
- The 30-day intraday limit is the binding constraint on ever extending this.
  It is the same blocker as the 10-second question, and it will keep being the
  answer until sub-minute history is bought.
- No commissions, no slippage, no borrow. Fractional shares assumed.
