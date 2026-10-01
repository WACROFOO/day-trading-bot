#!/usr/bin/env python3
"""Addendum 2026-10-01c: three opening-risk candidates on the ten-year plan
cache, under the rules audit's own adoption rule (research/edge-hunt/
PREREGISTRATION.md). O1 stop >= k x the recent 1-minute range, O2 no fill in
the first minutes of regular hours, O3 at most N armed plans per name per day.

Reads `data/cache/rules_audit_plans.pkl` (built by scripts/rules_audit.py)
and the day bar cache, adds `range5` and `plan_index` to every plan, then
runs B and the variants in modes A and C.

    python3 scripts/rules_audit_open.py [--procs 4]
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from collections import defaultdict
from datetime import datetime, time as dtime, timezone
from multiprocessing import Pool
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1] / "src")]
import backtest_history as H  # noqa: E402
import rules_audit as RA  # noqa: E402

K = 46
ALPHA = 0.05 / K
DECIDING = [
    ("O1 stop vs range", "stop >= 1.0x recent 1-min range", {"range_k": 1.0}),
    ("O2 opening lockout", "no fill 09:30-09:31", {"lockout": "09:32"}),
    ("O3 plans per name", "at most 3 a day", {"max_index": 3}),
]
REPORTED = [
    ("O1 stop vs range", "0.5x", {"range_k": 0.5}),
    ("O1 stop vs range", "1.5x", {"range_k": 1.5}),
    ("O2 opening lockout", "1 minute", {"lockout": "09:31"}),
    ("O2 opening lockout", "5 minutes", {"lockout": "09:35"}),
    ("O3 plans per name", "1 a day", {"max_index": 1}),
    ("O3 plans per name", "2 a day", {"max_index": 2}),
    ("O3 plans per name", "5 a day", {"max_index": 5}),
    ("O1+O2+O3", "all three", {"range_k": 1.0, "lockout": "09:32", "max_index": 3}),
]


def _ranges(args):
    """{(sym, arm): mean high-low of the 5 completed bars before the trigger bar}."""
    day, wanted, cache = args
    f = Path(cache) / f"{day}.json"
    if not f.exists():
        return {}
    bars = json.loads(f.read_text())
    out = {}
    for sym, arms in wanted.items():
        rows = [r for r in H.to_rows(bars.get(sym) or []) if dtime(4, 0) <= r[0].time() < dtime(16, 0)]
        at = {int(r[0].timestamp()): i for i, r in enumerate(rows)}
        for arm in arms:
            i = at.get(arm)
            if i is None or i < 5:
                continue
            prev = rows[i - 5:i]
            out[(sym, arm)] = sum(h - l for _, _, h, l, _, _ in prev) / 5.0
    return out


def enrich(plans: list[dict], cache: str, procs: int) -> None:
    by_sd = defaultdict(list)
    for p in plans:
        by_sd[(p["sym"], p["day"])].append(p)
    for ps in by_sd.values():
        for k, p in enumerate(sorted(ps, key=lambda x: x["arm"]), 1):
            p["plan_index"] = k
    wanted = defaultdict(lambda: defaultdict(list))
    for p in plans:
        wanted[p["day"]][p["sym"]].append(p["arm"])
    jobs = [(d, dict(w), cache) for d, w in wanted.items()]
    rng = {}
    with Pool(procs) as pool:
        for part in pool.imap(_ranges, jobs, chunksize=16):
            rng.update(part)
    for p in plans:
        p["range5"] = rng.get((p["sym"], p["arm"]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default=str(H.CACHE))
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--json", default=str(RA.ROOT / "research" / "paper-exercise" / "reports" / "rules_audit_open_results.json"))
    args = ap.parse_args(argv)
    RA.E.COST_MODEL = "live"
    plans = pickle.loads(RA.PLANS_CACHE.read_bytes())
    enrich(plans, args.cache, args.procs)
    have = sum(1 for p in plans if p.get("range5") is not None)
    by_day = defaultdict(list)
    for p in plans:
        by_day[p["day"]].append(p)
    print(f"{len(plans)} plans on {len(by_day)} sessions ({min(by_day)}..{max(by_day)}) · range5 known for {have}"
          f" · alpha 0.05/{K} · costs live ($40 / $2,000)")
    res = {"K": K, "alpha": ALPHA, "modes": {}}
    verdicts = defaultdict(dict)
    hdr = (f"  {'rule · variant':<48}{'tr n':>6}{'tr R':>8}{'te n':>6}{'te R':>8}{'te tot':>9}{'te DD':>7}"
           f"  yrs 2024/25/26        lb      verdict")
    for mode in ("A", "C"):
        bc = dict(RA.BASE, mode=mode)
        base = RA.portfolio(by_day, bc)
        b = RA.split_stats(base)
        print(f"\n=== MODE {mode} ===")
        print(hdr)

        def row(name, s, lb=None, v=""):
            tr, te = s["train"], s["test"]
            yrs = "/".join(f"{s['years'][y].get('mean', float('nan')):+.2f}" for y in ("2024", "2025", "2026"))
            lbs = f"{lb:+.3f}" if lb is not None else "      "
            return (f"  {name:<48}{tr.get('n', 0):>6}{tr.get('mean', float('nan')):>+8.3f}{te.get('n', 0):>6}"
                    f"{te.get('mean', float('nan')):>+8.3f}{te.get('total', 0):>+9.1f}{te.get('max_dd', 0):>7.1f}"
                    f"  {yrs:<20}{lbs:>8}  {v}")
        print(row("B (live rules)", b))
        rows = []
        for deciding, group in ((True, DECIDING), (False, REPORTED)):
            if not deciding:
                print("  -- reported, never deciding --")
            for g, name, over in group:
                tr = RA.portfolio(by_day, dict(bc, **over))
                s_ = RA.split_stats(tr)
                lb = RA.paired_lb(tr, base, alpha=ALPHA)
                v, checks = RA.verdict(g, b, s_, lb)
                if deciding:
                    verdicts[(g, name)][mode] = v
                print(row(f"{g} · {name}", s_, lb, v if deciding else "(" + v + ")"), flush=True)
                rows.append({"group": g, "variant": name, "deciding": deciding, "stats": s_, "lb": lb,
                             "verdict": v, "checks": checks})
        res["modes"][mode] = {"baseline": b, "variants": rows}
    print("\n=== ADOPTION: must pass under BOTH A and C ===")
    res["pass_both"] = []
    for (g, name), d in verdicts.items():
        ok = all(d.get(m) == "ADOPT" for m in ("A", "C"))
        print(f"  {g} · {name:<36} A {d.get('A')}  C {d.get('C')}  -> {'PASSES BOTH' if ok else 'keep B'}")
        if ok:
            res["pass_both"].append([g, name])
    Path(args.json).write_text(json.dumps(res, indent=1, default=str))
    print(f"\nwritten {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
