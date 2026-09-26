#!/usr/bin/env python3
"""Backtest the live rule set, and one-rule-off variants, over the last seven
sessions' 1-minute tape for every name the desk has carried.

Written 2026-09-25 for the full assessment. The DECISION RULE below was
fixed in this docstring before the first run, so the result cannot choose
its own threshold:

    A rule is relaxed only if, in REGULAR HOURS (09:30-11:20 ET):
      1. the plans it alone refuses number at least 15 that triggered,
      2. their sum is positive under BOTH the fixed 2 R exit and the A3 trail,
      3. they are positive on at least half the days they occur, and
      4. the portfolio run (one position, A10 entry, costs as below) with the
         rule off is at least as good as with it on, on both exits.
    An exit rule is replaced only if the variant beats the current A3 trail
    on the all-green regular-hours plans in total R AND on at least 4 of the
    days with trades, in the portfolio run.
    Pre-market rows are reported and never decide: Yahoo carries no
    pre-market volume, so VWAP and the volume gate are not evaluable there.

Source: Yahoo 1-minute bars, `range=7d`, the same endpoint `tape.py` falls
back to (the container has no Gateway). Regular-hours VWAP here is the
RTH-anchored VWAP of `tape.py`; the live desk anchors at 04:00 with IBKR's
pre-market volume, so a VWAP verdict can differ near the line.

Not modelled, and said so in every table: the pillar count (news is unknown
for past days), the A6 spread rule (no historical quotes), halts, fees.
Entries: A10 — the trigger must trade within 3 bars of the plan bar. Fills are
REALISTIC since 2026-09-26: at the trigger, at the bar's open when it opens
between the trigger and the stop-limit's cap, at the cap when it opens above
it and trades back down to it within 3 bars, otherwise no fill. The first
version filled every touch at the trigger, which a stop-limit cannot do; that
fill model produced the positive seven-session result behind A11, reverted. Stops: a bar that OPENS below the stop fills at its open (the
GRML 2026-09-25 slippage), otherwise at the stop. Flatten at 11:30.

Usage:
    python3 scripts/backtest_recent.py                 # default universe
    python3 scripts/backtest_recent.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, time as dtime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from momentum_platform import indicators as I  # noqa: E402
from momentum_platform.models import Bar  # noqa: E402
from momentum_platform.pullback import FirstPullbackDetector  # noqa: E402

ET = ZoneInfo("America/New_York")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}?range={}&interval={}&includePrePost={}"

# Every name the desk carried 2026-09-22 .. 09-25 (desk logs pasted by the owner).
UNIVERSE = ["GRML", "DCOY", "WHLR", "MSS", "HAO", "BENF", "VEEE", "AEHL", "GCTK", "WETO", "SPHL", "UXIN",
            "NCPL", "PFSA", "SKYQ", "SRZN", "GLND", "HCWB", "PMAX", "INLF", "APUS", "IFBD", "LONA", "SPRO",
            "ONCO", "SMX", "CNET", "JAGX", "AIFF", "SONM", "CTSO"]

PRICE_MIN, PRICE_MAX, RISING_MAX_OFF = 2.0, 20.0, 0.25      # FILTERS.md gates 1 and 4
GAIN_MIN = 0.10                                               # the scanner's "up >= 10 %"
PM_START, RTH_START, CUTOFF, FLAT = dtime(7, 0), dtime(9, 30), dtime(11, 20), dtime(11, 30)
TTL_BARS = 3
GATES = ("price", "rising", "vwap", "ema9", "macd", "volume")
EXITS = ("fixed", "trail", "be")


def _get(url: str) -> dict:
    p = subprocess.run(["curl", "-s", "--compressed", "--max-time", "40", "-H", f"User-Agent: {UA}", url],
                       capture_output=True, text=True)
    return json.loads(p.stdout)["chart"]["result"][0]


def fetch(sym: str, cache: Path) -> tuple[list, dict]:
    """(1-minute rows [(dt_et, o, h, l, c, v)], {date: previous close})."""
    f = cache / f"{sym}.json"
    if f.exists():
        raw = json.loads(f.read_text())
    else:
        raw = {"m": _get(URL.format(sym, "7d", "1m", "true")), "d": _get(URL.format(sym, "1mo", "1d", "false"))}
        f.write_text(json.dumps(raw))
    m = raw["m"]; q = m["indicators"]["quote"][0]
    rows = []
    for i, t in enumerate(m.get("timestamp") or []):
        if q["close"][i] is None:
            continue
        rows.append((datetime.fromtimestamp(t, ET), q["open"][i], q["high"][i], q["low"][i], q["close"][i],
                     q["volume"][i] or 0))
    d = raw["d"]; dq = d["indicators"]["quote"][0]
    closes = [(datetime.fromtimestamp(t, ET).date(), c) for t, c in zip(d.get("timestamp") or [], dq["close"]) if c]
    prev = {closes[i][0]: closes[i - 1][1] for i in range(1, len(closes))}
    return rows, prev


def simulate(bars: list, entry: float, stop: float, variant: str,
             fill: float | None = None) -> tuple[float, str, datetime]:
    """One trade from the entry bar on. Stop tested first against the level in
    force before the bar (opening below it fills at the open), then target,
    then the trail may rise. Flatten at 11:30."""
    rps = entry - stop
    px_in = entry if fill is None else fill
    level, target = stop, entry + 2 * rps
    for b in bars:
        ts, o, h, l, c, v = b
        if ts.time() >= FLAT:
            return round((o - px_in) / rps, 3), "flatten", ts
        if l <= level:
            px = min(level, o)
            return round((px - px_in) / rps, 3), ("stop" if level == stop else "trail"), ts
        if variant in ("fixed", "be") and h >= target:
            return round((target - px_in) / rps, 3), "target", ts
        if variant == "trail":
            level = max(level, h - rps)
        elif variant == "be" and h >= entry + rps:
            level = max(level, entry)
    return round((bars[-1][4] - px_in) / rps, 3), "close", bars[-1][0]


def entry_cap(entry: float) -> float:
    """A10's limit: trigger + max(1 cent, 0.3 %) (execution.intent.entry_limit)."""
    return round(entry + max(0.01, entry * 0.003), 4)


