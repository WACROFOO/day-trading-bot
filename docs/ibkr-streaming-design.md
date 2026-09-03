# IBKR streaming: what is built, what is wired, what comes next

Status date: 2026-09-03. Companion to the handoff audit
`CLAUDE_IBKR_HANDOFF_AUDIT_20260903.md` (kept outside Git by the user).

## Why this document exists

The audit verified a read-only TWS connection on the user's Mac and listed
the P0/P1/P2 work needed before the desk is "live for real". That IBKR
integration (`ibkr_source.py`, `ibkr_session.py`, `verify_ibkr.py`,
`start_ibkr.sh`, `docs/ibkr-setup.md`, `tests/test_ibkr_source.py`, plus
edits to `server.py`, `session_builder.py`, `app.js`, `requirements.txt`,
`.env.example`, `README.md`) is **uncommitted on the user's machine** and
is not on `origin/claude/ross-trading-mastery-setup-q4cz29`. To avoid
colliding with that diff, everything in this round lives in **new files
only**. Wiring is described here and executed after the diff is pushed.

## Built and tested in this round (new files)

| File | Role | Tests |
|---|---|---|
| `src/momentum_platform/datasources/ibkr_stream.py` | Persistent read-only TWS client: one connection, top-of-book tickers + 5-second real-time bars per desk symbol, a single `BarStore` all timeframes derive from, `Health` with freshness, reconnect with resubscribe. | `tests/test_ibkr_stream.py` (21) |
| `src/momentum_platform/dashboard/stream.py` | Server-sent-events hub: monotonic ids, replay buffer, `Last-Event-ID` resume, `resync` on buffer overrun, heartbeat, `UpdatePublisher` mapping `MarketUpdate` to events. | `tests/test_stream.py` (12) |
| `src/momentum_platform/dashboard/web/live.js` | Browser `DeskLive`: one `EventSource`, typed handlers (`on(type, fn)`), state badge, resume id tracking, bad frames never advance the resume id. | node-driven test in `tests/test_stream.py` |

Invariants enforced by tests, mapped to the audit's rules:

| Audit rule | Where enforced |
|---|---|
| Keep `readonly=True`; expose no order surface | `IbkrStream.connect()` passes `readonly=True`; `test_the_module_exposes_no_order_surface` fails if any order method name appears in the module. |
| Market-data types 3 and 4 must fail | `ingest_quote()` rejects them, sets `Health.state = DELAYED`; `check()` never overrides DELAYED. |
| Do not interpolate empty ten-second bars | `BarStore.closed_10s()` emits a candle only when both five-second halves exist; `test_missing_half_is_not_interpolated`. |
| No duplicate timestamps; backfill/live overlap | `BarStore.append()` returns False on an existing start; overlap tests. |
| Minute must equal its sub-bars | `closed_1m()` aggregates the same store; `test_minute_equals_aggregate…`. |
| Freshness / stale-but-green | `stale_threshold_seconds()` 20 s RTH, 60 s extended; `check()` -> LIVE/STALE/OFFLINE from an injected clock. |
| Reconnect must resubscribe once, no duplicates | `reconnect()` unsubscribes, backs off (1,2,4…30 s), reconnects, resubscribes, 120 s gap backfill; `test_reconnect_resubscribes_each_symbol_once`. |
| Client ids 27 (desk) / 28 (scanner) | `IbkrStream(client_id=27)` default; the scanner process uses 28 (wiring step). |
| Line limits | `max_lines=50`, two lines per symbol, refusal is logged in `Health.messages`, never silent. |

## Wired (second round, same day)

The user asked to move to live IBKR data without waiting for the uncommitted
diff, so the wiring below was executed in this repository:

| File | Change |
|---|---|
| `src/momentum_platform/datasources/ibkr_scanner.py` | 10-query NASDAQ scanner union (5 codes × NMS/SCM), live snapshot rows, reference / daily / minute records, SEC float bound, Alpaca headlines. |
| `src/momentum_platform/dashboard/ibkr_desk.py` | One worker thread owning both TWS connections (27 desk, 28 scanner); pumps the ib_async loop, ticks health every second, rebuilds the session in memory every 10 s, scans every 120 s, queues cross-thread symbol adds. Duck-types `LiveSession`. |
| `src/momentum_platform/dashboard/server.py` | `--ibkr [SYMBOLS]`, `--ibkr-rescan`; `GET /api/v1/stream` (SSE); `provider` block in `/api/v1/health`; honest fallback to the recorded session when TWS is unreachable. |
| `src/momentum_platform/dashboard/web/app.js`, `index.html` | `live.js` loaded; live desks hide the replay transport; `streamFollow()` draws `bar10s`/`bar1m`/`quote` events in place, swaps the session in place on rebuild (no reload), provider badge LIVE/STALE/DELAYED/OFFLINE; provider-named "last print". |
| `src/momentum_platform/datasources/screener.py` | IEX rows whose last print predates the session are dropped (the "+30 % as of 307 h" rows). |
| `scripts/ibkr_preflight.py`, `scripts/start.sh --ibkr`, `.env.example`, `requirements.txt` | Preflight with exit codes; launcher mode; `IBKR_HOST/PORT`; `ib_async==2.1.0`. |
| `tests/fake_ibkr.py`, `tests/test_ibkr_desk.py`, `tests/test_live_ui.py` | Offline fake TWS; desk/scanner tests; end-to-end page test through the real server (Playwright). |

