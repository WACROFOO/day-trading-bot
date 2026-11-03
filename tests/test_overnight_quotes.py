"""The owner's screenshot of 2026-11-02, 02:51 ET (Monday): the desk on Friday's session,
INO's card reading PRICE $2.17 beside a GAIN of +166 %, the tiles LIVE over Friday's 19:59
bar, the news tile WEAK beside a news line NONE, the tape "starting…" all night. Each is
pinned here at its source; the page's side is in tests/test_dashboard.py."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from momentum_platform.sessions import quote_parts  # noqa: E402

ET = ZoneInfo("America/New_York")
UTC = timezone.utc
FRI_0400 = datetime(2026, 10, 30, 4, 0, tzinfo=ET)          # the desk's session at 02:51 on Monday
MON_0251 = datetime(2026, 11, 2, 2, 51, 23, tzinfo=ET)
MON_0400 = datetime(2026, 11, 2, 4, 0, tzinfo=ET)


# -- the rule ---------------------------------------------------------------------

def test_an_overnight_trade_is_never_the_sessions_price():
    """The screenshot: a trade 15 s before 02:51 on Monday, the book 2.17 × 2.18."""
    got = quote_parts(MON_0251, FRI_0400, last=2.17, print_ts=MON_0251 - timedelta(seconds=15), bid=2.17, ask=2.18)
    assert got["session"] == {}
    assert got["overnight"]["last"] == 2.17 and (got["overnight"]["bid"], got["overnight"]["ask"]) == (2.17, 2.18)


def test_the_sessions_last_trade_stays_the_sessions_and_the_night_book_does_not():
    fri_close = datetime(2026, 10, 30, 19, 59, 59, tzinfo=ET)
    got = quote_parts(MON_0251, FRI_0400, last=2.05, print_ts=fri_close, bid=2.17, ask=2.18)
    assert got["session"] == {"last": 2.05, "ts": fri_close}
    assert got["overnight"] == {"bid": 2.17, "ask": 2.18}


def test_at_four_the_book_is_the_sessions_and_the_nights_last_trade_is_not():
    night = datetime(2026, 11, 2, 3, 49, tzinfo=ET)
    got = quote_parts(MON_0400 + timedelta(minutes=5), MON_0400, last=2.17, print_ts=night, bid=2.20, ask=2.25)
    assert got["session"] == {"bid": 2.20, "ask": 2.25}, "no session trade yet: no session price"
    assert got["overnight"] == {"last": 2.17, "ts": night}


def test_an_earlier_sessions_close_belongs_to_neither_and_the_overnight_venue_never_to_the_session():
    old = quote_parts(MON_0400 + timedelta(minutes=5), MON_0400, last=2.05,
                      print_ts=datetime(2026, 10, 30, 19, 59, 59, tzinfo=ET))
    assert old == {"session": {}, "overnight": {}}, "Friday's close is in Friday's bars, not Monday's price"
    venue = quote_parts(MON_0400 + timedelta(hours=1), MON_0400, last=2.4,
                        print_ts=MON_0400 + timedelta(minutes=59), venue="OVERNIGHT")
    assert venue["session"] == {} and venue["overnight"]["last"] == 2.4


def test_a_trade_with_no_time_is_judged_at_the_clock():
    assert quote_parts(MON_0251, FRI_0400, last=2.17)["overnight"]["last"] == 2.17
    assert quote_parts(MON_0400 + timedelta(hours=6), MON_0400, last=2.3)["session"]["last"] == 2.3


# -- the desk ---------------------------------------------------------------------

def _ticker(**kw):
    from fake_ibkr import FakeTicker
    t = FakeTicker(last=kw.pop("last"), bid=kw.pop("bid", float("nan")), ask=kw.pop("ask", float("nan")))
    for k, v in kw.items():
        setattr(t, k, v)
    return t


def test_the_desk_files_the_night_apart_from_the_sessions_print():
    from test_ibkr_desk import make_desk
    desk, ib, clock = make_desk()
    ref = {}
    t = _ticker(last=2.17, bid=2.17, ask=2.18, lastTimestamp=(MON_0251 - timedelta(seconds=15)).astimezone(UTC),
                lastExchange="OVERNIGHT")
    desk._quote_into(ref, t, MON_0251.astimezone(UTC), FRI_0400.astimezone(UTC))
    assert "iex_last_price" not in ref and "iex_bid" not in ref, "the card would read 2.17 as the name's price"
    assert ref["overnight"]["last"] == 2.17 and (ref["overnight"]["bid"], ref["overnight"]["ask"]) == (2.17, 2.18)
    ref = {}
    t = _ticker(last=5.21, bid=5.20, ask=5.22, lastTimestamp=datetime(2026, 10, 30, 10, 0, 1, tzinfo=ET).astimezone(UTC))
    desk._quote_into(ref, t, datetime(2026, 10, 30, 10, 0, 3, tzinfo=ET).astimezone(UTC), FRI_0400.astimezone(UTC))
    assert ref["iex_last_price"] == 5.21 and (ref["iex_bid"], ref["iex_ask"]) == (5.20, 5.22) and "overnight" not in ref
    assert ref["iex_last_ts"] == "2026-10-30T14:00:01+00:00", "the trade's own time, not the rebuild's"


def test_a_streamed_quote_is_split_the_same_way():
    from momentum_platform.dashboard.stream import EventHub, UpdatePublisher
    from momentum_platform.state import MarketUpdate
    from test_ibkr_desk import make_desk
    desk, ib, clock = make_desk()
    clock.now = MON_0251.astimezone(UTC)
    hub = EventHub()
    pub = UpdatePublisher(hub, split=desk._split_quote)
    pub(MarketUpdate(symbol="INO", ts=clock.now, price=2.17, size=100, bid=2.17, ask=2.18,
                     print_ts=clock.now - timedelta(seconds=15), venue="OVERNIGHT"))
    q = hub.since(0)[-1].data
    assert q["price"] is None and q["bid"] is None and q["ask"] is None
    assert q["overnight"]["last"] == 2.17 and q["overnight"]["ask"] == 2.18
    plain = UpdatePublisher(EventHub())                      # a source with no session split is unchanged
    ev = plain(MarketUpdate(symbol="X", ts=clock.now, price=1.0, bid=0.99, ask=1.01))
    assert ev.data["price"] == 1.0 and "overnight" not in ev.data


def test_the_session_says_whether_it_is_open_on_the_calendar():
    from test_ibkr_desk import make_desk, T0
    desk, ib, clock = make_desk()
    s = desk._bootstrap()
    assert s["inSession"] is True and s["marketPhase"] == "regular"          # Thursday 10:00 ET
    clock.now = T0.replace(hour=1, minute=0) + timedelta(days=2)            # Saturday 21:00 ET
    s = desk.refresh_session()
    assert s["inSession"] is False and s["marketPhase"] == "closed"


# -- the card ---------------------------------------------------------------------

def test_the_price_tile_is_the_price_the_gates_judged_and_the_news_tile_the_lines_word():
    from momentum_platform.catalyst import card_read
    from test_desk_card import _bars, _cascade, _det, PULLBACK
    from momentum_platform.decision_card import build_card
    bars = _bars(PULLBACK)
    now = datetime.fromtimestamp(bars[-1][0], UTC) + timedelta(seconds=30)
    meta = {"iexLast": 5.60, "prevClose": 4.0,
            "metrics": {"last": 5.22, "changePct": 30.5, "rvol": 8.0, "sessionHigh": 5.40, "volumeToday": 2e6}}
    cat = card_read([], now=now, trading_date="2026-10-07")
    assert (cat["grade"], cat["plain"]["label"]) == ("WEAK", "NONE")
    card = build_card("ABCD", meta=meta, cascade=_cascade(), bars=bars, detector=_det(bars), now=now,
                      catalyst=cat, risk=25.0, risk_source="yours")
    lamps = {l["id"]: l for l in card["lamps"]}
    assert lamps["price"]["value"] == "$5.22" and lamps["gain"]["value"] == "+30.5%", \
        "the price and the gain of one snapshot, never a newer print beside an older gain"
    assert lamps["catalyst"]["value"].split(" · ")[0] == "NONE", "the tile says what the news line says"


# -- the tape ---------------------------------------------------------------------

def test_the_tape_says_the_session_is_over_instead_of_starting_all_night():
    from momentum_platform.tape import TapeBook
    clock = [datetime(2026, 11, 2, 7, 51, tzinfo=UTC)]
    book = TapeBook("INO", clock=lambda: clock[0])
    assert book.state == "STARTING"
    book.check_session(False)
    assert book.state == "CLOSED" and "04:00 ET" in book.message
    book.add_print(clock[0], 2.17, 100)
    assert book.state == "LIVE", "a print that does arrive is shown, and the tape is live"
    book.set_state("QUIET", "no print in the last 60 s")
    book.check_session(False)
    assert book.state == "CLOSED"
    book.check_session(True)
    assert book.state == "STARTING" and book.message == "waiting for the first print"


def test_the_ibkr_tape_closes_outside_the_session(monkeypatch):
    from momentum_platform.datasources.ibkr_tape import TapeFeed
    from momentum_platform.tape import TapeBook

    class _Stream:
        health = type("H", (), {"state": "LIVE", "generation": 0})()

    clock = [MON_0251.astimezone(UTC)]
    feed = TapeFeed(_Stream(), clock=lambda: clock[0])
    feed.book = TapeBook("INO", clock=lambda: clock[0])
    feed.check()
    assert feed.book.state == "CLOSED"
    clock[0] = (MON_0400 + timedelta(minutes=1)).astimezone(UTC)
    feed.check()
    assert feed.book.state == "STARTING"
