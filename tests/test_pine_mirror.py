"""The Pine Script is the desk's mirror on a TradingView chart. It went stale
once — daily RVOL, a 2-minute Running Up, signal-bar bands — while the
platform moved on. These checks pin its defaults to the platform's constants
and the shared profile so the two cannot drift apart silently again.

Pine cannot be compiled here; this is a parity check, not a compile check."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from momentum_platform.scanners import five_pillars as fp  # noqa: E402
from momentum_platform.scanners.momentum_events import HodMomentumScanner, UptrendScanner  # noqa: E402
from momentum_platform.pullback import FirstPullbackDetector  # noqa: E402

PINE = ROOT / "CLAUDE_ROSS_TRADING_MASTERY_2026-08-31" / "assets" / "ross_style_momentum_scanner.pine"
PROFILE = json.loads((ROOT / "config" / "desk-profile.json").read_text())


def _default(name: str) -> float:
    """The default value of a Pine input by variable name."""
    m = re.search(rf"^\s*(?:float|int|bool|string)\s+{name}\s*=\s*input\.\w+\(([^,]+),", PINE.read_text(), re.M)
    assert m, f"no input named {name} in the Pine"
    raw = m.group(1).strip().strip('"')
    try:
        return float(raw)
    except ValueError:
        return raw


def test_pine_is_version_six_and_declares_itself_a_mirror():
    src = PINE.read_text()
    assert src.startswith("//@version=6")
    assert "desk mirror" in src.splitlines()[1]
    assert "does not reproduce Warrior" in src


def test_pine_pillar_defaults_are_the_confirmed_course_values():
    assert _default("minPrice") == fp.PRICE_MIN_CONFIRMED
    assert _default("maxPrice") == fp.PRICE_MAX_CONFIRMED
    assert _default("minGainPct") == fp.GAIN_MIN_PCT
    assert _default("minRvol") == fp.RVOL_MIN
    assert _default("maxFloatM") * 1_000_000 == fp.FLOAT_MAX_SHARES


def test_pine_desk_band_and_liquidity_gate_follow_the_shared_profile():
    assert _default("deskMinPrice") == PROFILE["desk"]["priceMin"]
    assert _default("deskMaxPrice") == PROFILE["desk"]["priceMax"]
    assert _default("minVolume5m") == PROFILE["liquidity"]["minVolume5m"]
    assert _default("minPillars") == PROFILE["liquidity"]["minPillars"]
    assert _default("baselineSessions") == PROFILE["cadence"]["volumeProfileDays"]


def test_pine_running_up_is_the_ten_minute_uptrend():
    up = UptrendScanner()
    assert _default("runUpMins") == up.window_minutes == 10
    assert _default("runUpPct") == up.threshold_pct == 3.0
    assert _default("runUpFreshMin") == up.fresh_minutes == 3
    src = PINE.read_text()
    assert "vwapWin" in src and "freshHigh >= windowHigh" in src, "fresh high and window VWAP are part of the rule"
    assert "f_edge(runningUpNow, 3)" in src, "one alert per leg, re-armed after three failing bars"


def test_pine_hod_rule_matches_the_scanner():
    hod = HodMomentumScanner()
    assert _default("hodAdvancePct") == hod.min_hod_advance_pct
    assert _default("hodMinGainPct") == hod.min_change_pct
    assert _default("hodMinRvol5m") == hod.min_recent_rvol
    assert _default("eventMinPrice") == hod.min_price
    assert _default("lowFloatMaxM") * 1_000_000 == hod.low_float_max
    assert _default("mediumFloatMaxM") * 1_000_000 == hod.medium_float_max
    assert _default("highRvolMin") == hod.high_rvol_min


def test_pine_plan_is_the_first_pullback_detector():
    d = FirstPullbackDetector()
    assert _default("minImpulseBars") == d.min_impulse_bars
    assert _default("maxImpulseBars") == d.max_impulse_bars
    assert _default("minImpulseRangePct") == d.min_impulse_range_pct
    assert _default("maxPullbackBars") == d.max_pullback_bars
    assert _default("entryBuffer") == d.entry_buffer
    assert _default("stopBuffer") == d.stop_buffer
    assert _default("rewardR") == d.reward_multiple
    assert _default("expireArmedAfter") == d.expire_armed_after_bars
    src = PINE.read_text()
    assert "planVolOk := array.avg(pbV) < array.avg(impV)" in src, "light-volume pullback is recorded, as the desk does"


def test_pine_rvol_is_time_of_day_with_a_daily_fallback_and_says_which():
    src = PINE.read_text()
    assert 'input.string("Time of day", "RVOL measure"' in src
    assert "array.median(seen)" in src, "median across sessions that had traded by this bucket"
    assert "int BUCKETS = 192" in src, "five-minute buckets across 04:00–20:00 ET, like the desk"
    assert 'rvolLabel = usingTod ? "time of day" : "daily"' in src


def test_pine_keeps_the_first_ten_screener_columns_in_order():
    """Pine Screener columns are addressed by plot order; a saved screen must
    keep working across the upgrade."""
    titles = re.findall(r'^plot\([^,]+,\s*"([^"]+)"', PINE.read_text(), re.M)
    assert titles[:10] == [
        "Pillar score (0-4)", "Price", "Gain from prior close %", "RVOL (used)", "5-minute RVOL",
        "Float/supply M", "Technical 4/4 candidate", "Five Pillars HOD", "HOD Momentum", "Running Up",
    ]


def test_pine_has_no_bool_na_and_guards_its_loops():
    """Two Pine v6 traps: a bool can no longer be na, and a `for` whose start
    exceeds its end counts DOWN instead of skipping."""
    src = PINE.read_text()
    assert not re.search(r"^[ \t]*(var\s+)?bool\s+\w+\s*=\s*na[ \t]*(//.*)?$", src, re.M)
    for m in re.finditer(r"^(\s*)for (\w+) = (.+?) to (.+?)$", src, re.M):
        indent, start, end = m.group(1), m.group(3).strip(), m.group(4).strip()
        # every loop here is either a constant-bounded 0..N-1 over a non-empty
        # structure, or sits under an `if` that proves start <= end
        before = src[: m.start()].splitlines()[-3:]
        guarded = any(l.strip().startswith("if ") for l in before) or (start == "0" and end.endswith("- 1"))
        assert guarded, f"unguarded loop: for {m.group(2)} = {start} to {end}"


def test_pine_verdict_mirrors_the_desk_card():
    src = PINE.read_text()
    for needle in ("blockScore", "block52w", "blockVolume", "waitScore", "waitPlan", "waitChase", "waitMomo"):
        assert needle in src
    assert 'verdict = blockers > 0 ? "PASS" : waits > 0 ? "WAIT" : "GO"' in src
    assert "Spread and halt state are not checked here" in src, "what Pine cannot see is said, not hidden"
