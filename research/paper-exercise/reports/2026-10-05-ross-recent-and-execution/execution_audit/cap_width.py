#!/usr/bin/env python3
"""A10 cap-width sweep on the stage-1 tick replay universe (BASE plans with an outcome, 2024-2026).
Same replay as TR.replay with the cap as a parameter; cap 'trig' = limit at the trigger (exec_props (D)).
NET=1 env: allow Alpaca fetch for missing chunks (keys from env), else cache only."""
from __future__ import annotations

import os
import pickle
import sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path("/home/user/day-trading-bot")
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src"),
                str(ROOT / "research/paper-exercise/reports/2026-10-02-execution-study")]
import rules_audit as RA  # noqa: E402
import tick_replay as TR  # noqa: E402
import cost_decomp as CD  # noqa: E402

CAPS = [("trig", None), ("0.15%", 0.15), ("0.3% live", 0.3), ("0.5%", 0.5), ("1.0%", 1.0), ("2.0%", 2.0)]
NET = os.environ.get("NET") == "1"


def cap_price(entry, pct):
    return entry if pct is None else RA.cap_of(entry, pct)


def replay_cap(T, P, entry, stop, t_order, flat_t, cap):
    rps = entry - stop
    i = int(np.searchsorted(T, t_order * 1000, side="left"))
    end_entry = (t_order + TR.TTL_S) * 1000
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
        return ("unfilled", None) if (n and T[-1] >= end_entry) else ("incomplete", None)
    fill = float(min(cap, max(entry, P[fill_i])))
    level, high = stop, fill
    nxt = int(T[fill_i]) + TR.TRAIL_EVERY_S * 1000
    j = fill_i + 1
    while j < n:
        tj, pj = int(T[j]), float(P[j])
        if tj >= flat_t * 1000:
            return "ok", {"fill": fill, "exit": float(P[j - 1]), "stopish": False, "trig": bool(trig)}
        while tj >= nxt:
            level = max(level, round(high - TR.TRAIL_R * rps, 4))
            nxt += TR.TRAIL_EVERY_S * 1000
        if pj <= level:
            return "ok", {"fill": fill, "exit": pj, "stopish": True}
        high = max(high, pj)
        j += 1
    return "incomplete", None


def work(p):
    fx = TR.Fetcher(_client()) if NET else CD.CacheOnly()
    day0 = TR.day_open(p["day"])
    t_order = p["arm"] + 60
    flat_t = TR.at_et(p["day"], TR.FLAT)
    k = (t_order - day0) // TR.CHUNK_S
    last_k = (flat_t - day0) // TR.CHUNK_S
    ts, ps = [], []
    out = {}
    pending = dict(CAPS)
    while k <= last_k and pending:
        try:
            t, pr = fx.chunk(p["sym"], p["day"], int(k), day0)
        except (CD.NoNet, FileNotFoundError):
            break
        except Exception as exc:                       # noqa: BLE001
            out["_err"] = repr(exc)[:120]
            break
        ts.append(t); ps.append(pr)
        T = np.concatenate(ts)
        P = np.round(np.concatenate(ps).astype(np.float64), 4)
        for name, pct in list(pending.items()):
            st, o = replay_cap(T, P, p["entry"], p["stop"], t_order, flat_t, cap_price(p["entry"], pct))
            if st != "incomplete":
                out[name] = (st, o)
                pending.pop(name)
        k += 1
    for name in pending:
        out[name] = ("incomplete", None)
    return (p["sym"], p["arm"]), out


def _client():
    return TR.client_from_env() if hasattr(TR, "client_from_env") else None


