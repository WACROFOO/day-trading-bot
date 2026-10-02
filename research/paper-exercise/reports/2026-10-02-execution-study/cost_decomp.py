#!/usr/bin/env python3
"""Where the per-trade execution cost comes from (stage-1 tick replay, cached data only).

Universe: plans in data/cache/rules_audit_plans.pkl that pass RA.passes(p, RA.BASE)
and have a FILLED stage-1 outcome in data/cache/tick_outcomes.pkl.
Sizing: shares = max(1, min(int(40 // (entry-stop)), int(2000 // entry))).
1 R here = shares x (entry - stop) dollars.

Components, $ then / R:
  (1) comm      IBKR fixed both ways, per order min(max(1, .005 q), max(1, .01 q px))
  (2) sp_in     half the REAL spread at the fill (spread_in)
  (3) slip_in   (fill - entry) x shares            [already inside the replay's gross R]
  (4) sp_out    half the REAL spread at the exit, stop/trail exits only
  (5) slip_out  (level_at_exit - exit) x shares, stop/trail exits [inside gross R]
                level_at_exit recomputed by re-running the replay loop on cached ticks
  (6) m1c       the backtests' 1 cent per marketable side (reference only)
  total = (1)+(2)+(3)+(4)+(5);  modelled add-on (= tick_replay.cost_real) = (1)+(2)+(4)+(6)

No network: the Fetcher subclass raises on any request; a missing chunk skips the trade.
"""
from __future__ import annotations

import pickle
import sys
from collections import defaultdict
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path("/home/user/day-trading-bot")
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import rules_audit as RA  # noqa: E402
import tick_replay as TR  # noqa: E402

RISK, NOTIONAL = 40.0, 2000.0


class NoNet(Exception):
    pass


class CacheOnly(TR.Fetcher):
    def __init__(self):
        super().__init__(None)

    def _get(self, path, params):                     # any attempt to fetch = missing chunk
        raise NoNet(path)


# ---------------------------------------------------------------- instrumented copy of TR.replay
def replay_instr(ticks_t, ticks_p, entry, stop, t_order, flat_t, cap_pct=TR.CAP_PCT, ttl_s=TR.TTL_S,
                 trail_r=TR.TRAIL_R, trail_every=TR.TRAIL_EVERY_S):
    """Line-for-line TR.replay, plus `level` (the stop in force) at the exit."""
    cap = RA.cap_of(entry, cap_pct)
    rps = entry - stop
    if rps <= 0:
        return None
    i = int(np.searchsorted(ticks_t, t_order * 1000, side="left"))
    end_entry = (t_order + ttl_s) * 1000
    n = len(ticks_t)
    triggered = False
    fill_i = None
    while i < n and ticks_t[i] < end_entry:
        p = ticks_p[i]
        if not triggered and p >= entry:
            triggered = True
        if triggered and p <= cap:
            fill_i = i
            break
        i += 1
    if fill_i is None:
        return None
    fill = float(min(cap, max(entry, ticks_p[fill_i])))
    t_fill = int(ticks_t[fill_i])
    level, high = stop, fill
    next_trail = t_fill + trail_every * 1000
    j = fill_i + 1
    flat_ms = flat_t * 1000
    while j < n:
        tj, pj = int(ticks_t[j]), float(ticks_p[j])
        if tj >= flat_ms:
            return {"t_in": t_fill, "t_out": int(ticks_t[j - 1]), "fill": fill, "exit": float(ticks_p[j - 1]),
                    "stopish": False, "how": "flat", "level": level, "high": high, "fill_print": float(ticks_p[fill_i])}
        while tj >= next_trail:
            level = max(level, round(high - trail_r * rps, 4))
            next_trail += trail_every * 1000
        if pj <= level:
            return {"t_in": t_fill, "t_out": tj, "fill": fill, "exit": pj, "stopish": True,
                    "how": "trail" if level > stop else "stop", "level": level, "high": high,
                    "fill_print": float(ticks_p[fill_i]), "j_exit": j}
        high = max(high, pj)
        j += 1
    return {"t_in": t_fill, "t_out": int(ticks_t[n - 1]), "fill": fill, "exit": float(ticks_p[n - 1]),
            "stopish": False, "how": "end-of-data", "level": level, "high": high, "fill_print": float(ticks_p[fill_i])}


