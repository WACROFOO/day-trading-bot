"""Tick replay (scripts/tick_replay.py): the live executor's rules on a print sequence."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import tick_replay as TR  # noqa: E402

T0 = 1_700_000_000           # an order time, epoch seconds


def _run(prints, entry=5.00, stop=4.90, flat_after=3600):
    t = np.array([(T0 + s) * 1000 + int(ms) for s, ms, _ in prints], dtype=np.int64)
    p = np.array([px for _, _, px in prints], dtype=np.float64)
    return TR.replay(t, p, entry, stop, T0, T0 + flat_after)


def test_fill_needs_the_trigger_then_a_print_inside_the_cap():
    # cap = 5.00 + max(0.01, 0.3 %) = 5.02 (rounded to the cent)
    out = _run([(1, 0, 4.98), (2, 0, 5.05), (3, 0, 5.01), (4, 0, 4.85)])
    assert out["fill"] == 5.01 and out["t_in"] == (T0 + 3) * 1000        # 5.05 triggered, over the cap
    assert out["how"] == "stop" and out["exit"] == 4.85 and out["stopish"]
    assert round(out["r"], 3) == round((4.85 - 5.01) / 0.10, 3)          # the print through the stop is the slip


def test_prints_before_the_order_do_not_trigger_and_the_entry_expires():
    assert _run([(-5, 0, 5.10), (1, 0, 4.99), (200, 0, 5.00)]) is None   # 200 s > the 3-minute expiry


def test_trail_moves_on_the_runner_cadence_and_never_down():
    prints = [(1, 0, 5.00), (2, 0, 5.30), (6, 500, 5.31), (7, 0, 5.20), (8, 0, 5.19)]
    out = _run(prints)
    # at 6.0 s (fill 1 s + 5 s) the trail rises to 5.30 - 0.10 = 5.20; 5.20 at 7 s exits
    assert out["how"] == "trail" and out["exit"] == 5.20


def test_flat_at_the_cutoff_uses_the_last_print_before_it():
    out = _run([(1, 0, 5.00), (30, 0, 5.08), (61, 0, 5.50)], flat_after=60)
    assert out["how"] == "flat" and out["exit"] == 5.08 and not out["stopish"]


def test_ms_parses_nanosecond_timestamps():
    assert TR._ms("2026-10-01T13:30:23.123456789Z") % 1000 == 123


def test_real_cost_uses_measured_spreads():
    p = {"entry": 5.0, "stop": 4.9, "tick": {"spread_in": 0.02, "spread_out": 0.04}}
    # 400 shares by risk, capped at 400 by $2,000; comm 2 x $2; (0.01 + 0.01) + (0.02 + 0.01) per share
    assert TR.cost_real(p, True) == round((4.0 + 400 * 0.02 + 400 * 0.03) / 40.0, 3)
    assert TR.cost_real(p, False) == round((4.0 + 400 * 0.02) / 40.0, 3)
    assert TR.cost_real({"entry": 5.0, "stop": 4.9, "tick": {}}, False) is None


def test_a_stray_low_print_after_the_trigger_fills_at_the_trigger_not_below():
    out = _run([(1, 0, 5.00), (1, 200, 4.70), (5, 0, 5.40)])
    assert out["fill"] == 5.00                                            # NXL 09:30: 8.74 print, live 8.89


def test_a_print_exactly_at_the_trigger_triggers_even_after_a_float32_round_trip():
    t = np.array([(T0 + 1) * 1000, (T0 + 2) * 1000, (T0 + 3) * 1000], dtype=np.int64)
    p = np.round(np.array([8.86, 8.87, 8.60], dtype=np.float32).astype(np.float64), 4)
    out = TR.replay(t, p, 8.87, 8.61, T0, T0 + 3600)
    assert out is not None and out["fill"] == 8.87
