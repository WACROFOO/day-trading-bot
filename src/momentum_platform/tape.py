"""Time & Sales — the prints of the selected name, read, never invented.

The desk's tape (owner, 2026-10-08). Provider-neutral: the IBKR adapter
(`datasources/ibkr_tape.py`) feeds it prints and quotes; the page reads its
snapshot. What it may say, and what it may not:

- A print's side is a fact only against the quote that stood when it printed:
  at or above the ask, a buyer lifted the offer (the "green on the tape" he
  reads at the trigger); at or below the bid, a seller hit the bid; between,
  mid. With no quote, and for history loaded before the live stream started,
  the side is "?" — never guessed from the price path.
- Facts, not scores: shares and the share of volume at the ask over the last
  60 and 10 seconds, prints per minute, big prints, the age of the last print.
  None of it is a gate and none of it moves a verdict: nothing in this
  repository has measured what a tape figure is worth
  (`docs/desk-assessment-2026-10-08.md`, "Level 2").
- A gap is said, never smoothed: a reconnect, a resubscribe or a refusal puts
  a marker in the tape, and the windowed facts restart after it.

The "big print" line is this desk's Approximation (BIG_MULT × the median print
of the tape, never under BIG_FLOOR shares), not a number from the corpus.
"""

from __future__ import annotations

import threading
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median
from typing import Callable, Deque, Iterable, List, Optional

UTC = timezone.utc

WINDOW_S = 60.0          # the facts window
NOW_S = 10.0             # the "right now" window
QUIET_S = 30.0           # no live print for this long: QUIET, said in words
BIG_MULT = 10.0          # a big print: ≥ BIG_MULT × the median print size …
BIG_FLOOR = 2000         # … and never under this many shares (Approximation)
BIG_SAMPLE = 300         # prints the median is taken over
KEEP = 600               # prints kept per tape
SHOW = 80                # prints shipped in a snapshot, newest first
GAPS_KEPT = 20           # gap markers kept (and shipped) per tape

STATES = ("OFF", "STARTING", "LIVE", "QUIET", "PAUSED", "ERROR")


@dataclass(frozen=True)
class Print:
    ts: datetime          # receive time (live) or exchange time (history), UTC
    price: float
    size: int
    side: str             # "ask" | "bid" | "mid" | "?"
    src: str = "live"     # "live" | "hist"
    exch: str = ""
    cond: str = ""
    seq: int = 0          # arrival order of live prints; a gap cuts the facts by it

    def key(self) -> tuple:
        return (int(self.ts.timestamp()), self.price, self.size)


def side_of(price: float, bid: Optional[float], ask: Optional[float]) -> str:
    """The aggressor side against the quote that stood: a fact only with a
    real two-sided quote; anything else is "?". A LOCKED quote (bid = ask)
    names no side either: every print would read "ask" (review 2026-10-08)."""
    if bid is None or ask is None or bid <= 0 or ask <= 0 or bid >= ask:
        return "?"
    if price >= ask:
        return "ask"
    if price <= bid:
        return "bid"
    return "mid"


def _utc(ts) -> datetime:
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, UTC)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


