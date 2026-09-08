# External review pack — 8 September 2026

Self-contained. Written to be pasted into another assistant for an
independent review; the reader has no access to this repository, so every
fact it needs is stated here, with the file it comes from named in brackets
for the owner's benefit. Nothing about real markets is claimed: the first
open-market session is running today, in log-only mode.

Companion documents, if the reviewer is given more:
`docs/paper-exercise-brief.md` (the requirements), `docs/preregistration.md`
(the pre-registered test), `docs/READINESS-2026-09-08.md` (the audit before
today), `docs/ASSESSMENT-2026-09-07.md` (plain-words status).

---

## 1. What this is

A paper-trading exercise that replicates Ross Cameron's small-cap momentum
method mechanically on Interactive Brokers (IBKR) and grades its own
selection quality. It is **not** an attempt to make money: two historical
studies in the same repository already found the method negative
(section 8). The exercise exists to measure, under live conditions that no
backtest reaches, what the method selects and what happens next.

The owner is neither a developer nor a trader. Paper account only; the
code refuses any account whose id does not start with `DU`, IBKR's paper
prefix, and there is no switch to turn that off.

## 2. Architecture in one picture

```
gap scan (finviz) ──► desk watches the names on IBKR real-time data
                              │
                       rule-checker (Layer 1 reject cascade)
                              │
                       pullback detector (Layer 2 setup, 1-minute bars)
                              │
              every armed plan written to the LEDGER (SQLite) at that instant
                              │
              runner, a separate process, reads the ledger every 5 s
              ├─ REFUSED  (reason recorded)
              ├─ LOG_ONLY (phase A — where the exercise is today)
              └─ TAKEN    (phase B+: entry + stop transmitted as one bracket)
                              │
              fills, exits, NBBO at the fill, then the grader adds what
              the stock did next; a nightly replay re-runs every decision
```

The desk and the runner never talk to each other. The ledger is the bus.
Nothing can be traded that was not first written down with everything that
was known at that moment.

## 3. The strategy as implemented

Source of every rule: `knowledge-base/strategies/FILTERS.md`, the repo's
"filter bible", which wins any conflict with any other file.

**Layer 0, scanner dials.** Wide, set once. The scanner discovers candidates;
it is never a gate.

**Layer 1, the reject cascade.** Evaluated before a chart is opened; the
first kill is terminal; an unknown input fails closed. Eight gates:

| # | gate | kill if |
|---|---|---|
| 1 | price | outside $2.00–20.00 |
| 2 | float | over 20M shares |
| 3 | catalyst | none dated today and no live theme |
| 4 | still rising | more than 25% off the pre-market high |
| 5 | reverse split | the gap is arithmetic (the split alone is not the veto) |
| 6 | instrument | fund or ETF |
| 7 | tick size | quotes in 5-cent increments |
| 8 | buyout | acquisition announced |

**Layer 2, chart gates, all true at entry.** Price above VWAP; holding the
9 EMA; MACD 12/26/9 positive and above signal; pullback volume lighter than
the impulse; first or second pullback. Trigger: the first candle to exceed
the previous red candle's high, intrabar. Entry = trigger + 1 cent; stop =
pullback low − 1 cent; planning target 2R. Plans freeze when armed and
never repaint.

**Verdict vocabulary.** The cascade emits REJECT, WAIT, WATCH, REVIEW,
STALE or LOG. It never says BUY, PASS or ARMED. REVIEW means every gate
passed and the chart must be read; it is the only verdict the runner will
trade on.

**Session.** Pre-market 07:00–09:30 ET, regular 09:30–16:00. Prime window
09:35–10:30, hard stop 11:30 ET: the runner flattens everything. No
overnight positions. After-hours is exit-only and requires a human to
confirm each exit by command.

**Sizing.** From the owner's stated dollar risk only ($20 today):
shares = risk ÷ (entry − stop), integer arithmetic. Results are expressed
in R. Paper buying power is never used.

## 4. Execution safety (phase B onward)

