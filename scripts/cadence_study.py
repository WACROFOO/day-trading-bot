#!/usr/bin/env python3
"""Reaction speed: how much acting faster than the live desk would change the
result, pre-market and regular hours. Preregistered as addendum 2026-10-02d in
research/edge-hunt/PREREGISTRATION.md before any run.

Two knobs, every combination re-simulated on the SIP prints of the stage-3 D
trades (desk-time plans passing the live gates with a measured D fill):

  ARMING  when the order goes in after the first print above the trigger:
          10-s candle close + 4 s (live: the desk sees closed 10-s candles; the
          runner's measured pickup is 3-4 s), 10-s close + 1 s, 5-s close +
          2.5 s, the crossing print + 1 s.
  LOOP    the runner's period: pre-market it samples the tape to trigger the
          entry and to check the monitored stop; in both sessions it moves the
          A3 trail. 1, 2, 5 (live), 10 s, and 0 = every print (a bound).

Pre-market (filled before 09:30) the entry is runner-triggered (a sample at or
above the trigger sends a limit at the cap) and the stop is monitored (a
sample at or under the level sells at that sample's last print; the cost
model adds half the real spread + 1 cent). Regular hours the entry is a
resting stop-limit and the stop rests at the broker: both trigger on the first
print through them; only the trail moves at the loop period. Gates stay as
the desk judged them, so only timing moves.

    python3 scripts/cadence_study.py [--since 2024-01-01] [--procs 4]
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import desk_replay as DR  # noqa: E402
import rules_audit as RA  # noqa: E402
import stage3 as S3  # noqa: E402
import tick_replay as TR  # noqa: E402

ARMS = {"10s+4 live": ("candle", 10, 4.0), "10s+1": ("candle", 10, 1.0),
        "5s+2.5": ("candle", 5, 2.5), "print+1": ("print", 0, 1.0)}
LOOPS = {"1s": 1, "2s": 2, "5s live": 5, "10s": 10, "every print": 0}
LIVE = ("10s+4 live", "5s live")


def order_time(arm_s: int, t_cross: int, kind: str, width: int, lat: float) -> int:
    """ms when the order goes in."""
    if kind == "print":
        return int(t_cross + lat * 1000)
    a0, w = arm_s * 1000, width * 1000
    return int(a0 + w * ((t_cross - a0) // w + 1) + lat * 1000)


def _samples(t0: int, t1: int, period: int):
    return np.arange(t0, t1, period * 1000, dtype=np.int64) if period else None


def entry(T, P, entry_px: float, t_order: int, rth_ms: int, period: int):
    """(index, fill) or None. Before 09:30 the runner samples the tape and
    sends a limit at the cap when a sample is at or above the trigger; from
    09:30 a stop-limit rests and the first print through it triggers."""
    cap = RA.cap_of(entry_px, TR.CAP_PCT)
    t_end = t_order + TR.TTL_S * 1000
    i0 = int(np.searchsorted(T, t_order, "left"))
    i1 = int(np.searchsorted(T, t_end, "left"))
    if i0 >= i1:
        return None
    if t_order < rth_ms and period:
        s = _samples(t_order, t_end, period)
        j = np.searchsorted(T, s, "right") - 1
        ok = (j >= 0) & (P[np.clip(j, 0, None)] >= entry_px)
        hit = np.nonzero(ok)[0]
        if not len(hit):
            return None
        start = int(np.searchsorted(T, s[hit[0]], "left"))
        seg = P[start:i1]
        k = np.nonzero(seg <= cap)[0]
        if not len(k):
            return None
        i = start + int(k[0])
        return i, float(min(cap, max(entry_px, P[i])))
    seg = P[i0:i1]
    trig = np.nonzero(seg >= entry_px)[0]
    if not len(trig):
        return None
    after = seg[trig[0]:]
    k = np.nonzero(after <= cap)[0]
    if not len(k):
        return None
    i = i0 + int(trig[0]) + int(k[0])
    return i, float(min(cap, max(entry_px, P[i])))


def exit_(T, P, i_fill: int, fill: float, entry_px: float, stop: float, flat_ms: int,
          monitored: bool, period: int):
    """(exit price, kind, t_out ms) or None when the tape runs out first."""
    rps = entry_px - stop
    i_end = int(np.searchsorted(T, flat_ms, "left"))
    if i_end <= i_fill + 1:
        return (float(P[i_end - 1]), "flat", int(T[i_end - 1])) if i_end - 1 > i_fill else None
    t_fill = int(T[i_fill])
    seg_t, seg_p = T[i_fill + 1:i_end], P[i_fill + 1:i_end]
    hi = np.maximum.accumulate(np.concatenate([[fill], seg_p]))     # hi[k] = high up to print k-1 of seg
    if not period:
        lvl = np.maximum(stop, np.maximum.accumulate(np.round(hi[:-1] - rps, 4)))
        k = np.nonzero(seg_p <= lvl)[0]
        if len(k):
            kk = int(k[0])
            return float(seg_p[kk]), ("trail" if lvl[kk] > stop else "stop"), int(seg_t[kk])
    else:
        upd = _samples(t_fill + period * 1000, flat_ms, period)
        # level after each loop: the trail uses the high of the prints before it
        j = np.searchsorted(seg_t, upd, "right")                    # prints seen by update u
        upd_lvl = np.maximum(stop, np.maximum.accumulate(np.round(hi[j] - rps, 4))) if len(upd) else np.array([])
        if monitored:
            # each loop: check the last print against the level in force, then move the trail
            last = j - 1
            ok = last >= 0
            prev_lvl = np.concatenate([[stop], upd_lvl[:-1]]) if len(upd) else np.array([])
            px = np.where(ok, seg_p[np.clip(last, 0, None)], np.inf)
            k = np.nonzero(px <= prev_lvl)[0]
            if len(k):
                kk = int(k[0])
                return float(px[kk]), ("trail" if prev_lvl[kk] > stop else "stop"), int(upd[kk])
        else:
            # a resting stop: every print is checked against the level last moved to
            which = np.searchsorted(upd, seg_t, "right") - 1
            lvl = np.where(which >= 0, upd_lvl[np.clip(which, 0, None)] if len(upd) else stop, stop)
            k = np.nonzero(seg_p <= lvl)[0]
            if len(k):
                kk = int(k[0])
                return float(seg_p[kk]), ("trail" if lvl[kk] > stop else "stop"), int(seg_t[kk])
    if T[i_end - 1] >= flat_ms - 60_000 or i_end < len(T):
        return float(P[i_end - 1]), "flat", int(T[i_end - 1])
    return None


class _CacheOnly(TR.Fetcher):
    def _get(self, path, params):
        raise RuntimeError("chunk not cached")


def run_plan(args):
    p, d, spreads = args
    fx = _CacheOnly(None)
    flat_s = TR.at_et(p["day"], TR.FLAT)
    rth_ms = TR.at_et(p["day"], "09:30") * 1000
    # Every cached chunk from the crossing onward, up to the first one not
    # cached (the stage-1..3 fetches stopped at each variant's exit). A
    # combination whose exit falls past the cached tape is reported as None.
    day0 = TR.day_open(p["day"])
    k0 = (int(d["t_cross"]) // 1000 - 60 - day0) // TR.CHUNK_S
    k1 = (flat_s - day0) // TR.CHUNK_S
    ts, ps = [], []
    for k in range(int(k0), int(k1) + 1):
        try:
            t, pr = fx.chunk(p["sym"], p["day"], k, day0)
        except Exception:                                               # noqa: BLE001
            break
        ts.append(t); ps.append(pr)
    if not ts:
        return (p["sym"], p["arm"]), None
    T, P = np.concatenate(ts), np.concatenate(ps).astype(np.float64)
    s_in, s_out = spreads
    res = {}
    for an, (kind, width, lat) in ARMS.items():
        t_order = order_time(p["arm"], int(d["t_cross"]), kind, width, lat)
        for ln, period in LOOPS.items():
            if t_order >= flat_s * 1000:
                res[(an, ln)] = None
                continue
            e = entry(T, P, p["entry"], t_order, rth_ms, period)
            if e is None:
                res[(an, ln)] = {"filled": False}
                continue
            i, fill = e
            pre = int(T[i]) < rth_ms
            x = exit_(T, P, i, fill, p["entry"], p["stop"], flat_s * 1000, pre, period)
            if x is None:
                res[(an, ln)] = None
                continue
            px, kindx, t_out = x
            g, c, stopish = S3.price_trade(p["entry"], p["stop"], fill, [(1.0, px, kindx)], s_in, s_out)
            res[(an, ln)] = {"filled": True, "t_in": int(T[i]) // 1000, "t_out": t_out // 1000, "gross": g,
                             "cost": c, "stopish": stopish, "fill": fill, "pre": pre}
    return (p["sym"], p["arm"]), res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default="2024-01-01")
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--json", default=str(ROOT / "research" / "paper-exercise" / "reports" / "cadence_results.json"))
    args = ap.parse_args(argv)
    RA.E.COST_MODEL = "live"
    desk = pickle.loads(DR.OUTCOMES.read_bytes())
    plans = TR.load_plans(args.since, None)
    by_key = {(p["sym"], p["arm"]): p for p in plans}
    jobs = []
    for key, d in desk.items():
        if "t_order" not in d or d["red"] or d["fade"] > RA.BASE["fade"] or key not in by_key:
            continue
        o = d.get("out") or {}
        if not o.get("filled") or o.get("spread_in") is None:
            continue
        jobs.append((by_key[key], d, (o["spread_in"], o.get("spread_out") or o["spread_in"])))
    with Pool(args.procs) as pool:
        out = dict(pool.imap_unordered(run_plan, jobs, chunksize=8))
    skipped = {k for k, v in out.items() if v is None or any(x is None for x in v.values())}
    DR.attach(plans, desk)
    by_day = defaultdict(list)
    for p in plans:
        by_day[p["day"]].append(p)
    run_keys = {k for k in out} - skipped
    jobkeys = {(j[0]["sym"], j[0]["arm"]) for j in jobs}
    days = sorted(day for day, ps in by_day.items()
                  if any((p["sym"], p["arm"]) in jobkeys for p in ps)
                  and all((p["sym"], p["arm"]) in run_keys for p in ps if (p["sym"], p["arm"]) in jobkeys))
    print(f"reaction speed · {len(jobs)} desk-time plans · {len(skipped)} skipped (tape not cached) · "
          f"{len(days)} complete sessions {days[0]}..{days[-1]} · real spreads, $40 / $2,000")
    table = {}
    for an in ARMS:
        for ln in LOOPS:
            sub = {}
            for day in days:
                ps = []
                for p in by_day[day]:
                    q = dict(p, out=dict(p["out"]))
                    r = out.get((p["sym"], p["arm"])) if (p["sym"], p["arm"]) in run_keys else None
                    if r is None:
                        q["desk"] = None
                    else:
                        o = r[(an, ln)]
                        q["out"][("Q", "base")] = ((o["t_in"], o["t_out"], o["gross"], o["stopish"], o["fill"])
                                                   if o.get("filled") else None)
                        q["_q"] = o
                    ps.append(q)
                sub[day] = ps
            trades = []
            for t in RA.portfolio(sub, dict(RA.BASE, mode="Q", gates="desk", costs="none")):
                q = next(x for x in sub[t["day"]] if x["sym"] == t["sym"] and x["t"] == t["t"])
                trades.append(dict(t, net=t["gross"] - q["_q"]["cost"], pre=q["_q"]["pre"]))
            table[(an, ln)] = trades
    res = {}
    for seg, pick in (("ALL", lambda t: True), ("PRE-MARKET fills", lambda t: t["pre"]),
                      ("REGULAR-HOURS fills", lambda t: not t["pre"])):
        print(f"\n  {seg}: net R per trade (n) — rows arming, columns loop period")
        print(f"  {'arming':<14}" + "".join(f"{ln:>18}" for ln in LOOPS))
        for an in ARMS:
            cells = []
            for ln in LOOPS:
                tr = [t for t in table[(an, ln)] if pick(t)]
                s = RA.stats(tr)
                res[f"{seg}|{an}|{ln}"] = {"stats": s, "years": {y: RA.stats([t for t in tr if t["day"][:4] == y])
                                                                 for y in ("2024", "2025", "2026")}}
                cells.append(f"{s.get('mean', float('nan')):+.3f} ({s.get('n', 0)})")
            print(f"  {an:<14}" + "".join(f"{c:>18}" for c in cells))
    print("\n  by year, against the live setting (10s+4, 5 s loop), net R per trade:")
    for seg in ("PRE-MARKET fills", "REGULAR-HOURS fills"):
        base = res[f"{seg}|{LIVE[0]}|{LIVE[1]}"]["years"]
        print(f"  {seg}:  live " + " ".join(f"{y} {base[y].get('mean', float('nan')):+.3f}" for y in base))
        for an in ARMS:
            for ln in LOOPS:
                if (an, ln) == LIVE:
                    continue
                yrs = res[f"{seg}|{an}|{ln}"]["years"]
                better = all(yrs[y].get("n", 0) and base[y].get("n", 0) and yrs[y]["mean"] > base[y]["mean"]
                             for y in yrs)
                if better:
                    print(f"     better every year: {an:<12} loop {ln:<12} "
                          + " ".join(f"{y} {yrs[y]['mean']:+.3f}" for y in yrs))
    Path(args.json).write_text(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
