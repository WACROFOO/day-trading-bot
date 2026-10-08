"""The market's closed days are data with a reason, and the day command
refuses to start on them."""
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from momentum_platform.holidays import is_trading_day, nyse_calendar, why_closed  # noqa: E402


def test_labor_day_2026_is_closed_and_the_next_day_is_open():
    assert why_closed(date(2026, 9, 7)) == "NYSE holiday"
    assert is_trading_day(date(2026, 9, 7)) is False
    assert is_trading_day(date(2026, 9, 8)) is True and why_closed(date(2026, 9, 8)) is None
    assert why_closed(date(2026, 9, 6)) == "weekend"


def test_early_closes_are_1300():
    from datetime import time
    cal = nyse_calendar()
    assert cal.regular_end(date(2026, 11, 27)) == time(13, 0)
    assert cal.regular_end(date(2026, 11, 30)) == time(16, 0)


def test_the_day_command_names_the_closure_and_never_starts_the_bot(tmp_path, monkeypatch, capsys):
    """Frozen to 2026-09-07 07:30 ET. On the real day the chain ran all
    morning on a stale feed and nothing said why. Since 2026-10-08 the desk
    comes up on a closed day too (the owner's platform at any hour), alone:
    no runner, and it writes nothing to the exercise ledger."""
    src = (ROOT / "scripts/day.py").read_text()
    assert "why_closed(now.date())" in src
    # exercise the branch directly
    sys.path.insert(0, str(ROOT / "scripts"))
    import day
    from datetime import datetime
    from zoneinfo import ZoneInfo
    frozen = datetime(2026, 9, 7, 7, 30, tzinfo=ZoneInfo("America/New_York"))

    class FrozenDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen if tz else frozen.replace(tzinfo=None)
    monkeypatch.setattr(day, "datetime", FrozenDT)
    monkeypatch.setattr(day, "DB", tmp_path / "j.sqlite")
    monkeypatch.setattr(day, "DAY_LOCK", tmp_path / "j.sqlite.day.lock")
    monkeypatch.setenv("IBKR_PORT", "4002")             # no port probing from a test
    started = []
    monkeypatch.setattr(day, "start_desk", lambda *a, **k: started.append(("desk", k.get("record_until"))))
    monkeypatch.setattr(day, "start_runner", lambda *a, **k: started.append("runner"))
    assert day.main([]) == 0
    assert started == [("desk", "0")], "the desk alone, writing nothing; never the runner"
    assert "NYSE holiday — the market is closed; the bot does not run today" in capsys.readouterr().out
