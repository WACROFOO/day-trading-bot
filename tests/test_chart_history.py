"""Older candles for the desk's charts (2026-10-13): previous sessions of
one-minute bars and older daily bars, from IBKR on a read-only client of their
own, paced, cached on disk — and never seen by a gate."""

from __future__ import annotations

import http.client
import json
import socket
import sys
import threading
from datetime import date, datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from fake_ibkr import FakeIB, FakeTicker, Obj  # noqa: E402
from momentum_platform.dashboard import chart_history as CH  # noqa: E402
from momentum_platform.dashboard.chart_history import BudgetSpent, ChartHistory  # noqa: E402

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
TODAY = date(2026, 10, 13)                    # a Tuesday
DAYS = [date(2026, 10, 8), date(2026, 10, 9), date(2026, 10, 12)]   # Thu, Fri, Mon (NYSE open)


def et(d: date, hh: int, mm: int) -> datetime:
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=ET).astimezone(UTC)


def session(d: date, price: float, n: int = 30, start=(9, 30)) -> list:
    t0 = et(d, *start)
    return [(t0 + timedelta(minutes=i), price, price + 0.05, price - 0.05, price + 0.01, 1000 + i)
            for i in range(n)]


def seeded(extra_today: bool = True) -> dict:
    mins = []
    for i, d in enumerate(DAYS):
        mins += session(d, 2.0 + i)
        mins.append((et(d, 3, 30), 9.0, 9.0, 9.0, 9.0, 5))        # before 04:00 ET: not the session
        mins.append((et(d, 20, 5), 9.0, 9.0, 9.0, 9.0, 5))        # after 20:00 ET: not the session
        mins.append((et(d, 10, 30), 2.0, 2.0, 2.0, 0.0, 5))       # a zero close: a bad print
    if extra_today:
        mins += session(TODAY, 6.0, n=10)
    return {"AAA": sorted(mins)}


def daily_rows() -> list:
    rows = [(d.isoformat(), 2.0 + i, 2.1 + i, 1.9 + i, 2.01 + i + 0.28, 100_000) for i, d in enumerate(DAYS)]
    return rows + [(TODAY.isoformat(), 6.0, 6.1, 5.9, 6.0, 50_000)]


class Mono:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def make(tmp_path, ib=None, known=True, **kw) -> tuple:
    ib = ib or FakeIB(minutes=seeded(), daily={"AAA": daily_rows()})
    ib.connected = True
    closes = {d: c for d, o, h, l, c, v in daily_rows()} if known else {}
    hist = ChartHistory(ib_factory=lambda: ib, contract_for=lambda s: Obj(symbol=s),
                        daily_closes=lambda s: closes, today=lambda: TODAY,
                        cache_dir=tmp_path, pace_s=kw.pop("pace_s", 0.0), monotonic=kw.pop("monotonic", Mono()), **kw)
    return hist, ib


def one_min_calls(ib) -> list:
    return [c for c in ib.hist_calls if c[2] == "1 min"]


def test_previous_sessions_come_oldest_first_each_one_whole_extended_session(tmp_path):
    hist, ib = make(tmp_path)
    got = hist.minutes("aaa", before="2026-10-13", sessions=2)
    assert [s["day"] for s in got["sessions"]] == ["2026-10-09", "2026-10-12"], "oldest first, the weekend skipped"
    assert got["next_before"] == "2026-10-09" and got["more"] is True and got["note"] is None
    for s in got["sessions"]:
        d = date.fromisoformat(s["day"])
        stamps = [b[0] for b in s["bars"]]
        assert stamps == sorted(stamps) and len(stamps) == 30, "04:00-20:00 ET only, bad prints dropped"
        assert all(et(d, 4, 0).timestamp() <= t < et(d, 20, 0).timestamp() for t in stamps)
        assert all(len(b) == 6 and b[4] > 0 for b in s["bars"]), "[t, o, h, l, c, v] like the session's bars"
    # one "1 D" request a session, extended hours, ending 20:00 ET of that day
    assert [(c[1], c[3]) for c in one_min_calls(ib)] == [("1 D", False), ("1 D", False)]


def test_the_next_page_starts_where_the_last_one_stopped(tmp_path):
    hist, ib = make(tmp_path)
    first = hist.minutes("AAA", before="2026-10-13", sessions=2)
    older = hist.minutes("AAA", before=first["next_before"], sessions=2)
    assert [s["day"] for s in older["sessions"]] == ["2026-10-08"]
    # inside the daily bars' year a day the name did not trade is never asked
    assert len(one_min_calls(ib)) == 3


def test_a_completed_session_is_cached_and_never_asked_again(tmp_path):
    hist, ib = make(tmp_path)
    a = hist.minutes("AAA", before="2026-10-13", sessions=1)
    assert (tmp_path / "AAA" / "2026-10-12.json").is_file()
    fresh, _ = make(tmp_path, ib=ib)                     # a new run on the same disk
    ib.hist_calls.clear()
    b = fresh.minutes("AAA", before="2026-10-13", sessions=1)
    assert b["sessions"] == a["sessions"] and one_min_calls(ib) == []


