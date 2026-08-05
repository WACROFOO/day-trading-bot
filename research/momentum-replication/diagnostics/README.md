# diagnostics/ — measurements, not simulations

Each script answers one question about the engine, usually against an external
reference. None of them tune anything. The steering metric for the whole
project is `calibrate.py`'s final level — agreement with the trades he
demonstrably took — not P&L.

| Script | Question |
|---|---|
| `calibrate.py` | Of every ticker his recaps name, how far does the engine get? (pool → scan → pillars → setup → trade) |
| `pillars.py` | Which scanner criterion rejects the names he traded? |
| `sweep.py` | Price floor / top-N, measured as recall of his names |
| `intraday.py` | Were the non-gappers moving intraday instead? |
| `lost.py` | Gate said yes — what stopped the trade? |
| `trades.py` | The 17 sessions, trade by trade, with the realised P/L ratio |
| `target_r.py` | How far away is target 1, in R? |
| `mae.py` / `his_mae.py` | Worst excursion before target 1 — ours vs his names |
| `excursion.py` | The same, every setup, both pools — the selection-vs-timing test |
| `small_account.py` | The run priced for a small account (PDT cap, 1x margin) |
| `exercise.py` | Deals one real setup as a decision with the future withheld (training) |
| `score_basket.py` | Buy-open/sell-close basket sized by a 0-100 pillar score, with an equal-weight control (offline) |
| `vwap.py` | How binding is `price > VWAP`, and is it redundant with the 9 EMA? (offline) |
| `probe*.py`, `diag.py`, `loo.py`, `gradient.py` | Older one-off probes; superseded by the above |

Convention: a diagnostic that needs the engine's verdict calls
`engine20.run_day` — it never re-implements the gate (see `../HISTORY.md` #15).
