"""A ledger decision -> an EntryIntent. Nothing else.

The bridge is deliberately thin: everything that decides whether an order
may exist lives in `intent.refusals`, and everything that decides whether a
name is tradeable lives in the cascade, upstream. This module only carries
the cascade's answer across, sizes from the user's stated dollar risk, and
states which session the intent is FOR — from the decision's own bar, never
from the wall clock, so a replay is judged as of the moment it happened.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional

from .intent import EntryIntent, shares_for


def intent_from_decision(row: sqlite3.Row | dict, dollar_risk: float,
                         target: Optional[float] = None) -> EntryIntent:
    """Size the plan and carry the verdict. Does not judge; `refusals` does."""
    r = dict(row)
    trigger, stop = float(r["trigger"]), float(r["stop"])
    return EntryIntent(
        symbol=r["symbol"],
        trigger=round(trigger, 2),
        stop=round(stop, 2),
        shares=shares_for(round(trigger, 2), round(stop, 2), dollar_risk),
        dollar_risk=dollar_risk,
        target=round(target, 2) if target is not None else None,
        plan_allowed=bool(r["plan_allowed"]),
        verdict=r["verdict"] or "",
        session=r["session"] if r["session"] in ("regular", "premarket") else "none",
        note=f"decision {r['decision_id']}",
        ref=str(r["decision_id"]),
    )


def decision_clock(row: sqlite3.Row | dict) -> datetime:
    """The bar that armed the plan, as an aware datetime. Point in time."""
    return datetime.fromisoformat(dict(row)["ts_et"])
