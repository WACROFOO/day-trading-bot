# Ticks, execution costs and the Running Up tile — 2026-10-02

Paper only. This report measures execution and selection quality; it claims no
edge. The replication is negative expectancy
(`research/momentum-replication/reports/2026-08-regime-filter.md`).

**Out of scope:**
- The AMOD trade-by-trade review. It was answered in chat from the owner's
  pasted desk output; this checkout has no ledger.
- The orderflow-scalping material.

## 1 · Provenance

```
TAPE     Alpaca SIP prints + the prevailing NBBO: one quote at the fill, one at the exit
         cache data/cache/ticks/ · gitignored, NOT in the repo · 2024-01-02..2026-08-21
BARS     1-minute history cache data/cache/history/ · gitignored · last day 2026-08-21
SPLIT    ticks exist for 2024-2026 only, so there is no train period. The stricter rule applies:
         better in EACH year AND paired lower bound > 0 at α 0.05/49, then OFF until
         200 prospective trades.
         Running Up replay: train 2016-2023 · test 2024-2026
COSTS    real spread at each fill: ½ spread + 1¢ per marketable side + IBKR Fixed commission
         $40 risk · $2,000 notional cap · one position · the daily limits
PREREG   research/edge-hunt/PREREGISTRATION.md addenda 2026-10-02, -02b, -02c, -02d,
         each written before its read-out
CODE     tick engine c750541 · stage 2 9a3a26a · stage 3 19173f3 · cadence 92c404d
         execution and Running Up studies read the code at 92c404d · fixes e58a9d2
! The execution and Running Up studies ran in the session scratchpad. Their
  outputs and scripts are copied into the two 2026-10-02-* folders; their
  pickled inputs (alerts.pkl, events.pkl, the cached tick outcomes) are not.
  Paths inside those files that start /tmp/claude-0/… no longer resolve.
! Live-session facts come from commit messages and docs/preregistration.md.
  No live journal exists in this checkout.
```

Sources. Tags are used inline as `tag:line`.

| tag | file |
|---|---|
| T1 | `research/paper-exercise/reports/tick_replay_output.txt` |
| T2 | `research/paper-exercise/reports/desk_replay_output.txt` |
| T3 | `research/paper-exercise/reports/stage3_output.txt` |
| T4 | `research/paper-exercise/reports/cadence_output.txt` |
| X | `research/paper-exercise/reports/2026-10-02-execution-study/cost_decomposition_output.txt` |
| XP | `research/paper-exercise/reports/2026-10-02-execution-study/proposals_output.txt` |
| XP2 | `research/paper-exercise/reports/2026-10-02-execution-study/proposals2_output.txt` |
| XO | `research/paper-exercise/reports/2026-10-02-execution-study/open_cross_output.txt` |
| XJ | `research/paper-exercise/reports/2026-10-02-execution-study/study_result.json`: ranked proposals, rejects, reviews M1–M5 |
| XM1 | `research/paper-exercise/reports/2026-10-02-execution-study/review/m1_race_output.txt` |
| XM2 | `research/paper-exercise/reports/2026-10-02-execution-study/review/m2_output.txt` |
| XM3 | `research/paper-exercise/reports/2026-10-02-execution-study/review/m3_output.txt` |
| XM4 | `research/paper-exercise/reports/2026-10-02-execution-study/review/m4_report_output.txt` |
| XM5 | `research/paper-exercise/reports/2026-10-02-execution-study/review/m5_output.txt` |
| R | `research/paper-exercise/reports/2026-10-02-running-up-study/analysis_full.txt` |
| RR | `research/paper-exercise/reports/2026-10-02-running-up-study/results.txt` |
| RM | `research/paper-exercise/reports/2026-10-02-running-up-study/merge_checks2.txt` |
| RX | `research/paper-exercise/reports/2026-10-02-running-up-study/extra_stats.txt` |
| RB | `research/paper-exercise/reports/2026-10-02-running-up-study/robustness_check.txt` |
| RE | `research/paper-exercise/reports/2026-10-02-running-up-study/e1_check.txt` |
| RC | `research/paper-exercise/reports/2026-10-02-running-up-study/review/c1_check.txt` |
| RG | `research/paper-exercise/reports/2026-10-02-running-up-study/review/g1_check.txt` |
| RQ | `research/paper-exercise/reports/2026-10-02-running-up-study/review/g1_ci_q5.txt` |
| RJ | `research/paper-exercise/reports/2026-10-02-running-up-study/study_result.json`: diagnosis, ranked changes, rejects, reviews E1/C1/G1 |

