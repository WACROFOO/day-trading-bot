"""Would a published Ross-style bot's rules help ours? Their rules, replayed on
OUR 20 exported days through the month study's own engine and cost model.

The rules are those of the flow image in "I automated Ross Cameron's small-cap
momentum rules into a bot. Looking for feedback on the flow" (r/Daytrading,
u/Necessary-Gas-1665, 2026-10-11) — see README.md for the list as read.

Engine (read-only reuse of scripts/backtest_recent.py): plans_for_day — the
desk's FirstPullbackDetector, the chart gates, A10 fills (a touch within 3
bars; a bar opening above trigger + max(1 c, 0.3 %) fills only if the tape
comes back to that cap), stops that a bar opens through fill at its open —
simulate (fixed 2R / trail 1R / break-even then 2R), entry_cap, and cost_r
with COST_MODEL = "live" ($40 risk, $2,000 cap, IBKR commissions, the edge
hunt's NBBO-calibrated spread proxy plus 1 c a side). The A10 fill is
re-implemented in the hook so their 2 % chase can be read beside it;
audit.py proves it identical to the engine's own on every plan.

Bars: the desk's own 1-minute bars exported per day (board_bars.csv.gz for
screener and board names, bars.csv for decision names), 04:00-12:00 ET.

Usage (from the repo root):  python3 research/reddit-bot-rules-2026-10-12/their_rules.py
"""
import collections
import csv
import gzip
import random
import statistics
import sys
from datetime import datetime, time as dtime
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import backtest_recent as E  # noqa: E402

DAILY = ROOT / "research" / "daily"
SEL_END = "2026-10-01"
ET = E.ET
REGIMES = {"bot": (dtime(7, 0), dtime(11, 20), dtime(11, 30)),
           "wide": (dtime(6, 0), dtime(11, 50), dtime(12, 0))}   # their 06:00 start; our bars stop at 12:00
OURS = ("price", "rising", "vwap", "ema9", "macd", "volume")


def read_csv(p):
    if not p.exists() or p.stat().st_size == 0:
        return []
    with p.open(newline="") as f:
        return list(csv.DictReader(f))


