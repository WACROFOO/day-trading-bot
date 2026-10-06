#!/usr/bin/env python3
"""RA — re-anchor a run-past entry instead of dropping it (addendum 2026-10-06c).

The owner, IPDN 2026-10-06 08:01: the plan armed at 5.28 / 4.83 and was dropped
because the ask ran past the A10 limit (5.30). RA keeps the chart's stop and
buys the run-past print if it is at most +2 % over the trigger, sizing from the
price paid ($40 / (print - stop)) and trailing 1 x (print - stop).

Primary: the B plans with a stage-1 tick outcome, 2024-26 SIP prints (cache only).
Check: 1-minute bars 2016-2023 (reading C): a trigger bar opening above the limit
and within +2 % is the re-anchored fill at its open.

    python3 scripts/reanchor.py
"""
from __future__ import annotations

import json
import pickle
import sys
from collections import defaultdict
from datetime import time as dtime
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src"),
                str(ROOT / "research/paper-exercise/reports/2026-10-02-execution-study")]
import backtest_history as H  # noqa: E402
import backtest_recent as E  # noqa: E402
import cost_decomp as CD  # noqa: E402
import rules_audit as RA  # noqa: E402
import tick_replay as TR  # noqa: E402

OUT = ROOT / "research" / "paper-exercise" / "reports" / "reanchor_output.txt"
CEIL_PCT = 2.0
RISK, NOTIONAL = 40.0, 2000.0


def ceil_of(entry: float) -> float:
    return round(entry * (1 + CEIL_PCT / 100.0), 4)


# ------------------------------------------------------------------ ticks
def replay(T, P, entry, stop, t_order, flat_t, reanchor: bool):
    """('ok', {fill, exit, stopish, kind}) | ('unfilled', None) | ('incomplete', None).
    kind: 'live' (filled inside the A10 limit) or 'ra' (re-anchored above it)."""
    cap, ceil = RA.cap_of(entry, TR.CAP_PCT), ceil_of(entry)
    i = int(np.searchsorted(T, t_order * 1000, side="left"))
    end = (t_order + TR.TTL_S) * 1000
    n = len(T)
    trig, fill_i, kind = False, None, None
    while i < n and T[i] < end:
        p = P[i]
        if not trig and p >= entry:
            trig = True
        if trig:
            if p <= cap + 1e-9:
                fill_i, kind = i, "live"
                break
            if reanchor and p <= ceil + 1e-9:
                fill_i, kind = i, "ra"
                break
        i += 1
    if fill_i is None:
        return ("unfilled", None) if (n and T[-1] >= end) else ("incomplete", None)
    fill = float(min(cap, max(entry, P[fill_i]))) if kind == "live" else float(P[fill_i])
    rps = (entry - stop) if kind == "live" else (fill - stop)
    level, high = stop, fill
    nxt = int(T[fill_i]) + TR.TRAIL_EVERY_S * 1000
    j = fill_i + 1
    while j < n:
        tj, pj = int(T[j]), float(P[j])
        if tj >= flat_t * 1000:
            return "ok", {"fill": fill, "exit": float(P[j - 1]), "stopish": False, "kind": kind, "rps": rps}
        while tj >= nxt:
            level = max(level, round(high - TR.TRAIL_R * rps, 4))
            nxt += TR.TRAIL_EVERY_S * 1000
        if pj <= level:
            return "ok", {"fill": fill, "exit": pj, "stopish": True, "kind": kind, "rps": rps}
        high = max(high, pj)
        j += 1
    return "incomplete", None


def work(p):
    fx = CD.CacheOnly()
    day0 = TR.day_open(p["day"])
    t_order = p["arm"] + 60
    flat_t = TR.at_et(p["day"], TR.FLAT)
    k, last_k = (t_order - day0) // TR.CHUNK_S, (flat_t - day0) // TR.CHUNK_S
    ts, ps, out = [], [], {}
    pending = {"live": False, "ra": True}
    while k <= last_k and pending:
        try:
            t, pr = fx.chunk(p["sym"], p["day"], int(k), day0)
        except Exception:                                  # noqa: BLE001
            break
        ts.append(t); ps.append(pr)
        T = np.concatenate(ts); P = np.round(np.concatenate(ps).astype(np.float64), 4)
        for name, flag in list(pending.items()):
            st, o = replay(T, P, p["entry"], p["stop"], t_order, flat_t, flag)
            if st != "incomplete":
                out[name] = (st, o); pending.pop(name)
        k += 1
    for name in pending:
        out[name] = ("incomplete", None)
    return (p["sym"], p["arm"]), out


