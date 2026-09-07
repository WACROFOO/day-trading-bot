"""The three chart gates FILTERS.md Layer 2 requires, from minute bars alone.

    price > vwap · price > ema9 · macd_hist > 0 and macd > signal

Pure Python over the session's [ts, o, h, l, c, v] rows, so the desk, the
cascade and the replay all compute them the same way from the same bars.
Anything that cannot be computed honestly is None — never a guess — and the
cascade turns None into WATCH, not into a pass.

Warm-up is the honesty rule here: an EMA9 needs 9 closes, a MACD 12/26/9
needs 26 closes before the slow EMA means anything and 9 more before the
signal does. Below that the answer is None. Until this module existed the
cascade received None for all three on every live decision, so REVIEW was
unreachable and TRADE mode never checked the chart at all.
"""

from __future__ import annotations

from typing import Optional, Sequence

Bar = Sequence  # [ts, o, h, l, c, v]

EMA9_MIN = 9
MACD_MIN = 26 + 9


def vwap(bars: Sequence[Bar]) -> Optional[float]:
    pv = vol = 0.0
    for b in bars:
        tp = (b[2] + b[3] + b[4]) / 3.0
        pv += tp * b[5]
        vol += b[5]
    return pv / vol if vol > 0 else None


def ema(values: Sequence[float], n: int) -> list[float]:
    """Seeded with the first value; standard 2/(n+1) smoothing after."""
    if not values:
        return []
    k = 2.0 / (n + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def macd(closes: Sequence[float], fast: int = 12, slow: int = 26, sig: int = 9):
    """(macd_line, signal, hist) as lists, or None when too short."""
    if len(closes) < slow + sig:
        return None
    ef, es = ema(closes, fast), ema(closes, slow)
    line = [a - b for a, b in zip(ef, es)]
    signal = ema(line[slow - 1:], sig)
    line = line[slow - 1:]
    hist = [m - s for m, s in zip(line, signal)]
    return line, signal, hist


def chart_gates(bars: Sequence[Bar]) -> dict:
    """The Layer 2 booleans for the LAST bar in `bars`, or None each."""
    out = {"above_vwap": None, "above_ema9": None, "macd_positive_and_above_signal": None,
           "vwap": None, "ema9": None, "macd_hist": None}
    if not bars:
        return out
    closes = [b[4] for b in bars]
    last = closes[-1]
    v = vwap(bars)
    if v is not None:
        out["vwap"] = round(v, 4)
        out["above_vwap"] = last > v
    if len(closes) >= EMA9_MIN:
        e = ema(closes, 9)[-1]
        out["ema9"] = round(e, 4)
        out["above_ema9"] = last > e
    m = macd(closes)
    if m is not None:
        line, signal, hist = m
        out["macd_hist"] = round(hist[-1], 6)
        out["macd_positive_and_above_signal"] = hist[-1] > 0 and line[-1] > signal[-1]
    return out
