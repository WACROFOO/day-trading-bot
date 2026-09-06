# src/momentum_platform/

The live desk. Discovers candidates, evaluates them, draws a plan, states a
verdict. **It does not trade** — no order path exists in this package and
`test_no_order_surface_anywhere_in_the_ibkr_path` fails if one appears.

| Module | What |
|---|---|
| `pullback.py` | the first-pullback state machine: impulse -> pullback -> ARMED -> TRIGGERED. Plans freeze when armed and never repaint |
| `engine.py` | builds a session from reference data, history and live candles |
| `formulas.py` | RVOL and the derived measures, with their denominators named |
| `models.py` · `state.py` · `store.py` | records, per-symbol state, persistence |
| `sessions.py` | market phases on the New York clock |
| `catalyst.py` | catalyst evidence, three channels |
| `desk_profile.py` | the shared rule set and the fingerprint that proves parity |
| `notify.py` | alerts out |
| `cli.py` | entry point |
| `datasources/` | the feeds — IBKR, Alpaca, Yahoo, SEC, replay |
| `scanners/` | Five Pillars and the momentum-event approximations |
| `dashboard/` | the server, the event stream and the browser desk |

Every non-pillar scanner branch is an **Approximation** and is labelled as one
wherever it appears. The Confirmed pillars are price $2-20, gain >=10%, daily
RVOL >=5x, float <20M, catalyst.
