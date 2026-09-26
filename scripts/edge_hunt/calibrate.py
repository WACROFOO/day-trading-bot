#!/usr/bin/env python3
"""Fit the spread proxy on real Alpaca NBBO quotes, TRAIN and VALIDATION
moments only; report its error on holdout-period moments (no refit).

A moment is a sampled desk fill (sym, day, minute). Its spread is the
median quoted spread (ask − bid, both sides live, ask > bid) across the NBBO
updates in that minute. The proxy cell is price tier × pre-market/regular ×
the dollar volume of the five bars before the moment.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from edge_hunt import costs as C  # noqa: E402
from edge_hunt.data import STORE, Store, minute, split_of  # noqa: E402
from edge_hunt.features import Grid  # noqa: E402

MOMENTS = ROOT / "research" / "edge-hunt" / "results" / "quote_moments.csv"     # the sampled fills, fixed


def moments(listfile: Path) -> pd.DataFrame:
    rows = []
    for sym, day, hm in csv.reader(open(listfile)):
        f = STORE / "quotes" / f"{day}_{sym}_{hm.replace(':', '')}.json"
        if not f.exists():
            continue
        q = json.loads(f.read_text())
        sp = [a - b for t, b, a, bs, as_ in q if b and a and a > b and b > 0]
        mid = [(a + b) / 2 for t, b, a, bs, as_ in q if b and a and a > b and b > 0]
        if len(sp) < 3:
            continue
        rows.append({"sym": sym, "day": day, "min": minute(int(hm[:2]), int(hm[3:])), "spread": float(np.median(sp)),
                     "mid": float(np.median(mid)), "n_quotes": len(sp)})
    return pd.DataFrame(rows)


def main() -> int:
    S = Store(); g = Grid(S)
    key = {(d, s): i for i, (d, s) in enumerate(zip(S.sd["day"], S.sd["sym"]))}
    m = moments(MOMENTS)
    m["sid"] = [key.get((d, s), -1) for d, s in zip(m.day, m.sym)]
    m = m[m.sid >= 0].copy()
    t = np.clip(m["min"].to_numpy() - 1, 0, 719)
    lo = t - 5
    m["dv5"] = g.cumdv[m.sid, t] - np.where(lo >= 0, g.cumdv[m.sid, np.clip(lo, 0, 719)], 0)
    m["pm"] = m["min"] < minute(9, 30)
    m["rel"] = m["spread"] / m["mid"]
    m["split"] = m["day"].map(split_of)
    m["cell"] = [C.SpreadProxy.key(p, pm, dv) for p, pm, dv in zip(m.mid, m.pm, m.dv5)]
    fit = m[m.split != "holdout"]
    # the MEAN across moments: an expected cost, and spreads are right-skewed (the median understates it)
    cells = fit.groupby("cell")["rel"].agg(["mean", "count"])
    default = float(fit["rel"].mean())
    table = {"cells": {k: float(r["mean"]) for k, r in cells.iterrows() if r["count"] >= 8},
             "default": default, "n_fit": int(len(fit)),
             "counts": {k: int(r["count"]) for k, r in cells.iterrows()},
             "note": "mean across moments of the minute's median quoted spread / mid, at sampled desk fills; train+validation moments only"}
    out = ROOT / "research" / "edge-hunt" / "results" / "spread_proxy.json"
    out.write_text(json.dumps(table, indent=1, sort_keys=True))
    prox = C.SpreadProxy(out)
    for name, part in (("fit (train+valid)", fit), ("holdout (not fitted)", m[m.split == "holdout"])):
        pred = np.array([prox.spread(p, pm, dv) for p, pm, dv in zip(part.mid, part.pm, part.dv5)])
        err = pred - part["spread"].to_numpy()
        print(f"{name:<22} n {len(part):>4} · median spread {part.spread.median():.3f} $ · predicted {np.median(pred):.3f} $ · "
              f"median |error| {np.median(np.abs(err)):.3f} $ · bias {np.median(err):+.3f} $ · "
              f"half-spread > 1c in {np.mean(part.spread > 0.02):.0%}")
    print("\ncell                     n   mean spread % of price")
    for k in sorted(table["counts"]):
        print(f"  {k:<22}{table['counts'][k]:>4}   {table['cells'].get(k, default) * 100:.2f} %")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
