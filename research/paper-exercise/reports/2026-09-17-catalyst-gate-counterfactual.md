# Counterfactual — what the catalyst gate suppressed, 11–17 September 2026

**LEDGER** · `journal.sqlite` snapshot, 11.8 MB, uploaded by the owner
2026-09-17 · 389 decisions · 311 graded · integrity_check `ok` ·
replay 389/389 reproduce · rules hash `33dfeedb3f51` · analysed 2026-09-17

**DATA STATUS** · IBKR TWS read-only, paper session, market data type 1
(`realtime` on all five days) · 1-minute bars from the desk's own stream ·
`decisions.catalyst = 0` on **all 389 rows** — see the defect below.

> ⚠ **NOT A BACKTEST AND NOT A RESULT.** Every trade below is
> counterfactual: no order was ever sent, `orders` is empty, `fills` is
> empty. Outcomes are read off 1-minute bars against planned levels.
> Section 6 lists what that cannot establish. The repo's own eleven-year
> ablation of this same strategy reports **NO EDGE**
> (`research/first-pullback-edge/README.md`); 19 counterfactual trades do
> not revise it.

---

## 1. The defect this measures

| | |
|---|---|
| Symptom | 5 sessions, 389 decisions, **389 REJECT**, 0 plans allowed, 0 orders |
| Kill reasons | catalyst **254** · price 88 · float 47 — nothing ever passed gate 3 |
| Root cause | The desk's only headline source is Alpaca news. The `.env` rebuilt after the 2026-09-11 laptop reset carried no Alpaca keys, so `news_records()` returned `no headline source` all week |
| Why it killed | Gate 3 fails closed. It read *absence of data* as *absence of news* |
| Second defect | The roundup filter keyed on `category`, which every live record fills with the **provider name** (`benzinga`). It never fired once. Verified against the live endpoint 2026-09-17: VEEA read `catalyst=True` on four headlines, all roundups |

Both fixed: commits `ec19f6a` (amendment A2 — gate 3 flags, does not kill;
no-source reads UNKNOWN) and `f1aa048` (roundup filter scans the headline).

---

## 2. Funnel — what the amended cascade would have allowed

Every one of the 389 stored `inputs_json` re-evaluated through
`cascade.evaluate` with `CATALYST_GATE_KILLS = False`. This is the same
mechanism the replay check uses; it is not a re-simulation of the session.

```
389 decisions recorded
├─ 191 still killed   price 88 · float 47 · rising 56   ← gates 4-8 were never
│                                                          reached before, because
│                                                          gate 3 stopped the cascade
└─ 198 plan allowed   REVIEW 80 · WAIT 106 · WATCH 12
   └─  53 prospective (live bars; backfill excluded per pre-registration §3)
       └─  51 trigger touched
           └─  19 actually takeable under the one-position rule
```

**56 of the 254 catalyst-killed names would have died at gate 4 anyway**
(more than 25% off the session high). The catalyst gate was masking a
later gate on nearly a quarter of what it killed.

---

## 3. Success rate — three readings of the same 53 decisions

Each row is stricter than the one above it. Only the last is a rate you
could have achieved.

| reading | n | trigger touched | target first | stop first | mean R | total R |
|---|---:|---:|---:|---:|---:|---:|
| ① every allowed decision | 198 | 148 | 74 (**50%**) | 73 (49%) | +0.51 | +75.7 |
| ② prospective only | 53 | 51 | 30 (**59%**) | 20 (39%) | +0.80 | +40.7 |
| ③ one position at a time, gross | 19 | 19 | 12 (**63%**) | 7 (37%) | +0.83 | +15.7 |
| ④ ③ net of one spread round trip | 19 | 19 | 12 (**63%**) | 7 (37%) | **+0.60** | **+11.5** |

Reading ③ takes decisions in clock order, holds until the plan resolves,
and refuses anything armed while a position is open — the pre-registered
`max_positions = 1`. **32 of the 51 triggered decisions were blocked that
way.** Reading ④ charges the quoted spread at the moment of decision
against the planned stop distance; rows with no stored quote (14 of 53)
are charged the cohort median of 0.25 R.

At the pre-registered $20 per R, reading ④ is **+$229 over five sessions**.

### The 19 trades, in full

