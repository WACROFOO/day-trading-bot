"""The daily risk gate, computed from the ledger and latched in it.

`src/paper_trading/risk_gate.py` has the five rules but reads a ledger this
exercise does not write, so the live TRADE path ran with no gate at all —
found in the 2026-09-07 review. This gate reads `orders` (fills and exits
in the journal) and latches in `risk_day`, keyed by ET date, so once
tripped it stays tripped for the day even if the next trade would have
won, and it survives a restart.

Limits are in R of the stated dollar risk, because that is the unit the
whole exercise reports in. PROPOSED values, to be set with the rest of
docs/preregistration.md; the defaults mirror `RiskLimits` where a mapping
exists (3 consecutive losses) and put the daily loss at 3 R.

Exits are always allowed. This gate is asked before an ENTRY only.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from . import ledger as L


class RiskVeto(RuntimeError):
    """The day is locked. Carries .reason. Exits are still allowed."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Limits:
    max_daily_loss_r: float = 3.0        # PROPOSED
    consecutive_losses: int = 3          # mirrors RiskLimits.consecutive_loss_stop
    max_entries_per_day: int = 6         # PROPOSED: Ross's morning is a handful of names


def _today_et() -> str:
    return datetime.now(timezone.utc).astimezone(L.ET).date().isoformat()


def closed_trades(conn: sqlite3.Connection, day: str) -> list[dict]:
    """Orders filled and exited on `day`, oldest first, with realised R."""
    rows = conn.execute("""SELECT order_id, symbol, fill_price, exit_price, shares, planned_risk,
                                  fill_ts, exit_ts FROM orders
                           WHERE fill_price IS NOT NULL AND exit_price IS NOT NULL
                             AND substr(exit_ts, 1, 10) = ? ORDER BY exit_ts""", (day,)).fetchall()
    out = []
    for r in rows:
        pnl = (r["exit_price"] - r["fill_price"]) * r["shares"]
        out.append({**dict(r), "pnl": round(pnl, 2),
                    "r": round(pnl / r["planned_risk"], 4) if r["planned_risk"] else None})
    return out


def entries_today(conn: sqlite3.Connection, day: str) -> int:
    return conn.execute("SELECT COUNT(*) FROM orders WHERE substr(placed_at,1,10)=? OR "
                        "substr(fill_ts,1,10)=?", (day, day)).fetchone()[0]


class JournalRiskGate:
    def __init__(self, conn: sqlite3.Connection, limits: Limits = Limits(),
                 today: Optional[callable] = None):
        self.conn, self.limits = conn, limits
        self.today = today or _today_et

    def state(self) -> dict:
        day = self.today()
        row = self.conn.execute("SELECT * FROM risk_day WHERE date=?", (day,)).fetchone()
        trades = closed_trades(self.conn, day)
        day_r = round(sum(t["r"] or 0.0 for t in trades), 4)
        streak = 0
        for t in reversed(trades):
            if (t["r"] or 0) < 0:
                streak += 1
            else:
                break
        return {"date": day, "locked": bool(row and row["locked"]),
                "reason": row["reason"] if row else None, "day_r": day_r,
                "consecutive_losses": streak, "entries": entries_today(self.conn, day),
                "closed": len(trades)}

    def _lock(self, day: str, reason: str) -> None:
        self.conn.execute("INSERT OR REPLACE INTO risk_day (date, locked, reason, locked_at) "
                          "VALUES (?, 1, ?, ?)", (day, reason, L._now()))
        self.conn.commit()

    def assert_can_buy(self) -> None:
        st = self.state()
        if st["locked"]:
            raise RiskVeto(f"day locked: {st['reason']}")
        lim = self.limits
        if st["day_r"] <= -lim.max_daily_loss_r:
            self._lock(st["date"], f"daily loss {st['day_r']} R reached −{lim.max_daily_loss_r} R")
        elif st["consecutive_losses"] >= lim.consecutive_losses:
            self._lock(st["date"], f"{st['consecutive_losses']} consecutive losses")
        elif st["entries"] >= lim.max_entries_per_day:
            self._lock(st["date"], f"{st['entries']} entries today, limit {lim.max_entries_per_day}")
        else:
            return
        raise RiskVeto(f"day locked: {self.state()['reason']}")
