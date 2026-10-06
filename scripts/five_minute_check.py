#!/usr/bin/env python3
"""Diagnostic for addendum 2026-10-06b — deciding nothing, written after the run.

E1's random-entry baseline read +0.405 R gross a trade (train, mode A) while E1
itself read -0.028. Before that gap is reported as a finding, this checks it is
not a defect in `five_minute.random_entries`:

  1. the same baseline around B's trades (same windows of the same symbol-days);
  2. the baseline with no conditioning at all: random symbol-days of the
     universe, random bars of each window, stops at 3 % and 5 %;
  3. E1's baseline split by window, and the baseline drawn only from bars
     BEFORE the E1 order (what being long earlier in the same window earned).

    python3 scripts/five_minute_check.py
"""
from __future__ import annotations

import json
import pickle
import random
import sys
from collections import defaultdict
from datetime import time as dtime
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

import backtest_history as H  # noqa: E402
import backtest_recent as E  # noqa: E402
import five_minute as FM  # noqa: E402
import rules_audit as RA  # noqa: E402

OUT = ROOT / "research" / "paper-exercise" / "reports" / "five_minute_check_output.txt"
WINDOWS = {"pre-market": ("07:00", "09:30"), "09:30-10:30": ("09:30", "10:30"), "10:30-11:30": ("10:30", "11:20")}


def rows_of(day: str, sym: str, cache: dict) -> list:
    if day not in cache:
        cache.clear()
        cache[day] = json.loads((H.CACHE / f"{day}.json").read_text())
    raw = cache[day].get(sym) or []
    return [r for r in H.to_rows(raw) if dtime(4, 0) <= r[0].time() < dtime(16, 0)]


def entries(rows, lo, hi, stop_pct, rng, k=20, before=None):
    idx = [j for j, r in enumerate(rows) if lo <= r[0].strftime("%H:%M") < hi and j + 1 < len(rows)
           and (before is None or int(r[0].timestamp()) < before)]
    out = []
    for _ in range(k if idx else 0):
        j = rng.choice(idx)
        bars = rows[j:]
        px = bars[0][1]
        stop = px * (1 - stop_pct / 100.0)
        r, _, _ = RA.run_exit(bars, px, stop, px, 1.0, dtime(11, 30), "C", "open")
        out.append(r)
    return out


