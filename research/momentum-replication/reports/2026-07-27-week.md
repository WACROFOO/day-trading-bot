# Test run — week of 2026-07-27, all rules applied

Engine as consolidated: the six `PARAMETERS.md` §3 gate conditions, cumulative
volume, nearest-objective target with 2:1 as a filter, spread floor, cut-size
on wide stops, and halt handling.

## Halts — now implemented

A halt is invisible in OHLCV except as a gap in an otherwise continuous minute
series. An LULD halt lasts a 5-minute minimum (`FN-uqfbEVKw` [01:24]), so five
consecutive missing minutes inside regular hours is the detection threshold.

Two behaviours, both from the corpus:

1. **Structure resets across the gap.** Price does not travel from the pre-halt
   bar to the resumption bar — it is re-auctioned. Carrying `leg_low`,
   `leg_high` and the pullback count across invents a move that never traded.
2. **A halt that resumes lower is not tradeable** — *"halted going down
   typically resumes lower"* (`FN-uqfbEVKw` [19:03]) — added as a gate check.

**16 halts detected across the week**, including three consecutive on EDBL
(Mon, $8.30 → $5.89, all resuming lower), two on STFS and one on AMIX
(Wed — exactly the ones the recap names), and three on CUPR (Fri), of which
10:15 → 10:25 resumed **up** $4.38 → $4.70, the move to its high of day.

---

## The result depends on one unsettled reading

`rate_of_change_min > 0` sits in `PARAMETERS.md` §1 — the **universe filter**.
A scanner runs continuously through the session; applying it once at 09:35
kills a name for the whole day because it was soft in its first five minutes.
Both readings were run against identical data.

| | A: one-shot at 09:35 | B: left to the gate |
|---|---:|---:|
| Trades | 1 | 3 |
| Winners | 0 | 1 (33%) |
| P&L | **−$199.98** (−2.00%) | **+$49.97** (+0.50%) |
| Expectancy | −1.00R | +0.07R |
| Name-days dropped | 15 | 0 |

**Reading A removes AGPU, the week's only winner** (+$314.67, +2.21R). AGPU was
below its open at 09:35 and set up cleanly at 10:04.

I am not choosing between these on P&L. The argument for B is textual: §1 is a
scanner criterion, and §13 of `PARAMETERS.md` now documents this exact class of
error — applying a continuously-evaluated rule as a one-shot gate is the same
mistake as treating a pattern description as a gate condition. The argument for
A is that it directly encodes the `faded from pre-market high` reject, which is
also §1 and which the week audit showed matters.

The gate already contains `price > VWAP` and `price > 9 EMA`, both of which test
"is this rising *now*". That makes a one-shot ROC filter largely redundant *and*
more destructive than the rule it implements. **B is the better reading; the
ambiguity is recorded rather than resolved.**

---

## Reading B, day by day

| Day | Watchlist | Setups | Passed | Trades | P&L |
|---|---|---:|---:|---:|---:|
| Mon 07-27 | EDBL, LGHL, DFNS, BIYA… | 15 | 2 | 2 | **+114.69** |
| Tue 07-28 | FIRY, INLF, BIYA, PMN… | 31 | 1 | 1 | −64.72 |
| Wed 07-29 | NCRA, AMIX, VIVK, GMM… | 43 | 0 | 0 | 0.00 |
| Thu 07-30 | NUWE, STAK | 13 | 0 | 0 | 0.00 |
| Fri 07-31 | CUPR, TCX | 14 | 0 | 0 | 0.00 |
| | | **116** | **3** | **3** | **+$49.97** |

| Day | Sym | In | Out | $/sh | R | Exit |
|---|---|---|---|---:|---:|---|
| 07-27 | AGPU | 10:04 | 10:16 | 0.12 | **+2.21** | big red candle → trailing stop |
| 07-27 | BIYA | 10:24 | 10:26 | 0.18 | −1.00 | stop hit |
| 07-28 | EHGO | 11:08 | 11:11 | 0.04 | −1.00 | stop hit |

Halt handling removed 3 setups versus the previous run (119 → 116) without
changing any trade — the phantom structures it deleted were already being
rejected by the gate.

Look-ahead audit passes at every cut-off.

---

## Against his own recaps

| Day | His recap | My engine |
|---|---|---|
| Mon 07-27 | "Record Breaking Green Day!" — EDBL, LGHL, DFNS | 2 trades, +$114.69 |
| Tue 07-28 | "Biggest Red Day…" — DFNS, INLF, LGHL, BIYA | 1 trade, −$64.72 |
| Wed 07-29 | up ~$22,000 — NCRA, DFNS | **0 trades** |

Direction matches on Monday and Tuesday: green on his green day, red on his
biggest red day. Wednesday remains the gap — he made $22,000 on a session my
engine sat out entirely, and implementing halts did not change that. The halts
on AMIX and STFS all resumed **lower**, which the new gate check correctly
refuses; whatever he traded there, the dip-and-rip on a halt that resumes lower
is not what the corpus describes as the setup.

---

## Honest status

n=3, and one trade is 100% of the P&L. Nothing here is a result.

What the week does show: the engine is now directionally consistent with his own
characterisation of two of the three sessions he recapped, the scanner selects
the same names he trades, and the remaining gap is concentrated on one session
whose defining feature — repeated halts — is the newest and least-tested part of
the implementation.
