#!/usr/bin/env python3
"""Two tests preregistered as addendum 2026-10-03 (research/edge-hunt/PREREGISTRATION.md),
both from the reverse-engineering review of his trades (2026-10-02):

  L  the leader — is the bot's own pullback better on the minute's #1-2 gainer?
     (his entries were on the #1 gainer 57 % of the time: research/ross-trades/)
  P  the green pause — does letting a green lower-high candle start a pullback
     (the owner's "no visible pullback" case) improve the coded detector?

    python3 scripts/sel3_pause.py leader            # cached plans, ~minutes
    python3 scripts/sel3_pause.py pause [--procs 4] # rebuilds plans twice, ~an hour

Engine, costs and portfolio are `scripts/rules_audit.py` unchanged (rule set B,
$40 / $2,000, live costs). Train 2016-2022 decides, 2023 must agree in sign,
2024-2026 is reported only. Day-paired bootstrap, one-sided alpha 0.05 / 4.
"""
from __future__ import annotations

import argparse
import json
import pickle
import random
import sys
from collections import defaultdict
from datetime import datetime
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import backtest_history as H  # noqa: E402
import rules_audit as RA  # noqa: E402
from momentum_platform.pullback import FirstPullbackDetector  # noqa: E402

OUT = ROOT / "research" / "paper-exercise" / "reports"
ALPHA = 0.05 / 4
SPLITS = (("train 2016-22", "2016-01-01", "2023-01-01"), ("2023", "2023-01-01", "2024-01-01"),
          ("2024-26 (report only)", "2024-01-01", "2099-01-01"))
LEADER_MIN_GAIN, LEADER_MIN_VOL = 0.10, 50_000


# ------------------------------------------------------------------ shared
def day_paired_lb(var, ref, lo, hi, alpha=ALPHA, draws=20000, seed=20261003):
    days = sorted({t["day"] for t in var + ref if lo <= t["day"] < hi})
    if len(days) < 20:
        return float("nan"), float("nan")
    ix = {d: i for i, d in enumerate(days)}
    sv, nv, sr, nr = (np.zeros(len(days)) for _ in range(4))
    for t in var:
        if t["day"] in ix:
            sv[ix[t["day"]]] += t["net"]; nv[ix[t["day"]]] += 1
    for t in ref:
        if t["day"] in ix:
            sr[ix[t["day"]]] += t["net"]; nr[ix[t["day"]]] += 1
    pick = np.random.default_rng(seed).integers(0, len(days), size=(draws, len(days)))
    d = sv[pick].sum(1) / np.maximum(1, nv[pick].sum(1)) - sr[pick].sum(1) / np.maximum(1, nr[pick].sum(1))
    point = sv.sum() / max(1, nv.sum()) - sr.sum() / max(1, nr.sum())
    return float(point), float(np.quantile(d, alpha))


def summ(tr, lo, hi):
    x = [t for t in tr if lo <= t["day"] < hi]
    if not x:
        return {"n": 0}
    g, n = np.array([t["gross"] for t in x]), np.array([t["net"] for t in x])
    return {"n": len(x), "gross": round(float(g.mean()), 4), "net": round(float(n.mean()), 4),
            "win_gross": round(float((g > 0).mean()), 3)}


def by_day(plans):
    d = defaultdict(list)
    for p in plans:
        d[p["day"]].append(p)
    return d


