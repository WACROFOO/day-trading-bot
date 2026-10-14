# levels-first-look/ — the levels round on the desk's own 22 exported days

```
DATA     · research/daily/ — the 22 exported desk days, 2026-09-11 → 2026-10-13, 04:00-12:00 one-minute
           bars, the desk's board names, previous close as exported. OUTSIDE the five years, chosen by
           the desk's scanners, not by candidate_days.csv
RULES    · PREREGISTRATION.md, amendment 2026-10-14 — committed and pushed (f3e6063) BEFORE this ran
RUNS     · 2026-10-14T1254Z-smoke (families.txt) · 2026-10-14T1254Z-levels-smoke (levels.txt), both at
           git f3e6063; deterministic — a second run gave the same figures
SPLIT    · the smoke split of scripts/candidates/data.py: "train" = days to 2026-10-01, "valid" = later
! FIRST LOOK — plumbing, NOT evidence. 195 symbol-days, 20 to 69 trades a cell: the protocol's
  floor is 100 train trades before a configuration may even be chosen
```

## 1 · What was considered

| | count |
|---|---|
| symbol-days with bars | 195 of 195 (136 "train", 59 "valid") |
| configurations | 24: L4, L5, L6 × stop {bars5, level} × target {fixed2, trail1, res, hod} |
| signals before the one-position rule | L4 95/33 (bars5), 81/32 (level) · L5 107/38, 109/38 · L6 113/41, 112/40 |
| level tests in the read-out | 19,649, real and placebo, 09:30-11:29 |

## 2 · What survived — nothing, and why each failed

Every family stops at the protocol's first step: **too few train trades** (best 69, 66 and 53
against 100). The figures below are what the cells did anyway, one position at a time, net
of costs, R a trade (`families.txt`).

| family | best train cell | train | "valid" | why it is not a suggestion |
|---|---|---:|---:|---|
| L4 trend-line break | bars5·trail1 | −0.162 (62) | −0.335 (26) | negative in both halves, every cell |
| L4 | level·trail1 | −0.163 (65) | −0.326 (27) | the same |
| L5 support hold | bars5·fixed2 | −0.281 (43) | −0.306 (20) | negative in both halves, every cell |
| L6 resistance break | level·trail1 | **+0.243** (44) | −0.495 (21) ✗ | flips sign on the later days |
| L6 | level·hod | **+0.132** (43) | −0.914 (18) ✗ | flips sign on the later days |

The 22 other cells are negative on the early days; all 24 are negative on the later ones.

## 3 · Per-item detail — where the R goes

| reading | figure | source line |
|---|---|---|
| costs a trade | 0.254 to 0.592 R | `families.txt`, column `cost` |
| gross, before any cost | −0.230 to +0.723 R; 9 of 24 cells negative on the early days | column `gross` |
| how far the trade goes the right way | MFE median 0.24-0.27 R (each family's busiest cell) | the `WHY` lines |
| random entries on the same names, same stop and exit | −0.315 to −0.495 R | the `WHY` lines: the names drift against a long |
| **TP at the next resistance (`res`)** | median **0.22-0.51 R** above the entry; reached on 50-72 % of trades | the `TARGETS` lines |
| **TP at the high of day (`hod`)** | median **4.11-6.70 R** above; reached on 12-26 % | the `TARGETS` lines |
| SL `level` against `bars5` | no consistent winner: each is the better one in some cells | the tables |

The fan's nearest resistance sits a fraction of the stop above the entry, so `res` books small
wins that the costs take entirely; the high of day sits so far that it is rarely reached by
11:30. A 2 R target and a 1 R trail are between the two, and also negative after costs here.

**The level read-out** (`levels.txt`) — held % = a high 1 ATR above a support before a close
through it (resistance mirrored), against the same level moved ±0.5-1.5 ATR:

| level | support Δ held, pts [95 %] | resistance Δ held, pts [95 %] |
|---|---|---|
| fan (the Pine's S/R) | **−3.0** [−5.8, −0.2] ✗ | −0.6 [−3.4, +2.3] |
| trend lines | −1.1 [−4.9, +2.9] | +0.9 [−4.0, +6.1] |
| VWAP | −4.2 [−10.5, +1.8] | −2.9 [−8.3, +2.4] |
| whole / half dollar | +3.3 [−1.2, +7.9] | +1.5 [−3.2, +5.6] |
| pre-market high | −6.2 [−15.7, +3.4] | +0.7 [−11.3, +13.3] |
| high of day | — | +5.9 [−2.4, +13.9] |
| fan + a second reason | −0.8 [−9.2, +9.2] | −4.5 [−15.0, +8.0] |

On these days no level holds more often than the same level drawn at random; the fan's nearest
support holds less often. Whole/half dollars and the high of day lean the other way, inside
their noise.

## 4 · What this could not check

- **Size.** 195 symbol-days, 22 sessions. The intervals above are as wide as the effects they
  bound; a cell's sign can flip between two halves of a month (§2 shows it twice).
- **The population.** The desk's board names, not the preregistered universe; 04:00-12:00 bars.
- **Prior sessions.** Levels come from the symbol-day's own bars; the desk's chart may also hold
  yesterday's swings. Daily and weekly levels — a component the corpus names — are untested.
- **Execution.** One-minute bars and the live cost model; no Level 2, no halt handling, no
  sub-minute structure.

## 5 · Verdict

**WAIT — no record.** By the amendment's mapping, a live L4, L5 or L6 setup carries WAIT until
the five-year run reads it; this first look adds no reason to expect better than NO. It is the
record that suggests a stop and a target, and no cell here has earned one. The run that does,
on the Mac:

```bash
bash scripts/update.sh
python3 scripts/candidates/run.py --families L4,L5,L6     # train chooses the stop and target, 2023 gates
python3 scripts/candidates/level_read.py                  # do the levels hold, 2021-2023
```

Paper only. Not evidence.
