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
