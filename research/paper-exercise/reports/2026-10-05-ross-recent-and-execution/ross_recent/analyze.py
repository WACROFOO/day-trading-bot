"""Steps 2-5: locate each of Ross's June-July 2026 entries on the SIP tape and
measure our two setups around it.

  * 1-minute plan  scripts/rules_audit.plans_for_symbol_day on the cached SIP
                   1-minute bars; armed nearby = trigger bar start in
                   [his minute - 5 min, his minute]; gates = red list, fade,
                   stop %, spread ratio, RA.passes(p, RA.BASE); outcome mode C 'base'.
  * green-run S    scripts/green_run.minute_context + runup_micro._signals on
                   10-second bars from SIP prints (tick_replay.Fetcher.chunk)
                   over [his minute - 20 min, his minute + 60 min] clipped to
                   07:00-11:30 (the hours S was tested on); gates as
                   green_run.run_day (price 2-20, stop at 1-min low - 1c,
                   stop >= 2 %, stop >= 4x proxy spread); outcome
                   runup_micro._trade (A3 1 R trail every 5 s, flat 11:30), gross R.
"""
import csv
import json
import sys
from datetime import datetime, time as dtime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path("/home/user/day-trading-bot")
sys.path[:0] = [str(HERE), str(ROOT / "scripts"), str(ROOT / "src")]
import backtest_history as H  # noqa: E402
import green_run as G  # noqa: E402
import rules_audit as RA  # noqa: E402
import runup_micro as RM  # noqa: E402
import tick_replay as TR  # noqa: E402
import trades  # noqa: E402

ET = RA.E.ET
DAILY = json.loads((HERE / "daily.json").read_text())
# rows whose context gives a price the ticker must have printed (no entry price field)
SANITY_PX = {("iZ-mXl0ga3U", "00:03:16"): 5.50, ("iZ-mXl0ga3U", "00:04:07"): 5.50}
NEAR_PLAN_S = 300
S_BEFORE, S_AFTER = 180, 60
WIN_BEFORE, WIN_AFTER = 20 * 60, 60 * 60

_day_cache = {}


def bars_of(day, sym):
    if day not in _day_cache:
        _day_cache.clear()
        f = H.CACHE / f"{day}.json"
        _day_cache[day] = json.loads(f.read_text()) if f.exists() else {}
    raw = _day_cache[day].get(sym) or []
    return [r for r in H.to_rows(raw) if dtime(4, 0) <= r[0].time() < dtime(16, 0)]


def prev_close(sym, day):
    d = DAILY.get(sym) or {}
    prev = [k for k in d if k < day]
    if not prev or day not in d:
        return None, None, None
    pk = max(prev)
    raw = d[pk].get("raw")
    try:
        eq = d[pk]["split"] * d[day]["raw"] / d[day]["split"]
    except (KeyError, ZeroDivisionError, TypeError):
        eq = raw
    return raw, eq, pk


def hm(s):
    h, m = s.split(":")
    return dtime(int(h), int(m))


def parse_tspec(s):
    exact = approx = lo = hi = None
    if s.startswith("=") or s.startswith("~"):
        exact, approx = hm(s[1:6]), s[0] == "~"
    else:
        rest = s
        while rest:
            if rest[0] == ">":
                lo, rest = hm(rest[1:6]), rest[6:]
            elif rest[0] == "<":
                hi, rest = hm(rest[1:6]), rest[6:]
            else:
                break
    return exact, approx, lo, hi


def clusters(idx, rows, gap_min=10):
    """Separate visits to the price: (first, last) minute holding it, split where
    more than `gap_min` minutes pass without one."""
    out = []
    for k, i in enumerate(idx):
        if k == 0 or (rows[i][0] - rows[idx[k - 1]][0]).total_seconds() > gap_min * 60:
            out.append([rows[i][0], rows[i][0]])
        else:
            out[-1][1] = rows[i][0]
    return out


