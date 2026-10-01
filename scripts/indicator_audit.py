#!/usr/bin/env python3
"""Indicator and data accuracy audit for the four Layer 2 checks.

The desk decides a pullback on: price > VWAP, price > 9 EMA, MACD 12/26/9
"positive and above signal" (`momentum_platform.indicators.chart_gates`),
and pullback volume < impulse volume (`FirstPullbackDetector.volume_ok`).
This script recomputes the three chart gates INDEPENDENTLY (numpy/pandas, not
the desk's own functions) at every plan the detector arms, and measures what
each convention choice changes. READ-ONLY: it never writes a ledger and
changes no decision logic.

Modes

  (default)        the Alpaca SIP 1-minute cache, data/cache/history/<day>.json,
                   a seeded random sample of sessions drawn exactly as
                   `backtest_history.py --sample N --seed S` draws it. For every
                   plan armed 07:00-11:20 ET (the `backtest_recent.plans_for_day`
                   loop, bars from 04:00 ET) it reports:
                     (a) agreement of chart_gates with an independent recompute;
                         EMA9 and MACD seeded two ways (first value = the desk;
                         SMA of the first n = the TradingView convention) and the
                         plan decisions that flip; MACD warm-up (None below 35
                         bars since 04:00); bars available at arm time; MACD
                         "hist>0 and line>signal" against "line>0 and line>signal";
                     (b) how often the impulse ("push") volume rises (second-half
                         mean >= first-half mean) and exceeds the 10 bars before it;
                     (e) entry timing: how often the trigger bar itself traded
                         through the entry (the live runner can fill there; the
                         backtest needs a re-touch in the next 3 bars), and the
                         chart gates at the break instant (a labelled proxy for the
                         desk's forming-minute evaluation) against the bar close.
  --ledger PATH    (c) every `decisions` row against a recompute from the
                   ledger's own `bars` table (04:00 ET up to the decision minute):
                   gates_json vwap/ema9/macd and volume_ok. When `bars_10s` holds
                   the decision minute, also a point-in-time recompute with the
                   minute rebuilt from the 10-second candles closed by the row's
                   `recorded_at` (what the desk could have seen when it wrote it).
  --ledger PATH --alpaca-compare
                   (d) ledger volume / Alpaca SIP volume per symbol-minute,
                   pre-market and regular separately, split by whether the desk
                   built the minute from 10-second candles or from IBKR minute
                   history. Needs ALPACA_KEY_ID / ALPACA_SECRET_KEY (env or .env).

    python3 scripts/indicator_audit.py                       # ~300 sessions, a few minutes
    python3 scripts/indicator_audit.py --sample 40
    python3 scripts/indicator_audit.py --ledger data/journal.sqlite
    python3 scripts/indicator_audit.py --ledger data/journal.sqlite --alpaca-compare
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path
from statistics import mean, median

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

import backtest_history as H  # noqa: E402  universe, cache parsing, Alpaca fetch
import backtest_recent as E  # noqa: E402  the plans_for_day engine
from momentum_platform import indicators as I  # noqa: E402
from momentum_platform.models import Bar  # noqa: E402
from momentum_platform.pullback import FirstPullbackDetector  # noqa: E402

ET = E.ET
UTC = timezone.utc
PM_START, RTH_START, CUTOFF = dtime(7, 0), dtime(9, 30), dtime(11, 20)
DAY_START, DAY_END = dtime(4, 0), dtime(16, 0)
GATES = ("vwap", "ema9", "macd")
DESK_KEY = {"vwap": "above_vwap", "ema9": "above_ema9", "macd": "macd_positive_and_above_signal"}
TIE = 1e-9            # |price - indicator| below this (relative) is a float tie, not a disagreement


# ------------------------------------------------------------ independent maths
def ema_first(x, n: int) -> np.ndarray:
    """EMA seeded with the first value (the desk's convention): pandas
    ewm(adjust=False) is y0 = x0, yt = a*xt + (1-a)*y(t-1), a = 2/(n+1)."""
    x = np.asarray(x, dtype=float)
    if not len(x):
        return x
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def ema_sma(x, n: int) -> np.ndarray:
    """EMA seeded with the SMA of the first n values (TradingView ta.ema);
    NaN before index n-1."""
    x = np.asarray(x, dtype=float)
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = pd.Series(np.r_[x[:n].mean(), x[n:]]).ewm(span=n, adjust=False).mean().to_numpy()
    return out


def frame(rows) -> dict:
    """Every indicator, causal, for every bar of one symbol-day. Index i is
    what a computation over rows[:i+1] gives. rows: (ts, o, h, l, c, v)."""
    a = np.asarray([[r[2], r[3], r[4], r[5]] for r in rows], dtype=float).reshape(-1, 4)
    h, l, c, v = a[:, 0], a[:, 1], a[:, 2], a[:, 3]
    cum_v = np.cumsum(v)
    with np.errstate(invalid="ignore", divide="ignore"):
        vwap = np.where(cum_v > 0, np.cumsum((h + l + c) / 3.0 * v) / np.where(cum_v > 0, cum_v, 1), np.nan)
    out = {"close": c, "high": h, "vol": v, "vwap": vwap, "n": len(c)}
    for seed, fn in (("first", ema_first), ("sma", ema_sma)):
        out[f"ema9_{seed}"] = fn(c, 9)
        fast, slow = fn(c, 12), fn(c, 26)
        line = fast - slow
        sig = np.full(len(c), np.nan)
        if len(c) >= 26:
            sig[25:] = fn(line[25:], 9)       # the signal starts where the slow EMA does
        out[f"fast_{seed}"], out[f"slow_{seed}"] = fast, slow
        out[f"line_{seed}"], out[f"sig_{seed}"] = line, sig
    return out


#: first index with a value: the desk needs 35 closes for MACD (26 + 9) and
#: 9 for EMA9; the SMA seed has its signal at index 25 + 8 = 33.
MACD_FROM = {"first": 34, "sma": 33}


def _gt(x: float, ref: float):
    if ref is None or np.isnan(ref):
        return None
    return bool(x > ref)


def gates_at(f: dict, i: int, seed: str = "first", semantics: str = "hist") -> dict:
    """The three booleans at bar i, None below warm-up. semantics 'hist' is
    the desk's `hist > 0 and line > signal`; 'line' is `line > 0 and line > signal`."""
    c = f["close"][i]
    out = {"vwap": _gt(c, f["vwap"][i]),
           "ema9": _gt(c, f[f"ema9_{seed}"][i]) if i + 1 >= I.EMA9_MIN else None,
           "macd": None}
    if i >= MACD_FROM[seed]:
        line, sig = f[f"line_{seed}"][i], f[f"sig_{seed}"][i]
        hist = line - sig
        out["macd"] = bool(hist > 0 and line > sig) if semantics == "hist" else bool(line > 0 and line > sig)
    return out


def margin(f: dict, i: int, gate: str, seed: str = "first") -> float:
    """|price - indicator| / price at bar i: how close to the line a gate sat."""
    c = f["close"][i]
    if gate == "vwap":
        ref = f["vwap"][i]
    elif gate == "ema9":
        ref = f[f"ema9_{seed}"][i]
    else:
        return abs(f[f"line_{seed}"][i] - f[f"sig_{seed}"][i]) / max(abs(c), 1e-12)
    return abs(c - ref) / max(abs(c), 1e-12)


def break_proxy(f: dict, i: int, price: float) -> dict:
    """The chart gates at the INSTANT of the break, approximated: the last
    price is the plan's entry (prior high + 1c), VWAP is through the previous
    bar (the trigger bar's own volume is not known yet), the EMAs and MACD
    take one step from bar i-1 with the break price. A proxy for what the live
    desk evaluates on its forming minute; the real value sits between this
    and the bar close depending on when in the minute the break came."""
    out = {"vwap": None, "ema9": None, "macd": None}
    if i < 1:
        return out
    out["vwap"] = _gt(price, f["vwap"][i - 1])
    k9, k12, k26 = 2 / 10, 2 / 13, 2 / 27
    if i + 1 >= I.EMA9_MIN:
        e = price * k9 + f["ema9_first"][i - 1] * (1 - k9)
        out["ema9"] = bool(price > e)
    if i >= MACD_FROM["first"]:
        fast = price * k12 + f["fast_first"][i - 1] * (1 - k12)
        slow = price * k26 + f["slow_first"][i - 1] * (1 - k26)
        line = fast - slow
        sig = line * k9 + f["sig_first"][i - 1] * (1 - k9)
        out["macd"] = bool(line - sig > 0 and line > sig)
    return out


# ------------------------------------------------------------ mode (a)+(b)+(e)
def push_volume(impulse, rows, index_of) -> dict:
    """(b): is the push's volume rising, and is it above the 10 bars before it?
    Halves: first n//2 bars against the last n//2 (the middle bar of an odd
    impulse sits in neither)."""
    vols = [b.volume for b in impulse]
    n = len(vols)
    first, second = vols[: n // 2], vols[(n + 1) // 2:]
    rising = (mean(second) >= mean(first)) if first and second else None
    j = index_of.get(impulse[0].ts) if impulse else None
    pre = [r[5] for r in rows[max(0, j - 10):j]] if j is not None else []
    elevated = (mean(vols) > mean(pre)) if pre else None
    return {"imp_n": n, "rising": rising, "elevated": elevated, "pre_n": len(pre),
            "imp_mean": mean(vols) if vols else None}


def audit_symbol_day(sym: str, rows: list, prev_close: float) -> list[dict]:
    """Every plan the detector arms 07:00-11:20 on one symbol-day, with the
    desk's gates, the independent recompute, and the backtest record for the
    same plan (plans_for_day, desk_vwap=True, gap_miss=True)."""
    recs = E.plans_for_day(sym, rows, prev_close, desk_vwap=True, gap_miss=True)
    f = frame(rows)
    det = FirstPullbackDetector()
    hist, out = [], []
    index_of = {}
    for i, (ts, o, h, l, c, v) in enumerate(rows):
        hist.append([int(ts.timestamp()), o, h, l, c, v])
        bar_ts = ts.astimezone(UTC)
        index_of[bar_ts] = i
        plan = det.on_bar(Bar(symbol=sym, timeframe="1m", ts=bar_ts, open=o, high=h, low=l, close=c, volume=v))
        if plan is None or not (PM_START <= ts.time() < CUTOFF):
            continue
        desk = I.chart_gates(hist)
        p = {"sym": sym, "day": ts.date().isoformat(), "t": ts.strftime("%H:%M"),
             "window": "pre-market" if ts.time() < RTH_START else "regular", "n_bars": i + 1,
             "desk": {g: desk[DESK_KEY[g]] for g in GATES},
             "first": gates_at(f, i, "first"), "sma": gates_at(f, i, "sma"),
             "line_first": gates_at(f, i, "first", "line")["macd"],
             "margin": {g: margin(f, i, g) for g in GATES},
             "diff": {"vwap": None if desk["vwap"] is None else abs(desk["vwap"] - round(f["vwap"][i], 4)),
                      "ema9": None if desk["ema9"] is None else abs(desk["ema9"] - round(f["ema9_first"][i], 4)),
                      "macd": None if desk["macd_hist"] is None
                      else abs(desk["macd_hist"] - round(f["line_first"][i] - f["sig_first"][i], 6))},
             "macd_line": None if i < MACD_FROM["first"] else float(f["line_first"][i]),
             "volume_ok": plan.volume_ok,
             "trig_reach": h >= plan.entry,
             "trig_close_over_cap": c > E.entry_cap(plan.entry),
             "proxy": break_proxy(f, i, plan.entry)}
        p.update(push_volume(det._w.impulse_bars, rows, index_of))
        out.append(p)
    if len(out) != len(recs) or any(p["t"] != r["t"] for p, r in zip(out, recs)):
        raise RuntimeError(f"{sym}: plan list does not line up with plans_for_day "
                           f"({len(out)} vs {len(recs)})")
    for p, r in zip(out, recs):
        p["rec"] = r
    return out


def _allowed(p: dict, red) -> bool:
    return H.current_rules({"red": list(red), "window": p["window"]})


def _swap(p: dict, values: dict) -> set:
    """The plan's red set with these chart gates replaced (None is red)."""
    red = set(p["rec"]["red"])
    for g, ok in values.items():
        red.discard(g)
        if ok is not True:
            red.add(g)
    return red


def _q(xs, qs=(10, 25, 50, 75, 90)) -> str:
    if not xs:
        return "n 0"
    a = np.percentile(np.asarray(xs, float), qs)
    return f"n {len(xs)} · " + " · ".join(f"p{q} {v:.0f}" for q, v in zip(qs, a))


def _pct(k: int, n: int) -> str:
    return f"{k}/{n} ({100.0 * k / n:.1f}%)" if n else f"{k}/0"


def _outcome(ps: list[dict]) -> str:
    t = [p["rec"] for p in ps if p["rec"]["touched"]]
    if not t:
        return f"n {len(ps)}, filled 0"
    vals = [r["trail_net"] for r in t]
    return f"n {len(ps)}, filled {len(t)}, trail net mean {mean(vals):+.3f} R, sum {sum(vals):+.1f} R"


def flips(ps: list[dict], alt) -> tuple[list, list]:
    """(allowed now and refused by alt, refused now and allowed by alt)."""
    a, b = [], []
    for p in ps:
        now, then = _allowed(p, p["rec"]["red"]), _allowed(p, alt(p))
        if now and not then:
            a.append(p)
        elif then and not now:
            b.append(p)
    return a, b


def report(plans: list[dict], meta: dict) -> list[str]:
    L = []
    w = L.append
    w(f"INDICATOR AUDIT · Alpaca SIP 1-minute cache · {meta['sessions']} sessions sampled (seed {meta['seed']}), "
      f"{meta['missing']} not cached · {meta['symdays']} symbol-days with >= 40 bars · {len(plans)} plans armed "
      f"07:00-11:20 ET ({sum(p['window'] == 'pre-market' for p in plans)} pre-market, "
      f"{sum(p['window'] == 'regular' for p in plans)} regular)")
    w("Outcomes are backtest_recent's (A10 re-touch within 3 bars, gap_miss fills, cost model "
      f"'{E.COST_MODEL}', trail exit). 'allowed' = backtest_history.current_rules on the plan's red set.")
    for win in ("pre-market", "regular"):
        w(f"  baseline {win:<10} allowed by current rules: "
          f"{_outcome([p for p in plans if p['window'] == win and _allowed(p, p['rec']['red'])])}")
    w("")

    # (a1) implementation agreement
    w("(a1) momentum_platform.indicators.chart_gates vs independent numpy/pandas recompute (first-value seed)")
    for g in GATES:
        agree = sum(p["desk"][g] == p["first"][g] for p in plans)
        dis = [p for p in plans if p["desk"][g] != p["first"][g]]
        ties = sum(1 for p in dis if p["margin"][g] <= TIE)
        diffs = [p["diff"][g] for p in plans if p["diff"][g] is not None]
        w(f"  {g:<5} agree {_pct(agree, len(plans))} · disagree {len(dis)} (float ties {ties}) · "
          f"max |desk value - recompute| {max(diffs) if diffs else float('nan'):.2e} (desk rounds to 4/6 dp)")
    w("")

    # (a2) warm-up and bars available
    w("(a2) warm-up · bars since 04:00 ET at arm time (Alpaca omits minutes with no trade)")
    for win in ("pre-market", "regular"):
        ps = [p for p in plans if p["window"] == win]
        nb = [p["n_bars"] for p in ps]
        w(f"  {win:<10} bars {_q(nb)}")
        w(f"  {'':<10} MACD None (< 35 bars) {_pct(sum(p['desk']['macd'] is None for p in ps), len(ps))} · "
          f"EMA9 None (< 9) {_pct(sum(p['desk']['ema9'] is None for p in ps), len(ps))} · "
          f"VWAP None {_pct(sum(p['desk']['vwap'] is None for p in ps), len(ps))}")
        none_alone = [p for p in ps if p["desk"]["macd"] is None]
        w(f"  {'':<10} plans refused only because MACD is None: "
          f"{sum(1 for p in none_alone if set(p['rec']['red']) == {'macd'})}")
    w("")

    # (a3) seeding
    w("(a3) EMA9 / MACD seeding: first value (desk) vs SMA of the first n (TradingView)")
    for win in ("pre-market", "regular", "all"):
        ps = plans if win == "all" else [p for p in plans if p["window"] == win]
        e_both = [p for p in ps if p["first"]["ema9"] is not None]
        e_flip = sum(p["first"]["ema9"] != p["sma"]["ema9"] for p in e_both)
        m_both = [p for p in ps if p["first"]["macd"] is not None and p["sma"]["macd"] is not None]
        m_flip = sum(p["first"]["macd"] != p["sma"]["macd"] for p in m_both)
        m_edge = sum(p["first"]["macd"] is None and p["sma"]["macd"] is not None for p in ps)
        chart_f = sum(all(p["first"][g] is True for g in GATES) != all(p["sma"][g] is True for g in GATES) for p in ps)
        a, b = flips(ps, lambda p: _swap(p, {"ema9": p["sma"]["ema9"], "macd": p["sma"]["macd"]}))
        w(f"  {win:<10} EMA9 flips {_pct(e_flip, len(e_both))} · MACD flips {_pct(m_flip, len(m_both))} "
          f"(+{m_edge} at exactly 34 bars: None vs a value) · chart-green flips {_pct(chart_f, len(ps))}")
        w(f"  {'':<10} current-rules decision: allowed->refused {len(a)}, refused->allowed {len(b)}")
    buckets = ((9, 19), (20, 49), (50, 99), (100, 10 ** 6))
    for lo, hi in buckets:
        ps = [p for p in plans if lo <= p["n_bars"] <= hi]
        ef = sum(p["first"]["ema9"] != p["sma"]["ema9"] for p in ps if p["first"]["ema9"] is not None)
        mf = sum(p["first"]["macd"] != p["sma"]["macd"] for p in ps
                 if p["first"]["macd"] is not None and p["sma"]["macd"] is not None)
        w(f"    bars {lo:>3}-{hi if hi < 10 ** 6 else 'max':<4} plans {len(ps):>5} · EMA9 flips {ef:>4} · MACD flips {mf:>4}")
    a, b = flips(plans, lambda p: _swap(p, {"ema9": p["sma"]["ema9"], "macd": p["sma"]["macd"]}))
    w(f"  outcome of plans the SMA seed would refuse: {_outcome(a)}")
    w(f"  outcome of plans the SMA seed would allow:  {_outcome(b)}")
    w("")

    # (a4) MACD semantics
    w("(a4) MACD semantics: desk 'hist>0 and line>signal' (hist = line - signal, so this is line>signal alone) "
      "vs 'line>0 and line>signal'")
    for win in ("pre-market", "regular", "all"):
        ps = plans if win == "all" else [p for p in plans if p["window"] == win]
        ok = [p for p in ps if p["first"]["macd"] is not None]
        a_true = sum(p["first"]["macd"] for p in ok)
        b_true = sum(bool(p["line_first"]) for p in ok)
        below0 = sum(1 for p in ok if p["first"]["macd"] and not p["line_first"])
        fa, fb = flips(ps, lambda p: _swap(p, {"macd": p["line_first"]}))
        w(f"  {win:<10} MACD evaluable {len(ok)} · pass (desk) {_pct(a_true, len(ok))} · pass (line>0 too) "
          f"{_pct(b_true, len(ok))} · above signal but line < 0: {below0}")
        w(f"  {'':<10} current-rules decision allowed->refused {len(fa)} · {_outcome(fa)}")
    w("")

    # (b) push volume
    w("(b) the impulse ('push') volume. _impulse_valid checks bar count and the 2% range only; no volume test.")
    for win in ("pre-market", "regular", "all"):
        ps = plans if win == "all" else [p for p in plans if p["window"] == win]
        r_ok = [p for p in ps if p["rising"] is not None]
        e_ok = [p for p in ps if p["elevated"] is not None]
        w(f"  {win:<10} impulse bars {_q([p['imp_n'] for p in ps], (50,))} · rising (2nd half >= 1st) "
          f"{_pct(sum(p['rising'] for p in r_ok), len(r_ok))} · above the 10 bars before "
          f"{_pct(sum(p['elevated'] for p in e_ok), len(e_ok))} (fewer than 10 before: "
          f"{sum(1 for p in ps if p['pre_n'] < 10)}, none before: {sum(1 for p in ps if p['pre_n'] == 0)})")
        both = [p for p in ps if p["rising"] is True and p["elevated"] is True]
        w(f"  {'':<10} rising AND elevated {_pct(len(both), len(ps))} · current volume_ok true "
          f"{_pct(sum(bool(p['volume_ok']) for p in ps), len(ps))}")
        for name, key in (("push rising", "rising"), ("push elevated", "elevated")):
            fa, _ = flips(ps, lambda p, k=key: set(p["rec"]["red"]) | ({k} if p[k] is not True else set()))
            w(f"  {'':<10} a '{name}' rule would refuse {len(fa)} plans the current rules allow · {_outcome(fa)}")
    w("")

    # (e) entry timing and the forming minute
    w("(e) entry timing · the trigger bar is the bar that armed the plan; entry = prior bar high + 1c")
    for win in ("pre-market", "regular", "all"):
        ps = plans if win == "all" else [p for p in plans if p["window"] == win]
        reach = [p for p in ps if p["trig_reach"]]
        retouch = [p for p in ps if p["rec"]["touched"]]
        w(f"  {win:<10} trigger bar traded through the entry {_pct(len(reach), len(ps))} · backtest re-touch "
          f"in next 3 bars {_pct(len(retouch), len(ps))} · through on the trigger bar but NO re-touch "
          f"{_pct(sum(1 for p in reach if not p['rec']['touched']), len(ps))}")
        w(f"  {'':<10} trigger bar CLOSED above the A10 limit cap (entry + max(1c, 0.3%)) "
          f"{_pct(sum(1 for p in ps if p['trig_close_over_cap']), len(ps))}")
    w("  chart gates at the break instant (proxy, see break_proxy) vs at the trigger-bar close (backtest):")
    for win in ("pre-market", "regular", "all"):
        ps = plans if win == "all" else [p for p in plans if p["window"] == win]
        cells = []
        for g in GATES:
            both = [p for p in ps if p["proxy"][g] is not None and p["first"][g] is not None]
            cells.append(f"{g} differs {_pct(sum(p['proxy'][g] != p['first'][g] for p in both), len(both))}")
        fa, fb = flips(ps, lambda p: _swap(p, p["proxy"]))
        w(f"  {win:<10} " + " · ".join(cells))
        w(f"  {'':<10} allowed at close, refused at break: {_outcome(fa)}")
        w(f"  {'':<10} refused at close, allowed at break: {_outcome(fb)}")
    return L


def run_cache(args) -> int:
    uni = H.load_universe(args.since, args.until)
    days = sorted(uni)
    if args.sample and args.sample < len(days):
        days = sorted(random.Random(args.seed).sample(days, args.sample))
    cache = Path(args.cache)
    plans, missing, symdays = [], 0, 0
    t0 = time.monotonic()
    for k, d in enumerate(days, 1):
        f = cache / f"{d}.json"
        if not f.exists():
            missing += 1
            continue
        bars = json.loads(f.read_text())
        for sym in sorted(uni[d]):
            raw = bars.get(sym) or []
            rows = [r for r in H.to_rows(raw) if DAY_START <= r[0].time() < DAY_END]
            if len(rows) < 40:
                continue
            symdays += 1
            plans += audit_symbol_day(sym, rows, uni[d].get(sym) or rows[0][1])
        if args.progress and k % 50 == 0:
            print(f"  {k}/{len(days)} sessions · {len(plans)} plans · {time.monotonic() - t0:.0f}s",
                  file=sys.stderr, flush=True)
    meta = {"sessions": len(days), "seed": args.seed, "missing": missing, "symdays": symdays}
    print("\n".join(report(plans, meta)))
    print(f"\n[{time.monotonic() - t0:.0f}s]")
    if args.json:
        Path(args.json).write_text(json.dumps(
            [{k: v for k, v in p.items() if k != "rec"} | {"red": p["rec"]["red"], "touched": p["rec"]["touched"]}
             for p in plans], default=str))
    return 0


# ------------------------------------------------------------ mode (c): ledger
def _dt(s) -> datetime:
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def _has_table(conn, name: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def ledger_day_bars(conn, symbol: str, day: str) -> list:
    """The desk's own minutes for one ET day, 04:00-20:00, as (ts_et, o, h, l, c, v)."""
    out = []
    for r in conn.execute("SELECT ts, open, high, low, close, volume FROM bars WHERE symbol=? ORDER BY ts",
                          (symbol,)):
        ts = _dt(r[0]).astimezone(ET)
        if ts.date().isoformat() != day or not (DAY_START <= ts.time() < dtime(20, 0)):
            continue
        out.append((ts, float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5] or 0)))
    out.sort(key=lambda x: x[0])
    return out


def forming_minute(tens: list, minute_start: datetime, as_of: datetime):
    """The minute as the desk could have built it at `as_of`: the 10-second
    candles of that minute whose end (start + 10 s) is not after `as_of`.
    tens: [(ts_utc, o, h, l, c, v)]. None when no candle had closed."""
    end = minute_start + timedelta(minutes=1)
    got = sorted(t for t in tens if minute_start <= t[0] < end and t[0] + timedelta(seconds=10) <= as_of)
    if not got:
        return None
    return (minute_start.astimezone(ET), got[0][1], max(t[2] for t in got), min(t[3] for t in got),
            got[-1][4], float(sum(t[5] for t in got)))


def recorded_states(gates_json) -> dict:
    """gates_json -> {gate: True / False / None (UNKNOWN) / 'NA' (not evaluated)}."""
    try:
        gates = json.loads(gates_json or "[]")
    except (TypeError, ValueError):
        gates = []
    out = {g: "NA" for g in GATES}
    for g in gates:
        gid = g.get("id") if isinstance(g, dict) else None
        if gid in GATES:
            s = str(g.get("state") or "").upper()
            out[gid] = {"PASS": True, "FAIL": False, "UNKNOWN": None}.get(s, "NA")
    return out


def audit_ledger(conn, since: str | None = None) -> dict:
    conn.row_factory = sqlite3.Row
    tens_ok = _has_table(conn, "bars_10s")
    decs = conn.execute("""SELECT decision_id, symbol, ts_et, session, data_status, gates_json, volume_ok,
                                  trigger, stop, recorded_at FROM decisions
                           WHERE source='pullback' ORDER BY ts_et""").fetchall()
    if since:
        decs = [d for d in decs if d["ts_et"][:10] >= since]
    groups = defaultdict(list)
    for d in decs:
        groups[(d["symbol"], d["ts_et"][:10])].append(d)
    rows_out = []
    for (sym, day), ds in sorted(groups.items()):
        bars = ledger_day_bars(conn, sym, day)
        f = frame(bars) if bars else None
        idx = {b[0]: i for i, b in enumerate(bars)}
        det, vol = FirstPullbackDetector(), {}
        for b in bars:
            plan = det.on_bar(Bar(symbol=sym, timeframe="1m", ts=b[0].astimezone(UTC), open=b[1], high=b[2],
                                  low=b[3], close=b[4], volume=b[5]))
            if plan is not None:
                vol[(b[0], round(plan.entry, 4), round(plan.stop, 4))] = plan.volume_ok
        tens = []
        if tens_ok:
            tens = [(_dt(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5] or 0))
                    for r in conn.execute("SELECT ts, open, high, low, close, volume FROM bars_10s "
                                          "WHERE symbol=?", (sym,))]
        for d in ds:
            ts = _dt(d["ts_et"]).astimezone(ET)
            i = idx.get(ts)
            rec = recorded_states(d["gates_json"])
            row = {"symbol": sym, "ts_et": d["ts_et"], "session": d["session"], "status": d["data_status"],
                   "recorded": rec, "final": None, "pit": None, "n_bars": None, "close": None,
                   "volume_ok": d["volume_ok"], "volume_ok_replay": "not reproduced"}
            if i is not None:
                row["final"] = gates_at(f, i, "first")
                row["n_bars"], row["close"] = i + 1, float(f["close"][i])
                row["values"] = {"vwap": float(f["vwap"][i]), "ema9": float(f["ema9_first"][i])}
                fm = forming_minute(tens, ts.astimezone(UTC), _dt(d["recorded_at"])) if tens and d["recorded_at"] else None
                if fm is not None:
                    row["pit"] = gates_at(frame(bars[:i] + [fm]), i, "first")
                    row["pit_close"] = fm[4]
            key = (ts, round(d["trigger"], 4), round(d["stop"], 4)) if d["trigger"] is not None else None
            if key in vol:
                row["volume_ok_replay"] = int(bool(vol[key]))
            rows_out.append(row)
    return {"rows": rows_out, "has_10s": tens_ok}


