"""Look-ahead and point-in-time tests (brief section 32).

These are the tests that decide whether any number this study produces means
anything. They are written to FAIL if a future bar ever becomes reachable.
"""
import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data import Bar                                    # noqa: E402
from src.indicators import SessionState                     # noqa: E402
from src.setups import Params, SetupEngine, Variant         # noqa: E402
from src.backtest import run_day                            # noqa: E402
from src.execution import REALISTIC                         # noqa: E402

ET = ZoneInfo("America/New_York")
P = Params()
VA = Variant("A", "First pullback",
             ("impulse", "pullback_structure", "retracement", "risk_structural"))


def mk(day, t0, seq):
    """seq: list of (o,h,l,c,v) starting at t0 ET, one bar per minute."""
    base = int(dt.datetime.combine(day, t0, ET).timestamp())
    return [Bar(base + 60 * i, *row) for i, row in enumerate(seq)]


def ramp(n=60, start=5.0, step=0.01, vol=20000):
    return [(start + i * step, start + i * step + 0.02,
             start + i * step - 0.02, start + i * step + 0.01, vol) for i in range(n)]


# --------------------------------------------------------------- HOD ------
def test_hod_is_high_so_far_not_eventual_daily_high():
    day = dt.date(2026, 8, 3)
    seq = ramp(20, 5.0)
    seq += [(5.20, 5.25, 5.18, 5.22, 30000)]          # local high at index 20
    seq += [(5.22, 5.23, 5.10, 5.12, 20000)]          # dip
    seq += [(5.12, 9.99, 5.10, 9.90, 90000)]          # the eventual daily high
    bars = mk(day, dt.time(9, 30), seq)
    st = SessionState("X", day, prev_close=4.0)
    hods = [st.update(b).hod for b in bars]
    assert hods[20] == 5.25, "HOD at bar 20 must be the high SO FAR"
    assert hods[21] == 5.25, "a dip cannot raise HOD"
    assert hods[22] == 9.99, "HOD only becomes 9.99 on the bar that prints it"
    assert max(hods[:22]) < 9.99, "the eventual daily high leaked backwards"


def test_hod_monotonic_non_decreasing():
    day = dt.date(2026, 8, 3)
    bars = mk(day, dt.time(9, 30), ramp(40) + [(5.4, 5.4, 3.0, 3.1, 99999)])
    st = SessionState("X", day, prev_close=4.0)
    hods = [st.update(b).hod for b in bars]
    assert all(b >= a for a, b in zip(hods, hods[1:]))


# ---------------------------------------------------- indicator causality --
def test_prefix_reproduces_exactly():
    """Feeding bars 0..k must give identical values to the first k+1 values of
    a full-day pass. If any indicator peeked forward this fails."""
    day = dt.date(2026, 8, 3)
    bars = mk(day, dt.time(9, 30), ramp(90))
    full = []
    st = SessionState("X", day, prev_close=4.0)
    for b in bars:
        s = st.update(b)
        full.append((s.ema9, s.ema20, s.macd, s.macd_hist, s.atr, s.vwap, s.hod,
                     s.cum_volume))
    for k in (10, 30, 55, 89):
        st2 = SessionState("X", day, prev_close=4.0)
        got = None
        for b in bars[:k + 1]:
            s = st2.update(b)
            got = (s.ema9, s.ema20, s.macd, s.macd_hist, s.atr, s.vwap, s.hod,
                   s.cum_volume)
        assert got == full[k], f"prefix mismatch at bar {k}"


def test_engine_cannot_address_future_bars():
    """The engine keeps its own snapshot list. Assert it never grows past the
    bar it was handed."""
    day = dt.date(2026, 8, 3)
    bars = mk(day, dt.time(9, 30), ramp(80))
    st = SessionState("X", day, prev_close=4.0)
    eng = SetupEngine("X", day, P, VA)
    for i, b in enumerate(bars):
        eng.step(st.update(b), in_position=False)
        assert len(eng.snaps) == i + 1


# ------------------------------------------------------- truncation audit --
def _impulse_day():
    """A day with a real 6% push, a two-bar dip and a break of the dip high."""
    seq = ramp(35, 5.00, 0.001, 8000)                 # quiet baseline
    seq += [(5.05, 5.18, 5.04, 5.17, 60000),          # push bar 1
            (5.17, 5.34, 5.16, 5.33, 70000)]          # push bar 2  (+5.9%)
    seq += [(5.33, 5.34, 5.24, 5.26, 12000)]          # red dip bar
    seq += [(5.26, 5.45, 5.25, 5.44, 40000)]          # breaks the dip high
    seq += [(5.44, 5.70, 5.42, 5.68, 40000)]          # runs
    seq += [(5.68, 5.90, 5.60, 5.85, 30000)]
    seq += ramp(20, 5.85, 0.0, 15000)
    return seq


def test_truncation_audit_trades_identical_before_cutoff():
    """Truncate the session at successive cut-offs and re-run. Any trade
    entered before a cut-off must come back identical."""
    day = dt.date(2026, 8, 3)
    bars = mk(day, dt.time(9, 30), _impulse_day())
    full = run_day("X", day, bars, P, VA, REALISTIC, "pessimistic",
                   prev_close=4.50)
    for cut in (45, 50, 55, 60):
        part = run_day("X", day, bars[:cut], P, VA, REALISTIC, "pessimistic",
                       prev_close=4.50)
        cut_ts = bars[cut - 1].ts
        a = [(t.entry_ts, round(t.entry_fill, 6), round(t.stop, 6))
             for t in full.trades if t.entry_ts <= cut_ts]
        b = [(t.entry_ts, round(t.entry_fill, 6), round(t.stop, 6))
             for t in part.trades if t.entry_ts <= cut_ts]
        # entries must match; exits may differ because the truncated day
        # force-flats early, which is correct behaviour, not leakage
        assert [x[0] for x in a] == [x[0] for x in b], f"entry set changed at cut {cut}"
        assert a == b, f"entry price/stop changed at cut {cut}"


def test_entry_never_precedes_its_scan_timestamp():
    day = dt.date(2026, 8, 3)
    bars = mk(day, dt.time(9, 30), _impulse_day())
    scan_ts = bars[30].ts
    res = run_day("X", day, bars, P, VA, REALISTIC, "pessimistic",
                  prev_close=4.50, scan_ts=scan_ts)
    for t in res.trades:
        assert t.entry_ts >= scan_ts


def test_setup_fields_use_no_future_information():
    """Every recorded setup's HOD must equal the running high through its own
    bar, computed independently."""
    day = dt.date(2026, 8, 3)
    bars = mk(day, dt.time(9, 30), _impulse_day())
    res = run_day("X", day, bars, P, VA, REALISTIC, "pessimistic", prev_close=4.50)
    by_ts = {b.ts: i for i, b in enumerate(bars)}
    for s in res.observed:
        i = by_ts[s.ts]
        assert abs(s.hod_at_time - max(b.h for b in bars[:i + 1])) < 1e-9