def test_today_is_served_but_never_cached(tmp_path):
    hist, ib = make(tmp_path)
    got = hist.minutes("AAA", before="2026-10-14", sessions=1)
    assert [s["day"] for s in got["sessions"]] == ["2026-10-13"]
    assert not (tmp_path / "AAA" / "2026-10-13.json").exists(), "an unfinished session is not a past day"


def test_the_budget_stops_the_walk_and_says_when_it_frees(tmp_path):
    mono = Mono()
    hist, ib = make(tmp_path, budget=2, window_s=600.0, monotonic=mono)
    got = hist.minutes("AAA", before="2026-10-13", sessions=3)
    assert [s["day"] for s in got["sessions"]] == ["2026-10-09", "2026-10-12"]
    assert "2 requests in ten minutes" in got["note"] and "client 30" in got["note"]
    assert got["next_before"] == "2026-10-09" and got["more"] is True, "the page asks again later, from there"
    mono.t += 601
    again = hist.minutes("AAA", before=got["next_before"], sessions=1)
    assert [s["day"] for s in again["sessions"]] == ["2026-10-08"]


def test_requests_are_spaced_at_least_the_pace(tmp_path):
    mono = Mono()
    waits = []
    hist, ib = make(tmp_path, pace_s=2.0, monotonic=mono)
    hist._pump = lambda s: (waits.append(round(s, 3)), setattr(mono, "t", mono.t + s))
    hist.minutes("AAA", before="2026-10-13", sessions=3)
    assert waits == [2.0, 2.0], "the first request goes at once, each next one 2 s later"
    with pytest.raises(BudgetSpent):
        hist.budget = 3
        hist._wait_turn()


def test_a_split_since_caching_asks_the_day_again_once(tmp_path):
    hist, ib = make(tmp_path)
    hist.minutes("AAA", before="2026-10-13", sessions=1)            # caches 2026-10-12 near 4.01
    # a 1-for-10 reverse split later: IBKR's history is rescaled, the daily bar with it
    ib.minutes["AAA"] = [(t, o * 10, h * 10, l * 10, c * 10, v) for t, o, h, l, c, v in ib.minutes["AAA"]]
    rows = [(d, o * 10, h * 10, l * 10, c * 10, v) for d, o, h, l, c, v in daily_rows()]
    closes = {d: c for d, o, h, l, c, v in rows}
    fresh = ChartHistory(ib_factory=lambda: ib, contract_for=lambda s: Obj(symbol=s),
                         daily_closes=lambda s: closes, today=lambda: TODAY, cache_dir=tmp_path,
                         pace_s=0.0, monotonic=Mono())
    ib.hist_calls.clear()
    got = fresh.minutes("AAA", before="2026-10-13", sessions=1)
    assert len(one_min_calls(ib)) == 1, "the stale scale is fetched again"
    assert got["sessions"][0]["bars"][-1][4] == pytest.approx(40.1 + 0.0, rel=0.01)
    ib.hist_calls.clear()
    fresh.minutes("AAA", before="2026-10-13", sessions=1)
    assert one_min_calls(ib) == [], "once a run, never in a loop"


def test_a_timeout_is_not_cached_as_an_empty_day(tmp_path):
    mono = Mono()

    class Slow(FakeIB):
        def reqHistoricalData(self, contract, end, duration, size, *a, **kw):
            mono.t += 20.0                               # ib_async gives up and answers []
            return []
    ib = Slow()
    hist, _ = make(tmp_path, ib=ib, monotonic=mono)
    got = hist.minutes("AAA", before="2026-10-13", sessions=1)
    assert got["sessions"] == [] and "did not answer" in got["note"] and got["more"] is True
    assert not any((tmp_path / "AAA").glob("*.json")), "a timeout is not a day without trades"


def test_weekdays_without_bars_end_the_walk(tmp_path):
    ib = FakeIB(minutes={"AAA": []})
    hist, _ = make(tmp_path, ib=ib, known=False)
    got = hist.minutes("AAA", before="2026-10-13", sessions=1)
    assert got["sessions"] == [] and got["more"] is False and got["note"] is None
    assert len(one_min_calls(ib)) == CH.EMPTY_RUN, "before the listing there is nothing older to ask for"


def test_older_daily_bars_end_before_the_oldest_the_page_holds(tmp_path):
    hist, ib = make(tmp_path)
    got = hist.daily("AAA", before="2026-10-12", years=5)
    assert [b["d"] for b in got["bars"]] == ["2026-10-08", "2026-10-09"]
    assert got["more"] is False, "a short answer: the name has nothing older"
    assert [c for c in ib.hist_calls if c[2] == "1 day"] == [("AAA", "5 Y", "1 day", True)]
    hist.daily("AAA", before="2026-10-12", years=5)
    assert len([c for c in ib.hist_calls if c[2] == "1 day"]) == 1, "asked once a run"


