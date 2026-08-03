# The VWAP condition — there are four of them, and our gate implements one

`PARAMETERS.md` carries VWAP as a single boolean: `require_above_vwap: true`,
n=45. The corpus does not support one condition. It supports four distinct
roles, and **one of them is the negation of the gate we implement**.

Registers checked: teaching 62/257 files (321 mentions), recaps 30/68 (83),
streams 160/289 (526).

---

## The four roles

### 1. Bias line — who is in control

> *"this is considered the equilibrium point of this instrument today… anytime
> the price is above the volume weighted average price, who's in control? The
> buyers, the bulls, strength. Anytime the price is below its equilibrium…
> the bears, the short sellers. It's weak."* — `LNDd7rf-9FU` 25:36

Live, this is the single most common use — it is how he rejects names on the
watchlist before the bell:

> *"RSLS, I like the idea, but it broke below VWAP"* — `Pnl7ItPyeUQ` 16:01
> *"the 5-minute chart being below VWAP is what gives me pause there"* — `Pnl7ItPyeUQ` 30:47
> *"TLSA… the chart to me, below VWAP, selling off… I didn't like it"* — `ZfwTJAMLroA` 33:00

### 2. Directional support / resistance

> *"when a stock is right at the VWAP and it's below it, the VWAP serves as
> **resistance**. And when the price is above it and coming down to it, the
> VWAP serves as **support**."* — `LNDd7rf-9FU` 26:24

> *"the stock should always be priced well above VWAP when it's trending
> higher… VWAP is almost always a significant area of support when the price
> is above it"* — `_fsRWw0VbS4` 49:01

This is the role our engine actually uses correctly: VWAP is one of the six
confluence components (77 mentions / 25 videos) a stop can be placed against.
Live he buys those touches directly:

> *"got a nice dip here off the VWAP… added back on a second dip of the VWAP"*
> — `Pnl7ItPyeUQ` 31:59
> *"I'm buying very close to the volume weighted average price. 1938's the
> VWAP. And now over 20 would be the add."* — `Pnl7ItPyeUQ` 20:09

### 3. **Break of VWAP — a named setup, entered from BELOW**

65 occurrences across 46 files, and its own dedicated video:
**`SCy6RrASpJY` — "The Pre-Market Break of VWAP Setup"**.

> *"I like when stocks break the VWAP and squeeze back up… **that shift is when
> the stock goes from being weak to being strong**"* — `ZfwTJAMLroA` 57:36

> *"one challenge with the break of VWAP setup is that it **inherently requires
> the stock to have gone below VWAP**"* — `SCy6RrASpJY` 08:00

The full trade plan, in his words (`SCy6RrASpJY` 07:31):

| | |
|---|---|
| **Entry** | the micro pullback as it reclaims VWAP — *"I jumped in right on that micro pullback for the break of VWAP"* |
| **Stop** | *"my stop is if we go back below VWAP"*, tightened to the nearest whole dollar if one is closer |
| **Target** | *"once we held over VWAP I wanted to see that we started squeezing back to the **pre-market high** — that's the target"* |
| **Why it pays** | *"shorts usually get confident when a stock is holding below VWAP… they're selling against this level, looking for the fade, and so they don't expect it to rip back up"* |

He is explicit that it is a second-tier setup — *"it's not my number one
favorite setup"* (`ZfwTJAMLroA` 30:09) — and that the weakness it implies is a
real cost: *"this has already shown early weakness during a time that it really
shouldn't have weakness"*.

**Our gate cannot take this trade.** `price > VWAP` is evaluated at the trigger
bar, which on this setup is at or just under VWAP by construction.

### 4. Exit / hard invalidation

`vwap_break_exit: true`, n=45, and the engine implements it (`engine20.py:189`,
`'lost VWAP'`).

> *"if the price dips down and breaks below VWAP that's almost always a high
> volume breakdown"* — `wC2Bbf6OMFQ` 09:47
> *"ISPC, I don't like it back below VWAP"* — `jNlqblruYzA` 24:34
> *"APVO breaking below VWAP, bears are in control"* — `jNlqblruYzA` 29:07

---

## Two measurements — `diagnostics/vwap.py`

168 pullback triggers, 12 July sessions, run offline from `data/bars_cache`.

### The redundancy claim is false on our data

> *"you'll almost never have an instance where you'll be below VWAP and above
> the 9 MA, that's very uncommon, **they're rarely inverted**. So by saying it
> has to be above the 9 EMA, kind of by default I'm saying it should also be
> above VWAP."* — `IwDORxvXAAs` 20:49

| | above 9 EMA | below 9 EMA |
|---|---|---|
| **above VWAP** | 68 | 27 |
| **below VWAP** | **42** | 31 |

**41% inverted. 25% of triggers sit below VWAP while above the 9 EMA** — the
exact combination he calls very uncommon. On his names, at his timeframe, the
claim may hold; on ours it does not, so the two conditions are not one
condition and cannot be collapsed.

### VWAP is the most binding gate we have

| pass rate | condition |
|---|---|
| 92.3% | cumulative volume ≥ 500k |
| 86.9% | not resumed lower after a halt |
| 82.7% | pullback_volume < impulse_volume |
| 69.6% | support confluence ≥ 2 |
| 65.5% | price > 9 EMA |
| 59.5% | MACD histogram > 0 |
| **56.5%** | **price > VWAP** |

18 setups (10.7%) clear every condition. **19 more are blocked by VWAP alone** —
dropping the gate would more than double the setups reaching the sizing stage.
Only 1 is blocked by the 9 EMA alone.

---

## The implementation discrepancy

`sim.py:154` — *"VWAP resets at the opening bell — pre-market volume is not in
it."* His does not. The dedicated setup video is a **pre-market** break of VWAP,
he quotes VWAP levels at 06:30 and 07:00, and he runs a custom calculation
rather than the platform default:

> *"I use Warrior Trading WTVWAP. This is a custom calculation that we've added
> here."* — `LNDd7rf-9FU` 27:13

We do not know what WTVWAP does differently. But a VWAP that excludes
pre-market and one that includes it are different lines on a gapper — on these
names most of the day's volume before 09:35 is pre-market — so some unknown
share of the 41% inversion above is our VWAP, not his signal.

## What should change

1. `PARAMETERS.md` should record VWAP as **four rules**, not one boolean.
2. `require_above_vwap: true` is a *bias filter*, and it excludes a setup he
   has a whole video about. It should not be a hard entry gate for a system
   that claims to replicate him.
3. Whether our VWAP should include pre-market is an open, testable question —
   the cheapest single experiment left on this gate.

Not changed yet: this report records the finding. Changing the gate changes
every P&L number in `reports/`, and per house rule 3 that needs its own audited
run, not a drive-by edit.
