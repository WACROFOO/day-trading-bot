#!/usr/bin/env python3
"""What separates a Running Up alert that turns into a real move from noise?

Replays the LIVE scanner classes (not a re-implementation) over the local
ten-year history cache, one symbol-day at a time, 04:00 -> 11:30 ET, with the
engine and notification router built exactly as
`src/momentum_platform/dashboard/session_builder.py` builds them (same scanner
list, same order, same RouterConfig). A "tile alert" is an event the router
DELIVERED whose scanner is in app.js ALERT_TILES.running_up.scanners
(running_up, squeeze_5_in_5, squeeze_10_in_10), between 07:00 and 11:30 ET.

Point-in-time features are read off the engine's own snapshot at the alert bar
plus causal running indicators; outcomes are read from the bars AFTER the
alert bar; first-pullback plans are joined from data/cache/rules_audit_plans.pkl
and judged with rules_audit.passes(p, BASE), net R under mode C / key base
with rules_audit.cost_live.

    python3 runup_study.py --selftest          # indicator + plumbing checks on a few days
    python3 runup_study.py --sample 60         # quick
    python3 runup_study.py                     # everything (alerts cached in alerts.pkl)
    python3 runup_study.py --analyse-only      # re-run the tables from alerts.pkl
"""
from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
import pickle
import random
import sys
import time as _time
from collections import defaultdict
from datetime import datetime, time as dtime, timedelta, timezone
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path("/home/user/day-trading-bot")
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))
OUT = Path(__file__).resolve().parent
CACHE = ROOT / "data" / "cache" / "history"
UNIVERSE_CSV = ROOT / "research" / "first-pullback-edge" / "data" / "candidate_days.csv"
SPLIT = "2024-01-01"
TILE = ("running_up", "squeeze_5_in_5", "squeeze_10_in_10")
A_START, A_END = dtime(7, 0), dtime(11, 30)
FEED_START = dtime(4, 0)


# ---------------------------------------------------------------- universe
def load_meta():
    """{day: {sym: meta}} — the same day/symbol set backtest_history.load_universe
    keeps (reverse-split days dropped), with the csv's other columns."""
    import backtest_history as H
    uni = H.load_universe(None, None)
    meta = defaultdict(dict)
    float_rows = float_have = 0
    with open(UNIVERSE_CSV) as f:
        for r in csv.DictReader(f):
            d, s = r["day"], r["sym"]
            if d not in uni or s not in uni[d]:
                continue
            float_rows += 1
            fm = r.get("float_m") or ""
            if fm.strip():
                float_have += 1
            meta[d][s] = {
                "prev_close": float(r["prev_close"]), "open_px": float(r["open_px"]),
                "gap_pct": float(r["gap_pct"]), "pdv20": float(r["prior_dollar_volume_20d"]),
                "float_m": float(fm) if fm.strip() else None,
                "catalyst": (r.get("catalyst") or "").strip() or None,
            }
    return dict(meta), float_rows, float_have


# ---------------------------------------------------------------- causal indicators
class Causal:
    """Incremental session VWAP (typical price, anchored at the first bar fed),
    EMA9 and MACD(12,26,9) — the same arithmetic as indicators.chart_gates."""

    def __init__(self):
        self.pv = self.v = 0.0
        self.n = 0
        self.e9 = self.e12 = self.e26 = None
        self.sig = None
        self.line_n = 0
        self.dollar = 0.0

    def add(self, h, l, c, v):
        self.pv += (h + l + c) / 3.0 * v
        self.v += v
        self.dollar += c * v
        self.n += 1
        k9, k12, k26, ks = 2 / 10, 2 / 13, 2 / 27, 2 / 10
        self.e9 = c if self.e9 is None else c * k9 + self.e9 * (1 - k9)
        self.e12 = c if self.e12 is None else c * k12 + self.e12 * (1 - k12)
        self.e26 = c if self.e26 is None else c * k26 + self.e26 * (1 - k26)
        line = self.e12 - self.e26
        if self.n >= 26:                      # signal = ema(line[25:], 9)
            self.sig = line if self.sig is None else line * ks + self.sig * (1 - ks)
        self.line = line

    def gates(self, c):
        vw = self.pv / self.v if self.v > 0 else None
        above_vwap = None if vw is None else c > vw
        above_e9 = c > self.e9 if self.n >= 9 else None
        macd_ok = None
        if self.n >= 35:
            hist = self.line - self.sig
            macd_ok = hist > 0 and self.line > self.sig
        return vw, above_vwap, above_e9, macd_ok


