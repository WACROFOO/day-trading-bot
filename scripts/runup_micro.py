#!/usr/bin/env python3
"""Runner + 10-second micro pullback + 5-minute confirmation — the assessment
preregistered as addendum 2026-10-02e (research/edge-hunt/PREREGISTRATION.md).

The owner's idea after AMOD 2026-10-02: a name the Running Up scanner flags as
climbing can be bought at a 10-second micro pullback even when the 1-minute
chart shows none, and a 5-minute chart in an uptrend confirms it.

    python3 scripts/runup_micro.py sample --alerts PATH/alerts.pkl   (writes the fixed sample)
    python3 scripts/runup_micro.py fetch                              (SIP prints, cached; resumable)
    python3 scripts/runup_micro.py run                                (detect, replay, quotes, report)

Setup S, everything point-in-time:
  runner   armed from a running_up alert bar's close for 10 minutes
  5-min    last COMPLETED 5-minute bar closes above its EMA9 and MACD line > signal
  10-s     the 6 bars before the pause: >= 3 green, span >= 1 %; a pause of 1-3
           bars, none above that high, low not under the leg's midpoint
  entry    buy stop-limit at the last pause bar's high + 1c, cap + max(1c, 0.3 %),
           live 20 s from that bar's close;  stop = pause low - 1c
  exit     A3 trail 1 R moved every 5 s, flat 11:30; one position per symbol-day
Reported beside it: N5 (no 5-minute confirmation), X2 (fixed +2 R / stop exit),
RND (5 random entries per S trade inside the same runner windows, same stop %).
Costs per trade, decomposed (see `costs`). Assessment only: it decides nothing live.
"""
from __future__ import annotations

import argparse
import json
import pickle
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import tick_replay as TR  # noqa: E402

OUT = ROOT / "research" / "paper-exercise" / "reports"
SAMPLE = OUT / "runup_micro_sample.json"
QUOTES = ROOT / "data" / "cache" / "runup_micro_quotes.json"
HISTORY = ROOT / "data" / "cache" / "history"
SEED, N_DAYS = 20261002, 300
RUNNER_S = 600
LEG_BARS, LEG_MIN_PCT, MIN_GREEN = 6, 1.0, 3
TTL_ENTRY_S = 20
RISK, NOTIONAL = 40.0, 2000.0
K_RANDOM = 5


# ------------------------------------------------------------------ sample
def cmd_sample(args) -> int:
    alerts = pickle.load(open(args.alerts, "rb"))[0]
    by = {}
    for a in alerts:
        if a["scanner"] != "running_up" or a["day"] < "2024-01-01" or not a.get("price_band"):
            continue
        by.setdefault((a["day"], a["sym"]), []).append(int(a["epoch"]))
    keys = sorted(by)
    pick = sorted(random.Random(SEED).sample(keys, min(N_DAYS, len(keys))))
    rows = [{"day": d, "sym": s, "alerts": sorted(by[(d, s)])} for d, s in pick]
    SAMPLE.write_text(json.dumps({"seed": SEED, "population": len(keys), "rows": rows}, indent=0))
    print(f"population {len(keys)} symbol-days · sample {len(rows)} -> {SAMPLE.relative_to(ROOT)}")
    return 0


