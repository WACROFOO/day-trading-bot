# data/ — market data and run outputs

Everything here is either fetched market data (cacheable, regenerable) or the
output of a pipeline run. Nothing is hand-written; nothing is source of truth.

| File(s) | What | Producer |
|---|---|---|
| `pool20.json` | Candidate universe snapshot (symbol, price, mcap) | `pipeline/fetch_daily.py` |
| `daily20.json[.gz]` | Daily bars + split calendar per symbol | `pipeline/fetch_daily.py` |
| `scan20_stats.json[.gz]` | Per symbol-day pre-market stats (gap, rvol, v5) | scan pipeline |
| `bars_cache/` | 1-minute bars per symbol (7-day Yahoo windows) | `pipeline/run20.py::fetch_symbol` |
| `watchlists20.json` | Built watchlists per day | `pipeline/run20b.py` |
| `run20_max*.json`, `week_*.json` | Simulation results | `run20b.py`, `week.py` |
| `july_meta.json` | Real upload dates for July videos | scratch fetch (documented in reports) |
| `stream_meta.json` | Real upload dates for the live streams | same |
| `calibration.json`, `pillars.json` | Calibration outputs | `diagnostics/calibrate.py`, `pillars.py` |
| `cupr_*`, `tcx_*`, `friday_*` | Single-session deep-dive data | `pipeline/cupr_friday.py` etc. |

Known data caveats (reverse-split contamination, window stitching, missing
minutes vs halts) are documented in `../DATA-SOURCES.md` and `../HISTORY.md`.
