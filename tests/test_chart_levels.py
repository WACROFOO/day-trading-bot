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

def node(expr: str, prelude: str = ""):
    if shutil.which("node") is None:
        pytest.skip("no node binary")
    code = (f"const L = require({json.dumps(str(LEVELS))}); {prelude}\n"
            f"process.stdout.write(JSON.stringify(({expr})));")
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


PINE = ROOT / "knowledge-base" / "tradingview" / "ross-fp-v4.pine"


def test_the_ports_constants_are_the_pine_scripts_own():
    """Support/resistance ports ross-fp-v4.pine (owner, 2026-10-13: "you can
    use the pine we've developed at its latest version"); the trend lines keep
    its touch tolerance. Its numbers are read here from the script itself, so
    a change to the Pine fails this until the port follows."""
    import re
    pine = PINE.read_text()
    want = {
        "PIVOT": int(re.search(r"srPivotLen\s*=\s*input\.int\((\d+)", pine).group(1)),
        "SR_EACH": int(re.search(r"maxSRlines\s*=\s*input\.int\((\d+)", pine).group(1)),
        "SR_DEDUP_ATR": float(re.search(r"tolSR\s*=\s*atr\s*\*\s*([\d.]+)", pine).group(1)),
        "BAND_ATR": float(re.search(r"bandATRfrac\s*=\s*input\.float\(([\d.]+)", pine).group(1)),
        "TL_TOL_ATR": float(re.search(r"tolTL\s*=\s*math\.max\(atr\s*\*\s*([\d.]+)", pine).group(1)),
        "PIVOTS_KEPT": int(re.search(r"array\.size\(pivHighs\) > (\d+)", pine).group(1)),
    }
    assert re.search(r'REV = "V9\.12"', pine), "the port follows REV V9.12"
    got = node("({ PIVOT: L.PIVOT, SR_EACH: L.SR_EACH, SR_DEDUP_ATR: L.SR_DEDUP_ATR, BAND_ATR: L.BAND_ATR, "
               "TL_TOL_ATR: L.TL_TOL_ATR, PIVOTS_KEPT: L.PIVOTS_KEPT })")
    assert got == want


def test_atr_is_wilders_true_range_average():
    got = node("""(() => {
      const flat = Array.from({length: 30}, (_, i) => [i * 60, 5, 5.05, 4.95, 5, 100]);
      const gap = [[0, 5, 5.1, 4.9, 5.0, 1], [60, 5.5, 5.6, 5.4, 5.5, 1], [120, 5.5, 5.6, 5.5, 5.55, 1]];
      return [L.atr(flat, 14), L.atr(flat.slice(0, 10), 14), L.atr(gap, 2)];
    })()""")
    assert got[0] == pytest.approx(0.10) and got[1] is None
    # TRs 0.2, 0.6 (5.6 - prior close 5.0), 0.1: seed (0.2 + 0.6) / 2 = 0.4, then (0.4 + 0.1) / 2 = 0.25
    assert got[2] == pytest.approx(0.25)


def test_the_fan_is_two_a_side_polarised_and_deduplicated():
    """ross-fp-v4 V9.5: a resistance shelf price has cleared is support now.
    Highs at 5.41 (twice) under a 5.60 price print once, as support with 2
    swings; lows at 4.99 the same; the shelf at the price is the resistance."""
    got = node("""(() => {
      const ys = [5.1,5.2,5.3,5.4,5.3,5.2,5.1,5.0,5.1,5.2,5.3,5.4,5.3,5.2,5.1,5.0,5.1,5.2,5.3,5.4,5.5,5.6,5.6,5.6,5.6,5.6];
      const bars = ys.map((y, i) => [i * 60, y, y + 0.01, y - 0.01, y, 100]);
      const a = L.atr(bars, 14), fan = L.srFan(bars, 5.6, a, { pivot: 3 });
      return { sup: fan.sup.map(s => [+s.price.toFixed(2), s.touches, s.highs, s.lows]),
               res: fan.res.map(s => +s.price.toFixed(2)), band: fan.band, a };
    })()""")
    assert got["sup"] == [[5.41, 2, 2, 0], [4.99, 2, 0, 2]], "nearest first, the broken highs now support"
    assert got["res"] == [5.61] and len(got["sup"]) <= 2
    assert got["band"] == pytest.approx(max(got["a"] * 0.12, 0.01))


