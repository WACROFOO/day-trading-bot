"""Hard risk gate: evaluates the 5 daily rules and latches violations.

The gate is fully evaluable offline from ledger data (realized P&L, cash,
round trips) — no market data required — which makes it deterministic,
testable, and un-bypassable by a data outage. Callers may pass live
``equity``/``unrealized`` for full mark-to-market evaluation.

Enforcement lives in ``broker.buy`` (veto on BUY only; exits are always
allowed — see plan §8 decision 1). The latch persists in SQLite
(``risk_day.locked``, keyed by ET date), so once tripped it stays tripped
even if P&L recovers, and survives process restarts. A new ET date means a
new row — the daily reset is automatic. The 20%-drawdown walkaway is
account-level (``account.walkaway_locked``), spans days, and needs an
explicit ``reset_walkaway``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from . import ledger, risk

_ET = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class RiskLimits:
    max_daily_loss_pct: float = 6.0
    giveback_pct: float = 50.0
    consecutive_loss_stop: int = 3
    drawdown_walkaway_pct: float = 20.0
    green_to_red: bool = True


class RiskVeto(RuntimeError):
    """Raised by broker when the gate refuses an order. Carries .report."""

    def __init__(self, message: str, report: risk.RiskReport | None = None):
        super().__init__(message)
        self.report = report


@dataclass
class GateState:
    date: str                    # ET date
    locked: bool
    lock_reason: str | None
    report: risk.RiskReport      # live status of all 5 rules for the UI
    day_pnl: float
    day_peak_pnl: float
    equity_hwm: float


class RiskGate:
    def __init__(self, db_path=None, limits: RiskLimits = RiskLimits(),
                 clock: Callable[[], datetime] | None = None):
        self.db_path = db_path
        self.limits = limits
        # clock injectable for tests; default = now in America/New_York
        self._clock = clock or (lambda: datetime.now(_ET))

    def _today(self) -> str:
        return self._clock().astimezone(_ET).date().isoformat()

    def state(self, equity: float | None = None,
              unrealized: float = 0.0) -> GateState:
        today = self._today()
        account = ledger.get_account(self.db_path)
        pnl_info = ledger.get_daily_pnl(today, self.db_path)
        realized = pnl_info["realized_pnl"]
        day_pnl = realized + unrealized
        if equity is None:
            # Offline estimate: exact when flat (equity = cash); open
            # positions valued at cost basis plus the supplied unrealized.
            open_cost = sum(
                p["qty"] * p["avg_cost"]
                for p in ledger.get_open_positions(self.db_path)
            )
            equity = account.cash + open_cost + unrealized

        row = ledger.get_risk_day(today, equity - day_pnl, db_path=self.db_path)
        peak_pnl = max(row["peak_pnl"], day_pnl)
        was_green = bool(row["was_green"]) or day_pnl > 0
        hwm = max(ledger.get_equity_hwm(self.db_path), equity)
        ledger.set_equity_hwm(hwm, self.db_path)

        # Today's closed round trips, in close order, for the loss streak.
        trips_today = [
            t.pnl for t in ledger.get_round_trips(self.db_path)
            if t.closed_at is not None and ledger._et_date(t.closed_at) == today
        ]

        lim = self.limits
        rules = [
            risk.check_max_daily_loss(day_pnl, equity, lim.max_daily_loss_pct),
            risk.check_giveback(day_pnl, peak_pnl, lim.giveback_pct),
        ]
        if lim.green_to_red:
            rules.append(risk.check_green_to_red(day_pnl, was_green))
        else:
            rules.append(risk.RuleStatus("Green-to-red stop", True, "disabled"))
        rules.append(risk.check_consecutive_losses(trips_today,
                                                   lim.consecutive_loss_stop))
        drawdown = risk.check_drawdown(equity, hwm, lim.drawdown_walkaway_pct)
        rules.append(drawdown)
        report = risk.RiskReport(rules=rules)

        if not drawdown.ok:
            ledger.set_walkaway_locked(True, self.db_path)
        walkaway = ledger.is_walkaway_locked(self.db_path)

        # Latch: once locked it stays locked, even if P&L recovers.
        reasons: list[str] = []
        if row["lock_reason"]:
            reasons.extend(r.strip() for r in row["lock_reason"].split(";") if r.strip())
        for v in report.violations:
            if v.name not in reasons:
                reasons.append(v.name)
        locked = bool(row["locked"]) or report.should_stop or walkaway
        if walkaway and drawdown.name not in reasons:
            reasons.append(drawdown.name)
        lock_reason = "; ".join(reasons) if locked else None

        ledger.save_risk_day(today, peak_pnl=peak_pnl, was_green=was_green,
                             locked=locked, lock_reason=lock_reason,
                             db_path=self.db_path)
        return GateState(
            date=today,
            locked=locked,
            lock_reason=lock_reason,
            report=report,
            day_pnl=day_pnl,
            day_peak_pnl=peak_pnl,
            equity_hwm=hwm,
        )

    def assert_can_buy(self, equity: float | None = None,
                       unrealized: float = 0.0) -> None:
        """Raise RiskVeto if the gate is locked (latched OR newly tripped)."""
        s = self.state(equity, unrealized)
        if s.locked:
            raise RiskVeto(
                f"risk gate locked for {s.date}: {s.lock_reason}",
                report=s.report,
            )

    def on_fill(self, equity: float | None = None,
                unrealized: float = 0.0) -> None:
        """Called by broker after every fill; re-runs state() to latch."""
        self.state(equity, unrealized)

    def reset_for_new_day(self) -> None:
        """Clear today's latch (testing / manual new-day reset).

        Resets the row's latch and intraday peak tracking. Rules driven by
        today's realized P&L (daily loss, loss streak) will re-trip if the
        P&L still violates them — the true daily reset is the ET date
        rollover, which starts a fresh row.
        """
        today = self._today()
        row = ledger.get_risk_day(today, 0.0, db_path=self.db_path)
        ledger.save_risk_day(today, peak_pnl=row["peak_pnl"],
                             was_green=bool(row["was_green"]),
                             locked=False, lock_reason=None,
                             db_path=self.db_path)

    def reset_walkaway(self) -> None:
        """Clear the account-level 20% walkaway lock (explicit user action).

        Also rebases the equity high-water mark to the current equity and
        clears today's latch — otherwise the drawdown rule would re-trip on
        the very next evaluation and the reset would be a no-op.
        """
        account = ledger.get_account(self.db_path)
        open_cost = sum(
            p["qty"] * p["avg_cost"]
            for p in ledger.get_open_positions(self.db_path)
        )
        ledger.set_equity_hwm(account.cash + open_cost, self.db_path)
        ledger.set_walkaway_locked(False, self.db_path)
        self.reset_for_new_day()
