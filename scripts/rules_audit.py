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
K_VARIANTS = 43          # 41 preregistered + 2 Ross-retrace (addendum 2026-10-01b)
ALPHA = 0.05 / K_VARIANTS
PLANS_CACHE = ROOT / "data" / "cache" / "rules_audit_plans.pkl"

# outcome keys: entry model x exit
ENTRY_KEYS = {"base": ("rt", 3, 0.3), "ttl1": ("rt", 1, 0.3), "ttl5": ("rt", 5, 0.3),
              "cap0.5": ("rt", 3, 0.5), "cap1.0": ("rt", 3, 1.0), "intrabar": ("ib", 3, 0.3)}
EXIT_KEYS = {"tr0.5": (0.5, dtime(11, 30)), "tr1.5": (1.5, dtime(11, 30)), "tr2.0": (2.0, dtime(11, 30)),
             "flat1100": (1.0, dtime(11, 0)), "flat1200": (1.0, dtime(12, 0))}


# ------------------------------------------------------------------ engine
#: Bar-order readings of a 1-minute bar (added after the 2026-10-01 adversarial
#: review; mode A is the preregistered run, reproduced exactly):
#:   A   as run — `backtest_recent` semantics: the fill bar's high ratchets the
#:       trail even when the fill came on the way DOWN to the cap, the fill
#:       bar's low stops the trade even if it came before the fill, the order
#:       expiry counts bars;
#:   C   corrected — on a cap-return fill the fill bar ratchets only with
#:       max(fill, close); the expiry counts minutes from the order;
#:   CA  C, and a fill-bar low under the stop is taken to have come BEFORE a
#:       fill at the trigger (the stop-limit had not yet triggered);
#:   H   C, and on every later bar the high comes first (a spike then a fade
#:       inside the minute, as the live 10-second trail would see it).
MODES = ("A", "C", "CA", "H")


def cap_of(entry: float, cap_pct: float) -> float:
    """A10's limit: trigger + max(1 cent, cap %) — execution.intent.entry_limit at 0.3 %."""
    return round(entry + max(0.01, entry * cap_pct / 100.0), 4)


def fill_retouch(fwd: list, entry: float, ttl: int, cap_pct: float, order_t: int | None = None):
    """`backtest_recent.plans_for_day(gap_miss=True)`, with the expiry and the cap
    as parameters: (index into fwd, fill price, kind) or None. kind is 'entry'
    (crossed the trigger), 'open' (opened between trigger and cap) or
    'cap_return' (opened above the cap, filled on the way back down). With
    `order_t` (epoch of the order) the expiry is `ttl` MINUTES from the order,
    as the live runner cancels it; without, `ttl` bars as backtest_recent did."""
    cap = cap_of(entry, cap_pct)
    if order_t is None:
        window = list(range(min(ttl, len(fwd))))
    else:
        window = [k for k, b in enumerate(fwd) if b[0].timestamp() < order_t + ttl * 60]
    touch = next((k for k in window if fwd[k][2] >= entry), None)
    if touch is None:
        return None
    o = fwd[touch][1]
    if o > cap:
        back_range = (range(touch, min(len(fwd), touch + ttl)) if order_t is None
                      else [k for k in window if k >= touch])
        back = next((k for k in back_range if fwd[k][3] <= cap), None)
        return None if back is None else (back, cap, "cap_return")
    if o > entry:
        return touch, o, "open"
    return touch, entry, "entry"


def run_exit(bars: list, entry: float, stop: float, fill: float, trail_r: float, flat: dtime,
             mode: str = "A", kind: str = "entry"):
    """A3 trail (`backtest_recent.simulate` 'trail' with the multiple and the
    flatten time as parameters), under one bar-order reading (MODES). Returns
    (R, stopish, exit bar index)."""
    rps = entry - stop
    level = stop
    for k, (ts, o, h, l, c, v) in enumerate(bars):
        if ts.time() >= flat:
            return (o - fill) / rps, True, k                # a market flatten crosses the spread too
        if k == 0:
            skip_low = mode == "CA" and kind == "entry" and o <= entry
            if l <= level and not skip_low:
                return (min(level, o) - fill) / rps, True, k
            top = max(fill, c) if (mode != "A" and kind == "cap_return") else h
            level = max(level, top - trail_r * rps)
            continue
        if mode == "H":
            # open, then the high, then the low: a gap under the standing stop
            # fills at the open; otherwise the high raises the stop first and
            # the fade takes it out at that raised level.
            if o <= level:
                return (o - fill) / rps, True, k
            level = max(level, h - trail_r * rps)
            if l <= level:
                return (level - fill) / rps, True, k
            continue
        if l <= level:
            return (min(level, o) - fill) / rps, True, k
        level = max(level, h - trail_r * rps)
    return (bars[-1][4] - fill) / rps, False, len(bars) - 1


