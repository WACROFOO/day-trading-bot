"""The desk's Time & Sales (owner, 2026-10-08): the tape model, the IBKR
tick-by-tick adapter against tests/fake_ibkr.py, the desk wiring, the hub and
the server routes. Read-only throughout; a print's side is a fact only
against the quote that stood; a gap is said, never smoothed."""

from __future__ import annotations

import inspect
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from fake_ibkr import FakeIB, Obj  # noqa: E402
from test_desk_card import fixture_server  # noqa: E402,F401 — the replay server
from momentum_platform import tape as T  # noqa: E402
from momentum_platform.datasources import ibkr_tape as IT  # noqa: E402
from momentum_platform.datasources.ibkr_stream import IbkrStream  # noqa: E402

UTC = timezone.utc
T0 = datetime(2026, 10, 8, 13, 41, 0, tzinfo=UTC)        # 09:41 ET


class Clock:
    def __init__(self, now=T0):
        self.now = now

    def __call__(self):
        return self.now

    def step(self, s):
        self.now += timedelta(seconds=s)


class Mono:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


# ------------------------------------------------------------------ the model

def test_a_prints_side_is_read_against_the_quote_that_stood():
    assert T.side_of(7.21, 7.20, 7.21) == "ask"
    assert T.side_of(7.25, 7.20, 7.21) == "ask", "through the offer is still the buyer"
    assert T.side_of(7.20, 7.20, 7.21) == "bid"
    assert T.side_of(7.205, 7.20, 7.21) == "mid"
    assert T.side_of(7.21, None, 7.21) == "?", "no two-sided quote, no side"
    assert T.side_of(7.21, 7.25, 7.21) == "?", "a crossed quote reads nothing"


def test_the_facts_count_shares_by_side_over_the_window():
    clock = Clock()
    b = T.TapeBook("abcd", clock=clock)
    b.live_from(T0)
    b.quote(7.20, 7.21)
    for i in range(30):
        clock.step(1)
        b.add_print(clock.now, 7.21, 300)                 # lifted the offer
    for i in range(10):
        clock.step(1)
        b.add_print(clock.now, 7.20, 300)                 # hit the bid
    f = b.facts()
    assert f["atAsk"] == 9000 and f["atBid"] == 3000 and f["pctAsk"] == 75.0
    assert f["prints"] == 40 and f["perMin"] == 60.0
    assert b.state == "LIVE" and b.symbol == "ABCD"
    now = b.facts(10)
    assert now["atAsk"] == 0 and now["pctBid"] == 100.0, "the last ten seconds were all on the bid"


def test_a_big_print_is_measured_against_this_tape_with_a_floor():
    clock = Clock()
    b = T.TapeBook("ABCD", clock=clock)
    b.quote(7.20, 7.21)
    for _ in range(50):
        clock.step(1)
        b.add_print(clock.now, 7.21, 100)
    assert b.big_line() == T.BIG_FLOOR, "10 × a 100-share median is under the floor"
    clock.step(1)
    b.add_print(clock.now, 7.22, 5000)
    snap = b.snapshot()
    assert snap["prints"][0]["s"] == 5000 and snap["prints"][0]["big"] is True
    assert snap["facts"]["big"] == 1 and snap["facts"]["lastBig"]["s"] == 5000
    assert snap["rule"]["label"] == "Approximation"


def test_history_has_no_side_and_never_counts_in_the_facts():
    clock = Clock()
    b = T.TapeBook("ABCD", clock=clock)
    rows = [(T0 - timedelta(seconds=30 - i), 7.10 + i / 100, 200, "NASDAQ", "") for i in range(5)]
    assert b.add_history(rows) == 5
    assert b.add_history(rows) == 0, "a print already on the tape is not added twice"
    b.live_from(T0)
    b.quote(7.20, 7.21)
    clock.step(2)
    b.add_print(clock.now, 7.21, 100)
    snap = b.snapshot()
    assert [p["src"] for p in snap["prints"]] == ["live"] + ["hist"] * 5, "newest first"
    assert all(p["side"] == "?" for p in snap["prints"] if p["src"] == "hist")
    assert snap["facts"]["prints"] == 1 and snap["facts"]["shares"] == 100
    late = [(T0 + timedelta(seconds=1), 7.30, 999, "", "")]
    assert b.add_history(late) == 0, "the live stream owns everything from its start"