def job(p):
    """TR.replay_plan's chunk walk, cache only. Returns (key, result|None, status, check vs TR.replay)."""
    fx = CacheOnly()
    key = (p["sym"], p["arm"])
    day0 = TR.day_open(p["day"])
    t_order = p["arm"] + 60
    flat_t = TR.at_et(p["day"], TR.FLAT)
    k = (t_order - day0) // TR.CHUNK_S
    last_k = (flat_t - day0) // TR.CHUNK_S
    ts, ps = [], []
    out = None
    T = P = None
    try:
        while k <= last_k:
            t, pr = fx.chunk(p["sym"], p["day"], int(k), day0)
            ts.append(t); ps.append(pr)
            T, P = np.concatenate(ts), np.round(np.concatenate(ps).astype(np.float64), 4)
            out = replay_instr(T, P, p["entry"], p["stop"], t_order, flat_t)
            chunk_end = (day0 + (k + 1) * TR.CHUNK_S) * 1000
            if out is None and len(T) and T[-1] >= (t_order + TR.TTL_S) * 1000:
                return key, None, "unfilled", None
            if out is None and chunk_end >= (t_order + TR.TTL_S) * 1000:
                return key, None, "unfilled", None
            if out is not None and out["how"] != "end-of-data":
                break
            k += 1
    except NoNet:
        return key, None, "missing-chunk", None
    except FileNotFoundError:
        return key, None, "missing-chunk", None
    if out is None:
        return key, None, "unfilled", None
    ref = TR.replay(T, P, p["entry"], p["stop"], t_order, flat_t)       # the repo's own function, same ticks
    # diagnostic: the median of the 20 prints after the exit print (next cached chunk if needed)
    out["med20"] = None
    if out["stopish"]:
        j = out["j_exit"]
        nxt = list(P[j + 1:j + 21])
        if len(nxt) < 20:
            try:
                t2, p2 = fx.chunk(p["sym"], p["day"], int(k) + 1, day0)
                nxt += list(np.round(np.asarray(p2, dtype=np.float64), 4)[:20 - len(nxt)])
            except (NoNet, FileNotFoundError):
                pass
        if len(nxt) >= 5:
            out["med20"] = float(np.median(nxt))
    same = ref is not None and all(ref[x] == out[x] for x in ("t_in", "t_out", "fill", "exit", "how"))
    return key, out, "ok", same


# ---------------------------------------------------------------- costs
def comm_fixed(q, px):
    return min(max(1.0, 0.005 * q), max(1.0, 0.01 * q * px))


def comm_tiered(q, px):
    """HYPOTHETICAL tiered commission ONLY: $0.0035/sh, $0.35 min, 1 % cap (same min-over-cap shape as fixed).
    Exchange / clearing / regulatory pass-through fees: NAMED UNKNOWN, not included."""
    return min(max(0.35, 0.0035 * q), max(0.35, 0.01 * q * px))


COMP = ("comm", "sp_in", "slip_in", "sp_out", "slip_out", "total", "m1c")
LBL = {"comm": "(1)comm", "sp_in": "(2)½sp_in", "slip_in": "(3)slip_in", "sp_out": "(4)½sp_out",
       "slip_out": "(5)slip_out", "total": "Σ(1..5)", "m1c": "(6)1c ref"}


def et_hm(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).astimezone(RA.E.ET).strftime("%H:%M")


def bucket(x, edges, labels):
    for e, l in zip(edges, labels):
        if x < e:
            return l
    return labels[-1]


