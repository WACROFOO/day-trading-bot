#!/usr/bin/env python3
"""E1 — the first 5-minute candle to make a new high; B30 — the MACD warm-up.

Preregistered in research/edge-hunt/PREREGISTRATION.md, addendum 2026-10-06b,
committed with this script before it first ran. The owner's question: a name
climbing in green 1-minute candles never gets a plan, because the desk's detector
needs a red 1-minute candle. The method's answer is the 5-minute chart — wait for
the 5-minute pullback, buy the first 5-minute candle to make a new high, stop at
the pullback's low (`Xdw5azEqs6o` [00:12:38]).

E1 runs `FirstPullbackDetector`'s rules on clock-aligned 5-minute candles built
from the cached 1-minute bars, with one difference that makes it executable: the
stop-limit RESTS during the candle after each pullback candle (the break is
bought intrabar, as A10 does on the 1-minute), instead of arming after the break
has already printed. Fills, exits, costs, the portfolio and the bootstrap are
`rules_audit`'s.

B30 measures the plans B refuses only because the MACD could not be computed yet
(fewer than 35 one-minute bars since 04:00).

    python3 scripts/five_minute.py                 # every session (~10-20 min on 4 cores)
    python3 scripts/five_minute.py --sample 40     # a seeded smoke sample
"""
from __future__ import annotations

import argparse
import json
import pickle
import random
import sys
from collections import defaultdict
from datetime import datetime, time as dtime, timezone
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

import backtest_history as H  # noqa: E402
import backtest_recent as E  # noqa: E402
import rules_audit as RA  # noqa: E402
from momentum_platform import indicators as I  # noqa: E402

OUT = ROOT / "research" / "paper-exercise" / "reports"
TRAIN_END, GATE_YEAR, HOLDOUT = "2023-01-01", "2023", "2024-01-01"
ORDER_START, ORDER_END = "07:00", "11:20"
CANDLE_S = 300
TTL_MIN = 5                     # the order lives for the next 5-minute candle
MIN_IMPULSE, MAX_IMPULSE, MIN_RANGE_PCT, MAX_PULLBACK = 2, 6, 2.0, 4     # FirstPullbackDetector defaults
EXT_GREEN = 4                   # the owner's case: >= 4 consecutive green 1-minute bars, the last at a new high of day
RANDOM_K, RANDOM_SEED = 20, 20261006
ALPHA_STAGE, ALPHA_HOLDOUT, ALPHA_B30 = 0.05, 0.0042, 0.05 / 2
MACD_MIN = I.MACD_MIN


# ------------------------------------------------------------------ candles
def candles5(rows: list) -> list[dict]:
    """Clock-aligned 5-minute candles from 1-minute rows (ts = bar open, ET).
    Each carries the indices of its 1-minute bars."""
    out: list[dict] = []
    for i, (ts, o, h, l, c, v) in enumerate(rows):
        slot = int(ts.timestamp()) // CANDLE_S * CANDLE_S
        if out and out[-1]["t"] == slot:
            k = out[-1]
            k["h"], k["l"], k["c"], k["v"] = max(k["h"], h), min(k["l"], l), c, k["v"] + v
            k["last"] = i
        else:
            out.append({"t": slot, "o": o, "h": h, "l": l, "c": c, "v": v, "first": i, "last": i})
    return out


def _green(k: dict) -> bool:
    return k["c"] > k["o"]


def _impulse_ok(imp: list[dict]) -> bool:
    if len(imp) < MIN_IMPULSE or imp[0]["o"] <= 0:
        return False
    return 100.0 * (max(k["h"] for k in imp) - imp[0]["o"]) / imp[0]["o"] >= MIN_RANGE_PCT


def extended_inside(rows: list, i0: int, i1: int) -> bool:
    """The owner's case: in rows[i0..i1] a run of >= EXT_GREEN consecutive green
    1-minute bars whose last bar made a new high of day (high above every high
    since 04:00 before it)."""
    hod = max((r[2] for r in rows[:i0]), default=float("-inf"))
    run = 0
    for j in range(i0, i1 + 1):
        ts, o, h, l, c, v = rows[j]
        new_high = h > hod
        hod = max(hod, h)
        run = run + 1 if c > o else 0
        if run >= EXT_GREEN and new_high:
            return True
    return False


