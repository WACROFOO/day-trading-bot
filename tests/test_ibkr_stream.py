"""Offline tests for the persistent read-only IBKR streaming service.

A FakeIB stands in for ib_async.IB; every invariant from the handoff audit
is asserted here without a TWS: ten-second candles need both halves, no
duplicate timestamps, a minute equals its five-second aggregate, backfill and
live overlap do not double count, staleness comes from the clock, reconnect
resubscribes once, delayed data is rejected, and no order method exists.
"""

from __future__ import annotations

import inspect
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from momentum_platform.datasources import ibkr_stream as mod  # noqa: E402
from momentum_platform.datasources.ibkr_stream import (  # noqa: E402
    Bar5s, BarStore, IbkrStream, stale_threshold_seconds)
from momentum_platform.models import DataStatus  # noqa: E402

UTC = timezone.utc
T0 = datetime(2026, 9, 3, 14, 0, 0, tzinfo=UTC)          # 10:00 ET, regular hours


def five(symbol, i, ts0=T0, vol=10):
    ts = ts0 + timedelta(seconds=5 * i)
    return Bar5s(symbol, ts, 1.0 + i, 2.0 + i, 0.5 + i, 1.5 + i, vol)


# -- store ---------------------------------------------------------------------

def test_ten_second_candle_needs_both_halves():
    st = BarStore()
    st.append(five("A", 0))
    assert st.closed_10s("A") == [], "one five-second bar is half a candle, not a candle"
    st.append(five("A", 1))
    out = st.closed_10s("A")
    assert len(out) == 1 and out[0].timeframe == "10s" and out[0].ts == T0
    assert out[0].open == 1.0 and out[0].close == 2.5 and out[0].high == 3.0 and out[0].low == 0.5
    assert out[0].volume == 20
    assert st.closed_10s("A") == [], "a closed candle is emitted exactly once"


def test_missing_half_is_not_interpolated():
    st = BarStore()
    st.append(five("A", 0))
    st.append(five("A", 3))          # 14:00:15 — bar 14:00:05 and 14:00:10 never arrived
    assert st.closed_10s("A") == [], "no candle is invented for an empty bucket"


def test_duplicate_timestamps_are_ignored():
    st = BarStore()
    assert st.append(five("A", 0)) is True
    assert st.append(five("A", 0)) is False
    assert len(st.bars5s("A")) == 1


def test_minute_equals_aggregate_of_its_five_second_bars():
    st = BarStore()
    for i in range(13):              # 14:00:00 .. 14:01:00
        st.append(five("A", i))
    closed = st.closed_1m("A", now=T0 + timedelta(seconds=61))
    assert [b.ts for b in closed] == [T0]
    m = closed[0]
    assert m.timeframe == "1m" and m.open == 1.0 and m.close == 1.5 + 11
    assert m.high == 2.0 + 11 and m.low == 0.5 and m.volume == 120
    assert st.forming_1m("A").ts == T0 + timedelta(minutes=1)
    assert st.forming_1m("A").volume == 10


def test_minute_closes_by_clock_when_no_later_bar_arrives():
    st = BarStore()
    for i in range(12):
        st.append(five("A", i))
    assert st.closed_1m("A", now=T0 + timedelta(seconds=60)) == [], "grace period not over"
    assert len(st.closed_1m("A", now=T0 + timedelta(seconds=65))) == 1


def test_backfill_and_live_overlap_do_not_double_count():
    st = BarStore()
    for i in range(6):
        st.append(five("A", i))
    for i in range(3, 9):            # live stream overlaps the last three backfilled bars
        st.append(five("A", i))
    assert len(st.bars5s("A")) == 9
    keys = [b.ts for b in st.bars5s("A")]
    assert keys == sorted(set(keys))


# -- fake TWS ------------------------------------------------------------------

class FakeEvent:
    def __init__(self):
        self.handlers = []

    def __iadd__(self, fn):
        self.handlers.append(fn)
        return self

    def emit(self, *args):
        for h in list(self.handlers):
            h(*args)


class FakeBarList(list):
    def __init__(self, contract):
        super().__init__()
        self.contract = contract
        self.updateEvent = FakeEvent()


