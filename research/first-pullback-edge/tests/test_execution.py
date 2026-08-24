"""Fill-ordering, ambiguity and stop-limit tests (brief section 32)."""
import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data import Bar                                          # noqa: E402
from src.execution import CostModel, GROSS, try_fill              # noqa: E402
from src.indicators import SessionState                           # noqa: E402
from src.setups import Params, Setup, Variant                     # noqa: E402
from src.backtest import run_day                                  # noqa: E402
from tests.test_lookahead import mk, ramp                         # noqa: E402

ET = ZoneInfo("America/New_York")
P = Params()
VA = Variant("A", "First pullback",
             ("impulse", "pullback_structure", "retracement", "risk_structural"))


def _setup(trigger=5.00, stop=4.90, shares=100) -> Setup:
    return Setup(
        sym="X", day="2026-08-03", ts=0, et="2026-08-03T09:45:00", kind="pullback",
        scan_ts=None, gap_pct=20.0, price=4.98, rvol_at_time=3.0, cum_volume=1e6,
        cum_dollar_volume=5e6, dollar_per_min_20=2e5, impulse_start_bar=0,
        impulse_peak_bar=3, push_start_price=4.5, push_peak=5.05, push_pct=12.0,
        push_atr=3.0, push_efficiency=0.8, push_rvol=4.0, push_dollar_volume=3e5,
        push_bars=3, pullback_number=1, pullback_bars=1, red_pullback_bars=1,
        pullback_low=4.91, pullback_depth_pct=25.0, pullback_volume_ratio=0.4,
        trigger=trigger, stop=stop, uses_atr_stop=False,
        risk_per_share=trigger - stop, risk_pct=2.0, risk_atr=1.0,
        target_t1=trigger + (trigger - stop), target_t2=trigger + 2 * (trigger - stop),
        planned_shares=shares, vwap=4.9, ema9=4.95, ema20=4.9, macd=0.02,
        macd_hist=0.01, atr=0.10, confluence_count=2, support_reasons="vwap|ema9",
        hod_at_time=5.05, room_to_hod_r=0.5, is_new_high_trigger=False,
        halt_band_width=0.50, gates={})


def _snap(o, h, l, c, v, atr=0.10, spread=0.01):
    day = dt.date(2026, 8, 3)
    st = SessionState("X", day, prev_close=4.0)
    base = int(dt.datetime.combine(day, dt.time(9, 45), ET).timestamp())
    s = st.update(Bar(base, o, h, l, c, v))
    s.atr = atr
    s.spread_est = spread
    return s


# ----------------------------------------------------- stop-limit entries --
def test_no_touch_is_not_a_fill():
    out = try_fill(_setup(), _snap(4.90, 4.99, 4.88, 4.95, 1e6), GROSS, P, 1.0)
    assert out[0] == "NO_TOUCH"


def test_clean_touch_fills_at_the_trigger():
    outcome, px, sh, slip = try_fill(_setup(), _snap(4.95, 5.10, 4.93, 5.05, 1e6),
                                     GROSS, P, 1.0)
    assert outcome == "FILL"
    assert abs(px - 5.00) < 1e-9, "a bar that opened below the trigger fills AT it"
    assert sh == 100


def test_gap_through_the_limit_is_a_miss_not_a_fill():
    """brief section 10: price gapping past the permitted entry range must
    produce a MISSED trade, not an impossible fill."""
    s = _setup(trigger=5.00)                    # cap = 5.05 at 1%
    outcome, px, sh, _ = try_fill(s, _snap(5.40, 5.60, 5.35, 5.55, 1e6), GROSS, P, 1.0)
    assert outcome == "MISS_GAP"
    assert sh == 0 and px == 0.0


def test_open_above_trigger_but_inside_cap_fills_at_the_open():
    outcome, px, _, _ = try_fill(_setup(trigger=5.00),
                                 _snap(5.02, 5.20, 5.01, 5.18, 1e6), GROSS, P, 1.0)
    assert outcome == "FILL" and abs(px - 5.02) < 1e-9


def test_slippage_that_breaches_the_cap_is_a_miss():
    stressed = CostModel("t", slip_ticks_min=40, spread_mult=0.0, atr_mult=0.0)
    outcome, _, _, _ = try_fill(_setup(trigger=5.00),
                                _snap(5.02, 5.20, 5.01, 5.18, 1e6), stressed, P, 1.0)
    assert outcome == "MISS_GAP", "a fill worse than the limit is not a fill"


def test_limit_cap_is_the_larger_of_the_percentage_and_the_tick_floor():
    """On a cheap stock the percentage cap is inside the spread, so the tick
    floor governs; on an expensive one the percentage does."""
    from src.execution import entry_limit_cap
    assert abs(entry_limit_cap(3.00, P, 1.0, 10) - 3.10) < 1e-9   # ticks win
    assert abs(entry_limit_cap(30.00, P, 1.0, 10) - 30.30) < 1e-9  # pct wins