def test_a_gap_is_said_and_the_facts_restart_after_it():
    clock = Clock()
    b = T.TapeBook("ABCD", clock=clock)
    b.quote(7.20, 7.21)
    for _ in range(20):
        clock.step(1)
        b.add_print(clock.now, 7.21, 100)
    b.gap("the IBKR connection was rebuilt")
    clock.step(3)
    b.add_print(clock.now, 7.20, 100)
    snap = b.snapshot()
    assert snap["gaps"][0]["why"].startswith("the IBKR connection")
    assert snap["facts"]["prints"] == 1 and snap["facts"]["pctBid"] == 100.0
    assert snap["facts"]["perMin"] is None, "three seconds of tape is not a rate"


def test_a_silent_tape_says_quiet_then_comes_back():
    clock = Clock()
    b = T.TapeBook("ABCD", clock=clock)
    b.add_print(clock.now, 7.21, 100)
    clock.step(45)
    b.check_quiet()
    assert b.state == "QUIET" and b.message == "no print for 45 s"
    b.add_print(clock.now, 7.22, 100)
    assert b.state == "LIVE"


def test_with_no_tape_the_snapshot_says_why_and_holds_nothing():
    off = T.off_snapshot("no tape in this replay")
    assert off["state"] == "OFF" and off["prints"] == [] and off["facts"] is None
    assert off["message"] == "no tape in this replay"


# ---------------------------------------------------------- the IBKR adapter

def _feed(ticks=None, refuse=(), symbols=("ABCD", "WXYZ")):
    ib = FakeIB(ticks=ticks or {}, refuse_tbt=refuse)
    clock, mono = Clock(), Mono()
    s = IbkrStream(ib=ib, clock=clock)
    s.connect()
    s.subscribe(list(symbols), backfill_seconds=0)
    return IT.TapeFeed(s, clock=clock, monotonic=mono), ib, clock, mono


def _batch(ticker, *ticks):
    ticker.tickByTicks = list(ticks)
    ticker.updateEvent.emit(ticker)
    ticker.tickByTicks = []


def _ba(bid, ask, t=T0):
    return Obj(time=t, bidPrice=bid, askPrice=ask, bidSize=100, askSize=100)


def _last(price, size, t=T0, unreported=False):
    return Obj(time=t, price=price, size=size, exchange="NASDAQ", specialConditions="",
               tickAttribLast=Obj(pastLimit=False, unreported=unreported))


def test_focus_opens_last_and_bidask_and_loads_history():
    hist = {"ABCD": [(T0 - timedelta(seconds=20 - i), 7.15, 100) for i in range(10)]}
    feed, ib, clock, mono = _feed(ticks=hist)
    snap = feed.focus("abcd")
    assert ("tbt:Last", "ABCD") in ib.live_lines and ("tbt:BidAsk", "ABCD") in ib.live_lines
    assert ("ABCD", "ticks", IT.HISTORY_TICKS, False) in ib.hist_calls
    assert snap["state"] == "STARTING" and len(snap["prints"]) == 10
    assert any("their side is not known" in n for n in snap["notes"])
    t = ib.tickers["ABCD"]
    _batch(t, _ba(7.20, 7.21), _last(7.21, 400), _last(7.20, 100), _last(7.30, 50, unreported=True))
    snap = feed.snapshot()
    assert snap["state"] == "LIVE"
    live = [p for p in snap["prints"] if p["src"] == "live"]
    assert [(p["p"], p["side"]) for p in live] == [(7.20, "bid"), (7.21, "ask")], "unreported prints skipped"


