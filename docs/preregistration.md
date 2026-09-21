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
| B | TRADE, regular hours only | **PROPOSED: 30 taken trades** | ≥90% of fills carry NBBO; median slippage ratio recorded; zero unprotected entries; **and, from 2026-09-21, one fully reconciled paper trade lifecycle** (below) |
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
- **Operational readiness (added 2026-09-21 evening, review item 11;
  applies prospectively).** The original A→B gate passed on 2026-09-18. It
  did not establish operational readiness: a decision count validates
  activity, not order submission, protective exits, reconciliation or
  recovery. The historical pass stands as recorded in §5 and is not
  rewritten. A revised gate applies from here forward: phase C requires, in
  addition to the counts, **one fully reconciled paper trade lifecycle** —
  an entry IBKR reported filled, a protective stop leg that existed at the
  broker, an exit IBKR reported filled (never a sent-but-unconfirmed sell),
  the ledger row closed, and no human flag on it
  (`ledger.reconciled_lifecycles`, `scripts/day.py` `gates_for_advance`).
  Thirty taken trades do not unlock pre-market on their own, because
  pre-market is a different execution regime. Until that lifecycle exists
  the exercise's status is **paper commissioning**, whatever the phase
  letter says.
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

**A2, re-justified (2026-09-21 evening, review item 6).** The paragraph
above argues from a dead feed to a flag-only gate, and the review is right
that this conflates two things: an infrastructure defect (no keys) and a
strategy amendment (catalyst not mandatory). A dead feed establishes that
the desk *could not assess* catalysts. It establishes nothing about whether
catalysts matter. The 254 kills were kills on **missing information**, and
the counterfactual quoted above (47 % of catalyst-killed rows reached the
target) is a statement about names the desk never looked at, not about
names with no news.

Three states, kept apart from here on (`momentum_platform.catalyst.
news_verdict`, A7; `scripts/gate_audit.py` `catalyst_states`):

| state | meaning | how the ledger tells |
|---|---|---|
| **FOUND** | a catalyst dated today, this company's own headline | `inputs.catalyst_today = true` (A7: verdict STRONG or WEAK) |
| **NONE** | the feed was healthy and found nothing inside its coverage | `catalyst_source_ok = true`, `catalyst_today = false` |
| **UNKNOWN** | the feed was unavailable or refused; nothing was ruled in or out | `catalyst_source_ok = false` |

A2's justification is therefore restated as what it is: **a deliberate test
of trading without a mandatory catalyst**, chosen by the owner, with the
read-out split by FOUND / NONE so that phase D can say whether NONE names
paid on this tape. UNKNOWN rows sit in neither cohort; a kill on UNKNOWN is
not evidence about catalysts and is reported on its own line. The `.env`
repair (`86e0ded`) is the infrastructure half and stands on its own; A2
would be the same amendment with a working feed. The count the review asked
for — how many of the 254 A2-era catalyst kills were UNKNOWN and how many
NONE — is printed by `python3 scripts/gate_audit.py` under *catalyst states*
on the owner's ledger; from the cause recorded above (no keys all week) the
expectation is that all 254 read UNKNOWN, and that expectation is written
here before the number is read.

**Amendment A3 — the exit rule (IN FORCE from the first desk start after
2026-09-21 21:00 ET; proposed the same morning, coded that evening).** The controls of 2026-09-21 (`exercise.py report`, sessions
11–18 September, 199 triggered prospective rows) put the armed plan at mean
+0.461 R against hold-to-close at +6.301 R **on the same entries**, with all
three medians negative: most trades lose, a few run enormously, and the fixed
2 R target sells exactly the runners. This is failure condition ② of §6,
observed in the ledger's own controls.

Honesty constraint before adopting it: 192 of those 199 rows are plans the
cascade KILLED; the allowed cohort is 7 rows. The signal is strong in
direction and thin in the cohort that would actually have traded, so A3 is
adopted as a **forward test**, not as a conclusion.

The proposed rule, stated so it can be implemented and killed:

