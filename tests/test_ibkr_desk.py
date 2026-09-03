"""IBKR scanner union and the desk worker, offline against tests/fake_ibkr.py."""

from __future__ import annotations

import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from fake_ibkr import FakeIB, FakeTicker, day_bars, minute_bars  # noqa: E402
from momentum_platform.dashboard.ibkr_desk import IbkrDesk  # noqa: E402
from momentum_platform.datasources import ibkr_scanner as sc  # noqa: E402
from momentum_platform.datasources.ibkr_scanner import IbkrError  # noqa: E402

UTC = timezone.utc
T0 = datetime(2026, 9, 3, 14, 0, tzinfo=UTC)          # 10:00 ET


class Clock:
    def __init__(self, now=T0):
        self.now = now

    def __call__(self):
        return self.now


# -- scanner union ---------------------------------------------------------------

def test_scan_union_runs_ten_queries_in_the_band_and_merges_symbols():
    ib = FakeIB(scans={"TOP_PERC_GAIN": ["AAA", "BBB"], "HOT_BY_VOLUME": ["BBB", "CCC"]},
                names={"AAA": "Alpha Corp"})
    found = sc.scan_union(ib, 1.0, 20.0)
    assert len(ib.scan_calls) == 10
    assert {c[0] for c in ib.scan_calls} == set(sc.SCAN_CODES)
    assert {c[1] for c in ib.scan_calls} == set(sc.LOCATIONS)
    assert all(c[2] == 1.0 and c[3] == 20.0 and c[4] == 50 for c in ib.scan_calls)
    assert set(found) - {"__meta__"} == {"AAA", "BBB", "CCC"}
    assert found["BBB"]["scans"] == ["TOP_PERC_GAIN", "HOT_BY_VOLUME"]
    assert found["AAA"]["name"] == "Alpha Corp"
    assert found["__meta__"]["ran"] == 10 and found["__meta__"]["failed"] == 0 and found["__meta__"]["excluded"] == {}


def test_screener_rows_come_from_live_snapshots_and_drop_delayed_names():
    ib = FakeIB(scans={"TOP_PERC_GAIN": ["AAA", "BBB", "CCC", "DDD"]},
                quotes={"AAA": FakeTicker(last=4.4, close=4.0, volume=1_000_000),
                        "BBB": FakeTicker(last=4.1, close=4.0),
                        "CCC": FakeTicker(last=9.0, close=6.0),
                        "DDD": FakeTicker(last=30.0, close=20.0)},
                delayed={"CCC"})
    out = sc.build_ibkr_screener(ib, 1.0, 20.0, min_gain=5.0, clock=Clock())
    assert [r["symbol"] for r in out["rows"]] == ["AAA"], "BBB under min gain, CCC delayed, DDD over band"
    row = out["rows"][0]
    assert row["change_pct"] == 10.0 and row["source"] == "ibkr" and row["as_of"] == "2026-09-03T14:00:00Z"
    assert out["source"] == "ibkr" and "not an exhaustive list" in out["notes"][0]
    assert any("DELAYED" in n for n in out["notes"])


# -- reference records -------------------------------------------------------------

def test_reference_uses_the_last_completed_day_for_previous_close():
    bars = [{"d": d, "o": o, "h": h, "l": l, "c": c, "v": v} for d, o, h, l, c, v in day_bars(25)]
    bars.append({"d": "2026-09-03", "o": 4.5, "h": 5.5, "l": 4.4, "c": 5.2, "v": 900_000})   # today, partial
    ref = sc.reference_record("AAA", bars, ticker=FakeTicker(last=5.2, bid=5.19, ask=5.21),
                              exchange="NASDAQ", today="2026-09-03",
                              sec={"shares": 12_000_000, "as_of": "2026-06-30"})
    assert ref["prev_close"] == pytest.approx(3.99)
    assert ref["high_52w"] == 5.5 and ref["avg_daily_volume"] > 0
    assert ref["iex_last_price"] == 5.2 and ref["last_source"] == "ibkr"
    assert ref["float_quality"] == "shares_outstanding_proxy" and ref["float_shares"] == 12_000_000


# -- desk ---------------------------------------------------------------------------

