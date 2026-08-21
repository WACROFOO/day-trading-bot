# V10 corrections

Every change in `ross_momentum_v10.pine` traces to a defect found by *running*
the Python replay engine, not by reading it. Each entry gives the symptom, the
root cause, and where the fix lives on both sides.

The distinction that matters throughout: **a rule that is correctly implemented
and still loses money is a result about the strategy, not a bug.** Those are
recorded as findings and the parameters are left alone (§12.3). Only the rows
marked *defect* changed behaviour.

---

## FIX-1 — the pullback counter never reset · defect · §3

**Symptom.** `pullback_index_ok` passed on **0 of 348** decisions. The run
reported zero trades and looked clean.

**Cause.** The counter incremented on every dip from the session open onward and
never reset, so by 09:35 it was far past 2 and the §3 gate could not open. A
gate that can never open is indistinguishable from a selective strategy when you
only look at the output.

**Fix.** The counter means "pullbacks since *this move* began", so it resets on
a new high of day (a new leg), on a VWAP break (§5 hard invalidation), and on a
close under the prior dip low (the leg broke).

`replay.detect_pullback` · Pine `[FIX-1]`

---

## FIX-2 — the trigger candle destroyed the evidence needed to judge it · defect · §3/§4

**Symptom.** Setups that visibly satisfied §3 were rejected with
`pullback_volume>=impulse` on the exact bar that should have triggered.

**Cause.** §4's trigger *is* the candle that ends the pullback. By the time the
break happened, the dip was over and its low and volume were gone — so the §3
"pullback on lighter volume" test had nothing to measure precisely when it was
needed.

**Fix.** Python freezes the resolved dip and carries it with its own index.
Pine avoids the problem entirely: the impulse statistics are frozen when the dip
*begins*, the gate is evaluated *during* the dip, and the entry is a resting
stop order at the prior candle's high. That ordering matches the playbook —
Step 3 confirms the chart, Step 4 waits for the trigger — and cannot repaint,
because the order fills on a real break rather than on a decision made after it.

`replay.detect_pullback` (`just_resolved`) · Pine `[FIX-2]`

---

## FIX-3 — position size ignored buying power · defect · §7

**Symptom.** 6,249 shares of a $5.08 stock on a $25,000 account: $31,745 of
stock in a cash account with no margin.

**Cause.** §7 sizes purely from risk (`risk_budget / risk_per_share`). With the
$0.08 stop §5 asks for, that formula returns more shares than the account can
pay for.

**Fix.** Size is capped by cash as well as by risk.

`replay.size_position` · `portfolio.simulate` · Pine `[FIX-3]`

---

## FIX-4 — position size ignored the tape · defect · §7

**Symptom.** With the cash cap in place, every trade still deployed **100% of
equity** — 15,000–24,000 shares of a $5–7 small cap — and the synthetic run
returned **+50% in five sessions**.

**Cause.** No liquidity constraint. On a sub-20M float those fills do not exist
at any price. §7 concedes the point in its own text: *"fill quality degrades
with size on sub-20M float. The edge does not scale linearly."* A backtest
without this cap reports P&L on shares that were never buyable.

**Fix.** Size is also capped by participation — a share of the tape, default 10%
of trailing median minute volume. On the same fixture the return fell from
**+50% to +1.3%**. That gap is the entire difference between a fantasy backtest
and a plausible one, and it is invisible unless you look at notional per trade.

`replay.size_position` · `portfolio.Config.max_participation_pct` · Pine `[FIX-4]`

---

## FIX-5 — support tolerance had no floor · defect · §3

**Symptom.** Confluence never fired on low-priced names.

**Cause.** §3 specifies `tolerance_floor: spread`, which was unimplemented.
0.25% of a $2.00 stock is $0.005 — **half a tick**. No level can match a window
narrower than the minimum price increment except by exact equality, so the gate
was unreachable across the bottom of §1's $2–$20 range.

**Fix.** Tolerance is floored at one tick, standing in for the spread that free
OHLCV cannot supply.

`replay.support_reasons` · Pine `[FIX-5]`

---

## FIX-6 — §8 was not implemented at all · defect · §8

**Symptom.** Losing days compounded instead of stopping.

**Cause.** The per-symbol replay had no concept of an account, so none of §8's
five limits existed: max daily loss, giveback of peak gain, green-to-red,
consecutive losses, drawdown walkaway.

**Fix.** A portfolio layer enforces all five, latching for the day and releasing
on the next session. Signals arriving after a lock are recorded as blocked and
priced, not silently dropped — §8 shaping the day *is* the strategy working, and
the cost of that discipline should be visible.