- Entry and stop are transmitted as one IBKR bracket; the stop leg carries
  the transmit flag, so the group is not released while it is being
  assembled. That is IBKR's documented use of the flag and no more: a child
  rejected later, a disconnect or a quantity mismatch is caught by reading
  order states back and reconciling broker positions against the ledger's
  exits every loop, not by the transmit sequence.
- The intent is written and committed before the send, every leg carries
  the decision id as its order reference, and a restarted runner matches an
  unacknowledged intent at the broker by that reference or marks it
  unresolved. It never resends. One runner per ledger, by file lock.
- Refusals before any order: plan not allowed, stop not below trigger,
  size outside 5% of the sized quantity, off the tick grid, after 11:30,
  wrong session, decision older than 120 s, no fresh desk quote within
  30 s for the symbol, verdict not REVIEW, pullback volume not lighter.
- A journal risk gate locks the day after 3 consecutive losses, −3R, or
  6 entries; the lock survives a restart and closes **entries only**.
  Exits, the monitored stop and the 11:30 flatten keep running.
- Pre-market: IBKR does not rest stop orders before 09:30 (today's probe:
  warning 2109, the outside-hours attribute is ignored for the stop type).
  A pre-market entry therefore gets **no resting stop**; the runner itself
  is the stop, selling at bid − $0.10 the moment the bid touches the level,
  and the record says `protected=0`. Phase C cannot start until the owner
  accepts that exposure in writing.
- A sent exit is recorded as `ExitPending` until IBKR reports the fill; the
  limit price of a sent order is never written as a fill.
- A restarted runner adopts its open orders from the ledger and matches
  them at the broker by IBKR's permanent id; verified live this morning.

## 5. The ledger, and why it is the deliverable

Every plan the detector arms, allowed or suppressed, becomes a decision row
with: symbol, the bar's own ET timestamp, session, the point-in-time
snapshot (last, bid, ask, session high, volume, RVOL, gap), float and its
quality, catalyst flag, halt flag, verdict, the gate that killed, every
gate's state, warnings, the full cascade inputs as JSON, trigger, stop,
target, and a deterministic id hashed from symbol, bar time, entry and stop.

Orders carry planned risk and realised risk (from the actual fill), the
NBBO bid/ask and sizes at the instant the fill was seen, exit reason,
exit price, protection status. Bars and quotes the desk saw are stored too,
so the grade is computed on the tape the decision was made on.

Twelve requirements govern it (`docs/paper-exercise-brief.md` §④):
R1 log the universe not the survivors; R2 point-in-time or it is not
evidence; R3 both R denominators; R4 NBBO at the fill or the fill is
unverified; R5 a control or the result is unattributable; R6 pre-register
success before the first trade; R7 sessions and the hard stop; R8
pre-market protection settled empirically; R9 halts first-class; R10
after-hours exit-only and never automatic; R11 nightly replay must
reproduce every decision; R12 score my own calls.

## 6. The pre-registered test (`docs/preregistration.md`)

| Phase | Mode | Runs until | Gate to next |
|---|---|---|---|
| A | log only, live desk | 5 sessions **and** 40 decisions (PROPOSED) | replay check 100%; probe verdict recorded; paper session on real-time data |
| B | trade, regular hours only | 30 taken trades (PROPOSED) | ≥90% of fills carry NBBO; zero unprotected entries |
| C | trade, pre-market added | 30 more (PROPOSED) | only in the shape the probe dictates |
| D | read-out at n = 60 | once | the failure condition below |

**Failure condition, evaluated once at n = 60 in realised R:** mean R ≤ 0,
**or** the strategy does not beat hold-to-close on the same rows, **or**
fewer than 80% of fills passed the NBBO plausibility check (then
"unmeasured", not failed). Passing earns phase E (n = 120), nothing more.

**Stopping rules:** risk gate latches 3 sessions of any 10; any unprotected
entry; any replay divergence; cumulative −20R (PROPOSED); any after-hours
exit without a logged confirmation.

**May not change until phase D:** any threshold or gate, the detector's
entry/stop logic, the failure condition, n. Tuning on paper fills is
forbidden explicitly: paper fills are optimistic and tuning on them
amplifies the error.

The values marked PROPOSED become binding when the owner replaces them in
a commit that precedes the first order in the ledger.

## 7. Where the exercise stands today

