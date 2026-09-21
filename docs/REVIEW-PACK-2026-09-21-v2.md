# Review pack v2 — response to the 2026-09-21 external review

**PROVENANCE** · answers the external review of `docs/REVIEW-PACK-2026-09-21.md`
(the original is kept; its four over-strong conclusions were reworded under
item 1 and it says so at its top) · repository `WACROFOO/day-trading-bot`,
branch `claude/playbook-pullback-explanation-tg5c33`, commits `26cdb4c` →
the commit that adds this file, one per item · written 2026-09-21 evening,
after the 11:30 ET hard stop of the first phase-B session · test suite green
at every commit (740 tests at the last).

**What this file can and cannot contain.** The owner's ledger
(`data/journal.sqlite`) lives on the owner's machine and is not in the
repository. Every measurement the review asked for is now produced by a
command; where the number needs that ledger, this file names the command and
the line to read, and leaves the number to the owner's run. No figure below
was typed from memory. Where a tool output on the **synthetic fixture** is
quoted it is labelled synthetic and proves plumbing, never a market.

> ⚠ Paper account only (IBKR `DUR339781`). No real money. The 894-session
> replication was negative expectancy (item 10). Status: **paper
> commissioning** until one fully reconciled trade lifecycle exists (item 11).

## What changed, item by item

| # | review point | what landed | where | numbers |
|---|---|---|---|---|
| 1 | conclusions stronger than the evidence | the four statements are hypotheses with n and cohort; a contamination statement leads the pack | `docs/REVIEW-PACK-2026-09-21.md` | unchanged; 192 / +0.452 / +0.461 confirmed by the review |
| 2 | 66 − 65 − 0 = 1 | every allowed decision reconciles to a named outcome; `EXPIRED` for a plan no runner judged; residual printed | `ledger.reconcile_allowed`, `expire_pending`; `exercise.py report` ALLOWED RECONCILIATION line | owner: `python3 scripts/exercise.py report`, the line under FUNNEL |
| 3 | controls undefined; no like-for-like exit table | hold_close and random_bar carry NO stop; "close" = last bar the desk recorded (11:30, not 16:00); no costs anywhere; three exit variants on one entry, bar-ordered | `src/journal/controls.py` docstring, `exit_variants`, `simulate_exit`; both reports | owner: report block EXIT VARIANTS |
| 4 | A3 execution unspecified; adopted on thin evidence | execution table read from the code; the +1.2 R → 1 R pullback cost written in; A/B = live A3 vs simulated baseline and no_target; kill rule from the first fill | `docs/preregistration.md` §5 A3 | — |
| 5 | A5 not isolated; needs a truth table | truth table; `rising` is outside the count; float-only cohort by re-evaluating stored inputs (first-kill column cannot answer it) | `docs/preregistration.md` §5 A5; `scripts/gate_audit.py` *float-only cohort* | owner: `python3 scripts/gate_audit.py` |
| 6 | A2 argued from a dead feed | FOUND / NONE / UNKNOWN kept apart; A2 restated as a deliberate test; expectation written before the count | `docs/preregistration.md` §5 A2; `gate_audit.py` *catalyst states* | owner: same command, block *catalyst states* |
| 7 | "median dip inside the spread" not shown by 0.41 | it did not fire; the k-survival line did; verdict renamed; +0.25 R derived; 37 non-independent; session two kept | `research/paper-exercise/reports/2026-09-21-microflow-phase0-nogo.md`, `docs/PLAN-10s-micro-pullback.md`, `src/momentum_platform/microflow/measure.py` | 0.4091 < 1; 2 / 37 clear k = 8 (from the original run) |
| 8 | R0 must be fixed at the fill | `r0_violations` check in the ledger and the report; three trail moves leave realised R unchanged (test) | `src/journal/ledger.py`; `tests/test_runner.py` | — |
| 9 | statistical unit unclear | rows, unique setups, unique symbol-days, sessions, per-session series, top-3 symbol-day share | `controls.units`; both reports, STATISTICAL UNIT | owner: report block |
| 10 | reconcile with the 894 sessions | section below | this file | from the named reports |
| 11 | phase gate misused | the A→B pass stands; prospective B→C needs one reconciled lifecycle; 30 trades do not unlock pre-market alone | `ledger.reconciled_lifecycles`; `day.py gates_for_advance`; §3 | — |
| 12 | one clock for three delays | `bar_end_ts`, `clocks_json` (published, runner_seen, quote_ts, both delays); refusals name the clock; backfill stays backfill | `src/journal/ledger.py`, `src/execution/runner.py`; §5 C1b | — |
| 13 | event ordering and order state | six tests, three fixes; the halt known-positive found the collector defect (below) | `src/execution/runner.py`, `src/execution/ibkr_trader.py`, `src/momentum_platform/dashboard/ibkr_desk.py`, `src/momentum_platform/dashboard/session_builder.py` | — |