def test_limit_cap_does_not_widen_with_the_cost_model():
    """The offset is set before the order goes in. A stressed-slippage run
    must MISS more, never quietly raise its own limit to keep filling."""
    from src.execution import entry_limit_cap
    a = entry_limit_cap(5.00, P, 1.0, 10)
    b = entry_limit_cap(5.00, P, 1.0, 10)
    assert a == b
    s = _setup(trigger=5.00)
    calm, _, _, _ = try_fill(s, _snap(4.95, 5.30, 4.93, 5.25, 1e6), GROSS, P, 1.0)
    rough = CostModel("rough", slip_ticks_min=25, spread_mult=0.0, atr_mult=0.0)
    stressed, _, _, _ = try_fill(s, _snap(4.95, 5.30, 4.93, 5.25, 1e6), rough, P, 1.0)
    assert calm == "FILL" and stressed == "MISS_GAP"


def test_participation_cap_reduces_or_refuses_size():
    s = _setup(shares=100_000)
    outcome, _, sh, _ = try_fill(s, _snap(4.95, 5.10, 4.93, 5.05, 10_000), GROSS, P, 1.0)
    assert outcome == "FILL" and sh == 200, "2% of a 10,000-share minute"
    outcome2, _, sh2, _ = try_fill(s, _snap(4.95, 5.10, 4.93, 5.05, 10), GROSS, P, 1.0)
    assert outcome2 == "MISS_LIQUIDITY" and sh2 == 0


# ------------------------------------------------------- fill ordering ----
def _day_with(entry_bar):
    """A qualifying setup followed by one controlled bar."""
    seq = ramp(35, 5.00, 0.001, 8000)
    seq += [(5.05, 5.18, 5.04, 5.17, 60000), (5.17, 5.34, 5.16, 5.33, 70000)]
    seq += [(5.33, 5.34, 5.24, 5.26, 12000)]        # the red dip bar
    seq += [entry_bar]                               # trigger 5.35, stop 5.23
    seq += ramp(10, 5.40, 0.0, 20000)
    return mk(dt.date(2026, 8, 3), dt.time(9, 30), seq)


def test_entry_only_touched_fills_and_survives():
    bars = _day_with((5.26, 5.45, 5.30, 5.44, 40000))   # never reaches 5.23
    r = run_day("X", dt.date(2026, 8, 3), bars, P, VA, GROSS, "pessimistic",
                prev_close=4.5)
    assert len(r.trades) == 1
    assert not r.trades[0].ambiguous


def test_stop_only_touched_kills_the_order_without_a_trade():
    bars = _day_with((5.26, 5.30, 5.15, 5.20, 40000))   # low 5.15 < stop, high < trigger
    r = run_day("X", dt.date(2026, 8, 3), bars, P, VA, GROSS, "pessimistic",
                prev_close=4.5)
    assert len(r.trades) == 0, "the order must die, not fill"


def test_both_touched_is_ambiguous_and_policy_decides():
    entry_bar = (5.26, 5.45, 5.15, 5.30, 40000)        # clears 5.35 AND breaks 5.23
    day = dt.date(2026, 8, 3)
    bars = _day_with(entry_bar)
    pess = run_day("X", day, bars, P, VA, GROSS, "pessimistic", prev_close=4.5)
    opt = run_day("X", day, bars, P, VA, GROSS, "optimistic", prev_close=4.5)
    exc = run_day("X", day, bars, P, VA, GROSS, "exclude", prev_close=4.5)

    assert pess.ambiguous == 1 and opt.ambiguous == 1
    assert len(pess.trades) == 1 and pess.trades[0].ambiguous
    assert pess.trades[0].net_r < 0, "pessimistic must book the stop"
    assert pess.trades[0].exit_reason.startswith("STOP")
    assert len(exc.trades) == 0, "exclude must drop the trade entirely"
    assert opt.trades[0].net_r > pess.trades[0].net_r, \
        "optimistic must be strictly kinder than pessimistic on the same bar"


def test_ambiguous_bar_is_never_silently_a_winner():
    """The regression this whole policy exists for."""
    bars = _day_with((5.26, 5.60, 5.10, 5.55, 40000))   # would hit +2R and the stop
    r = run_day("X", dt.date(2026, 8, 3), bars, P, VA, GROSS, "pessimistic",
                prev_close=4.5)
    assert len(r.trades) == 1
    t = r.trades[0]
    assert t.ambiguous is True
    assert t.net_r < 0, "a bar covering target AND stop must not book the target"
