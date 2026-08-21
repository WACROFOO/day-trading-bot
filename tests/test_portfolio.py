"""Offline tests for the portfolio-level simulation (§7 sizing, §8 limits)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paper_trading import portfolio, replay  # noqa: E402

TZ = "America/New_York"


def bars_for(path, session="2026-08-20", start="09:35"):
    px = np.asarray(path, dtype=float)
    idx = pd.date_range(f"{session} {start}", periods=len(px), freq="1min", tz=TZ)
    return pd.DataFrame({"Open": px, "High": px + 0.02, "Low": px - 0.02,
                         "Close": px, "Volume": 10_000.0}, index=idx)


def take_row(session, symbol, bars, cursor, entry, stop, target, price=None):
    return {
        "session": session, "symbol": symbol, "cursor": cursor,
        "timestamp": bars.index[cursor], "verdict": "TAKE", "reason": "test",
        "price": price if price is not None else entry, "entry": entry,
        "stop": stop, "target": target, "target_source": "hod_retest",
        "risk_per_share": entry - stop,
        "reward_risk": (target - entry) / (entry - stop),
        "shares": 0, "confluence_count": 2, "support_reasons": "test",
        "outcome_resolved": False, "outcome_r_multiple": float("nan"),
    }


def winner_session(session="2026-08-20", symbol="AAA"):
    """Entry at 5.00, stop 4.90, target 5.20 — price runs straight up."""
    bars = bars_for([5.00, 5.10, 5.25, 5.40, 5.55, 5.70], session)
    row = take_row(session, symbol, bars, 0, 5.00, 4.90, 5.20)
    return bars, row


def loser_session(session="2026-08-20", symbol="BBB"):
    """Entry at 5.00, stop 4.90 — price falls straight through it."""
    bars = bars_for([5.00, 4.95, 4.85, 4.75, 4.60], session)
    row = take_row(session, symbol, bars, 0, 5.00, 4.90, 5.20)
    return bars, row


def build(rows_and_bars):
    logs, keys = [], {}
    for bars, row in rows_and_bars:
        logs.append(row)
        keys[(row["symbol"], row["session"])] = bars
    return pd.DataFrame(logs), keys


# ------------------------------------------------------------------ sizing

def test_size_is_capped_by_cash_on_a_tight_stop():
    """$100k risking 2% on a $0.10 stop wants 20,000 shares of a $5 stock —
    $100k of notional. The cash cap is what makes that survivable."""
    bars, row = winner_session()
    logs, keys = build([(bars, row)])
    sim = portfolio.simulate(logs, keys, portfolio.Config(starting_equity=100_000.0))
    t = sim["trades"].iloc[0]
    assert t["shares"] * t["entry"] <= 100_000.0 + 1e-6


def test_sizing_uses_live_equity_not_the_starting_balance():
    """Equity compounds: the second trade must size off the post-trade number."""
    b1, r1 = winner_session("2026-08-20", "AAA")
    b2, r2 = winner_session("2026-08-21", "AAA")
    logs, keys = build([(b1, r1), (b2, r2)])
    sim = portfolio.simulate(logs, keys, portfolio.Config(starting_equity=100_000.0))
    t = sim["trades"]
    assert len(t) == 2
    assert t.iloc[1]["equity_before"] == pytest.approx(t.iloc[0]["equity_after"])


def test_equity_curve_and_return_are_consistent():
    bars, row = winner_session()
    logs, keys = build([(bars, row)])
    sim = portfolio.simulate(logs, keys, portfolio.Config(starting_equity=100_000.0))
    assert sim["final_equity"] == pytest.approx(
        100_000.0 + sim["trades"]["net_pnl"].sum())
    assert sim["return_pct"] == pytest.approx(
        (sim["final_equity"] - 100_000.0) / 100_000.0 * 100.0)


# ------------------------------------------------------------------ §7 caps

def test_third_trade_of_the_day_is_blocked():
    """§7 max_trades_per_day = 2."""
    rows = []
    for i, sym in enumerate(["AAA", "BBB", "CCC"]):
        bars = bars_for([5.00, 5.10, 5.25, 5.40], "2026-08-20", f"09:4{i}")
        rows.append((bars, take_row("2026-08-20", sym, bars, 0, 5.00, 4.90, 5.20)))
    logs, keys = build(rows)
    cfg = portfolio.Config(starting_equity=100_000.0, one_position_at_a_time=False)
    sim = portfolio.simulate(logs, keys, cfg)
    assert len(sim["trades"]) == 2
    assert portfolio.BLOCK_MAX_TRADES in set(sim["blocked"]["reason"])


def test_overlapping_signal_is_blocked_while_a_position_is_open():
    b1 = bars_for([5.00, 5.10, 5.25, 5.40, 5.55], "2026-08-20", "09:35")
    b2 = bars_for([5.00, 5.10, 5.25, 5.40, 5.55], "2026-08-20", "09:36")
    rows = [(b1, take_row("2026-08-20", "AAA", b1, 0, 5.00, 4.90, 5.20)),
            (b2, take_row("2026-08-20", "BBB", b2, 0, 5.00, 4.90, 5.20))]
    logs, keys = build(rows)
    sim = portfolio.simulate(logs, keys, portfolio.Config(one_position_at_a_time=True))
    assert portfolio.BLOCK_POSITION_OPEN in set(sim["blocked"]["reason"])


def test_blocked_signals_carry_their_opportunity_cost():
    """A list of missed trades with no P&L attached is not actionable."""
    rows = []
    for i, sym in enumerate(["AAA", "BBB", "CCC"]):
        bars = bars_for([5.00, 5.10, 5.25, 5.40], "2026-08-20", f"09:4{i}")
        rows.append((bars, take_row("2026-08-20", sym, bars, 0, 5.00, 4.90, 5.20)))
    logs, keys = build(rows)
    cfg = portfolio.Config(one_position_at_a_time=False)
    sim = portfolio.simulate(logs, keys, cfg)
    blocked = sim["blocked"]
    assert len(blocked) >= 1
    assert np.isfinite(blocked["would_be_r"]).any()


# ------------------------------------------------------------------ §8 limits

def test_consecutive_losses_lock_the_account():
    rows = []
    for i, sym in enumerate(["AAA", "BBB", "CCC", "DDD"]):
        bars = bars_for([5.00, 4.95, 4.85, 4.70], "2026-08-20", f"09:4{i}")
        rows.append((bars, take_row("2026-08-20", sym, bars, 0, 5.00, 4.90, 5.20)))
    logs, keys = build(rows)
    cfg = portfolio.Config(starting_equity=100_000.0, max_trades_per_day=10,
                           one_position_at_a_time=False, consecutive_loss_stop=3,
                           max_daily_loss_pct=99.0, giveback_pct=999.0,
                           green_to_red_stop=False, drawdown_walkaway_pct=99.0)
    sim = portfolio.simulate(logs, keys, cfg)
    assert len(sim["trades"]) == 3
    assert sim["days"].iloc[0]["locked"]
    assert "consecutive losses" in sim["days"].iloc[0]["lock_reason"]


def test_max_daily_loss_locks_the_account():
    bars, row = loser_session()
    logs, keys = build([(bars, row)])
    cfg = portfolio.Config(starting_equity=5_000.0, max_daily_loss_pct=1.0,
                           max_trades_per_day=10)
    sim = portfolio.simulate(logs, keys, cfg)
    assert sim["days"].iloc[0]["locked"]
    assert "max_daily_loss" in sim["days"].iloc[0]["lock_reason"]


def state(start=100_000.0, peak=100_000.0, losses=0):
    return portfolio.DayState(date="2026-08-20", start_equity=start,
                              peak_equity=peak, consecutive_losses=losses)


def test_risk_check_green_to_red():
    """§8: the day was green, then went red — stop, regardless of size."""
    cfg = portfolio.Config(giveback_pct=999.0, max_daily_loss_pct=99.0)
    locked, why = portfolio.risk_check(state(peak=104_000.0), 99_000.0, 104_000.0, cfg)
    assert locked and why == "green_to_red"


def test_risk_check_green_day_stays_open():
    cfg = portfolio.Config()
    locked, _ = portfolio.risk_check(state(peak=101_000.0), 100_900.0, 101_000.0, cfg)
    assert not locked


def test_risk_check_giveback_of_peak_gain():
    """§8: handing back half the day's peak gain stops the day."""
    cfg = portfolio.Config(green_to_red_stop=False, max_daily_loss_pct=99.0)
    locked, why = portfolio.risk_check(state(peak=110_000.0), 104_000.0, 110_000.0, cfg)
    assert locked and "giveback" in why


