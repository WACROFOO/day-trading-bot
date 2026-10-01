"""scripts/rules_audit.py: its costs equal backtest_recent's live model at the
live sizing, its default fill equals plans_for_day's, and the portfolio holds
the slot from the order, locks the day like journal.risk, and one position."""
import sys
from datetime import datetime, time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))

import backtest_recent as E  # noqa: E402
import rules_audit as RA  # noqa: E402

ET = ZoneInfo("America/New_York")


def test_cost_live_matches_backtest_recent_at_live_sizing():
    E.COST_MODEL = "live"
    try:
        for entry, stop, stopish, pm, dv5 in [(3.0, 2.9, True, False, 2e5), (12.5, 12.1, False, True, 4e4),
                                              (5.2, 5.0, True, True, 1e6)]:
            assert RA.cost_live(entry, stop, stopish, pm, dv5) == E.cost_r(entry, stop, stopish, pm=pm, dv5=dv5)
    finally:
        E.COST_MODEL = "old"


def _bar(h, m, o, hi, lo, c):
    return (datetime(2024, 3, 4, h, m, tzinfo=ET), o, hi, lo, c, 1000)


def test_fill_retouch_defaults_reproduce_the_a10_fill():
    entry = 5.00
    fwd = [_bar(9, 40, 4.95, 4.99, 4.90, 4.97), _bar(9, 41, 4.98, 5.05, 4.97, 5.03)]
    assert RA.fill_retouch(fwd, entry, 3, 0.3) == (1, entry, "entry")         # touched inside the cap
    gap = [_bar(9, 40, 5.10, 5.20, 5.09, 5.15), _bar(9, 41, 5.12, 5.13, 5.01, 5.05)]
    assert RA.fill_retouch(gap, entry, 3, 0.3) == (1, RA.cap_of(entry, 0.3), "cap_return")  # came back
    assert RA.fill_retouch(gap, entry, 1, 0.3) is None                         # no return inside a 1-bar expiry
    assert RA.fill_retouch([_bar(9, 40, 5.01, 5.02, 4.99, 5.0)], entry, 3, 0.3) == (0, 5.01, "open")


def test_run_exit_trails_and_flattens_with_spread():
    bars = [_bar(10, 0, 5.0, 5.3, 4.95, 5.25), _bar(10, 1, 5.25, 5.3, 5.18, 5.2)]
    r, stopish, k = RA.run_exit(bars, 5.0, 4.9, 5.0, 1.0, dtime(11, 30))
    assert k == 1 and stopish and abs(r - 2.0) < 1e-9                          # trail level 5.20 hit on bar 2
    late = [_bar(11, 30, 5.1, 5.2, 5.0, 5.1)]
    assert RA.run_exit(late, 5.0, 4.9, 5.0, 1.0, dtime(11, 30))[1] is True      # a flatten pays the spread


def _p(sym, t, arm, out, red=()):
    return {"sym": sym, "day": "2024-03-04", "t": t, "arm": arm, "entry": 5.0, "stop": 4.8, "stop_pct": 4.0,
            "fade": 5.0, "red": list(red), "fade_prev": 5.0, "red_prev": list(red), "retrace": 0.3,
            "macd_line_pos": True, "push_rising": True, "push_elevated": True,
            "pm": False, "dv5": 5e5, "spread_ratio": 20.0, "out": {("A", "base"): out}}


def test_portfolio_one_position_slot_from_the_order_and_daily_lock():
    t0 = 1_709_560_000
    a = _p("AAA", "10:00", t0, None)                                 # unfilled: holds the slot 3 minutes
    b = _p("BBB", "10:01", t0 + 60, (t0 + 120, t0 + 300, 1.0, True, 5.0))   # inside AAA's expiry: skipped
    c = _p("CCC", "10:10", t0 + 600, (t0 + 660, t0 + 700, -1.0, True, 5.0))
    d = _p("DDD", "10:20", t0 + 1200, (t0 + 1260, t0 + 1300, -1.0, True, 5.0))
    e = _p("EEE", "10:30", t0 + 1800, (t0 + 1860, t0 + 1900, -1.0, True, 5.0))
    f = _p("FFF", "10:40", t0 + 2400, (t0 + 2460, t0 + 2500, 2.0, True, 5.0))   # after 3 losses: locked
    tr = RA.portfolio({"2024-03-04": [a, b, c, d, e, f]}, dict(RA.BASE))
    assert [t["sym"] for t in tr] == ["CCC", "DDD", "EEE"]
    off = RA.portfolio({"2024-03-04": [a, b, c, d, e, f]}, dict(RA.BASE, streak=None, loss=None))
    assert [t["sym"] for t in off] == ["CCC", "DDD", "EEE", "FFF"]


