#!/usr/bin/env python3
"""External-review checks — verifying claims made against this work.

Every check here was raised by an outside reviewer and is answerable from
data already on disk. Run them rather than concede or defend from memory.

    python3 review_checks.py

C1  loss-tail decomposition of the parent study. The reviewer derived a
    ~-2.2R average loser from win rate and profit factor and asked whether
    the failure is "directionally wrong" or "occasionally overshoots its
    nominal risk". Those are different mechanisms and the report does not
    separate them.

C2  MFE denominator contamination. Pattern MFE 0.78R and random 1.15R are
    quoted in strategy-specific R, but the two arms have different median
    risk as a percent of price (1.98% vs 1.49%), so R is not a common unit.
    Recompute the excursion in percent and in ATR.

C3  paired delta-AUC with DAY-CLUSTERED resampling. Comparing two marginal
    confidence intervals and observing overlap is not a test of equality.
    The two scores are evaluated on the same rows and are correlated, so the
    paired difference is the quantity with a meaningful interval — and the
    anchors are not independent, they cluster by session.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from controls import add_free_features            # noqa: E402
from run_probe import _auc                        # noqa: E402

FPE = ROOT.parent / "first-pullback-edge"


# ----------------------------------------------------------------- C1
def loss_tail_decomposition() -> dict:
    t = pd.read_parquet(FPE / "data" / "trades.parquet")
    a = t[(t.variant == "A") & (t.cost_model == "realistic")
          & (t.experiment == "exp1_common_exits")
          & (t.ambiguity_policy == "pessimistic")]
    r = a.net_r.astype(float)
    w, l = r[r > 0], r[r <= 0]
    tot = r.sum()

    def share(mask):
        return round(float(r[mask].sum() / tot), 4) if tot else None

    return dict(
        n=int(len(r)),
        win_rate=round(float((r > 0).mean()), 4),
        expectancy_r=round(float(r.mean()), 4),
        mean_winner=round(float(w.mean()), 4), median_winner=round(float(w.median()), 4),
        mean_loser=round(float(l.mean()), 4), median_loser=round(float(l.median()), 4),
        worst=round(float(r.min()), 4),
        # the question: is -1.741 a slope or a tail?
        frac_losses_beyond_1_25R=round(float((r < -1.25).mean()), 4),
        frac_losses_beyond_2R=round(float((r < -2).mean()), 4),
        frac_losses_beyond_5R=round(float((r < -5).mean()), 4),
        share_of_total_R_from_beyond_2R=share(r < -2),
        share_of_total_R_from_beyond_5R=share(r < -5),
        expectancy_if_losses_capped_at_1R=round(float(r.clip(lower=-1).mean()), 4),
        expectancy_if_losses_capped_at_2R=round(float(r.clip(lower=-2).mean()), 4),
        exit_reason_mix=a.exit_reason.value_counts().head(8).to_dict(),
        mean_r_by_exit={k: round(float(v), 3) for k, v in
                        a.groupby("exit_reason").net_r.mean().items()},
    )


# ----------------------------------------------------------------- C2
def mfe_units() -> dict:
    out = {}
    for tag in ("pattern", "random"):
        d = pd.read_csv(ROOT / "results" / f"probe_{tag}.csv")
        risk_pct = (d.risk / d.entry).astype(float)
        out[tag] = dict(
            n=int(len(d)),
            median_risk_pct=round(float(100 * risk_pct.median()), 4),
            # as reported: strategy-specific R
            mfe_R=round(float(d.true_fwd_mfe_r.mean()), 4),
            mae_R=round(float(d.true_fwd_mae_r.mean()), 4),
            # common unit: percent of price
            mfe_pct=round(float((d.true_fwd_mfe_r * risk_pct * 100).mean()), 4),
            mae_pct=round(float((d.true_fwd_mae_r * risk_pct * 100).mean()), 4),
            median_mfe_pct=round(float((d.true_fwd_mfe_r * risk_pct * 100).median()), 4),
        )
    p, r = out["pattern"], out["random"]
    out["verdict"] = dict(
        ratio_in_R=round(r["mfe_R"] / p["mfe_R"], 4),
        ratio_in_pct=round(r["mfe_pct"] / p["mfe_pct"], 4),
        note="If the ratio shrinks moving from R to percent, part of the gap "
             "was the denominator, exactly as the reviewer argued.",
    )
    return out


# ----------------------------------------------------------------- C3
def paired_delta_auc(path: Path, score_a: str, score_b: str,
                     n_boot: int = 4000, seed: int = 19) -> dict:
    """AUC(a) - AUC(b) on the same rows, resampling SESSIONS not anchors."""
    d = add_free_features(pd.read_csv(path))
    dec = d[d.true_outcome.isin(["win", "loss"])].copy()
    dec["hit"] = (dec.true_outcome == "win").astype(int)
    dec = dec[np.isfinite(dec[score_a]) & np.isfinite(dec[score_b])]

    def oriented(v, y):
        a = _auc(v, y)
        return (1 - a) if a < 0.5 else a

    y = dec.hit.values
    obs = dict(auc_a=round(oriented(dec[score_a].values.astype(float), y), 4),
               auc_b=round(oriented(dec[score_b].values.astype(float), y), 4))
    obs["delta"] = round(obs["auc_a"] - obs["auc_b"], 4)

    days = dec.day.unique()
    by_day = {k: g for k, g in dec.groupby("day")}
    rng = np.random.default_rng(seed)
    deltas, a_s, b_s = [], [], []
    for _ in range(n_boot):
        pick = rng.choice(days, size=len(days), replace=True)
        s = pd.concat([by_day[k] for k in pick], ignore_index=True)
        yy = s.hit.values
        if not (0 < yy.sum() < len(yy)):
            continue
        aa = oriented(s[score_a].values.astype(float), yy)
        bb = oriented(s[score_b].values.astype(float), yy)
        a_s.append(aa)
        b_s.append(bb)
        deltas.append(aa - bb)
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    return dict(
        file=path.name, score_a=score_a, score_b=score_b,
        n=int(len(dec)), n_sessions=int(len(days)), n_win=int(y.sum()),
        observed=obs,
        auc_a_clustered_ci=[round(float(x), 3)
                            for x in np.percentile(a_s, [2.5, 97.5])],
        auc_b_clustered_ci=[round(float(x), 3)
                            for x in np.percentile(b_s, [2.5, 97.5])],
        delta_clustered_ci=[round(float(lo), 4), round(float(hi), 4)],
        delta_excludes_zero=bool(lo > 0 or hi < 0),
    )


def main():
    out = {}

    print("=" * 72)
    print("C1  loss-tail decomposition — is -1.741 R a slope or a tail?")
    print("=" * 72)
    out["C1_loss_tail"] = loss_tail_decomposition()
    print(json.dumps(out["C1_loss_tail"], indent=2))

    print("\n" + "=" * 72)
    print("C2  MFE in a COMMON unit, not strategy-specific R")
    print("=" * 72)
    out["C2_mfe_units"] = mfe_units()
    print(json.dumps(out["C2_mfe_units"], indent=2))

    print("\n" + "=" * 72)
    print("C3  paired delta-AUC, DAY-CLUSTERED — the actual test")
    print("=" * 72)
    out["C3_paired_delta_auc"] = []
    for f, a, b in [
        ("probe_pattern.csv", "exp_close_r", "dist_from_window_mean_R"),
        ("probe_random.csv", "exp_close_r", "risk_pct"),
    ]:
        r = paired_delta_auc(ROOT / "results" / f, a, b)
        out["C3_paired_delta_auc"].append(r)
        print(f"\n{r['file']}  n={r['n']} over {r['n_sessions']} sessions, "
              f"{r['n_win']} winners")
        print(f"  {a:26s} AUC {r['observed']['auc_a']:.4f} "
              f"clustered CI {r['auc_a_clustered_ci']}")
        print(f"  {b:26s} AUC {r['observed']['auc_b']:.4f} "
              f"clustered CI {r['auc_b_clustered_ci']}")
        print(f"  PAIRED delta {r['observed']['delta']:+.4f}  "
              f"CI {r['delta_clustered_ci']}  "
              f"excludes zero: {r['delta_excludes_zero']}")

    (ROOT / "results" / "review_checks.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {ROOT / 'results' / 'review_checks.json'}")


if __name__ == "__main__":
    main()