class TapeBook:
    """The tape of ONE symbol: prints newest last, the standing quote, gap
    markers, a state in words. Thread-safe: the IBKR worker writes, HTTP
    threads read snapshots."""

    def __init__(self, symbol: str, source: str = "", clock: Callable[[], datetime] = lambda: datetime.now(UTC),
                 keep: int = KEEP) -> None:
        self.symbol = symbol.upper()
        self.source = source
        self.clock = clock
        self._prints: Deque[Print] = deque(maxlen=keep)
        self._gaps: Deque[dict] = deque(maxlen=GAPS_KEPT)
        self._notes: List[str] = []
        self._bid: Optional[float] = None
        self._ask: Optional[float] = None
        self._quote_at: Optional[datetime] = None
        self._live_since: Optional[datetime] = None
        self._facts_since: Optional[datetime] = None      # when the windowed facts (re)started
        self._facts_after = 0                              # … counting live prints after this seq
        self._seq = 0
        self.state = "STARTING"
        self.message = "waiting for the first print"
        self.version = 0                                   # bumps on every change; the publisher diffs on it
        self._lock = threading.RLock()

    # -- writers ---------------------------------------------------------------

    def set_state(self, state: str, message: str = "") -> None:
        assert state in STATES, state
        with self._lock:
            if (state, message) != (self.state, self.message):
                self.state, self.message = state, message
                self.version += 1

    def note(self, text: str) -> None:
        with self._lock:
            if text not in self._notes:
                self._notes.append(text)
                self.version += 1

    def live_from(self, ts: Optional[datetime] = None) -> None:
        """The live stream starts (or restarts) here: the facts count from it."""
        with self._lock:
            ts = _utc(ts or self.clock())
            if self._live_since is None:
                self._live_since = ts
            self._facts_since = ts
            self._facts_after = self._seq
            self._bid = self._ask = self._quote_at = None      # a (re)started stream reads its own quote
            self.version += 1

    def quote(self, bid: Optional[float], ask: Optional[float], ts=None) -> None:
        with self._lock:
            self._bid = _pos(bid)
            self._ask = _pos(ask)
            self._quote_at = _utc(ts or self.clock())

    def add_print(self, ts, price: float, size, exch: str = "", cond: str = "",
                  bid: Optional[float] = None, ask: Optional[float] = None) -> Optional[Print]:
        """A live print, read against the standing quote (or the one passed)."""
        try:
            price, size = float(price), int(round(float(size)))
        except (TypeError, ValueError):
            return None
        if price <= 0 or size <= 0:
            return None
        with self._lock:
            b = _pos(bid) if bid is not None else self._bid
            a = _pos(ask) if ask is not None else self._ask
            self._seq += 1
            p = Print(_utc(ts), price, size, side_of(price, b, a), "live", str(exch or ""), str(cond or ""),
                      self._seq)
            self._prints.append(p)
            if self._live_since is None:
                self._live_since = p.ts
            if self._facts_since is None:
                self._facts_since = p.ts
            if self.state in ("STARTING", "QUIET"):
                self.state, self.message = "LIVE", ""
            self.version += 1
            return p

    def add_history(self, rows: Iterable[tuple]) -> int:
        """Prints from before the live stream (ts, price, size, exch, cond).
        Their side is "?": no quote of that moment was read.

        IBKR stamps history in whole seconds, so three 100-share prints at one
        price in one second are three prints, not one: the same history loaded
        twice is caught by COUNT per (second, price, size), never by presence.
        The live stream owns everything from one second before it started — a
        print traded just before the start and received just after it is
        already on the tape as live (review 2026-10-08)."""
        added = 0
        with self._lock:
            live = [p for p in self._prints if p.src == "live"]
            have = Counter(p.key() for p in self._prints if p.src == "hist")
            cutoff = self._live_since.timestamp() - 1.0 if self._live_since is not None else None
            hist = []
            for r in rows:
                try:
                    ts, price, size = _utc(r[0]), float(r[1]), int(round(float(r[2])))
                except (TypeError, ValueError, IndexError):
                    continue
                if price <= 0 or size <= 0:
                    continue
                if cutoff is not None and ts.timestamp() >= cutoff:
                    continue
                p = Print(ts, price, size, "?", "hist", str(r[3] if len(r) > 3 else "") or "",
                          str(r[4] if len(r) > 4 else "") or "")
                if have[p.key()] > 0:
                    have[p.key()] -= 1            # already on the tape from an earlier load
                    continue
                hist.append(p)
                added += 1
            if added:
                older = [p for p in self._prints if p.src == "hist"]
                merged = sorted(older + hist, key=lambda p: p.ts) + live
                self._prints.clear()
                self._prints.extend(merged[-self._prints.maxlen:])
                self.version += 1
        return added

    def gap(self, why: str, ts=None) -> None:
        """Prints may be missing from here: said on the tape, and the facts
        restart after it."""
        with self._lock:
            t = _utc(ts or self.clock())
            self._gaps.append({"t": t.isoformat(), "why": why})
            self._facts_since = t
            self._facts_after = self._seq
            # the quote from before the gap is not the quote now: a print that
            # lands before the next quote reads "?" rather than a stale side
            self._bid = self._ask = self._quote_at = None
            self.version += 1

    # -- readers ---------------------------------------------------------------

    def big_line(self) -> int:
        """The size a print must reach to count as big on THIS tape."""
        with self._lock:
            sizes = [p.size for p in list(self._prints)[-BIG_SAMPLE:]]
        med = median(sizes) if sizes else 0
        return int(max(BIG_FLOOR, BIG_MULT * med))

    def facts(self, window_s: float = WINDOW_S, now: Optional[datetime] = None) -> dict:
        """Shares by side, prints per minute and big prints over the window —
        live prints after the latest gap only."""
        now = _utc(now or self.clock())
        line = self.big_line()
        with self._lock:
            since, after = self._facts_since, self._facts_after
            t0 = now.timestamp() - window_s                       # the window excludes its start instant
            rows = [p for p in self._prints if p.src == "live" and p.seq > after and p.ts.timestamp() > t0]
        start = max(t0, since.timestamp()) if since is not None else t0
        cover = max(0.0, now.timestamp() - start) if since is not None else 0.0
        by = {"ask": 0, "bid": 0, "mid": 0, "?": 0}
        for p in rows:
            by[p.side] += p.size
        sided = by["ask"] + by["bid"] + by["mid"]
        big = [p for p in rows if p.size >= line]
        out = {
            "windowS": window_s, "coverS": round(cover, 1), "prints": len(rows),
            "shares": sum(p.size for p in rows), "atAsk": by["ask"], "atBid": by["bid"],
            "mid": by["mid"], "unknown": by["?"],
            "pctAsk": round(100.0 * by["ask"] / sided, 1) if sided else None,
            "pctBid": round(100.0 * by["bid"] / sided, 1) if sided else None,
            "perMin": round(len(rows) * 60.0 / cover, 1) if cover >= 5 else None,
            "big": len(big), "bigLine": line,
            "lo": min((p.price for p in rows), default=None),
            "hi": max((p.price for p in rows), default=None),
        }
        if big:
            b = big[-1]
            out["lastBig"] = {"t": b.ts.isoformat(), "p": b.price, "s": b.size, "side": b.side}
        return out

    def last_live(self) -> Optional[Print]:
        with self._lock:
            for p in reversed(self._prints):
                if p.src == "live":
                    return p
        return None

    def last_live_at(self) -> Optional[datetime]:
        with self._lock:
            for p in reversed(self._prints):
                if p.src == "live":
                    return p.ts
        return None

    def check_quiet(self, now: Optional[datetime] = None) -> None:
        """LIVE → QUIET after QUIET_S without a print, in words; back to LIVE
        on the next print."""
        now = _utc(now or self.clock())
        last = self.last_live_at() or self._live_since
        if self.state == "LIVE" and last is not None:
            age = (now - last).total_seconds()
            if age >= QUIET_S:
                # no number in the words: it froze while the age kept counting
                # (review 2026-10-08); the card shows the live age beside it
                self.set_state("QUIET", f"no print in the last {int(QUIET_S)} s")

    def snapshot(self, n: int = SHOW, now: Optional[datetime] = None) -> dict:
        now = _utc(now or self.clock())
        line = self.big_line()
        with self._lock:
            rows = list(self._prints)[-n:]
            last = next((p for p in reversed(self._prints) if p.src == "live"), None)
            out = {
                "symbol": self.symbol, "source": self.source, "state": self.state,
                "message": self.message, "version": self.version, "asOf": now.isoformat(),
                "liveSince": self._live_since.isoformat() if self._live_since else None,
                "lastPrintAt": last.ts.isoformat() if last else None,
                "lastPrintAge": round((now - last.ts).total_seconds(), 1) if last else None,
                "quote": ({"bid": self._bid, "ask": self._ask, "at": self._quote_at.isoformat()}
                          if self._quote_at else None),
                "prints": [{"t": p.ts.isoformat(), "p": p.price, "s": p.size, "side": p.side,
                            "big": p.size >= line, "src": p.src, "x": p.exch, "c": p.cond}
                           for p in reversed(rows)],
                "gaps": list(self._gaps),
                "notes": list(self._notes),
                "rule": {"bigMult": BIG_MULT, "bigFloor": BIG_FLOOR, "label": "Approximation"},
            }
        out["facts"] = self.facts(WINDOW_S, now)
        out["now"] = self.facts(NOW_S, now)
        return out


def off_snapshot(message: str, symbol: Optional[str] = None) -> dict:
    """What the page shows when there is no tape at all — a replay, or a desk
    with no live feed. Said, never filled in."""
    return {"symbol": symbol, "source": "", "state": "OFF", "message": message, "version": 0,
            "prints": [], "gaps": [], "notes": [], "facts": None, "now": None, "quote": None,
            "lastPrintAt": None, "lastPrintAge": None, "liveSince": None, "asOf": None,
            "rule": {"bigMult": BIG_MULT, "bigFloor": BIG_FLOOR, "label": "Approximation"}}


def _pos(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and f > 0 else None
