"""The desk's chart levels in Python: support/resistance and trend lines exactly as
`dashboard/web/levels.js` draws them, so research scores the lines the trader sees.

A line-for-line port of levels.js's `pivots`, `atr`, `mintick`, `srFan`, `trendLines` and
`roundLevels` (the fan is the port of knowledge-base/tradingview/ross-fp-v4.pine V9.5; the
trend lines the two-swing method of 2026-10-14 — see levels.js's header). Same names, same
order of floating-point operations: `tests/test_levels_port.py` runs both on the same bars
in node and compares.

Bars are (t, o, h, l, c, v) sequences, oldest first — the JS shape.

`DayLevels` is the same answers for every bar of one day, fast enough for five years of
backtests: a swing, once confirmed, never changes (its five right-hand bars are fixed), so
the day's pivots and each pair of swings' fixed facts are computed once and every query
reads only bars before the bar it is asked about. The tests check it against the direct
port at every bar.

Levels and lines describe where trading happened. Whether price turns or breaks out there
is what `scripts/candidates/` measures (research/strategy-candidates/PREREGISTRATION.md,
amendment 2026-10-14) — nothing here decides anything.
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

PIVOT = 5              # ross-fp-v4.pine srPivotLen
PIVOTS_KEPT = 40       # ross-fp-v4.pine: pivHighs / pivLows hold the last 40 each
SR_EACH = 2            # ross-fp-v4.pine maxSRlines: "2 = clean"
SR_DEDUP_ATR = 0.5     # ross-fp-v4.pine tolSR = atr * 0.5
BAND_ATR = 0.12        # ross-fp-v4.pine bandATRfrac
TL_TOL_ATR = 0.20      # ross-fp-v4.pine tolTL = atr * 0.20
TL_SWINGS = 10         # "Trend Lines v2": the last 10 swings of each kind
TL_KEEP_BROKEN = 20    # a line broken within the last 20 bars stays drawn
ATR_LEN = 14


def pivots(bars: Sequence, left: int = PIVOT, right: int = PIVOT) -> list[dict]:
    """levels.js `pivots`: swing highs and lows in time order; a high above the `left`
    bars before it and not below the `right` bars after it (lows mirrored)."""
    out = []
    n = len(bars)
    for i in range(left, n - right):
        high = low = True
        hi, lo = bars[i][2], bars[i][3]
        j = i - left
        while j <= i + right and (high or low):
            if j != i:
                if (bars[j][2] >= hi) if j < i else (bars[j][2] > hi):
                    high = False
                if (bars[j][3] <= lo) if j < i else (bars[j][3] < lo):
                    low = False
            j += 1
        if high:
            out.append({"i": i, "t": bars[i][0], "price": hi, "kind": "high"})
        if low:
            out.append({"i": i, "t": bars[i][0], "price": lo, "kind": "low"})
    return out


def _tr(bars: Sequence, i: int) -> float:
    b = bars[i]
    if i == 0:
        return b[2] - b[3]
    pc = bars[i - 1][4]
    return max(b[2] - b[3], abs(b[2] - pc), abs(b[3] - pc))


def atr(bars: Sequence, n: int = ATR_LEN) -> Optional[float]:
    """levels.js `atr`: Pine's ta.atr — the simple mean of the first n true ranges, then
    Wilder's average. The value at the last bar; None with fewer than n bars."""
    if not bars or len(bars) < n:
        return None
    s, a = 0.0, None
    for i in range(len(bars)):
        tr = _tr(bars, i)
        if i < n:
            s += tr
            if i == n - 1:
                a = s / n
        else:
            a = (a * (n - 1) + tr) / n
    return a


def atr_series(bars: Sequence, n: int = ATR_LEN) -> list[Optional[float]]:
    """`atr(bars[:i + 1])` for every i, in one pass (the same operations, so the same floats)."""
    out: list[Optional[float]] = []
    s, a = 0.0, None
    for i in range(len(bars)):
        tr = _tr(bars, i)
        if i < n:
            s += tr
            if i == n - 1:
                a = s / n
        else:
            a = (a * (n - 1) + tr) / n
        out.append(a if i >= n - 1 else None)
    return out


def mintick(price: float) -> float:
    """A US stock's minimum tick: a cent from $1, a hundredth of a cent under."""
    return 0.01 if price >= 1 else 0.0001


