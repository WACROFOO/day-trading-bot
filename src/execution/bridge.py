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

from .intent import WORST_FILL_SIZING, EntryIntent, entry_limit, shares_for, sized_for, sizing_reserve


def intent_from_decision(row: sqlite3.Row | dict, dollar_risk: float,
                         target: Optional[float] = None,
                         max_notional: Optional[float] = None,
                         spread: Optional[float] = None,
                         worst_fill: Optional[bool] = None) -> EntryIntent:
    """Size the plan and carry the verdict. Does not judge; `refusals` does.

    The stop defines the size; the account bounds it. With `max_notional`
    the share count is the smaller of the two, and the note says which.
    Under A18 (`worst_fill`, default the live switch) the size is divided by
    the worst fill's risk: (entry limit − stop) + `spread` + commission."""
    r = dict(row)
    trigger, stop = round(float(r["trigger"]), 2), round(float(r["stop"]), 2)
    worst = WORST_FILL_SIZING if worst_fill is None else worst_fill
    reserve = sizing_reserve(trigger, spread) if worst and trigger > stop > 0 else 0.0
    shares, by = sized_for(trigger, stop, dollar_risk, max_notional, reserve=reserve)
    note = f"decision {r['decision_id']}"
    if reserve:
        sp = f"spread {spread:.2f}" if spread is not None and spread > 0 else "no spread read"
        note += (f" · sized from the worst fill (A18): limit {entry_limit(trigger):.2f} − stop {stop:.2f}"
                 f" + {sp} + 0.01 commission = ${trigger - stop + reserve:.4f}/sh")
    if by == "funds":
        note += " · sized by funds, not risk"
    return EntryIntent(
        symbol=r["symbol"],
        trigger=trigger,
        stop=stop,
        shares=shares,
        dollar_risk=dollar_risk,
        max_notional=max_notional,
        target=round(target, 2) if target is not None else None,
        plan_allowed=bool(r["plan_allowed"]),
        verdict=r["verdict"] or "",
        session=r["session"] if r["session"] in ("regular", "premarket") else "none",
        note=note,
        ref=str(r["decision_id"]),
        sizing_reserve=reserve,
        sizing_spread=spread if spread is not None and spread > 0 else None,
    )


def bar_seconds(row: sqlite3.Row | dict) -> int:
    """How long the bar that armed the plan lasted. `ts_et` is the bar's OPEN;
    the decision could not exist before open + this. Unknown reads as one
    minute, the desk's only decision resolution."""
    res = str(dict(row).get("bar_resolution") or "1m").strip().lower()
    if res.endswith("s") and res[:-1].isdigit():
        return int(res[:-1])
    if res.endswith("m") and res[:-1].isdigit():
        return int(res[:-1]) * 60
    return 60


def decision_clock(row: sqlite3.Row | dict) -> datetime:
    """The bar that armed the plan, as an aware datetime. Point in time."""
    return datetime.fromisoformat(dict(row)["ts_et"])