def e1_placements(rows: list) -> list[dict]:
    """Every E1 order placement of a symbol-day, in time order: at the close of
    each pullback candle, a stop-limit at its high + 1c, stop at the pullback low
    - 1c, resting during the next candle. Mirrors FirstPullbackDetector on
    5-minute candles; `seq` numbers the setups (pullbacks) of the day."""
    ks = candles5(rows)
    out: list[dict] = []
    imp: list[dict] = []
    pull: list[dict] = []
    seq = 0
    state = "seek"
    for k in ks:
        if state == "pull":
            if k["h"] > pull[-1]["h"]:
                # the first candle to make a new high: the resting order met its trigger
                # (filled or not, the setup ends here, as the detector's does)
                state, imp, pull = "seek", [], []
                if _green(k):
                    imp = [k]
                continue
            pull.append(k)
            if len(pull) > MAX_PULLBACK:
                state, imp, pull = "seek", ([k] if _green(k) else []), []
                continue
            if min(p["l"] for p in pull) < min(p["l"] for p in pull[:-1]) and k["l"] < min(b["l"] for b in imp):
                state, imp, pull = "seek", [], []
                continue
            out.append(_placement(rows, imp, pull, seq))
            continue
        # seek
        if _green(k):
            imp.append(k)
            del imp[:-MAX_IMPULSE]
        elif _impulse_ok(imp):
            seq += 1
            state, pull = "pull", [k]
            out.append(_placement(rows, imp, pull, seq))
        else:
            imp = []
    return out


def _placement(rows: list, imp: list[dict], pull: list[dict], seq: int) -> dict:
    last = pull[-1]
    entry = round(last["h"] + 0.01, 4)
    stop = round(min(p["l"] for p in pull) - 0.01, 4)
    order_t = last["t"] + CANDLE_S
    i_last = last["last"]
    imp_v = sum(k["v"] for k in imp) / len(imp)
    pull_v = sum(k["v"] for k in pull) / len(pull)
    return {"entry": entry, "stop": stop, "order_t": order_t, "i_last": i_last, "seq": seq,
            "volume_ok": pull_v < imp_v, "ext": extended_inside(rows, imp[0]["first"], i_last),
            "n_pull": len(pull)}


# ------------------------------------------------------------------ one symbol-day
def _fwd_from(rows: list, t: int) -> list:
    return [r for r in rows if int(r[0].timestamp()) >= t]


def e1_plans(sym: str, day: str, rows: list) -> list[dict]:
    out = []
    hist = [[int(r[0].timestamp()), r[1], r[2], r[3], r[4], r[5]] for r in rows]
    for pl in e1_placements(rows):
        i = pl["i_last"]
        ts = rows[i][0]
        arm_ts = pl["order_t"] - 60
        t = datetime.fromtimestamp(arm_ts, timezone.utc).astimezone(E.ET).strftime("%H:%M")
        entry, stop = pl["entry"], pl["stop"]
        if entry - stop <= 0:
            continue
        h1 = hist[:i + 1]
        g = I.chart_gates(h1)
        red = RA._red(g, entry, pl["volume_ok"])
        hod = max(r[2] for r in rows[:i + 1])
        c = rows[i][4]
        pm = datetime.fromtimestamp(pl["order_t"], timezone.utc).astimezone(E.ET).time() < RA.RTH
        dv5 = float(sum(b[4] * b[5] for b in h1[-5:]))
        spread = RA.PROXY.spread(entry, pm, dv5)
        rec = {"sym": sym, "day": day, "t": t, "arm": arm_ts, "entry": entry, "stop": stop,
               "stop_pct": (entry - stop) / entry * 100.0, "fade": 100.0 * (hod - c) / hod if hod else 0.0,
               "red": red, "red_prev": red, "fade_prev": 100.0 * (hod - c) / hod if hod else 0.0,
               "retrace": None, "macd_line_pos": False, "push_rising": False, "push_elevated": False,
               "pm": pm, "dv5": dv5, "spread_ratio": (entry - stop) / spread if spread > 0 else 99.0,
               "ext": pl["ext"], "seq": pl["seq"], "n_pull": pl["n_pull"], "ttl": TTL_MIN, "kind": "E1",
               "vwap_only_red": [x for x in red if x in ("price", "vwap")], "out": {}}
        fwd = _fwd_from(rows, pl["order_t"])
        for mode in ("A", "C"):
            got = RA.fill_retouch(fwd, entry, TTL_MIN, 0.3, None if mode == "A" else pl["order_t"]) if fwd else None
            if got is None:
                rec["out"][(mode, "base")] = None
                continue
            fk, px, kind = got
            bars = fwd[fk:]
            r, stopish, k = RA.run_exit(bars, entry, stop, px, 1.0, dtime(11, 30), mode, kind)
            rec["out"][(mode, "base")] = (int(bars[0][0].timestamp()), int(bars[k][0].timestamp()),
                                          round(r, 4), stopish, px)
        rec["_ts"] = ts.isoformat()
        out.append(rec)
    return out


