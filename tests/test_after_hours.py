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
    def adopt(self, rows): return 0
    def adopt(self, rows): return 0
    def sync(self): pass


@pytest.fixture
def held(tmp_path):
    """A ledger with one filled, un-exited position."""
    db = tmp_path / "j.sqlite"
    c = L.connect(db)
    build_session(FIXTURE, journal=c)
    c.execute("UPDATE decisions SET verdict='REVIEW' WHERE plan_allowed=1"); c.commit()
    L.set_state(c, phase="B")                  # entries exist from phase B on (review round 2)
    t = FakeTrader()
    r = Runner(c, mode="TRADE", dollar_risk=20.0, trader=t,
               now=lambda: datetime(2026, 9, 1, 13, 52, tzinfo=timezone.utc), max_age_s=3600,
               quote=lambda s: dict(bid=1.0, ask=1.01, bid_size=1, ask_size=1, ts="2026-09-01T13:52:00Z"))
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


def test_ah_exit_takes_an_exit_failed_row_and_refuses_an_exit_pending_one(held):
    """GRML x62 (order #5), 2026-09-22: the hard-stop sell was rejected, the
    row read ExitFailed with the failed sell's exit_ts, and `ah-exit 5` said
    "not a held position". It is held. An ExitPending row stays refused: its
    sell is working and a second one would sell shares that are not held."""
    db, c, t = held
    oid = L.stuck_orders(c)[0]["order_id"]
    L.record_exit(c, oid, reason="hard_stop", price=None, ts="2026-09-01T15:30:00Z",
                  confirmed=False, exit_order_id=901)
    c.commit()
    r = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "ah-exit", str(oid), "--market"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 1 and "not a held position" in r.stdout and "ExitPending" in r.stdout
    L.exit_failed(c, oid, status="Inactive"); c.commit()
    r = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "ah-exit", str(oid), "--market"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 2, r.stdout
    assert "MANUAL_CONFIRMATION_REQUIRED" in r.stdout and "ExitFailed" in r.stdout and "MARKET" in r.stdout
    assert c.execute("SELECT status FROM orders WHERE order_id=?", (oid,)).fetchone()[0] == "ExitFailed"


def test_held_row_is_the_single_definition_of_a_position_the_manual_exit_may_sell():
    sys.path.insert(0, str(ROOT / "scripts"))
    import exercise
    row = lambda **k: {"fill_price": 6.0, "exit_ts": None, "status": "Filled", **k}   # noqa: E731
    assert exercise.held_row(row()) is True
    assert exercise.held_row(row(fill_price=None)) is False
    assert exercise.held_row(row(exit_ts="x", status="Closed")) is False
    assert exercise.held_row(row(exit_ts="x", status="ExitPending")) is False
    assert exercise.held_row(row(exit_ts="x", status="ExitFailed")) is True
    assert exercise.held_row(None) is False


def test_stuck_lists_held_positions(held):
    db, c, t = held
    r = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "stuck"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0 and "filled" in r.stdout


def test_the_report_and_the_review_print_each_trade_with_its_exit_and_r(held):
    """2026-09-22: three trades, and no tool output said how any of them
    ended. TRADES lists entry, exit, reason and planned R per row; a held
    row says HELD; an ExitFailed row says it has no exit."""
    db, c, t = held
    oid = L.stuck_orders(c)[0]["order_id"]
    o = c.execute("SELECT * FROM orders WHERE order_id=?", (oid,)).fetchone()
    rows = L.trade_rows(c)
    assert len(rows) == 1 and rows[0]["closed"] is False and rows[0]["r"] is None
    r = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "review"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0 and "TRADES" in r.stdout and "HELD" in r.stdout, r.stdout[-800:]
    L.record_exit(c, oid, reason="hard_stop", price=None, ts="2026-09-01T15:30:00Z", confirmed=False, exit_order_id=901)
    L.exit_failed(c, oid, status="Inactive"); c.commit()
    assert L.trade_rows(c)[0]["closed"] is False
    exit_px = round(o["fill_price"] + 2 * (o["fill_price"] - o["stop"]), 2)      # a +2R exit
    L.record_exit(c, oid, reason="manual_market", price=exit_px, ts="2026-09-01T15:40:00Z",
                  confirmed_by="ayman", confirmed=True); c.commit()
    row = L.trade_rows(c)[0]
    assert row["closed"] is True and abs(row["r"] - 2.0) < 0.06, row
    assert row["pnl"] == round((exit_px - o["fill_price"]) * row["qty"], 2)
    r = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "report"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    assert "TRADES" in r.stdout and "1 closed" in r.stdout and "manual_market" in r.stdout and "1 won" in r.stdout


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


