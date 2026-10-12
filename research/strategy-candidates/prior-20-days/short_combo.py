"""The owner's short combination, read once on OUR 20 exported days — the same
bars, universe, split and cost model as short_test.py / their_rules.py.

Conditions, fixed BEFORE the first run, each read at the CLOSE of a 1-min bar,
causally (nothing after that bar):
  VW   below VWAP           close < VWAP (04:00-anchored, typical price x volume)
  MC   MACD turning down    MACD 12/26/9 histogram < 0 now, >= 0 within the 3 bars before
  HD   high of day failed   the high of day was set 10-60 min ago (no new high since)
  HV   high-volume red      a red bar on > 2x the day's average 1-min volume so far
                            (scripts/tape.py's gatekeeper, applied to all bars so far)
  DP   too deep a pullback  close more than 50 % of the way down from the high of day
                            to the low before it
  L2   big sell orders      NOT TESTABLE: no historical book exists here
Trade: sell the next bar's open; stop = the highest high of the last 5 bars + 1 c,
risk 1-15 % of price (else that signal is skipped); the first valid signal per
symbol-day; entries 07:00-11:20; fixed 2R or trail 1R; flat 11:30. Costs: the
live model, mirrored for a short. NOT modelled: borrow, locate, SSR, margin.
Read: ALL five, each four (one left out), each one alone.

Run in the chat of 2026-10-12, before the candidate preregistration; kept
here because research/strategy-candidates/ records every combination tried.

Usage (from the repo root):
    python3 research/strategy-candidates/prior-20-days/short_combo.py
"""
import collections
import sys
from datetime import time as dtime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "reddit-bot-rules-2026-10-12"))
import their_rules as T  # noqa: E402
from short_test import FLAT, WIN_A, WIN_B, short_cost, sim_short, vwap_series  # noqa: E402

E = T.E
CONDS = ("VW", "MC", "HD", "HV", "DP")


def ema_step(prev, x, n):
    k = 2.0 / (n + 1)
    return x if prev is None else x * k + prev * (1 - k)


def flags_by_bar(rows):
    """[{cond: bool}] per bar, causal."""
    vw = vwap_series(rows)
    out = []
    e12 = e26 = sig = None
    hist_hist = []
    hod = hod_t = None
    lows_before_hod = []
    day_low_before = None
    vol_sum = 0.0
    for i, (ts, o, h, l, c, v) in enumerate(rows):
        vol_sum += v
        avg_v = vol_sum / (i + 1)
        e12, e26 = ema_step(e12, c, 12), ema_step(e26, c, 26)
        line = e12 - e26
        sig = ema_step(sig, line, 9) if i >= 25 else None
        hist = (line - sig) if sig is not None else None
        hist_hist.append(hist)
        if hod is None or h > hod:
            hod, hod_t = h, ts
            day_low_before = min([r[3] for r in rows[:i + 1]])
        age = (ts - hod_t).total_seconds() / 60
        prev3 = [x for x in hist_hist[-4:-1] if x is not None]
        f = {
            "VW": c < vw[i],
            "MC": hist is not None and hist < 0 and bool(prev3) and max(prev3) >= 0,
            "HD": 10 <= age <= 60,
            "HV": c < o and avg_v > 0 and v > 2 * avg_v,
            "DP": hod is not None and day_low_before is not None and hod > day_low_before
                  and (hod - c) / (hod - day_low_before) > 0.5,
        }
        out.append(f)
    return out


def main():
    uni = T.universe()
    E.PM_START, E.CUTOFF, E.FLAT = WIN_A, WIN_B, FLAT
    E.COST_MODEL = "live"
    E.cost_r(5.0, 4.9, False)
    sets = {"ALL five": CONDS}
    for c in CONDS:
        sets["all but " + c] = tuple(x for x in CONDS if x != c)
    for c in CONDS:
        sets[c + " alone"] = (c,)
    res = collections.defaultdict(list)
    for d in sorted(uni):
        bars = T.bars_for_day(d)
        period = "sel" if d <= T.SEL_END else "hold"
        for sym in sorted(uni[d]):
            rows = [r for r in bars.get(sym, []) if dtime(4, 0) <= r[0].time() < dtime(16, 0)]
            if len(rows) < 40:
                continue
            fl = flags_by_bar(rows)
            for name, need in sets.items():
                for i in range(len(rows) - 1):
                    if not (WIN_A <= rows[i][0].time() < WIN_B):
                        continue
                    if not all(fl[i][c] for c in need):
                        continue
                    entry = rows[i + 1][1]
                    stop = max(r[2] for r in rows[max(0, i - 4):i + 1]) + 0.01
                    risk = stop - entry
                    if not (0.01 * entry <= risk <= 0.15 * entry):
                        continue
                    dv5 = sum(r[4] * r[5] for r in rows[max(0, i - 4):i + 1])
                    pm = rows[i + 1][0].time() < E.RTH_START
                    for ex in ("fixed", "trail"):
                        r, why = sim_short(rows[i + 1:], entry, stop, ex)
                        res[(name, ex)].append((period, d, r - short_cost(entry, stop, why, pm, dv5), r))
                    break
    print("THE OWNER'S SHORT COMBINATION on the 20 exported days · mean R a trade net (gross)")
    print("  in-sample, before borrow / locate / SSR; Level 2 not testable\n")
    m = lambda ys, k: sum(y[k] for y in ys) / len(ys) if ys else float("nan")  # noqa: E731
    for name in sets:
        for ex in ("fixed", "trail"):
            xs = res.get((name, ex), [])
            s = [x for x in xs if x[0] == "sel"]; h = [x for x in xs if x[0] == "hold"]
            both = (m(s, 2) > 0 and m(h, 2) > 0) if s and h else False
            print(f"  {name:<14} {ex:<5}  sel {m(s, 2):+.3f} ({m(s, 3):+.3f}) n={len(s):4d}   "
                  f"hold {m(h, 2):+.3f} ({m(h, 3):+.3f}) n={len(h):3d}   days {len({x[1] for x in xs}):2d}"
                  + ("   <- positive net in both" if both else ""))


if __name__ == "__main__":
    main()
