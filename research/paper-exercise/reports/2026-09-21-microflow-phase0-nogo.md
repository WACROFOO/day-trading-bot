# Phase 0 — the 10-second micro pullback: **NO-GO**

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

It is. Not by a narrow margin.

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
on these names is two cents. **The round trip costs 0.41 R before the trade
is right or wrong.**

The strategy's own best case is +0.25 R per trade. A cost of 0.41 R leaves
**−0.159 R**, every time, on the median setup.

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
  any other universe or any other day.
- The quote is the last tick at or before the dip, **not the quote at a fill**.
- No fill, no slippage, no partial fill, no commission is modelled — every one
  of which makes the number worse, none better.
- A halt inside a dip is not detected. The `halts` table has been empty for
  six sessions and that remains unexplained.
- This says nothing about whether the 1-minute first pullback works. It says
  the 10-second version of it cannot clear its own transaction cost.

## 7. Verdict

**NO-GO. Phase 1 is not built.**

The pre-registered stop condition fired on the first session of captured tape:
the median dip is inside the spread by a factor that no gate setting recovers.

Phase 0 cost three days and one module. It was written to be able to say this,
and saying it is the whole return on it.

**What survives:** `bars_10s` and the capture path stay — 10-second candles are
a genuine instrument and cost nothing to keep. `microflow/` stays as the
measurement, and `measure.py` can be re-run on any later session in one
command. What is abandoned is the *entry idea*: that a pause inside a pushing
1-minute candle is a tradeable trigger on small caps at this spread.

**Where the attention should go instead:** the exit rule. The controls in the
same ledger say the 2 R target forfeits the tail that carries the whole
distribution (`exercise.py report`, 2026-09-21: strategy mean +0.461 R against
hold-to-close +6.301 R on the same 199 rows). That is a much larger effect than
anything a finer entry resolution was ever going to produce.

---

*No ticket was issued. Paper account only. The 894-session replication of this
strategy was negative expectancy; this measures selection and cost, never edge.*
