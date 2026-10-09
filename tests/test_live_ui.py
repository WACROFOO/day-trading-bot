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


def test_health_names_the_code_the_desk_started_on_and_its_recording_window(desk_server):
    """scripts/day.py reads both: a second launch names a desk on older code
    (2026-10-08), and the day's start confirms what the desk will record."""
    from momentum_platform import desk_profile
    r, body = _get(desk_server["port"], "/api/v1/health")
    h = json.loads(body)
    assert h["codeAtStart"] == desk_profile.build_commit()
    assert h["provider"]["recording"] is True and h["provider"]["recordUntil"] is None   # a desk by hand


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
        # the line under the name is the date alone; the feed mode moved to its tooltip
        assert pg.text_content("#sessionLabel").strip() == "2026-09-03"
        assert "read-only, streaming" in pg.get_attribute("#sessionLabel", "title")
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
        # the board's column is the verdict list (2026-10-09): one name judged
        assert pg.text_content("[data-card=pillars-board] .vl-funnel").startswith("1 name judged")
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
        assert pg.eval_on_selector("#pillarsBoard", "e => e.classList.contains('vlist')"), "the verdict list in the column"
        assert pg.locator("[data-card=pillars-board] .pb-row.head").count() == 0
        # the thresholds moved off the card head into the "?" tooltip
        assert pg.text_content("#pillarsBoardNote").strip() == "?"
        note = pg.get_attribute("#pillarsBoardNote", "title")
        assert "$2–20" in note and "RVOL ≥5×" in note and "desk admits $1–30" in note, note
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
        # A live desk opens on the live edge and stays there. It used to open
        # eight minutes before the bell — a replay convenience — and the
        # follow rule then refused to catch up, so every card sat in the past
        # while this chip said "live".
        pos = pg.evaluate("window.__deskFrame()")
        assert pos["frame"] == pos["frames"] - 1, pos
        assert pos["ts"] == pos["last"]
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


@pytest.mark.skipif(not Path(CHROME).is_file(), reason="no chromium binary")
def test_the_desk_shows_which_rules_it_is_running(desk_server):
    """Two traders on their own IBKR connections compare one badge instead of
    two screens: the hash covers the shared profile, any local override, the
    Confirmed pillars and the scanner definitions."""
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        pg = browser.new_page(viewport={"width": 1500, "height": 900})
        pg.goto(f"http://127.0.0.1:{desk_server['port']}/")
        pg.wait_for_function("!document.getElementById('rulesBadge').hidden", timeout=10000)
        assert pg.text_content("#rulesHash").strip()
        title = pg.get_attribute("#rulesBadge", "title")
        assert "Desk rules" in title and "liquidity" in title
        assert "same scanners and the same alerts" in title
        browser.close()


@pytest.mark.skipif(not Path(CHROME).is_file(), reason="no chromium binary")
def test_a_live_desk_can_be_parked_on_a_minute_and_says_so(desk_server):
    """Stepping back to an alert's minute is a deliberate act with a way home.
    Before this, clicking any alert row pinned every card to that minute for
    the rest of the session and the header chip still read "live"."""
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright
    desk, port = desk_server["desk"], desk_server["port"]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        pg = browser.new_page(viewport={"width": 1500, "height": 900})
        pg.goto(f"http://127.0.0.1:{port}/")
        pg.wait_for_timeout(800)
        start = pg.evaluate("window.__deskFrame()")
        assert start["frame"] == start["frames"] - 1

        # A click on an alert row selects the name; it does not move the desk.
        rows = pg.locator(".alert-row")
        if rows.count():
            rows.first.click()
            pg.wait_for_timeout(200)
            assert pg.evaluate("window.__deskFrame()")["frame"] == start["frames"] - 1
            assert pg.text_content("#dataLag").startswith("live")

        # Parking is explicit, visible, and reversible.
        target = pg.evaluate("window.__SESSION__.frames[2].ts")
        pg.evaluate("ts => window.__deskSeek(ts)", target)
        pg.wait_for_timeout(200)
        assert pg.text_content("#dataLag").startswith("paused")
        assert "return to live" in pg.get_attribute("#dataLag", "title")
        desk.refresh_session()
        pg.wait_for_timeout(700)
        assert pg.text_content("#dataLag").startswith("paused"), "a rebuild does not unpark it"
        pg.click("#dataLag")
        pg.wait_for_timeout(200)
        pos = pg.evaluate("window.__deskFrame()")
        assert pos["frame"] == pos["frames"] - 1 and pos["ts"] == pos["last"]
        assert pg.text_content("#dataLag").startswith("live")
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
        # The rollover drops yesterday's minute cache for good — correct on a
        # real desk, which never travels back in time. This module's desk does
        # (the clock is reset below), so the cache is snapshotted and restored;
        # without it every later test in the module saw an empty tape and the
        # verdict card showed "no bars yet" instead of a banner.
        saved_minutes = {k: list(v) for k, v in desk._minutes.items()}
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
            desk._minutes = saved_minutes
            desk.refresh_session()
        browser.close()


