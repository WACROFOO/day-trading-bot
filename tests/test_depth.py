"""The desk's Level 2 (owner, 2026-10-09): the book model, the IBKR market-depth
adapter against tests/fake_ibkr.py, the desk wiring, the hub and the server
routes. Read-only throughout: one SmartDepth request for the selected name,
released when the selection moves; no subscription is a state said with
IBKR's exact code; a huge resting order is an Approximation and never a gate."""

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
from momentum_platform import depth as D  # noqa: E402
from momentum_platform.datasources import ibkr_depth as ID  # noqa: E402
from momentum_platform.datasources import ibkr_tape as IT  # noqa: E402
from momentum_platform.datasources.ibkr_stream import IbkrStream  # noqa: E402

UTC = timezone.utc
T0 = datetime(2026, 10, 9, 13, 41, 0, tzinfo=UTC)        # 09:41 ET


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


BIDS = [(6.50, 800, "NSDQ"), (6.50, 400, "ARCA"), (6.49, 1200, "EDGX"), (6.48, 500, "NSDQ"), (6.45, 900, "BATS")]
ASKS = [(6.51, 600, "NSDQ"), (6.52, 700, "ARCA"), (6.53, 400, "IEX"), (6.55, 1000, "NSDQ")]


# ------------------------------------------------------------------ the model
def test_the_book_aggregates_by_price_and_names_each_venue():
    b = D.DepthBook("abcd", clock=Clock())
    assert b.update(BIDS, ASKS)
    s = b.snapshot()
    assert s["state"] == "LIVE" and s["symbol"] == "ABCD"
    assert s["inside"] == {"bid": 6.50, "ask": 6.51, "spread": 0.01}
    assert [(r["p"], r["s"], r["x"]) for r in s["bids"][:2]] == [(6.50, 800, "NSDQ"), (6.50, 400, "ARCA")]
    assert s["bids"][0]["lvl"] == s["bids"][1]["lvl"] == 0 and s["bids"][2]["lvl"] == 1, "one band per price"
    assert s["totals"]["bidLevels"] == 4 and s["totals"]["askLevels"] == 4
    assert s["rule"]["label"] == "Approximation"
    assert not b.update(BIDS, ASKS), "an unchanged book is not news"


def test_a_huge_order_near_the_inside_appears_and_is_pulled():
    """With a 12,000-share ask at the second level the book's median
    price-level size is 950, so the line is 9,500 (10x, never under 2,000):
    the wall is huge. When it vanishes with no print there it was PULLED, and
    the event says so."""
    clock = Clock()
    b = D.DepthBook("ABCD", clock=clock, printed=lambda price, s: 0)
    b.update(BIDS, ASKS)
    wall = [ASKS[0], (6.52, 12000, "NSDQ")] + ASKS[2:]
    b.update(BIDS, wall)
    ev = b.snapshot()["events"][-1]
    assert (ev["kind"], ev["side"], ev["price"], ev["size"], ev["venues"]) == ("appeared", "ask", 6.52, 12000, ["NSDQ"])
    assert ev["line"] == 9500
    assert [r["huge"] for r in b.snapshot()["asks"]][:2] == [False, True]
    clock.step(40)
    b.update(BIDS, ASKS)
    ev = b.snapshot()["events"][-1]
    assert (ev["kind"], ev["how"], ev["printed"]) == ("gone", "pulled", 0)


def test_a_huge_level_eaten_by_the_tape_is_taken_and_without_a_tape_it_is_unknown():
    clock = Clock()
    b = D.DepthBook("ABCD", clock=clock, printed=lambda price, s: 11000 if price == 6.52 else 0)
    b.update(BIDS, ASKS)
    b.update(BIDS, [ASKS[0], (6.52, 12000, "NSDQ")] + ASKS[2:])
    clock.step(40)
    b.update(BIDS, ASKS)
    assert b.snapshot()["events"][-1]["how"] == "taken"
    c = D.DepthBook("ABCD", clock=Clock())
    c.update(BIDS, ASKS)
    c.update(BIDS, [ASKS[0], (6.52, 12000, "NSDQ")] + ASKS[2:])
    c.clock.step(40)
    c.update(BIDS, ASKS)
    assert c.snapshot()["events"][-1]["how"] == "unknown", "no tape on the name: cannot tell"


