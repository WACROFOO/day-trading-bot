#!/usr/bin/env python3
"""Green-run continuation: the 1-minute chart climbs with every live gate green
and no 1-minute pullback; the 10-second chart times the entry; the 1-minute
structure sets the risk. Preregistered as addendum 2026-10-05
(research/edge-hunt/PREREGISTRATION.md) before its first run.

Why (owner, 2026-10-05, after SAIQ and JAGX): "those green candles with the
setup all set perfectly need to be traded somehow ... if a one minute bar
doesn't allow a pullback, the 10s should confirm it". The earlier 10-second
tests either applied none of the live gates (runup_micro: no VWAP/EMA9/MACD,
no 2 % stop floor) or put the stop at the 10-second low, where costs ate
~1 R a trade. This one keeps every live gate and lets the 1-minute bar set
the stop.

    python3 scripts/green_run.py run

Same 300 symbol-days and SIP prints as scripts/runup_micro.py (cached), the
same fill/exit engine, real NBBO spreads at fill and exit, $40 / $2,000.
"""
from __future__ import annotations

import bisect  # noqa: F401
import json
import pickle
import random
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import rules_audit as RA  # noqa: E402
import runup_micro as RM  # noqa: E402
import tick_replay as TR  # noqa: E402

OUT = ROOT / "research" / "paper-exercise" / "reports"
STOP_FLOOR_PCT, SPREAD_K, FADE_MAX = 2.0, 4.0, 25.0
K_RANDOM = 5
ALPHA = 0.05


# ------------------------------------------------------------------ 1-minute context
def minute_context(day, sym):
    """Per completed 1-minute bar (04:00 on): close time, the gates as the live
    desk reads them on that bar, its low, and the 5-bar dollar volume."""
    f = RM.HISTORY / f"{day}.json"
    rows = (json.loads(f.read_text()) if f.exists() else {}).get(sym) or []
    if len(rows) < 30:
        return None
    ts = np.array([int(datetime.fromisoformat(r[0].replace("Z", "+00:00")).timestamp()) for r in rows])
    o, h, l, c, v = (np.array([r[k] for r in rows], dtype=float) for k in (1, 2, 3, 4, 5))
    vwap = np.cumsum(v * (h + l + c) / 3) / np.maximum(1, np.cumsum(v))
    e9 = RM._ema(c, 9)
    m = RM._ema(c, 12) - RM._ema(c, 26)
    sig = RM._ema(m, 9)
    hod = np.maximum.accumulate(h)
    prev_hod = np.r_[-np.inf, hod[:-1]]
    green = c > o
    out = []
    for i in range(len(rows)):
        dv5 = float(np.sum(c[max(0, i - 4):i + 1] * v[max(0, i - 4):i + 1]))
        out.append(dict(close_t=int(ts[i]) + 60, ok=bool(
            i >= 30 and green[i] and green[i - 1] and h[i] >= prev_hod[i]          # climbing, new high of day
            and c[i] > vwap[i] and c[i] > e9[i] and m[i] > sig[i] and m[i] - sig[i] > 0
            and (hod[i] - c[i]) / hod[i] * 100 <= FADE_MAX),
            low=float(l[i]), dv5=dv5))
    return out


def _ctx_at(ctx, t):
    """The last bar completed at or before t."""
    import bisect
    keys = ctx[0].get("_keys") if ctx else None
    if keys is None and ctx:
        keys = [b["close_t"] for b in ctx]
        ctx[0]["_keys"] = keys
    i = bisect.bisect_right(keys, t) - 1 if ctx else -1
    return ctx[i] if i >= 0 else None