def test_history_loads_without_blocking_the_worker_on_the_async_api():
    """On the real ib_async the history request is scheduled on the worker's
    loop and lands while ib.sleep() pumps it: a fresh focus never stalls the
    desk's rebuilds waiting for IBKR."""
    import asyncio
    feed, ib, clock, mono = _feed()

    async def history_async(c, start, end, n, what, rth):
        await asyncio.sleep(0)
        return [Obj(time=T0 - timedelta(seconds=5), price=7.10, size=100, exchange="", specialConditions="")]
    ib.reqHistoricalTicksAsync = history_async
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        feed.focus("ABCD")
        assert feed.snapshot()["prints"] == [], "in flight: focus() returned at once"
        loop.run_until_complete(asyncio.sleep(0.05))
        assert [p["src"] for p in feed.snapshot()["prints"]] == ["hist"]
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def test_a_new_focus_cancels_the_old_streams():
    feed, ib, clock, mono = _feed()
    feed.focus("ABCD")
    feed.focus("WXYZ")
    assert ("tbt:Last", "ABCD") in ib.cancelled and ("tbt:BidAsk", "ABCD") in ib.cancelled
    assert feed.symbol == "WXYZ" and ("tbt:Last", "WXYZ") in ib.live_lines
    old = ib.tickers["ABCD"]
    assert old.updateEvent.handlers == [], "the old ticker no longer feeds the tape"


def test_ibkr_pacing_delays_a_second_request_for_the_same_name():
    feed, ib, clock, mono = _feed()
    feed.focus("ABCD")
    feed.focus("WXYZ")
    snap = feed.focus("ABCD")
    assert snap["state"] == "STARTING" and "every 15 s" in snap["message"]
    assert ib.live_lines.count(("tbt:Last", "ABCD")) == 1
    mono.t += IT.PACING_S
    feed.check()
    assert ib.live_lines.count(("tbt:Last", "ABCD")) == 2


def test_bidask_refused_falls_back_to_level1_and_says_so():
    feed, ib, clock, mono = _feed(refuse=("BidAsk",))
    feed.focus("ABCD")
    t = ib.tickers["ABCD"]
    t.bid, t.ask = 7.20, 7.21
    _batch(t, _last(7.21, 300))
    snap = feed.snapshot()
    assert "Level 1" in snap["source"] and any("Approximation" in n for n in snap["notes"])
    assert snap["prints"][0]["side"] == "ask"


def test_refusals_and_lost_connections_are_said_on_the_tape():
    feed, ib, clock, mono = _feed()
    feed.focus("ABCD")
    feed.on_error(9, 10190, "Max number of tick-by-tick requests has been reached", Obj(symbol="ABCD"))
    assert feed.snapshot()["state"] == "ERROR" and "tick-by-tick limit" in feed.snapshot()["message"]
    feed, ib, clock, mono = _feed()
    feed.focus("ABCD")
    feed.on_error(9, 10089, "needs a subscription", Obj(symbol="WXYZ"))
    assert feed.snapshot()["state"] != "ERROR", "another name's refusal is not this tape's"
    feed.on_error(-1, 10197, "competing live session", None)
    snap = feed.snapshot()
    assert snap["state"] == "PAUSED" and snap["gaps"] and "10197" in snap["gaps"][0]["why"]


def test_a_rebuilt_connection_resubscribes_behind_a_gap():
    feed, ib, clock, mono = _feed()
    feed.focus("ABCD")
    feed.stream.health.generation += 1
    mono.t += IT.PACING_S
    feed.check()
    snap = feed.snapshot()
    assert snap["gaps"] and "rebuilt" in snap["gaps"][0]["why"]
    assert ib.live_lines.count(("tbt:Last", "ABCD")) == 2


def test_a_name_off_the_desk_or_without_data_gets_no_request():
    feed, ib, clock, mono = _feed(symbols=("ABCD",))
    assert feed.focus("NOPE")["state"] == "ERROR"
    feed.stream.banned = {"ABCD"}
    assert feed.focus("ABCD")["state"] == "ERROR"
    assert not any(k.startswith("tbt:") for k, _ in ib.live_lines)


