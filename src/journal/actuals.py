"""What the market did after each decision. Filled for EVERY decision.

This is the block that makes the exercise a backtest rather than a diary,
and it is computed for refused, suppressed and unfilled decisions exactly
as for taken ones — that is the only way "the one I passed on" becomes a
measurement instead of a memory (`docs/paper-exercise-brief.md` §⑤).

Everything is measured from the decision's OWN bar forward. The reference
price is the plan's trigger when there is one (what the plan would have
paid) and the bar close otherwise. MFE/MAE are reported in PLANNED R —
(trigger − stop) — and the column names say so, because the replication
found realised risk ran a median 1.52× planned and a bare "R" hides which
one you are reading.

Whether the stop or the target was hit first is decided bar by bar with
the conservative rule: if one bar's range touches both, the STOP is taken
as first. On a 1-minute bar that is a 25% ambiguity the external review
already called out; the choice is stated here rather than buried.
"""

from __future__ import annotations

import sqlite3
from bisect import bisect_right
from datetime import datetime, timedelta, timezone
from typing import Optional

from . import ledger as L
from .bars import Bar

HORIZONS_MIN = (5, 15, 30, 60)


def _utc(ts_et_iso: str) -> datetime:
    return datetime.fromisoformat(ts_et_iso).astimezone(timezone.utc)


def _bar_dt(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def forward(bars: list[Bar], from_dt: datetime) -> list[Bar]:
    """Bars strictly AFTER the decision bar. The decision bar itself is what
    was knowable; the next one is the first thing that was not."""
    keys = [_bar_dt(b[0]) for b in bars]
    i = bisect_right(keys, from_dt)
    return bars[i:]


def compute(row: sqlite3.Row | dict, bars: list[Bar]) -> Optional[dict]:
    """The actuals dict for one decision, or None when there is no tape."""
    r = dict(row)
    t0 = _utc(r["ts_et"])
    # Same session only. Without this a decision with no forward bars today
    # was scored against the NEXT day's tape when the symbol recurred, and
    # "close" silently meant the last bar the desk saw before the hard stop.
    day = r["ts_et"][:10]
    fwd = [b for b in forward(bars, t0) if _bar_dt(b[0]).astimezone(L.ET).date().isoformat() == day]
    if not fwd:
        return {"ref_price": float(r["trigger"]) if r.get("trigger") else float(r["last"] or 0),
                "risk_share": None, "bars_available": 0, "first_hit": "no_tape",
                "trigger_hit": 0, "stop_hit": 0, "target_hit": 0}

    ref = float(r["trigger"]) if r.get("trigger") else float(r["last"] or fwd[0][1])
    stop = float(r["stop"]) if r.get("stop") else None
    target = float(r["target"]) if r.get("target") else None
    rps = (ref - stop) if stop is not None and stop < ref else None

    out: dict = {"ref_price": ref, "risk_share": rps, "bars_available": len(fwd)}

    hi = lo = None
    stop_hit = target_hit = None
    first_hit = "neither"
    # The plan is a buy-stop at the trigger, above the market when armed. A
    # stop or target "hit" before price ever reached the trigger is not a
    # trade outcome; the controls used to charge −1 R for it (audit
    # 2026-09-08). Tracking starts at the first bar that touches the trigger.
    trigger_hit = None
    for ts, o, h, l, c, v in fwd:
        if trigger_hit is None:
            if r.get("trigger") and h >= float(r["trigger"]):
                trigger_hit = ts
            else:
                continue
        hi = h if hi is None else max(hi, h)
        lo = l if lo is None else min(lo, l)
        if stop is not None and stop_hit is None and l <= stop:
            stop_hit = ts
            if first_hit == "neither":
                first_hit = "stop"
        if target is not None and target_hit is None and h >= target:
            target_hit = ts
            if first_hit == "neither":
                first_hit = "target"
            elif first_hit == "stop" and stop_hit == ts:
                first_hit = "stop"          # same bar: conservative
    # a bar that touched both on the same timestamp: stop wins (stated above)
    if stop_hit and target_hit and stop_hit == target_hit:
        first_hit = "stop"

    for m in HORIZONS_MIN:
        cut = t0 + timedelta(minutes=m)
        win = [b for b in fwd if _bar_dt(b[0]) <= cut]
        if win:
            out[f"h{m}"] = max(b[2] for b in win)
            out[f"l{m}"] = min(b[3] for b in win)
            out[f"c{m}"] = win[-1][4]
    out["h_close"], out["l_close"], out["c_close"] = hi, lo, fwd[-1][4]
    out["trigger_hit"] = int(trigger_hit is not None)
    out["trigger_hit_ts"] = trigger_hit
    if trigger_hit is None:
        first_hit = "untriggered"

    if rps and hi is not None:
        out["mfe_r_planned"] = round((hi - ref) / rps, 4)
        out["mae_r_planned"] = round((lo - ref) / rps, 4)
    out["stop_hit"] = int(stop_hit is not None)
    out["stop_hit_ts"] = stop_hit
    out["target_hit"] = int(target_hit is not None)
    out["target_hit_ts"] = target_hit
    out["first_hit"] = first_hit
    return out


def fill_all(conn: sqlite3.Connection, bars_by_symbol: dict[str, list[Bar]]) -> dict:
    """Compute and store actuals for every decision that has none yet."""
    done, no_tape = 0, []
    for row in L.without_actuals(conn):
        bars = bars_by_symbol.get(row["symbol"], [])
        a = compute(row, bars)
        if a is None or a.get("bars_available") == 0:
            no_tape.append(row["decision_id"])
            if a is not None:
                L.record_actuals(conn, row["decision_id"], a)   # recorded as no_tape, not left for tomorrow
            continue
        L.record_actuals(conn, row["decision_id"], a)
        done += 1
    conn.commit()
    return {"computed": done, "no_tape": no_tape}