# Closes through linear anchors (index, price); highs and lows two cents out.
PATH_JS = """const path = anchors => { const out = []; let prev = anchors[0][1];
  for (let k = 0; k + 1 < anchors.length; k++) { const [i0, p0] = anchors[k], [i1, p1] = anchors[k + 1];
    for (let i = i0; i < i1; i++) { const c = +(p0 + (p1 - p0) * (i - i0) / (i1 - i0)).toFixed(4);
      out.push([i * 60, prev, Math.max(prev, c) + 0.02, Math.min(prev, c) - 0.02, c, 1000]); prev = c; } }
  return out; };
const lines = (bars, close, opts) => { const t = L.trendLines(bars, close, L.atr(bars, 14), opts);
  const f = ln => ln && { a: ln.a, b: ln.b, touches: ln.touches, brokeAt: ln.brokeAt, through: ln.through,
                          now: ln.now, slope: ln.slope };
  return { up: f(t.up), down: f(t.down), upBroken: f(t.upBroken), downBroken: f(t.downBroken) }; };"""


def test_a_down_line_joins_the_high_to_the_lower_high_and_breaks_on_a_close():
    """The breakout line (owner, 2026-10-13: "so i spot breakouts"): from the
    high of the day through the lower high; a candle CLOSING above it breaks
    it, a live price above it is only breaking. Never two neighbouring bars."""
    got = node("""(() => {
      const pull = path([[0, 4.0], [20, 5.0], [26, 4.6], [32, 4.8], [40, 4.4], [50, 4.5], [51, 4.5]]);
      const out = path([[0, 4.0], [20, 5.0], [26, 4.6], [32, 4.8], [40, 4.4], [50, 4.5], [56, 4.95], [60, 4.9], [61, 4.9]]);
      const held = lines(pull, 4.5);
      return { held, live: lines(pull, held.down.now + 0.05), out: lines(out, 4.9),
               old: lines(out, 4.9, { keep: 5 }) };
    })()""", PATH_JS)
    d = got["held"]["down"]
    assert (d["a"], d["b"]) == (20, 32) and d["touches"] == 2 and d["brokeAt"] is None and d["slope"] < 0
    assert d["b"] - d["a"] > 5, "two swings, never neighbouring bars"
    assert got["held"]["up"] is None, "lower lows: no up-line"
    assert got["live"]["down"]["through"] is True and got["live"]["downBroken"] is None, \
        "live price over the line is breaking, not broken"
    assert got["out"]["down"] is None and got["out"]["downBroken"]["brokeAt"] == 51, "the first close above it"
    assert got["old"]["downBroken"] is None, "a break older than the window drops off"


def test_an_up_line_on_a_gapper_stands_on_the_swings_after_the_gap():
    """GRML 5-minute, 2026-10-14: the tangent anchored on the pre-gap print.
    Swings are searched newest first, and the flat pre-gap closes sit under any
    line from the pre-gap dip, so it cannot qualify."""
    got = node("""(() => {
      const bars = path([[0, 2.0], [10, 1.95], [20, 2.0], [29, 2.0], [30, 3.0], [38, 3.3], [45, 2.9],
                         [52, 3.35], [60, 3.05], [68, 3.4], [70, 3.4]]);
      const one = path([[0, 2.0], [10, 1.95], [20, 2.0], [29, 2.0], [30, 3.0], [38, 3.3], [45, 2.9],
                        [52, 3.35], [54, 3.35]]);
      return { two: lines(bars, 3.4), one: lines(one, 3.35), today: lines(bars, 3.4, { from: 40 }) };
    })()""", PATH_JS)
    assert (got["two"]["up"]["a"], got["two"]["up"]["b"]) == (45, 60)
    assert got["one"]["up"] is None, "one swing after the gap: no line, rather than one from under the gap"
    assert got["today"]["up"]["a"] >= 40, "anchors are today's swings only"