def cost_r(entry: float, stop: float, stop_exit: bool, dollar_risk: float = 20.0) -> float:
    """Costs in R for one round trip at the desk's sizing: IBKR fixed pricing
    ($0.005/share, $1 minimum per order) both ways, plus one cent of slippage
    on entry and one on a stop exit (a gap through the stop is modelled in
    `simulate` itself)."""
    rps = entry - stop
    if rps <= 0:
        return 0.0
    shares = max(1, int(dollar_risk // rps))
    comm = 2 * max(1.0, 0.005 * shares)
    slip = 0.01 * shares * (2 if stop_exit else 1)
    return round((comm + slip) / dollar_risk, 3)


def plans_for_day(sym: str, day_rows: list, prev_close: float, desk_vwap: bool = False,
                  gap_miss: bool = False, hook=None) -> list[dict]:
    """Every pullback plan the desk's detector arms on one symbol-day.

    desk_vwap=False (Yahoo, no pre-market volume): regular-hours VWAP is
    RTH-anchored and pre-market VWAP / volume are not evaluated.
    desk_vwap=True (a consolidated feed WITH pre-market volume): VWAP is
    anchored at 04:00 like the live desk, and VWAP and the volume gate are
    evaluated in both windows.
    gap_miss=True: a touch bar that OPENS above A10's limit is no fill."""
    det = FirstPullbackDetector()
    hist, out, hi = [], [], None
    cum_vol, pm_hi, n_plans = 0.0, None, 0
    for i, (ts, o, h, l, c, v) in enumerate(day_rows):
        hi_before = hi
        hi = h if hi is None else max(hi, h)
        cum_vol += v
        if ts.time() < RTH_START:
            pm_hi = h if pm_hi is None else max(pm_hi, h)
        hist.append([int(ts.timestamp()), o, h, l, c, v])
        plan = det.on_bar(Bar(symbol=sym, timeframe="1m", ts=ts.astimezone(timezone.utc),
                              open=o, high=h, low=l, close=c, volume=v))
        if plan is None or not (PM_START <= ts.time() < CUTOFF):
            continue
        window = "pre-market" if ts.time() < RTH_START else "regular"
        rth = [r for r in hist if datetime.fromtimestamp(r[0], ET).time() >= RTH_START]
        g = I.chart_gates(rth if window == "regular" and len(rth) >= 1 else hist)
        # chart_gates needs history for the EMA/MACD: use the full series for those
        gfull = I.chart_gates(hist)
        red = []
        if not (PRICE_MIN <= plan.entry <= PRICE_MAX):
            red.append("price")
        if hi and c < (1 - RISING_MAX_OFF) * hi:
            red.append("rising")
        if desk_vwap:
            if gfull["above_vwap"] is not True:
                red.append("vwap")
        elif window == "regular":
            if g["above_vwap"] is not True:
                red.append("vwap")
        if gfull["above_ema9"] is not True:
            red.append("ema9")
        if gfull["macd_positive_and_above_signal"] is not True:
            red.append("macd")
        if (window == "regular" or desk_vwap) and not plan.volume_ok:
            red.append("volume")
        fwd = day_rows[i + 1:]
        touch = next((k for k, b in enumerate(fwd[:TTL_BARS]) if b[2] >= plan.entry), None)
        missed, fill, fill_k = False, plan.entry, touch
        if touch is not None and gap_miss:
            cap = entry_cap(plan.entry)
            o_t = fwd[touch][1]
            if o_t > cap:
                # Triggered above the cap: the order rests as a buy limit at the
                # cap and fills only if the tape comes back to it inside the
                # TTL — the adverse-selection fill a real stop-limit gets.
                back = next((k for k in range(touch, min(len(fwd), touch + TTL_BARS)) if fwd[k][3] <= cap), None)
                if back is None:
                    touch, missed = None, True
                else:
                    fill, fill_k = cap, back
            elif o_t > plan.entry:
                fill = o_t                            # triggered on the open, filled there (inside the cap)
        n_plans += 1
        rec = {"sym": sym, "day": ts.date().isoformat(), "t": ts.strftime("%H:%M"), "ts": ts, "window": window,
               "cum_vol": cum_vol, "pm_high": pm_hi, "hod_before": hi_before, "pb_index": n_plans,
               "price": round(plan.entry, 4), "stop_pct": round((plan.entry - plan.stop) / plan.entry * 100, 3),
               "gap": round(o / prev_close - 1, 3) if prev_close else None,
               "entry": round(plan.entry, 4), "stop": round(plan.stop, 4), "red": red,
               "gain": round(c / prev_close - 1, 3) if prev_close else None, "touched": touch is not None,
               "gap_missed": missed}
        if touch is not None:
            ent = fwd[fill_k:]
            rec["fill"] = round(fill, 4)
            for v in EXITS:
                r, why, t_out = simulate(ent, plan.entry, plan.stop, v, fill=fill if gap_miss else None)
                rec[v], rec[v + "_why"], rec[v + "_out"] = r, why, t_out
                rec[v + "_net"] = round(r - cost_r(plan.entry, plan.stop, why in ("stop", "trail")), 3)
            if hook is not None:
                hook(rec, ent, fill if gap_miss else plan.entry)
            rec["t_in"] = ent[0][0]
        out.append(rec)
    return out


def load(universe: list[str], cache: Path) -> list[dict]:
    plans = []
    for sym in universe:
        try:
            rows, prev = fetch(sym, cache)
        except Exception as exc:                      # noqa: BLE001
            print(f"  {sym}: fetch failed ({exc})", file=sys.stderr); continue
        by_day = defaultdict(list)
        for r in rows:
            if dtime(4, 0) <= r[0].time() < dtime(16, 0):
                by_day[r[0].date()].append(r)
        for day, rs in sorted(by_day.items()):
            pc = prev.get(day)
            early = [r[2] for r in rs if r[0].time() < FLAT]
            if not pc or not early or max(early) < (1 + GAIN_MIN) * pc:
                continue                              # never up 10 % before 11:30: not on the scanner
            plans += plans_for_day(sym, rs, pc, gap_miss=True)   # realistic stop-limit fills (2026-09-26)
    return plans


def cohort(ps: list[dict]) -> dict:
    t = [p for p in ps if p["touched"]]
    out = {"n": len(ps), "trig": len(t)}
    for v in EXITS:
        vals = [p[v] for p in t]
        out[v] = round(sum(vals), 2)
        out[v + "_win"] = round(sum(1 for x in vals if x > 0) / len(vals), 2) if vals else None
    days = defaultdict(float)
    for p in t:
        days[p["day"]] += p["trail"]
    out["days"] = len(days); out["days_pos_trail"] = sum(1 for x in days.values() if x > 0)
    days_f = defaultdict(float)
    for p in t:
        days_f[p["day"]] += p["fixed"]
    out["days_pos_fixed"] = sum(1 for x in days_f.values() if x > 0)
    return out


def portfolio(plans: list[dict], allowed, exit_: str, max_pos: int = 1) -> dict:
    """Take plans in time order, at most `max_pos` open at once, one per symbol."""
    by_day = defaultdict(list)
    for p in plans:
        if p["touched"] and allowed(p):
            by_day[p["day"]].append(p)
    total, trades, per_day = 0.0, 0, {}
    for day, ps in sorted(by_day.items()):
        open_until: list[tuple] = []
        day_r = 0.0
        for p in sorted(ps, key=lambda x: x["t_in"]):
            open_until = [(s, t) for s, t in open_until if t > p["t_in"]]
            if len(open_until) >= max_pos or any(s == p["sym"] for s, _ in open_until):
                continue
            open_until.append((p["sym"], p[exit_ + "_out"]))
            day_r += p[exit_]; trades += 1
        per_day[day] = round(day_r, 2); total += day_r
    return {"total": round(total, 2), "trades": trades, "per_day": per_day,
            "days_pos": sum(1 for x in per_day.values() if x > 0), "days": len(per_day)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default=os.environ.get("BACKTEST_CACHE", str(ROOT / "data" / "cache" / "backtest_recent")))
    ap.add_argument("--json", help="write every plan and every table here")
    args = ap.parse_args(argv)
    cache = Path(args.cache); cache.mkdir(parents=True, exist_ok=True)
    plans = load(UNIVERSE, cache)
    rth = [p for p in plans if p["window"] == "regular"]
    pm = [p for p in plans if p["window"] == "pre-market"]
    res = {"plans": len(plans), "symbol_days": len({(p["sym"], p["day"]) for p in plans}),
           "days": sorted({p["day"] for p in plans})}
    print(f"{res['plans']} plans on {res['symbol_days']} symbol-days, {len(res['days'])} sessions "
          f"({res['days'][0]} .. {res['days'][-1]}) · upper bound: fill at trigger, no costs, no halts, "
          f"pillars and A6 not modelled\n")

    def show(title, rows):
        print(title)
        print(f"  {'cohort':<34}{'n':>4}{'trig':>6}{'fixed':>8}{'trail':>8}{'BE+2R':>8}{'win(f)':>7}{'days +':>8}")
        for name, c in rows:
            print(f"  {name:<34}{c['n']:>4}{c['trig']:>6}{c['fixed']:>+8.2f}{c['trail']:>+8.2f}{c['be']:>+8.2f}"
                  f"{(c['fixed_win'] or 0):>7.0%}{c['days_pos_fixed']:>4}/{c['days']:<3}")
        print()

    tables = {}
    for win, ps in (("regular", rth), ("pre-market", pm)):
        rows = [("all rules green", cohort([p for p in ps if not p["red"]]))]
        for g in GATES:
            rows.append((f"{g} the ONLY red rule", cohort([p for p in ps if p["red"] == [g]])))
        rows.append(("two or more rules red", cohort([p for p in ps if len(p["red"]) >= 2])))
        rows.append(("every plan (no rules)", cohort(ps)))
        tables[win] = rows
        show(f"PLAN LEVEL · {win}" + (" (VWAP and volume not evaluable: no pre-market volume)" if win == "pre-market" else ""), rows)

    print("PORTFOLIO · regular hours · one position · A10 entry · stop gaps fill at the open")
    print(f"  {'rule set':<34}{'fixed':>9}{'trail':>9}{'BE+2R':>9}{'trades':>8}  days + (trail)")
    sets = {"current rules": lambda p: not p["red"]}
    for g in GATES:
        sets[f"current minus {g}"] = (lambda gg: lambda p: not [x for x in p["red"] if x != gg])(g)
    sets["current minus macd and volume"] = lambda p: not [x for x in p["red"] if x not in ("macd", "volume")]
    sets["no chart gates (price+rising only)"] = lambda p: not [x for x in p["red"] if x in ("price", "rising")]
    port = {}
    for name, f in sets.items():
        port[name] = {v: portfolio(rth, f, v) for v in EXITS}
        pf = port[name]
        print(f"  {name:<34}{pf['fixed']['total']:>+9.2f}{pf['trail']['total']:>+9.2f}{pf['be']['total']:>+9.2f}"
              f"{pf['trail']['trades']:>8}  {pf['trail']['days_pos']}/{pf['trail']['days']}")
    two = {v: portfolio(rth, sets["current rules"], v, max_pos=2) for v in EXITS}
    print(f"  {'current rules, TWO positions':<34}{two['fixed']['total']:>+9.2f}{two['trail']['total']:>+9.2f}"
          f"{two['be']['total']:>+9.2f}{two['trail']['trades']:>8}  {two['trail']['days_pos']}/{two['trail']['days']}")
    print("\nPER DAY · current rules · regular hours")
    cur = port["current rules"]
    for d in sorted(set(cur["trail"]["per_day"]) | set(cur["fixed"]["per_day"])):
        print(f"  {d}  fixed {cur['fixed']['per_day'].get(d, 0):+.2f}  trail {cur['trail']['per_day'].get(d, 0):+.2f}"
              f"  BE+2R {cur['be']['per_day'].get(d, 0):+.2f}")
    if args.json:
        Path(args.json).write_text(json.dumps({"summary": res, "tables": tables, "portfolio": port, "two_positions": two,
                                               "plans": plans}, default=str, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
