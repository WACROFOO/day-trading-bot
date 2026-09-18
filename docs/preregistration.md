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
| A | LOG_ONLY, live desk | **PROPOSED: 5 qualifying sessions AND 40 prospective decisions under the rules currently in force** (owner, 2026-09-18: the cohort resets on an amendment — see §5) | replay check 100% (`scripts/exercise.py check`) on every session; pre-market probe result recorded in §5; paper session measured `realtime` |
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
- **Known gap in the phase-A gate (noted 2026-09-17, PROPOSED, not
  changed):** "40 prospective decisions" counts REJECT rows. Five sessions
  cleared it with zero plans allowed, which would have sent phase B to
  trade with a cascade that had never let a name through. The owner may
  replace it with "40 prospective decisions **of which ≥ 10 allowed**"
  by editing this line and `scripts/day.py` `gates_for_advance` together.
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

**A non-answer is not a verdict** (added 2026-09-18). On 18 September at 08:36
ET the probe ran with the Gateway still in Read-Only mode. IBKR refused both
legs with warning 321, *"The API interface is currently in Read-Only mode"*,
and transmitted nothing. The probe recorded `inconclusive`, and the phase A→B
gate in `scripts/day.py` tested only `is None` — so a run that asked IBKR
nothing cleared the gate that exists to make sure IBKR was asked.

Two corrections, both tightening:

- `premarket_probe.py` now returns `not_run` (exit 7) when every leg is refused
  for read-only, records **no** verdict, and the day runner retries by itself
  on its next pass. A refused run and a murky answer no longer share a word.
- the A→B gate rejects `inconclusive` as well as `None`. This table has rows
  for `held` and `queued` and none for a non-answer; the code now matches.

**SETTLED 2026-09-18, 08:43 ET — verdict `queued`.** With Read-Only unticked
the probe placed the bracket on DUR339781 and IBKR answered the stop leg with
warning 2109: *"Attribute 'Outside Regular Trading Hours' is ignored based on
the order type and destination."* The parent read `Submitted`, the stop
`PreSubmitted`, and both were cancelled cleanly with nothing resting.

The leg looks alive and is not. IBKR accepts the stop and silently drops the
`outsideRth` flag, so it cannot trigger before 09:30. **A pre-market bracket
protects nothing.** This is the second observation of the same behaviour — the
2026-09-08 run produced warning 2109 on the same leg and was miscalled `held`
on the `PreSubmitted` status alone; `verdict_from` has read 2109 as `queued`
since. Ten days apart, same answer.

Consequences, per the table above:

- the phase A→B gate's probe condition is met: `queued` is a definite verdict;
- **phase C does not start** until the owner accepts Amendment A1 below by
  replacing its `PROPOSED`. Accepting it means accepting an unprotected
  pre-market position by name. It is not accepted as of this edit, and the
  outside review of 2026-09-08 recommends against it.

**An amendment is not a broken log** (added 2026-09-18). The first
`exercise.py advance` after Amendment A2 reported *"282 decision(s) do not
reproduce"*. Nothing was corrupt: A2 had correctly changed the answer for the
282 rows the blind catalyst gate had killed, and R11 re-ran every stored
decision through today's cascade.

R11 stands — a log that cannot reproduce its own decisions voids anything built
on it — but it now distinguishes three outcomes instead of two, against
`cascade.RULE_SETS`:

| outcome | meaning | gate |
|---|---|---|
| `reproduced` | the current rules give the recorded answer | counts |
| `superseded` | an older rule set gives it, and that set is named | printed everywhere the replay result is printed, never folded into it |
| `diverged` | **no** rule set this cascade has run under gives it — the log lost something | still blocks, still a defect |

A superseded cohort is not a pass in disguise. It is a statement that part of
the evidence base was collected under rules that no longer exist, which is a
real fact about a backtest even when it is nobody's bug.

**SETTLED — owner, 2026-09-18: the cohort resets on an amendment.** The phase
A→B threshold of 40 prospective decisions counts only decisions that reproduce
under the **current** rules. A row whose answer the amendment did not change
still counts, because it does reproduce under them; a row that only reproduces
under a superseded set does not.

The reason is the gate's own question — *do the rules I am about to trade
produce 40 decisions I have watched?* The pre-A2 cohort cannot answer it: 389
decisions, 389 REJECT, produced by a catalyst gate that killed 254 names
because a config file had no key in it. The cost of this decision is about a
week; the alternative is starting to place orders on evidence gathered by a
defect.

Effective immediately in `scripts/day.py`, tested by
`test_decisions_made_under_superseded_rules_do_not_count_toward_phase_a`.

