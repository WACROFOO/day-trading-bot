"""The streaming desk end to end, offline: a fake TWS behind the real server
and the real page. Asserts the live UX rules — no replay transport, the
provider badge, candles arriving over the event stream without a reload —
and the HTTP surface (/api/v1/stream, /api/v1/health provider block)."""

from __future__ import annotations

import http.client
import json
import os
import socket
import sys
import threading
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from fake_ibkr import FakeIB, FakeTicker, day_bars, minute_bars  # noqa: E402
from momentum_platform.dashboard.ibkr_desk import IbkrDesk  # noqa: E402
from momentum_platform.dashboard.server import make_handler  # noqa: E402

UTC = timezone.utc
T0 = datetime(2026, 9, 3, 14, 0, tzinfo=UTC)
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


class Clock:
    def __init__(self):
        self.now = T0

    def __call__(self):
        return self.now


@pytest.fixture(scope="module")
def desk_server():
    start = T0 - timedelta(minutes=30)
    ib = FakeIB(daily={"AAA": day_bars(30, 4.0)}, minutes={"AAA": minute_bars(start, 30, 4.0)},
                quotes={"AAA": FakeTicker(last=4.35, close=3.99, bid=4.34, ask=4.36)})
    clock = Clock()
    desk = IbkrDesk(["AAA"], ib_factory=lambda: ib, clock=clock, headlines=False, sec=False, rescan=0)
    desk.log = lambda m: None
    desk._bootstrap()
    desk._worker_thread = threading.main_thread()
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]; sock.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler("ibkr:AAA", desk, None))
    t = threading.Thread(target=httpd.serve_forever, daemon=True); t.start()
    yield {"desk": desk, "ib": ib, "clock": clock, "port": port}
    httpd.shutdown()


def _get(port, path, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path, headers=headers or {})
    r = conn.getresponse()
    body = r.read()
    conn.close()
    return r, body


def test_health_carries_the_provider_block_and_streaming_flag(desk_server):
    r, body = _get(desk_server["port"], "/api/v1/health")
    h = json.loads(body)
    assert h["mode"] == "live" and h["streaming"] is True
    assert h["provider"]["readOnly"] is True and h["provider"]["clientId"] == 27
    assert h["provider"]["state"] in ("LIVE", "STALE")


def test_stream_endpoint_replays_from_last_event_id(desk_server):
    desk, port = desk_server["desk"], desk_server["port"]
    ev = desk.hub.publish("health", {"state": "LIVE"})
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", "/api/v1/stream", headers={"Last-Event-ID": str(ev.id - 1)})
    r = conn.getresponse()
    assert r.getheader("Content-Type").startswith("text/event-stream")
    frame = r.fp.readline() + r.fp.readline() + r.fp.readline() + r.fp.readline()
    conn.close()
    assert frame.startswith(f"id: {ev.id}\nevent: health\n".encode())


def test_session_js_never_leaks_private_keys(desk_server):
    r, body = _get(desk_server["port"], "/session.js")
    assert b"_records" not in body
    session = json.loads(body.split(b"=", 1)[1].rstrip(b";"))
    assert session["live"] is True and session["streaming"] is True and session["provider"]["readOnly"] is True


