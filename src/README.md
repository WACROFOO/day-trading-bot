# src/

Application code (as opposed to research code, which lives under `research/`).

| Package | What |
|---|---|
| `paper_trading/` | Manual paper-trading platform — see its README |
| `journal/` | The decision ledger and everything read back out of it — `ledger.py` (schema and writes), `replay.py` (R11: every stored decision must reproduce its verdict, classified by rule set), `actuals.py`, `controls.py`, `bars.py`, `risk.py`. The bus every other package talks through |
| `execution/` | The ONLY order path: `ibkr_trader.py` (client 31, port 4002, `readonly=False`), `runner.py`, `intent.py`, `policy.py`, `bridge.py`. Refuses any account not beginning `DU`. Kept out of `momentum_platform/` so the read-only guard there stays testable |
| `momentum_platform/` | The live desk: IBKR read-only stream (clients 27/28), the scanner engine, `pullback.py` (first-pullback state machine, frozen non-repainting plans), and the browser dashboard under `dashboard/`. **No order path exists here, by design and by test** |
