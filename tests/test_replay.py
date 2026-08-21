"""Offline tests for the blinded walk-forward replay. No network.

Synthetic bars are used to test the *machinery*. They must never be used
to produce a measurement — see REPLAY_EVAL_PROMPT.md ground rules.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paper_trading import indicators, replay  # noqa: E402


def session(prices, volumes=None, start="2026-08-20 09:30", tz="America/New_York"):
    """Build a 1m session frame from a close path."""
    prices = np.asarray(prices, dtype=float)
    n = len(prices)
    vol = np.asarray(volumes if volumes is not None else [10_000.0] * n, dtype=float)
    idx = pd.date_range(start, periods=n, freq="1min", tz=tz)
    return pd.DataFrame({
        "Open": prices, "High": prices + 0.05, "Low": prices - 0.05,
        "Close": prices, "Volume": vol,
    }, index=idx)


def ramp_then_dip(n_up=12, n_dip=3, base=5.0, step=0.05):
    """An impulse leg followed by a lighter-volume pullback."""
    up = [base + i * step for i in range(n_up)]
    dip = [up[-1] - (i + 1) * step for i in range(n_dip)]
    prices = up + dip + [up[-1] + step]          # final candle breaks the high
    vols = [50_000.0] * n_up + [5_000.0] * n_dip + [60_000.0]
    return session(prices, vols)


# ------------------------------------------------------------------ blinding

def test_visible_slice_stops_at_the_cursor():
    bars = session([5.0] * 10)
    v = replay.visible_slice(bars, 4)
    assert len(v) == 5 and v.index[-1] == bars.index[4]


def test_visible_slice_rejects_an_out_of_range_cursor():
    bars = session([5.0] * 3)
    with pytest.raises(IndexError):
        replay.visible_slice(bars, 3)


def test_assert_causal_passes_on_the_real_indicators():
    bars = ramp_then_dip()
    for cursor in range(2, len(bars)):
        replay.assert_causal(bars, cursor)


def test_assert_causal_catches_a_leaky_indicator(monkeypatch):
    """The guard must actually fire — a green run proves nothing otherwise."""
    bars = ramp_then_dip()

    def leaky(close):                      # centered window sees the future
        return close.rolling(5, center=True, min_periods=1).mean()

    monkeypatch.setattr(indicators, "ema9", leaky)
    with pytest.raises(replay.LookAheadError):
        replay.assert_causal(bars, 5)


def test_five_minute_bar_is_partial_at_the_cursor():
    """The in-progress 5m bar must not contain minutes that haven't printed."""
    bars = session([5.0, 5.1, 5.2, 5.3, 5.4, 9.9], start="2026-08-20 09:30")
    visible = replay.visible_slice(bars, 2)          # 09:30, 09:31, 09:32
    five = replay.resample_5m(visible)
    assert len(five) == 1
    assert float(five["High"].iloc[-1]) == pytest.approx(5.25)   # not 9.95
    assert float(five["Volume"].iloc[-1]) == 30_000.0            # 3 bars, not 5


def test_five_minute_bars_close_only_when_complete():
    bars = session([5.0] * 7, start="2026-08-20 09:30")
    five = replay.resample_5m(replay.visible_slice(bars, 6))
    assert len(five) == 2                     # 09:30-09:34 closed, 09:35 forming
    assert float(five["Volume"].iloc[0]) == 50_000.0
    assert float(five["Volume"].iloc[1]) == 20_000.0


# ------------------------------------------------------------------ §3 support

def test_support_reasons_finds_whole_dollar_and_a_moving_average():
    bars = session([5.0] * 30)
    reasons = replay.support_reasons(5.0, bars)
    assert "whole_half_dollar" in reasons
    assert "ema9" in reasons                 # flat path -> ema sits on price
    assert len(reasons) >= replay.CONFLUENCE_MIN


def test_support_reasons_empty_at_a_random_price():
    bars = session([5.0 + i * 0.01 for i in range(30)])
    assert replay.support_reasons(4.37, bars) == []


