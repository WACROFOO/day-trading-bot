#!/usr/bin/env python3
"""F7 — the leader breakout (research/edge-hunt/PREREGISTRATION.md, addendum
2026-09-28): at each minute, the #1 gainer among names up >= 10 % ($1-20,
>= 50k shares since 04:00, bars <= t only); a buy stop-limit at its high of day
+ 1c; his scalp-style exits; one position at a time, one trade per symbol-day.

    python3 scripts/edge_hunt/leader.py --stage search
    python3 scripts/edge_hunt/leader.py --stage holdout
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from edge_hunt import costs as C  # noqa: E402
from edge_hunt import engine as G  # noqa: E402
from edge_hunt import protocol as P  # noqa: E402
from edge_hunt.data import minute  # noqa: E402
from edge_hunt.pit import Pit  # noqa: E402

FAM = "F7-leader"
WINDOWS = {"07-09:30": (minute(7, 0), minute(9, 30)), "09:30-11": (minute(9, 30), minute(11, 0)),
           "07-11": (minute(7, 0), minute(11, 0))}
STOPS = ("bar", "pct3")
EXITS = {"fixed1": dict(target=1.0), "trail1": dict(trail=1.0), "bail2_trail1": dict(trail=1.0, time_stop=2)}
PROXY = C.SpreadProxy()


def leaders(Pt: Pit, day: str):
    """Per minute 0..479: (symday index of the leader or -1, its running high)."""
    idx = Pt.by_day[day]
    pc = Pt.sd["prev_close"].to_numpy()[idx]
    cs, cv, hh = [], [], []
    for i in idx:
        c, v, _, h = Pt.grid(int(i))
        cs.append(c); cv.append(v); hh.append(h)
    c, v, h = np.array(cs), np.array(cv), np.array(hh)
    gain = c / pc[:, None] - 1
    ok = (gain >= 0.10) & (c >= 1) & (c <= 20) & (v >= 5e4)
    g = np.where(ok, gain, -np.inf)
    best = np.argmax(g, axis=0)
    has = np.isfinite(g[best, np.arange(g.shape[1])])
    lead = np.where(has, idx[best], -1)
    return lead, h[best, np.arange(g.shape[1])]


def dv5(m, c, v, k):
    lo = np.searchsorted(m, m[k] - 5, side="left")
    return float((c[lo:k] * v[lo:k]).sum())


def run_day(Pt: Pit, day: str, lead, hod, cfg: dict, model: str = "prereg") -> list[dict]:
    w0, w1 = WINDOWS[cfg["window"]]
    sp = G.spec(flat_min=minute(11, 30), **EXITS[cfg["exit"]])
    out, busy, done = [], -1, set()
    for t in range(w0, w1):
        i = int(lead[t])
        if i < 0 or t <= busy or i in done:
            continue
        s, e = Pt.starts[i], Pt.ends[i]
        m = Pt.minute[s:e]
        k_bar = int(np.searchsorted(m, t, side="right")) - 1
        if k_bar < 0 or m[k_bar] != t:
            continue
        trig = float(hod[t]) + 0.01
        stop = float(Pt.l[s + k_bar]) - 0.01 if cfg["stop"] == "bar" else trig * 0.97
        if not (0 < stop < trig) or trig > 20.3:
            continue
        o, h, l, c, v = (Pt.o[s:e], Pt.h[s:e], Pt.l[s:e], Pt.c[s:e], Pt.v[s:e])
        fk, fpx, capf = G.stop_limit_fill(m, o, h, l, k_bar + 1, trig, 3, 0.003, 0.01)
        if fk < 0:
            continue
        r, n_o, ke, why, st = G.simulate(m, o, h, l, c, fk, fpx, trig, stop, sp, capf == 0)
        px_out = fpx + r * (trig - stop)
        hs_in = PROXY.spread(fpx, m[fk] < minute(9, 30), dv5(m, c, v, fk)) / 2
        hs_out = PROXY.spread(px_out, m[ke] < minute(9, 30), dv5(m, c, v, ke)) / 2
        cost = float(C.cost_r_vec([trig], [stop], [fpx], [px_out], [n_o], [st], [hs_in], [hs_out], model=model)[0])
        out.append({"day": day, "sid": i, "sym": Pt.sd["sym"].iat[i], "arm_min": t, "fill_min": int(m[fk]),
                    "exit_min": int(m[ke]), "entry": trig, "stop": stop, "fill": fpx, "gross": r, "cost": cost,
                    "net": r - cost, "stop_pct": (trig - stop) / trig})
        busy = int(m[ke]); done.add(i)
    return out


def run(Pt: Pit, days: list[str], cfgs: list[dict], cache: dict, model="prereg") -> dict:
    res = {json.dumps(c, sort_keys=True): [] for c in cfgs}
    for d in days:
        if d not in cache:
            cache[d] = leaders(Pt, d)
        lead, hod = cache[d]
        for c in cfgs:
            res[json.dumps(c, sort_keys=True)] += run_day(Pt, d, lead, hod, c, model)
    return {k: pd.DataFrame(v) for k, v in res.items()}


def random_diff(Pt: Pit, tr: pd.DataFrame, cfg: dict) -> np.ndarray:
    w0, w1 = WINDOWS[cfg["window"]]
    sp = G.spec(flat_min=minute(11, 30), **EXITS[cfg["exit"]])
    out = np.full(len(tr), np.nan)
    for j, r in enumerate(tr.itertuples()):
        s, e = Pt.starts[r.sid], Pt.ends[r.sid]
        m = Pt.minute[s:e]; o, h, l, c, v = (Pt.o[s:e], Pt.h[s:e], Pt.l[s:e], Pt.c[s:e], Pt.v[s:e])
        rr, oo, ss, ff, stp, kk, kx = G.random_entries(m, o, h, l, c, w0, w1, r.stop_pct, sp, 20, int(r.sid) % 100000 + r.arm_min)
        ok = np.flatnonzero(~np.isnan(rr))
        if not len(ok):
            continue
        nets = []
        for q in ok:
            px_out = ff[q] + rr[q] * (ff[q] - stp[q])
            hi = PROXY.spread(ff[q], m[kk[q]] < minute(9, 30), dv5(m, c, v, kk[q])) / 2
            ho = PROXY.spread(px_out, m[kx[q]] < minute(9, 30), dv5(m, c, v, kx[q])) / 2
            nets.append(rr[q] - float(C.cost_r_vec([ff[q]], [stp[q]], [ff[q]], [px_out], [oo[q]], [ss[q]], [hi], [ho])[0]))
        out[j] = r.net - float(np.mean(nets))
    return out


def summ(df):
    return P.summary(df["net"].to_numpy(float), df["day"].to_numpy()) | (
        {"gross": round(float(df["gross"].mean()), 4), "cost": round(float(df["cost"].mean()), 4)} if len(df) else {})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("search", "holdout"), default="search")
    args = ap.parse_args(argv)
    Pt = Pit()
    days = sorted(Pt.by_day)
    split = {d: ("train" if d <= "2022-12-31" else "valid" if d <= "2023-12-31" else "holdout") for d in days}
    cfgs = [{"window": w, "stop": s, "exit": x} for w in WINDOWS for s in STOPS for x in EXITS]
    assert len(cfgs) == 18
    cache: dict = {}
    tr = run(Pt, [d for d in days if split[d] == "train"], cfgs, cache)
    rows = [{"hash": P.config_hash(json.loads(k)), "config": json.loads(k), "train_port": summ(v)} for k, v in tr.items()]
    rows.sort(key=lambda r: r["train_port"].get("mean", -9) if r["train_port"].get("n", 0) >= 300 else -9, reverse=True)
    top = rows[:5]
    va = run(Pt, [d for d in days if split[d] == "valid"], [r["config"] for r in top], cache)
    for r in top:
        r["valid_port"] = summ(va[json.dumps(r["config"], sort_keys=True)])
    P.register(FAM, rows)
    print(f"{FAM} · {len(cfgs)} configurations")
    for r in rows:
        tp, vp = r["train_port"], r.get("valid_port", {})
        print(f"  {json.dumps(r['config']):<62} train {tp.get('mean', float('nan')):+.3f} ({tp.get('n', 0)}) gross {tp.get('gross', float('nan')):+.3f}"
              + (f" · valid {vp.get('mean', float('nan')):+.3f} ({vp.get('n', 0)})" if vp else ""))
    cands = [r for r in top if r.get("valid_port", {}).get("n", 0) >= 30]
    best = max(cands, key=lambda r: r["valid_port"]["mean"]) if cands else None
    if best is None or best["valid_port"]["mean"] <= 0:
        print("  validation gate NOT met — F7's holdout stays closed")
        return 0
    print(f"  chosen {best['hash']} {json.dumps(best['config'])} — positive on validation")
    if args.stage != "holdout":
        return 0
    P.open_holdout(FAM, best["config"], len(cfgs), best["train_port"], best["valid_port"])
    ho = run(Pt, [d for d in days if split[d] == "holdout"], [best["config"]], cache)[json.dumps(best["config"], sort_keys=True)]
    rd = random_diff(Pt, ho, best["config"])
    res = P.adoption(ho["net"].to_numpy(float), ho["day"].to_numpy(), rd)
    res["portfolio"] = summ(ho)
    for mdl in ("light", "old"):
        res["cost_" + mdl] = summ(run(Pt, [d for d in days if split[d] == "holdout"], [best["config"]], cache, mdl)[json.dumps(best["config"], sort_keys=True)])
    P.record_result(FAM, res)
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
