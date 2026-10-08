#!/usr/bin/env python3
"""F9 diagnostic — written after the addendum 2026-10-08 run, deciding nothing.

Is the portfolio's loss a data defect or the rule? Worst trades with their prices,
the overnight gap at entry, every signal without the 10-position cap, and the
signals by how far the stock had already run (126-day return, the ranking key).

    python3 scripts/daily_momentum_check.py
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import daily_momentum as M  # noqa: E402

OUT = ROOT / "research" / "paper-exercise" / "reports" / "daily_momentum_check_output.txt"


def main() -> int:
    lines = []

    def pr(x=""):
        print(x, flush=True); lines.append(x)
    np.seterr(all="ignore")
    data = {}
    for f in sorted(M.CACHE.glob("chunk_*.npz")) + sorted(M.CACHE.glob("delisted_*.npz")):
        z = np.load(f)
        for s in z.files:
            if s not in data:
                data[s] = M.prep(z[s])
    sig = []                                           # every signal, one open trade per symbol at a time
    for s, a in data.items():
        ok = (a["c"] >= M.MIN_PRICE) & (a["dv"] >= M.MIN_DVOL) & np.isfinite(a["s200"]) & np.isfinite(a["hi"])
        ok[:M.HISTORY - 1] = False
        busy = -1
        for i in np.nonzero(ok[:-1])[0]:
            if i <= busy or not (a["c"][i] >= a["hi"][i] and a["c"][i] > a["s50"][i] > a["s200"][i]):
                continue
            t = M.trade(a, int(i))
            if t is None:
                continue
            busy = int(np.searchsorted(a["d"], t["exit_d"]))
            t.update(sym=s, day=M.iso(a["d"][i]), ret=float(a["ret"][i]), gap=float(a["o"][i + 1] / a["c"][i] - 1),
                     R_pct=float(M.R_ATR * a["atr"][i] / a["o"][i + 1]))
            sig.append(t)
    pr("F9 diagnostic · after the addendum 2026-10-08 run · deciding nothing · gross and net R a trade")

    def line(name, ts):
        if not ts:
            pr(f"  {name:<34} n 0"); return
        pr(f"  {name:<34} n {len(ts):>6} · gross {np.mean([t['gross'] for t in ts]):+.3f} · net "
           f"{np.mean([t['net'] for t in ts]):+.3f} · win {np.mean([t['net'] > 0 for t in ts]):.0%} · "
           f"median R {np.median([t['R_pct'] for t in ts]):.1%} of price")
    pr("\n1. every signal, no position cap (one trade per symbol at a time)")
    for name, lo, hi in (("train 2017-2022", "2017", "2023"), ("2023", "2023", "2024"), ("holdout 2024-2026", "2024", "2027")):
        line(name, [t for t in sig if lo <= t["day"] < hi])
    pr("\n2. the same signals by the ranking key, 126-day return at the signal (the portfolio takes the top)")
    for lo, hi in ((-9, 0.25), (0.25, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 99)):
        for name, a_, b_ in (("train", "2017", "2023"), ("holdout", "2024", "2027")):
            line(f"{name:<8} 126-d return {lo:+.0%}..{hi:+.0%}".replace("-900%", "below").replace("+9900%", "up"),
                 [t for t in sig if a_ <= t["day"] < b_ and lo <= t["ret"] < hi])
    pr("\n3. by year, every signal")
    by = defaultdict(list)
    for t in sig:
        by[t["day"][:4]].append(t)
    for y in sorted(by):
        line(y, by[y])
    pr("\n4. data check — the overnight gap from the signal close to the entry open")
    g = np.array([t["gap"] for t in sig])
    pr(f"  median {np.median(g):+.2%} · |gap| > 20 %: {int((abs(g) > 0.2).sum())} of {len(g)} · > 50 %: {int((abs(g) > 0.5).sum())}")
    pr("\n5. the 12 worst trades without a cap (a data defect would show as an impossible gap or R)")
    for t in sorted(sig, key=lambda t: t["gross"])[:12]:
        pr(f"  {t['sym']:<6} {t['day']} · 126-d {t['ret']:+.0%} · gap {t['gap']:+.1%} · R {t['R_pct']:.1%} of price · "
           f"held {t['days']} d · gross {t['gross']:+.2f}")
    pr("\n6. the PORTFOLIO's trades (daily_momentum_output.json) whose holding window holds an overnight jump > 50 %")
    pr("   (feed defects: spin-offs adjusted the wrong way, acquired tickers stitched to a successor — and real crashes)")
    raw = {}
    for f in sorted(M.CACHE.glob("chunk_*.npz")) + sorted(M.CACHE.glob("delisted_*.npz")):
        z = np.load(f)
        for s in z.files:
            raw.setdefault(s, z[s])
    trades = __import__("json").loads(M.OUT.with_suffix(".json").read_text())["trades"]

    def jumpy(t):
        a = raw[t["sym"]]; i0, i1 = np.searchsorted(a[:, 0], t["entry_d"]), np.searchsorted(a[:, 0], t["exit_d"])
        g = a[i0 + 1:i1 + 1, 1] / a[i0:i1, 4]
        return bool((np.abs(g - 1) > 0.5).any())
    for name, lo, hi in (("train 2017-2022", "2017", "2023"), ("2023", "2023", "2024"), ("holdout 2024-2026", "2024", "2027")):
        ts = [t for t in trades if lo <= t["day"] < hi]
        bad, ok = [t for t in ts if jumpy(t)], [t for t in ts if not jumpy(t)]
        pr(f"  {name:<18} n {len(ts)} · net {np.mean([t['net'] for t in ts]):+.3f} · flagged {len(bad)} "
           f"(total {sum(t['net'] for t in bad):+.1f} R) · without them n {len(ok)} · gross "
           f"{np.mean([t['gross'] for t in ok]):+.3f} · net {np.mean([t['net'] for t in ok]):+.3f}")
        for t in sorted(bad, key=lambda t: t["net"]):
            pr(f"      {t['sym']:<6} {t['day']} · held {t['days']} d · net {t['net']:+.2f}")
    OUT.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
