"""Level 2 — the selected name's order book, read, never invented (2026-10-09).

The desk's book (owner, 2026-10-09: "Level 2 as a default card, ready for the
subscription the owner is adding soon"). Provider-neutral like `tape.py`: the
IBKR adapter (`datasources/ibkr_depth.py`) feeds it the rows IBKR holds; the
page reads its snapshot. What it may say, and what it may not:

- A row is (price, size, venue) as the provider sent it. With IBKR SmartDepth
  the venue is the exchange the quote comes from; on a direct book it is the
  market maker's MPID (IBKR's TWS API market-depth page, read 2026-10-09).
- No subscription is a state, said with the provider's exact code and words
  (`NO_SUBSCRIPTION`), until data flows. A replay has no book and says so.
- Huge resting orders are this desk's APPROXIMATION, not a number from the
  corpus. What the corpus does count is the need: in tape reading, what
  requires depth of book is "large seller / buyer" (104 mentions, 31 videos)
  and "refresh / reload" (29) — `knowledge-base/strategies/PARAMETERS.md` §10.
  No threshold is stated there, so the line below is reasoned, labelled and
  configurable. Facts, never a gate: nothing here moves a verdict.

  A price level is HUGE when it sits within the first `HUGE_NEAR` price levels
  of its side and its resting size (all venues at that price) is at least
  `HUGE_MULT` × the median price-level size on the whole book (never under
  `HUGE_MIN` shares), or at least `HUGE_ABS` shares outright. It APPEARS when a
  level first crosses that line; it is GONE when that price no longer holds the
  line anywhere on the book. A gone level is TAKEN when the tape printed at
  least half its size at that price in the last `TAKEN_WINDOW_S` seconds, else
  PULLED — or UNKNOWN when there is no tape on the name to tell.
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone
from statistics import median
from typing import Callable, Deque, Dict, List, Optional, Sequence, Tuple

UTC = timezone.utc

STATES = ("OFF", "STARTING", "LIVE", "PAUSED", "NO_SUBSCRIPTION", "ERROR")
SHOW_ROWS = 10           # rows per side in a snapshot
HUGE_MULT = 10.0         # a resting size >= HUGE_MULT x the book's median price-level size ...
HUGE_MIN = 2000          # ... never under this many shares (Approximation)
HUGE_ABS = 25000         # or this many shares outright (Approximation)
HUGE_NEAR = 3            # within the first HUGE_NEAR price levels of its side
TAKEN_WINDOW_S = 10.0    # prints at that price this recent make a gone level TAKEN
TAKEN_SHARE = 0.5        # ... when they add up to this share of its size
EVENT_COOLDOWN_S = 30.0  # the same side and price says nothing new for this long
EVENTS_KEPT = 30

Row = Tuple[float, int, str]         # (price, size, venue)


def _utc(ts) -> datetime:
    if ts is None:
        return datetime.now(UTC)
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, UTC)
    return ts.replace(tzinfo=UTC) if ts.tzinfo is None else ts.astimezone(UTC)


def _rows(raw: Sequence) -> List[Row]:
    """Clean provider rows: positive price and size only, in the provider's order."""
    out: List[Row] = []
    for r in raw or ():
        try:
            price, size = float(r[0]), int(round(float(r[1])))
        except (TypeError, ValueError, IndexError):
            continue
        if price > 0 and size > 0 and price == price:
            out.append((price, size, str(r[2] if len(r) > 2 and r[2] is not None else "")))
    return out


def levels(rows: Sequence[Row], side: str) -> List[Tuple[float, int]]:
    """Rows aggregated by price, best first (bids high to low, asks low to high)."""
    agg: Dict[float, int] = {}
    for p, s, _ in rows:
        key = round(p, 4)
        agg[key] = agg.get(key, 0) + s
    return sorted(agg.items(), key=lambda kv: -kv[0] if side == "bid" else kv[0])


def huge_line(bid_levels, ask_levels) -> Optional[int]:
    """The resting size a near price level needs to count as huge on THIS book."""
    sizes = [s for _, s in bid_levels] + [s for _, s in ask_levels]
    if not sizes:
        return None
    return int(min(HUGE_ABS, max(HUGE_MIN, HUGE_MULT * median(sizes))))


