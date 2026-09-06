# Wiring the workstation to market data

> Every card on the desk is fed by exactly one normalized record stream. Learn
> that one contract and every integration below is the same job twice: fetch
> the vendor's shape, emit the record, verify in replay.

## 0. The contract

Nothing in the platform talks to a vendor. Everything talks to **normalized
records**, and the scanner engine consumes them identically whether they came
from a fixture, a free delayed feed, or a licensed real-time socket.

```jsonc
{"type":"reference","symbol":"ABCD","prev_close":5.10,"avg_daily_volume":250000,
 "high_52w":7.90,"float_shares":12000000,"float_quality":"verified",
 "daily_bars":[{"d":"2026-08-29","o":5.0,"h":5.2,"l":4.9,"c":5.1,"v":310000}]}

{"type":"news","symbol":"ABCD","provider_id":"bz-1234",
 "published_at":"2026-09-01T12:55:00Z","first_observed_at":"2026-09-01T12:56:35Z",
 "headline":"ABCD awarded $48M defense logistics contract","category":"contract"}

{"type":"bar","tf":"10s","symbol":"ABCD","ts":"2026-09-01T13:31:00Z",
 "open":6.28,"high":6.35,"low":6.27,"close":6.34,"volume":12066,
 "bid":6.33,"ask":6.35}

{"type":"halt","symbol":"DVLT","status":"halted","ts":"2026-09-01T13:47:00Z"}
```

Two entry points consume them:

| Use | Function | File |
|---|---|---|
| Batch → a replayable session | `build_session_from_records(records, id, name)` | `src/momentum_platform/dashboard/session_builder.py` |
| Streaming → live scanners | `ScannerEngine.process(MarketUpdate(...))` | `src/momentum_platform/engine.py` |

`tf:"10s"` is optional. When present the 1-minute bars the scanners consume are
**aggregated from it**, so the micro chart can never disagree with the
scanners. Omit it and minute bars pass through untouched.

## 1. Which card needs which stream

| Card | Needs | Without it |
|---|---|---|
| Five Pillars Scan | bars + `prev_close`, `avg_daily_volume`, `float_shares` | Runs on price and volume; the supply pillar fails as `unknown` |
| Running Up | bars only | Fully functional on minute bars |
| HOD Momentum | bars + `float_shares` for the branch label | Alerts fire; branch shows as unclassified |
| 1m / 5m / 10s charts | bars (`tf:"10s"` for the micro pane) | 10s pane shows an explicit "needs sub-minute data" note |
| Daily chart | `daily_bars` | Empty pane |
| Quote · supply · risk | bars + `bid`/`ask` + reference | Spread and float read `—` |
| Catalyst | news records | Shows "no qualifying headline", which is a valid state |
| Level 2 · Time & Sales | depth + prints (not yet wired) | Simulated ladder, labelled on the card |
| Setup verdict | everything above | Degrades pillar by pillar, never silently |

Nothing fabricates a value it does not have. That is the property to preserve
in every adapter you write.

## 2. Step 1 — choose the provider (the decision that gates everything)

| Provider | Good for | Watch |
|---|---|---|
| **Alpaca** | Simplest real-time start; WebSocket trades/quotes/bars, IEX free tier, SIP on paid | Confirm SIP vs IEX coverage — IEX alone misses most prints on thin small caps |
| **Polygon** | Broad US coverage, reference data and news in one vendor | Check plan latency tier and redistribution terms |
| **Databento** | Highest fidelity, real replay, a genuine path to L2/L3 later | Venue selection and licensing need care |
| **Intrinio** | Prices, fundamentals, news and movers together | Confirm exchange scope per dataset |

Verify before you sign: SIP vs single-venue; 04:00–20:00 ET extended hours;
corrections and cancels; NBBO quotes; timestamp precision; snapshot + stream
recovery; 1-minute historical replay; rate limits; corporate actions;
**display vs non-display** terms; redistribution rights.

Small-cap momentum lives on thin, fast names. A feed that misses odd-lot or
off-exchange prints will understate exactly the volume the strategy keys on.

## 3. Step 2 — the market-data adapter (lights up scanners and charts)

Create `src/momentum_platform/datasources/<vendor>_source.py`. Two functions,
mirroring `live_session.py`:

```python
def fetch_records(symbols, day=None) -> list[dict]:
    """Historical/batch: return reference + bar records for a session."""

async def stream(symbols, on_update) -> None:
    """Real-time: call on_update(MarketUpdate(...)) per trade or bar."""
```

Streaming shape:

```python
from momentum_platform.models import DataStatus
from momentum_platform.state import MarketUpdate

async def stream(symbols, on_update):
    async for msg in vendor_socket(symbols):          # your vendor's client
        if msg.type != "trade":
            continue
        on_update(MarketUpdate(
            symbol=msg.symbol,
            ts=msg.timestamp,                          # tz-aware UTC, vendor clock
            price=msg.price,
            size=msg.size,
            bid=msg.bid, ask=msg.ask,                  # from the quote stream
            data_status=DataStatus.LIVE,
        ))
```

Then drive the engine:

```python
engine = ScannerEngine(scanners=default_scanners(), router=build_router(), store=store)
engine.hot.load_reference(fetch_reference(symbols))
await stream(symbols, engine.process)
```

`HotState` builds 1-minute bars from ticks itself, so a trade stream is enough.

**Five rules that will bite you if you skip them.**

1. **Timestamps are the vendor's, never `now()`.** The platform measures
   latency as `scan_ts − event_ts`; using local time makes that metric lie.
2. **Never mix vendors** for price and volume until symbol mapping and
   timestamp behaviour are validated against each other.
