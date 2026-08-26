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

def _parent_module(name: str):
    """Import `first-pullback-edge/src/<name>.py` as `fpe_src.<name>`.

    Both studies name their package `src`, and this file already occupies
    that name, so a plain `from src.indicators import ...` resolves here and
    fails. The parent's modules also use relative imports (`from .data import
    Bar`), so loading a single file standalone fails too — it has to be
    registered as a package with a search path before its submodules resolve.
    """
    import importlib
    import importlib.util
    import sys

    if "fpe_src" not in sys.modules:
        pkg = importlib.util.module_from_spec(
            importlib.machinery.ModuleSpec("fpe_src", None, is_package=True))
        pkg.__path__ = [str(FPE / "src")]
        sys.modules["fpe_src"] = pkg
    return importlib.import_module(f"fpe_src.{name}")


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


def random_entries(n: int, seed: int, ctx_len: int = 150,
                   window=("09:35", "11:30")) -> list[dict]:
    """The study's random-entry baseline, rebuilt as scoreable anchors.

    `run.py::_baseline_random` keeps only day/net_r/mfe_r in its trade rows,
    so the anchors themselves were never stored. They are reconstructed here
    under the same rule — a random minute in 09:35-11:30 on a qualifying
    ticker-day, risk = 1 ATR — using the parent study's own SessionState so
    the ATR is the same causal, incremental one the backtest used.

    This is the arm that matters: the report's open question is why the
    RANDOM population reaches +1R more often than the pattern-selected one.
    """
    import datetime as dt
    import random

    from .bars import session_bars
    # The parent study's package is ALSO called `src`, and this file lives in
    # a `src` that is already imported — a plain `from src.data import Bar`
    # would resolve here and fail. Load its modules by path instead.
    Bar = _parent_module("data").Bar
    SessionState = _parent_module("indicators").SessionState

    lo = dt.time(*map(int, window[0].split(":")))
    hi = dt.time(*map(int, window[1].split(":")))

    q = pd.read_parquet(FPE / "data" / "scanned_ticker_days.parquet")
    q = q[q["qualified_intraday"] == True]      # noqa: E712
    rng = random.Random(seed)
    order = list(range(len(q)))
    rng.shuffle(order)

    out = []
    for i in order:
        row = q.iloc[i]
        rows = session_bars(row.sym, row.day)
        if len(rows) < ctx_len + 10:
            continue
        st = SessionState(row.sym, dt.date.fromisoformat(row.day),
                          prev_close=float(row.prev_close))
        snaps = [st.update(Bar(*r)) for r in rows]
        elig = [k for k, s in enumerate(snaps)
                if lo <= s.et.time() < hi and k >= ctx_len and s.atr
                and s.atr > 0 and k < len(snaps) - 5]
        if not elig:
            continue
        k = rng.choice(elig)
        s = snaps[k]
        out.append(dict(sym=row.sym, day=row.day, anchor_ts=int(rows[k][0]),
                        entry=float(s.bar.c), risk=float(s.atr),
                        pullback_number=-1))
        if len(out) >= n:
            break
    return out