# ---------------------------------------------------------------- engine (live classes)
def build_engine(sym, m):
    from momentum_platform.engine import ScannerEngine
    from momentum_platform.notify import NotificationRouter, RouterConfig
    from momentum_platform.scanners import (FivePillarsAlert, HodMomentumScanner, RunningMoveScanner,
                                            UptrendScanner, squeeze_5_in_5, squeeze_10_in_10,
                                            Breakout52wScanner)
    from momentum_platform.scanners.momentum_events import MIN_VOLUME_5M
    from momentum_platform.state import HotState, ReferenceData
    from momentum_platform.models import FloatQuality

    class Collector:
        name = "session_collector"

        def __init__(self):
            self.sink = []

        def deliver(self, event, consolidated=None):
            self.sink.append(event)

    hot = HotState()
    pc = m["prev_close"]
    # avg daily SHARES: the universe carries the 20-day mean DOLLAR volume
    # (research/first-pullback-edge/src/universe.py:196); / prev close is the
    # nearest share figure available offline. Approximation, said so.
    adv = m["pdv20"] / pc if pc > 0 else None
    fl = m["float_m"] * 1e6 if m.get("float_m") else None
    hot.load_reference([ReferenceData(symbol=sym, prev_close=pc, avg_daily_volume=adv,
                                      float_shares=fl,
                                      float_quality=FloatQuality.UNKNOWN)])
    coll = Collector()
    router = NotificationRouter(RouterConfig(), [coll])
    scale = 1.0                                   # ibkr_desk.py:911 volume_floor_scale=1.0
    eng = ScannerEngine(hot=hot, scanners=[
        FivePillarsAlert(),
        HodMomentumScanner(min_volume_5m=MIN_VOLUME_5M * scale),
        UptrendScanner(min_volume_5m=MIN_VOLUME_5M * scale),
        RunningMoveScanner(direction="down", min_volume_5m=MIN_VOLUME_5M * scale),
        squeeze_5_in_5(), squeeze_10_in_10(),
        Breakout52wScanner(),
    ], router=router)
    return hot, eng, router, coll


def _reason(ev, prefix):
    for r in ev.reasons:
        if r.filter.startswith(prefix):
            return r.value
    return None


def symbol_day(sym, day, m, raw, plans_idx=None):
    import backtest_history as H
    from momentum_platform.models import Bar
    from momentum_platform.state import MarketUpdate
    from momentum_platform.scanners.five_pillars import pillars_passed

    rows = [r for r in H.to_rows(raw) if FEED_START <= r[0].time() < dtime(16, 0)]
    info = {"sym": sym, "day": day, "bars": len(rows), "basis": None, "raw_events": 0,
            "suppressed": defaultdict(int)}
    if len(rows) < 10:
        return [], info
    rth = next((r for r in rows if r[0].time() >= dtime(9, 30)), None)
    if rth is not None and m["open_px"] > 0:
        info["basis"] = rth[1] / m["open_px"]
    ts_list = [r[0] for r in rows]
    hot, eng, router, coll = build_engine(sym, m)
    ind = Causal()
    alerts = []
    tile_seen = 0
    nd = 0
    for i, (ts, o, h, l, c, v) in enumerate(rows):
        if ts.time() >= A_END:
            break
        tsu = ts.astimezone(timezone.utc)
        bar = Bar(symbol=sym, timeframe="1m", ts=tsu, open=o, high=h, low=l, close=c, volume=v)
        ind.add(h, l, c, v)
        n_before = len(coll.sink)
        emitted = eng.process(MarketUpdate(symbol=sym, ts=tsu, price=c, size=v, bar=bar))
        # router bookkeeping for the tile scanners
        new_deliv = router.deliveries[nd:]
        nd = len(router.deliveries)
        for dl in new_deliv:
            if dl.event.scanner in TILE:
                if dl.status == "delivered":
                    pass
                else:
                    info["suppressed"][dl.detail or dl.status] += 1
        info["raw_events"] += sum(1 for e in emitted if e.scanner in TILE)
        delivered = [e for e in coll.sink[n_before:] if e.scanner in TILE]
        if not delivered:
            continue
        snap = hot.get(sym).snapshot
        vw, above_vwap, above_e9, macd_ok = ind.gates(c)
        for ev in delivered:
            tile_seen += 1
            if not (A_START <= ts.time() < A_END):
                continue
            if ev.scanner == "running_up":
                kind = "UP10m_hod" if (ev.branch or "").endswith("_hod") else "UP10m"
                move = _reason(ev, "move_10m_pct")
            elif ev.scanner == "squeeze_5_in_5":
                kind, move = "5in5", _reason(ev, "move_5m_pct")
            else:
                kind, move = "10in10", _reason(ev, "move_10m_pct")
            hod = snap.session_high
            # ------- outcomes (strictly after the alert bar)
            out = {}
            t0 = ts
            j0 = i + 1
            for N in (10, 30, 60):
                jN = bisect.bisect_right(ts_list, t0 + timedelta(minutes=N), lo=j0)
                seg = rows[j0:jN]
                if not seg:
                    out[f"max{N}"] = float("nan"); out[f"ret{N}"] = float("nan")
                    if N == 30:
                        out["dd30"] = float("nan"); out["newhod30"] = False
                    continue
                highs = [r[2] for r in seg]
                k = int(np.argmax(highs))
                out[f"max{N}"] = 100.0 * (highs[k] / c - 1.0)
                out[f"ret{N}"] = 100.0 * (seg[-1][4] / c - 1.0)
                if N == 30:
                    lo = min(r[3] for r in seg[:k + 1])
                    out["dd30"] = min(0.0, 100.0 * (lo / c - 1.0))
                    out["newhod30"] = highs[k] > (hod or c)
            a = {
                "sym": sym, "day": day, "t": ts.strftime("%H:%M"), "epoch": int(tsu.timestamp()),
                "scanner": ev.scanner, "kind": kind, "severity": ev.severity,
                "move": move, "price": c,
                "chg": snap.change_from_close_pct,
                "gap": m["gap_pct"] if ts.time() >= dtime(9, 31) else None,   # the 09:30 gap is known only after the open
                "rvol_d": snap.rvol_daily, "rvol5": snap.rvol_5m,
                "vol5": snap.volume_5m, "dvol5": (snap.volume_5m or 0) * c,
                "cumvol": snap.volume_today, "cumdollar": ind.dollar,
                "hod_dist": snap.hod_distance_pct if snap.hod_distance_pct is not None else 0.0,
                "above_vwap": above_vwap, "above_e9": above_e9, "macd_ok": macd_ok,
                "vwap_dist": (100.0 * (c / vw - 1.0)) if vw else None,
                "idx": tile_seen, "mins": (ts.hour * 60 + ts.minute) - 7 * 60,
                "float_m": m.get("float_m"), "pillars3": pillars_passed(snap, snap.event_ts),
                "price_band": 2.0 <= c <= 20.0, "gain10": (snap.change_from_close_pct or 0) >= 10.0,
                "bar_range": 100.0 * (h - l) / l if l > 0 else None,
                **out,
            }
            alerts.append(a)
    info["suppressed"] = dict(info["suppressed"])
    return alerts, info