| symbol | date | trigger | stop | stop dist | spread | cost R | outcome | gross R | net R |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| FTFT | 09-11 | 2.86 | 2.77 | 0.090 | 0.010 | 0.11 | target | +2.00 | +1.89 |
| FTFT | 09-11 | 2.86 | 2.75 | 0.110 | 0.010 | 0.09 | target | +2.00 | +1.91 |
| PCLA | 09-11 | 12.57 | 12.31 | 0.259 | 0.100 | 0.39 | target | +2.00 | +1.61 |
| PCLA | 09-11 | 13.14 | 12.94 | 0.200 | 0.050 | 0.25 | target | +2.00 | +1.75 |
| SXTC | 09-11 | 2.34 | 2.29 | 0.050 | 0.010 | 0.20 | target | +2.00 | +1.80 |
| PCLA | 09-11 | 13.58 | 13.19 | 0.390 | — | 0.25 | target | +2.00 | +1.75 |
| TNON | 09-11 | 7.41 | 7.29 | 0.120 | — | 0.25 | target | +2.00 | +1.75 |
| TNON | 09-11 | 7.92 | 7.80 | 0.120 | — | 0.25 | stop | −1.00 | −1.25 |
| TNON | 09-11 | 8.01 | 7.87 | 0.140 | — | 0.25 | target | +2.00 | +1.75 |
| FTFT | 09-11 | 2.78 | 2.70 | 0.080 | — | 0.25 | stop | −1.00 | −1.25 |
| TNON | 09-11 | 9.05 | 8.86 | 0.190 | — | 0.25 | target | +2.00 | +1.75 |
| SXTC | 09-11 | 2.37 | 2.33 | 0.034 | — | 0.25 | stop | −1.00 | −1.25 |
| TNON | 09-11 | 9.41 | 9.27 | 0.140 | — | 0.25 | stop | −1.00 | −1.25 |
| VRA | 09-15 | 3.46 | 3.41 | 0.053 | 0.020 | 0.38 | stop | −1.00 | −1.38 |
| TNON | 09-15 | 6.42 | 6.29 | 0.130 | 0.040 | 0.31 | target | +2.00 | +1.69 |
| VEEA | 09-15 | 6.11 | 5.88 | 0.230 | 0.010 | 0.04 | stop | −1.00 | −1.04 |
| VRA | 09-15 | 3.51 | 3.48 | 0.030 | 0.010 | 0.33 | stop | −1.00 | −1.33 |
| VEEA | 09-15 | 5.60 | 5.44 | 0.160 | 0.010 | 0.06 | target | +2.00 | +1.94 |
| VRA | 09-15 | 3.69 | 3.60 | 0.095 | 0.010 | 0.11 | neither | +0.74 | +0.63 |

`—` = no bid/ask stored on that decision, charged the median. Every
`target` credits exactly +2.00 R because `reward_multiple` is a fixed 2.0
in the plan; a real exit would differ.

---

## 4. Three tests that decide how much of this to believe

### ✗ ① The interval includes zero

```
n = 19 · mean +0.604 R · stdev 1.48 · standard error 0.34
95% CI on the mean:  −0.06 R  to  +1.27 R          ← INCLUDES ZERO
bootstrap 20,000 resamples: −0.04 to +1.24 R · P(mean ≤ 0) = 3.5%
```

Positive, not established. A mean this size on 19 observations with this
variance is what a coin can look like.

### ✗ ② Hold-to-close beats it on the same 19 entries

| series, same entries, same costs | mean R | total R |
|---|---:|---:|
| strategy (2R target, stop at the pullback low) | +0.604 | +11.5 |
| **hold to the close** | **+1.036** | **+19.7** |
| paired difference (strategy − hold) | **−0.432** | — |

This is failure condition **#2** of the pre-registration §4, stated on
2026-09-06 before any of this was known: *"the strategy series does not
beat `hold_close` on the same rows."* On this sample it does not. The
fixed 2R target truncates the runners that make the distribution.

### ✗ ③ The result is one day

| session | trades | net R |
|---|---:|---:|
| 2026-09-11 | 13 | **+11.0** |
| 2026-09-15 | 6 | +0.5 |
| 2026-09-14, 09-16, 09-17 | 0 | — |

Remove 11 September: **n = 6, mean +0.085 R, total +0.5 R.** Nothing.
Concentration is as bad: 6 symbols, TNON alone 6 of 19 trades
(TNON 6 · FTFT 3 · PCLA 3 · VRA 3 · SXTC 2 · VEEA 2).

---

## 5. Spread against stop — the executability test

The stops are small enough that the spread is a first-order cost, not a
rounding error.

```
stop distance, prospective allowed: median $0.120 · min $0.020 · max $0.550
spread ÷ stop distance (39 rows with a stored quote):
   median 0.25 · mean 0.54 · max 6.50

  under 25% of the stop — comfortably tradeable   19 rows
  25-100% of the stop  — marginal                 15 rows
  WIDER than the entire stop                       5 rows  ✗
```