## 2 · What was considered

```
TICKS       88,823 plans in the cache
            6,132 pass the live gates (rules_audit BASE)
            2,577 from 2024 on (1,666 symbol-days, 607 complete sessions)
            1,886 filled · 1,873 with a real spread at the fill            X:1-5 · T1:1
STAGE 2     7,477 plans the desk would arm mid-minute · 648 sessions         T2:1
STAGE 3     648 sessions · reference D 1,721 trades · 5 variants             T3:1-9
CADENCE     2,193 desk-time plans · 179 skipped (tape not cached)
            434 sessions · 4 arming × 5 loop settings                        T4:1
EXECUTION   9 ranked proposals · 8 rejected · M1-M5 adversarially reviewed   XJ
RUNNING UP  286,152 scanner events on 2,608 days
            174,920 rows reach the tile
            103,201 analysed 07:00-11:30 (train 59,606 / test 43,595)       R:1,25 · RM:1
            8 ranked changes · 12 rejected · E1, C1, G1 adversarially reviewed  RJ
```

## 3 · What survived, and what did not

Net R is per trade, with real spreads. ✗ marks the condition that failed.

### 3.1 · The replay stages

| stage | question | reading | status |
|---|---|---|---|
| 1 | Do 1-minute bars tell the truth about fills and exits? | Per-plan gap, bars minus ticks, mode A: mean +0.010, median 0.000, 5 fill disagreements in 1,886. Mode C: +0.012 and 1 (T1:11-12). | ✓ bars stay the backtest standard |
| 1 | What does the B portfolio earn on the real tape? | Gross −0.108. Proxy spread −0.475. Real spread −0.511 (T1:6-8). | measured |
| 2 | Does arming mid-minute, as the desk does, change it? | The order goes in a median 36 s before the minute closes (p10 6 s, p90 46 s). 243 plans pass only at desk time and 165 only at the close. Net −0.534 at desk time vs −0.511 at bar close (T2:3-4, 10-11). | informs only; addendum 02b lets it decide nothing |
| 3 | S3-dip: wait for a 10-s micro pullback | −0.452 vs D −0.542, better in every year, lb ✗ −0.004 (T3:4-5) | keep D |
| 3 | S3-confirm: skip a false break | −0.549, lb ✗ −0.124 (T3:6) | keep D |
| 3 | P-half2R: half the shares sold at +2 R | −0.529, lb ✗ −0.009 (T3:7) | keep D |
| 3 | P-half1R (reported only) | −0.504, lb +0.008, but only with a fill on a touch of the target (T3:8). With a fill only when price trades through: lb ✗ −0.0004. Through by 1¢: −0.0040 (XM3:65-67). | refuted; not built |
| 3 | S3-dip + P-half2R (reported only) | −0.436, lb +0.013 (T3:9). Not re-run under the strict fill rule. | not a deciding variant; needs its own preregistered run, then 200 prospective trades; not built |

### 3.2 · Reaction speed

Arming is when the order goes in; the loop is how often the runner checks.
Net R per trade. Trades per cell: 1,136–1,174 overall, 491–552 pre-market,
615–645 regular hours.
All cells are from T4:5-22.

| arming · loop | all | pre-market | regular | status |
|---|---|---|---|---|
| **10-s candle + 4 s · 5 s (live)** | **−0.449** | **−0.379** | −0.505 | best overall and pre-market |
| live arming · 1-s loop | −0.466 | −0.393 | −0.528 | worse |
| live arming · every print | ✗ −0.531 | ✗ −0.523 | −0.538 | worst: the trail ratchets on noise |
| crossing print + 1 s · 5 s | −0.493 | −0.487 | −0.498 | worse overall |
| crossing print + 1 s · 10-s loop | −0.475 | −0.457 | **−0.491** | regular hours only: better than live each year (below) |

