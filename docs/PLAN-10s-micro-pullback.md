# Plan — the 10-second micro pullback, confirmed inside the 1-minute candle

```
WHAT THIS IS · a research plan, owner-specified 2026-09-17, to test the
     setup at the resolution the corpus says he actually trades it.
     Phase 0-1 LOG_ONLY; Phase 2 sends PAPER orders (owner, 2026-09-17).
     Runs BESIDE the phase-A exercise and never touches it.
STATUS · PROPOSED. Nothing here is built. Section 8 is the kill rule and
     it is written before any data is collected, on purpose.
PAPER ONLY · the 1-minute version of this setup measured NEGATIVE over
     eleven years (research/first-pullback-edge/README.md). This plan
     argues that study tested a different pattern, not that this one pays.
```

## 1. Why this exists

`knowledge-base/strategies/PARAMETERS.md` states the problem in its own
words, and it is not a small one:

> Of the "micro pullback" mentions carrying an explicit timeframe, 19 are
> 10-second against 59 one-minute. On a 1-minute chart a 10-second pullback
> is not a candle — it is the wick of one.
>
> **This is not a parameter error, it is a resolution error.** No setting of
> `MIN_DIP_BARS` on 1-minute data can represent it, and it is the mechanical
> explanation for why replicated entries sit in front of a median −1.56 R
> excursion.

Spoken sources for the pattern itself:

| claim | source |
|---|---|
| the entry is the break of the prior candle's high, not the close | `IwDORxvXAAs` @00:48:34 |
| 10-second micro pullback, traded live | `6xIr761eZj8` [41:38] · `XIQUoLyUWuw` [33:32] |
| micro pullback = smallest pullback in a move, lowest-risk entry | `ZpiWEMTpvoo` @00:17:31 |
| he claims 65-70% accuracy (his claim, unverified here) | `Gf791LDEsQI` @00:39:41 |

**The state today.** The desk already receives IBKR 5-second real-time bars,
aggregates them to 10-second candles and publishes them to the browser
(`src/momentum_platform/datasources/ibkr_stream.py` `BarStore.closed_10s`,
`src/momentum_platform/dashboard/stream.py` `publish_closed_10s`). The detector that arms plans is
fed **1-minute bars only** (`session_builder.py` builds
`FirstPullbackDetector` and feeds it minute groups). The right data arrives
and the decision is taken at the wrong resolution.

**The 10-second bars are never stored.** The ledger's `bars` table has no
resolution column and holds 16,414 one-minute rows for 11–17 September.
`closed_10s()` is a *draining* read — each candle is emitted exactly once and
then gone. Nothing can be measured or replayed until that changes, which is
why Phase 0 exists.

## 2. The design, in the owner's terms

**1-minute is the base. 10-second is a confirmation layer used only inside a
forming momentum candle.** Not a 10-second strategy.

```
LAYER A · 1-MINUTE · closed bars · CONTEXT
  answers: are we in a momentum move, and is it healthy?
  → arms a HUNTING state. Never triggers an entry by itself.

LAYER B · 10-SECOND · closed bars inside the FORMING minute · TIMING
  answers: is the micro pullback complete, and is the move still up
           right now, within this candle?
  → fires the trigger, sets the stop.
```

### Layer A — mandatory conditions, all on closed 1-minute bars

| # | condition | source |
|---|---|---|
| A1 | impulse: price rising over the last 1–6 candles, at or near the day's high | `MICRO-PULLBACK-SPEC.md` §1 |
| A2 | volume above its own recent average during the impulse | §1 |
| A3 | price above VWAP | §4 (below VWAP = refuse) |
| A4 | price above the 9 EMA | §4 |
| A5 | MACD positive **and** above signal | §4 — "no long, ever" if not |
| A6 | Layer 1 cascade already passed (price band, float, instrument, tick, halt) | `cascade.py` |

Layer A holding is what the existing desk already computes. It arms HUNTING
and nothing more.

### Layer B — mandatory conditions, on closed 10-second bars