# ------------------------------------------------------------------ the setup
def run_day(r, t, p, bars, ctx, stop_mode):
    flat = TR.at_et(r["day"], "11:30")
    armed = lambda ts: bool((_ctx_at(ctx, ts) or {}).get("ok"))      # noqa: E731
    out, busy = [], 0
    for t_arm, entry, stop10 in RM._signals(bars, armed, None, False):
        if t_arm * 1000 < busy:
            continue
        b = _ctx_at(ctx, t_arm)
        stop = round(b["low"] - 0.01, 4) if stop_mode == "1m" else stop10
        if not (2.0 <= entry <= 20.0) or stop >= entry:
            continue
        stop_pct = (entry - stop) / entry * 100
        pm = datetime.fromtimestamp(t_arm, TR.RA.E.ET).strftime("%H:%M") < "09:30"
        spread = RA.PROXY.spread(entry, pm, b["dv5"])
        if stop_pct < STOP_FLOOR_PCT or (spread > 0 and (entry - stop) / spread < SPREAD_K):
            continue
        x = RM._trade(t, p, entry, stop, t_arm, flat, RM.TTL_ENTRY_S)
        if x:
            busy = x["t_out"]
            out.append(dict(sym=r["sym"], day=r["day"], t_arm=t_arm, entry=entry, stop=stop, pm=pm, **x))
    return out


def random_baseline(r, t, p, bars, ctx, trade, k=K_RANDOM):
    """k market entries at random 10-s closes inside the same green-run windows, same stop %."""
    flat = TR.at_et(r["day"], "11:30")
    closes = [b[0] + 10 for b in bars if (_ctx_at(ctx, b[0] + 10) or {}).get("ok")]
    rng = random.Random(f"green{r['day']}{r['sym']}{trade['t_arm']}")
    pct = (trade["entry"] - trade["stop"]) / trade["entry"]
    res = []
    for ts in rng.sample(closes, min(k, len(closes))):
        i = int(np.searchsorted(t, ts * 1000))
        if i >= len(t):
            continue
        e = float(p[i])
        x = RM._trade(t, p, e, round(e * (1 - pct), 4), ts, flat, RM.TTL_ENTRY_S)
        if x:
            res.append((r["day"], x["r"]))
    return res


def day_lb(a, b, alpha=ALPHA, draws=10000, seed=20261005):
    """Day-clustered bootstrap lower bound of mean(a) - mean(b); a, b = [(day, r)]."""
    days = sorted({d for d, _ in a} | {d for d, _ in b})
    ix = {d: i for i, d in enumerate(days)}
    sa, na, sb, nb = (np.zeros(len(days)) for _ in range(4))
    for d, x in a:
        sa[ix[d]] += x; na[ix[d]] += 1
    for d, x in b:
        sb[ix[d]] += x; nb[ix[d]] += 1
    pick = np.random.default_rng(seed).integers(0, len(days), size=(draws, len(days)))
    diff = sa[pick].sum(1) / np.maximum(1, na[pick].sum(1)) - sb[pick].sum(1) / np.maximum(1, nb[pick].sum(1))
    return float(np.quantile(diff, alpha))


SAMPLE2 = OUT / "green_run_sample2.json"


def cmd_sample2(args) -> int:
    """Addendum 2026-10-06: 600 new runner symbol-days, none of the first 300."""
    import pickle
    alerts = pickle.load(open(args.alerts, "rb"))[0]
    first = {(r["day"], r["sym"]) for r in json.loads(RM.SAMPLE.read_text())["rows"]}
    by = {}
    for a in alerts:
        if a["scanner"] != "running_up" or a["day"] < "2024-01-01" or not a.get("price_band"):
            continue
        if (a["day"], a["sym"]) in first:
            continue
        by.setdefault((a["day"], a["sym"]), []).append(int(a["epoch"]))
    keys = sorted(by)
    pick = sorted(random.Random(20261006).sample(keys, min(600, len(keys))))
    rows = [{"day": d, "sym": s, "alerts": sorted(by[(d, s)])} for d, s in pick]
    SAMPLE2.write_text(json.dumps({"seed": 20261006, "population": len(keys), "rows": rows}, indent=0))
    print(f"population {len(keys)} (first 300 excluded) · sample {len(rows)}")
    return 0


def cmd_fetch(args) -> int:
    rows = json.loads(Path(args.sample).read_text())["rows"]
    fx = RM._fetcher()
    for n, r in enumerate(rows, 1):
        day0, ks = RM._chunks(r)
        for k in ks:
            fx.chunk(r["sym"], r["day"], k, day0)
        if n % 25 == 0:
            print(f"{n}/{len(rows)} symbol-days · requests {fx.requests}", flush=True)
    print(f"done · requests {fx.requests}")
    return 0


