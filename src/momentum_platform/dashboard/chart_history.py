"""Older candles for the desk's charts, from IBKR: the sessions before today
in one-minute bars, and daily bars older than the year the desk loads.

Charts only. The gates, the plans and the cards are built from today's bars
(`IbkrDesk._minutes`, from 04:00 ET); nothing here writes there, so scrolling
back through last week cannot move a verdict (owner, 2026-10-13: "the graphs
dont keep ols candles; is it possible to load the full histroy from ibkr ?").

Its own read-only client (30 unless IBKR_HISTORY_CLIENT_ID says otherwise) on
its own thread. A slow history farm, or IBKR throttling heavy history
requests, must never hold up the worker that publishes decisions — the
scanner's lesson of 2026-09-21, when scans on the worker delayed every plan
of the morning.

IBKR's rules, read 2026-10-13 from
https://interactivebrokers.github.io/tws-api/historical_limitations.html :
the hard pacing limits (no identical request within 15 s, no six for one
contract within 2 s, no more than 60 in ten minutes) are stated for bars of
30 seconds or less; for "1 mins" and greater the limitations "have been
lifted", with a "soft" slow and the warning that "requesting too much
historical data can lead to throttling and eventual disconnect of the API
client"; requests should return "only a few thousand bars at a time"; its
table pairs a "1 D" duration with one-minute bars. So: one session per
request ("1 D" ending 20:00 ET, extended hours, at most 960 bars), one
request at a time, at least PACE_S apart, at most BUDGET in any ten minutes —
with the desk's own refresh (one request every 20 s on client 27) the two stay
inside 60 in ten minutes, the strictest reading — and every completed session
cached on disk, because a past day does not change. Except through a split:
a cached session whose close disagrees with the desk's fresh daily bar by
more than SPLIT_TOL is fetched again, once a run.

Nothing here transmits anything. Every call is a request for data.
"""

from __future__ import annotations

import json
import os
import queue
import threading
import time
from collections import deque
from concurrent.futures import Future, TimeoutError as FutureTimeout
from datetime import date, datetime, time as dtime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

from ..holidays import why_closed

UTC = timezone.utc
ET = ZoneInfo("America/New_York")

CLIENT_ID = int(os.environ.get("IBKR_HISTORY_CLIENT_ID", "30"))
PACE_S = 2.0              # at least this long between two requests on this client
BUDGET = 30               # requests in any WINDOW_S
WINDOW_S = 600.0
TIMEOUT_S = 20.0          # as the desk's HISTORY_TIMEOUT
MAX_SESSIONS = 5          # sessions one page request may ask for
EMPTY_RUN = 10            # asked weekdays in a row with no bars: nothing older (before the listing)
LOOKBACK_DAYS = 3 * 366   # how far back the walk goes at all
SPLIT_TOL = 0.2           # cached regular close vs the fresh daily close, relative
DAILY_YEARS = 5
SOURCE = "IBKR 1 min TRADES, 04:00-20:00 ET (extended hours)"


class HistoryError(RuntimeError):
    pass


class BudgetSpent(HistoryError):
    def __init__(self, wait_s: float):
        super().__init__(f"history budget spent; the next request in {wait_s:.0f} s")
        self.wait_s = wait_s


def default_cache_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "cache" / "ibkr_chart_minutes"


