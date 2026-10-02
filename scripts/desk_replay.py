#!/usr/bin/env python3
"""Stage 2 of the tick replay: each plan as the LIVE DESK arms it, while the
trigger minute is still forming, instead of at the minute's close.

Why this is exact and cheap (2026-10-02). The desk rebuilds every 3 s and
runs `FirstPullbackDetector` over the complete minutes plus the forming one
(`session_builder.build_session_from_records`). The pullback structure, so
the trigger, the entry and the stop, depends only on COMPLETE candles; the
detector arms on the trigger candle the moment its high exceeds the previous
candle's high. So the desk arms the same plans as the 1-minute backtest, with
the same entry and stop. Two things differ, and both are rebuilt from prints:

  1. WHEN: the desk sees closed 10-second candles, so it arms at the close of
     the 10-s candle holding the first print above the trigger, plus the
     rebuild (≤ 3 s) and the runner's loop (≤ 5 s). LATENCY_S is the
     expected sum of those two, added to the 10-s candle's close.
  2. THE GATES: VWAP, the 9 EMA, MACD and "still rising" are judged with the
     half-formed trigger minute as the last bar (its closed 10-s candles),
     exactly as `chart_gates(bars_by_symbol)` sees it live.

From that moment the order is replayed on the prints (scripts/tick_replay.py
`replay`: A10 stop-limit, stop-market stop, A3 trail every 5 s, 11:30 flat).

    python3 scripts/desk_replay.py fetch  [--since 2024-01-01] [--limit N]
    python3 scripts/desk_replay.py report [--since 2024-01-01]

Outcomes in data/cache/desk_outcomes.pkl; ticks shared with tick_replay.
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from collections import defaultdict
from datetime import time as dtime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import backtest_history as H  # noqa: E402
import rules_audit as RA  # noqa: E402
import tick_replay as TR  # noqa: E402
from momentum_platform import indicators as I  # noqa: E402

OUTCOMES = ROOT / "data" / "cache" / "desk_outcomes.pkl"
CANDLE_S = 10                 # the desk's closed 10-second candles
LATENCY_S = 4.0               # rebuild (3 s loop, 1.5 expected) + runner (5 s loop, 2.5 expected)
ENTRY_BUFFER = 0.01           # FirstPullbackDetector entry_buffer: entry = trigger high + 0.01


def candidates(plans: list[dict]) -> list[dict]:
    """Plans that pass every live gate that does NOT depend on the trigger
    candle: price, the pullback-volume gate, the stop floor, the spread, the
    window. The chart gates and "still rising" are judged at desk time."""
    loose = dict(RA.BASE, fade=None)
    return [p for p in plans
            if RA.passes(dict(p, red=[r for r in p["red"] if r in ("price", "volume")]), loose)]


def desk_moment(p: dict, rows: list, t: np.ndarray, pr: np.ndarray, sz: np.ndarray,
                latency_s: float = LATENCY_S) -> dict:
    """The desk's view of plan p. `rows` the day's 1-minute bars (H.to_rows),
    t/pr/sz the prints of the trigger minute's chunk (ms, price, size)."""
    trigger_high = round(p["entry"] - ENTRY_BUFFER, 4)
    idx = next((i for i, r in enumerate(rows) if int(r[0].timestamp()) == p["arm"]), None)
    if idx is None:
        return {"why": "trigger bar not in the bar file"}
    a0, a1 = p["arm"] * 1000, (p["arm"] + 60) * 1000
    lo, hi = np.searchsorted(t, a0, "left"), np.searchsorted(t, a1, "left")
    mt, mp, ms = t[lo:hi], np.round(pr[lo:hi].astype(np.float64), 4), sz[lo:hi]
    above = np.nonzero(mp > trigger_high + 1e-9)[0]
    if not len(above):
        return {"why": "no last-sale print above the trigger in the minute"}
    t_cross = int(mt[above[0]])
    candle_end = a0 + CANDLE_S * 1000 * ((t_cross - a0) // (CANDLE_S * 1000) + 1)
    seen = mt < candle_end
    fo, fh, fl, fc = float(mp[seen][0]), float(mp[seen].max()), float(mp[seen].min()), float(mp[seen][-1])
    fv = float(ms[seen].sum())
    hist = [[int(r[0].timestamp()), r[1], r[2], r[3], r[4], r[5]] for r in rows[:idx]]
    hist.append([p["arm"], fo, fh, fl, fc, fv])
    volume_ok = "volume" not in p["red"]
    red = RA._red(I.chart_gates(hist), p["entry"], volume_ok)
    day_hi = max([h[2] for h in hist])
    fade = 100.0 * (day_hi - fc) / day_hi if day_hi else 0.0
    t_order = candle_end / 1000.0 + latency_s
    return {"t_cross": t_cross, "candle_end": candle_end, "t_order": t_order, "red": red, "fade": fade,
            "last": fc, "secs_before_close": (a1 - (t_order * 1000)) / 1000.0}


def run_one(fx: TR.Fetcher, p: dict, rows: list) -> dict:
    day0 = TR.day_open(p["day"])
    k = (p["arm"] - day0) // TR.CHUNK_S
    t, pr, sz = fx.chunk(p["sym"], p["day"], int(k), day0, sizes=True)
    d = desk_moment(p, rows, t, pr, sz)
    if "t_order" not in d:
        return d
    if d["red"] or d["fade"] > RA.BASE["fade"]:
        return d                                   # refused at desk time: no order, no ticks needed
    flat_t = TR.at_et(p["day"], TR.FLAT)
    # tick_replay.replay_plan sends at arm + 60; give it the desk's order second.
    plan = dict(p, arm=int(d["t_order"]) - 60)
    out = TR.replay_plan(fx, plan) if int(d["t_order"]) < flat_t else None
    if out and out.get("filled"):
        out["spread_in"] = fx.spread_at(p["sym"], out["t_in"])
        out["spread_out"] = fx.spread_at(p["sym"], out["t_out"]) if out["stopish"] else None
    d["out"] = out or {"filled": False}
    return d


def cmd_fetch(args) -> int:
    from momentum_platform.datasources.alpaca_source import client_from_env
    fx = TR.Fetcher(client_from_env(feed="sip"))
    plans = candidates(TR.load_plans(args.since, args.until))
    plans.sort(key=lambda p: (p["day"], p["sym"], p["arm"]))
    done = pickle.loads(OUTCOMES.read_bytes()) if OUTCOMES.exists() else {}
    todo = [p for p in plans if (p["sym"], p["arm"]) not in done]
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(plans)} candidate plans since {args.since}; {len(done)} done, {len(todo)} to go", flush=True)
    bars_day, rows_cache = None, {}
    t0 = time.monotonic()
    for k, p in enumerate(todo, 1):
        if p["day"] != bars_day:
            f = Path(args.cache) / f"{p['day']}.json"
            raw = json.loads(f.read_text()) if f.exists() else {}
            rows_cache = {s: [r for r in H.to_rows(v) if dtime(4, 0) <= r[0].time() < dtime(16, 0)]
                          for s, v in raw.items()}
            bars_day = p["day"]
        try:
            d = run_one(fx, p, rows_cache.get(p["sym"], []))
        except Exception as exc:                                        # noqa: BLE001
            print(f"  {p['day']} {p['sym']} {p['t']}: {exc}", flush=True)
            continue
        done[(p["sym"], p["arm"])] = d
        if k % 25 == 0 or k == len(todo):
            OUTCOMES.write_bytes(pickle.dumps(done))
            rate = k / max(1e-9, time.monotonic() - t0) * 60
            print(f"  {k}/{len(todo)} · {fx.requests} requests · {rate:.0f} plans/min", flush=True)
    OUTCOMES.write_bytes(pickle.dumps(done))
    return 0


