# edge-hunt/ — is any version of the bot positive after costs, on data it never saw?

A holdout-guarded search, started 2026-09-26. The protocol was written and
committed before the first run: `PREREGISTRATION.md`. Code in
`scripts/edge_hunt/`, guards in `tests/test_edge_hunt.py`.

| Path | What |
|---|---|
| `PREREGISTRATION.md` | the benchmark (his published figures), the split, the five-part adoption rule, the six families and their 449 configurations |
| `holdout_ledger.jsonl` | one line per holdout opening, written BEFORE the holdout is read; a family opens once |
| `results/registry.jsonl` | every configuration evaluated on train and validation, counted |
| results folder, spread_proxy.json | the spread model, calibrated on real NBBO quotes from train/validation fills |
| `results/` | per-family tables |
| `REPORT.md` | the verdict, in plain words, when the families are done |

Data (not committed, regenerable): `data/cache/edge/` — the compact bar store
(`scripts/edge_hunt/data.py`), the desk's plans (`plans.py`), Alpaca news,
SEC shares outstanding, NBBO quotes and ticks (`fetch.py`).
