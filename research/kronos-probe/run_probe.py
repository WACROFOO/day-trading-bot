#!/usr/bin/env python3
"""Does Kronos separate the trades that worked from the ones that didn't?

The only question worth asking first. At each variant-A decision point
(`setup_ts`, the pullback bar's close), hand the model the previous 150
same-session bars, sample N forward paths of 30 minutes, and reduce them to
P(+1R before -1R) using the PREDICTED high and low. Then put that probability
next to the outcome the ablation already measured.

If the probability carries information, realised winners should score higher
than realised losers. If it doesn't, the tool is producing well-formed
numbers with nothing in them, and that is the finding.

    python3 run_probe.py --limit 300 --paths 16 --batch 16

Nothing here is a trading claim. It is a discrimination test against a
population whose outcomes are already known and already negative.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/user/shiyu-coder/kronos")

from src import anchors as anchor_src                        # noqa: E402
from src.bars import context_window                          # noqa: E402
from src.forecast import (Forecaster, barrier_probabilities,  # noqa: E402
                          to_features)
from model import Kronos, KronosTokenizer                    # noqa: E402


def materialise(df, ctx_len, want, rng):
    """Seeded sample of usable anchors, spread over the whole study period.

    Taking the first N would take eleven years of tape and score only 2016.
    """
    order = rng.permutation(len(df))
    out, dropped = [], 0
    for i in order:
        row = df.iloc[int(i)]
        rows = context_window(row.sym, row.day, int(row.setup_ts), ctx_len)
        if rows is None:
            dropped += 1
            continue
        out.append(dict(
            sym=row.sym, day=row.day, anchor_ts=int(row.setup_ts),
            ctx=to_features(rows), ctx_ts=[int(r[0]) for r in rows],
            entry=float(row.entry_fill), risk=float(row.risk_per_share),
            net_r=float(row.net_r), mfe_r=float(row.mfe_r),
            pullback_number=int(row.ctx_pullback_number),
        ))
        if len(out) >= want:
            break
    return out, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--paths", type=int, default=16)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--ctx", type=int, default=150)
    ap.add_argument("--pred", type=int, default=30)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--top-p", type=float, default=0.9)
    ap.add_argument("--seed", type=int, default=20260826)
    ap.add_argument("--model", default="NeoQuasar/Kronos-small")
    ap.add_argument("--tokenizer", default="NeoQuasar/Kronos-Tokenizer-base")
    ap.add_argument("--tag", default="varA")
    a = ap.parse_args()

    torch.manual_seed(a.seed)
    rng = np.random.default_rng(a.seed)

    df = anchor_src.variant_a()
    print(f"population: {len(df)} variant-A trades", flush=True)
    items, dropped = materialise(df, a.ctx, a.limit, rng)
    print(f"anchors: {len(items)} usable, {dropped} dropped for <{a.ctx} "
          f"same-session bars", flush=True)

    tok = KronosTokenizer.from_pretrained(a.tokenizer)
    mdl = Kronos.from_pretrained(a.model)
    fc = Forecaster(tok, mdl, device="cpu")

    recs, t_start = [], time.time()
    for s in range(0, len(items), a.batch):
        chunk = items[s:s + a.batch]
        paths = fc.paths(np.stack([c["ctx"] for c in chunk]),
                         [c["ctx_ts"] for c in chunk],
                         [c["anchor_ts"] for c in chunk],
                         pred_len=a.pred, n_paths=a.paths,
                         T=a.temperature, top_p=a.top_p)
        stats = barrier_probabilities(
            paths,
            np.array([c["entry"] for c in chunk], dtype=np.float64),
            np.array([c["risk"] for c in chunk], dtype=np.float64))
        for j, c in enumerate(chunk):
            recs.append(dict(
                sym=c["sym"], day=c["day"], anchor_ts=c["anchor_ts"],
                entry=c["entry"], risk=c["risk"],
                pullback_number=c["pullback_number"],
                **{k: float(v[j]) for k, v in stats.items()},
                realised_net_r=c["net_r"], realised_mfe_r=c["mfe_r"],
                realised_win=int(c["net_r"] > 0),
            ))
        done = min(s + a.batch, len(items))
        el = time.time() - t_start
        print(f"  {done}/{len(items)} anchors · {el / 60:.1f} min elapsed · "
              f"eta {(el / done) * (len(items) - done) / 60:.1f} min",
              flush=True)

    out = pd.DataFrame(recs)
    dest = ROOT / "results" / f"probe_{a.tag}.csv"
    out.to_csv(dest, index=False)

    w = out[out.realised_win == 1]
    l = out[out.realised_win == 0]
    summary = dict(
        config=dict(model=a.model, ctx=a.ctx, pred_len=a.pred, paths=a.paths,
                    temperature=a.temperature, top_p=a.top_p, seed=a.seed),
        n=len(out), n_win=len(w), n_loss=len(l),
        realised_win_rate=round(out.realised_win.mean(), 4),
        realised_exp_r=round(out.realised_net_r.mean(), 4),
        p_win_mean=round(out.p_win.mean(), 4),
        p_win_on_realised_winners=round(w.p_win.mean(), 4) if len(w) else None,
        p_win_on_realised_losers=round(l.p_win.mean(), 4) if len(l) else None,
        separation=round(w.p_win.mean() - l.p_win.mean(), 4) if len(w) else None,
        corr_p_win_vs_net_r=round(out.p_win.corr(out.realised_net_r), 4),
        corr_exp_mfe_vs_mfe=round(out.exp_mfe_r.corr(out.realised_mfe_r), 4),
        model_mean_exp_mfe_r=round(out.exp_mfe_r.mean(), 3),
        realised_mean_mfe_r=round(out.realised_mfe_r.mean(), 3),
        minutes=round((time.time() - t_start) / 60, 1),
    )
    # top-decile lift: the only form a filter could actually be used in
    if len(out) >= 20:
        k = max(1, len(out) // 10)
        top = out.nlargest(k, "p_win")
        summary["top_decile"] = dict(
            n=int(k), win_rate=round(top.realised_win.mean(), 4),
            exp_r=round(top.realised_net_r.mean(), 4))

    (ROOT / "results" / f"probe_{a.tag}_summary.json").write_text(
        json.dumps(summary, indent=2))
    print("\n" + json.dumps(summary, indent=2))
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