`portfolio.risk_check` · `portfolio.simulate` · Pine `[FIX-6]`

---

## FIX-7 — floor division silently dropped a share · defect · arithmetic

`2000 // 0.10` evaluates to `19999.0`, not `20000`, because 0.1 has no exact
binary representation. Sizing lost a share, and the error scales with position
size. Now computed as `int(budget / risk + 1e-9)`.

`replay.size_position`

---

## FIX-8 — missed opportunities were overcounted ~8× · defect · reporting

**Symptom.** "530 winners blocked" out of 1,208 decisions.

**Cause.** Every candle inside a single move resolves profitably, so one
opportunity was counted once per candle. The opportunity-cost table was
inflated by roughly an order of magnitude, which would have made any gate look
catastrophically expensive.

**Fix.** Missed winners collapse into non-overlapping opportunities before
anything is counted; recall is reported on that basis, with the raw candle
figure shown alongside so the two are never confused.

`report.distinct_missed`

---

---

# Second pass — defects found by adversarial audit

Three independent audits of `replay.py` (leakage, spec fidelity, execution
realism) produced 29 candidates. Several were found by more than one auditor
working separately, which is the signal worth trusting. Each was reproduced
before being fixed.

## FIX-9 — flipped_level was a tautology · defect · §3 · **both engines**

`abs(price - level) <= tol and price >= level - tol` — the second clause
follows from the first, so it tested nothing. Every nearby swing high counted
as a "flipped level" and confluence was inflated, which matters because
confluence ≥ 2 is the §3 gate's tightest condition.

§3 means resistance that was **broken** and is now being retested from above.
Both engines now require the level to have actually been exceeded since it
formed. Pine tracks a pending pivot and promotes it only once price trades
through it.

`replay.support_reasons` · Pine `[FIX-9]`

## FIX-10 — §5 stop_min_distance was unimplemented · defect · §5

§5 sets a floor of the spread width on the stop. Without it a sub-tick stop
produces an enormous share count from `risk_budget / risk_per_share`.

## FIX-11 — the scale ladder was 50/50, not 50/25/25 · defect · §6

§6 scales 50% at target_1, 25% at the next level, and trails 25%. Both engines
sold half and dumped the rest on the first hard exit — which understates the
runner and misrepresents where R actually comes from. §5's `+$0.10` breakeven
arm was also missing; only the after-first-scale arm existed.

## FIX-12 — two §6 hard exits were missing · defect · §6

§6 lists six. Four were implemented. "Large topping tail" (upper wick > 2× body
and > half the range) and "green candles shrinking / momentum stalls" (three up
bars with contracting range) are both computable from OHLCV, so leaving them
out was an omission rather than a data limit. Also `high_volume_red` divided by
an average that **included the current bar**, making the signal impossible on
the first bars and too strict right after.

## FIX-13 — §8's drawdown walkaway released overnight · defect · §8

The 20% walkaway stops the *account*, not the day. Resetting it with the daily
latches let the deepest drawdown of the run trade straight through. It now
persists until explicitly cleared.

`portfolio.simulate` · Pine `[FIX-13]`

---

# Python-only defects

These could not occur in Pine, which is worth saying plainly — the Pine
implementation is structurally safer in these two respects.

## The exit model ran on fabricated indicator values · critical · §5/§6

`resolve()` computed VWAP and MACD on a slice **beginning at the entry bar**.
VWAP is cumulative from the session open, so re-seeding it makes it equal that
bar's own typical price; MACD's histogram restarts at exactly 0.0.

Measured on a monotonic 5.00 → 6.00 ramp, at the entry bar: full-session VWAP
**5.2564**, re-seeded VWAP **5.5128**. `close < vwap` flips from false to true —
so a **rising** stock fires a `vwap_break` exit on the first bar it is held. The
entire §5/§6 exit model was running on invented numbers.

Pine's `ta.vwap` is session-anchored by construction and cannot be re-seeded
this way.

## Other execution defects

- **§2's 11:30 hard stop was never enforced on exits.** Positions ran to the end
  of the fetched frame — 20:00 with premarket data — so an 11:29 entry could be
  held all afternoon and scored on whatever the close did. Pine flattens at the
  window edge.
- **The entry candle was never inspected.** Management began at `cursor + 1`, so
  a fill that reversed through its own stop inside the entry minute was recorded
  as an untouched winner with `mae_r = 0`. Pine's broker model checks intrabar.
