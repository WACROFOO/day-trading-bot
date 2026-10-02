#!/usr/bin/env python3
"""Stage 3 (10-second entries) and the partial exit, on the desk-time plans.

Preregistered as addendum 2026-10-02c in research/edge-hunt/PREREGISTRATION.md
before any run. Every variant is played on SIP prints (scripts/tick_replay.py
cache) from the moment the live desk arms the plan (scripts/desk_replay.py):

  D           the live order: stop-limit at the trigger, 1-minute stop, A3 trail
  S3-dip      wait for a 10-s micro pullback after the arm, buy its break
  S3-confirm  send only if the 10-s candle after the crossing one closes >= entry
  P-half2R    the D entry; half sold at +2 R by limit, the rest on the A3 trail
  P-half1R    the same at +1 R (reported)
  S3-dip+P2R  the dip entry with the half-at-2R exit (reported)

Every leg is sized and priced the way the live executor would: shares from
$40 / (the order's entry - stop) capped at $2,000; commission per order; half
the spread + 1 cent on a marketable side (entry, stop, trail); none on a
limit target. Spreads: the prevailing NBBO measured at the plan's D fill and
D exit (stage 1/2 `spread_at`), applied to that plan's legs in every variant —
same stock, same minutes, one price list for all, so the comparison is fair.

    python3 scripts/stage3.py run     [--since 2024-01-01]
    python3 scripts/stage3.py report  [--since 2024-01-01]
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import desk_replay as DR  # noqa: E402
import rules_audit as RA  # noqa: E402
import tick_replay as TR  # noqa: E402

OUTCOMES = ROOT / "data" / "cache" / "stage3_outcomes.pkl"
K = 49
ALPHA = 0.05 / K
CANDLE_MS = 10_000
LAT_MS = int(DR.LATENCY_S * 1000)
TTL_MS = TR.TTL_S * 1000
DECIDING = ("S3-dip", "S3-confirm", "P-half2R")
REPORTED = ("P-half1R", "S3-dip+P2R")
VARIANTS = ("D",) + DECIDING + REPORTED


# ------------------------------------------------------------------ entries
def _fill_from(T, P, level: float, i0: int, t_end: int):
    """Stop-limit at `level`, cap +0.3 %, working from print i0 until t_end (ms).
    Triggered by a print >= level, filled by the first print <= cap from then
    on at max(level, print). Returns (index, price) or None."""
    cap = RA.cap_of(level, TR.CAP_PCT)
    trig = False
    i, n = i0, len(T)
    while i < n and T[i] < t_end:
        if not trig and P[i] >= level:
            trig = True
        if trig and P[i] <= cap:
            return i, float(min(cap, max(level, P[i])))
        i += 1
    return None


def entry_stoplimit(T, P, entry: float, t_from: int):
    i0 = int(np.searchsorted(T, t_from, "left"))
    got = _fill_from(T, P, entry, i0, t_from + TTL_MS)
    return None if got is None else (got[0], got[1], entry)


def entry_confirm(T, P, entry: float, candle_end: int):
    """Only if the 10-s candle after the crossing candle closes at or above the
    entry (its last print; the previous print when it has none)."""
    b = int(np.searchsorted(T, candle_end + CANDLE_MS, "left"))
    if b == 0 or P[b - 1] < entry - 1e-9:
        return None
    return entry_stoplimit(T, P, entry, candle_end + CANDLE_MS + LAT_MS)


def entry_dip(T, P, stop: float, cross_candle_start: int, t_order: int, max_pull: int = 3):
    """The 10-second micro pullback after the arm. Candles on the desk's grid
    from the crossing candle. A candle above the push high extends the push;
    1..max_pull candles without a new high are the pullback; at each pullback
    candle's close (+ latency) a stop-limit rests at its high + 1 cent. A print
    at or under the stop kills the plan; 3 minutes from the arm, cancelled."""
    t_end = t_order + TTL_MS
    i = int(np.searchsorted(T, cross_candle_start, "left"))
    n = len(T)
    push_high, pulls, level, live_from = None, 0, None, None
    c0 = cross_candle_start
    while c0 < t_end:
        c1 = c0 + CANDLE_MS
        hi = None
        while i < n and T[i] < c1:
            p = float(P[i])
            if T[i] >= t_order:
                if p <= stop:
                    return None
                if level is not None and T[i] >= live_from and p >= level:
                    got = _fill_from(T, P, level, i, t_end)
                    return None if got is None else (got[0], got[1], level)
            hi = p if hi is None else max(hi, p)
            i += 1
        if hi is not None:
            if push_high is None or hi > push_high:
                push_high, pulls, level = hi, 0, None          # a new high: still pushing, no order
            else:
                pulls += 1
                if pulls > max_pull:
                    pulls, level = 0, None                      # lost interest: wait for a new push
                else:
                    level, live_from = round(hi + 0.01, 4), c1 + LAT_MS
        c0 = c1
        if i >= n:
            break
    return None


# ------------------------------------------------------------------ exits
def exit_from(T, P, i_fill: int, fill: float, entry: float, stop: float, flat_ms: int, half_at_r=None):
    """A3 trail (1 R = entry - stop, moved every 5 s on the high since the fill),
    a stop-market at the trail, flat at 11:30; with `half_at_r` half the shares
    are sold by limit at entry + half_at_r x R first. Returns legs
    [(fraction, price, kind)] with kind 'target' | 'stop' | 'trail' | 'flat',
    the exit time (ms) of the last leg, or None when the data ran out."""
    rps = entry - stop
    level, high = stop, fill
    t_fill = int(T[i_fill])
    next_trail = t_fill + TR.TRAIL_EVERY_S * 1000
    target = round(entry + half_at_r * rps, 4) if half_at_r else None
    legs, left = [], 1.0
    for j in range(i_fill + 1, len(T)):
        tj, pj = int(T[j]), float(P[j])
        if tj >= flat_ms:
            legs.append((left, float(P[j - 1]), "flat"))
            return legs, int(T[j - 1])
        while tj >= next_trail:
            level = max(level, round(high - TR.TRAIL_R * rps, 4))
            next_trail += TR.TRAIL_EVERY_S * 1000
        if pj <= level:
            legs.append((left, pj, "trail" if level > stop else "stop"))
            return legs, tj
        if target is not None and left == 1.0 and pj >= target:
            legs.append((0.5, target, "target"))
            left = 0.5
        high = max(high, pj)
    return None


# ------------------------------------------------------------------ costs
def _comm(q: int, px: float) -> float:
    return min(max(1.0, 0.005 * q), max(1.0, 0.01 * q * px))


def price_trade(entry: float, stop: float, fill: float, legs, s_in: float, s_out: float,
                risk: float = 40.0, notional: float = 2000.0):
    """(gross R, cost R, stopish) for one trade, sized like the live executor:
    shares = $40 / (entry - stop) capped at $2,000; a target leg is half the
    shares (rounded down), the last leg the rest."""
    rps = entry - stop
    sh = max(1, min(int(risk // rps), int(notional // entry)))
    split = any(k == "target" for _, _, k in legs)
    pnl, cost = 0.0, _comm(sh, fill) + sh * (s_in / 2 + 0.01)
    for _, px, kind in legs:
        q = (sh // 2 if kind == "target" else sh - sh // 2) if split else sh
        if q <= 0:
            continue
        pnl += q * (px - fill)
        cost += _comm(q, px) + (q * (s_out / 2 + 0.01) if kind in ("stop", "trail") else 0.0)
    unit = sh * rps
    return pnl / unit, cost / unit, any(k in ("stop", "trail") for _, _, k in legs)


# ------------------------------------------------------------------ the run
def _ticks(fx, sym, day, t_from_s: int, t_to_s: int):
    day0 = TR.day_open(day)
    k0, k1 = (t_from_s - day0) // TR.CHUNK_S, (t_to_s - day0) // TR.CHUNK_S
    ts, ps = [], []
    for k in range(int(k0), int(k1) + 1):
        t, p = fx.chunk(sym, day, k, day0)
        ts.append(t); ps.append(p)
    return np.concatenate(ts), np.concatenate(ps).astype(np.float64)


def run_plan(fx, p: dict, d: dict, spreads: tuple) -> dict:
    flat_s = TR.at_et(p["day"], TR.FLAT)
    t_order = int(d["t_order"] * 1000)
    cross_start = int(d["candle_end"]) - CANDLE_MS
    s_in, s_out = spreads
    out = {}
    for horizon in (20 * 60, None):
        t_to = flat_s if horizon is None else min(flat_s, int(d["t_order"]) + horizon)
        T, P = _ticks(fx, p["sym"], p["day"], cross_start // 1000, t_to)
        flat_ms = flat_s * 1000 if horizon is None or t_to >= flat_s else 10 ** 15
        entries = {"D": entry_stoplimit(T, P, p["entry"], t_order),
                   "S3-confirm": entry_confirm(T, P, p["entry"], int(d["candle_end"])),
                   "S3-dip": entry_dip(T, P, p["stop"], cross_start, t_order)}
        todo = {"D": ("D", None), "S3-dip": ("S3-dip", None), "S3-confirm": ("S3-confirm", None),
                "P-half2R": ("D", 2.0), "P-half1R": ("D", 1.0), "S3-dip+P2R": ("S3-dip", 2.0)}
        out, missing = {}, False
        for name, (ent, half) in todo.items():
            e = entries[ent]
            if e is None:
                out[name] = {"filled": False}
                continue
            i_fill, fill, order_entry = e
            ex = exit_from(T, P, i_fill, fill, order_entry, p["stop"], flat_ms, half)
            if ex is None:
                missing = True
                break
            legs, t_out = ex
            g, c, stopish = price_trade(order_entry, p["stop"], fill, legs, s_in, s_out)
            out[name] = {"filled": True, "t_in": int(T[i_fill]) // 1000, "t_out": t_out // 1000, "gross": g,
                         "cost": c, "stopish": stopish, "fill": fill, "legs": legs}
        if not missing:
            return out
    return out


def cmd_run(args) -> int:
    from momentum_platform.datasources.alpaca_source import client_from_env
    fx = TR.Fetcher(client_from_env(feed="sip"))
    desk = pickle.loads(DR.OUTCOMES.read_bytes())
    plans = {(p["sym"], p["arm"]): p for p in TR.load_plans(args.since, args.until)}
    done = pickle.loads(OUTCOMES.read_bytes()) if OUTCOMES.exists() else {}
    todo = []
    for key, d in desk.items():
        if key in done or "t_order" not in d or d["red"] or d["fade"] > RA.BASE["fade"] or key not in plans:
            continue
        o = d.get("out") or {}
        if not o.get("filled") or o.get("spread_in") is None:
            continue                                   # no measured spread: cannot price it the same way
        todo.append((key, d, (o["spread_in"], o.get("spread_out") or o["spread_in"])))
    print(f"{len(todo)} desk-time plans with a measured fill to run; {len(done)} done", flush=True)
    for k, (key, d, sp) in enumerate(sorted(todo, key=lambda x: (plans[x[0]]["day"], x[0])), 1):
        try:
            done[key] = run_plan(fx, plans[key], d, sp)
        except Exception as exc:                                        # noqa: BLE001
            print(f"  {key}: {exc}", flush=True)
        if k % 100 == 0 or k == len(todo):
            OUTCOMES.write_bytes(pickle.dumps(done))
            print(f"  {k}/{len(todo)} · {fx.requests} requests", flush=True)
    OUTCOMES.write_bytes(pickle.dumps(done))
    return 0


def cmd_report(args) -> int:
    desk = pickle.loads(DR.OUTCOMES.read_bytes())
    res3 = pickle.loads(OUTCOMES.read_bytes())
    plans = TR.load_plans(args.since, args.until)
    DR.attach(plans, desk)
    by_day = defaultdict(list)
    for p in plans:
        by_day[p["day"]].append(p)
    # Sessions where every desk-passing plan with a measured D fill was run.
    days = sorted(d for d, ps in by_day.items()
                  if any(p.get("desk") for p in ps)
                  and all((p["sym"], p["arm"]) in res3 for p in ps
                          if p.get("desk") and not p["desk"]["red"] and p["desk"]["fade"] <= RA.BASE["fade"]
                          and (desk.get((p["sym"], p["arm"]), {}).get("out") or {}).get("filled")
                          and (desk[(p["sym"], p["arm"])]["out"]).get("spread_in") is not None))
    trades = {}
    for v in VARIANTS:
        sub = {}
        for day in days:
            ps = []
            for p in by_day[day]:
                r = res3.get((p["sym"], p["arm"]))
                q = dict(p, out=dict(p["out"]))
                if r is None:
                    q["desk"] = None                    # not run: not a candidate in any variant
                else:
                    o = r.get(v) or {"filled": False}
                    q["out"][(v, "base")] = ((o["t_in"], o["t_out"], o["gross"], o["stopish"], o["fill"])
                                             if o.get("filled") else None)
                    q["s3cost"] = o.get("cost")
                ps.append(q)
            sub[day] = ps
        raw = RA.portfolio(sub, dict(RA.BASE, mode=v, gates="desk", costs="none"))
        out = []
        for t in raw:
            q = next(x for x in sub[t["day"]] if x["sym"] == t["sym"] and x["t"] == t["t"])
            out.append(dict(t, net=t["gross"] - (q["s3cost"] or 0.0)))
        trades[v] = out
    print(f"stage 3 · {len(days)} sessions {days[0] if days else '-'}..{days[-1] if days else '-'} · "
          f"costs: real spread at each fill, commission per order · alpha 0.05/{K}")
    print(f"\n  {'variant':<14}{'n':>6}{'net R':>9}{'gross R':>9}{'total':>9}{'win %':>7}"
          f"{'2024':>8}{'2025':>8}{'2026':>8}{'lb vs D':>9}  verdict")
    res = {}
    base = trades["D"]
    by_year_d = {y: RA.stats([t for t in base if t["day"][:4] == y]) for y in ("2024", "2025", "2026")}
    for v in VARIANTS:
        tr = trades[v]
        s = RA.stats(tr)
        yrs = {y: RA.stats([t for t in tr if t["day"][:4] == y]) for y in ("2024", "2025", "2026")}
        lb = float("nan") if v == "D" else RA.paired_lb(tr, base, alpha=ALPHA)
        if v == "D":
            verdict = "reference"
        else:
            ok = (s.get("n", 0) >= 200 and lb == lb and lb > 0
                  and all(yrs[y].get("n", 0) and by_year_d[y].get("n", 0)
                          and yrs[y]["mean"] > by_year_d[y]["mean"] for y in yrs))
            verdict = ("PASSES — switch OFF until 200 prospective trades" if ok else "keep D")
            if v in REPORTED:
                verdict = f"({verdict}, reported only)"
        res[v] = {"stats": s, "years": yrs, "lb": lb, "verdict": verdict}
        ys = "".join(f"{yrs[y].get('mean', float('nan')):>+8.3f}" for y in ("2024", "2025", "2026"))
        print(f"  {v:<14}{s.get('n', 0):>6}{s.get('mean', float('nan')):>+9.3f}{s.get('gross', float('nan')):>+9.3f}"
              f"{s.get('total', 0):>+9.1f}{100 * s.get('win', 0):>6.1f}%{ys}"
              f"{(f'{lb:+.3f}' if lb == lb else ''):>9}  {verdict}")
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=1, default=str))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "report"):
        s = sub.add_parser(name)
        s.add_argument("--since", default="2024-01-01")
        s.add_argument("--until")
        if name == "report":
            s.add_argument("--json")
    args = ap.parse_args(argv)
    RA.E.COST_MODEL = "live"
    return cmd_run(args) if args.cmd == "run" else cmd_report(args)


if __name__ == "__main__":
    raise SystemExit(main())