def cmd_run(args) -> int:
    meta = json.loads(Path(args.sample).read_text())
    fx = RM._fetcher()
    qc = json.loads(RM.QUOTES.read_text()) if RM.QUOTES.exists() else {}
    res = {"1m": [], "10s": []}
    rnd = []
    for r in meta["rows"]:
        tp = RM._prints(r)
        ctx = minute_context(r["day"], r["sym"])
        if tp is None or not ctx:
            continue
        t, p = tp
        bars = RM._bars10(t, p)
        for mode in ("1m", "10s"):
            tr = run_day(r, t, p, bars, ctx, mode)
            res[mode] += tr
            if mode == "1m":
                for x in tr:
                    rnd += random_baseline(r, t, p, bars, ctx, x)
    S = res["1m"]
    for x in S:
        x["s_in"] = RM._quote(fx, qc, x["sym"], x["t_in"])
        x["s_out"] = RM._quote(fx, qc, x["sym"], x["t_out"]) if x["how"] in ("trail", "stop") else 0.0
    RM.QUOTES.write_text(json.dumps(qc))
    L = []
    pr = lambda s="": (print(s), L.append(s))                       # noqa: E731
    pr(f"green-run continuation · addendum 2026-10-05 · {len(meta['rows'])} symbol-days 2024-01-02..2026-08-21 "
       f"(the runup_micro sample) · gates: new high of day on 2 green 1-min bars, above VWAP and 9 EMA, MACD > signal, "
       f"<= 25% off the high, stop >= 2%, stop >= 4x proxy spread · 10-s pause, entry = pause high + 1c")
    pr()
    pr("GROSS R per trade (no costs)")
    pr(f"  S    stop at the 1-min bar low     {RM._stats([x['r'] for x in S])}")
    pr(f"  S10  stop at the 10-s pause low    {RM._stats([x['r'] for x in res['10s']])}")
    pr(f"  RND  random entries, same windows  {RM._stats([v for _, v in rnd])}")
    for y in ("2024", "2025", "2026"):
        pr(f"  S {y}  {RM._stats([x['r'] for x in S if x['day'].startswith(y)])}")
    pr(f"  S pre-market  {RM._stats([x['r'] for x in S if x['pm']])}")
    pr(f"  S regular     {RM._stats([x['r'] for x in S if not x['pm']])}")
    if S and rnd:
        lb = day_lb([(x["day"], x["r"]) for x in S], rnd)
        pr(f"  S minus random, gross, day-clustered one-sided 95% lower bound: {lb:+.3f}")
    q = [x for x in S if x["s_in"] is not None and x["s_out"] is not None]
    if q:
        nets, comp = [], {"commission": [], "half_spread_in": [], "half_spread_out": []}
        for x in q:
            sh, r_usd, cr, cd = RM.costs(x, x["s_in"], x["s_out"])
            billed = cr["commission"] + cr["half_spread_in"] + cr["half_spread_out"]
            nets.append((x["day"], x["r"] - billed))
            for k in comp:
                comp[k].append(cr[k])
        pr()
        pr(f"COSTS on {len(q)} trades with quotes: " + " · ".join(f"{k} {np.mean(v):.3f} R" for k, v in comp.items()))
        nv = np.array([v for _, v in nets])
        pr(f"  NET R per trade {nv.mean():+.3f} (median {np.median(nv):+.3f}, total {nv.sum():+.1f}, win {100 * np.mean(nv > 0):.0f}%)")
        pr(f"  stop % median {np.median([100 * x['rps'] / x['fill'] for x in q]):.2f}")
        lbn = day_lb(nets, [(d, 0.0) for d, _ in nets])
        pr(f"  net mean, day-clustered one-sided 95% lower bound: {lbn:+.3f}")
    (OUT / f"green_run{args.tag}_output.txt").write_text("\n".join(L) + "\n")
    (OUT / f"green_run{args.tag}_results.json").write_text(json.dumps({"S": S, "S10": [x["r"] for x in res["10s"]],
                                                            "RND": [v for _, v in rnd]}, default=float))
    return 0


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["run", "sample2", "fetch"])
    ap.add_argument("--sample", default=str(RM.SAMPLE))
    ap.add_argument("--tag", default="")
    ap.add_argument("--alerts")
    a = ap.parse_args(argv)
    return {"run": cmd_run, "sample2": cmd_sample2, "fetch": cmd_fetch}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
