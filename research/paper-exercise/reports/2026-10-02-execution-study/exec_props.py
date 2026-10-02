#!/usr/bin/env python3
"""Execution-proposal measurements on the cached stage-1 tick tape (no network, repo untouched).

Universe: the same 1,886 filled gate-passing plans as cost_decomp.py (RA.passes(p, RA.BASE) and a
filled stage-1 outcome in tick_outcomes.pkl); 13 without a real spread are dropped as there.

(A) post-trigger drift: for stop/trail exits, the last print at or before t_out + D seconds vs the
    trigger print the replay sells at. (exit - px(D)) / rps = extra R lost by acting D s later.
(B) protective STP -> STP LMT (limit = level - exit_offset(level, level + spread_out), i.e. A16):
    trigger print >= limit -> same fill; else first print >= limit within 15 s -> fill AT the limit;
    else the runner's enforce_stops (15 s + half a 5 s loop) sells at the last print at t+17.5 s.
(C) A6 on the real spread at the fill: net R (gross - cost_real) for pass vs fail.
(D) entry cap variants: cap = trigger (0 c) vs the live max(1c, 0.3 %); replayed on the same prints;
    per PLAN (unfilled = 0) over all 2,577 plans with a stage-1 outcome.
(E) commission: Fixed vs Tiered all-in for marketable orders (published IBKR rates, dossier §1).
"""
from __future__ import annotations

import pickle
import sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cost_decomp as CD  # noqa: E402  (puts scripts/ and src/ on the path)
RA, TR = CD.RA, CD.TR
from execution.intent import exit_offset  # noqa: E402

RISK, NOTIONAL = 40.0, 2000.0
DELAYS = (1, 2, 4, 5, 8, 10, 17.5)


def load_window(fx, sym, day, day0, k_from, k_to):
    ts, ps = [], []
    for k in range(k_from, k_to + 1):
        try:
            t, p = fx.chunk(sym, day, int(k), day0)
        except (CD.NoNet, FileNotFoundError):
            continue
        ts.append(np.asarray(t)); ps.append(np.round(np.asarray(p, dtype=np.float64), 4))
    if not ts:
        return np.zeros(0, np.int64), np.zeros(0)
    T, P = np.concatenate(ts), np.concatenate(ps)
    o = np.argsort(T, kind="stable")
    return T[o], P[o]


def replay_cap(T, P, entry, stop, t_order, flat_t, cap, ttl_s=TR.TTL_S, trail_r=TR.TRAIL_R,
               trail_every=TR.TRAIL_EVERY_S):
    """TR.replay with the limit given in dollars (no 1-cent floor)."""
    rps = entry - stop
    i = int(np.searchsorted(T, t_order * 1000, side="left"))
    end_entry = (t_order + ttl_s) * 1000
    n = len(T)
    trig, fill_i = False, None
    while i < n and T[i] < end_entry:
        p = P[i]
        if not trig and p >= entry:
            trig = True
        if trig and p <= cap + 1e-9:
            fill_i = i
            break
        i += 1
    if fill_i is None:
        return None if (n and T[-1] >= end_entry) else "incomplete"
    fill = float(min(cap, max(entry, P[fill_i])))
    level, high = stop, fill
    nxt = int(T[fill_i]) + trail_every * 1000
    j = fill_i + 1
    while j < n:
        tj, pj = int(T[j]), float(P[j])
        if tj >= flat_t * 1000:
            return {"fill": fill, "exit": float(P[j - 1]), "stopish": False, "r": (float(P[j - 1]) - fill) / rps}
        while tj >= nxt:
            level = max(level, round(high - trail_r * rps, 4))
            nxt += trail_every * 1000
        if pj <= level:
            return {"fill": fill, "exit": pj, "stopish": True, "r": (pj - fill) / rps, "t_out": tj}
        high = max(high, pj)
        j += 1
    return "incomplete"


