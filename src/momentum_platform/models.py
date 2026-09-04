"""Canonical data models: symbol snapshots, bars, events, news.

All timestamps are timezone-aware UTC datetimes. Session logic converts to
America/New_York at the edges (see sessions.py); nothing in the models assumes
a fixed UTC offset.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class Session(str, Enum):
    PREMARKET = "premarket"
    REGULAR = "regular"
    AFTER_HOURS = "after_hours"
    CLOSED = "closed"


class FloatQuality(str, Enum):
    VERIFIED = "verified"           # true float from a trusted reference source
    SHARES_OUTSTANDING = "shares_outstanding_proxy"
    UNKNOWN = "unknown"


class DataStatus(str, Enum):
    LIVE = "live"
    DELAYED = "delayed"
    REPLAY = "replay"
    STALE = "stale"


@dataclass
class Bar:
    """One OHLCV bar. `ts` is the bar's open time (UTC)."""

    symbol: str
    timeframe: str  # "1m", "5m", "1d"
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    session: Session = Session.REGULAR


@dataclass
class SymbolSnapshot:
    """Hot per-symbol state. One instance per tracked symbol, mutated in place
    by the HotState as market updates arrive."""

    symbol: str
    event_ts: Optional[datetime] = None
    ingest_ts: Optional[datetime] = None
    last: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    prev_close: Optional[float] = None
    regular_open: Optional[float] = None
    session_high: Optional[float] = None
    session_low: Optional[float] = None
    volume_today: float = 0.0
    volume_5m: Optional[float] = None
    avg_daily_volume: Optional[float] = None   # baseline for simple daily RVOL
    # Median cumulative volume prior sessions had traded by each five-minute
    # bucket after 04:00 ET. The baseline for time-of-day relative volume.
    volume_profile: Optional[list] = None
    high_52w: Optional[float] = None           # prior 252 sessions, excludes today
    float_shares: Optional[float] = None
    float_quality: FloatQuality = FloatQuality.UNKNOWN
    latest_news_ts: Optional[datetime] = None
    news_headline: Optional[str] = None
    halt_status: str = "trading"
    data_status: DataStatus = DataStatus.REPLAY
    session: Session = Session.CLOSED

    # ---- derived metrics (computed by formulas.enrich_snapshot) -------------
    change_from_close_pct: Optional[float] = None
    change_from_open_pct: Optional[float] = None
    gap_pct: Optional[float] = None
    rvol_daily: Optional[float] = None         # today / mean prior FULL days
    rvol_tod: Optional[float] = None           # today / prior sessions at this clock time
    rvol: Optional[float] = None               # the measure the pillars use
    rvol_measure: str = "daily"                # "time_of_day" when a profile drove it
    rvol_baseline: Optional[float] = None      # shares the profile expected by now
    rvol_5m: Optional[float] = None
    spread_abs: Optional[float] = None
    spread_bps: Optional[float] = None
    range_position: Optional[float] = None
    hod_distance_pct: Optional[float] = None

    def copy_shallow(self) -> "SymbolSnapshot":
        return SymbolSnapshot(**{k: v for k, v in self.__dict__.items()})


@dataclass
class Reason:
    """One explainable pass/fail condition attached to a scanner event."""

    filter: str
    value: Any
    passed: bool
    threshold: Any = None

    def to_dict(self) -> dict:
        d = {"filter": self.filter, "value": self.value, "passed": self.passed}
        if self.threshold is not None:
            d["threshold"] = self.threshold
        return d


@dataclass
class ScannerEvent:
    """Canonical scanner event envelope (spec section 13)."""

    symbol: str
    scanner: str
    branch: Optional[str]
    event_type: str            # "qualified", "rank_update", ...
    severity: str              # "critical" | "high" | "medium" | "low"
    session: Session
    source_ts: datetime
    scan_ts: datetime
    definition_version: str
    values: dict = field(default_factory=dict)
    reasons: list = field(default_factory=list)      # list[Reason]
    news: Optional[dict] = None
    data_quality: str = DataStatus.REPLAY.value
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    idempotency_key: str = ""

    def __post_init__(self) -> None:
        if not self.idempotency_key:
            bucket = self.source_ts.strftime("%Y%m%dT%H%M%S")
            self.idempotency_key = (
                f"{self.symbol}|{self.scanner}|{self.branch or '-'}|{bucket}"
            )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["session"] = self.session.value
        d["source_ts"] = self.source_ts.isoformat()
        d["scan_ts"] = self.scan_ts.isoformat()
        d["reasons"] = [
            r.to_dict() if isinstance(r, Reason) else r for r in self.reasons
        ]
        return d


@dataclass
class RankedRow:
    """One row of a ranked list scanner."""

    symbol: str
    rank_metric: float
    values: dict = field(default_factory=dict)
    reasons: list = field(default_factory=list)


@dataclass
class NewsItem:
    provider: str
    provider_id: str
    published_at: datetime
    headline: str
    symbols: list = field(default_factory=list)
    url: Optional[str] = None
    category: Optional[str] = None

    def age_minutes(self, now: datetime) -> float:
        return (now - self.published_at).total_seconds() / 60.0


def flame_color(news_age_minutes: Optional[float]) -> Optional[str]:
    """Flame is a NEWS-AGE indicator only (Confirmed platform behavior):
    red 0-2h, orange 2-12h, yellow 12-24h, none >24h or no item.
    It is not a compliance score and not a statement about news quality."""
    if news_age_minutes is None or news_age_minutes < 0:
        return None
    if news_age_minutes <= 2 * 60:
        return "red"
    if news_age_minutes <= 12 * 60:
        return "orange"
    if news_age_minutes <= 24 * 60:
        return "yellow"
    return None