# -- one desk, two browsers: the access key ----------------------------------------

def test_with_no_key_configured_the_desk_stays_open(desk_server, monkeypatch):
    monkeypatch.delenv("DESK_KEY", raising=False)
    monkeypatch.delenv("DESK_VIEWER_KEY", raising=False)
    r, body = _get(desk_server["port"], "/api/v1/health")
    assert r.status == 200 and json.loads(body)["role"] == "open"


def test_a_configured_key_gates_every_request_and_a_cookie_keeps_it(desk_server, monkeypatch):
    """Opened beyond localhost, the desk must not be readable — or changeable —
    by whoever finds the URL. The key travels once as ?key= and lives in a
    cookie after that, so the page's own fetches and its event stream carry
    it without the key ever appearing in the page's code."""
    monkeypatch.setenv("DESK_KEY", "owner-secret")
    port = desk_server["port"]
    for path in ("/", "/session.js", "/api/v1/health", "/api/v1/stream"):
        r, body = _get(port, path)
        assert r.status == 401, path
        assert b"needs a key" in body
    r, body = _get(port, "/api/v1/health?key=owner-secret")
    assert r.status == 200 and json.loads(body)["role"] == "owner"
    cookie = r.getheader("Set-Cookie")
    assert cookie and cookie.startswith("desk_key=owner-secret") and "HttpOnly" in cookie
    r, body = _get(port, "/api/v1/health", headers={"Cookie": "desk_key=owner-secret"})
    assert r.status == 200 and json.loads(body)["role"] == "owner"
    r, _ = _get(port, "/api/v1/health", headers={"Cookie": "desk_key=wrong"})
    assert r.status == 401


def test_the_viewer_key_sees_the_desk_but_cannot_change_it(desk_server, monkeypatch):
    monkeypatch.setenv("DESK_KEY", "owner-secret")
    monkeypatch.setenv("DESK_VIEWER_KEY", "viewer-secret")
    port = desk_server["port"]
    r, body = _get(port, "/api/v1/health?key=viewer-secret")
    assert r.status == 200 and json.loads(body)["role"] == "viewer"
    r, body = _get(port, "/session.js", headers={"Cookie": "desk_key=viewer-secret"})
    assert r.status == 200 and b"__SESSION__" in body
    r, body = _get(port, "/api/v1/desk/add?symbol=ZZZ", headers={"Cookie": "desk_key=viewer-secret"})
    assert r.status == 403 and "only the owner" in json.loads(body)["note"]
    assert "ZZZ" not in desk_server["desk"].symbols