def main():
    plans = pickle.loads(RA.PLANS_CACHE.read_bytes())
    done = pickle.loads(TR.OUTCOMES.read_bytes())
    gate = [p for p in plans if RA.passes(p, RA.BASE)]
    have = [p for p in gate if (p["sym"], p["arm"]) in done]
    slim = [{k: p[k] for k in ("sym", "day", "arm", "entry", "stop", "pm")} for p in have]
    print(f"plans with stage-1 outcome {len(have)} · cache only: {not NET}")
    with Pool(4) as pool:
        R = dict(pool.imap_unordered(work, slim, chunksize=8))
    pickle.dump(R, open(Path(__file__).with_suffix(".pkl"), "wb"))
    # cross-check: the 0.3% replay must equal the cached stage-1 outcome
    agree = dis = 0
    for p in have:
        key = (p["sym"], p["arm"])
        st, o = R[key]["0.3% live"]
        ref = done[key]
        if st == "incomplete":
            continue
        if (st == "ok") == bool(ref.get("filled")) and (st != "ok" or (abs(o["fill"] - ref["fill"]) < 1e-9 and abs(o["exit"] - ref["exit"]) < 1e-9)):
            agree += 1
        else:
            dis += 1
    print(f"0.3% replay vs cached outcome: agree {agree} · differ {dis}")
    med_sp = float(np.median([d["spread_in"] for d in done.values() if d.get("spread_in") is not None]))
    print(f"cost proxy for fills without a recorded spread: median spread_in {med_sp:.3f}")
    print(f"\n  {'cap':<10}{'filled':>7}{'incompl':>8}{'fill-trig c p50/p90/p99':>26}{'gross/fill':>11}{'net/fill':>10}{'net/plan':>10}{'net sum':>9}")
    base_fill = {}
    for name, pct in CAPS:
        fills, inc, net, gross, slip = 0, 0, [], [], []
        for p in have:
            key = (p["sym"], p["arm"])
            st, o = R[key][name]
            if st == "incomplete":
                inc += 1
                continue
            if st != "ok":
                net.append(0.0)
                continue
            fills += 1
            e, s = p["entry"], p["stop"]
            rps = e - s
            sh = max(1, min(int(40 // rps), int(2000 // e)))
            ref = done[key]
            s_in = ref.get("spread_in") if ref.get("filled") and ref.get("spread_in") is not None else med_sp
            s_out = ref.get("spread_out") if ref.get("filled") and ref.get("spread_out") is not None else med_sp
            g = (o["exit"] - o["fill"]) / rps
            n_ = g - (CD.comm_fixed(sh, o["fill"]) + CD.comm_fixed(sh, o["exit"]) + sh * s_in / 2
                      + (sh * s_out / 2 if o["stopish"] else 0.0)) / (sh * rps)
            gross.append(g); net.append(n_); slip.append((o["fill"] - e) * 100)
        net = np.array(net)
        sl = np.array(slip)
        print(f"  {name:<10}{fills:>7}{inc:>8}{f'{np.percentile(sl,50):.2f}/{np.percentile(sl,90):.2f}/{np.percentile(sl,99):.2f}':>26}"
              f"{np.mean(gross):>11.4f}{np.sum(net) / fills:>10.4f}{net.mean():>10.4f}{net.sum():>9.1f}")
    # the marginal fills: filled at a wider cap but not at 0.3 %
    for name, pct in CAPS:
        if pct is None or pct <= 0.3:
            continue
        m = []
        for p in have:
            key = (p["sym"], p["arm"])
            a, b = R[key]["0.3% live"], R[key][name]
            if a[0] == "unfilled" and b[0] == "ok":
                e, s = p["entry"], p["stop"]
                m.append((b[1]["exit"] - b[1]["fill"]) / (e - s))
            elif b[0] == "incomplete" and a[0] == "unfilled":
                pass
        m = np.array(m)
        if len(m):
            print(f"  marginal fills at {name} (unfilled at 0.3 %): n {len(m)} · gross mean {m.mean():+.3f} · median {np.median(m):+.3f}")
    for name, pct in CAPS:
        if pct is not None and pct >= 0.3:
            continue
        m = []
        for p in have:
            key = (p["sym"], p["arm"])
            a, b = R[key]["0.3% live"], R[key][name]
            if a[0] == "ok" and b[0] == "unfilled":
                e, s = p["entry"], p["stop"]
                m.append((a[1]["exit"] - a[1]["fill"]) / (e - s))
        m = np.array(m)
        if len(m):
            print(f"  fills LOST at {name} (filled at 0.3 %): n {len(m)} · their gross at 0.3 % mean {m.mean():+.3f} · median {np.median(m):+.3f}")


if __name__ == "__main__":
    main()
