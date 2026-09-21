#!/usr/bin/env python3
"""What each kill gate cost, measured on what the tape did afterwards.

    python3 scripts/gate_audit.py [--db PATH] [--gate rising]

READ-ONLY. No order path, no writes: every number is a SELECT over decisions
the desk already recorded and actuals already computed from its own bars.

Why this exists. On 2026-09-18 the cascade killed IMCC on the `rising` gate
at 3.65, 3.05, 6.00 and 6.25 while it ran from 3 to 8 — the same shape as
MSGY (2026-08-11: rejected untested, ran 2.54 → 5.43). A gate meant to skip
names that have already faded may be skipping names mid-run. Feelings about
one sting are not a reason to change a threshold; a distribution is. This
script produces the distribution, and any change it motivates goes through
`docs/preregistration.md` §5 as an amendment BEFORE the code changes.

Method, stated so it can be argued with:

  - prospective decisions only; backfill rows are excluded (audit F3);
  - a killed plan counts as a would-have-been trade only if the tape later
    touched its trigger (`actuals.trigger_hit`) — a plan never triggered is
    not a missed trade, it is nothing;
  - outcomes are the same three series as `journal.controls`, in PLANNED R:
    the armed plan (target first = +2R, stop first = −1R, neither = close),
    and hold-to-close on the same instants;
  - MFE is planned-R from the reference price; it answers "how far did it
    run", not "what would you have kept".

The one thing this cannot see: the gap scan's own "already faded" filter
rejects names BEFORE the desk subscribes, so nothing about them reaches the
ledger. This audit covers the cascade's gate only, and says so.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from journal import ledger as L  # noqa: E402

DIM, BOLD, OK, BAD, WARN, END = "\033[2m", "\033[1m", "\033[92m", "\033[91m", "\033[93m", "\033[0m"

PROSPECTIVE = "(d.data_status IS NULL OR d.data_status NOT LIKE '%-backfill')"


def _stats(v):
    if not v:
        return "n=0"
    s = sorted(v)
    p75 = s[(3 * len(s)) // 4] if len(s) > 3 else s[-1]
    return (f"n={len(s):<4} mean {mean(s):+7.3f}  median {median(s):+7.3f}  "
            f"p75 {p75:+7.3f}  max {s[-1]:+7.3f}")


def rows_for_gate(conn, gate):
    return conn.execute(f"""
        SELECT d.decision_id, d.symbol, d.ts_et, d.trigger, d.stop, d.target,
               a.first_hit, a.c_close, a.risk_share, a.mfe_r_planned, a.trigger_hit
        FROM decisions d JOIN actuals a USING(decision_id)
        WHERE d.killed_by = ? AND {PROSPECTIVE}
          AND a.risk_share IS NOT NULL AND a.risk_share > 0
        ORDER BY d.ts_et
    """, (gate,)).fetchall()


def strat_r(r):
    rps = r["risk_share"]
    if r["first_hit"] == "stop":
        return -1.0
    if r["first_hit"] == "target" and r["target"]:
        return (r["target"] - r["trigger"]) / rps
    if r["c_close"] is None:
        return None
    return (r["c_close"] - r["trigger"]) / rps


def audit_gate(conn, gate):
    rows = rows_for_gate(conn, gate)
    triggered = [r for r in rows if r["trigger_hit"]]
    print(f"\n{BOLD}gate `{gate}`{END} — {len(rows)} prospective kill(s), "
          f"{len(triggered)} would have triggered ({len(rows) - len(triggered)} never touched the entry)")
    if not triggered:
        return
    hits = {}
    for r in triggered:
        hits[r["first_hit"]] = hits.get(r["first_hit"], 0) + 1
    print(f"  first hit: " + " · ".join(f"{k} {v}" for k, v in sorted(hits.items())))
    strat = [x for x in (strat_r(r) for r in triggered) if x is not None]
    hold = [(r["c_close"] - r["trigger"]) / r["risk_share"] for r in triggered
            if r["c_close"] is not None]
    mfe = [r["mfe_r_planned"] for r in triggered if r["mfe_r_planned"] is not None]
    print(f"  armed plan (2R/stop) {_stats(strat)}")
    print(f"  hold to close        {_stats(hold)}")
    print(f"  MFE (how far it ran) {_stats(mfe)}")
    runners = sorted((r for r in triggered if (r["mfe_r_planned"] or 0) >= 2.0),
                     key=lambda r: -(r["mfe_r_planned"] or 0))[:10]
    if runners:
        print(f"  {WARN}killed, then ran ≥ 2R{END} — {len(runners)} shown, worst first:")
        for r in runners:
            print(f"    {r['ts_et'][11:16]}  {r['symbol']:<6} trigger {r['trigger']:<8} "
                  f"MFE {r['mfe_r_planned']:+.2f}R  first_hit {r['first_hit']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=os.environ.get("JOURNAL_DB") or str(L.DEFAULT_DB))
    ap.add_argument("--gate", help="one gate id; default: every gate that killed anything")
    args = ap.parse_args(argv)
    conn = L.connect(args.db)

    print(f"{BOLD}GATE AUDIT{END} · {args.db}")
    print(f"{DIM}read-only · prospective decisions only · planned R · "
          f"the gap scan's rejects never reach the ledger and are NOT covered here{END}")

    gates = ([args.gate] if args.gate else
             [g[0] for g in conn.execute(
                 f"SELECT DISTINCT killed_by FROM decisions d "
                 f"WHERE killed_by IS NOT NULL AND {PROSPECTIVE} ORDER BY 1")])
    for g in gates:
        audit_gate(conn, g)

    # The comparison that decides whether a gate earns its keep: the cohort
    # it kills against the cohort it lets through, same rule, same units.
    allowed = conn.execute(f"""
        SELECT d.trigger, d.stop, d.target, a.first_hit, a.c_close, a.risk_share
        FROM decisions d JOIN actuals a USING(decision_id)
        WHERE d.plan_allowed = 1 AND {PROSPECTIVE}
          AND a.risk_share IS NOT NULL AND a.risk_share > 0
          AND COALESCE(a.trigger_hit, 1) = 1
    """).fetchall()
    strat_allowed = [x for x in (strat_r(r) for r in allowed) if x is not None]
    print(f"\n{BOLD}the allowed cohort, same rule{END}")
    print(f"  armed plan (2R/stop) {_stats(strat_allowed)}")
    print(f"\n{DIM}A gate is earning its keep when the cohort it kills does WORSE than the")
    print(f"cohort it allows. One that kills a better cohort than it keeps is a cost,")
    print(f"and its threshold is the thing to re-derive — via an amendment in")
    print(f"docs/preregistration.md §5, never by editing the constant first.{END}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