def random_entries(rows: list, trade: dict, mode: str, rng: random.Random, k: int = RANDOM_K) -> list[tuple]:
    """§4.5: K market entries at the open of random 1-minute bars in the same
    window of the same symbol-day, the same stop in % of price, the same exit."""
    win = trade["win"]
    lo, hi = {"pre-market": ("07:00", "09:30"), "09:30-10:30": ("09:30", "10:30"),
              "10:30-11:30": ("10:30", "11:20")}[win]
    idx = [j for j, r in enumerate(rows) if lo <= r[0].strftime("%H:%M") < hi and j + 1 < len(rows)]
    if not idx:
        return []
    out = []
    for _ in range(k):
        j = rng.choice(idx)
        bars = rows[j:]
        px = bars[0][1]
        stop = px * (1 - trade["stop_pct"] / 100.0)
        if px <= stop:
            continue
        r, stopish, _ = RA.run_exit(bars, px, stop, px, 1.0, dtime(11, 30), mode, "open")
        pm = bars[0][0].time() < RA.RTH
        dv5 = float(sum(b[4] * b[5] for b in rows[max(0, j - 5):j]))
        cost = RA.cost_live(px, stop, stopish, pm, dv5)
        out.append((r, r - cost))
    return out


def day_job(args):
    day, syms, cache, arms = args
    f = Path(cache) / f"{day}.json"
    if not f.exists():
        return day, [], {}
    bars = json.loads(f.read_text())
    plans, nbars = [], {}
    for sym, pc in syms.items():
        raw = bars.get(sym)
        if not raw:
            continue
        rows = [r for r in H.to_rows(raw) if dtime(4, 0) <= r[0].time() < dtime(16, 0)]
        if len(rows) < 40:
            continue
        plans += e1_plans(sym, day, rows)
        # B30: the number of 1-minute bars each B plan's gates were computed on
        want = arms.get(sym)
        if want:
            for j, r in enumerate(rows):
                t = int(r[0].timestamp())
                if t in want:
                    nbars[(sym, t)] = j + 1
    return day, plans, nbars


