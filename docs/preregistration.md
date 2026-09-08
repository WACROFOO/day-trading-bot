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
| Daily risk gate | **PROPOSED: journal gate — 3 consecutive losses, −3 R on the day, 6 entries** | `src/journal/risk.py` `JournalRiskGate`, the one the executor is built with (`scripts/exercise.py live`). It reads this ledger's fills and exits and latches in `risk_day` by ET date. An earlier draft of this row named `src/paper_trading/risk_gate.py` (percentage rules) — that gate belongs to the manual Streamlit app and reads a ledger this exercise does not write; corrected 2026-09-08 after the outside review. The lock closes entries only; exits, the monitored stop and the 11:30 flatten keep running |
| Max concurrent positions, enforced | **1** | `Runner._act` refuses an entry while any order is alive — resting, filled and not exited, exit pending, or an unresolved intent (`ledger.positions_alive`). Enforced in code since 2026-09-08; before that it was a value in this table only |
| Configuration and code, pinned | rules hash + commit | `desk_profile.fingerprint()` and the git commit are stamped on every decision, order and the exercise state |
| Hard stop, new entries | **11:30 ET** | `PARAMETERS.md` §2 `session_close`, enforced in `src/execution/intent.py` |

## 3. Phases and sample sizes

| Phase | Mode | Runs until | Gate to the next phase |
|---|---|---|---|
| A | LOG_ONLY, live desk | **PROPOSED: 5 qualifying sessions AND 40 prospective decisions** | replay check 100% (`scripts/exercise.py check`) on every session; pre-market probe result recorded in §5; paper session measured `realtime` |
| B | TRADE, regular hours only | **PROPOSED: 30 taken trades** | ≥90% of fills carry NBBO; median slippage ratio recorded; zero unprotected entries |
| C | TRADE, pre-market added | **PROPOSED: 30 more taken trades** | only in the shape the probe dictates (§5) |
| D | Read-out | at **PROPOSED: n = 60 taken trades** total | the failure condition in §4 is evaluated ONCE, here, not continuously |

Definitions, fixed 2026-09-08 after the outside review:

- A **qualifying session** is a day on which the desk recorded bars and the
  runner ran to the hard stop. A holiday, a dead feed, or a rerun of the
  same day counts for nothing (`scripts/day.py` `after_close`).
- A **prospective decision** is one armed on a bar the desk watched live.
  A decision armed on history loaded at start carries `-backfill` in
  `data_status`, is refused by the runner in every mode, and is excluded
  from every count and comparison. It stays in the ledger as a diagnostic
  cohort and the report says how many were excluded.
- **Probe and smoke orders** (`premarket_probe.py`, `restart_probe.py`,
  `paper_trade_smoke.py`) never write `orders`; they are not enrolled
  trades. "Before the first order" means the first row in `orders`.
- Phase D is a **capped feasibility pilot**, not an inferential threshold.
  Results are reported with uncertainty, by session stratum (regular hours
  and pre-market separately), and never pooled without a pre-stated weight.

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
| stop queued to 09:30 | **phase C does not start** until the owner accepts the monitored-exit amendment below by replacing its `PROPOSED` |

**What "protected" means, field by field** (added 2026-09-08 — one boolean
carried too much):

| fact | where it lives | values |
|---|---|---|
| a stop rests at the broker | `orders.stop_status` | `Submitted`/`PreSubmitted` yes; `Cancelled`/`Inactive` no; `monitored` no stop at the broker |
| the session the order is for | `orders.session` | `regular` / `premarket` |
| quantity actually held | `orders.filled_qty` | from IBKR; a partial fill is a smaller position |
| the runner's monitor is alive | runner process + `quote_source` | the monitored stop exists only while `exercise.py live` runs and the desk's quote is under 30 s old |
| an exit was sent, not yet filled | `orders.status = ExitPending` | closed at the real fill by the next sync |
| an intent whose acknowledgement was lost | `orders.status = intent` / `UNRESOLVED` | reconciled by `orderRef`; never resent |

`orders.protected` summarises the first row only. A monitored entry is
**UNPROTECTED** in every report and gate, whatever the monitor's health.

**Accepting A1 is a human act.** `python3 scripts/exercise.py accept-a1
--confirm` records the operator's name and time in `exercise_state`; the
policy refuses the monitored shape without it (`src/execution/policy.py`).
No code path sets it. The outside review of 2026-09-08 recommends not
accepting it and observing pre-market without orders.

**Amendment A1 — monitored exit (PROPOSED, 2026-09-06).** On a `queued`
verdict a pre-market entry is placed as a limit alone, with no stop leg
(`PaperTrader.place_entry_monitored`), recorded `protected=0`,
`stop_status='monitored'`. `Runner.watch_stops` is the stop: on every loop
it reads the desk's latest quote from the ledger and, the moment
bid ≤ stop, sells at bid − $0.10, limit, extended hours — the only exit
that exists pre-market (`.claude/skills/extended-hours/SKILL.md`). It exists
only while the runner runs. A missing or stale quote is logged and acted on
by holding; no price is ever guessed. Every such position counts as
**unprotected** in the report and in the B→C gate. Accepting A1 means
accepting that exposure by name.

Result: `PROPOSED: not yet run` — replace with the date and the verdict line.

## 6. Stopping rules — the exercise halts and is reviewed if

- the daily risk gate latches on **3 sessions out of any 10**
- **any** entry is found without a working exit: no stop resting at the
  broker and — for an A1-accepted monitored entry only — no live monitor
  with a fresh quote. (A monitored entry is reported UNPROTECTED always; it
  is a stopping event when its monitor is not live.)
- an order intent is `UNRESOLVED` at the broker, or the position
  reconciliation finds an untracked position or a quantity mismatch
- the replay check diverges on **any** decision
- cumulative realised R reaches **PROPOSED: −20 R** at any point
- an after-hours continuation happens without a logged human confirmation

A halt is a review, not a failure. But the exercise does not resume until
the cause is written into `docs/paper-exercise-brief.md` §⑦ or fixed.

## 7. What may be changed during the exercise, and what may not

| May change, with a dated note here | May NOT change until phase D |
|---|---|
| dollar risk **downward** | any FILTERS.md threshold or cascade gate |
| bar resolution **for archival only** — finer bars stored, decisions unchanged | the detector's entry/stop logic — and its **input resolution**: a finer bar feeding the detector is a new strategy version and starts a new cohort |
| the NBBO source | the failure condition (§4) |
| the report layout | n (§3) |

Tuning the cascade or the detector mid-exercise on the ledger's own fills
is specifically forbidden: paper fills are optimistic, and tuning on them
amplifies the error (brief R4).

---

*Committed as PROPOSED on 2026-09-06. Becomes binding when every `PROPOSED`
is replaced and the commit precedes the first TRADE-mode order in
`data/journal.sqlite`. The ledger's first `orders.placed_at` is the check.*