class FakeRTBar:
    def __init__(self, time, o, h, l, c, v):
        self.time, self.open_, self.high, self.low, self.close, self.volume = time, o, h, l, c, v


class FakeHistBar:
    def __init__(self, date, o, h, l, c, v):
        self.date, self.open, self.high, self.low, self.close, self.volume = date, o, h, l, c, v


class FakeTicker:
    def __init__(self):
        self.last = math.nan
        self.lastSize = 0
        self.bid = math.nan
        self.ask = math.nan
        self.marketDataType = 1


class FakeClient:
    def serverVersion(self):
        return 178


class FakeIB:
    def __init__(self, fail_connects=0, hist=None):
        self.fail_connects = fail_connects
        self.hist = hist or {}
        self.connected = False
        self.connect_calls = []
        self.md_type = None
        self.tickers = {}
        self.bar_lists = {}
        self.live_lines = []
        self.cancelled = []
        self.client = FakeClient()

    def connect(self, host, port, clientId, readonly=False, timeout=0):
        self.connect_calls.append({"host": host, "port": port, "clientId": clientId,
                                   "readonly": readonly, "timeout": timeout})
        if self.fail_connects > 0:
            self.fail_connects -= 1
            raise ConnectionRefusedError("TWS not listening")
        self.connected = True

    def disconnect(self):
        self.connected = False

    def isConnected(self):
        return self.connected

    def reqMarketDataType(self, n):
        self.md_type = n

    def qualifyContracts(self, *contracts):
        return list(contracts)

    def reqMktData(self, contract, *args):
        t = self.tickers.setdefault(contract.symbol, FakeTicker())
        self.live_lines.append(("mkt", contract.symbol))
        return t

    def cancelMktData(self, contract):
        self.cancelled.append(("mkt", contract.symbol))

    def reqRealTimeBars(self, contract, size, what, use_rth):
        assert size == 5 and what == "TRADES"
        lst = FakeBarList(contract)
        self.bar_lists[contract.symbol] = lst
        self.live_lines.append(("rtb", contract.symbol))
        return lst

    def cancelRealTimeBars(self, lst):
        self.cancelled.append(("rtb", lst.contract.symbol))

    def reqHistoricalData(self, contract, end, duration, size, what, use_rth, formatDate=2):
        return list(self.hist.get(contract.symbol, []))

    # helpers for tests
    def push_bar(self, symbol, ts, o, h, l, c, v):
        lst = self.bar_lists[symbol]
        lst.append(FakeRTBar(ts, o, h, l, c, v))
        lst.updateEvent.emit(lst, True)


class Clock:
    def __init__(self, now=T0):
        self.now = now

    def __call__(self):
        return self.now

    def tick(self, seconds):
        self.now = self.now + timedelta(seconds=seconds)


def make(ib=None, **kw):
    ib = ib or FakeIB()
    clock = Clock()
    got = []
    s = IbkrStream(ib=ib, on_update=got.append, clock=clock, **kw)
    return s, ib, clock, got


# -- connection ----------------------------------------------------------------

def test_connect_is_read_only_and_requests_live_data_type():
    s, ib, _, _ = make()
    h = s.connect()
    assert ib.connect_calls[0]["readonly"] is True
    assert ib.connect_calls[0]["clientId"] == 27 and ib.connect_calls[0]["port"] == 7496
    assert ib.md_type == 1
    assert h.connected and h.state == "LIVE" and h.read_only and h.market_data_type == 1
    assert h.server_version == 178 and h.generation == 1


def test_connect_failure_is_offline_not_an_exception():
    s, ib, _, _ = make(ib=FakeIB(fail_connects=1))
    h = s.connect()
    assert h.state == "OFFLINE" and not h.connected and "connect failed" in h.last_error


# -- subscriptions -------------------------------------------------------------

def test_subscribe_uses_two_lines_per_symbol_and_respects_the_limit():
    s, ib, _, _ = make(max_lines=4)
    s.connect()
    added = s.subscribe(["aaa", "BBB", "CCC"], backfill_seconds=0)
    assert added == ["AAA", "BBB"]
    assert s.health.subscriptions == 4
    assert "CCC" in " ".join(s.health.messages) and "line limit" in " ".join(s.health.messages)
    assert s.subscribe(["AAA"], backfill_seconds=0) == [], "already subscribed"