def make_desk(**kw):
    start = T0 - timedelta(minutes=30)
    ib = FakeIB(daily={"AAA": day_bars(30, 4.0), "BBB": day_bars(30, 8.0)},
                minutes={"AAA": minute_bars(start, 30, 4.0), "BBB": minute_bars(start, 30, 8.0)},
                quotes={"AAA": FakeTicker(last=4.35, close=3.99, bid=4.34, ask=4.36),
                        "BBB": FakeTicker(last=8.1, close=7.99)},
                scans={"TOP_PERC_GAIN": ["AAA", "CCC"]})
    ib.quotes["CCC"] = FakeTicker(last=6.0, close=5.0)
    ib.daily["CCC"], ib.minutes["CCC"] = day_bars(30, 5.0), minute_bars(start, 30, 5.0)
    clock = Clock()
    desk = IbkrDesk(["AAA", "BBB"], ib_factory=lambda: ib, clock=clock, headlines=False, sec=False, **kw)
    desk.log = lambda m: None
    return desk, ib, clock


def test_bootstrap_connects_read_only_and_builds_a_live_session():
    desk, ib, clock = make_desk()
    session = desk._bootstrap()
    assert ib.connect_calls[0] == {"host": "127.0.0.1", "port": 7496, "clientId": 27, "readonly": True, "timeout": 12.0}
    assert ib.md_type == 1
    assert session["live"] is True and session["streaming"] is True
    assert session["dataStatus"] == "live" and session["generatedFrom"].startswith("IBKR")
    assert set(session["symbols"]) == {"AAA", "BBB"}
    assert session["symbols"]["AAA"]["prevClose"] == pytest.approx(3.99)
    assert session["symbols"]["AAA"]["iexLast"] == 4.35
    assert len(session["frames"]) == 30, "one frame per minute of history"
    assert session["provider"]["readOnly"] is True and session["provider"]["clientId"] == 27
    assert desk.current() is session


def test_bootstrap_failure_is_a_clear_error_not_a_traceback():
    desk, ib, clock = make_desk()
    ib.fail_connects = 1
    with pytest.raises(IbkrError) as exc:
        desk._bootstrap()
    assert "7496" in str(exc.value) and "ibkr_preflight" in str(exc.value)


def test_live_bars_flow_into_the_session_and_the_stream():
    desk, ib, clock = make_desk()
    desk._bootstrap()
    base = desk.hub.last_id
    for i in range(12):
        clock.now = T0 + timedelta(seconds=5 * i + 5)
        ib.push_bar("AAA", T0 + timedelta(seconds=5 * i), 4.4 + 0.01 * i, 4.45, 4.39, 4.41 + 0.01 * i, 500)
        desk.tick()
    events = desk.hub.since(base)
    kinds = [e.type for e in events]
    assert kinds.count("bar10s") == 6, "six ten-second candles from twelve five-second bars"
    assert "quote" in kinds and "health" in kinds
    session = desk.refresh_session()
    tens = session["bars10s"]["AAA"]
    assert len(tens) == 6 and tens[0][0] == int(T0.timestamp()) and tens[0][5] == 1000
    assert session["frames"][-1]["ts"] == "2026-09-03T14:00:00Z", "the live minute is the newest frame"
    assert len(session["frames"]) == 31
    aaa_minute = [b for b in session["bars"]["AAA"] if b[0] == int(T0.timestamp())]
    assert aaa_minute and aaa_minute[0][5] == 6000, "the minute is the sum of its ten-second candles"


def test_history_minutes_are_dropped_where_the_live_store_covers_them():
    desk, ib, clock = make_desk()
    desk._bootstrap()
    # history already has a bar for 14:00 - 30 min .. ; push live bars into the LAST history minute
    last_hist = T0 - timedelta(minutes=1)
    for i in range(12):
        ib.push_bar("AAA", last_hist + timedelta(seconds=5 * i), 4, 4, 4, 4, 100)
    session = desk.refresh_session()
    at = [b for b in session["bars"]["AAA"] if b[0] == int(last_hist.timestamp())]
    assert len(at) == 1 and at[0][5] == 1200, "no double counting between history and the store"


def test_health_goes_stale_then_reconnects_and_resubscribes(monkeypatch):
    from momentum_platform.datasources import ibkr_stream as mod
    monkeypatch.setattr(mod.time, "sleep", lambda *_: None)
    desk, ib, clock = make_desk()
    desk._bootstrap()
    ib.push_bar("AAA", T0, 4, 4, 4, 4, 100)
    desk.tick()
    assert desk.health()["state"] == "LIVE"
    clock.now = T0 + timedelta(seconds=30)
    desk.tick()
    assert desk.health()["state"] == "STALE"
    ib.connected = False
    desk.tick()                     # OFFLINE -> reconnect inside the same tick
    assert ib.connected and desk.health()["generation"] == 2 and desk.health()["reconnects"] == 1
    assert desk.stream.symbols == ["AAA", "BBB"]
    assert ib.live_lines.count(("rtb", "AAA")) == 2