3. **Honour corrections and cancels.** A cancelled trade that stays in
   cumulative volume inflates RVOL, which is a Confirmed pillar.
4. **Set `data_status` honestly.** `LIVE`, `DELAYED`, `REPLAY`, `STALE` — the
   header badge and every event carry it forward.
5. **Reconnect with a snapshot, not a gap.** On resume, pull the day's bars so
   far before resubscribing, or the session high and cumulative volume will be
   wrong for the rest of the day.

**Verify:** run your adapter against yesterday's session, build a session with
`build_session_from_records`, and diff the alert list against the same day
pulled from a second source. Then `python -m pytest tests/ -q`.

## 4. Step 3 — reference data and float (unlocks the supply pillar)

Float is the pillar most often wrong, and wrong float is worse than no float.

Emit three distinct fields — never collapse them:

```python
{"float_shares": 12_000_000, "float_quality": "verified"}                 # trustworthy
{"float_shares": 45_000_000, "float_quality": "shares_outstanding_proxy"} # labelled proxy
{"float_shares": None,       "float_quality": "unknown"}                  # honest gap
```

Only `verified` can pass the supply pillar. Refresh daily before the open and
re-check after any offering, split or conversion — float moves, and a stale
value silently changes the pillar.

Sources worth combining: your market-data vendor's reference endpoint,
SEC `data.sec.gov` company facts (free; descriptive `User-Agent`, ≤10 req/s,
cache by accession number), and a paid fundamentals vendor for coverage.

**Verify:** the Five Pillars card shows a real float with `verified`, and a
symbol you know has no reliable float shows `UNKNOWN` with the pillar failing.

## 5. Step 4 — news and catalyst (lights up the flames)

The flame is only as honest as its timestamps. You need three per item:

- `published_at` — the provider's own publication time; the flame is computed
  from this and nothing else;
- `first_observed_at` — when *you* received it; the card shows the gap, which
  is how you learn your feed's real latency;
- `provider_id` — stable, for dedupe and for correction/update handling.

```python
records.append({
    "type": "news", "symbol": symbol, "provider_id": item.id,
    "published_at": item.published.isoformat(),
    "first_observed_at": datetime.now(timezone.utc).isoformat(),
    "headline": item.title, "category": item.channel,
})
```

Licensed real-time news (Benzinga and similar) streams over WebSocket with
unique IDs and replay. Keep the token server-side; it must never reach the
browser.

The catalyst card classifies the headline into **hard / soft / dilutive** by
keyword and shows the grade beside the flame. That classifier is a labelled
heuristic in `app.js` (`CATALYST_RULES`) — extend it with the vocabulary your
provider actually uses, and remember the headline stays on screen precisely so
you can overrule it.

**Verify:** a headline you can timestamp independently shows the right flame
band (red ≤2h, orange ≤12h, yellow ≤24h) and a plausible observation latency.

## 6. Step 5 — halts (the one that protects you)

Never infer a halt from missing trades. Require an official status event.

- Free: the Nasdaq Trader halt RSS, updated once per minute — poll no faster.
- Better: your vendor's trading-status messages, if your licence includes them.

```python
{"type": "halt", "symbol": "DVLT", "status": "halted",  "ts": "..."}
{"type": "halt", "symbol": "DVLT", "status": "trading", "ts": "..."}
```

Halt transitions are `critical` severity and are never suppressed by cooldown
or consolidation. The Level 2 card shows a banner during a halt, because a
book mid-halt is not a picture of anything — and a stop does not protect you
through a reopen at a different price.

## 7. Step 6 — Level 2 and Time & Sales (the licensed one)

Today `_depth()` in `app.js` generates a deterministic ladder from the replay
snapshot, labelled **simulated** on the card. Replacing it is a contained job:

1. Licence depth data (Nasdaq TotalView, ARCA, or your vendor's aggregated
   book). This is a separate agreement from consolidated trades and quotes.
2. Normalize to price levels per side with size, venue and a sequence number.
3. Publish `{bids:[{price,size,mpid}], asks:[...], prints:[...]}` per symbol on
   the session/WebSocket.
4. In `renderL2`, replace the `_depth(...)` call with the streamed book. Every
   other line of that card — ladder, size bars, wall detection, tape colouring
   — already works on that shape.
5. Detect sequence gaps and recover from a fresh snapshot rather than
   patching. A silently wrong book is worse than no book.

Then delete the `simulated` tag — and only then.

## 8. Step 7 — before you call it live

- [ ] Header shows `LIVE`, not `DELAYED` or `REPLAY`.
- [ ] Event-to-scan p95 under 500 ms; scan-to-browser p95 under 1 s.
- [ ] Reconnect mid-session leaves session high and cumulative volume correct.
- [ ] A cancelled trade does not remain in RVOL.
- [ ] Float reads `verified` for names you can confirm, `unknown` otherwise.
- [ ] Flame bands match an independently timestamped headline.
- [ ] A real halt and resume produce two critical alerts.
- [ ] No token, key or webhook URL appears anywhere in the page source.
- [ ] Replaying yesterday reproduces yesterday's alerts exactly.
- [ ] Every unconfirmed threshold still reads as an approximation on screen.

## 9. What it costs, in the order it becomes worth paying for

| Stage | Adds | Rough monthly |
|---|---|---|
| Now | Delayed bars, delayed news, universe scan | €0 |
| 1 | Real-time consolidated trades and quotes | €30–200 |
| 2 | Licensed real-time news with timestamps | €30–150 |
| 3 | Fundamentals with reliable float | €0–100 |
| 4 | Depth of book | €50–200+ per venue |

Stage 1 is the only one that changes what you can *do*. Stages 2–4 change how
well you do it. Buy them in that order, and only after the delayed platform has
shown you it earns the upgrade.
