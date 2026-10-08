# src/momentum_platform/

The live desk. Discovers candidates, evaluates them, draws a plan, states a
verdict. **It does not trade** — no order path exists in this package and
`test_no_order_surface_anywhere_in_the_ibkr_path` fails if one appears.

| Module | What |
|---|---|
| `pullback.py` | the first-pullback state machine: impulse -> pullback -> ARMED -> TRIGGERED. Plans freeze when armed and never repaint |
| `green_run.py` | setup S, the green-run continuation (addendum 2026-10-05 of `research/edge-hunt/PREREGISTRATION.md`), for the desk's **shadow log**: 1-minute context, 10-second pause, entry/stop, refusals — one reasoned `Check` per condition. Parity with the frozen `scripts/green_run.py` is a test (`tests/test_green_run.py`). Logged to `green_run_signals`, never a decision, never an order; `score()` is the after-the-close bar replay `exercise.py green-runs` uses |
| `engine.py` | builds a session from reference data, history and live candles |
| `formulas.py` | RVOL and the derived measures, with their denominators named |
| `models.py` · `state.py` · `store.py` | records, per-symbol state, persistence |
| `sessions.py` | market phases on the New York clock |
| `catalyst.py` | catalyst evidence, three channels; `card_read` is the decision card's two-line grade (rules C0–C13 in `knowledge-base/strategies/CATALYST.md`) |
| `cascade.py` | the reject cascade — the single authority on whether a name is tradeable (FILTERS.md Layer 1 kills, Layer 2 chart gates) |
| `indicators.py` | the Layer 2 chart gates from minute bars alone: VWAP, EMA 9, MACD |
| `five_minute.py` | the 5-minute state of a name whose 1-minute chart gives no pullback — display only |
| `decision_card.py` | the per-symbol card a manual trader acts on: REVIEW / WATCH / WAIT / NO, the reason, the level, the gates as lamps, the bot's own order (2026-10-08) |
| `order_math.py` | the order arithmetic the bot executes and the desk displays — one copy, re-exported by `execution.intent` |
| `tape.py` | Time & Sales: one name's prints read against the quote that stood, the 60-s and 10-s facts, gaps said (2026-10-08). Facts, never a gate |
| `holidays.py` | NYSE full-day and early closes, as data |
| `desk_profile.py` | the shared rule set and the fingerprint that proves parity |
| `notify.py` | alerts out |
| `cli.py` | entry point |
| `datasources/` | the feeds — IBKR, Alpaca, Yahoo, SEC, replay |
| `scanners/` | Five Pillars and the momentum-event approximations |
| `dashboard/` | the server, the event stream and the browser desk |
| `microflow/` | Phase 0 of the 10-second micro-pullback study — `config.py` (every parameter carries its provenance), `bars.py` (10s candles and the 1-minute sync assertion), `spread.py` (the gate that fails closed), `measure.py` (the GO/NO-GO read-out). Measures the tape; decides no trades. See `docs/PLAN-10s-micro-pullback.md` |

Every non-pillar scanner branch is an **Approximation** and is labelled as one
wherever it appears. The Confirmed pillars are price $2-20, gain >=10%, daily
RVOL >=5x, float <20M, catalyst.
