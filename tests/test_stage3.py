"""Stage 3 and the partial exit (scripts/stage3.py), on hand-built print tapes."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import stage3 as S3  # noqa: E402

A = 1_700_000_000_000          # the trigger minute's start, ms


def tape(points):
    t = np.array([A + int(s * 1000) for s, _ in points], dtype=np.int64)
    return t, np.array([p for _, p in points], dtype=np.float64)


def test_dip_entry_buys_the_break_of_the_10s_pullback_candle():
    # cross candle 0-10 s pushes to 5.10; 10-20 s dips (high 5.06); 20-30 s breaks 5.07
    T, P = tape([(2, 5.01), (5, 5.10), (12, 5.06), (15, 5.03), (22, 5.05), (24, 5.08), (26, 5.12)])
    got = S3.entry_dip(T, P, stop=4.90, cross_candle_start=A, t_order=A + 14_000)
    i, fill, level = got
    assert level == 5.07 and fill == 5.08 and T[i] == A + 24_000      # first print >= 5.07 inside the cap


def test_dip_entry_dies_when_the_stop_trades_first():
    T, P = tape([(2, 5.01), (5, 5.10), (12, 5.00), (16, 4.89), (24, 5.20)])
    assert S3.entry_dip(T, P, stop=4.90, cross_candle_start=A, t_order=A + 14_000) is None


def test_confirm_skips_a_false_break():
    T, P = tape([(3, 5.01), (12, 4.97), (18, 4.98), (25, 5.05)])     # next candle closes 4.98 < 5.00
    assert S3.entry_confirm(T, P, entry=5.00, candle_end=A + 10_000) is None
    T, P = tape([(3, 5.01), (12, 5.02), (25, 5.00), (26, 5.01)])     # closes 5.02: sent at 24 s
    i, fill, _ = S3.entry_confirm(T, P, entry=5.00, candle_end=A + 10_000)
    assert T[i] == A + 25_000 and fill == 5.00


def test_half_at_2r_then_trail_the_rest():
    T, P = tape([(0, 5.00), (2, 5.21), (3, 5.30), (9, 5.25), (10, 5.19)])
    legs, t_out = S3.exit_from(T, P, 0, 5.00, entry=5.00, stop=4.90, flat_ms=A + 3_600_000, half_at_r=2.0)
    assert legs[0] == (0.5, 5.20, "target")
    assert legs[1][2] == "trail" and legs[1][1] == 5.19                # trail 5.30 - 0.10 = 5.20 from 5 s
    g, c, stopish = S3.price_trade(5.00, 4.90, 5.00, legs, 0.02, 0.02)
    # 400 shares: 200 at +0.20, 200 at +0.19 -> (40 + 38) / 40
    assert round(g, 3) == round((200 * 0.20 + 200 * 0.19) / 40.0, 3) and stopish


def test_a_stop_before_the_target_takes_everything():
    T, P = tape([(0, 5.00), (2, 5.05), (3, 4.88)])
    legs, _ = S3.exit_from(T, P, 0, 5.00, entry=5.00, stop=4.90, flat_ms=A + 3_600_000, half_at_r=2.0)
    assert legs == [(1.0, 4.88, "stop")]