# ------------------------------------------------------------------ portfolio (per-plan expiry)
def portfolio(plans_by_day: dict, c: dict, keep=None) -> list[dict]:
    """`rules_audit.portfolio` with each plan's own expiry (B 3 minutes, E1 5)."""
    trades = []
    for day in sorted(plans_by_day):
        cands = sorted((p for p in plans_by_day[day] if (keep is None or keep(p)) and RA.passes(p, c)),
                       key=lambda p: p["arm"])
        busy: list[tuple] = []
        pending: list[tuple] = []
        day_r, streak, orders = 0.0, 0, 0
        counted: set = set()
        for p in cands:
            t_order = p["arm"] + 60
            pending.sort()
            while pending and pending[0][0] <= t_order:
                _, r = pending.pop(0)
                day_r += r
                if r <= -0.25:
                    streak += 1
                elif r >= 0.25:
                    streak = 0
            if (c["loss"] and day_r <= -c["loss"]) or (c["streak"] and streak >= c["streak"]) \
                    or (c["orders"] and orders >= c["orders"]):
                break
            busy = [(f_, s) for f_, s in busy if f_ > t_order]
            if (c["max_pos"] and len(busy) >= c["max_pos"]) or any(s == p["sym"] for _, s in busy):
                continue
            # an E1 order re-placed at the next pullback candle is the same order
            # modified in place, so it counts once against the daily order limit
            key = ("E1", p["sym"], p["seq"]) if p.get("kind") == "E1" else ("B", p["sym"], p["arm"])
            if key not in counted:
                counted.add(key)
                orders += 1
            o = p["out"].get((c.get("mode", "A"), c["key"]))
            if o is None:
                busy.append((t_order + p.get("ttl", c["ttl"]) * 60, p["sym"]))
                continue
            t_in, t_out, r, stopish, px = o
            busy.append((t_out + 60, p["sym"]))
            pending.append((t_out + 60, r))
            net = r - RA.cost_live(p["entry"], p["stop"], stopish, p["pm"], p["dv5"], c["risk"], c["notional"],
                                   c.get("costs", "live"))
            trades.append({"day": day, "t": p["t"], "sym": p["sym"], "gross": r, "net": net,
                           "win": RA.window_of(p["t"]), "out": t_out, "kind": p.get("kind", "B"),
                           "seq": p.get("seq"), "stop_pct": p["stop_pct"], "mode": c.get("mode", "A")})
    return trades


# ------------------------------------------------------------------ statistics
def day_lb(trades: list[dict], key: str = "net", alpha: float = ALPHA_STAGE, draws: int = 20000,
           seed: int = 20261006) -> float:
    """Day-clustered bootstrap lower bound of the mean per trade."""
    by = defaultdict(lambda: [0.0, 0])
    for t in trades:
        by[t["day"]][0] += t[key]; by[t["day"]][1] += 1
    if len(by) < 10:
        return float("nan")
    s = np.array([v[0] for v in by.values()]); n = np.array([v[1] for v in by.values()])
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(s), size=(draws, len(s)))
    return float(np.quantile(s[pick].sum(1) / np.maximum(1, n[pick].sum(1)), alpha))


def paired_diff_lb(trades: list[dict], alpha: float, draws: int = 20000, seed: int = 20261006) -> float:
    """Day-clustered lower bound of mean(trade - its random baseline), gross."""
    by = defaultdict(lambda: [0.0, 0])
    for t in trades:
        if t.get("rnd_gross") is None:
            continue
        by[t["day"]][0] += t["gross"] - t["rnd_gross"]; by[t["day"]][1] += 1
    if len(by) < 10:
        return float("nan")
    s = np.array([v[0] for v in by.values()]); n = np.array([v[1] for v in by.values()])
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(s), size=(draws, len(s)))
    return float(np.quantile(s[pick].sum(1) / np.maximum(1, n[pick].sum(1)), alpha))


def period(trades, lo=None, hi=None):
    return [t for t in trades if (lo is None or t["day"] >= lo) and (hi is None or t["day"] < hi)]


def summary(trades: list[dict]) -> dict:
    if not trades:
        return {"n": 0}
    g = np.array([t["gross"] for t in trades]); n_ = np.array([t["net"] for t in trades])
    return {"n": len(trades), "gross": round(float(g.mean()), 4), "net": round(float(n_.mean()), 4),
            "win": round(float((n_ > 0).mean()), 3), "total": round(float(n_.sum()), 1),
            "stop_pct_med": round(float(np.median([t["stop_pct"] for t in trades])), 2)}


def fmt(s: dict) -> str:
    if not s.get("n"):
        return "n 0"
    return (f"n {s['n']:>5} · gross {s['gross']:+.3f} · net {s['net']:+.3f} · win {s['win']:.1%} · "
            f"total {s['total']:+.1f} R · stop med {s['stop_pct_med']:.2f}%")