def print_ledger(res: dict, show: int = 40) -> list[str]:
    rows = res["rows"]
    L = []
    w = L.append
    w(f"LEDGER AUDIT · {len(rows)} pullback decisions · recompute from the ledger's own 1-minute bars, "
      f"04:00 ET to the decision minute, first-value seed (the desk's)")
    w(f"  decision minute missing from bars: {sum(1 for r in rows if r['final'] is None)}")
    dis = []
    for g in GATES:
        ev = [r for r in rows if r["recorded"][g] != "NA" and r["final"] is not None]
        agree = sum(r["recorded"][g] == r["final"][g] for r in ev)
        pit = [r for r in ev if r["pit"] is not None]
        pagree = sum(r["recorded"][g] == r["pit"][g] for r in pit)
        na = sum(1 for r in rows if r["recorded"][g] == "NA")
        w(f"  {g:<6} final-bar agree {_pct(agree, len(ev))} · point-in-time agree {_pct(pagree, len(pit))} · "
          f"not evaluated by the cascade (killed or stale) {na}")
        for r in ev:
            if r["recorded"][g] != r["final"][g] or (r["pit"] is not None and r["recorded"][g] != r["pit"][g]):
                dis.append((r, g))
    vr = [r for r in rows if r["volume_ok_replay"] != "not reproduced"]
    w(f"  volume_ok agree {_pct(sum(int(bool(r['volume_ok'])) == r['volume_ok_replay'] for r in vr), len(vr))} · "
      f"plan not reproduced by the detector on the final bars: {len(rows) - len(vr)}")
    if not res["has_10s"]:
        w("  (no bars_10s table: point-in-time recompute unavailable)")
    w(f"  disagreements ({len(dis)}; first {show}):")
    for r, g in dis[:show]:
        vals = r.get("values", {})
        w(f"    {r['ts_et'][:16]} {r['symbol']:<6} {r['session']:<9} {str(r['status']):<14} {g:<5} recorded "
          f"{r['recorded'][g]!s:<5} final {r['final'][g]!s:<5} pit {('—' if r['pit'] is None else r['pit'][g])!s:<5} "
          f"bars {r['n_bars']} close {r['close']} pit_close {r.get('pit_close', '—')} "
          f"vwap {vals.get('vwap', float('nan')):.4f} ema9 {vals.get('ema9', float('nan')):.4f}")
    for r in [r for r in vr if int(bool(r["volume_ok"])) != r["volume_ok_replay"]][:show]:
        w(f"    {r['ts_et'][:16]} {r['symbol']:<6} volume_ok recorded {r['volume_ok']} replay {r['volume_ok_replay']}")
    return L


