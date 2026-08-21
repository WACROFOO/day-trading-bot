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
    narrow = replay.support_reasons(price, bars, tolerance_pct=0.01)
    wide = replay.support_reasons(price, bars, tolerance_pct=0.50)
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

def test_resolve_stops_out_at_the_pullback_low():
    d = replay.Decision(timestamp=pd.Timestamp("2026-08-20 09:40", tz="America/New_York"),
                        symbol="T", price=5.0, verdict="TAKE", reason="",
                        entry=5.00, stop=4.90, target=5.20, risk_per_share=0.10,
                        shares=100)
    future = session([4.85, 4.80], start="2026-08-20 09:41")
    out = replay.resolve(future, d)
    assert out.resolved and out.r_multiple < 0
    assert out.exit_reason in {"stop", "first_candle_new_low"}


def test_resolve_scales_at_target_then_trails_to_breakeven():
    d = replay.Decision(timestamp=pd.Timestamp("2026-08-20 09:40", tz="America/New_York"),
                        symbol="T", price=5.0, verdict="TAKE", reason="",
                        entry=5.00, stop=4.90, target=5.20, risk_per_share=0.10,
                        shares=100)
    future = session([5.25, 5.30, 5.35], start="2026-08-20 09:41")
    out = replay.resolve(future, d)
    assert out.resolved and out.r_multiple > 0
    assert out.mfe_r > 0


def test_resolve_costs_reduce_net_pnl():
    d = replay.Decision(timestamp=pd.Timestamp("2026-08-20 09:40", tz="America/New_York"),
                        symbol="T", price=5.0, verdict="TAKE", reason="",
                        entry=5.00, stop=4.90, target=5.20, risk_per_share=0.10,
                        shares=100)
    future = session([5.25, 5.30], start="2026-08-20 09:41")
    out = replay.resolve(future, d)
    gross = out.r_multiple * d.risk_per_share * d.shares
    assert out.net_pnl < gross            # commission taken off

def test_resolve_on_empty_future_is_unresolved():
    d = replay.Decision(timestamp=pd.Timestamp("2026-08-20 09:40", tz="America/New_York"),
                        symbol="T", price=5.0, verdict="TAKE", reason="",
                        entry=5.0, stop=4.9, target=5.2, risk_per_share=0.1, shares=100)
    assert not replay.resolve(session([]).iloc[:0], d).resolved


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


def test_full_pipeline_produces_a_trade_on_a_textbook_bull_flag():
    """End-to-end guard: impulse -> 2-candle light-volume dip onto a whole
    dollar -> break of the prior high. If this ever stops producing a TAKE,
    the gate has silently closed and every run will report zero trades as
    though that were a clean result."""
    pre = list(4.45 + np.random.default_rng(7).normal(0, 0.004, 150))
    ramp = list(np.linspace(4.50, 5.30, 20))
    dip = [5.15, 5.03]                       # low lands on $5.00
    brk = [5.20, 5.32, 5.46, 5.60, 5.72]
    px = np.array(pre + ramp + dip + brk)
    vol = np.array([2_000.] * 150 + [60_000.] * 20 + [7_000., 5_000.] + [80_000.] * 5)
    idx = pd.date_range("2026-08-20 07:00", periods=len(px), freq="1min",
                        tz="America/New_York")
    bars = pd.DataFrame({"Open": px, "High": px + 0.03, "Low": px - 0.03,
                         "Close": px, "Volume": vol}, index=idx)

    log = replay.replay_session(bars, "TEST")
    takes = log[log["verdict"] == "TAKE"]
    assert len(takes) >= 1
    t = takes.iloc[0]
    assert t["stop"] == pytest.approx(5.00, abs=1e-6)        # §5 pullback low
    assert t["risk_per_share"] <= replay.STOP_MAX_DISTANCE   # §5 cap
    assert t["reward_risk"] >= replay.MIN_REWARD_RISK        # §6
    assert t["confluence_count"] >= replay.CONFLUENCE_MIN    # §3
    assert t["shares"] * t["entry"] <= 25_000.0 + 1e-6       # §7 cash cap