def test_unsubscribe_cancels_both_lines():
    s, ib, _, _ = make()
    s.connect()
    s.subscribe(["AAA"], backfill_seconds=0)
    s.unsubscribe(["AAA"])
    assert ("mkt", "AAA") in ib.cancelled and ("rtb", "AAA") in ib.cancelled
    assert s.symbols == [] and s.health.subscriptions == 0


# -- live bars -----------------------------------------------------------------

def test_realtime_bars_close_a_minute_and_emit_one_market_update():
    s, ib, clock, got = make()
    s.connect()
    s.subscribe(["AAA"], backfill_seconds=0)
    for i in range(12):
        clock.now = T0 + timedelta(seconds=5 * i + 5)
        ib.push_bar("AAA", T0 + timedelta(seconds=5 * i), 1 + i, 2 + i, 0.5 + i, 1.5 + i, 10)
    assert got == [], "the minute is still forming"
    clock.now = T0 + timedelta(seconds=65)
    ib.push_bar("AAA", T0 + timedelta(seconds=60), 20, 21, 19, 20.5, 10)
    assert len(got) == 1
    u = got[0]
    assert u.symbol == "AAA" and u.bar.timeframe == "1m" and u.bar.ts == T0
    assert u.bar.volume == 120 and u.price == u.bar.close and u.data_status == DataStatus.LIVE
    assert s.health.last_bar_at == clock.now
    tens = s.store.closed_10s("AAA")
    assert len(tens) == 6 and all(b.volume == 20 for b in tens)


def test_backfill_then_live_overlap_keeps_one_bar_per_timestamp():
    hist = [FakeHistBar(T0 + timedelta(seconds=5 * i), 1, 2, 0.5, 1.5, 10) for i in range(6)]
    s, ib, clock, got = make(ib=FakeIB(hist={"AAA": hist}))
    s.connect()
    s.subscribe(["AAA"], backfill_seconds=60)
    assert len(s.store.bars5s("AAA")) == 6
    for i in range(3, 9):
        ib.push_bar("AAA", T0 + timedelta(seconds=5 * i), 1, 2, 0.5, 1.5, 10)
    assert len(s.store.bars5s("AAA")) == 9


# -- quotes and the delayed-data rule -----------------------------------------

def test_delayed_market_data_type_is_rejected():
    s, ib, clock, got = make()
    s.connect()
    s.subscribe(["AAA"], backfill_seconds=0)
    ib.tickers["AAA"].last, ib.tickers["AAA"].marketDataType = 4.2, 3
    s.poll_tickers()
    assert got == [] and s.health.state == "DELAYED" and s.health.market_data_type == 3
    assert s.check().state == "DELAYED", "check() does not paper over a delayed feed"


def test_live_quote_is_emitted_and_nan_is_skipped():
    s, ib, clock, got = make()
    s.connect()
    s.subscribe(["AAA", "BBB"], backfill_seconds=0)
    ib.tickers["AAA"].last, ib.tickers["AAA"].lastSize = 4.2, 300
    ib.tickers["AAA"].bid, ib.tickers["AAA"].ask = 4.19, 4.21
    s.poll_tickers()                            # BBB.last is NaN
    assert [u.symbol for u in got] == ["AAA"]
    assert got[0].price == 4.2 and got[0].size == 300 and got[0].bid == 4.19 and got[0].ask == 4.21
    assert got[0].data_status == DataStatus.LIVE and s.health.last_quote_at == clock.now


# -- freshness -----------------------------------------------------------------

def test_stale_threshold_is_session_aware():
    assert stale_threshold_seconds(T0) == 20                                    # 10:00 ET
    assert stale_threshold_seconds(datetime(2026, 9, 3, 11, 0, tzinfo=UTC)) == 60  # 07:00 ET


def test_check_turns_stale_on_a_frozen_clock_and_offline_on_socket_drop():
    s, ib, clock, got = make()
    s.connect()
    s.subscribe(["AAA"], backfill_seconds=0)
    ib.push_bar("AAA", T0, 1, 2, 0.5, 1.5, 10)
    assert s.check().state == "LIVE"
    clock.tick(19)
    assert s.check().state == "LIVE"
    clock.tick(2)
    assert s.check().state == "STALE"
    ib.push_bar("AAA", T0 + timedelta(seconds=5), 1, 2, 0.5, 1.5, 10)
    assert s.check().state == "LIVE"
    ib.connected = False
    assert s.check().state == "OFFLINE" and "socket dropped" in s.health.messages[-1]


