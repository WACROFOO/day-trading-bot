# V11 — merging V9.12 with the V10 correction set

## What happened

V10 was written clean-room. I searched this repo for Pine sources, found none,
and built a 516-line strategy from `PARAMETERS.md`. That search was wrong: the
V9 lineage lives on `claude/playbook-pullback-explanation-tg5c33` in
`knowledge-base/tradingview/ross-fp-v4.pine` — 2,774 lines, revision **V9.12**,
carrying an audit history from V6 onward including the answers to a 20-finding
external adversarial audit.

So V11 is **V9.12 with V10's corrections ported in**, not a merge of equals.
Rebasing onto the 516-line file would have discarded thousands of lines of
audited work to gain a handful of rules.

## Where each side was ahead

Reviewing both against `PARAMETERS.md` line by line, V9 was **better** in five
places, and those were kept untouched:

| Area | V9.12 | V10 | Kept |
|---|---|---|---|
| Protective exits | pre-staged with the entry; the entry bar is never naked | added late, then fixed | **V9** |
| Sizing basis | `risk + 2 × slippage` per share | structural risk only | **V9** |
| Support tolerance | `max(% of price, ATR × k)` | one tick | **V9** |
| Exit legs | whole shares, 1-share position skips T1 | fractional on odd counts | **V9** |
| Venue realism | halt-band veto, supported-market gate, RVOL-at-time, no fictional pre-market fills | none | **V9** |

The sizing row is the one worth dwelling on. V10 independently derived that
round-trip costs are ~0.62R against §5's $0.08 stop and reported it as a
finding — while still sizing on structural risk alone. V9 had already drawn the
conclusion and *applied* it (`effRiskPerShare = candidateRisk + slipPerShare`,
its V6 finding 14). Same insight; V9 acted on it.

## What V11 adds

Seven gaps, each input-gated and defaulting ON. Turning all of them off
reproduces V9.12 exactly.

### 1. §3 confluence became a gate

V9 computed `supportCount` and spent it **only** on the display-only quality
score. A dip that stopped at no level at all could still arm. §3 is explicit —
`confluence_min = 2`, "not one, two" — and it is the tightest condition in the
whole entry gate.

### 2. Two confluence components V9 lacked

The 200 MA, and the flipped level (resistance broken, now retested from above).
The flip requires the level to have **actually been exceeded** since it formed;
testing only "price is near a prior high" is a tautology that counts every
nearby swing high and inflates the count. That exact tautology was a live bug
in V10 and is not reproduced here.

### 3. §3 pullback index

V9 gated `pullbackBars` — how many *bars* the dip lasts. That is a different
rule from §3's `pullback_index <= 2`, which is *which dip of the current leg*
this is. The counter resets on a new high of day, a VWAP break, and a close
under the prior dip low. Without those resets it climbs all session and the
gate can never open — a failure indistinguishable from a selective strategy
from the outside, and one that cost two debugging passes in the Python engine.

### 4. §7 participation cap

A third bound beside risk and capital. V9 capped by `maxPositionValue`, which
makes a position *affordable* but not *fillable*: on a sub-20M float the order
does not exist at any price. §7 concedes it directly — "fill quality degrades
with size on sub-20M float. The edge does not scale linearly." In the Python
engine, adding this moved a synthetic run from +50% to +1.3%.

### 5. §8 daily risk limits — absent from V9 entirely

All five rules, plus §7's daily trade cap. One structural point took a
reproduction to find:

The 20% drawdown walkaway is **account scope** and must be evaluated first and
independently of the four daily latches. Chained behind them it is close to
unreachable, because a 20% account drawdown is always assembled out of days
that trip the 6% daily loss or green-to-red first — those consume the branch
and the walkaway never records:

```
high-water mark 100,000; day opens at 85,000; equity falls to 79,800
  daily loss    =  6.12%  (limit 6%)   -> fires first, chain exits
  acct drawdown = 20.20%  (limit 20%)  -> never evaluated
  walkaway recorded? False
```

The account is a fifth underwater and trades again the next morning.

§8 counters also count **round trips**, not `strategy.closedtrades`, which
increments on every partial exit — a T1 scale plus a runner books two "trades"
for one position, so a single winner would exhaust the daily budget.

### 6. Two §6 hard exits V9 scored but never acted on

`toppingTailWarning` existed and fed the display-only score; §6 lists a large
topping tail as a hard exit. Stalling momentum (three up bars with contracting
range) is the other. Both route through V9's **single flatten flag** — competing
`strategy.close` calls firing two different stories in one execution was a
defect V9 had already fixed, and adding a third close would have reintroduced it.

### 7. §6 ladder 50/25/25

V9 sold half at 1R and ran the rest. §6 specifies 50 / 25 / 25. The middle rung
respects V9's whole-share discipline: below 4 shares the ladder collapses back
to two legs.

## What is still not true of V11

- **It has never been compiled.** Written and checked statically — declaration
  order, balanced delimiters, no identifier used before it exists. Paste it
  into the TradingView editor before trusting it.
- **§1's float and catalyst pillars remain unevaluated.** They need outside
  data. `pillarScore` tops out below 5 and §1's `min_pillars_to_trade = 5` is
  not verifiable from a chart.
- **No result is claimed.** No market data reached the environment this was
  built in, so nothing here has been measured on real bars.
