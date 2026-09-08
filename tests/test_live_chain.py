"""The LIVE code path — IbkrDesk → session builder → journal → runner — driven
by the fake broker. The fixture tests exercise the replay path; today's
first live run exercised this one for real and found things the fixture
could not. This locks the live path in.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "tests"))

from fake_ibkr import FakeIB, FakeTicker, day_bars  # noqa: E402
from momentum_platform.dashboard import ibkr_desk as desk_mod  # noqa: E402
from momentum_platform.dashboard.ibkr_desk import IbkrDesk  # noqa: E402
from journal import ledger as L  # noqa: E402
from execution.runner import Runner  # noqa: E402

T0 = datetime(2026, 9, 8, 14, 0, tzinfo=timezone.utc)      # Tue 10:00 ET


def pullback_minutes(start: datetime):
    """Two green impulse bars (+3%), two lighter red pullback bars, then a
    bar that breaks the prior bar's high — the detector's arming shape."""
    p = 4.00
    bars = [
        (start + timedelta(minutes=0), p,      p + .07, p - .01, p + .06, 9000),   # impulse
        (start + timedelta(minutes=1), p + .06, p + .13, p + .05, p + .12, 9500),  # impulse (+3%)
        (start + timedelta(minutes=2), p + .12, p + .12, p + .08, p + .09, 3000),  # pullback, light
        (start + timedelta(minutes=3), p + .09, p + .10, p + .07, p + .08, 2500),  # pullback, light
        (start + timedelta(minutes=4), p + .08, p + .14, p + .08, p + .13, 8000),  # trigger > prior high
    ]
    return bars


@pytest.fixture
def live(tmp_path, monkeypatch):
    db = tmp_path / "j.sqlite"
    monkeypatch.setenv("JOURNAL_DB", str(db))
    monkeypatch.setattr(desk_mod, "_JOURNAL", None)         # fresh connection per test
    monkeypatch.setenv("FLOAT_OVERRIDES", str(tmp_path / "floats.json"))
    (tmp_path / "floats.json").write_text(json.dumps(
        {"date": "2026-09-08", "source": "finviz via premarket_stars.py", "floats": {"AAA": 6_000_000}}))
    start = T0 - timedelta(minutes=5)
    ib = FakeIB(daily={"AAA": day_bars(30, 3.0, today="2026-09-08")},
                minutes={"AAA": pullback_minutes(start)},
                quotes={"AAA": FakeTicker(last=4.13, close=3.00, bid=4.12, ask=4.14)})
    clock = lambda: T0  # noqa: E731
    desk = IbkrDesk(["AAA"], ib_factory=lambda: ib, clock=clock, headlines=False, sec=False, rescan=0)
    desk.log = lambda m: None
    # This desk was "up" before the tape it is fed: the fixture's minute bars
    # stand for bars watched live, not history loaded at start. A start time
    # after them would (correctly) tag every decision as backfill.
    desk._started = start - timedelta(minutes=1)
    desk._bootstrap()
    desk.refresh_session()
    yield {"desk": desk, "ib": ib, "db": db, "conn": L.connect(db)}
    desk.stop()


def test_the_live_desk_journals_tape_quotes_and_board(live):
    c = live["conn"]
    assert c.execute("SELECT COUNT(*) FROM bars WHERE symbol='AAA'").fetchone()[0] >= 5
    q = c.execute("SELECT bid, ask FROM quotes WHERE symbol='AAA'").fetchone()
    assert q["bid"] == 4.12 and q["ask"] == 4.14           # the stream quote, not a bar's
    board = c.execute("SELECT symbol, verdict FROM board_snapshots").fetchall()
    assert [b["symbol"] for b in board] == ["AAA"]


def test_the_gap_scan_float_overrides_the_shares_outstanding_bound(live):
    ref = live["desk"].current()["symbols"]["AAA"]
    assert ref["floatShares"] == 6_000_000
    assert ref["floatQuality"] == "verified"
    assert "finviz" in ref["floatSource"]


def test_a_live_pullback_becomes_a_decision_with_the_live_quote(live):
    c = live["conn"]
    rows = L.decisions(c)
    assert rows, "the arming shape must produce a decision on the live path"
    d = rows[-1]
    assert d["symbol"] == "AAA" and d["source_name"].startswith("IBKR")
    assert d["data_status"] == "live"
    assert d["trigger"] > d["stop"] > 0
    assert d["bid"] is not None and d["ask"] is not None      # point-in-time quote on the row
    assert d["verdict"] in ("REVIEW", "WAIT", "WATCH", "REJECT")


def test_the_runner_acts_on_the_live_decision_in_log_only(live):
    c = live["conn"]
    done = Runner(c, mode="LOG_ONLY", dollar_risk=20.0).step()
    allowed = [r for r in L.decisions(c) if r["plan_allowed"]]
    assert len(done) == len(allowed)
    assert all(a.outcome in ("LOG_ONLY", "REFUSED") for a in done)


def test_a_stale_live_feed_arms_nothing_and_says_stale(live, tmp_path):
    desk, c = live["desk"], live["conn"]
    before = c.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
    desk.stream.health.state = "STALE"
    session = desk.refresh_session()
    assert session["dataStatus"] == "stale"
    assert session["plans"] == []
    assert {v["verdict"] for v in session["cascade"].values()} == {"STALE"}
    # the journal did not gain a fresh PENDING decision from a stale tape
    assert c.execute("SELECT COUNT(*) FROM decisions WHERE outcome='PENDING'").fetchone()[0] \
        <= c.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] - 0
    assert c.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] >= before


def test_a_float_file_from_another_day_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOAT_OVERRIDES", str(tmp_path / "old.json"))
    (tmp_path / "old.json").write_text(json.dumps({"date": "2026-09-07", "floats": {"AAA": 6e6}}))
    assert desk_mod._float_override("AAA", "2026-09-08") is None
    (tmp_path / "old.json").write_text(json.dumps({"date": "2026-09-08", "floats": {"AAA": 6e6}}))
    assert desk_mod._float_override("AAA", "2026-09-08")["float"] == 6e6



def test_a_log_only_day_never_reaches_an_order_function(live, monkeypatch):
    """Audit 2026-09-08 F6: the runner's mode alone does not prove the day is
    order-free. Give the fake broker an order surface that explodes, then run
    the whole observational loop — desk rebuild, runner step, fill sync,
    monitored stop, after-hours flag, end of day — and expect silence."""
    def boom(*a, **k):
        raise AssertionError("ORDER PATH REACHED in a LOG_ONLY day")
    for name in ("placeOrder", "cancelOrder", "bracketOrder", "whatIfOrder"):
        monkeypatch.setattr(type(live["ib"]), name, boom, raising=False)
    live["desk"].refresh_session()
    r = Runner(live["conn"], mode="LOG_ONLY", dollar_risk=20.0)
    assert L.decisions(live["conn"]), "the fixture arms a plan on the live path"
    acted = r.step()                                   # whatever is pending is judged, never sent
    assert all(a.outcome in ("LOG_ONLY", "REFUSED") for a in acted)
    assert r.sync_fills() == 0 and r.watch_stops() == [] and r.flag_after_hours() == [] and r.end_of_day() == []
    assert live["conn"].execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
