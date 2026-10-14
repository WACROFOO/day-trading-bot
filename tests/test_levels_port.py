"""The desk's levels in Python (src/momentum_platform/levels.py) against levels.js, and the
one-day tracker against the direct port: the research of amendment 2026-10-14 scores the
lines the desk draws only if both say the same thing on the same bars."""
from __future__ import annotations

import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from momentum_platform import levels as LV  # noqa: E402

LEVELS_JS = ROOT / "src" / "momentum_platform" / "dashboard" / "web" / "levels.js"


def bars_for(seed: int, n: int = 260, start: float = 4.0, tick: float = 0.01) -> list[list[float]]:
    """Trending legs with pullbacks, prices on the cent so equal highs and lows happen."""
    rnd = random.Random(seed)
    out, px, t = [], start, 1_760_000_000
    drift = 0.0
    for i in range(n):
        if i % rnd.randint(8, 25) == 0:
            drift = rnd.choice((-1, 1)) * rnd.uniform(0.0005, 0.004)
        o = px
        c = max(0.5, o * (1 + drift + rnd.gauss(0, 0.004)))
        h = max(o, c) * (1 + abs(rnd.gauss(0, 0.002)))
        lo = min(o, c) * (1 - abs(rnd.gauss(0, 0.002)))
        r = lambda x: round(round(x / tick) * tick, 4)  # noqa: E731
        o, h, lo, c = r(o), r(h), r(lo), r(c)
        h, lo = max(h, o, c), min(lo, o, c)
        out.append([t + 60 * i, o, h, lo, c, rnd.randint(1_000, 90_000)])
        px = c
    return out


