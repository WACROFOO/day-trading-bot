# Phase 0 — the 10-second micro pullback: **poor initial execution feasibility; development paused**

> **Corrected 2026-09-21 evening (external review, item 7).** The first
> version of this report said the plan's pre-registered stop condition —
> *"if the median dip is inside the spread, stop here"* — had fired "not by a
> narrow margin". It had not. Dip depth and stop distance are the same
> quantity here (`Dip.risk_per_share = trigger − dip_low`), so a dip is
> inside the spread when spread ÷ risk ≥ 1. The measured median is
> **0.4091**: the median dip is about two and a half spreads deep, outside
> the spread. What did fire is the second, independent condition in
> `measure.verdict`: fewer than 10 % of quoted dips clear k = 8 (2 of 37).
> The verdict is renamed accordingly and the two conditions are now printed
> separately by `scripts/microflow.py measure` ("dips INSIDE the spread: n /
> quoted"). The economics below are unchanged and still serious; what
> changed is which sentence they support.

**PROVENANCE** · `data/journal.sqlite`, table `bars_10s` · 10,320 ten-second
candles across 13 symbols, 2026-09-18 11:23:50Z → 15:31:30Z (one session,
07:23–11:31 ET) · measured by `python3 scripts/microflow.py measure` on
2026-09-21 05:05 ET · thresholds fixed in `src/momentum_platform/microflow/measure.py`
before any data existed.

> ⚠ **No order was placed and no trade was simulated.** This measures the
> shape of the tape and the cost of crossing the spread against it. Nothing
> here is a claim about profit.

---

## 1. What was asked, and what was answered

`docs/PLAN-10s-micro-pullback.md` §4 made Phase 0 a two-session feasibility
check with one question able to end the project:

> *"distribution of 10-second dip depth, in cents and in spread multiples —
> sets `k` in M5; **if the median dip is inside the spread, stop here**"*

It is not: median spread ÷ dip 0.41 means the median dip is outside the
spread. The pause rests on the k-survival line (§4), not on this condition.

## 2. The funnel

```
10,320 ten-second candles · 13 symbols · one session
│
└─  40 micro-pullback shapes found
    │   shape only — no Layer A context gate applied, so this is an
    │   UPPER BOUND. Filtering can only reduce it.
    │
    ├─  3 carry no quote          UNKNOWN, never assumed zero
    └─ 37 carry a quote           the measurable population
```

## 3. The number that decides it

| | median | p25 | p75 | min | max |
|---|---:|---:|---:|---:|---:|
| risk per share | **$0.05** | $0.03 | $0.14 | $0.01 | $0.40 |
| spread ÷ risk | **0.4091** | 0.25 | 0.6667 | — | 4.75 |

A 10-second pullback puts the stop a **nickel** under the trigger. The spread
on these names is two cents. **The round trip costs 0.41 R on the median
setup before the trade is right or wrong.**

The strategy's own best case is +0.25 R per trade. That figure is derived,
not measured: 50 % wins on the half-at-1 R / half-at-2 R ladder, so over 50
trades 25 × +1.5 R and 25 × −1 R = +12.5 R, +0.25 R per trade before costs
(`knowledge-base/strategies/MICRO-PULLBACK-SPEC.md` §Sizing). A cost of
0.41 R leaves **−0.159 R** on the *median* setup. Two things that sentence
does not say: a median cost is not the expected cost of the subset a gate
would select (at k = 4 the qualifying dips cost at most 0.25 R and some cost
less), and no context gate was applied, so the population is not the one a
detector would trade. The arithmetic bounds the idea; it does not close it.

## 4. Survival by gate

`k` is how many times the stop must exceed the spread.

| k | spread at most | dips surviving | | what the round trip costs |
|---:|---:|---:|---:|---:|
| 2 | 50% | 22 / 37 | 59.5% | 0.500 R |
| 4 | 25% | 9 / 37 | 24.3% | 0.250 R |
| 6 | 17% | 4 / 37 | 10.8% | 0.167 R |
| **8** | **12%** | **2 / 37** | **5.4%** | **0.125 R** ← in force |
| 10 | 10% | 1 / 37 | 2.7% | 0.100 R |
| 20 | 5% | 1 / 37 | 2.7% | 0.050 R |

**Loosening `k` does not rescue it, and that is the important line.** At k=4
the cost is 0.250 R — the entire best case, spent on the spread. At k=2 it is
0.500 R, double the best case, and two thirds of the setups still fail. There
is no value of `k` at which this universe pays: a gate that lets more trades
through only lets through trades that cost more than they can win.

## 5. Why this is not a filtering problem

The 40 shapes were counted with **no context gate applied** — no VWAP, no
9 EMA, no MACD, no impulse check. Adding them can only remove setups, and
nothing about those gates selects for a *wider* stop. The population that
survives them is a subset of a population that already fails.

## 6. What this does not establish

- **One session, 13 symbols, 37 quoted dips.** Small, and not a claim about
  any other universe or any other day. The 37 dips are not 37 independent
  observations: they come from 13 names on one morning, several from the
  same push, and one wide-spread name contributes many of them.
- The quote is the last tick at or before the dip, **not the quote at a fill**.
- No fill, no slippage, no partial fill, no commission is modelled — every one
  of which makes the number worse, none better.
- A halt inside a dip is not detected. The `halts` table has been empty for
  six sessions and that remains unexplained.
- This says nothing about whether the 1-minute first pullback works. It says
  the 10-second version of it cannot clear its own transaction cost.

## 7. Verdict

**Poor initial execution feasibility; development paused. Phase 1 is not
built.** The plan's second session of capture is kept: `bars_10s` costs
nothing to record and `measure` re-runs in one command, so the pause is
re-read after session two rather than declared closed on one.

The pre-registered median-dip condition did **not** fire (0.41, see the
correction at the top). The k-survival condition did: 2 of 37 quoted dips
clear k = 8, and at every lower k the spread's cost meets or exceeds the
best case. On one session that is a reason to build nothing yet, not a
rejection of every filtered version of the idea.

**Session two, read 2026-09-21 evening (tape 2026-09-18 → 2026-09-21,
28,708 candles, 28 symbols, 104 shapes, 80 quoted):** spread ÷ risk median
0.3333; dips inside the spread 15 / 80 (18.8 %); 7 / 80 clear k = 8 (8.8 %);
verdict NO-GO on the k-survival line, stop condition not fired. Same answer
as session one, on a tape twice the size. The pause stands.

Phase 0 cost three days and one module. It was written to be able to say this,
and saying it is the whole return on it.

**What survives:** `bars_10s` and the capture path stay — 10-second candles are
a genuine instrument and cost nothing to keep. `microflow/` stays as the
measurement, and `measure.py` can be re-run on any later session in one
command. What is abandoned is the *entry idea*: that a pause inside a pushing
1-minute candle is a tradeable trigger on small caps at this spread.

**Where the attention went next:** the exit rule, as a hypothesis. The
controls in the same ledger put the simulated 2 R target at +0.461 R against
a stop-less hold-to-close at +6.301 R on the same 199 rows (`exercise.py
report`, 2026-09-21) — 192 of them cascade-killed, zero fills, micro-cent
stops, no uncertainty estimate. Amendment A3 tests it forward with the
fixed-target rule simulated beside it; nothing here shows which exit is
better.

---

*No ticket was issued. Paper account only. The 894-session replication of this
strategy was negative expectancy; this measures selection and cost, never edge.*