def main() -> int:
    E.COST_MODEL = "live"
    lines = []

    def pr(s=""):
        print(s, flush=True); lines.append(s)

    uni = H.load_universe(None, None)
    days = sorted(uni)
    pr("five_minute_check · diagnostic, written after the addendum 2026-10-06b run, deciding nothing · mode C · gross R")
    rng = random.Random(20261007)
    cache: dict = {}

    # 1. around B's trades
    plans = pickle.loads(RA.PLANS_CACHE.read_bytes())
    by_day = defaultdict(list)
    for p in plans:
        p["kind"] = "B"
        by_day[p["day"]].append(p)
    c = dict(RA.BASE, mode="C")
    b = FM.portfolio(by_day, c)
    tr = [t for t in b if t["day"] < FM.TRAIN_END]
    rnd = []
    for t in sorted(tr, key=lambda t: t["day"]):
        rs = FM.random_entries(rows_of(t["day"], t["sym"], cache), t, "C", rng)
        if rs:
            rnd.append((t["win"], t["gross"], float(np.mean([x[0] for x in rs]))))
    pr(f"\n1. B's trades, train 2016-2022: n {len(rnd)} · B gross {np.mean([x[1] for x in rnd]):+.3f} · "
       f"random same windows {np.mean([x[2] for x in rnd]):+.3f}")
    for w in WINDOWS:
        sel = [x for x in rnd if x[0] == w]
        if sel:
            pr(f"   {w:<12} n {len(sel):>5} · B {np.mean([x[1] for x in sel]):+.3f} · random {np.mean([x[2] for x in sel]):+.3f}")

    # 2. no conditioning
    pairs = [(d, s) for d in days if d < FM.TRAIN_END for s in uni[d]]
    sample = random.Random(20261007).sample(pairs, 800)
    pr("\n2. no conditioning: 800 random symbol-days of the 2016-2022 universe, 20 random bars per window")
    for stop_pct in (3.0, 5.0):
        acc = defaultdict(list)
        for d, s in sorted(sample):
            rows = rows_of(d, s, cache)
            if len(rows) < 40:
                continue
            for w, (lo, hi) in WINDOWS.items():
                acc[w] += entries(rows, lo, hi, stop_pct, rng)
        pr(f"   stop {stop_pct:.0f}% · " + " · ".join(f"{w} {np.mean(v):+.3f} (n {len(v)})" for w, v in acc.items()))

    # 3. E1's own windows
    jobs = [(d, uni[d], str(H.CACHE), {}) for d in days]
    e1 = []
    with Pool(4) as pool:
        for _, ps, _ in pool.imap(FM.day_job, jobs, chunksize=8):
            e1 += ps
    e_by_day = defaultdict(list)
    for p in e1:
        e_by_day[p["day"]].append(p)
    prim = [t for t in FM.portfolio(e_by_day, c, keep=lambda p: p["ext"]) if t["day"] < FM.TRAIN_END]
    pr(f"\n3. E1 primary, train 2016-2022: n {len(prim)} · E1 gross {np.mean([t['gross'] for t in prim]):+.3f}")
    by_w = defaultdict(list)
    for t in prim:
        rows = rows_of(t["day"], t["sym"], cache)
        lo, hi = WINDOWS[t["win"]]
        allw = entries(rows, lo, hi, t["stop_pct"], rng)
        t_order = next(p["arm"] + 60 for p in e_by_day[t["day"]] if p["sym"] == t["sym"] and p["t"] == t["t"])
        early = entries(rows, lo, hi, t["stop_pct"], rng, before=t_order)
        by_w[t["win"]].append((t["gross"], np.mean(allw) if allw else np.nan, np.mean(early) if early else np.nan))
    for w, v in by_w.items():
        a = np.array(v, dtype=float)
        pr(f"   {w:<12} n {len(v):>3} · E1 {np.nanmean(a[:, 0]):+.3f} · random whole window {np.nanmean(a[:, 1]):+.3f} · "
           f"random before the E1 order {np.nanmean(a[:, 2]):+.3f}")
    # 4. the funnel: E1 placements in the owner's case, by the first rule that refused them
    order = ("window", "price", "vwap", "ema9", "macd", "volume", "fade", "stop < 2%", "stop < 4x spread")

    def first_fail(p):
        if not (RA.BASE["start"] <= p["t"] < RA.BASE["end"]):
            return "window"
        for g in ("price", "vwap", "ema9", "macd", "volume"):
            if g in p["red"]:
                return g
        if p["fade"] > RA.BASE["fade"]:
            return "fade"
        if p["stop_pct"] < RA.BASE["stop_floor"]:
            return "stop < 2%"
        if p["spread_ratio"] < RA.BASE["spread_k"]:
            return "stop < 4x spread"
        return None
    ext = [p for p in e1 if p["ext"]]
    pr(f"\n4. funnel, all periods: {len(e1)} E1 placements · {len(ext)} in the owner's case "
       f"(a straight green 1-minute run inside the 5-minute impulse) · refused by, first rule that fired:")
    cnt = {k: 0 for k in order}
    ok = 0
    for p in ext:
        f = first_fail(p)
        if f is None:
            ok += 1
        else:
            cnt[f] += 1
    for k in order:
        pr(f"   {k:<18} {cnt[k]:>6}")
    pr(f"   {'pass every rule':<18} {ok:>6}  (one position, the daily limits and the fill then leave the trades above)")
    OUT.write_text("\n".join(lines) + "\n")
    print(f"written {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