**What happened when it ran, 2026-09-18 09:0x ET: the gate cleared anyway, and
phase B was entered.** Recorded here because the reason matters and because a
gate that passes is worth auditing as carefully as one that fails.

Of the ~425 decisions, 282 were classified superseded — the rows the blind
catalyst gate had killed. The remainder reproduce under A2 for a reason that is
correct but narrow: the cascade **stops at the first kill**, so a decision that
died at price (88) or float (47) never reached the catalyst gate and therefore
gives the same answer under both rule sets. Those rows are genuine evidence for
the current rules, which is exactly the semantics chosen above, and there were
more than 40 of them.

**The weakness this exposes is a different one, and it is not fixed:** the
A→B gate has never required a single decision with `plan_allowed=1`. It counts
decisions, and a REJECT is a decision. Phase A therefore completed on a
pipeline that, in five sessions, allowed **zero** plans and placed zero orders.
Phase B is TRADE.

This is NOT amended retroactively. The gate was pre-registered, it was met, and
tightening a criterion after seeing that it passed is precisely what
pre-registration exists to prevent. It is recorded as a known weakness of the
phase-A evidence, and the mitigation is that phase B is itself the observation:
it needs 30 taken trades to reach C, and if the desk allows no plans it takes no
trades and phase B is simply inert.

**Proposed for the next amendment, not applied:** A→B should require N
prospective decisions with `plan_allowed=1`, not merely N decisions. The value
of N is unset because setting it now, knowing the current count, would be the
same offence.

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

Result: `PROPOSED: triggered 2026-09-18 by the `queued` verdict above, NOT
accepted`. `exercise.py accept-a1 --confirm` has not been run; the policy
refuses the monitored shape without it.

**Amendment A2 — the catalyst gate flags, it does not kill (owner,
2026-09-17).** What the ledger showed after five phase-A sessions
(11, 14, 15, 16, 17 September): 389 decisions, **389 REJECT**, zero plans
allowed, zero orders; 254 killed at gate 3 (catalyst), 88 at price, 47 at
float; and `decisions.catalyst` was 0 on **every** row. Cause: the desk's
only headline source is Alpaca's news endpoint, and the `.env` written after
the 2026-09-11 laptop reset carried no Alpaca keys, so `news_records`
returned "no headline source" all week and gate 3, which fails closed, read
that absence of data as an absence of news. The 9 September review of the
pre-reset ledger (lost with the reset; figure from that session's output)
reported `strat·allowed n=16` under the same cascade with keys present.

Two changes, in the same commit:

1. **Gate 3 is a flag in this exercise.** `cascade.CATALYST_GATE_KILLS =
   False`. The gate is still evaluated on every bar and written to
   `decisions.catalyst`; it no longer stops the cascade. A desk with no
   headline source reads **UNKNOWN** at the gate, never "none". The rule as
   Ross teaches it (`knowledge-base/strategies/FILTERS.md` gate 3;
   `PARAMETERS.md` `has_catalyst`) is unchanged and one constant away.
2. **The read-out splits by it.** `controls.summary` adds `strat·news` and
   `strat·no-news` next to `strat·allowed` / `strat·killed`, so phase D can
   say whether catalyst-less names paid on this tape instead of assuming.

This is a deviation from the method, made by the owner, before the first
order (no row in `orders`), and it moves the rules hash: every phase-A
decision keeps the hash it was made under (`33dfeedb3f51`). Counterfactual
from the same ledger, planned 2 R targets, no slippage: of the 190
catalyst-killed decisions whose trigger was touched, 47 % reached the target
before the stop; of the 73 prospective ones, 52 %. Not evidence of edge —
paper, and stops of 2–9 cents that no fill would honour — but evidence that
the gate was not selecting on anything the tape rewarded.

Owner action that remains: put Alpaca paper keys back in `.env`
(`ALPACA_KEY_ID`, `ALPACA_SECRET_KEY`, see `.env.example`), or the gate
reads UNKNOWN on every name and the split above has one empty side.

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
| **gate 3 (catalyst): kill → flag** — Amendment A2, owner, 2026-09-17, before the first order; rules hash moved; phase-A decisions keep theirs | every other cascade gate and every threshold |

Tuning the cascade or the detector mid-exercise on the ledger's own fills
is specifically forbidden: paper fills are optimistic, and tuning on them
amplifies the error (brief R4).

---

*Committed as PROPOSED on 2026-09-06. Becomes binding when every `PROPOSED`
is replaced and the commit precedes the first TRADE-mode order in
`data/journal.sqlite`. The ledger's first `orders.placed_at` is the check.*
