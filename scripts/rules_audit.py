#!/usr/bin/env python3
"""The bot's operating rules, one at a time, on ten years of 1-minute candles.

Preregistered in research/edge-hunt/PREREGISTRATION.md, addendum 2026-10-01
("R-audit"), committed before this script first ran. The owner asked which
operating rules hide profit and which protect it: rule 5 (still rising) and the
safety (E), order (F) and exit (G) rules. Every variant is measured against
the live rule set B in a one-position portfolio, net of costs.

What is new against scripts/ablation_history.py:
  * the A6 spread rule (stop >= 4x the spread) is modelled, with the edge hunt's
    spread proxy at the arming bar;
  * the position slot is held from the ORDER to the exit — an unfilled
    stop-limit holds it until its expiry, as `positions_alive` does live;
  * the daily limits of `journal.risk` run inside the portfolio (gross R, the
    way the live gate reads closed trades; scratches inside +-0.25 R skipped);
  * a forced flatten pays the exit spread like a stop does (a market order);
  * drawdown, losing streaks, worst day, per window and per year are reported.

Not modelled (judged on the live ledger instead): the pillar count (no
historical float or news), halts, the 2-minute signal clock, the 30-second
quote clock, the 15-second stop enforcement, the monitored pre-market stop.

    python3 scripts/rules_audit.py                 # all 2,608 sessions (cached plans reused)
    python3 scripts/rules_audit.py --sample 200    # a quick seeded sample
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
from edge_hunt.costs import SpreadProxy  # noqa: E402
from momentum_platform import indicators as I  # noqa: E402
from momentum_platform.models import Bar  # noqa: E402
from momentum_platform.pullback import FirstPullbackDetector  # noqa: E402

SPLIT = "2024-01-01"
ARM_START, ARM_END = dtime(7, 0), dtime(11, 30)     # recorded; the rule window is applied later
RTH = dtime(9, 30)
PROXY = SpreadProxy()
K_VARIANTS = 41
ALPHA = 0.05 / K_VARIANTS
PLANS_CACHE = ROOT / "data" / "cache" / "rules_audit_plans.pkl"

# outcome keys: entry model x exit
ENTRY_KEYS = {"base": ("rt", 3, 0.3), "ttl1": ("rt", 1, 0.3), "ttl5": ("rt", 5, 0.3),
              "cap0.5": ("rt", 3, 0.5), "cap1.0": ("rt", 3, 1.0), "intrabar": ("ib", 3, 0.3)}
EXIT_KEYS = {"tr0.5": (0.5, dtime(11, 30)), "tr1.5": (1.5, dtime(11, 30)), "tr2.0": (2.0, dtime(11, 30)),
             "flat1100": (1.0, dtime(11, 0)), "flat1200": (1.0, dtime(12, 0))}


# ------------------------------------------------------------------ engine
def cap_of(entry: float, cap_pct: float) -> float:
    """A10's limit: trigger + max(1 cent, cap %) — execution.intent.entry_limit at 0.3 %."""
    return round(entry + max(0.01, entry * cap_pct / 100.0), 4)


def fill_retouch(fwd: list, entry: float, ttl: int, cap_pct: float):
    """`backtest_recent.plans_for_day(gap_miss=True)`, with the expiry and the cap
    as parameters: (index into fwd, fill price) or None."""
    cap = cap_of(entry, cap_pct)
    touch = next((k for k, b in enumerate(fwd[:ttl]) if b[2] >= entry), None)
    if touch is None:
        return None
    o = fwd[touch][1]
    if o > cap:
        back = next((k for k in range(touch, min(len(fwd), touch + ttl)) if fwd[k][3] <= cap), None)
        return None if back is None else (back, cap)
    if o > entry:
        return touch, o
    return touch, entry


