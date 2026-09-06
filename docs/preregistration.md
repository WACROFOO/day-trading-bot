# Pre-registration — the paper-trading exercise

**Status: PROPOSED. Not in force until the owner replaces every `PROPOSED`
below with a value and this file is committed BEFORE the first order.**

`docs/paper-exercise-brief.md` R6: written down, committed, timestamped,
before any trade — the sample size, the stopping rule, and what result
would count as the strategy failing. Against the 894-session negative prior
(`research/momentum-replication/reports/2026-08-regime-filter.md`), a
result read off n=20 is noise, and an exercise without a pre-stated failure
condition is p-hacking with a broker attached.

Every number here is a **decision the owner makes**, not a measurement.
The proposals are defaults chosen to be defensible, with the reason given
so they can be argued with rather than accepted.

---

## 1. What is being tested

The Ross small-cap momentum method as encoded in
`knowledge-base/strategies/FILTERS.md` (Layer 1 reject cascade →
`src/momentum_platform/cascade.py`) and the first-pullback detector
(`src/momentum_platform/pullback.py`), executed as brackets on the IBKR
paper account `DUR339781`, pre-market 07:00–09:30 ET and regular hours
09:30–11:30 ET, sized from the stated dollar risk only.

Not being tested: the strategy's profitability in general. Being measured:
**selection quality** — whether what the cascade and detector select does
better than the free baselines on the same names at the same instants.

## 2. The parameters

| Parameter | PROPOSED value | Why this default |
|---|---|---|
| Dollar risk per trade | **$20** | ≈1% of NetLiq $2,143.70 (preflight 2026-09-06). Also what every probe has used, so nothing changes shape at go-live |
| Max concurrent positions | **1** | one name at a time makes every fill and every exit attributable; add a second only after the ledger has 60 taken trades |
| Bar resolution logged | **1m** | the only resolution the desk produces. `2026-08-streams-roundup.md`: the micro-pullback is often a 10-second pattern; this must be recorded as a known limitation, not discovered later |
| Daily risk gate | existing `RiskLimits` | `src/paper_trading/risk_gate.py`: max daily loss 6%, giveback 50%, 3 consecutive losses stop, 20% drawdown walkaway. Unchanged; these are already latched and persisted |
| Hard stop, new entries | **11:30 ET** | `PARAMETERS.md` §2 `session_close`, enforced in `src/execution/intent.py` |

## 3. Phases and sample sizes

| Phase | Mode | Runs until | Gate to the next phase |
|---|---|---|---|
| A | LOG_ONLY, live desk | **PROPOSED: 5 sessions or 40 decisions**, whichever is later | replay check 100% (`scripts/exercise.py check`) on every session; pre-market probe result recorded in §5 |
| B | TRADE, regular hours only | **PROPOSED: 30 taken trades** | ≥90% of fills carry NBBO; median slippage ratio recorded; zero unprotected entries |
| C | TRADE, pre-market added | **PROPOSED: 30 more taken trades** | only in the shape the probe dictates (§5) |
| D | Read-out | at **PROPOSED: n = 60 taken trades** total | the failure condition in §4 is evaluated ONCE, here, not continuously |

Why 60: not a power calculation — with the variance the replication
measured (`2026-08-short-hold.md`: stdev 31.2% per trade before short
holds) no affordable n gives power against a small edge. 60 is the point
at which the *controls* become interpretable: whether the strategy beats
hold-to-close on its own names is a paired comparison and 60 pairs is
enough to see a large effect, which is the only kind worth acting on.

## 4. The failure condition — evaluated once, at phase D

The strategy is judged to have **failed this exercise** if, at n = 60, in
**realised** R:

1. mean realised R ≤ 0, **or**
2. the strategy series does not beat `hold_close` on the same rows
   (`src/journal/controls.py`), **or**
3. fewer than 80% of fills passed the NBBO plausibility check (the
   result is then *unmeasured*, not failed — but it is not a pass)

Any one is sufficient. This is stated now so it cannot be renegotiated
after the number is known.

The strategy is **not** judged to have succeeded by the converse. Passing
all three at n = 60 earns phase E (continue to n = 120 with the same
conditions), nothing more. `2026-08-oos-march-2024.md`: 36 of 36 settings
positive in one month, 0 of 49 in another. One window proves one window.

## 5. Open question to be settled before phase C

**Does IBKR hold a stop pre-market with `outsideRth=True`?** Not in the
corpus (`.claude/skills/extended-hours/SKILL.md` names other brokers).
Settled by `scripts/premarket_probe.py` between 07:00 and 09:30 ET.

| Probe verdict | Phase C shape |
|---|---|
| stop held live | brackets as in phase B, `outsideRth=True`, `protected` confirmed by read-back |
| stop queued to 09:30 | **phase C does not start** until a monitored-exit design is written, reviewed and pre-registered as an amendment here |

Result: `PROPOSED: not yet run` — replace with the date and the verdict line.

## 6. Stopping rules — the exercise halts and is reviewed if

- the daily risk gate latches on **3 sessions out of any 10**
- **any** entry is found unprotected (no resting stop, no confirmed monitor)
- the replay check diverges on **any** decision
- cumulative realised R reaches **PROPOSED: −20 R** at any point
- an after-hours continuation happens without a logged human confirmation

A halt is a review, not a failure. But the exercise does not resume until
the cause is written into `docs/paper-exercise-brief.md` §⑦ or fixed.

## 7. What may be changed during the exercise, and what may not

| May change, with a dated note here | May NOT change until phase D |
|---|---|
| dollar risk **downward** | any FILTERS.md threshold or cascade gate |
| bar resolution, if the desk gains a finer one | the detector's entry/stop logic |
| the NBBO source | the failure condition (§4) |
| the report layout | n (§3) |

Tuning the cascade or the detector mid-exercise on the ledger's own fills
is specifically forbidden: paper fills are optimistic, and tuning on them
amplifies the error (brief R4).

---

*Committed as PROPOSED on 2026-09-06. Becomes binding when every `PROPOSED`
is replaced and the commit precedes the first TRADE-mode order in
`data/journal.sqlite`. The ledger's first `orders.placed_at` is the check.*
