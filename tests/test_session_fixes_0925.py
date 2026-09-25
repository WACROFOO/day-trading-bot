"""2026-09-25: a name IBKR refuses data for stays off the stream, the history
refresh backs off when the farm times out, Ctrl-C ends the day, the day
waits for the Gateway, and stop slippage is measured on every stop exit."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "tests"))

import day  # noqa: E402
from journal import ledger as L  # noqa: E402
from momentum_platform.dashboard import ibkr_desk as D  # noqa: E402
from test_ibkr_desk import make_desk  # noqa: E402


def test_a_name_without_data_permission_is_banned_from_the_stream_for_good():
    desk, ib, clock = make_desk()
    desk._bootstrap()
    assert "AAA" in desk.symbols and "AAA" in desk.stream.symbols
    # IBKR answers 420 for AAA (no AMEX permission) — as it did for APUS while subscribe() was still running
    desk._on_tws_error(8, 420, "Invalid Real-time Query:No market data permissions for AMEX STK",
                       SimpleNamespace(symbol="AAA"))
    assert "AAA" in desk.no_live_data and "AAA" not in desk.symbols and "AAA" not in desk.stream.symbols
    assert "AAA" in desk.stream.banned
    # a later subscribe (the "connection restored" resubscribe, a desk restart's watchlist) does not bring it back
    assert desk.stream.subscribe(["AAA"]) == [] and "AAA" not in desk.stream.symbols
    assert desk.stream.resubscribe_all() == ["BBB"] or "AAA" not in desk.stream.symbols


def test_history_refresh_backs_off_after_three_timeouts(monkeypatch):
    desk, ib, clock = make_desk()
    desk._bootstrap()
    desk._profile_day = {s: desk.session_day() for s in desk.symbols}           # profiles done: the turn goes to minutes
    logs = []; desk.log = logs.append
    ticks = iter([0.0, 20.0, 100.0, 120.0, 200.0, 220.0, 300.0, 300.0, 300.0])   # each refresh "takes" 20 s
    monkeypatch.setattr(D.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(D, "minute_records", lambda *a, **k: [])                 # the farm returns nothing
    desk._next_history = 0.0
    desk.refresh_history(); desk.refresh_history()
    assert desk._next_history == 0.0 and not any("timed out" in x for x in logs)  # two slow refreshes: no backoff yet
    desk.refresh_history()
    assert desk._next_history == 300.0 + D.HISTORY_BACKOFF_S                     # the third pauses the refresh
    assert any("timed out" in x and "paused" in x for x in logs)
    # a fast, empty refresh (a quiet name) is not a timeout
    desk2, ib2, _ = make_desk(); desk2._bootstrap(); desk2._next_history = 0.0
    desk2._profile_day = {s: desk2.session_day() for s in desk2.symbols}
    t2 = iter([0.0, 0.5, 1.0, 1.5, 2.0, 2.5])
    monkeypatch.setattr(D.time, "monotonic", lambda: next(t2))
    for _ in range(3):
        desk2.refresh_history()
    assert desk2._next_history == 0.0


def test_ctrl_c_flag_and_gateway_wait_exist_on_the_day_command():
    assert "requested" in day.STOP and isinstance(day.STOP["requested"], bool)   # set by the SIGINT handler, read by the loop
    assert day.wait_for_gateway("127.0.0.1", "4002", 0.0, sleep=lambda s: None,
                                connect=lambda addr, timeout=2: (_ for _ in ()).throw(OSError())) is False


def test_trade_rows_measure_stop_slippage_and_the_tapes_range_at_entry():
    from momentum_platform.dashboard.session_builder import build_session
    FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c)
    did = L.decisions(c, plan_allowed=1)[0]["decision_id"]
    # thirty 1-minute bars before the fill with a 0.10 range, one outlier
    t0 = datetime(2026, 9, 25, 14, 0, tzinfo=timezone.utc)
    bars = [((t0 + timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:%SZ"), 16.0, 16.10, 16.00, 16.05, 1000) for i in range(29)]
    bars.append(((t0 + timedelta(minutes=29)).strftime("%Y-%m-%dT%H:%M:%SZ"), 16.0, 16.90, 16.00, 16.5, 1000))
    L.record_bars(c, {"GRML": bars}); c.commit()
    oid = L.record_order(c, did, symbol="GRML", account="DU1", session="regular", parent_id=900, stop_id=901,
                         target_id=None, trigger=16.39, stop=16.11, target=None, shares=71, dollar_risk=20.0, protected=True)
    L.record_fill(c, oid, fill_price=16.44, fill_ts="2026-09-25T14:28:10Z")
    c.execute("UPDATE orders SET trail_stop=16.22 WHERE order_id=?", (oid,))
    L.record_exit(c, oid, reason="trail", price=15.99, ts="2026-09-25T14:30:24Z")
    (row,) = L.trade_rows(c)
    assert row["stop_slip"] == -0.23                      # filled 0.23 under the 16.22 trail level
    assert row["stop_slip_r"] == -0.82                    # 0.23 / 0.28 planned risk per share
    assert row["range30"] == 0.1                          # the median ignores the one wide bar
    assert row["r"] == -1.61
    # a target exit carries no stop slippage
    c.execute("UPDATE orders SET exit_reason='target' WHERE order_id=?", (oid,))
    assert L.trade_rows(c)[0]["stop_slip"] is None
    assert L.median_range_before(c, "GRML", "2026-09-25T14:03:00Z") is None     # fewer than 5 bars: no number