def test_the_verdict_card_renders_the_servers_cascade_not_its_own_score(desk_server):
    """The card once summed four booleans into a score where FILTERS.md Layer 1
    kills, and the browser and server disagreed on screen (IMRN 2026-09-04).
    Since 2026-10-08 the whole card is the server's (decision_card.py): the word
    from REVIEW / WATCH / WAIT / NO, its reason, and every red gate as a lamp.
    'PASS' never appears as a verdict — on this desk it means a gate passed."""
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright
    port = desk_server["port"]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        pg = browser.new_page(viewport={"width": 1500, "height": 900})
        errors: list = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(f"http://127.0.0.1:{port}/")
        pg.wait_for_timeout(800)
        assert not errors, errors
        assert pg.evaluate("!!(window.__SESSION__.cards && window.__SESSION__.cards.AAA)"), \
            "the server must ship a decision card for every symbol"
        card = pg.evaluate("window.__SESSION__.cards.AAA")
        banner = pg.text_content("#verdictCard .dc-answer .dc-word")
        assert banner == card["verdict"]["word"], (banner, card["verdict"])
        assert banner in {"REVIEW", "WATCH", "WAIT", "NO"}
        assert banner != "PASS"
        assert "server card" in pg.get_attribute("#verdictCard .dc-answer", "title")
        assert pg.text_content("#verdictCard .dc-answer .dc-reason") == card["verdict"]["reason"]
        # the top bar says the same word for the desk (one name here)
        assert pg.text_content("#dvWord") == ("NOTHING TO TRADE" if banner == "NO" else banner)
        # every gate the cascade could not pass is a lamp on the card, by state
        red = [l["label"] for l in card["lamps"] if l["state"] in ("FAIL", "UNKNOWN")]
        shown = pg.eval_on_selector_all("#verdictCard .dc-lamp .l", "els => els.map(e => e.textContent)")
        for label in red:
            assert label in shown, (label, shown)
        browser.close()


def test_a_desk_with_no_bars_yet_renders_without_a_page_error():
    """The 2026-09-07 rehearsal screenshot: a live desk on a holiday showed
    empty cards. Correct if it is 'nothing to show', a defect if render()
    threw on an empty frame list. This pins the difference."""
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright
    ib = FakeIB(daily={"AAA": day_bars(30, 4.0)}, minutes={"AAA": []},
                quotes={"AAA": FakeTicker(last=4.35, close=3.99, bid=4.34, ask=4.36)})
    desk = IbkrDesk(["AAA"], ib_factory=lambda: ib, clock=Clock(), headlines=False, sec=False, rescan=0)
    desk.log = lambda m: None
    desk._bootstrap(); desk._worker_thread = threading.main_thread()
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]; sock.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler("ibkr:AAA", desk, None))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
            pg = browser.new_page(viewport={"width": 1500, "height": 900})
            errors: list = []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_timeout(1200)
            assert not errors, errors
            assert pg.evaluate("window.__SESSION__.frames.length") == 0
            # the verdict card says something rather than nothing
            txt = pg.text_content("#verdictCard") or ""
            assert txt.strip(), "an empty verdict card on an empty tape hides the reason"
            browser.close()
    finally:
        httpd.shutdown()