def test_risk_check_max_daily_loss():
    cfg = portfolio.Config(max_daily_loss_pct=6.0)
    locked, why = portfolio.risk_check(state(), 93_000.0, 100_000.0, cfg)
    assert locked and "max_daily_loss" in why


def test_risk_check_drawdown_walkaway_uses_the_high_water_mark():
    """§8's 20% walkaway is measured from the account HWM, not from today."""
    cfg = portfolio.Config(max_daily_loss_pct=99.0, green_to_red_stop=False,
                           giveback_pct=999.0)
    locked, why = portfolio.risk_check(state(start=80_000.0, peak=80_000.0),
                                       79_000.0, 100_000.0, cfg)
    assert locked and "drawdown" in why


def test_risk_check_clean_day_is_not_locked():
    cfg = portfolio.Config()
    assert not portfolio.risk_check(state(), 100_000.0, 100_000.0, cfg)[0]


def test_signals_after_a_lock_are_recorded_as_blocked_not_dropped():
    """The whole point: a locked-out signal must be visible in the report."""
    rows = []
    for i, sym in enumerate(["AAA", "BBB", "CCC", "DDD"]):
        bars = bars_for([5.00, 4.95, 4.85, 4.70], "2026-08-20", f"09:4{i}")
        rows.append((bars, take_row("2026-08-20", sym, bars, 0, 5.00, 4.90, 5.20)))
    logs, keys = build(rows)
    cfg = portfolio.Config(starting_equity=100_000.0, max_trades_per_day=10,
                           one_position_at_a_time=False, consecutive_loss_stop=2,
                           max_daily_loss_pct=99.0, giveback_pct=999.0,
                           green_to_red_stop=False, drawdown_walkaway_pct=99.0)
    sim = portfolio.simulate(logs, keys, cfg)
    assert portfolio.BLOCK_RISK_GATE in set(sim["blocked"]["reason"])