- **Gaps through the stop filled at the stop.** Every loss was capped near 1.2R
  regardless of how far the bar opened below it.
- **§6's target read the trigger candle's own high**, which only prints once that
  bar closes — after the fill price is already fixed. A minute of hindsight
  handed to the reward:risk test.
- **SKIP counterfactuals were priced under different rules than TAKEs** (flat 2R
  target, uncapped size), so precision and recall measured different things and
  could not be compared. Both now route through one `order_params`.
- **§9's breakeven win rate was hard-coded** to `1/(1+2.0)`. Scaling half at
  target_1 caps upside well below 2R while a stop still costs a full R plus
  costs, so a losing system could be reported as clearing breakeven. It now
  follows the realized reward:risk.

On the wiring fixture these changes moved the reported return from **+8.6% to
+1.1%**, with exits finally firing on real values.


---

# Third pass — timing leaks found by self-review

## FIX-14 — the resting order's terms were re-derived at fill time · defect · Pine only · §5

When a resting stop order fills, Pine is on a **later bar**, by which point
`entryPrice`, `stopPrice` and `riskPerShare` have all been recomputed from that
bar. The position was then managed against a stop it was never sized against —
and if the dip state had moved on, against a stop belonging to a different
pullback entirely.

The order's terms are now latched when it is **placed** and read back on the
fill. The Python engine cannot have this bug: it decides and prices in the same
call.

Pine `[FIX-14]`

## FIX-15 — the §3 gate was judged on the trigger candle's close · defect · Python only · §3/§4

The fill is priced at the break of the **prior** bar's high — an event that
happens mid-candle. But the gate read `close`, `vwap`, `ema9` and `macd_hist`
at the trigger candle's own close, which is only knowable a minute later. The
filter therefore had information the fill did not.

It is not a subtle distortion. A dip that had **already lost the 9 EMA** could
still qualify, because by the trigger candle's close price had recovered above
it. §3 requires *holding* the 9 EMA; the old timing let setups through that had
already broken it.

The gate is now judged on the close of the last dip bar, and the current bar is
allowed to contribute one fact only: whether it took out that bar's high. This
is the playbook's own ordering — Step 3 confirms the chart, Step 4 waits for the
trigger — and it is why the same decision expresses cleanly in Pine as a resting
stop order.

`replay.evaluate` · Pine had this right by construction

### What it cost

The end-to-end fixture stopped qualifying, which is the finding rather than a
problem with the fix: it had only ever passed *because* of the leak. Its dip ran
from 5.30 to 5.03 and was below the 9 EMA at the moment the order would have
rested. Under honest timing it is not a §3 setup.

A replacement had to satisfy both §3 conditions **simultaneously** — the dip
lands on a level *and* is still holding the 9 EMA when the chart is confirmed.
Those coexist only in a narrow band, and a scan of 36 candidate geometries found
8. The one now in the suite: an impulse topping at 5.50, a dip confirming that
pivot, a second leg breaking 5.50 so it flips to support, then a two-bar
light-volume pullback whose low returns to exactly 5.50 — half dollar, flipped
level and 9 EMA at one price. Entry 5.58, stop 5.50, risk **$0.08** (§5's stated
typical), reward:risk 2.38, confluence 3.

That difficulty is itself the result. The setup §3 describes is genuinely rare,
and any backtest finding it often is finding something else.


---

# Fourth pass — Pine review

Three lenses over the Pine source (runtime/arithmetic, repainting, spec
fidelity) produced 16 candidates; 7 survived refutation. One of them was also
live in the Python engine.

## FIX-13 was unreachable — the account walkaway queued behind the daily latches · critical · §8 · **both engines**

`accountLocked` was set only in the **last** branch of an `else if` chain, so
any of the four daily latches firing first consumed the branch and the 20%
drawdown walkaway never recorded. The Python `risk_check` had the identical
shape via early `return`s.

Reproduced exactly: high-water mark 100,000, the day opens at 85,000 (already
15% down), losses take equity to 79,800.

```
daily loss   = 6.12%   (limit 6%)   -> fires first, chain exits
acct drawdown = 20.20%  (limit 20%)  -> never evaluated
account walkaway recorded? False
```

The account is a fifth underwater and trades on the next morning. And because
a 20% account drawdown is *always* assembled out of days that trip the 6%
daily loss or green-to-red first, this was not merely fragile — the walkaway
was close to unreachable, leaving §8's only account-scope limit inert.

The account walkaway is now evaluated **first and independently**, in both
engines, because it is a different scope from the daily latches and outlives
them.

