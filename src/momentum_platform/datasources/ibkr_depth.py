"""Read-only IBKR market depth for the desk's Level 2 card (owner, 2026-10-09).

One focus symbol at a time — the name selected on the page, the same focus as
the Time & Sales — on the desk's own read-only connection (client 27):
`reqMktDepth(contract, numRows, isSmartDepth=True)`, released with
`cancelMktDepth` the moment the selection moves.

What IBKR's TWS API pages say, read 2026-10-09 (interactivebrokers.github.io,
"market depth" and "message codes"; the pages call themselves deprecated in
favour of IBKR Campus):

- SmartDepth gives "aggregated data from all available exchanges, similar to
  the TWS BookTrader display", and then "the marketMaker field will indicate
  the exchange from which the quote originates".
- Depth requests are limited by market-data lines, "with a minimum of three
  and maximum of 60"; this card holds one.
- No maximum row count is stated: "In case the market depth is smaller than
  the requested number of rows, the TWS will simply return the available
  entries." ib_async's docstring says 5 max. So DEPTH_ROWS are asked for, and
  an unexplained refusal is retried once at FALLBACK_ROWS.
- Codes: 309 "Max number (3) of market depth requests has been reached",
  316 "Market depth data has been HALTED. Please re-subscribe.", 317 "Market
  depth data has been RESET. Please empty deep book contents before applying
  any new entries.", 354 "Not subscribed to requested market data.", 10090
  "Part of requested market data is not subscribed.", 10186 "Requested market
  data is not subscribed. Delayed market data is not enabled".

Until the owner's depth subscription is on the account, IBKR refuses the
request: the card says NO_SUBSCRIPTION with IBKR's exact code and words, and
asks again every RETRY_S seconds, so the book appears by itself once data
flows. Reconnects are handled as the tape handles them.

ib_async keys a Ticker by the contract, so the depth lives on the desk's own
Level 1 Ticker (`domBids`, `domAsks`); its update event fires for quotes too,
and the book is re-read on each — the DepthBook ignores an unchanged book.

There is no order, cancel-order or open-order call here. Every call is on the
desk's worker thread, which owns the asyncio loop.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Callable, Optional

from ..depth import DepthBook, off_depth

UTC = timezone.utc

DEPTH_ROWS = 10           # rows per side asked for (see the module note)
FALLBACK_ROWS = 5         # ib_async's documented maximum, tried once after an unexplained refusal
RETRY_S = 120.0           # a refused request is asked again this often while the name stays selected

# IBKR codes on the depth request that mean "this account has no depth for it".
NO_SUBSCRIPTION = (354, 10089, 10090, 10186, 420)
SOURCE = "IBKR market depth · SmartDepth (all exchanges)"


def _req_id(ib, ticker) -> Optional[int]:
    try:
        return ib.wrapper.ticker2ReqId["mktDepth"].get(ticker)
    except Exception:                                      # noqa: BLE001
        return None


class DepthFeed:
    """The focus symbol's book, fed from IBKR. `stream` is the desk's
    IbkrStream (its `ib`, its contract cache, its health generation); `tape`
    returns the desk's TapeFeed, whose prints tell a pulled level from a taken
    one."""

    def __init__(self, stream, clock: Callable[[], datetime] = lambda: datetime.now(UTC),
                 monotonic: Callable[[], float] = time.monotonic,
                 tape: Optional[Callable[[], object]] = None) -> None:
        self.stream = stream
        self.clock = clock
        self.monotonic = monotonic
        self.tape = tape
        self.symbol: Optional[str] = None
        self.book: Optional[DepthBook] = None
        self.rows = DEPTH_ROWS
        self._contract = None
        self._ticker = None
        self._req: Optional[int] = None
        self._reqs: set = set()                            # every depth request id this feed made
        self._active = False                               # a request IBKR has not refused
        self._retry_at: Optional[float] = None
        self._resume = False
        self._generation = getattr(getattr(stream, "health", None), "generation", 0)

    # -- focus ------------------------------------------------------------------

    def focus(self, symbol: Optional[str]) -> dict:
        """Point the book at `symbol` (worker thread). The same name again is a
        no-op while its request runs; a refused one is asked again at once."""
        sym = (symbol or "").strip().upper() or None
        if sym is not None and sym == self.symbol and self.book is not None and self._active:
            return self.snapshot()
        self._cancel()
        self.symbol = sym
        self._resume = False
        self._retry_at = None
        if sym is None:
            self.book = None
            return self.snapshot()
        self.book = DepthBook(sym, source=SOURCE, clock=self.clock, printed=self._printed)
        self._start()
        return self.snapshot()

    def _printed(self, price: float, seconds: float) -> Optional[int]:
        feed = self.tape() if self.tape is not None else None
        book = getattr(feed, "book", None)
        if book is None or getattr(book, "symbol", None) != self.symbol or book.state in ("OFF", "ERROR"):
            return None                                    # no tape on this name: cannot tell
        return book.printed_at(price, seconds)

    def _refused(self, sym: str) -> Optional[str]:
        if sym in (getattr(self.stream, "banned", None) or ()):
            return "IBKR: no live data permission for this name's exchange (420) — no book either"
        if sym not in (getattr(self.stream, "symbols", None) or [sym]):
            return f"{sym} is not on the desk — no book to read"
        return None

    def _start(self) -> None:
        sym, book = self.symbol, self.book
        self._retry_at = None
        refused = self._refused(sym)
        if refused:
            book.set_state("ERROR", refused)
            return
        c = self.stream._contract(sym)
        if c is None:
            book.set_state("ERROR", f"{sym} is unknown to IBKR (no security definition)")
            return
        ib = self.stream.ib
        self._unhook()                                     # a retry must not hook the same ticker twice
        try:
            t = ib.reqMktDepth(c, numRows=self.rows, isSmartDepth=True)
        except Exception as exc:                           # noqa: BLE001 — the socket is down
            book.set_state("ERROR", f"IBKR refused the book: {exc}")
            self._retry_at = self.monotonic() + RETRY_S
            return
        self._contract, self._ticker, self._req, self._active = c, t, _req_id(ib, t), True
        if self._req is not None:
            self._reqs.add(self._req)
        try:
            t.updateEvent += self._on_ticker
        except Exception:                                  # noqa: BLE001
            pass
        self._generation = getattr(self.stream.health, "generation", 0)
        self._resume = False
        if book.state == "NO_SUBSCRIPTION":
            # IBKR's last answer stays on screen while it is asked again: the
            # card does not flicker to "starting" every RETRY_S
            book.asked_again(self.clock())
        elif book.state != "LIVE":
            book.set_state("STARTING", "waiting for the book")
        self._on_ticker(t)                                 # a book already held on this ticker

    def _unhook(self) -> None:
        if self._ticker is not None:
            try:
                self._ticker.updateEvent -= self._on_ticker
            except Exception:                              # noqa: BLE001
                pass

    def _cancel(self) -> None:
        """Release the depth line: one book on the account at a time."""
        ib = self.stream.ib if self.stream is not None else None
        self._unhook()
        if ib is not None and self._contract is not None and self._active:
            try:
                ib.cancelMktDepth(self._contract, isSmartDepth=True)
            except Exception:                              # noqa: BLE001
                pass
        self._contract, self._ticker, self._req, self._active = None, None, None, False

    def stop(self) -> None:
        self._cancel()
        self.symbol, self.book = None, None

    # -- events -----------------------------------------------------------------

    def _on_ticker(self, ticker) -> None:
        if ticker is not self._ticker or self.book is None or not self._active:
            return
        bids = [(lv.price, lv.size, getattr(lv, "marketMaker", "")) for lv in (getattr(ticker, "domBids", None) or [])]
        asks = [(lv.price, lv.size, getattr(lv, "marketMaker", "")) for lv in (getattr(ticker, "domAsks", None) or [])]
        if bids or asks or self.book.state == "LIVE":
            self.book.update(bids, asks)

    def owns(self, req_id) -> bool:
        """True when `req_id` is one of this feed's depth requests, current or
        released: its errors are the book's and no one else's."""
        return req_id is not None and req_id in self._reqs

    def on_error(self, req_id, code, message, contract=None) -> None:
        """TWS errors that are this book's, in words; a lost connection empties
        the book and the request is made again when it comes back."""
        if self.book is None:
            return
        book = self.book
        if code == 1100:
            if book.state not in ("ERROR", "NO_SUBSCRIPTION"):
                book.set_state("PAUSED", "TWS lost its connection to IB (1100)")
            return
        if code == 1101:
            book.clear("TWS reconnected and IBKR says data was lost (1101)")
            if book.state not in ("ERROR", "NO_SUBSCRIPTION"):
                self._restart_later()
            return
        if code == 1102:
            if book.state == "PAUSED" or self._resume:
                self._restart_later()
            return
        if code == 10197:
            if book.state not in ("ERROR", "NO_SUBSCRIPTION"):
                book.set_state("PAUSED", "another login on this IBKR username holds the market data (10197)")
            book.clear("competing login (10197)")
            self._resume = True
            return
        if req_id is None or req_id != self._req:
            return                                         # another request's error is not this book's
        words = f"IBKR {code}: {message}".rstrip(": ").strip()
        if code in NO_SUBSCRIPTION:
            self._active = False
            book.clear()
            book.set_state("NO_SUBSCRIPTION", words, code)
            self._retry_at = self.monotonic() + RETRY_S
        elif code == 316:                                  # HALTED: "Please re-subscribe."
            book.clear(words)
            self._restart_later()
        elif code == 317:                                  # RESET: "Please empty deep book contents"
            t = self._ticker
            for name in ("domBids", "domAsks", "domBidsDict", "domAsksDict"):
                try:
                    getattr(t, name).clear()
                except Exception:                          # noqa: BLE001
                    pass
            book.clear(words)
        elif 2100 <= int(code) < 2200:
            book.note(words)                               # IBKR's warnings: said, never a state
        else:
            self._active = False
            book.set_state("ERROR", words, code)
            if self.rows > FALLBACK_ROWS:
                self.rows = FALLBACK_ROWS                  # one retry at ib_async's documented maximum
                book.note(f"retrying with {FALLBACK_ROWS} rows a side after {words}")
                self._retry_at = self.monotonic()
            else:
                self._retry_at = self.monotonic() + RETRY_S

    def _restart_later(self) -> None:
        sym = self.symbol
        self._cancel()
        self.symbol = sym
        self._resume = True
        self._retry_at = self.monotonic()

    # -- the worker's twice-a-second look --------------------------------------

    def check(self) -> None:
        """A retry that is due runs; a rebuilt connection resubscribes; a feed
        the desk calls STALE/OFFLINE pauses the book and a recovered one asks
        again."""
        book = self.book
        if book is None:
            return
        health = getattr(self.stream, "health", None)
        gen = getattr(health, "generation", 0)
        if self._active and gen != self._generation:
            book.clear("the IBKR connection was rebuilt")
            self._restart_later()
        state = getattr(health, "state", "LIVE")
        if self._retry_at is not None and self.monotonic() >= self._retry_at and state == "LIVE":
            self._start()
            return
        if state in ("OFFLINE", "STALE", "DELAYED") and book.state not in ("ERROR", "NO_SUBSCRIPTION"):
            book.set_state("PAUSED", f"the desk's feed is {state} — the book is paused")
            self._resume = True
            return
        if book.state == "PAUSED" and state == "LIVE" and self._resume and self._retry_at is None:
            self._restart_later()

    # -- readers ----------------------------------------------------------------

    def snapshot(self) -> dict:
        if self.book is None:
            return off_depth("select a name to read its book")
        out = self.book.snapshot()
        if self._retry_at is not None and self.book.state in ("NO_SUBSCRIPTION", "ERROR"):
            out["retryInS"] = max(0, round(self._retry_at - self.monotonic()))
        out["rows"] = self.rows
        return out

    def status(self) -> dict:
        return {"symbol": self.symbol, "state": self.book.state if self.book else "OFF",
                "code": self.book.code if self.book else None, "rows": self.rows, "active": self._active}

    @property
    def version(self) -> int:
        return self.book.version if self.book is not None else 0
