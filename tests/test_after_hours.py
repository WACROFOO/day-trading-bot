"""Brief R10: after 16:00 a held position is flagged for a human and never
sold by the runner. The exit is a separate, confirmed command that records
who confirmed it."""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from execution.intent import PlacedOrder  # noqa: E402
from execution.runner import Runner  # noqa: E402
from journal import ledger as L  # noqa: E402
from momentum_platform.dashboard.session_builder import build_session  # noqa: E402

FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"


class FakeTrader:
    account = "DUR339781"
    def __init__(self): self.placed, self.exits = [], []
    def place_bracket(self, intent, now=None):
        n = len(self.placed)
        rec = PlacedOrder(symbol=intent.symbol, parent_id=100 + n, stop_id=200 + n,
                          trigger=intent.trigger, stop=intent.stop, shares=intent.shares,
                          protected=True)
        self.placed.append(rec); return rec
    def exit_limit(self, *a, **k): self.exits.append(a); return 1.0
    def sync(self): pass


@pytest.fixture
def held(tmp_path):
    """A ledger with one filled, un-exited position."""
    db = tmp_path / "j.sqlite"
    c = L.connect(db)
    build_session(FIXTURE, journal=c)
    t = FakeTrader()
    r = Runner(c, mode="TRADE", dollar_risk=20.0, trader=t,
               now=lambda: datetime(2026, 9, 1, 13, 52, tzinfo=timezone.utc), max_age_s=3600)
    r.step()
    t.placed[0].fill_price = t.placed[0].trigger; t.placed[0].fill_time = "2026-09-01T13:52:05Z"
    r.sync_fills()
    return db, c, t


def test_before_the_close_nothing_is_flagged(held):
    db, c, t = held
    r = Runner(c, mode="TRADE", dollar_risk=20.0, trader=t,
               now=lambda: datetime(2026, 9, 1, 19, 59, tzinfo=timezone.utc))   # 15:59 ET
    assert r.flag_after_hours() == []
    assert not any(o["stop_status"] == L.MANUAL for o in L.stuck_orders(c))


def test_after_the_close_a_held_position_is_flagged_and_never_sold(held):
    db, c, t = held
    r = Runner(c, mode="TRADE", dollar_risk=20.0, trader=t,
               now=lambda: datetime(2026, 9, 1, 20, 1, tzinfo=timezone.utc))    # 16:01 ET
    flagged = r.flag_after_hours()
    assert len(flagged) >= 1
    assert t.exits == []                                    # the runner did not sell
    o = c.execute("SELECT stop_status FROM orders WHERE order_id=?", (flagged[0],)).fetchone()
    assert o["stop_status"] == L.MANUAL
    ev = c.execute("SELECT text FROM order_events WHERE order_id=?", (flagged[0],)).fetchall()
    assert len(ev) == 1 and "ah-exit" in ev[0][0]
    assert r.flag_after_hours() == flagged                   # idempotent: one event, same ids
    assert len(c.execute("SELECT * FROM order_events WHERE order_id=?", (flagged[0],)).fetchall()) == 1


def test_flagging_is_inert_in_log_only(held):
    db, c, t = held
    assert Runner(c, mode="LOG_ONLY", dollar_risk=20.0,
                  now=lambda: datetime(2026, 9, 1, 20, 1, tzinfo=timezone.utc)).flag_after_hours() == []


def test_ah_exit_without_confirm_refuses_and_explains(held):
    db, c, t = held
    oid = L.stuck_orders(c)[0]["order_id"]
    r = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "ah-exit", str(oid)],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 2
    assert "MANUAL_CONFIRMATION_REQUIRED" in r.stdout and "--confirm" in r.stdout
    assert c.execute("SELECT exit_ts FROM orders WHERE order_id=?", (oid,)).fetchone()[0] is None


def test_ah_exit_with_confirm_needs_a_fresh_quote_before_touching_the_broker(held):
    db, c, t = held
    oid = L.stuck_orders(c)[0]["order_id"]
    c.execute("UPDATE quotes SET recorded_at='2026-01-01T00:00:00+00:00'"); c.commit()
    r = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "ah-exit", str(oid), "--confirm"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 1 and "no fresh quote" in r.stdout


def test_stuck_lists_held_positions(held):
    db, c, t = held
    r = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "stuck"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0 and "filled" in r.stdout


def test_a_confirmed_exit_records_who_confirmed():
    c = L.connect(":memory:")
    build_session(FIXTURE, journal=c)
    did = L.decisions(c, plan_allowed=1)[0]["decision_id"]
    oid = L.record_order(c, did, symbol="ABCD", account="DU1", session="regular", parent_id=1,
                         stop_id=2, target_id=None, trigger=7.2, stop=7.05, target=None,
                         shares=100, dollar_risk=15.0, protected=True)
    L.record_fill(c, oid, fill_price=7.21, fill_ts="2026-09-01T14:00:00Z")
    L.record_exit(c, oid, reason="AH_exception", price=7.00, ts="2026-09-01T20:05:00Z",
                  confirmed_by="ayman")
    o = c.execute("SELECT * FROM orders WHERE order_id=?", (oid,)).fetchone()
    assert o["exit_reason"] == "AH_exception" and o["exit_confirmed_by"] == "ayman"
    assert o["exit_ts"].startswith("2026-09-01T16:05")
    assert L.stuck_orders(c) == []
