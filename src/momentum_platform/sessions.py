"""US-equity session calendar. All boundaries are America/New_York wall-clock
times, DST-safe via zoneinfo (never a fixed UTC offset).

Premarket 04:00-09:30, regular 09:30-16:00, after-hours 16:00-20:00 ET.
Weekend handling is built in; exchange holidays/early closes are supplied as
data because a hardcoded list rots.
"""

from __future__ import annotations

from datetime import datetime, time, date
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

from .models import Session

ET = ZoneInfo("America/New_York")

PREMARKET_START = time(4, 0)
REGULAR_START = time(9, 30)
REGULAR_END = time(16, 0)
AFTER_HOURS_END = time(20, 0)


class SessionCalendar:
    def __init__(
        self,
        holidays: Optional[Iterable[date]] = None,
        early_close_days: Optional[Iterable[date]] = None,
        early_close_time: time = time(13, 0),
    ) -> None:
        self.holidays = set(holidays or ())
        self.early_close_days = set(early_close_days or ())
        self.early_close_time = early_close_time

    def to_et(self, ts: datetime) -> datetime:
        if ts.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        return ts.astimezone(ET)

    def is_trading_day(self, d: date) -> bool:
        return d.weekday() < 5 and d not in self.holidays

    def regular_end(self, d: date) -> time:
        return self.early_close_time if d in self.early_close_days else REGULAR_END

    def session_at(self, ts: datetime) -> Session:
        et = self.to_et(ts)
        d = et.date()
        if not self.is_trading_day(d):
            return Session.CLOSED
        t = et.time()
        if PREMARKET_START <= t < REGULAR_START:
            return Session.PREMARKET
        if REGULAR_START <= t < self.regular_end(d):
            return Session.REGULAR
        if self.regular_end(d) <= t < AFTER_HOURS_END:
            return Session.AFTER_HOURS
        return Session.CLOSED

    def is_before_open(self, ts: datetime) -> bool:
        return self.to_et(ts).time() < REGULAR_START

    def trading_date(self, ts: datetime) -> date:
        """The trading date a timestamp belongs to (its ET calendar date)."""
        return self.to_et(ts).date()

    def minutes_since_open(self, ts: datetime) -> Optional[float]:
        et = self.to_et(ts)
        if not self.is_trading_day(et.date()):
            return None
        open_dt = et.replace(hour=9, minute=30, second=0, microsecond=0)
        return (et - open_dt).total_seconds() / 60.0
