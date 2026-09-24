"""tape.py runs on IBKR when a Gateway answers (2026-09-24). Before, the IBKR
path was written for the wrong library and port behind an opt-in nobody set,
so every hand check ran on Yahoo while the desk ran on IBKR."""
from __future__ import annotations

import datetime as dt
import math
import sys
import types
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ib_feed  # noqa: E402
import tape  # noqa: E402

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc


class _Bar:
    def __init__(self, date, o, h, l, c, v):
        self.date, self.open, self.high, self.low, self.close, self.volume = date, o, h, l, c, v


class _Ticker:
    last, bid, ask, halted = 7.31, 7.30, 7.32, math.nan


def _fake_ib_module(record: dict):
    class IB:
        def connect(self, host, port, clientId, readonly=False, timeout=8):
            record["connect"] = dict(host=host, port=port, clientId=clientId, readonly=readonly)
        def qualifyContracts(self, c): return [c]
        def reqHistoricalData(self, c, endDateTime, durationStr, barSizeSetting, whatToShow, useRTH, formatDate):
            record.setdefault("hist", []).append(dict(bar=barSizeSetting, dur=durationStr, rth=useRTH, show=whatToShow))
            if barSizeSetting == "1 day":
                return [_Bar(dt.date(2026, 9, 22), 6.0, 6.5, 5.9, 6.40, 900_000),
                        _Bar(dt.date(2026, 9, 23), 6.4, 7.0, 6.3, 6.90, 1_200_000),
                        _Bar(dt.date(2026, 9, 24), 7.2, 7.5, 7.1, 7.31, 300_000)]      # today, half-formed
            return [_Bar(dt.datetime(2026, 9, 23, 19, 59, tzinfo=UTC), 6.9, 6.9, 6.9, 6.90, 100),   # yesterday 15:59 ET
                    _Bar(dt.datetime(2026, 9, 24, 8, 1, tzinfo=UTC), 7.0, 7.05, 6.98, 7.02, 1500),  # 04:01 ET
                    _Bar(dt.datetime(2026, 9, 24, 11, 12, tzinfo=UTC), 7.1, 7.2, 7.1, 7.18, 42_000),   # 07:12 ET
                    _Bar(dt.datetime(2026, 9, 24, 11, 13, tzinfo=UTC), 7.18, 7.18, 7.18, 0.0, 0),     # no close
                    _Bar(dt.datetime(2026, 9, 24, 11, 14, tzinfo=UTC), 7.18, 7.31, 7.15, 7.31, 61_000)]
        def reqTickers(self, c): return [_Ticker()]
        def disconnect(self): record["disconnected"] = True
    class Stock:
        def __init__(self, sym, ex, cur): self.symbol = sym
    m = types.ModuleType("ib_async"); m.IB, m.Stock = IB, Stock
    return m


