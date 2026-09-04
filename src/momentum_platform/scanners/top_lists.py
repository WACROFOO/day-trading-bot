"""Ranked list scanners: Top Gainers, Top Losers, Top Gappers,
Low Float Top Gainers, Top RVOL, Top 5-minute Volume.

Confirmed platform behavior reproduced: lists refresh on a cadence (not
per-tick), Top Gappers freezes at 09:30 ET, displayed columns are data fields
rather than inclusion filters. Ranking metrics are transparent formulas.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from ..formulas import effective_rvol
from ..models import RankedRow, Reason
from ..sessions import SessionCalendar
from ..state import HotState
from .base import Scanner, _round


class TopListScanner(Scanner):
    """Generic ranked list over the tracked universe."""

    def __init__(
        self,
        scanner_id: str,
        metric: str,                    # snapshot attribute to rank by
        descending: bool = True,
        min_price: float = 1.0,
        max_price: Optional[float] = None,
        max_float_shares: Optional[float] = None,
        min_volume_today: float = 0.0,
        max_rows: int = 50,
        version: str = "1.0.0",
    ) -> None:
        self.scanner_id = scanner_id
        self.definition_version = f"{scanner_id}@{version}"
        self.metric = metric
        self.descending = descending
        self.min_price = min_price
        self.max_price = max_price
        self.max_float_shares = max_float_shares
        self.min_volume_today = min_volume_today
        self.max_rows = max_rows

    def rank(self, hot: HotState, now: datetime) -> List[RankedRow]:
        rows: List[RankedRow] = []
        for state in hot.symbols.values():
            snap = state.snapshot
            if snap.last is None:
                continue
            if snap.last < self.min_price:
                continue
            if self.max_price is not None and snap.last > self.max_price:
                continue
            if snap.volume_today < self.min_volume_today:
                continue
            if self.max_float_shares is not None:
                if snap.float_shares is None or snap.float_shares > self.max_float_shares:
                    continue
            value = (effective_rvol(snap) if self.metric == "rvol"
                     else getattr(snap, self.metric, None))
            if value is None:
                continue
            rows.append(
                RankedRow(
                    symbol=snap.symbol,
                    rank_metric=value,
                    values=self._base_values(snap)
                    | {"metric": self.metric, "metric_value": _round(value)},
                )
            )
        rows.sort(key=lambda r: r.rank_metric, reverse=self.descending)
        return rows[: self.max_rows]


def top_gainers(**kw) -> TopListScanner:
    return TopListScanner("top_gainers", metric="change_from_close_pct", **kw)


def top_losers(**kw) -> TopListScanner:
    return TopListScanner("top_losers", metric="change_from_close_pct", descending=False, **kw)


def low_float_top_gainers(max_float_shares: float = 20_000_000, **kw) -> TopListScanner:
    return TopListScanner(
        "low_float_top_gainers",
        metric="change_from_close_pct",
        max_float_shares=max_float_shares,
        **kw,
    )


def top_relative_volume(**kw) -> TopListScanner:
    return TopListScanner("top_relative_volume", metric="rvol", **kw)


def top_volume_5m(**kw) -> TopListScanner:
    return TopListScanner("top_volume_5m", metric="volume_5m", **kw)


class TopGappersScanner(TopListScanner):
    """Ranks by gap percentage and freezes its output at 09:30 ET
    (Confirmed platform behavior: gapper lists stop updating at the open)."""

    def __init__(self, calendar: Optional[SessionCalendar] = None, **kw) -> None:
        super().__init__("top_gappers", metric="gap_pct", **kw)
        self.calendar = calendar or SessionCalendar()
        self._frozen: Optional[List[RankedRow]] = None
        self._frozen_date = None

    def rank(self, hot: HotState, now: datetime) -> List[RankedRow]:
        d = self.calendar.trading_date(now)
        if self._frozen_date != d:
            self._frozen, self._frozen_date = None, d
        if self.calendar.is_before_open(now):
            rows = super().rank(hot, now)
            self._frozen = rows
            return rows
        if self._frozen is None:
            self._frozen = super().rank(hot, now)
        return self._frozen