def test_lock_resets_on_the_next_session():
    """§8 latches for the day, not forever."""
    b1 = bars_for([5.00, 4.95, 4.80, 4.50], "2026-08-20")
    r1 = take_row("2026-08-20", "AAA", b1, 0, 5.00, 4.90, 5.20)
    b2, r2 = winner_session("2026-08-21", "AAA")
    logs, keys = build([(b1, r1), (b2, r2)])
    cfg = portfolio.Config(starting_equity=5_000.0, max_daily_loss_pct=1.0)
    sim = portfolio.simulate(logs, keys, cfg)
    assert sim["days"].iloc[0]["locked"]
    assert len(sim["trades"]) == 2          # day two traded again


def test_empty_log_is_handled():
    sim = portfolio.simulate(pd.DataFrame(), {})
    assert sim["trades"].empty and sim["blocked"].empty


def test_liquidity_cap_prevents_owning_the_whole_tape():
    """§7's risk formula asks a $100k account for ~20,000 shares of a $5
    stock. On a thin sub-20M float that fill does not exist — the sim must
    not report P&L on shares that could never have been bought."""
    thin = bars_for([5.00, 5.10, 5.25, 5.40, 5.55])
    thin["Volume"] = 3_000.0                      # 3k shares a minute
    row = take_row("2026-08-20", "AAA", thin, 0, 5.00, 4.90, 5.20)
    logs, keys = build([(thin, row)])
    sim = portfolio.simulate(logs, keys,
                             portfolio.Config(starting_equity=100_000.0,
                                              max_participation_pct=10.0))
    t = sim["trades"].iloc[0]
    assert t["shares"] <= 300                     # 10% of a 3,000-share minute
    assert t["size_bound_by"] == "liquidity"


