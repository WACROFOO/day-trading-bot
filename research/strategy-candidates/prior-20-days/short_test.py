"""Shorting the momentum names instead of buying them — a first read on OUR
20 exported days, through the same bars, universe, split and cost model as
research/reddit-bot-rules-2026-10-12/their_rules.py.

Run in the chat of 2026-10-12, before the candidate preregistration; kept
here because research/strategy-candidates/ records every combination tried.
20 sessions, 04:00-12:00 bars: a first look, not evidence.

Variants fixed BEFORE the first run (no tuning on this month):
  A  MIRROR      every plan our detector arms: SELL at its trigger as the price
                 trades up through it; stop = trigger + the long plan's risk;
                 also on the plans our live rules allow.
  B  BACK SIDE   the first 1-min close below VWAP (04:00-anchored) after trading
                 above it, the high of day >= 15 min old, the name still >= 10 %
                 over the previous close; sell the next bar's open; stop = the
                 highest high of the last 5 bars + 1 c; risk >= 1 % of price;
                 one per symbol-day.
  C  EXTENSION   the first bar closing >= 20 % above VWAP whose low breaks the
                 previous bar's low; sell the next bar's open; stop = the high of
                 day + 1 c; risk 1-15 % of price; one per symbol-day.
  T  TIME FADE   sell 09:30's open, buy back 11:30's open, no stop — the base
                 rate, in % of price, gross and after one round-trip spread.
Exits: fixed 2R, trail 1R, flat 11:30 (open of the 11:30 bar). Entries
07:00-11:20. Stop first on a tie (conservative); a bar opening through the stop
fills at its open (a halt, a gap). Costs: backtest_recent.cost_r "live", mirrored
for a short. NOT modelled: borrow fees, locate availability (many low floats
cannot be shorted at all), the short-sale restriction, margin.

Usage (from the repo root):
    python3 research/strategy-candidates/prior-20-days/short_test.py
"""
import collections
import random
import sys
from datetime import time as dtime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "reddit-bot-rules-2026-10-12"))
import their_rules as T  # noqa: E402  (the repo root is its parents[2])

E = T.E
FLAT = dtime(11, 30)
WIN_A, WIN_B = dtime(7, 0), dtime(11, 20)


def sim_short(bars, entry, stop, exit_):
    """Short from `entry`; bars from the fill bar on. Returns (R, why)."""
    rps = stop - entry
    level, tgt, lo = stop, entry - 2 * rps, entry
    for ts, o, h, l, c, v in bars:
        if ts.time() >= FLAT:
            return (entry - o) / rps, "flatten"
        if h >= level:
            px = max(level, o)
            return (entry - px) / rps, ("stop" if level == stop else "trail")
        if exit_ == "fixed" and l <= tgt:
            return 2.0, "target"                         # at the target, as the long side is scored
        lo = min(lo, l)
        if exit_ == "trail":
            level = min(level, lo + rps)
    return (entry - bars[-1][4]) / rps, "close"


def short_cost(entry, stop, why, pm, dv5):
    # the same frictions as a long of the same size and risk distance
    return E.cost_r(entry, entry - (stop - entry), why in ("stop", "trail"), pm=pm, dv5=dv5)


def vwap_series(rows):
    out, pv, vv = [], 0.0, 0.0
    for ts, o, h, l, c, v in rows:
        pv += (h + l + c) / 3 * v
        vv += v
        out.append(pv / vv if vv else c)
    return out


