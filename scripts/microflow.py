#!/usr/bin/env python3
"""The microflow research command — 10-second micro pullback, Phase 0.

    python3 scripts/microflow.py capture               what the tape holds
    python3 scripts/microflow.py measure               the Phase-0 read-out
    python3 scripts/microflow.py measure --day 2026-09-18
    python3 scripts/microflow.py config                every parameter and its provenance

Reads the ledger. Writes nothing, decides nothing, and places nothing.
See docs/PLAN-10s-micro-pullback.md.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from journal import ledger as L  # noqa: E402
from momentum_platform.microflow import DEFAULT, bars as B, measure as M  # noqa: E402

DIM, BOLD, OK, BAD, WARN, END = "\033[2m", "\033[1m", "\033[92m", "\033[91m", "\033[93m", "\033[0m"


def say(m=""):
    print(m, flush=True)


def banner(conn, db):
    n = conn.execute("SELECT COUNT(*) FROM bars_10s").fetchone()[0]
    rng = conn.execute("SELECT MIN(ts), MAX(ts) FROM bars_10s").fetchone()
    say(f"{BOLD}TAPE{END} · {db.name} · {n:,} ten-second candles · "
        f"{rng[0] or '—'} → {rng[1] or '—'}")
    say(f"{DIM}10-second candles are captured by the desk from 2026-09-18. "
        f"Days before that hold 1-minute bars only.{END}")
    say()


def cmd_capture(conn, args) -> int:
    fine = B.load(conn, day=args.day)
    if not fine:
        say(f"  {WARN}!!{END}   no ten-second candles for {args.day or 'any day'}")
        return 1
    say(f"{BOLD}COVERAGE{END}  a full minute holds six ten-second candles")
    say(f"  {'symbol':8} {'candles':>8} {'minutes':>8} {'present':>8} {'gap mins':>9}")
    for sym, cs in sorted(fine.items()):
        c = B.coverage(cs)
        pct = f"{c['present_pct']}%" if c["present_pct"] is not None else "—"
        say(f"  {sym:8} {c['candles']:>8,} {c['minutes']:>8,} {pct:>8} {len(c['gaps']):>9}")
    return 0


def cmd_measure(conn, args) -> int:
    cfg = DEFAULT
    m = M.measure(conn, cfg, day=args.day)
    if not m["symbols"]:
        say(f"  {WARN}!!{END}   nothing captured for {args.day or 'any day'} — run a session first")
        return 1

    say(f"{BOLD}FUNNEL{END}")
    say(f"  {m['candles']:,} ten-second candles across {len(m['symbols'])} symbols")
    say(f"  {m['dips']} micro-pullback shapes found  "
        f"{DIM}(shape only — no context gate applied, so this is an upper bound){END}")
    say(f"  {m['dips_with_quote']} carry a quote · {m['dips_without_quote']} do not "
        f"{DIM}(no quote = UNKNOWN, never assumed zero){END}")
    say()

    say(f"{BOLD}THE NUMBER THAT DECIDES IT{END}  spread ÷ risk = what a round trip costs, in R")
    d = m["spread_over_risk"]
    r = m["risk_per_share"]
    if d["n"]:
        say(f"  risk per share   median ${r['median']}  (p25 ${r['p25']} · p75 ${r['p75']} · "
            f"min ${r['min']} · max ${r['max']})")
        say(f"  spread ÷ risk    median {d['median']}  (p25 {d['p25']} · p75 {d['p75']} · "
            f"max {d['max']})")
        ins = m.get("dips_inside_spread") or {}
        say(f"  dips INSIDE the spread (spread ≥ the whole stop): {ins.get('n', 0)} / {m['dips_with_quote']}"
            f"  ({ins.get('pct')}%) — the plan's stop condition "
            f"{'FIRED' if ins.get('median_dip_inside') else 'did NOT fire'} on the median")
        say(f"  {DIM}best case +0.25 R per trade = 50% wins on the half-at-1R / half-at-2R ladder "
            f"(MICRO-PULLBACK-SPEC.md §sizing: 25 x +1.5R, 25 x −1R over 50 trades = +12.5R); "
            f"a median cost of {d['median']} leaves {0.25 - (d['median'] or 0):+.3f} R on the median "
            f"setup — a median cost, not the expected cost of the subset a gate would select{END}")
    else:
        say("  — no quoted dip to measure")
    say()

    say(f"{BOLD}SURVIVAL BY GATE{END}  k = how many times the stop must exceed the spread")
    say(f"  {'k':>4} {'spread at most':>15} {'dips surviving':>16} {'spread costs':>13}")
    for k, v in sorted(m["survival_by_k"].items()):
        mark = "  ← in force" if float(k) == cfg.spread_k else ""
        pct = f"{v['pct']}%" if v["pct"] is not None else "—"
        say(f"  {k:>4} {1 / k:>14.0%} {v['n']:>6} / {m['dips_with_quote']:<5} {pct:>4} "
            f"{1 / k:>12.3f}R{mark}")
    say()

    v, reasons = M.verdict(m, cfg)
    colour = {"GO": OK, "MARGINAL": WARN, "NO-GO": BAD, "INCONCLUSIVE": WARN}[v]
    say(f"{BOLD}VERDICT{END}  {colour}{v}{END}")
    for x in reasons:
        say(f"  · {x}")
    say()
    say(f"{BOLD}WHAT THIS DID NOT CHECK{END}")
    for x in M.limitations():
        say(f"  {DIM}· {x}{END}")
    return 0


def cmd_config(conn, args) -> int:
    cfg = DEFAULT
    say(f"{BOLD}MICROFLOW CONFIG{END}  fingerprint {cfg.fingerprint()}")
    say()
    for k, val in sorted(cfg.as_dict().items()):
        p = cfg.provenance(k)
        flag = {"MEASURED": OK, "REASONED_NOT_MEASURED": WARN, "UNKNOWN": BAD}.get(
            p["evidence_status"], WARN)
        say(f"  {BOLD}{k}{END} = {val}")
        say(f"    {flag}{p['evidence_status']}{END} · {p['origin']}")
        for line in _wrap(p["note"], 72):
            say(f"    {DIM}{line}{END}")
        say()
    und, unm = cfg.undeclared(), cfg.unmeasured()
    if und:
        say(f"  {BAD}UNDECLARED (a defect):{END} {', '.join(und)}")
    say(f"  {WARN}awaiting a measurement:{END} {', '.join(unm) if unm else 'none'}")
    return 0


def _wrap(text, width):
    words, line, out = text.split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > width:
            out.append(line); line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        out.append(line)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["capture", "measure", "config"])
    ap.add_argument("--day", help="ISO date, e.g. 2026-09-18")
    ap.add_argument("--db", default=os.environ.get("JOURNAL_DB") or str(L.DEFAULT_DB))
    args = ap.parse_args(argv)

    db = Path(args.db)
    if not db.exists():
        say(f"no ledger at {db}")
        return 1
    conn = L.connect(db)
    banner(conn, db)
    return {"capture": cmd_capture, "measure": cmd_measure, "config": cmd_config}[args.command](conn, args)


if __name__ == "__main__":
    sys.exit(main())