def attach(plans: list[dict], done: dict) -> None:
    for p in plans:
        d = done.get((p["sym"], p["arm"]))
        if d is None or "t_order" not in d:
            continue
        p["desk"] = {"red": d["red"], "fade": d["fade"]}
        o = d.get("out")
        if o is None:
            continue
        if not o.get("filled"):
            p["out"][("D", "base")] = None
            continue
        p["out"][("D", "base")] = (o["t_in"] // 1000, o["t_out"] // 1000, round(o["r"], 4), o["stopish"], o["fill"])
        p["desk_tick"] = {"spread_in": o.get("spread_in"), "spread_out": o.get("spread_out")}


def cmd_report(args) -> int:
    plans = TR.load_plans(args.since, args.until)
    cand = candidates(plans)
    done_d = pickle.loads(OUTCOMES.read_bytes())
    done_t = pickle.loads(TR.OUTCOMES.read_bytes()) if TR.OUTCOMES.exists() else {}
    TR.attach(plans, done_t)
    attach(plans, done_d)
    by_day = defaultdict(list)
    for p in plans:
        by_day[p["day"]].append(p)
    cand_days = defaultdict(list)
    for p in cand:
        cand_days[p["day"]].append(p)
    # Complete sessions: every candidate seen at desk time AND every bar-gate plan tick-replayed.
    full = sorted(d for d, ps in cand_days.items()
                  if all((p["sym"], p["arm"]) in done_d for p in ps)
                  and all(("T", "base") in p["out"] for p in by_day[d] if RA.passes(p, RA.BASE)))
    sub = {d: by_day[d] for d in full}
    seen = [done_d[(p["sym"], p["arm"])] for d in full for p in cand_days[d]]
    timed = [d for d in seen if "t_order" in d]
    print(f"desk replay · {len(seen)} candidate plans on {len(full)} complete sessions "
          f"{full[0] if full else '-'}..{full[-1] if full else '-'}")
    print(f"  armed while the minute formed: {len(timed)} · no last-sale print above the trigger: "
          f"{sum(1 for d in seen if 'no last-sale' in d.get('why', ''))}")
    if timed:
        early = np.array([d["secs_before_close"] for d in timed])
        print(f"  order sent before the trigger minute closed: median {np.median(early):.0f} s "
              f"(p10 {np.percentile(early, 10):.0f} s, p90 {np.percentile(early, 90):.0f} s)")
    # Gate verdicts: bar close vs desk time, on the same candidates.
    flips = defaultdict(int)
    for d in full:
        for p in cand_days[d]:
            if "desk" not in p:
                continue
            bar_ok = not p["red"] and p["fade"] <= RA.BASE["fade"]
            desk_ok = not p["desk"]["red"] and p["desk"]["fade"] <= RA.BASE["fade"]
            flips[(bar_ok, desk_ok)] += 1
    print(f"  gates at the bar close vs at desk time: both pass {flips[(True, True)]} · bar only "
          f"{flips[(True, False)]} · desk only {flips[(False, True)]} · neither {flips[(False, False)]}")
    rows = []
    for name, c in (("T  bar-close arm, ticks, proxy", dict(RA.BASE, mode="T")),
                    ("D  desk-time arm, ticks, proxy", dict(RA.BASE, mode="D", gates="desk")),
                    ("D  desk-time arm, ticks, gross", dict(RA.BASE, mode="D", gates="desk", costs="none"))):
        rows.append((name, RA.portfolio(sub, c)))
    real = {"T": [], "D": []}
    for mode, gates, key in (("T", "close", "tick"), ("D", "desk", "desk_tick")):
        for t in RA.portfolio(sub, dict(RA.BASE, mode=mode, gates=gates, costs="none")):
            p = next(x for x in sub[t["day"]] if x["sym"] == t["sym"] and x["t"] == t["t"])
            o = p["out"][(mode, "base")]
            cr = TR.cost_real(dict(p, tick=p.get(key) or {}), o[3])
            if cr is not None:
                real[mode].append(dict(t, net=t["gross"] - cr))
    rows.append(("T  bar-close arm, REAL spread", real["T"]))
    rows.append(("D  desk-time arm, REAL spread", real["D"]))
    print(f"\n  {'model':<34}{'n':>6}{'net R/trade':>13}{'total R':>10}{'win %':>8}{'max DD':>8}")
    res = {}
    for name, tr in rows:
        s = RA.stats(tr)
        res[name] = s
        print(f"  {name:<34}{s.get('n', 0):>6}{s.get('mean', float('nan')):>+13.3f}{s.get('total', 0):>+10.1f}"
              f"{100 * s.get('win', 0):>7.1f}%{s.get('max_dd', 0):>8.1f}")
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("fetch", "report"):
        s = sub.add_parser(name)
        s.add_argument("--since", default="2024-01-01")
        s.add_argument("--until")
        s.add_argument("--cache", default=str(H.CACHE))
        if name == "fetch":
            s.add_argument("--limit", type=int)
        else:
            s.add_argument("--json")
    args = ap.parse_args(argv)
    RA.E.COST_MODEL = "live"
    return cmd_fetch(args) if args.cmd == "fetch" else cmd_report(args)


if __name__ == "__main__":
    raise SystemExit(main())