def run_exit(bars: list, entry: float, stop: float, fill: float, trail_r: float, flat: dtime):
    """A3 trail (`backtest_recent.simulate` 'trail' with the multiple and the
    flatten time as parameters). Returns (R, stopish, exit bar index)."""
    rps = entry - stop
    level = stop
    for k, (ts, o, h, l, c, v) in enumerate(bars):
        if ts.time() >= flat:
            return (o - fill) / rps, True, k                # a market flatten crosses the spread too
        if l <= level:
            return (min(level, o) - fill) / rps, True, k
        level = max(level, h - trail_r * rps)
    return (bars[-1][4] - fill) / rps, False, len(bars) - 1


def plans_for_symbol_day(sym: str, day: str, rows: list, prev_close: float) -> list[dict]:
    det = FirstPullbackDetector()
    hist: list = []
    hi = None
    out = []
    for i, (ts, o, h, l, c, v) in enumerate(rows):
        hi = h if hi is None else max(hi, h)
        hist.append([int(ts.timestamp()), o, h, l, c, v])
        plan = det.on_bar(Bar(symbol=sym, timeframe="1m", ts=ts.astimezone(timezone.utc),
                              open=o, high=h, low=l, close=c, volume=v))
        if plan is None or not (ARM_START <= ts.time() < ARM_END):
            continue
        entry, stop = round(plan.entry, 4), round(plan.stop, 4)
        if entry - stop <= 0:
            continue
        g = I.chart_gates(hist)
        red = []
        if not (E.PRICE_MIN <= entry <= E.PRICE_MAX):
            red.append("price")
        if g["above_vwap"] is not True:
            red.append("vwap")
        if g["above_ema9"] is not True:
            red.append("ema9")
        if g["macd_positive_and_above_signal"] is not True:
            red.append("macd")
        if not plan.volume_ok:
            red.append("volume")
        m = I.macd([b[4] for b in hist])
        macd_line_pos = bool(m and m[0][-1] > 0)
        imp = list(det._w.impulse_bars)
        vols = [b.volume for b in imp]
        half = len(vols) // 2
        push_rising = bool(vols) and (sum(vols[half:]) / max(1, len(vols) - half)) >= (sum(vols[:half]) / half if half else 0)
        first_imp = int(imp[0].ts.timestamp()) if imp else None
        k0 = next((j for j in range(len(hist)) if hist[j][0] == first_imp), None)
        before = [b[5] for b in hist[max(0, (k0 or 0) - 10):(k0 or 0)]] if k0 is not None else []
        push_elevated = bool(before) and (sum(vols) / len(vols)) >= (sum(before) / len(before))
        pm = ts.time() < RTH
        dv5 = float(sum(b[4] * b[5] for b in hist[-5:]))
        spread = PROXY.spread(entry, pm, dv5)
        rec = {"sym": sym, "day": day, "t": ts.strftime("%H:%M"), "arm": int(ts.timestamp()),
               "entry": entry, "stop": stop, "stop_pct": (entry - stop) / entry * 100.0,
               "fade": 100.0 * (hi - c) / hi if hi else 0.0, "red": red,
               "macd_line_pos": macd_line_pos, "push_rising": push_rising, "push_elevated": push_elevated,
               "pm": pm, "dv5": dv5, "spread_ratio": (entry - stop) / spread if spread > 0 else 99.0,
               "out": {}}
        fwd = rows[i + 1:]
        if not fwd:
            out.append(rec); continue
        for key, (model, ttl, cap_pct) in ENTRY_KEYS.items():
            f = None
            if model == "ib":
                cap = cap_of(entry, cap_pct)
                if o <= entry <= h:
                    f = ("bar", entry)                      # crossed while the trigger bar formed
                elif entry < o <= cap:
                    f = ("bar", o)
                if f is not None:
                    bars = rows[i:]
                    r, stopish, k = run_exit(bars, entry, stop, f[1], 1.0, dtime(11, 30))
                    rec["out"][key] = (int(bars[0][0].timestamp()), int(bars[k][0].timestamp()), round(r, 4), stopish, f[1])
                    continue
            got = fill_retouch(fwd, entry, ttl, cap_pct)
            if got is None:
                rec["out"][key] = None; continue
            fk, px = got
            bars = fwd[fk:]
            r, stopish, k = run_exit(bars, entry, stop, px, 1.0, dtime(11, 30))
            rec["out"][key] = (int(bars[0][0].timestamp()), int(bars[k][0].timestamp()), round(r, 4), stopish, px)
        base_fill = fill_retouch(fwd, entry, 3, 0.3)
        for key, (trail_r, flat) in EXIT_KEYS.items():
            if base_fill is None:
                rec["out"][key] = None; continue
            fk, px = base_fill
            bars = fwd[fk:]
            r, stopish, k = run_exit(bars, entry, stop, px, trail_r, flat)
            rec["out"][key] = (int(bars[0][0].timestamp()), int(bars[k][0].timestamp()), round(r, 4), stopish, px)
        out.append(rec)
    return out


