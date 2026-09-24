# 2026-09-24 — every name on the desk, every pullback the detector finds, and why each was refused

**Provenance.** Fifteen names were on the desk today (watchlist, scanner joins,
and the names on the 11:26 board). Their 1-minute bars were pulled this evening
with `python3 scripts/tape.py SYM --bars 900` from the cloud container, where no
Gateway answers, so the source is **Yahoo**: pre-market bars carry **no volume**,
which makes two things uncomputable there — the pullback-volume gate and VWAP
(a VWAP over zero volume is undefined, and the repo's `indicators.vwap` returns
None, which the cascade reads as red). Where this report says what a
pre-market gate did on the DESK, the number comes from the owner's pasted
`exercise.py missed --day 2026-09-24` LAYER 2 block (IBKR bars). Trades and
ledger facts come from the pasted `review`. SONM, RJET and CTSO had 18–32 Yahoo
bars and are not run. Detector: `FirstPullbackDetector` with the desk's
defaults, fed every bar from 04:00. Gates: `FILTERS.md` Layer 1 price $2–20,
float ≥ 20M, still-rising (>25 % off the session high at the plan), then Layer 2
from `indicators.chart_gates` and the detector's `volume_ok`. Scoring: A10 (the
trigger must be touched within 3 bars, else no order), fill at the trigger, no
costs, fixed 2 R target vs the A3 1 R trail (`controls.simulate_exit`), one
position rule ignored. **Upper bounds, never P&L.**

## 1. The verdict on the day

| question | answer |
|---|---|
| profitable? | no, and not a loss either: two trades, PFSA −$0.83 (−0.04 R) and GRML −$0.44 (−0.02 R). The day is −$1.27 on a $20-risk paper book |
| cumulative | 6 trades, −2.18 R planned, −$42.64 (the −5.41 R GRML defect exit of 09-22 is 84 % of it) |
| did the bot do what it was built to do? | yes: both entries filled at the trigger (slippage ratios 1.04, 1.04 against 0.55 for WHLR the day before), both trailed stops executed within a bar of their level, pre-market entries were live for the first time and refused 14 plans at Layer 2 with the gate now named |
| what went wrong | the Gateway went down at ~07:15 (desk blind until 08:07), the IBKR link dropped at 10:40 with the desk OFFLINE after it, the day never settled. Both are the Gateway's link, not the bot; the settle is now automatic (`day.settle_unsettled`) |
| progress | real: the three defects of 09-22 and 09-23 (naked position, plain-limit fill far under plan, resting stop that did not execute) did not recur. The frontier moved from execution to selection |

## 2. Name by name (Yahoo tape; times ET; "plans" = pullbacks the detector armed 07:00–11:20)

| sym | prev → last | PM high | RTH HOD (time) | fade | float | plans | why refused (count) | touched | fixed 2 R | A3 trail |
|---|---|---|---|---|---|---|---|---|---|---|
| GRML | 11.19 → 14.62 | 15.39 | 16.00 (10:17) | −8.6 % | 2.9M | 10 | VWAP red 4, MACD red 2, three gates 1, **all green 3** | 10 | +8.00 | +0.23 |
| GCTK | 2.03 → 2.64 | 5.05 | 3.25 (09:39) | −18.8 % | 0.6M | 13 | still-rising 8 (the 5.05 pre-market high collapsed to 2.4 before the open), VWAP 2, VWAP+MACD 1, three gates 2 | 9 | +0.00 | +15.99 (one 4-cent-stop plan is +14.0 of it) |
| WETO | 1.45 → 1.86 | 2.71 | 2.19 (09:37) | −15.1 % | 0.9M | 4 | price under $2: 3, VWAP 1 | 3 | +3.00 | +3.41 |
| SPHL | 2.31 → 2.75 | 5.97 | 3.67 (09:33) | −25.1 % | 1.2M | 5 | still-rising 5 (54 % off its pre-market high at the scan) | 4 | −1.00 | −0.74 |
| UXIN | 1.09 → 1.21 | 1.43 | 1.41 (09:46) | −14.2 % | 219.7M | 6 | price under $2: 6 (float would kill it too) | 4 | +5.00 | +1.41 |
| NCPL | 1.04 → 1.37 | 2.14 | 1.63 (10:05) | −16.0 % | 4.4M | 7 | price under $2: 7 | 7 | +2.00 | −0.07 |
| PFSA | 2.05 → 2.70 | 4.55 | 4.18 (09:35) | −35.4 % | 0.5M | 12 | still-rising 5, VWAP+MACD 4, VWAP 2, MACD 1 | 11 | +4.00 | +3.50 |
| SKYQ | 2.54 → 3.19 | 3.36 | 3.19 (11:29) | 0.0 % | 8.0M | 8 | VWAP 3, VWAP+MACD 3, VWAP+volume 1, **all green 1** | 7 | +11.00 | +1.96 |
| SRZN | 16.16 → 32.00 | 31.24 | 35.86 (09:54) | −10.8 % | 11.8M proxy | 9 | price over $20: 8, VWAP+MACD 1 | 7 | +8.00 | +0.30 |
| GLND | 2.91 → 4.46 | 3.23 | 5.00 (10:12) | −10.8 % | **27.5M** | 8 | float over 20M: 8 | 8 | −1.14 | −0.09 |
| HCWB | 1.66 → 2.26 | 1.79 | 3.12 (10:29) | −27.5 % | 1.8M | 4 | price 1, still-rising 1, VWAP 1, volume 1 | 4 | −1.00 | −2.44 |
| PMAX | 0.91 → 1.93 | 1.07 | 2.87 (10:40) | −32.8 % | passes (desk card) | 3 | price 1, volume 1, 9EMA+MACD 1 | 3 | +0.00 | +0.09 |