Regular hours by year (T4:26-27):

| setting | 2024 | 2025 | 2026 |
|---|---|---|---|
| live | −0.471 | −0.522 | −0.528 |
| crossing print + 1 s · 10-s loop | −0.467 | −0.514 | −0.487 |

That cell meets addendum 2026-10-02d's own bar, which calls a setting
"worth building" if it is better in each year of the session it targets. The
margin is +0.014 R a trade. **Not built**, for three reasons:
- The bar has no lower bound.
- The grid made 19 comparisons per session.
- Arming on the crossing print needs a per-print feed on the desk, and its
  cost was not assessed.

If it is pursued, the order is: a paired lower bound first, then an OFF switch.

### 3.3 · Execution proposals

| id | proposal | measured | review | status |
|---|---|---|---|---|
| M1 | Stop of last resort: cancel, wait for the confirmation, then sell only the remainder | A tail, mean UNKNOWN. At 92c404d a filled leg sold 166 more shares, and a simulated race ended short in 82 of 200 runs (`docs/preregistration.md` "The stop of last resort…") | survives: mechanism verified in the code | ✓ **built** e58a9d2 |
| M4 | `triggerMethod = 2` (Last) on every stop | live 0 R: it pins IBKR's documented default | The pin survives. Its replay claims do not: the proposed 0.5% print band moves 789 exits and worsens regular-hours slip p99 from 0.460 to ✗ 0.754 R (XM4:4, 21, 23) | ✓ pin **built** e58a9d2; band not adopted |
| M2 | Stay on Fixed commission; move the paper account off its simulated Tiered | Tiered all-in costs +0.016 R a trade more at a 0.0030 take fee (XP:46) | Refuted as stated: the sign flips at an average take fee of $0.00183/sh at $40 risk, and Tiered wins at $20 risk (XM2:6, 18, 28-29) | no change: second-order, under ~0.03 R |
| M3 | Resting limit for half the shares at +1 R | lb +0.008 with a touch fill | Refuted on the strict fill rules above. Placed after the runner sees the fill: lb −0.0028 (XM3:76) | ✗ |
| M5 | Re-check A6 (stop ≥ 4× spread) on a fresh quote at the fire | upper bound +0.042 (XM5:4) | Refuted: the gain came from charging entries above their own limit. With the limit respected it is about +0.003 (XJ). Portfolio lb −0.015 (XM5:25) | ✗ |
| M6 | Pre-market server STP LMT with outsideRth, as an outage backstop below the runner | 0 to +0.010 R | not reviewed; IBKR pages conflict on whether it triggers before 09:30 | open: one paper probe settles it |
| M7 | 09:30 handoff: keep watching a pre-market position until its regular-hours stop is live | Tail guard. 32 of 760 pre-market fills were held at 09:30:00. 18 exited in the 09:30 minute, mean +0.127 R, worst −1.002 R (XO:1-3) | not reviewed | open |
| M8 | An entry time-to-live in seconds, counted from the touch | untested; the nearest test (a 1-bar expiry) was not significant | not reviewed | open: tape study first |
| M9 | $80 risk per trade dilutes the $1 commission minimum | +0.006 / +0.007 R at bar level (XJ, citing the 2026-10-01 rules audit) | not reviewed | owner decision |

**Rejected** (XJ):
- **A faster loop or acting on every print.** The cadence study contradicts it.
- **A regular-hours stop as STP LMT.** It saves +0.0001 R a trade with flagged prints removed (XP:21).
- **Entry cap = trigger.** Net per filled trade is −0.5181 under both rules: it saves 0.039 R of price but loses 85 fills that netted +0.445 R each (XP:35-38).
- **A pre-market server stop at the level as the primary stop.**
- **MIDPRICE sells.** They cannot be validated on paper.
- **Other trigger methods.** All of them fire later in a fall.
- **Tiered or IBKR Lite.**
- **The A16 offset in flatten/ah-exit as a saving.**

### 3.4 · Running Up changes

