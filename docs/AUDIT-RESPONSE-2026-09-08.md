# Response to the independent document review — 8 September 2026

The review (a document-only audit by another assistant, supplied by the
owner) listed six blocking findings, a set of measurement corrections and
operational gaps. This page checks each claim against the code on branch
`claude/playbook-pullback-explanation-tg5c33`, says what was found, what
was changed the same day, and what is left for the owner to decide. It is
written for the owner first and for the next reviewer second.

Nothing here places an order, promotes a phase, accepts an amendment,
changes a risk limit or resets the ledger. Every code change below is
pinned by a test named next to it.

---

## 1. The six blocking findings

| # | claim | verdict against the code | what changed | pinned by |
|---|---|---|---|---|
| F1 | "Protection" has incompatible meanings; the monitored pre-market path is allowed on a `queued` verdict although §5 says phase C waits for the owner's acceptance | **Confirmed.** `src/execution/policy.py` returned "allowed" on the verdict alone | The `queued` shape now requires `a1_accepted="yes"` in the exercise state, which only `python3 scripts/exercise.py accept-a1 --confirm` sets, with the operator's name and time. Code never sets it. The stopping rule and the protection fields are separated in §5 (see 3 below) | `tests/test_premarket_path.py::test_policy_is_phase_c_and_a_definite_verdict`, `tests/test_day.py::test_premarket_needs_phase_c_and_a_probe_verdict` |
| F2a | The pre-registration names a different risk gate (`RiskLimits`, percentage-based) from the one the executor runs (journal gate: 3 losses, −3R, 6 entries) | **Confirmed.** `scripts/exercise.py live` wires `journal.risk.JournalRiskGate`; `src/paper_trading/risk_gate.py` belongs to the manual Streamlit app and reads a ledger this exercise does not write | `docs/preregistration.md` §2 now names the journal gate and its PROPOSED values | `tests/test_review_fixes.py` (gate wiring), doc |
| F2b | "Max concurrent positions 1" is a parameter in a document, not enforced | **Confirmed.** No check existed | `Runner._act` refuses an entry while any order is alive: resting, filled and not exited, exit pending, or an unresolved intent (`ledger.positions_alive`) | `tests/test_audit_fixes.py::test_one_position_at_a_time_refuses_a_second_entry_while_the_first_is_alive` |
| F2c | "5 sessions or 40 decisions, whichever is later" is ambiguous | **Confirmed** (the code already required both) | Wording is "5 sessions AND 40 prospective decisions" in the doc and the gate message | `tests/test_day.py::test_phase_a_is_blocked_until_sessions_and_probe` |
| F2d | Freeze a machine-readable configuration and record its hash with decisions and orders | **Confirmed gap.** The desk had a rules fingerprint (`desk_profile.fingerprint`) but nothing in the ledger carried it | `rules_hash` and `code_commit` columns on `decisions`, `orders` and `exercise_state`, stamped by the builder, the runner and the day command | `tests/test_audit_fixes.py` (intent tests read the stamped rows) |
| F2e | Distinguish probe/smoke orders from enrolled trades | **Already true, now stated.** Probes and the smoke test use `PaperTrader` directly and never write `orders`; the ledger's first `orders.placed_at` is a runner order by construction | Stated in §3 of the pre-registration | — |
| F3 | Backfilled decisions must not count as prospective evidence | **Confirmed.** The funnel counted every decision; the phase A gate used that count | `funnel()` splits `plans_prospective` from `plans_backfill`; the gate uses prospective; the runner refuses a backfill row in every mode with the reason recorded | `tests/test_audit_fixes.py::test_backfill_decisions_are_refused_and_excluded_from_prospective_counts` |
| F4a | The ledger row is written after the send, so a crash between broker acceptance and the row leaves a PENDING decision that a restart would place again | **Confirmed.** `Runner._act` called `place_bracket` then `record_order` | An intent row (status `intent`) and the decision's `CLAIMED` outcome are committed before `placeOrder`. Every leg carries `orderRef = decision_id`. On start, `reconcile_intents` finds a claimed intent at the broker by that reference and writes its ids, or marks it `UNRESOLVED` for a human. Nothing is ever resent | `test_the_intent_row_and_the_claim_exist_before_the_order_is_sent`, `test_a_send_that_raises_leaves_a_claimed_intent_that_is_never_resent`, `test_an_intent_the_broker_never_saw_becomes_unresolved_and_blocks_entries` |
| F4b | Two runners could claim the same decision | **Confirmed gap** | `exercise.py live` takes an exclusive lock beside the ledger file and refuses to start a second | manual: start two; the second exits 4 |
| F5 | The bracket transmit sequence is described as a guarantee against any unprotected entry | **Confirmed as overstated.** The sequence prevents premature release while the bracket is assembled; it says nothing about a child rejected later, a disconnect or a quantity mismatch | Wording corrected in `src/execution/ibkr_trader.py` and the review pack. `Runner.reconcile_positions` compares broker longs with the ledger each loop: an untracked position, a quantity mismatch, or a filled row with no working exit (no resting stop, no monitored stop, no sell sent) is flagged for a human | `tests/test_audit_fixes.py::test_reconcile_positions_flags_a_long_with_no_working_exit_and_an_untracked_one` |
| F6 | "LOG_ONLY" was claimed for the day while the orchestration dispatched an order-placing probe | **Confirmed.** `scripts/day.py` ran `premarket_probe.py` (which places and cancels an unfillable bracket) automatically at 07:00 | The probe is off unless `--probe-orders` is passed. Order-capable entry points are listed in section 4. A test drives the whole observational loop against a broker double whose order surface explodes | `tests/test_live_chain.py::test_a_log_only_day_never_reaches_an_order_function` |

