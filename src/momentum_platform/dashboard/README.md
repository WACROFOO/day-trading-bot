# dashboard/

The desk's server, event stream and browser page.

| Module | What |
|---|---|
| `ibkr_desk.py` | ONE worker thread owning both IBKR connections; rebuilds the session in memory every 3 s |
| `server.py` | HTTP: the page, `/api/v1/stream`, `/health`, `/screener`, `/desk/add` |
| `stream.py` | server-sent events: quote, bar10s, bar1m, health, screener, session, resync |
| `session_builder.py` | turns reference data, history and live candles into the session the page renders |
| `web/` | the page itself — `app.js`, `live.js`, `index.html`, `styles.css`, and a vendored chart library |

**One store, every timeframe.** 10-second candles and minutes derive from the
same 5-second bars; a candle exists only when both halves arrived, so no two
panes can disagree and nothing is interpolated.

The setup verdict currently computed in `web/app.js` is a browser-side pillar
SCORE. The strategy is a reject CASCADE. Moving it server-side is Phase 1 of
the execution plan.
