# research/

Research efforts, one folder per question.

| Folder | Question |
|---|---|
| `momentum-replication/` | Can the documented small-cap momentum strategy be implemented mechanically and does it survive contact with real market data? (The project's main body of work — start at its README; `reports/` holds 27 measurements, cite before re-deriving) |
| `trade-log/` | Which propositions did the tools actually make, and what happened to the ones nobody acted on? `propositions.csv` is the source of truth, `propositions.md` its readable mirror. Written by `scripts/tradelog.py` |
| `trade-journal/` | The OPERATOR's actual fills (TV Paper Trading is invisible to Pine) vs the engine's verdicts — the improvement loop. `journal.csv` written by `scripts/trade_log.py`, audited by `scripts/trade_audit.py` |

Superseded research lives in `../archive/`, not here.
