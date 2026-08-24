"""Strictly causal, incremental indicators.

Every value here is a function of bars 0..i and nothing else. That is not a
convention, it is the whole defence against look-ahead: there is no vectorised
pass over a full day anywhere in this module, so there is no place for a
future bar to leak in. tests/test_lookahead.py checks the property by
truncation - feeding a prefix must reproduce the prefix's values exactly.

The one number people get wrong is HOD. Here it is always
`max(high) over session start .. current bar inclusive`, never the eventual
daily high.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from .data import Bar


class EMA:
    def __init__(self, n: int):
        self.k = 2.0 / (n + 1)
        self.value: float | None = None

    def update(self, x: float) -> float:
        self.value = x if self.value is None else x * self.k + self.value * (1 - self.k)
        return self.value


class MACD:
    """12/26 EMAs, 9-EMA signal. `hist` = macd - signal.

    ross-fp-v4.pine line 1583: macdBullish = macdValue > 0 and macdHist > 0.
    """

    def __init__(self, fast=12, slow=26, sig=9):
        self.f, self.s, self.g = EMA(fast), EMA(slow), EMA(sig)
        self.macd = self.signal = self.hist = 0.0

    def update(self, c: float):
        self.macd = self.f.update(c) - self.s.update(c)
        self.signal = self.g.update(self.macd)
        self.hist = self.macd - self.signal
        return self.macd, self.signal, self.hist


class ATR:
    """Wilder ATR14, seeded on the first true range - same shape as ta.atr()."""

    def __init__(self, n: int = 14):
        self.n = n
        self.value: float | None = None
        self._prev_close: float | None = None

    def update(self, b: Bar) -> float:
        tr = (b.h - b.l) if self._prev_close is None else max(
            b.h - b.l, abs(b.h - self._prev_close), abs(b.l - self._prev_close))
        self.value = tr if self.value is None else (self.value * (self.n - 1) + tr) / self.n
        self._prev_close = b.c
        return self.value


class RollingMean:
    def __init__(self, n: int):
        self.n = n
        self.buf: list[float] = []
        self.total = 0.0

    def update(self, x: float) -> float | None:
        self.buf.append(x)
        self.total += x
        if len(self.buf) > self.n:
            self.total -= self.buf.pop(0)
        return self.value

    @property
    def value(self) -> float | None:
        return self.total / len(self.buf) if self.buf else None


@dataclass
class Snapshot:
    """Everything the setup detector may read at bar i. Nothing else exists."""

    i: int
    bar: Bar
    ema9: float
    ema20: float
    macd: float
    macd_signal: float
    macd_hist: float
    macd_hist_prev: float
    atr: float
    vwap: float | None
    hod: float                 # session high THROUGH this bar
    lod: float
    cum_volume: float
    cum_dollar_volume: float
    vol_baseline: float | None       # SMA(volume, 20) through this bar
    vol_baseline_hist: list[float]   # per-bar history of the above, index = bar i
    rvol_at_time: float | None       # cum volume vs same-time-of-day average
    prev_close: float | None
    gap_pct: float | None
    session_minute: int              # minutes since 04:00 ET
    in_rth: bool
    et: dt.datetime
    dollar_per_min_5: float
    dollar_per_min_20: float
    dollar_per_min_day: float
    spread_est: float                # proxy: see SessionState.spread_estimate
    halt_gap_before: int             # missing minutes immediately before this bar


class SessionState:
    """One symbol, one trading day, fed bar by bar in order.

    `prev_close` and `same_time_cum_volume` are inputs from BEFORE the day
    starts, so they carry no look-ahead. Everything else accumulates forward.
    """

    def __init__(self, sym: str, day: dt.date, prev_close: float | None = None,
                 same_time_cum_volume: dict[int, float] | None = None,
                 vwap_include_premarket: bool = True,
                 vol_baseline_bars: int = 20):
        self.sym = sym
        self.day = day
        self.prev_close = prev_close
        self.same_time = same_time_cum_volume or {}
        self.vwap_include_premarket = vwap_include_premarket

        self.ema9, self.ema20 = EMA(9), EMA(20)
        self.macd = MACD()
        self.atr = ATR(14)
        self.volbase = RollingMean(vol_baseline_bars)
        self.vol_baseline_hist: list[float] = []

        self._pv = 0.0
        self._pvol = 0.0
        self.hod: float | None = None
        self.lod: float | None = None
        self.cum_volume = 0.0
        self.cum_dollar = 0.0
        self.bars: list[Bar] = []
        self._last_ts: int | None = None
        self._ranges: list[float] = []

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def session_minute(b: Bar) -> int:
        e = b.et
        return (e.hour - 4) * 60 + e.minute

    def spread_estimate(self) -> float:
        """No quote data anywhere in the free tier, so the spread is a proxy:
        the 25th percentile of recent 1-minute ranges, floored at one tick.
        Labelled an estimate everywhere it is used; a real study buys quotes.
        """
        if not self._ranges:
            return 0.01
        r = sorted(self._ranges[-60:])
        return max(0.01, r[max(0, int(len(r) * 0.25) - 1)])

    def _dollar_per_min(self, n: int) -> float:
        window = self.bars[-n:] if n else self.bars
        if not window:
            return 0.0
        return sum(b.v * b.c for b in window) / len(window)

    # -- the only mutating entry point -----------------------------------
    def update(self, b: Bar) -> Snapshot:
        gap_minutes = 0
        if self._last_ts is not None:
            gap_minutes = max(0, int((b.ts - self._last_ts) / 60) - 1)
        self._last_ts = b.ts

        self.bars.append(b)
        i = len(self.bars) - 1

        in_rth = dt.time(9, 30) <= b.et.time() < dt.time(16, 0)
        use_for_vwap = self.vwap_include_premarket or in_rth
        if use_for_vwap and b.v > 0:
            typ = (b.h + b.l + b.c) / 3.0
            self._pv += typ * b.v
            self._pvol += b.v
        vwap = (self._pv / self._pvol) if self._pvol > 0 else None

        self.hod = b.h if self.hod is None else max(self.hod, b.h)
        self.lod = b.l if self.lod is None else min(self.lod, b.l)
        self.cum_volume += b.v
        self.cum_dollar += b.v * b.c
        self._ranges.append(b.h - b.l)

        e9 = self.ema9.update(b.c)
        e20 = self.ema20.update(b.c)
        prev_hist = self.macd.hist
        m, s, h = self.macd.update(b.c)
        a = self.atr.update(b)
        vb = self.volbase.update(b.v)
        self.vol_baseline_hist.append(vb if vb is not None else 0.0)

        sm = self.session_minute(b)
        expected = self.same_time.get(sm)
        rvol = (self.cum_volume / expected) if expected else None
        gap = ((b.c - self.prev_close) / self.prev_close * 100.0
               if self.prev_close else None)

        return Snapshot(
            i=i, bar=b, ema9=e9, ema20=e20, macd=m, macd_signal=s, macd_hist=h,
            macd_hist_prev=prev_hist, atr=a, vwap=vwap, hod=self.hod, lod=self.lod,
            cum_volume=self.cum_volume, cum_dollar_volume=self.cum_dollar,
            vol_baseline=vb, vol_baseline_hist=self.vol_baseline_hist,
            rvol_at_time=rvol, prev_close=self.prev_close, gap_pct=gap,
            session_minute=sm, in_rth=in_rth, et=b.et,
            dollar_per_min_5=self._dollar_per_min(5),
            dollar_per_min_20=self._dollar_per_min(20),
            dollar_per_min_day=self._dollar_per_min(0),
            spread_est=self.spread_estimate(),
            halt_gap_before=gap_minutes)


def same_time_cum_volume_profile(prior_days: list[list[Bar]]) -> dict[int, float]:
    """Average cumulative volume by session minute, over PRIOR days only.

    This is the honest RVOL-at-time denominator: at 09:47 you compare today's
    cumulative volume to what this name had done by 09:47 on previous days,
    never to its eventual full-day total (which is the proxy the Pine's own
    dashboard warns about at line 355).
    """
    acc: dict[int, list[float]] = {}
    for bars in prior_days:
        cum = 0.0
        seen: dict[int, float] = {}
        for b in bars:
            cum += b.v
            seen[SessionState.session_minute(b)] = cum
        for k, v in seen.items():
            acc.setdefault(k, []).append(v)
    return {k: sum(v) / len(v) for k, v in acc.items() if v}
