"""Daily risk-rule checks from the strategy spec (PARAMETERS.md §8).

Pure functions: given the day's P&L path and per-trade results, return
warnings/violations. A "violation" means the strategy says stop trading.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MAX_DAILY_LOSS_PCT = 6.0
GIVEBACK_PCT = 50.0
CONSECUTIVE_LOSS_STOP = 3
MIN_REWARD_RISK = 2.0


@dataclass
class RuleStatus:
    name: str
    ok: bool
    detail: str


@dataclass
class RiskReport:
    rules: list[RuleStatus] = field(default_factory=list)

    @property
    def violations(self) -> list[RuleStatus]:
        return [r for r in self.rules if not r.ok]

    @property
    def should_stop(self) -> bool:
        return bool(self.violations)


def check_max_daily_loss(day_pnl: float, equity: float,
                         max_pct: float = MAX_DAILY_LOSS_PCT) -> RuleStatus:
    """Stop if the day is down more than max_pct of the account."""
    limit = equity * max_pct / 100.0
    ok = day_pnl > -limit
    return RuleStatus(
        f"Max daily loss {max_pct:.0f}%", ok,
        f"day P&L ${day_pnl:,.2f} vs limit -${limit:,.2f}",
    )


def check_giveback(day_pnl: float, day_peak_pnl: float,
                   giveback_pct: float = GIVEBACK_PCT) -> RuleStatus:
    """Stop if down giveback_pct (50%) from the day's peak gain."""
    if day_peak_pnl <= 0:
        return RuleStatus("Giveback 50% of peak", True, "no peak gain yet")
    floor = day_peak_pnl * (1.0 - giveback_pct / 100.0)
    ok = day_pnl >= floor
    return RuleStatus(
        "Giveback 50% of peak", ok,
        f"P&L ${day_pnl:,.2f} vs floor ${floor:,.2f} (peak ${day_peak_pnl:,.2f})",
    )


def check_green_to_red(day_pnl: float, was_green: bool) -> RuleStatus:
    """Stop if the day was green and has now turned negative."""
    ok = not (was_green and day_pnl < 0)
    return RuleStatus(
        "Green-to-red stop", ok,
        f"day P&L ${day_pnl:,.2f}" + (" (was green)" if was_green else ""),
    )


def check_consecutive_losses(round_trips: list[float],
                             max_consec: int = CONSECUTIVE_LOSS_STOP) -> RuleStatus:
    """Stop after max_consec losing round-trips in a row."""
    streak = 0
    for pnl in reversed(round_trips):
        if pnl < 0:
            streak += 1
        else:
            break
    ok = streak < max_consec
    return RuleStatus(
        f"{max_consec} consecutive losses", ok,
        f"current losing streak: {streak}",
    )


def reward_risk_ratio(entry: float, stop: float, target: float) -> float:
    """(target - entry) / (entry - stop)."""
    risk = entry - stop
    if risk <= 0:
        raise ValueError("stop must be below entry")
    return (target - entry) / risk


def check_reward_risk(entry: float, stop: float, target: float,
                      min_rr: float = MIN_REWARD_RISK) -> RuleStatus:
    """Flag if reward:risk is below 2.0."""
    rr = reward_risk_ratio(entry, stop, target)
    ok = rr >= min_rr
    return RuleStatus(f"Reward:risk >= {min_rr:.1f}", ok, f"R:R = {rr:.2f}")


def daily_report(day_pnl: float, day_peak_pnl: float, equity: float,
                 round_trips: list[float]) -> RiskReport:
    """All §8 daily rules in one report."""
    was_green = day_peak_pnl > 0
    return RiskReport(rules=[
        check_max_daily_loss(day_pnl, equity),
        check_giveback(day_pnl, day_peak_pnl),
        check_green_to_red(day_pnl, was_green),
        check_consecutive_losses(round_trips),
    ])