| id | change | measured | review | status |
|---|---|---|---|---|
| E1 | Per-pillar chips, three states: pass / fail / amber "verify" for unknown. Plus a timed at-alert stamp: INCOMPLETE vs REJECT (measured) | Display only. In the replay 72.7% of rows read INCOMPLETE (78.0% in 07:00–11:30), with float unknown on every row (RE:9; RJ). Live will be lower. | Survives with corrections: force only the AMBER inputs (a measured 50M float must stay a lost pillar, RE:10-13); the kill list is price, pillars and still-rising only; provisional until the minute closes | ready to build |
| C1 | Numbers on the row: Move/10m, Day %, RVOL as the pillar judges it, volume today, Float ('?' when null). One note per scanner. A click opens the alert detail | Move separates within running_up: AUC10 0.653 train / 0.651 test (RC:22) | Survives with corrections. No RVOL dim: it would dim 50.7% / 41.2% of rows and separate little (RC:4, 8). Float red only when verified. | ready to build |
| G1 | A 1–5 "swing" grade from three bar-only features, 09:30–11:30 only | RTH test AUC10 0.725, CI [0.716, 0.737] (RM:86; RG:6) | Survives. The readout must show both tails; see 4.4 | build only with both tails |
| D1 | Dim and mute grade-1 rows after 09:30, never a name's first row | Dims 9.0% of test rows; 4.7% of those reached +10% vs 30.0% of the rest. 1.5% of all +10% alerts are dimmed; 0 symbol-days fully dimmed (RM:91) | not reviewed | after G1 |
| X1 | Context cell: leg count, distance to HOD, VWAP/MACD state, window, gainer rank | descriptive; lifts small or reversed (RR:199-219) | not reviewed | optional |
| L1 | Stop HOD consolidation consuming Running Up legs | Up to 12,090 legs come back. They swing more, not better: MFE30 median 5.40% vs 4.08%, ret30 −1.43% vs −1.28% (R:23, 47, 51) | not reviewed | optional |
| P1 | Store every alert with its at-alert evaluation (an alerts table) | UNKNOWN by design: it is the only way to score E1, G1 and D1 going forward | not reviewed | **prerequisite** for any scoring |
| A5 | TRADE-AFFECTING. Count a no-feed catalyst or an unentitled float as UNKNOWN in the pillar count, not FAIL | — | not reviewed | owner decision + preregistration |

**Rejected** (RJ):
- **Raise the 3% trigger, or hide small moves.** Small moves have lower amplitude, not a lower mean (4.3).
- **Time of day or `vwap_dist` in the grade.** Neither adds anything within a session part.
- **Pillar count, gain, price band or daily RVOL as grade inputs.** Their AUC10 is 0.49–0.55 (RR:212-217).
- **Printing a counterfactual "REVIEW".** It reads as permission to trade an unverified float.
- **The grade as a sort key or weight.** It has no direction.
- **One row per name.**
- **"curl" / "back side" labels.**
- **Dimming:**
  - day change < 10%: the only bucket with a positive median 30-min close;
  - squeezes under 25k: vacuous;
  - after 11:30: no outcome measure there;
  - pre-market by score: the pre-market grade is weak, CI [0.619, 0.641] (RM:87).

## 4 · Detail

### 4.1 · Where the cost goes

1,873 filled trades, R per trade (X:9-15):

| component | mean | median | share |
|---|---|---|---|
| ½ spread at the exit | 0.097 | 0.062 | 25.0% |
| ½ spread at the entry | 0.086 | 0.062 | 22.3% |
| exit slippage past the level | 0.085 | 0.000 | 22.0% |
| commission (Fixed) | 0.078 | 0.061 | 20.1% |
| entry fill above the trigger | 0.041 | 0.025 | 10.6% |
| **total** | **0.387** | **0.273** | |

**Spread is 47% of cost, and cost scales with spread ÷ stop** (X:47-51):

| real spread ÷ stop | n | cost, R a trade |
|---|---|---|
| < 0.05 | 189 | 0.208 |
| 0.05–0.10 | 547 | 0.284 |
| 0.10–0.25 | 812 | 0.401 |
| 0.25–0.50 | 229 | 0.542 |
| ≥ 0.50 | 96 | 0.839 |

