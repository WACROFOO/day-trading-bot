"""Pullback classification and gate-vector tests (brief section 32)."""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.indicators import SessionState                     # noqa: E402
from src.setups import Params, SetupEngine, Variant, halt_band_width  # noqa: E402
from tests.test_lookahead import mk, ramp                   # noqa: E402

P = Params()
VA = Variant("A", "First pullback",
             ("impulse", "pullback_structure", "retracement", "risk_structural"))
V_OBS = Variant("OBS", "observation only", ())     # arms on everything


def _run(seq, variant=V_OBS, day=dt.date(2026, 8, 3), prev_close=4.5):
    bars = mk(day, dt.time(9, 30), seq)
    st = SessionState("X", day, prev_close=prev_close)
    eng = SetupEngine("X", day, P, variant)
    for b in bars:
        eng.step(st.update(b), in_position=False)
    return eng


def _push(start, top, vol=70000):
    """Two green bars carrying price from `start` to `top`."""
    mid = (start + top) / 2
    return [(start, mid, start - 0.01, mid - 0.005, vol),
            (mid - 0.005, top, mid - 0.02, top - 0.01, vol)]


def _dip(top, low, vol=12000):
    return [(top - 0.01, top, low, low + 0.01, vol)]


# ----------------------------------------------------- pullback numbering --
def test_first_pullback_is_numbered_one():
    seq = ramp(35, 5.00, 0.001, 8000) + _push(5.05, 5.34) + _dip(5.34, 5.24)
    eng = _run(seq)
    assert eng.observed, "no setup detected on a clean 5.7% push + dip"
    assert eng.observed[0].pullback_number == 1


def test_second_and_third_pullbacks_are_numbered_in_order():
    """Push, dip, higher push, dip, higher push, dip. The counter must read
    1, 2, 3 - and must not reset while each new leg makes a higher peak.

    The filler bars matter: the ported state machine stays in PULLBACK until
    the dip exceeds max_pullback_bars (ross-fp-v4.pine 1461-1472), so a new
    leg is only DETECTABLE once the previous setup has aged out. That is the
    Pine's behaviour, not an artefact of the test.
    """
    def flat(px):
        return [(px, px + 0.005, px - 0.005, px, 6000)] * 6

    seq = ramp(35, 5.00, 0.001, 8000)
    seq += _push(5.05, 5.34) + _dip(5.34, 5.26) + flat(5.27)
    seq += _push(5.28, 5.62) + _dip(5.62, 5.52) + flat(5.53)
    seq += _push(5.54, 5.99) + _dip(5.99, 5.88)
    eng = _run(seq)
    numbers = []
    for s in eng.observed:
        if not numbers or s.pullback_number != numbers[-1]:
            numbers.append(s.pullback_number)
    assert numbers[:3] == [1, 2, 3], f"got {numbers}"


def test_a_lower_peak_restarts_the_count():
    """A dip off a LOWER high is a new leg, not the fourth pullback of the
    old one - the trend it was counting has broken."""
    seq = ramp(35, 5.00, 0.001, 8000)
    seq += _push(5.05, 5.60) + _dip(5.60, 5.45)
    seq += ramp(20, 5.00, 0.0, 8000)                      # the leg dies
    seq += _push(5.02, 5.30) + _dip(5.30, 5.22)           # lower peak
    eng = _run(seq)
    nums = [s.pullback_number for s in eng.observed]
    assert 1 in nums
    assert max(nums) <= 2, f"counter should have restarted, got {nums}"


def test_pullback_bars_and_reds_are_counted_on_closed_bars_only():
    """Two red bars, the second an inside bar. Both are counted.

    The second bar must NOT undercut the first bar's low: once armed, a bar
    trading through the structural stop kills the setup (ross-fp-v4.pine
    1494-1500) and there is no second pullback bar to count. That path has
    its own test below.
    """
    seq = ramp(35, 5.00, 0.001, 8000) + _push(5.05, 5.34)
    seq += [(5.33, 5.34, 5.28, 5.29, 9000),      # red 1, low 5.28
            (5.29, 5.30, 5.285, 5.288, 8000)]    # red 2, inside bar
    eng = _run(seq)
    last = eng.observed[-1]
    assert last.pullback_bars == 2 and last.red_pullback_bars == 2


def test_armed_order_dies_when_the_next_bar_trades_through_the_stop():
    seq = ramp(35, 5.00, 0.001, 8000) + _push(5.05, 5.34)
    seq += [(5.33, 5.34, 5.28, 5.29, 9000),      # arms: stop 5.27
            (5.29, 5.30, 5.20, 5.22, 8000)]      # trades through it
    eng = _run(seq)
    assert eng.state == "INVALID"
    assert len(eng.observed) == 1, "no setup may be recorded after the kill"


def test_dip_deeper_than_max_retracement_invalidates():
    seq = ramp(35, 5.00, 0.001, 8000) + _push(5.05, 5.34)
    seq += _dip(5.34, 5.34 - (5.34 - 5.04) * 0.80)        # 80% retrace
    eng = _run(seq, variant=VA)
    assert not eng.setups, "an 80% retracement must not arm variant A"
    assert eng.observed and eng.observed[-1].gates["retracement"] is False


