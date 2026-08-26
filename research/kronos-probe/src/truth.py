"""The realised barrier outcome, computed from bars that actually traded.

The parent study's `net_r` is the result of a full trade: a T1 scale, a
runner, a session-flat rule, commissions and slippage. Scoring a pure
P(+1R before -1R) against it would grade the model on a question it was
never asked.

So the matched truth is computed here from the forward tape under exactly
the rule the model's paths are reduced by: walk the next `horizon` bars, ask
which barrier was touched first, and score a bar that spans both as a loss.
The parent study's number stays in the output alongside it — they answer
different questions and both are worth seeing.
"""
from __future__ import annotations

import numpy as np

from .bars import forward_bars

TS, O, H, L, C, V = range(6)


def barrier_outcome(sym: str, day: str, anchor_ts: int, entry: float,
                    risk: float, horizon: int = 30) -> dict:
    """First-touch of entry +/- risk over the next `horizon` traded bars.

    Returns `outcome` in {win, loss, neither, no_data} — 'neither' when the
    horizon ran out (or the session ended) with no barrier touched, which is
    a real and common third case, not a loss in disguise.
    """
    rows = forward_bars(sym, day, anchor_ts, horizon)
    if not rows:
        return dict(outcome="no_data", bars_seen=0, t_win=None, t_loss=None,
                    fwd_mfe_r=np.nan, fwd_mae_r=np.nan, fwd_close_r=np.nan)

    up, dn = entry + risk, entry - risk
    t_win = t_loss = None
    for i, r in enumerate(rows):
        hit_up, hit_dn = r[H] >= up, r[L] <= dn
        if hit_up and hit_dn:                 # ambiguous bar -> pessimistic
            t_loss = i
            break
        if hit_dn:
            t_loss = i
            break
        if hit_up:
            t_win = i
            break

    highs = np.array([r[H] for r in rows], dtype=float)
    lows = np.array([r[L] for r in rows], dtype=float)
    outcome = "win" if t_win is not None else ("loss" if t_loss is not None
                                               else "neither")
    return dict(
        outcome=outcome,
        bars_seen=len(rows),
        t_win=t_win, t_loss=t_loss,
        fwd_mfe_r=float((highs.max() - entry) / risk),
        fwd_mae_r=float((entry - lows.min()) / risk),
        fwd_close_r=float((rows[-1][C] - entry) / risk),
    )


def attach(df, horizon: int = 30):
    """Add the matched truth columns to a probe result frame."""
    recs = [barrier_outcome(r.sym, r.day, int(r.anchor_ts), float(r.entry),
                            float(r.risk), horizon)
            for r in df.itertuples()]
    for k in recs[0]:
        df[f"true_{k}"] = [r[k] for r in recs]
    return df
