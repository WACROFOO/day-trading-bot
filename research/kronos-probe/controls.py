#!/usr/bin/env python3
"""What would a free statistic have scored?

A foundation model that ranks outcomes at AUC 0.67 sounds like it found
something. The question that decides whether it did is what a one-line,
model-less statistic scores on the same anchors. If they match, 24.7M
parameters and 87 CPU-minutes bought nothing.

Also re-scores the SAME rollouts under every available reduction, because
p_win turned out degenerate — 90% of anchors exactly zero — and an AUC of
0.49 on a score with no variance is not evidence of absence, it is absence of
evidence. Changing the reduction costs no rollouts.

    python3 controls.py results/probe_pattern.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from run_probe import _auc              # noqa: E402
from src.bars import context_window     # noqa: E402

KRONOS_SCORES = ["exp_close_r", "exp_mfe_r", "med_close_r", "p_touch_up",
                 "p_win", "p_win_repaired", "exp_mae_r"]
FREE_SCORES = ["dist_from_window_mean_R", "anchor_z", "dist_from_window_high_R",
               "window_ret_pct", "risk_pct"]


def add_free_features(d: pd.DataFrame, ctx_len: int = 150) -> pd.DataFrame:
    """Statistics available from the context window alone — no model."""
    feats = []
    for r in d.itertuples():
        w = context_window(r.sym, r.day, int(r.anchor_ts), ctx_len)
        if w is None:
            feats.append({k: np.nan for k in FREE_SCORES})
            continue
        closes = np.array([b[4] for b in w], dtype=float)
        highs = np.array([b[2] for b in w], dtype=float)
        feats.append(dict(
            dist_from_window_mean_R=(r.entry - closes.mean()) / r.risk,
            anchor_z=(r.entry - closes.mean()) / (closes.std() + 1e-9),
            dist_from_window_high_R=(highs.max() - r.entry) / r.risk,
            window_ret_pct=100.0 * (r.entry - closes[0]) / closes[0],
            risk_pct=100.0 * r.risk / r.entry,
        ))
    return pd.concat([d.reset_index(drop=True), pd.DataFrame(feats)], axis=1)


def boot_auc(v, y, n=2000, seed=7):
    """AUC is noisy on a couple of dozen winners; a point estimate invites
    over-reading, so every number here carries an interval."""
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        if 0 < y[i].sum() < len(y):
            out.append(_auc(v[i], y[i]))
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)))


def evaluate(path: Path, ctx_len: int = 150) -> dict:
    d = add_free_features(pd.read_csv(path), ctx_len)
    dec = d[d.true_outcome.isin(["win", "loss"])].copy()
    dec["hit"] = (dec.true_outcome == "win").astype(int)
    y = dec.hit.values

    rows = []
    for c, src in ([(c, "kronos") for c in KRONOS_SCORES]
                   + [(c, "free") for c in FREE_SCORES]):
        if c not in dec.columns:
            continue
        v = dec[c].values.astype(float)
        if not np.isfinite(v).all():
            continue
        a = _auc(v, y)
        lo, hi = boot_auc(v, y)
        inverted = a < 0.5
        if inverted:                      # a backwards-ranking score is still
            a, lo, hi = 1 - a, 1 - hi, 1 - lo   # information, just signed
        rows.append(dict(score=c, source=src, auc=round(a, 4),
                         ci=[round(lo, 3), round(hi, 3)], inverted=bool(inverted),
                         distinct=int(pd.Series(v).nunique()),
                         frac_at_mode=round(
                             float(pd.Series(v).value_counts(normalize=True).iloc[0]), 3)))
    rows.sort(key=lambda r: -r["auc"])

    best_k = max((r for r in rows if r["source"] == "kronos"),
                 key=lambda r: r["auc"], default=None)
    best_f = max((r for r in rows if r["source"] == "free"),
                 key=lambda r: r["auc"], default=None)
    return dict(
        file=path.name, n=len(d), n_resolved=len(dec), n_win=int(y.sum()),
        base_rate=round(float(y.mean()), 4), scores=rows,
        best_kronos=best_k, best_free=best_f,
        kronos_minus_free=(round(best_k["auc"] - best_f["auc"], 4)
                           if best_k and best_f else None),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--ctx", type=int, default=150)
    a = ap.parse_args()

    out = []
    for f in a.files:
        r = evaluate(f, a.ctx)
        out.append(r)
        print(f"\n=== {r['file']} — n {r['n_resolved']} resolved, "
              f"{r['n_win']} winners, base {r['base_rate']:.4f} ===")
        print(f"{'score':26s} {'AUC':>7s} {'95% CI':>17s} {'distinct':>9s} "
              f"{'mode':>6s}  source")
        for s in r["scores"]:
            flag = " (inv)" if s["inverted"] else ""
            print(f"{s['score']:26s} {s['auc']:7.4f} "
                  f"[{s['ci'][0]:6.3f},{s['ci'][1]:6.3f}] {s['distinct']:9d} "
                  f"{s['frac_at_mode']:6.3f}  {s['source']}{flag}")
        if r["kronos_minus_free"] is not None:
            print(f"\nbest kronos {r['best_kronos']['score']} "
                  f"{r['best_kronos']['auc']:.4f}  vs  best free "
                  f"{r['best_free']['score']} {r['best_free']['auc']:.4f}"
                  f"   delta {r['kronos_minus_free']:+.4f}")

    (ROOT / "results" / "controls.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {ROOT / 'results' / 'controls.json'}")


if __name__ == "__main__":
    main()