# ------------------------------------------------------------ mode (d): Alpaca
def alpaca_compare(conn, client, cache: Path, since: str | None = None) -> dict:
    """ledger volume / Alpaca SIP volume per symbol-minute, by window and by
    how the desk built the minute (10-second candles or IBKR minute history)."""
    conn.row_factory = sqlite3.Row
    tens_min = set()
    if _has_table(conn, "bars_10s"):
        for r in conn.execute("SELECT symbol, ts FROM bars_10s"):
            m = _dt(r[1]).replace(second=0, microsecond=0)
            tens_min.add((r[0], m))
    by_day = defaultdict(lambda: defaultdict(dict))
    for r in conn.execute("SELECT symbol, ts, close, volume FROM bars"):
        ts = _dt(r[1])
        et = ts.astimezone(ET)
        day = et.date().isoformat()
        if since and day < since:
            continue
        if DAY_START <= et.time() < DAY_END:
            by_day[day][r[0]][ts] = (float(r[2]), float(r[3] or 0))
    cells = defaultdict(lambda: {"ratio": [], "lv": 0.0, "av": 0.0, "px": [], "ledger_only": 0,
                                 "alpaca_only": 0, "zero": 0})
    for day in sorted(by_day):
        syms = sorted(by_day[day])
        alp = H.fetch_day(client, day, syms, cache)
        for sym in syms:
            led = by_day[day][sym]
            a = {_dt(t): (float(c), float(v or 0)) for t, o, h, l, c, v in alp.get(sym, [])}
            lo, hi = min(led), max(led)
            for ts in set(led) | {t for t in a if lo <= t <= hi}:
                et = ts.astimezone(ET)
                win = "pre-market" if et.time() < RTH_START else "regular"
                if ts not in led:
                    cells[(win, "—")]["alpaca_only"] += 1
                    continue
                c = cells[(win, "10s" if (sym, ts) in tens_min else "minute-history")]
                lc, lv = led[ts]
                if lv == 0:
                    c["zero"] += 1
                if ts not in a:
                    c["ledger_only"] += 1
                    continue
                ac, av = a[ts]
                c["lv"] += lv; c["av"] += av
                if av > 0:
                    c["ratio"].append(lv / av)
                if ac > 0:
                    c["px"].append(abs(lc - ac) / ac)
    return dict(cells)


