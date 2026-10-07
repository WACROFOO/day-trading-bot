#!/usr/bin/env python3
"""BX — skip VWAP and still-rising for plans armed > 25 % off the high (addendum 2026-10-07)."""
from __future__ import annotations

import pickle
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

import backtest_recent as E  # noqa: E402
import rules_audit as RA  # noqa: E402

OUT = ROOT / "research" / "paper-exercise" / "reports" / "bounce_exemption_output.txt"


def exempt(p: dict, keep_rising: bool) -> dict:
    """A bounce plan with VWAP (and, unless keep_rising, still-rising) waived."""
    if p["fade"] <= RA.BASE["fade"]:
        return p
    q = dict(p, red=[x for x in p["red"] if x != "vwap"], red_prev=[x for x in p["red_prev"] if x != "vwap"])
    if not keep_rising:
        q["fade"] = q["fade_prev"] = 0.0
    q["bounce"] = True
    return q


def total(tr, lo=None, hi=None):
    return sum(t["net"] for t in tr if (lo is None or t["day"] >= lo) and (hi is None or t["day"] < hi))


def main() -> int:
    E.COST_MODEL = "live"
    lines = []

    def pr(s=""):
        print(s, flush=True); lines.append(s)
    plans = pickle.loads(RA.PLANS_CACHE.read_bytes())
    by = {"B": defaultdict(list), "BX": defaultdict(list), "BV": defaultdict(list)}
    for p in plans:
        by["B"][p["day"]].append(p)
        by["BX"][p["day"]].append(exempt(p, False))
        by["BV"][p["day"]].append(exempt(p, True))
    pr(f"addendum 2026-10-07 · {len(plans)} plans (rules_audit cache, 07:00-11:30) · costs live · bounce = > 25 % off the high")
    ok_all = {"BX": [], "BV": []}
    for mode in ("A", "C"):
        c = dict(RA.BASE, mode=mode)
        base = RA.portfolio(by["B"], c); sb = RA.split_stats(base)
        pr(f"\n=== reading {mode} ===")
        pr(f"  B   train n {sb['train']['n']} net {sb['train']['mean']:+.3f} total {total(base, hi=RA.SPLIT):+.1f} R · "
           f"holdout n {sb['test']['n']} net {sb['test']['mean']:+.3f} total {total(base, lo=RA.SPLIT):+.1f} R")
        for name in ("BX", "BV"):
            tr = RA.portfolio(by[name], c); sv = RA.split_stats(tr)
            lb = RA.paired_lb(tr, base, alpha=0.05)
            v, checks = RA.verdict(name, sb, sv, lb)
            checks["train total not worse"] = total(tr, hi=RA.SPLIT) >= total(base, hi=RA.SPLIT)
            checks["holdout total not worse"] = total(tr, lo=RA.SPLIT) >= total(base, lo=RA.SPLIT)
            ok = all(checks.values()); ok_all[name].append(ok)
            keys_b = {(t["day"], t["sym"], t["t"]) for t in base}
            added = [t for t in tr if (t["day"], t["sym"], t["t"]) not in keys_b]
            pr(f"  {name}  train n {sv['train']['n']} net {sv['train']['mean']:+.3f} total {total(tr, hi=RA.SPLIT):+.1f} R · "
               f"holdout n {sv['test']['n']} net {sv['test']['mean']:+.3f} total {total(tr, lo=RA.SPLIT):+.1f} R · lb {lb:+.3f}")
            if added:
                g = sum(t["gross"] for t in added) / len(added); n_ = sum(t["net"] for t in added) / len(added)
                pr(f"      trades it adds: n {len(added)} · gross {g:+.3f} · net {n_:+.3f} · "
                   f"won {sum(1 for t in added if t['net'] > 0) / len(added):.0%}")
            pr("      " + " · ".join(f"{'✓' if x else '✗'} {k}" for k, x in checks.items()) + f"  → {'PASS' if ok else 'keep B'}")
    pr("\nDECISION (both readings): " + " · ".join(f"{n} {'PASS → owner, built OFF' if all(v) else 'fails'}" for n, v in ok_all.items()))
    OUT.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
