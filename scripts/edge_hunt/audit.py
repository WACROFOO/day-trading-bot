#!/usr/bin/env python3
"""F2's universe audit (PREREGISTRATION.md §6 F2): the 09:30-gap universe
cannot see a name that ran pre-market and was no longer +10 % at the open.
On sampled sessions, names from the 2016-2026 gapper pool that traded +10 %
over their previous close at some pre-market minute ($2-20, 20-day dollar
volume >= $250k) but are missing from that day's universe are run through the
SAME configuration, and weighed against the in-universe trades of the same
sessions. The pool is an undercount (a name that never gapped at an open in
2016-2026 is not queried), so the correction this measures is a floor.

    python3 scripts/edge_hunt/audit.py --split trainvalid      # sessions before 2024
    python3 scripts/edge_hunt/audit.py --split holdout         # only after F2's opening
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))

from edge_hunt import costs as C  # noqa: E402
from edge_hunt import engine as G  # noqa: E402
from edge_hunt import families as FM  # noqa: E402
from edge_hunt import protocol as P  # noqa: E402
from edge_hunt.data import STORE, minute, split_of  # noqa: E402

ET = ZoneInfo("America/New_York")
FAM = "F2-premarket"


def bars_of(raw: list, day: str):
    noon = datetime.fromisoformat(f"{day}T12:00:00").replace(tzinfo=ET)
    off = int(noon.utcoffset().total_seconds() // 60)
    m, a = [], []
    for t, o, h, l, c, v in raw:
        mm = int(t[11:13]) * 60 + int(t[14:16]) + off - 240
        if 0 <= mm < 720:
            m.append(mm); a.append((o, h, l, c, v or 0))
    if not m:
        return None, None
    order = np.argsort(m, kind="stable")
    return np.array(m, np.int64)[order], np.array(a, float)[order]


def run_config(cfg: dict, m, a, pc, proxy, model="prereg"):
    """The F2 configuration on one symbol-day's bars; None if no trade."""
    w0, w1 = FM.F2_WINDOWS[cfg["window"]]
    o, h, l, c, v = (np.ascontiguousarray(a[:, j]) for j in range(5))
    if cfg["entry"] != "pmh":
        raise SystemExit("the audit implements the pre-market-high entry (the chosen one); extend it for 'pb'")
    arm, trig, stop, fk, fpx, capf = G.pmh_break(m, o, h, l, c, w0, w1, 3, 0.03, 5)
    if arm < 0:
        return None
    if cfg["sel"] == "gain>=30%" and not (c[arm] / pc - 1 >= 0.30):
        return None
    if cfg["sel"] in ("headline", "rvol>=3"):
        raise SystemExit(f"selection {cfg['sel']} needs features the audit does not fetch")
    rule = FM.F2_STOPS[cfg["stop"]]
    if rule[0] == "skip_pct" and (trig - stop) / trig * 100 < rule[1]:
        return None
    if rule[0] == "widen_pct":
        stop = min(stop, trig * (1 - rule[1] / 100))
    sp = FM.spec_of(cfg["exit"])
    r, orders, ke, why, st = G.simulate(m, o, h, l, c, fk, fpx, trig, stop, sp, capf == 0)
    dv = np.cumsum(c * v)

    def dv5(k):
        lo = np.searchsorted(m, m[k] - 5, side="right") - 1
        return dv[k] - (dv[lo] if lo >= 0 else 0.0)
    hs_in = proxy.spread(fpx, True, dv5(arm)) / 2
    ex_px = fpx + r * (trig - stop)
    hs_out = proxy.spread(ex_px, m[ke] < minute(9, 30), dv5(max(ke - 1, 0))) / 2
    cost = float(C.cost_r_vec([trig], [stop], [fpx], [ex_px], [orders], [st], [hs_in], [hs_out], model=model)[0])
    return {"gross": r, "net": r - cost, "fill_min": int(m[fk]), "exit_min": int(m[ke])}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=("trainvalid", "holdout"), required=True)
    ap.add_argument("--config", help="JSON config; default: F2's chosen configuration from the registry")
    args = ap.parse_args(argv)
    if args.split == "holdout" and P.opened(FAM) is None:
        raise SystemExit("F2's holdout is closed; the holdout audit runs only at its opening")
    if args.config:
        cfg = json.loads(args.config)
    else:
        led = P.opened(FAM)
        cfg = led["config"] if led else json.loads(Path(ROOT / "research/edge-hunt/results/f2_chosen.json").read_text())
    proxy = C.SpreadProxy()
    ctx = FM.Ctx(features=False)
    files = sorted((STORE / "pm_audit").glob("*.json"))
    days = [f.stem for f in files if (split_of(f.stem) == "holdout") == (args.split == "holdout")]
    miss, inside = [], []
    pool_n, miss_names = [], 0
    for d in days:
        z = json.loads((STORE / "pm_audit" / f"{d}.json").read_text())
        pool_n.append(z["pool"])
        for sym, info in z["missing"].items():
            miss_names += 1
            m, a = bars_of(info.get("bars") or [], d)
            if m is None or len(m) < 20:
                continue
            t = run_config(cfg, m, a, info["pc"], proxy)
            if t:
                miss.append({"day": d, "sym": sym, **t})
        for i in np.flatnonzero(ctx.sd["day"].to_numpy() == d):
            s, e = ctx.starts[i], ctx.ends[i]
            mm = ctx.m[s:e]; keep = mm < minute(11, 30)
            aa = np.column_stack([ctx.o[s:e], ctx.h[s:e], ctx.l[s:e], ctx.c[s:e], ctx.v[s:e]])[keep]
            t = run_config(cfg, mm[keep], aa, ctx.pc[i], proxy)
            if t:
                inside.append({"day": d, "sym": ctx.sd["sym"].iat[i], **t})
    mi, ins = pd.DataFrame(miss), pd.DataFrame(inside)
    print(f"F2 universe audit · {args.split} · {len(days)} sessions · config {json.dumps(cfg)}")
    print(f"  gapper pool queried per session ~{int(np.mean(pool_n)) if pool_n else 0} names · "
          f"missing names that ran +10 % pre-market: {miss_names}")
    for name, df in (("in the 09:30-gap universe", ins), ("MISSING from it", mi)):
        if df.empty:
            print(f"  {name:<28} no trades"); continue
        print(f"  {name:<28} trades {len(df):>4} · gross {df.gross.mean():+.3f} · net {df.net.mean():+.3f} · "
              f"win {np.mean(df.net > 0):.0%}")
    if not ins.empty:
        allp = pd.concat([ins, mi]) if not mi.empty else ins
        share = len(mi) / len(allp)
        print(f"  combined (plan level)        trades {len(allp):>4} · net {allp.net.mean():+.3f} · missing share {share:.0%}")
        out = {"split": args.split, "config": cfg, "sessions": len(days), "in_n": len(ins), "in_net": float(ins.net.mean()),
               "miss_n": len(mi), "miss_net": float(mi.net.mean()) if len(mi) else None,
               "combined_net": float(allp.net.mean()), "missing_share": share}
        (ROOT / "research" / "edge-hunt" / "results" / f"f2_audit_{args.split}.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