def test_trend_lines_never_have_a_close_or_a_swing_through_them_between_their_swings():
    """The rule that makes a line a line, on random walks: between its two
    swings no candle closes through it and no swing of its kind pierces it by
    more than 0.2 ATR; its break is the first close through after them."""
    got = node("""(() => {
      let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
      const bad = []; let drawn = 0;
      for (let run = 0; run < 40; run++) {
        const bars = []; let p = 5;
        for (let i = 0; i < 240; i++) { const o = p; p = Math.max(0.5, p * (1 + (rnd() - 0.5) * 0.02));
          bars.push([i * 60, o, Math.max(o, p) * (1 + rnd() * 0.004), Math.min(o, p) * (1 - rnd() * 0.004), p, 1000]); }
        const a = L.atr(bars, 14), t = L.trendLines(bars, p, a), sw = L.pivots(bars, 5, 5);
        [["up", true], ["down", false], ["upBroken", true], ["downBroken", false]].forEach(([k, up]) => {
          const ln = t[k]; if (!ln) return; drawn += 1;
          const kind = up ? "low" : "high", tol = Math.max(a * L.TL_TOL_ATR, 0.01);
          const beyond = (v, i, by) => up ? v < ln.at(i) - by : v > ln.at(i) + by;
          if (!sw.some(s => s.i === ln.a && s.kind === kind) || !sw.some(s => s.i === ln.b && s.kind === kind)) bad.push([run, k, "anchor"]);
          if (up ? !(ln.slope > 0) : !(ln.slope < 0)) bad.push([run, k, "slope"]);
          for (let i = ln.a + 1; i < ln.b; i++) if (beyond(bars[i][4], i, 1e-9)) bad.push([run, k, "close", i]);
          sw.filter(s => s.kind === kind && s.i > ln.a && s.i < ln.b).forEach(s => { if (beyond(s.price, s.i, tol)) bad.push([run, k, "swing", s.i]); });
          const first = bars.findIndex((b, i) => i > ln.b && beyond(b[4], i, 1e-9));
          if ((first < 0 ? null : first) !== ln.brokeAt) bad.push([run, k, "break", first, ln.brokeAt]);
        });
      }
      return { bad, drawn };
    })()""", PATH_JS)
    assert got["drawn"] >= 40, "the walks draw lines"
    assert got["bad"] == []


def test_a_line_moves_only_when_a_swing_confirms_or_a_close_breaks_it():
    """Consistency (owner, 2026-10-14: "the trendlines are not consistent"): the
    tangent re-anchored on every bar; a two-swing line stays put bar after bar
    until the market confirms a new swing or closes through it."""
    got = node("""(() => {
      const bars = path([[0, 4.0], [20, 5.0], [26, 4.6], [32, 4.8], [40, 4.4], [60, 4.45], [61, 4.45]]);
      const ids = [], states = [];
      for (let n = 44; n <= bars.length; n++) {
        const sl = bars.slice(0, n), t = L.trendLines(sl, sl[n - 1][4], L.atr(sl, 14)), ln = t.down || t.downBroken;
        ids.push(ln ? ln.a + "-" + ln.b : "none");
        const st = t.down ? "intact" : t.downBroken ? "broken@" + t.downBroken.brokeAt : "none";
        if (states[states.length - 1] !== st) states.push(st);
      }
      // the first close over the line through the 20 and 32 highs, by hand
      const slope = (bars[32][2] - bars[20][2]) / 12;
      const first = bars.findIndex((b, i) => i > 32 && b[4] > bars[20][2] + slope * (i - 20) + 1e-9);
      return { ids: [...new Set(ids)], states, first };
    })()""", PATH_JS)
    assert got["ids"] == ["20-32"], "the same two swings on every bar"
    assert got["states"] == ["intact", "broken@%d" % got["first"]], "it changes once: the candle that closes through it"


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
def chromium():
    """One Playwright and one browser for every page in this module."""
    if not Path(CHROME).is_file():
        pytest.skip("no chromium binary")
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
    yield browser
    browser.close()
    pw.stop()


@pytest.fixture(scope="module")
def desk_page(tmp_path_factory, chromium):
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
    pg = chromium.new_page(viewport={"width": 1600, "height": 950})
    errors: list = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(f"http://127.0.0.1:{port}/")
    pg.wait_for_function("() => window.__deskPanes && window.__deskPanes().a.sessionStarts().length >= 1", timeout=8000)
    yield {"pg": pg, "errors": errors, "desk": desk, "ib": ib}
    pg.close()
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


def test_the_levels_drawn_are_the_pine_fan_the_prior_day_and_the_dollars(desk_page):
    pg = desk_page["pg"]
    lv = pg.evaluate("() => window.__deskPanes().a.levelsDrawn()")
    assert lv["pd"] == {"d": "2026-10-12", "h": 3.43, "l": 2.17, "c": 3.06}
    last = lv["last"]
    assert lv["round"]["below"] < last < lv["round"]["above"]
    assert lv["round"]["above"] - lv["round"]["below"] <= 0.5 + 1e-9
    assert 1 <= len(lv["res"]) <= 2 and 1 <= len(lv["sup"]) <= 2, "two a side at most (ross-fp-v4 V9.4)"
    assert all(r["price"] > last for r in lv["res"]) and all(x["price"] < last for x in lv["sup"])
    assert [x["price"] for x in lv["sup"]] == sorted((x["price"] for x in lv["sup"]), reverse=True), "nearest first"
    # V9.5 polarity: yesterday's two highs, a cent apart, are today's nearest support
    first = lv["sup"][0]
    assert 3.41 <= first["price"] <= 3.44 and first["touches"] == 2 and first["highs"] == 2
    assert lv["band"] >= 0.01 and all(x["dens"] is None or x["dens"] >= 0 for x in lv["res"] + lv["sup"])
    assert pg.evaluate("() => window.__deskPanes().d.levelsDrawn()") is None, "off on the 10-second pane"


