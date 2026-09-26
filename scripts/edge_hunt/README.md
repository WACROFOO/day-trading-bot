# scripts/edge_hunt/ — the edge hunt's code

Protocol: `research/edge-hunt/PREREGISTRATION.md`. Tests: `tests/test_edge_hunt.py`.

| Module | What |
|---|---|
| `data.py` | the compact bar store from the Alpaca SIP history cache; the split (`split_of`) |
| `plans.py` | every plan the live desk's detector arms, over every symbol-day |
| `features.py` | point-in-time features: volume, relative volume, rank, headlines, SEC shares, former runner |
| `engine.py` | exit simulation, A10 stop-limit fills, the random-entry baseline |
| `costs.py` | IBKR fixed/tiered commissions, the spread proxy, cost in R at $20 risk |
| `protocol.py` | holdout ledger (one opening per family), registry, bootstrap, the adoption rule, one-position portfolio |
| `fetch.py` | Alpaca news / quotes / trades, the pre-market universe audit, SEC shares outstanding — cached under `data/cache/edge/` |
| `calibrate.py` | the spread proxy from real NBBO quotes (train/validation moments), its error on holdout moments |
| `families.py` | F1 selection, F2 pre-market, F4 exits/sizing, F5 new hypotheses: search on train/validation, one holdout opening |
| `micro.py` | F3, ten-second micro-pullbacks on the tick subset |
| `audit.py` | F2's universe audit: pre-market runners missing from the 09:30-gap universe |