def locate(r, rows):
    """-> (index into rows | None, method, flag)"""
    if not rows:
        return None, "UNLOCATED", "no SIP bars for this ticker/day"
    sp = SANITY_PX.get((r["vid"], r["ts"]))
    if sp is not None and not any(b[3] <= sp <= b[2] for b in rows):
        return None, "TICKER_MISMATCH", f"context price {sp} never printed (day range {min(b[3] for b in rows):.2f}-{max(b[2] for b in rows):.2f})"
    exact, approx, lo, hi = parse_tspec(r["tspec"])
    px = r["px"]
    if px is not None and not any(b[3] <= px <= b[2] for b in rows):
        return None, "PRICE_NEVER_PRINTED", f"stated {px} never printed 04:00-16:00 (range {min(b[3] for b in rows):.2f}-{max(b[2] for b in rows):.2f})"
    if exact is not None:
        tgt = datetime.combine(rows[0][0].date(), exact, ET)
        near = [i for i, b in enumerate(rows) if abs((b[0] - tgt).total_seconds()) <= 120]
        if not near:
            return None, "UNLOCATED", f"no print within 2 min of stated {exact.strftime('%H:%M')}"
        i = min(near, key=lambda k: (abs((rows[k][0] - tgt).total_seconds()), rows[k][0]))
        meth = "time~" if approx else "time"
        if px is not None and not (rows[i][3] <= px <= rows[i][2]):
            cand = [k for k, b in enumerate(rows) if abs((b[0] - tgt).total_seconds()) <= 900 and b[3] <= px <= b[2]]
            if cand:
                k = min(cand, key=lambda k: abs((rows[k][0] - tgt).total_seconds()))
                d = int((rows[k][0] - tgt).total_seconds() // 60)
                return k, meth + "+price", f"stated price {px} not in the {exact.strftime('%H:%M')} bar; nearest bar holding it {d:+d} min"
            return i, meth, f"stated price {px} not within 15 min of the stated time"
        return i, meth, ""
    if px is not None:
        lo_t, hi_t = max(lo or dtime(4, 0), dtime(4, 0)), min(hi or dtime(12, 0), dtime(12, 0))
        idx = [k for k, b in enumerate(rows) if lo_t <= b[0].time() < hi_t and b[3] <= px <= b[2]]
        if not idx:
            return None, "UNLOCATED", f"stated {px} printed, but not inside {lo_t.strftime('%H:%M')}-{hi_t.strftime('%H:%M')}"
        cl = clusters(idx, rows)
        span = int((cl[0][1] - cl[0][0]).total_seconds() // 60)
        meth = "price" + ("+bounds" if (lo or hi) else "")
        if len(cl) > 1:
            return idx[0], meth, (f"AMBIGUOUS: price visited {len(cl)} times >10 min apart inside the window, at "
                                  + " ".join(c[0].strftime("%H:%M") for c in cl[:8]))
        if span > 5:
            return idx[0], meth, f"AMBIGUOUS: price held in range {span} min ({cl[0][0]:%H:%M}-{cl[0][1]:%H:%M})"
        return idx[0], meth, ""
    return None, "UNLOCATED", "no stated entry price or clock time"


def context(rows, i, ref, pc_eq):
    pre = rows[:i] or rows[:1]
    v = np.array([b[5] for b in pre]); tp = np.array([(b[2] + b[3] + b[4]) / 3 for b in pre])
    vwap = float((v * tp).sum() / v.sum()) if v.sum() > 0 else float(tp[-1])
    hod = max(b[2] for b in pre)
    out = dict(vwap=round(vwap, 4), above_vwap=ref > vwap, hod_prev=hod,
               dist_hod_pct=round((hod - ref) / hod * 100, 2),
               session="pre-market" if rows[i][0].time() < dtime(9, 30) else "regular")
    if pc_eq:
        out["gain_pct"] = round((ref / pc_eq - 1) * 100, 1)
        f10 = next((b[0] for b in rows if b[2] >= 1.10 * pc_eq), None)
        out["min_since_10pct"] = None if f10 is None else int((rows[i][0] - f10).total_seconds() // 60)
    return out


def newhigh_map(rows):
    """{bar start epoch: True if the bar's high exceeds every earlier high of the day}"""
    out, hi = {}, None
    for b in rows:
        out[int(b[0].timestamp())] = hi is None or b[2] > hi
        hi = b[2] if hi is None else max(hi, b[2])
    return out


# ------------------------------------------------------------------ 1-minute plans
_plans = {}


def plans_of(day, sym, rows, pc):
    k = (day, sym)
    if k not in _plans:
        _plans[k] = RA.plans_for_symbol_day(sym, day, rows, pc or rows[0][1]) if len(rows) >= 2 else []
    return _plans[k]


def plan_near(plans, E):
    near = [p for p in plans if E - NEAR_PLAN_S <= p["arm"] <= E]
    if not near:
        return None, 0
    ok = [p for p in near if RA.passes(p, RA.BASE)]
    return (ok[-1] if ok else near[-1]), len(near)


def plan_rate(plans, E, nh):
    """Chance that a random minute in the same 80-minute window (07:00-11:30) has a plan armed in its 5
    minutes before: over every minute, and over minutes matched to his on 'new high of day or not'."""
    lo, hi = E - WIN_BEFORE, E + WIN_AFTER
    arms = [p["arm"] for p in plans]
    arms_ok = [p["arm"] for p in plans if RA.passes(p, RA.BASE)]
    grid = [t for t in range(lo + NEAR_PLAN_S, hi, 60)
            if dtime(7, 0) <= datetime.fromtimestamp(t, ET).time() < dtime(11, 30) and t in nh]
    if not grid:
        return None, None, None
    f = lambda arr, g: float(np.mean([any(t - NEAR_PLAN_S <= a <= t for a in arr) for t in g])) if g else None  # noqa: E731
    gm = [t for t in grid if nh[t] == nh.get(E)]
    r = lambda v: None if v is None else round(v, 3)  # noqa: E731
    return r(f(arms, grid)), r(f(arms_ok, grid)), r(f(arms_ok, gm))


# ------------------------------------------------------------------ green-run S
FX = None
_ctx = {}


def prints(sym, day, a, b):
    global FX
    if FX is None:
        FX = RM._fetcher()
    day0 = TR.day_open(day)
    T, P = [], []
    for k in range((a - day0) // TR.CHUNK_S, (b - 1 - day0) // TR.CHUNK_S + 1):
        t, p = FX.chunk(sym, day, int(k), day0)
        T.append(t); P.append(np.round(np.asarray(p, dtype=np.float64), 4))
    t, p = np.concatenate(T), np.concatenate(P)
    m = (t >= a * 1000) & (t < b * 1000)
    return t[m], p[m]


def s_window(day, E):
    a = max(E - WIN_BEFORE, TR.at_et(day, "07:00"))
    b = min(E + WIN_AFTER, TR.at_et(day, "11:30"))
    return a, b


def green_run(day, sym, E, nh=None):
    a, b = s_window(day, E)
    if b - a < 600:
        return dict(s_status="outside 07:00-11:30")
    k = (day, sym)
    if k not in _ctx:
        _ctx[k] = G.minute_context(day, sym)
    ctx = _ctx[k]
    if not ctx:
        return dict(s_status="no 1-min context")
    t, p = prints(sym, day, a, b)
    if len(t) < 10:
        return dict(s_status="no prints")
    bars = RM._bars10(t, p)
    armed = lambda ts: bool((G._ctx_at(ctx, ts) or {}).get("ok"))  # noqa: E731
    sigs = []
    for t_arm, entry, stop10 in RM._signals(bars, armed, None, False):
        bb = G._ctx_at(ctx, t_arm)
        stop = round(bb["low"] - 0.01, 4)
        why = []
        if not (2.0 <= entry <= 20.0):
            why.append("price")
        if stop >= entry:
            why.append("stop>=entry")
        else:
            sp = (entry - stop) / entry * 100
            pm = datetime.fromtimestamp(t_arm, ET).strftime("%H:%M") < "09:30"
            spread = RA.PROXY.spread(entry, pm, bb["dv5"])
            if sp < G.STOP_FLOOR_PCT:
                why.append("stop<2%")
            if spread > 0 and (entry - stop) / spread < G.SPREAD_K:
                why.append("stop<4x spread")
        sigs.append(dict(t=t_arm, entry=entry, stop=stop, why=why))
    fires = [s for s in sigs if not s["why"]]
    hours = (b - a) / 3600
    near = [s for s in fires if E - S_BEFORE <= s["t"] <= E + S_AFTER]
    near_raw = [s for s in sigs if E - S_BEFORE <= s["t"] <= E + S_AFTER]
    grid = list(range(a + S_BEFORE, b - S_AFTER, 10))
    pch = float(np.mean([any(g - S_BEFORE <= s["t"] <= g + S_AFTER for s in fires) for g in grid])) if grid else None
    gm = [t for t in nh if a + S_BEFORE <= t < b - S_AFTER and nh[t] == nh.get(E)] if nh else []
    pm_ = float(np.mean([any(g - S_BEFORE <= s["t"] <= g + S_AFTER for s in fires) for g in gm])) if gm else None
    out = dict(s_status="ok", s_p_chance_matched=None if pm_ is None else round(pm_, 3), s_matched_n=len(gm), s_window=f"{datetime.fromtimestamp(a, ET):%H:%M}-{datetime.fromtimestamp(b, ET):%H:%M}",
               s_signals_raw=len(sigs), s_fires=len(fires), s_fires_per_hr=round(len(fires) / hours, 2),
               s_p_chance=None if pch is None else round(pch, 3), s_near=bool(near),
               s_near_raw_only=bool(near_raw) and not near,
               s_near_raw_why=";".join(sorted({w for s in near_raw for w in s["why"]})) if near_raw and not near else "",
               s_fires_before=sum(1 for s in fires if E - WIN_BEFORE <= s["t"] < E - S_BEFORE))
    flat = TR.at_et(day, "11:30")
    for s in near:
        x = RM._trade(t, p, s["entry"], s["stop"], s["t"], flat, RM.TTL_ENTRY_S)
        if x and x["how"] == "end":
            t2, p2 = prints(sym, day, a, flat)
            x = RM._trade(t2, p2, s["entry"], s["stop"], s["t"], flat, RM.TTL_ENTRY_S)
        if x:
            out.update(s_t=f"{datetime.fromtimestamp(s['t'], ET):%H:%M:%S}", s_entry=s["entry"], s_stop=s["stop"],
                       s_stop_pct=round((s["entry"] - s["stop"]) / s["entry"] * 100, 2), s_fill=round(x["fill"], 4),
                       s_exit=round(x["exit"], 4), s_how=x["how"], s_R=round(x["r"], 3),
                       s_hold_s=round((x["t_out"] - x["t_in"]) / 1000))
            break
    else:
        if near:
            s = near[0]
            out.update(s_t=f"{datetime.fromtimestamp(s['t'], ET):%H:%M:%S}", s_entry=s["entry"], s_stop=s["stop"],
                       s_how="unfilled")
    return out


# ------------------------------------------------------------------ main
# Sensitivity only (never in the main counts): CA8i4Rc2bUY was uploaded 2026-07-24 but its ZCMD 5.50 and
# EHGO 3.00 never printed that day; both printed 2026-07-23, the day Ts7C0flv-1g recaps a main-account
# ZCMD entry and an EHGO entry. Hypothesis: the video recaps 07-23.
ALT_DATE = {("CA8i4Rc2bUY", "00:02:59"): "2026-07-23", ("CA8i4Rc2bUY", "00:05:20"): "2026-07-23"}


def main():
    out = []
    rows_in = trades.rows()
    for r in list(rows_in):
        if (r["vid"], r["ts"]) in ALT_DATE:
            rows_in.append(dict(r, date=ALT_DATE[(r["vid"], r["ts"])], alt=True))
    for r in rows_in:
        rec = {k: r[k] for k in ("vid", "ts", "date", "raw_ticker", "acct", "outcome", "px", "t_text", "exit",
                                 "shares", "pnl", "setup", "conf")}
        rec["sym"] = ""
        rec["alt_date"] = bool(r.get("alt"))
        if not r["cands"]:
            rec.update(status="NO_TICKER", flag="no ticker named")
            out.append(rec); continue
        rows, sym = [], r["cands"][0]
        for s in r["cands"]:
            rows = bars_of(r["date"], s)
            if rows:
                sym = s
                break
        rec["sym"] = sym
        i, meth, flag = locate(r, rows)
        rec.update(status=meth if i is not None else meth, flag=flag)
        if i is None:
            out.append(rec); continue
        rec["status"] = "LOCATED_ALT_DATE" if r.get("alt") else "LOCATED"
        rec["loc_method"] = meth
        rec["tier"] = ("A" if meth.startswith("time") else ("C" if flag.startswith("AMBIGUOUS") else "B"))
        E = int(rows[i][0].timestamp())
        rec["entry_min"] = rows[i][0].strftime("%H:%M")
        rec["bars_before"] = i                      # 1-min bars printed since 04:00 before his minute
        rec["first_bar"] = rows[0][0].strftime("%H:%M")
        rec["bar"] = f"{rows[i][1]:.4g}/{rows[i][2]:.4g}/{rows[i][3]:.4g}/{rows[i][4]:.4g}"
        pc_raw, pc_eq, pk = prev_close(sym, r["date"])
        rec["prev_close"] = None if pc_eq is None else round(pc_eq, 4)
        if pc_raw and pc_eq and abs(pc_raw / pc_eq - 1) > 0.02:
            rec["flag"] = (rec["flag"] + "; " if rec["flag"] else "") + f"split between {pk} and session (raw prev close {pc_raw}, split-equivalent {pc_eq:.4f})"
        ref = r["px"] if r["px"] is not None else rows[i][1]
        rec["ref_px"] = ref
        rec.update(context(rows, i, ref, pc_eq))
        plans = plans_of(r["date"], sym, rows, pc_eq)
        p, n = plan_near(plans, E)
        rec["plans_day"] = len(plans)
        rec["plans_day_pass"] = sum(1 for q in plans if RA.passes(q, RA.BASE))
        rec["plan_near_n"] = n
        rec["plan_armed"] = p is not None
        nh = newhigh_map(rows)
        rec["new_high_minute"] = nh.get(E)
        rec["plan_rate_any"], rec["plan_rate_pass"], rec["plan_rate_pass_matched"] = plan_rate(plans, E, nh)
        if p is not None:
            o = p["out"].get(("C", "base"))
            rec.update(plan_t=p["t"], plan_entry=p["entry"], plan_stop=p["stop"], plan_red="|".join(p["red"]),
                       plan_fade=round(p["fade"], 1), plan_stop_pct=round(p["stop_pct"], 2),
                       plan_spread_ratio=round(p["spread_ratio"], 2), plan_pass=RA.passes(p, RA.BASE),
                       plan_R_C=None if o is None else o[2], plan_filled=o is not None)
        try:
            rec.update(green_run(r["date"], sym, E, nh))
        except Exception as exc:  # noqa: BLE001
            rec["s_status"] = f"error {exc}"[:120]
        print(r["date"], sym, rec["entry_min"], rec["loc_method"], "plan", rec.get("plan_armed"), rec.get("plan_pass"),
              "S", rec.get("s_status"), rec.get("s_near"), rec.get("s_R"), flush=True)
        out.append(rec)
    keys = []
    for rec in out:
        for k in rec:
            if k not in keys:
                keys.append(k)
    with open(HERE / "ledger.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for rec in out:
            w.writerow(rec)
    (HERE / "ledger.json").write_text(json.dumps(out, indent=0, default=str))
    print("rows", len(out), "located", sum(1 for x in out if x["status"] == "LOCATED"), "alt", sum(1 for x in out if x["status"] == "LOCATED_ALT_DATE"))


if __name__ == "__main__":
    main()
