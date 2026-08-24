# first-pullback-edge/ — does the First Pullback have an edge?

An adversarial ablation of `knowledge-base/tradingview/ross-fp-v4.pine`
(REV V9.12): six increasingly restrictive variants, point-in-time universe,
no look-ahead, costs modelled, ambiguity counted.

**Read `reports/data_quality.md` before `reports/final_report.md`.** The
headline is a data verdict, not a strategy verdict: 1-minute history reaches
**25 days** from the only feed available here, so the ablation runs on **20
sessions and 49 trades at its widest rung** where the brief asks for
1,000–3,000 ticker-days. Everything the pipeline can do without minute data
— the 4-year point-in-time universe — **is** done: 8,152 candidate ticker-days
over 976 sessions.

## Layout

| Path | What |
|---|---|
| `config/strategy.yaml` | the frozen parameter set. Every value carries the `ross-fp-v4.pine` line it came from and a `provenance` tag (sourced / measured / local / study) |
| `src/data.py` | provider interface + the free Nasdaq halt feed. Yahoo works here; the Massive/Polygon adapter (free-tier throttle, grouped daily, point-in-time delisted symbol list) and Alpaca adapter activate on a key |
| `src/data_quality.py` | the measured data-quality probes — minute reach, pre-market volume, delisted retention, missing bars |
| `src/universe.py` | point-in-time scanner. Daily layer (multi-year) and intraday layer (frozen at 09:35 ET) |
| `src/indicators.py` | strictly causal incremental EMA/MACD/ATR/VWAP/HOD. No vectorised pass exists, so no future bar can leak |
| `src/setups.py` | the ported state machine — impulse, pullback, lanes, HOD retest — emitting every gate's verdict per candidate |
| `src/execution.py` | stop-limit fills, the ambiguity policy, the slippage/commission/participation model |
| `src/backtest.py` | one strict left-to-right pass per symbol-day |
| `src/metrics.py` | §13 metrics and the day-clustered bootstrap |
| `src/validation.py` | chronological splits, ablation marginals, rejected-trade split, gate overlap, placebos |
| `src/param_audit.py` | parameter inventory and the degrees-of-freedom estimate |
| `tests/` | 33 tests, all about look-ahead and fill ordering. `python3 -m pytest tests/ -q` |
| `run.py` | `verify` → `universe` → `fetch` → `ablation` → `sensitivity` → `placebo` → `report` |
| `data/` | `candidate_days`, `trades`, `rejected_setups`, `missed_entries` (parquet + csv) |
| `results/` | `summary`, `ablation`, `yearly`, `regime`, `sensitivity`, `rejected_trades`, `holdout`, `parameter_inventory`, `run_manifest.json` |
| `reports/` | `data_quality.md` first, then `data_acquisition.md` (which free APIs unblock it), then `final_report.md` |

## Reproduce

```bash
cd research/first-pullback-edge
python3 -m pytest tests/ -q                       # 33 tests
python3 -m src.data_quality                       # measure the feed
python3 run.py universe --start 2022-09-01 --end 2026-08-21
python3 run.py fetch     --days 25
python3 run.py ablation  --days 25
python3 run.py sensitivity --days 25 --variants A B F
python3 run.py placebo   --days 25
python3 run.py report
```

`results/run_manifest.json` carries the git commit, the config SHA-256, the
study period, the cost assumptions and the seed.

## The one thing that would change the answer

A minute feed with years of history, extended-hours volume and delisted
tickers — and **the free tier of Massive (formerly Polygon.io) has all
three.** Full reasoning, with the vendor docs quoted, in
`reports/data_acquisition.md`.

```bash
export POLYGON_API_KEY=...                    # free "Stocks Basic" plan
python3 run.py verify --provider polygon      # the five decisive checks
python3 run.py universe --provider polygon --start 2024-08-01 --end 2026-08-21
python3 run.py ablation --provider polygon --days 500
```

`run.py verify` makes the requests rather than trusting the docs: pre-market
volume, delisted retention, minute-history depth, the point-in-time symbol
list, and the free Nasdaq halt feed. Run it before believing any backtest.

Nothing else in the pipeline changes — the provider is one seam, the config
is frozen and hashed, and the tests do not care where bars come from.

## Related work in this repo — cite before re-deriving

- `research/momentum-replication/reports/2026-08-regime-filter.md` — 8,828
  symbol-days over 894 sessions: buy-the-open on gappers is negative in every
  year 2022–2026
- `research/momentum-replication/reports/2026-08-pine-v8-benchmark.md` — the
  V7.5/V8.0 cores on 330 real ticker-days; 25% of fills touched trigger and
  stop in the same minute
- `research/megaday-study/RESULTS.md` — 250+ megadays; the `maxStopPct = 3%`
  cap sits on the population median and is the single most consequential
  unsourced parameter in the strategy

Paper only. An exact implementation is still not an edge.
