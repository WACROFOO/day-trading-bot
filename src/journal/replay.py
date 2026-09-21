"""R11: the stored inputs must reproduce the stored verdict.

Re-run the cascade on each decision's `inputs_json` and compare verdict and
killed_by with what was recorded at the time. A divergence means one of
two things and both are defects: the log lost something the cascade used,
or the cascade changed under the log. Neither announces itself, and a
backtest built on a log that cannot reproduce its own decisions is void
before it starts.

**A deliberate amendment is neither of those**, and until 2026-09-18 this
module could not tell the difference. Amendment A2 changed one gate, and the
next `exercise.py advance` reported "282 decision(s) do not reproduce" — a
true statement about the current rules and a false alarm about the ledger,
which had lost nothing. Those 282 rows reproduce perfectly under the rules
that were in force when they were made.

So the check now walks `cascade.RULE_SETS`, newest first:

    reproduced  the current rules give the recorded answer
    superseded  an older rule set gives it, and that set is named
    diverged    NO rule set this cascade has ever run under gives it —
                the log lost something, and that is still a defect

`superseded` is not a pass in disguise. It is counted, named and printed,
because a growing superseded cohort means the evidence base was collected
under rules that no longer exist, which is a real fact about a backtest even
when it is nobody's bug.
"""

from __future__ import annotations

import json
import sqlite3

from momentum_platform.cascade import RULE_SETS, Inputs, evaluate

from . import ledger as L


OVERRIDE_KEYS = ("catalyst_gate_kills", "float_gate_kills", "pillars_min")


def _overrides(rs: dict) -> dict:
    """The evaluate() keyword arguments a rule set carries. Every amendment
    adds its key here and in cascade.RULE_SETS — nowhere else."""
    return {k: rs[k] for k in OVERRIDE_KEYS if k in rs}


def _matches(stored: dict, row, **kw) -> bool:
    res = evaluate(Inputs(**stored), **kw)
    return res.verdict.value == row["verdict"] and res.killed_by == row["killed_by"]


def check(conn: sqlite3.Connection) -> dict:
    rows = L.decisions(conn)
    diverged, superseded, by_rules = [], [], {}
    current = RULE_SETS[0]
    for r in rows:
        stored = json.loads(r["inputs_json"])
        if _matches(stored, r, **_overrides(current)):
            by_rules[current["name"]] = by_rules.get(current["name"], 0) + 1
            continue
        for rs in RULE_SETS[1:]:
            if _matches(stored, r, **_overrides(rs)):
                by_rules[rs["name"]] = by_rules.get(rs["name"], 0) + 1
                superseded.append({
                    "decision_id": r["decision_id"], "symbol": r["symbol"],
                    "ts_et": r["ts_et"], "rules": rs["name"],
                    "recorded": (r["verdict"], r["killed_by"])})
                break
        else:
            res = evaluate(Inputs(**stored))
            diverged.append({
                "decision_id": r["decision_id"], "symbol": r["symbol"], "ts_et": r["ts_et"],
                "recorded": (r["verdict"], r["killed_by"]),
                "replayed": (res.verdict.value, res.killed_by),
            })
    return {"checked": len(rows),
            "reproduced": len(rows) - len(diverged) - len(superseded),
            "superseded": superseded,
            "by_rules": by_rules,
            "current_rules": current["name"],
            "diverged": diverged}
