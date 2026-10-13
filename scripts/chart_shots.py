"""Screenshots of the desk's charts on SYNTHETIC data (docs/desk-2026-10-13/).

No IBKR in the build container, so the desk runs on the test suite's fake TWS
(tests/fake_ibkr.py) with four made-up sessions of one name, "SYNTH": two
quiet days around $2.10-2.30, a news spike to $3.40 that faded, and today's
gap to $4.40. The real server and the real page draw them; the page carries a
"SYNTHETIC" label. Nothing here is a market fact.

    python3 scripts/chart_shots.py [OUT_DIR] [PREFIX]

PREFIX (default "after") names the files; the same script copied into a
checkout of an older commit draws that commit's charts on the same data
("before"): there the desk has no history client and the panes no older
sessions, so those steps are skipped. Needs Playwright and the Chromium the
container provides."""

from __future__ import annotations

import random
import socket
import sys
import tempfile
import threading
from datetime import date, datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from fake_ibkr import FakeIB, FakeTicker  # noqa: E402

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
SYM = "SYNTH"
TODAY = date(2026, 10, 13)
NOW = datetime(2026, 10, 13, 10, 16, tzinfo=ET)
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

# (ET hh:mm, price) anchors per session; minutes in between are interpolated with noise.
PATHS = {
    date(2026, 10, 8): [("04:00", 2.12), ("09:30", 2.14), ("09:46", 2.25), ("10:40", 2.06), ("12:10", 2.18),
                        ("13:35", 2.25), ("14:40", 2.09), ("16:00", 2.13), ("20:00", 2.12)],
    date(2026, 10, 9): [("04:00", 2.13), ("09:30", 2.12), ("09:52", 2.26), ("10:45", 2.07), ("12:30", 2.19),
                        ("14:10", 2.11), ("16:00", 2.18), ("20:00", 2.19)],
    date(2026, 10, 12): [("04:00", 2.19), ("08:30", 2.24), ("09:30", 2.30), ("09:41", 3.40), ("10:25", 2.81),
                         ("11:15", 3.36), ("12:20", 2.83), ("13:40", 3.12), ("14:30", 2.84), ("16:00", 3.05),
                         ("20:00", 3.10)],
    TODAY: [("04:00", 3.10), ("06:10", 3.38), ("07:30", 4.20), ("08:15", 3.88), ("08:50", 4.12), ("09:12", 3.86),
            ("09:35", 4.46), ("09:55", 4.04), ("10:08", 4.41), ("10:16", 4.36)],
}


def _session(day: date, anchors, rng: random.Random) -> list:
    pts = [(datetime.combine(day, datetime.strptime(t, "%H:%M").time(), tzinfo=ET), p) for t, p in anchors]
    out, prev = [], pts[0][1]
    for (t0, p0), (t1, p1) in zip(pts, pts[1:]):
        n = int((t1 - t0).total_seconds() // 60)
        for k in range(n):
            ts = t0 + timedelta(minutes=k)
            mins = ts.hour * 60 + ts.minute
            if ts >= NOW:
                return out
            target = p0 + (p1 - p0) * (k + 1) / n
            close = round(max(0.5, target * (1 + rng.gauss(0, 0.004))), 2)
            o = round(prev, 2)
            hi = round(max(o, close) * (1 + abs(rng.gauss(0, 0.003))), 2)
            lo = round(min(o, close) * (1 - abs(rng.gauss(0, 0.003))), 2)
            regular = 570 <= mins < 960
            move = abs(p1 - p0) / max(p0, 0.01) / max(n, 1) * 400
            base = 9000 if regular else 1200
            if day == TODAY:
                base *= 6 if mins >= 420 else 2
            vol = int(base * (1 + move * 8) * (0.4 + rng.random()))
            # pre-market and after-hours print less often: some minutes have no trade at all
            if not regular and rng.random() < (0.55 if day != TODAY else 0.15):
                continue
            out.append((ts.astimezone(UTC), o, hi, lo, close, vol))
            prev = close
    return out


def build_ib() -> FakeIB:
    rng = random.Random(20261013)
    minutes = []
    for day, anchors in PATHS.items():
        minutes += _session(day, anchors, rng)
    daily, d, px = [], TODAY - timedelta(days=380), 1.9
    while d < date(2026, 10, 8):
        if d.weekday() < 5:
            px = max(1.2, px * (1 + rng.gauss(0, 0.02)))
            daily.append((d.isoformat(), round(px, 2), round(px * 1.04, 2), round(px * 0.96, 2), round(px, 2), 180_000))
        d += timedelta(days=1)
    for day in (date(2026, 10, 8), date(2026, 10, 9), date(2026, 10, 12)):
        reg = [m for m in minutes if m[0].astimezone(ET).date() == day and 570 <= m[0].astimezone(ET).hour * 60 + m[0].astimezone(ET).minute < 960]
        daily.append((day.isoformat(), reg[0][1], max(m[2] for m in reg), min(m[3] for m in reg), reg[-1][4],
                      sum(m[5] for m in reg)))
    last = minutes[-1][4]
    return FakeIB(daily={SYM: daily}, minutes={SYM: minutes},
                  quotes={SYM: FakeTicker(last=last, close=daily[-1][4], bid=round(last - 0.01, 2), ask=last)},
                  names={SYM: "Synthetic Test Data Inc"})


def serve(cache_dir: Path):
    from momentum_platform.dashboard.ibkr_desk import IbkrDesk
    from momentum_platform.dashboard.server import make_handler
    ib = build_ib()
    desk = IbkrDesk([SYM], ib_factory=lambda: ib, clock=lambda: NOW.astimezone(UTC), headlines=False, sec=False,
                    rescan=0)
    desk.log = lambda m: None
    hist = getattr(desk, "chart_history", None)
    if hist is not None:
        hist.cache_dir = cache_dir
        hist.pace_s = 0.0
    desk._bootstrap()
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]; sock.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler("ibkr:" + SYM, desk, None))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return desk, httpd, port