def day_job(args):
    day, metas = args
    f = CACHE / f"{day}.json"
    if not f.exists():
        return [], []
    bars = json.loads(f.read_text())
    alerts, infos = [], []
    for sym, m in metas.items():
        raw = bars.get(sym)
        if not raw:
            continue
        a, info = symbol_day(sym, day, m, raw)
        alerts += a
        infos.append(info)
    return alerts, infos


# ---------------------------------------------------------------- plans join
def plan_index():
    import rules_audit as RA
    plans = pickle.loads(RA.PLANS_CACHE.read_bytes())
    idx = defaultdict(list)
    n_pass = 0
    for p in plans:
        ok = RA.passes(p, RA.BASE)
        net = None
        filled = False
        if ok:
            n_pass += 1
            o = p["out"].get(("C", "base"))
            if o is not None:
                t_in, t_out, r, stopish, px = o
                net = r - RA.cost_live(p["entry"], p["stop"], stopish, p["pm"], p["dv5"],
                                       RA.BASE["risk"], RA.BASE["notional"], "live")
                filled = True
        idx[(p["sym"], p["day"])].append((p["arm"], ok, filled, net))
    for k in idx:
        idx[k].sort()
    return idx, len(plans), n_pass


def join_plans(alerts, idx):
    for a in alerts:
        a["plan"] = False; a["plan_filled"] = False; a["plan_net"] = None; a["plan_any"] = False
        for arm, ok, filled, net in idx.get((a["sym"], a["day"]), ()):
            if arm < a["epoch"] or arm > a["epoch"] + 30 * 60:
                continue
            a["plan_any"] = True
            if ok:
                a["plan"] = True; a["plan_filled"] = filled; a["plan_net"] = net
                break


# ---------------------------------------------------------------- analysis
def fnum(x, nd=1):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return f"{x:.{nd}f}"


