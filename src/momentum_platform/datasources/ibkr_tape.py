"""Read-only IBKR tick-by-tick for the desk's Time & Sales (owner, 2026-10-08).

One focus symbol at a time — the name selected on the page — on the desk's
own read-only connection (client 27). Two streams:

- `Last`: the trades on the consolidated tape. `AllLast` would add combo,
  derivative and average-price prints, which are not market trades and would
  read as prints far from the quote.
- `BidAsk`: the quote each print is read against. If IBKR refuses it (an
  error on its request id — IBKR refuses through the error event, never by
  raising), the prints are read against the desk's Level 1 quote instead and
  the source line says so.

IBKR's tick-by-tick runs on the Level 1 entitlement the desk already uses and
allows five streams on the default 100 market-data lines; one request per
instrument every 15 seconds (IBKR's documentation as reported by a web search
on 2026-10-08 — its pages refuse automated reading; `docs/desk-assessment-2026-10-08.md`).
Two streams for one name stay inside that.

ib_async stamps a tick with its arrival time and clears `ticker.tickByTicks`
on every network batch, so the prints are read in the ticker's update event:
a poll would drop the ticks of every batch it missed.

ib_async keys a Ticker by the contract's conId, so these streams share the
desk's own Level 1 Ticker: `BidAsk` keeps the desk's bid/ask current, and
`Last` writes `ticker.last`. A print IBKR flags unreported is not a tape print
and must not become the desk's last price either — the batch handler puts the
last reported print back (review 2026-10-08).

An error is the tape's only when it is on one of the tape's own request ids,
or on the focus name's contract for a data-permission code. An error with no
contract — ib_async drops a request's contract once it is cancelled, which is
how the desk's own 10089/420 handler leaves a refused scanner name — is never
pinned on the focus name (review 2026-10-08).

There is no order, cancel-order or open-order call here. Every call is on the
desk's worker thread, which owns the asyncio loop.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from datetime import datetime, timezone
from typing import Callable, Optional

from ..tape import TapeBook, off_snapshot

UTC = timezone.utc

PACING_S = 15.0           # one tick-by-tick request per instrument per 15 s
HISTORY_TICKS = 300       # prints loaded behind the live stream on a new focus
HISTORY_TIMEOUT_S = 10.0
HISTORY_SYMBOL_EVERY_S = 60.0   # one history load per name per minute
HISTORY_BUDGET = 12             # history loads in any HISTORY_BUDGET_S, shared with the
HISTORY_BUDGET_S = 600.0        # desk's minute history (IBKR: ~60 per 10 min)

# TWS codes that stop a stream, in the owner's words.
REFUSED = {
    10089: "IBKR: this name needs a market-data subscription the account does not have",
    354: "IBKR: market data for this name is not subscribed",
    420: "IBKR: no live data permission for this exchange",
    10189: "IBKR refused the tick-by-tick request",
    10190: "IBKR: the tick-by-tick limit is reached (other tapes are open on this login)",
    10197: "another login on this IBKR username holds the market data (10197)",
}
# Codes about the NAME's data permission, whichever request carried them.
NAME_REFUSED = (10089, 354, 420)

SOURCE_FULL = "IBKR tick-by-tick · Last + BidAsk"
SOURCE_L1 = "IBKR tick-by-tick · Last; side vs the desk's Level 1 quote"


def _req_id(ib, ticker, tick_type: str) -> Optional[int]:
    """The request id ib_async gave this stream (wrapper.ticker2ReqId), or
    None when the IB object keeps no such map."""
    try:
        return ib.wrapper.ticker2ReqId[tick_type].get(ticker)
    except Exception:                                      # noqa: BLE001
        return None


class TapeFeed:
    """The focus symbol's tape, fed from IBKR. `stream` is the desk's
    IbkrStream (its `ib`, its contract cache, its health generation)."""

    def __init__(self, stream, clock: Callable[[], datetime] = lambda: datetime.now(UTC),
                 monotonic: Callable[[], float] = time.monotonic, history: bool = True) -> None:
        self.stream = stream
        self.clock = clock
        self.monotonic = monotonic
        self.history = history
        self.symbol: Optional[str] = None
        self.book: Optional[TapeBook] = None
        self._contract = None
        self._ticker = None
        self._streams: list = []
        self._req: dict = {}                              # tick type -> request id
        self._pending_at: Optional[float] = None          # monotonic time the focus may start
        self._resume = False                              # streams died (10197 / 1101): re-request on recovery
        self._requested_at: dict = {}                     # symbol -> monotonic of the last request
        self._history_at: dict = {}
        self._history_log: deque = deque()
        self._generation = getattr(getattr(stream, "health", None), "generation", 0)
        self._quote_l1 = False                            # True when BidAsk was refused

    # -- focus ------------------------------------------------------------------

    def focus(self, symbol: Optional[str]) -> dict:
        """Point the tape at `symbol` (worker thread). The same name again is a
        no-op only while its streams run or a start is scheduled — a tape in
        ERROR, or left without streams, is re-requested."""
        sym = (symbol or "").strip().upper() or None
        if sym is not None and sym == self.symbol and self.book is not None and \
                (self._streams or self._pending_at is not None) and self.book.state != "ERROR":
            return self.snapshot()
        self._cancel()
        self.symbol = sym
        self._resume = False
        if sym is None:
            self.book = None
            return self.snapshot()
        self.book = TapeBook(sym, source=SOURCE_FULL, clock=self.clock)
        refused = self._refused(sym)
        if refused:
            self.book.set_state("ERROR", refused)
            return self.snapshot()
        self._schedule()
        return self.snapshot()

    def _schedule(self) -> None:
        """Start now, or as soon as IBKR's per-name pacing allows."""
        wait = PACING_S - (self.monotonic() - self._requested_at.get(self.symbol, -1e9))
        if wait > 0:
            self._pending_at = self.monotonic() + wait
            self.book.set_state("STARTING", f"starting shortly — IBKR allows one tape request per name "
                                            f"every {PACING_S:.0f} s")
            return
        self._start()

    def _refused(self, sym: str) -> Optional[str]:
        banned = getattr(self.stream, "banned", None) or ()
        if sym in banned:
            return REFUSED[420]
        if sym not in (getattr(self.stream, "symbols", None) or [sym]):
            return f"{sym} is not on the desk — no stream to read"
        return None

    def _start(self) -> None:
        sym, book = self.symbol, self.book
        self._pending_at = None
        refused = self._refused(sym)                       # a reconnect must not bypass the refusal
        if refused:
            book.set_state("ERROR", refused)
            return
        c = self.stream._contract(sym)
        if c is None:
            book.set_state("ERROR", f"{sym} is unknown to IBKR (no security definition)")
            return
        ib = self.stream.ib
        self._requested_at[sym] = self.monotonic()
        try:
            t = ib.reqTickByTickData(c, "Last", 0, False)
        except Exception as exc:                          # noqa: BLE001 — the socket is down
            book.set_state("ERROR", f"IBKR refused the tape: {exc}")
            return
        self._contract, self._ticker, self._streams = c, t, ["Last"]
        self._req = {"Last": _req_id(ib, t, "Last")}
        self._quote_l1 = False
        book.source = SOURCE_FULL
        try:
            ib.reqTickByTickData(c, "BidAsk", 0, True)
            self._streams.append("BidAsk")
            self._req["BidAsk"] = _req_id(ib, t, "BidAsk")
        except Exception:                                  # noqa: BLE001
            self._fall_back_to_l1()
        try:
            t.updateEvent += self._on_ticker
        except Exception:                                  # noqa: BLE001
            pass
        self._generation = getattr(self.stream.health, "generation", 0)
        self._resume = False
        book.live_from(self.clock())
        book.set_state("STARTING", "waiting for the first print")
        self._load_history(sym, c)

    def _fall_back_to_l1(self) -> None:
        self._quote_l1 = True
        if "BidAsk" in self._streams:
            self._streams.remove("BidAsk")
        self._req.pop("BidAsk", None)
        if self.book is not None:
            self.book.source = SOURCE_L1
            self.book.note("BidAsk refused: each print's side is read against the Level 1 quote, "
                           "which IBKR samples — an Approximation")

    def _cancel(self) -> None:
        ib = self.stream.ib if self.stream is not None else None
        if self._ticker is not None:
            try:
                self._ticker.updateEvent -= self._on_ticker
            except Exception:                              # noqa: BLE001
                pass
        if ib is not None and self._contract is not None:
            for tt in self._streams:
                try:
                    ib.cancelTickByTickData(self._contract, tt)
                except Exception:                          # noqa: BLE001
                    pass
        self._contract, self._ticker, self._streams, self._req = None, None, [], {}
        self._pending_at = None

    def stop(self) -> None:
        self._cancel()
        self.symbol, self.book = None, None

    # -- events -----------------------------------------------------------------

    def _on_ticker(self, ticker) -> None:
        """One network batch: quotes and prints in the order they arrived."""
        if ticker is not self._ticker or self.book is None:
            return
        book = self.book
        reported, tail_unreported = None, False
        for tk in list(getattr(ticker, "tickByTicks", None) or []):
            if hasattr(tk, "bidPrice"):
                book.quote(tk.bidPrice, tk.askPrice, getattr(tk, "time", None))
            elif hasattr(tk, "price"):
                attrib = getattr(tk, "tickAttribLast", None)
                if attrib is not None and getattr(attrib, "unreported", False):
                    tail_unreported = True                 # not a tape print
                    continue
                tail_unreported = False
                reported = (tk.price, tk.size)
                if self._quote_l1:
                    book.quote(getattr(ticker, "bid", None), getattr(ticker, "ask", None))
                book.add_print(getattr(tk, "time", None) or self.clock(), tk.price, tk.size,
                               getattr(tk, "exchange", "") or "", getattr(tk, "specialConditions", "") or "")
        if tail_unreported:
            # ib_async already wrote the unreported print into the SHARED
            # ticker's last; the desk's quote poll must not read it
            prev = book.last_live()
            ref = reported or ((prev.price, prev.size) if prev is not None else None) or \
                (getattr(ticker, "prevLast", None), getattr(ticker, "prevLastSize", None))
            try:
                ticker.last, ticker.lastSize = ref
            except Exception:                              # noqa: BLE001
                pass

    def on_error(self, req_id, code, message, contract=None) -> None:
        """TWS errors that are this tape's, in words; a lost connection is a
        gap and the streams are re-requested when it comes back."""
        if self.book is None:
            return
        book = self.book
        if code == 1100:
            if book.state != "ERROR":
                book.set_state("PAUSED", "TWS lost its connection to IB (1100)")
            return
        if code == 1101:
            book.gap("TWS reconnected and IBKR says data was lost (1101) — prints in between are missing")
            if book.state != "ERROR":
                self._restart_later()
            return
        if code == 1102:
            if book.state == "PAUSED" or self._resume:
                self._restart_later()                      # the desk re-requests its own streams too
            return
        if code == 10197:
            if book.state != "ERROR":
                book.set_state("PAUSED", REFUSED[10197])
            book.gap("competing login (10197) — prints in between are missing")
            self._resume = True
            return
        if code not in REFUSED:
            return
        mine = {v: k for k, v in self._req.items() if v is not None}
        if req_id in mine:
            if mine[req_id] == "BidAsk":
                self._fall_back_to_l1()                    # the prints still flow; the side reads L1
            else:
                book.set_state("ERROR", f"{REFUSED[code]}: {message}".rstrip(": "))
            return
        sym = getattr(contract, "symbol", None)
        if sym is not None and sym == self.symbol and code in NAME_REFUSED:
            book.set_state("ERROR", f"{REFUSED[code]}: {message}".rstrip(": "))
        # anything else — another name's refusal, or an error whose contract
        # ib_async already dropped — is not this tape's

    def _restart_later(self) -> None:
        sym = self.symbol
        self._cancel()
        self.symbol = sym
        self._resume = True
        wait = max(0.0, PACING_S - (self.monotonic() - self._requested_at.get(sym, -1e9)))
        self._pending_at = self.monotonic() + wait

    # -- the worker's twice-a-second look --------------------------------------

    def check(self) -> None:
        """A focus waiting on pacing starts; a rebuilt connection resubscribes
        with a gap marker; a feed the desk calls STALE/OFFLINE pauses the tape
        and a recovered one re-requests what died; a silent tape says QUIET."""
        book = self.book
        if book is None:
            return
        health = getattr(self.stream, "health", None)
        gen = getattr(health, "generation", 0)
        if self._streams and gen != self._generation:
            book.gap("the IBKR connection was rebuilt — prints in between are missing")
            self._restart_later()
        state = getattr(health, "state", "LIVE")
        if self._pending_at is not None and self.monotonic() >= self._pending_at and state == "LIVE":
            self._start()
            return
        if state in ("OFFLINE", "STALE", "DELAYED") and book.state not in ("ERROR",):
            book.set_state("PAUSED", f"the desk's feed is {state} — the tape is paused")
            return
        if book.state == "PAUSED" and state == "LIVE":
            if self._resume and self._pending_at is None:
                self._restart_later()                      # 10197 cleared without a 1102: ask again
            elif self._streams:
                book.set_state("STARTING", "feed back — waiting for a print")
        book.check_quiet()

    # -- history ----------------------------------------------------------------

    def _load_history(self, sym: str, contract) -> None:
        """The last HISTORY_TICKS prints, so a fresh focus is not an empty tape.
        Asynchronous on the real IB (the worker never blocks on it); bounded by
        a per-name minute and a shared budget so history pacing is not spent."""
        if not self.history:
            return
        now = self.monotonic()
        if now - self._history_at.get(sym, -1e9) < HISTORY_SYMBOL_EVERY_S:
            return
        while self._history_log and now - self._history_log[0] > HISTORY_BUDGET_S:
            self._history_log.popleft()
        if len(self._history_log) >= HISTORY_BUDGET:
            self.book.note("history skipped: the desk's historical-request budget is spent for a few minutes")
            return
        self._history_at[sym] = now
        self._history_log.append(now)
        ib, book, end = self.stream.ib, self.book, self.clock()
        async_fn = getattr(ib, "reqHistoricalTicksAsync", None)
        if async_fn is not None:
            try:
                from ib_async import util                  # the loop ib.sleep() runs on this thread
                fut = util.getLoop().create_task(asyncio.wait_for(
                    async_fn(contract, "", end, HISTORY_TICKS, "TRADES", False), HISTORY_TIMEOUT_S))
            except Exception as exc:                       # noqa: BLE001 — no loop, no library
                book.note(f"history not loaded: {exc}")
                return
            fut.add_done_callback(lambda f: self._history_done(book, f))
            return
        try:
            rows = ib.reqHistoricalTicks(contract, "", end, HISTORY_TICKS, "TRADES", False)
        except Exception as exc:                          # noqa: BLE001
            book.note(f"history not loaded: {exc}")
            return
        self._add_history(book, rows)

    def _history_done(self, book: TapeBook, fut) -> None:
        if book is not self.book:
            return                                         # the focus moved on
        try:
            rows = fut.result()
        except Exception as exc:                          # noqa: BLE001 — timeout or refusal
            book.note(f"history not loaded: {type(exc).__name__}")
            return
        self._add_history(book, rows)

    @staticmethod
    def _add_history(book: TapeBook, rows) -> None:
        n = book.add_history((r.time, r.price, r.size, getattr(r, "exchange", ""),
                              getattr(r, "specialConditions", "")) for r in rows or [])
        if n:
            book.note(f"{n} earlier prints loaded from IBKR history — their side is not known")

    # -- readers ----------------------------------------------------------------

    def snapshot(self) -> dict:
        if self.book is None:
            return off_snapshot("select a name to start its tape")
        return self.book.snapshot()

    def status(self) -> dict:
        return {"symbol": self.symbol, "state": self.book.state if self.book else "OFF",
                "streams": list(self._streams), "quoteFromL1": self._quote_l1}

    @property
    def version(self) -> int:
        return self.book.version if self.book is not None else 0