@pytest.mark.skipif(not Path(CHROME).is_file(), reason="no chromium binary")
def test_the_chart_panes_carry_drawing_tools_and_an_indicator_menu(desk_server):
    """Lightweight Charts ships neither, and TradingView's Advanced Charting
    Library — which ships both — is licensed to companies for public projects
    only, so it is not available to this desk. The tools are drawn here.

    The drawing canvas must be transparent to the mouse until a tool is picked,
    or it eats the crosshair, the zoom and the pan on every pane.
    """
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        pg = browser.new_page(viewport={"width": 1500, "height": 900})
        pg.goto(f"http://127.0.0.1:{desk_server['port']}/")
        pg.wait_for_timeout(1200)

        assert pg.evaluate("!!window.ChartTools"), "chartTools.js was not served"
        # the real renderer, not the canvas fallback: the tools attach to it
        assert pg.evaluate("window.LightweightCharts !== undefined")

        for pane in ("chartA", "chartB", "chartD"):
            assert pg.locator(f"#{pane} .draw-layer").count() == 1, pane
            assert pg.locator(f"#{pane} .draw-bar .draw-btn").count() >= 6, pane
            assert pg.locator(f"#{pane} .ind-btn").count() == 1, pane
            assert pg.eval_on_selector(
                f"#{pane} .draw-layer",
                "e => getComputedStyle(e).pointerEvents") == "none", f"{pane} eats the crosshair"

        # picking a tool arms the canvas; Escape disarms it
        pg.eval_on_selector("#chartA .draw-btn[data-tool=level]", "e => e.click()")
        assert pg.eval_on_selector("#chartA .draw-layer",
                                   "e => getComputedStyle(e).pointerEvents") == "auto"
        pg.keyboard.press("Escape")
        assert pg.eval_on_selector("#chartA .draw-layer",
                                   "e => getComputedStyle(e).pointerEvents") == "none"

        # the indicator menu lists MACD, which the cascade judged but no pane drew
        pg.eval_on_selector("#chartA .ind-btn", "e => e.click()")
        labels = pg.eval_on_selector_all("#chartA .ind-menu label",
                                         "els => els.map(e => e.textContent)")
        for name in ("Volume", "VWAP", "EMA 9", "EMA 200", "MACD 12/26/9"):
            assert any(name in t for t in labels), name
        # MACD reads on the 1-minute only (audit 2026-10-09; Preview ch. 5)
        assert pg.is_visible("#chartA .band-tag")
        assert not pg.is_visible("#chartB .band-tag") and not pg.is_visible("#chartD .band-tag")
        browser.close()