BUCKETS = {
    "price": ("price $", [1, 2, 5, 10, 20], None),
    "chg": ("% chg vs prev close", [10, 20, 40, 80, 150], None),
    "gap": ("09:30 gap % (RTH alerts only)", [20, 40, 80], None),
    "rvol_d": ("daily RVOL (cum vol / 20d avg)", [0.5, 1, 2, 5, 10], None),
    "rvol5": ("5-min RVOL (vs prior 5m windows)", [1, 2, 5, 10, 20], None),
    "vol5": ("5-min volume (shares)", [25e3, 5e4, 1e5, 2.5e5, 1e6], None),
    "dvol5": ("5-min $ volume", [1e5, 2.5e5, 1e6, 5e6], None),
    "cumdollar": ("cum $ volume today", [1e6, 5e6, 2e7, 1e8], None),
    "hod_dist": ("% below HOD at alert", [0.001, 2, 5, 10, 25], None),
    "vwap_dist": ("% above session VWAP", [0, 5, 10, 20, 40], None),
    "move": ("scanner move %", [4, 5, 7, 10, 15], None),
    "idx": ("alert # for the name today", [1.5, 2.5, 3.5, 5.5], None),
    "mins": ("minutes after 07:00", [60, 120, 150, 180, 210], None),
    "bar_range": ("alert bar range %", [1, 2, 4, 8], None),
    "kind": ("scanner / branch", None, ["UP10m", "UP10m_hod", "5in5", "10in10"]),
    "above_vwap": ("above session VWAP", None, [False, True]),
    "above_e9": ("above EMA9", None, [False, True]),
    "macd_ok": ("MACD hist>0 & line>signal", None, [False, True]),
    "price_band": ("cascade price $2-20", None, [False, True]),
    "gain10": ("gain pillar >=10%", None, [False, True]),
    "pillars3": ("pillars passed (of 3 measurable)", None, [0, 1, 2, 3]),
}


def bucket_of(key, x):
    _, edges, cats = BUCKETS[key]
    if cats is not None:
        return x if x in cats else None
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return bisect.bisect_right(edges, x)


def bucket_label(key, b):
    _, edges, cats = BUCKETS[key]
    if cats is not None:
        return str(b)
    def f(e):
        if e >= 1e6:
            return f"{e/1e6:g}M"
        if e >= 1e3:
            return f"{e/1e3:g}k"
        return f"{e:g}"
    if b == 0:
        return f"< {f(edges[0])}"
    if b == len(edges):
        return f">= {f(edges[-1])}"
    return f"{f(edges[b-1])}-{f(edges[b])}"


def outcome_row(sub):
    n = len(sub)
    if n == 0:
        return None
    m30 = np.array([a["max30"] for a in sub if not math.isnan(a["max30"])])
    nets = [a["plan_net"] for a in sub if a["plan_filled"]]
    r30 = np.array([a["ret30"] for a in sub if not math.isnan(a["ret30"])])
    return {
        "n": n,
        "ret": float(np.median(r30)) if len(r30) else float("nan"),
        "up": 100.0 * float(np.mean(r30 > 0)) if len(r30) else float("nan"),
        "p10": 100.0 * float(np.mean(m30 >= 10.0)) if len(m30) else float("nan"),
        "med": float(np.median(m30)) if len(m30) else float("nan"),
        "small": 100.0 * float(np.mean(m30 < 3.0)) if len(m30) else float("nan"),
        "hod": 100.0 * float(np.mean([a["newhod30"] for a in sub])),
        "plan": 100.0 * float(np.mean([a["plan"] for a in sub])),
        "nfill": len(nets),
        "netR": float(np.mean(nets)) if nets else float("nan"),
    }


def lift_table(alerts, key, lines):
    title = BUCKETS[key][0]
    tr = [a for a in alerts if a["day"] < SPLIT]
    te = [a for a in alerts if a["day"] >= SPLIT]
    bt_tr, bt_te = defaultdict(list), defaultdict(list)
    for a in tr:
        b = bucket_of(key, a[key])
        if b is not None:
            bt_tr[b].append(a)
    for a in te:
        b = bucket_of(key, a[key])
        if b is not None:
            bt_te[b].append(a)
    cov_tr = sum(len(v) for v in bt_tr.values()); cov_te = sum(len(v) for v in bt_te.values())
    lines.append(f"\n### {key} — {title}   (coverage train {cov_tr}/{len(tr)}, test {cov_te}/{len(te)})")
    hd = f" {'n':>6} {'P>=10%':>7} {'med30':>6} {'small':>6} {'ret30':>6} {'newHOD':>6} {'plan%':>6} {'nfill':>5} {'netR':>6}"
    lines.append(f"{'bucket':<14}|{hd} |{hd}")
    lines.append(f"{'':<14}| {'TRAIN 2016-2023':^65} | {'TEST 2024-2026':^65}")
    keys = sorted(set(bt_tr) | set(bt_te), key=lambda b: (str(type(b)), b))
    for b in keys:
        r1, r2 = outcome_row(bt_tr.get(b, [])), outcome_row(bt_te.get(b, []))
        def cells(r):
            if r is None:
                return f"{0:>6} {'—':>7} {'—':>6} {'—':>6} {'—':>6} {'—':>6} {'—':>6} {0:>5} {'—':>6}"
            return (f"{r['n']:>6} {fnum(r['p10']):>7} {fnum(r['med']):>6} {fnum(r['small']):>6} {fnum(r['ret']):>6} {fnum(r['hod']):>6} "
                    f"{fnum(r['plan']):>6} {r['nfill']:>5} {fnum(r['netR'], 2):>6}")
        lines.append(f"{bucket_label(key, b):<14}| {cells(r1)} | {cells(r2)}")