## Item 8 — the sizing caveat and what a paper fill can prove

With a 3-cent stop the rule "the stop defines the size" gives about 666
shares at $20 of risk. A 15-cent adverse print on that position loses about
$100 before fees: five times the intended risk, from a stop that was never
fillable at its level. A3 changes when the position exits; it does not
change this arithmetic, and neither do paper fills. The account cap landed
with the first order (`sized_for`, §5 A6) bounds notional, not this.

IBKR's paper account fills against the top of the book with no deep-book
access, and simulates stop and complex orders. Paper fills validate that
the integration works (orders leave, legs rest, fills are read back, the
ledger closes); they establish nothing about live execution quality, and
every R figure built on them is optimistic by an amount the exercise cannot
measure from inside. Stated here so that no later pack quotes a paper fill
as a fill.

## Item 9 — the power illustration, labelled

Under simple independent paired-observation assumptions, detecting a 0.2 R
improvement at 80 % power with a two-sided 5 % test needs roughly 196 pairs
when the standard deviation of the paired difference is 1 R, and roughly 441
at 1.5 R. The pairs here are not independent (several rows per symbol-day,
one morning per session), so those are lower bounds on an unknown quantity
and are printed as a caveat, never as a plan.

## Item 10 — reconciliation with the 894-session negative replication

The review asked what produced the negative result and what in this
exercise is actually different. Read from `research/momentum-replication/reports/`
(nothing re-derived):

**What was measured, and how it failed.** `2026-08-regime-filter.md`: daily
bars, 2,410 symbols, December 2022 to August 2026, 8,828 qualifying
symbol-days over 894 sessions under the same Layer 1 gates (open $2–20, gap
≥ 10 %, no split days). The rule tested was *buy the 09:30 open, exit on a
level or at the close*. Every year is negative on mean open→close (−6.25 %
in 2022 to −1.60 % in 2025; −3.02 % for 2026), 67–78 % of names close red,
and every stop/target cell is negative on the pessimistic bound. The
mechanism the report names: the favourable excursion is a **fat right tail**
(mean MFE +13.76 %, median +5.09 %) against a −10.64 % median drawdown, so a
target close enough to be hit reliably is too small to pay for the losers
and one large enough to matter is hit too rarely. The regime is not
persistent (r ≤ 0.09 at every lookback), so it cannot be timed.

**The cost layer.** `2026-08-pine-v8-benchmark.md`, 330 ticker-days, 20
fills in both engines: at the $2,000 / $20-risk basis commissions are
~18 % of nominal R (a stop-out is two orders = $2 = 10 % of a $20 budget),
and 25 % of fills touched trigger and stop in the same minute — an
ambiguity the daily-bar study could not even see. `2026-08-short-hold.md`:
the median return is negative at every holding period from 5 minutes to the
close, and entering before the open is worse than entering at it in every
pairing.

**The entry layer.** `2026-07-july-calibration.md`: of 61 session-ticker
pairs he named, 100 % were in the pool, 31 % passed the five pillars and 3
survived the entry rules — the universe is not the problem; the gates and
the entry are where the method is lost. `2026-08-target-and-entries.md`:
the 2:1 reward veto was anti-correlated with the chart gate (setups that
passed the gate had *closer* targets), and the losses were entries, not
tight stops.

