"""Audit of their_rules.py, read-only.

1. Fill-model equivalence: the hook-side A10 replication (gap_miss=False plus
   the hook) against the engine's own gap_miss=True, plan by plan.
2. Spike exits: their R distribution.
3. Robustness of the two leads on our live rules: per day.
4. The same comparisons under the "old" cost model ($20 risk, 1 c a side).

Usage (from the repo root):  python3 research/reddit-bot-rules-2026-10-12/audit.py
"""
import collections
import sys
from datetime import time as dtime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import their_rules as T  # noqa: E402  (reads sys.argv[1] as the repo root)

E = T.E


def native(uni):
    E.PM_START, E.CUTOFF, E.FLAT = T.REGIMES["bot"]
    E.COST_MODEL = "live"
    out = {}
    for d in sorted(uni):
        bars = T.bars_for_day(d)
        for sym in sorted(uni[d]):
            rows = [r for r in bars.get(sym, []) if dtime(4, 0) <= r[0].time() < dtime(16, 0)]
            if len(rows) < 40:
                continue
            for p in E.plans_for_day(sym, rows, uni[d][sym]["prev"] or 0, desk_vwap=True, gap_miss=True):
                out[(d, sym, p["ts"])] = p
    return out


def main():
    uni = T.universe()
    mine, _ = T.build("bot", uni)
    nat = native(uni)
    n_same = n_diff = n_fill_mismatch = 0
    worst = []
    for p in mine:
        k = (p["day"], p["sym"], p["ts"])
        q = nat.get(k)
        if q is None:
            n_diff += 1
            continue
        a = p["v"]["a10"] if p["touched"] and p["v"] else None
        filled_native = q["touched"]
        if (a is not None) != filled_native:
            n_fill_mismatch += 1
            worst.append(("fill", k, a is not None, filled_native))
            continue
        if a is None:
            n_same += 1
            continue
        ok = True
        for v in ("fixed", "trail", "be"):
            if abs(a[v]["r"] - q[v]) > 1e-6 or abs(a[v]["net"] - q[v + "_net"]) > 1e-6:
                ok = False
                worst.append((v, k, a[v]["r"], q[v], a[v]["net"], q[v + "_net"]))
        n_same += ok
        n_diff += not ok
    print(f"1 · equivalence: {len(mine)} plans · identical {n_same} · differ {n_diff} · fill set mismatch {n_fill_mismatch}")
    for w in worst[:8]:
        print("   ", w)

    print("\n2 · spike exits (their exit), every fill and our live rules")
    for name, allowed in (("every fill", lambda p: True), ("our live rules", T.ours_live)):
        rs = [p["v"]["a10"]["theirs"]["r"] for p in mine
              if p["touched"] and p["v"] and p["v"]["a10"] and allowed(p) and p["v"]["a10"]["theirs"]["why"] == "spike"]
        if rs:
            rs.sort()
            print(f"   {name:<16} n={len(rs):4d}  mean {sum(rs) / len(rs):+.2f} R  median {rs[len(rs) // 2]:+.2f}  "
                  f"min {rs[0]:+.2f}  max {rs[-1]:+.2f}")
        why = collections.Counter(p["v"]["a10"]["theirs"]["why"] for p in mine
                                  if p["touched"] and p["v"] and p["v"]["a10"] and allowed(p))
        print(f"   {'':<16} exits: {dict(why)}")

    print("\n3 · per-day: fixed 2R vs trail 1R on our live rules, portfolio with the risk lock")
    fx = T.portfolio(mine, T.ours_live, ex="fixed", ours_risk=True)
    tr = T.portfolio(mine, T.ours_live, ex="trail", ours_risk=True)
    print("   periods (fixed):", fx, "\n   periods (trail):", tr)
    by_f, by_t = collections.defaultdict(float), collections.defaultdict(float)
    for p, net, _ in T.trades(mine, T.ours_live, ex="fixed"):
        by_f[p["day"]] += net
    for p, net, _ in T.trades(mine, T.ours_live, ex="trail"):
        by_t[p["day"]] += net
    days = sorted(set(by_f) | set(by_t))
    better = sum(1 for d in days if by_f[d] > by_t[d] + 1e-9)
    worse = sum(1 for d in days if by_f[d] < by_t[d] - 1e-9)
    print(f"   plan level by day: fixed better on {better} days, worse on {worse}, equal on {len(days) - better - worse}")
    for d in days:
        print(f"     {d}  fixed {by_f[d]:+6.2f}  trail {by_t[d]:+6.2f}")

    print("\n4 · the same comparisons under the OLD cost model ($20 risk, 1 cent a side)")
    E.COST_MODEL = "old"
    for p in mine:
        if not (p["touched"] and p["v"]):
            continue
        for fm in ("a10", "chase2"):
            t = p["v"].get(fm)
            if not t:
                continue
            for v in ("fixed", "trail", "be", "theirs", "lock", "spike"):
                c = E.cost_r(p["entry"], p["stop"], t[v]["why"] in T.MARKETABLE, pm=p["pm"], dv5=p["dv5"])
                t[v]["net"] = round(t[v]["r"] - c, 3)
    for ex in ("trail", "fixed", "be", "theirs"):
        T.line(f"ours as live · {ex} (old costs)", mine, T.ours_live, ex=ex)
    al = T.after_loss_filter(mine, T.ours_live, "a10", "trail")
    T.line("ours + done after a loss · trail (old costs)", mine, lambda p: T.ours_live(p) and al(p))
    T.pline("portfolio ours · trail (old costs)", mine, T.ours_live, ours_risk=True)
    T.pline("portfolio ours · fixed 2R (old costs)", mine, T.ours_live, ours_risk=True, ex="fixed")
    T.pline("portfolio ours + after loss · trail (old)", mine, T.ours_live, ours_risk=True, after_loss=True)


if __name__ == "__main__":
    main()
