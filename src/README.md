# src/

Application code (as opposed to research code, which lives under `research/`).

| Package | What |
|---|---|
| `paper_trading/` | Manual paper-trading platform — see its README |
| `momentum_platform/` | The live desk: IBKR read-only stream (clients 27/28), the scanner engine, `pullback.py` (first-pullback state machine, frozen non-repainting plans), and the browser dashboard under `dashboard/`. **No order path exists here, by design and by test** |