def test_scan_publishes_the_screener_and_puts_new_runners_on_the_desk():
    desk, ib, clock = make_desk(rescan=60)
    desk._bootstrap()
    out = desk.scan()
    assert ib.connect_calls[1]["clientId"] == 28 and ib.connect_calls[1]["readonly"] is True
    assert [r["symbol"] for r in out["rows"]] == ["CCC"], "AAA is already on the desk but still a row; CCC is new"  # noqa
    assert desk.symbols == ["AAA", "BBB", "CCC"]
    assert "CCC" in desk.stream.symbols
    kinds = [e.type for e in desk.hub.since(0)]
    assert "screener" in kinds and "symbol-added" in kinds
    assert desk.screener.current()["source"] == "ibkr"


def test_desk_respects_the_symbol_cap_and_ignores_duplicates():
    desk, ib, clock = make_desk(max_symbols=3)
    desk._bootstrap()
    assert desk.add_symbols(["aaa", "CCC", "DDD"]) == ["CCC"]
    assert desk.symbols == ["AAA", "BBB", "CCC"]


def test_add_symbols_from_another_thread_is_queued_to_the_worker():
    desk, ib, clock = make_desk()
    desk._bootstrap()
    desk._worker_thread = threading.main_thread()      # this test thread plays the worker
    got = {}

    def other():
        got["r"] = desk.add_symbols(["CCC"])
    t = threading.Thread(target=other)
    t.start(); t.join()
    assert got["r"] == ["CCC"], "the caller learns what will join"
    assert "CCC" not in desk.stream.symbols, "not subscribed yet: the worker owns TWS"
    desk.run_pending()
    assert "CCC" in desk.stream.symbols and "CCC" in desk.current()["symbols"]


def test_no_order_surface_anywhere_in_the_ibkr_path():
    import inspect
    from momentum_platform.dashboard import ibkr_desk
    for mod in (ibkr_desk, sc):
        src = inspect.getsource(mod)
        for word in ("placeOrder", "cancelOrder", "reqOpenOrders", "whatIfOrder"):
            assert word not in src, f"{mod.__name__} mentions {word}"


def test_scan_hits_are_prioritised_and_capped_with_every_top_gainer_kept():
    found = {f"G{i}": {"symbol": f"G{i}", "scans": ["TOP_PERC_GAIN"], "contract": None, "exchange": "NASDAQ"} for i in range(100)}
    found.update({f"M{i}": {"symbol": f"M{i}", "scans": ["HOT_BY_VOLUME", "MOST_ACTIVE"], "contract": None, "exchange": "NASDAQ"} for i in range(100)})
    found.update({f"S{i}": {"symbol": f"S{i}", "scans": ["MOST_ACTIVE"], "contract": None, "exchange": "NASDAQ"} for i in range(200)})
    found["__meta__"] = {"ran": 10, "failed": 0}
    picked = sc.prioritise(found, 150)
    assert len(picked) == 150
    assert all(e["symbol"].startswith("G") for e in picked[:100]), "every TOP_PERC_GAIN hit is quoted"
    assert all(e["symbol"].startswith("M") for e in picked[100:]), "then names several scans agree on"


def test_tws_scanner_cancel_acknowledgements_are_filtered_from_the_log():
    import logging
    from momentum_platform.dashboard.ibkr_desk import quiet_tws_logs
    quiet_tws_logs()
    lg = logging.getLogger("ib_async.wrapper")
    rec = lg.makeRecord("ib_async.wrapper", logging.ERROR, __file__, 1,
                        "Error 162, reqId 3: Historical Market Data Service error message:API scanner subscription cancelled: 3", (), None)
    assert not all(f.filter(rec) for f in lg.filters), "the acknowledgement is dropped"
    real = lg.makeRecord("ib_async.wrapper", logging.ERROR, __file__, 1, "Error 10197: No market data during competing live session", (), None)
    assert all(f.filter(real) for f in lg.filters), "a real error still shows"


def test_bootstrap_without_symbols_lets_the_scanner_pick_the_desk():
    desk, ib, clock = make_desk(rescan=60)
    desk.symbols = []
    session = desk._bootstrap()
    assert desk.symbols == ["CCC"], "only names up >= min gain in the band (AAA is +9%) become the desk"
    assert set(session["symbols"]) == {"CCC"}