## 2. Measurement corrections (section 4 of the review)

| claim | verdict | what changed |
|---|---|---|
| Overwriting a decision or a bar loses the original point-in-time record | **Confirmed.** The STALE→LIVE upgrade and the fuller-minute rule rewrote in place | `decision_revisions` keeps every write that changed a decision row; the `decisions` table is the latest projection. Bars keep the fuller aggregate (the partial one is a fragment of the same minute, not a different observation); the completion status is implicit in the volume monotonicity and is a known limitation |
| The NBBO at "the moment the fill was seen" is the poll time, not the execution time | **Confirmed** | Every quote change is appended to `quote_ticks`; a fill is joined to the quote in force at the broker's execution stamp, within 30 s, and `orders.nbbo_source` says whether it was that join or the poll fallback |
| Hold-to-close on the same names is an exit-policy control, not a selection control | **Accepted as a design point.** The controls in `src/journal/controls.py` are what the brief pre-registered; a matched-sample selection control needs a frozen candidate universe per session, which the ledger now records (`candidates` table since 8 September) but no control consumes yet | Owner decision 5 below |
| Sixty trades is a pilot budget, not a power calculation | **Agreed; the pre-registration already says so** ("not a power calculation") | §3 reworded to call phase D a capped feasibility pilot |
| Finer detector resolution is a new strategy version | **Agreed** | §7: a finer resolution feeding the detector starts a new cohort; archival-only finer data does not |
| Timestamps: store provenance, never invent an exchange stamp | **Partly true today.** Bar and quote stamps are the provider's; the fill time is the broker's log stamp since 8 September; the decision's `recorded_at` is the desk's clock | Left as is; the fields are named in the ledger schema comments |

## 3. Owner decisions the code will not make

1. **Amendment A1.** Accept the monitored pre-market exit (no stop at the
   broker; the runner is the stop) or keep pre-market observation-only in
   phase C. The review recommends observation-only. Recording acceptance is
   `exercise.py accept-a1 --confirm`; nothing else turns it on.
2. **The PROPOSED values** in `docs/preregistration.md`: dollar risk, phase
   sizes, the journal gate's three limits, the −20R stop. They bind when
   replaced in a commit that precedes the first runner order.
3. **Whether pre-market entries stay in the exercise at all**, given that
   every backtest measured 09:30 entries and pre-market is the unmeasured
   path the brief wanted to measure.
4. **The read-out n.** Sixty as a capped pilot, or a different cap.
5. **Controls.** Keep hold-to-close and random-entry as the pre-registered
   comparisons, or add the matched-candidate selection control the review
   proposes before enrolled trades begin.

## 4. Order-capable entry points (inventory)

| entry point | places orders | how it is gated |
|---|---|---|
| `scripts/exercise.py live --trade` | yes | phase B or C in `exercise_state`; the day command passes `--trade` only then; single-writer lock |
| `scripts/premarket_probe.py` | yes, an unfillable bracket, then cancels | manual, or `day.py --probe-orders` |
| `scripts/restart_probe.py` | yes, an unfillable bracket, then cancels | manual only |
| `scripts/paper_trade_smoke.py` | yes, an unfillable bracket, then cancels | manual only |
| `scripts/exercise.py ah-exit ID --confirm` | a sell | manual, `--confirm`, recorded with the operator's name |
| `scripts/ibkr_paper_preflight.py` | what-if only | manual |
| desk (`momentum_platform`) | never | two tests fail if an order path appears |

## 5. What this response does not claim

- Passing tests demonstrate the tested cases. The pre-market path has no
  live evidence; the REVIEW verdict has not been produced on real bars.
- The broker doubles in the tests model acknowledgement, fills and
  positions; they do not model IBKR's paper simulation of stops.
- Warning 2109 was observed once, on one contract, in the paper
  environment, at 08:06 ET on 8 September. The probe's raw output is kept in
  the session log; the verdict rule generalises only that observation.

*Paper only. Every figure in the reports is selection quality, never edge.*