LABEL = """() => { const d = document.createElement('div');
  d.textContent = 'SYNTHETIC — made-up test data, not IBKR, not a market fact';
  d.style.cssText = 'position:fixed;left:50%;top:6px;transform:translateX(-50%);z-index:9999;padding:2px 10px;'
    + 'border:1px dashed #ffc247;color:#ffc247;background:#131722e6;font:11px monospace;pointer-events:none';
  document.body.appendChild(d); }"""


def main(argv=None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    out = Path(args[0] if args else str(ROOT / "docs" / "desk-2026-10-13"))
    tag = args[1] if len(args) > 1 else "after"
    out.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright
    with tempfile.TemporaryDirectory() as tmp:
        desk, httpd, port = serve(Path(tmp))
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
                pg = browser.new_page(viewport={"width": 1920, "height": 952})
                errors = []
                pg.on("pageerror", lambda e: errors.append(str(e)))
                pg.goto(f"http://127.0.0.1:{port}/")
                pg.wait_for_timeout(2500)
                pg.evaluate(LABEL)
                # Drag the 1-minute chart to the right, as the trader would, until three
                # earlier sessions are on it: each pass over the oldest bar asks for one more.
                box = pg.locator("#chartA").bounding_box()
                has_history = pg.evaluate("() => typeof window.__deskPanes().a.sessionStarts === 'function'")
                for _ in range(60 if has_history else 0):
                    if len(pg.evaluate("() => window.__deskPanes().a.sessionStarts()")) >= 3:
                        break
                    pg.mouse.move(box["x"] + 200, box["y"] + box["height"] * 0.35)
                    pg.mouse.down()
                    pg.mouse.move(box["x"] + box["width"] - 120, box["y"] + box["height"] * 0.35, steps=10)
                    pg.mouse.up()
                    pg.wait_for_timeout(350)
                pg.evaluate("() => window.__deskPanes().a.snapToLive()")
                pg.wait_for_timeout(1200)
                # the desk: today and the afternoon before it on the 1-minute
                pg.evaluate("() => { const a = window.__deskPanes().a; const n = a.rows().length; a.setRange({from: n - 560, to: n + 3}); }")
                pg.mouse.move(5, 5)                      # no synced crosshair in the picture
                pg.wait_for_timeout(600)
                pg.screenshot(path=str(out / f"{tag}_desk_SYNTHETIC.png"))
                for card in ("chart-1m", "chart-5m"):
                    pg.locator(f"[data-card={card}]").screenshot(path=str(out / f"{tag}_{card}_SYNTHETIC.png"))
                # the 1-minute zoomed out over every loaded session
                pg.evaluate("() => { const a = window.__deskPanes().a; const n = a.rows().length; a.setRange({from: 0, to: n + 3}); }")
                pg.wait_for_timeout(600)
                pg.locator("[data-card=chart-1m]").screenshot(path=str(out / f"{tag}_chart-1m_sessions_SYNTHETIC.png"))
                # "Values" ticked in the 1-minute's ƒ menu: the TradingView legend, read at the crosshair
                if pg.locator("#chartA .ind-menu label", has_text="Values").count():
                    pg.evaluate("() => { const a = window.__deskPanes().a; const n = a.rows().length; a.setRange({from: n - 240, to: n + 3}); }")
                    pg.eval_on_selector("#chartA .ind-btn", "e => e.click()")
                    pg.locator("#chartA .ind-menu label", has_text="Values").click()
                    pg.eval_on_selector("#chartA .ind-btn", "e => e.click()")
                    x = pg.evaluate("() => { const a = window.__deskPanes().a, r = a.rows(); return a.xOf(r[r.length - 40].time); }")
                    pg.mouse.move(box["x"] + x, box["y"] + box["height"] * 0.3)
                    pg.wait_for_timeout(400)
                    pg.locator("[data-card=chart-1m]").screenshot(path=str(out / f"{tag}_chart-1m_values_SYNTHETIC.png"))
                # a live ten-second bar through the downtrend line: the breakout flag
                if pg.evaluate("() => { const t = window.__deskPanes().a.trendDrawn && window.__deskPanes().a.trendDrawn(); return !!(t && t.down); }"):
                    pg.mouse.move(5, 5)
                    pg.evaluate("() => { const a = window.__deskPanes().a; const n = a.rows().length; a.setRange({from: n - 150, to: n + 3}); }")
                    line = pg.evaluate("() => window.__deskPanes().a.trendDrawn().down.now")
                    last = pg.evaluate("() => { const r = window.__SESSION__.bars[%r]; return r[r.length - 1]; }" % SYM)
                    t0 = last[0] + 60
                    for i, px in enumerate((last[4], round(line + 0.03, 2), round(line + 0.06, 2))):
                        desk.hub.publish("bar10s", {"symbol": SYM, "t": t0 + 10 * i, "open": px, "high": px + 0.01,
                                                    "low": px - 0.01, "close": px, "volume": 4000})
                        pg.wait_for_timeout(400)
                    pg.locator("[data-card=chart-1m]").screenshot(path=str(out / f"{tag}_chart-1m_breakout_SYNTHETIC.png"))
                if errors:
                    print("page errors:", errors)
                browser.close()
        finally:
            httpd.shutdown()
    print("wrote", ", ".join(sorted(p.name for p in out.glob("*_SYNTHETIC.png"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