def compare(name, var_plans, ref_plans, cfg, L, gross_bar=None):
    """Both modes; returns the decision line's ingredients."""
    res = {}
    for mode in ("A", "C"):
        c = dict(cfg, mode=mode)
        tv, tr_ = RA.portfolio(by_day(var_plans), c), RA.portfolio(by_day(ref_plans), c)
        res[mode] = {}
        for lab, lo, hi in SPLITS:
            sv, sr = summ(tv, lo, hi), summ(tr_, lo, hi)
            point, lb = day_paired_lb(tv, tr_, lo, hi)
            res[mode][lab] = {"variant": sv, "reference": sr, "diff_net": round(point, 4), "lb": round(lb, 4)}
            L.append(f"  mode {mode} · {lab:<22} variant {fmt(sv)}  |  reference {fmt(sr)}  |  diff net {point:+.3f} · lb {lb:+.3f}")
    tr_lab, v_lab = SPLITS[0][0], SPLITS[1][0]
    ok = all(res[m][tr_lab]["lb"] > 0 and res[m][v_lab]["diff_net"] > 0
             and (gross_bar is None or res[m][tr_lab]["variant"].get("gross", -9) >= gross_bar) for m in ("A", "C"))
    L.append(f"  DECISION {name}: {'CANDIDATE (build OFF, 200 prospective paper trades)' if ok else 'NOT a candidate'}")
    return res, ok


def fmt(s):
    return "n 0" if not s["n"] else f"n {s['n']:>5} gross {s['gross']:+.3f} net {s['net']:+.3f} win(gross) {100*s['win_gross']:.0f}%"


# ------------------------------------------------------------------ L: the leader
def _day_series(day, syms):
    f = H.CACHE / f"{day}.json"
    raw = json.loads(f.read_text()) if f.exists() else {}
    out = {}
    for s, pc in syms.items():
        rows = raw.get(s)
        if not rows or not pc:
            continue
        r = H.to_rows(rows)
        ts = np.array([int(x[0].timestamp()) for x in r])
        out[s] = (ts, np.array([x[4] for x in r]), np.cumsum([x[5] for x in r]), pc)
    return out


def leader_rank(series, sym, t):
    """Rank of `sym` by gain among qualifying names, bars stamped <= t; None if it does not qualify."""
    gains = {}
    for s, (ts, c, cv, pc) in series.items():
        i = int(np.searchsorted(ts, t, side="right")) - 1
        if i < 0:
            continue
        g = c[i] / pc - 1
        if g >= LEADER_MIN_GAIN and 1 <= c[i] <= 20 and cv[i] >= LEADER_MIN_VOL:
            gains[s] = g
    if sym not in gains:
        return None
    return 1 + sum(1 for s, g in gains.items() if g > gains[sym])


def cmd_leader(args) -> int:
    uni = H.load_universe(None, None)
    plans = pickle.loads(RA.PLANS_CACHE.read_bytes())
    cfg = dict(RA.BASE, start="09:30")
    rth = [p for p in plans if cfg["start"] <= p["t"] < cfg["end"]]
    need = by_day([p for p in rth if RA.passes(p, dict(cfg, mode="A")) or RA.passes(p, dict(cfg, mode="C"))])
    ranks = {}
    for k, (day, ps) in enumerate(sorted(need.items()), 1):
        ser = _day_series(day, uni.get(day, {}))
        for p in ps:
            ranks[(p["sym"], p["day"], p["arm"])] = leader_rank(ser, p["sym"], p["arm"])
        if k % 250 == 0:
            print(f"  ranked {k}/{len(need)} days", flush=True)
    for p in rth:
        p["leader_rank"] = ranks.get((p["sym"], p["day"], p["arm"]))
    lead = [p for p in rth if p["leader_rank"] is not None and p["leader_rank"] <= 2]
    L = [f"L — the leader (addendum 2026-10-03) · plans in 09:30-11:20 {len(rth)} · ranked (gate-passing) {len(ranks)}"
         f" · rank <= 2: {sum(1 for r in ranks.values() if r is not None and r <= 2)} · not qualifying: {sum(1 for r in ranks.values() if r is None)}",
         "  variant = B on plans ranked <= 2 by % gain; reference = B, same window; costs live $40/$2,000"]
    res, ok = compare("L", lead, rth, cfg, L, gross_bar=0.17)
    rank_of = {(p["sym"], p["day"], p["t"]): p["leader_rank"] for p in rth}
    bd = by_day(rth)
    for mode in ("A", "C"):
        tr = RA.portfolio(bd, dict(cfg, mode=mode))
        for lab, lo, hi in SPLITS:
            cut = defaultdict(list)
            for t in tr:
                if lo <= t["day"] < hi:
                    r = rank_of.get((t["sym"], t["day"], t["t"]))
                    cut["rank 1" if r == 1 else "rank 2" if r == 2 else "rank 3-5" if r and r <= 5 else "rank 6+" if r else "not qualifying"].append(t)
            L.append(f"  mode {mode} · {lab} · reference trades by rank: " + " · ".join(
                f"{k} n {len(v)} gross {np.mean([x['gross'] for x in v]):+.3f}" for k, v in sorted(cut.items())))
    print("\n".join(L))
    (OUT / "sel3_leader_output.txt").write_text("\n".join(L) + "\n")
    (OUT / "sel3_leader_results.json").write_text(json.dumps({"decision": ok, "res": res}, indent=1))
    return 0


