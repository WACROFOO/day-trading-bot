"""The charts' key levels, volume profile, older sessions and TradingView
dressing (2026-10-13).

levels.js is pure arithmetic and is checked in node; the page is checked on
the fake TWS behind the real server: older sessions arrive on the panes, the
gate's VWAP is unchanged on today's bars, the levels and the profile are drawn
from what the pane holds, MACD has its own pane, and the values legend is one
click away."""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
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

from fake_ibkr import FakeIB, FakeTicker  # noqa: E402

LEVELS = ROOT / "src" / "momentum_platform" / "dashboard" / "web" / "levels.js"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
UTC = timezone.utc
ET = ZoneInfo("America/New_York")
TODAY = date(2026, 10, 13)


# -- levels.js, in node ---------------------------------------------------------------

def node(expr: str):
    if shutil.which("node") is None:
        pytest.skip("no node binary")
    code = f"const L = require({json.dumps(str(LEVELS))}); process.stdout.write(JSON.stringify(({expr})));"
    out = subprocess.run(["node", "-e", code], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_the_profile_keeps_every_share_and_finds_its_point_of_control():
    got = node("""(() => {
      const bars = [[0, 10.00, 10.10, 10.00, 10.10, 1000], [60, 10.05, 10.05, 10.05, 10.05, 3000],
                    [120, 10.08, 10.10, 10.02, 10.03, 500], [180, 10.1, 10.1, 10.0, 10.0, 0]];
      const p = L.profile(bars, { rows: 10 });
      const inside = p.rows.slice(p.vaFrom, p.vaTo + 1).reduce((s, r) => s + r.total, 0);
      return { total: p.total, sum: p.rows.reduce((s, r) => s + r.total, 0), poc: p.poc, share: inside / p.total,
               up: p.rows.reduce((s, r) => s + r.up, 0), down: p.rows.reduce((s, r) => s + r.down, 0),
               none: L.profile([[0, 1, 1, 1, 1, 0]]) };
    })()""")
    assert got["total"] == 4500 and got["sum"] == pytest.approx(4500)
    assert got["up"] == pytest.approx(4000) and got["down"] == pytest.approx(500), "up = closed at or above its open"
    assert 10.05 <= got["poc"] <= 10.06, "the row the 3,000 shares traded in"
    assert got["share"] >= 0.70, "the value area holds at least 70 % of the volume"
    assert got["none"] is None, "nothing traded: no profile, never a made-up one"


def test_the_corpus_settings_are_the_defaults():
    got = node("({ rows: L.ROWS, va: L.VALUE_AREA })")
    assert got == {"rows": 24, "va": 0.7}, "wC2Bbf6OMFQ [00:06:02]: value area 70, row size 24"


def test_density_is_a_multiple_of_the_average():
    got = node("""(() => {
      const p = L.profile([[0, 10.00, 10.10, 10.00, 10.10, 1000], [60, 10.05, 10.05, 10.05, 10.05, 3000]], { rows: 10 });
      return [L.density(p, p.lo, p.hi), L.density(p, 10.05, 10.06), L.density(p, 10.0, 10.0)];
    })()""")
    assert got[0] == pytest.approx(1.0) and got[1] == pytest.approx(7.75) and got[2] is None


def test_swings_never_look_ahead():
    got = node("""(() => {
      const ys = [1, 2, 3, 2, 1, 2, 3.5];
      const bars = ys.map((y, i) => [i * 300, y, y + 0.01, y - 0.01, y, 100]);
      return L.pivots(bars, 2, 2).map(p => [p.i, p.kind]);
    })()""")
    assert [2, "high"] in got and [4, "low"] in got
    assert all(i <= 4 for i, _ in got), "the newest two bars cannot be swings yet"


def test_zones_cluster_swings_and_name_a_flip():
    """Two highs near 3.40 (resistance), a break to 3.73, and a pullback that
    holds 3.40 from above: one zone, three touches, a flipped level. Two lows
    near 2.79: support, not a flip. The median bar range here is 6 cents, so
    swings within 3 cents join (half the range beats 0.3 % of price)."""
    got = node("""(() => {
      const ys = [3.0, 3.2, 3.37, 3.2, 3.0, 2.83, 2.95, 3.1, 3.40, 3.2, 2.9, 2.81, 3.0, 3.25, 3.6, 3.7, 3.55, 3.43, 3.55, 3.7, 3.8];
      const bars = ys.map((y, i) => [i * 300, y, y + 0.03, y - 0.03, y, 100]);
      return L.zones(bars, { left: 2, right: 2 }).map(z => ({ p: +z.price.toFixed(2), t: z.touches, h: z.highs, l: z.lows, flip: z.flip }));
    })()""")
    assert got == [{"p": 2.79, "t": 2, "h": 0, "l": 2, "flip": False},
                   {"p": 3.41, "t": 3, "h": 2, "l": 1, "flip": True}]


def test_overlapping_neighbours_are_one_zone():
    """Highs at 2.98, 3.00 and 3.013 drift the first cluster's mean; 3.025 is
    too far from it to join but its band overlaps — one zone of four touches,
    not two labels on top of each other."""
    got = node("""(() => {
      const ys = [2.5, 2.7, 2.95, 2.7, 2.5, 2.7, 2.97, 2.7, 2.5, 2.7, 2.983, 2.7, 2.5, 2.7, 2.995, 2.7, 2.5];
      const bars = ys.map((y, i) => [i * 300, y, y + 0.03, y - 0.03, y, 100]);
      return L.zones(bars, { left: 2, right: 2, rangeShare: 0, tol: 0.008 }).filter(z => z.highs)
        .map(z => [+z.price.toFixed(3), z.touches]);
    })()""")
    assert got == [[3.005, 4]], got


def test_round_levels_prior_day_and_sessions():
    got = node("""({
      r1: L.roundLevels(4.37), r2: L.roundLevels(5.0), r3: L.roundLevels(0.42),
      pd: L.priorDay([{d: "2026-10-09", h: 5, l: 4, c: 4.5}, {d: "2026-10-12", h: 6, l: 5, c: 5.5},
                      {d: "2026-10-13", h: 7, l: 6, c: 6.5}], "2026-10-13"),
      runs: L.bySession([[Date.UTC(2026, 9, 12, 23, 59) / 1000], [Date.UTC(2026, 9, 13, 0, 30) / 1000],
                         [Date.UTC(2026, 9, 13, 8, 0) / 1000]]).map(r => [r.day, r.from, r.to]),
    })""")
    assert got["r1"] == {"below": 4.0, "above": 4.5} and got["r2"] == {"below": 4.5, "above": 5.5}
    assert got["r3"] == {"below": None, "above": 0.5}
    assert got["pd"] == {"d": "2026-10-12", "h": 6, "l": 5, "c": 5.5}, "the last COMPLETED day, never today's"
    assert got["runs"] == [["2026-10-12", 0, 1], ["2026-10-13", 2, 2]], "00:30 UTC is still the evening before in New York"


# -- the page, on the fake TWS --------------------------------------------------------

def _et(d: date, hh: int, mm: int) -> datetime:
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=ET).astimezone(UTC)