def test_no_symbols_means_no_staleness_claim():
    s, ib, clock, got = make()
    s.connect()
    clock.tick(600)
    assert s.check().state == "LIVE"


# -- reconnect -----------------------------------------------------------------

def test_reconnect_resubscribes_each_symbol_once(monkeypatch):
    monkeypatch.setattr(mod.time, "sleep", lambda *_: None)
    s, ib, clock, got = make()
    s.connect()
    s.subscribe(["AAA", "BBB"], backfill_seconds=0)
    ib.connected = False
    h = s.reconnect()
    assert h.connected and h.generation == 2 and h.reconnects == 1
    assert s.symbols == ["AAA", "BBB"]
    assert ib.live_lines.count(("rtb", "AAA")) == 2, "one live line per connection generation"
    assert ib.live_lines.count(("mkt", "AAA")) == 2
    assert h.subscriptions == 4


def test_reconnect_backs_off_and_stays_offline_while_tws_is_down(monkeypatch):
    sleeps = []
    monkeypatch.setattr(mod.time, "sleep", sleeps.append)
    s, ib, clock, got = make(ib=FakeIB())
    s.connect()
    ib.fail_connects = 2
    assert s.reconnect().state == "OFFLINE"
    assert s.reconnect().state == "OFFLINE"
    assert s.reconnect().state == "LIVE"
    assert sleeps == [1.0, 2.0, 4.0] and s.health.reconnects == 1


# -- boundary: read-only forever ------------------------------------------------

def test_the_module_exposes_no_order_surface():
    names = [n for n in dir(IbkrStream) if "order" in n.lower()]
    assert names == []
    src = inspect.getsource(mod)
    for forbidden in ("placeOrder", "cancelOrder", "reqOpenOrders", "reqAllOpenOrders", "reqGlobalCancel"):
        assert forbidden not in src, forbidden
    assert "readonly=True" in src


def test_health_dict_is_json_ready():
    s, ib, clock, got = make()
    s.connect()
    d = s.health.as_dict()
    assert d["readOnly"] is True and d["marketDataType"] == 1 and d["state"] == "LIVE"
    assert d["lastBarAt"] is None and isinstance(d["messages"], list)


def test_read_only_connect_skips_the_startup_account_sync_when_ib_async_offers_it():
    """The desk never trades: no positions, orders, executions or account
    updates at connect time, so a flapping TWS link cannot exhaust the account
    summary quota (error 322). readonly=True is always passed."""
    seen = {}

    class Real:
        def connect(self, host, port, clientId=1, timeout=4, readonly=False, fetchFields=None):
            seen.update(host=host, port=port, clientId=clientId, timeout=timeout,
                        readonly=readonly, fetchFields=fetchFields)

    mod.read_only_connect(Real(), "127.0.0.1", 7496, 27, 4)
    assert seen["readonly"] is True and seen["clientId"] == 27
    assert seen["fetchFields"] is not None and not any(seen["fetchFields"] & m for m in type(seen["fetchFields"]))

    class Old:                                   # no fetchFields parameter at all
        def connect(self, host, port, clientId=1, timeout=4, readonly=False):
            seen.clear(); seen.update(readonly=readonly)

    mod.read_only_connect(Old(), "127.0.0.1", 7496, 27, 4)
    assert seen == {"readonly": True}


def test_late_reply_filter_turns_the_key_error_traceback_into_one_info_line(caplog):
    import logging
    mod.quiet_ib_async_logging()
    lg = logging.getLogger("ib_async.Decoder")
    with caplog.at_level(logging.INFO, logger="ib_async.Decoder"):
        try:
            {}[7]
        except KeyError:
            lg.exception("Error handling fields: [10, 3, 7]")
        lg.error("Error handling fields: something real", exc_info=False)
    recs = [r for r in caplog.records if r.name == "ib_async.Decoder"]
    assert [r.levelname for r in recs] == ["INFO", "ERROR"]
    assert "late reply" in recs[0].getMessage() and recs[0].exc_info is None