- 7 September (Labor Day, closed): connections rehearsed against the real
  Gateway; a restart probe verified order recovery; a smoke bracket was
  placed and cancelled on the paper account.
- 8 September, first open session, from 08:06 ET: desk live on IBKR
  real-time data, single login (the read-only desk and the writable
  executor share one paper session, so decision tape and fill tape are the
  same tape by construction). Runner in log-only mode. First decisions
  refused for stated reasons (before the 07:00 window; pre-market not
  allowed in phase A). Phase B cannot begin before 14 September.
- Findings from this first morning, all fixed the same day: a browser tab
  on the Gateway's API port blocked the desk's connection; the pre-market
  probe mis-read IBKR warning 2109 as a held stop; decisions armed from
  loaded history are now tagged `backfill` so they can be separated from
  plans watched live.

## 8. What the evidence already says (before the exercise)

From `research/momentum-replication/reports/` and `research/first-pullback-edge/`:

- 8,828 symbol-days over 894 sessions: buy-the-open on gappers is negative
  in every year 2022–2026; the regime is not persistent and a regime filter
  adds nothing (`2026-08-regime-filter.md`).
- The first-pullback state machine, ported from the Pine script and run
  point-in-time with costs over 3,627 trades, 1,453 sessions and eleven
  years: every variant's 95% CI below zero in every year and in a
  478-session holdout; a random entry minute beats it by 0.80 R
  (`research/first-pullback-edge/README.md`).
- Of 61 tickers he named, 100% were in the pool and structure was found on
  97%, but only 3 survived the entry rules: the scanner and the entry gate
  are where the method is lost (reports index headline).
- Every backtest enters at 09:30, while he names 07:00 far more often than
  09:30 (`2026-07-challenge.md`). The pre-market path is unmeasured; the
  live log is the only instrument that can measure it.
- The micro-pullback is often a 10-second pattern a 1-minute detector
  cannot see (`2026-08-streams-roundup.md`).

## 9. Known limitations, stated up front

- Paper fills are simulated; NBBO plausibility is the only check.
- Halt-resume behaviour is unmodellable from bars; only the live log
  accumulates it.
- A 1-minute bot may be measuring a different entry than the documented one.
- IBKR fundamentals are not entitled on this account: float falls back to
  finviz where the gap scan had it, else to SEC shares outstanding, which is
  an upper bound; above the 20M cap it reads UNKNOWN and fails closed.
- Layer 2's REVIEW verdict has not yet been produced on real bars; until it
  is, the trade path's entry condition is untested on live data.

## 10. Questions for the reviewer

1. **Design.** Does the ledger-as-bus design (desk writes, runner reads,
   never in-process) leave any path by which a decision could be traded
   without its point-in-time record? What would you add to the decision row?
2. **Pre-registration.** Are the phase gates and the failure condition
   well-formed? Is "beats hold-to-close on the same rows" the right primary
   control, or would you pair it differently? Is n = 60 defensible as "the
   point at which the controls become interpretable" given a per-trade
   stdev of about 31% measured in the replication?
3. **Look-ahead.** The grader scores decisions against same-day forward
   bars, only after the trigger was actually touched, and excludes
   untriggered plans from the controls. Where could a future value still
   leak into a recorded verdict?
4. **Pre-market protection.** IBKR ignores the outside-hours flag on stop
   orders. The proposed answer is a runner-side monitored stop at bid −
   $0.10, recorded as unprotected. Is there a safer shape, or a reason to
   drop pre-market entries from the exercise entirely?
5. **Backfill.** Decisions armed on history loaded at desk start carry
   today's catalyst/float/halt inputs and are tagged. Should they be
   excluded from the phase A decision count, counted separately, or is the
   tag enough?
6. **Failure modes you have seen elsewhere.** Given a non-developer owner
   running a one-command day on a Mac against IB Gateway, what operational
   failures would you expect that the readiness review may have missed?
7. **The premise.** Two large studies already found the method negative.
   Is a 60-trade live paper exercise a reasonable use of effort as a
   measurement of selection quality, or is there a cheaper design that
   answers the same question?

*Paper only. Every figure is selection quality, never a claim of edge.*