def fmt_cell(v):
    if len(v) == 0:
        return f"{'-':>13}"
    return f"{np.mean(v):>6.3f}|{np.median(v):<6.3f}"


def table(title, rows, keyf, order=None):
    g = defaultdict(list)
    for r in rows:
        g[keyf(r)].append(r)
    keys = order if order else sorted(g)
    print(f"\n== {title}   (cells: mean|median, R per trade)")
    print(f"  {'group':<20}{'n':>5} " + "".join(f"{LBL[c]:>14}" for c in COMP) + f"{'mod.addon':>14}")
    for k in keys:
        rs = g.get(k, [])
        if not rs:
            print(f"  {str(k):<20}{0:>5}")
            continue
        cells = "".join(f"{fmt_cell(np.array([r[c] for r in rs])):>14}" for c in COMP)
        addon = np.array([r["addon"] for r in rs])
        print(f"  {str(k):<20}{len(rs):>5} {cells}{fmt_cell(addon):>14}")


def main():
    plans = pickle.loads(RA.PLANS_CACHE.read_bytes())
    done = pickle.loads(TR.OUTCOMES.read_bytes())
    gate = [p for p in plans if RA.passes(p, RA.BASE)]
    have = [p for p in gate if (p["sym"], p["arm"]) in done]
    filled = [p for p in have if (done[(p["sym"], p["arm"])] or {}).get("filled")]
    print(f"plans in cache {len(plans)} · pass RA.BASE {len(gate)} · with stage-1 outcome {len(have)}"
          f" · filled {len(filled)}")

    slim = [{k: p[k] for k in ("sym", "day", "arm", "entry", "stop")} for p in filled]
    with Pool(4) as pool:
        res = {key: (out, st, same) for key, out, st, same in pool.imap_unordered(job, slim, chunksize=8)}
    stat = defaultdict(int)
    for out, st, same in res.values():
        stat[st] += 1
    print("re-replay status:", dict(stat))
    agree = sum(1 for out, st, same in res.values() if st == "ok" and same)
    print(f"instrumented copy == TR.replay on same ticks: {agree}/{stat['ok']}")
    cmp = defaultdict(int)
    for p in filled:
        key = (p["sym"], p["arm"])
        out, st, _ = res[key]
        if st != "ok":
            continue
        o = done[key]
        m = all(abs(o[x] - out[x]) < 1e-9 for x in ("fill", "exit")) and o["how"] == out["how"] \
            and o["t_in"] == out["t_in"] and o["t_out"] == out["t_out"]
        cmp["match cached outcome" if m else "DIFFERS from cached outcome"] += 1
    print("re-replay vs tick_outcomes.pkl:", dict(cmp))

    rows, skipped = [], defaultdict(int)
    for p in filled:
        key = (p["sym"], p["arm"])
        o = done[key]
        out, st, _ = res[key]
        if st != "ok":
            skipped[st] += 1; continue
        if not (abs(o["fill"] - out["fill"]) < 1e-9 and abs(o["exit"] - out["exit"]) < 1e-9 and o["how"] == out["how"]):
            skipped["re-replay differs"] += 1; continue
        if o.get("spread_in") is None or (o["stopish"] and o.get("spread_out") is None):
            skipped["no real spread"] += 1; continue
        e, s = p["entry"], p["stop"]
        rps = e - s
        sh = max(1, min(int(RISK // rps), int(NOTIONAL // e)))
        unit = sh * rps
        fill, ex = o["fill"], o["exit"]
        stopish = o["stopish"]
        comm = comm_fixed(sh, fill) + comm_fixed(sh, ex)
        tier = comm_tiered(sh, fill) + comm_tiered(sh, ex)
        sp_in = sh * o["spread_in"] / 2
        slip_in = sh * (fill - e)
        sp_out = sh * o["spread_out"] / 2 if stopish else 0.0
        slip_out = sh * (out["level"] - ex) if stopish else 0.0
        m1c = sh * 0.01 * (2 if stopish else 1)
        tot = comm + sp_in + slip_in + sp_out + slip_out
        # tick_replay.cost_real on the same plan, for cross-check
        q = dict(p, tick={"spread_in": o["spread_in"], "spread_out": o.get("spread_out")})
        cr = TR.cost_real(q, stopish)
        lv_above = (out["level"] - s) / rps
        how = o["how"]
        kind = how if how != "trail" else ("trail<=0.1R" if lv_above <= 0.1 + 1e-9 else "trail>0.1R")
        rows.append({
            "key": key, "day": p["day"], "t": p["t"], "sym": p["sym"], "entry": e, "stop": s, "rps": rps, "sh": sh,
            "pm_plan": p["pm"], "sess": "pre-market" if et_hm(o["t_in"]) < "09:30" else "regular",
            "stop_pct": p["stop_pct"], "ratio": o["spread_in"] / rps, "how": how, "kind": kind,
            "spread_in": o["spread_in"], "spread_out": o.get("spread_out"), "stopish": stopish,
            "comm": comm / unit, "sp_in": sp_in / unit, "slip_in": slip_in / unit, "sp_out": sp_out / unit,
            "slip_out": slip_out / unit, "m1c": m1c / unit, "total": tot / unit,
            "addon": (comm + sp_in + sp_out + m1c) / unit, "cost_real": cr, "tier": tier / unit,
            "comm_usd": comm, "tier_usd": tier, "slip_in_c": (fill - e) * 100, "slip_out_c": (out["level"] - ex) * 100,
            "level_above_stop_R": lv_above, "level": out["level"], "med20": out.get("med20"), "exit_px": ex, "gross": o["r"], "cap_c": (RA.cap_of(e, TR.CAP_PCT) - e) * 100,
        })
    print(f"skipped: {dict(skipped)} · analysed {len(rows)} filled trades")
    diff = np.array([abs(r["addon"] - r["cost_real"]) for r in rows])
    print(f"check: (1)+(2)+(4)+(6) vs tick_replay.cost_real · max |diff| {diff.max():.4f} R (cost_real rounds to 3 dp)")

    # ---------------------------------------------------------------- overall
    print("\n==== OVERALL (all filled gate-passing plans, R per trade)")
    print(f"  {'component':<14}{'mean':>8}{'median':>8}{'p90':>8}{'share of Σ mean':>17}{'mean ¢/sh':>11}{'med ¢/sh':>10}")
    tot_mean = np.mean([r["total"] for r in rows])
    for c in COMP:
        v = np.array([r[c] for r in rows])
        cps = np.array([r[c] * r["rps"] * 100 for r in rows])        # R x rps = $/sh -> cents/sh
        share = f"{100 * v.mean() / tot_mean:>15.1f}%" if c not in ("total", "m1c") else f"{'':>16}"
        print(f"  {LBL[c]:<14}{v.mean():>8.3f}{np.median(v):>8.3f}{np.quantile(v, .9):>8.3f}{share} "
              f"{cps.mean():>10.2f}{np.median(cps):>10.2f}")
    a = np.array([r["addon"] for r in rows])
    print(f"  {'mod.addon':<14}{a.mean():>8.3f}{np.median(a):>8.3f}{np.quantile(a, .9):>8.3f}"
          f"   (= cost_real: comm + ½spreads + 1c/side; slip_in/slip_out are inside gross R)")
    g = np.array([r["gross"] for r in rows])
    print(f"  gross R (replay) mean {g.mean():+.3f} median {np.median(g):+.3f} · shares median "
          f"{np.median([r['sh'] for r in rows]):.0f} · 1R $ median {np.median([r['sh'] * r['rps'] for r in rows]):.2f}"
          f" · notional-capped {np.mean([r['sh'] * r['rps'] < 39.0 for r in rows]) * 100:.1f}% of trades (1R < $39)")

    # ---------------------------------------------------------------- splits
    table("session at the fill (ET)", rows, lambda r: r["sess"], ["pre-market", "regular"])
    table("plan armed pre-market (plan pm flag)", rows, lambda r: "pm" if r["pm_plan"] else "rth", ["pm", "rth"])
    pl = ["$2-3", "$3-5", "$5-10", "$10-20", ">=$20"]
    table("price (entry)", rows, lambda r: bucket(r["entry"], [3, 5, 10, 20, 1e9], pl), pl)
    sl = ["<2%", "2-3%", "3-5%", ">=5%"]
    table("stop % of price", rows, lambda r: bucket(r["stop_pct"], [2, 3, 5, 1e9], sl), sl)
    rl = ["<0.05", "0.05-0.10", "0.10-0.25", "0.25-0.50", ">=0.50"]
    table("REAL spread_in / stop distance", rows, lambda r: bucket(r["ratio"], [.05, .10, .25, .50, 1e9], rl), rl)
    shl = ["1-99", "100-199", "200-399", "400-699", "700+"]
    table("shares", rows, lambda r: bucket(r["sh"], [100, 200, 400, 700, 1e9], shl), shl)
    kl = ["stop", "trail<=0.1R", "trail>0.1R", "flat"]
    table("exit kind (trail split by level above initial stop)", rows, lambda r: r["kind"], kl)
    table("whatif split: stop<3% OR fill pre-09:30", rows,
          lambda r: "stop<3% or pm" if (r["stop_pct"] < 3 or r["sess"] == "pre-market") else "rest",
          ["stop<3% or pm", "rest"])
    table("year", rows, lambda r: r["day"][:4])

    # ---------------------------------------------------------------- exit slippage
    ex = [r for r in rows if r["stopish"]]
    s = np.array([r["slip_out"] for r in ex])
    sc = np.array([r["slip_out_c"] for r in ex])
    print(f"\n==== EXIT SLIPPAGE beyond the level (stop/trail exits, n {len(ex)})")
    print(f"  R:     p50 {np.quantile(s, .5):.3f} · p75 {np.quantile(s, .75):.3f} · p90 {np.quantile(s, .9):.3f}"
          f" · p95 {np.quantile(s, .95):.3f} · p99 {np.quantile(s, .99):.3f} · max {s.max():.3f} · mean {s.mean():.3f}")
    print(f"  cents: p50 {np.quantile(sc, .5):.2f} · p75 {np.quantile(sc, .75):.2f} · p90 {np.quantile(sc, .9):.2f}"
          f" · p95 {np.quantile(sc, .95):.2f} · p99 {np.quantile(sc, .99):.2f} · max {sc.max():.2f}")
    print(f"  exits at exactly the level (0 slip): {np.mean(sc < 1e-6) * 100:.1f}% · <=1c: {np.mean(sc <= 1 + 1e-6) * 100:.1f}%"
          f" · >5c: {np.mean(sc > 5 + 1e-6) * 100:.1f}%")
    order = np.argsort(-s)
    k10 = int(np.ceil(0.10 * len(ex)))
    worst = [ex[i] for i in order[:k10]]
    tot_all = sum(r["total"] for r in rows)
    print(f"  worst 10% of exits by slip (n {k10}): carry {100 * s[order[:k10]].sum() / s.sum():.1f}% of all exit slippage"
          f" and {100 * s[order[:k10]].sum() / tot_all:.1f}% of total cost Σ(1..5) over all {len(rows)} trades;"
          f" their own Σ(1..5) = {100 * sum(r['total'] for r in worst) / tot_all:.1f}% of the total")
    print(f"  worst-10% profile: slip median {np.median([r['slip_out'] for r in worst]):.3f} R"
          f" ({np.median([r['slip_out_c'] for r in worst]):.1f}c) · entry median ${np.median([r['entry'] for r in worst]):.2f}"
          f" (all ${np.median([r['entry'] for r in ex]):.2f}) · stop% median {np.median([r['stop_pct'] for r in worst]):.2f}"
          f" (all {np.median([r['stop_pct'] for r in ex]):.2f}) · fill pre-market {100 * np.mean([r['sess'] == 'pre-market' for r in worst]):.0f}%"
          f" (all {100 * np.mean([r['sess'] == 'pre-market' for r in ex]):.0f}%) · real spread/stop median"
          f" {np.median([r['ratio'] for r in worst]):.3f} (all {np.median([r['ratio'] for r in ex]):.3f})")
    print(f"  worst-10% exit kinds: {dict(sorted(defaultdict(int, {k: sum(1 for r in worst if r['kind'] == k) for k in kl}).items()))}")
    for nm, f in (("pre-market", lambda r: r["sess"] == "pre-market"), ("regular", lambda r: r["sess"] == "regular")):
        v = np.array([r["slip_out"] for r in ex if f(r)])
        if len(v):
            print(f"  {nm:<11} n {len(v):>4} · p50 {np.quantile(v, .5):.3f} · p90 {np.quantile(v, .9):.3f} · p99 {np.quantile(v, .99):.3f} R")
    pm_share = sum(r["slip_out"] for r in ex if r["sess"] == "pre-market") / s.sum()
    print(f"  share of all exit slippage (R) from pre-market fills: {100 * pm_share:.1f}%"
          f" (they are {100 * np.mean([r['sess'] == 'pre-market' for r in ex]):.1f}% of exits)")
    print("  the 12 largest exit slips:")
    print(f"    {'day':<11}{'sym':<6}{'t':<6}{'sess':<11}{'entry':>7}{'stop':>7}{'level':>8}{'exit':>8}{'slip c':>8}"
          f"{'slip R':>8}{'sp_out':>7}{'sh':>5}  kind")
    for i in order[:12]:
        r = ex[i]
        print(f"    {r['day']:<11}{r['sym']:<6}{r['t']:<6}{r['sess']:<11}{r['entry']:>7.2f}{r['stop']:>7.2f}"
              f"{r['entry'] - r['rps'] + r['level_above_stop_R'] * r['rps']:>8.3f}"
              f"{r['entry'] - r['rps'] + r['level_above_stop_R'] * r['rps'] - r['slip_out_c'] / 100:>8.3f}"
              f"{r['slip_out_c']:>8.2f}{r['slip_out']:>8.3f}{r['spread_out']:>7.3f}{r['sh']:>5}  {r['kind']:<12} med20 {r['med20']}")
    # off-market exit prints (HEURISTIC, my definition): the median of the next 20 prints is back at/above the
    # level AND the exit print sits more than X % under that median
    known = [r for r in ex if r["med20"] is not None]
    print(f"  off-market exit print heuristic: med20 (median of the 20 prints after the exit print) >= level"
          f" AND exit < med20 x (1 - X); med20 unknown for {len(ex) - len(known)} exits")
    for X in (0.03, 0.10):
        off = [r for r in known if r["med20"] >= r["level"] - 1e-9 and r["exit_px"] < r["med20"] * (1 - X)]
        ids = {id(r) for r in off}
        rest = np.array([r["slip_out"] for r in ex if id(r) not in ids])
        big = [r for r in known if r["slip_out"] > 0.5]
        print(f"   X={X:.0%}: {len(off)} exits (pre-market {sum(r['sess'] == 'pre-market' for r in off)}, regular"
              f" {sum(r['sess'] == 'regular' for r in off)}) carry {100 * sum(r['slip_out'] for r in off) / s.sum():.1f}%"
              f" of exit slippage · of the {len(big)} exits with slip > 0.5 R, {sum(id(r) in ids for r in big)} flagged")
        print(f"          exit slip without them (n {len(rest)}): mean {rest.mean():.3f} · p50 {np.quantile(rest, .5):.3f}"
              f" · p90 {np.quantile(rest, .9):.3f} · p99 {np.quantile(rest, .99):.3f} · max {rest.max():.3f} R"
              f" · Σ(1..5) mean would be {(sum(r['total'] for r in rows) - sum(r['slip_out'] for r in off)) / len(rows):.3f} R")
    print("  (an off-market print also ENDS the replayed trade, so it moves gross R too; not re-simulated here)")
    lv = np.array([r["level_above_stop_R"] for r in ex])
    print(f"  level in force at exit, above the initial stop (R): p25 {np.quantile(lv, .25):.3f} · p50 {np.quantile(lv, .5):.3f}"
          f" · p75 {np.quantile(lv, .75):.3f} · p90 {np.quantile(lv, .9):.3f}")

    # ---------------------------------------------------------------- fills
    unf = [p for p in have if not (done[(p["sym"], p["arm"])] or {}).get("filled")]
    print(f"\n==== FILLS · gate-passing plans with an outcome {len(have)} · filled {len(filled)}"
          f" ({100 * len(filled) / len(have):.1f}%) · unfilled {len(unf)}")
    for nm, f in (("plan pm", lambda p: p["pm"]), ("plan rth", lambda p: not p["pm"])):
        h = [p for p in have if f(p)]
        fl = [p for p in h if (done[(p["sym"], p["arm"])] or {}).get("filled")]
        print(f"  {nm:<9} fill rate {len(fl)}/{len(h)} = {100 * len(fl) / max(1, len(h)):.1f}%")
    for lo, hi_, nm in ((2, 3, "$2-3"), (3, 5, "$3-5"), (5, 10, "$5-10"), (10, 20.01, "$10-20")):
        h = [p for p in have if lo <= p["entry"] < hi_]
        fl = [p for p in h if (done[(p["sym"], p["arm"])] or {}).get("filled")]
        print(f"  {nm:<9} fill rate {len(fl)}/{len(h)} = {100 * len(fl) / max(1, len(h)):.1f}%")
    fc = np.array([r["slip_in_c"] for r in rows])
    fr = np.array([r["slip_in"] for r in rows])
    capc = np.array([r["cap_c"] for r in rows])
    print(f"  fill - trigger, cents: p50 {np.quantile(fc, .5):.2f} · p75 {np.quantile(fc, .75):.2f} · p90 {np.quantile(fc, .9):.2f}"
          f" · p99 {np.quantile(fc, .99):.2f} · max {fc.max():.2f} · mean {fc.mean():.2f}")
    print(f"  fill - trigger, R:     p50 {np.quantile(fr, .5):.3f} · p90 {np.quantile(fr, .9):.3f} · p99 {np.quantile(fr, .99):.3f}"
          f" · mean {fr.mean():.3f}")
    print(f"  at exactly the trigger {100 * np.mean(fc < 1e-6):.1f}% · at the cap {100 * np.mean(np.abs(fc - capc) < 1e-6):.1f}%"
          f" · in between {100 * np.mean((fc > 1e-6) & (np.abs(fc - capc) >= 1e-6)):.1f}% · cap offset median {np.median(capc):.2f}c")

    # ---------------------------------------------------------------- A6 with the real spread
    rin = np.array([r["ratio"] for r in rows])
    print(f"\n==== A6 (stop >= 4 x spread) with the REAL spread · all {len(rows)} trades passed it on the PROXY spread")
    print(f"  spread_in > stop/4 (A6 would fail): {int((rin > 0.25).sum())} = {100 * np.mean(rin > 0.25):.1f}%"
          f" · pre-market fills {100 * np.mean([r['ratio'] > 0.25 for r in rows if r['sess'] == 'pre-market']):.1f}%"
          f" · regular {100 * np.mean([r['ratio'] > 0.25 for r in rows if r['sess'] == 'regular']):.1f}%")
    ro = np.array([r["spread_out"] / r["rps"] for r in ex])
    print(f"  spread_out > stop/4 at stop/trail exits: {100 * np.mean(ro > 0.25):.1f}%")
    a6f = [r for r in rows if r["ratio"] > 0.25]
    a6p = [r for r in rows if r["ratio"] <= 0.25]
    print(f"  Σ(1..5) mean: real-A6 fail {np.mean([r['total'] for r in a6f]):.3f} R (n {len(a6f)})"
          f" vs pass {np.mean([r['total'] for r in a6p]):.3f} R (n {len(a6p)})")
    print(f"  real spread_in cents: p50 {np.median([r['spread_in'] for r in rows]) * 100:.2f} · p90"
          f" {np.quantile([r['spread_in'] for r in rows], .9) * 100:.2f}")

    # ---------------------------------------------------------------- tiered (commission part only)
    cf = np.array([r["comm"] for r in rows]); ct = np.array([r["tier"] for r in rows])
    cfu = np.array([r["comm_usd"] for r in rows]); ctu = np.array([r["tier_usd"] for r in rows])
    print("\n==== COMMISSION: fixed vs HYPOTHETICAL tiered ($0.0035/sh, $0.35 min, 1% cap) — COMMISSION PART ONLY;"
          "\n     tiered exchange/clearing/regulatory pass-through fees = NAMED UNKNOWN, NOT INCLUDED")
    print(f"  fixed  round trip: mean ${cfu.mean():.2f} median ${np.median(cfu):.2f} · mean {cf.mean():.3f} R median {np.median(cf):.3f} R")
    print(f"  tiered round trip: mean ${ctu.mean():.2f} median ${np.median(ctu):.2f} · mean {ct.mean():.3f} R median {np.median(ct):.3f} R"
          f"   (+ unknown pass-through)")
    for lab, lo, hi_ in (("1-99", 1, 100), ("100-199", 100, 200), ("200-399", 200, 400), ("400-699", 400, 700), ("700+", 700, 10 ** 9)):
        sel = [r for r in rows if lo <= r["sh"] < hi_]
        if sel:
            print(f"  shares {lab:<8} n {len(sel):>4} · fixed {np.mean([r['comm'] for r in sel]):.3f} R"
                  f" · tiered-commission-only {np.mean([r['tier'] for r in sel]):.3f} R"
                  f" · break-even pass-through for tiered = {np.mean([(r['comm_usd'] - r['tier_usd']) / (2 * r['sh']) for r in sel]) * 100:.3f}c/sh/side")

    # ---------------------------------------------------------------- portfolio B subset (cross-check)
    TR.attach(plans, done)
    by_day = defaultdict(list)
    for p in plans:
        if p["day"] >= "2024-01-01":
            by_day[p["day"]].append(p)
    days = sorted({p["day"] for ps in by_day.values() for p in ps if ("T", "base") in p["out"]})
    full = {d for d in days if all(("T", "base") in p["out"] for p in by_day[d] if RA.passes(p, RA.BASE))}
    sub = {d: by_day[d] for d in full}
    trades = RA.portfolio(sub, dict(RA.BASE, mode="T", costs="none"))
    idx = {(r["sym"], r["day"], r["t"]): r for r in rows}
    pb = [idx[(t["sym"], t["day"], t["t"])] for t in trades if (t["sym"], t["day"], t["t"]) in idx]
    print(f"\n==== PORTFOLIO B subset (one position, daily limits; {len(trades)} trades, {len(pb)} analysed)")
    print(f"  {'component':<14}{'mean':>8}{'median':>8}")
    for c in COMP + ("addon",):
        v = np.array([r[c] for r in pb])
        print(f"  {LBL.get(c, 'mod.addon'):<14}{v.mean():>8.3f}{np.median(v):>8.3f}")
    print(f"  cost_real (repo fn) mean {np.mean([r['cost_real'] for r in pb]):.3f} median {np.median([r['cost_real'] for r in pb]):.3f}")


if __name__ == "__main__":
    main()