def test_the_tape_adapter_has_no_order_surface():
    for mod in (IT, T):
        src = inspect.getsource(mod)
        for word in ("placeOrder", "cancelOrder", "reqOpenOrders", "whatIfOrder", "reqGlobalCancel",
                     "import execution", "from execution"):
            assert word not in src, f"{mod.__name__} mentions {word}"


# ------------------------------------------------------- desk, hub and server

def test_the_hub_delivers_a_tape_but_never_keeps_it_for_replay():
    from momentum_platform.dashboard.stream import EventHub
    hub = EventHub()
    q = hub.subscribe()
    first = hub.publish("bar1m", {"x": 1})
    hub.publish("tape", {"symbol": "ABCD"})
    assert q.get_nowait().type == "bar1m" and q.get_nowait().type == "tape"
    assert [e.type for e in hub.since(first.id - 1)] == ["bar1m"]


def test_the_desk_publishes_the_focus_tape_only_when_it_moved():
    from momentum_platform.dashboard.ibkr_desk import IbkrDesk
    from momentum_platform.dashboard.stream import EventHub
    feed, ib, clock, mono = _feed()
    desk = IbkrDesk.__new__(IbkrDesk)
    desk.hub, desk.tape, desk._tape_sent = EventHub(), feed, -1
    desk._worker_thread = None
    q = desk.hub.subscribe()
    desk.focus("ABCD")
    assert q.get_nowait().data["symbol"] == "ABCD"
    desk._publish_tape()
    assert q.empty(), "nothing moved, nothing sent"
    _batch(ib.tickers["ABCD"], _ba(7.20, 7.21), _last(7.21, 100))
    desk._publish_tape()
    assert q.get_nowait().data["state"] == "LIVE"
    desk.stream = feed.stream
    desk.client_id, desk.scanner_client_id, desk.built_at, desk.no_live_data = 27, 28, 0, set()
    assert desk.health()["tape"] == {"symbol": "ABCD", "state": "LIVE",
                                     "streams": ["Last", "BidAsk"], "quoteFromL1": False}


def test_a_tws_error_reaches_the_tape():
    from momentum_platform.dashboard.ibkr_desk import IbkrDesk
    feed, ib, clock, mono = _feed()
    feed.focus("ABCD")
    desk = IbkrDesk.__new__(IbkrDesk)
    desk.stream, desk.tape = feed.stream, feed
    desk.no_live_data, desk.symbols, desk.fundamentals = set(), ["ABCD"], None
    desk.competing_since, desk._next_competing_note, desk.clock = None, 0.0, clock
    desk.log = lambda m: None
    desk._on_tws_error(9, 10190, "Max number of tick-by-tick requests has been reached", Obj(symbol="ABCD"))
    assert feed.snapshot()["state"] == "ERROR"


def test_a_replay_says_it_has_no_tape(fixture_server):
    from urllib.request import Request, urlopen
    with urlopen(fixture_server + "/api/v1/tape") as r:
        snap = json.loads(r.read())
    assert snap["state"] == "OFF" and "no tape in this replay" in snap["message"]
    req = Request(fixture_server + "/api/v1/focus", data=json.dumps({"symbol": "ABCD"}).encode(),
                  headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req) as r:
        body = json.loads(r.read())
    assert body == {"focus": "ABCD", "tape": False, "message": snap["message"]}


def test_focus_wants_a_symbol():
    from momentum_platform.dashboard import server as SRV
    assert SRV._focus_post(object(), {"symbol": "<script>"})[1] == 400
    assert SRV._focus_post(object(), {})[1] == 400
    seen = []

    class Live:
        def focus(self, sym):
            seen.append(sym)
    assert SRV._focus_post(Live(), {"symbol": "abcd"}) == ({"focus": "ABCD", "tape": True}, 200)
    assert seen == ["ABCD"]
