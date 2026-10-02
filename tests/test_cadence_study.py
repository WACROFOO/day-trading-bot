"""Reaction-speed study (scripts/cadence_study.py): sampling, arming and stop timing on a print tape."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import cadence_study as C  # noqa: E402

A = 1_700_000_000_000
RTH = A + 10_000_000          # regular hours start far after the tape: everything is pre-market


def tape(pts):
    return (np.array([A + int(s * 1000) for s, _ in pts], dtype=np.int64),
            np.array([p for _, p in pts], dtype=np.float64))


def test_order_time_for_each_arming():
    arm = A // 1000
    assert C.order_time(arm, A + 23_400, "candle", 10, 4.0) == A + 34_000
    assert C.order_time(arm, A + 23_400, "candle", 5, 2.5) == A + 27_500
    assert C.order_time(arm, A + 23_400, "print", 0, 1.0) == A + 24_400


def test_premarket_entry_waits_for_a_sample_at_or_above_the_trigger():
    T, P = tape([(0.5, 5.00), (1.2, 4.99), (4.0, 5.01), (6.0, 5.01)])
    # samples every 5 s from t_order=A: at 0 s nothing yet, at 5 s last print 5.01 >= 5.00 -> fill at 6 s
    i, fill = C.entry(T, P, 5.00, A, RTH, 5)
    assert T[i] == A + 6000 and fill == 5.01                 # cap 5.01
    i, fill = C.entry(T, P, 5.00, A, RTH, 1)                 # every second: the 1 s sample sees 5.00
    assert T[i] == A + 1200 and fill == 5.00                 # 4.99 <= cap, filled no better than the trigger


def test_monitored_stop_sells_at_the_sample_not_at_the_first_print_through():
    T, P = tape([(0, 5.00), (1, 4.89), (3, 4.80), (6, 4.70)])
    px, kind, t_out = C.exit_(T, P, 0, 5.00, 5.00, 4.90, A + 3_600_000, True, 5)
    assert kind == "stop" and px == 4.80 and t_out == A + 5000   # checked at 5 s: last print 4.80
    px, kind, _ = C.exit_(T, P, 0, 5.00, 5.00, 4.90, A + 3_600_000, True, 1)
    assert px == 4.89                                             # checked at 1 s


def test_a_resting_stop_triggers_on_the_first_print_through_whatever_the_loop():
    T, P = tape([(0, 5.00), (1, 4.89), (3, 4.80)])
    for period in (1, 5, 10):
        px, kind, _ = C.exit_(T, P, 0, 5.00, 5.00, 4.90, A + 3_600_000, False, period)
        assert px == 4.89 and kind == "stop"


def test_the_trail_moves_only_at_the_loop():
    T, P = tape([(0, 5.00), (1, 5.30), (2, 5.19), (6, 5.19)])
    px, kind, _ = C.exit_(T, P, 0, 5.00, 5.00, 4.90, A + 3_600_000, False, 5)
    assert kind == "trail" and px == 5.19 and _ == A + 6000      # the 5 s move to 5.20 catches the 6 s print
    px, kind, t = C.exit_(T, P, 0, 5.00, 5.00, 4.90, A + 3_600_000, False, 1)
    assert t == A + 2000                                          # the 1 s move already sits at 5.20
