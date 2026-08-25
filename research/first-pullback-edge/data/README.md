# data/ — study inputs and outputs

Nothing here is hand-written and nothing is a source of truth. Every file is
either fetched market data or the output of a `run.py` stage.

| File | What | Producer |
|---|---|---|
| `candidate_days.{parquet,csv}` | the point-in-time universe: 8,152 ticker-days, 2022-09-01 → 2026-08-21, built from open / previous close / trailing-20 dollar volume only | `run.py universe` |
| `scanned_ticker_days.{parquet,csv}` | the 218 ticker-days that passed the 09:35 ET intraday scanner inside the minute window | `run.py ablation` |
| `trades.{parquet,csv}` | the trade ledger — every field brief §11 asks for, one row per (variant × cost model × ambiguity policy × experiment) | `run.py ablation` |
| `rejected_setups.parquet` | **parquet only** (189k rows; the CSV mirror is 115MB, over GitHub's per-file limit). EVERY candidate the detector saw with each gate's verdict, traded or not. This is what makes the rejected-trade analysis possible | `run.py ablation` |
| `missed_entries.{parquet,csv}` | stop-limit orders that triggered but could not fill inside the limit offset | `run.py ablation` |
| `placebo_trades.{parquet,csv}` | the null-test ledger: pullback number, shifted triggers | `run.py placebo` |
| `halts.csv` | accumulated LULD halts from the free Nasdaq RSS feed — halt time to the millisecond, resumption time, reason code. **Forward-only**: the feed is a rolling ~100-record window with no archive, so this builds from the day the poller starts and cannot backfill | `python3 -m src.halt_poller` |
| `symbol_pool.json` | current Nasdaq/NYSE/AMEX listings (6,742). **Survivorship-biased snapshot** — not committed, regenerate with `--refresh-pool` | `run.py universe` |
| `cache/` | provider bar cache, ~121MB, regenerable. Not committed | `src/data.py` |

Known caveats live in `../reports/data_quality.md`. Read it before using any
column: the float and catalyst columns are `null` by construction, and the
spread behind every slippage figure is a proxy, not a quote.