def day_job(args):
    day, syms, cache = args
    f = Path(cache) / f"{day}.json"
    if not f.exists():
        return []
    bars = json.loads(f.read_text())
    plans = []
    for sym, pc in syms.items():
        raw = bars.get(sym)
        if not raw:
            continue
        rows = [r for r in H.to_rows(raw) if dtime(4, 0) <= r[0].time() < dtime(16, 0)]
        if len(rows) < 40:
            continue
        plans += plans_for_symbol_day(sym, day, rows, pc or rows[0][1])
    return plans


def collect(days: list[str], uni: dict, cache: str, procs: int) -> list[dict]:
    jobs = [(d, uni[d], cache) for d in days]
    out = []
    with Pool(procs) as pool:
        for k, ps in enumerate(pool.imap(day_job, jobs, chunksize=8), 1):
            out += ps
            if k % 250 == 0:
                print(f"  {k}/{len(jobs)} sessions · {len(out)} plans", flush=True)
    return out


# ------------------------------------------------------------------ costs
def cost_live(entry: float, stop: float, stopish: bool, pm: bool, dv5: float,
              risk: float = 40.0, notional: float | None = 2000.0) -> float:
    """`backtest_recent.cost_r` model "live", with the risk and the cap as
    parameters (F1). tests/test_rules_audit.py pins it to cost_r at $40 / $2,000."""
    rps = entry - stop
    sh = int(risk // rps)
    if notional:
        sh = min(sh, int(notional // entry))
    sh = max(1, sh)
    half = PROXY.spread(entry, pm, dv5) / 2
    comm = 2 * min(max(1.0, 0.005 * sh), max(1.0, 0.01 * sh * entry))
    fric = sh * (half + 0.01) * (2 if stopish else 1)
    return round((comm + fric) / (sh * rps), 3)


# ------------------------------------------------------------------ rules and portfolio
BASE = dict(fade=25.0, stop_floor=2.0, spread_k=4.0, start="07:00", end="11:20", push=None, macd_line=False,
            key="base", ttl=3, max_pos=1, loss=3.0, streak=3, orders=6, risk=40.0, notional=2000.0)


def passes(p: dict, c: dict) -> bool:
    if p["red"]:
        return False
    if c["fade"] is not None and p["fade"] > c["fade"]:
        return False
    if c["stop_floor"] and p["stop_pct"] < c["stop_floor"]:
        return False
    if c["spread_k"] and p["spread_ratio"] < c["spread_k"]:
        return False
    if not (c["start"] <= p["t"] < c["end"]):
        return False
    if c["push"] == "rising" and not p["push_rising"]:
        return False
    if c["push"] == "elevated" and not p["push_elevated"]:
        return False
    if c["macd_line"] and not p["macd_line_pos"]:
        return False
    return True


def window_of(t: str) -> str:
    return "pre-market" if t < "09:30" else ("09:30-10:30" if t < "10:30" else "10:30-11:30")


def portfolio(plans_by_day: dict, c: dict) -> list[dict]:
    """One run of the live executor's gates over every day. Returns the trades."""
    trades = []
    for day in sorted(plans_by_day):
        cands = sorted((p for p in plans_by_day[day] if passes(p, c)), key=lambda p: p["arm"])
        busy: list[tuple] = []               # (free_at, sym)
        pending: list[tuple] = []            # (exit_at, gross R) not yet realised
        day_r, streak, orders = 0.0, 0, 0
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
                break                                       # the day is locked
            busy = [(f, s) for f, s in busy if f > t_order]
            if (c["max_pos"] and len(busy) >= c["max_pos"]) or any(s == p["sym"] for _, s in busy):
                continue
            orders += 1
            o = p["out"].get(c["key"])
            if o is None:
                busy.append((t_order + c["ttl"] * 60, p["sym"]))
                continue
            t_in, t_out, r, stopish, px = o
            busy.append((t_out + 60, p["sym"]))
            pending.append((t_out + 60, r))
            net = r - cost_live(p["entry"], p["stop"], stopish, p["pm"], p["dv5"], c["risk"], c["notional"])
            trades.append({"day": day, "t": p["t"], "sym": p["sym"], "gross": r, "net": net,
                           "win": window_of(p["t"]), "out": t_out})
    return trades


def stats(trades: list[dict]) -> dict:
    if not trades:
        return {"n": 0}
    net = np.array([t["net"] for t in trades])
    cum = np.cumsum(net)
    dd = float((np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:] - cum).max())
    streak = best = 0
    for x in net:
        streak = streak + 1 if x < 0 else 0
        best = max(best, streak)
    by_day = defaultdict(float)
    for t in trades:
        by_day[t["day"]] += t["net"]
    months = len({t["day"][:7] for t in trades})
    return {"n": len(net), "mean": round(float(net.mean()), 4), "total": round(float(net.sum()), 2),
            "gross": round(float(np.mean([t["gross"] for t in trades])), 4),
            "win": round(float((net > 0).mean()), 3), "max_dd": round(dd, 2), "lose_streak": best,
            "worst_day": round(min(by_day.values()), 2), "per_month": round(len(net) / max(1, months), 1)}


def split_stats(trades: list[dict]) -> dict:
    tr = [t for t in trades if t["day"] < SPLIT]
    te = [t for t in trades if t["day"] >= SPLIT]
    out = {"train": stats(tr), "test": stats(te), "years": {}, "windows": {}}
    for y in ("2024", "2025", "2026"):
        out["years"][y] = stats([t for t in te if t["day"][:4] == y])
    for w in ("pre-market", "09:30-10:30", "10:30-11:30"):
        out["windows"][w] = {"train": stats([t for t in tr if t["win"] == w]),
                             "test": stats([t for t in te if t["win"] == w])}
    return out


def paired_lb(var: list[dict], base: list[dict], draws: int = 20000, seed: int = 20261001) -> float:
    """Day-paired bootstrap of (variant - B) mean net R per trade on test days,
    lower bound at one-sided ALPHA."""
    days = sorted({t["day"] for t in var + base if t["day"] >= SPLIT})
    if len(days) < 20:
        return float("nan")
    idx = {d: i for i, d in enumerate(days)}
    sv, nv, sb, nb = (np.zeros(len(days)) for _ in range(4))
    for t in var:
        if t["day"] >= SPLIT:
            sv[idx[t["day"]]] += t["net"]; nv[idx[t["day"]]] += 1
    for t in base:
        if t["day"] >= SPLIT:
            sb[idx[t["day"]]] += t["net"]; nb[idx[t["day"]]] += 1
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(days), size=(draws, len(days)))
    mv = sv[pick].sum(1) / np.maximum(1, nv[pick].sum(1))
    mb = sb[pick].sum(1) / np.maximum(1, nb[pick].sum(1))
    return float(np.quantile(mv - mb, ALPHA))


VARIANTS = [
    ("5 still rising", "off the high <= 15 %", {"fade": 15.0}),
    ("5 still rising", "off the high <= 35 %", {"fade": 35.0}),
    ("5 still rising", "off the high <= 50 %", {"fade": 50.0}),
    ("5 still rising", "off", {"fade": None}),
    ("E1 window", "start 08:00", {"start": "08:00"}),
    ("E1 window", "start 09:30", {"start": "09:30"}),
    ("E1 window", "end 10:30", {"end": "10:30"}),
    ("E1 window", "end 11:00", {"end": "11:00"}),
    ("E1 window", "end 11:30 (no A8 buffer)", {"end": "11:30"}),
    ("E2 stop floor", "off", {"stop_floor": None}),
    ("E2 stop floor", "1 %", {"stop_floor": 1.0}),
    ("E2 stop floor", "1.5 %", {"stop_floor": 1.5}),
    ("E2 stop floor", "3 %", {"stop_floor": 3.0}),
    ("E3 stop vs spread", "off", {"spread_k": None}),
    ("E3 stop vs spread", "2x", {"spread_k": 2.0}),
    ("E3 stop vs spread", "3x", {"spread_k": 3.0}),
    ("E3 stop vs spread", "6x", {"spread_k": 6.0}),
    ("E6 positions", "2 at once", {"max_pos": 2}),
    ("E6 positions", "no cap", {"max_pos": None}),
    ("E7 daily limits", "all off", {"loss": None, "streak": None, "orders": None}),
    ("E7 daily limits", "loss -2 R", {"loss": 2.0}),
    ("E7 daily limits", "loss -4 R", {"loss": 4.0}),
    ("E7 daily limits", "streak 2", {"streak": 2}),
    ("E7 daily limits", "streak 4", {"streak": 4}),
    ("E7 daily limits", "orders 4", {"orders": 4}),
    ("E7 daily limits", "orders 8", {"orders": 8}),
    ("F1 sizing", "$20 risk", {"risk": 20.0}),
    ("F1 sizing", "$80 risk", {"risk": 80.0}),
    ("F1 sizing", "no $2,000 cap", {"notional": None}),
    ("F2 entry order", "expiry 1 bar", {"key": "ttl1", "ttl": 1}),
    ("F2 entry order", "expiry 5 bars", {"key": "ttl5", "ttl": 5}),
    ("F2 entry order", "cap +0.5 %", {"key": "cap0.5"}),
    ("F2 entry order", "cap +1 %", {"key": "cap1.0"}),
    ("G1 trail", "0.5 R", {"key": "tr0.5"}),
    ("G1 trail", "1.5 R", {"key": "tr1.5"}),
    ("G1 trail", "2 R", {"key": "tr2.0"}),
    ("G4 flat time", "11:00", {"key": "flat1100"}),
    ("G4 flat time", "12:00", {"key": "flat1200"}),
    ("Ross volume", "push volume rising", {"push": "rising"}),
    ("Ross volume", "push volume elevated", {"push": "elevated"}),
    ("MACD reading", "line above zero and signal", {"macd_line": True}),
]
SENSITIVITIES = [("entry model", "intrabar fill (live-like)", {"key": "intrabar"})]
RISK_RULES = ("E6", "E7", "F1")


def verdict(group: str, b: dict, v: dict, lb: float) -> tuple[str, dict]:
    tr_ok = v["train"].get("n", 0) and v["train"]["mean"] > b["train"]["mean"]
    te_ok = v["test"].get("n", 0) and v["test"]["mean"] > b["test"]["mean"]
    n_ok = v["test"].get("n", 0) >= 200
    yrs = sum(1 for y in ("2024", "2025", "2026")
              if v["years"][y].get("n", 0) and b["years"][y].get("n", 0)
              and v["years"][y]["mean"] > b["years"][y]["mean"])
    lb_ok = lb == lb and lb > 0
    dd_ok = True
    if group.split()[0] in RISK_RULES:
        dd_ok = v["test"].get("max_dd", 1e9) <= 1.10 * b["test"].get("max_dd", 0)
    checks = {"train better": bool(tr_ok), "test better": bool(te_ok), ">=200 test trades": bool(n_ok),
              "2 of 3 test years": yrs >= 2, "paired lower bound > 0": bool(lb_ok), "drawdown ok": bool(dd_ok)}
    return ("ADOPT" if all(checks.values()) else "keep B"), checks


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default=str(H.CACHE))
    ap.add_argument("--sample", type=int)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--rebuild", action="store_true", help="recompute plans even if cached")
    ap.add_argument("--json", default=str(ROOT / "research" / "paper-exercise" / "reports" / "rules_audit_results.json"))
    args = ap.parse_args(argv)
    E.COST_MODEL = "live"
    uni = H.load_universe(None, None)
    days = sorted(uni)
    if args.sample:
        days = sorted(random.Random(20261001).sample(days, args.sample))
    cache_ok = PLANS_CACHE.exists() and not args.rebuild and not args.sample
    if cache_ok:
        plans = pickle.loads(PLANS_CACHE.read_bytes())
    else:
        plans = collect(days, uni, args.cache, args.procs)
        if not args.sample:
            PLANS_CACHE.parent.mkdir(parents=True, exist_ok=True)
            PLANS_CACHE.write_bytes(pickle.dumps(plans))
    by_day = defaultdict(list)
    for p in plans:
        by_day[p["day"]].append(p)
    print(f"{len(plans)} plans armed 07:00-11:30 on {len(by_day)} sessions · costs live ($40 / $2,000, spread proxy + 1c)")
    base_tr = portfolio(by_day, BASE)
    b = split_stats(base_tr)
    res = {"baseline": b, "variants": [], "sensitivities": [], "alpha": ALPHA, "K": K_VARIANTS}

    def line(name, s):
        tr, te = s["train"], s["test"]
        return (f"  {name:<40}{tr.get('n', 0):>7}{tr.get('mean', float('nan')):>+9.3f}"
                f"{te.get('n', 0):>7}{te.get('mean', float('nan')):>+9.3f}{te.get('total', 0):>+10.1f}"
                f"{te.get('max_dd', 0):>8.1f}{te.get('lose_streak', 0):>6}{te.get('worst_day', 0):>+8.1f}"
                f"{te.get('per_month', 0):>7.1f}")

    hdr = (f"  {'rule · variant':<40}{'tr n':>7}{'tr R':>9}{'te n':>7}{'te R':>9}{'te tot':>10}"
           f"{'te DD':>8}{'strk':>6}{'worst':>8}{'/mo':>7}")
    print("\nBASELINE B (live rules) · one position · net R per trade")
    print(hdr)
    print(line("B", b))
    for y in ("2024", "2025", "2026"):
        s = b["years"][y]
        print(f"    test {y}: n {s.get('n', 0)} · mean {s.get('mean', float('nan')):+.3f} · total {s.get('total', 0):+.1f}")
    for w, s in b["windows"].items():
        print(f"    {w:<12} train {s['train'].get('n', 0):>5} {s['train'].get('mean', float('nan')):+.3f}"
              f" · test {s['test'].get('n', 0):>5} {s['test'].get('mean', float('nan')):+.3f}")
    print("\nVARIANTS, one at a time against B")
    print(hdr + "  verdict")
    for group, name, over in VARIANTS:
        c = dict(BASE, **over)
        tr = portfolio(by_day, c)
        s = split_stats(tr)
        lb = paired_lb(tr, base_tr)
        v, checks = verdict(group, b, s, lb)
        res["variants"].append({"group": group, "variant": name, "stats": s, "paired_lb": lb,
                                "verdict": v, "checks": checks})
        yrs = " ".join(f"{s['years'][y].get('mean', float('nan')):+.2f}" for y in ("2024", "2025", "2026"))
        print(line(f"{group} · {name}", s) + f"  {v}  (lb {lb:+.3f} · yrs {yrs})", flush=True)
    print("\nSENSITIVITIES (never deciding)")
    for group, name, over in SENSITIVITIES:
        s = split_stats(portfolio(by_day, dict(BASE, **over)))
        res["sensitivities"].append({"group": group, "variant": name, "stats": s})
        print(line(f"{group} · {name}", s))
    Path(args.json).write_text(json.dumps(res, indent=1, default=str))
    print(f"\nwritten {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