def test_size_alone_crosses_the_absolute_line_and_far_levels_never_count():
    b = D.DepthBook("ABCD", clock=Clock())
    deep = BIDS + [(6.30, 90000, "NSDQ")]                     # far down the book: not near the inside
    b.update(deep, ASKS)
    assert not b.snapshot()["events"], "a wall five levels down is not at the inside"
    b.update([(6.50, 30000, "NSDQ")] + BIDS[1:], ASKS)       # >= HUGE_ABS at the inside
    assert b.snapshot()["events"][-1]["kind"] == "appeared"


def test_a_level_flapping_at_the_line_says_nothing_new_inside_the_cooldown():
    clock = Clock()
    b = D.DepthBook("ABCD", clock=clock, printed=lambda p, s: 0)
    b.update(BIDS, ASKS)
    wall = [ASKS[0], (6.52, 12000, "NSDQ")] + ASKS[2:]
    for _ in range(3):
        b.update(BIDS, wall)
        clock.step(2)
        b.update(BIDS, ASKS)
        clock.step(2)
    kinds = [e["kind"] for e in b.snapshot()["events"]]
    assert kinds == ["appeared"], kinds


def test_a_cleared_book_calls_nothing_gone():
    b = D.DepthBook("ABCD", clock=Clock())
    b.update(BIDS, [ASKS[0], (6.52, 12000, "NSDQ")] + ASKS[2:])
    b.clear("TWS reconnected (1101)")
    b.update(BIDS, ASKS)
    kinds = [e["kind"] for e in b.snapshot()["events"]]
    assert kinds == ["appeared", "gap"], kinds


def test_with_no_book_the_snapshot_says_why_and_holds_nothing():
    s = D.off_depth("no Level 2 in this replay")
    assert s["state"] == "OFF" and s["bids"] == [] and s["asks"] == [] and "replay" in s["message"]


# ------------------------------------------------------------------ IBKR
def _feed(symbols=("ABCD", "WXYZ")):
    ib = FakeIB()
    clock, mono = Clock(), Mono()
    s = IbkrStream(ib=ib, clock=clock)
    s.connect()
    s.subscribe(list(symbols), backfill_seconds=0)
    return ID.DepthFeed(s, clock=clock, monotonic=mono), ib, clock, mono


def test_focus_asks_for_smart_depth_and_reads_the_book():
    feed, ib, clock, mono = _feed()
    snap = feed.focus("abcd")
    assert ib.depth_calls == [("ABCD", ID.DEPTH_ROWS, True)], "SmartDepth: every exchange, one request"
    assert snap["state"] == "STARTING"
    ib.push_depth("ABCD", BIDS, ASKS)
    snap = feed.snapshot()
    assert snap["state"] == "LIVE" and snap["inside"]["bid"] == 6.50 and snap["bids"][0]["x"] == "NSDQ"


def test_a_new_selection_releases_the_old_book():
    feed, ib, clock, mono = _feed()
    feed.focus("ABCD")
    feed.focus("WXYZ")
    assert ("depth", "ABCD", True) in ib.cancelled, "one depth line at a time"
    assert ib.depth_calls[-1][0] == "WXYZ"
    ib.push_depth("ABCD", BIDS, ASKS)                         # the old name's update is not this book's
    assert feed.snapshot()["symbol"] == "WXYZ" and feed.snapshot()["bids"] == []


def test_no_subscription_is_said_with_ibkrs_exact_code_until_data_flows():
    """Until the owner's depth subscription is on the account IBKR refuses:
    the card says so in IBKR's words and asks again every RETRY_S, so the book
    appears by itself once the subscription is live."""
    feed, ib, clock, mono = _feed()
    feed.focus("ABCD")
    rid = ib.depth_req_id("ABCD")
    feed.on_error(rid, 354, "Not subscribed to requested market data.", Obj(symbol="ABCD"))
    s = feed.snapshot()
    assert s["state"] == "NO_SUBSCRIPTION" and s["code"] == 354
    assert s["message"] == "IBKR 354: Not subscribed to requested market data."
    assert s["retryInS"] == ID.RETRY_S
    feed.check()
    assert len(ib.depth_calls) == 1, "not before the retry is due"
    mono.t += ID.RETRY_S
    feed.check()
    s = feed.snapshot()
    assert len(ib.depth_calls) == 2 and s["state"] == "NO_SUBSCRIPTION", "IBKR's answer stays while it is asked again"
    assert s["askedAgainAt"] == T0.isoformat() and not s["notes"]
    ib.push_depth("ABCD", BIDS, ASKS)                         # the subscription went live
    s = feed.snapshot()
    assert s["state"] == "LIVE" and s["code"] is None and s["message"] == ""