# ------------------------------------------------------------------ P: the green pause
class PauseDetector(FirstPullbackDetector):
    """The impulse continues only on a green bar that makes a new impulse high."""

    def _green(self, bar):
        if bar.close <= bar.open:
            return False
        imp = self._w.impulse_bars
        return (not imp) or bar.high > max(b.high for b in imp)


def _job(a):
    day, syms, cache, which = a
    RA.FirstPullbackDetector = PauseDetector if which == "pause" else FirstPullbackDetector
    return RA.day_job((day, syms, cache))


def cmd_pause(args) -> int:
    uni = H.load_universe(None, None)
    probe = set(random.Random(20261002).sample(sorted(uni), 400))
    days = [d for d in sorted(uni) if d not in probe]
    built = {}
    for which in ("coded", "pause"):
        out = []
        with Pool(args.procs) as pool:
            for k, ps in enumerate(pool.imap(_job, [(d, uni[d], str(H.CACHE), which) for d in days], chunksize=8), 1):
                out += ps
                if k % 250 == 0:
                    print(f"  {which} {k}/{len(days)} sessions · {len(out)} plans", flush=True)
        built[which] = out
    key = lambda p: (p["sym"], p["day"], p["arm"], p["entry"], p["stop"])        # noqa: E731
    coded_keys = {key(p) for p in built["coded"]}
    only = [p for p in built["pause"] if key(p) not in coded_keys]
    cfg = dict(RA.BASE)
    L = [f"P — the green pause (addendum 2026-10-03) · sessions {len(days)} (400 probe days excluded) · plans coded "
         f"{len(built['coded'])} · pause {len(built['pause'])} · armed only by the pause {len(only)}",
         "  variant = B on the pause detector's plans; reference = B on the coded detector's plans; 07:00-11:20"]
    res, ok = compare("P", built["pause"], built["coded"], cfg, L)
    for mode in ("A", "C"):
        c = dict(cfg, mode=mode)
        g = [p["out"][(mode, "base")][2] for p in only if RA.passes(p, c) and p["out"].get((mode, "base"))]
        net = [p["out"][(mode, "base")][2] - RA.cost_live(p["entry"], p["stop"], p["out"][(mode, "base")][3], p["pm"], p["dv5"])
               for p in only if RA.passes(p, c) and p["out"].get((mode, "base"))]
        L.append(f"  mode {mode} · plans only the pause arms, gate-passing and filled (all years, no portfolio): n {len(g)} · "
                 f"gross {np.mean(g) if g else float('nan'):+.3f} · net {np.mean(net) if net else float('nan'):+.3f}")
    print("\n".join(L))
    (OUT / "sel3_pause_output.txt").write_text("\n".join(L) + "\n")
    (OUT / "sel3_pause_results.json").write_text(json.dumps({"decision": ok, "res": res}, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("leader")
    p = sub.add_parser("pause"); p.add_argument("--procs", type=int, default=4)
    a = ap.parse_args(argv)
    return {"leader": cmd_leader, "pause": cmd_pause}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
