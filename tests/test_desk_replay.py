"""Stage 2 (scripts/desk_replay.py): the plan as the live desk arms it, mid-minute."""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import desk_replay as DR  # noqa: E402

ET = ZoneInfo("America/New_York")
START = datetime(2025, 3, 3, 9, 0, tzinfo=ET)


def _rows(n=40):
    """A steady climb so VWAP, EMA9 and MACD are all green on the last bar."""
    out = []
    for i in range(n):
        o = 4.0 + 0.02 * i
        out.append((START + timedelta(minutes=i), o, o + 0.03, o - 0.01, o + 0.02, 10_000))
    return out


def test_arms_at_the_close_of_the_10s_candle_holding_the_cross_plus_latency():
    rows = _rows()
    arm = int(rows[-1][0].timestamp())
    entry = 4.82                                          # trigger high 4.81
    p = {"arm": arm, "entry": entry, "red": []}
    ms = lambda s: (arm + s) * 1000                       # noqa: E731
    t = np.array([ms(1), ms(14), ms(23), ms(40)], dtype=np.int64)
    pr = np.array([4.79, 4.80, 4.83, 4.90], dtype=np.float32)
    sz = np.array([100, 100, 200, 300])
    d = DR.desk_moment(p, rows, t, pr, sz)
    assert d["t_cross"] == ms(23)                          # first print ABOVE 4.81
    assert d["candle_end"] == ms(30)                       # the 20-30 s candle closes at 30 s
    assert d["t_order"] == arm + 30 + DR.LATENCY_S
    assert d["last"] == 4.83                               # the 4.90 print at 40 s is not seen yet
    assert d["red"] == [] and d["secs_before_close"] == 60 - 30 - DR.LATENCY_S


def test_no_print_above_the_trigger_means_the_desk_never_arms():
    rows = _rows()
    arm = int(rows[-1][0].timestamp())
    t = np.array([(arm + 5) * 1000], dtype=np.int64)
    d = DR.desk_moment({"arm": arm, "entry": 4.82, "red": []}, rows, t, np.array([4.81], dtype=np.float32),
                       np.array([100]))
    assert "no last-sale print" in d["why"]


def test_gates_are_judged_on_the_half_formed_minute():
    rows = _rows()
    arm = int(rows[-1][0].timestamp())
    # the forming minute crosses at 3 s, then collapses: the desk saw only the cross
    t = np.array([(arm + 1) * 1000, (arm + 3) * 1000, (arm + 45) * 1000], dtype=np.int64)
    pr = np.array([4.80, 4.83, 3.50], dtype=np.float32)
    d = DR.desk_moment({"arm": arm, "entry": 4.82, "red": []}, rows, t, pr, np.array([100, 100, 5000]))
    assert d["last"] == 4.83 and d["red"] == [] and d["fade"] < 1.0