def test_another_requests_error_is_not_the_books():
    feed, ib, clock, mono = _feed()
    feed.focus("ABCD")
    feed.on_error(ib.depth_req_id("ABCD") + 77, 354, "Not subscribed to requested market data.", Obj(symbol="ABCD"))
    assert feed.snapshot()["state"] == "STARTING"


def test_an_unexplained_refusal_retries_once_at_five_rows():
    feed, ib, clock, mono = _feed()
    feed.focus("ABCD")
    feed.on_error(ib.depth_req_id("ABCD"), 321, "Error validating request.", Obj(symbol="ABCD"))
    assert feed.snapshot()["state"] == "ERROR" and feed.snapshot()["code"] == 321
    feed.check()
    assert ib.depth_calls[-1] == ("ABCD", ID.FALLBACK_ROWS, True)
    feed.on_error(ib.depth_req_id("ABCD"), 321, "Error validating request.", Obj(symbol="ABCD"))
    feed.check()
    assert len(ib.depth_calls) == 2, "the fallback is tried once, then the slow retry"


def test_halted_resubscribes_and_reset_empties_the_book():
    feed, ib, clock, mono = _feed()
    feed.focus("ABCD")
    ib.push_depth("ABCD", BIDS, ASKS)
    feed.on_error(ib.depth_req_id("ABCD"), 317, "Market depth data has been RESET. Please empty deep book "
                  "contents before applying any new entries.", Obj(symbol="ABCD"))
    s = feed.snapshot()
    assert s["bids"] == [] and s["events"][-1]["kind"] == "gap" and "317" in s["events"][-1]["why"]
    ib.push_depth("ABCD", BIDS, ASKS)
    feed.on_error(ib.depth_req_id("ABCD"), 316, "Market depth data has been HALTED. Please re-subscribe.",
                  Obj(symbol="ABCD"))
    feed.check()
    assert ("depth", "ABCD", True) in ib.cancelled and len(ib.depth_calls) == 2


def test_a_competing_login_pauses_the_book_and_recovery_asks_again():
    feed, ib, clock, mono = _feed()
    feed.focus("ABCD")
    ib.push_depth("ABCD", BIDS, ASKS)
    feed.on_error(-1, 10197, "No market data during competing session", None)
    assert feed.snapshot()["state"] == "PAUSED" and feed.snapshot()["bids"] == []
    feed.on_error(-1, 1102, "Connectivity between IB and TWS has been restored- data maintained.", None)
    feed.check()
    assert len(ib.depth_calls) == 2
    ib.push_depth("ABCD", BIDS, ASKS)
    assert feed.snapshot()["state"] == "LIVE"


def test_a_rebuilt_connection_resubscribes_behind_a_gap():
    feed, ib, clock, mono = _feed()
    feed.focus("ABCD")
    ib.push_depth("ABCD", BIDS, ASKS)
    feed.stream.health.generation += 1
    feed.check()
    assert len(ib.depth_calls) == 2
    assert any(e["kind"] == "gap" and "rebuilt" in e["why"] for e in feed.snapshot()["events"])


def test_a_name_off_the_desk_or_banned_gets_no_request():
    feed, ib, clock, mono = _feed(symbols=("ABCD",))
    assert feed.focus("NOPE")["state"] == "ERROR"
    feed.stream.banned = {"ABCD"}
    assert feed.focus("ABCD")["state"] == "ERROR"
    assert ib.depth_calls == []


