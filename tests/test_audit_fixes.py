"""Fixes from the 2026-09-08 pre-session audit, each pinned."""
from __future__ import annotations

import json
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "tests"))

from journal import actuals, ledger as L  # noqa: E402
from momentum_platform.cascade import Inputs, evaluate  # noqa: E402
from momentum_platform.dashboard import session_builder as SB  # noqa: E402
from types import SimpleNamespace as NS  # noqa: E402


# ---- stream health: a quiet minute with live quotes is not STALE ------------------------
def test_health_uses_the_newest_heartbeat_bar_or_quote():
    from momentum_platform.datasources.ibkr_stream import IbkrStream, Health
    now = datetime(2026, 9, 8, 12, 30, tzinfo=timezone.utc)          # 08:30 ET, extended hours
    s = IbkrStream.__new__(IbkrStream)
    s.health = Health(); s.health.connected = True; s.health.state = "LIVE"
    s._symbols = {"AAA"}; s.clock = lambda: now
    s._ib = NS(isConnected=lambda: True)
    s.health.last_bar_at = now - timedelta(seconds=200)                # no TRADES bar for 200 s
    s.health.last_quote_at = now - timedelta(seconds=1)                # quotes ticking
    assert s.check().state == "LIVE"
    s.health.last_quote_at = now - timedelta(seconds=200)
    assert s.check().state == "STALE"


# ---- ledger: bars upsert, STALE rows upgrade -------------------------------------------
def test_a_fuller_minute_aggregate_replaces_the_partial_one():
    c = L.connect(":memory:")
    L.record_bars(c, {"X": [("2026-09-08T14:05:00Z", 5.0, 5.05, 4.99, 5.02, 300)]})   # first 10 s
    L.record_bars(c, {"X": [("2026-09-08T14:05:00Z", 5.0, 5.20, 4.95, 5.15, 4200)]})  # full minute
    r = c.execute("SELECT high, low, close, volume FROM bars").fetchone()
    assert (r["high"], r["low"], r["close"], r["volume"]) == (5.20, 4.95, 5.15, 4200)
    L.record_bars(c, {"X": [("2026-09-08T14:05:00Z", 5.0, 5.01, 5.0, 5.0, 10)]})     # a lesser write never wins
    assert c.execute("SELECT volume FROM bars").fetchone()[0] == 4200


def _inputs(**over):
    base = dict(symbol="T", last=6.0, prev_close=4.0, change_pct=50.0, session_high=6.2,
                float_shares=4e6, float_verified=True, catalyst_today=True, is_fund_or_etf=False,
                tick_size=0.01, above_vwap=True, above_ema9=True, macd_positive_and_above_signal=True,
                session_volume=3e6, rvol=8.0)
    base.update(over); return Inputs(**base)


def test_a_decision_first_seen_stale_is_upgraded_by_the_next_live_build():
    c = L.connect(":memory:")
    plan = NS(entry=6.05, stop=5.90, target=None, risk_share=0.15, reward_multiple=None,
              pullback_candles=2, volume_ok=True)
    kw = dict(symbol="T", armed_at="2026-09-08T14:05:00Z", plan=plan, snapshot={}, session="regular")
    stale = _inputs(feed_stale=True); L.record_decision(c, cascade=evaluate(stale), inputs=stale, **kw)
    row = c.execute("SELECT verdict, outcome FROM decisions").fetchone()
    assert (row["verdict"], row["outcome"]) == ("STALE", "SUPPRESSED")
    live = _inputs(); L.record_decision(c, cascade=evaluate(live), inputs=live, **kw)
    row = c.execute("SELECT verdict, outcome, plan_allowed FROM decisions").fetchone()
    assert (row["verdict"], row["outcome"], row["plan_allowed"]) == ("REVIEW", "PENDING", 1)
    # but a REAL verdict is never overwritten by a later build
    killed = _inputs(last=1.0); L.record_decision(c, cascade=evaluate(killed), inputs=killed, **kw)
    assert c.execute("SELECT verdict FROM decisions").fetchone()[0] == "REVIEW"


