"""R11: the stored inputs must reproduce the stored verdict.

Re-run the cascade on each decision's `inputs_json` and compare verdict and
killed_by with what was recorded at the time. A divergence means one of
two things and both are defects: the log lost something the cascade used,
or the cascade changed under the log. Neither announces itself, and a
backtest built on a log that cannot reproduce its own decisions is void
before it starts.
"""

from __future__ import annotations

import json
import sqlite3

from momentum_platform.cascade import Inputs, evaluate

from . import ledger as L


def check(conn: sqlite3.Connection) -> dict:
    rows = L.decisions(conn)
    diverged = []
    for r in rows:
        stored = json.loads(r["inputs_json"])
        res = evaluate(Inputs(**stored))
        if res.verdict.value != r["verdict"] or res.killed_by != r["killed_by"]:
            diverged.append({
                "decision_id": r["decision_id"], "symbol": r["symbol"], "ts_et": r["ts_et"],
                "recorded": (r["verdict"], r["killed_by"]),
                "replayed": (res.verdict.value, res.killed_by),
            })
    return {"checked": len(rows), "reproduced": len(rows) - len(diverged),
            "diverged": diverged}