Five of 39 planned trades had a spread wider than the whole risk. Those
are not trades; a stop inside the spread is hit by the quote, not the
market. This is the same finding as the sizing rule in `CLAUDE.md` #5:
judge enforceability, not notional.

---

## 6. What this analysis could NOT check

- **Fills.** No order existed. A buy-stop at the trigger is assumed to
  fill *at* the trigger; on a fast small cap it fills above. The spread
  charge in reading ④ is a **floor** on friction, not the whole of it.
- **Intra-bar path.** 1-minute bars. When one bar touched both stop and
  target the grader credits the **stop** (`src/journal/actuals.py`), which
  is conservative, but the ordering across bars is still inferred from
  highs and lows, not from the tape.
- **Halts.** `halts` table is empty across five sessions. Either none
  occurred or the live path is not recording them; unresolved.
- **Partial fills, borrow, fees, PDT.** None modelled.
- **Selection of the universe.** Only names the gap scan put on the desk
  were ever evaluated. The scan's own rejects are not in this cohort.
- **Whether the catalyst gate has value when it has data.** Every row
  here had `catalyst = 0` *because the feed was missing*. This measures
  the cost of the gate firing blind. It does **not** measure whether a
  working catalyst filter helps — that needs sessions with keys in place,
  which start 2026-09-18.
- **Regime.** Five consecutive September sessions, one market.

---

## 7. Next step for a detailed backtest

**The detailed backtest already exists and it is more powerful than
anything five sessions can produce.** `research/first-pullback-edge/` is
an adversarial ablation of this exact strategy:

> **Verdict: NO EDGE.** 3,627 trades across 1,453 sessions, 5,797 names,
> eleven calendar years (2016–2026). Every variant's 95% CI lies entirely
> below zero, in every one of the eleven years, and in a 478-session
> untouched holdout. A random entry minute on the same tape beats every
> variant by 0.80 R (−0.940 R on 42,510 trades vs −1.741 R for the basic
> first pullback). Negative **gross** of costs.
> — `research/first-pullback-edge/README.md`

So the useful next step is **not** another backtest of the same rule. It
is to ask the two questions this counterfactual actually raised, using
that harness, which already has point-in-time data, a survivorship-free
universe (12,613 tickers, 6,701 delisted) and cost modelling:

| # | question | why it is worth the compute | how |
|---|---|---|---|
| 1 | **Does gate 3 do any work when it has data?** | It killed 65% of everything for a week while blind. Nobody has measured its contribution when fed | Add catalyst presence as an ablation dimension in `config/strategy.yaml`; compare variants with the gate on and off across the eleven years |
| 2 | **Is the fixed 2R target the wrong exit?** | Hold-to-close beat it by 0.43 R per trade here, and §4 makes that a failure condition | Re-run the existing variants with exit = close, trailing 9EMA, and 2R; same entries, paired comparison |
| 3 | **Is the stop enforceable?** | Median stop $0.12 with a median spread a quarter of it; 5 of 39 unexecutable | Add a minimum stop distance as a multiple of the spread, and count how many setups survive |

Question 2 is the one I would run first: it is a pure exit study on
entries that already exist in the study's output, it is cheap, and it
tests a failure condition that is already written down.

**What NOT to do:** tune the cascade on these 19 trades. Pre-registration
§7 forbids it explicitly, and it is the exact error that makes paper
results worse than useless — *"paper fills are optimistic, and tuning on
them amplifies the error."*

---

## 8. Verdict

**The catalyst gate was firing on missing data and that was a real defect,
now fixed. The counterfactual does not establish that removing it makes
money.**

- The gate killed 254 names on a feed that did not exist. Fixing it is
  correct regardless of what the counterfactual says. ✓ REMEDIATED.
- The 19 takeable trades read **63% target-first, +0.60 R net, +$229** —
  and that number fails two of its own three tests: the 95% confidence
  interval includes zero, and hold-to-close beats it by 0.43 R per trade.
- Thirteen of the 19 are one session. Without it there is nothing.
- Against an eleven-year, 3,627-trade study of the same strategy reporting
  every yearly CI below zero, five sessions carry no weight.

**Status: the exercise continues in phase A, LOG_ONLY, unchanged.** What
changes from 2026-09-18 is only that gate 3 records instead of kills, and
the read-out now splits `strat·news` against `strat·no-news`
(`src/journal/controls.py`) so the question can be answered from the
owner's own tape at phase D rather than assumed.

---

*NO TICKET ISSUED. This report validates no spread against a live book, no
borrow, no halt state, no fee schedule and no fill. Every trade in it is
hypothetical and no order was placed. Paper exercise only; the replication
of this strategy over 894 sessions was negative expectancy
(`research/momentum-replication/reports/2026-08-regime-filter.md`).*
