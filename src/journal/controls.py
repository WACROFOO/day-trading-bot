"""R5: the free baselines every result has to beat before it means anything.

`2026-08-score-basket.md`: equal weight beat the pillar score in 16 of 16
matched pairs. A selection rule that loses to its own equal-weight baseline
looks identical to one that works until the baseline is run, so it is run
here, on the same decisions, from the same actuals, in the same units.

Three series, all in PLANNED R so they are comparable to each other:

  strategy    the plan as armed: +target_R if the target was hit first,
              −1 if the stop was hit first, else the close in R
  hold_close  enter at the trigger, no stop, no target, sell at the close.
              Same names, same instants — isolates what the stop and target
              add or cost
  random_bar  enter at the CLOSE of the decision bar instead of the trigger,
              same stop distance, same close. Isolates the trigger

No confidence intervals are computed. With the sample sizes this exercise
will have for months, a CI would be decoration; the honest output is n and
the raw series, and the reader is told that.
"""

from __future__ import annotations

import sqlite3
from statistics import mean, median


def series(conn: sqlite3.Connection) -> dict[str, list[float]]:
    rows = conn.execute("""
        SELECT d.decision_id, d.trigger, d.stop, d.target, d.last, d.reward_multiple,
               a.first_hit, a.c_close, a.risk_share
        FROM decisions d JOIN actuals a USING(decision_id)
        WHERE a.risk_share IS NOT NULL AND a.risk_share > 0
    """).fetchall()
    out = {"strategy": [], "hold_close": [], "random_bar": []}
    for r in rows:
        rps = r["risk_share"]
        close_r = (r["c_close"] - r["trigger"]) / rps
        if r["first_hit"] == "stop":
            strat = -1.0
        elif r["first_hit"] == "target" and r["target"]:
            strat = (r["target"] - r["trigger"]) / rps
        else:
            strat = close_r
        out["strategy"].append(round(strat, 4))
        out["hold_close"].append(round(close_r, 4))
        if r["last"]:
            out["random_bar"].append(round((r["c_close"] - r["last"]) / rps, 4))
    return out


def summary(conn: sqlite3.Connection) -> dict[str, dict]:
    s = series(conn)
    return {k: {"n": len(v), "mean_R": round(mean(v), 4) if v else None,
                "median_R": round(median(v), 4) if v else None,
                "win_rate": round(sum(1 for x in v if x > 0) / len(v), 3) if v else None}
            for k, v in s.items()}