- entry and sizing unchanged; initial stop unchanged; total planned risk
  stays the owner's $20;
- **no fixed profit target.** The protective stop trails the high since
  entry at a distance of one initial risk (1 R per share), ratcheting up,
  never down. A trade that reaches +2 R and retraces exits at about +1 R; a
  trade that runs keeps running until it gives back 1 R from its peak;
- the 11:30 flatten and every phase gate are untouched;
- the A/B: **A3 runs live; `baseline` (fixed +2 R target) and `no_target`
  (initial stop only, the rule actually in force until A3) are simulated on
  the same entry fill, same initial stop and same cutoff by
  `journal.controls.exit_variants`, bar-ordered with no within-bar
  look-ahead.** The simulated exits share the entry fill; sharing it does not
  make their exit fills real, and the report says so beside the table.

Kill rule for A3, before its data exists: a **prospective comparison from
the first fill**, read at every session close-out. If, on the same fills,
the live trailing exit's mean realised R is below the `baseline` control's
simulated mean, that is the signal to revert A3 in one commit and record the
reversion here. Thirty trades is a review of implementation and costs
(does the stop move, does IBKR honour the modify, what does the trail cost
in whipsaws), not a basis for choosing a tail-dependent exit rule: the
review's illustration — detecting a 0.2 R improvement at 80 % power needs
roughly 196 independent pairs at a 1 R standard deviation and 441 at 1.5 R —
is an independence-assuming figure, and these pairs are not independent.

**Execution specification, read from the code (2026-09-21, review item 4):**

| question | answer | where |
|---|---|---|
| when does trailing begin | at the entry fill; the first high considered is the first print after `orders.fill_ts` | `Runner.trail_stops`, `ledger.high_since` |
| what is "the high" | the higher of the 10-second bar highs and the quote-tick **bids** the desk wrote since the fill; the last-trade price is not used | `ledger.high_since` |
| how often does the stop move | every runner loop, 5 s, after the fill sync; only when high − 1 R/share is at least one cent above the resting stop | `scripts/exercise.py` `manage_exits` |
| what does a move do at the broker | re-prices the resting stop leg in place: same order id, new trigger, so the broker holds a stop at every instant | `PaperTrader.move_stop` |
| a reconnect or restart | `orders.trail_stop` is carried into the adopted record; the next loop continues from the last level, never from the initial stop | `PaperTrader.adopt` |
| a refused move (leg gone, broker error) | the stop stays where it rests; an `order_events` row names the level it would have reached and why it did not | `Runner.trail_stops` |
| no tape since the fill | no move; the stop stays at its last level | `ledger.high_since` returns None |
| what the exit is called | `trail` when the stop that filled had been raised above the initial stop, `stop` otherwise | `PaperTrader.sync` |