class DepthBook:
    """The book of ONE symbol: rows per side, a state in words, huge-order
    events. Thread-safe: the IBKR worker writes, HTTP threads read snapshots.

    `printed(price, seconds)` — optional — returns the shares the tape printed
    at `price` in the last `seconds`; it decides TAKEN against PULLED."""

    def __init__(self, symbol: str, source: str = "", clock: Callable[[], datetime] = lambda: datetime.now(UTC),
                 printed: Optional[Callable[[float, float], Optional[int]]] = None) -> None:
        self.symbol = symbol.upper()
        self.source = source
        self.clock = clock
        self.printed = printed
        self._bids: List[Row] = []
        self._asks: List[Row] = []
        self._huge: Dict[Tuple[str, float], int] = {}       # (side, price) -> size when last seen huge
        self._events: Deque[dict] = deque(maxlen=EVENTS_KEPT)
        self._last_event: Dict[Tuple[str, float], datetime] = {}
        self._notes: List[str] = []
        self._seq = 0
        # event ids stay unique across books of one name (a re-focus makes a new book)
        self._born = int(_utc(clock()).timestamp() * 1000)
        self.updated_at: Optional[datetime] = None
        self.asked_again_at: Optional[datetime] = None     # a refused request, asked again
        self.state = "STARTING"
        self.message = "waiting for the book"
        self.code: Optional[int] = None
        self.version = 0
        self._lock = threading.RLock()

    # -- writers ---------------------------------------------------------------

    def set_state(self, state: str, message: str = "", code: Optional[int] = None) -> None:
        assert state in STATES, state
        with self._lock:
            if (state, message, code) != (self.state, self.message, self.code):
                self.state, self.message, self.code = state, message, code
                self.version += 1

    def asked_again(self, ts=None) -> None:
        with self._lock:
            self.asked_again_at = _utc(ts or self.clock())
            self.version += 1

    def note(self, text: str) -> None:
        with self._lock:
            if text not in self._notes:
                self._notes.append(text)
                self.version += 1

    def clear(self, why: str = "") -> None:
        """The book is emptied (IBKR reset, a halt, a reconnect): no level from
        before is carried into the next one, and no huge level is called gone
        because the book went blank."""
        with self._lock:
            self._bids, self._asks, self._huge = [], [], {}
            if why:
                self._events.append({"id": self._next_id(), "t": _utc(self.clock()).isoformat(), "kind": "gap",
                                     "why": why})
            self.version += 1

    def update(self, bids: Sequence, asks: Sequence, ts=None) -> bool:
        """The whole book as the provider now holds it. Returns True when it
        changed. Data flowing ends a NO_SUBSCRIPTION / STARTING state."""
        b, a = _rows(bids), _rows(asks)
        now = _utc(ts or self.clock())
        with self._lock:
            if b == self._bids and a == self._asks and self.state == "LIVE":
                return False
            self._bids, self._asks = b, a
            self.updated_at = now
            if (b or a) and self.state in ("STARTING", "NO_SUBSCRIPTION", "ERROR", "PAUSED"):
                self.state, self.message, self.code = "LIVE", "", None
            self._detect(now)
            self.version += 1
            return True

    def _next_id(self) -> str:
        self._seq += 1
        return f"{self._born}:{self._seq}"

    def _detect(self, now: datetime) -> None:
        bl, al = levels(self._bids, "bid"), levels(self._asks, "ask")
        line = huge_line(bl, al)
        if line is None:
            return
        here = {("bid", p): s for p, s in bl}
        here.update({("ask", p): s for p, s in al})
        near = {("bid", p): s for p, s in bl[:HUGE_NEAR] if s >= line}
        near.update({("ask", p): s for p, s in al[:HUGE_NEAR] if s >= line})
        for key, size in near.items():
            if key not in self._huge:
                self._emit("appeared", key, size, line, now)
            self._huge[key] = size
        for key in list(self._huge):
            if key in near:
                continue
            still = here.get(key)
            if still is not None and still >= line:
                continue                               # moved back from the inside, still resting
            size = self._huge.pop(key)
            self._emit("gone", key, size, line, now, left=still or 0)

    def _emit(self, kind: str, key: Tuple[str, float], size: int, line: int, now: datetime, left: int = 0) -> None:
        last = self._last_event.get(key)
        self._last_event[key] = now
        if last is not None and (now - last).total_seconds() < EVENT_COOLDOWN_S:
            return                                     # a level flapping at the line says nothing new
        side, price = key
        ev = {"id": self._next_id(), "t": now.isoformat(), "kind": kind, "side": side, "price": price,
              "size": size, "line": line}
        venues = sorted({v for p, s, v in (self._bids if side == "bid" else self._asks)
                         if round(p, 4) == price and v})
        if venues:
            ev["venues"] = venues
        if kind == "gone":
            ev["left"] = left
            got = None
            if self.printed is not None:
                try:
                    got = self.printed(price, TAKEN_WINDOW_S)
                except Exception:                         # noqa: BLE001 — a missing tape is not an error
                    got = None
            ev["printed"] = got
            ev["how"] = ("unknown" if got is None else
                         "taken" if got >= TAKEN_SHARE * (size - left) else "pulled")
        self._events.append(ev)

    # -- readers ---------------------------------------------------------------

    def snapshot(self, n: int = SHOW_ROWS, now: Optional[datetime] = None) -> dict:
        now = _utc(now or self.clock())
        with self._lock:
            bl, al = levels(self._bids, "bid"), levels(self._asks, "ask")
            line = huge_line(bl, al)
            hb = {p for p, s in bl[:HUGE_NEAR] if line is not None and s >= line}
            ha = {p for p, s in al[:HUGE_NEAR] if line is not None and s >= line}
            band = {("bid", p): i for i, (p, _) in enumerate(bl)}
            band.update({("ask", p): i for i, (p, _) in enumerate(al)})

            def row(side, r):
                p = round(r[0], 4)
                return {"p": r[0], "s": r[1], "x": r[2], "lvl": band.get((side, p)),
                        "huge": p in (hb if side == "bid" else ha)}

            bids = sorted(self._bids, key=lambda r: (-r[0], -r[1]))[:n]
            asks = sorted(self._asks, key=lambda r: (r[0], -r[1]))[:n]
            best_bid = bl[0][0] if bl else None
            best_ask = al[0][0] if al else None
            return {
                "symbol": self.symbol, "source": self.source, "state": self.state, "message": self.message,
                "code": self.code, "version": self.version, "asOf": now.isoformat(),
                "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
                "askedAgainAt": self.asked_again_at.isoformat() if self.asked_again_at else None,
                "bids": [row("bid", r) for r in bids], "asks": [row("ask", r) for r in asks],
                "inside": {"bid": best_bid, "ask": best_ask,
                           "spread": round(best_ask - best_bid, 4) if best_bid and best_ask else None},
                "totals": {"bid": sum(s for _, s, _ in self._bids), "ask": sum(s for _, s, _ in self._asks),
                           "bidLevels": len(bl), "askLevels": len(al)},
                "hugeLine": line,
                "events": list(self._events),
                "notes": list(self._notes),
                "rule": {"hugeMult": HUGE_MULT, "hugeMin": HUGE_MIN, "hugeAbs": HUGE_ABS, "near": HUGE_NEAR,
                         "takenWindowS": TAKEN_WINDOW_S, "label": "Approximation"},
            }


def off_depth(message: str, symbol: Optional[str] = None) -> dict:
    """What the page shows when there is no book at all — a replay, or a desk
    with no live feed. Said, never filled in."""
    return {"symbol": symbol, "source": "", "state": "OFF", "message": message, "code": None, "version": 0,
            "asOf": None, "updatedAt": None, "askedAgainAt": None, "bids": [], "asks": [],
            "inside": {"bid": None, "ask": None, "spread": None},
            "totals": {"bid": 0, "ask": 0, "bidLevels": 0, "askLevels": 0}, "hugeLine": None,
            "events": [], "notes": [],
            "rule": {"hugeMult": HUGE_MULT, "hugeMin": HUGE_MIN, "hugeAbs": HUGE_ABS, "near": HUGE_NEAR,
                     "takenWindowS": TAKEN_WINDOW_S, "label": "Approximation"}}