def _num(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def _day(text) -> Optional[date]:
    if isinstance(text, date):
        return text
    try:
        return date.fromisoformat(str(text)[:10]) if text else None
    except ValueError:
        return None


def _stamp(b) -> datetime:
    ts = b.date if isinstance(b.date, datetime) else datetime.fromisoformat(str(b.date))
    return ts if ts.tzinfo is not None else ts.replace(tzinfo=UTC)


class ChartHistory:
    """Previous sessions' one-minute bars and older daily bars, on request.

    `contract_for(symbol)` hands over the desk's qualified contract (a dict
    read, no request); `daily_closes(symbol)` the desk's daily closes by ISO
    day, which say which days the name traded and catch a split; `today()`
    the desk's session day. Without a running thread (tests, a desk that was
    never started) every call runs inline in the caller's thread."""

    def __init__(self, host: str = "127.0.0.1", port: int = 7496, client_id: int = CLIENT_ID,
                 ib_factory: Optional[Callable[[], object]] = None,
                 contract_for: Optional[Callable[[str], object]] = None,
                 daily_closes: Optional[Callable[[str], Dict[str, float]]] = None,
                 today: Optional[Callable[[], date]] = None,
                 cache_dir: Optional[Path] = None,
                 log: Optional[Callable[[str], None]] = None,
                 pace_s: float = PACE_S, budget: int = BUDGET, window_s: float = WINDOW_S,
                 timeout_s: float = TIMEOUT_S,
                 monotonic: Callable[[], float] = time.monotonic) -> None:
        self.host, self.port, self.client_id = host, port, client_id
        self.ib_factory = ib_factory
        self.contract_for = contract_for
        self.daily_closes = daily_closes
        self.today = today or (lambda: datetime.now(ET).date())
        self.cache_dir = Path(cache_dir) if cache_dir is not None else default_cache_dir()
        self.log = log or (lambda m: None)
        self.pace_s, self.budget, self.window_s, self.timeout_s = pace_s, budget, window_s, timeout_s
        self.monotonic = monotonic
        self.ib = None
        self._jobs: "queue.Queue[tuple]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._asked: deque = deque()           # monotonic times of the requests in the window
        self._last = -1e9
        self._daily_cache: Dict[tuple, List[dict]] = {}
        self._checked: set = set()             # (symbol, day) compared with the daily close this run
        self.requests = 0
        self.last_error: Optional[str] = None

    # -- thread ------------------------------------------------------------------

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="ibkr-chart-history")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        try:
            import asyncio
            asyncio.set_event_loop(asyncio.new_event_loop())
        except Exception:
            pass
        while not self._stop.is_set():
            try:
                fn, args, fut = self._jobs.get(timeout=0.5)
            except queue.Empty:
                self._pump(0)
                continue
            if fut.set_running_or_notify_cancel():
                try:
                    fut.set_result(fn(*args))
                except BaseException as exc:          # noqa: BLE001 — the caller reads it
                    fut.set_exception(exc)
        ib, self.ib = self.ib, None
        if ib is not None and self.ib_factory is None:
            try:
                ib.disconnect()
            except Exception:
                pass

    def submit(self, fn: Callable, *args) -> Future:
        fut: Future = Future()
        if self.running:
            self._jobs.put((fn, args, fut))
            return fut
        try:
            fut.set_result(fn(*args))
        except BaseException as exc:                  # noqa: BLE001
            fut.set_exception(exc)
        return fut

    def _pump(self, seconds: float) -> None:
        ib = self.ib
        if ib is not None and hasattr(ib, "sleep"):
            try:
                ib.sleep(seconds)
                return
            except Exception:
                pass
        if seconds > 0:
            time.sleep(seconds)

    # -- what the page asks for ----------------------------------------------------

    def minutes(self, symbol: str, before=None, sessions: int = 1, wait: float = 30.0) -> dict:
        """Up to `sessions` trading sessions before `before` (default: the
        desk's session day), oldest first, each as [t, o, h, l, c, v] rows like
        the session's own bars. `next_before` is where the next call starts."""
        symbol = symbol.upper()
        n = max(1, min(MAX_SESSIONS, int(sessions or 1)))
        start = _day(before) or self.today()
        fut = self.submit(self._minutes_job, symbol, start, n)
        try:
            return fut.result(timeout=wait)
        except FutureTimeout:
            note = "IBKR is still sending the older candles — they come with the next scroll"
            pending = True
        except Exception as exc:                      # noqa: BLE001 — said, never raised to the page
            note, pending = f"older candles unavailable: {exc}", False
        return {"symbol": symbol, "tf": "1m", "before": start.isoformat(), "next_before": start.isoformat(),
                "sessions": [], "more": True, "pending": pending, "note": note, "source": SOURCE}

    def prefetch(self, symbol: str, sessions: int = 1) -> None:
        """Warm the cache for a name that just joined the desk, so its previous
        session is there when it is first clicked. Never waits; only with the
        thread running, so it never runs on the desk's worker."""
        if self.running:
            self.submit(self._minutes_job, symbol.upper(), self.today(), max(1, int(sessions)))

    def daily(self, symbol: str, before=None, years: int = DAILY_YEARS, wait: float = 30.0) -> dict:
        """Daily bars before `before` (the oldest bar the page holds), `years` deep."""
        symbol = symbol.upper()
        start = _day(before) or self.today()
        fut = self.submit(self._daily_job, symbol, start, max(1, min(20, int(years or DAILY_YEARS))))
        try:
            return fut.result(timeout=wait)
        except FutureTimeout:
            note, pending = "IBKR is still sending the older daily bars", True
        except Exception as exc:                      # noqa: BLE001
            note, pending = f"older daily bars unavailable: {exc}", False
        return {"symbol": symbol, "tf": "D", "before": start.isoformat(), "next_before": start.isoformat(),
                "bars": [], "more": True, "pending": pending, "note": note}

    def status(self) -> dict:
        return {"clientId": self.client_id, "running": self.running, "requests": self.requests,
                "budget": self.budget, "windowSeconds": self.window_s, "lastError": self.last_error}

    # -- jobs (the history thread, or inline) ----------------------------------------

    def _minutes_job(self, symbol: str, before: date, n: int) -> dict:
        known = self._known(symbol)
        first_known = min(known) if known else None
        # The desk loads a year of daily bars. When they start later than that,
        # the name was listed then: nothing older exists to ask for.
        listed_from = (first_known if first_known is not None
                       and date.fromisoformat(first_known) > self.today() - timedelta(days=360) else None)
        out: List[dict] = []
        note = None
        ended = False
        examined = before
        day = before - timedelta(days=1)
        floor = before - timedelta(days=LOOKBACK_DAYS)
        empties = 0
        while len(out) < n and empties < EMPTY_RUN and day >= floor:
            iso = day.isoformat()
            if listed_from is not None and iso < listed_from:
                ended = True
                break
            if why_closed(day):
                day -= timedelta(days=1)
                continue
            if first_known is not None and iso >= first_known and iso not in known:
                examined = day                        # inside the daily bars' range, not in them:
                day -= timedelta(days=1)              # no session for this name that day
                continue
            try:
                bars = self._session(symbol, day, known.get(iso))
            except BudgetSpent as exc:
                note = (f"IBKR history: {self.budget} requests in ten minutes reached on client "
                        f"{self.client_id} — older candles in {exc.wait_s:.0f} s")
                break
            except Exception as exc:                  # noqa: BLE001
                self.last_error = str(exc)
                note = f"older candles unavailable: {exc}"
                break
            examined = day
            if bars:
                out.append({"day": iso, "bars": bars})
                empties = 0
            else:
                empties += 1
            day -= timedelta(days=1)
        out.reverse()
        more = note is not None or (not ended and empties < EMPTY_RUN and day >= floor)
        return {"symbol": symbol, "tf": "1m", "before": before.isoformat(), "next_before": examined.isoformat(),
                "sessions": out, "more": more, "pending": False, "note": note, "source": SOURCE}

    def _daily_job(self, symbol: str, before: date, years: int) -> dict:
        key = (symbol, before.isoformat(), years)
        rows = self._daily_cache.get(key)
        if rows is None:
            ib = self._ensure_ib()
            contract = self._contract(symbol, ib)
            self._wait_turn()
            end = datetime.combine(before, dtime(0, 0), tzinfo=ET)
            hist = ib.reqHistoricalData(contract, end, f"{years} Y", "1 day", "TRADES", True, formatDate=2,
                                        timeout=self.timeout_s)
            rows = []
            for b in hist or []:
                d = b.date.isoformat()[:10] if isinstance(b.date, (date, datetime)) else str(b.date)[:10]
                c = _num(b.close)
                if d >= before.isoformat() or not c:
                    continue
                rows.append({"d": d, "o": _num(b.open), "h": _num(b.high), "l": _num(b.low), "c": c,
                             "v": int(_num(b.volume) or 0)})
            rows.sort(key=lambda r: r["d"])
            self._daily_cache[key] = rows
        # A name listed for less than the span asked comes back short: nothing older.
        more = len(rows) >= int(0.8 * 252 * years)
        return {"symbol": symbol, "tf": "D", "before": before.isoformat(),
                "next_before": rows[0]["d"] if rows else before.isoformat(),
                "bars": rows, "more": more, "pending": False, "note": None,
                "source": "IBKR 1 day TRADES, regular hours"}

    # -- one session -----------------------------------------------------------------

    def _known(self, symbol: str) -> Dict[str, float]:
        try:
            return dict(self.daily_closes(symbol) or {}) if self.daily_closes else {}
        except Exception:
            return {}

    def _path(self, symbol: str, day: date) -> Path:
        return self.cache_dir / symbol / f"{day.isoformat()}.json"

    def _session(self, symbol: str, day: date, daily_close: Optional[float]) -> List[list]:
        path = self._path(symbol, day)
        cached = self._read(path)
        if cached is not None and not self._suspect(symbol, day, cached, daily_close):
            return cached
        bars = self._fetch(symbol, day)
        self._checked.add((symbol, day))
        if day < self.today():                        # a completed session: it will not change
            self._write(path, symbol, day, bars)
        return bars

    def _suspect(self, symbol: str, day: date, bars: List[list], daily_close: Optional[float]) -> bool:
        """A cached session that disagrees with the fresh daily bar: a split
        since it was cached (prices rescaled), or a quiet answer cached on a day
        the name did trade. Asked again once a run, never in a loop."""
        if (symbol, day) in self._checked or daily_close is None or daily_close <= 0:
            return False
        self._checked.add((symbol, day))
        if not bars:
            return True
        close_at = datetime.combine(day, dtime(16, 0), tzinfo=ET).timestamp()
        regular = [b for b in bars if b[0] < close_at]
        last = (regular or bars)[-1][4]
        return abs(last / daily_close - 1.0) > SPLIT_TOL

    def _read(self, path: Path) -> Optional[List[list]]:
        try:
            doc = json.loads(path.read_text())
        except (OSError, ValueError):
            return None
        bars = doc.get("bars") if isinstance(doc, dict) else None
        return bars if isinstance(bars, list) else None

    def _write(self, path: Path, symbol: str, day: date, bars: List[list]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"v": 1, "symbol": symbol, "day": day.isoformat(), "source": SOURCE,
                                       "fetched": datetime.now(UTC).isoformat(timespec="seconds"),
                                       "bars": bars}, separators=(",", ":")))
            os.replace(tmp, path)
        except OSError as exc:
            self.log(f"  chart history: cache not written for {symbol} {day}: {exc}")

    def _fetch(self, symbol: str, day: date) -> List[list]:
        ib = self._ensure_ib()
        contract = self._contract(symbol, ib)
        self._wait_turn()
        lo = datetime.combine(day, dtime(4, 0), tzinfo=ET)
        hi = datetime.combine(day, dtime(20, 0), tzinfo=ET)
        t0 = self.monotonic()
        hist = ib.reqHistoricalData(contract, hi, "1 D", "1 min", "TRADES", False, formatDate=2,
                                    timeout=self.timeout_s)
        took = self.monotonic() - t0
        bars = []
        for b in hist or []:
            ts = _stamp(b)
            c = _num(b.close)
            if not (lo <= ts < hi) or not c or c <= 0:
                continue
            bars.append([int(ts.timestamp()), _num(b.open), _num(b.high), _num(b.low), c,
                         int(_num(b.volume) or 0)])
        if not bars and took >= self.timeout_s * 0.9:
            # ib_async answers a timeout with an empty list, like "no data":
            # a timeout is not cached as an empty day.
            raise HistoryError(f"IBKR did not answer for {symbol} {day} within {self.timeout_s:.0f} s")
        bars.sort(key=lambda r: r[0])
        return bars

    def _wait_turn(self) -> None:
        now = self.monotonic()
        while self._asked and now - self._asked[0] >= self.window_s:
            self._asked.popleft()
        if len(self._asked) >= self.budget:
            raise BudgetSpent(self.window_s - (now - self._asked[0]))
        gap = self._last + self.pace_s - now
        if gap > 0:
            self._pump(gap)
        self._last = self.monotonic()
        self._asked.append(self._last)
        self.requests += 1

    def _ensure_ib(self):
        ib = self.ib
        if ib is not None:
            try:
                if ib.isConnected():
                    return ib
            except Exception:
                pass
        ib = self.ib_factory() if self.ib_factory else None
        if ib is None:
            from ib_async import IB
            ib = IB()
        try:
            if not ib.isConnected():
                from ..datasources.ibkr_stream import read_only_connect
                read_only_connect(ib, self.host, self.port, self.client_id, 12)
                self.log(f"  IBKR chart history connected read-only, client {self.client_id}")
        except Exception as exc:
            raise HistoryError(f"TWS did not take the history client {self.client_id}: {exc}") from exc
        self.ib = ib
        return ib

    def _contract(self, symbol: str, ib):
        c = None
        if self.contract_for is not None:
            try:
                c = self.contract_for(symbol)
            except Exception:
                c = None
        if c is not None:
            return c
        try:
            from ib_async import Stock
        except ImportError:
            raise HistoryError(f"{symbol} is not on the desk")
        c = Stock(symbol, "SMART", "USD")
        try:
            got = ib.qualifyContracts(c)
        except Exception as exc:
            raise HistoryError(f"{symbol}: no contract ({exc})") from exc
        if not got or got[0] is None:
            raise HistoryError(f"{symbol}: unknown to IBKR")
        return got[0]