# ------------------------------------------------------------------ main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default=str(H.CACHE))
    ap.add_argument("--sample", type=int)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--out", default=str(OUT / "five_minute_output.txt"))
    ap.add_argument("--json", default=str(OUT / "five_minute_results.json"))
    args = ap.parse_args(argv)
    E.COST_MODEL = "live"
    lines: list[str] = []

    def pr(s=""):
        print(s, flush=True); lines.append(s)

    uni = H.load_universe(None, None)
    days = sorted(uni)
    if args.sample:
        days = sorted(random.Random(20261006).sample(days, args.sample))
    day_set = set(days)
    b_plans = [p for p in pickle.loads(RA.PLANS_CACHE.read_bytes()) if p["day"] in day_set]
    arms_by_day: dict = defaultdict(lambda: defaultdict(set))
    for p in b_plans:
        arms_by_day[p["day"]][p["sym"]].add(p["arm"])
    jobs = [(d, uni[d], args.cache, {k: v for k, v in arms_by_day[d].items()}) for d in days]
    e1, nbars = [], {}
    with Pool(args.procs) as pool:
        for k, (d, ps, nb) in enumerate(pool.imap(day_job, jobs, chunksize=8), 1):
            e1 += ps; nbars.update(nb)
            if k % 250 == 0:
                print(f"  {k}/{len(jobs)} sessions · {len(e1)} E1 placements", flush=True)
    for p in b_plans:
        p["kind"] = "B"
        p["n_bars"] = nbars.get((p["sym"], p["arm"]))
    pr(f"E1 · addendum 2026-10-06b · {len(days)} sessions {days[0]} → {days[-1]} · cache {args.cache}")
    pr(f"E1 placements {len(e1)} (owner's case {sum(1 for p in e1 if p['ext'])}) · B plans {len(b_plans)} "
       f"(bar count known {sum(1 for p in b_plans if p['n_bars'] is not None)})")
    pr("costs live ($40 / $2,000, spread proxy + 1c) · one position · B's daily limits · modes A and C")
    pr("R = gross on the 1-minute replay; net = gross - cost_live. Lower bounds are day-clustered, one-sided.")

    by_day_e1 = defaultdict(list)
    for p in e1:
        by_day_e1[p["day"]].append(p)
    by_day_b = defaultdict(list)
    for p in b_plans:
        by_day_b[p["day"]].append(p)
    res: dict = {"sessions": len(days), "e1_placements": len(e1), "modes": {}}
    rows_cache: dict = {}
    day_cache: dict = {}

    def rows_for(day, sym):
        key = (day, sym)
        if key not in rows_cache:
            if day not in day_cache:
                day_cache.clear()
                day_cache[day] = json.loads((Path(args.cache) / f"{day}.json").read_text())
            raw = day_cache[day].get(sym) or []
            rows_cache[key] = [r for r in H.to_rows(raw) if dtime(4, 0) <= r[0].time() < dtime(16, 0)]
        return rows_cache[key]

    for mode in ("A", "C"):
        c = dict(RA.BASE, mode=mode)
        pr(f"\n=== MODE {mode} " + "=" * 60)
        primary = portfolio(by_day_e1, c, keep=lambda p: p["ext"])
        # random baseline per primary trade, same mode
        rng = random.Random(RANDOM_SEED)
        for t in primary:
            rs = random_entries(rows_for(t["day"], t["sym"]), t, mode, rng)
            t["rnd_gross"] = float(np.mean([x[0] for x in rs])) if rs else None
            t["rnd_net"] = float(np.mean([x[1] for x in rs])) if rs else None
        stages = {}
        tr = period(primary, hi=TRAIN_END)
        g23 = [t for t in primary if t["day"][:4] == GATE_YEAR]
        ho = period(primary, lo=HOLDOUT)
        pr("\nE1 (primary: the owner's case — a straight green 1-minute run inside the 5-minute impulse)")
        for name, ts_ in (("train 2016-2022", tr), ("gate 2023", g23), ("holdout 2024-2026", ho)):
            s = summary(ts_)
            rth = [t for t in ts_ if t["win"] != "pre-market"]
            rnd = [t["rnd_gross"] for t in ts_ if t.get("rnd_gross") is not None]
            pr(f"  {name:<18} {fmt(s)}")
            pr(f"  {'':<18} regular hours {fmt(summary(rth))}")
            pr(f"  {'':<18} random same windows: gross {np.mean(rnd) if rnd else float('nan'):+.3f} · "
               f"lb(net) {day_lb(ts_):+.3f} · lb(E1 - random, gross) {paired_diff_lb(ts_, ALPHA_STAGE):+.3f}")
        # stage 1
        s_tr = summary(tr)
        st1 = {"n>=200": s_tr.get("n", 0) >= 200, "net>0": s_tr.get("net", -1) > 0,
               "lb(net)>0": day_lb(tr) > 0,
               "regular hours net>0": summary([t for t in tr if t["win"] != "pre-market"]).get("net", -1) > 0,
               "lb(E1-random)>0": paired_diff_lb(tr, ALPHA_STAGE) > 0}
        st2 = {"2023 net>0": summary(g23).get("net", -1) > 0}
        s_ho = summary(ho)
        yrs = sum(1 for y in ("2024", "2025", "2026") if summary([t for t in ho if t["day"][:4] == y]).get("net", -1) > 0)
        st3 = {"net>0": s_ho.get("net", -1) > 0, "lb(net)>0 at 0.42%": day_lb(ho, alpha=ALPHA_HOLDOUT) > 0,
               "n>=200": s_ho.get("n", 0) >= 200, "2 of 3 years": yrs >= 2,
               "lb(E1-random)>0 at 0.42%": paired_diff_lb(ho, ALPHA_HOLDOUT) > 0}
        stages = {"1 train": st1, "2 gate 2023": st2, "3 holdout": st3}
        first_fail = next((k for k, v in stages.items() if not all(v.values())), None)
        pr("\n  decision stages (both modes must pass every stage):")
        for k, v in stages.items():
            pr(f"    {k:<12} " + " · ".join(f"{'✓' if ok else '✗'} {name}" for name, ok in v.items()))
        pr(f"  mode {mode}: " + ("PASSES every stage" if first_fail is None else f"FAILS at stage {first_fail}"))

        # reported, deciding nothing
        pr("\n  reported, deciding nothing:")
        allx = portfolio(by_day_e1, c)
        pr(f"    E1 without the owner's-case condition · train {fmt(summary(period(allx, hi=TRAIN_END)))}")
        pr(f"    {'':<41}· holdout {fmt(summary(period(allx, lo=HOLDOUT)))}")
        vw_days = defaultdict(list)
        for d, ps in by_day_e1.items():
            for p in ps:
                if p["ext"]:
                    vw_days[d].append(dict(p, red=p["vwap_only_red"] + (["volume"] if "volume" in p["red"] else []),
                                           red_prev=p["vwap_only_red"] + (["volume"] if "volume" in p["red"] else [])))
        vw = portfolio(vw_days, c)
        pr(f"    E1, VWAP the only chart gate          · train {fmt(summary(period(vw, hi=TRAIN_END)))}")
        pr(f"    {'':<41}· holdout {fmt(summary(period(vw, lo=HOLDOUT)))}")
        for q in (1, 2, 3):
            sel = [t for t in primary if (t["seq"] or 0) == q or (q == 3 and (t["seq"] or 0) >= 3)]
            pr(f"    E1 by pullback count {q if q < 3 else '3+'}                 · all periods {fmt(summary(sel))}")
        both_days = defaultdict(list)
        for d in set(by_day_b) | set(by_day_e1):
            both_days[d] = by_day_b.get(d, []) + [p for p in by_day_e1.get(d, []) if p["ext"]]
        b_only = portfolio(by_day_b, c)
        both = portfolio(both_days, c)
        lb_both = RA.paired_lb(both, b_only, alpha=0.05)
        pr(f"    B alone      · train {fmt(summary(period(b_only, hi=TRAIN_END)))}")
        pr(f"    {'':<13}· holdout {fmt(summary(period(b_only, lo=HOLDOUT)))}")
        pr(f"    B ∪ E1       · train {fmt(summary(period(both, hi=TRAIN_END)))}")
        pr(f"    {'':<13}· holdout {fmt(summary(period(both, lo=HOLDOUT)))}")
        pr(f"    B ∪ E1 − B, day-paired lower bound on the holdout (one-sided 5 %): {lb_both:+.3f}")

        # B30
        pr("\nB30 — plans armed before the MACD exists (< 35 one-minute bars since 04:00)")
        warm = [p for p in b_plans if p["n_bars"] is not None and p["n_bars"] < MACD_MIN]
        only_macd = [p for p in warm if p["red"] == ["macd"]]
        pr(f"  B plans with < {MACD_MIN} bars: {len(warm)} · of them MACD the only red gate: {len(only_macd)}")
        for w in ("pre-market", "09:30-10:30", "10:30-11:30"):
            pr(f"    {w:<12} {sum(1 for p in only_macd if RA.window_of(p['t']) == w)}")
        b30_days = defaultdict(list)
        for d, ps in by_day_b.items():
            for p in ps:
                if p["n_bars"] is not None and p["n_bars"] < MACD_MIN and p["red"] == ["macd"]:
                    p = dict(p, red=[], red_prev=[x for x in p["red_prev"] if x != "macd"])
                b30_days[d].append(p)
        b30 = portfolio(b30_days, c)
        sb, sv = RA.split_stats(b_only), RA.split_stats(b30)
        lb30 = RA.paired_lb(b30, b_only, alpha=ALPHA_B30)
        v, checks = RA.verdict("B30", sb, sv, lb30)
        pr(f"  B    train {fmt(summary(period(b_only, hi=HOLDOUT)))}")
        pr(f"       holdout {fmt(summary(period(b_only, lo=HOLDOUT)))}")
        pr(f"  B30  train {fmt(summary(period(b30, hi=HOLDOUT)))}")
        pr(f"       holdout {fmt(summary(period(b30, lo=HOLDOUT)))}")
        added = [t for t in b30 if (t["day"], t["sym"], t["t"]) not in {(x["day"], x["sym"], x["t"]) for x in b_only}]
        pr(f"  trades B30 adds (not in B): {fmt(summary(added))}")
        pr(f"  day-paired lower bound (B30 − B) on the holdout, one-sided {ALPHA_B30:.3f}: {lb30:+.3f}")
        pr("  " + " · ".join(f"{'✓' if ok else '✗'} {k}" for k, ok in checks.items()) + f"  → {v}")
        res["modes"][mode] = {"e1_stages": stages, "e1_first_fail": first_fail,
                              "e1": {"train": summary(tr), "2023": summary(g23), "holdout": summary(ho)},
                              "b30": {"verdict": v, "checks": checks, "lb": lb30,
                                      "train": summary(period(b30, hi=HOLDOUT)),
                                      "holdout": summary(period(b30, lo=HOLDOUT)), "added": summary(added)},
                              "b_union_e1_lb": lb_both}

    pr("\n=== DECISION (addendum 2026-10-06b) ===")
    e1_pass = all(res["modes"][m]["e1_first_fail"] is None for m in ("A", "C"))
    pr("  E1: " + ("passes every stage in both modes → built OFF as a paper order source, 200 prospective trades"
                   if e1_pass else "fails → never an order; the desk shows the EXTENDED state, nothing more"))
    b30_pass = all(res["modes"][m]["b30"]["verdict"] == "ADOPT" for m in ("A", "C"))
    pr("  B30: " + ("passes both modes → to the owner with the data; built OFF, 200 prospective trades"
                    if b30_pass else "fails → the warm-up refusal stays; the question is closed"))
    res["decision"] = {"e1": e1_pass, "b30": b30_pass}
    if not args.sample:
        Path(args.out).write_text("\n".join(lines) + "\n")
        Path(args.json).write_text(json.dumps(res, indent=1, default=str))
        print(f"\nwritten {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
