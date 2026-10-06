#!/usr/bin/env python3
"""D1 no blackout · D2 one-bar impulse · D12 both · W4 04:00 start (addendum 2026-10-06d).

Plans rebuilt with the same code for B and every variant on the 2,608-session
cache, outcomes in bar readings A and C (`rules_audit` fill, exit, costs,
portfolio). Decision: addendum 2026-10-01's rule in both readings plus total
net R not worse than B's in train and holdout.

    python3 scripts/detector_variants.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import time as dtime, timezone
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

import backtest_history as H  # noqa: E402
import backtest_recent as E  # noqa: E402
import rules_audit as RA  # noqa: E402
from momentum_platform import indicators as I  # noqa: E402
from momentum_platform.models import Bar  # noqa: E402
from momentum_platform.pullback import FirstPullbackDetector  # noqa: E402

OUT = ROOT / "research" / "paper-exercise" / "reports" / "detector_variants_output.txt"
ARM_START, ARM_END = dtime(4, 0), dtime(11, 30)
K = 4
CONFIGS = {"B": (False, 2), "D1": (True, 2), "D2": (False, 1), "D12": (True, 1)}


class NoBlackout(FirstPullbackDetector):
    """D1: a frozen plan does not hold the machine; it searches again at once."""

    def on_bar(self, bar):
        plan = super().on_bar(bar)
        if plan is not None:
            self._reset()
            if self._green(bar):
                self._w.impulse_bars.append(bar)
        return plan


def plans_for(sym, day, rows, cfg):
    no_blackout, min_imp = CONFIGS[cfg]
    det = (NoBlackout if no_blackout else FirstPullbackDetector)(min_impulse_bars=min_imp)
    hist, hi, out = [], None, []
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
        red = RA._red(I.chart_gates(hist), entry, plan.volume_ok)
        red_prev = RA._red(I.chart_gates(hist[:-1]), entry, plan.volume_ok)
        c_prev = rows[i - 1][4] if i else c
        pm = ts.time() < RA.RTH
        dv5 = float(sum(b[4] * b[5] for b in hist[-5:]))
        spread = RA.PROXY.spread(entry, pm, dv5)
        rec = {"sym": sym, "day": day, "t": ts.strftime("%H:%M"), "arm": int(ts.timestamp()),
               "entry": entry, "stop": stop, "stop_pct": (entry - stop) / entry * 100.0,
               "fade": 100.0 * (hi - c) / hi if hi else 0.0, "red": red,
               "fade_prev": 100.0 * (hi_prev - c_prev) / hi_prev if hi_prev else 0.0, "red_prev": red_prev,
               "retrace": None, "macd_line_pos": False, "push_rising": False, "push_elevated": False,
               "pm": pm, "dv5": dv5, "spread_ratio": (entry - stop) / spread if spread > 0 else 99.0, "out": {}}
        fwd = rows[i + 1:]
        order_t = int(ts.timestamp()) + 60
        for mode in ("A", "C"):
            got = RA.fill_retouch(fwd, entry, 3, 0.3, None if mode == "A" else order_t) if fwd else None
            if got is None:
                rec["out"][(mode, "base")] = None
                continue
            fk, px, kind = got
            bars = fwd[fk:]
            r, stopish, k = RA.run_exit(bars, entry, stop, px, 1.0, dtime(11, 30), mode, kind)
            rec["out"][(mode, "base")] = (int(bars[0][0].timestamp()), int(bars[k][0].timestamp()),
                                          round(r, 4), stopish, px)
        out.append(rec)
    return out


def day_job(args):
    day, syms = args
    f = H.CACHE / f"{day}.json"
    if not f.exists():
        return day, {}
    data = json.loads(f.read_text())
    res = {cfg: [] for cfg in CONFIGS}
    for sym, pc in syms.items():
        raw = data.get(sym)
        if not raw:
            continue
        rows = [r for r in H.to_rows(raw) if dtime(4, 0) <= r[0].time() < dtime(16, 0)]
        if len(rows) < 40:
            continue
        for cfg in CONFIGS:
            res[cfg] += plans_for(sym, day, rows, cfg)
    return day, res


def total(tr, lo=None, hi=None):
    return sum(t["net"] for t in tr if (lo is None or t["day"] >= lo) and (hi is None or t["day"] < hi))


def main() -> int:
    E.COST_MODEL = "live"
    lines = []

    def pr(s=""):
        print(s, flush=True); lines.append(s)

    uni = H.load_universe(None, None)
    by_cfg = {cfg: defaultdict(list) for cfg in CONFIGS}
    with Pool(4) as pool:
        for k, (day, res) in enumerate(pool.imap(day_job, sorted(uni.items()), chunksize=8), 1):
            for cfg, ps in res.items():
                by_cfg[cfg][day] += ps
            if k % 500 == 0:
                print(f"  {k}/{len(uni)} sessions", flush=True)
    pr(f"addendum 2026-10-06d · {len(uni)} sessions · plans armed 04:00-11:30, rebuilt per variant · costs live")
    pr("  " + " · ".join(f"{c} {sum(len(v) for v in by_cfg[c].values())} plans" for c in CONFIGS))
    runs = [("D1 no blackout", "D1", {}), ("D2 one-bar impulse", "D2", {}), ("D12 both", "D12", {}),
            ("W4 04:00 start", "B", {"start": "04:00"})]
    passes = {}
    for mode in ("A", "C"):
        c0 = dict(RA.BASE, mode=mode)
        base = RA.portfolio(by_cfg["B"], c0)
        sb = RA.split_stats(base)
        pr(f"\n=== reading {mode} ===")
        pr(f"  B   train n {sb['train']['n']} net {sb['train']['mean']:+.3f} total {total(base, hi=RA.SPLIT):+.1f} R · "
           f"holdout n {sb['test']['n']} net {sb['test']['mean']:+.3f} total {total(base, lo=RA.SPLIT):+.1f} R")
        for name, cfg, over in runs:
            tr = RA.portfolio(by_cfg[cfg], dict(c0, **over))
            sv = RA.split_stats(tr)
            lb = RA.paired_lb(tr, base, alpha=0.05 / K)
            v, checks = RA.verdict(name, sb, sv, lb)
            checks["train total not worse"] = total(tr, hi=RA.SPLIT) >= total(base, hi=RA.SPLIT)
            checks["holdout total not worse"] = total(tr, lo=RA.SPLIT) >= total(base, lo=RA.SPLIT)
            ok = all(checks.values())
            passes.setdefault(name, []).append(ok)
            yrs = " ".join(f"{sv['years'][y].get('mean', float('nan')):+.2f}" for y in ("2024", "2025", "2026"))
            pr(f"  {name:<20} train n {sv['train']['n']} net {sv['train']['mean']:+.3f} total {total(tr, hi=RA.SPLIT):+.1f} R · "
               f"holdout n {sv['test']['n']} net {sv['test']['mean']:+.3f} total {total(tr, lo=RA.SPLIT):+.1f} R · "
               f"lb {lb:+.3f} · yrs {yrs}")
            pr("      " + " · ".join(f"{'✓' if x else '✗'} {k}" for k, x in checks.items()) + f"  → {'PASS' if ok else 'keep B'}")
            if name.startswith("W4"):
                early = [t for t in tr if t["t"] < "07:00"]
                pr(f"      trades 04:00-07:00: n {len(early)} · net {sum(t['net'] for t in early) / max(1, len(early)):+.3f} "
                   f"· gross {sum(t['gross'] for t in early) / max(1, len(early)):+.3f}")
    pr("\nDECISION (both readings): " + " · ".join(f"{n} {'PASS → built OFF' if all(v) else 'fails'}" for n, v in passes.items()))
    OUT.write_text("\n".join(lines) + "\n")
    print(f"written {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