def test_a_defect_exit_stays_in_pnl_and_leaves_the_a3_kill_rule(held):
    """Owner decision 2026-09-22: DCOY's and GRML's exits were defects'. They
    keep their R everywhere; the kill rule is read on clean fills only and
    is read-only below ten of them."""
    from journal import controls, bars
    db, c, t = held
    oid = L.stuck_orders(c)[0]["order_id"]
    o = c.execute("SELECT * FROM orders WHERE order_id=?", (oid,)).fetchone()
    L.record_exit(c, oid, reason="trail", price=round(o["fill_price"] + 0.5 * (o["fill_price"] - o["stop"]), 2),
                  ts="2026-09-01T14:20:00Z"); c.commit()
    k = controls.kill_rule_read(c, bars.from_ledger(c))
    assert len(k["rows"]) == 1 and k["verdict"] == "READ-ONLY" and k["excluded_defect"] == 0
    r = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "defect", str(oid),
                        "--note", "stop killed by an OCA modify; exit at the restart price"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 2 and "would mark" in r.stdout
    assert c.execute("SELECT defect_note FROM orders WHERE order_id=?", (oid,)).fetchone()[0] is None
    r = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "defect", str(oid),
                        "--note", "stop killed by an OCA modify; exit at the restart price", "--confirm"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0 and "marked" in r.stdout, r.stdout
    c2 = L.connect(db)
    note = c2.execute("SELECT defect_note FROM orders WHERE order_id=?", (oid,)).fetchone()[0]
    assert "OCA modify" in note and "marked by" in note
    assert len(L.trade_rows(c2)) == 1 and L.trade_rows(c2)[0]["closed"] is True      # still in P&L
    k = controls.kill_rule_read(c2, bars.from_ledger(c2))
    assert k["rows"] == [] and k["excluded_defect"] == 1 and k["verdict"] == "READ-ONLY"
    rv = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "review"],
                        cwd=ROOT, capture_output=True, text=True)
    assert rv.returncode == 0 and "A3 KILL RULE" in rv.stdout and "1 defect exit(s) excluded" in rv.stdout


def test_the_kill_rule_binds_only_from_ten_clean_fills():
    from journal import controls
    c = L.connect(":memory:")
    build_session(FIXTURE, journal=c)
    did = L.decisions(c, plan_allowed=1)[0]["decision_id"]
    for i in range(10):
        oid = L.record_order(c, did, symbol="ABCD", account="DU1", session="regular", parent_id=100 + i,
                             stop_id=200 + i, target_id=None, trigger=7.2, stop=7.05, target=None,
                             shares=100, dollar_risk=15.0, protected=True)
        L.record_fill(c, oid, fill_price=7.2, fill_ts=f"2026-09-01T14:{i:02d}:00Z")
        L.record_exit(c, oid, reason="stop", price=7.05, ts=f"2026-09-01T14:{i:02d}:30Z")   # -1 R each, live
    c.commit()
    k = controls.kill_rule_read(c, {}, min_n=10)
    # every fill carries the same decision; its actuals decide the baseline
    if k["n"] >= 10:
        assert k["verdict"] in ("MET", "NOT MET")
        assert (k["verdict"] == "MET") == (k["live_mean"] < k["baseline_mean"])
    else:
        assert k["verdict"] == "READ-ONLY"
    assert controls.kill_rule_read(c, {}, min_n=11)["verdict"] == "READ-ONLY"
