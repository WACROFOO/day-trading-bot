# Review pack — 2026-09-21 · first TRADE session, and the week that led to it

**PROVENANCE** · repository `WACROFOO/day-trading-bot`, branch
`claude/playbook-pullback-explanation-tg5c33`, commits `86e0ded` → `6a24294`
(15 commits since the previous pack, `docs/REVIEW-PACK-2026-09-18.md`) ·
ledger `data/journal.sqlite`, sessions 11–18 September 2026, six session
days, 557 decisions · read-outs run by the owner on 2026-09-21 05:05 ET:
`scripts/exercise.py report`, `scripts/microflow.py measure`,
`scripts/gate_audit.py` · this document written 2026-09-21 ~08:20 ET while
the first phase-B session was running.

**For the reviewer.** You are reading this cold. Everything you need is in
this file; the repository paths are given so claims can be checked, not so
you have to read them. Numbers come from the tool outputs named above and
nowhere else. Where a number is contaminated, the contamination is named
beside it. The questions for you are in §9.

> ⚠ **Paper account only (IBKR `DUR339781`). No real money. The 894-session
> replication of this strategy was negative expectancy.** Nothing here is a
> claim of edge; the exercise measures selection and cost.

---

## 1. What this is, in five lines

A mechanical replication of Ross Cameron's small-cap momentum method: a
scanner finds gappers, a cascade of gates rejects most of them, a first-pullback
detector arms a plan (entry, structural stop, 2 R target), a runner places a
bracket on the paper account, and a ledger records every decision with the
inputs it was made from so it can be re-judged later. Sizing is the owner's
$20 per trade; results are in R. The desk starts itself each weekday at 06:55
ET via launchd, trades 09:30–11:30, flattens at the hard stop.

## 2. Where the exercise stands

| | |
|---|---|
| phase | **B — TRADE** (entered 2026-09-18 09:0x ET; first orders possible today) |
| sessions recorded | 6 (11, 14, 15, 16, 17, 18 September) |
| decisions | 557 armed · 491 killed by the cascade · 66 allowed · 65 refused by the executor · **0 taken, 0 fills** |
| replay check R11 | 275 reproduce under the current rules; 282 reproduce only under superseded rules (A2 boundary); **0 diverged** |
| paper tape | `realtime` (alignment probe) |
| pre-market stop probe | **`queued`** — IBKR drops `outsideRth` on the stop leg; a pre-market bracket protects nothing (2026-09-18, second observation of the same behaviour) |
| pre-market trading (phase C) | not started; requires the owner to accept Amendment A1 (monitored exit). Not accepted, and the 8 September outside review advised against |

Zero taken trades in six sessions is explained, not mysterious: five sessions
ran with a dead news feed (a `.env` defect, §6.1) and the sixth started
mid-morning so every decision was backfill or stale. Today is the first
session with a working pipeline from 06:55.

## 3. The three measurements that decided this week

### 3.1 Controls — the exit rule is the problem (`exercise.py report`, 199 triggered prospective rows)

| series | n | mean R | median R | win |
|---|---:|---:|---:|---:|
| strategy (armed plan: +2R target / −1R stop / else close) | 199 | **+0.461** | −0.164 | 49% |
| hold to close, same entries | 199 | **+6.301** | −0.402 | 43% |
| random bar, same stop distance | 199 | +6.169 | −0.357 | 45% |
| strat · allowed only | **7** | +0.714 | +2.000 | 57% |
| strat · killed only | 192 | +0.452 | −0.189 | 48% |

Read mean and median together: most trades lose, a few run enormously, and the
fixed 2 R target sells exactly the runners. This is failure condition ② of the
pre-registration (`docs/preregistration.md` §6), observed in the ledger's own
controls.

**Contamination, stated:** 192 of the 199 rows are plans the cascade *killed*;
the allowed cohort is 7. And the giant means are inflated by stops of a few
cents — a 12-cent move on a 3-cent stop is +4 R on paper and unfillable in
practice. The direction (fixed target < hold) is strong; the magnitude is not
to be believed.

### 3.2 Phase 0 of the 10-second micro pullback — NO-GO (`scripts/microflow.py measure`)

