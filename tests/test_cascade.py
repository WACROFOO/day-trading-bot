"""The cascade must kill where FILTERS.md kills, and never arm a killed name.

Every test here corresponds to a line in `knowledge-base/strategies/FILTERS.md`
Layer 1, or to a defect actually observed on the desk.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from momentum_platform.cascade import (  # noqa: E402
    FLOAT_MAX, GateState, Inputs, Verdict, evaluate,
)


def good(**over) -> Inputs:
    """A name that passes every Layer 1 gate; override one field per test."""
    base = dict(
        symbol="TEST", last=6.00, prev_close=4.00, change_pct=50.0,
        session_high=6.20, float_shares=4_000_000, float_verified=True,
        catalyst_today=True, is_fund_or_etf=False, tick_size=0.01,
        above_vwap=True, above_ema9=True, macd_positive_and_above_signal=True,
        session_volume=3_000_000, rvol=8.0, in_session_window=True,
    )
    base.update(over)
    return Inputs(**base)


def gate(res, gid):
    return next(g for g in res.gates if g.id == gid)


# ---------------------------------------------------------------- the point
def test_a_clean_name_reaches_review():
    r = evaluate(good())
    assert r.verdict is Verdict.REVIEW
    assert r.killed_by is None and r.plan_allowed


def test_price_below_band_kills_and_forbids_a_plan():
    """THE regression. IMRN, 2026-09-04: last $1.69 against a $2-20 band, and
    the desk still rendered `Entry 1.75 ARMED · Stop 1.71`. A killed name gets
    no plan — that is the whole reason this module exists."""
    r = evaluate(good(last=1.69))
    assert r.verdict is Verdict.REJECT
    assert r.killed_by == "price"
    assert r.plan_allowed is False


def test_price_above_band_kills():
    assert evaluate(good(last=32.0)).killed_by == "price"


def test_penny_theme_softens_the_floor_but_does_not_remove_it():
    """FILTERS.md: under a penny theme "the floor moves to roughly $1.50".

    session_high moves with the price here on purpose — leaving the default
    $6.20 high against a $1.66 last makes the name 73% off its high, and the
    FADE gate would kill it before price was ever reached. The first draft of
    this test did exactly that and looked like a price-gate failure.
    """
    assert evaluate(good(last=1.66, session_high=1.70,
                         penny_theme=True)).killed_by is None
    assert evaluate(good(last=1.20, session_high=1.25,
                         penny_theme=True)).killed_by == "price"
    assert evaluate(good(last=1.66, session_high=1.70)).killed_by == "price"


# ------------------------------------------------------------------- float
def test_float_over_cap_kills():
    r = evaluate(good(float_shares=45_000_000, float_verified=True))
    assert r.killed_by == "float"
    assert gate(r, "float").state is GateState.FAIL


def test_over_cap_shares_outstanding_is_manual_not_unknown_and_still_kills():
    """IMRN showed 234.0M SO rendered as a quiet UNKNOWN, and the cascade
    walked straight past it. Shares outstanding is an UPPER BOUND: under the
    cap it proves float is under; over the cap it proves nothing, which is a
    question for a human — and it must stop the cascade either way."""
    r = evaluate(good(float_shares=234_000_000,
                      float_is_shares_outstanding=True, float_verified=False))
    assert gate(r, "float").state is GateState.MANUAL_CONFIRMATION_REQUIRED
    assert r.killed_by == "float" and r.plan_allowed is False


def test_under_cap_shares_outstanding_bound_passes():
    """Under the cap the bound is sufficient: SO >= float always."""
    r = evaluate(good(float_shares=12_000_000,
                      float_is_shares_outstanding=True, float_verified=False))
    assert gate(r, "float").state is GateState.PASS
    assert r.killed_by is None


def test_unknown_float_fails_closed():
    r = evaluate(good(float_shares=None))
    assert r.killed_by == "float"
    assert gate(r, "float").state is GateState.UNKNOWN


# --------------------------------------------------------------- catalyst
def test_no_catalyst_and_no_theme_kills():
    assert evaluate(good(catalyst_today=False)).killed_by == "catalyst"


def test_a_live_theme_substitutes_for_the_catalyst():
    """The 2026-08-12 correction: sympathy momentum IS the same-day reason.
    JWEL was rejected on 'no catalyst' for the wrong reading."""
    r = evaluate(good(catalyst_today=False, live_theme=True))
    assert r.killed_by is None
    assert gate(r, "catalyst").value == "live theme"


# ----------------------------------------------------------- still rising
def test_more_than_25_percent_off_the_high_kills():
    r = evaluate(good(last=4.00, session_high=6.00))   # 33% off
    assert r.killed_by == "rising"


def test_exactly_at_the_fade_limit_survives():
    assert evaluate(good(last=4.50, session_high=6.00)).killed_by is None


# ------------------------------------------------------------------ split
def test_split_kills_only_when_the_ratio_is_a_clean_integer():
    """MSGY 2026-08-11 was rejected on this gate without its precondition and
    ran 2.54 -> 5.43. A settled split is a shrunken float, which is the thing
    the method hunts."""
    assert evaluate(good(split_ratio_clean_integer=8.0)).killed_by == "split"
    assert evaluate(good(split_ratio_clean_integer=None)).killed_by is None


# ------------------------------------------------- instrument, tick, buyout
def test_fund_kills_but_unknown_instrument_only_warns():
    assert evaluate(good(is_fund_or_etf=True)).killed_by == "instrument"
    r = evaluate(good(is_fund_or_etf=None))
    assert r.killed_by is None and any("Instrument type unknown" in w
                                       for w in r.warnings)


def test_five_cent_tick_kills():
    assert evaluate(good(tick_size=0.05)).killed_by == "tick"


def test_buyout_kills():
    assert evaluate(good(buyout_announced=True)).killed_by == "buyout"


# ------------------------------------------------------- cascade behaviour
def test_the_cascade_stops_at_the_first_kill():
    """Gates after a kill report NOT_APPLICABLE — visible as stopped, never
    silently absent."""
    r = evaluate(good(last=1.00, float_shares=999_000_000))
    assert r.killed_by == "price"
    assert gate(r, "float").state is GateState.NOT_APPLICABLE


def test_only_one_killed_by_is_reported():
    r = evaluate(good(last=1.00, catalyst_today=False, buyout_announced=True))
    assert r.killed_by == "price"


# ----------------------------------------------------------- layer 2 and 3
def test_chart_gates_do_not_kill_they_only_downgrade():
    """A name failing VWAP is still the right name, just not yet."""
    r = evaluate(good(above_vwap=False))
    assert r.verdict is Verdict.WAIT
    assert r.killed_by is None and r.plan_allowed


def test_unknown_chart_gate_gives_watch():
    assert evaluate(good(above_ema9=None)).verdict is Verdict.WATCH


def test_tape_and_level2_are_rendered_not_omitted():
    r = evaluate(good())
    assert gate(r, "tape").state is GateState.MANUAL_CONFIRMATION_REQUIRED


def test_halt_downgrades_to_wait():
    r = evaluate(good(halted=True))
    assert r.verdict is Verdict.WAIT
    assert any("reopen" in x for x in r.reasons)


def test_outside_the_window_logs_rather_than_reviews():
    assert evaluate(good(in_session_window=False)).verdict is Verdict.LOG


def test_thin_session_volume_warns_but_does_not_kill():
    r = evaluate(good(session_volume=400_000))
    assert r.killed_by is None
    assert any("1M floor" in w for w in r.warnings)


def test_rvol_below_the_trade_floor_warns_and_names_the_dial():
    r = evaluate(good(rvol=1.1))
    assert any("scanner dial" in w for w in r.warnings)


def test_premarket_volume_is_a_ceiling_with_no_floor():
    """Every other volume rule has a floor. This one runs backwards: he
    traded NCTY on 8,000 pre-market shares."""
    assert not evaluate(good(premarket_volume=8_000)).warnings
    assert any("ceiling" in w
               for w in evaluate(good(premarket_volume=4_000_000)).warnings)


# ------------------------------------------------------------------ stale
def test_a_stale_feed_yields_no_verdict_and_no_plan():
    """The screenshot showed `1D BEHIND` and an armed plan in the same frame."""
    r = evaluate(good(feed_stale=True))
    assert r.verdict is Verdict.STALE
    assert r.plan_allowed is False


# -------------------------------------------------------------- vocabulary
def test_pass_is_never_a_verdict():
    """The desk rendered a red banner reading "PASS — reject this candidate"
    over rows whose green PASS meant the opposite. One word, one meaning."""
    assert "PASS" not in {v.value for v in Verdict}
    assert Verdict.REJECT.value == "REJECT"


@pytest.mark.parametrize("bad", [
    dict(last=1.69), dict(float_shares=234e6, float_is_shares_outstanding=True),
    dict(catalyst_today=False), dict(is_fund_or_etf=True),
    dict(buyout_announced=True), dict(tick_size=0.05),
])
def test_no_killed_name_ever_allows_a_plan(bad):
    assert evaluate(good(**bad)).plan_allowed is False