@pytest.fixture(scope="module")
def synth_page(tmp_path_factory, chromium):
    """The SYNTHETIC desk of scripts/chart_shots.py — four noisy made-up
    sessions of "SYNTH" — on the real server and page."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import chart_shots
    desk, httpd, port = chart_shots.serve(tmp_path_factory.mktemp("synth_cache"))
    pg = chart_shots.open_page(chromium, port, {"width": 1600, "height": 950})
    errors: list = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(f"http://127.0.0.1:{port}/")
    pg.wait_for_function("() => window.__deskPanes && window.__deskPanes().a.rows().length > 100", timeout=8000)
    yield {"pg": pg, "errors": errors, "desk": desk}
    pg.close()
    httpd.shutdown()


def test_every_trend_line_drawn_stands_on_two_of_todays_swings(synth_page):
    """On the page (2026-10-14): each line drawn on the 1- and 5-minute panes
    joins two of today's confirmed swings, at least six bars apart; no candle
    closes through it between them; a broken one broke at the first close
    through it."""
    pg = synth_page["pg"]
    got = pg.evaluate("""() => {
      const P = window.__deskPanes(), out = {};
      ['a', 'b'].forEach(k => {
        const pane = P[k], t = pane.trendDrawn(), rows = pane.rows(), today = pane.sessionStarts().slice(-1)[0] || 0;
        const bars = rows.map(r => [r.time, r.open, r.high, r.low, r.close, 0]);
        const sw = window.DeskLevels.pivots(bars.slice(0, -1), 5, 5);
        out[k] = [];
        ['up', 'down', 'upBroken', 'downBroken'].forEach(name => {
          const ln = t && t[name]; if (!ln) return;
          const up = name.startsWith('up'), kind = up ? 'low' : 'high';
          const at = i => ln.price + ln.slope * (i - ln.anchor);
          const through = i => up ? rows[i].close < at(i) - 1e-9 : rows[i].close > at(i) + 1e-9;
          let crossed = 0; for (let i = ln.anchor + 1; i < ln.touch; i++) if (through(i)) crossed += 1;
          let first = null; for (let i = ln.touch + 1; i < ln.live; i++) if (through(i)) { first = i; break; }
          out[k].push({ name, gap: ln.touch - ln.anchor, today: ln.anchor >= today, crossed, first, brokeAt: ln.brokeAt,
                        swings: sw.some(s => s.i === ln.anchor && s.kind === kind) && sw.some(s => s.i === ln.touch && s.kind === kind) });
        });
      });
      return out;
    }""")
    drawn = got["a"] + got["b"]
    assert drawn, "the noisy SYNTH day draws trend lines"
    for ln in drawn:
        assert ln["swings"] and ln["today"] and ln["gap"] > 5, ln
        assert ln["crossed"] == 0, ln
        assert ln["first"] == ln["brokeAt"], ln
    assert not synth_page["errors"], synth_page["errors"]


def test_one_history_request_on_load_and_the_other_pane_stays_live(desk_page):
    """The regression found building this (2026-10-13): a guard judged the
    5-minute pane's range against its OLD bar count while the previous session
    was being laid in, threw the view back to the oldest bars, and that empty
    left edge asked IBKR for yet another session."""
    pg, desk = desk_page["pg"], desk_page["desk"]
    assert desk.chart_history.requests >= 1
    b = pg.evaluate("() => { const b = window.__deskPanes().b, r = b.getRange(); return {to: r.to, n: b.rows().length, live: b.liveButton()}; }")
    assert b["to"] >= b["n"] - 1 and b["live"] is False, "the 5-minute pane sits on its newest bar"


def test_the_wheel_over_the_price_axis_zooms_the_price(desk_page):
    pg = desk_page["pg"]
    pg.evaluate("() => window.__deskPanes().a.snapToLive()")
    box = pg.locator("#chartA .pane-main").bounding_box()
    x, y = box["x"] + box["width"] - 20, box["y"] + box["height"] * 0.3        # over the price axis
    pg.mouse.move(x, y)
    pg.mouse.wheel(0, -400)                                                    # up: zoom in
    pg.wait_for_timeout(150)
    z = pg.evaluate("() => window.__deskPanes().a.priceZoomed()")
    assert z is not None and z["max"] > z["min"]
    pg.mouse.wheel(0, 400)                                                     # down: back out
    pg.wait_for_timeout(150)
    z2 = pg.evaluate("() => window.__deskPanes().a.priceZoomed()")
    assert z2["max"] - z2["min"] > z["max"] - z["min"]
    pg.mouse.dblclick(x, y)                                                    # double-click: the data's own scale
    pg.wait_for_timeout(150)
    assert pg.evaluate("() => window.__deskPanes().a.priceZoomed()") is None
    pg.mouse.move(box["x"] + box["width"] * 0.5, y)                            # the bare wheel on the chart: time
    pg.mouse.wheel(0, -200)
    pg.wait_for_timeout(150)
    assert pg.evaluate("() => window.__deskPanes().a.priceZoomed()") is None
    assert not desk_page["errors"], desk_page["errors"]


def test_a_vertical_drag_moves_the_price_and_a_sideways_one_does_not(desk_page):
    """Owner's recording 2026-10-14: "i cannot move the chart up and down using
    the mouse". Dragging down shows higher prices by the distance dragged, the
    time axis follows the library's own sideways drag, and "A" hands the scale
    back to the data."""
    pg = desk_page["pg"]
    a = "window.__deskPanes().a"
    pg.evaluate(f"() => {a}.snapToLive()")
    pg.wait_for_timeout(200)
    box = pg.locator("#chartA .pane-main").bounding_box()
    x, y = box["x"] + box["width"] * 0.45, box["y"] + box["height"] * 0.4
    # a sideways drag with a pixel of wobble: time only
    pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x - 120, y + 2, steps=8); pg.mouse.up()
    pg.wait_for_timeout(150)
    assert pg.evaluate(f"() => {a}.priceZoomed()") is None
    assert not pg.evaluate("() => !document.querySelector('#chartA .auto-btn').hidden")
    pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x, y + 80, steps=10); pg.mouse.up()
    pg.wait_for_timeout(150)
    z = pg.evaluate(f"() => {a}.priceZoomed()")
    assert z is not None and z["max"] > z["min"]
    assert pg.evaluate("() => !document.querySelector('#chartA .auto-btn').hidden"), "the A button shows"
    pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x, y + 40, steps=5); pg.mouse.up()
    pg.wait_for_timeout(150)
    z2 = pg.evaluate(f"() => {a}.priceZoomed()")
    span = z["max"] - z["min"]
    assert z2["max"] - z2["min"] == pytest.approx(span, rel=1e-6), "a drag pans, it does not zoom"
    assert z2["min"] > z["min"], "dragging down shows higher prices"
    # 40 px of the pane's 70 % price area: the range moves by 40 / (0.70 h) of its span
    h = box["height"]
    assert (z2["min"] - z["min"]) / span == pytest.approx(40 / (0.70 * h), rel=0.25)
    pg.click("#chartA .auto-btn")
    pg.wait_for_timeout(150)
    assert pg.evaluate(f"() => {a}.priceZoomed()") is None
    assert pg.evaluate("() => document.querySelector('#chartA .auto-btn').hidden")
    # the library's own drag on the price axis scales by hand: "A" offers the way back too
    ax = box["x"] + box["width"] - 20
    pg.mouse.move(ax, y); pg.mouse.down(); pg.mouse.move(ax, y + 60, steps=6); pg.mouse.up()
    pg.wait_for_timeout(150)
    assert pg.evaluate("() => !document.querySelector('#chartA .auto-btn').hidden"), "A after an axis drag"
    pg.click("#chartA .auto-btn")
    pg.wait_for_timeout(150)
    assert pg.evaluate("() => document.querySelector('#chartA .auto-btn').hidden")
    assert not desk_page["errors"], desk_page["errors"]


def test_back_in_time_the_pane_offers_the_live_edge_and_never_strands_in_empty_future(desk_page):
    """Owner's recording, 2026-10-13 17:53: the 1-minute view ran off into
    empty space and stayed there."""
    pg = desk_page["pg"]
    n = pg.evaluate("() => window.__deskPanes().a.rows().length")
    pg.evaluate("() => window.__deskPanes().a.setRange({from: 40, to: 200})")
    pg.wait_for_timeout(150)
    assert pg.evaluate("() => window.__deskPanes().a.liveButton()") is True
    pg.click("#chartA .live-btn")
    pg.wait_for_function(f"() => window.__deskPanes().a.getRange().to >= {n} - 1", timeout=5000)
    assert pg.evaluate("() => window.__deskPanes().a.liveButton()") is False
    pg.evaluate(f"() => window.__deskPanes().a.setRange({{from: {n} + 40, to: {n} + 200}})")   # all empty future
    pg.wait_for_function(f"() => {{ const r = window.__deskPanes().a.getRange(); return r.to - ({n} - 1) <= 12; }}",
                         timeout=5000)


def test_the_live_tape_redraws_one_bar_not_the_whole_pane(desk_page):
    """Ten-second bars inside the forming minute update the last candle with
    one point per series; a quote that changes no bar redraws nothing."""
    pg, desk = desk_page["pg"], desk_page["desk"]
    pg.evaluate("() => window.__deskPanes().a.snapToLive()")
    pg.wait_for_timeout(300)
    last = pg.evaluate("() => { const r = window.__SESSION__.bars.AAA; return r[r.length - 1]; }")
    minute, before = last[0] + 60, pg.evaluate("() => window.__deskPanes().a.drawStats()")
    for i, (o, h, l, c, v) in enumerate([(4.40, 4.42, 4.39, 4.41, 900), (4.41, 4.44, 4.40, 4.43, 1200),
                                         (4.43, 4.45, 4.42, 4.44, 800)]):
        desk.hub.publish("bar10s", {"symbol": "AAA", "t": minute + 10 * i, "open": o, "high": h, "low": l,
                                    "close": c, "volume": v})
        pg.wait_for_timeout(400)
    after = pg.evaluate("() => window.__deskPanes().a.drawStats()")
    assert after["incremental"] - before["incremental"] >= 2, (before, after)
    assert after["full"] - before["full"] <= 1, "one full draw at most, when the new minute's first bar arrives"
    quiet = pg.evaluate("() => window.__deskPanes().a.drawStats()")
    desk.hub.publish("quote", {"symbol": "AAA", "price": 4.44, "ts": "2026-10-13T14:16:05Z", "bid": 4.43, "ask": 4.45})
    pg.wait_for_timeout(500)
    assert pg.evaluate("() => window.__deskPanes().a.drawStats()") == quiet, "no bar changed: no redraw"


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


def test_the_header_chips_switch_the_overlays_off_and_on(synth_page):
    """Owner, 2026-10-14: "the possibility to switch off the default indicators
    such as trendlines and supp/res". A chip on the card's header flips the
    pane's own setting — the ƒ menu shows the same — and a second click brings
    the overlay back."""
    pg = synth_page["pg"]
    a = "window.__deskPanes().a"
    chip = "[data-card=chart-1m] .ov-chip[data-key={}]"
    menu_box = """() => Array.from(document.querySelectorAll('#chartA .ind-menu label'))
      .find(l => l.textContent.startsWith('{}')).querySelector('input').checked"""
    assert pg.evaluate(f"() => !!{a}.trendDrawn()") and pg.evaluate(f"() => !!{a}.levelsDrawn()")
    assert pg.get_attribute(chip.format("trend"), "aria-pressed") == "true"
    pg.click(chip.format("trend"))
    pg.click(chip.format("levels"))
    pg.wait_for_timeout(150)
    assert pg.evaluate(f"() => {a}.trendDrawn()") is None and pg.evaluate(f"() => {a}.levelsDrawn()") is None
    assert pg.get_attribute(chip.format("trend"), "aria-pressed") == "false"
    assert pg.evaluate(menu_box.replace("{}", "Trend lines")) is False, "the ƒ menu says the same"
    assert pg.evaluate("() => window.__deskPanes().b.trendDrawn()") is not None, "the other pane keeps its own"
    pg.click(chip.format("trend"))
    pg.click(chip.format("levels"))
    pg.wait_for_timeout(150)
    assert pg.evaluate(f"() => !!{a}.trendDrawn()") and pg.evaluate(f"() => !!{a}.levelsDrawn()")
    assert pg.evaluate(menu_box.replace("{}", "Trend lines")) is True
    assert pg.locator("[data-card=chart-daily] .ov-chip").count() == 0, "the daily has none of these overlays"
    assert not synth_page["errors"], synth_page["errors"]