def auc(scores, labels):
    """Mann-Whitney AUC with average ranks for ties."""
    s = np.asarray(scores, float); y = np.asarray(labels, bool)
    if y.all() or (~y).all():
        return float("nan")
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s)); sorted_s = s[order]
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and sorted_s[j + 1] == sorted_s[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1
        i = j + 1
    npos = y.sum(); nneg = len(y) - npos
    return float((ranks[y].sum() - npos * (npos + 1) / 2.0) / (npos * nneg))


def _ranks(v):
    v = np.asarray(v, float)
    order = np.argsort(v, kind="mergesort"); sv = v[order]
    ranks = np.empty(len(v)); i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and sv[j + 1] == sv[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1
        i = j + 1
    return ranks


def spearman(x, y):
    rx, ry = _ranks(x), _ranks(y)
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


NUMERIC = ["price", "chg", "gap", "rvol_d", "rvol5", "vol5", "dvol5", "cumdollar", "hod_dist",
           "vwap_dist", "move", "idx", "mins", "bar_range", "above_vwap", "above_e9", "macd_ok",
           "price_band", "gain10", "pillars3"]


def featvec(alerts, key, out="max30"):
    xs, ys, ys10 = [], [], []
    for a in alerts:
        x = a.get(key)
        if x is None or (isinstance(x, float) and math.isnan(x)) or math.isnan(a[out]):
            continue
        xs.append(float(x)); ys.append(a[out]); ys10.append(a[out] >= 10.0)
    return np.array(xs), np.array(ys), np.array(ys10)


def discriminators(alerts, lines):
    tr = [a for a in alerts if a["day"] < SPLIT]
    te = [a for a in alerts if a["day"] >= SPLIT]
    rows = []
    for k in NUMERIC:
        x1, y1, z1 = featvec(tr, k); x2, y2, z2 = featvec(te, k)
        if len(x1) < 50 or len(x2) < 50:
            continue
        r1 = featvec(tr, k, "ret30"); r2 = featvec(te, k, "ret30")
        rows.append((k, len(x1), auc(x1, z1), spearman(x1, y1), auc(x1, y1 < 3.0),
                     len(x2), auc(x2, z2), spearman(x2, y2), auc(x2, y2 < 3.0),
                     spearman(r1[0], r1[1]), spearman(r2[0], r2[1])))
    rows.sort(key=lambda r: -abs(r[2] - 0.5))
    lines.append("\n## Single-feature discrimination (AUC10 = AUC for max30 >= +10%; rho = Spearman with max30; AUCsm = AUC for small move max30 < 3%; rhoR = Spearman with ret30) — sorted by train |AUC10-0.5|")
    lines.append(f"{'feature':<12}| {'n tr':>6} {'AUC10':>6} {'rho':>6} {'AUCsm':>6} {'rhoR':>6} | {'n te':>6} {'AUC10':>6} {'rho':>6} {'AUCsm':>6} {'rhoR':>6}")
    for r in rows:
        lines.append(f"{r[0]:<12}| {r[1]:>6} {r[2]:>6.3f} {r[3]:>+6.3f} {r[4]:>6.3f} {r[9]:>+6.3f} | {r[5]:>6} {r[6]:>6.3f} {r[7]:>+6.3f} {r[8]:>6.3f} {r[10]:>+6.3f}")
    return rows


def small_moves(alerts, lines):
    lines.append("\n## Small moves — max30 < +3% from the alert close")
    for name, sub in (("train", [a for a in alerts if a["day"] < SPLIT]), ("test", [a for a in alerts if a["day"] >= SPLIT])):
        sub = [a for a in sub if not math.isnan(a["max30"])]
        sm = [a for a in sub if a["max30"] < 3.0]
        rest = [a for a in sub if a["max30"] >= 3.0]
        big = [a for a in sub if a["max30"] >= 10.0]
        lines.append(f"{name}: {len(sm)}/{len(sub)} = {100*len(sm)/max(1,len(sub)):.1f}% small; "
                     f"{len(big)} = {100*len(big)/max(1,len(sub)):.1f}% reach +10% in 30 min")
        lines.append(f"  {'feature (median, or % true)':<34}{'small':>10}{'>=3%':>10}{'>=10%':>10}")
        scale = {"vol5": (1e3, "vol5 (k shares)"), "dvol5": (1e3, "dvol5 ($k)"), "cumdollar": (1e6, "cumdollar ($M)")}
        for k in ("price", "chg", "rvol_d", "rvol5", "vol5", "dvol5", "cumdollar", "hod_dist", "vwap_dist",
                  "move", "idx", "mins", "bar_range"):
            div, lab = scale.get(k, (1.0, k))
            def med(s):
                v = [a[k] for a in s if a.get(k) is not None and not (isinstance(a[k], float) and math.isnan(a[k]))]
                return float(np.median(v)) / div if v else float("nan")
            lines.append(f"  {lab:<34}{med(sm):>10.2f}{med(rest):>10.2f}{med(big):>10.2f}")
        for k in ("above_vwap", "above_e9", "macd_ok", "price_band", "gain10"):
            def pct(s):
                v = [bool(a[k]) for a in s if a.get(k) is not None]
                return 100.0 * float(np.mean(v)) if v else float("nan")
            lines.append(f"  {k + ' (% true)':<34}{pct(sm):>10.1f}{pct(rest):>10.1f}{pct(big):>10.1f}")
        for kd in ("UP10m", "UP10m_hod", "5in5", "10in10"):
            def share(s):
                return 100.0 * sum(1 for a in s if a["kind"] == kd) / max(1, len(s))
            lines.append(f"  {'kind=' + kd + ' (% of group)':<34}{share(sm):>10.1f}{share(rest):>10.1f}{share(big):>10.1f}")


def score_model(alerts, rows, lines, k_best=5, seed=7):
    """Monotone score: the k features with the largest train |AUC-0.5| (one per
    family), each turned into its TRAIN-distribution percentile rank, signed by
    the train direction, averaged. Nothing is fitted on test."""
    tr = [a for a in alerts if a["day"] < SPLIT and not math.isnan(a["max30"])]
    te = [a for a in alerts if a["day"] >= SPLIT and not math.isnan(a["max30"])]
    family = {"vol5": "vol", "dvol5": "vol", "cumdollar": "vol", "rvol_d": "rvol", "rvol5": "rvol5",
              "above_vwap": "vwap", "vwap_dist": "vwap", "price": "price", "price_band": "price",
              "chg": "chg", "gain10": "chg", "pillars3": "chg"}
    chosen, fams = [], set()
    for r in rows:
        k = r[0]
        if k == "gap":                         # missing pre-market: not usable for every alert
            continue
        f = family.get(k, k)
        if f in fams:
            continue
        chosen.append((k, 1.0 if r[2] >= 0.5 else -1.0)); fams.add(f)
        if len(chosen) == k_best:
            break
    ref = {k: np.sort(np.array([float(a[k]) for a in tr if a.get(k) is not None])) for k, _ in chosen}

    def score(a):
        s, n = 0.0, 0
        for k, sign in chosen:
            x = a.get(k)
            if x is None:
                continue
            arr = ref[k]
            lo = np.searchsorted(arr, float(x), "left"); hi = np.searchsorted(arr, float(x), "right")
            pr = (lo + hi) / 2.0 / len(arr)
            s += sign * pr; n += 1
        return s / n if n else 0.0
    for a in tr + te:
        a["score"] = score(a)
    lines.append("\n## Monotone score — features chosen on TRAIN only: " +
                 ", ".join(f"{k}({'+' if s > 0 else '-'})" for k, s in chosen))
    for name, sub in (("train", tr), ("test", te)):
        sc = np.array([a["score"] for a in sub]); y = np.array([a["max30"] for a in sub])
        lines.append(f"{name}: n={len(sub)}  Spearman(score, max30) = {spearman(sc, y):+.3f}  "
                     f"AUC(max30>=10%) = {auc(sc, y >= 10):.3f}  AUC(small<3%) = {auc(sc, y < 3):.3f}")
        # deciles by the TRAIN cut points
        cuts = np.quantile(np.array([a["score"] for a in tr]), np.linspace(0.1, 0.9, 9))
        groups = defaultdict(list)
        for a in sub:
            groups[int(np.searchsorted(cuts, a["score"], "right"))].append(a)
        lines.append(f"  {'decile':<7}{'n':>6}{'P>=10%':>8}{'med30':>7}{'small%':>8}{'ret30':>7}{'up30%':>7}{'newHOD':>8}{'plan%':>7}{'nfill':>6}{'netR':>7}{'med dd30':>9}")
        for d in range(10):
            g = groups.get(d, [])
            r = outcome_row(g)
            if r is None:
                continue
            dd = float(np.median([a["dd30"] for a in g if not math.isnan(a["dd30"])])) if g else float("nan")
            lines.append(f"  {d+1:<7}{r['n']:>6}{fnum(r['p10']):>8}{fnum(r['med']):>7}{fnum(r['small']):>8}"
                         f"{fnum(r['ret']):>7}{fnum(r['up']):>7}{fnum(r['hod']):>8}{fnum(r['plan']):>7}{r['nfill']:>6}{fnum(r['netR'], 2):>7}{fnum(dd):>9}")
        if name == "test":
            top = groups.get(9, []); bot = groups.get(0, [])
            days = sorted({a["day"] for a in sub})
            by_day_top, by_day_bot = defaultdict(list), defaultdict(list)
            for a in top:
                by_day_top[a["day"]].append(a["max30"] >= 10)
            for a in bot:
                by_day_bot[a["day"]].append(a["max30"] >= 10)
            rng = random.Random(seed); diffs = []
            for _ in range(1000):
                ds = [rng.choice(days) for _ in days]
                t = [x for d in ds for x in by_day_top.get(d, [])]
                b = [x for d in ds for x in by_day_bot.get(d, [])]
                if t and b:
                    diffs.append(100 * (np.mean(t) - np.mean(b)))
            lo, hi = np.percentile(diffs, [2.5, 97.5])
            lines.append(f"  test top-decile minus bottom-decile P(max30>=10%): "
                         f"{100*(np.mean([a['max30']>=10 for a in top]) - np.mean([a['max30']>=10 for a in bot])):+.1f} pts, "
                         f"day-clustered bootstrap 95% CI [{lo:+.1f}, {hi:+.1f}] (1000 draws)")
    return chosen


def analyse(alerts, infos, meta_stats, plan_stats, lines):
    n_sd = len(infos)
    bad = [i for i in infos if i["basis"] is not None and not (0.9 <= i["basis"] <= 1.1)]
    bad_keys = {(i["sym"], i["day"]) for i in bad}
    lines.append(f"symbol-days replayed: {n_sd}  (sessions: {len({i['day'] for i in infos})})")
    lines.append(f"float_m coverage in candidate_days.csv: {meta_stats[1]}/{meta_stats[0]} rows; catalyst: 0 used")
    lines.append(f"price-basis check: 09:30 bar open / csv open_px outside [0.9, 1.1] on {len(bad)} symbol-days "
                 f"(dropped: their prev_close-based % would be wrong)")
    raw = sum(i["raw_events"] for i in infos)
    sup = defaultdict(int)
    for i in infos:
        for k, v in i["suppressed"].items():
            sup[k] += v
    lines.append(f"tile-scanner raw events 04:00-11:30: {raw}; router-suppressed: {dict(sup)}")
    lines.append(f"plans in rules_audit_plans.pkl: {plan_stats[0]}; passing rules_audit.passes(p, BASE): {plan_stats[1]}")
    alerts = [a for a in alerts if (a["sym"], a["day"]) not in bad_keys]
    tr = [a for a in alerts if a["day"] < SPLIT]; te = [a for a in alerts if a["day"] >= SPLIT]
    lines.append(f"tile alerts 07:00-11:30 delivered (analysed): {len(alerts)}  train {len(tr)} / test {len(te)}; "
                 f"symbol-days with >=1 alert: {len({(a['sym'], a['day']) for a in alerts})}")
    kinds = defaultdict(int)
    for a in alerts:
        kinds[a["kind"]] += 1
    lines.append(f"by scanner/branch: {dict(kinds)}")
    lines.append("\n## Overall outcome (all tile alerts)")
    lines.append(f"{'':<8}{'n':>7}{'P>=10%':>8}{'med30':>7}{'small%':>8}{'newHOD':>8}{'plan%':>7}{'nfill':>6}{'netR':>7}"
                 f"{'med10':>7}{'med60':>7}{'med dd30':>9}{'ret30':>7}{'up30%':>7}")
    for name, sub in (("train", tr), ("test", te)):
        r = outcome_row(sub)
        m10 = float(np.nanmedian([a["max10"] for a in sub])); m60 = float(np.nanmedian([a["max60"] for a in sub]))
        dd = float(np.nanmedian([a["dd30"] for a in sub]))
        lines.append(f"{name:<8}{r['n']:>7}{fnum(r['p10']):>8}{fnum(r['med']):>7}{fnum(r['small']):>8}{fnum(r['hod']):>8}"
                     f"{fnum(r['plan']):>7}{r['nfill']:>6}{fnum(r['netR'], 2):>7}{fnum(m10):>7}{fnum(m60):>7}{fnum(dd):>9}"
                     f"{fnum(r['ret']):>7}{fnum(r['up']):>7}")
    lines.append("\ncolumns: n alerts · P>=10% = share whose max high in the next 30 min is >= +10% over the alert close ·"
                 " med30 = median of that max (%) · small = share with max30 < +3% · newHOD = share making a new high of day"
                 " within 30 min · plan% = share with a first-pullback plan armed within 30 min that passes"
                 " rules_audit.passes(p, BASE) · nfill/netR = those plans that filled (mode C, key base) and their mean net R"
                 " (cost_live $40/$2,000) — plan-level, no one-position portfolio · ret30 = median close 30 min later vs alert close (%)"
                 " · up30% = share with ret30 > 0 · dd30 = deepest low between the alert and the 30-min max (%)")
    lines.append("\n## Lift tables")
    for k in BUCKETS:
        lift_table(alerts, k, lines)
    rows = discriminators(alerts, lines)
    small_moves(alerts, lines)
    score_model(alerts, rows, lines)
    return alerts


# ---------------------------------------------------------------- selftest
def selftest():
    from momentum_platform import indicators as I
    import backtest_history as H
    meta, *_ = load_meta()
    days = sorted(meta)
    rng = random.Random(3)
    checked = 0
    for d in rng.sample(days, 6):
        bars = json.loads((CACHE / f"{d}.json").read_text())
        for s, m in list(meta[d].items())[:3]:
            raw = bars.get(s)
            if not raw:
                continue
            rows = [r for r in H.to_rows(raw) if FEED_START <= r[0].time() < dtime(11, 30)]
            ind = Causal(); hist = []
            for (ts, o, h, l, c, v) in rows:
                ind.add(h, l, c, v); hist.append([0, o, h, l, c, v])
                g = I.chart_gates(hist)
                vw, av, ae, mo = ind.gates(c)
                assert (g["above_vwap"] is None) == (av is None) and (av is None or g["above_vwap"] == av), (d, s, ts)
                assert g["above_ema9"] == ae, (d, s, ts, g["above_ema9"], ae)
                assert g["macd_positive_and_above_signal"] == mo, (d, s, ts, g, mo)
                checked += 1
            a, info = symbol_day(s, d, m, raw)
            print(d, s, info["bars"], "alerts", len(a), "raw", info["raw_events"], info["suppressed"],
                  [(x["t"], x["kind"], round(x["move"] or 0, 1), round(x["max30"], 1)) for x in a[:4]])
    print("selftest ok: causal VWAP/EMA9/MACD equal indicators.chart_gates on", checked, "bars")


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--sample", type=int)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--analyse-only", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest(); return
    meta, n_rows, n_float = load_meta()
    store = OUT / ("alerts.pkl" if not args.sample else f"alerts_sample{args.sample}.pkl")
    if args.analyse_only and store.exists():
        alerts, infos = pickle.loads(store.read_bytes())
    else:
        days = sorted(d for d in meta if (CACHE / f"{d}.json").exists())
        if args.sample:
            days = sorted(random.Random(20261002).sample(days, args.sample))
        t0 = _time.time()
        alerts, infos = [], []
        with Pool(args.procs) as pool:
            for k, (a, inf) in enumerate(pool.imap_unordered(day_job, [(d, meta[d]) for d in days], chunksize=4), 1):
                alerts += a; infos += inf
                if k % 200 == 0:
                    print(f"  {k}/{len(days)} sessions · {len(alerts)} alerts · {_time.time()-t0:.0f}s", flush=True)
        print(f"replay done in {_time.time()-t0:.0f}s", flush=True)
        store.write_bytes(pickle.dumps((alerts, infos)))
    idx, n_plans, n_pass = plan_index()
    join_plans(alerts, idx)
    lines = [f"# Running Up tile alerts — replay of the live scanner classes · script {Path(__file__).resolve()}",
             f"# split: train day < {SPLIT}, test day >= {SPLIT}"]
    analyse(alerts, infos, (n_rows, n_float), (n_plans, n_pass), lines)
    txt = "\n".join(lines)
    print(txt)
    (OUT / ("results.txt" if not args.sample else f"results_sample{args.sample}.txt")).write_text(txt)


if __name__ == "__main__":
    main()
