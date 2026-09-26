#!/usr/bin/env python3
"""F3 — ten-second micro-pullbacks, on the tick subset.

Ticks (Alpaca SIP trades, 07:00-11:30 ET) → 10-second bars. The detector:
an impulse of >= X % inside the last six bars with >= 3 green; then 1-3 red
bars that retrace <= 50 % of it; while in that pullback, a buy stop at the
latest bar's high + 1c; stop under the pullback's low. Layer 2 (VWAP from
04:00, 9 EMA, MACD above signal and positive) and the $2-20 price gate read
COMPLETED one-minute bars only. Fills: A10 — a bar opening above the cap
rests at the cap and fills only if the price returns within three minutes.

    python3 scripts/edge_hunt/micro.py --stage search
    python3 scripts/edge_hunt/micro.py --stage holdout
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))

from edge_hunt import costs as C  # noqa: E402
from edge_hunt import engine as G  # noqa: E402
from edge_hunt import families as FM  # noqa: E402
from edge_hunt import protocol as P  # noqa: E402
from edge_hunt.data import ET, STORE, minute, split_of  # noqa: E402
from edge_hunt.engine import njit  # noqa: E402

SAMPLE = ROOT / "research" / "edge-hunt" / "results" / "f3_symdays.csv"   # the tick subset, fixed before the first F3 run
FAM = "F3-micro10s"
MIN_TRAIN_PLANS_F3 = 100      # the subset is 150 train symbol-days; fixed before the first F3 run
# Conditions that do not update a consolidated last sale (CTA/UTP): average-price, out-of-sequence,
# cash, next-day, seller's option, derivatively priced, contingent, prior reference, official open/close.
SKIP = set("WZUCNR479BGHPVMQ")


def ten_second_bars(path: Path, day: str) -> tuple[np.ndarray, np.ndarray]:
    """(fractional minutes since 04:00 ET, [o, h, l, c, v]) per 10-second bucket with trades.
    Cached next to the ticks as .npz."""
    npz = path.with_suffix(".10s.npz")
    if npz.exists():
        z = np.load(npz)
        return z["m"], z["a"]
    m, a = _ten_second_bars(path, day)
    np.savez(npz, m=m, a=a)
    return m, a


def _ten_second_bars(path: Path, day: str) -> tuple[np.ndarray, np.ndarray]:
    rows = json.loads(path.read_text())
    noon = datetime.fromisoformat(f"{day}T12:00:00").replace(tzinfo=ET)
    off = int(noon.utcoffset().total_seconds())                     # -14400 or -18000
    buckets: dict[int, list] = {}
    for t, p, s, conds in rows:
        if any(c in SKIP for c in (conds or [])):
            continue
        sec = int(t[11:13]) * 3600 + int(t[14:16]) * 60 + int(t[17:19]) + off - 4 * 3600
        b = sec // 10
        x = buckets.get(b)
        if x is None:
            buckets[b] = [p, p, p, p, s]
        else:
            x[1] = max(x[1], p); x[2] = min(x[2], p); x[3] = p; x[4] += s
    keys = sorted(buckets)
    m = np.array([k * 10 / 60 for k in keys], float)
    a = np.array([buckets[k] for k in keys], float) if keys else np.zeros((0, 5))
    return m, a


@njit(cache=True)
def minute_gates(m1, o1, h1, l1, c1, v1):
    """Per one-minute bar k: Layer 2 green at the CLOSE of bar k (VWAP from
    04:00 on typical price, EMA9, MACD 12/26/9 above signal and positive)."""
    n = len(c1)
    ok = np.zeros(n, np.bool_)
    sv = 0.0; spv = 0.0
    e9 = c1[0]; e12 = c1[0]; e26 = c1[0]; sig = 0.0
    a9, a12, a26, a_s = 2 / 10, 2 / 13, 2 / 27, 2 / 10
    for k in range(n):
        tp = (h1[k] + l1[k] + c1[k]) / 3
        sv += v1[k]; spv += tp * v1[k]
        vw = spv / sv if sv > 0 else c1[k]
        e9 = c1[k] if k == 0 else a9 * c1[k] + (1 - a9) * e9
        e12 = c1[k] if k == 0 else a12 * c1[k] + (1 - a12) * e12
        e26 = c1[k] if k == 0 else a26 * c1[k] + (1 - a26) * e26
        macd = e12 - e26
        sig = macd if k == 0 else a_s * macd + (1 - a_s) * sig
        ok[k] = c1[k] > vw and c1[k] > e9 and macd > sig and macd > 0
    return ok


@njit(cache=True)
def detect(m, o, h, l, c, gate_min, gate_ok, x_pct, t_end):
    """Micro-pullback plans on 10-second bars. gate_min/gate_ok: the one-
    minute bars' minute stamps and Layer 2 verdicts; a 10-second bar at
    minute mm reads the last one-minute bar stamped < floor(mm). Returns
    rows (arm bar, trigger, stop, fill bar, fill price), one open trade at a
    time (the next arm waits for nothing but the previous fill: the
    portfolio enforces one position)."""
    n = len(o)
    out = np.full((n, 6), -1.0); q = 0
    imp_hi = -1.0; imp_lo = -1.0; reds = 0; pb_lo = 1e18; in_pb = False; since = 0
    g = 0
    for k in range(6, n - 1):
        if m[k] >= t_end:
            break
        # impulse over the last six bars ending at k
        hi = -1.0; lo = 1e18; greens = 0
        for j in range(k - 5, k + 1):
            hi = max(hi, h[j]); lo = min(lo, l[j])
            if c[j] > o[j]:
                greens += 1
        if not in_pb and lo > 0 and (hi - lo) / lo >= x_pct and greens >= 3 and h[k] >= hi:
            imp_hi = hi; imp_lo = lo; in_pb = True; reds = 0; pb_lo = 1e18; since = 0
            continue
        if not in_pb:
            continue
        since += 1
        if c[k] < o[k]:
            reds += 1
        pb_lo = min(pb_lo, l[k])
        if reds > 3 or since > 6 or pb_lo < imp_hi - 0.5 * (imp_hi - imp_lo) or h[k] > imp_hi:
            in_pb = False
            continue
        if reds < 1:
            continue
        # gates from completed one-minute bars
        while g + 1 < len(gate_min) and gate_min[g + 1] < np.floor(m[k]):
            g += 1
        if len(gate_min) == 0 or gate_min[g] >= np.floor(m[k]) or not gate_ok[g]:
            continue
        trig = h[k] + 0.01
        stop = pb_lo - 0.01
        if trig < 2.0 or trig > 20.0 or stop <= 0 or stop >= trig:
            continue
        nxt = k + 1
        if h[nxt] < trig:
            continue
        cap = trig + max(0.01, trig * 0.003)
        fk = -1; fpx = 0.0; capf = 0
        if o[nxt] > cap:
            for j in range(nxt, n):
                if m[j] - m[k] > 3.0:
                    break
                if l[j] <= cap:
                    fk = j; fpx = o[j] if (j > nxt and o[j] <= cap) else cap; capf = 1
                    break
        elif o[nxt] > trig:
            fk = nxt; fpx = o[nxt]
        else:
            fk = nxt; fpx = trig
        in_pb = False
        if fk < 0:
            continue
        out[q, 0] = k; out[q, 1] = trig; out[q, 2] = stop; out[q, 3] = fk; out[q, 4] = fpx; out[q, 5] = capf; q += 1
    return out[:q]


def load_subset():
    s = pd.read_csv(SAMPLE)
    return s


def build(ctx: FM.Ctx, x_pct: float) -> pd.DataFrame:
    sub = load_subset()
    key = {(d, sy): i for i, (d, sy) in enumerate(zip(ctx.sd["day"], ctx.sd["sym"]))}
    rows = []
    for r in sub.itertuples(index=False):
        f = STORE / "trades" / f"{r.day}_{r.sym}.json"
        sid = key.get((r.day, r.sym))
        if not f.exists() or sid is None:
            continue
        m, a = ten_second_bars(f, r.day)
        if len(m) < 30:
            continue
        s, e = ctx.starts[sid], ctx.ends[sid]
        gm = ctx.m[s:e].astype(float)
        gok = minute_gates(gm, ctx.o[s:e], ctx.h[s:e], ctx.l[s:e], ctx.c[s:e], ctx.v[s:e])
        det = detect(m, a[:, 0].copy(), a[:, 1].copy(), a[:, 2].copy(), a[:, 3].copy(), gm, gok, x_pct,
                     float(minute(11, 20)))
        for arm, trig, stop, fk, fpx, capf in det:
            rows.append({"sid": sid, "day": r.day, "sym": r.sym, "arm_k": int(arm), "k0": int(fk), "high_ok": 1 - int(capf),
                         "plan_min": int(np.floor(m[int(arm)])), "fill_min": float(m[int(fk)]),
                         "entry": trig, "stop": stop, "fill": fpx,
                         "window": "pre-market" if m[int(arm)] < minute(9, 30) else "regular"})
    d = pd.DataFrame(rows)
    if not d.empty:
        d["split"] = d["day"].map(split_of)
    return d


class Ticks:
    """10-second bar arrays for the subset, concatenated like the store."""

    def __init__(self, ctx: FM.Ctx):
        sub = load_subset()
        key = {(d, sy): i for i, (d, sy) in enumerate(zip(ctx.sd["day"], ctx.sd["sym"]))}
        ms, arrs, self.pos = [], [], {}
        p = 0
        for r in sub.itertuples(index=False):
            f = STORE / "trades" / f"{r.day}_{r.sym}.json"
            sid = key.get((r.day, r.sym))
            if not f.exists() or sid is None:
                continue
            m, a = ten_second_bars(f, r.day)
            if len(m) < 30:
                continue
            self.pos[sid] = (p, p + len(m)); ms.append(m); arrs.append(a); p += len(m)
        self.m = np.concatenate(ms); a = np.concatenate(arrs)
        self.o, self.h, self.l, self.c = (np.ascontiguousarray(a[:, j]) for j in range(4))


def trades(ctx: FM.Ctx, tk: Ticks, d: pd.DataFrame, stop_rule, sp, plan="fixed") -> pd.DataFrame:
    if d.empty:
        return d
    entry = d["entry"].to_numpy(float); stop = d["stop"].to_numpy(float).copy()
    keep = np.ones(len(d), bool)
    if stop_rule[0] == "skip_pct":
        keep = (entry - stop) / entry * 100 >= stop_rule[1]
    d = d[keep]; entry = entry[keep]; stop = stop[keep]
    sids = d["sid"].to_numpy(np.int64)
    st = np.array([tk.pos[s][0] for s in sids], np.int64); en = np.array([tk.pos[s][1] for s in sids], np.int64)
    R, orders, kex, why, sside = G.simulate_many(tk.m, tk.o, tk.h, tk.l, tk.c, st, en, d["k0"].to_numpy(np.int64),
                                                 d["fill"].to_numpy(float), entry, stop, sp,
                                                 d["high_ok"].to_numpy(np.int64))
    exit_min = tk.m[kex]
    fill = d["fill"].to_numpy(float); exit_px = fill + R * (entry - stop)
    pm_in = d["window"].to_numpy() == "pre-market"
    hs_in = ctx.proxy.spread_vec(fill, pm_in, ctx.dv5(sids, d["plan_min"].to_numpy())) / 2
    hs_out = ctx.proxy.spread_vec(exit_px, exit_min < minute(9, 30), ctx.dv5(sids, np.floor(exit_min).astype(int) - 1)) / 2
    cost = C.cost_r_vec(entry, stop, fill, exit_px, orders, sside, hs_in, hs_out, plan, model=FM.COST_MODEL)
    out = d.assign(entry_used=entry, stop_used=stop, gross=R, cost=cost, net=R - cost, exit_min=exit_min,
                   orders=orders, why=why, stop_side=sside)
    return out[~np.isnan(out["gross"].to_numpy())]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", choices=("search", "holdout"), default="search")
    args = ap.parse_args(argv)
    ctx = FM.Ctx(features=False)
    tk = Ticks(ctx)
    plans = {x: build(ctx, x / 100) for x in (2, 4)}
    stops = {"none": ("none",), "skip<1%": ("skip_pct", 1.0), "skip<2%": ("skip_pct", 2.0)}

    def ev(cfg, split, plan="fixed"):
        return trades(ctx, tk, ctx.frame(plans[cfg["x"]], split, FAM), stops[cfg["stop"]], FM.spec_of(cfg["exit"]), plan)

    configs = [{"x": x, "stop": s, "exit": e} for x in (2, 4) for s in stops for e in ("trail1", "fixed2")]
    FM.MIN_TRAIN_PLANS = MIN_TRAIN_PLANS_F3
    res = FM.choose(FAM, configs, ev)
    FM.print_search(FAM, res)
    # beside it: the one-minute desk plans on the same symbol-days
    subs = set(tk.pos)
    base = FM.base_rows(ctx)
    for split in ("train", "valid"):
        one = ctx.trades(ctx.frame(base[base["sid"].isin(subs)], split, FAM), ("none",), FM.spec_of("trail1"))
        print(f"  one-minute desk plans on the same {split} symbol-days: {FM.stats(one)}")
    if args.stage == "holdout":
        def windows_fn(port):
            return pd.Series([(float(minute(7, 0)), float(minute(11, 20)))] * len(port))
        out = FM.open_and_read(ctx, FAM, res, ev, windows_fn=windows_fn,
                               spec_fn=lambda cfg: FM.spec_of(cfg["exit"]))
        print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
