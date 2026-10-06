"""E1's 5-minute state machine on synthetic bars (addendum 2026-10-06b).
Checked before the study's first run; no market data here."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]

FM = pytest.importorskip("five_minute")
from momentum_platform.sessions import ET  # noqa: E402

T0 = datetime(2024, 3, 5, 9, 30, tzinfo=ET)


def bars(spec):
    """spec: one (o, h, l, c, v) per minute from 09:30 ET."""
    return [(T0 + timedelta(minutes=i), o, h, l, c, v) for i, (o, h, l, c, v) in enumerate(spec)]


def candle(o, c, lo=None, hi=None, v=1000, n=5):
    """Five 1-minute bars walking from o to c; the candle's low/high forced if given."""
    out = []
    step = (c - o) / n
    for i in range(n):
        a, b = o + step * i, o + step * (i + 1)
        out.append([a, max(a, b), min(a, b), b, v])
    if hi is not None:
        out[n // 2][1] = hi
    if lo is not None:
        out[n // 2][2] = lo
    return [tuple(x) for x in out]


def test_candles_are_clock_aligned_and_carry_their_minutes():
    rows = bars(candle(5.0, 5.5) + candle(5.5, 5.4))
    ks = FM.candles5(rows)
    assert len(ks) == 2 and ks[0]["first"] == 0 and ks[0]["last"] == 4 and ks[1]["first"] == 5
    assert ks[0]["o"] == 5.0 and ks[0]["c"] == pytest.approx(5.5) and ks[0]["v"] == 5000
    assert ks[1]["t"] - ks[0]["t"] == 300


def test_a_red_candle_after_a_green_impulse_places_an_order_at_its_high():
    rows = bars(candle(5.0, 5.3) + candle(5.3, 5.6) + candle(5.6, 5.5, lo=5.45, hi=5.62))
    pl = FM.e1_placements(rows)
    assert len(pl) == 1
    p = pl[0]
    assert p["entry"] == pytest.approx(5.63) and p["stop"] == pytest.approx(5.44)
    k2 = FM.candles5(rows)[2]
    assert p["order_t"] == k2["t"] + 300, "the order rests from the pullback candle's close"
    assert p["seq"] == 1 and p["n_pull"] == 1


def test_a_lower_high_candle_moves_the_order_down_and_the_stop_to_the_lowest_low():
    rows = bars(candle(5.0, 5.3) + candle(5.3, 5.6) + candle(5.6, 5.5, lo=5.45, hi=5.62)
                + candle(5.5, 5.52, lo=5.40, hi=5.58))
    pl = FM.e1_placements(rows)
    assert [round(p["entry"], 2) for p in pl] == [5.63, 5.59]
    assert pl[1]["stop"] == pytest.approx(5.39) and pl[1]["n_pull"] == 2 and pl[1]["seq"] == 1


def test_the_first_candle_to_make_a_new_high_ends_the_setup():
    rows = bars(candle(5.0, 5.3) + candle(5.3, 5.6) + candle(5.6, 5.5, lo=5.45, hi=5.62)
                + candle(5.5, 5.8, hi=5.85) + candle(5.8, 5.9))
    pl = FM.e1_placements(rows)
    assert len(pl) == 1, "no order after the break; the green breakout candle starts the next search"


def test_five_pullback_candles_expire_the_setup():
    spec = candle(5.0, 5.3) + candle(5.3, 5.6)
    hi = 5.6
    for _ in range(5):
        hi -= 0.02
        spec += candle(hi, hi - 0.01, hi=hi, lo=hi - 0.05)
    pl = FM.e1_placements(bars(spec))
    assert len(pl) == FM.MAX_PULLBACK


def test_a_short_impulse_is_not_a_setup():
    rows = bars(candle(5.0, 5.04) + candle(5.04, 5.06) + candle(5.06, 5.0))
    assert FM.e1_placements(rows) == [], "two green candles spanning 1.2 % are under the 2 % impulse"


def test_the_owners_case_needs_four_green_minutes_ending_at_a_new_high():
    up = [(5.0 + 0.1 * i, 5.1 + 0.1 * i, 5.0 + 0.1 * i, 5.1 + 0.1 * i, 1000) for i in range(4)]
    rows = bars(up)
    assert FM.extended_inside(rows, 0, 3)
    broken = up[:2] + [(5.2, 5.25, 5.1, 5.15, 1000)] + up[3:]
    assert not FM.extended_inside(bars(broken), 0, 3)
    below = [(6.0, 6.5, 6.0, 6.4, 1000)] + up                         # an earlier high above the run
    assert not FM.extended_inside(bars(below), 1, 4)