**What is different here, stated without claiming it is enough.** This
exercise enters on a first pullback on the desk's own 1-minute tape after a
confirmed move, with a structural stop, inside 09:30–11:30, on names the
cascade passed at that minute — the intraday method the daily-bar study
explicitly says it could not represent ("this does not show that the
strategy fails — it shows that the daily-bar version of it fails"). It also
records the NBBO at every decision and fill, so the same-bar ambiguity and
the spread cost are measured rather than assumed. That is the whole of the
difference. It removes one stated blocker of the replication (no intraday
data); it does not remove the tail-versus-median structure, the commission
toll at $20 risk, or the negative median at every horizon, and six
compromised sessions with zero fills do not overturn a 894-session result.
Until the failure condition in `docs/preregistration.md` §4 is evaluated at
phase D on realised R, the standing verdict is the replication's.


## Item 13 — what the defect search found

Six tests were written first; three passed against the existing code and
three needed a fix. The known-positive halt test found the largest defect
of the pass.

- **(a) within-bar look-ahead** — `simulate_exit` tests the low against the
  stop in force before the bar, then the target, then lets the high raise
  the trail. The test writes out what a raise-first implementation returns
  on the same bar (+1 R) against the correct answer (−1 R).
- **(b) no fill inside the decision candle** — asserted on every actual and
  every exit-variant row: the entry bar is strictly after the decision bar.
- **(c) partial fills** — the stop leg's quantity is read from the broker on
  every sync (`orders.stop_qty`); a leg covering fewer shares than were
  filled is a RECONCILE line, an order event, and a bar on new entries.
- **(d) reconnect recovery** — the runner reconciles broker positions and
  working orders at start, before anything can be sent; while an untracked
  position, a quantity mismatch or a short stop stands, every entry is
  refused with the reason.
- **(e) duplicates** — a second step places nothing; a repeated or differing
  exit callback closes the row once.
- **(f) flattening** — "flat" is the broker's position state, re-asked every
  loop after the hard stop; NOT FLAT until `positions()` is empty, then
  "flat confirmed from broker position state" once.

**The halt collector.** Feeding a ticker with `halted = 1` through the live
desk wrote **no** `halts` row. Cause: a transition was emitted once, in the
rebuild that observed it, and the session builder journals a halt only
inside a minute frame at or after its stamp; a halt is always observed in
the forming minute, so the record had no frame, was dropped, and was never
re-offered. The desk now keeps every transition for the session and
re-offers it on each rebuild; the builder flushes halts stamped after the
last frame into the ledger, the hot state and the newest frame. What seven
empty sessions could mean, now separable: there were no LULD pauses on the
desk's names (possible, unmeasured), the collector could not see them
(this defect — every halt in the forming minute was lost), or coverage was
missing (a name not subscribed). The table can now say which; before this
it could not. Every measurement that said "a halt inside a dip is not
detected" was unverified and stays so until a live pause is recorded.

## The six questions, answered

| question | the review's answer | this response |
|---|---|---|
| A3 now or after 30 baseline fills? | begin a prospective comparison once the pipeline works; retain the baseline; do not adopt on current evidence | **Owner's decision stands: A3 runs live as a forward test.** The review's method is adopted: the fixed-target baseline and the stop-only rule are simulated on every fill from the first one, bar-ordered, and the stated cost of A3 is written into the amendment. "After 30 fills" is withdrawn. |
| Would I make A5? | as an explicitly experimental variant, yes; separate float relaxation from four-of-five | **Accepted as written.** A5 is labelled experimental, its truth table is published, `rising` is shown to be outside the count, and the float-only cohort is measured on its own by re-evaluation. The four-of-five policy itself is the owner's and is not defended as an improvement. |
| Leave the passed phase gate unchanged? | preserve the historical pass; revise readiness prospectively | **Accepted.** The A→B pass is not rewritten; phase C now needs one fully reconciled lifecycle; status is paper commissioning. |
| Staleness: conservative or fill-starving? | the timestamp mixes delays; fix the model before the threshold | **Accepted.** Four clocks are recorded, the refusal names the failing one, the 120 s budget is untouched and applies to the bar clock. |
| Is one session enough for the micro NO-GO? | enough to pause; the stated stop condition was not shown | **Accepted.** The report says the median-dip condition did not fire (0.41), the k-survival condition did, the verdict is "poor initial execution feasibility; development paused", and session two is collected. |
| What defect class next? | event ordering, within-bar look-ahead, order-state reconciliation, silent data-source failure | **Accepted and done** (item 13). The silent-failure class produced the halt collector finding. |

## Commands the owner runs to complete the numbers

```
python3 scripts/exercise.py report
python3 scripts/gate_audit.py
python3 scripts/microflow.py measure
```

The lines to lift into a v3 of this file: ALLOWED RECONCILIATION (item 2),
EXIT VARIANTS (item 3), STATISTICAL UNIT and the R0 check (items 8 and 9),
*float-only cohort* and *catalyst states* (items 5 and 6), and "dips INSIDE
the spread" (item 7). A number that is not in one of those outputs does not
go in.

---

*No claim of edge. Paper only. Written to be argued with; the review was,
and this is the result.*