def test_the_tape_tells_taken_from_pulled_on_the_same_name():
    """The desk's tape prints at the wall's price make it TAKEN."""
    ib = FakeIB()
    clock, mono = Clock(), Mono()
    s = IbkrStream(ib=ib, clock=clock)
    s.connect()
    s.subscribe(["ABCD"], backfill_seconds=0)
    tape = IT.TapeFeed(s, clock=clock, monotonic=mono, history=False)
    feed = ID.DepthFeed(s, clock=clock, monotonic=mono, tape=lambda: tape)
    tape.focus("ABCD")
    feed.focus("ABCD")
    ib.push_depth("ABCD", BIDS, ASKS)
    ib.push_depth("ABCD", BIDS, [ASKS[0], (6.52, 12000, "NSDQ")] + ASKS[2:])
    clock.step(35)
    tape.book.add_print(clock(), 6.52, 11800, "NSDQ")
    ib.push_depth("ABCD", BIDS, ASKS)
    ev = feed.snapshot()["events"][-1]
    assert (ev["kind"], ev["how"], ev["printed"]) == ("gone", "taken", 11800)


def test_the_depth_adapter_has_no_order_surface():
    for mod in (ID, D):
        src = inspect.getsource(mod)
        for word in ("placeOrder", "cancelOrder", "reqOpenOrders", "whatIfOrder", "reqGlobalCancel",
                     "import execution", "from execution"):
            assert word not in src, f"{mod.__name__} mentions {word}"


# ------------------------------------------------------- desk, hub and server
def test_the_hub_delivers_a_book_but_never_keeps_it_for_replay():
    from momentum_platform.dashboard.stream import EventHub
    hub = EventHub()
    q = hub.subscribe()
    first = hub.publish("bar1m", {"x": 1})
    hub.publish("depth", {"symbol": "ABCD"})
    assert q.get_nowait().type == "bar1m" and q.get_nowait().type == "depth"
    assert [e.type for e in hub.since(first.id - 1)] == ["bar1m"]


def test_the_desk_moves_the_book_with_the_selection_and_reports_it():
    from momentum_platform.dashboard.ibkr_desk import IbkrDesk
    from momentum_platform.dashboard.stream import EventHub
    feed, ib, clock, mono = _feed()
    desk = IbkrDesk.__new__(IbkrDesk)
    desk.hub, desk.depth, desk._depth_sent, desk.tape = EventHub(), feed, -1, None
    desk._worker_thread = None
    q = desk.hub.subscribe()
    desk.focus("ABCD")
    first = q.get_nowait()
    assert first.type == "depth" and first.data["symbol"] == "ABCD"
    desk._publish_depth()
    assert q.empty(), "nothing moved, nothing sent"
    ib.push_depth("ABCD", BIDS, ASKS)
    desk._publish_depth()
    assert q.get_nowait().data["state"] == "LIVE"
    desk.stream = feed.stream
    desk.client_id, desk.scanner_client_id, desk.built_at, desk.no_live_data = 27, 28, 0, set()
    assert desk.health()["depth"] == {"symbol": "ABCD", "state": "LIVE", "code": None,
                                      "rows": ID.DEPTH_ROWS, "active": True}


def test_a_tws_error_reaches_the_book():
    from momentum_platform.dashboard.ibkr_desk import IbkrDesk
    feed, ib, clock, mono = _feed()
    feed.focus("ABCD")
    desk = IbkrDesk.__new__(IbkrDesk)
    desk.stream, desk.tape, desk.depth = feed.stream, None, feed
    desk.no_live_data, desk.symbols, desk.fundamentals = set(), ["ABCD"], None
    desk.competing_since, desk._next_competing_note, desk.clock = None, 0.0, clock
    desk.log = lambda m: None
    desk._on_tws_error(ib.depth_req_id("ABCD"), 10186, "Requested market data is not subscribed. Delayed "
                       "market data is not enabled", Obj(symbol="ABCD"))
    s = feed.snapshot()
    assert s["state"] == "NO_SUBSCRIPTION" and s["code"] == 10186


def test_a_replay_says_it_has_no_book(fixture_server):
    from urllib.request import urlopen
    with urlopen(fixture_server + "/api/v1/depth") as r:
        snap = json.loads(r.read())
    assert snap["state"] == "OFF" and "no Level 2 in this replay" in snap["message"]