**Exit slippage is a pre-market tail:**
- p99 is 4.096 R pre-market against 0.461 R in regular hours.
- Pre-market fills are 39.9% of exits but carry 71.4% of exit slippage (X:86-88).
- A heuristic flags single off-market prints: 34 exits carry 51.1% of exit
  slippage, and pre-market cost falls from 0.419 to 0.327 R without them
  (X:104; XP2:4-5).
- That flag looks ahead 20 prints and drops trades instead of re-simulating
  them (M4 review, XJ), so treat it as a ceiling.

**Entry:**
- 73.2% of plans fill.
- A fill sits a median 0.64¢ over the trigger: 39.6% exactly at the trigger,
  12.1% at the cap (X:111, 118-120).
- On the real spread, 17.4% of trades would fail A6 (X:124). They cost 0.630
  against 0.336 R (X:125). Dropping them is not a passing rule: lb −0.015
  (XM5:25).

### 4.2 · The stop of last resort (built, e58a9d2)

Before and after the change:

| | before (92c404d) | now |
|---|---|---|
| cancel and sell | same pass; the cancel's answer is ignored | pass 1 cancels and sells nothing; later passes sell only on the server's confirmation (error 202) |
| quantity | the full row | the row minus what the leg already sold |
| filled or uncancellable leg | sold again | never sold again |
| no confirmation | — | alert every loop, block entries, name `ah-exit` after `ENFORCE_ACK_LOOPS` |
| negative broker position | skipped by the reconcile | reads SHORT and blocks entries |
| stop trigger | IBKR default, unset | `triggerMethod = 2` (Last), explicit |

Source: `docs/preregistration.md`, entry of 2026-10-02 "The stop of last
resort sells only on a confirmed cancel".

On the tape, the hazard is rare. The review modelled stop-limit exits with
the enforce fallback. Only 5 of 1,867 stop/trail exits reached the enforce
step, and in 1 of those 5 a print reached the limit within 0.5 s, i.e. the
leg could fill while the old code was selling (XM1:2, 6, 14).

### 4.3 · Why a small-move row gets no positive evaluation

Three reasons. Move size is not one of them.

1. **Nothing evaluative is on the row.** `fillAlertCard` in
   `src/momentum_platform/dashboard/web/app.js` renders Time, PM/Day %,
   Symbol (with flame and session), Price and Strategy. A click only selects
   the symbol (read for this report).
2. **The one evaluation lives elsewhere and is taken at the wrong moment.**
   The card's cascade runs on the name's current metrics, not at the alert
   (RJ diagnosis).
3. **In the desk's usual data state, that cascade cannot pass.**
   - In `src/momentum_platform/cascade.py`, the pillar count (A5) needs 4 of 5
     (lines 122-123).
   - It counts an unknown float or catalyst as not passed (lines 309-323).
   - Its catalyst pillar ignores `catalyst_source_ok`, although the catalyst
     gate reads UNKNOWN without a headline source (line 293).
   - Replayed at the alert bar with float unknown and no news: 0 of 174,920
     rows are non-REJECT. 95.7% die on pillars and 4.3% on price (R:35-37).
   - With a verified float under 20M and a catalyst assumed: REVIEW 44.6%,
     WAIT 19.7%, REJECT still-rising 17.0% (R:87-90).

**Small moves are smaller, not worse** (R:53, 57):

| move at alert | median 30-min change | mean |
|---|---|---|
| 3–4% | −0.68% | −0.19% |
| 10%+ | −2.72% | +0.09% |

Under-5% moves are 42.5% of tile rows (RX:1).

**What does separate the rows:** the size of the alert bar, the move and the
day change (G1).

### 4.4 · The swing grade, both tails

Test 2024–26, 09:30–11:30, by grade quintile (RG:11-16, 63-68):

| quintile | +10% high within 30 min | −10% low within 30 min | median 30-min change |
|---|---|---|---|
| 1 | 4.7% | 2.8% | −0.41% |
| 2 | 11.2% | 8.7% | −0.58% |
| 3 | 18.8% | 16.3% | −1.28% |
| 4 | 27.4% | 29.9% | −2.25% |
| 5 | 40.2% | 49.5% | −4.09% |

**The grade measures amplitude, not direction.** In quintile 5, a −10% low is
more likely than a +10% high: +9.3 points, CI [+6.3, +12.3] (RQ:5).