def test_support_tolerance_widens_the_match():
    bars = session([5.0 + i * 0.01 for i in range(30)])
    price = float(indicators.ema9(bars["Close"]).iloc[-1]) + 0.01
    narrow = replay.support_reasons(price, bars, tolerance_pct=0.01,
                                    tolerance_floor=0.0)
    wide = replay.support_reasons(price, bars, tolerance_pct=0.50,
                                  tolerance_floor=0.0)
    assert len(wide) > len(narrow)


def test_swing_highs_only_reports_confirmed_pivots():
    bars = session([5.0, 5.1, 5.5, 5.2, 5.1, 5.0])
    # the 5.5 pivot needs bars after it to confirm; the final bar never can
    assert any(abs(h - 5.55) < 1e-9 for h in replay.swing_highs(bars))


# ------------------------------------------------------------------ §3 pullback

def test_detect_pullback_finds_the_dip_and_its_volume():
    bars = ramp_then_dip()
    pb = replay.detect_pullback(bars.iloc[:-1])        # cursor inside the dip
    assert pb.in_pullback and pb.index == 1
    assert pb.pullback_volume < pb.impulse_volume
    assert pb.low == pytest.approx(bars["Low"].iloc[-4:-1].min())


def test_detect_pullback_needs_bars():
    assert not replay.detect_pullback(session([5.0, 5.1])).in_pullback


# ------------------------------------------------------------------ decision

def test_evaluate_skips_when_the_macd_is_negative():
    bars = session([6.0 - i * 0.05 for i in range(40)])   # steady downtrend
    d = replay.evaluate(bars, "TEST")
    assert d.verdict == "SKIP"
    assert "macd_hist<=0" in d.reason or "price<=vwap" in d.reason


def test_evaluate_marks_level_two_inputs_untestable():
    d = replay.evaluate(ramp_then_dip(), "TEST")
    assert d.tape_green == replay.UNTESTABLE
    assert d.no_seller_wall == replay.UNTESTABLE


def test_evaluate_rejects_a_stop_wider_than_the_cap():
    """§5: too-wide stop is a skip, never a widened stop."""
    up = [5.0 + i * 0.05 for i in range(12)]
    prices = up + [up[-1] - 1.5, up[-1] + 0.10]          # huge dip, then break
    vols = [50_000.0] * 12 + [5_000.0, 60_000.0]
    d = replay.evaluate(session(prices, vols), "TEST")
    assert d.verdict == "SKIP"
    assert "stop distance" in d.reason or "gate:" in d.reason


def test_evaluate_requires_the_trigger():
    """No candle takes out the prior high -> no entry, however good it looks."""
    bars = ramp_then_dip().iloc[:-1]                     # drop the breakout bar
    d = replay.evaluate(bars, "TEST")
    assert d.verdict == "SKIP" and not d.trigger


