# pipeline/ — data fetching and simulation runners

| Script | What |
|---|---|
| `fetch_daily.py` | Daily bars + split calendar for the candidate pool (single-response gaps: the fix for HISTORY #1) |
| `run20.py` | 1-minute bar fetching (`fetch_symbol`, cached) + the original 17-day runner |
| `run20b.py` | The corrected 17-day runner: consistently-adjusted watchlists (`build()`), ROC confirmation, then `engine20.run_day` per day |
| `week.py` | One-week scoped run (`WEEK=07-20|07-27`), same engine |
| `friday.py`, `cupr_friday.py`, `cupr_mock.py`, `fetch_day.py` | Single-session deep dives (2026-07-31) |

Env switches honoured throughout: `PRICE_MIN`, `GAP_CAP`, `WATCH_NAMES`,
`ACCOUNT`, `MARGIN`, plus the engine's `RR_FILTER` / `RE_ENTRY` / `SCALE_IN`.
Commands with expected output: `../RUN.md`.