Twelve names, **89 plans** in the window: 53 killed at Layer 1 (price 26,
still-rising 19, float 8), 32 red at Layer 2, **4 all green**.

## 3. The four plans the rules would have sent, and what the desk did with them

| plan | Yahoo verdict | desk's record | outcome (upper bound) |
|---|---|---|---|
| 09:39 GRML 12.94/12.74 | all green | REFUSED: one position at a time (PFSA open 09:38–09:40), and Layer 2 WAIT on IBKR bars | fixed +2.0, trail +0.15, MFE 2.85 R |
| 09:52 GRML 13.71/13.44 | all green | REFUSED: A6, the 0.27 stop inside 4 × the 0.10 spread | fixed +2.0, trail +1.0, MFE 2.48 R |
| 10:07 GRML 14.47/14.02 | all green | **TAKEN**, live −0.02 R (trail to 14.46, hit 10:14) | fixed +2.0, trail −0.02, MFE 2.62 R — the simulation reproduces the live exit to the cent; the stock went on to 16.00 |
| 10:51 SKYQ 3.03/2.96 | all green | never seen: the desk was OFFLINE after 10:40 | fixed +2.0, trail −0.86, MFE 2.29 R |

Same-minute, same-trigger agreement between the Yahoo detector and the
ledger on the three GRML plans says the detector is deterministic across
tapes in regular hours; pre-market plans differ bar by bar because the two
tapes differ there.

## 4. "How many pullbacks were neglected, and why"

Per gate, upper bound, 07:00–11:20, twelve names:

| cohort | n | touched | fixed 2 R | A3 trail | win (fixed) |
|---|---|---|---|---|---|
| **all green · regular** | 4 | 4 | **+8.00** | +0.27 | 4/4 |
| killed on **price** · pre-market (WETO, NCPL, UXIN, HCWB under $2; SRZN over $20) | 14 | 11 | +16.00 | +3.99 | 9/11 |
| killed on **price** · regular | 12 | 11 | +4.00 | +2.96 | 5/11 |
| killed on **still-rising** · pre-market (GCTK, PFSA, SPHL) | 7 | 6 | +3.00 | +14.10 (+0.10 without the 4-cent-stop GCTK plan) | 3/6 |
| killed on **still-rising** · regular | 12 | 9 | −3.00 | +0.44 | 2/9 |
| killed on **float** (GLND) · both windows | 8 | 8 | −1.14 | −0.09 | 2/8 |
| Layer 2 red · pre-market (GRML, GCTK, PFSA, SKYQ; VWAP uncomputable on Yahoo) | 26 | 22 | +11.00 | +19.31 (+5.31 without the same GCTK plan) | 14/22 |
| MACD the only red gate · regular | 3 | 3 | +3.00 | +0.86 | 2/3 |
| volume the only red gate · regular | 2 | 2 | −2.00 | −0.62 | 0/2 |
| VWAP the only red gate · regular | 1 | 1 | −1.00 | −1.00 | 0/1 |

Reading, in the order a trader would rank it:

1. **Regular hours, rules as written: 4 for 4 to the fixed target, +8 R.** The trail kept +0.27 of it. That is the second day the A3 trail has given back a fixed-target win (GRML 10:07: −0.02 live against +2.0 fixed). The kill rule needs ten clean fills; it has four.
2. **The price band was the biggest "neglect" today, and it is the method's rule, not a defect.** Sub-$2 names (WETO, NCPL, UXIN, PMAX, HCWB early) and a $32 name (SRZN) produced 26 plans worth +20 R fixed upper bound. `FILTERS.md` gate 1 kills them unless a penny theme is live, which the desk cannot yet assert. That is a cohort to keep counting, not a threshold to move on one day.
3. **Still-rising did its job in regular hours** (−3 R over 9 on the plans it refused) and was roughly neutral pre-market once the 4-cent-stop outlier is removed.
4. **GLND, the owner's example chart:** 27.5M float, killed on gate 2 on all eight plans. On the tape those eight plans were −1.14 R fixed / −0.09 R trail. The one clean entry was the first pullback after the open, 09:43 at 3.68/3.60: +2 R fixed, +3 R trail. The later pullbacks at 10:12, 10:54, 11:01 and 11:17 all lost or scratched. A chart that looks tradeable at 11:26 was one good entry and four bad ones by the rules' own definition of a pullback.
5. **Pre-market:** on IBKR bars the desk saw 14 plans and none all green (VWAP red 9, MACD 8, volume 7). On the Yahoo tape the same names' pre-market plans scored +11 R fixed over 22 touched. Yesterday's cumulative read on graded days was the opposite sign (all-green pre-market −4 R over 13). Two days, two signs: the count continues, five graded phase-C sessions before any pre-market change.
6. **Outages cost visibility, not money:** SKYQ 10:51 (all green) and GRML 10:49 fell in the blind window after 10:40; GCTK, GRML and PFSA plans 07:23–08:07 were backfill.

## 5. My own calls, scored

- Morning Yahoo table: "+10 R over 11 pre-market plans" — same tape, same limits; today's full run gives +11 R fixed over 22 touched for those names. Consistent, and still an upper bound with no volume gate.
- "PFSA's stop may have failed" — wrong; it executed at 09:40:00.
- "GRML 09:39 was refused by Layer 2" — the desk's reason list started with the one-position rule; Layer 2 was second. Both were true on IBKR bars; on Yahoo bars the plan is all green. The tapes differ by cents around VWAP.

## 6. Limitations

Yahoo hides pre-market volume: VWAP and the volume gate are not evaluable
pre-market here, and every pre-market Layer 2 statement about the DESK comes
from the ledger. Fills at the trigger with no costs, no halts, no spread
check, one position ignored. Three names not run. One day. Paper only;
nothing here is a claim of edge.
