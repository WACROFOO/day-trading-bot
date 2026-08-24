# src/ — the pipeline

Import order is the data-flow order. Nothing downstream re-derives what an
earlier module decided.

| File | What | Why it exists in this shape |
|---|---|---|
| `data.py` | provider interface + `YahooProvider` (works here), `PolygonProvider`, `AlpacaProvider` (need a key), `capability_matrix()` | one seam so the whole study re-runs on a paid feed with `--provider polygon` and no other change |
| `data_quality.py` | the measured probes: minute reach, pre-market volume, delisted retention, missing bars, suspicious records | brief §29. Measured from this container, failures recorded as failures |
| `universe.py` | `candidate_days()` (daily, multi-year) and `qualify_intraday()` (frozen at 09:35 ET) | scanner parameters are DISCOVERY dials, never entry gates — `scanGates` is false in the shipped Pine |
| `indicators.py` | incremental EMA / MACD / ATR / VWAP / HOD / RVOL-at-time | strictly causal by construction: there is no vectorised pass, so no future bar can leak |
| `setups.py` | the ported state machine — impulse window search, pullback tracker, fast/uptrend lanes, HOD break-and-retest — emitting EVERY gate's verdict per candidate | one engine per (symbol, day, variant): the machine is stateful, so filtering one run afterwards would be wrong |
| `execution.py` | stop-limit fills with a fixed limit offset, the three ambiguity policies, slippage / commission / participation | the offset must not be a function of the cost model, or a stressed run silently widens its own limit |
| `backtest.py` | `run_day()` — one strict left-to-right pass, entry bar resolved on the bar it fills | deferring the entry bar to *i+1* silently makes every ambiguous fill optimistic |
| `metrics.py` | brief §13 metrics, day-clustered bootstrap, account simulation | trades inside one session are not independent; resampling SESSIONS is the honest interval |
| `validation.py` | chronological splits, ablation marginals, accept/reject split, gate overlap, placebos | nothing shuffles — a chronological cut is the only split a market allows |
| `param_audit.py` | parameter inventory and the degrees-of-freedom estimate | brief §22 |

A port is not the Pine. TradingView is the only Pine compiler; state parity
with `ross-fp-v4.pine` is asserted here and checked only by `../tests/`.
