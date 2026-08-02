# Reports

Findings from the replication attempt, newest first. Each is reproducible with
the command at its head.

## Weekly runs

| Report | Period | Trades | P&L | Note |
|---|---|---:|---:|---|
| `2026-07-27-week.md` | Mon–Fri 07-27 | 3 | +$49.97 | halts implemented; two readings of §1 compared |
| `2026-07-20-week.md` | Mon–Fri 07-20 | 1 | +$833.28 | prior week, run second — engine unchanged after seeing it |

**Combined: 4 trades over 10 sessions, +$883.25.** One trade is 94% of it.

## Against his own recaps

| Report | What it establishes |
|---|---|
| `2026-07-27-vs-recaps.md` | Ticker overlap confirmed; halts identified as unmodelled |
| `2026-07-20-week.md` (§Comparison) | Overlap confirmed a third time (ZCMD, INM, CJMB) |

## Single-session deep dives

| Report | Subject |
|---|---|
| `2026-07-31-friday.md` | Whole session, multi-timeframe; 10s unobtainable |
| `2026-07-31-cupr.md` | One symbol end to end; every setup mock-traded, each loss diagnosed |

## Diagnosis and fixes

| Report | Subject |
|---|---|
| `2026-07-27-audit.md` | Why the week produced almost nothing — selection, not execution |
| `fix-target.md` | The unreachable-target defect, verified out-of-sample on TCX |

Root-cause history for the whole effort is in `../HISTORY.md`; the rules the
engine implements and their citations are in `../ENGINE-RULES.md`.
