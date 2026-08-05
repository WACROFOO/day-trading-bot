# Reports

Findings from the replication attempt, newest first. Each is reproducible with
the command at its head.

## Calibration against his real trades — start here

| Report | What it establishes |
|---|---|
| `2026-07-july-calibration.md` | **The first external measurement.** Real upload dates turn 28 July recaps into labelled sessions; the engine is scored against 61 session-ticker pairs he named |
| `2026-08-target-and-entries.md` | Settles the 2:1 veto against the spec's own numbers, then shows what it was hiding: the losses are bad entries, not tight stops |
| `2026-08-streams-roundup.md` | **The 480 live streams the corpus never had.** Answers the timing question: the micro-pullback is often a 10-second pattern our 1-minute detector cannot see |
| `2026-08-bughunt.md` | Four mechanical defects found by line-by-line re-read; the fake-halt veto alone moved agreement with his labelled trades 4% → 22% |
| `2026-08-ispo-stream.md` | Case study of the 4½-hour ISPO live session: risk discipline matches the spec, four rules diverge (session window, halt-level targets, resumption entries, anticipation) |
| `2026-08-05-session.md` | A live watch list scored against its own session. The pre-market fade veto cost the day's biggest winner; tested on 722 July symbol-days, faded names run MORE — but only 7% take out their pre-market high, so it is a setup classifier, not a filter |
| `2026-08-05-recap.md` | The close. All twelve names finished off their highs, median −30%, the three biggest runners −45 to −49%. Four of the six traps were visible in filings before the open |
| `2026-08-score-basket.md` | Buy-open/sell-close sized by a 0-100 pillar score, 17 sessions. Equal weight beat the score in 16 of 16 matched pairs; raising the score threshold made it monotonically worse; 15 of 17 days lost money |
| `2026-08-vwap-condition.md` | `require_above_vwap` is our most binding gate (56.5% pass) and it vetoes a setup he has a dedicated video about. Also disproves his "VWAP and the 9 EMA are rarely inverted" claim on our data (41% inverted) |

Headline: of every ticker he named that resolves to a symbol, **100% were in
the pool** and the detector found structure on **97%** — but only 31% pass the
five pillars and **3 of 61** survive the entry rules. The universe and the
detector are exonerated; the scanner and the entry gate are where the strategy
is being lost. It also found the exit look-ahead below.

## Weekly runs

| Report | Period | Trades | P&L | Note |
|---|---|---:|---:|---|
| `2026-07-27-week.md` | Mon–Fri 07-27 | 3 | +$49.97 | halts implemented; two readings of §1 compared |
| `2026-07-20-week.md` | Mon–Fri 07-20 | 1 | +$833.28 | prior week, run second — engine unchanged after seeing it |

> **Both P&L figures above are superseded.** They were measured before defect
> 14 (`HISTORY.md`), which priced the 11:30 forced exit off the 15:59 bar. The
> 07-20 week is **+$557.52 (+5.58%)**, not +$833.28; the 07-27 week is
> **−$199.98**. Over the full 17 sessions: 2 trades, **+$357.54**.

## Against his own recaps

| Report | What it establishes |
|---|---|
| `2026-07-july-calibration.md` | Scored, not just overlapping — 61 labelled pairs across 14 sessions |
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