def test_dip_longer_than_max_pullback_bars_invalidates():
    seq = ramp(35, 5.00, 0.001, 8000) + _push(5.05, 5.34)
    seq += [(5.33, 5.34, 5.31, 5.32, 9000)] * 6           # six flat/red bars
    eng = _run(seq, variant=VA)
    assert all(s.pullback_bars <= P.max_pullback_bars + 1 for s in eng.observed)
    assert eng.state in ("INVALID", "IDLE", "IMPULSE")


# ---------------------------------------------------------- gate vectors --
def test_every_gate_id_is_present_on_every_observed_setup():
    seq = ramp(35, 5.00, 0.001, 8000) + _push(5.05, 5.34) + _dip(5.34, 5.24)
    eng = _run(seq)
    required = {"impulse", "pullback_structure", "retracement", "risk_structural",
                "momentum", "confluence", "pb_volume", "hod_room", "halt_band"}
    for s in eng.observed:
        assert required <= set(s.gates), f"missing {required - set(s.gates)}"


def test_hod_room_passes_on_a_new_high_trigger():
    seq = ramp(35, 5.00, 0.001, 8000) + _push(5.05, 5.34) + _dip(5.34, 5.24)
    eng = _run(seq)
    s = eng.observed[0]
    # the dip bar's high IS the day high here, so the trigger is above it
    assert s.is_new_high_trigger or (s.room_to_hod_r or 0) >= P.min_room_r
    assert s.gates["hod_room"] is True


def test_hod_room_fails_under_a_lower_high():
    """Trigger well below the session high with less than 1R of headroom.

    The ATR fallback has to be off for this case to be constructible at all,
    and that is itself a finding: with the fallback ON (the shipped default)
    a stop too wide to leave 1R of room is replaced by a ~1-ATR stop, which
    shrinks the risk and hands the room gate back its pass. The HOD gate is
    therefore much weaker in the shipped configuration than it looks.
    """
    import dataclasses
    p_nofallback = dataclasses.replace(P, atr_stop_fallback=False,
                                       max_stop_pct=99.0, max_stop_atr=99.0)
    seq = ramp(35, 5.00, 0.001, 8000)
    seq += _push(5.05, 6.50)                              # sets a high HOD
    seq += [(6.40, 6.45, 5.55, 5.60, 30000)]              # gives it all back
    seq += ramp(6, 5.60, 0.0, 20000)
    seq += _push(5.62, 5.95)
    seq += [(5.94, 5.95, 5.30, 5.34, 25000)]              # deep dip -> wide stop
    bars = mk(dt.date(2026, 8, 3), dt.time(9, 30), seq)
    st = SessionState("X", dt.date(2026, 8, 3), prev_close=4.5)
    eng = SetupEngine("X", dt.date(2026, 8, 3), p_nofallback, V_OBS)
    for b in bars:
        eng.step(st.update(b), in_position=False)
    lows = [s for s in eng.observed
            if not s.is_new_high_trigger and (s.room_to_hod_r or 0) < 1.0]
    assert lows, "expected a lower-high setup with under 1R of headroom"
    assert all(s.gates["hod_room"] is False for s in lows)


def test_confluence_counts_clustered_emas_once():
    seq = ramp(60, 5.00, 0.0005, 9000) + _push(5.05, 5.34) + _dip(5.34, 5.24)
    eng = _run(seq)
    for s in eng.observed:
        assert s.confluence_count <= 3, \
            "four raw supports minus the EMA cluster can never exceed 3"


def test_a_sub_tick_stop_is_refused_by_the_risk_gate():
    """A one-tick stop makes R meaningless - every wiggle reads as tens of R."""
    import dataclasses
    from src.setups import Params as _P
    p = dataclasses.replace(P, min_risk_ticks=5)
    seq = ramp(35, 5.00, 0.001, 8000) + _push(5.05, 5.34)
    seq += [(5.33, 5.34, 5.335, 5.336, 9000)]     # dip low one tick under the high
    bars = mk(dt.date(2026, 8, 3), dt.time(9, 30), seq)
    st = SessionState("X", dt.date(2026, 8, 3), prev_close=4.5)
    eng = SetupEngine("X", dt.date(2026, 8, 3), p, V_OBS)
    for b in bars:
        eng.step(st.update(b), in_position=False)
    tiny = [s for s in eng.observed if s.risk_per_share < 5 * p.tick]
    assert tiny, "expected a sub-threshold stop in this construction"
    assert all(s.gates["risk_structural"] is False for s in tiny)


# ---------------------------------------------------------------- halts ---
def test_halt_band_tiers():
    assert halt_band_width(0.50, 0.60) == 0.15
    assert abs(halt_band_width(2.00, 2.50) - 0.50) < 1e-9
    assert abs(halt_band_width(6.00, 7.00) - 0.70) < 1e-9
    assert halt_band_width(None, 5.0) is None


def test_unknown_halt_band_fails_closed_inside_rth():
    """ross-fp-v4.pine finding 9: an unknown band inside RTH must VETO."""
    seq = ramp(35, 5.00, 0.001, 8000) + _push(5.05, 5.34) + _dip(5.34, 5.24)
    bars = mk(dt.date(2026, 8, 3), dt.time(9, 30), seq)
    st = SessionState("X", dt.date(2026, 8, 3), prev_close=None)   # no prev close
    eng = SetupEngine("X", dt.date(2026, 8, 3), P, V_OBS)
    for b in bars:
        eng.step(st.update(b), in_position=False)
    assert eng.observed
    assert all(s.gates["halt_band"] is False for s in eng.observed)