def work(p):
    key, out, st, same = CD.job(p)
    if st != "ok" or out is None:
        return key, None
    fx = CD.CacheOnly()
    day0 = TR.day_open(p["day"])
    t_order = p["arm"] + 60
    flat_t = TR.at_et(p["day"], TR.FLAT)
    res = {"out": out}
    # (A)/(B) post-exit window
    if out["stopish"]:
        t0 = out["t_out"]
        k0 = (t0 // 1000 - day0) // TR.CHUNK_S
        k1 = ((t0 // 1000 + 25) - day0) // TR.CHUNK_S
        T, P = load_window(fx, p["sym"], p["day"], day0, int(k0), int(k1))
        last_t = int(T[-1]) if len(T) else 0
        px = {}
        for d in DELAYS:
            tt = t0 + int(d * 1000)
            idx = int(np.searchsorted(T, tt, side="right")) - 1
            # only trust it when the window is covered (a later print exists or the chunk was loaded)
            covered = (last_t >= tt) or ((tt // 1000 - day0) // TR.CHUNK_S <= k1 and
                                         CD.CacheOnly is not None and
                                         (TR.TICKS / p["day"] / f"{p['sym']}_{int((tt // 1000 - day0) // TR.CHUNK_S):03d}.npz").exists())
            px[d] = float(P[idx]) if (idx >= 0 and covered) else None
        res["px"] = px
        res["post"] = (T, P)
    # (D) entry cap = trigger, on the stage-1 window (t_order chunk .. exit chunk + 1)
    k_from = (t_order - day0) // TR.CHUNK_S
    k_to = ((out["t_out"] // 1000) - day0) // TR.CHUNK_S + 1
    T2, P2 = load_window(fx, p["sym"], p["day"], day0, int(k_from), int(k_to))
    res["cap0"] = replay_cap(T2, P2, p["entry"], p["stop"], t_order, flat_t, cap=p["entry"])
    res["capnow"] = replay_cap(T2, P2, p["entry"], p["stop"], t_order, flat_t, cap=RA.cap_of(p["entry"], TR.CAP_PCT))
    res.pop("post", None)
    return key, res


def comm_tiered_take(q, px):
    """Tiered, marketable (removes liquidity): commission + NASDAQ/ARCA take 0.0030 + NSCC 0.0002
    (max 0.5 % value) + NYSE/FINRA pass-through on the commission. Regulatory fees omitted (same on both plans)."""
    c = min(max(0.35, 0.0035 * q), max(0.35, 0.01 * q * px))
    return c + 0.0030 * q + min(0.0002 * q, 0.005 * q * px) + c * (0.000175 + 0.00056)


def net_of(gross, sh, rps, s_in, s_out, stopish, fill, ex):
    comm = CD.comm_fixed(sh, fill) + CD.comm_fixed(sh, ex)
    fric = sh * (s_in / 2 + 0.01) + (sh * (s_out / 2 + 0.01) if stopish else 0.0)
    return gross - (comm + fric) / (sh * rps)


def main():
    plans = pickle.loads(RA.PLANS_CACHE.read_bytes())
    done = pickle.loads(TR.OUTCOMES.read_bytes())
    gate = [p for p in plans if RA.passes(p, RA.BASE)]
    have = [p for p in gate if (p["sym"], p["arm"]) in done]
    filled = [p for p in have if (done[(p["sym"], p["arm"])] or {}).get("filled")]
    print(f"plans with stage-1 outcome {len(have)} · filled {len(filled)}")
    slim = [{k: p[k] for k in ("sym", "day", "arm", "entry", "stop")} for p in filled]
    with Pool(4) as pool:
        R = dict(pool.imap_unordered(work, slim, chunksize=8))

    rows = []
    for p in filled:
        key = (p["sym"], p["arm"])
        o, r = done[key], R.get(key)
        if r is None or o.get("spread_in") is None or (o["stopish"] and o.get("spread_out") is None):
            continue
        out = r["out"]
        e, s = p["entry"], p["stop"]
        rps = e - s
        sh = max(1, min(int(RISK // rps), int(NOTIONAL // e)))
        rows.append(dict(p=p, o=o, r=r, out=out, rps=rps, sh=sh,
                         sess="pm" if CD.et_hm(o["t_in"]) < "09:30" else "rth",
                         flag=(out.get("med20") is not None and out["med20"] >= out["level"]
                               and o["exit"] < out["med20"] * 0.97)))
    print(f"analysed {len(rows)} filled trades (same filter as cost_decomp)")

    # ---------------------------------------------------------------- (A)
    print("\n==== (A) post-trigger drift: (exit print - last print at t_out + D) / rps, stop/trail exits")
    ex = [x for x in rows if x["o"]["stopish"]]
    for label, sub in (("all", ex), ("all, off-market flag removed", [x for x in ex if not x["flag"]]),
                       ("pre-market", [x for x in ex if x["sess"] == "pm"]),
                       ("pre-market, flag removed", [x for x in ex if x["sess"] == "pm" and not x["flag"]]),
                       ("regular", [x for x in ex if x["sess"] == "rth"]),
                       ("regular, flag removed", [x for x in ex if x["sess"] == "rth" and not x["flag"]])):
        line = f"  {label:<32} n {len(sub):>5}"
        for d in DELAYS:
            v = np.array([(x["o"]["exit"] - x["r"]["px"][d]) / x["rps"] for x in sub if x["r"]["px"].get(d) is not None])
            line += f" | D={d:>4}s mean {v.mean():+.3f} med {np.median(v):+.3f} (n {len(v)})"
        print(line)
    # value per trade over ALL analysed trades (non-stop exits contribute 0)
    for d in (4, 8):
        for label, flt in (("incl. flagged", lambda x: True), ("flag removed", lambda x: not x["flag"])):
            v = [((x["o"]["exit"] - x["r"]["px"][d]) / x["rps"]) if (x["o"]["stopish"] and x["r"]["px"].get(d) is not None and flt(x)) else 0.0
                 for x in rows]
            vpm = [((x["o"]["exit"] - x["r"]["px"][d]) / x["rps"]) if (x["o"]["stopish"] and x["sess"] == "pm" and x["r"]["px"].get(d) is not None and flt(x)) else 0.0
                   for x in rows]
            print(f"  per ALL trades, D={d}s, {label}: mean {np.mean(v):+.4f} R · pre-market exits only, per all trades {np.mean(vpm):+.4f} R")

    # ---------------------------------------------------------------- (B)
    print("\n==== (B) resting STP (sell at trigger print) -> STP LMT at level - A16 offset, enforce at +17.5 s")
    for label, sub in (("all", ex), ("regular", [x for x in ex if x["sess"] == "rth"]), ("pre-market", [x for x in ex if x["sess"] == "pm"]),
                       ("all, flag removed", [x for x in ex if not x["flag"]]),
                       ("regular, flag removed", [x for x in ex if x["sess"] == "rth" and not x["flag"]]),
                       ("pre-market, flag removed", [x for x in ex if x["sess"] == "pm" and not x["flag"]])):
        sav, how = [], defaultdict(int)
        for x in sub:
            lv = x["out"]["level"]
            so = x["o"]["spread_out"]
            lim = round(lv - exit_offset(round(lv, 2), round(lv + so, 4)), 2)
            exitp = x["o"]["exit"]
            if exitp >= lim - 1e-9:
                how["same (trigger print >= limit)"] += 1
                sav.append(0.0); continue
            # first print >= limit within 15 s after the trigger: we need the post window again -> use px at delays
            # conservative: a fill at the limit only if the last print at +1, +2, +4, +5, +8 or +10 s is >= limit
            got = any((x["r"]["px"].get(d) is not None and x["r"]["px"][d] >= lim - 1e-9) for d in (1, 2, 4, 5, 8, 10))
            if got:
                how["filled at the limit later"] += 1
                sav.append((lim - exitp) / x["rps"])
            else:
                pe = x["r"]["px"].get(17.5)
                if pe is None:
                    how["no tape at +17.5 s (dropped)"] += 1
                    continue
                how["enforced at +17.5 s"] += 1
                sav.append((pe - exitp) / x["rps"])
        v = np.array(sav)
        print(f"  {label:<26} n {len(v):>5} · saving mean {v.mean():+.4f} R median {np.median(v):+.4f} "
              f"p5 {np.quantile(v, .05):+.3f} p95 {np.quantile(v, .95):+.3f} · per ALL {len(rows)} trades {v.sum() / len(rows):+.4f} R · {dict(how)}")

    # ---------------------------------------------------------------- (C)
    print("\n==== (C) A6 on the REAL spread at the fill (spread_in > rps/4 = fail)")
    for label, flt in (("pass", lambda x: x["o"]["spread_in"] <= x["rps"] / 4), ("fail", lambda x: x["o"]["spread_in"] > x["rps"] / 4)):
        sub = [x for x in rows if flt(x)]
        g = np.array([x["o"]["r"] for x in sub])
        c = np.array([TR.cost_real(dict(x["p"], tick={"spread_in": x["o"]["spread_in"], "spread_out": x["o"].get("spread_out")}), x["o"]["stopish"]) for x in sub])
        print(f"  {label}: n {len(sub)} · gross {g.mean():+.3f} · cost_real {c.mean():.3f} · net {np.mean(g - c):+.3f} R/trade · sum net {np.sum(g - c):+.1f} R")
        for sess in ("pm", "rth"):
            ss = [i for i, x in enumerate(sub) if x["sess"] == sess]
            print(f"     {sess}: n {len(ss)} · net {np.mean((g - c)[ss]):+.3f}")

    # ---------------------------------------------------------------- (D)
    print("\n==== (D) entry cap = trigger vs live cap (re-replayed on the same prints); per plan over all plans with a stage-1 outcome")
    n_plans = len(have)
    stat = defaultdict(int)
    tot = {"capnow": 0.0, "cap0": 0.0}
    nfill = {"capnow": 0, "cap0": 0}
    lost_gross, lost_n = [], 0
    for x in rows:
        o = x["o"]
        for v in ("capnow", "cap0"):
            res = x["r"][v]
            if res == "incomplete":
                stat[f"{v} incomplete"] += 1
                continue
            if res is None:
                stat[f"{v} unfilled"] += 1
                continue
            nfill[v] += 1
            tot[v] += net_of(res["r"], x["sh"], x["rps"], o["spread_in"], o.get("spread_out") or 0.0, res["stopish"], res["fill"], res["exit"])
        if x["r"]["cap0"] is None and isinstance(x["r"]["capnow"], dict):
            lost_n += 1
            lost_gross.append(net_of(x["r"]["capnow"]["r"], x["sh"], x["rps"], o["spread_in"], o.get("spread_out") or 0.0,
                                     x["r"]["capnow"]["stopish"], x["r"]["capnow"]["fill"], x["r"]["capnow"]["exit"]))
    chk = sum(1 for x in rows if isinstance(x["r"]["capnow"], dict) and abs(x["r"]["capnow"]["fill"] - x["o"]["fill"]) < 1e-9
              and abs(x["r"]["capnow"]["exit"] - x["o"]["exit"]) < 1e-9)
    print(f"  check: capnow replay == cached outcome on {chk}/{len(rows)}")
    print(f"  status {dict(stat)}")
    for v in ("capnow", "cap0"):
        print(f"  {v:<7} filled {nfill[v]:>5} of {n_plans} plans · net R sum {tot[v]:+.1f} · per plan {tot[v] / n_plans:+.4f} · per filled trade {tot[v] / max(1, nfill[v]):+.4f}")
    if lost_gross:
        print(f"  plans filled now but NOT at cap = trigger: {lost_n} · their net R now mean {np.mean(lost_gross):+.3f} sum {np.sum(lost_gross):+.1f}")
    same_fill = [x for x in rows if isinstance(x["r"]["cap0"], dict) and isinstance(x["r"]["capnow"], dict)]
    d = [(x["r"]["capnow"]["fill"] - x["r"]["cap0"]["fill"]) / x["rps"] for x in same_fill]
    print(f"  both filled: {len(same_fill)} · entry price saved by cap = trigger mean {np.mean(d):.4f} R")

    # ---------------------------------------------------------------- (E)
    print("\n==== (E) commission per round trip, Fixed vs Tiered ALL-IN marketable both legs (take 0.0030 + NSCC 0.0002 + pass-through)")
    bands = [(1, 99), (100, 199), (200, 399), (400, 699), (700, 10 ** 9)]
    allf, allt = [], []
    for lo, hi in bands:
        sub = [x for x in rows if lo <= x["sh"] <= hi]
        f = np.array([(CD.comm_fixed(x["sh"], x["o"]["fill"]) + CD.comm_fixed(x["sh"], x["o"]["exit"])) / (x["sh"] * x["rps"]) for x in sub])
        t = np.array([(comm_tiered_take(x["sh"], x["o"]["fill"]) + comm_tiered_take(x["sh"], x["o"]["exit"])) / (x["sh"] * x["rps"]) for x in sub])
        allf += list(f); allt += list(t)
        print(f"  shares {lo}-{hi if hi < 10 ** 9 else '+'}: n {len(sub):>4} · fixed {f.mean():.3f} R · tiered all-in take {t.mean():.3f} R · tiered - fixed {t.mean() - f.mean():+.3f}")
    print(f"  ALL: fixed {np.mean(allf):.4f} R · tiered all-in take {np.mean(allt):.4f} R · tiered - fixed {np.mean(allt) - np.mean(allf):+.4f} R/trade")
    pmrows = [x for x in rows if x["sess"] == "pm"]
    print(f"  pre-market fills: fixed {np.mean([(CD.comm_fixed(x['sh'], x['o']['fill']) + CD.comm_fixed(x['sh'], x['o']['exit'])) / (x['sh'] * x['rps']) for x in pmrows]):.4f}"
          f" · tiered {np.mean([(comm_tiered_take(x['sh'], x['o']['fill']) + comm_tiered_take(x['sh'], x['o']['exit'])) / (x['sh'] * x['rps']) for x in pmrows]):.4f}")


if __name__ == "__main__":
    main()
