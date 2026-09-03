"""The live desk on IBKR: one worker thread, two read-only TWS connections.

Why one thread: ib_async drives an asyncio loop, and its real-time bar and
ticker events are dispatched only while that loop runs (inside ib.sleep or a
blocking request). Spreading calls over HTTP handler threads would starve the
events or race the loop. So every TWS call — desk stream (client 27), scanner
union (client 28), history, snapshots — runs on this worker, which alternates
between pumping the loop and running queued jobs. HTTP handlers only read the
last built session and enqueue work.

What the worker does, on a schedule:
  every 0.25 s  pump the loop (events arrive: 5-second bars, tickers)
  every 1 s     poll tickers -> quote events; publish closed 10 s candles;
                refresh Health; publish it when it changes; reconnect if down
  every N s     rebuild the desk session in memory from reference + minute
                history + the live store, run the scanners, swap the session
  every M s     run the scanner union on client 28, publish the screener,
                and put new runners on the desk when there is room

Read-only, never delayed, never invented: the invariants live in
ibkr_stream.py; this file only schedules them.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
import traceback
from concurrent.futures import Future
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from ..datasources.ibkr_scanner import (IbkrError, build_ibkr_screener, daily_bars, minute_records,
                                        news_records, reference_record, sec_profile, store_records)
from ..datasources.ibkr_stream import IbkrStream
from .session_builder import build_session_from_records
from .stream import EventHub, UpdatePublisher

UTC = timezone.utc

# TWS messages that are acknowledgements, not problems. 162 "API scanner
# subscription cancelled" is TWS confirming that a one-shot scan was closed
# after it answered; ib_async logs it at ERROR and it filled the terminal with
# ten red lines per scan round.
BENIGN = ("API scanner subscription cancelled", "Market data farm connection is OK",
          "HMDS data farm connection is OK", "Sec-def data farm connection is OK")


class _TwsNoise(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(b in msg for b in BENIGN)


def quiet_tws_logs() -> None:
    for name in ("ib_async.wrapper", "ib_async.ib", "ib_async.client"):
        lg = logging.getLogger(name)
        if not any(isinstance(f, _TwsNoise) for f in lg.filters):
            lg.addFilter(_TwsNoise())


class _ScreenerView:
    def __init__(self, desk: "IbkrDesk") -> None:
        self.desk = desk
        self.use_yahoo = False

    def current(self) -> dict:
        return self.desk.screener_current()


class IbkrDesk:
    """Duck-types LiveSession for make_handler: current(), symbols,
    add_symbols(), screener.current(); adds hub (SSE) and health()."""

    def __init__(self, symbols: List[str], host: str = "127.0.0.1", port: int = 7496,
                 client_id: int = 27, scanner_client_id: int = 28, rebuild: int = 3,
                 rescan: int = 120, max_symbols: int = 8, min_price: float = 2.0,
                 max_price: float = 20.0, min_gain: float = 10.0, top: int = 30,
                 ib_factory: Optional[Callable[[], object]] = None,
                 clock: Callable[[], datetime] = lambda: datetime.now(UTC),
                 headlines: bool = True, sec: bool = True) -> None:
        self.host, self.port = host, port
        self.client_id, self.scanner_client_id = client_id, scanner_client_id
        self.rebuild, self.rescan, self.max_symbols = rebuild, rescan, max_symbols
        self.min_price, self.max_price, self.min_gain, self.top = min_price, max_price, min_gain, top
        self.symbols: List[str] = [s.strip().upper() for s in symbols if s and s.strip()]
        self.ib_factory = ib_factory
        self.clock = clock
        self.headlines, self.sec = headlines, sec
        self.hub = EventHub()
        self.publisher = UpdatePublisher(self.hub)
        self.stream: Optional[IbkrStream] = None
        self.scanner_ib = None
        self.screener = _ScreenerView(self)
        self.lock = threading.Lock()
        self.session: dict = {}
        self.built_at = 0.0
        self.refresh = rebuild
        self.source = "ibkr:" + ",".join(self.symbols)
        self._screener: dict = {"rows": [], "source": "ibkr", "asof": None,
                                "notes": ["scanner has not run yet"]}
        self._reference: Dict[str, dict] = {}
        self._minutes: Dict[str, List[dict]] = {}
        self._news: List[dict] = []
        self._news_note: Optional[str] = None
        self._jobs: "queue.Queue[tuple]" = queue.Queue()
        self._stop = threading.Event()
        self._last_state: Optional[tuple] = None
        self._next_tick = self._next_build = self._next_scan = 0.0
        self._worker_thread: Optional[threading.Thread] = None
        self.log: Callable[[str], None] = lambda m: print(m, flush=True)

    # -- lifecycle --------------------------------------------------------------

    def start(self, timeout: float = 600.0) -> dict:
        """Start the worker and block until the first session exists."""
        quiet_tws_logs()
        t = threading.Thread(target=self._worker, daemon=True, name="ibkr-desk")
        self._worker_thread = t
        t.start()
        return self.submit(self._bootstrap).result(timeout=timeout)

    def stop(self) -> None:
        self._stop.set()

    def submit(self, fn: Callable, *args) -> Future:
        fut: Future = Future()
        self._jobs.put((fn, args, fut))
        return fut

    def _worker(self) -> None:
        try:
            import asyncio
            asyncio.set_event_loop(asyncio.new_event_loop())
        except Exception:
            pass
        while not self._stop.is_set():
            self.run_pending()
            self.pump(0.25)

    def run_pending(self) -> None:
        """Run queued jobs and any due scheduled work. Called by the worker;
        tests call it directly with a fake clock."""
        while True:
            try:
                fn, args, fut = self._jobs.get_nowait()
            except queue.Empty:
                break
            try:
                fut.set_result(fn(*args))
            except Exception as exc:
                fut.set_exception(exc)
        if self.stream is None:
            return
        now = time.monotonic()
        if now >= self._next_tick:
            self._next_tick = now + 1.0
            self._guard(self.tick)
        if now >= self._next_build:
            self._next_build = now + self.rebuild
            self._guard(self.refresh_session)
        if self.rescan and now >= self._next_scan:
            self._next_scan = now + self.rescan
            self._guard(self.scan)

    def _guard(self, fn: Callable) -> None:
        try:
            fn()
        except Exception as exc:                       # never let the worker die
            self.log(f"  ibkr desk: {fn.__name__} failed: {exc!r}")
            self.log("  " + traceback.format_exc().strip().replace("\n", "\n  ")[-600:])

    def pump(self, seconds: float) -> None:
        ib = self.stream.ib if self.stream is not None else None
        if ib is not None and hasattr(ib, "sleep"):
            try:
                ib.sleep(seconds)
                return
            except Exception:
                pass
        time.sleep(seconds)

    # -- bootstrap ----------------------------------------------------------------

    def _bootstrap(self) -> dict:
        ib = self.ib_factory() if self.ib_factory else None
        self.stream = IbkrStream(self.host, self.port, self.client_id, ib=ib,
                                 on_update=self.publisher, clock=self.clock)
        h = self.stream.connect()
        if not h.connected:
            raise IbkrError(f"TWS not reachable at {self.host}:{self.port} (client {self.client_id}): "
                            f"{h.last_error}. Start TWS, enable the read-only API on port {self.port}, "
                            "and run: python3 scripts/ibkr_preflight.py")
        self.log(f"  IBKR desk connected read-only, client {self.client_id}, server version {h.server_version}")
        if not self.symbols and self.rescan:
            self._connect_scanner()
            self.log("  no symbols given: the scanner picks the desk (30-90 s the first time)")
            self.scan(add=False)
            self.symbols = [r["symbol"] for r in self._screener["rows"][:self.max_symbols]]
        if not self.symbols:
            raise IbkrError("no symbols on the desk and the scanner found nothing in the band; "
                            "start with names, e.g.  bash scripts/start.sh --ibkr CHPT,AEHL  "
                            "or widen DESK_PRICE_MIN in .env")
        self._subscribe(self.symbols)
        self.refresh_session()
        s = self.current()
        self.log(f"  desk ready: {', '.join(self.symbols)} — {len(s['frames'])} minutes of history, "
                 f"{sum(len(f['alerts']) for f in s['frames'])} alerts so far")
        return s

    def _connect_scanner(self) -> None:
        if self.scanner_ib is not None and self.scanner_ib.isConnected():
            return
        self.scanner_ib = self.ib_factory() if self.ib_factory else None
        if self.scanner_ib is None:
            from ib_async import IB
            self.scanner_ib = IB()
        self.scanner_ib.connect(self.host, self.port, clientId=self.scanner_client_id, readonly=True, timeout=12)
        try:
            self.scanner_ib.reqMarketDataType(1)
        except Exception:
            pass
        self.log(f"  IBKR scanner connected read-only, client {self.scanner_client_id}")

    def _subscribe(self, symbols: List[str]) -> List[str]:
        added = self.stream.subscribe(symbols, backfill_seconds=3600)
        for sym in added:
            self.log(f"  {sym}: subscribed (quote + 5-second bars); loading daily and minute history")
            c = self.stream._contract(sym)
            try:
                bars = daily_bars(self.stream.ib, c)
            except Exception as exc:
                self.log(f"  {sym}: daily history failed: {exc}")
                bars = []
            try:
                self._minutes[sym] = minute_records(self.stream.ib, c, sym)
            except Exception as exc:
                self.log(f"  {sym}: minute history failed: {exc}")
                self._minutes[sym] = []
            sec = sec_profile(sym) if self.sec else {}
            self._reference[sym] = reference_record(
                sym, bars, ticker=self.stream._tickers.get(sym),
                exchange=getattr(c, "primaryExchange", None) or "NASDAQ",
                name=getattr(c, "longName", None) or None, sec=sec, clock=self.clock)
        if added and self.headlines:
            recs, note = news_records(self.symbols)
            if recs:
                seen = {(r["symbol"], r["provider_id"]) for r in self._news}
                self._news += [r for r in recs if (r["symbol"], r["provider_id"]) not in seen]
            self._news_note = note
        return added

    # -- scheduled work -------------------------------------------------------------

    def tick(self) -> None:
        s = self.stream
        s.poll_tickers()
        self.publisher.publish_closed_10s(s.store, s.symbols)
        h = s.check()
        key = (h.state, h.generation, h.subscriptions, h.market_data_type)
        if key != self._last_state:
            self._last_state = key
            self.publisher.publish_health(self.health())
            self.log(f"  feed {h.state} (gen {h.generation}, {h.subscriptions} lines)")
        if h.state == "OFFLINE":
            s.reconnect()

    def refresh_session(self) -> dict:
        """Rebuild from memory: reference + minute history (for minutes the
        live store does not cover) + complete ten-second candles."""
        s = self.stream
        records: List[dict] = []
        for sym in self.symbols:
            ref = dict(self._reference.get(sym) or {"type": "reference", "symbol": sym})
            t = s._tickers.get(sym)
            if t is not None:
                last = getattr(t, "last", None)
                if last is not None and last == last:
                    ref["iex_last_price"] = float(last)
                    ref["iex_last_ts"] = self.clock().isoformat(timespec="seconds")
                    ref["iex_bid"] = _num(getattr(t, "bid", None))
                    ref["iex_ask"] = _num(getattr(t, "ask", None))
            records.append(ref)
            tens = store_records(s.store, sym)
            covered = {r["ts"][:17] + "00Z" for r in tens}
            records += [m for m in self._minutes.get(sym, []) if m["ts"][:17] + "00Z" not in covered]
            records += tens
        records += self._news
        h = s.health
        status = "live" if h.state == "LIVE" else h.state.lower()
        session = build_session_from_records(
            records, session_id="ibkr-" + "-".join(self.symbols[:3]),
            source_name="IBKR · TWS read-only · live", data_status=status,
            volume_floor_scale=1.0)
        session["live"] = True
        session["streaming"] = True
        session["refreshSeconds"] = self.rebuild
        session["builtAt"] = time.time()
        session["provider"] = self.health()
        session["symbolsOrder"] = list(self.symbols)
        if self._news_note:
            session["newsNote"] = self._news_note
        with self.lock:
            self.session = session
            self.built_at = session["builtAt"]
        # Tell every open page now: the scanners moved. A poll would find out
        # in up to five seconds; a trader watching Running Up should not wait.
        n_alerts = sum(len(f["alerts"]) for f in session["frames"])
        self.hub.publish("session", {"builtAt": session["builtAt"], "frames": len(session["frames"]),
                                     "alerts": n_alerts, "symbols": list(self.symbols)})
        return session

    def scan(self, add: bool = True) -> dict:
        self._connect_scanner()
        out = build_ibkr_screener(self.scanner_ib, self.min_price, self.max_price, self.min_gain,
                                  self.top, log=self.log, clock=self.clock)
        with self.lock:
            self._screener = out
        self.hub.publish("screener", out)
        self.log(f"  scanner: {len(out['rows'])} names up ≥{self.min_gain:g}% in the band"
                 + (": " + " ".join(r["symbol"] for r in out["rows"][:10]) if out["rows"] else ""))
        if add:
            fresh = [r["symbol"] for r in out["rows"] if r["symbol"] not in self.symbols]
            room = max(0, self.max_symbols - len(self.symbols))
            if fresh and room:
                self.add_symbols(fresh[:room])
        return out

    # -- surface used by the HTTP handler ------------------------------------------

    def current(self) -> dict:
        with self.lock:
            return self.session

    def screener_current(self) -> dict:
        with self.lock:
            return self._screener

    def health(self) -> dict:
        d = self.stream.health.as_dict() if self.stream is not None else {"state": "OFFLINE"}
        d["clientId"] = self.client_id
        d["scannerClientId"] = self.scanner_client_id
        d["builtAt"] = self.built_at
        return d

    def add_symbols(self, symbols) -> list:
        """From the worker: subscribe now. From another thread: enqueue."""
        wanted = []
        for sym in symbols:
            sym = str(sym).strip().upper()
            if sym and sym not in self.symbols and sym not in wanted and \
                    len(self.symbols) + len(wanted) < self.max_symbols:
                wanted.append(sym)
        if not wanted:
            return []
        on_worker = self._worker_thread is None or threading.current_thread() is self._worker_thread
        if on_worker:
            return self._add_now(wanted)
        self.submit(self._add_now, wanted)
        return wanted

    def _add_now(self, wanted: List[str]) -> List[str]:
        self.symbols += [s for s in wanted if s not in self.symbols]
        added = self._subscribe(wanted)
        for sym in added:
            self.hub.publish("symbol-added", {"symbol": sym})
        self.refresh_session()
        self.log(f"  {', '.join(added)} joined the desk" if added else "  nothing joined the desk")
        return added


def _num(v):
    try:
        f = float(v)
        return None if f != f else f
    except (TypeError, ValueError):
        return None
