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
from src import truth                                        # noqa: E402
from src.bars import context_window                          # noqa: E402
from src.forecast import (Forecaster, barrier_probabilities,  # noqa: E402
                          to_features)
from model import Kronos, KronosTokenizer                    # noqa: E402


def _auc(score, label):
    """Rank AUC — P(a random winner scores above a random loser).

    0.5 is no information. Ties are credited half, which matters here: with
    N sampled paths the probability is quantised to multiples of 1/N and ties
    are common, so ignoring them would inflate the number.
    """
    order = np.argsort(score, kind="mergesort")
    s, y = np.asarray(score)[order], np.asarray(label)[order]
    ranks = np.empty(len(s), dtype=float)
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        ranks[i:j + 1] = (i + j) / 2.0 + 1.0     # average rank over the tie
        i = j + 1
    n_pos, n_neg = y.sum(), len(y) - y.sum()
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    return (ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def _attach_context(cand, ctx_len):
    """Materialise the context window, or None if the session is too thin."""
    rows = context_window(cand["sym"], cand["day"], cand["anchor_ts"], ctx_len)
    if rows is None:
        return None
    return dict(cand, ctx=to_features(rows), ctx_ts=[int(r[0]) for r in rows])


def materialise_pattern(df, ctx_len, want, rng):
    """Seeded sample of variant-A anchors, spread over the whole period.

    Taking the first N would take eleven years of tape and score only 2016.
    """
    out, dropped = [], 0
    for i in rng.permutation(len(df)):
        row = df.iloc[int(i)]
        cand = _attach_context(dict(
            sym=row.sym, day=row.day, anchor_ts=int(row.setup_ts),
            entry=float(row.entry_fill), risk=float(row.risk_per_share),
            study_net_r=float(row.net_r), study_mfe_r=float(row.mfe_r),
            pullback_number=int(row.ctx_pullback_number)), ctx_len)
        if cand is None:
            dropped += 1
            continue
        out.append(cand)
        if len(out) >= want:
            break
    return out, dropped


def materialise_random(ctx_len, want, seed):
    """The random-entry arm — the population the report says does BETTER."""
    out, dropped = [], 0
    for cand in anchor_src.random_entries(n=want * 3, seed=seed, ctx_len=ctx_len):
        c = _attach_context(dict(cand, study_net_r=float("nan"),
                                 study_mfe_r=float("nan")), ctx_len)
        if c is None:
            dropped += 1
            continue
        out.append(c)
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
    ap.add_argument("--tag", default=None)
    ap.add_argument("--population", choices=["pattern", "random"],
                    default="pattern")
    a = ap.parse_args()
    tag = a.tag or a.population

    torch.manual_seed(a.seed)
    rng = np.random.default_rng(a.seed)

    if a.population == "pattern":
        df = anchor_src.variant_a()
        print(f"population: {len(df)} variant-A trades", flush=True)
        items, dropped = materialise_pattern(df, a.ctx, a.limit, rng)
    else:
        print("population: random entries on qualifying ticker-days",
              flush=True)
        items, dropped = materialise_random(a.ctx, a.limit, a.seed)
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
                study_net_r=c["study_net_r"], study_mfe_r=c["study_mfe_r"],
            ))
        done = min(s + a.batch, len(items))
        el = time.time() - t_start
        print(f"  {done}/{len(items)} anchors · {el / 60:.1f} min elapsed · "
              f"eta {(el / done) * (len(items) - done) / 60:.1f} min",
              flush=True)

    out = truth.attach(pd.DataFrame(recs), horizon=a.pred)
    dest = ROOT / "results" / f"probe_{tag}.csv"
    out.to_csv(dest, index=False)

    # Score only where the barrier question actually resolved. 'neither' is a
    # real third outcome (the horizon ran out untouched), not a hidden loss,
    # so it is counted and excluded rather than folded into the losers.
    dec = out[out.true_outcome.isin(["win", "loss"])].copy()
    dec["hit"] = (dec.true_outcome == "win").astype(int)
    w, l = dec[dec.hit == 1], dec[dec.hit == 0]

    summary = dict(
        config=dict(model=a.model, population=a.population, ctx=a.ctx,
                    pred_len=a.pred, paths=a.paths, temperature=a.temperature,
                    top_p=a.top_p, seed=a.seed),
        n=len(out), anchors_dropped=dropped,
        outcome_counts=out.true_outcome.value_counts().to_dict(),
        n_resolved=len(dec), n_win=len(w), n_loss=len(l),
        realised_barrier_win_rate=(round(dec.hit.mean(), 4) if len(dec) else None),
        # --- the test: does the model's probability separate them? ---
        p_win_mean=round(out.p_win.mean(), 4),
        p_win_on_winners=round(w.p_win.mean(), 4) if len(w) else None,
        p_win_on_losers=round(l.p_win.mean(), 4) if len(l) else None,
        separation=(round(w.p_win.mean() - l.p_win.mean(), 4)
                    if len(w) and len(l) else None),
        auc=(round(_auc(dec.p_win.values, dec.hit.values), 4)
             if len(w) and len(l) else None),
        corr_p_win_vs_fwd_close_r=round(out.p_win.corr(out.true_fwd_close_r), 4),
        corr_exp_mfe_vs_true_mfe=round(out.exp_mfe_r.corr(out.true_fwd_mfe_r), 4),
        # --- calibration: is the number even on the right scale? ---
        model_mean_exp_mfe_r=round(out.exp_mfe_r.mean(), 3),
        true_mean_fwd_mfe_r=round(out.true_fwd_mfe_r.mean(), 3),
        model_mean_exp_mae_r=round(out.exp_mae_r.mean(), 3),
        true_mean_fwd_mae_r=round(out.true_fwd_mae_r.mean(), 3),
        study_exp_r=(round(out.study_net_r.mean(), 4)
                     if out.study_net_r.notna().any() else None),
        minutes=round((time.time() - t_start) / 60, 1),
    )
    # top-decile lift: the only form a filter could actually be used in
    if len(dec) >= 20:
        k = max(1, len(dec) // 10)
        top = dec.nlargest(k, "p_win")
        summary["top_decile"] = dict(
            n=int(k), win_rate=round(top.hit.mean(), 4),
            vs_base=round(top.hit.mean() - dec.hit.mean(), 4))

    (ROOT / "results" / f"probe_{tag}_summary.json").write_text(
        json.dumps(summary, indent=2))
    print("\n" + json.dumps(summary, indent=2))
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