def fnum(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def universe():
    uni = {}
    for folder in sorted(p for p in DAILY.iterdir() if p.is_dir() and (p / "decisions.csv").exists()):
        day = uni.setdefault(folder.name, {})
        for src, fname in (("screener", "screener.csv"), ("board", "board.csv"), ("decision", "decisions.csv")):
            for r in read_csv(folder / fname):
                sym = (r.get("symbol") or "").strip().upper()
                if not sym:
                    continue
                e = day.setdefault(sym, {"prev": None})
                if e["prev"] is None:
                    if src == "decision":
                        last, chg = fnum(r.get("last")), fnum(r.get("change_pct"))
                        if last and chg is not None and chg > -99:
                            e["prev"] = last / (1 + chg / 100)
                    elif src == "screener":
                        px, gap = fnum(r.get("price")), fnum(r.get("gap_pct"))
                        if px and gap is not None and gap > -99:
                            e["prev"] = px / (1 + gap / 100)
    return uni


def bars_for_day(d):
    out = collections.defaultdict(dict)
    srcs = []
    bb = DAILY / d / "board_bars.csv.gz"
    if bb.exists():
        with gzip.open(bb, "rt", newline="") as fh:
            srcs.append(list(csv.DictReader(fh)))
    srcs.append(read_csv(DAILY / d / "bars.csv"))
    for rows in srcs:
        for r in rows:
            try:
                ts = datetime.fromisoformat(r["ts"].replace("Z", "+00:00")).astimezone(ET)
                o, h, l, c, v = (float(r[k]) for k in ("open", "high", "low", "close", "volume"))
            except (KeyError, TypeError, ValueError):
                continue
            out[r["symbol"].upper()].setdefault(ts, (ts, o, h, l, c, v))
    return {s: [m[k] for k in sorted(m)] for s, m in out.items()}


def sim_theirs(bars, entry, stop, fill, lock=True, spike=True):
    """Their MANAGE box on 1-min bars: 2R bracket; at +1.5R the stop locks
    +0.5R (only up); sell into a spike when price is >= +1R and rose 0.75R
    within ~60 s (previous bar's close as the 60-s-ago price). Stop tested
    first against the level in force before the bar, as E.simulate does."""
    rps = entry - stop
    level, tgt, ref = stop, entry + 2 * rps, fill
    for ts, o, h, l, c, v in bars:
        if ts.time() >= E.FLAT:
            return round((o - fill) / rps, 3), "flatten", ts
        if l <= level:
            return round((min(level, o) - fill) / rps, 3), ("stop" if level == stop else "lock"), ts
        if o >= tgt:
            return round((tgt - fill) / rps, 3), "target", ts
        if spike:
            trig = max(entry + rps, ref + 0.75 * rps)
            if trig < tgt and h >= trig:
                return round((max(o, trig) - fill) / rps, 3), "spike", ts
        if h >= tgt:
            return round((tgt - fill) / rps, 3), "target", ts
        if lock and h >= entry + 1.5 * rps:
            level = max(level, entry + 0.5 * rps)
        ref = c
    return round((bars[-1][4] - fill) / rps, 3), "close", bars[-1][0]


MARKETABLE = ("stop", "trail", "lock", "spike")


def variants(rec, ent):
    entry, stop = rec["entry"], rec["stop"]
    rps = entry - stop
    if rps <= 0:
        return None
    out = {"touch_k": int(round((ent[0][0] - rec["ts"]).total_seconds() / 60)) - 1}
    o_t = ent[0][1]
    cap = E.entry_cap(entry)
    if o_t > cap:                                    # A10: rests at the cap, fills only if the tape comes back
        back = next((k for k in range(0, min(len(ent), E.TTL_BARS)) if ent[k][3] <= cap), None)
        a10 = None if back is None else (cap, back)
    else:
        a10 = (max(o_t, entry), 0)
    chase2 = None if o_t > entry * 1.02 else (max(o_t, entry), 0)   # their chase guard: skip above +2 %
    for name, f in (("a10", a10), ("chase2", chase2)):
        if f is None:
            out[name] = None
            continue
        fill, k0 = f
        bars = ent[k0:]
        res = {}
        for v in ("fixed", "trail", "be"):
            res[v] = E.simulate(bars, entry, stop, v, fill=fill)
        for v, lk, sp in (("theirs", True, True), ("lock", True, False), ("spike", False, True)):
            res[v] = sim_theirs(bars, entry, stop, fill, lk, sp)
        for v, (r, why, t_out) in list(res.items()):
            cost = E.cost_r(entry, stop, why in MARKETABLE, pm=rec["pm"], dv5=rec["dv5"])
            res[v] = {"r": r, "why": why, "out": t_out, "net": round(r - cost, 3)}
        res["fill_t"] = bars[0][0]
        out[name] = res
    return out


def build(regime, uni):
    E.PM_START, E.CUTOFF, E.FLAT = REGIMES[regime]
    E.COST_MODEL = "live"
    plans, symdays = [], 0
    for d in sorted(uni):
        bars = bars_for_day(d)
        for sym in sorted(uni[d]):
            rows = [r for r in bars.get(sym, []) if dtime(4, 0) <= r[0].time() < dtime(16, 0)]
            if len(rows) < 40:
                continue
            symdays += 1
            run_hi, run_t, hi, ht = [], [], None, None
            for r in rows:
                if hi is None or r[2] > hi:
                    hi, ht = r[2], r[0]
                run_hi.append(hi)
                run_t.append(ht)
            idx = {r[0]: i for i, r in enumerate(rows)}
            extra = {}

            def hook(rec, ent, _f, _x=extra):
                _x[rec["ts"]] = variants(rec, ent)

            for p in E.plans_for_day(sym, rows, uni[d][sym]["prev"] or 0, desk_vwap=True, gap_miss=False, hook=hook):
                i = idx[p["ts"]]
                p["off_hod"] = (run_hi[i] - p["entry"]) / run_hi[i]
                p["hod_age"] = (p["ts"] - run_t[i]).total_seconds() / 60
                p["period"] = "sel" if d <= SEL_END else "hold"
                p["v"] = extra.get(p["ts"]) if p["touched"] else None
                plans.append(p)
    return plans, symdays


# ------------------------------------------------------------------ rule sets
def ours_mstudy(p):                 # the month study's "bot rules" reference line
    return not p["red"]


def ours_live(p):                   # the bot as it runs: + A13's 2 % stop floor
    return not p["red"] and p["stop_pct"] >= 2.0


def front(p):
    return p["off_hod"] <= 0.10 and p["hod_age"] <= 60


def stop30(p):
    return (p["entry"] - p["stop"]) <= 0.30 + 1e-9


def fresh(p):
    return p["v"] is not None and p["v"]["touch_k"] == 0


def theirs(p):                      # what their GATE can be read as on our plans (pillars not re-applied)
    return "price" not in p["red"] and "vwap" not in p["red"] and front(p) and stop30(p) and fresh(p)


def trades(plans, allowed, fillm="a10", ex="trail", period=None):
    out = []
    for p in plans:
        if period and p["period"] != period:
            continue
        if not p["touched"] or p["v"] is None or not allowed(p):
            continue
        t = p["v"].get(fillm)
        if t is None:
            continue
        out.append((p, t[ex]["net"], t[ex]["r"]))
    return out


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def boot_ci(tr, n=2000, seed=7):
    """90 % interval of the mean net R a trade, resampling DAYS."""
    by = collections.defaultdict(list)
    for p, net, _ in tr:
        by[p["day"]].append(net)
    days = list(by)
    if len(days) < 3:
        return (float("nan"), float("nan"))
    rnd = random.Random(seed)
    ms = []
    for _ in range(n):
        xs = []
        for _ in days:
            xs += by[rnd.choice(days)]
        ms.append(mean(xs))
    ms.sort()
    return ms[int(0.05 * n)], ms[int(0.95 * n)]


def line(name, plans, allowed, fillm="a10", ex="trail", ci=False):
    s = trades(plans, allowed, fillm, ex, "sel")
    h = trades(plans, allowed, fillm, ex, "hold")
    a = s + h
    gross = mean([g for _, _, g in a])
    extra = ""
    if ci:
        lo, hi = boot_ci(a)
        extra = f"  90% CI(all, by day) {lo:+.3f}..{hi:+.3f}"
    print(f"  {name:<46} sel {mean([x for _, x, _ in s]):+.3f} ({len(s):4d})  hold {mean([x for _, x, _ in h]):+.3f} "
          f"({len(h):3d})  all {mean([x for _, x, _ in a]):+.3f} ({len(a):4d})  gross {gross:+.3f}{extra}")
    return a


def after_loss_filter(plans, allowed, fillm, ex):
    """Plan-level 'done after a loss': drop a plan whose touch comes after an
    earlier allowed plan on the same symbol-day lost (net < 0) and exited."""
    keep = set()
    by = collections.defaultdict(list)
    for p in plans:
        if p["touched"] and p["v"] is not None and p["v"].get(fillm) is not None and allowed(p):
            by[(p["day"], p["sym"])].append(p)
    for key, ps in by.items():
        ps.sort(key=lambda q: q["v"][fillm]["fill_t"])
        lost_at = None
        for q in ps:
            t = q["v"][fillm]
            if lost_at is not None and t["fill_t"] >= lost_at:
                continue
            keep.add(id(q))
            if t[ex]["net"] < 0:
                lost_at = t[ex]["out"] if lost_at is None else min(lost_at, t[ex]["out"])
    return lambda p: id(p) in keep


def portfolio(plans, allowed, fillm="a10", ex="trail", after_loss=False, day_stop=None, cushion=False,
              ours_risk=False, quarter=False):
    """One position at a time, one per symbol, in fill order. ours_risk = the
    runner's RiskVeto (src/journal/risk.py Limits: -3 R a day, 3 losses in a
    row counting losses >= 0.25 R, 6 entries). Returns {period: (total
    full-size R, trades, days, days up)}."""
    by = collections.defaultdict(list)
    for p in plans:
        if p["touched"] and p["v"] is not None and p["v"].get(fillm) is not None and allowed(p):
            by[p["day"]].append(p)
    res = {}
    for day, ps in sorted(by.items()):
        free_at, lost, day_r, n, streak = None, set(), 0.0, 0, 0
        for p in sorted(ps, key=lambda q: q["v"][fillm]["fill_t"]):
            t = p["v"][fillm]
            if free_at is not None and t["fill_t"] < free_at:
                continue
            if after_loss and p["sym"] in lost:
                continue
            if day_stop is not None and day_r <= -day_stop:
                break
            if ours_risk and (day_r <= -3.0 or streak >= 3 or n >= 6):
                break
            size = (1.0 if day_r > 0 else 0.25) if cushion else (0.25 if quarter else 1.0)
            net = t[ex]["net"]
            day_r += size * net
            n += 1
            free_at = t[ex]["out"]
            if net <= -0.25:
                streak += 1
            elif net > 0.25:
                streak = 0
            if net < 0:
                lost.add(p["sym"])
        per = "sel" if day <= SEL_END else "hold"
        tot, cnt, nd, up = res.get(per, (0.0, 0, 0, 0))
        res[per] = (tot + day_r, cnt + n, nd + 1, up + (1 if day_r > 0 else 0))
    return res


def pline(name, plans, allowed, **kw):
    r = portfolio(plans, allowed, **kw)
    s, h = r.get("sel", (0, 0, 0, 0)), r.get("hold", (0, 0, 0, 0))
    per = lambda x: x[0] / x[1] if x[1] else float("nan")  # noqa: E731
    print(f"  {name:<52} sel {s[0]:+7.2f} R / {s[1]:3d} tr = {per(s):+.2f} ({s[3]}/{s[2]} days up)   "
          f"hold {h[0]:+6.2f} R / {h[1]:2d} tr = {per(h):+.2f} ({h[3]}/{h[2]} up)   total {s[0] + h[0]:+7.2f}")


def main():
    uni = universe()
    print(f"universe: {len(uni)} days, {sum(len(v) for v in uni.values())} symbol-days "
          f"({min(uni)}..{max(uni)}); selection <= {SEL_END}")
    P = {}
    for reg in REGIMES:
        P[reg], sd = build(reg, uni)
        t = sum(1 for p in P[reg] if p["touched"])
        print(f"  {reg}: {sd} symbol-days with >= 40 bars, {len(P[reg])} plans armed, {t} touched")
    bot = P["bot"]
    allp = lambda p: True  # noqa: E731

    print("\nA · REPLICATION of the month study (bot window, A10 fills, live costs), mean net R a trade (n)")
    print("    month study: L0 fixed -0.918 (1,046) · trail -1.124 · BE -1.006 ; bot rules trail sel -0.879 (119), hold -1.694 (31)")
    for ex in ("fixed", "trail", "be"):
        line(f"L0 every plan · {ex}", bot, allp, ex=ex)
    line("month-study bot rules (no A13) · trail", bot, ours_mstudy)
    print("    month study one-lever deltas on L0 fixed (sel): VWAP +0.202 · SW>=2 +0.293 · SW>=3 +0.376 · first plan -0.257")
    base = mean([x for _, x, _ in trades(bot, allp, ex="fixed", period="sel")])
    for name, f in (("VWAP", lambda p: "vwap" not in p["red"]), ("SW>=2", lambda p: p["stop_pct"] >= 2),
                    ("SW>=3", lambda p: p["stop_pct"] >= 3), ("first plan", lambda p: p["pb_index"] == 1)):
        m = mean([x for _, x, _ in trades(bot, f, ex="fixed", period="sel")])
        print(f"    here: {name:<10} {m - base:+.3f}")

    print("\nB · THEIR GATES, one at a time on L0 (bot window, A10 fills, fixed 2R) — delta vs L0, sel / hold")
    b_s = mean([x for _, x, _ in trades(bot, allp, ex="fixed", period="sel")])
    b_h = mean([x for _, x, _ in trades(bot, allp, ex="fixed", period="hold")])
    for name, f in (("front side (<=10% off HOD, HOD <=60 min old)", front), ("stop <= $0.30", stop30),
                    ("fresh signal (trigger on the next bar)", fresh), ("above VWAP", lambda p: "vwap" not in p["red"]),
                    ("OUR stop floor >= 2% (A13)", lambda p: p["stop_pct"] >= 2)):
        s = trades(bot, f, ex="fixed", period="sel")
        h = trades(bot, f, ex="fixed", period="hold")
        print(f"  {name:<46} sel {mean([x for _, x, _ in s]) - b_s:+.3f} ({len(s):4d})  hold {mean([x for _, x, _ in h]) - b_h:+.3f} ({len(h):3d})")

    print("\nB2 · EXITS on every fill (L0, bot window, A10) — mean net R a trade")
    for ex in ("fixed", "trail", "be", "theirs", "lock", "spike"):
        line(f"L0 · {ex}", bot, allp, ex=ex)

    print("\nC · ON TOP OF OUR LIVE RULES (G1 G4 VW E9 MC PV + A13 2% floor), bot window — mean net R a trade")
    line("ours as live · trail (A3)", bot, ours_live, ci=True)
    line("ours · fixed 2R", bot, ours_live, ex="fixed")
    line("ours · BE then 2R", bot, ours_live, ex="be")
    line("ours · THEIR exit (2R + lock + spike)", bot, ours_live, ex="theirs", ci=True)
    line("ours · lock only (2R + lock)", bot, ours_live, ex="lock")
    line("ours · spike only (2R + spike)", bot, ours_live, ex="spike")
    line("ours + front side · trail", bot, lambda p: ours_live(p) and front(p), ci=True)
    line("ours + stop <= $0.30 · trail", bot, lambda p: ours_live(p) and stop30(p))
    line("ours + fresh signal · trail", bot, lambda p: ours_live(p) and fresh(p))
    line("ours, their 2% chase fill · trail", bot, ours_live, fillm="chase2")
    al = after_loss_filter(bot, ours_live, "a10", "trail")
    line("ours + done after a loss (plan level) · trail", bot, lambda p: ours_live(p) and al(p), ci=True)

    print("\nD · THEIR RULE SET as far as it reads on our plans (G1, VWAP, front side, stop<=$0.30, fresh)")
    line("theirs · their fill (2% chase) · their exit", bot, theirs, fillm="chase2", ex="theirs", ci=True)
    line("theirs · their fill · fixed 2R", bot, theirs, fillm="chase2", ex="fixed")
    line("theirs, stop<=$0.30 swapped for our 2% floor · their exit", bot,
         lambda p: "price" not in p["red"] and "vwap" not in p["red"] and front(p) and fresh(p) and p["stop_pct"] >= 2,
         fillm="chase2", ex="theirs")

    print("\nE · PORTFOLIO, one position at a time (both bots), total net R in full-size R")
    pline("ours as live (RiskVeto -3R/3 losses/6 entries) · trail", bot, ours_live, ours_risk=True)
    pline("  same, no risk veto", bot, ours_live)
    pline("  + done after a loss", bot, ours_live, ours_risk=True, after_loss=True)
    pline("  + their daily stop -2R", bot, ours_live, ours_risk=True, day_stop=2.0)
    pline("  + cushion (25% until green)", bot, ours_live, ours_risk=True, cushion=True)
    pline("  constant quarter size (cushion's comparator)", bot, ours_live, ours_risk=True, quarter=True)
    pline("  exit: their 2R+lock+spike", bot, ours_live, ours_risk=True, ex="theirs")
    pline("  exit: 2R + lock (no spike)", bot, ours_live, ours_risk=True, ex="lock")
    pline("  exit: fixed 2R", bot, ours_live, ours_risk=True, ex="fixed")
    pline("  exit: break-even then 2R", bot, ours_live, ours_risk=True, ex="be")
    pline("  exit: fixed 2R + done after a loss", bot, ours_live, ours_risk=True, ex="fixed", after_loss=True)
    pline("theirs full: gates+chase+exit+after-loss+-2R+cushion", bot, theirs, fillm="chase2", ex="theirs",
          after_loss=True, day_stop=2.0, cushion=True)
    pline("theirs, flat size (no cushion)", bot, theirs, fillm="chase2", ex="theirs", after_loss=True, day_stop=2.0)

    print("\nF · THEIR WINDOW (arms from 06:00; our bars end 12:00, so 12:00-13:00 is not read)")
    wide = P["wide"]
    early = lambda p: p["ts"].time() < dtime(7, 0)  # noqa: E731
    line("ours as live, plans armed 06:00-07:00 · trail", wide, lambda p: ours_live(p) and early(p))
    line("ours as live, plans armed 11:20-11:50 · trail", wide, lambda p: ours_live(p) and p["ts"].time() >= dtime(11, 20))
    line("L0, plans armed 06:00-07:00 · fixed", wide, early, ex="fixed")
    line("L0, plans armed 07:00-09:30 · fixed", wide, lambda p: dtime(7, 0) <= p["ts"].time() < dtime(9, 30), ex="fixed")
    line("L0, plans armed 09:30-11:20 · fixed", wide, lambda p: dtime(9, 30) <= p["ts"].time() < dtime(11, 20), ex="fixed")

    print("\nG · exit reasons under their exit, ours as live (all periods)")
    c = collections.Counter(p["v"]["a10"]["theirs"]["why"] for p, _, _ in trades(bot, ours_live, ex="theirs"))
    print("  ", dict(c))


if __name__ == "__main__":
    main()
