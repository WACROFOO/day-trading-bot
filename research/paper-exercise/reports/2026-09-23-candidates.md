# Candidates 2026-09-23 — every armed plan, why it did not trade, and what it did next

**PROVENANCE** · `exercise.py missed --day 2026-09-23` (141 rows), run by the
owner after the close and pasted; the same command for 2026-09-21 (125) and
2026-09-22 (93); `exercise.py review` after the close · every R below is the
ledger's simulation: fill at the plan's trigger when the tape touched it, no
slippage, no costs, no halts, planned R. **An upper bound on what was
missed, never a P&L.** Rows marked ‡ have a stop inside 0.5 % of the trigger
and their R is inflated by that denominator. Rows tagged backfill (armed on
history loaded at start) are excluded everywhere. Sums are my arithmetic
over the pasted rows and can be re-run with the command.

> ⚠ Paper. One live trade today (WHLR, −1.06 R realised). Nothing here is a
> claim of edge; the 894-session replication was negative expectancy.

## 1. The funnel, prospective rows only

| stage | rows |
|---|---:|
| armed today | 141 |
| history loaded at start (backfill), excluded | 74 |
| prospective | 67 |
| of which regular hours 09:30–11:30 | 35 |
| taken | 1 |

## 2. Why the 66 untaken prospective plans did not trade

| reason | rows | trig. | fixed-target sum R | trail sum R | what it is |
|---|---:|---:|---:|---:|---|
| killed: `rising` (cascade) | 27 | 22 | +14.91 | +13.97 | a threshold, frozen (A4 says re-derive from measurement) |
| killed: price (< $2) | 14 | 14 | −3.14 | +5.49 | a threshold, frozen |
| killed: pillars | 8 | 8 | +1.00 | +2.40 | a threshold, frozen |
| refused: Layer 2 not green | 7 | 6 | 0.00 | +2.44 | the chart gates at entry |
| refused: one position at a time | 5 | 5 | −2.00 | +0.63 | preregistration §2, by design until 60 trades |
| refused: before 07:00 (desk started 05:35) | 2 | 2 | +4.00 | +3.24 | the session window |
| refused: pre-market, phase B | 2 | 2 | +4.00 | +2.87 | phase gate; phase C opens it |
| refused: A8 buffer (11:25) | 1 | 1 | +1.00 | +1.00 | owner decision 09-22 |

None of the 66 was a defect. Every refusal fired for the reason it states.

## 3. The same table, regular hours only (09:30–11:30)

This is the cohort the gates actually decide today: a pre-market plan is
refused by phase B whatever the cascade says, so a kill there cost nothing.

| reason | rows | fixed-target sum R | trail sum R | winners |
|---|---:|---:|---:|---|
| killed: `rising` | 12 | **+0.91** | **+2.64** | WHLR 09:36, GRML 09:47, GRML 10:25, DCOY 10:31 |
| killed: price | 7 | −2.13 | −0.31 | BENF 11:05 only |
| refused: Layer 2 | 6 | 0.00 | +2.44 | HAO 09:38 ‡, HAO 10:52 ‡ — both two-cent stops |
| refused: one position | 5 | −2.00 | +0.63 | WHLR 10:46 (an add-on to the name already held) |
| killed: pillars | 1 | +2.00 | +0.50 | HAO 10:34 ‡ |
| refused: A8 | 1 | +1.00 | +1.00 | DCOY 11:25 |
| TAKEN | 1 | −1.00 | −0.59 | — |

Read together: **in regular hours the gates left roughly nothing on the
table today.** The `rising` gate's +14.91 R in §2 is +14.00 R of pre-market
rows (WHLR and IPDN between 05:44 and 09:26) and +0.91 R inside the session.
Layer 2's two "winners" are two-cent-stop artefacts; on the four real rows it
refused, all four lost. What cost money today was execution, not selection:
the fill at 7.87 against a plan of 8.31, and a stop that did not execute.
Both are fixed (A10; the stop of last resort).

## 4. The plans that would have won — in the simulation

Chart-approved (verdict REVIEW) plans refused for a reason that was not the
chart, three days, with what the simulation says they did:

| day | ET | symbol | plan | refused for | fixed target | trail | real? |
|---|---|---|---|---|---:|---:|---|
| 09-23 | 05:37 | GRML | 18.97/18.52 | before 07:00 | +2.00 | +2.40 | thin pre-07:00 tape; the window is a rule |
| 09-23 | 09:22 | BENF | 2.47/2.32 | pre-market, phase B | +2.00 | −0.53 | won on the fixed target only |
| 09-23 | 10:14 | WHLR | 7.87/7.19 | one position (WHLR held) | −1.00 | +0.18 | — |
| 09-23 | 10:46 | WHLR | 7.18/7.00 | one position (WHLR held) | +2.00 | +1.89 | an add-on to a losing position |
| 09-22 | 09:30 | GRML | 13.81/13.59 | Layer 2, pullback volume | +2.00 | **+8.36** | the best plan of the week, refused by the volume rule |
| 09-22 | 10:19 | GRML | 13.23/12.60 | Layer 2, pullback volume | +2.00 | +0.97 | — |
| 09-21 | 10:44–11:28 | GRML ×3, VEEE ×2, GLND ×2 | — | the ghost order (defect, fixed 09-21) | +7.35 | +7.27 | a defect's cost; seven rows |

Killed plans with a REJECT verdict have no chart verdict, so "would have won"
for them means the simulation only. The regular-hours ones: WHLR 09:36
(+2.00 / +2.00), GRML 10:25 (+2.00 / +1.41), DCOY 10:31 (+2.00 / +2.00), all
killed on `rising`.

"Real" in the last column means: at the trigger, with the tape there, in a
session the exercise trades. The pre-07:00 and pre-market rows are not
tradeable in phase B; the WHLR add-ons are second entries in a name already
held; the two-cent-stop rows are not tradeable at the size the plan implies.
The one row that survives every caveat is GRML 09-22 09:30, refused by
Layer 2's volume rule, +8.36 R on the trail. One row.

## 5. How each bucket is addressed

| bucket | address | status |
|---|---|---|
| execution: fill far from the plan | A10 stop-limit at the trigger, 3-minute expiry | in force from 09-24 |
| execution: a resting stop that does not execute | the stop of last resort, 15 s | in force from 09-24 |
| `rising` kills | A4: re-derive the threshold from measurement at the phase D read-out; §3 is the first three days of that measurement, and the regular-hours part is +0.91 R over 12 rows | frozen, measured daily by `missed` |
| Layer 2 volume rule | hypothesis for phase D: too strict on a parabolic name (GRML 09-22 09:30). One row. Nothing changes on one row | frozen, counted daily |
| price < $2 | the cheapest cohort loses on the fixed target three days running | frozen, right so far |
| one position at a time | attribution needs it until 60 trades (preregistration §2). Its cost today was an add-on to a losing name | by design |
| pre-market refusals | three-day cohort −6.00 R fixed target over 15 rows (today +4.00 over 2) | right so far; phase C decides |
| before 07:00 | 2 rows, both GRML, both won; the tape before 07:00 is thin and the window is the exercise's | not evidence |
| two-cent stops (HAO ×3 today) | A9 measurement; the floor is written from the count | measuring |
| the ghost order (09-21) | fixed the same day | closed |

*No claim of edge. Upper bounds, correlated rows, one live trade.
`research/momentum-replication/reports/2026-08-regime-filter.md` for the
replication that frames all of this.*
