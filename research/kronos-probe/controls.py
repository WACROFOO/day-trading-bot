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
import datetime as _dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

_ET = ZoneInfo("America/New_York")

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


def compare(path_a: Path, path_b: Path, ctx_len: int = 150) -> dict:
    """Pattern vs random, with the confound measured instead of ignored.

    The two populations differ by ~2.5 sigma in where the anchor sits inside
    its own context window (pattern median +2.12, random -0.44), and the
    model's forecast correlates 0.756 with that window's mean. So a raw gap
    in p_win between the arms is mostly the z-score gap, NOT the model
    telling the populations apart.

    The honest comparison is within an overlapping z band: among anchors that
    sit at comparable heights in their own window, does the model still
    separate the two populations?
    """
    frames = {}
    for tag, p in (("pattern", path_a), ("random", path_b)):
        d = add_free_features(pd.read_csv(p), ctx_len)
        d["arm"] = tag
        frames[tag] = d
    both = pd.concat(frames.values(), ignore_index=True)

    def _stats(d):
        dec = d[d.true_outcome.isin(["win", "loss"])]
        return dict(
            n=int(len(d)), n_resolved=int(len(dec)),
            realised_win_rate=(round(float((dec.true_outcome == "win").mean()), 4)
                               if len(dec) else None),
            anchor_z_median=(round(float(d.anchor_z.median()), 3)
                             if len(d) else None),
            p_win_mean=round(float(d.p_win.mean()), 4) if len(d) else None,
            frac_p_win_zero=(round(float((d.p_win == 0).mean()), 4)
                             if len(d) else None),
            exp_close_r_mean=(round(float(d.exp_close_r.mean()), 3)
                              if len(d) else None),
            true_fwd_close_r_mean=(round(float(d.true_fwd_close_r.mean()), 3)
                                   if len(d) else None),
        )

    # SECOND confound, found after the first: the random arm inherits the
    # parent baseline's 09:35-11:30 window while the pattern arm runs all
    # session and is 52% afternoon. The parent report's own time-of-day cut
    # makes 09:30-10:00 the strategy's best bucket, so leaving this
    # uncontrolled flatters the random arm. Match on both, not one.
    both["et"] = both.anchor_ts.map(
        lambda t: _dt.datetime.fromtimestamp(int(t), _ET))
    both["in_window"] = both.et.map(
        lambda x: _dt.time(9, 35) <= x.time() < _dt.time(11, 30))
    win = both[both.in_window]

    lo = max(win[win.arm == "pattern"].anchor_z.quantile(.05),
             win[win.arm == "random"].anchor_z.quantile(.05))
    hi = min(win[win.arm == "pattern"].anchor_z.quantile(.95),
             win[win.arm == "random"].anchor_z.quantile(.95))
    band = win[(win.anchor_z >= lo) & (win.anchor_z <= hi)]

    return dict(
        raw={t: _stats(f) for t, f in frames.items()},
        session_window_only={t: _stats(win[win.arm == t]) for t in frames},
        z_overlap_band=[round(float(lo), 3), round(float(hi), 3)],
        matched={t: _stats(band[band.arm == t]) for t in frames},
        note="Matched on BOTH 09:35-11:30 and the overlapping anchor-z band. "
             "A gap that survives is about the populations; one that vanishes "
             "was a confound.",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--ctx", type=int, default=150)
    ap.add_argument("--compare", action="store_true",
                    help="with exactly two files: pattern vs random, "
                         "raw and matched on anchor z-score")
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

    payload = dict(per_file=out)

    if a.compare and len(a.files) == 2:
        cmp = compare(a.files[0], a.files[1], a.ctx)
        payload["comparison"] = cmp
        print(f"\n=== pattern vs random ===")
        print(f"z overlap band: {cmp['z_overlap_band']}")
        for label in ("raw", "session_window_only", "matched"):
            print(f"\n-- {label} --")
            print(f"{'':22s} {'pattern':>12s} {'random':>12s}")
            for k in ("n", "anchor_z_median", "realised_win_rate",
                      "p_win_mean", "frac_p_win_zero", "exp_close_r_mean",
                      "true_fwd_close_r_mean"):
                p = cmp[label]["pattern"].get(k)
                q = cmp[label]["random"].get(k)
                print(f"{k:22s} {str(p):>12s} {str(q):>12s}")
        print(f"\n{cmp['note']}")

    (ROOT / "results" / "controls.json").write_text(json.dumps(payload, indent=2))
    print(f"\nwrote {ROOT / 'results' / 'controls.json'}")


if __name__ == "__main__":
    main()
