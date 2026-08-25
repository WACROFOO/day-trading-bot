# first-pullback-edge/ — does the First Pullback have an edge?

An adversarial ablation of `knowledge-base/tradingview/ross-fp-v4.pine`
(REV V9.12): six increasingly restrictive variants, point-in-time universe,
no look-ahead, costs modelled, ambiguity counted.

**Verdict: NO EDGE.** 838 trades across 479 sessions, 945 names and three
calendar years. Every variant's 95% CI lies entirely below zero, in every
year and in the untouched 112-session holdout — and a **random entry minute
on the same tape beats every variant by more than a full R** (−0.823 R on
9,175 trades vs −1.853 R for the basic first pullback). The strategy is
negative **gross of all costs**; costs then add ~0.8 R of tax on top.

Read `reports/data_acquisition.md` for how the data blocker was cleared
(two free API keys), then `reports/final_report.md`.
`reports/data_quality.md` is kept as the record of what was wrong with the
original feed and how it was found.

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
export POLYGON_API_KEY=...           # free Massive Basic — the universe
export ALPACA_API_KEY_ID=... ALPACA_API_SECRET_KEY=... ALPACA_FEED=sip
python3 -m pytest tests/ -q                       # 33 tests
python3 run.py verify --provider alpaca           # the five decisive checks
python3 run.py universe --grouped --provider polygon \
        --start 2024-09-24 --end 2026-08-21       # survivorship-free, ~1.7h
python3 run.py ablation --provider alpaca --prefetch \
        --start 2024-09-24 --end 2026-08-21 --compute-workers 4
python3 run.py sensitivity --provider alpaca --variants A F \
        --start 2024-09-24 --end 2026-08-21
python3 run.py placebo  --provider alpaca --start 2024-09-24 --end 2026-08-21
python3 run.py report
```

**Massive for the universe, Alpaca for the bars.** Only Massive has a
point-in-time symbol list that includes delisted names (the survivorship
fix); only Alpaca serves consolidated minute bars deep and fast enough to
make the intraday run affordable. Neither alone is sufficient.

`results/run_manifest.json` carries the git commit, the config SHA-256, the
study period, the cost assumptions and the seed.

## Data provenance

Both feeds were verified from this container rather than trusted:
`run.py verify` makes the requests — pre-market volume, delisted retention,
minute-history depth, the point-in-time symbol list, the halt feed — and
writes `results/provider_verification.json`.

The two feeds were also **cross-checked against each other** on 28 shared RTH
sessions: identical minute counts, identical session highs and lows, volume
within 0.7%, **zero disagreements**. Two independent consolidated sources
agreeing is the defence this repo lacked when a stitched-window adjustment
once fabricated +10,555% gaps (`momentum-replication/HISTORY.md` defect 1).

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