def test_corrected_modes_change_only_the_ambiguous_bars():
    """Review 2026-10-01: on a cap-return fill the fill bar's high may have come
    before the fill; mode C ratchets with max(fill, close). CA treats a fill-bar
    low under the stop as earlier than a fill at the trigger. H puts each later
    bar's high first."""
    entry, stop = 5.0, 4.8
    fill_bar = _bar(10, 0, 5.30, 5.40, 5.00, 5.05)            # opened above the cap, filled at the cap on the way down
    nxt = _bar(10, 1, 5.05, 5.10, 4.95, 5.00)
    cap = RA.cap_of(entry, 0.3)
    r_a = RA.run_exit([fill_bar, nxt], entry, stop, cap, 1.0, dtime(11, 30), "A", "cap_return")
    r_c = RA.run_exit([fill_bar, nxt], entry, stop, cap, 1.0, dtime(11, 30), "C", "cap_return")
    assert r_a[2] == 1 and r_a[0] > 0                          # A: trail at 5.20 from the 5.40 high, stopped there
    assert r_c[2] == 1 and r_c[0] < r_a[0]                     # C: no ratchet from a pre-fill high
    low_first = _bar(10, 0, 4.90, 5.10, 4.78, 5.05)            # opened under the trigger, low under the stop
    after = _bar(10, 1, 5.05, 5.30, 5.02, 5.25)
    assert RA.run_exit([low_first, after], entry, stop, entry, 1.0, dtime(11, 30), "C", "entry")[2] == 0
    assert RA.run_exit([low_first, after], entry, stop, entry, 1.0, dtime(11, 30), "CA", "entry")[2] == 1
    spike = _bar(10, 1, 5.05, 5.60, 5.20, 5.30)                # high then a fade to 5.20 inside the minute
    tail = _bar(10, 2, 5.30, 5.35, 5.25, 5.30)
    first = _bar(10, 0, 4.99, 5.05, 4.99, 5.05)
    rh = RA.run_exit([first, spike, tail], entry, stop, entry, 1.0, dtime(11, 30), "H", "entry")
    rc = RA.run_exit([first, spike, tail], entry, stop, entry, 1.0, dtime(11, 30), "C", "entry")
    assert rh[2] == 1 and abs(rh[0] - 2.0) < 1e-9              # H: trail raised to 5.40 by the spike, faded through
    assert rc[2] == 2 and rc[0] < 0.5 + 1e-9 or rc[2] == 2     # C: the low is tested before the spike raises the stop


def _plan(t="09:31", arm_et=(9, 31), fill_et=(9, 30), **kw):
    ET = ZoneInfo("America/New_York")
    arm = int(datetime(2025, 3, 3, *arm_et, tzinfo=ET).timestamp())
    t_in = int(datetime(2025, 3, 3, *fill_et, tzinfo=ET).timestamp())
    p = {"sym": "X", "day": "2025-03-03", "t": t, "arm": arm, "entry": 5.0, "stop": 4.85, "stop_pct": 3.0,
         "fade": 0.0, "fade_prev": 0.0, "red": [], "red_prev": [], "retrace": 0.3, "macd_line_pos": True,
         "push_rising": True, "push_elevated": True, "pm": False, "dv5": 1e6, "spread_ratio": 50.0,
         "out": {("A", "base"): (t_in, t_in + 120, 1.0, False, 5.0)}}
    p.update(kw)
    return p


def test_opening_risk_hooks_addendum_2026_10_01c():
    base = dict(RA.BASE)
    assert RA.passes(_plan(range5=0.10), dict(base, range_k=1.0))           # 0.15 stop >= 0.10 range
    assert not RA.passes(_plan(range5=0.20), dict(base, range_k=1.0))       # 0.15 < 0.20
    assert not RA.passes(_plan(range5=None), dict(base, range_k=1.0))       # unknown range: refused
    assert RA.passes(_plan(plan_index=3), dict(base, max_index=3))
    assert not RA.passes(_plan(plan_index=4), dict(base, max_index=3))
    assert RA.passes(_plan(range5=None, plan_index=9), base)                 # B ignores both fields
    p = _plan(t="09:29", arm_et=(9, 29), fill_et=(9, 30))
    assert len(RA.portfolio({"2025-03-03": [p]}, base)) == 1
    assert RA.portfolio({"2025-03-03": [p]}, dict(base, lockout="09:32")) == []        # 09:30 fill cancelled
    late = _plan(t="09:31", arm_et=(9, 31), fill_et=(9, 32))
    assert len(RA.portfolio({"2025-03-03": [late]}, dict(base, lockout="09:32"))) == 1
