"""Ten-second candles: reading them, folding them into minutes, and proving
the two resolutions describe the same instant.

Plan M3 and M4. Two properties are load-bearing:

**Synchronisation.** The minute Layer A reads must be the aggregate of the
ten-second candles Layer B reads, never a second subscription. If they can
disagree, the disagreement is invisible and every result is unreadable.

**A missing candle is missing, not flat.** IBKR five-second `TRADES` bars do
not print when nothing trades, so a ten-second slot with no trade is absent.
Filling it with a doji at the last price invents a pullback. Gaps are
preserved here and reported by `coverage`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

UTC = timezone.utc
BUCKET_SECONDS = 10


@dataclass(frozen=True)
class Candle:
    symbol: str
    ts: datetime          # bucket START, UTC
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def minute(self) -> datetime:
        return self.ts.replace(second=0, microsecond=0)


class SyncError(AssertionError):
    """The two resolutions disagree about one instant."""


def _dt(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=UTC)
    s = str(ts).replace("Z", "+00:00")
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def load(conn, symbol: Optional[str] = None, day: Optional[str] = None) -> dict[str, list[Candle]]:
    """symbol -> ordered [Candle], straight from `bars_10s`.

    `day` is an ET-naive ISO date ('2026-09-18') matched against the UTC
    timestamp's date. For a 04:00-20:00 ET session the two agree; a candle
    after 20:00 ET would fall on the next UTC day and is deliberately not
    swept in, because this is research data and a silent reach across the
    boundary is worse than a short day.
    """
    from journal import ledger as L
    raw = L.bars_10s_from_ledger(conn, symbol)
    out: dict[str, list[Candle]] = {}
    for sym, rows in raw.items():
        cs = []
        for ts, o, h, lo, c, v in rows:
            if day and str(ts)[:10] != day:
                continue
            cs.append(Candle(sym, _dt(ts), o, h, lo, c, v))
        if cs:
            out[sym] = sorted(cs, key=lambda x: x.ts)
    return out


def to_minutes(candles: Iterable[Candle]) -> list[Candle]:
    """Fold ten-second candles into the minute bars they compose.

    Open of the first, close of the last, extremes and sum of what is
    PRESENT. A minute holding two candles is a real minute with two candles,
    not a broken one — `coverage` is where that is judged.
    """
    by_minute: dict[datetime, list[Candle]] = {}
    for c in sorted(candles, key=lambda x: x.ts):
        by_minute.setdefault(c.minute, []).append(c)
    out = []
    for m, group in sorted(by_minute.items()):
        out.append(Candle(group[0].symbol, m, group[0].open,
                          max(g.high for g in group), min(g.low for g in group),
                          group[-1].close, sum(g.volume for g in group)))
    return out


def coverage(candles: Iterable[Candle]) -> dict:
    """How complete the tape is. A full minute has six ten-second candles.

    Returns counts and the missing slots — never an interpolation.
    """
    cs = sorted(candles, key=lambda x: x.ts)
    if not cs:
        return {"candles": 0, "minutes": 0, "expected": 0, "present_pct": None, "gaps": []}
    by_minute: dict[datetime, set] = {}
    for c in cs:
        by_minute.setdefault(c.minute, set()).add(c.ts.second // BUCKET_SECONDS)
    gaps = []
    for m, slots in sorted(by_minute.items()):
        missing = sorted(set(range(6)) - slots)
        if missing:
            gaps.append({"minute": m.isoformat().replace("+00:00", "Z"),
                         "missing_slots": missing, "present": len(slots)})
    expected = len(by_minute) * 6
    return {"candles": len(cs), "minutes": len(by_minute), "expected": expected,
            "present_pct": round(100.0 * len(cs) / expected, 2) if expected else None,
            "gaps": gaps}


def assert_sync(fine: Iterable[Candle], minute_bars: Iterable, tol: float = 1e-6) -> None:
    """M3. Raise unless every minute bar equals the fold of its ten-second
    candles. Minutes absent from either side are skipped, not guessed at:
    this checks agreement where both spoke, and `coverage` reports silence.

    `minute_bars` is an iterable of (ts, o, h, l, c, v) or of Candle.
    """
    folded = {c.ts: c for c in to_minutes(fine)}
    for b in minute_bars:
        if isinstance(b, Candle):
            ts, o, h, lo, c, v = b.ts, b.open, b.high, b.low, b.close, b.volume
        else:
            ts, o, h, lo, c, v = _dt(b[0]), b[1], b[2], b[3], b[4], b[5]
        f = folded.get(ts)
        if f is None:
            continue
        for name, mine, theirs in (("high", f.high, h), ("low", f.low, lo),
                                   ("open", f.open, o), ("close", f.close, c)):
            if mine is None or theirs is None:
                continue
            if abs(mine - theirs) > tol:
                raise SyncError(
                    f"{f.symbol} {ts.isoformat()}: {name} disagrees — "
                    f"10s fold {mine} vs 1m bar {theirs}. One of the two "
                    f"resolutions is describing a different instant.")
        if v is not None and f.volume > v + tol:
            raise SyncError(
                f"{f.symbol} {ts.isoformat()}: the 10s candles carry more "
                f"volume ({f.volume}) than the minute bar ({v}).")


def forming_minute(candles: Iterable[Candle], now: datetime) -> Optional[Candle]:
    """The minute in progress at `now`, built ONLY from candles already closed.

    This is what Layer B is allowed to see: the running open, high, low and
    volume of the current minute as it stood at that instant, never the
    finished bar. Returns None before the first closed candle of the minute.
    """
    m = now.replace(second=0, microsecond=0)
    group = [c for c in candles if c.minute == m and c.ts + timedelta(seconds=BUCKET_SECONDS) <= now]
    if not group:
        return None
    group.sort(key=lambda x: x.ts)
    return Candle(group[0].symbol, m, group[0].open, max(g.high for g in group),
                  min(g.low for g in group), group[-1].close, sum(g.volume for g in group))