def test_deep_liquidity_lets_risk_be_the_binding_cap():
    liquid = bars_for([5.00, 5.10, 5.25, 5.40, 5.55])
    liquid["Volume"] = 5_000_000.0
    row = take_row("2026-08-20", "AAA", liquid, 0, 5.00, 4.90, 5.20)
    logs, keys = build([(liquid, row)])
    sim = portfolio.simulate(logs, keys,
                             portfolio.Config(starting_equity=1_000_000.0))
    assert sim["trades"].iloc[0]["size_bound_by"] == "risk"


def test_sizing_helper_reports_which_cap_bound():
    import numpy as np
    bars = bars_for([5.0] * 30)
    bars["Volume"] = 1_000_000.0
    shares, bound = replay.size_position(100_000.0, 5.00, 0.10, bars)
    assert bound == "risk" and shares == 20_000
    shares, bound = replay.size_position(10_000.0, 5.00, 0.01, bars)
    assert bound == "cash" and shares == 2_000


def test_drawdown_walkaway_persists_across_sessions():
    """§8's 20% walkaway stops the account until a human resets it. If it
    released overnight, the deepest drawdown of the run would trade on."""
    rows = []
    for i, day in enumerate(["2026-08-20", "2026-08-21"]):
        bars = bars_for([5.00, 4.95, 4.85, 4.70], day)
        rows.append((bars, take_row(day, "AAA", bars, 0, 5.00, 4.90, 5.20)))
    logs, keys = build(rows)
    cfg = portfolio.Config(starting_equity=1_000.0, drawdown_walkaway_pct=1.0,
                           max_daily_loss_pct=99.0, giveback_pct=999.0,
                           green_to_red_stop=False, consecutive_loss_stop=99)
    sim = portfolio.simulate(logs, keys, cfg)
    assert sim["days"].iloc[1]["locked"]
    assert "drawdown" in sim["days"].iloc[1]["lock_reason"]


def test_account_walkaway_is_recorded_even_when_a_daily_limit_fires_first():
    """Reviewer scenario. HWM 100,000; the day opens at 85,000 (already 15%
    down) and losses take equity to 79,800 — 6.12% on the day AND 20.2% off
    the high-water mark. The daily-loss rule used to return first, so §8's
    account walkaway was never recorded and released the next morning.

    A 20% account drawdown is always assembled out of days that trip the 6%
    daily limit first, which made the walkaway close to unreachable."""
    day = portfolio.DayState(date="d", start_equity=85_000.0, peak_equity=85_000.0)
    cfg = portfolio.Config()
    assert portfolio.account_walkaway(79_800.0, 100_000.0, cfg) != ""
    locked, reason = portfolio.risk_check(day, 79_800.0, 100_000.0, cfg)
    assert locked and "drawdown" in reason, \
        "the account walkaway must outrank the daily latch, not queue behind it"


def test_daily_limits_still_fire_when_the_account_is_healthy():
    day = portfolio.DayState(date="d", start_equity=100_000.0, peak_equity=100_000.0)
    cfg = portfolio.Config()
    locked, reason = portfolio.risk_check(day, 93_000.0, 100_000.0, cfg)
    assert locked and "max_daily_loss" in reason


def test_walkaway_persists_when_a_daily_rule_fired_on_the_same_trade():
    """End-to-end version: the lock must survive into the next session."""
    rows = []
    for day in ["2026-08-20", "2026-08-21"]:
        bars = bars_for([5.00, 4.95, 4.85, 4.70], day)
        rows.append((bars, take_row(day, "AAA", bars, 0, 5.00, 4.90, 5.20)))
    logs, keys = build(rows)
    cfg = portfolio.Config(starting_equity=1_000.0, drawdown_walkaway_pct=1.0,
                           max_daily_loss_pct=0.5)      # daily rule fires too
    sim = portfolio.simulate(logs, keys, cfg)
    assert sim["days"].iloc[1]["locked"], "walkaway released overnight"
