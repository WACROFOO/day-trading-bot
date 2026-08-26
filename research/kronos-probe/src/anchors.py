"""Decision points to score, drawn from the finished ablation.

The anchor is `setup_ts` — the pullback bar's close, the moment the strategy
commits — NOT `entry_ts`. A filter has to be usable before the trigger is
touched, so the context window ends where the decision was actually made and
the forecast horizon starts one minute later.

Each anchor carries the realised outcome the study already measured, so the
probe can be scored without re-running the backtest.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

FPE = Path(__file__).resolve().parents[2] / "first-pullback-edge"

COLS = ["sym", "day", "setup_ts", "entry_ts", "entry_fill", "risk_per_share",
        "net_r", "mfe_r", "mae_r", "ctx_price", "ctx_pullback_number",
        "ctx_rvol_at_time", "exit_reason"]


def variant_a(cost_model: str = "realistic",
              ambiguity: str = "pessimistic") -> pd.DataFrame:
    """The study's headline variant-A population.

    All four filters are load-bearing: without `ambiguity` the table holds
    the same setups scored three ways and the row count triples. This
    combination reproduces the report's 3,627 trades at -1.741 R, MFE 0.78
    (`first-pullback-edge/reports/final_report.md` §10).
    """
    t = pd.read_parquet(FPE / "data" / "trades.parquet")
    t = t[(t["variant"] == "A")
          & (t["cost_model"] == cost_model)
          & (t["experiment"] == "exp1_common_exits")
          & (t["ambiguity_policy"] == ambiguity)]
    return t[COLS].sort_values(["day", "sym", "setup_ts"]).reset_index(drop=True)


def placebo(variant: str = "base_A") -> pd.DataFrame:
    p = pd.read_parquet(FPE / "data" / "placebo_trades.parquet")
    p = p[p["variant"] == variant]
    return p[COLS].sort_values(["day", "sym", "setup_ts"]).reset_index(drop=True)