@pytest.mark.skipif(not Path(CHROME).is_file(), reason="no chromium binary")
def test_page_is_live_only_and_draws_streamed_candles(desk_server):
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright
    desk, ib, clock, port = (desk_server[k] for k in ("desk", "ib", "clock", "port"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        pg = browser.new_page(viewport={"width": 1500, "height": 900})
        errors: list = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(f"http://127.0.0.1:{port}/")
        pg.wait_for_timeout(800)
        assert not errors, errors
        assert pg.eval_on_selector(".transport", "e => e.hidden") is True, "no replay controls on a live desk"
        assert not pg.is_visible(".transport"), "hidden must beat the flex display rule, or the bar still shows"
        assert not pg.is_visible("#frameCounter")
        assert pg.text_content("#feedText") == "LIVE"
        assert "IBKR" in pg.text_content("#feedAge") and "read-only" in pg.text_content("#feedAge")
        assert "read-only, streaming" in pg.text_content("#sessionLabel")
        pg.wait_for_function("window.DeskLive && window.DeskLive.state === 'open'", timeout=5000)
        before = pg.evaluate("(window.__SESSION__.bars10s.AAA || []).length")
        for i in range(2):
            clock.now = T0 + timedelta(seconds=5 * i + 5)
            ib.push_bar("AAA", T0 + timedelta(seconds=5 * i), 4.40, 4.45, 4.39, 4.42, 700)
        desk.tick()
        pg.wait_for_function(f"(window.__SESSION__.bars10s.AAA || []).length === {before + 1}", timeout=5000)
        last = pg.evaluate("window.__SESSION__.bars10s.AAA.slice(-1)[0]")
        assert last[0] == int(T0.timestamp()) and last[5] == 1400, "the streamed ten-second candle is in the chart data"
        assert pg.evaluate("window.DeskLive.counts.bar10s") >= 1
        assert pg.evaluate("window.DeskLive.counts.health") >= 1
        assert pg.text_content("#feedText") in ("LIVE", "STALE")
        quote = pg.evaluate("window.__SESSION__.symbols.AAA.iexLast")
        assert quote == 4.35
        label = pg.evaluate("Array.from(document.querySelectorAll('#quoteCard .qgrid span')).map(e => e.textContent).join('|')")
        assert "IBKR print" in label and "IEX print" not in label
        # One stamp format from both code paths: the server rebuild and the
        # streamed quote must not disagree about a trailing " ET".
        assert " ET" not in label, label
        stamp = pg.eval_on_selector("#quoteCard .stamp", "e => e.children.length")
        assert stamp == 2, "price and time are separate elements, so neither wraps"
        states = pg.eval_on_selector_all(".tile-state", "els => els.map(e => e.textContent)")
        assert states and "REPLAY" not in states and set(states) <= {"LIVE", "STALE"}, states
        assert pg.locator("[data-card=pillars-board] .pb-row:not(.head)").count() == 1
        assert pg.locator(".slot [data-card=timeline]").count() == 0
        # audio alerts default on for a live desk; the legend opens and closes
        assert pg.get_attribute("#btnSound", "aria-pressed") == "true"
        assert "Alerts" in pg.text_content("#btnSound")
        assert not pg.is_visible("#legend")
        pg.click("#btnHelp")
        assert pg.is_visible("#legend") and "PM" in pg.text_content("#legend") and "RTH" in pg.text_content("#legend")
        pg.click("#legendClose")
        assert not pg.is_visible("#legend")
        # the board carries the market-data columns and the desk band note
        heads = pg.eval_on_selector_all("[data-card=pillars-board] .pb-row.head span", "els => els.map(e => e.textContent)")
        assert heads == ["Symbol", "Last", "Gain", "P", "G", "R", "F", "N", "Score"], "compact form in the column"
        note = pg.text_content("#pillarsBoardNote")
        assert "$2–20" in note and "RVOL ≥5×" in note and len(note) < 70, note
        assert "desk admits $1–30" in pg.get_attribute("#pillarsBoardNote", "title")
        # a server rebuild announces itself and the page refetches at once
        before_built = pg.evaluate("window.__SESSION__.builtAt")
        desk.refresh_session()
        pg.wait_for_function(f"window.__SESSION__.builtAt !== {before_built!r}", timeout=5000)
        assert pg.evaluate("window.DeskLive.counts.session") >= 1

        # The alert sound fires on ARRIVALS, never on refreshes. Every rebuild
        # mints fresh event ids, so keying the sound on ids turned the desk
        # into a metronome; keying it on a ticker entering a grid does not.
        beeps = pg.evaluate("window.__deskBeeps()")
        for _ in range(3):
            desk.refresh_session()
            pg.wait_for_timeout(250)
        assert pg.evaluate("window.__deskBeeps()") == beeps, "a refresh is not an alert"

        # The timeline keeps what the rebuild window drops.
        logged = pg.evaluate("document.querySelectorAll('[data-card=scan-running] .trow').length")
        desk.refresh_session()
        pg.wait_for_timeout(250)
        assert pg.evaluate("document.querySelectorAll('[data-card=scan-running] .trow').length") >= logged
        assert pg.locator("[data-card=scan-running] .tile-rows.timeline").count() == 1

        # A rebuild must not clobber the live health badge with a static LIVE.
        desk.hub.publish("health", dict(desk.health(), state="STALE"))
        pg.wait_for_function("document.querySelector('#feedText').textContent === 'STALE'", timeout=5000)
        desk.refresh_session()
        pg.wait_for_timeout(400)
        assert pg.text_content("#feedText") == "STALE", "render() repainted the badge over the health stream"

        # The streamed print survives a rebuild that does not carry it.
        pg.evaluate("window.__SESSION__.symbols.AAA.iexLastTime = '09:59:59'")
        pg.evaluate("""() => { const n = JSON.parse(JSON.stringify(window.__SESSION__.symbols));
                               n.AAA.iexLastTime = null; window.__mergeProbe = n; }""")
        desk.refresh_session()
        pg.wait_for_timeout(400)
        assert pg.evaluate("window.__SESSION__.symbols.AAA.iexLastTime") is not None, \
            "a rebuild that omits the streamed stamp must not blank it"

        # Scroll position in a tile survives the rebuild.
        # The height has to come from a stylesheet: the tile body is rebuilt on
        # every render, so an inline style would vanish with the old element
        # and the assertion below would test nothing.
        pg.add_style_tag(content="[data-card=scan-running] .tile-rows{max-height:40px;overflow:auto}")
        pg.evaluate("""() => { const b = document.querySelector('[data-card=scan-running] .tile-rows');
                               if (b) b.scrollTop = 12; }""")
        top = pg.evaluate("document.querySelector('[data-card=scan-running] .tile-rows').scrollTop")
        desk.refresh_session()
        pg.wait_for_timeout(400)
        if top:
            assert pg.evaluate("document.querySelector('[data-card=scan-running] .tile-rows').scrollTop") == top
        # The header clock is the REAL ET clock on a live desk. It used to show
        # the newest frame's stamp, so a session that stopped advancing read as
        # "09:22" for hours while the market ran on.
        import datetime as _dt
        from zoneinfo import ZoneInfo as _Z
        shown = pg.text_content("#clockET")
        real = _dt.datetime.now(_Z("America/New_York")).strftime("%H:%M")
        assert shown.startswith(real[:4]), f"clock {shown} is not the ET wall clock {real}"
        assert pg.text_content("#sessionBadge") in {"premarket", "regular", "after_hours", "closed"}

        # And the desk states its own freshness beside that clock. The feed is
        # live (quotes and bars reached the desk seconds ago) while the newest
        # BAR is hours old: that is quiet tape, and the chip says both rather
        # than calling a live desk "hours behind".
        lag = pg.text_content("#dataLag")
        # Short text, fixed-width slot: the chip sits between the clock and the
        # feed badges and must not shove them along the bar when the tape goes
        # quiet. The explanation is in the tooltip.
        assert lag.startswith("live · "), lag
        title = pg.get_attribute("#dataLag", "title")
        assert "newest bar" in title and "quiet tape, not a delay" in title
        assert pg.get_attribute("#dataLag", "class").endswith("ok")
        assert "quiet tape" in pg.get_attribute("#dataLag", "title")
        assert not errors, errors
        browser.close()


def test_page_rolls_to_the_new_trading_day(desk_server):
    """04:00 ET: the desk's session is dated today, yesterday's tape is gone,
    the lag chip says "no prints yet" instead of a 19-hour lag, and the
    alert timeline and arrival memory start empty. The header read
    "2026-09-03 · 19H BEHIND" at 04:03 on the 4th before this."""
    pytest.importorskip("playwright.sync_api")
    from datetime import datetime
    from playwright.sync_api import sync_playwright
    desk, ib, clock, port = (desk_server[k] for k in ("desk", "ib", "clock", "port"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        pg = browser.new_page(viewport={"width": 1500, "height": 900})
        errors: list = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(f"http://127.0.0.1:{port}/")
        pg.wait_for_timeout(800)
        pg.wait_for_function("window.DeskLive && window.DeskLive.state === 'open'", timeout=5000)
        assert pg.text_content("#sessionLabel").startswith("2026-09-03")
        pg.evaluate("(() => { const m = window.__deskMemory(); m.log.push({symbol: 'AAA', _at: Date.now()}); m.keys.add('x'); m.seen.set('k', 1); })()")
        try:
            ib.daily["AAA"] = day_bars(31, 4.2, today="2026-09-04")
            clock.now = datetime(2026, 9, 4, 8, 5, tzinfo=UTC)
            desk.refresh_session()
            pg.wait_for_function("document.querySelector('#sessionLabel').textContent.startsWith('2026-09-04')", timeout=5000)
            mem = pg.evaluate("(() => { const m = window.__deskMemory(); return [m.log.length, m.keys.size, m.seen.size]; })()")
            assert mem == [0, 0, 0], mem
            assert pg.text_content("#dataLag") == "no prints yet"
            assert "warn" in pg.get_attribute("#dataLag", "class")
            assert pg.evaluate("window.__SESSION__.frames.length") == 0
            assert not errors, errors
        finally:
            clock.now = T0
            ib.daily["AAA"] = day_bars(30, 4.0)
            desk.refresh_session()
        browser.close()