def _day(d: date, prices) -> list:
    """One bar a minute from 09:30 ET through the anchors, plus a pre-market stretch."""
    out, t = [], _et(d, 7, 0)
    for k in range(60):
        p = prices[0]
        out.append((t + timedelta(minutes=k), p, p + 0.02, p - 0.02, p + 0.01, 800))
    t = _et(d, 9, 30)
    seq = []
    for a, b in zip(prices, prices[1:]):
        seq += [a + (b - a) * j / 20 for j in range(20)]
    for k, p in enumerate(seq):
        out.append((t + timedelta(minutes=k), round(p, 2), round(p + 0.03, 2), round(p - 0.03, 2),
                    round(p + 0.01, 2), 5000 + 100 * (k % 7)))
    return out


@pytest.fixture(scope="module")
def desk_page(tmp_path_factory):
    if not Path(CHROME).is_file():
        pytest.skip("no chromium binary")
    pytest.importorskip("playwright.sync_api")
    from momentum_platform.dashboard.ibkr_desk import IbkrDesk
    from momentum_platform.dashboard.server import make_handler
    days = {date(2026, 10, 8): [2.1, 2.3, 2.1, 2.3, 2.1], date(2026, 10, 9): [2.1, 2.3, 2.12, 2.3, 2.2],
            date(2026, 10, 12): [2.2, 3.4, 2.8, 3.39, 2.81, 3.05]}
    minutes = []
    for d, ps in days.items():
        minutes += _day(d, ps)
    now = _et(TODAY, 10, 15)
    t = _et(TODAY, 4, 0)
    p = 3.1
    while t < now:
        p = round(p + (0.004 if t < _et(TODAY, 9, 35) else -0.001), 3)
        minutes.append((t, p, p + 0.02, p - 0.02, p + 0.01, 3000))
        t += timedelta(minutes=1)
    daily = [("2026-09-%02d" % d, 2.0, 2.1, 1.9, 2.05, 150_000) for d in range(1, 30) if date(2026, 9, d).weekday() < 5]
    daily += [("2026-10-08", 2.1, 2.33, 2.07, 2.11, 400_000), ("2026-10-09", 2.11, 2.33, 2.09, 2.21, 380_000),
              ("2026-10-12", 2.2, 3.43, 2.17, 3.06, 2_500_000)]
    ib = FakeIB(daily={"AAA": daily}, minutes={"AAA": minutes},
                quotes={"AAA": FakeTicker(last=p, close=3.06, bid=p - 0.01, ask=p + 0.01)})
    desk = IbkrDesk(["AAA"], ib_factory=lambda: ib, clock=lambda: now, headlines=False, sec=False, rescan=0)
    desk.log = lambda m: None
    desk.chart_history.cache_dir = tmp_path_factory.mktemp("chart_cache")
    desk.chart_history.pace_s = 0.0
    desk._bootstrap()
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]; sock.close()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler("ibkr:AAA", desk, None))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
    pg = browser.new_page(viewport={"width": 1600, "height": 950})
    errors: list = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(f"http://127.0.0.1:{port}/")
    pg.wait_for_function("() => window.__deskPanes && window.__deskPanes().a.sessionStarts().length >= 1", timeout=8000)
    yield {"pg": pg, "errors": errors, "desk": desk, "ib": ib}
    browser.close()
    pw.stop()
    httpd.shutdown()