| # | condition | note |
|---|---|---|
| B1 | we are inside a forming 1-minute candle that is **pushing** (current price above that candle's open) | this is the "momentum bar" the owner described |
| B2 | dip: 1–3 consecutive 10s bars that do not make a new high | the micro pullback |
| B3 | dip volume **falls** against the 10s bars of the push | rising volume in the dip = real selling, refuse |
| B4 | during the dip, price holds above VWAP and above the 9 EMA | the intra-candle trend check the owner asked for |
| B5 | the dip is shallow — it gives back a small part of the move, not most of it | deep dip = **skip**, never "widen the stop" |
| B6 | TRIGGER: a 10s bar trades above the previous 10s bar's high | the entry, per `IwDORxvXAAs` @00:48:34 |
| B7 | stop = low of the 10s dip, minus one tick | |
| B8 | **(trigger − stop) ≥ k × spread** | the executability gate, §4 below. Mandatory |

### What is optional, and why

The 5-minute trend check the owner mentioned is **optional and deliberately
excluded from v1**. Register split, measured this turn with
`scripts/corpus.py "5 minute chart"`: 21 hits in teaching across 19 of 258
files, **0 hits in 290 live-stream files, 0 in 69 daily recaps**. He teaches
it; he does not talk about it while deciding. Adding an untested gate that
only ever removes trades makes a small sample smaller. It is recorded here as
a candidate for v2 and it will be *measured* before it is *added*.

## 3. What is mandatory to get right, and what breaks if it is not

Each of these has a named failure this repo has already suffered.

### M1 · Persist the 10-second bars, with the resolution recorded

Nothing is measurable or replayable otherwise. `bars` needs a `tf` column
(`'1m'` / `'10s'`) or a sibling table, and the write must happen where the
candles are drained, or they are lost.

*Breaks if not:* no replay check, and the replay check is this project's
core guarantee — 389/389 today.

### M2 · Strictly point-in-time, no look-ahead

Layer B may read only **closed** 10s bars and the forming 1-minute state as
it existed at that instant. Indicators must be incremental, never a
vectorised pass over the day.

*Breaks if not:* the single most common way a backtest lies. The study
enforces this in `research/first-pullback-edge/src/indicators.py` and says so:
*"strictly causal incremental EMA/MACD/ATR/VWAP/HOD. No vectorised pass
exists, so no future bar can leak."*

### M3 · One source of truth for both resolutions

The 1-minute bars fed to Layer A must be the **aggregate of the same 10-second
bars** Layer B reads, never a separate IBKR subscription. The repo already
does this for fixtures and states why: *"the 1-minute bars the scanner engine
consumes are aggregated from them, so no chart timeframe can disagree with
what the scanners saw."*

*Breaks if not:* the two layers disagree about the same instant, and the
disagreement is invisible.

### M4 · Absence of a bar is not a flat bar

IBKR 5-second `TRADES` bars do not print when nothing trades. A 10-second
slot with no trade is **missing**, not a doji at the last price. The existing
store already refuses to invent candles (`test_missing_half_is_not_interpolated`)
and that behaviour must survive.

*Breaks if not:* phantom pullbacks in thin names, which is most of this
universe pre-market.

### M5 · The executability gate (B8)

Measured on your own five sessions: median stop distance $0.12, **spread a
median 25% of the stop**, and 5 of 39 planned trades had a spread wider than
the entire stop. A 10-second dip is *smaller* than a 1-minute dip by
construction, so this gets worse, not better.

**`k = 8`, owner-confirmed 2026-09-17.** An earlier draft of this file
proposed `k = 4` and that was wrong by arithmetic, not by taste. The
strategy's own best theoretical case is 50% wins on the half-at-1R ladder,
which is **+0.25 R per trade before costs** (`MICRO-PULLBACK-SPEC.md` §sizing).
A round trip pays roughly one full spread, so the spread costs `1/k` R:

| k | spread at most | spread costs | left of the +0.25 R |
|---:|---:|---:|---:|
| 4 | 25% of risk | 0.250 R | **0.000 R — the whole edge** |
| 6 | 17% | 0.167 R | +0.083 R |
| **8** | **12%** | **0.125 R** | **+0.125 R** |
| 10 | 10% | 0.100 R | +0.150 R |

Commissions take a further ~0.05–0.07 R (measured,
`research/momentum-replication/reports/2026-08-pine-v8-benchmark.md`), so
`k = 8` keeps roughly +0.06 R in the best case and `k = 4` keeps nothing.

Cost of the strictness, on the 39 prospective 1-minute setups with a stored
quote: `k=4` keeps 19, `k=8` keeps 16, `k=10` keeps 12. Three setups buy the
difference between zero and positive expectancy.

Declared `LOCAL_ADDITION / REASONED_NOT_MEASURED`. Phase 0 measures the
10-second dip depth and may raise it; it may not lower it below 8 without a
dated note here.

*Breaks if not:* a stop inside the spread is hit by the quote, not by the
market. You are not trading, you are paying.

### M5b · Concurrent positions and the real binding constraint

Owner decision 2026-09-17: **more than one position at a time is allowed,
subject to margin.** Two facts make this less free than it sounds.

**The PDT rule is no longer the limit.** It was eliminated in spring 2026;
margin accounts now need a $2,000 minimum
(`knowledge-base/warrior-blog/rules-regulation/pattern-day-trader-rule.md`,
lastmod 2026-08-03). The paper account's $2,143.70 clears it. Trade count is
not capped.

**Cash is the limit, and it binds much earlier than risk does.** A tight stop
produces a large share count: $20 of risk on a 3-cent stop is 666 shares, and
at $3.50 that is $2,331 of stock — already the whole account for ONE position.
`MICRO-PULLBACK-SPEC.md` states the same two caps: the risk budget and the
cash, whichever binds first. At 10-second stops this gets tighter, not looser.

**Correlation is the danger, not the count.** Every name on this desk is a
low-float momentum runner on the same session. They are one factor, not three
positions. Three concurrent trades in this universe is 3× the same bet.

Therefore, mandatory, all three enforced together:

| cap | value | why |
|---|---|---|
| concurrent positions | **3** | beyond this the correlation makes the risk figure fiction |
| total open risk | **3 R** | one adverse market minute can take every open position at once |
| position value | existing cash cap, no margin borrowing in v1 | the account is $2,143; leverage on a correlated basket is how it goes to zero |

The daily risk gate (`src/journal/risk.py`) keeps running unchanged on top.

### M6 · Separate cohort, separate rules hash, phase A untouched

`docs/preregistration.md` §7 already governs this: a finer bar feeding the
detector *"is a new strategy version and starts a new cohort"*. So: a distinct
`source` value in `decisions` (`pullback10s`), the rules fingerprint carries
the resolution, and the phase-A gates keep counting only the 1-minute cohort.

*Breaks if not:* the running exercise is contaminated and five sessions of
clean work are wasted.

### M7 · No order path, ever, in this package

LOG_ONLY. `tests/test_ibkr_stream.py::test_the_module_exposes_no_order_surface`
must keep passing, and the new detector gets the same guard.

### M8 · A control, decided before the data

Random 10-second entry on the same names, same sessions, same stop rule,
same costs — and run on the **same terms** as the strategy. The study's own
`baseline_random_entry` documents three ways an unfair version flatters the
strategy, and correcting only the risk denominator shrank an apparent 0.80 R
edge to about 0.14 R. That correction is the reason this control is
mandatory and must use `symmetric=True` semantics.

### M9 · Halts

Zero halt transitions recorded across five sessions is not plausible for this
universe; either none occurred or the live path is not recording them. At
10-second resolution a halt is the difference between a stop and a gap. This
must be verified in Phase 0.

### M10 · Cost and volume budget

10-second bars are six times the rows of 1-minute. The desk rebuilds every
3 seconds (`config/desk-profile.json` `rebuildSeconds`). Detector cost per
rebuild must be measured, and the ledger's growth per session recorded — the
current ledger reached 11.8 MB in five sessions on 1-minute bars alone.

## 4. Phases

### Phase 0 — Feasibility. Two sessions. Can kill the whole idea.

Build **only** the persistence (M1) plus a measurement script. No detector.

Then measure, on real captured tape:

| measurement | decision it drives |
|---|---|
| distribution of 10-second dip depth, in cents and in spread multiples | sets `k` in M5; if the median dip is inside the spread, **stop here** |
| how often a 10s dip exists inside a pushing 1-minute candle | is there anything to trade at all |
| missing-bar rate per symbol, pre-market and regular hours | M4 feasibility in thin names |
| halt transitions actually captured | M9 |
| rows and megabytes added per session, detector cost per rebuild | M10 |

**Deliverable:** a report in `research/paper-exercise/reports/`, with an
explicit GO or NO-GO. A NO-GO here costs two days and saves weeks.

### Phase 1 — The detector, offline, against captured tape.

A new module `micro_pullback.py` under `src/momentum_platform/`, a
two-layer state machine implementing §2 (does not exist yet). Fed from the persisted bars, never from the network.

Mandatory tests before it runs live:
- no look-ahead: feeding bars one at a time reproduces the identical setups
- 1m/10s synchronisation: the aggregate of the 10s bars equals the 1m bar
- a missing 10s slot never becomes a candle
- every B-condition has a test that fails when the condition is removed
- no order surface

**Deliverable:** replay of Phase 0's sessions reproduces 100% of its own
setups, the same guarantee the 1-minute path already meets.

### Phase 2 — Live, PAPER ORDERS, beside phase A.

**Revised 2026-09-17 on the owner's decision.** The original draft was
LOG_ONLY for 20 sessions. That was over-cautious: logging can never answer
the question that actually decides this, which is *does the stop hold at
10-second resolution?* Only real fills produce real slippage. On the
eleven-year data a stop meant to cost 1 R actually cost 2.06 R, and nothing
but sending orders will show whether that happens here.

Same IBKR connection, same desk, same paper account. Writes
`source='pullback10s'` into the same ledger as a separate cohort.

**Who sends orders.** The 10-second detector, and only it. The 1-minute
detector keeps running LOG_ONLY as the paired control on the same names and
instants. One thing touches the broker; the comparison is free.

**Two questions, two very different sample sizes.** Conflating them is how a
week of noise becomes a conviction:

| question | needs | realistic |
|---|---|---|
| do fills happen at sane prices, does the stop hold, is `k` right | 20–30 fills, mechanical, low variance | **one week** |
| does it make money | hundreds of trades, very high variance | months; no shortcut exists |

**Week 1 is read as an execution report, not a profit report.** That is not
caution, it is arithmetic: at this variance a 10-trade P&L is consistent with
almost any true expectancy. The read-out in §8 is not evaluated until the
sample exists.

Runs until the kill rule fires or the sample is reached.

Three series are recorded on every session, on identical names and instants:
1. the 1-minute detector (the existing cohort)
2. the 10-second detector
3. the symmetric random-entry control

### Phase 3 — Read-out, once, against §8.

## 5. What "synchronised" means operationally

The owner's requirement, stated precisely so it can be tested:

- one IBKR subscription per symbol, 5-second real-time bars
- 10-second candles = pairs of 5-second bars, both halves required
- 1-minute candles = aggregate of the six 10-second candles of that minute
- Layer A reads only **closed** minutes
- Layer B reads only **closed** 10-second candles of the **currently forming**
  minute, plus that minute's running open/high/low/volume
- at any instant, `sum(10s bars of minute M) == 1m bar M` is an assertion, not
  an assumption, and a test

## 6. What this plan will NOT do

- It will not place an order. Not in paper, not once, not as a probe.
- It will not change the phase-A exercise, its thresholds, or its gates.
- It will not tune anything on the 19 counterfactual trades, nor on Phase 2's
  own results. `docs/preregistration.md` §7 forbids it and it is the error
  that makes paper results worse than useless.
- It will not add the 5-minute check until v2 measures it.

## 7. Honest expectations

Three things are true at once and all three belong here.

1. The 1-minute version of this setup is measured negative over eleven
   years, in every year, with every yearly confidence interval below zero.
2. That study could not represent the pattern at the resolution the corpus
   says he trades it. This plan tests something genuinely untested.
3. A finer resolution means **more trades, smaller stops and more spread paid
   per unit of risk** — and spread is already a quarter of the stop at
   1-minute. The most likely single outcome of Phase 0 is that the micro
   pullback's stop is not executable for a retail account on these names.

Discovering (3) in two days is a good outcome, not a failure.

## 8. The kill rule — written before the data

Phase 2 is abandoned, and the approach with it, if **any** of these is true
at the read-out:

1. the 10-second cohort does not beat the symmetric random control on the
   same instants, on realised risk, with a confidence interval that excludes
   zero;
2. median realised risk exceeds 1.5× planned risk (the stop does not hold at
   this resolution);
3. fewer than 30 takeable setups in 20 sessions after the one-position rule
   (nothing to measure);
4. the replay check fails on any session (the record is not trustworthy).

A pass on all four earns **one thing only**: the right to write a
pre-registration for a phase-B style paper test. It is not permission to
trade money.

---

## 9. Owner decisions — settled 2026-09-17

| decision | value |
|---|---|
| spread gate `k` | **8** (was 4; corrected by arithmetic, §M5) |
| Phase 2 shape | **paper orders from day one**, week 1 read as execution quality only |
| who sends orders | the **10-second detector only**; the 1-minute detector stays LOG_ONLY as the paired control |
| concurrent positions | **allowed, capped at 3 and at 3 R of open risk**, no margin borrowing in v1 (§M5b) |
| a NO-GO at Phase 0 | accepted as a legitimate outcome |

Still required before the first paper order: a pre-registration for the
10-second cohort, written and committed before it, in the shape of
`docs/preregistration.md`. It is a different strategy version, so it is a new
document and not an amendment to the 1-minute one.

## 10. Build log

| date | what | commit |
|---|---|---|
| 2026-09-17 | **M1 done.** `bars_10s` table, `record_bars_10s`, `bars_10s_from_ledger`; the drain in `publish_closed_10s` takes a `sink`; the desk buffers 30 candles per write and flushes on stop. 8 tests, including the safety property that no 10-second row can reach the 1-minute tape the grader reads | `b3f644e` |
| 2026-09-17 | **Package + Phase 0 tooling.** `src/momentum_platform/microflow/` — one module per responsibility, README carrying the contracts: `config.py` (every parameter with `origin` and `evidence_status`, nothing written twice), `bars.py` (fold to minutes, coverage, `assert_sync`, `forming_minute`), `spread.py` (the k gate, three states, fails closed on a missing quote), `measure.py` (dip shapes, the survival-by-k table, the GO/NO-GO with its thresholds stated first). `scripts/microflow.py capture / measure / config`. 23 tests. A test caught the first draft of `find_dips` treating sideways chop as a string of micro pullbacks, which would have biased the stop distribution small and risked a false NO-GO; the push must now set a new run high | this commit |

---

## 11. The modules, and why the split is where it is

`src/momentum_platform/microflow/README.md` holds the contracts. The split
follows the plan's own sections so a later change lands in one file:

| module | owns | a later change that touches only this |
|---|---|---|
| `config.py` | every parameter, with provenance | raising `k` after Phase 0; setting the retrace cap once measured |
| `bars.py` | resolution mechanics | a different bucket size; a stricter sync tolerance |
| `spread.py` | executability | a cost model with commissions in it |
| `measure.py` | Phase 0 | a new measurement, a different GO threshold |
| `context.py` | Layer A (Phase 1) | **adding the 5-minute trend check** — the v2 candidate |
| `timing.py` | Layer B (Phase 1) | the dip definition; a 5-second variant |
| `detector.py` | composition + ledger writes (Phase 1) | |
| `risk.py` | position caps (Phase 2) | changing 3 positions / 3 R |

Two package rules, both enforced by tests: a number is written once, in
`config.py`; and no module here may name an order primitive — the order path
stays in `src/execution/`.

---

*Status: Phase 0 tooling built, awaiting the first captured session
(2026-09-18). Nothing has been traded and no order path exists.*
