"""Persistent, read-only IBKR market-data service.

This is the P0 architecture from the 2026-09-03 handoff audit: one TWS
connection that stays up, live top-of-book tickers and five-second real-time
bars for the desk symbols, a single rolling bar store that every timeframe is
derived from, freshness/staleness health, and reconnect with resubscribe. It
replaces "rebuild the whole session from history every N seconds".

Invariants (from the audit, section 11):

- read-only. The connection is opened with readonly=True and this module has
  no order, cancel-order or open-order method. TWS remains the boundary.
- never delayed. Market-data type 1 is requested; a ticker that reports type 3
  or 4 is rejected and the health state says DELAYED. Nothing here ever shows
  a delayed print under a LIVE badge.
- never invented. A ten-second candle closes only after two real closed
  five-second bars; a minute closes from the same five-second bars; empty
  buckets stay absent. No timeframe can disagree with another because all of
  them are views of one store.
- never stale-but-green. Health carries the last quote time, the last bar
  time, a connection generation, a reconnect count and pacing state; it turns
  STALE after a session-aware threshold and OFFLINE on disconnect.

The service is written against ib_async 2.1.0 (protocol 178, share volume)
but takes its IB object by injection, so it is fully testable offline with a
fake. It emits provider-neutral MarketUpdate objects to a callback; the
scanner engine and the browser transport consume those, not IBKR types.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Deque, Dict, List, Optional
from zoneinfo import ZoneInfo

from ..models import Bar, DataStatus
from ..state import MarketUpdate

UTC = timezone.utc
ET = ZoneInfo("America/New_York")

LIVE_TYPE = 1                     # IBKR market-data type codes
FROZEN_TYPE = 2
DELAYED_TYPES = (3, 4)


# ---------------------------------------------------------------- bars -----


@dataclass
class Bar5s:
    """One closed five-second bar. `ts` is the bar's START, tz-aware UTC."""

    symbol: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


def _floor(ts: datetime, seconds: int) -> datetime:
    epoch = int(ts.timestamp()) // seconds * seconds
    return datetime.fromtimestamp(epoch, UTC)