def test_the_previous_session_is_on_the_chart_and_the_gate_vwap_is_unchanged(desk_page):
    pg = desk_page["pg"]
    got = pg.evaluate("""() => {
      const a = window.__deskPanes().a, rows = a.rows(), vw = a.vwapDrawn(), today = window.__SESSION__.bars.AAA;
      const first = rows.findIndex(r => r.time >= a.rows()[a.sessionStarts().slice(-1)[0]].time);
      // the gate's VWAP over today's bars, recomputed here
      let pv = 0, vv = 0; const gate = today.map(b => { const tp = (b[2] + b[3] + b[4]) / 3; pv += tp * b[5]; vv += b[5]; return pv / vv; });
      const drawn = vw.slice(first);
      return { n: rows.length, today: today.length, starts: a.sessionStarts(),
               worst: Math.max(...gate.map((g, i) => Math.abs(g - drawn[i]))) };
    }""")
    assert got["n"] > got["today"], "older candles on the 1-minute pane"
    assert got["worst"] < 1e-9, "today's VWAP is the gate's own, older sessions do not leak into it"
    assert desk_page["desk"]._minutes["AAA"][0]["ts"] >= _et(TODAY, 4, 0).isoformat().replace("+00:00", "Z"), \
        "the desk's own bars stay today's"


