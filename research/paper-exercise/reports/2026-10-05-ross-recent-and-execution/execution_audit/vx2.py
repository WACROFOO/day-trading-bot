#!/usr/bin/env python3
"""Adversarial checks on the execution-design audit. Cached data only.
(1) P1 with a decision-time spread (arming-bar proxy) instead of the spread at the fill.
(2) P2 against a live-faithful G0: the live gate reads real fills, which already embed the spread,
    so its R is (print P&L - half spreads) / planned, without commission.
(3) P3: live-like trail anchor (high only from prints at/after the next 10-s boundary after the fill,
    1c move threshold) vs the replay's high = fill. Same fills, same ticks."""
from __future__ import annotations
import pickle, sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path
import numpy as np
ROOT = Path("/home/user/day-trading-bot")
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src"),
                str(ROOT / "research/paper-exercise/reports/2026-10-02-execution-study")]
import rules_audit as RA  # noqa
import tick_replay as TR  # noqa
import cost_decomp as CD  # noqa
RISK, NOTIONAL = 40.0, 2000.0

def shares(rps_eff, entry, risk=RISK, px=None):
    if rps_eff <= 0 or risk < rps_eff:
        return 0
    sh = int(round(risk * 1000)) // int(round(rps_eff * 1000))
    sh = min(sh, int(NOTIONAL // (px or entry)))
    return max(1, sh)

def replay_anchor(T, P, entry, stop, t_order, flat_t, live_anchor):
    cap = RA.cap_of(entry, TR.CAP_PCT); rps = entry - stop
    i = int(np.searchsorted(T, t_order * 1000, side="left")); end = (t_order + TR.TTL_S) * 1000
    n = len(T); trig = False; fi = None
    while i < n and T[i] < end:
        p = P[i]
        if not trig and p >= entry: trig = True
        if trig and p <= cap: fi = i; break
        i += 1
    if fi is None: return None
    fill = float(min(cap, max(entry, P[fi]))); tf = int(T[fi])
    level = stop
    if live_anchor:
        high = None; bar0 = ((tf // 10000) + 1) * 10000   # first 10-s bar whose open >= fill_ts
    else:
        high = fill; bar0 = None
    nxt = tf + TR.TRAIL_EVERY_S * 1000; j = fi + 1; fl = flat_t * 1000
    while j < n:
        tj, pj = int(T[j]), float(P[j])
        if tj >= fl:
            return dict(fill=fill, exit=float(P[j-1]), stopish=False, how="flat")
        while tj >= nxt:
            if high is not None:
                new = round(high - rps, 4)
                if live_anchor:
                    if new >= level + 0.01 - 1e-9: level = new
                else:
                    level = max(level, new)
            nxt += TR.TRAIL_EVERY_S * 1000
        if pj <= level:
            return dict(fill=fill, exit=pj, stopish=True, how="trail" if level > stop else "stop")
        if live_anchor:
            if tj >= bar0: high = pj if high is None else max(high, pj)
        else:
            high = max(high, pj)
        j += 1
    return dict(fill=fill, exit=float(P[n-1]), stopish=False, how="end")

def job(p):
    fx = CD.CacheOnly(); day0 = TR.day_open(p["day"]); t_order = p["arm"] + 60
    flat_t = TR.at_et(p["day"], TR.FLAT)
    k = (t_order - day0) // TR.CHUNK_S; last = (flat_t - day0) // TR.CHUNK_S
    ts, ps = [], []
    try:
        while k <= last:
            t, pr = fx.chunk(p["sym"], p["day"], int(k), day0); ts.append(t); ps.append(pr); k += 1
    except Exception:
        if not ts: return (p["sym"], p["arm"]), None
    T = np.concatenate(ts); P = np.round(np.concatenate(ps).astype(np.float64), 4)
    a = replay_anchor(T, P, p["entry"], p["stop"], t_order, flat_t, False)
    b = replay_anchor(T, P, p["entry"], p["stop"], t_order, flat_t, True)
    return (p["sym"], p["arm"]), (a, b)

def main():
    plans = pickle.loads(RA.PLANS_CACHE.read_bytes()); done = pickle.loads(TR.OUTCOMES.read_bytes())
    gate = [p for p in plans if RA.passes(p, RA.BASE)]
    have = [p for p in gate if (p["sym"], p["arm"]) in done]
    filled = [p for p in have if (done[(p["sym"], p["arm"])] or {}).get("filled")]
    rows = {}
    for p in filled:
        o = done[(p["sym"], p["arm"])]
        if o.get("spread_in") is None or (o["stopish"] and o.get("spread_out") is None):
            continue
        rps = p["entry"] - p["stop"]
        sp_dec = rps / p["spread_ratio"] if p["spread_ratio"] and p["spread_ratio"] < 99 else None
        rows[(p["sym"], p["arm"])] = dict(p=p, entry=p["entry"], stop=p["stop"], rps=rps,
            cap=RA.cap_of(p["entry"], TR.CAP_PCT), fill=o["fill"], exit=o["exit"], stopish=o["stopish"],
            how=o["how"], sp_in=o["spread_in"], sp_out=o.get("spread_out") or 0.0, sp_dec=sp_dec,
            t_out=o["t_out"], pm=p["pm"])
    R = list(rows.values())
    print(f"trades {len(R)} · decision-time spread proxy known {sum(1 for r in R if r['sp_dec'] is not None)}")
    spd = np.array([r["sp_dec"] for r in R if r["sp_dec"] is not None]); spf = np.array([r["sp_in"] for r in R if r["sp_dec"] is not None])
    print(f"  arming-bar proxy spread p50 {np.median(spd):.4f} · fill spread p50 {np.median(spf):.4f} · proxy < fill spread on {np.mean(spd < spf - 1e-9):.1%}")

    def outcome(sz):
        pnl, unit = [], []
        for r in R:
            sh = sz(r)
            c = CD.comm_fixed(sh, r["fill"]) + CD.comm_fixed(sh, r["exit"])
            fr = sh * r["sp_in"] / 2 + (sh * r["sp_out"] / 2 if r["stopish"] else 0.0)
            pnl.append(sh * (r["exit"] - r["fill"]) - c - fr); unit.append(sh * r["rps"])
        return np.array(pnl), np.array(unit)
    print("\n(1) P1 sizing, fill spread (audit) vs decision-time proxy spread")
    for name, f in (("V0 live", lambda r: shares(r["rps"], r["entry"])),
                    ("V2 fill spread (audit)", lambda r: shares(r["cap"] - r["stop"] + r["sp_in"] + 0.01, r["entry"])),
                    ("V2 decision proxy spread", lambda r: shares(r["cap"] - r["stop"] + (r["sp_dec"] if r["sp_dec"] is not None else r["sp_in"]) + 0.01, r["entry"]))):
        pnl, unit = outcome(f)
        print(f"  {name:<28} $ mean {pnl.mean():7.2f} · std {pnl.std():6.2f} · p1 {np.percentile(pnl,1):8.2f} · min {pnl.min():8.2f} · "
              f">$40 {int(np.sum(-pnl>40)):4d} · >$42 {int(np.sum(-pnl>42)):4d} · R/plan$ {np.mean(pnl/unit):.4f} · R/$40 {pnl.mean()/RISK:.4f}")

    # (2) daily gate variants incl. live-faithful G0
    by_day = defaultdict(list)
    for p in have: by_day[p["day"]].append(p)
    def sz_live(r, risk): return shares(r["rps"], r["entry"], risk)
    def run(gate_mode, remaining, v2=False):
        days, trades = {}, []
        for day in sorted(by_day):
            cands = sorted(by_day[day], key=lambda p: p["arm"]); busy, pending = [], []
            gate_sum, streak, orders, day_usd = 0.0, 0, 0, 0.0
            for p in cands:
                t_order = p["arm"] + 60; pending.sort(key=lambda x: x[0])
                while pending and pending[0][0] <= t_order:
                    _, unit, usd = pending.pop(0); gate_sum += unit; day_usd += usd
                    if unit <= -0.25: streak += 1
                    elif unit >= 0.25: streak = 0
                spent = -gate_sum
                if spent >= 3.0 or streak >= 3 or orders >= 6: break
                busy = [(f, s) for f, s in busy if f > t_order]
                if len(busy) >= 1: continue
                orders += 1
                o = done[(p["sym"], p["arm"])]; r = rows.get((p["sym"], p["arm"]))
                if not o.get("filled") or r is None:
                    busy.append(((o["t_out"] // 1000 + 60) if o.get("filled") else t_order + 180, p["sym"])); continue
                risk = min(RISK, (3.0 - spent) * RISK) if remaining else RISK
                sh = (shares(r['cap'] - r['stop'] + (r['sp_dec'] if r['sp_dec'] is not None else r['sp_in']) + 0.01, r['entry'], risk, px=r['cap']) if v2 else sz_live(r, risk))
                if sh <= 0: busy.append((t_order + 180, p["sym"])); continue
                c = CD.comm_fixed(sh, r["fill"]) + CD.comm_fixed(sh, r["exit"])
                fr = sh * r["sp_in"] / 2 + (sh * r["sp_out"] / 2 if r["stopish"] else 0.0)
                usd = sh * (r["exit"] - r["fill"]) - c - fr
                planned = sh * r["rps"]
                if gate_mode == "gross": unit = sh * (r["exit"] - r["fill"]) / planned
                elif gate_mode == "fills": unit = (sh * (r["exit"] - r["fill"]) - fr) / planned   # what risk.py sees on real fills
                else: unit = usd / RISK
                busy.append((r["t_out"] // 1000 + 60, p["sym"])); pending.append((r["t_out"] // 1000 + 60, unit, usd)); trades.append(usd)
            for _, u, usd in pending: day_usd += usd
            days[day] = day_usd
        return np.array(trades), np.array(list(days.values()))
    print("\n(2) daily gate: G0 as the audit modelled it, G0 live-faithful (real fills embed the spread), G1, G2")
    for label, gm, rem in (("G0 audit: gate on print P&L / planned", "gross", False),
                           ("G0f live-faithful: (print - half spreads) / planned", "fills", False),
                           ("G1 all-in $ gate", "usd", False), ("G2 all-in $ gate + remaining", "usd", True)):
        t, d = run(gm, rem)
        print(f"  {label:<52} trades {len(t)} · $/trade {t.mean():7.2f} · days {len(d)} · worst {d.min():8.2f} · p1 {np.percentile(d,1):8.2f} · "
              f"days<-120 {int(np.sum(d<-120))} · days<-160 {int(np.sum(d<-160))}")
    for label, gm, rem in (("G3f V2(decision spread) + live-faithful gate", "fills", False),
                           ("G4d V2(decision spread) + $ gate + remaining", "usd", True)):
        t, d = run(gm, rem, v2=True)
        print(f"  {label:<52} trades {len(t)} · $/trade {t.mean():7.2f} · days {len(d)} · worst {d.min():8.2f} · p1 {np.percentile(d,1):8.2f} · "
              f"days<-120 {int(np.sum(d<-120))} · days<-160 {int(np.sum(d<-160))}")

    return
    # (3) P3
    slim = [{k: r["p"][k] for k in ("sym", "day", "arm", "entry", "stop")} for r in R]
    with Pool(4) as pool:
        res = dict(pool.imap_unordered(job, slim, chunksize=8))
    agree = diff = 0; dA, dB = [], []; kinds = defaultdict(int); changed = 0
    for r in R:
        k = (r["p"]["sym"], r["p"]["arm"]); v = res.get(k)
        if not v or v[0] is None or v[1] is None: continue
        a, b = v
        if abs(a["fill"] - r["fill"]) < 1e-9 and abs(a["exit"] - r["exit"]) < 1e-9: agree += 1
        else: diff += 1
        sh = shares(r["rps"], r["entry"])
        dA.append(sh * (a["exit"] - a["fill"])); dB.append(sh * (b["exit"] - b["fill"]))
        if abs(a["exit"] - b["exit"]) > 1e-9: changed += 1
        kinds[(a["how"], b["how"])] += 1
    dA, dB = np.array(dA), np.array(dB)
    rpsS = np.array([shares(r["rps"], r["entry"]) * r["rps"] for r in R if res.get((r["p"]["sym"], r["p"]["arm"])) and res[(r["p"]["sym"], r["p"]["arm"])][1] is not None])
    print(f"\n(3) P3: replay anchor (high = fill) reproduces cached outcome on {agree}, differs {diff}")
    print(f"  trades {len(dA)} · exits changed by the live-like anchor {changed} · print P&L $ replay {dA.sum():.2f} vs live-like {dB.sum():.2f}"
          f" · diff ${dA.sum()-dB.sum():.2f} total, ${(dA-dB).mean():.3f}/trade, {np.mean((dA-dB)/rpsS):.4f} R/trade")
    print(f"  per-trade diff (replay - live-like) $: p50 {np.median(dA-dB):.2f} · p99 {np.percentile(dA-dB,99):.2f} · min {np.min(dA-dB):.2f} · max {np.max(dA-dB):.2f}")
    print(f"  exit kinds (replay, live-like): {dict(kinds)}")

if __name__ == "__main__":
    main()