def print_compare(cells: dict) -> list[str]:
    L = ["ALPACA COMPARE · ledger volume / Alpaca SIP volume per symbol-minute (1.00 = same shares; "
         "0.01 = lots of 100; << 1 pre-market only = missing extended-hours volume)"]
    for (win, src), c in sorted(cells.items()):
        if src == "—":
            L.append(f"  {win:<10} minutes Alpaca has inside the ledger's span but the ledger does not: {c['alpaca_only']}")
            continue
        r = c["ratio"]
        q = np.percentile(r, (5, 25, 50, 75, 95)) if r else [float("nan")] * 5
        px = np.percentile(c["px"], (50, 95)) if c["px"] else [float("nan")] * 2
        L.append(f"  {win:<10} {src:<14} matched {len(r):>6} · ratio p5 {q[0]:.3f} p25 {q[1]:.3f} median {q[2]:.3f} "
                 f"p75 {q[3]:.3f} p95 {q[4]:.3f} · sum ratio {c['lv'] / c['av'] if c['av'] else float('nan'):.3f} · "
                 f"close |diff| median {px[0]:.4%} p95 {px[1]:.4%} · ledger-only minutes {c['ledger_only']} · "
                 f"zero-volume ledger minutes {c['zero']}")
    return L


# ------------------------------------------------------------ main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", type=int, default=300, help="seeded random sample of sessions (0 = all)")
    ap.add_argument("--seed", type=int, default=20260926, help="backtest_history's default, so the sample matches")
    ap.add_argument("--since"); ap.add_argument("--until")
    ap.add_argument("--cache", default=str(H.CACHE))
    ap.add_argument("--json", help="write every audited plan here (cache mode)")
    ap.add_argument("--progress", action="store_true")
    ap.add_argument("--ledger", help="(c) audit this journal.sqlite's decisions against its own bars")
    ap.add_argument("--alpaca-compare", action="store_true", help="(d) with --ledger: ledger vs Alpaca SIP volume")
    ap.add_argument("--show", type=int, default=40, help="disagreements to list in ledger mode")
    args = ap.parse_args(argv)
    if args.alpaca_compare and not args.ledger:
        ap.error("--alpaca-compare needs --ledger")
    if not args.ledger:
        return run_cache(args)
    if not Path(args.ledger).exists():
        ap.error(f"no ledger at {args.ledger}")
    try:
        conn = sqlite3.connect(f"file:{args.ledger}?mode=ro", uri=True)
        conn.execute("SELECT 1 FROM decisions LIMIT 1")
    except sqlite3.OperationalError:
        # A WAL ledger with no -shm beside it will not open read-only; this
        # script still only SELECTs.
        conn = sqlite3.connect(args.ledger)
    print("\n".join(print_ledger(audit_ledger(conn, args.since), args.show)))
    if args.alpaca_compare:
        try:
            client = H.alpaca_client()
            if not client.key_id:
                raise RuntimeError("ALPACA_KEY_ID is empty")
        except Exception as exc:                                     # noqa: BLE001
            print(f"\nno Alpaca credentials ({exc}); put ALPACA_KEY_ID / ALPACA_SECRET_KEY in .env")
            return 2
        print()
        print("\n".join(print_compare(alpaca_compare(conn, client, Path(args.cache), args.since))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