@pytest.fixture
def today(monkeypatch):
    class _DT(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return dt.datetime(2026, 9, 24, 9, 40, tzinfo=ET) if tz else dt.datetime(2026, 9, 24, 9, 40)
    monkeypatch.setattr(ib_feed.dt, "datetime", _DT)
    return dt.date(2026, 9, 24)


def test_fetch_reads_todays_extended_hours_bars_with_real_premarket_volume(monkeypatch, today):
    rec: dict = {}
    monkeypatch.setitem(sys.modules, "ib_async", _fake_ib_module(rec))
    monkeypatch.setattr(ib_feed, "port", lambda env=None: (4002, "detected"))
    rows, meta = ib_feed.fetch("ABCD")
    assert rec["connect"] == dict(host="127.0.0.1", port=4002, clientId=36, readonly=True)
    assert rec["disconnected"] is True
    assert [r[0].strftime("%H:%M") for r in rows] == ["04:01", "07:12", "07:14"]     # yesterday and the closeless bar dropped
    assert rows[1][5] == 42_000 and rows[0][0].tzinfo is not None
    assert meta["source"] == "ibkr" and meta["port"] == 4002 and meta["port_label"] == "paper gateway"
    assert meta["prev"] == 6.90                                                    # last close BEFORE today
    assert (meta["last"], meta["bid"], meta["ask"], meta["halted"]) == (7.31, 7.30, 7.32, None)   # nan halted = unknown
    assert meta["quote_error"] is None
    assert any(h["bar"] == "1 min" and h["rth"] is False for h in rec["hist"])


def test_a_dead_quote_keeps_the_bars(monkeypatch, today):
    rec: dict = {}
    m = _fake_ib_module(rec)
    def boom(self, c): raise RuntimeError("10197 competing live session")
    m.IB.reqTickers = boom
    monkeypatch.setitem(sys.modules, "ib_async", m)
    monkeypatch.setattr(ib_feed, "port", lambda env=None: (4002, "detected"))
    rows, meta = ib_feed.fetch("ABCD")
    assert len(rows) == 3 and meta["last"] == 7.31 and "10197" in meta["quote_error"]


def test_port_and_enabled_follow_the_environment(monkeypatch):
    ib_feed._port_cache.clear()
    assert ib_feed.port({"IBKR_PORT": "4002"}) == (4002, "IBKR_PORT")
    assert ib_feed.port({"IB_PORT": "7497"}) == (7497, "IBKR_PORT")
    def refuse(addr, timeout=0): raise OSError("refused")
    monkeypatch.setattr(ib_feed.socket, "create_connection", refuse)
    p, why = ib_feed.port({})
    assert p is None and "4002/7497/7496" in why
    assert ib_feed.enabled({}) is False
    ib_feed._port_cache.clear()
    class _Sock:
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(ib_feed.socket, "create_connection", lambda addr, timeout=0: _Sock())
    assert ib_feed.port({}) == (4002, "detected") and ib_feed.enabled({}) is True
    assert ib_feed.enabled({"TAPE_SOURCE": "yahoo"}) is False
    assert ib_feed.enabled({"IB_GATEWAY": "0"}) is False
    ib_feed._port_cache.clear()


def test_tape_compute_uses_ibkr_rows_and_labels_the_source(monkeypatch, capsys):
    rows = [(dt.datetime(2026, 9, 24, 7, 12, tzinfo=ET), 7.1, 7.2, 7.1, 7.18, 42_000),
            (dt.datetime(2026, 9, 24, 7, 14, tzinfo=ET), 7.18, 7.31, 7.15, 7.31, 61_000)]
    meta = dict(last=7.31, prev=6.90, bid=7.30, ask=7.32, halted=False, quote_error=None,
                quote_time=None, source="ibkr", port=4002, port_label="paper gateway", lib="ib_async")
    monkeypatch.setattr(ib_feed, "enabled", lambda env=None: True)
    monkeypatch.setattr(ib_feed, "fetch", lambda sym, timeout=8: (rows, meta))
    monkeypatch.setattr(tape, "fetch", lambda sym: (_ for _ in ()).throw(AssertionError("yahoo must not be called")))
    d = tape.compute("ABCD")
    assert d["source"] == "ibkr" and d["port"] == 4002 and d["pm_vol"] == 103_000 and d["prev"] == 6.90
    tape.render(d, 2)
    out = capsys.readouterr().out
    assert "ibkr·rt :4002 paper gateway" in out and "yahoo hides" not in out and "vol 103,000" in out


def test_tape_falls_back_to_yahoo_and_says_why(monkeypatch, capsys):
    monkeypatch.setattr(ib_feed, "enabled", lambda env=None: True)
    def down(sym, timeout=8): raise ConnectionRefusedError("Connect call failed ('127.0.0.1', 4002)")
    monkeypatch.setattr(ib_feed, "fetch", down)
    ts = [int(dt.datetime(2026, 9, 24, 7, 12, tzinfo=ET).timestamp()), int(dt.datetime(2026, 9, 24, 7, 14, tzinfo=ET).timestamp())]
    monkeypatch.setattr(tape, "fetch", lambda sym: {
        "meta": {"regularMarketPrice": 6.90, "chartPreviousClose": 6.40, "regularMarketTime": ts[0] - 86400},
        "timestamp": ts,
        "indicators": {"quote": [{"open": [7.1, 7.18], "high": [7.2, 7.31], "low": [7.1, 7.15],
                                  "close": [7.18, 7.31], "volume": [0, 0]}]}})
    d = tape.compute("ABCD")
    assert d["source"] == "yahoo" and d["source_note"].startswith("ibkr unreachable: ConnectionRefusedError")
    tape.render(d, 2)
    out = capsys.readouterr().out
    assert "yahoo" in out and "ibkr unreachable" in out and "yahoo hides most PM volume" in out