def test_the_selected_name_gets_a_live_tape_end_to_end(desk_server):
    """The page asks for the selected name's tape (POST /api/v1/focus), the
    desk opens IBKR tick-by-tick on its worker, prints arrive in the ticker's
    update event, and the tape event paints the Time & Sales card and the
    decision card's tape line — read-only all the way (2026-10-08)."""
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright
    from fake_ibkr import Obj
    desk, ib, clock, port = (desk_server[k] for k in ("desk", "ib", "clock", "port"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        pg = browser.new_page(viewport={"width": 1500, "height": 900})
        errors: list = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(f"http://127.0.0.1:{port}/")
        pg.wait_for_function("window.DeskLive && window.DeskLive.state === 'open'", timeout=5000)
        pg.wait_for_timeout(700)                         # the focus request is debounced
        desk.run_pending()                               # the worker opens the tape
        assert ("tbt:Last", "AAA") in ib.live_lines and ("tbt:BidAsk", "AAA") in ib.live_lines
        t = ib.tickers["AAA"]
        at = clock.now
        t.tickByTicks = [Obj(time=at, bidPrice=4.34, askPrice=4.36, bidSize=100, askSize=100),
                         Obj(time=at, price=4.36, size=500, exchange="NASDAQ", specialConditions="",
                             tickAttribLast=Obj(pastLimit=False, unreported=False)),
                         Obj(time=at, price=4.34, size=100, exchange="ARCA", specialConditions="",
                             tickAttribLast=Obj(pastLimit=False, unreported=False))]
        t.updateEvent.emit(t)
        t.tickByTicks = []
        desk._publish_tape()
        pg.wait_for_function("document.querySelector('#tapeTag').textContent === 'LIVE'", timeout=5000)
        marks = pg.eval_on_selector_all("#tapeCard .ts-row .ts-m", "els => els.map(e => e.textContent)")
        assert marks == ["▼", "▲"], marks
        word = pg.evaluate("window.__SESSION__.cards.AAA.verdict.word")
        if word == "NO":                                 # a NO card carries no tape line (2026-10-09)
            assert pg.locator("#verdictCard .dc-tape").count() == 0
        else:
            assert "at the ask" in pg.text_content(".dc-tape")
        assert desk.health()["tape"]["symbol"] == "AAA"
        assert not errors, errors
        browser.close()


def test_the_selected_name_gets_its_book_end_to_end(desk_server):
    """Level 2 (owner, 2026-10-09): the same focus asks IBKR for SmartDepth on
    the desk's read-only connection. Until the account holds the subscription
    IBKR refuses, and the card says so with IBKR's exact code; the request is
    made again on its own, and the moment depth flows the ladder paints."""
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright
    from fake_ibkr import Obj
    from momentum_platform.datasources import ibkr_depth as ID
    desk, ib, clock, port = (desk_server[k] for k in ("desk", "ib", "clock", "port"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        pg = browser.new_page(viewport={"width": 1600, "height": 900})
        errors: list = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(f"http://127.0.0.1:{port}/")
        pg.wait_for_function("window.DeskLive && window.DeskLive.state === 'open'", timeout=5000)
        pg.wait_for_timeout(700)                         # the focus request is debounced
        desk.run_pending()
        assert ("AAA", ID.DEPTH_ROWS, True) in ib.depth_calls, "SmartDepth for the selected name"
        desk._on_tws_error(ib.depth_req_id("AAA"), 354, "Not subscribed to requested market data.",
                           Obj(symbol="AAA"))
        desk._publish_depth()
        pg.wait_for_function("document.querySelector('#depthTag').textContent === 'NO SUB'", timeout=5000)
        assert "IBKR 354: Not subscribed to requested market data." in pg.text_content("#depthCard")
        assert desk.health()["depth"]["code"] == 354
        desk.depth._retry_at = 0                         # the two-minute retry comes due
        desk._publish_depth()
        assert sum(1 for c in ib.depth_calls if c[0] == "AAA") >= 2
        ib.push_depth("AAA", [(4.34, 500, "NSDQ"), (4.33, 800, "ARCA")], [(4.36, 300, "NSDQ"), (4.37, 900, "EDGX")])
        desk._publish_depth()
        pg.wait_for_function("document.querySelector('#depthTag').textContent === 'LIVE'", timeout=5000)
        assert pg.locator("#depthCard .l2-row").count() == 4
        assert pg.text_content("#depthCard .l2-mid") == "4.34 × 4.36"
        assert desk.health()["depth"]["state"] == "LIVE"
        assert not errors, errors
        browser.close()


def test_the_page_asks_for_the_tape_only_when_it_needs_to(desk_server):
    """Review 2026-10-08: the first version posted a name the owner had
    already left, and never asked again for the selected one. Now a post for a
    name left is void; a render does not loop on a refused tape; a click
    retries it; a tape on another window's name is left there until a click
    or this tab coming into view; a restarted desk's empty tape is asked for."""
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright
    port = desk_server["port"]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        pg = browser.new_page(viewport={"width": 1500, "height": 900})
        posts: list = []
        pg.on("request", lambda r: posts.append(json.loads(r.post_data)["symbol"])
              if r.url.endswith("/api/v1/focus") else None)
        pg.goto(f"http://127.0.0.1:{port}/")
        pg.wait_for_function("window.DeskLive && window.DeskLive.state === 'open'", timeout=5000)
        pg.wait_for_timeout(800)
        live = {"symbol": "AAA", "state": "LIVE", "prints": [], "gaps": [], "notes": [], "facts": None,
                "message": "", "source": "test"}
        pg.evaluate("s => window.__applyTape(s)", live)
        posts.clear()
        pg.evaluate("() => { window.__postFocus('BBB', true); window.__postFocus('AAA', true); }")
        pg.wait_for_timeout(700)
        assert posts == [], "the post for a name already left is void, and the tape is on AAA"
        pg.evaluate("s => window.__applyTape(s)", dict(live, state="ERROR", message="IBKR refused"))
        pg.evaluate("() => window.__postFocus('AAA')")
        pg.wait_for_timeout(700)
        assert posts == [], "a render does not loop on a refused tape"
        pg.evaluate("() => window.__postFocus('AAA', true)")
        pg.wait_for_timeout(700)
        assert posts == ["AAA"], "a click retries it"
        # Owner, 2026-10-09 05:30: two open tabs each re-posted their own name
        # every 5 s and IBKR's 15-s pacing never let either start — FLYE sat on
        # "starting shortly" under AIXI. A repaint no longer takes the tape back
        # from another window; a click does, and so does a tab coming into view.
        pg.evaluate("s => window.__applyTape(s)", dict(live, symbol="ZZZ"))
        pg.wait_for_timeout(5200)
        pg.evaluate("() => window.__postFocus('AAA')")
        pg.wait_for_timeout(700)
        assert posts == ["AAA"], "a repaint leaves another window's name alone"
        pg.evaluate("() => window.__postFocus('AAA', true)")
        pg.wait_for_timeout(700)
        assert posts == ["AAA", "AAA"], "a click takes it back"
        pg.evaluate("s => window.__applyTape(s)", dict(live, symbol="ZZZ"))
        pg.evaluate("() => Object.defineProperty(document, 'visibilityState', {value: 'hidden', configurable: true})")
        pg.evaluate("() => window.__postFocus('AAA', true)")
        pg.wait_for_timeout(700)
        assert posts == ["AAA", "AAA"], "a tab out of view never moves the tape"
        pg.evaluate("""() => { Object.defineProperty(document, 'visibilityState', {value: 'visible', configurable: true});
                               document.dispatchEvent(new Event('visibilitychange')); }""")
        pg.wait_for_timeout(700)
        assert posts == ["AAA", "AAA", "AAA"], "the tab that comes into view takes the tape"
        pg.evaluate("s => window.__applyTape(s)", dict(live, symbol=None, state="OFF"))
        pg.wait_for_timeout(5200)
        pg.evaluate("() => window.__postFocus('AAA')")
        pg.wait_for_timeout(700)
        assert posts == ["AAA", "AAA", "AAA", "AAA"], "a desk with no tape at all (restarted) is asked again"
        browser.close()


def test_a_desk_running_older_code_than_its_page_says_restart(desk_server):
    """Owner, 2026-10-08: after an update without a restart the new page met
    the old desk — no tape, no news on the new layout, and nothing said why.
    The desk sends the build it started on; a desk from before this check
    sends none. Either way the page names it: RESTART THE DESK."""
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright
    port = desk_server["port"]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        pg = browser.new_page(viewport={"width": 1500, "height": 900})
        r, body = _get(port, "/api/v1/health")
        h = json.loads(body)
        assert r.status == 200 and h["appBuildAtStart"], "the desk names the build it started on"
        pg.goto(f"http://127.0.0.1:{port}/")
        pg.wait_for_function("window.DeskLive && window.DeskLive.state === 'open' && window.__APP_BUILD__", timeout=5000)
        assert pg.evaluate("window.__APP_BUILD__") == h["appBuildAtStart"], "same files, same build"
        pg.wait_for_timeout(5600)                       # one health poll
        assert "RESTART THE DESK" not in (pg.text_content("#deskAlerts") or "")

        def old_desk(route):                            # a desk started before the check existed
            body = dict(h)
            body.pop("appBuildAtStart")
            route.fulfill(status=200, content_type="application/json", body=json.dumps(body))
        pg.route("**/api/v1/health", old_desk)
        pg.wait_for_timeout(5600)
        assert "RESTART THE DESK" in pg.text_content("#deskAlerts")
        # the banner adds a row; it never takes the desk's (owner's screenshot:
        # the whole desk collapsed under it, the charts a strip at the bottom)
        banner = pg.locator("#deskAlerts").bounding_box()
        grid = pg.locator("#grid").bounding_box()
        chart = pg.locator("[data-card=chart-1m]").bounding_box()
        assert banner["height"] < 120, banner
        assert abs(grid["y"] - (banner["y"] + banner["height"])) < 4, "the desk starts right under the banner"
        assert grid["height"] > 600 and chart["height"] > 250, (grid, chart)
        assert pg.evaluate("document.body.scrollHeight <= window.innerHeight + 2")
        browser.close()