`portfolio.account_walkaway` / `portfolio.daily_limits` · Pine `[FIX-13]`

## FIX-16 — §8 counted every partial scale-out as a completed trade · major · §7/§8

`strategy.closedtrades` increments on **partial** exits, so the §6 50/25/25
ladder booked three "trades" per position. One winner exhausted §7's 2-per-day
budget while its runner was still open — delivering 0.67 trades/day against
§7's 1–2 — and a green first scale reset the consecutive-loss counter even
when the trade ended red, so §8's three-in-a-row stop could never latch on a
scaled trade. Round trips are now detected from the position going flat.

## FIX-17 — the §5 stop was not live on the candle the entry filled · major · §5

`strategy.exit` was submitted only from inside `if inPos`, which first becomes
true at the **close** of the fill bar — so no stop existed during the trigger
candle, the most volatile candle of the trade. Meanwhile that same candle's
high was allowed to ratchet the stop to breakeven. The entry candle's upside
was priced and its downside ignored.

The reviewer's walk-through: entry fills at 5.31, the bar trades down to 5.10
through a 5.12 stop, recovers, and closes 5.34 — booked as a small winner
instead of a −1R stop-out. The whole bracket is now submitted on the placement
bar and is live from the instant the entry fills.

## FIX-18 — `scale2Pct` was a dead input · major · §6

The second rung hard-coded "50% of the remainder", which equals 25% of the
original **only while `scale1Pct` is exactly 50**. `scale2Pct` was read
nowhere. Setting `scale1Pct = 40` silently produced a 40/30/30 ladder; setting
`scale2Pct = 30` changed nothing at all. The rungs are now `strategy.exit`
orders whose `qty_percent` is a share of the entry quantity, so both inputs are
read and the ladder is whatever they say.

## FIX-19 — the rungs filled at the next bar's open · major · §6

`strategy.close()` is a **market** order. A target touched intrabar was
therefore executed at whatever the next bar opened at, so the realized R was
never the R the §6 gate approved: a bar that spikes to 5.22 and closes 5.02
"scaled at target" somewhere near 5.02. A profit target is a resting limit
order and is now modelled as one.

## FIX-20 — §1 was reduced to a price band · major · §1

`priceOk` checked price alone, while §1 is explicit: *"applied before the chart
is looked at. All must pass."* Day gain ≥ 10%, RVOL ≥ 5.0, cumulative volume
≥ 500,000 and a rising rate of change are all computable from OHLCV and were
simply absent — so the strategy would arm on a flat, barely-traded stock whose
dip happened to land on a level. The comment naming only float and catalyst as
non-computable implied the rest were handled.

All four are now enforced, and `pillars_passed` is plotted to the data window
so results can be split by it as §12.3 asks. It tops out at 3 of 5: float and
catalyst genuinely need outside data and are still not evaluated.


# Findings — not fixed, deliberately

## The §6 2:1 gate structurally rejects shallow pullbacks

Every setup that passed all seven §3/§4 conditions in the wiring run was then
rejected by `reward:risk < 2.0` against a high-of-day target — at 1.05, 1.13,
1.35, 1.69 and 1.98.

This is a genuine tension inside the spec, not a coding error. §6 sets
`target_1 = high_of_day_retest` and `min_reward_risk = 2.0`. A *shallow, clean*
pullback — the highest-quality version of the setup — sits close to the high of
day and therefore has the least room to the retest. The rule prefers deeper,
uglier dips. Meanwhile an entry breaking to new highs has no HOD above it at
all and falls through to a 2R fallback target, passing the check trivially.

The threshold has **not** been touched. Per §12.3 this is investigated, not
tuned away.

## Cost drag makes tight stops more expensive, not safer

Round-trip cost is $0.05/share ($0.02 slippage + $0.005 commission, each way).
Against §5's preferred $0.08 stop that is **0.62R per trade**, so a nominal "1R"
loss is really 1.62R and §9's breakeven win rate moves from **33.3% to ~45%**.

§5 recommends tight stops on the assumption that a tighter stop means less risk.
In this cost structure the opposite holds: the tighter the stop, the larger
costs loom relative to it. This is the single most consequential number in the
whole model and it is arithmetic, not opinion.

## Four §1/§3 inputs remain untestable on free data

`tape_green` and `no_seller_wall` need Level 2; `float_max` and `has_catalyst`
need paid fundamentals and news. They are carried as UNKNOWN and never as
passing. Every reported win rate is therefore an **upper bound** conditional on
those four holding, and the Pine script marks them as the trader's manual check
rather than evaluating them.