def _fan(highs: list[dict], lows: list[dict], close: float, a: float, each: int, keep: int) -> dict:
    pool = highs[-keep:] + lows[-keep:]                     # Pine: pivHighs, then pivLows
    tol = a * SR_DEDUP_ATR

    def side(above: bool) -> list[dict]:
        out: list[dict] = []
        for p in pool:
            if not (p["price"] > close if above else p["price"] < close):
                continue
            dup = next((o for o in out if abs(o["price"] - p["price"]) <= tol), None)
            if dup is not None:
                dup["touches"] += 1
                dup["highs"] += 1 if p["kind"] == "high" else 0
                dup["lows"] += 1 if p["kind"] == "low" else 0
                continue
            out.append({"price": p["price"], "touches": 1, "highs": 1 if p["kind"] == "high" else 0,
                        "lows": 1 if p["kind"] == "low" else 0})
        out.sort(key=(lambda x: x["price"]) if above else (lambda x: -x["price"]))
        return out[:each]

    return {"res": side(True), "sup": side(False), "band": max(a * BAND_ATR, mintick(close)), "atr": a}


def sr_fan(bars: Sequence, close: Optional[float], a: Optional[float], each: int = SR_EACH,
           keep: int = PIVOTS_KEPT, pivot: int = PIVOT) -> dict:
    """levels.js `srFan`: the last 40 swing highs and 40 swing lows feed both sides; above
    `close` a level is resistance, below it support; levels within half an ATR print once;
    the two nearest each side are kept, nearest first; `band` is the highlighted half-width."""
    if not bars or close is None or not (a is not None and a > 0):
        return {"res": [], "sup": [], "band": None, "atr": a or None}
    piv = pivots(bars, pivot, pivot)
    return _fan([p for p in piv if p["kind"] == "high"], [p for p in piv if p["kind"] == "low"], close, a, each, keep)


class _Line:
    """One trend line: levels.js's line object (`at(i)` is the line's price at bar i)."""
    __slots__ = ("a", "b", "pa", "pb", "slope", "touches", "brokeAt", "breakPrice", "now", "through")

    def __init__(self, A: dict, B: dict, slope: float):
        self.a, self.b, self.pa, self.pb, self.slope = A["i"], B["i"], A["price"], B["price"], slope

    def at(self, i: float) -> float:
        return self.pa + self.slope * (i - self.a)

    def as_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__slots__}


def _beyond(up: bool, v: float, line: float, by: float) -> bool:
    return v < line - by if up else v > line + by


def trend_lines(bars: Sequence, close: Optional[float], a: Optional[float], from_: int = 0,
                pivot: int = PIVOT, keep: int = TL_KEEP_BROKEN) -> dict:
    """levels.js `trendLines`: `bars` are the CONFIRMED bars, oldest first; the live bar is
    index len(bars) and `close` its price. Returns {up, down, upBroken, downBroken}, each a
    `_Line` or None — see levels.js for the method."""
    none = {"up": None, "down": None, "upBroken": None, "downBroken": None}
    P, frm = pivot, max(0, from_ or 0)
    n = len(bars)
    if n < 2 * P + 2 or close is None or not (a is not None and a > 0):
        return none
    tol = max(a * TL_TOL_ATR, mintick(close))
    piv = [p for p in pivots(bars, P, P) if p["i"] >= frm]

    def side(up: bool):
        sw = [p for p in piv if p["kind"] == ("low" if up else "high")][-TL_SWINGS:]
        intact = broken = None
        bi = len(sw) - 1
        while bi >= 1 and intact is None:
            B = sw[bi]
            for ai in range(bi - 1, -1, -1):
                A = sw[ai]
                if (not (A["price"] < B["price"])) if up else (not (A["price"] > B["price"])):
                    continue
                ln = _Line(A, B, (B["price"] - A["price"]) / (B["i"] - A["i"]))
                ok = True
                k = A["i"] + 1
                while k < B["i"] and ok:
                    if _beyond(up, bars[k][4], ln.at(k), 1e-9):
                        ok = False
                    k += 1
                k = ai + 1
                while k < bi and ok:
                    if _beyond(up, sw[k]["price"], ln.at(sw[k]["i"]), tol):
                        ok = False
                    k += 1
                if not ok:
                    continue
                broke_at = None
                for k in range(B["i"] + 1, n):
                    if _beyond(up, bars[k][4], ln.at(k), 1e-9):
                        broke_at = k
                        break
                end = n if broke_at is None else broke_at
                ln.touches = sum(1 for p in sw if A["i"] <= p["i"] <= end and abs(p["price"] - ln.at(p["i"])) <= tol)
                ln.brokeAt = broke_at
                ln.breakPrice = None if broke_at is None else ln.at(broke_at)
                ln.now = ln.at(n)
                ln.through = broke_at is None and _beyond(up, close, ln.now, 1e-9)
                if broke_at is None:
                    intact = ln
                    break
                if n - broke_at <= keep and (broken is None or broke_at > broken.brokeAt):
                    broken = ln
            bi -= 1
        return intact, broken

    u, d = side(True), side(False)
    return {"up": u[0], "down": d[0], "upBroken": u[1], "downBroken": d[1]}