It holds in every calendar year (AUC10 0.704–0.739) and within each
time-of-day slice (RG:26-42).

Net R of first-pullback plans that follow these alerts is negative in every
quintile. Test RTH, one position: −0.525 / −0.583 / −0.535 / −0.315 / −0.362
(RG:85-89). **It must never become a filter.**

### 4.5 · Live defects fixed today

| when (ET) | seen | fix | commit |
|---|---|---|---|
| 2026-10-01 | SDEV (AMEX) on the gap watchlist twice, dropped on error 420; the live scanner never queried AMEX | scanner searches AMEX too (15 queries a round) | 9e4ac19 |
| 08:25 | AMOD SELL LMT 2.43 ×666 filled 466 and left 200 working. "Quantity mismatch" every 5 s blocked entries, and the chase never moved the remainder | the partial fill is counted; a stale sell steps down after 10 s; `watch.py` prints SELL SENT until the fill | 1d02068 |
| 08:57 | The third loss latched the day between arm and touch. The plan stayed armed and was refused 3 minutes later with the wrong reason | REFUSED "risk gate vetoed at the touch: …"; plan disarmed | 940ac01 |
| 08:35 filing | The AMOD card read WEAK on a reaction piece; the 8-K (Item 8.01, Nasdaq bid-price compliance) never reached the desk | 8-K/6-K and finviz "why" sources; listing, PIPE and reaction words; one-line headline summary; chart value line off | 7430f2e, f3817a9 |
| study | the stop of last resort could double-sell | 4.2 | e58a9d2 |

## 5 · What this could not check

- **The tape.**
  - There is one NBBO snapshot at the fill and one at the exit.
  - There is no queue position.
  - Fills are taken at prints whatever the size, so a thin pre-market book
    is invisible.
  - The 1¢-per-side add-on may double-count part of the slippage (XJ).
  - The cache is gitignored, so a fresh clone cannot re-run any stage
    without re-fetching.
- **IBKR behaviour.**
  - Paper fills from the top of the book and treats stops differently.
  - Whether a STP LMT with outsideRth triggers before 09:30 is UNCONFIRMED (M6).
  - The opening print cannot be identified in the cache (M7).
  - Tiered pass-through fees and the paper account's pricing plan are not
    verified (M2).
- **Reaction speed.**
  - The addendum set no lower bound.
  - 179 plans were skipped for uncached tape.
- **Review coverage.**
  - Execution: only M1–M5 were adversarially reviewed.
  - Running Up: only E1, C1 and G1.
  - The corpus alignment written into each proposal (XJ, RJ) was not
    re-read for this report.
- **Running Up replay.**
  - Float was unknown on every row: 0 of 24,831 (RR:4).
  - No news was used.
  - The universe was picked on a ≥10% gap at the open, so the gain pillar
    passes on 94.5% of pre-market rows (RE:47).
  - Live splits will differ, and only P1 can measure them.
- **Prospective evidence.** Nothing here is prospective: 0 live trades under
  any variant.
- **AMOD per trade.** No ledger, so the per-trade facts stay in chat.

## 6 · Verdict

- **No entry variant, cadence or execution change closes the deficit.**
  - On the real tape the strategy is −0.108 R a trade before costs and
    −0.511 after (T1:7-8).
  - Costs run about 0.39 R a trade, about half of it spread.
- **Nothing was adopted.** Built today:
  - execution safety: M1, and the M4 pin;
  - four live defects: partial exits, the veto reason, AMEX, news sources.
- **The live cadence is already the best measured setting.** Faster is worse.
  One regular-hours cell (+0.014 R) meets the addendum's soft bar and stays
  unbuilt until a lower bound exists.
- **The largest cost driver is spread ÷ stop:** 0.21 R a trade below 0.05,
  0.84 R at 0.50 and above. Dropping wide-spread trades did not pass as a rule.
- **Running Up.** The fix is an honest evaluation on the row, not a positive
  verdict.
  - E1 and C1 (display only) and P1 (the alerts table) are ready to build.
  - G1 ships only with both tails shown.
  - Changing A5 is the owner's decision and needs a preregistration.
- **Open safety items:** M7 (the 09:30 handoff) and the M6 probe.
