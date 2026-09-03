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
        assert "IBKR last print" in label and "IEX last print" not in label
        assert not errors, errors
        browser.close()
