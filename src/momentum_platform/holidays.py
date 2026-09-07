"""NYSE full-day closes and early closes, as data.

`sessions.SessionCalendar` deliberately takes holidays as input because a
hard-coded list rots. This module IS that input for the dates the exercise
runs through, and it is data with a provenance note, not a rule.

Source of the dates: the exchange's standard holiday rules (Labor Day is the
first Monday of September; Thanksgiving the fourth Thursday of November;
Christmas 25 December, observed on the nearest weekday; the day after
Thanksgiving and 24 December close at 13:00). VERIFY against the exchange's
published calendar before relying on a date near a year boundary — the
observed-day rules for New Year's Day and Independence Day shift.

2026-09-07 (Labor Day) is here because the first live run of scripts/day.py
happened on it: the whole chain ran, the feed was correctly STALE all
morning, and nothing said "the market is closed today".
"""

from __future__ import annotations

from datetime import date

from .sessions import SessionCalendar

FULL_CLOSE_2026 = (
    date(2026, 1, 1),    # New Year's Day
    date(2026, 1, 19),   # Martin Luther King Jr. Day
    date(2026, 2, 16),   # Presidents' Day
    date(2026, 4, 3),    # Good Friday
    date(2026, 5, 25),   # Memorial Day
    date(2026, 6, 19),   # Juneteenth
    date(2026, 7, 3),    # Independence Day, observed (4 July is a Saturday)
    date(2026, 9, 7),    # Labor Day
    date(2026, 11, 26),  # Thanksgiving
    date(2026, 12, 25),  # Christmas
)

EARLY_CLOSE_2026 = (
    date(2026, 11, 27),  # day after Thanksgiving, 13:00
    date(2026, 12, 24),  # Christmas Eve, 13:00
)


def nyse_calendar() -> SessionCalendar:
    return SessionCalendar(holidays=FULL_CLOSE_2026, early_close_days=EARLY_CLOSE_2026)


def is_trading_day(d: date) -> bool:
    return nyse_calendar().is_trading_day(d)


def why_closed(d: date) -> str | None:
    """A one-line reason when the market is closed on `d`, else None."""
    if d.weekday() >= 5:
        return "weekend"
    if d in FULL_CLOSE_2026:
        return "NYSE holiday"
    return None