**The stated cost of the rule (the review's example, adopted here).** A
trade that reaches +1.2 R has its stop at about +0.2 R; an ordinary 1 R
pullback then exits it — even if the stock later reaches +10 R. Evidence that
*holding* captures large moves is not evidence that a 1 R trail captures
them, and the hold-to-close control carries no stop at all. When the initial
risk is a few cents, 1 R sits inside normal fluctuation and the trail becomes
a coin-flip exit; the microflow NO-GO measured exactly that stop
distribution. A3 is kept as a forward test with this cost written down, not
as an improvement.

Implementation (2026-09-21 evening). `Runner.trail_stops` runs every loop in
TRADE mode after the fill sync: for each filled position whose stop rests at
the broker it reads the high since the fill from the ledger's own tape
(10-second bars and quote ticks, `ledger.high_since`), and when
high − 1 R/share is at least a cent above the resting stop it re-prices the
stop leg in place (`PaperTrader.move_stop`: same order id, new trigger, so
the broker never stops holding a stop). `orders.trail_stop` and
`orders.high_since_fill` record every move; a stop that fills after being
raised is recorded with `exit_reason = trail`, one still at its initial level
with `stop`. Nothing written to the ledger since the fill means no move.
`TRAIL_R = 1.0` in `src/execution/intent.py`.

A finding made while landing it, recorded because it corrects this section:
**the live order path never carried a profit target.** `intent_from_decision`
is called without one, so every bracket the runner sent (VEEE, 09:37) was
entry + stop only. The "old rule" with its fixed 2 R target existed in
`journal.controls` (the *strategy* series) and on the verdict card, never at
the broker; the rule actually in force until today was initial stop + the
11:30 flatten. The A/B stated above still holds — controls keep computing the
fixed-target exit on every decision — but the control is a simulation on the
desk's tape, not a rule the desk ever traded.

**Amendment A4 — re-derive the `rising` gate threshold from measurement
(PROPOSED, 2026-09-21; measurement first, no threshold has changed).** On
2026-09-18 the cascade killed IMCC on `rising` at 3.65, 3.05, 6.00 and 6.25
during a 3 → 8 run — the MSGY shape (rejected untested, ran 2.54 → 5.43).
One sting is not a distribution, so the audit comes first:
`python3 scripts/gate_audit.py` (read-only) reports, for every kill gate,
how many killed plans later triggered, what the armed rule and hold-to-close
would have returned on them, their MFE, and every kill that went on to run
≥ 2 R, by name. A gate earns its keep only if the cohort it kills does worse
than the cohort it allows. Any threshold change is written here with the
audit's numbers beside it BEFORE the constant moves.

**A4 RESULT, 2026-09-21 — the `rising` gate is JUSTIFIED; nothing changes.**
The audit ran, and it contradicts the hypothesis that motivated it. Judged on
the only trustworthy column — the armed plan, capped at +2R / −1R, the rule the
desk would actually trade — the cohorts rank:

| cohort | n (triggered) | armed-plan mean R | verdict |
|---|---:|---:|---|
| allowed | 7 | **+0.714** | the bar to beat |
| `rising`-killed | 13 | **−0.231** | kills LOSERS — earning its keep, strongly |
| `price`-killed | 50 | +0.237 | worse than allowed — earning its keep |
| `catalyst`-killed | 99 | +0.514 | A2 already flags, does not kill |
| `float`-killed | 30 | +0.900 | kills a BETTER cohort — the one real cost |

The IMCC sting that motivated A4 was **one row**, and on the armed rule it was a
loss (`first_hit stop`). Its +104 R MFE is an artefact, not a miss: the stop was
a few cents, so a small dollar move is a huge R multiple that no real fill on a
2–9-cent stop would honour. The same artefact inflates every `hold-to-close`
and `MFE` figure in the audit (MEDS +281 R MFE, RETO +348 R) and is the very
thing the microflow NO-GO named. **The `rising` threshold is not changed.** A4
is closed: the measurement said the gate is right and the sting was noise.

What the audit did surface is `float`: on the armed column it kills a
better-than-allowed cohort (+0.900 vs +0.714). But float < 20M is a Confirmed
Ross pillar, n=30 is small, and the same micro-stop contamination sits on top
of it, so this is logged as **a question for a later amendment with clean
stops, not a change now.** No constant moves on the strength of stops no fill
would honour.

**Amendment A5 — the float gate flags; the Five Pillars become a count
(owner, 2026-09-21).** Owner's words, 07:2x ET: *"even if the float is not
respected and you see a potential, why not drop it and take the trade? … at
least 4 should be satisfied."* Evidence the same morning, `scripts/gate_audit.py`
on the armed-plan column (capped +2R/−1R): the float-killed cohort at
**+0.900 R** against the allowed cohort's +0.714 — the only gate that killed a
better cohort than it kept. The price gate, on the same column, kills a worse
one (+0.237, median −1) and **stays a hard kill**.

The rule, in `cascade.py`: `FLOAT_GATE_KILLS = False`; the float gate is still
evaluated and still reads FAIL / MANUAL over the cap; a new gate `pillars`
after gate 3 counts price, gain ≥ 10 %, RVOL ≥ 5×, float < 20 M and catalyst,
UNKNOWN counting as not passed, and **kills below `PILLARS_MIN = 4`**. So a
27 M float with the other four green is 4/5 and alive; the same float with no
catalyst is 3/5 and killed on `pillars` — never silently through two flags.
`RULE_SETS` carries A5; R11 classifies pre-A5 float kills as superseded under
A2. Rules hash moves (`floatGateKills`, `pillarsMin` in the fingerprint). Not
a Ross rule: float < 20 M is a Confirmed pillar and this is a deviation made
by the owner, measured forward. **Effective from the next desk start** — the
running desk of 2026-09-21 keeps the rules it started with.

Kill rule for A5, before its data: if after 30 taken trades the
`float`-flagged cohort's realised R is below the allowed-with-float cohort's,
A5 is reverted.

**A5 truth table (review 2026-09-21, item 5).** The count is over exactly
five pillars — price, gain ≥ 10 %, RVOL ≥ 5×, float < 20 M, catalyst dated
today — and the gate passes at 4 or more. Price is a hard kill at gate 1, so
a name that reaches the count has already passed it; the count is therefore
1 + the number of the other four that pass, and the table has four columns
that matter. UNKNOWN never counts: a float the desk does not have, or a
catalyst the desk could not look for (no feed), is a pillar not passed.

| gain | RVOL | float | catalyst | count | gate |
|---|---|---|---|---:|---|
| ✓ | ✓ | ✓ | ✓ | 5/5 | pass |
| ✗ | ✓ | ✓ | ✓ | 4/5 | pass |
| ✓ | ✗ | ✓ | ✓ | 4/5 | pass |
| ✓ | ✓ | ✗ or UNKNOWN | ✓ | 4/5 | pass — the case the owner asked for |
| ✓ | ✓ | ✓ | ✗ or UNKNOWN | 4/5 | pass — the A2 case, no longer silent: it is counted |
| any two of the four ✗ / UNKNOWN | | | | 3/5 | **kill on `pillars`** |
| three or four ✗ / UNKNOWN | | | | ≤ 2/5 | **kill on `pillars`** |

What is **outside** the count and unchanged by A5: the price band (gate 1,
hard kill), the instrument, tick-size, reverse-split and buyout checks, the
`rising` gate (gate 4, hard kill — it is not a pillar and a name cannot
"substitute" its way past it), the halt WAIT, the feed and session-window
checks, and every Layer 2 chart gate. The review's concern that a name could
fail `rising` and still pass the count does not arise: `rising` is evaluated
after the count and kills on its own.

Two consequences the table makes visible: with a dead news feed every name
that also misses one of gain, RVOL or float is killed (UNKNOWN counts as
not passed), so A5 is stricter than A2 alone on a desk with no headlines;
and float and catalyst are jointly decisive in exactly one way — a name may
lack one of them, never both.

**The measurement the review asked for, separated from the four-of-five
policy.** `scripts/gate_audit.py` now prints a *float-only cohort*: every
prospective decision recorded `killed_by = float` is re-evaluated from its
stored inputs with the float and catalyst gates switched off, and only the
rows that are then allowed failed nothing but float. The cascade records the
gates after the first kill as NOT_APPLICABLE (`gates_json`), so the
first-kill column cannot answer this; the re-evaluation can. The read-out
reports the float-only rows, the rows that also failed another gate (by
gate), and the armed-plan series on the float-only rows beside the allowed
cohort. This ledger is on the owner's machine; the numbers go in
`docs/REVIEW-PACK-2026-09-21-v2.md` when the owner runs it.

**Relevance of a headline — the shared-tag rule (2026-09-21, display and gate
3 label; verdicts unaffected).** "Why Is Critical Metals Stock Soaring
Monday?" arrived on GLND's card because the provider tagged it to both. News
records now carry every tag; a headline tagged to several names that does not
contain THIS ticker is labelled **Shared tag — about <other>** on the card and
does not count as this name's catalyst in `_catalyst_today`. Gate 3 flags
rather than kills (A2), so the change moves `decisions.catalyst` and the
`strat·news` split, never a verdict — R11 is untouched.

**Clarification C1 — staleness is measured from the bar's close
(2026-09-21).** The runner refuses a decision older than 120 s. `ts_et` is the
bar's OPEN, and a 1-minute decision cannot exist before its bar has closed, so
the old arithmetic charged every plan 60 s it never had: a plan the runner saw
70 s after the close read as "130 s old" and was refused (GRML, 07:43). The
budget is unchanged at 120 s; the clock now starts at open + bar length. This
is a definition, not a loosening — the same plan is stale at the same moment
of the market, and it is now named correctly.

The refusals that motivated it (142–400 s on 2026-09-21, 08:47–09:25) had a
second cause that C1 does not fix and is fixed separately: the scanner union
ran on the same thread as the 3-second session rebuild and starved it for most
of every 120-second period. It runs on its own thread from the next desk start,
and the rebuild logs its own duration when it exceeds 2 s.

**The first order, and Amendment A6 (2026-09-21, 09:37 ET).** VEEE, trigger
16.33, stop 16.31: a 2-cent stop on a $16 stock, sized by the rule "the stop
defines the size" to 1,000 shares — $16,330 of notional on $2,288 of equity.
IBKR rejected it in the same second (error 201: initial margin 14,439 EUR
against equity-with-loan 2,288 EUR; small caps carry ~100 % initial margin).
The stop leg cancelled with the parent. Nothing rested. Two defects it exposed,
both fixed the same hour:

- **The account bounds the size.** `sized_for` takes the smaller of the
  risk-sized count and what NetLiquidation can hold (read once at connect);
  a position sized by funds carries LESS than the stated $20 of risk, never
  more, and says so in its note. `refusals` guards the same bound.
- **A6 — the spread gate on the 1-minute path (tightening).** The runner now
  refuses an entry whose stop is inside `SPREAD_K = 4` × the desk's live
  spread. Same arithmetic as the 10-second study — the spread costs 1/k R per
  round trip against a +2 R target, so k=4 caps it at 0.25 R. The 10-second
  study used k=8 because its dips are a nickel deep; on the 1-minute path the
  18 September counterfactual put the median spread at 25 % of the stop, so
  k=4 admits the median setup and refuses the fee-only tail (5 of 39 trades
  there had a spread wider than the whole stop; VEEE's 2-cent stop against a
  1–2 cent spread is the same case). Tightening against oneself needs no
  owner acceptance; it is recorded so its refusals can be counted, and the
  constant moved by amendment if it starves the exercise.
- **A rejected order counted as a live position.** IBKR's word for rejected
  is `Inactive`; it was missing from the dead list, so the one-position rule
  blocked every entry after 09:37 ("1 order(s) alive or unresolved").

**Amendment A7 — the catalyst gets one word (2026-09-21, 10:42 ET; gate 3
input, flag-only under A2; the `pillars` count moves).** "Why Is Greenland
Mines Stock Surging on Monday?" sat on GRML's card graded *Unclassified* and
counted as the news pillar. A story about the move is not its cause. Two
families no longer count as a catalyst dated today in `_catalyst_today`:
**reaction pieces** (why-is / surging / soaring headlines with no catalyst
word in them) and **dilutive** headlines (an offering is a supply event, not
a reason to buy). Every decision now records `catalyst_verdict`, one of
STRONG / WEAK / NONE / DILUTIVE / UNKNOWN (`momentum_platform.catalyst.
news_verdict`), and the card leads with the same word: STRONG and WEAK pass
the pillar, the other three fail it. Which families count is this desk's
Approximation of "news today"; the word is on every row so the STRONG / WEAK
/ NONE split can be measured once there are outcomes. Effect on verdicts: a
name whose only headline is a reaction piece or an offering counts one pillar
fewer, so a 4/5 built on such a headline is now 3/5 and killed on `pillars`
(A5). Decisions before the next desk start keep their rules hash; R11
classifies the difference as superseded, not diverged.

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