def test_scrolling_past_the_oldest_bar_brings_the_session_before(desk_page):
    pg = desk_page["pg"]
    before = pg.evaluate("() => window.__deskPanes().a.sessionStarts().length")
    pg.evaluate("() => { const a = window.__deskPanes().a; a.setRange({from: 60, to: 300}); a.setRange({from: -5, to: 235}); }")
    pg.wait_for_function(f"() => window.__deskPanes().a.sessionStarts().length > {before}", timeout=8000)
    rng = pg.evaluate("() => window.__deskPanes().a.getRange()")
    assert rng["from"] > 100, "the bars the trader was reading stay in view while the older ones load"
    assert not desk_page["errors"], desk_page["errors"]


def test_the_levels_drawn_are_the_prior_day_the_dollars_and_the_zones(desk_page):
    pg = desk_page["pg"]
    lv = pg.evaluate("() => window.__deskPanes().a.levelsDrawn()")
    assert lv["pd"] == {"d": "2026-10-12", "h": 3.43, "l": 2.17, "c": 3.06}
    last = lv["last"]
    assert lv["round"]["below"] < last < lv["round"]["above"]
    assert lv["round"]["above"] - lv["round"]["below"] <= 0.5 + 1e-9
    # yesterday's two highs, a cent apart, are today's support (the price is above them)
    assert len(lv["zones"]) == 1 and 3.41 <= lv["zones"][0]["price"] <= 3.44 < last
    assert lv["zones"][0]["touches"] == 2 and lv["zones"][0]["highs"] == 2
    for z in lv["zones"]:
        assert z["touches"] >= 2 and z["lo"] <= z["price"] <= z["hi"]
        assert z["dens"] is None or z["dens"] >= 0
        assert abs(z["price"] - last) <= last * 0.3
    assert pg.evaluate("() => window.__deskPanes().d.levelsDrawn()") is None, "off on the 10-second pane"


def test_the_volume_profile_reads_the_bars_in_view_on_the_five_minute(desk_page):
    pg = desk_page["pg"]
    pr = pg.evaluate("() => window.__deskPanes().b.profileDrawn()")
    assert pr is not None and len(pr["rows"]) == 24
    assert pr["lo"] <= pr["poc"] <= pr["hi"] and pr["val"] <= pr["poc"] <= pr["vah"]
    inside = sum(r["total"] for r in pr["rows"][pr["vaFrom"]:pr["vaTo"] + 1])
    assert inside >= 0.7 * pr["total"] - 1e-6
    assert pg.evaluate("() => window.__deskPanes().a.profileDrawn()") is None, "one click away on the 1-minute"


def test_macd_has_its_own_pane_and_the_values_legend_is_one_click(desk_page):
    pg = desk_page["pg"]
    a = pg.evaluate("() => window.__deskPanes().a.macdPane()")
    b = pg.evaluate("() => window.__deskPanes().b.macdPane()")
    assert a["visible"] and a["height"] >= 56 and a["timeAxisOnPrice"] is False, "one time axis, under MACD"
    assert not b["visible"] and b["timeAxisOnPrice"] is True
    assert pg.evaluate("() => window.__deskPanes().a.legendText()") == "", "off since 2026-10-02"
    pg.eval_on_selector("#chartA .ind-btn", "e => e.click()")
    pg.locator("#chartA .ind-menu label", has_text="Values").click()
    pg.eval_on_selector("#chartA .ind-btn", "e => e.click()")
    text = pg.evaluate("() => window.__deskPanes().a.legendText()")
    assert text.startswith("AAA") and all(k in text for k in ("O", "H", "L", "C", "Vol", "VWAP"))
    assert "MACD 12 26 9" in pg.inner_text("#chartA .band-tag")
    pg.locator("#chartA .ind-btn").click()
    pg.locator("#chartA .ind-menu label", has_text="Values").click()
    assert pg.evaluate("() => window.__deskPanes().a.legendText()") == ""
    assert not desk_page["errors"], desk_page["errors"]