# ---- catalyst dated today ---------------------------------------------------------------
def test_catalyst_counts_only_since_yesterdays_close_and_never_a_roundup():
    day = "2026-09-08"
    fresh = {"publishedAt": "2026-09-08T11:30:00Z", "category": "press_release"}        # 07:30 ET today
    overnight = {"publishedAt": "2026-09-07T21:00:00Z", "category": "news"}            # 17:00 ET yesterday
    old = {"publishedAt": "2026-09-06T14:00:00Z", "category": "news"}                   # two days ago
    roundup = {"publishedAt": "2026-09-08T11:00:00Z", "category": "market_roundup"}
    assert SB._catalyst_today([fresh], day) is True
    assert SB._catalyst_today([overnight], day) is True
    assert SB._catalyst_today([old], day) is False
    assert SB._catalyst_today([roundup], day) is False
    assert SB._catalyst_today([], day) is False


# ---- point-in-time quote ---------------------------------------------------------------
def test_stream_quote_is_attached_only_to_the_newest_bar():
    bar_now = NS(ts=datetime(2026, 9, 8, 14, 5, tzinfo=timezone.utc))
    bar_old = NS(ts=datetime(2026, 9, 8, 12, 5, tzinfo=timezone.utc))
    meta = {"iexLastTs": "2026-09-08T14:05:30Z"}
    assert SB._newest_bar_ts(bar_now, meta) is True
    assert SB._newest_bar_ts(bar_old, meta) is False
    assert SB._newest_bar_ts(bar_now, {}) is False


# ---- actuals: trigger first -------------------------------------------------------------
def test_stop_before_the_trigger_is_untriggered_not_a_loss():
    row = dict(ts_et="2026-09-08T10:00:00-04:00", trigger=10.0, stop=9.5, target=11.0, last=9.8)
    tape = [("2026-09-08T14:00:00Z", 9.8, 9.9, 9.7, 9.8, 1),
            ("2026-09-08T14:01:00Z", 9.8, 9.85, 9.4, 9.45, 1),     # dips through the stop, never reached 10
            ("2026-09-08T14:02:00Z", 9.45, 9.6, 9.4, 9.5, 1)]
    a = actuals.compute(row, tape)
    assert a["trigger_hit"] == 0 and a["first_hit"] == "untriggered" and a["stop_hit"] == 0


def test_tracking_starts_at_the_trigger_bar():
    row = dict(ts_et="2026-09-08T10:00:00-04:00", trigger=10.0, stop=9.5, target=11.0, last=9.8)
    tape = [("2026-09-08T14:00:00Z", 9.8, 9.9, 9.7, 9.8, 1),
            ("2026-09-08T14:01:00Z", 9.8, 10.05, 9.75, 10.0, 1),   # trigger touched
            ("2026-09-08T14:02:00Z", 10.0, 10.4, 9.9, 10.3, 1),
            ("2026-09-08T14:03:00Z", 10.3, 10.35, 9.45, 9.5, 1)]   # stop
    a = actuals.compute(row, tape)
    assert a["trigger_hit"] == 1 and a["trigger_hit_ts"] == "2026-09-08T14:01:00Z"
    assert a["stop_hit"] == 1 and a["first_hit"] == "stop"
    assert a["mfe_r_planned"] == pytest.approx((10.4 - 10.0) / 0.5)