def _red(g: dict, entry: float, volume_ok: bool) -> list:
    red = []
    if not (E.PRICE_MIN <= entry <= E.PRICE_MAX):
        red.append("price")
    if g["above_vwap"] is not True:
        red.append("vwap")
    if g["above_ema9"] is not True:
        red.append("ema9")
    if g["macd_positive_and_above_signal"] is not True:
        red.append("macd")
    if not volume_ok:
        red.append("volume")
    return red


def plans_for_symbol_day(sym: str, day: str, rows: list, prev_close: float) -> list[dict]:
    det = FirstPullbackDetector()
    hist: list = []
    hi = None
    out = []
    for i, (ts, o, h, l, c, v) in enumerate(rows):
        hi_prev = hi
        hi = h if hi is None else max(hi, h)
        hist.append([int(ts.timestamp()), o, h, l, c, v])
        plan = det.on_bar(Bar(symbol=sym, timeframe="1m", ts=ts.astimezone(timezone.utc),
                              open=o, high=h, low=l, close=c, volume=v))
        if plan is None or not (ARM_START <= ts.time() < ARM_END):
            continue
        entry, stop = round(plan.entry, 4), round(plan.stop, 4)
        if entry - stop <= 0:
            continue
        red = _red(I.chart_gates(hist), entry, plan.volume_ok)
        # The live desk arms while the trigger bar forms and freezes the gates
        # then: it never sees this bar's close. For an entry ON the trigger bar
        # the honest gates are the last completed bar's (review 2026-10-01).
        red_prev = _red(I.chart_gates(hist[:-1]), entry, plan.volume_ok)
        c_prev = rows[i - 1][4] if i else c
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
        leg_low = imp[0].open if imp else None
        leg = (plan.impulse_high - leg_low) if leg_low else None
        retrace = (plan.impulse_high - plan.pullback_low) / leg if leg and leg > 0 else None
        pm = ts.time() < RTH
        dv5 = float(sum(b[4] * b[5] for b in hist[-5:]))
        spread = PROXY.spread(entry, pm, dv5)
        rec = {"sym": sym, "day": day, "t": ts.strftime("%H:%M"), "arm": int(ts.timestamp()),
               "entry": entry, "stop": stop, "stop_pct": (entry - stop) / entry * 100.0,
               "fade": 100.0 * (hi - c) / hi if hi else 0.0, "red": red,
               "fade_prev": 100.0 * (hi_prev - c_prev) / hi_prev if hi_prev else 0.0, "red_prev": red_prev,
               "retrace": retrace,
               "macd_line_pos": macd_line_pos, "push_rising": push_rising, "push_elevated": push_elevated,
               "pm": pm, "dv5": dv5, "spread_ratio": (entry - stop) / spread if spread > 0 else 99.0,
               "out": {}}
        fwd = rows[i + 1:]
        if not fwd:
            out.append(rec); continue
        order_t = int(ts.timestamp()) + 60
        for mode in MODES:
            mins = None if mode == "A" else order_t
            for key, (model, ttl, cap_pct) in ENTRY_KEYS.items():
                f = None
                if model == "ib":
                    cap = cap_of(entry, cap_pct)
                    if o <= entry <= h:
                        f = (entry, "entry")                # crossed while the trigger bar formed
                    elif entry < o <= cap:
                        f = (o, "open")
                    if f is not None:
                        bars = rows[i:]
                        r, stopish, k = run_exit(bars, entry, stop, f[0], 1.0, dtime(11, 30), mode, f[1])
                        rec["out"][(mode, key)] = (int(bars[0][0].timestamp()), int(bars[k][0].timestamp()),
                                                   round(r, 4), stopish, f[0])
                        continue
                got = fill_retouch(fwd, entry, ttl, cap_pct, mins)
                if got is None:
                    rec["out"][(mode, key)] = None; continue
                fk, px, kind = got
                bars = fwd[fk:]
                r, stopish, k = run_exit(bars, entry, stop, px, 1.0, dtime(11, 30), mode, kind)
                rec["out"][(mode, key)] = (int(bars[0][0].timestamp()), int(bars[k][0].timestamp()),
                                           round(r, 4), stopish, px)
            base_fill = fill_retouch(fwd, entry, 3, 0.3, mins)
            for key, (trail_r, flat) in EXIT_KEYS.items():
                if base_fill is None:
                    rec["out"][(mode, key)] = None; continue
                fk, px, kind = base_fill
                bars = fwd[fk:]
                r, stopish, k = run_exit(bars, entry, stop, px, trail_r, flat, mode, kind)
                rec["out"][(mode, key)] = (int(bars[0][0].timestamp()), int(bars[k][0].timestamp()),
                                           round(r, 4), stopish, px)
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
              risk: float = 40.0, notional: float | None = 2000.0, model: str = "live") -> float:
    """`backtest_recent.cost_r` model "live", with the risk and the cap as
    parameters (F1). tests/test_rules_audit.py pins it to cost_r at $40 / $2,000.
    model "old": one cent a marketable side, no spread (the preregistered
    sensitivity); "light": the larger of the half-spread and one cent a side
    (edge_hunt.costs "light"); "none": gross."""
    if model == "none":
        return 0.0
    rps = entry - stop
    sh = int(risk // rps)
    if notional:
        sh = min(sh, int(notional // entry))
    sh = max(1, sh)
    half = PROXY.spread(entry, pm, dv5) / 2
    per = {"live": half + 0.01, "old": 0.01, "light": max(half, 0.01)}[model]
    comm = 2 * min(max(1.0, 0.005 * sh), max(1.0, 0.01 * sh * entry))
    fric = sh * per * (2 if stopish else 1)
    return round((comm + fric) / (sh * rps), 3)


# ------------------------------------------------------------------ rules and portfolio
BASE = dict(fade=25.0, stop_floor=2.0, spread_k=4.0, start="07:00", end="11:20", push=None, macd_line=False,
            key="base", ttl=3, max_pos=1, loss=3.0, streak=3, orders=6, risk=40.0, notional=2000.0,
            mode="A", costs="live", gates="close", retrace=None)


def passes(p: dict, c: dict) -> bool:
    prev = c.get("gates") == "prev"
    if c.get("gates") == "desk":
        # scripts/desk_replay.py: the gates as the live desk judged them, on the
        # half-formed trigger minute at the moment it armed. No record, no plan.
        d = p.get("desk")
        if not d or d.get("red") is None or d["red"]:
            return False
        if c["fade"] is not None and d["fade"] > c["fade"]:
            return False
    elif (p["red_prev"] if prev else p["red"]):
        return False
    elif c["fade"] is not None and (p["fade_prev"] if prev else p["fade"]) > c["fade"]:
        return False
    if c.get("retrace") is not None and (p["retrace"] is None or p["retrace"] > c["retrace"]):
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
    # addendum 2026-10-01c (scripts/rules_audit_open.py adds the fields)
    if c.get("range_k") is not None and (p.get("range5") is None or p["entry"] - p["stop"] < c["range_k"] * p["range5"]):
        return False
    if c.get("max_index") is not None and p.get("plan_index", 1) > c["max_index"]:
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
            o = p["out"].get((c.get("mode", "A"), c["key"]))
            if o is None:
                busy.append((t_order + c["ttl"] * 60, p["sym"]))
                continue
            t_in, t_out, r, stopish, px = o
            if c.get("lockout"):
                hm = datetime.fromtimestamp(t_in, timezone.utc).astimezone(E.ET).strftime("%H:%M")
                if "09:30" <= hm < c["lockout"]:            # O2: the opening-minutes fill is cancelled
                    busy.append((t_order + c["ttl"] * 60, p["sym"]))
                    continue
            busy.append((t_out + 60, p["sym"]))
            pending.append((t_out + 60, r))
            net = r - cost_live(p["entry"], p["stop"], stopish, p["pm"], p["dv5"], c["risk"], c["notional"],
                                c.get("costs", "live"))
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


def paired_lb(var: list[dict], base: list[dict], draws: int = 20000, seed: int = 20261001,
              alpha: float | None = None) -> float:
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
    return float(np.quantile(mv - mb, ALPHA if alpha is None else alpha))


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


def verdict(group: str, b: dict, v: dict, lb: float, scale: float = 1.0) -> tuple[str, dict]:
    """The preregistered adoption rule. `scale` = variant risk / $40: a sizing
    variant is judged in DOLLARS (review 2026-10-01: in R, $80 risk 'passed'
    while losing 50 % more dollars), so its means and drawdown are scaled."""
    tr_ok = v["train"].get("n", 0) and v["train"]["mean"] * scale > b["train"]["mean"]
    te_ok = v["test"].get("n", 0) and v["test"]["mean"] * scale > b["test"]["mean"]
    n_ok = v["test"].get("n", 0) >= 200
    yrs = sum(1 for y in ("2024", "2025", "2026")
              if v["years"][y].get("n", 0) and b["years"][y].get("n", 0)
              and v["years"][y]["mean"] * scale > b["years"][y]["mean"])
    lb_ok = lb == lb and lb > 0 and scale == 1.0
    if scale != 1.0:                          # dollars: the per-trade gap itself, no bootstrap in R
        lb_ok = bool(te_ok and tr_ok)
    dd_ok = True
    if group.split()[0] in RISK_RULES:
        dd_ok = v["test"].get("max_dd", 1e9) * scale <= 1.10 * b["test"].get("max_dd", 0)
    checks = {"train better": bool(tr_ok), "test better": bool(te_ok), ">=200 test trades": bool(n_ok),
              "2 of 3 test years": yrs >= 2, "paired lower bound > 0": bool(lb_ok), "drawdown ok": bool(dd_ok)}
    if group.split()[0] == "F1":
        # With a negative expectancy, less money at risk always loses fewer
        # dollars and more always loses more: neither unit can judge a sizing
        # change. It is the owner's capital decision; R is reported for costs.
        return "OWNER", checks
    return ("ADOPT" if all(checks.values()) else "keep B"), checks


POSTHOC = [
    ("post-hoc combo", "start 09:30 + stop 3 %", {"start": "09:30", "stop_floor": 3.0}),
    ("post-hoc combo", "stop 3 % + spread 6x", {"stop_floor": 3.0, "spread_k": 6.0}),
]
ROSS_RETRACE = [
    ("Ross retrace", "pullback <= 50 % of the push (with rule 5)", {"retrace": 0.5}),
    ("Ross retrace", "pullback <= 50 % of the push, instead of rule 5", {"retrace": 0.5, "fade": None}),
]


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
    plans = None
    if cache_ok:
        plans = pickle.loads(PLANS_CACHE.read_bytes())
        if plans and ("C", "base") not in plans[0]["out"] and plans[0]["out"]:
            plans = None                                   # a cache from before the bar-order modes
    if plans is None:
        plans = collect(days, uni, args.cache, args.procs)
        if not args.sample:
            PLANS_CACHE.parent.mkdir(parents=True, exist_ok=True)
            PLANS_CACHE.write_bytes(pickle.dumps(plans))
    by_day = defaultdict(list)
    for p in plans:
        by_day[p["day"]].append(p)
    print(f"{len(plans)} plans armed 07:00-11:30 on {len(by_day)} sessions · costs live ($40 / $2,000, spread proxy + 1c)")
    res = {"alpha": ALPHA, "K": K_VARIANTS, "modes": {}, "robustness": []}

    def line(name, s):
        tr, te = s["train"], s["test"]
        return (f"  {name:<46}{tr.get('n', 0):>6}{tr.get('mean', float('nan')):>+8.3f}"
                f"{te.get('n', 0):>6}{te.get('mean', float('nan')):>+8.3f}{te.get('total', 0):>+9.1f}"
                f"{te.get('max_dd', 0):>7.1f}{te.get('lose_streak', 0):>5}{te.get('worst_day', 0):>+7.1f}"
                f"{te.get('per_month', 0):>6.1f}")
    hdr = (f"  {'rule · variant':<46}{'tr n':>6}{'tr R':>8}{'te n':>6}{'te R':>8}{'te tot':>9}"
           f"{'te DD':>7}{'strk':>5}{'worst':>7}{'/mo':>6}")

    base_trades, base_stats, verdicts = {}, {}, defaultdict(dict)
    for mode in ("A", "C"):
        bc = dict(BASE, mode=mode)
        base_trades[mode] = portfolio(by_day, bc)
        b = base_stats[mode] = split_stats(base_trades[mode])
        title = ("A — as preregistered (backtest_recent bar semantics)" if mode == "A"
                 else "C — corrected bar order (cap-return fill bar, expiry in minutes)")
        print(f"\n=== MODE {title} ===")
        print("BASELINE B (live rules) · one position · net R per trade")
        print(hdr)
        print(line("B", b))
        for y in ("2024", "2025", "2026"):
            sy = b["years"][y]
            print(f"    test {y}: n {sy.get('n', 0)} · mean {sy.get('mean', float('nan')):+.3f} · total {sy.get('total', 0):+.1f}")
        for w, sw in b["windows"].items():
            print(f"    {w:<12} train {sw['train'].get('n', 0):>5} {sw['train'].get('mean', float('nan')):+.3f}"
                  f" · test {sw['test'].get('n', 0):>5} {sw['test'].get('mean', float('nan')):+.3f}")
        print("\nVARIANTS, one at a time against B")
        print(hdr + "  verdict")
        rows = []
        for group, name, over in VARIANTS + POSTHOC + ROSS_RETRACE:
            c = dict(bc, **over)
            tr = portfolio(by_day, c)
            s_ = split_stats(tr)
            lb = paired_lb(tr, base_trades[mode])
            scale = c["risk"] / 40.0
            v, checks = verdict(group, b, s_, lb, scale)
            verdicts[(group, name)][mode] = (v, lb, s_["test"].get("mean"))
            rows.append({"group": group, "variant": name, "stats": s_, "paired_lb": lb, "verdict": v, "checks": checks})
            yrs = " ".join(f"{s_['years'][y].get('mean', float('nan')):+.2f}" for y in ("2024", "2025", "2026"))
            print(line(f"{group} · {name}", s_) + f"  {v}  (lb {lb:+.3f} · yrs {yrs})", flush=True)
        res["modes"][mode] = {"baseline": b, "variants": rows}

    print("\n=== ADOPTION: a change must pass under BOTH A and C (addendum 2026-10-01b) ===")
    both = []
    for (group, name), d in verdicts.items():
        ok = all(d.get(m, ("keep B",))[0] == "ADOPT" for m in ("A", "C"))
        flag = "POST-HOC: contaminated, switch OFF until 200 prospective trades" if group == "post-hoc combo" else ""
        if any(d.get(m, ("keep B",))[0] == "ADOPT" for m in ("A", "C")):
            print(f"  {group} · {name:<46} A {d['A'][0]:<7}(lb {d['A'][1]:+.3f})  C {d['C'][0]:<7}(lb {d['C'][1]:+.3f})"
                  f"  -> {'PASSES BOTH' if ok else 'fails one'} {flag}")
        if ok:
            both.append((group, name))
    res["pass_both"] = both

    print("\n=== ROBUSTNESS (never deciding): bar readings CA and H, cost models, live-like intrabar entry gated at the break ===")
    focus = [("B", {})] + [(f"{g} · {n}", o) for g, n, o in VARIANTS + POSTHOC + ROSS_RETRACE
                            if any(verdicts[(g, n)].get(m, ("",))[0] == "ADOPT" for m in ("A", "C"))]
    settings = [("CA", "live", "close", "base"), ("H", "live", "close", "base"),
                ("A", "old", "close", "base"), ("C", "old", "close", "base"),
                ("A", "light", "close", "base"), ("C", "none", "close", "base"),
                ("C", "live", "prev", "intrabar")]
    print(f"  {'variant':<52}" + "".join(f"{m}/{cst}/{g[:4]}/{k[:5]:>6}".rjust(22) for m, cst, g, k in settings))
    ref = {}
    for st in settings:
        m, cst, g, k = st
        ref[st] = portfolio(by_day, dict(BASE, mode=m, costs=cst, gates=g, key=k))
    for name, over in focus:
        cells = []
        for st in settings:
            m, cst, g, k = st
            tr = ref[st] if not over else portfolio(by_day, dict(BASE, mode=m, costs=cst, gates=g, key=k, **over))
            s_ = split_stats(tr)
            lb = float("nan") if not over else paired_lb(tr, ref[st])
            cells.append(f"{s_['train'].get('mean', float('nan')):+.3f}/{s_['test'].get('mean', float('nan')):+.3f}"
                         + (f" {lb:+.3f}" if over else "       "))
            res["robustness"].append({"variant": name, "setting": st, "train": s_["train"].get("mean"),
                                      "test": s_["test"].get("mean"), "n_test": s_["test"].get("n"), "lb": lb})
        print(f"  {name:<52}" + "".join(c.rjust(22) for c in cells), flush=True)
    print("  cells: train mean / test mean net R per trade, then the paired lower bound against B in the same setting")
    Path(args.json).write_text(json.dumps(res, indent=1, default=str))
    print(f"\nwritten {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