def main():
    uni = T.universe()
    E.PM_START, E.CUTOFF, E.FLAT = WIN_A, WIN_B, FLAT
    E.COST_MODEL = "live"
    E.cost_r(5.0, 4.9, False)                    # loads the spread proxy before the time fade reads it
    res = collections.defaultdict(list)          # (variant, exit) -> [(period, day, net, gross, why)]
    time_fade = []
    for d in sorted(uni):
        bars = T.bars_for_day(d)
        period = "sel" if d <= T.SEL_END else "hold"
        for sym in sorted(uni[d]):
            rows = [r for r in bars.get(sym, []) if dtime(4, 0) <= r[0].time() < dtime(16, 0)]
            if len(rows) < 40:
                continue
            pc = uni[d][sym]["prev"]
            vw = vwap_series(rows)

            # A · mirror of our detector's plans
            for p in E.plans_for_day(sym, rows, pc or 0, desk_vwap=True, gap_miss=False):
                if not p["touched"]:
                    continue
                i = next(k for k, r in enumerate(rows) if r[0] == p["ts"])
                fwd = rows[i + 1:]
                k = next((j for j, b in enumerate(fwd[:E.TTL_BARS]) if b[2] >= p["entry"]), None)
                if k is None:
                    continue
                entry = max(p["entry"], fwd[k][1])          # sold as it trades up through the trigger
                stop = entry + (p["entry"] - p["stop"])
                dv5 = p["dv5"]
                for ex in ("fixed", "trail"):
                    r, why = sim_short(fwd[k:], entry, stop, ex)
                    net = r - short_cost(entry, stop, why, p["pm"], dv5)
                    res[("A mirror · every plan", ex)].append((period, d, net, r, why))
                    if T.ours_live(p):
                        res[("A mirror · our live plans", ex)].append((period, d, net, r, why))

            # B · back side: VWAP lost after the high of day
            hod, hod_t, above = None, None, False
            for i, (ts, o, h, l, c, v) in enumerate(rows):
                if hod is None or h > hod:
                    hod, hod_t = h, ts
                if c > vw[i]:
                    above = True
                    continue
                if not (WIN_A <= ts.time() < WIN_B) or not above or i + 1 >= len(rows):
                    continue
                if (ts - hod_t).total_seconds() < 15 * 60 or not pc or c < 1.10 * pc:
                    continue
                entry = rows[i + 1][1]
                stop = max(r[2] for r in rows[max(0, i - 4):i + 1]) + 0.01
                if stop - entry < 0.01 * entry:
                    break
                dv5 = sum(r[4] * r[5] for r in rows[max(0, i - 4):i + 1])
                for ex in ("fixed", "trail"):
                    r, why = sim_short(rows[i + 1:], entry, stop, ex)
                    net = r - short_cost(entry, stop, why, rows[i + 1][0].time() < E.RTH_START, dv5)
                    res[("B back side · VWAP lost", ex)].append((period, d, net, r, why))
                break

            # C · fade the extension
            hod = None
            for i, (ts, o, h, l, c, v) in enumerate(rows):
                hod = h if hod is None else max(hod, h)
                if i == 0 or not (WIN_A <= ts.time() < WIN_B) or i + 1 >= len(rows):
                    continue
                if c < 1.20 * vw[i] or l >= rows[i - 1][3]:
                    continue
                entry, stop = rows[i + 1][1], hod + 0.01
                risk = stop - entry
                if not (0.01 * entry <= risk <= 0.15 * entry):
                    break
                dv5 = sum(r[4] * r[5] for r in rows[max(0, i - 4):i + 1])
                for ex in ("fixed", "trail"):
                    r, why = sim_short(rows[i + 1:], entry, stop, ex)
                    net = r - short_cost(entry, stop, why, rows[i + 1][0].time() < E.RTH_START, dv5)
                    res[("C extension · 20 % over VWAP", ex)].append((period, d, net, r, why))
                break

            # T · time fade, % of price
            o930 = next((r for r in rows if r[0].time() >= dtime(9, 30)), None)
            o1130 = next((r for r in rows if r[0].time() >= FLAT), None)
            if o930 and o1130 and pc and o930[1] >= 1.10 * pc:
                gross = (o930[1] - o1130[1]) / o930[1] * 100
                spread = E._PROXY.spread(o930[1], False, 100_000.0) if E._PROXY else 0.02
                time_fade.append((period, gross, gross - (spread + 0.02) / o930[1] * 100))

    print("SHORTS on the 20 exported days · mean R a trade, net of the live cost model (gross in brackets)")
    print("  borrow, locate, SSR and margin are NOT in these numbers: real shorts only do worse\n")
    for (name, ex), xs in sorted(res.items()):
        s = [x for x in xs if x[0] == "sel"]; h = [x for x in xs if x[0] == "hold"]
        m = lambda ys, k: sum(y[k] for y in ys) / len(ys) if ys else float("nan")  # noqa: E731
        worst = min(x[3] for x in xs)
        thru = sum(1 for x in xs if x[3] < -1.0 - 1e-9)
        wins = sum(1 for x in xs if x[2] > 0)
        print(f"  {name:<30} {ex:<5}  sel {m(s, 2):+.3f} ({m(s, 3):+.3f}) n={len(s):4d}   "
              f"hold {m(h, 2):+.3f} ({m(h, 3):+.3f}) n={len(h):3d}   win {wins}/{len(xs)}   "
              f"worst {worst:+.2f} R · {thru} lost more than 1 R")
    print("\n  T · sell the 09:30 open, buy the 11:30 open, gappers >= 10 %, % of price")
    for per in ("sel", "hold"):
        ys = [x for x in time_fade if x[0] == per]
        if ys:
            g = sorted(y[1] for y in ys)
            print(f"    {per:<4} n={len(ys):3d}  mean {sum(g) / len(g):+.2f} % gross · {sum(y[2] for y in ys) / len(ys):+.2f} % "
                  f"after one spread · median {g[len(g) // 2]:+.2f} % · worst {g[0]:+.2f} % · "
                  f"fell {sum(1 for x in g if x > 0)}/{len(g)}")
    print("\n  for scale, the long bot on the same days (results.txt §C): ours as live -0.285 / -0.891 R a trade")


if __name__ == "__main__":
    random.seed(7)
    main()