def _chunks(row):
    day0 = TR.day_open(row["day"])
    k0 = max(18, (min(row["alerts"]) - day0) // TR.CHUNK_S)       # never before 07:00
    k1 = (TR.at_et(row["day"], "11:30") - day0) // TR.CHUNK_S - 1
    return day0, range(int(k0), int(k1) + 1)


def _fetcher():
    from momentum_platform.datasources.alpaca_source import client_from_env
    return TR.Fetcher(client_from_env(feed="sip"))


def cmd_fetch(args) -> int:
    rows = json.loads(SAMPLE.read_text())["rows"]
    fx = _fetcher()
    for n, r in enumerate(rows, 1):
        day0, ks = _chunks(r)
        for k in ks:
            fx.chunk(r["sym"], r["day"], k, day0)
        if n % 10 == 0:
            print(f"{n}/{len(rows)} symbol-days · requests {fx.requests}", flush=True)
    print(f"done · requests {fx.requests}")
    return 0


# ------------------------------------------------------------------ bars
def _prints(r):
    day0, ks = _chunks(r)
    T, P = [], []
    for k in ks:
        f = TR.TICKS / r["day"] / f"{r['sym']}_{k:03d}.npz"
        if not f.exists():
            return None
        z = np.load(f)
        T.append(z["t"]); P.append(np.round(z["p"].astype(np.float64), 4))
    t, p = np.concatenate(T), np.concatenate(P)
    return (t, p) if len(t) else None


def _bars10(t, p):
    key = (t // 10_000) * 10
    out = []
    starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    ends = np.r_[starts[1:], len(t)]
    for a, b in zip(starts, ends):
        seg = p[a:b]
        out.append((int(key[a]), float(seg[0]), float(seg.max()), float(seg.min()), float(seg[-1])))
    return out


def _ema(x, n):
    a, out = 2 / (n + 1), np.empty(len(x))
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


_HIST: dict = {}


def _five_min_ok(day, sym):
    """[(end_epoch, ok)] for completed 5-minute bars of the cached 1-minute history."""
    if day not in _HIST:
        f = HISTORY / f"{day}.json"
        _HIST.clear()
        _HIST[day] = json.loads(f.read_text()) if f.exists() else {}
    rows = _HIST[day].get(sym) or []
    if not rows:
        return []
    b5 = {}
    for iso, o, h, l, c, v in rows:
        e = int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())
        b5[(e // 300) * 300] = c                       # last close in the bucket
    keys = sorted(b5)
    c = np.array([b5[k] for k in keys])
    if len(c) < 2:
        return []
    e9, m = _ema(c, 9), _ema(c, 12) - _ema(c, 26)
    sig = _ema(m, 9)
    return [(k + 300, bool(c[i] > e9[i] and m[i] > sig[i])) for i, k in enumerate(keys)]


def _ok_at(five, ts):
    ok = False
    for end, v in five:
        if end > ts:
            break
        ok = v
    return ok


# ------------------------------------------------------------------ exits
def _trade(t, p, entry, stop, t_order, flat_t, ttl_s, mode="trail"):
    """TR.replay's rules, returning the level in force at the exit too.
    mode 'trail' = A3 1 R trail every 5 s; 'x2' = +2 R limit target or the stop."""
    cap = TR.RA.cap_of(entry, TR.CAP_PCT)
    rps = entry - stop
    if rps <= 0:
        return None
    i = int(np.searchsorted(t, t_order * 1000, side="left"))
    end_entry, n, trig, fi = (t_order + ttl_s) * 1000, len(t), False, None
    while i < n and t[i] < end_entry:
        if not trig and p[i] >= entry:
            trig = True
        if trig and p[i] <= cap:
            fi = i
            break
        i += 1
    if fi is None:
        return None
    fill = float(min(cap, max(entry, p[fi])))
    level, high, nxt = stop, fill, int(t[fi]) + 5000
    target = fill + 2 * rps
    for j in range(fi + 1, n):
        tj, pj = int(t[j]), float(p[j])
        if tj >= flat_t * 1000:
            return dict(t_in=int(t[fi]), t_out=int(t[j - 1]), fill=fill, exit=float(p[j - 1]), level=None,
                        r=(float(p[j - 1]) - fill) / rps, how="flat", rps=rps)
        if mode == "trail":
            while tj >= nxt:
                level = max(level, round(high - rps, 4))
                nxt += 5000
        elif pj >= target:
            return dict(t_in=int(t[fi]), t_out=tj, fill=fill, exit=target, level=None, r=2.0, how="target", rps=rps)
        if pj <= level:
            return dict(t_in=int(t[fi]), t_out=tj, fill=fill, exit=pj, level=level, r=(pj - fill) / rps,
                        how="trail" if level > stop else "stop", rps=rps)
        high = max(high, pj)
    return dict(t_in=int(t[fi]), t_out=int(t[n - 1]), fill=fill, exit=float(p[n - 1]), level=None,
                r=(float(p[n - 1]) - fill) / rps, how="end", rps=rps)


# ------------------------------------------------------------------ detection
def _signals(bars, armed, five, use5):
    """Yield (t_arm, entry, stop) at each qualifying pause close."""
    for i in range(LEG_BARS + 1, len(bars) + 1):
        for npause in (1, 2, 3):
            a = i - npause
            if a - LEG_BARS < 0:
                break
            leg, pause = bars[a - LEG_BARS:a], bars[a:i]
            lh, ll = max(b[2] for b in leg), min(b[3] for b in leg)
            if sum(1 for b in leg if b[4] > b[1]) < MIN_GREEN or (lh - ll) / ll * 100 < LEG_MIN_PCT:
                continue
            if any(b[2] > lh for b in pause):
                continue
            pl = min(b[3] for b in pause)
            if pl < (lh + ll) / 2:
                continue
            t_arm = bars[i - 1][0] + 10
            if not armed(t_arm) or (use5 and not _ok_at(five, t_arm)):
                break
            yield t_arm, round(bars[i - 1][2] + 0.01, 4), round(pl - 0.01, 4)
            break


def _run_variant(r, t, p, bars, five, use5, mode):
    flat = TR.at_et(r["day"], "11:30")
    wins = [(e + 60, e + 60 + RUNNER_S) for e in r["alerts"]]
    armed = lambda ts: any(a <= ts < b for a, b in wins)          # noqa: E731
    out, busy = [], 0
    for t_arm, entry, stop in _signals(bars, armed, five, use5):
        if t_arm * 1000 < busy:
            continue
        x = _trade(t, p, entry, stop, t_arm, flat, TTL_ENTRY_S, mode)
        if x:
            busy = x["t_out"]
            out.append(dict(sym=r["sym"], day=r["day"], t_arm=t_arm, entry=entry, stop=stop, **x))
    return out


def _random(r, t, p, bars, trade, k):
    flat = TR.at_et(r["day"], "11:30")
    closes = [b[0] + 10 for b in bars if any(e + 60 <= b[0] + 10 < e + 660 for e in r["alerts"])]
    rng = random.Random(f"{r['day']}{r['sym']}{trade['t_arm']}")
    pct = (trade["entry"] - trade["stop"]) / trade["entry"]
    res = []
    for ts in rng.sample(closes, min(k, len(closes))):
        i = int(np.searchsorted(t, ts * 1000))
        if i >= len(t):
            continue
        e = float(p[i])
        x = _trade(t, p, e, round(e * (1 - pct), 4), ts, flat, TTL_ENTRY_S)
        if x:
            res.append(x["r"])
    return res


# ------------------------------------------------------------------ costs
def costs(tr, s_in, s_out):
    """One trade as IBKR would bill it. Dollars and R, by component."""
    rps, fill = tr["rps"], tr["fill"]
    sh = max(1, min(int(RISK // rps), int(NOTIONAL // fill)))
    r_usd = sh * rps
    side = lambda px: min(max(1.0, 0.005 * sh), 0.01 * sh * px)    # noqa: E731
    stopish = tr["how"] in ("trail", "stop")
    c = {
        "commission": side(fill) + side(tr["exit"]),
        "half_spread_in": sh * s_in / 2,
        "half_spread_out": sh * s_out / 2 if stopish else 0.0,
        "model_1c": sh * 0.01 * (2 if stopish else 1),
        "entry_slip": sh * (fill - tr["entry"]),                   # already inside gross R
        "exit_slip": sh * (tr["level"] - tr["exit"]) if tr.get("level") is not None else 0.0,
    }
    return sh, r_usd, {k: v / r_usd for k, v in c.items()}, c


def _quote(fx, cache, sym, ms):
    key = f"{sym}|{ms}"
    if key not in cache:
        cache[key] = fx.spread_at(sym, ms)
    return cache[key]


def _stats(rs):
    rs = np.asarray(rs, dtype=float)
    if not len(rs):
        return "n 0"
    w, l_ = rs[rs > 0], rs[rs <= 0]
    return (f"n {len(rs):>5} · mean {rs.mean():+.3f} · median {np.median(rs):+.3f} · win {100 * len(w) / len(rs):4.1f}% · "
            f"avg win {w.mean() if len(w) else 0:+.2f} · avg loss {l_.mean() if len(l_) else 0:+.2f} · total {rs.sum():+.1f}")


def cmd_run(args) -> int:
    meta = json.loads(SAMPLE.read_text())
    rows = meta["rows"]
    fx = _fetcher()
    qc = json.loads(QUOTES.read_text()) if QUOTES.exists() else {}
    S, N5, X2, RND, missing = [], [], [], [], 0
    for r in rows:
        tp = _prints(r)
        if tp is None:
            missing += 1
            continue
        t, p = tp
        bars = _bars10(t, p)
        five = _five_min_ok(r["day"], r["sym"])
        s = _run_variant(r, t, p, bars, five, True, "trail")
        S += s
        N5 += _run_variant(r, t, p, bars, five, False, "trail")
        X2 += _run_variant(r, t, p, bars, five, True, "x2")
        for tr in s:
            RND += _random(r, t, p, bars, tr, K_RANDOM)
    for tr in S:
        tr["s_in"] = _quote(fx, qc, tr["sym"], tr["t_in"])
        tr["s_out"] = _quote(fx, qc, tr["sym"], tr["t_out"]) if tr["how"] in ("trail", "stop") else 0.0
    QUOTES.write_text(json.dumps(qc))

    L = []
    pr = lambda s="": (print(s), L.append(s))                       # noqa: E731
    pr(f"runner + 10-s micro pullback + 5-min confirmation · addendum 2026-10-02e · sample {len(rows)} of "
       f"{meta['population']} symbol-days 2024-01-02..2026-08-21 (seed {meta['seed']}) · prints missing {missing}")
    pr()
    pr("GROSS R per trade (no costs; fills and exits on SIP prints, slippage against the prints included)")
    pr(f"  S    runner + 5-min + 10-s, trail  {_stats([x['r'] for x in S])}")
    pr(f"  N5   without the 5-min confirmation  {_stats([x['r'] for x in N5])}")
    pr(f"  X2   S with +2 R target / stop       {_stats([x['r'] for x in X2])}")
    pr(f"  RND  random entries, same windows    {_stats(RND)}")
    for y in ("2024", "2025", "2026"):
        pr(f"  S {y}  {_stats([x['r'] for x in S if x['day'].startswith(y)])}")
    for lo, hi, lab in ((0, 0.5, "pre-market"), (0.5, 9, "regular")):
        sub = [x for x in S if (lab == "pre-market") == (datetime.fromtimestamp(x["t_in"] / 1000, TR.RA.E.ET).strftime("%H:%M") < "09:30")]
        pr(f"  S {lab:<11} {_stats([x['r'] for x in sub])}")
    pr(f"  S exits: { {h: sum(1 for x in S if x['how'] == h) for h in ('stop', 'trail', 'flat', 'end')} }")

    q = [x for x in S if x["s_in"] is not None and x["s_out"] is not None]
    comp = {k: [] for k in ("commission", "half_spread_in", "half_spread_out", "model_1c", "entry_slip", "exit_slip")}
    rows_c = []
    for x in q:
        sh, r_usd, cr, cd = costs(x, x["s_in"], x["s_out"])
        x.update(sh=sh, r_usd=r_usd, cost_r=cr, cost_usd=cd)
        for k in comp:
            comp[k].append(cr[k])
        rows_c.append(x)
    pr()
    pr(f"COSTS on the {len(q)} S trades with a quote at fill and exit — R per trade (mean | median), and $ mean")
    for k in comp:
        v = np.array(comp[k])
        usd = np.mean([x["cost_usd"][k] for x in rows_c])
        tag = "  (inside gross)" if k in ("entry_slip", "exit_slip") else ""
        pr(f"  {k:<16} {v.mean():.3f} | {np.median(v):.3f}   ${usd:6.2f}{tag}")
    billed = np.array([x["cost_r"]["commission"] + x["cost_r"]["half_spread_in"] + x["cost_r"]["half_spread_out"] for x in q])
    model = billed + np.array([x["cost_r"]["model_1c"] for x in q])
    g = np.array([x["r"] for x in q])
    pr(f"  commission + half spreads: mean {billed.mean():.3f} R · with the 1c model charge {model.mean():.3f} R")
    pr(f"  NET R per trade: {(g - billed).mean():+.3f} (spreads + commission) · {(g - model).mean():+.3f} (with the 1c charge)")
    sh = np.array([x["sh"] for x in q]); ru = np.array([x["r_usd"] for x in q])
    pr(f"  shares median {np.median(sh):.0f} · 1 R in $ median {np.median(ru):.2f} (notional cap binds on {100 * np.mean(ru < RISK - 0.5):.0f}% of trades)")
    pr(f"  stop % of price median {100 * np.median([x['rps'] / x['fill'] for x in q]):.2f} · spread in median ${np.median([x['s_in'] for x in q]):.3f}")
    pr()
    pr("POST HOC cuts (labelled: chosen after seeing the data; they decide nothing)")
    def cut(name, f):
        sub = [x for x in q if f(x)]
        if sub:
            gg = np.array([x["r"] for x in sub])
            bb = np.array([x["cost_r"]["commission"] + x["cost_r"]["half_spread_in"] + x["cost_r"]["half_spread_out"] for x in sub])
            pr(f"  {name:<28} n {len(sub):>4} · gross {gg.mean():+.3f} · cost {bb.mean():.3f} · net {(gg - bb).mean():+.3f}")
    for lo, hi in ((0, 0.10), (0.10, 0.25), (0.25, 0.5), (0.5, 99)):
        cut(f"spread/stop {lo}-{hi}", lambda x, lo=lo, hi=hi: lo <= x["s_in"] / x["rps"] < hi)
    for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 99)):
        cut(f"stop % {lo}-{hi}", lambda x, lo=lo, hi=hi: lo <= 100 * x["rps"] / x["fill"] < hi)
    for lo, hi in ((2, 5), (5, 10), (10, 20.5)):
        cut(f"price ${lo}-{hi}", lambda x, lo=lo, hi=hi: lo <= x["fill"] < hi)
    if rows_c:
        med = sorted(rows_c, key=lambda x: sum(x["cost_r"][k] for k in ("commission", "half_spread_in", "half_spread_out")))[len(rows_c) // 2]
        pr()
        pr("THE MEDIAN-COST TRADE, as IBKR would bill it")
        pr(f"  {med['day']} {med['sym']} · buy stop {med['entry']:.2f}, stop {med['stop']:.2f} ({100 * med['rps'] / med['fill']:.2f} %) · "
           f"{med['sh']} shares · 1 R = ${med['r_usd']:.2f} · fill {med['fill']:.4f} · exit {med['exit']:.4f} ({med['how']})")
        pr(f"  spread at fill ${med['s_in']:.3f} · at exit ${med['s_out']:.3f}")
        for k, v in med["cost_usd"].items():
            pr(f"    {k:<16} ${v:7.2f}  = {med['cost_r'][k]:.3f} R")
    (OUT / "runup_micro_output.txt").write_text("\n".join(L) + "\n")
    (OUT / "runup_micro_results.json").write_text(json.dumps(
        {"S": S, "N5": [x["r"] for x in N5], "X2": [x["r"] for x in X2], "RND": RND}, default=float))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample"); s.add_argument("--alerts", required=True)
    sub.add_parser("fetch"); sub.add_parser("run")
    a = ap.parse_args(argv)
    return {"sample": cmd_sample, "fetch": cmd_fetch, "run": cmd_run}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
