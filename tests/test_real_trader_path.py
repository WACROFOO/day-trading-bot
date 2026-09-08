"""Run PaperTrader's real place_bracket / _bracket / sync code, not a fake
trader, against a fake `ib_async` module. ib_async is not installed in the
build container, so until now every test of the real path skipped — and a
NameError in place_bracket reached a live smoke test on 2026-09-07 after
both legs had been sent."""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


# ---- a fake ib_async: the handful of names the trader imports lazily -------------
class _Order:
    def __init__(self, action, qty, px=None):
        self.action, self.totalQuantity = action, qty
        self.orderId = 0; self.parentId = 0; self.ocaGroup = ""; self.transmit = True
        self.tif = "DAY"; self.outsideRth = False
        # IBKR's own strings, so the trader's leg lookup by orderType is exercised for real
        self.orderType = {"LimitOrder": "LMT", "StopOrder": "STP", "MarketOrder": "MKT"}[type(self).__name__]

class LimitOrder(_Order):
    def __init__(self, action, qty, lmt): super().__init__(action, qty, lmt); self.lmtPrice = lmt

class StopOrder(_Order):
    def __init__(self, action, qty, aux): super().__init__(action, qty, aux); self.auxPrice = aux

class MarketOrder(_Order): pass

class Stock:
    def __init__(self, symbol, exchange, currency): self.symbol = symbol

class _Status:
    def __init__(self, status="PreSubmitted", avg=0.0): self.status, self.avgFillPrice = status, avg

class _Trade:
    def __init__(self, order): self.order, self.orderStatus, self.log = order, _Status(), []

class _Client:
    def __init__(self): self.n = 500
    def getReqId(self): self.n += 1; return self.n

class FakeIB:
    def __init__(self): self.client = _Client(); self.placed = []; self.fail_on = None
    def qualifyContracts(self, c): return [c]
    def placeOrder(self, contract, order):
        if self.fail_on == order.orderType: raise RuntimeError("broker refused")
        t = _Trade(order); self.placed.append(t); return t
    def trades(self): return list(self.placed)
    def sleep(self, s): pass


@pytest.fixture
def trader(monkeypatch):
    fake = types.ModuleType("ib_async")
    fake.LimitOrder, fake.StopOrder, fake.MarketOrder, fake.Stock = LimitOrder, StopOrder, MarketOrder, Stock
    fake.util = types.SimpleNamespace(run=lambda c: c)
    monkeypatch.setitem(sys.modules, "ib_async", fake)
    from execution.ibkr_trader import PaperTrader
    t = PaperTrader(); t.ib = FakeIB(); t.account = "DUR339781"
    return t


def intent(**over):
    from execution.intent import EntryIntent
    base = dict(symbol="TEST", trigger=5.00, stop=4.80, shares=100, dollar_risk=20.0,
                plan_allowed=True, verdict="REVIEW", session="regular")
    base.update(over); return EntryIntent(**base)


def test_the_real_place_bracket_runs_end_to_end_and_records_before_sending(trader):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    rth = datetime(2026, 9, 8, 10, 15, tzinfo=ZoneInfo("America/New_York"))
    rec = trader.place_bracket(intent(), now=rth)
    assert rec in trader.placed
    assert rec.protected is True and rec.stop_id and rec.parent_id
    legs = trader.ib.placed
    assert [t.order.orderType for t in legs] == ["LMT", "STP"]          # entry then stop
    parent, stop = legs[0].order, legs[1].order
    assert parent.transmit is False and stop.transmit is True           # the group holds until the stop
    assert stop.parentId == parent.orderId and parent.outsideRth is False
    assert any("placed 2 legs" in e for e in rec.events)


def test_premarket_bracket_marks_protection_unconfirmed(trader):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    pm = datetime(2026, 9, 8, 8, 15, tzinfo=ZoneInfo("America/New_York"))
    rec = trader.place_bracket(intent(session="premarket"), now=pm)
    assert rec.protected is False
    assert all(t.order.outsideRth for t in trader.ib.placed)


def test_a_broker_error_mid_send_still_leaves_a_record_that_says_so(trader):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    rth = datetime(2026, 9, 8, 10, 15, tzinfo=ZoneInfo("America/New_York"))
    trader.ib.fail_on = "STP"                                           # entry goes, stop is refused
    with pytest.raises(RuntimeError, match="refused"):
        trader.place_bracket(intent(), now=rth)
    assert len(trader.placed) == 1 and trader.placed[0].status == "error"
    assert any("CHECK THE BROKER" in e for e in trader.placed[0].events)


def test_sync_reads_the_exit_legs(trader):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    rth = datetime(2026, 9, 8, 10, 15, tzinfo=ZoneInfo("America/New_York"))
    rec = trader.place_bracket(intent(target=5.40), now=rth)
    # two limit orders exist (entry, target); find them by id
    by_id = {t.order.orderId: t for t in trader.ib.placed}
    by_id[rec.parent_id].orderStatus = _Status("Filled", 5.02)
    by_id[rec.stop_id].orderStatus = _Status("Filled", 4.79)
    trader.sync()
    assert rec.fill_price == 5.02
    assert rec.exit_price == 4.79 and rec.exit_reason == "stop"


def test_sync_records_the_permid_and_matches_by_it_when_orderid_is_zero(trader):
    """IBKR reports an earlier session's orders as orderId 0; only permId
    survives. A restarted runner's adopted record must still find its order."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    rth = datetime(2026, 9, 8, 10, 15, tzinfo=ZoneInfo("America/New_York"))
    rec = trader.place_bracket(intent(), now=rth)
    by_id = {t.order.orderId: t for t in trader.ib.placed}
    by_id[rec.parent_id].order.permId = 987654
    trader.sync()
    assert rec.perm_id == 987654
    # simulate the next session: the broker reports the same order with orderId 0
    by_id[rec.parent_id].order.orderId = 0
    by_id[rec.parent_id].orderStatus = _Status("Filled", 5.03)
    trader.sync()
    assert rec.fill_price == 5.03


def test_ledger_persists_permid_once(tmp_path):
    from journal import ledger as L
    from momentum_platform.dashboard.session_builder import build_session
    c = L.connect(":memory:")
    build_session(ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl", journal=c)
    did = L.decisions(c, plan_allowed=1)[0]["decision_id"]
    oid = L.record_order(c, did, symbol="X", account="DU1", session="regular", parent_id=1, stop_id=2,
                         target_id=None, trigger=5.0, stop=4.8, target=None, shares=10, dollar_risk=2.0,
                         protected=True)
    L.set_perm_id(c, oid, 111); L.set_perm_id(c, oid, 222)          # second write is ignored
    assert c.execute("SELECT perm_id FROM orders WHERE order_id=?", (oid,)).fetchone()[0] == 111
    assert L.open_orders(c)[0]["perm_id"] == 111
