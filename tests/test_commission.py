"""IBKR's commission, recorded per side and shown as net R (2026-10-06).

The fill prices already carry the spread and the slippage; the commission is
the one cost they do not, and until now no ledger column held it, so every
report read "planned R, no costs"."""
from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

from execution.ibkr_trader import _commission  # noqa: E402
from execution.intent import PlacedOrder  # noqa: E402
from execution.runner import Runner  # noqa: E402
from journal import ledger as L  # noqa: E402

import test_real_trader_path as RT  # noqa: E402
from test_real_trader_path import trader  # noqa: E402,F401  (the fixture)


def _fill(commission, exec_id="e1"):
    return types.SimpleNamespace(commissionReport=types.SimpleNamespace(execId=exec_id, commission=commission))


def _trade(*fills):
    return types.SimpleNamespace(fills=list(fills))


# ------------------------------------------------------------------ reading the report
def test_commission_sums_every_execution():
    assert _commission([_trade(_fill(1.00), _fill(0.35, "e2"))]) == 1.35
    assert _commission([_trade(_fill(1.00)), _trade(_fill(1.00, "e3"))]) == 2.00


def test_no_execution_is_no_commission_not_zero():
    assert _commission([_trade()]) is None
    assert _commission([]) is None


def test_a_report_not_yet_arrived_withholds_the_whole_side():
    """ib_async keeps a blank report (execId '') until IBKR sends one; a partial
    sum would read as the whole cost."""
    assert _commission([_trade(_fill(1.00), _fill(0.0, exec_id=""))]) is None
    assert _commission([_trade(_fill(1.7976931348623157e308))]) is None, "UNSET_DOUBLE is not a commission"


def test_sync_reads_both_sides(trader):
    rth = datetime(2026, 9, 8, 10, 15, tzinfo=ZoneInfo("America/New_York"))
    rec = trader.place_bracket(RT.intent(), now=rth)
    by_id = {t.order.orderId: t for t in trader.ib.placed}
    by_id[rec.parent_id].orderStatus = RT._Status("Filled", 5.02)
    by_id[rec.parent_id].fills = [_fill(1.00, "in1")]
    trader.sync()
    assert rec.commission_in == 1.00 and rec.commission_out is None
    by_id[rec.stop_id].orderStatus = RT._Status("Filled", 4.79)
    by_id[rec.stop_id].fills = [_fill(0.60, "out1"), _fill(0.40, "out2")]
    trader.sync()
    assert rec.exit_price == 4.79 and rec.commission_out == 1.00


# ------------------------------------------------------------------ the ledger
def _closed(conn, *, fill=5.00, exit_=4.78, shares=200, c_in=None, c_out=None):
    conn.execute("""INSERT INTO decisions (decision_id, ts_et, session, symbol, source, verdict, killed_by,
                    plan_allowed, gates_json, warnings_json, inputs_json, recorded_at)
                    VALUES ('d1', '2026-10-06T09:40:00-04:00', 'regular', 'T', 'pullback', 'REVIEW', NULL, 1,
                            '[]', '[]', '{}', 'x')""")
    oid = L.record_order(conn, "d1", symbol="T", account="DUR339781", session="regular", parent_id=11,
                         stop_id=12, target_id=None, trigger=5.00, stop=4.80, target=None, shares=shares,
                         dollar_risk=40.0, protected=True)
    L.record_fill(conn, oid, fill_price=fill, fill_ts="2026-10-06T13:41:00Z")
    L.record_exit(conn, oid, reason="stop", price=exit_, ts="2026-10-06T13:45:00Z")
    if c_in is not None or c_out is not None:
        L.set_commissions(conn, oid, commission_in=c_in, commission_out=c_out)
    return oid


def test_net_r_needs_both_sides():
    c = L.connect(":memory:")
    oid = _closed(c, c_in=1.00)
    row = L.trade_rows(c)[0]
    assert row["r"] == -1.10 and row["commission"] is None and row["net_r"] is None
    assert L.set_commissions(c, oid, commission_out=1.00) is True
    row = L.trade_rows(c)[0]
    assert row["commission"] == 2.00 and row["net_pnl"] == -46.00 and row["net_r"] == -1.15
    assert L.set_commissions(c, oid, commission_in=1.00, commission_out=1.00) is False, "unchanged is not a write"


def test_an_unreported_side_keeps_what_the_row_had():
    c = L.connect(":memory:")
    oid = _closed(c, c_in=1.00, c_out=1.00)
    L.set_commissions(c, oid, commission_in=None, commission_out=None)
    assert L.trade_rows(c)[0]["commission"] == 2.00


# ------------------------------------------------------------------ the runner writes it
class _Trader:
    account = "DUR339781"

    def __init__(self, rec):
        self.placed = [rec]

    def adopt(self, rows): return 0
    def sync(self): pass


def test_sync_fills_writes_the_commission_as_it_arrives():
    c = L.connect(":memory:")
    oid = _closed(c)
    rec = PlacedOrder(symbol="T", parent_id=11, stop_id=12, trigger=5.00, stop=4.80, shares=200,
                      fill_price=5.00, exit_price=4.78, commission_in=1.00)
    now = lambda: datetime(2026, 10, 6, 13, 50, tzinfo=timezone.utc)   # noqa: E731
    r = Runner(c, mode="TRADE", dollar_risk=40.0, trader=_Trader(rec), now=now)
    r.sync_fills()
    got = c.execute("SELECT commission_in, commission_out FROM orders WHERE order_id=?", (oid,)).fetchone()
    assert (got["commission_in"], got["commission_out"]) == (1.00, None)
    rec.commission_out = 1.00
    r.sync_fills()
    got = c.execute("SELECT commission_in, commission_out FROM orders WHERE order_id=?", (oid,)).fetchone()
    assert (got["commission_in"], got["commission_out"]) == (1.00, 1.00)


# ------------------------------------------------------------------ the read-outs
def test_the_report_prints_net_r_beside_r(capsys):
    import exercise as X
    c = L.connect(":memory:")
    _closed(c, c_in=1.00, c_out=1.00)
    X.print_trades(c)
    out = capsys.readouterr().out
    assert "-1.10 R on the fills, before commission" in out
    assert "-1.15 R after $2.00 IBKR commission on 1 of 1" in out
    assert "no costs" not in out


def test_the_report_says_when_no_commission_was_reported(capsys):
    import exercise as X
    c = L.connect(":memory:")
    _closed(c)
    X.print_trades(c)
    assert "no IBKR commission report recorded yet" in capsys.readouterr().out


def test_watch_shows_the_net_once_the_report_arrives(tmp_path):
    import watch as W
    db = tmp_path / "j.sqlite"
    c = L.connect(str(db))
    oid = _closed(c)
    c.commit()
    w = W.Watcher(W.connect_ro(db), day="2026-10-06")
    lines = [t for _, t in w.poll()]
    exit_line = next(t for t in lines if " EXIT " in t)
    assert "on the fills" in exit_line and "commission not reported yet" in exit_line
    L.set_commissions(c, oid, commission_in=1.00, commission_out=1.00); c.commit()
    net = [t for _, t in w.poll() if " NET " in t]
    assert len(net) == 1 and "IBKR commission $2.00" in net[0] and "-1.15 R" in net[0]
    assert [t for _, t in w.poll() if " NET " in t] == [], "printed once"