def test_funds_are_dropped_by_contract_details_even_when_the_scan_hit_says_nothing():
    """Scanner hits carry no instrument type. CRCG, HODU, MSTX and MSTP — all
    leveraged ETFs — reached the desk as "top gainers" because of that."""
    from momentum_platform.datasources import ibkr_scanner as mod
    mod._STOCK_TYPES.clear()
    ib = FakeIB(scans={"TOP_PERC_GAIN": ["AAA", "CRCG", "MSTX"]},
                quotes={"AAA": FakeTicker(last=4.4, close=4.0), "CRCG": FakeTicker(last=22.0, close=17.0),
                        "MSTX": FakeTicker(last=16.0, close=12.0)},
                types={"CRCG": "ETF", "MSTX": "ETF"})
    out = sc.build_ibkr_screener(ib, 1.0, 30.0, min_gain=5.0, clock=Clock())
    assert [r["symbol"] for r in out["rows"]] == ["AAA"]
    assert any("non-stock instruments excluded" in n and "CRCG" in n for n in out["notes"])
    assert ib.detail_calls.count("CRCG") == 1
    sc.build_ibkr_screener(ib, 1.0, 30.0, min_gain=5.0, clock=Clock())
    assert ib.detail_calls.count("CRCG") == 1, "the type is resolved once per process, not per round"


def test_the_desk_refuses_a_fund_and_keeps_the_stocks():
    from momentum_platform.datasources import ibkr_scanner as mod
    mod._STOCK_TYPES.clear()
    desk, ib, clock = make_desk()
    ib.types["BBB"] = "ETF"
    desk._bootstrap()
    assert desk.symbols == ["AAA"] and desk.stream.symbols == ["AAA"]


def test_fundamentals_are_asked_once_when_the_account_is_not_entitled():
    from momentum_platform.datasources import ibkr_scanner as mod
    mod._STOCK_TYPES.clear()
    desk, ib, clock = make_desk()
    desk._bootstrap()
    desk._on_tws_error(37, 10358, "Fundamentals data is not allowed.", None)
    assert desk.fundamentals is False
    calls = []
    ib.reqFundamentalData = lambda *a, **k: calls.append(a) or ""
    desk.add_symbols(["CCC"])
    assert calls == [], "no further fundamentals requests after TWS said no"
    assert desk._reference["CCC"]["float_quality"] in ("unknown", "shares_outstanding_proxy")


def test_minute_history_is_refreshed_so_the_session_keeps_advancing():
    """The desk used to fetch minute history once at subscribe time. On a quiet
    name IBKR sends no TRADES bars at all, so nothing advanced and the newest
    frame stayed at the startup minute while the clock ran on for hours."""
    desk, ib, clock = make_desk()
    desk._bootstrap()
    first = desk.current()["frames"][-1]["ts"]

    # the market moves on: ten more minutes of history exist now
    for sym in ("AAA", "BBB"):
        start = T0 - timedelta(minutes=30)
        ib.minutes[sym] = minute_bars(start, 40, 4.0)
    # one symbol per cycle, round-robin, to stay inside IBKR's pacing limit
    assert desk.refresh_history() == "AAA"
    assert desk.refresh_history() == "BBB"
    assert desk.refresh_history() == "AAA", "round-robin, not every symbol at once"
    session = desk.refresh_session()
    assert session["frames"][-1]["ts"] > first, "the session must reach the newer minutes"


def test_the_session_reports_how_far_behind_its_data_is():
    desk, ib, clock = make_desk()
    session = desk._bootstrap()
    assert session["dataThrough"] == session["frames"][-1]["ts"]
    assert session["dataLagSeconds"] is not None and session["dataLagSeconds"] < 120
    clock.now = T0 + timedelta(hours=7)
    session = desk.refresh_session()
    assert session["dataLagSeconds"] > 6 * 3600, "a frozen session must say so"
    assert session["provider"]["dataLagSeconds"] == session["dataLagSeconds"]


def test_history_refresh_asks_for_a_short_window(monkeypatch):
    desk, ib, clock = make_desk()
    desk._bootstrap()
    ib.hist_calls.clear()
    desk.refresh_history()
    mins = [c for c in ib.hist_calls if c[2] == "1 min"]
    assert mins and mins[0][1] == "900 S", "a rolling refresh, not the whole day again"
