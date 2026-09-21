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


def float_only_cohort(conn) -> dict:
    """Review 2026-09-21, item 5: the cascade stops at the FIRST failing gate,
    so `killed_by = 'float'` means float was the first gate to fail, not the
    only one, and gates_json records the later gates as NOT_APPLICABLE. The
    question the review asked — what happens to names that fail ONLY float —
    is answered by re-running each float-killed decision's stored inputs with
    the float gate switched off (and the catalyst gate, which A2 already made
    a flag): a decision that is then allowed failed nothing but float.
    Read-only; nothing is written."""
    import json
    from momentum_platform.cascade import Inputs, evaluate
    rows = conn.execute(f"""
        SELECT d.decision_id, d.symbol, d.ts_et, d.inputs_json, d.trigger, d.stop, d.target,
               a.first_hit, a.c_close, a.risk_share, a.trigger_hit
        FROM decisions d LEFT JOIN actuals a USING(decision_id)
        WHERE d.killed_by = 'float' AND {PROSPECTIVE} ORDER BY d.ts_et""").fetchall()
    only, also = [], {}
    for r in rows:
        res = evaluate(Inputs(**json.loads(r["inputs_json"])),
                       float_gate_kills=False, catalyst_gate_kills=False, pillars_min=None)
        if res.plan_allowed:
            only.append(r)
        else:
            also[res.killed_by or "?"] = also.get(res.killed_by or "?", 0) + 1
    triggered = [r for r in only if r["trigger_hit"] and r["risk_share"] and r["risk_share"] > 0]
    strat = [x for x in (strat_r(r) for r in triggered) if x is not None]
    return {"float_killed": len(rows), "float_only": len(only), "also_failed": also,
            "float_only_triggered": len(triggered), "float_only_strat": strat}


def print_float_only(conn) -> None:
    c = float_only_cohort(conn)
    print(f"\n{BOLD}float-only cohort{END} — of {c['float_killed']} prospective float kills, "
          f"{c['float_only']} fail NOTHING but float"
          + (f"; the rest also fail: " + ", ".join(f"{k} {v}" for k, v in sorted(c["also_failed"].items()))
             if c["also_failed"] else ""))
    print(f"  {c['float_only_triggered']} of the float-only rows would have triggered")
    print(f"  armed plan (2R/stop) {_stats(c['float_only_strat'])}")
    print(f"  {DIM}gates_json records the gates after the first kill as NOT_APPLICABLE; this cohort "
          f"is a re-evaluation of the stored inputs with float (and catalyst) switched off{END}")


def catalyst_states(conn) -> dict:
    """Review item 6: three states that the phase-A ledger merged into one.
    From each decision's stored inputs: `catalyst_source_ok` False = the feed
    was unavailable (UNKNOWN); `catalyst_today` True = a catalyst dated today
    was found; otherwise a healthy feed found none (NONE). Counted over every
    prospective decision, over the rows the catalyst gate killed, and by day."""
    import json
    out = {"all": {}, "catalyst_killed": {}, "by_day": {}}

    def state(inp):
        # `catalyst_source_ok` was added with A2 on 2026-09-17. A stored input
        # without the key predates the UNKNOWN state: whether the feed was up
        # is UNRECORDED, and calling it NONE would invent a healthy feed.
        if "catalyst_source_ok" not in inp:
            return "FOUND" if inp.get("catalyst_today") or inp.get("live_theme") else "UNRECORDED"
        if not inp.get("catalyst_source_ok", True):
            return "UNKNOWN"
        return "FOUND" if inp.get("catalyst_today") or inp.get("live_theme") else "NONE"

    for r in conn.execute(f"SELECT ts_et, killed_by, inputs_json FROM decisions d WHERE {PROSPECTIVE}"):
        st = state(json.loads(r["inputs_json"]))
        out["all"][st] = out["all"].get(st, 0) + 1
        if r["killed_by"] == "catalyst":
            out["catalyst_killed"][st] = out["catalyst_killed"].get(st, 0) + 1
        day = out["by_day"].setdefault(r["ts_et"][:10], {})
        day[st] = day.get(st, 0) + 1
    return out


def print_catalyst_states(conn) -> None:
    c = catalyst_states(conn)
    fmt = lambda d: " · ".join(f"{k} {v}" for k, v in sorted(d.items())) or "none"   # noqa: E731
    print(f"\n{BOLD}catalyst states{END} (FOUND = catalyst dated today · NONE = healthy feed, none found · "
          f"UNKNOWN = no feed · UNRECORDED = row predates the UNKNOWN state, 2026-09-17)")
    print(f"  all prospective decisions: {fmt(c['all'])}")
    print(f"  killed by the catalyst gate: {fmt(c['catalyst_killed'])}")
    for day, d in sorted(c["by_day"].items()):
        print(f"    {day}: {fmt(d)}")
    print(f"  {DIM}a kill on UNKNOWN says the desk could not look, not that there was no news{END}")


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
    print_float_only(conn)
    print_catalyst_states(conn)
    print(f"\n{DIM}A gate is earning its keep when the cohort it kills does WORSE than the")
    print(f"cohort it allows. One that kills a better cohort than it keeps is a cost,")
    print(f"and its threshold is the thing to re-derive — via an amendment in")
    print(f"docs/preregistration.md §5, never by editing the constant first.{END}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