## Not done here, on purpose

- **No edits to `server.py`, `session_builder.py`, `app.js`, `index.html`,
  `requirements.txt`, `.env.example`, `README.md`.** They are in the user's
  uncommitted diff.
- **No TWS acceptance run.** The container has no TWS. The audit's preflight
  and acceptance checks run on the user's Mac after wiring.

## Wiring plan (execute after the IBKR diff is on the remote)

Line numbers refer to `origin/claude/ross-trading-mastery-setup-q4cz29`
at 604874b and will shift with the user's diff; the anchors are function
names.

### 1. `server.py`

1. `main()` (around line 334): add `--ibkr` (host:port, default
   `127.0.0.1:7496`), `--ibkr-client-id` (default 27), `--stream`
   (enable SSE; default on when `--ibkr` is set).
2. After the `LiveSession` is built and before `ThreadingHTTPServer(...)
   .serve_forever()` (line 389):
   ```python
   hub = EventHub()
   publisher = UpdatePublisher(hub)
   stream = IbkrStream(host, port, client_id=27, on_update=publisher)
   stream.connect(); stream.subscribe(live.symbols)
   ```
   plus a 1-second daemon thread: `stream.poll_tickers()`,
   `publisher.publish_closed_10s(stream.store, stream.symbols)`,
   `stream.check()`, publish `health` when the state or generation
   changes, `stream.reconnect()` when `check()` says OFFLINE.
3. `make_handler(...)` (line 258): accept `hub` and `stream`.
   - `GET /api/v1/stream`: send `SSE_HEADERS`, then
     `serve_sse(hub, self.wfile, parse_last_event_id(self.headers.get("Last-Event-ID")), flush=self.wfile.flush)`.
     `ThreadingHTTPServer` already gives each client its own thread.
   - `GET /api/v1/health` (line 287): merge `stream.health.as_dict()`
     under `"provider"` so the page badge reads LIVE/STALE/DELAYED/OFFLINE
     from the same object the tests exercise.
   - `GET /api/v1/desk/add`: after `holder.add_symbols(wanted)` call
     `stream.subscribe(added)` and publish `symbol-added`.
4. `LiveSession._build_live(full)`: when a stream is attached, the history
   rebuild runs **once at startup and after `resync`**, not every 20 s.
   Between rebuilds the store is the truth: `session["symbols"][sym]["bars10s"]`
   and the minute series are appended from `bar10s` / `bar1m` events on the
   page, not recomputed on the server.

### 2. `session_builder.py`

`build_session_from_records(...)` needs no change for the first cut: the
startup rebuild still comes from records. Follow-up: a
`records_from_store(store, symbol)` helper that emits `bar` records with
`tf="10s"` and `tf="1m"` from `BarStore` so replay fixtures and live share
one path.

### 3. `app.js` and `index.html`

1. `index.html` line 207: add `<script src="live.js"></script>` before
   `app.js`.
2. `app.js`:
   - Replace the reload-on-`builtAt` poll (`setInterval` near line 1416)
     with `DeskLive.on("resync", …)` doing the same reload; keep the poll as
     a fallback only when `DeskLive.state === "unsupported"`.
   - `DeskLive.on("bar10s", b => appendBar10s(b))` and
     `on("bar1m", b => appendBar1m(b))`: push to the symbol's arrays and
     call the chart series `update()`; `PENDING_RANGES` logic stays as is
     because there is no reload.
   - `on("quote", q => …)`: update the quote card (`iexLast` becomes the
     provider's last, labelled by `health.provider`).
   - `on("health", h => …)`: the live badge shows `h.state`; anything but
     LIVE turns the badge amber/red and the verdict banner adds
     "data not live".
   - `on("screener", …)` replaces `pollScreener` (line 1519) when the
     server publishes screener payloads; the poll stays as fallback.
   - `on("symbol-added", …)` adds the tile without a reload.

### 4. Scanner process (client id 28)

A second `IbkrStream(client_id=28)` in the scanner loop, or the existing
IBKR scanner union from the user's diff, publishing `screener` events into
the same hub. The union of the ten NASDAQ scans is **not exhaustive**; the
payload's `notes` must keep saying so.

### 5. Acceptance on the user's Mac (after wiring)

1. TWS running, Read-Only API on, port 7496. `python scripts/verify_ibkr.py`
   (user's diff) must report market-data type 1 and server version 178.
2. Start the desk with `--ibkr`. `curl -N 127.0.0.1:8787/api/v1/stream`
   shows `health` then `bar5s`/`bar10s`/`bar1m` frames with increasing ids.
3. Pull the network cable or stop TWS: within 20 s (RTH) the badge says
   STALE, then OFFLINE; restart TWS: generation increments, reconnects = 1,
   no duplicate candles on the 10-second pane.
4. Switch TWS to delayed data on purpose: the badge must say DELAYED and
   the chart must stop advancing. Switch back and confirm LIVE.
5. Ten-second pane: every candle time is a multiple of 10 s; no candle
   exists where the 5-second stream had a gap.

## Commands for the user (paste as-is, no comments)

```
cd ~/day-trading-bot
git status --short
git add -A
git commit -m "IBKR read-only live data path from the 2026-09-03 handoff"
git push -u origin claude/ross-trading-mastery-setup-q4cz29
```

Do not add `.env`, `.venv` or any file containing an API key; `git status`
must not list them (`.gitignore` already excludes `.env` and `.venv`).