def dollars(o, s_in, s_out) -> float:
    sh = max(1, min(int(RISK // o["rps"]), int(NOTIONAL // o["fill"])))
    return (sh * (o["exit"] - o["fill"]) - CD.comm_fixed(sh, o["fill"]) - CD.comm_fixed(sh, o["exit"])
            - sh * s_in / 2 - (sh * s_out / 2 if o["stopish"] else 0.0))


def day_lb(diffs: dict, alpha=0.05, draws=20000, seed=20261006) -> float:
    days = sorted(diffs)
    s = np.array([sum(diffs[d]) for d in days]); n = np.array([len(diffs[d]) for d in days])
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(days), size=(draws, len(days)))
    return float(np.quantile(s[pick].sum(1) / n[pick].sum(1), alpha))


# ------------------------------------------------------------------ bars 2016-2023
def bar_job(args):
    day, plans = args
    f = H.CACHE / f"{day}.json"
    if not f.exists():
        return []
    data = json.loads(f.read_text())
    out = []
    for p in plans:
        rows = [r for r in H.to_rows(data.get(p["sym"]) or []) if dtime(4, 0) <= r[0].time() < dtime(16, 0)]
        t_order = p["arm"] + 60
        fwd = [r for r in rows if int(r[0].timestamp()) >= t_order]
        if not fwd:
            continue
        entry, stop = p["entry"], p["stop"]
        cap, ceil = RA.cap_of(entry, 0.3), ceil_of(entry)
        live = RA.fill_retouch(fwd, entry, 3, 0.3, t_order)
        live_net = 0.0
        if live is not None:
            fk, px, kind = live
            r, stopish, _ = RA.run_exit(fwd[fk:], entry, stop, px, 1.0, dtime(11, 30), "C", kind)
            live_net = r - RA.cost_live(entry, stop, stopish, p["pm"], p["dv5"])
        window = [k for k, b in enumerate(fwd) if b[0].timestamp() < t_order + 180]
        touch = next((k for k in window if fwd[k][2] >= entry), None)
        ra_net, ra = live_net, False
        if touch is not None and cap < fwd[touch][1] <= ceil:
            o = fwd[touch][1]
            r, stopish, _ = RA.run_exit(fwd[touch:], o, stop, o, 1.0, dtime(11, 30), "C", "open")
            ra_net, ra = r - RA.cost_live(o, stop, stopish, p["pm"], p["dv5"]), True
        out.append({"day": day, "live": live_net, "ra": ra_net, "re": ra})
    return out


def main() -> int:
    E.COST_MODEL = "live"
    lines = []

    def pr(s=""):
        print(s, flush=True); lines.append(s)

    plans = pickle.loads(RA.PLANS_CACHE.read_bytes())
    done = pickle.loads(TR.OUTCOMES.read_bytes())
    gate = [p for p in plans if RA.passes(p, RA.BASE)]
    have = [p for p in gate if (p["sym"], p["arm"]) in done]
    slim = [{k: p[k] for k in ("sym", "day", "arm", "entry", "stop", "pm")} for p in have]
    pr(f"RA · addendum 2026-10-06c · ceiling +{CEIL_PCT:g} % · $40 / $2,000 · IBKR Fixed + half spreads")
    pr(f"ticks 2024-26: B plans with a stage-1 outcome {len(have)} (cache only)")
    with Pool(4) as pool:
        R = dict(pool.imap_unordered(work, slim, chunksize=8))
    med = float(np.median([d["spread_in"] for d in done.values() if d.get("spread_in") is not None]))
    diffs, ra_trades, live_tot, ra_tot, n_cmp = defaultdict(list), [], 0.0, 0.0, 0
    agree = differ = 0
    for p in have:
        key = (p["sym"], p["arm"])
        a, b = R[key]["live"], R[key]["ra"]
        if a[0] == "incomplete" or b[0] == "incomplete":
            continue
        ref = done[key]
        if (a[0] == "ok") == bool(ref.get("filled")) and (a[0] != "ok" or abs(a[1]["fill"] - ref["fill"]) < 1e-9):
            agree += 1
        else:
            differ += 1
        s_in = ref.get("spread_in") if ref.get("filled") and ref.get("spread_in") is not None else med
        s_out = ref.get("spread_out") if ref.get("filled") and ref.get("spread_out") is not None else med
        lv = dollars(a[1], s_in, s_out) / RISK if a[0] == "ok" else 0.0
        rv = dollars(b[1], s_in, s_out) / RISK if b[0] == "ok" else 0.0
        if b[0] == "ok" and b[1]["kind"] == "ra":
            ra_trades.append({"day": p["day"], "net": rv, "gross": (b[1]["exit"] - b[1]["fill"]) / b[1]["rps"],
                              "live_net": lv, "live_filled": a[0] == "ok",
                              "over": (b[1]["fill"] / p["entry"] - 1) * 100})
        diffs[p["day"]].append(rv - lv)
        live_tot += lv; ra_tot += rv; n_cmp += 1
    pr(f"live replay vs the cached stage-1 outcome: agree {agree} · differ {differ}")
    pr(f"plans compared {n_cmp} · live net {live_tot:+.1f} R ({live_tot / n_cmp:+.4f} a plan) · "
       f"RA net {ra_tot:+.1f} R ({ra_tot / n_cmp:+.4f} a plan)")
    lb = day_lb(diffs)
    pr(f"(1) RA − live per plan: mean {(ra_tot - live_tot) / n_cmp:+.4f} R · day-clustered one-sided 95 % lower bound {lb:+.4f}")
    if ra_trades:
        net = np.array([t["net"] for t in ra_trades]); g = np.array([t["gross"] for t in ra_trades])
        was = [t for t in ra_trades if t["live_filled"]]
        pr(f"(2) re-anchored trades n {len(net)} · gross {g.mean():+.3f} · net {net.mean():+.3f} R · "
           f"win {np.mean(net > 0):.1%} · median paid {np.median([t['over'] for t in ra_trades]):.2f} % over the trigger")
        pr(f"    of which live would have filled later on a return: {len(was)} · their live net "
           f"{np.mean([t['live_net'] for t in was]) if was else float('nan'):+.3f} vs RA "
           f"{np.mean([t['net'] for t in was]) if was else float('nan'):+.3f}")
        pr(f"    of which live never filled: {len(ra_trades) - len(was)} · RA net "
           f"{np.mean([t['net'] for t in ra_trades if not t['live_filled']]) if len(ra_trades) > len(was) else float('nan'):+.3f}")

    # bars 2016-2023
    train = [p for p in gate if p["day"] < "2024-01-01"]
    by_day = defaultdict(list)
    for p in train:
        by_day[p["day"]].append({k: p[k] for k in ("sym", "arm", "entry", "stop", "pm", "dv5")})
    with Pool(4) as pool:
        rows = [r for rs in pool.imap(bar_job, sorted(by_day.items()), chunksize=8) for r in rs]
    d = np.array([r["ra"] - r["live"] for r in rows])
    re_ = [r for r in rows if r["re"]]
    pr(f"\n(3) 1-minute bars 2016-2023, reading C: plans {len(rows)} · RA − live mean {d.mean():+.4f} R a plan · "
       f"re-anchored {len(re_)} · their net {np.mean([r['ra'] for r in re_]) if re_ else float('nan'):+.3f} "
       f"vs live {np.mean([r['live'] for r in re_]) if re_ else float('nan'):+.3f}")

    ok = (lb > 0, bool(ra_trades) and float(np.mean([t["net"] for t in ra_trades])) > 0, d.mean() > 0)
    pr("\nDECISION: " + " · ".join(f"{'✓' if x else '✗'} {n}" for x, n in
                                    zip(ok, ("(1) lower bound > 0", "(2) re-anchored net > 0", "(3) bars 2016-23 > 0")))
       + ("  → RA built OFF, 200 prospective paper trades" if all(ok) else "  → the 2¢ band stays"))
    OUT.write_text("\n".join(lines) + "\n")
    print(f"written {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