def round_levels(price: Optional[float]) -> dict:
    """levels.js `roundLevels`: the nearest whole or half dollar strictly below and above."""
    if not (price is not None and price > 0):
        return {"below": None, "above": None}
    below = math.ceil(price * 2 - 1e-9) / 2 - 0.5
    above = math.floor(price * 2 + 1e-9) / 2 + 0.5
    return {"below": below if below > 0 else None, "above": above}


# ------------------------------------------------------------------ one day, every bar
class DayLevels:
    """The desk's levels at every bar of one day of bars, as `sr_fan` and `trend_lines`
    would draw them from a prefix of the bars — without recomputing the prefix each time.

    `fan(t, close)`         == sr_fan(bars[:t], close, atr(bars[:t]))
    `lines(t, close, from_)` == trend_lines(bars[:t], close, atr(bars[:t]), from_) — intact lines
                               only (`up`, `down`), with `through` judged against `close`.

    Nothing about bar t or later is read to answer a question about bars[:t]: pivots and
    pair facts computed over the whole day are used only where they involve bars < t
    (a swing at i is in bars[:t] iff i + PIVOT < t; a pair's break counts iff before t)."""

    def __init__(self, bars: Sequence, pivot: int = PIVOT):
        self.bars = bars
        self.P = pivot
        self.atrs = atr_series(bars)
        self.piv = pivots(bars, pivot, pivot)
        self._kind = {"high": [p for p in self.piv if p["kind"] == "high"],
                      "low": [p for p in self.piv if p["kind"] == "low"]}
        self._pairs: dict = {}

    def atr_before(self, t: int) -> Optional[float]:
        """atr(bars[:t])."""
        return self.atrs[t - 1] if t >= 1 else None

    def _confirmed(self, kind: str, t: int, frm: int = 0) -> list[dict]:
        sw = self._kind[kind]
        # pivots(bars[:t]) holds swings with i + P < t, i.e. i <= t - P - 1
        lim = t - self.P - 1
        lo, hi = 0, len(sw)
        while lo < hi:
            mid = (lo + hi) // 2
            if sw[mid]["i"] <= lim:
                lo = mid + 1
            else:
                hi = mid
        out = sw[:lo]
        return [p for p in out if p["i"] >= frm] if frm > 0 else out

    def fan(self, t: int, close: Optional[float], each: int = SR_EACH, keep: int = PIVOTS_KEPT) -> dict:
        a = self.atr_before(t)
        if t <= 0 or close is None or not (a is not None and a > 0):
            return {"res": [], "sup": [], "band": None, "atr": a or None}
        # the swings of pivots(bars[:t]), each kind in time order
        return _fan(self._confirmed("high", t), self._confirmed("low", t), close, a, each, keep)

    def _pair(self, up: bool, A: dict, B: dict) -> dict:
        key = (up, A["i"], B["i"])
        got = self._pairs.get(key)
        if got is None:
            c = self.bars
            ln = _Line(A, B, (B["price"] - A["price"]) / (B["i"] - A["i"]))
            closes_ok = not any(_beyond(up, c[k][4], ln.at(k), 1e-9) for k in range(A["i"] + 1, B["i"]))
            broke = None
            for k in range(B["i"] + 1, len(c)):
                if _beyond(up, c[k][4], ln.at(k), 1e-9):
                    broke = k
                    break
            got = {"line": ln, "closes_ok": closes_ok, "broke": broke}
            self._pairs[key] = got
        return got

    def lines(self, t: int, close: Optional[float], from_: int = 0) -> dict:
        """The intact up- and down-lines drawn on bars[:t] (the live bar is t)."""
        a = self.atr_before(t)
        out = {"up": None, "down": None}
        if t < 2 * self.P + 2 or close is None or not (a is not None and a > 0):
            return out
        tol = max(a * TL_TOL_ATR, mintick(close))
        for up in (True, False):
            sw = self._confirmed("low" if up else "high", t, max(0, from_ or 0))[-TL_SWINGS:]
            found = None
            for bi in range(len(sw) - 1, 0, -1):
                B = sw[bi]
                for ai in range(bi - 1, -1, -1):
                    A = sw[ai]
                    if (not (A["price"] < B["price"])) if up else (not (A["price"] > B["price"])):
                        continue
                    pr = self._pair(up, A, B)
                    if not pr["closes_ok"]:
                        continue
                    ln = pr["line"]
                    if any(_beyond(up, sw[k]["price"], ln.at(sw[k]["i"]), tol) for k in range(ai + 1, bi)):
                        continue
                    if pr["broke"] is not None and pr["broke"] < t:
                        continue                                    # broken before the live bar
                    now = ln.at(t)
                    found = {"a": ln.a, "b": ln.b, "pa": ln.pa, "pb": ln.pb, "slope": ln.slope, "now": now,
                             "through": _beyond(up, close, now, 1e-9), "line": ln}
                    break
                if found is not None:
                    break
            out["up" if up else "down"] = found
        return out