def test_its_own_client_connects_read_only(tmp_path):
    own = FakeIB(minutes=seeded())
    hist = ChartHistory(ib_factory=lambda: own, contract_for=lambda s: Obj(symbol=s), today=lambda: TODAY,
                        cache_dir=tmp_path, pace_s=0.0)
    hist.minutes("AAA", before="2026-10-13", sessions=1)
    assert own.connect_calls[0]["clientId"] == 30 and own.connect_calls[0]["readonly"] is True


def test_with_its_thread_running_the_work_leaves_the_callers_thread(tmp_path):
    hist, ib = make(tmp_path)
    seen = []
    real = hist._minutes_job
    hist._minutes_job = lambda *a: (seen.append(threading.current_thread().name), real(*a))[1]
    hist.start()
    try:
        got = hist.minutes("AAA", before="2026-10-13", sessions=1, wait=5)
    finally:
        hist.stop()
    assert seen == ["ibkr-chart-history"] and got["sessions"][0]["day"] == "2026-10-12"


def test_no_order_surface_in_the_chart_history():
    import inspect
    src = inspect.getsource(CH)
    for word in ("placeOrder", "cancelOrder", "reqOpenOrders", "whatIfOrder"):
        assert word not in src, word


# -- the desk: the endpoint, and the gates never see a past session -------------------

class Clock:
    def __init__(self, now):
        self.now = now

    def __call__(self):
        return self.now


@pytest.fixture()
def desk_server(tmp_path, monkeypatch):
    from momentum_platform.dashboard.ibkr_desk import IbkrDesk
    from momentum_platform.dashboard.server import make_handler
    monkeypatch.setattr(CH, "default_cache_dir", lambda: tmp_path)
    ib = FakeIB(daily={"AAA": daily_rows()[:-1]}, minutes=seeded(),
                quotes={"AAA": FakeTicker(last=6.0, close=4.29, bid=5.99, ask=6.01)})
    clock = Clock(et(TODAY, 9, 45))
    desk = IbkrDesk(["AAA"], ib_factory=lambda: ib, clock=clock, headlines=False, sec=False, rescan=0)
    desk.log = lambda m: None
    desk.chart_history.pace_s = 0.0
    desk._bootstrap()
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]; sock.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler("ibkr:AAA", desk, None))
    t = threading.Thread(target=httpd.serve_forever, daemon=True); t.start()
    yield {"desk": desk, "ib": ib, "port": port}
    httpd.shutdown()


def _get(port, path):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request("GET", path)
    r = conn.getresponse()
    body = json.loads(r.read())
    conn.close()
    return r.status, body


def test_the_desk_serves_older_candles_and_no_gate_sees_them(desk_server):
    desk, port = desk_server["desk"], desk_server["port"]
    before = json.dumps(desk.current()["bars"], sort_keys=True)
    today_minutes = list(desk._minutes["AAA"])
    status, got = _get(port, "/api/v1/chart/history?symbol=AAA&tf=1m&sessions=2")
    assert status == 200 and [s["day"] for s in got["sessions"]] == ["2026-10-09", "2026-10-12"]
    desk.refresh_session()
    assert json.dumps(desk.current()["bars"], sort_keys=True) == before, "the session's bars are today's only"
    assert desk._minutes["AAA"] == today_minutes
    first_today = min(b[0] for b in desk.current()["bars"]["AAA"])
    assert first_today >= et(TODAY, 4, 0).timestamp()
    assert desk.chart_history.status()["clientId"] == 30 and desk.chart_history.status()["requests"] == 2


def test_the_endpoint_refuses_what_it_should(desk_server):
    port = desk_server["port"]
    assert _get(port, "/api/v1/chart/history?symbol=ZZZ")[0] == 404, "only a name on the desk"
    assert _get(port, "/api/v1/chart/history?symbol=AAA&before=yesterday")[0] == 400
    assert _get(port, "/api/v1/chart/history?symbol=AAA&tf=1h")[0] == 400
    assert _get(port, "/api/v1/chart/history")[0] == 400
    status, daily = _get(port, "/api/v1/chart/history?symbol=AAA&tf=D&before=2026-10-09")
    assert status == 200 and [b["d"] for b in daily["bars"]] == ["2026-10-08"]


def test_a_replay_says_it_has_no_older_candles():
    from momentum_platform.dashboard.server import NO_HISTORY, _chart_history

    class Replay:
        symbols = ["AAA"]
    body, status = _chart_history(Replay(), "symbol=AAA")
    assert status == 200 and body["sessions"] == [] and body["more"] is False and body["note"] == NO_HISTORY
