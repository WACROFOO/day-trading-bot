#!/usr/bin/env python3
"""Free each rule of the strategy one at a time, add each Ross guideline the
bot does not apply yet one at a time, change each exit one at a time — over
ten years of gappers with pre-market volume — and say which, if any, makes it
positive. Written 2026-09-26 at the owner's request: "free them one by one each
a time and evaluate which one would make the strategy profitable".

THE ADOPTION RULE, fixed here before the first run:
    A configuration is adopted only if, on the TEST years (2024-01-01 onward,
    never used to choose anything):
      1. its mean NET R per trade is above zero,
      2. the lower bound of a day-clustered 95 % bootstrap interval is above zero,
      3. it has at least 200 test trades, and
      4. it is positive in at least 2 of the 3 test years.
    Levers are ranked, and the greedy combination is built, on the TRAIN years
    (2016-2023) only. The test years are read once, at the end.

Levers (each against the baseline = the desk's current rules, trail-1R exit):
  free a rule     vwap · ema9 · macd · volume · rising · price band
  Ross guidelines (knowledge-base/strategies/PARAMETERS.md, FILTERS.md):
                  stop <= $0.30 (§5 stop_max_distance) · stop >= $0.05 / >= 1 %
                  of price (cost floor; §5 stop_min_distance >= spread) ·
                  session volume >= 1M at the plan (FILTERS Layer 3) ·
                  1st or 2nd pullback only (FILTERS Layer 2) · session
                  07:00-11:00 (FILTERS Layer 3) · 09:35-10:30 prime window
                  (CLAUDE.md, PARAMETERS §2) · price $5-20 / $10-20 ·
                  trigger at or above the pre-market high / the high of day
  exits           fixed 1 / 1.5 / 2 / 3 R · trail 0.5 / 1 / 2 R · break-even
                  then 2 R · Ross ladder (PARAMETERS §6: half at the first
                  target, stop to break-even, a quarter at the next, a quarter
                  trailed) · exit on the first candle to make a new low (§6
                  hard exits) · breakout-or-bailout (out after 2 bars unless
                  +0.5 R printed)

Costs as `backtest_recent.cost_r` plus $1 per extra partial exit. Fills
realistic (stop-limit: open inside the cap, cap only on a return, else none).

    python3 scripts/ablation_history.py          # from the history cache
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

import backtest_history as H  # noqa: E402
import backtest_recent as E  # noqa: E402

SPLIT = "2024-01-01"
FLAT = E.FLAT


def sim(bars, entry, stop, fill, spec):
    """Generic exit: returns (R from the fill, n_orders). spec keys:
    target (R) · trail (R) · be_at (R) · ladder · newlow · bail."""
    rps = entry - stop
    level = stop
    hi = entry
    qty_left, realised, orders = 1.0, 0.0, 0
    ladder_done = 0
    prev_low = None
    for k, (ts, o, h, l, c, v) in enumerate(bars):
        if ts.time() >= FLAT:
            realised += qty_left * (o - fill); orders += 1
            return realised / rps, orders
        stop_now = level
        if spec.get("newlow") and prev_low is not None and k >= 1:
            stop_now = max(stop_now, prev_low - 0.01)
        if l <= stop_now:
            px = min(stop_now, o)
            realised += qty_left * (px - fill); orders += 1
            return realised / rps, orders
        if spec.get("ladder"):
            t1, t2 = entry + spec["ladder"][0] * rps, entry + spec["ladder"][1] * rps
            if ladder_done == 0 and h >= t1:
                realised += 0.5 * (t1 - fill); qty_left -= 0.5; orders += 1; ladder_done = 1
                level = max(level, entry)
            if ladder_done == 1 and h >= t2:
                realised += 0.25 * (t2 - fill); qty_left -= 0.25; orders += 1; ladder_done = 2
        elif spec.get("target") and h >= entry + spec["target"] * rps:
            realised += qty_left * (entry + spec["target"] * rps - fill); orders += 1
            return realised / rps, orders
        hi = max(hi, h)
        if spec.get("trail"):
            level = max(level, hi - spec["trail"] * rps)
        if spec.get("ladder") and ladder_done >= 2:
            level = max(level, hi - rps)
        if spec.get("be_at") and hi >= entry + spec["be_at"] * rps:
            level = max(level, entry)
        if spec.get("bail") and k == 1 and hi < entry + 0.5 * rps:
            realised += qty_left * (c - fill); orders += 1
            return realised / rps, orders
        prev_low = l
    realised += qty_left * (bars[-1][4] - fill); orders += 1
    return realised / rps, orders


EXITS = {
    "trail 1R (now)": {"trail": 1.0},
    "fixed 1R": {"target": 1.0}, "fixed 1.5R": {"target": 1.5}, "fixed 2R": {"target": 2.0}, "fixed 3R": {"target": 3.0},
    "trail 0.5R": {"trail": 0.5}, "trail 2R": {"trail": 2.0},
    "BE at 1R, target 2R": {"target": 2.0, "be_at": 1.0},
    "Ross ladder 1R/2R": {"ladder": (1.0, 2.0)}, "Ross ladder 2R/3R": {"ladder": (2.0, 3.0)},
    "new-low candle exit": {"newlow": True},
    "new-low exit + 2R target": {"newlow": True, "target": 2.0},
    "breakout or bailout + trail 1R": {"bail": True, "trail": 1.0},
}


def net(r, orders, p, fill_stopish=True):
    base = E.cost_r(p["entry"], p["stop"], fill_stopish)
    return r - base - max(0, orders - 1) * 1.0 / 20.0


def collect(cache: Path, days: list[str], uni: dict) -> list[dict]:
    plans = []
    for d in days:
        f = cache / f"{d}.json"
        if not f.exists():
            continue
        bars = json.loads(f.read_text())
        for sym, raw in bars.items():
            if sym not in uni[d]:
                continue
            rows = [r for r in H.to_rows(raw) if E.dtime(4, 0) <= r[0].time() < E.dtime(16, 0)]
            if len(rows) < 40:
                continue

            def hook(rec, ent, fill):
                out = {}
                for name, spec in EXITS.items():
                    r, n = sim(ent, rec["entry"], rec["stop"], fill, spec)
                    out[name] = (round(r, 3), round(net(r, n, rec), 3))
                rec["x"] = out
            ps = E.plans_for_day(sym, rows, uni[d][sym] or rows[0][1], desk_vwap=True, gap_miss=True, hook=hook)
            for p in ps:
                if p["touched"]:
                    p.pop("ts", None); p.pop("t_in", None)
                    for k in ("fixed_out", "trail_out", "be_out"):
                        p.pop(k, None)
                    plans.append(p)
    return plans


# ------------------------------------------------------------------ levers
def base_ok(p, free=()):
    return not [g for g in p["red"] if g not in free]


FILTER_LEVERS = {
    "baseline (current rules)": lambda p: base_ok(p),
    "free VWAP": lambda p: base_ok(p, ("vwap",)),
    "free 9 EMA": lambda p: base_ok(p, ("ema9",)),
    "free MACD": lambda p: base_ok(p, ("macd",)),
    "free pullback volume": lambda p: base_ok(p, ("volume",)),
    "free still-rising": lambda p: base_ok(p, ("rising",)),
    "free price band": lambda p: base_ok(p, ("price",)),
    "free ALL chart gates": lambda p: base_ok(p, ("vwap", "ema9", "macd", "volume")),
    "free EVERY rule": lambda p: True,
    "+ stop <= $0.30": lambda p: base_ok(p) and p["entry"] - p["stop"] <= 0.30,
    "+ stop >= $0.05": lambda p: base_ok(p) and p["entry"] - p["stop"] >= 0.05,
    "+ stop >= 1% of price": lambda p: base_ok(p) and p["stop_pct"] >= 1.0,
    "+ stop >= 2% of price": lambda p: base_ok(p) and p["stop_pct"] >= 2.0,
    "+ session volume >= 1M": lambda p: base_ok(p) and p["cum_vol"] >= 1_000_000,
    "+ 1st or 2nd pullback": lambda p: base_ok(p) and p["pb_index"] <= 2,
    "+ 07:00-11:00 only": lambda p: base_ok(p) and "07:00" <= p["t"] < "11:00",
    "+ 09:35-10:30 only": lambda p: base_ok(p) and "09:35" <= p["t"] < "10:30",
    "+ pre-market only 08:00-09:30": lambda p: base_ok(p) and "08:00" <= p["t"] < "09:30",
    "+ price $5-20": lambda p: base_ok(p) and p["price"] >= 5,
    "+ price $10-20": lambda p: base_ok(p) and p["price"] >= 10,
    "+ trigger >= pre-market high": lambda p: base_ok(p) and p["pm_high"] is not None and p["entry"] >= p["pm_high"],
    "+ trigger >= high of day": lambda p: base_ok(p) and p["hod_before"] is not None and p["entry"] >= p["hod_before"],
    "+ gap >= 30%": lambda p: base_ok(p) and (p["gap"] or 0) >= 0.30,
}


def score(ps, exit_name, which=1):
    vals = [p["x"][exit_name][which] for p in ps]
    return (mean(vals) if vals else float("nan")), len(vals)


def boot_lb(ps, exit_name, draws=2000, seed=7):
    by = defaultdict(list)
    for p in ps:
        by[p["day"]].append(p["x"][exit_name][1])
    days = list(by)
    if len(days) < 5:
        return float("nan")
    rng = random.Random(seed); means = []
    for _ in range(draws):
        pick = [by[rng.choice(days)] for _ in days]
        flat = [v for g in pick for v in g]
        means.append(mean(flat))
    means.sort()
    return means[int(0.025 * draws)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default=str(H.CACHE))
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    uni = H.load_universe(None, None)
    plans = collect(Path(args.cache), sorted(uni), uni)
    tr = [p for p in plans if p["day"] < SPLIT]; te = [p for p in plans if p["day"] >= SPLIT]
    print(f"{len(plans)} filled plans · train {len(tr)} (2016-2023) · test {len(te)} (2024-2026) · NET R per trade\n")

    print("1. ONE FILTER LEVER AT A TIME · exit trail 1R (now) · plan level")
    print(f"  {'lever':<34}{'train n':>9}{'train R':>9}{'test n':>8}{'test R':>9}")
    rows = []
    for name, f in FILTER_LEVERS.items():
        a = [p for p in tr if f(p)]; b = [p for p in te if f(p)]
        ma, na = score(a, "trail 1R (now)"); mb, nb = score(b, "trail 1R (now)")
        rows.append((name, na, ma, nb, mb))
        print(f"  {name:<34}{na:>9}{ma:>+9.3f}{nb:>8}{mb:>+9.3f}")

    print("\n2. ONE EXIT LEVER AT A TIME · current rules · plan level")
    print(f"  {'exit':<34}{'train gross':>12}{'train net':>10}{'test gross':>11}{'test net':>9}")
    base_tr = [p for p in tr if base_ok(p)]; base_te = [p for p in te if base_ok(p)]
    for ex in EXITS:
        print(f"  {ex:<34}{score(base_tr, ex, 0)[0]:>+12.3f}{score(base_tr, ex)[0]:>+10.3f}"
              f"{score(base_te, ex, 0)[0]:>+11.3f}{score(base_te, ex)[0]:>+9.3f}")

    print("\n3. GREEDY COMBINATION, chosen on TRAIN only (filters x one exit), then TEST once")
    filt_names = [n for n in FILTER_LEVERS if n.startswith("+") or n.startswith("free")]
    best = None
    for ex in EXITS:
        chosen, cur_f = [], (lambda p: base_ok(p))
        cur, n0 = score([p for p in tr if cur_f(p)], ex)
        improved = True
        while improved:
            improved = False
            for name in filt_names:
                if name in chosen:
                    continue
                g = FILTER_LEVERS[name]
                if name.startswith("free"):
                    freed = {"free VWAP": ("vwap",), "free 9 EMA": ("ema9",), "free MACD": ("macd",),
                             "free pullback volume": ("volume",), "free still-rising": ("rising",),
                             "free price band": ("price",), "free ALL chart gates": ("vwap", "ema9", "macd", "volume"),
                             "free EVERY rule": ("vwap", "ema9", "macd", "volume", "rising", "price")}[name]
                    frees = set(freed) | {x for c in chosen if c.startswith("free") for x in
                                          {"free VWAP": ("vwap",), "free 9 EMA": ("ema9",), "free MACD": ("macd",),
                                           "free pullback volume": ("volume",), "free still-rising": ("rising",),
                                           "free price band": ("price",), "free ALL chart gates": ("vwap", "ema9", "macd", "volume"),
                                           "free EVERY rule": ("vwap", "ema9", "macd", "volume", "rising", "price")}[c]}
                    adds = [FILTER_LEVERS[c] for c in chosen if c.startswith("+")]
                    cand = (lambda fr, ad: lambda p: base_ok(p, tuple(fr)) and all(h(p) for h in ad))(frees, adds)
                else:
                    frees = {x for c in chosen if c.startswith("free") for x in
                             {"free VWAP": ("vwap",), "free 9 EMA": ("ema9",), "free MACD": ("macd",),
                              "free pullback volume": ("volume",), "free still-rising": ("rising",),
                              "free price band": ("price",), "free ALL chart gates": ("vwap", "ema9", "macd", "volume"),
                              "free EVERY rule": ("vwap", "ema9", "macd", "volume", "rising", "price")}[c]}
                    adds = [FILTER_LEVERS[c] for c in chosen if c.startswith("+")] + [g]
                    cand = (lambda fr, ad: lambda p: base_ok(p, tuple(fr)) and all(h(p) for h in ad))(frees, adds)
                m, n = score([p for p in tr if cand(p)], ex)
                if n >= 300 and m > cur + 0.005:
                    cur, cur_f, pick = m, cand, name
                    improved = True
            if improved:
                chosen.append(pick)
        te_sel = [p for p in te if cur_f(p)]
        mt, nt = score(te_sel, ex)
        if best is None or cur > best[0]:
            best = (cur, ex, chosen, cur_f, mt, nt)
        print(f"  {ex:<32} train {cur:+.3f}  test {mt:+.3f} (n {nt:>5})  levers: {', '.join(chosen) or 'none'}")

    cur, ex, chosen, f, mt, nt = best
    sel = [p for p in te if f(p)]
    yrs = defaultdict(list)
    for p in sel:
        yrs[p["day"][:4]].append(p["x"][ex][1])
    lb = boot_lb(sel, ex)
    print(f"\n4. THE BEST TRAIN CONFIGURATION, read once on TEST")
    print(f"  exit {ex} · levers {', '.join(chosen) or 'none'}")
    print(f"  train {cur:+.3f} R/trade · test {mt:+.3f} R/trade over {nt} · 95 % lower bound {lb:+.3f} · "
          f"test years {', '.join(f'{y} {mean(v):+.3f} ({len(v)})' for y, v in sorted(yrs.items()))}")
    ok = mt > 0 and lb > 0 and nt >= 200 and sum(1 for v in yrs.values() if mean(v) > 0) >= 2
    print(f"  ADOPTION RULE: {'MET' if ok else 'NOT MET'}")
    if args.json:
        Path(args.json).write_text(json.dumps({"rows": rows, "best": [cur, ex, chosen, mt, nt, lb]}, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