class BarStore:
    """Rolling per-symbol store of closed five-second bars, and the one place
    ten-second and one-minute candles are derived from.

    - append() ignores a bar whose start already exists (backfill/live overlap,
      a re-sent bar after reconnect) — no duplicate timestamps, ever;
    - a ten-second candle is emitted only when BOTH of its five-second halves
      are present, so it is never a half-bar drawn as a whole one;
    - a minute candle is emitted when the following minute's first bar arrives
      (the minute is then known to be closed) or on explicit flush.
    """

    def __init__(self, keep_seconds: int = 6 * 3600) -> None:
        self.keep = keep_seconds
        self._bars: Dict[str, Dict[int, Bar5s]] = {}
        self._emitted_10s: Dict[str, set] = {}
        self._emitted_1m: Dict[str, set] = {}

    # -- ingest ---------------------------------------------------------------

    def append(self, bar: Bar5s) -> bool:
        book = self._bars.setdefault(bar.symbol, {})
        key = int(bar.ts.timestamp())
        if key in book:
            return False                         # duplicate: overlap or replay
        book[key] = bar
        cutoff = key - self.keep
        for old in [k for k in book if k < cutoff]:
            del book[old]
        return True

    def bars5s(self, symbol: str) -> List[Bar5s]:
        return [self._bars.get(symbol, {})[k] for k in sorted(self._bars.get(symbol, {}))]

    # -- derived timeframes ---------------------------------------------------

    def _aggregate(self, symbol: str, start_epoch: int, seconds: int) -> Optional[Bar]:
        book = self._bars.get(symbol, {})
        keys = [k for k in range(start_epoch, start_epoch + seconds, 5) if k in book]
        if not keys:
            return None
        parts = [book[k] for k in keys]
        tf = {10: "10s", 60: "1m"}.get(seconds, f"{seconds}s")
        return Bar(symbol=symbol, timeframe=tf, ts=datetime.fromtimestamp(start_epoch, UTC),
                   open=parts[0].open, high=max(p.high for p in parts),
                   low=min(p.low for p in parts), close=parts[-1].close,
                   volume=sum(p.volume for p in parts))

    def closed_10s(self, symbol: str) -> List[Bar]:
        """Ten-second candles whose two halves are both present, not yet emitted."""
        book = self._bars.get(symbol, {})
        done = self._emitted_10s.setdefault(symbol, set())
        out = []
        for k in sorted(book):
            start = k // 10 * 10
            if start in done:
                continue
            if start in book and start + 5 in book:
                bar = self._aggregate(symbol, start, 10)
                if bar is not None:
                    out.append(bar)
                    done.add(start)
        return out

    def closed_1m(self, symbol: str, now: Optional[datetime] = None) -> List[Bar]:
        """Minutes that are known to be over: a later minute has data, or
        `now` is past the minute's end plus a five-second grace."""
        book = self._bars.get(symbol, {})
        if not book:
            return []
        done = self._emitted_1m.setdefault(symbol, set())
        minutes = sorted({k // 60 * 60 for k in book})
        latest = minutes[-1]
        now_epoch = int((now or datetime.now(UTC)).timestamp())
        out = []
        for m in minutes:
            if m in done:
                continue
            closed = m < latest or now_epoch >= m + 65
            if closed:
                bar = self._aggregate(symbol, m, 60)
                if bar is not None:
                    out.append(bar)
                    done.add(m)
        return out

    def candles_10s(self, symbol: str) -> List[Bar]:
        """Every complete ten-second candle in the store (both halves present),
        oldest first — the chart's history, independent of the emit-once set."""
        book = self._bars.get(symbol, {})
        out = []
        for start in sorted({k // 10 * 10 for k in book}):
            if start in book and start + 5 in book:
                bar = self._aggregate(symbol, start, 10)
                if bar is not None:
                    out.append(bar)
        return out

    def forming_1m(self, symbol: str) -> Optional[Bar]:
        """The current, still-open minute — for the chart's last candle."""
        book = self._bars.get(symbol, {})
        if not book:
            return None
        latest = max(book) // 60 * 60
        return self._aggregate(symbol, latest, 60)


# -------------------------------------------------------------- health -----


@dataclass
class Health:
    provider: str = "ibkr"
    state: str = "OFFLINE"                  # LIVE | STALE | DELAYED | OFFLINE
    connected: bool = False
    read_only: bool = True
    market_data_type: Optional[int] = None
    server_version: Optional[int] = None
    generation: int = 0                     # increments on every (re)connect
    reconnects: int = 0
    last_quote_at: Optional[datetime] = None
    last_bar_at: Optional[datetime] = None
    last_error: Optional[str] = None
    pacing: bool = False
    subscriptions: int = 0
    messages: Deque[str] = field(default_factory=lambda: deque(maxlen=20))

    def as_dict(self) -> dict:
        iso = lambda d: d.astimezone(UTC).isoformat(timespec="seconds") if d else None
        return {
            "provider": self.provider, "state": self.state, "connected": self.connected,
            "readOnly": self.read_only, "marketDataType": self.market_data_type,
            "serverVersion": self.server_version, "generation": self.generation,
            "reconnects": self.reconnects, "lastQuoteAt": iso(self.last_quote_at),
            "lastBarAt": iso(self.last_bar_at), "lastError": self.last_error,
            "pacing": self.pacing, "subscriptions": self.subscriptions,
            "messages": list(self.messages),
        }


def stale_threshold_seconds(now: Optional[datetime] = None) -> int:
    """How long without a bar before LIVE becomes STALE, by session.

    Regular hours: a five-second bar is due every five seconds; twenty seconds
    of silence on a subscribed name is a dead stream, not a quiet stock (IBKR
    sends flat bars). Extended hours are thinner; allow a minute."""
    et = (now or datetime.now(UTC)).astimezone(ET)
    hhmm = et.hour * 60 + et.minute
    if 9 * 60 + 30 <= hhmm < 16 * 60:
        return 20
    return 60


# ------------------------------------------------------------- service -----


class IbkrStream:
    """Owns the connection, the subscriptions and the store.

    `ib` is any object with the ib_async IB surface this class uses:
    connect(host, port, clientId, readonly, timeout), disconnect(),
    isConnected(), reqMarketDataType(n), reqMktData(contract) -> ticker,
    cancelMktData(contract), reqRealTimeBars(contract, 5, 'TRADES', useRTH)
    -> bar list with updateEvent, cancelRealTimeBars(list),
    reqHistoricalData(...) -> bars, qualifyContracts(*c), and `client.serverVersion()`.
    The default builds a real ib_async.IB(); tests inject a fake.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 7496, client_id: int = 27,
                 timeout: float = 12.0, max_lines: int = 50, ib=None,
                 on_update: Optional[Callable[[MarketUpdate], None]] = None,
                 clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self.host, self.port, self.client_id, self.timeout = host, port, client_id, timeout
        self.max_lines = max_lines
        self.store = BarStore()
        self.health = Health()
        self.on_update = on_update or (lambda u: None)
        self.clock = clock
        self._ib = ib
        self._symbols: List[str] = []
        self._contracts: Dict[str, object] = {}
        self._tickers: Dict[str, object] = {}
        self._bar_lists: Dict[str, object] = {}
        self._lock = threading.RLock()
        self._backoff = 1.0

    # -- explicit non-surface -------------------------------------------------
    # There is deliberately no order-placing, order-cancelling or open-order
    # method here, and no call into TWS that transmits anything.
    # A test asserts that stays true.

    @property
    def ib(self):
        if self._ib is None:
            from ib_async import IB
            self._ib = IB()
        return self._ib

    # -- connection -----------------------------------------------------------

    def connect(self) -> Health:
        h = self.health
        try:
            self.ib.connect(self.host, self.port, clientId=self.client_id,
                            readonly=True, timeout=self.timeout)
        except Exception as exc:
            h.connected, h.state, h.last_error = False, "OFFLINE", f"connect failed: {exc}"
            h.messages.append(h.last_error)
            return h
        h.connected = True
        h.generation += 1
        h.read_only = True
        try:
            h.server_version = self.ib.client.serverVersion()
        except Exception:
            h.server_version = None
        self.ib.reqMarketDataType(LIVE_TYPE)
        h.market_data_type = LIVE_TYPE
        h.state = "LIVE"
        h.last_error = None
        self._backoff = 1.0
        h.messages.append(f"connected gen {h.generation} to {self.host}:{self.port} client {self.client_id}")
        return h

    def disconnect(self) -> None:
        with self._lock:
            for sym in list(self._symbols):
                self._unsubscribe(sym)
            try:
                self.ib.disconnect()
            except Exception:
                pass
            self.health.connected = False
            self.health.state = "OFFLINE"

    # -- subscriptions --------------------------------------------------------

    def _contract(self, symbol: str):
        if symbol not in self._contracts:
            try:
                from ib_async import Stock
            except ImportError:                      # offline tests without ib_async
                Stock = _PlainStock
            c = Stock(symbol, "SMART", "USD", primaryExchange="NASDAQ")
            try:
                self.ib.qualifyContracts(c)
            except Exception as exc:
                self.health.messages.append(f"{symbol}: qualify failed: {exc}")
            self._contracts[symbol] = c
        return self._contracts[symbol]

    def subscribe(self, symbols: List[str], backfill_seconds: int = 1800) -> List[str]:
        """Top-of-book + five-second bars for each symbol, within line limits."""
        added = []
        with self._lock:
            for sym in [s.strip().upper() for s in symbols if s and s.strip()]:
                if sym in self._symbols:
                    continue
                if len(self._symbols) * 2 >= self.max_lines:
                    self.health.messages.append(f"{sym}: not subscribed — market-data line limit {self.max_lines}")
                    continue
                c = self._contract(sym)
                self._tickers[sym] = self.ib.reqMktData(c, "", False, False)
                bars = self.ib.reqRealTimeBars(c, 5, "TRADES", False)
                self._bar_lists[sym] = bars
                try:
                    bars.updateEvent += self._on_realtime_bars
                except Exception:
                    pass
                self._symbols.append(sym)
                added.append(sym)
                if backfill_seconds:
                    self.backfill(sym, backfill_seconds)
            self.health.subscriptions = len(self._symbols) * 2
        return added

    def _unsubscribe(self, sym: str) -> None:
        c = self._contracts.get(sym)
        try:
            if c is not None:
                self.ib.cancelMktData(c)
            if sym in self._bar_lists:
                self.ib.cancelRealTimeBars(self._bar_lists[sym])
        except Exception:
            pass
        self._tickers.pop(sym, None)
        self._bar_lists.pop(sym, None)
        if sym in self._symbols:
            self._symbols.remove(sym)
        self.health.subscriptions = len(self._symbols) * 2

    def unsubscribe(self, symbols: List[str]) -> None:
        with self._lock:
            for s in symbols:
                self._unsubscribe(s.upper())

    @property
    def symbols(self) -> List[str]:
        return list(self._symbols)

    # -- backfill -------------------------------------------------------------

    def backfill(self, symbol: str, seconds: int = 1800) -> int:
        """Bounded five-second history at startup or after a gap. Bars already
        in the store (live overlap) are ignored by the store, so this cannot
        double-count."""
        c = self._contract(symbol)
        try:
            hist = self.ib.reqHistoricalData(c, "", f"{int(seconds)} S", "5 secs",
                                             "TRADES", False, formatDate=2)
        except Exception as exc:
            self.health.messages.append(f"{symbol}: backfill failed: {exc}")
            self.health.pacing = "pacing" in str(exc).lower()
            return 0
        n = 0
        for b in hist or []:
            ts = b.date if isinstance(b.date, datetime) else datetime.fromisoformat(str(b.date))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if self.store.append(Bar5s(symbol, ts.astimezone(UTC), float(b.open), float(b.high),
                                       float(b.low), float(b.close), int(b.volume))):
                n += 1
        self._emit_closed(symbol)
        return n

    # -- live events ----------------------------------------------------------

    def _on_realtime_bars(self, bars, has_new_bar: bool = True) -> None:
        """ib_async RealTimeBarList update: the last element is the newest
        closed five-second bar."""
        if not bars:
            return
        b = bars[-1]
        sym = getattr(getattr(bars, "contract", None), "symbol", None) or self._symbol_of(bars)
        if not sym:
            return
        self.ingest_bar5s(sym, b.time, b.open_, b.high, b.low, b.close, int(b.volume))

    def _symbol_of(self, bars) -> Optional[str]:
        for sym, lst in self._bar_lists.items():
            if lst is bars:
                return sym
        return None

    def ingest_bar5s(self, symbol: str, ts: datetime, o: float, h: float, l: float, c: float, v: int) -> None:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        if not self.store.append(Bar5s(symbol, ts.astimezone(UTC), o, h, l, c, v)):
            return
        self.health.last_bar_at = self.clock()
        self._emit_closed(symbol)

    def ingest_quote(self, symbol: str, price: Optional[float], size: float = 0.0,
                     bid: Optional[float] = None, ask: Optional[float] = None,
                     market_data_type: Optional[int] = None) -> None:
        if market_data_type in DELAYED_TYPES:
            self.health.market_data_type = market_data_type
            self.health.state = "DELAYED"
            self.health.messages.append(f"{symbol}: DELAYED market data type {market_data_type} rejected")
            return
        self.health.last_quote_at = self.clock()
        self.on_update(MarketUpdate(symbol=symbol, ts=self.clock(), price=price, size=size,
                                    bid=bid, ask=ask, data_status=DataStatus.LIVE))

    def poll_tickers(self) -> None:
        """Read the current top-of-book from each ticker; call on a short timer."""
        for sym, t in list(self._tickers.items()):
            price = getattr(t, "last", None)
            if price is None or price != price:          # NaN
                continue
            self.ingest_quote(sym, float(price), float(getattr(t, "lastSize", 0) or 0),
                              _num(getattr(t, "bid", None)), _num(getattr(t, "ask", None)),
                              getattr(t, "marketDataType", None))

    def _emit_closed(self, symbol: str) -> None:
        for bar in self.store.closed_1m(symbol, now=self.clock()):
            self.on_update(MarketUpdate(symbol=symbol, ts=bar.ts, price=bar.close,
                                        size=bar.volume, bar=bar, data_status=DataStatus.LIVE))

    # -- health / reconnect ---------------------------------------------------

    def check(self) -> Health:
        """Refresh the state from the clock and the socket. Call every second."""
        h = self.health
        now = self.clock()
        if not self.ib.isConnected():
            if h.connected:
                h.messages.append("socket dropped")
            h.connected, h.state = False, "OFFLINE"
            return h
        if h.state == "DELAYED":
            return h
        thresh = stale_threshold_seconds(now)
        fresh = h.last_bar_at or h.last_quote_at
        if self._symbols and (fresh is None or (now - fresh).total_seconds() > thresh):
            h.state = "STALE"
        else:
            h.state = "LIVE"
        return h

    def reconnect(self) -> Health:
        """Drop, back off, connect again, resubscribe every symbol once."""
        wanted = list(self._symbols)
        with self._lock:
            for sym in wanted:
                self._unsubscribe(sym)
            try:
                self.ib.disconnect()
            except Exception:
                pass
            time.sleep(min(self._backoff, 30.0))
            self._backoff = min(self._backoff * 2, 30.0)
            h = self.connect()
            if h.connected:
                h.reconnects += 1
                self.subscribe(wanted, backfill_seconds=120)   # short gap fill only
            return h


@dataclass
class _PlainStock:
    """Stand-in contract when ib_async is not installed (tests only)."""

    symbol: str
    exchange: str = "SMART"
    currency: str = "USD"
    primaryExchange: str = "NASDAQ"


def _num(v):
    try:
        f = float(v)
        return None if f != f else f
    except (TypeError, ValueError):
        return None