One session, 10,320 ten-second candles, 13 symbols, 40 shapes (no context gate
applied — an upper bound), 37 quoted.

| | |
|---|---|
| median risk per share | **$0.05** (p25 0.03 · p75 0.14) |
| median spread ÷ risk | **0.41** — a round trip costs 0.41 R; the strategy's best case is +0.25 R |
| dips clearing k=8 | 2 / 37 (5.4%) |
| at k=4 | 24% survive, but the spread then costs the entire best case |

The pre-registered stop condition (`docs/PLAN-10s-micro-pullback.md` §4: *"if
the median dip is inside the spread, stop here"*) fired on the first session.
Phases 1–3 are not built. Report:
`research/paper-exercise/reports/2026-09-21-microflow-phase0-nogo.md`.

### 3.3 Gate audit — which gates earn their keep (`scripts/gate_audit.py`, armed-plan column, capped +2/−1 R)

| gate kills… | n triggered | armed-plan mean R | verdict |
|---|---:|---:|---|
| allowed cohort (the bar) | 7 | +0.714 | — |
| `rising` (already faded) | 13 | **−0.231** | kills losers — **justified, unchanged** |
| `price` ($2–20) | 50 | +0.237 | earning its keep — unchanged |
| `catalyst` | 99 | +0.514 | already a flag (A2) |
| `float` (< 20 M) | 30 | **+0.900** | kills a *better* cohort than it keeps — the one real cost |

The audit was written to test a suspicion about `rising` (IMCC killed four
times during a 3 → 8 run). The suspicion was wrong: on the tradeable column
that cohort loses, and IMCC's +104 R "MFE" was a few-cent stop. The
measurement contradicted the hypothesis that motivated it; the threshold did
not move. The audit surfaced `float` instead — and that became A5 (§4).

## 4. Amendments to the pre-registration (all in `docs/preregistration.md` §5)

| id | what | status | evidence |
|---|---|---|---|
| A2 | catalyst gate flags, does not kill | in force since 2026-09-17 | 254 of 389 kills were "no news" from a feed with no keys |
| A3 | **exit rule**: no fixed target; stop trails the high since entry by 1 R, ratcheting up | **PROPOSED — designed, not coded** | §3.1; kill rule: 30 trades, revert if it loses to the fixed-target control on the same fills |
| A4 | re-derive the `rising` threshold from measurement | **CLOSED — gate justified, no change** | §3.3 |
| A5 | float gate flags; the Five Pillars become a **count, ≥ 4 of 5 kills otherwise**; price stays a hard kill | **in force from the next desk start** (owner, 2026-09-21) | §3.3; owner's words: "at least 4 should be satisfied" |

Every amendment moves the rules hash, is carried in `cascade.RULE_SETS`, and
R11 classifies decisions made under a superseded set as *superseded* rather
than *diverged* — so an amendment never voids the log and never hides a real
defect (`src/journal/replay.py`).

A5 is a deviation from the method (float < 20 M is a Confirmed pillar), made by
the owner, pre-registered with its own kill rule, and measured forward.

## 5. Phase-gate audit — a gate that passed, examined

Phase A→B cleared on 2026-09-18. It was honest and it exposed a hole: the gate
counts *decisions*, and a REJECT is a decision, so phase A completed on a
pipeline that had allowed **zero** plans in five sessions. Recorded as a known
weakness, **not amended retroactively** — tightening a criterion after
watching it pass is the offence pre-registration exists to prevent. Mitigation:
phase B needs 30 *taken* trades to reach C; a desk that allows nothing takes
nothing. A proposed fix (require N `plan_allowed=1` decisions) is written with N
deliberately unset.

## 6. Defects found and fixed this week — the ones that matter

1. **`.env` reader took the first definition of a key** (`86e0ded`). The setup
   template's `paste_key_id_here` sat above the real Alpaca key; the news feed
   read "no source" for five sessions; the catalyst gate, failing closed,
   killed 254 names. Fixed: last definition wins, placeholders refused.
2. **A refused probe run recorded as `inconclusive`** and cleared the A→B gate
   (`1dc8d9a`). The gate tested `is None`. Now `not_run` records nothing and
   the gate rejects non-answers.
3. **R11 could not tell an amendment from corruption** (`9ab9b8e`): "282
   decisions do not reproduce" after A2. Three outcomes now.
4. **A stale plan stayed on the charts after the cascade killed the name**
   (`31fb2a5`): CPOP's card said "no plan is published" one line above "entry
   4.93 · stop 4.88 · target 5.03". `livePlan()` withdraws it.
5. **A scanner-joined name got no five-second bars, and the stall watchdog
   could not see it** (`32393ca`): it judged the connection, not the symbol.
   Per-symbol detection and re-request now.
6. **A second `day.py` on top of the scheduled one took the running desk's
   IBKR client id and knocked it offline** (`6a24294`). The desk process now
   takes an instance lock before touching the Gateway.
7. **A headline about another company shown as this name's news** (`b722fea`):
   provider tagging; now labelled "Shared tag — about X" and not counted.
8. **The simulated Level 2 spoke like the real tape** ("a seller above the
   trigger caps the move") (`c458653`). It now says it is an illustration.

## 7. What the desk looks like now (for orientation)

Own real-time charts from the IBKR stream (TradingView's open-source
renderer, vendored), 1-minute execution / 5-minute structure / 10-second micro;
VWAP, EMA 9/20/200, MACD; drawing tools (level, trend, measure in R, zone);
indicator menu per pane; verdict card driven by the server's cascade; Five
Pillars board; simulated Level 2 (labelled). TradingView's own delayed widget is
parked in the tray. Its full library is company-licensed and unavailable.

## 8. Open items, honestly

- **A3 is not coded.** The evidence for it is directional only (§3.1). It is
  the next change, with tests, for tomorrow's desk start.
- **Staleness budget.** Decisions are stamped at the bar's *start*; the runner
  refuses anything older than 120 s. Every 1-minute decision is ≥ 60 s old at
  birth. One pre-market refusal today read 130 s. If regular-hours setups are
  refused on staleness alone, the age should be measured from publication,
  not the bar clock. Waiting for evidence from today's session before changing
  a live rule.
- **The `halts` table has been empty for seven sessions.** Unexplained. Every
  measurement that says "a halt inside a dip is not detected" is unverified.
- **RVOL display** shows absurd values pre-market (GLND 8,123×) when the
  same-time baseline is near zero. Cosmetic, misleading; the pillar itself
  passes correctly.
- **Micro-stop contamination** runs through every R figure that is not capped.
  The fix is not a display change; it is A3 plus real fills, which give a
  realised-risk denominator.
- **Sample size.** 7 allowed rows. 0 fills. Nothing here is significant.

## 9. Questions for the reviewer

1. **A3 (trailing exit).** The controls say the fixed 2 R target forfeits the
   tail, but 192 of 199 rows are cascade-killed names and the means are
   inflated by micro-stops. Is a *forward test with its own kill rule* the
   right response, or should A3 wait for 30 fixed-target fills first so the
   control is real rather than reconstructed?
2. **A5 (float as a count, not a kill).** Evidence: +0.900 vs +0.714 on 30
   rows, same contamination. The owner wanted it and it is pre-registered.
   Would you have made the change on that evidence, and what is the minimum
   forward sample before it can be judged?
3. **Phase-gate hole (§5).** We chose not to tighten a passed gate. Do you
   agree, or is entering TRADE on a pipeline that never allowed a plan the
   bigger risk?
4. **Staleness (§8).** Bar-start stamping with a 120 s budget: defensible
   conservatism, or a rule that will quietly starve the exercise of fills?
5. **The NO-GO (§3.2).** One session, 37 dips. Is it decisive enough to close
   the 10-second idea, or should a second session have been captured first?
   The plan said two sessions; the first fired the stop condition by a wide
   margin.
6. **What did we miss?** The week produced eight structural defects (§6),
   several of which had been silently shaping results for days. Which class
   of defect would you look for next?

---

*No claim of edge. Paper only. Every number above is reproducible from the
named commands on the named ledger; the contaminations are named where they
apply. Written to be argued with.*
