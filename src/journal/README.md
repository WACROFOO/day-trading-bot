# src/journal/

The decision ledger: one SQLite file (`data/journal.sqlite`, WAL) that every
other package reads and writes. It is the bus, not a log — the desk records
decisions here, the runner reads them back, and every report is built from it
rather than from anything held in a process.

| Module | What |
|---|---|
| `ledger.py` | the schema and the writes: `decisions`, `actuals`, `orders`, `bars`, `bars_10s`, `quote_ticks`, `board_snapshots`, `candidates`, `decision_revisions`, `exercise_state`. `bars_10s` is deliberately NOT in `bars`: the grader selects every row of `bars` |
| `replay.py` | **R11.** Re-runs the cascade on each decision's stored `inputs_json` and compares. Three outcomes: `reproduced` (the current rules give the recorded answer), `superseded` (an older rule set does, and it is named), `diverged` (no rule set ever run does — the log lost something, and that is a defect) |
| `actuals.py` | what the tape did after each decision: MFE, MAE, first_hit. A bar touching stop and target is credited to the **stop** |
| `controls.py` | the same rows under alternative exit rules, in R, so the strategy can be compared with doing nothing |
| `bars.py` | tape in, from the ledger or a fixture |
| `risk.py` | the 5-rule gate with the persistent latch the runner obeys |

**Nothing here places an order.** The order path is `src/execution/`.

A decision row carries `inputs_json` precisely so it can be re-judged later.
That is what makes an amendment auditable instead of destructive: see
`docs/preregistration.md` §5 and `cascade.RULE_SETS`.
