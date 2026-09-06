"""The ledger records what was knowable, keeps outcomes apart from it, and
never records the same decision twice.

Everything here runs on an in-memory SQLite with hand-built objects; no
desk, no broker.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from journal import ledger as L  # noqa: E402
from momentum_platform.cascade import Inputs, evaluate  # noqa: E402


def good_inputs(**over) -> Inputs:
    base = dict(symbol="TEST", last=6.00, prev_close=4.00, change_pct=50.0,
                session_high=6.20, float_shares=4_000_000, float_verified=True,
                catalyst_today=True, is_fund_or_etf=False, tick_size=0.01,
                above_vwap=True, above_ema9=True, macd_positive_and_above_signal=True,
                session_volume=3_000_000, rvol=8.0)
    base.update(over)
    return Inputs(**base)


PLAN = NS(entry=6.05, stop=5.90, target=6.35, risk_share=0.15, reward_multiple=2.0,
          pullback_candles=3, volume_ok=True)
SNAP = dict(last=6.00, bid=5.99, ask=6.01, session_high=6.20, volume=3e6, rvol=8.0,
            change_pct=50.0)
ARMED = "2026-09-08T14:05:00Z"          # 10:05 ET, Tuesday


@pytest.fixture
def conn():
    c = L.connect(":memory:")
    yield c
    c.close()


def record(conn, inputs=None, **over):
    inputs = inputs or good_inputs()
    res = evaluate(inputs)
    kw = dict(symbol="TEST", armed_at=ARMED, plan=PLAN, cascade=res, inputs=inputs,
              snapshot=SNAP, session=L.session_of(ARMED), session_id="t",
              source_name="fixture", data_status="replay")
    kw.update(over)
    return L.record_decision(conn, **kw), res


# ------------------------------------------------------------ identity
def test_the_same_plan_is_one_decision_no_matter_how_often_the_desk_rebuilds(conn):
    """The live desk rebuilds every few seconds and the detector's plan_id is
    a fresh uuid each time. Keyed on uuid, one morning is hundreds of rows."""
    a, _ = record(conn)
    b, _ = record(conn)
    assert a == b
    assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 1


def test_a_different_stop_is_a_different_decision(conn):
    a, _ = record(conn)
    b, _ = record(conn, plan=NS(**{**vars(PLAN), "stop": 5.85}))
    assert a != b


def test_timestamps_are_stored_in_et_never_local(conn):
    did, _ = record(conn)
    row = conn.execute("SELECT ts_et, session FROM decisions").fetchone()
    assert row["ts_et"].startswith("2026-09-08T10:05:00")
    assert row["ts_et"].endswith("-04:00")
    assert row["session"] == "regular"


# --------------------------------------------------------- point in time
def test_the_row_carries_what_was_knowable_and_the_full_inputs_for_replay(conn):
    did, res = record(conn)
    row = conn.execute("SELECT * FROM decisions").fetchone()
    assert row["last"] == 6.00 and row["bid"] == 5.99 and row["ask"] == 6.01
    assert row["verdict"] == res.verdict.value
    stored = json.loads(row["inputs_json"])
    assert stored["float_shares"] == 4_000_000 and stored["last"] == 6.00
    gates = json.loads(row["gates_json"])
    assert {g["id"] for g in gates} >= {"price", "float", "catalyst"}


def test_a_killed_plan_is_recorded_as_suppressed_not_dropped(conn):
    """Suppressed plans are counted, never silently absent — the desk must be
    able to say why it shows no plans."""
    did, res = record(conn, inputs=good_inputs(last=1.69))
    row = conn.execute("SELECT outcome, killed_by, plan_allowed FROM decisions").fetchone()
    assert res.plan_allowed is False
    assert row["outcome"] == "SUPPRESSED" and row["killed_by"] == "price"
    assert row["plan_allowed"] == 0


def test_an_allowed_plan_starts_pending_and_shows_up_for_the_runner(conn):
    did, _ = record(conn)
    assert [r["decision_id"] for r in L.pending(conn)] == [did]


# ---------------------------------------------------- outcomes stay apart
def test_outcome_is_about_the_runner_and_actuals_are_about_the_market(conn):
    did, _ = record(conn)
    L.set_outcome(conn, did, "REFUSED", ["cascade forbids a plan"])
    row = conn.execute("SELECT * FROM decisions").fetchone()
    assert row["outcome"] == "REFUSED"
    assert json.loads(row["refusal_reasons_json"]) == ["cascade forbids a plan"]
    # the market-facing columns did not move
    assert row["last"] == 6.00 and row["verdict"] == "REVIEW"
    assert conn.execute("SELECT COUNT(*) FROM actuals").fetchone()[0] == 0


def test_an_unknown_outcome_is_rejected(conn):
    did, _ = record(conn)
    with pytest.raises(ValueError):
        L.set_outcome(conn, did, "ARMED")


# ------------------------------------------------ both R denominators, NBBO
def test_a_fill_records_realised_risk_and_the_nbbo_in_one_write(conn):
    did, _ = record(conn)
    oid = L.record_order(conn, did, account="DUR339781", session="regular",
                         parent_id=4, stop_id=5, target_id=None,
                         trigger=6.05, stop=5.90, target=None, shares=100,
                         dollar_risk=15.0, protected=True)
    o = conn.execute("SELECT * FROM orders").fetchone()
    assert o["planned_risk"] == 15.0 and o["fill_price"] is None

    L.record_fill(conn, oid, fill_price=6.12, fill_ts="2026-09-08T14:06:03Z",
                  nbbo=dict(bid=6.10, ask=6.13, bid_size=200, ask_size=100,
                            ts="2026-09-08T14:06:03Z"))
    o = conn.execute("SELECT * FROM orders").fetchone()
    assert o["realised_risk"] == 22.0            # (6.12 - 5.90) * 100
    assert o["slippage_ratio"] == pytest.approx(22.0 / 15.0, abs=1e-4)
    assert o["nbbo_bid"] == 6.10 and o["nbbo_ask_size"] == 100
    assert o["fill_ts"].startswith("2026-09-08T10:06:03")


def test_the_funnel_reports_every_stage_with_its_denominator(conn):
    record(conn)
    record(conn, inputs=good_inputs(last=1.69), symbol="DEAD",
           plan=NS(**{**vars(PLAN), "entry": 1.75, "stop": 1.71}))
    L.record_board(conn, ARMED, "t", [
        dict(symbol="TEST", verdict="REVIEW", killed_by=None, plan_allowed=True, last=6.0),
        dict(symbol="DEAD", verdict="REJECT", killed_by="price", plan_allowed=False, last=1.69),
        dict(symbol="MEH", verdict="WAIT", killed_by=None, plan_allowed=True, last=3.0),
    ])
    f = L.funnel(conn)
    assert f["board_symbols"] == 3 and f["board_plan_allowed"] == 2
    assert f["plans_armed"] == 2 and f["plans_suppressed"] == 1 and f["plans_allowed"] == 1
    assert f["taken"] == 0 and f["orders"] == 0


def test_board_snapshots_dedupe_per_bar_per_symbol(conn):
    rows = [dict(symbol="TEST", verdict="REVIEW", killed_by=None, plan_allowed=True, last=6.0)]
    assert L.record_board(conn, ARMED, "t", rows) == 1
    assert L.record_board(conn, ARMED, "t", rows) == 0


def test_halts_are_recorded_with_the_price_before(conn):
    L.record_halt(conn, ARMED, "TEST", "halted", 6.00)
    L.record_halt(conn, ARMED, "TEST", "halted", 6.00)          # repeat: no-op
    assert conn.execute("SELECT COUNT(*) FROM halts").fetchone()[0] == 1


# ------------------------------------------------------------ boundaries
def test_session_of_matches_the_desk_calendar():
    assert L.session_of("2026-09-08T11:00:00Z") == "premarket"     # 07:00 ET
    assert L.session_of("2026-09-08T13:29:00Z") == "premarket"     # 09:29
    assert L.session_of("2026-09-08T13:30:00Z") == "regular"       # 09:30
    assert L.session_of("2026-09-08T20:00:00Z") == "none"          # 16:00
    assert L.session_of("2026-09-08T10:59:00Z") == "none"          # 06:59
    assert L.session_of("2026-09-06T14:00:00Z") == "none"          # Sunday
