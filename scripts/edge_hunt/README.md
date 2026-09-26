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
| `fetch.py` | Alpaca news / quotes / trades and SEC shares outstanding, cached under `data/cache/edge/` |
