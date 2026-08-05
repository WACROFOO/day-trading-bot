# The regime filter does not work, and neither does the strategy

`2026-08-oos-march-2024.md` concluded that v2 was "a bet on the regime, not an
edge in a rule", and proposed measuring the regime in advance: compute the
trailing MFE/|MAE| of the qualifying population and deploy only when it is
favourable.

Tested. **The regime is not persistent, the filter adds nothing, and on a full
894-session history the underlying strategy has no edge at all.**

## Data

Daily bars for **2,410 symbols, Dec 2022 → Aug 2026, 2.03 million bars**.
Universe rebuilt each session under the same gates — open $2–20, gap ≥10% vs
the prior close, split days excluded — giving **8,828 qualifying symbol-days
across 894 sessions**.

Intrabar sequence is unavailable this far back, so brackets are reported as
bounds: pessimistic assumes the stop filled first when both levels traded,
optimistic assumes the target did. **11% of trades touched both**, so the two
bounds differ materially and the truth is between them.

## The population, over four years

| year | sessions | names | med MFE | med MAE | ratio | closed green | mean open→close |
|---|---|---|---|---|---|---|---|
| 2022 | 20 | 135 | +1.39% | −11.75% | 0.12 | 22% | **−6.25%** |
| 2023 | 229 | 1,641 | +2.12% | −10.00% | 0.21 | 27% | **−3.35%** |
| 2024 | 250 | 2,274 | +4.58% | −10.28% | 0.45 | 31% | **−2.09%** |
| 2025 | 247 | 2,818 | +6.00% | −10.71% | 0.56 | 33% | **−1.60%** |
| 2026 | 148 | 1,960 | +7.21% | −11.66% | 0.62 | 31% | **−3.02%** |

**Buying gappers at the open and holding has negative mean return in every
year measured, and 67–78% of them close red.** The MFE/|MAE| ratio trends
upward rather than cycling — which already makes a trailing filter unlikely to
find anything to time.

## 1. The regime is not persistent

Trailing-N average of each metric against what happens next:

| lookback | ratio → next ratio | ratio → next strategy return | green% → next return |
|---|---|---|---|
| 5 | +0.031 | +0.054 | +0.098 |
| 10 | +0.053 | +0.041 | +0.073 |
| 20 | +0.054 | +0.030 | +0.051 |
| 40 | +0.093 | +0.085 | +0.085 |
| 60 | +0.082 | +0.080 | +0.089 |

Best case r ≈ 0.09, explaining **under 1% of variance**. Yesterday's regime
does not tell you today's. There is nothing to filter on.

## 2. The filter, run anyway

Trade only when the trailing-20 ratio clears a percentile threshold:

| threshold | sessions | mean (pessimistic) | mean (optimistic) |
|---|---|---|---|
| always trade | 874 | −4.23% | −1.91% |
| ≥ q25 (0.44) | 656 | −4.08% | −1.60% |
| ≥ q50 (0.62) | 437 | −4.17% | −1.47% |
| ≥ q75 (0.80) | 219 | −3.98% | −1.29% |
| ≥ q90 (0.98) | 88 | −4.44% | −2.46% |

Every threshold is negative on both bounds. The most selective one is the
worst. **The filter does not work because there is nothing for it to detect.**

## 3. The strategy itself, over 894 sessions

| | mean | median |
|---|---|---|
| sell at close | **−2.44%** | −4.88% |
| open → high | +13.76% | **+5.09%** |
| open → low | −12.64% | −10.64% |

31% of qualifying names close green.

| stop / target | pessimistic | optimistic |
|---|---|---|
| −15 / +8 (the v2 rule) | −4.13% | −1.70% |
| −10 / +10 | −3.78% | −0.95% |
| **−6 / +20** | −2.52% | **+0.24%** |
| −8 / +6 | −4.13% | −0.68% |

**The single best cell, on the unachievable optimistic bound, is +0.24%.**

## Why the excursion cannot be harvested

The number that mattered in the v2 report was mean MFE of +16%. Over the full
history that mean is **+13.76% — but the median is +5.09%.**

The favourable excursion is a **fat right tail, not a typical outcome.** To
capture the mean you must hold for the tail; holding is precisely what turns
−4.88% median into the loss. Any target close enough to be hit reliably
(+5–8%) is too small to pay for the −10.64% median drawdown on the ones that
fail, and any target large enough to matter is hit too rarely.

That is the whole strategy in one line, and it is why every variation tested —
score-weighted, equal-weighted, bracketed, trailed, laddered, time-stopped,
regime-filtered — lands in the same place.

## Where this leaves the July 2026 result

v2's +2.18% per trade came from 55 symbol-days in a single month. Against 8,828
symbol-days it is an island, and 2026 as a whole has a mean open→close of
**−3.02%**, the second worst year in the sample. The July window was not even
representative of its own year.

## What is actually established

1. **Nothing predicts open→close.** Confirmed in July 2026, March 2024, and now
   across 894 sessions. The pillar score's failure was never a sampling fluke.
2. **The favourable excursion is real but skewed** — mean +13.76%, median
   +5.09%.
3. **Buy-the-open on gappers is negative in every year measured**, before costs.
4. **The regime is not forecastable** from its own history at any lookback
   between 5 and 60 sessions.

## What this does not rule out

Everything that needs intraday information, which is the entire actual
strategy. All of the above tests a *daily* proxy: enter at the open, exit on
levels. The documented method enters on a micro-pullback after a confirmed
move, on a chart our data cannot represent, with an exit driven by Level 2 and
candle structure. **This does not show that the strategy fails — it shows that
the daily-bar version of it fails**, and that no amount of exit tuning or
regime filtering rescues a daily-bar entry.

The blocker is unchanged and now better quantified: sub-minute data.
