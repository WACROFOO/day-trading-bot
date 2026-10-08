# dashboard/

The desk's server, event stream and browser page.

| Module | What |
|---|---|
| `ibkr_desk.py` | ONE worker thread owning both IBKR connections; rebuilds the session in memory every 3 s. On each closed 10-second candle it also evaluates setup S (`../green_run.py`) and logs it to the ledger's `green_run_signals` — a shadow log, no decision, no order. `DESK_RECORD_UNTIL` (set by `scripts/day.py`) ends every exercise write: an ISO instant for the bot's day, `0` for the desk alone; unset, a desk by hand writes as before |
| `server.py` | HTTP: the page, `/api/v1/stream`, `/health` (with the app build and the commit the desk started on), `/screener`, `/desk/add`, `/tape`; the owner's POSTs `/manual`, `/settings`, `/focus` (JSON only; a viewer key is refused) |
| `stream.py` | server-sent events: quote, bar10s, bar1m, health, screener, session, resync, and `tape` — live only, never kept for replay |
| `cards.py` | the decision cards for a built session: the detector re-run, the catalyst read, the bot's answer and the owner's calls from the ledger; sizes only on the owner's own stated risk |
| `session_builder.py` | turns reference data, history and live candles into the session the page renders |
| `web/` | the page itself — `app.js`, `live.js`, `index.html`, `styles.css`, and a vendored chart library |

**One store, every timeframe.** 10-second candles and minutes derive from the
same 5-second bars; a candle exists only when both halves arrived, so no two
panes can disagree and nothing is interpolated.

The setup verdict currently computed in `web/app.js` is a browser-side pillar
SCORE. The strategy is a reject CASCADE. Moving it server-side is Phase 1 of
the execution plan.

✓ REMEDIATED 2026-10-08 — the verdict is the server's (`../decision_card.py`
via `cards.py`); the page renders it and recomputes nothing. The browser path
above only runs for a session that ships no cards.
