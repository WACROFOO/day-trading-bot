#!/usr/bin/env python3
"""Re-score a probe CSV against the matched barrier truth.

Separate from `run_probe.py` so that scoring never costs a rollout: the model
output is the expensive artefact, and how it is graded should be revisable
without regenerating it. Also lets a run started under an older scorer be
brought forward.

    python3 score.py results/probe_pattern.csv results/probe_random.csv

With two files it also reports the comparison the parent study's open
question actually asks: does the model rank the RANDOM population above the
pattern-selected one, the way the realised outcomes do?
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

from run_probe import _auc          # noqa: E402
from src import truth               # noqa: E402


def score(path: Path, horizon: int = 30) -> dict:
    df = pd.read_csv(path)
    if "true_outcome" not in df.columns:
        df = truth.attach(df, horizon=horizon)
        df.to_csv(path, index=False)

    dec = df[df.true_outcome.isin(["win", "loss"])].copy()
    dec["hit"] = (dec.true_outcome == "win").astype(int)
    w, l = dec[dec.hit == 1], dec[dec.hit == 0]

    out = dict(
        file=path.name, n=len(df),
        outcomes=df.true_outcome.value_counts().to_dict(),
        n_resolved=len(dec),
        realised_win_rate=round(dec.hit.mean(), 4) if len(dec) else None,
        p_win_mean=round(df.p_win.mean(), 4),
        p_win_on_winners=round(w.p_win.mean(), 4) if len(w) else None,
        p_win_on_losers=round(l.p_win.mean(), 4) if len(l) else None,
        separation=(round(w.p_win.mean() - l.p_win.mean(), 4)
                    if len(w) and len(l) else None),
        auc=(round(_auc(dec.p_win.values, dec.hit.values), 4)
             if len(w) and len(l) else None),
        model_mean_exp_mfe_r=round(df.exp_mfe_r.mean(), 3),
        true_mean_fwd_mfe_r=round(df.true_fwd_mfe_r.mean(), 3),
        model_mean_exp_mae_r=round(df.exp_mae_r.mean(), 3),
        true_mean_fwd_mae_r=round(df.true_fwd_mae_r.mean(), 3),
    )
    if len(dec) >= 20:
        k = max(1, len(dec) // 10)
        top = dec.nlargest(k, "p_win")
        out["top_decile"] = dict(n=int(k), win_rate=round(top.hit.mean(), 4),
                                 vs_base=round(top.hit.mean() - dec.hit.mean(), 4))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--horizon", type=int, default=30)
    a = ap.parse_args()

    results = [score(f, a.horizon) for f in a.files]
    for r in results:
        print(json.dumps(r, indent=2))

    if len(results) == 2:
        p, q = results
        print("\n--- population comparison ---")
        print(f"{'':28s} {p['file']:>22s} {q['file']:>22s}")
        for k in ("realised_win_rate", "p_win_mean", "auc",
                  "model_mean_exp_mfe_r", "true_mean_fwd_mfe_r"):
            print(f"{k:28s} {str(p.get(k)):>22s} {str(q.get(k)):>22s}")
        print("\nThe report's open question: the random population wins more "
              "often in reality.\nIf the model's p_win does NOT also rank it "
              "higher, it is blind to the thing\nthat actually separates "
              "these two populations.")

    (ROOT / "results" / "scores.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