def run_node(script: str, payload) -> object:
    if shutil.which("node") is None:
        pytest.skip("no node binary")
    code = (f"const L = require({json.dumps(str(LEVELS_JS))});\n"
            "const IN = JSON.parse(require('fs').readFileSync(0, 'utf8'));\n"
            f"{script}\n")
    out = subprocess.run(["node", "-e", code], input=json.dumps(payload), capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


LINE_KEYS = ("a", "b", "pa", "pb", "slope", "touches", "brokeAt", "breakPrice", "now", "through")


def _line(x):
    return None if x is None else {k: getattr(x, k) for k in LINE_KEYS}


def _same(a, b, path=""):
    if isinstance(a, dict):
        assert isinstance(b, dict) and set(a) == set(b), (path, a, b)
        for k in a:
            _same(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        assert isinstance(b, list) and len(a) == len(b), (path, a, b)
        for i, (x, y) in enumerate(zip(a, b)):
            _same(x, y, f"{path}[{i}]")
    elif isinstance(a, float) or isinstance(b, float):
        assert a is not None and b is not None and a == pytest.approx(b, rel=1e-12, abs=1e-12), (path, a, b)
    else:
        assert a == b, (path, a, b)


def test_the_python_port_draws_what_levels_js_draws():
    cases = []
    for seed in range(24):
        bars = bars_for(seed, n=200 + 10 * (seed % 5), start=(0.8 if seed % 6 == 0 else 3.0 + seed))
        rnd = random.Random(seed)
        cuts = sorted({rnd.randint(8, len(bars)) for _ in range(6)} | {len(bars)})
        cases.append({"bars": bars, "cuts": cuts, "from": rnd.choice((0, 0, 30))})
    js = run_node("""
      const out = IN.map(cs => cs.cuts.map(n => {
        const b = cs.bars.slice(0, n), last = b[b.length - 1][4], a = L.atr(b, 14);
        const tl = a ? L.trendLines(b.slice(0, b.length - 1), last, a, { from: cs.from }) : null;
        const strip = x => x ? { a: x.a, b: x.b, pa: x.pa, pb: x.pb, slope: x.slope, touches: x.touches,
                                  brokeAt: x.brokeAt, breakPrice: x.breakPrice, now: x.now, through: x.through } : null;
        return { piv: L.pivots(b), atr: a, fan: a ? L.srFan(b, last, a) : null,
                 tl: tl ? { up: strip(tl.up), down: strip(tl.down), upBroken: strip(tl.upBroken),
                            downBroken: strip(tl.downBroken) } : null,
                 round: L.roundLevels(last) };
      }));
      process.stdout.write(JSON.stringify(out));""", cases)
    lines_seen = fans_seen = 0
    for cs, got in zip(cases, js):
        for n, g in zip(cs["cuts"], got):
            b = cs["bars"][:n]
            last = b[-1][4]
            a = LV.atr(b, 14)
            _same(LV.pivots(b), g["piv"], "pivots")
            _same(a, g["atr"], "atr")
            _same(LV.round_levels(last), g["round"], "round")
            if a:
                fan = LV.sr_fan(b, last, a)
                _same(fan, g["fan"], "fan")
                tl = LV.trend_lines(b[:-1], last, a, cs["from"])
                _same({k: _line(v) for k, v in tl.items()}, g["tl"], "trendLines")
                lines_seen += sum(1 for v in tl.values() if v is not None)
                fans_seen += len(fan["res"]) + len(fan["sup"])
    assert lines_seen >= 60 and fans_seen >= 200, (lines_seen, fans_seen)


def test_the_atr_series_is_the_atr_of_every_prefix():
    bars = bars_for(3)
    s = LV.atr_series(bars)
    for i in range(len(bars)):
        assert s[i] == LV.atr(bars[:i + 1]), i


def test_the_day_tracker_answers_what_the_direct_port_answers_at_every_bar():
    checked = 0
    for seed in range(10):
        bars = bars_for(100 + seed, n=180)
        day = LV.DayLevels(bars)
        for t in range(1, len(bars)):
            close = bars[t][4]
            a = LV.atr(bars[:t])
            assert day.atr_before(t) == a
            _same(day.fan(t, bars[t - 1][4]), LV.sr_fan(bars[:t], bars[t - 1][4], a), f"fan@{t}")
            for frm in (0, 40):
                want = LV.trend_lines(bars[:t], close, a, frm) if a else {"up": None, "down": None}
                got = day.lines(t, close, frm)
                for side in ("up", "down"):
                    w, g = want[side], got[side]
                    assert (w is None) == (g is None), (seed, t, side, frm)
                    if w is not None:
                        assert (g["a"], g["b"], g["through"]) == (w.a, w.b, w.through), (seed, t, side)
                        assert g["now"] == w.now and g["line"].at(t) == w.now
                        checked += 1
    assert checked >= 500, checked


def test_the_day_tracker_never_reads_a_bar_at_or_after_the_one_asked_about():
    for seed in range(6):
        bars = bars_for(200 + seed, n=200)
        full = LV.DayLevels(bars)
        rnd = random.Random(seed)
        for t in sorted(rnd.sample(range(20, 199), 25)):
            alt = [list(b) for b in bars[:t]] + [[b[0], b[1] * 3, b[2] * 3, b[3] * 3, b[4] * 3, b[5]] for b in bars[t:]]
            cut = LV.DayLevels(alt)
            _same(cut.fan(t, bars[t - 1][4]), full.fan(t, bars[t - 1][4]), f"fan@{t}")
            g1, g2 = full.lines(t, bars[t - 1][4]), cut.lines(t, bars[t - 1][4])
            for side in ("up", "down"):
                assert (g1[side] is None) == (g2[side] is None), (seed, t, side)
                if g1[side] is not None:
                    assert (g1[side]["a"], g1[side]["b"], g1[side]["now"]) == (g2[side]["a"], g2[side]["b"], g2[side]["now"])


def test_the_constants_are_the_pines_and_levels_js():
    if shutil.which("node") is None:
        pytest.skip("no node binary")
    js = run_node("""process.stdout.write(JSON.stringify({PIVOT: L.PIVOT, PIVOTS_KEPT: L.PIVOTS_KEPT, SR_EACH: L.SR_EACH,
      SR_DEDUP_ATR: L.SR_DEDUP_ATR, BAND_ATR: L.BAND_ATR, TL_TOL_ATR: L.TL_TOL_ATR, TL_SWINGS: L.TL_SWINGS,
      TL_KEEP_BROKEN: L.TL_KEEP_BROKEN}));""", None)
    assert js == {k: getattr(LV, k) for k in js}