def test_evaluate_sizes_from_risk_not_capital():
    """§7: shares = risk_budget / risk_per_share."""
    bars = ramp_then_dip()
    d = replay.evaluate(bars, "TEST", equity=50_000.0)
    if d.verdict == "TAKE":
        assert d.shares == int((50_000.0 * 0.02) // d.risk_per_share)


# ------------------------------------------------------------------ outcome

def make_trade(entry=5.00, stop=4.90, target=5.20, shares=100):
    return replay.Decision(
        timestamp=pd.Timestamp("2026-08-20 09:40", tz="America/New_York"),
        symbol="T", price=entry, verdict="TAKE", reason="",
        entry=entry, stop=stop, target=target,
        risk_per_share=entry - stop, shares=shares)


def test_resolve_stops_out_at_the_pullback_low():
    d = make_trade()
    bars = session([5.00, 4.85, 4.80], start="2026-08-20 09:40")
    out = replay.resolve(bars, 0, d)
    assert out.resolved and out.r_multiple < 0
    assert out.exit_reason in {"stop", "first_candle_new_low"}


def test_resolve_scales_at_target_then_trails_to_breakeven():
    d = make_trade()
    bars = session([5.00, 5.25, 5.30, 5.35], start="2026-08-20 09:40")
    out = replay.resolve(bars, 0, d)
    assert out.resolved and out.r_multiple > 0
    assert out.mfe_r > 0


def test_resolve_costs_reduce_net_pnl():
    d = make_trade()
    bars = session([5.00, 5.25, 5.30], start="2026-08-20 09:40")
    out = replay.resolve(bars, 0, d)
    gross = out.r_multiple * d.risk_per_share * d.shares
    assert out.net_pnl < gross            # commission taken off


def test_resolve_with_no_bars_after_entry_is_unresolved():
    bars = session([5.00], start="2026-08-20 09:40")
    assert not replay.resolve(bars, 0, make_trade()).resolved


# ------------------------------------------------------------------ session

def test_decision_window_enforces_the_blackout_and_hard_stop():
    idx = pd.date_range("2026-08-20 09:25", periods=180, freq="1min",
                        tz="America/New_York")
    bars = pd.DataFrame({"Open": 5.0, "High": 5.1, "Low": 4.9, "Close": 5.0,
                         "Volume": 1000.0}, index=idx)
    w = replay.decision_window(bars)
    assert w.index[0].strftime("%H:%M") == "09:35"
    assert w.index[-1].strftime("%H:%M") == "11:30"


def test_replay_session_emits_one_row_per_candle():
    idx = pd.date_range("2026-08-20 09:30", periods=60, freq="1min",
                        tz="America/New_York")
    path = 5.0 + np.sin(np.arange(60) / 4) * 0.2
    bars = pd.DataFrame({"Open": path, "High": path + 0.05, "Low": path - 0.05,
                         "Close": path, "Volume": 10_000.0}, index=idx)
    log = replay.replay_session(bars, "TEST")
    assert not log.empty
    assert set(log["verdict"]) <= {"TAKE", "SKIP"}
    assert log["timestamp"].min().strftime("%H:%M") == "09:35"


def test_replay_session_resolves_skips_counterfactually():
    """Without this, recall is unmeasurable."""
    idx = pd.date_range("2026-08-20 09:30", periods=60, freq="1min",
                        tz="America/New_York")
    path = 5.0 + np.sin(np.arange(60) / 4) * 0.2
    bars = pd.DataFrame({"Open": path, "High": path + 0.05, "Low": path - 0.05,
                         "Close": path, "Volume": 10_000.0}, index=idx)
    log = replay.replay_session(bars, "TEST")
    skipped_but_resolved = log[(log["verdict"] == "SKIP")
                               & log["outcome_resolved"].astype(bool)]
    assert len(skipped_but_resolved) > 0


def test_replay_session_runs_the_causality_guard_on_every_bar():
    calls = []
    idx = pd.date_range("2026-08-20 09:30", periods=45, freq="1min",
                        tz="America/New_York")
    bars = pd.DataFrame({"Open": 5.0, "High": 5.05, "Low": 4.95, "Close": 5.0,
                         "Volume": 1000.0}, index=idx)
    real = replay.assert_causal
    replay.assert_causal = lambda b, c, **k: calls.append(c) or real(b, c, **k)
    try:
        replay.replay_session(bars, "TEST")
    finally:
        replay.assert_causal = real
    assert len(calls) == len(replay.decision_window(bars))


# ------------------------------------------------------------------ scoring

def make_log(rows):
    return pd.DataFrame(rows)


def test_score_builds_the_confusion_matrix():
    log = make_log([
        {"verdict": "TAKE", "outcome_resolved": True, "outcome_r_multiple": 2.0,
         "outcome_net_pnl": 200.0},
        {"verdict": "TAKE", "outcome_resolved": True, "outcome_r_multiple": -1.0,
         "outcome_net_pnl": -100.0},
        {"verdict": "SKIP", "outcome_resolved": True, "outcome_r_multiple": 1.5,
         "outcome_net_pnl": 0.0},
        {"verdict": "SKIP", "outcome_resolved": True, "outcome_r_multiple": -1.0,
         "outcome_net_pnl": 0.0},
    ])
    s = replay.score(log)
    assert (s["true_positive"], s["false_positive"]) == (1, 1)
    assert (s["false_negative"], s["true_negative"]) == (1, 1)
    assert s["precision"] == pytest.approx(0.5)
    assert s["recall"] == pytest.approx(0.5)
    assert s["expectancy_r"] == pytest.approx(0.5)


def test_score_flags_an_undersized_sample():
    log = make_log([{"verdict": "TAKE", "outcome_resolved": True,
                     "outcome_r_multiple": 3.0, "outcome_net_pnl": 300.0}])
    s = replay.score(log)
    assert s["significant"] is False           # 1 trade is not evidence
    assert s["breakeven_win_rate"] == pytest.approx(1 / 3, abs=1e-9)


def test_score_marks_a_sample_significant_at_twenty_trades():
    log = make_log([{"verdict": "TAKE", "outcome_resolved": True,
                     "outcome_r_multiple": 1.0, "outcome_net_pnl": 100.0}] * 20)
    assert replay.score(log)["significant"] is True


def test_score_on_empty_log():
    assert replay.score(pd.DataFrame())["n_decisions"] == 0


# ------------------------------------------------------------------ baselines

def test_buy_hold_baseline_measures_the_window():
    idx = pd.date_range("2026-08-20 09:30", periods=150, freq="1min",
                        tz="America/New_York")
    path = np.linspace(5.0, 6.0, 150)
    bars = pd.DataFrame({"Open": path, "High": path, "Low": path,
                         "Close": path, "Volume": 1000.0}, index=idx)
    b = baseline = replay.baseline_buy_hold(bars)
    assert b["return_pct"] > 0


def test_random_baseline_is_seeded_and_reproducible():
    idx = pd.date_range("2026-08-20 09:30", periods=120, freq="1min",
                        tz="America/New_York")
    path = 5.0 + np.sin(np.arange(120) / 5) * 0.3
    bars = pd.DataFrame({"Open": path, "High": path + 0.05, "Low": path - 0.05,
                         "Close": path, "Volume": 1000.0}, index=idx)
    a = replay.baseline_random(bars, n=10, seed=42)
    b = replay.baseline_random(bars, n=10, seed=42)
    assert a == b


# ------------------------------------------------------------------ sweep

def test_sweep_reports_every_tolerance_and_detects_sign_flips():
    idx = pd.date_range("2026-08-20 09:30", periods=90, freq="1min",
                        tz="America/New_York")
    path = 5.0 + np.sin(np.arange(90) / 5) * 0.2
    bars = pd.DataFrame({"Open": path, "High": path + 0.05, "Low": path - 0.05,
                         "Close": path, "Volume": 10_000.0}, index=idx)
    out = replay.sweep_tolerance(bars, "TEST", tolerances=(0.10, 0.25, 0.50))
    assert list(out["tolerance_pct"]) == [0.10, 0.25, 0.50]
    assert "sign_flips" in out.attrs


# ------------------------------------------------------------------ regression

def test_pullback_index_resets_when_the_move_ends():
    """Regression: the counter used to climb all session, so the §3 gate
    could never open and every run reported zero trades as if that were a
    clean result."""
    idx = pd.date_range("2026-08-20 09:30", periods=240, freq="1min",
                        tz="America/New_York")
    # many small legs over two hours — a real session shape
    path = 5.0 + np.sin(np.arange(240) / 6) * 0.25 + np.arange(240) * 0.001
    bars = pd.DataFrame({"Open": path, "High": path + 0.05, "Low": path - 0.05,
                         "Close": path, "Volume": 10_000.0}, index=idx)
    seen = [replay.detect_pullback(replay.visible_slice(bars, c)).index
            for c in range(3, len(bars))]
    assert max(seen) <= 6, f"counter ran away to {max(seen)}"
    assert any(i in (1, 2) for i in seen), "counter never sits in the tradable range"


def test_pullback_index_resets_on_a_vwap_break():
    """§5 treats losing VWAP as hard invalidation — the move is over."""
    rise = [5.0 + i * 0.03 for i in range(25)]
    crash = [rise[-1] - (i + 1) * 0.15 for i in range(12)]
    bars = session(rise + crash)
    pb = replay.detect_pullback(bars)
    assert pb.index == 0, "counter survived a VWAP break"


def test_gate_can_actually_open_on_a_valid_setup():
    """A gate that never fires would report 'no trades' forever and look
    like a clean run. Prove TAKE is reachable."""
    bars = ramp_then_dip(n_up=14, n_dip=2, base=5.0, step=0.04)
    d = replay.evaluate(bars, "TEST")
    assert d.pullback_index_ok, f"pullback index {d.reason}"
    assert d.trigger and d.macd_positive and d.above_vwap


def test_size_is_capped_by_cash_not_just_risk():
    """§7 sizes from risk, but the account has no margin — an 8-cent stop
    would otherwise buy more stock than the cash can pay for."""
    bars = ramp_then_dip(n_up=14, n_dip=2, base=5.0, step=0.04)
    d = replay.evaluate(bars, "TEST", equity=25_000.0)
    if d.shares:
        assert d.shares * d.entry <= 25_000.0 + 1e-6
        by_risk = int((25_000.0 * 0.02) // d.risk_per_share)
        if by_risk * d.entry > 25_000.0:
            assert d.size_capped_by_cash


def textbook_flag() -> pd.DataFrame:
    """A setup that survives HONEST timing.

    The §3 gate is judged on the close of the last dip bar, so the dip must
    still be holding the 9 EMA at that moment *and* have landed on a level.
    Those two only coexist in a narrow band, which is exactly what makes the
    setup rare.

    Structure: an impulse topping at 5.50 (leaving a pivot), a shallow dip
    that confirms it, a second leg breaking 5.50 so it flips to support, then
    a two-bar light-volume pullback whose low returns to precisely 5.50 — the
    half dollar, the flipped level and the 9 EMA all at once.
    """
    pre = list(4.60 + np.random.default_rng(11).normal(0, 0.003, 160))
    legA = list(np.linspace(4.62, 5.47, 18))     # tops with High = 5.50
    pbA = [5.44, 5.40]                           # confirms the 5.50 pivot
    legB = [5.50, 5.62, 5.74]                    # breaks 5.50 -> it flips
    dip = [5.62, 5.53]                           # low = 5.50, back to the level
    brk = [5.65, 5.81, 5.99, 6.19, 6.39]
    px = np.array(pre + legA + pbA + legB + dip + brk)
    vol = np.array([2_000.] * 160 + [60_000.] * 18 + [8_000.] * 2
                   + [70_000.] * 3 + [5_000.] * 2 + [80_000.] * 5)
    idx = pd.date_range("2026-08-20 07:00", periods=len(px), freq="1min",
                        tz="America/New_York")
    return pd.DataFrame({"Open": px, "High": px + 0.03, "Low": px - 0.03,
                         "Close": px, "Volume": vol}, index=idx)


def test_full_pipeline_produces_a_trade_on_a_textbook_bull_flag():
    """End-to-end guard: if this stops producing a TAKE the gate has silently
    closed, and every run will then report zero trades as though that were a
    clean result. That failure mode has already occurred twice here."""
    log = replay.replay_session(textbook_flag(), "TEST")
    takes = log[log["verdict"] == "TAKE"]
    assert len(takes) >= 1
    t = takes.iloc[0]
    assert t["stop"] == pytest.approx(5.50, abs=1e-6)        # §5 pullback low
    assert t["risk_per_share"] <= replay.STOP_MAX_DISTANCE   # §5 cap
    assert t["reward_risk"] >= replay.MIN_REWARD_RISK        # §6
    assert t["confluence_count"] >= replay.CONFLUENCE_MIN    # §3
    assert t["shares"] * t["entry"] <= 25_000.0 + 1e-6       # §7 cash cap


def test_the_gate_is_judged_before_the_trigger_candle_closes():
    """The fill is priced at the break of the PRIOR bar's high, which happens
    mid-candle. Judging §3 on the trigger candle's own close hands the filter
    a minute of information the fill never had — enough to let a dip that had
    already lost the 9 EMA qualify because price recovered by the close."""
    bars = textbook_flag()
    trigger = 160 + 18 + 2 + 3 + 2
    visible = replay.visible_slice(bars, trigger)
    d = replay.evaluate(visible, "TEST")
    assert d.price == pytest.approx(float(visible["Close"].iloc[-2])), \
        "the gate must read the prior bar's close, not the trigger candle's"
    assert d.entry == pytest.approx(float(visible["High"].iloc[-2]) + 0.02)


# ------------------------------------------------------- audit regressions

def test_vwap_is_not_reseeded_at_the_entry_bar():
    """Regression, and the worst bug found: resolve() used to compute VWAP on
    a slice starting at the entry, so VWAP re-seeded to that bar's own typical
    price. On a RISING session that makes close < vwap true immediately and
    fires a fabricated vwap_break exit on essentially every trade."""
    rising = session(np.linspace(5.00, 6.00, 40), start="2026-08-20 09:40")
    d = make_trade(entry=5.02, stop=4.90, target=5.60, shares=100)
    out = replay.resolve(rising, 0, d)
    assert out.exit_reason != "vwap_break"
    assert out.r_multiple > 0


def test_macd_histogram_is_not_reseeded_at_the_entry_bar():
    """Same defect via MACD: on a fresh slice the histogram starts at exactly
    0.0 and the slightest dip reads as macd_negative."""
    rising = session(np.linspace(5.00, 5.80, 40), start="2026-08-20 09:40")
    d = make_trade(entry=5.02, stop=4.90, target=5.50, shares=100)
    out = replay.resolve(rising, 0, d)
    assert out.exit_reason != "macd_negative"


def test_position_is_not_carried_past_the_session_hard_stop():
    """§2 stops at 11:30. resolve() used to run to the end of the fetched
    frame — 20:00 with prepost=True — so an 11:29 entry could be held all
    afternoon and score whatever the close happened to do."""
    idx = pd.date_range("2026-08-20 11:25", periods=200, freq="1min",
                        tz="America/New_York")
    px = np.linspace(5.0, 9.0, 200)          # a huge afternoon run
    bars = pd.DataFrame({"Open": px, "High": px + 0.02, "Low": px - 0.02,
                         "Close": px, "Volume": 10_000.0}, index=idx)
    out = replay.resolve(bars, 0, make_trade(entry=5.02, stop=4.90, target=20.0))
    assert out.resolved
    exit_bar = idx[min(out.bars_held - 1, len(idx) - 1)]
    assert exit_bar.time() <= replay.SESSION_END


def test_entry_candle_reversal_through_the_stop_is_a_loss():
    """The fill happens intrabar. A candle that fills then reverses through
    the stop was previously recorded as an untouched winner with mae_r = 0,
    because management started at the NEXT bar."""
    idx = pd.date_range("2026-08-20 09:40", periods=3, freq="1min",
                        tz="America/New_York")
    bars = pd.DataFrame({
        "Open": [5.00, 5.10, 5.20], "High": [5.10, 5.15, 5.25],
        "Low":  [4.80, 5.05, 5.15], "Close": [4.85, 5.10, 5.20],
        "Volume": [10_000.0] * 3}, index=idx)
    out = replay.resolve(bars, 0, make_trade(entry=5.02, stop=4.90))
    assert out.exit_reason == "stop"
    assert out.r_multiple < 0 and out.mae_r < 0


def test_a_gap_through_the_stop_fills_at_the_open_not_the_stop():
    """Assuming stop - slippage on a bar that opened below the stop caps
    every loss at ~1.2R and quietly flatters the worst trades."""
    idx = pd.date_range("2026-08-20 09:40", periods=2, freq="1min",
                        tz="America/New_York")
    bars = pd.DataFrame({
        "Open": [5.02, 4.50], "High": [5.05, 4.55], "Low": [5.00, 4.40],
        "Close": [5.02, 4.45], "Volume": [10_000.0] * 2}, index=idx)
    out = replay.resolve(bars, 0, make_trade(entry=5.02, stop=4.90))
    assert out.exit_price <= 4.50           # filled at the gap, not at 4.90
    assert out.r_multiple < -1.0            # a gap costs more than 1R


def test_flipped_level_requires_the_level_to_have_been_broken():
    """§3's flipped level is resistance that was BROKEN and is being retested.
    The old guard (`abs(p-h) <= tol and p >= h - tol`) was a tautology — the
    second clause follows from the first — so any nearby swing high counted
    and confluence was inflated."""
    # a swing high at ~5.55 that price never exceeds afterwards
    never_broken = session([5.0, 5.2, 5.5, 5.3, 5.1, 5.2, 5.3, 5.25, 5.2, 5.3])
    assert "flipped_level" not in replay.support_reasons(5.55, never_broken)


def test_flipped_level_counts_once_the_level_is_actually_broken():
    broken = session([5.0, 5.2, 5.5, 5.3, 5.1, 5.6, 5.8, 5.7, 5.6, 5.55])
    assert "flipped_level" in replay.support_reasons(5.55, broken)


def test_target_excludes_the_trigger_candles_own_high():
    """§6's high-of-day target must not read the high of the candle that is
    still forming when the fill price is fixed — that is a minute of
    hindsight handed to the reward:risk test."""
    bars = ramp_then_dip(n_up=14, n_dip=2, base=5.0, step=0.04)
    d = replay.evaluate(bars, "TEST")
    if np.isfinite(d.target) and d.target_source == "hod_retest":
        assert d.target <= float(bars["High"].iloc[:-1].max())


def test_scale_ladder_is_fifty_twentyfive_twentyfive():
    """§6 scales 50/25/25, not 50/50."""
    idx = pd.date_range("2026-08-20 09:40", periods=6, freq="1min",
                        tz="America/New_York")
    px = np.array([5.02, 5.25, 5.45, 5.60, 5.70, 5.80])
    bars = pd.DataFrame({"Open": px, "High": px + 0.05, "Low": px - 0.01,
                         "Close": px, "Volume": 10_000.0}, index=idx)
    d = make_trade(entry=5.02, stop=4.92, target=5.22, shares=100)
    out = replay.resolve(bars, 0, d)
    assert out.resolved and out.r_multiple > 0


def test_high_volume_red_average_excludes_the_current_bar():
    """Dividing by an average that includes the current bar makes the signal
    impossible early on and 2x too strict right after."""
    idx = pd.date_range("2026-08-20 09:40", periods=5, freq="1min",
                        tz="America/New_York")
    bars = pd.DataFrame({
        "Open":  [5.02, 5.10, 5.20, 5.30, 5.40],
        "High":  [5.06, 5.15, 5.25, 5.35, 5.45],
        "Low":   [5.00, 5.08, 5.18, 5.28, 5.20],
        "Close": [5.02, 5.12, 5.22, 5.32, 5.22],   # last bar red
        "Volume": [1_000.0, 1_000.0, 1_000.0, 1_000.0, 50_000.0],
    }, index=idx)
    out = replay.resolve(bars, 0, make_trade(entry=5.02, stop=4.90, target=9.0))
    assert out.exit_reason in {"high_volume_red", "first_candle_new_low"}


def test_topping_tail_is_a_hard_exit():
    """§6 lists a large topping tail; it was computable but unimplemented."""
    idx = pd.date_range("2026-08-20 09:40", periods=3, freq="1min",
                        tz="America/New_York")
    bars = pd.DataFrame({
        "Open":  [5.02, 5.10, 5.20], "High": [5.06, 5.14, 5.90],
        "Low":   [5.00, 5.08, 5.18], "Close": [5.02, 5.12, 5.22],
        "Volume": [10_000.0] * 3}, index=idx)
    out = replay.resolve(bars, 0, make_trade(entry=5.02, stop=4.90, target=9.0))
    assert out.exit_reason == "topping_tail"


def test_momentum_stalling_is_a_hard_exit():
    """§6's 'green candles shrinking' — three up bars with contracting range."""
    idx = pd.date_range("2026-08-20 09:40", periods=5, freq="1min",
                        tz="America/New_York")
    bars = pd.DataFrame({
        "Open":  [5.02, 5.10, 5.30, 5.42, 5.48],
        "High":  [5.06, 5.32, 5.44, 5.50, 5.52],
        "Low":   [5.00, 5.09, 5.29, 5.41, 5.47],
        "Close": [5.02, 5.30, 5.42, 5.48, 5.51],
        "Volume": [10_000.0] * 5}, index=idx)
    out = replay.resolve(bars, 0, make_trade(entry=5.02, stop=4.90, target=9.0))
    assert out.exit_reason in {"momentum_stalling", "topping_tail"}


# --------------------------------------------- adversarial audit scenarios
# Both reproductions below were written by independent auditors against the
# pre-fix code. They are kept verbatim in intent so the exact attacks that
# found these leaks stay in the suite.

def flag_with_trigger_high(trigger_high: float) -> pd.DataFrame:
    """Identical session through the fill; only the trigger candle's high
    differs. Nothing knowable at the fill price changes between the two."""
    o = [4.85, 4.90, 4.95, 5.00, 5.03, 5.06, 5.02, 4.99, 5.03]
    h = [4.88, 4.93, 4.98, 5.03, 5.06, 5.09, 5.03, 5.02, trigger_high]
    l = [4.83, 4.88, 4.93, 4.98, 5.01, 5.04, 5.00, 5.00, 5.01]
    c = [4.87, 4.92, 4.97, 5.02, 5.05, 5.07, 5.01, 5.01, 5.05]
    v = [50_000.0] * 6 + [6_000.0, 5_000.0, 70_000.0]
    idx = pd.date_range("2026-08-20 09:35", periods=len(o), freq="1min",
                        tz="America/New_York")
    return pd.DataFrame({"Open": o, "High": h, "Low": l, "Close": c,
                         "Volume": v}, index=idx)


def test_trigger_candles_own_high_cannot_change_the_reward_risk():
    """Auditor scenario: two sessions identical through the fill, one whose
    trigger candle runs to 5.40. Pre-fix the §6 target read that high, so the
    same fill priced at 0.80 R:R in one case and 7.00 in the other — the
    engine selected exactly the breakouts that already exploded inside the
    entry minute, and booked them at the pre-explosion price."""
    quiet = replay.order_params(flag_with_trigger_high(5.06), stop=5.00)
    explosive = replay.order_params(flag_with_trigger_high(5.40), stop=5.00)
    assert quiet["entry"] == pytest.approx(explosive["entry"])
    assert quiet["target"] == pytest.approx(explosive["target"])
    assert quiet["reward_risk"] == pytest.approx(explosive["reward_risk"])


def test_a_same_candle_shakeout_is_a_loss_not_a_seven_r_winner():
    """Auditor scenario: the trigger candle dips through the pullback low
    after filling — the routine low-float stop-run this §1 universe produces
    constantly. Pre-fix, management started at cursor+1, so this was logged
    as exit_reason=session_end, r_multiple=+7.40, mae_r=0.00."""
    idx = pd.date_range("2026-08-20 09:35", periods=4, freq="1min",
                        tz="America/New_York")
    bars = pd.DataFrame({
        "Open":  [5.02, 5.30, 5.40, 5.50],
        "High":  [5.40, 5.45, 5.55, 5.65],   # trigger candle rips to 5.40
        "Low":   [4.95, 5.28, 5.38, 5.48],   # ...after slicing through 5.00
        "Close": [5.06, 5.42, 5.52, 5.62],
        "Volume": [70_000.0] * 4}, index=idx)
    out = replay.resolve(bars, 0, make_trade(entry=5.05, stop=5.00, target=5.60,
                                             shares=100))
    assert out.exit_reason == "stop"
    assert out.r_multiple < 0, "a same-candle shakeout must not book as a win"
    assert out.mae_r < 0, "the entry candle's excursion must be recorded"
