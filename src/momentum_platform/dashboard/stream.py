"""Server-sent events transport for the live desk.

P1 of the 2026-09-03 handoff audit: the page must stop polling and reloading
itself. This module is the transport half of that — an in-process event hub
with monotonic ids, a bounded replay buffer, SSE framing, and resume from
`Last-Event-ID`. It does not know about IBKR or Alpaca; it carries whatever
the producers publish:

    quote        {symbol, price, size, bid, ask, ts}
    bar5s        {symbol, ts, open, high, low, close, volume}
    bar10s       same shape, only after both five-second halves closed
    bar1m        same shape, closed minutes only
    health       the provider Health.as_dict() plus builtAt
    screener     the screener payload (rows, source, asof, notes)
    symbol-added {symbol}
    alert        a scanner alert record
    resync       {reason} — the client fell off the buffer; reload state

Wiring into server.py (a `/api/v1/stream` GET that calls `serve_sse`) is
deliberately left to the wiring step so the user's uncommitted IBKR diff to
server.py is not touched from here. Everything else is complete and tested.
"""

from __future__ import annotations

import json
import queue
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, List, Optional, Set

from ..state import MarketUpdate

UTC = timezone.utc

EVENT_TYPES = ("quote", "bar5s", "bar10s", "bar1m", "health", "screener",
               "symbol-added", "alert", "resync")


@dataclass(frozen=True)
class Event:
    id: int
    type: str
    data: Any
    ts: float


def format_sse(event: Event) -> bytes:
    """One SSE frame. Data is JSON on a single `data:` line (no newlines in
    JSON output), so the frame is exactly four lines."""
    payload = json.dumps(event.data, default=str, separators=(",", ":"))
    return f"id: {event.id}\nevent: {event.type}\ndata: {payload}\n\n".encode()


HEARTBEAT = b": ping\n\n"

SSE_HEADERS = (("Content-Type", "text/event-stream; charset=utf-8"),
               ("Cache-Control", "no-store"),
               ("Connection", "keep-alive"),
               ("X-Accel-Buffering", "no"))


class EventHub:
    """Fan-out of typed events to any number of subscribers, with a replay
    buffer so a client that reconnects gets what it missed — or is told to
    resync when it fell further behind than the buffer keeps."""

    def __init__(self, capacity: int = 4000) -> None:
        self._buf: Deque[Event] = deque(maxlen=capacity)
        self._next = 1
        self._lock = threading.Lock()
        self._subs: Set["queue.Queue[Event]"] = set()
        self.published = 0

    # -- producers -------------------------------------------------------------

    def publish(self, type: str, data: Any) -> Event:
        if type not in EVENT_TYPES:
            raise ValueError(f"unknown event type {type!r}")
        with self._lock:
            ev = Event(self._next, type, data, time.time())
            self._next += 1
            self._buf.append(ev)
            self.published += 1
            subs = list(self._subs)
        for q in subs:
            try:
                q.put_nowait(ev)
            except queue.Full:
                pass                                   # slow client: it will resync
        return ev

    # -- consumers -------------------------------------------------------------

    @property
    def last_id(self) -> int:
        return self._next - 1

    @property
    def oldest_id(self) -> Optional[int]:
        return self._buf[0].id if self._buf else None

    def since(self, last_event_id: Optional[int]) -> List[Event]:
        """Events after `last_event_id`. If that id is older than the buffer,
        the caller gets a single `resync` event instead of a partial history:
        a client that replays a gap would draw candles with a hole in them."""
        with self._lock:
            if last_event_id is None:
                return []
            oldest = self.oldest_id
            if oldest is not None and last_event_id < oldest - 1:
                return [Event(self.last_id, "resync", {"reason": "buffer overrun",
                                                       "lastEventId": last_event_id}, time.time())]
            return [e for e in self._buf if e.id > last_event_id]

    def subscribe(self, last_event_id: Optional[int] = None, maxsize: int = 2000) -> "queue.Queue[Event]":
        q: "queue.Queue[Event]" = queue.Queue(maxsize=maxsize)
        with self._lock:
            self._subs.add(q)
        for ev in self.since(last_event_id):
            q.put_nowait(ev)
        return q

    def unsubscribe(self, q: "queue.Queue[Event]") -> None:
        with self._lock:
            self._subs.discard(q)

    @property
    def subscribers(self) -> int:
        with self._lock:
            return len(self._subs)


def parse_last_event_id(value: Optional[str]) -> Optional[int]:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def serve_sse(hub: EventHub, wfile, last_event_id: Optional[int] = None,
              heartbeat_seconds: float = 15.0, max_events: Optional[int] = None,
              stop: Optional[Callable[[], bool]] = None, flush: Optional[Callable[[], None]] = None) -> int:
    """Blocking loop: write frames to `wfile` until the socket breaks, `stop()`
    says so, or `max_events` frames were sent (tests). Returns frames written.
    Headers are the caller's job (SSE_HEADERS)."""
    q = hub.subscribe(last_event_id)
    sent = 0
    try:
        while True:
            if stop is not None and stop():
                break
            if max_events is not None and sent >= max_events:
                break
            try:
                ev = q.get(timeout=heartbeat_seconds)
            except queue.Empty:
                wfile.write(HEARTBEAT)
                if flush:
                    flush()
                continue
            wfile.write(format_sse(ev))
            if flush:
                flush()
            sent += 1
    except (BrokenPipeError, ConnectionResetError, OSError):
        pass
    finally:
        hub.unsubscribe(q)
    return sent


# -- producers: provider-neutral MarketUpdate -> events ------------------------

def _iso(ts: datetime) -> str:
    return ts.astimezone(UTC).isoformat(timespec="seconds")


def bar_payload(bar) -> Dict[str, Any]:
    return {"symbol": bar.symbol, "tf": bar.timeframe, "ts": _iso(bar.ts), "t": int(bar.ts.timestamp()),
            "open": bar.open, "high": bar.high, "low": bar.low, "close": bar.close, "volume": bar.volume}


class UpdatePublisher:
    """Turns MarketUpdate objects (quotes and closed minute bars) into hub
    events, and drains a BarStore's closed ten-second candles on demand. This
    is the glue an IbkrStream `on_update` callback plugs into."""

    def __init__(self, hub: EventHub) -> None:
        self.hub = hub

    def __call__(self, update: MarketUpdate) -> Event:
        if update.bar is not None:
            tf = update.bar.timeframe
            kind = {"1m": "bar1m", "10s": "bar10s", "5s": "bar5s"}.get(tf, "bar1m")
            return self.hub.publish(kind, bar_payload(update.bar))
        return self.hub.publish("quote", {
            "symbol": update.symbol, "ts": _iso(update.ts), "price": update.price,
            "size": update.size, "bid": update.bid, "ask": update.ask,
            "status": getattr(update.data_status, "value", str(update.data_status)),
        })

    def publish_closed_10s(self, store, symbols) -> int:
        n = 0
        for sym in symbols:
            for bar in store.closed_10s(sym):
                self.hub.publish("bar10s", bar_payload(bar))
                n += 1
        return n

    def publish_health(self, health_dict: Dict[str, Any]) -> Event:
        return self.hub.publish("health", health_dict)
