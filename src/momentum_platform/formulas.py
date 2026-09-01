"""Core clean-room formulas (spec section 9).

These are independent definitions computed from market data. The vendor
normalization used by any commercial scanner is unknown; nothing here claims
to be a proprietary production formula.
"""

from __future__ import annotations

from statistics import median
from typing import Optional, Sequence

from .models import SymbolSnapshot


def pct_change(current: Optional[float], reference: Optional[float]) -> Optional[float]:
    if current is None or reference is None or reference <= 0:
        return None
    return 100.0 * (current / reference - 1.0)


def simple_daily_rvol(volume_today: float, avg_daily_volume: Optional[float]) -> Optional[float]:
    """cumulative volume today / mean full-day volume of prior N sessions.
    Understates early-session pace (partial day vs full days) — labeled as the
    'simple' definition wherever displayed."""
    if not avg_daily_volume or avg_daily_volume <= 0:
        return None
    return volume_today / avg_daily_volume


def rvol_time_of_day(
    cumulative_volume_today: float,
    baseline_cumulative_at_same_minute: Sequence[float],
) -> Optional[float]:
    """cumulative volume through minute t / median of the same-minute cumulative
    volume over prior comparable sessions (recommended N=20)."""
    cleaned = [v for v in baseline_cumulative_at_same_minute if v and v > 0]
    if not cleaned:
        return None
    return cumulative_volume_today / median(cleaned)


def rvol_5m_fallback(current_5m_volume: float, prior_5m_volumes: Sequence[float]) -> Optional[float]:
    """current 5m volume / mean of previous completed 5m bars (fallback when
    same-clock-window history is unavailable)."""
    cleaned = [v for v in prior_5m_volumes if v is not None and v >= 0]
    if not cleaned:
        return None
    mean = sum(cleaned) / len(cleaned)
    if mean <= 0:
        return None
    return current_5m_volume / mean


def spread(bid: Optional[float], ask: Optional[float]) -> tuple[Optional[float], Optional[float]]:
    """Returns (spread_abs, spread_bps)."""
    if bid is None or ask is None or bid <= 0 or ask <= 0 or ask < bid:
        return None, None
    mid = (ask + bid) / 2.0
    abs_spread = ask - bid
    return abs_spread, 10_000.0 * abs_spread / mid


def range_position(last: Optional[float], low: Optional[float], high: Optional[float]) -> Optional[float]:
    if last is None or low is None or high is None:
        return None
    rng = high - low
    if rng <= 0:
        return None
    return min(1.0, max(0.0, (last - low) / rng))


def enrich_snapshot(snap: SymbolSnapshot) -> SymbolSnapshot:
    """Compute all derived metrics on a snapshot in place, returning it."""
    snap.change_from_close_pct = pct_change(snap.last, snap.prev_close)
    snap.change_from_open_pct = pct_change(snap.last, snap.regular_open)
    # Before the regular open, the gap is measured from the latest premarket
    # trade; afterwards from the regular open when available.
    gap_ref = snap.regular_open if snap.regular_open else snap.last
    snap.gap_pct = pct_change(gap_ref, snap.prev_close)
    snap.rvol_daily = simple_daily_rvol(snap.volume_today, snap.avg_daily_volume)
    snap.spread_abs, snap.spread_bps = spread(snap.bid, snap.ask)
    snap.range_position = range_position(snap.last, snap.session_low, snap.session_high)
    if snap.last and snap.session_high and snap.session_high > 0:
        snap.hod_distance_pct = 100.0 * (snap.session_high - snap.last) / snap.session_high
    else:
        snap.hod_distance_pct = None
    return snap


def risk_plan(entry: float, stop: float, reward_multiple: float = 2.0) -> dict:
    """First-pullback planning arithmetic (Confirmed course structure):
    entry above trigger, stop under the complete pullback low, minimum target
    at `reward_multiple` R. Planning visual only — never an order."""
    risk_share = entry - stop
    if risk_share <= 0:
        raise ValueError("entry must be above stop")
    return {
        "entry": entry,
        "stop": stop,
        "risk_share": risk_share,
        "target": entry + reward_multiple * risk_share,
        "reward_multiple": reward_multiple,
    }


def position_size(
    allowed_dollar_risk: float,
    entry: float,
    stop: float,
    slippage_reserve: float = 0.0,
    liquidity_limit_shares: Optional[int] = None,
) -> dict:
    """Prudent sizing (Confirmed course structure). The dollar risk is always
    supplied by the user; this module never invents one."""
    prudent_risk = (entry - stop) + slippage_reserve
    if prudent_risk <= 0:
        raise ValueError("entry must exceed stop plus slippage reserve")
    theoretical = int(allowed_dollar_risk // prudent_risk)
    final = theoretical
    if liquidity_limit_shares is not None:
        final = min(theoretical, liquidity_limit_shares)
    return {
        "prudent_risk_share": prudent_risk,
        "theoretical_shares": theoretical,
        "final_shares": final,
        "planned_loss": final * prudent_risk,
    }
