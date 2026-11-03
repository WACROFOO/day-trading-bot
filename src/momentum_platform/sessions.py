"""US-equity session calendar. All boundaries are America/New_York wall-clock
times, DST-safe via zoneinfo (never a fixed UTC offset).

Premarket 04:00-09:30, regular 09:30-16:00, after-hours 16:00-20:00 ET.
Weekend handling is built in; exchange holidays/early closes are supplied as
data because a hardcoded list rots.
"""

from __future__ import annotations

from datetime import datetime, time, date, timedelta
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


# -- a feed quote: the desk's session, or the night (2026-11-02) -----------------

SESSION_SPAN = timedelta(hours=16)       # 04:00-20:00 ET: pre-market, regular, after-hours
OVERNIGHT_SPAN = timedelta(hours=8)      # 20:00-04:00 ET: IBKR's overnight venue
OVERNIGHT_VENUES = ("OVERNIGHT",)


def quote_parts(now: datetime, start: datetime, *, last: Optional[float] = None,
                print_ts: Optional[datetime] = None, venue: Optional[str] = None,
                bid: Optional[float] = None, ask: Optional[float] = None) -> dict:
    """Split one feed quote between the desk's session and the night.

    The desk's bars, gates and charts cover its session day, 04:00-20:00 ET
    (`start` is that day's 04:00). IBKR's quote keeps moving after 20:00 on its
    OVERNIGHT venue, and on 2026-11-02 at 02:51 ET a trade there (2.17) sat on
    the card beside a gain judged on Friday's last session trade (2.05): two
    prices for one name. So:

      last     the session's when it printed inside the window and not on the
               overnight venue; the night's when it printed after the window,
               on that venue, or in the eight hours before the window; older
               prints belong to neither (an earlier session's close is in the
               bars already)
      bid/ask  the session's while the desk's clock is inside the window, the
               night's outside it

    Returns {"session": {...}, "overnight": {...}} with only the keys that apply."""
    end = start + SESSION_SPAN
    session: dict = {}
    night: dict = {}
    if last is not None:
        ts = print_ts or now
        on_night_venue = (venue or "").upper() in OVERNIGHT_VENUES
        if start <= ts < end and not on_night_venue:
            session.update(last=last, ts=ts)
        elif on_night_venue or ts >= end or start - ts <= OVERNIGHT_SPAN:
            night.update(last=last, ts=ts)
    if bid is not None or ask is not None:
        (session if start <= now < end else night).update(bid=bid, ask=ask)
    return {"session": session, "overnight": night}

