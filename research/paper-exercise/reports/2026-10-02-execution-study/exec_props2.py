#!/usr/bin/env python3
"""Addendum to exec_props.py: tails of the post-trigger drift, the STP LMT downside cases, and the
cost components by session with the off-market-print exits removed. Cache only, repo untouched."""
from __future__ import annotations

import pickle
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exec_props as EP  # noqa: E402
CD, RA, TR = EP.CD, EP.RA, EP.TR


def main():
    plans = pickle.loads(RA.PLANS_CACHE.read_bytes())
    done = pickle.loads(TR.OUTCOMES.read_bytes())
    gate = [p for p in plans if RA.passes(p, RA.BASE)]
    filled = [p for p in gate if (p["sym"], p["arm"]) in done and (done[(p["sym"], p["arm"])] or {}).get("filled")]
    slim = [{k: p[k] for k in ("sym", "day", "arm", "entry", "stop")} for p in filled]
    with Pool(4) as pool:
        R = dict(pool.imap_unordered(EP.work, slim, chunksize=8))
    rows = []
    for p in filled:
        key = (p["sym"], p["arm"])
        o, r = done[key], R.get(key)
        if r is None or o.get("spread_in") is None or (o["stopish"] and o.get("spread_out") is None):
            continue
        out = r["out"]
        e, s = p["entry"], p["stop"]
        rps = e - s
        sh = max(1, min(int(40 // rps), int(2000 // e)))
        unit = sh * rps
        flag = out.get("med20") is not None and out["med20"] >= out["level"] and o["exit"] < out["med20"] * 0.97
        st = o["stopish"]
        comp = {
            "comm": (CD.comm_fixed(sh, o["fill"]) + CD.comm_fixed(sh, o["exit"])) / unit,
            "sp_in": sh * o["spread_in"] / 2 / unit,
            "slip_in": sh * (o["fill"] - e) / unit,
            "sp_out": (sh * o["spread_out"] / 2 / unit) if st else 0.0,
            "slip_out": (sh * (out["level"] - o["exit"]) / unit) if st else 0.0,
        }
        comp["total"] = sum(comp.values())
        rows.append(dict(o=o, r=r, out=out, rps=rps, sh=sh, flag=flag, comp=comp,
                         sess="pm" if CD.et_hm(o["t_in"]) < "09:30" else "rth"))
    print(f"analysed {len(rows)}")

    print("\n==== cost components by session, off-market-flagged exits removed (mean R/trade)")
    for sess in ("pm", "rth"):
        for lab, sub in (("all", [x for x in rows if x["sess"] == sess]),
                         ("flag removed", [x for x in rows if x["sess"] == sess and not x["flag"]])):
            line = f"  {sess:<4}{lab:<14} n {len(sub):>4}"
            for c in ("comm", "sp_in", "slip_in", "sp_out", "slip_out", "total"):
                line += f" · {c} {np.mean([x['comp'][c] for x in sub]):.3f}"
            print(line)

    print("\n==== drift tails, flag removed: (exit print - last print at t+D)/rps; POSITIVE = acting later sells lower")
    for sess in ("pm", "rth"):
        for d in (4, 8, 17.5):
            v = np.array([(x["o"]["exit"] - x["r"]["px"][d]) / x["rps"] for x in rows
                          if x["o"]["stopish"] and not x["flag"] and x["sess"] == sess and x["r"]["px"].get(d) is not None])
            print(f"  {sess:<4} D={d:>4}s n {len(v)} · share >0 {np.mean(v > 1e-9) * 100:.1f}% · p75 {np.quantile(v, .75):+.3f}"
                  f" · p90 {np.quantile(v, .9):+.3f} · p95 {np.quantile(v, .95):+.3f} · p99 {np.quantile(v, .99):+.3f}"
                  f" · mean of positive part {np.mean(np.clip(v, 0, None)):+.4f}")
    print("  (bid-ask bounce: the trigger print is usually at the bid, a later print may be at the ask, so the")
    print("   mean understates the cost of delay by up to half a spread; the positive-part mean is an upper bound)")
    sp = np.array([x["o"]["spread_out"] / 2 / x["rps"] for x in rows if x["o"]["stopish"] and not x["flag"]])
    print(f"  half spread at the exit, same trades: mean {sp.mean():.3f} R median {np.median(sp):.3f}")


if __name__ == "__main__":
    main()