# ---- runner: entries lock is not a mode flip; volume_ok enforced ------------------------
def test_entries_lock_keeps_trade_mode_for_exits():
    from execution.runner import Runner
    from momentum_platform.dashboard.session_builder import build_session
    c = L.connect(":memory:"); build_session(ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl", journal=c)
    c.execute("UPDATE decisions SET verdict='REVIEW' WHERE plan_allowed=1"); c.commit()
    class T:
        account = "DU1"; placed = []
        def place_bracket(self, *a, **k): raise AssertionError("locked: must not place")
        def adopt(self, rows): return 0
        def sync(self): pass
    r = Runner(c, mode="TRADE", dollar_risk=20.0, trader=T(), max_age_s=3600,
               now=lambda: datetime(2026, 9, 1, 13, 52, tzinfo=timezone.utc),
               quote=lambda s: dict(bid=1.0, ask=1.01, bid_size=1, ask_size=1, ts="2026-09-01T13:52:00Z"))
    r.entries_enabled = False
    done = r.step()
    assert done and all(a.outcome == "REFUSED" and any("day locked" in x for x in a.reasons) for a in done)
    assert r.mode == "TRADE"                              # exits, stops and the flatten still run


def test_trade_refuses_when_pullback_volume_was_not_lighter():
    from execution.runner import Runner
    from momentum_platform.dashboard.session_builder import build_session
    c = L.connect(":memory:"); build_session(ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl", journal=c)
    c.execute("UPDATE decisions SET verdict='REVIEW', volume_ok=0 WHERE plan_allowed=1"); c.commit()
    class T:
        account = "DU1"; placed = []
        def place_bracket(self, *a, **k): raise AssertionError("must not place")
        def adopt(self, rows): return 0
        def sync(self): pass
    r = Runner(c, mode="TRADE", dollar_risk=20.0, trader=T(), max_age_s=3600,
               now=lambda: datetime(2026, 9, 1, 13, 52, tzinfo=timezone.utc),
               quote=lambda s: dict(bid=1.0, ask=1.01, bid_size=1, ask_size=1, ts="2026-09-01T13:52:00Z"))
    done = r.step()
    assert done and all(any("pullback volume" in x for x in a.reasons) for a in done)


# ---- candidates + sessions idempotent ----------------------------------------------------
def test_gap_scan_rows_reach_the_ledger_survivors_and_rejects():
    c = L.connect(":memory:")
    rows = [dict(sym="AAA", verdict="STAR", reasons=[], price=3.1, gap=42.0, float=4e6, pm_vol=800e3),
            dict(sym="BBB", verdict="REJECT", reasons=["$0.92 under $2.00"], price=0.92)]
    assert L.record_candidates(c, "2026-09-08T10:55:00Z", "gap_scan", rows) == 2
    assert L.record_candidates(c, "2026-09-08T10:55:00Z", "gap_scan", rows) == 0
    r = c.execute("SELECT verdict, reasons_json FROM candidates WHERE symbol='BBB'").fetchone()
    assert r["verdict"] == "REJECT" and "under" in r["reasons_json"]


def test_replay_refuses_the_production_ledger(tmp_path):
    import subprocess
    r = subprocess.run([sys.executable, "scripts/exercise.py", "replay",
                        str(ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl")],
                       cwd=ROOT, capture_output=True, text=True, env={**__import__("os").environ, "JOURNAL_DB": str(tmp_path / "prod.sqlite")})
    assert r.returncode == 2 and "needs --db" in r.stdout
    assert not (tmp_path / "prod.sqlite").exists() or L.connect(tmp_path / "prod.sqlite").execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 0


# ---- Round B: the TRADE path's exits and fills -------------------------------------------
def _rth():
    from zoneinfo import ZoneInfo
    return datetime(2026, 9, 8, 10, 15, tzinfo=ZoneInfo("America/New_York"))


def test_sync_records_the_filled_quantity_and_the_brokers_fill_time(monkeypatch):
    import sys as _sys
    sys_path = str(Path(__file__).resolve().parents[1] / "tests")
    if sys_path not in _sys.path:
        _sys.path.insert(0, sys_path)
    import test_real_trader_path as F
    fake = types.ModuleType("ib_async")
    fake.LimitOrder, fake.StopOrder, fake.MarketOrder, fake.Stock = F.LimitOrder, F.StopOrder, F.MarketOrder, F.Stock
    monkeypatch.setitem(_sys.modules, "ib_async", fake)
    from execution.ibkr_trader import PaperTrader
    from execution.intent import EntryIntent
    t = PaperTrader(); t.ib = F.FakeIB(); t.account = "DU1"
    rec = t.place_bracket(EntryIntent(symbol="T", trigger=5.0, stop=4.8, shares=100, dollar_risk=20.0,
                                      plan_allowed=True, verdict="REVIEW", session="regular"), now=_rth())
    by_id = {x.order.orderId: x for x in t.ib.placed}
    st = F._Status("Filled", 5.02); st.filled = 60                    # PARTIAL: 60 of 100
    by_id[rec.parent_id].orderStatus = st
    when = datetime(2026, 9, 8, 14, 16, 3, tzinfo=timezone.utc)
    by_id[rec.parent_id].log.append(NS(status="Filled", time=when, errorCode=0, message=""))
    t.sync()
    assert rec.filled_qty == 60 and rec.fill_time == when.isoformat()
    assert any("PARTIAL" in e for e in rec.events)
    # a pending exit is confirmed by its own order id
    rec.exit_order_id, rec.exit_confirmed = 777, False
    ex = F._Trade(F.LimitOrder("SELL", 60, 4.70)); ex.order.orderId = 777
    ex.orderStatus = F._Status("Filled", 4.71); t.ib.placed.append(ex)
    t.sync()
    assert rec.exit_confirmed is True and rec.exit_price == 4.71


def test_the_flatten_is_recorded_as_a_pending_exit_and_confirmed_by_sync():
    """Before: flatten_all sold the position at the broker and the ledger row
    stayed 'stuck' forever. Now the sell is an ExitPending row carrying the
    flatten's order id, and the next sync closes it at the real fill."""
    from execution.runner import Runner
    from execution.intent import PlacedOrder

    class Trader:
        account = "DU1"
        def __init__(self): self.placed = []; self.last_flatten = []
        def adopt(self, rows): return 0
        def sync(self): pass
        def flatten_all(self, quote=None, now=None):
            self.last_flatten = [{"symbol": "T", "qty": 100, "order_id": 901, "type": "MKT", "price": None}]
            return ["T x100 MKT"]

    c = L.connect(":memory:")
    inp = _inputs(); res = evaluate(inp)
    did = L.record_decision(c, symbol="T", armed_at="2026-09-08T14:05:00Z",
                            plan=NS(entry=6.0, stop=5.8, target=6.4, risk_share=0.2, reward_multiple=2.0,
                                    pullback_candles=2, volume_ok=True),
                            cascade=res, inputs=inp, snapshot={}, session="regular")
    oid = L.record_order(c, did, symbol="T", account="DU1", session="regular", parent_id=11, stop_id=12,
                         target_id=None, trigger=6.0, stop=5.8, target=None, shares=100, dollar_risk=20.0,
                         protected=True)
    L.record_fill(c, oid, fill_price=6.02, fill_ts="2026-09-08T14:06:00Z")
    t = Trader(); t.placed.append(PlacedOrder(symbol="T", parent_id=11, stop_id=12, trigger=6.0, stop=5.8,
                                              shares=100, fill_price=6.02, protected=True))
    r = Runner(c, mode="TRADE", dollar_risk=20.0, trader=t,
               now=lambda: datetime(2026, 9, 8, 15, 30, tzinfo=timezone.utc))
    assert r.end_of_day() == ["T x100 MKT"]
    o = c.execute("SELECT status, exit_reason, exit_order_id, exit_price FROM orders").fetchone()
    assert (o["status"], o["exit_reason"], o["exit_order_id"], o["exit_price"]) == ("ExitPending", "hard_stop", 901, None)
    assert len(L.stuck_orders(c)) == 1                        # still held until the fill is seen
    assert r.end_of_day() == ["T x100 MKT"] and len(L.pending_exits(c)) == 1   # idempotent: not re-recorded
    rec = t.placed[0]
    assert rec.exit_order_id == 901 and rec.exit_confirmed is False
    rec.exit_price, rec.exit_time, rec.exit_confirmed = 5.97, "2026-09-08T15:30:02Z", True
    r.sync_fills()
    o = c.execute("SELECT status, exit_price FROM orders").fetchone()
    assert (o["status"], o["exit_price"]) == ("Closed", 5.97) and L.stuck_orders(c) == []


def test_connect_refuses_a_live_account_and_closes_the_socket(monkeypatch):
    """The paper guard on the real connect path, not just assert_paper()."""
    import sys as _sys
    calls = []

    class IB:
        def connect(self, host, port, clientId, readonly, timeout): calls.append(("connect", port, readonly))
        def managedAccounts(self): return ["U1234567"]
        def disconnect(self): calls.append(("disconnect",))

    fake = types.ModuleType("ib_async"); fake.IB = IB
    monkeypatch.setitem(_sys.modules, "ib_async", fake)
    from execution.ibkr_trader import NotPaperError, PaperTrader
    t = PaperTrader()
    with pytest.raises(NotPaperError, match="not a paper account"):
        t.connect()
    assert t.ib is None and calls == [("connect", 4002, False), ("disconnect",)]
