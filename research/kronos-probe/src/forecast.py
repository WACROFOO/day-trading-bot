"""Kronos inference that KEEPS the sample axis.

`KronosPredictor.predict` ends on `preds = np.mean(preds, axis=1)`
(model/kronos.py:467) — it averages the sampled OHLC paths in price space.
The mean of N paths has a lower high and a higher low than any single path,
which destroys the only quantity this project measures: did the high touch
+1R before the low touched the stop.

So the paths are kept. The trick that avoids forking their code: call
`auto_regressive_inference` with sample_count=1 and do the replication in the
batch dimension ourselves. Sampling is independent per batch row
(`torch.multinomial` over the flattened batch), so B anchors repeated N times
give B x N independent paths, and their averaging line becomes a no-op over
an axis of length 1.

Normalisation mirrors `predict()` exactly: per-anchor z-score over the
context window only, clip at +/-5, invert with the same statistics.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import torch

KRONOS_ROOT = Path("/home/user/shiyu-coder/kronos")
sys.path.insert(0, str(KRONOS_ROOT))

from model.kronos import auto_regressive_inference   # noqa: E402

ET = ZoneInfo("America/New_York")
CLIP = 5.0
# feature order is the tokenizer's: open, high, low, close, volume, amount
O, H, L, C, V, A = range(6)


def stamp(ts: int) -> tuple[int, int, int, int, int]:
    """(minute, hour, weekday, day, month) in EXCHANGE local time.

    Kronos' TemporalEmbedding indexes real calendar fields, so feeding UTC
    would put the US open at 13:30 and every learned session shape off by
    the offset.
    """
    d = dt.datetime.fromtimestamp(ts, ET)
    return d.minute, d.hour, d.weekday(), d.day, d.month


def to_features(rows: list[list]) -> np.ndarray:
    """[ts,o,h,l,c,v] -> [o,h,l,c,v,amount]; amount as predict() derives it."""
    out = np.empty((len(rows), 6), dtype=np.float32)
    for i, (_ts, o, h, l, c, v) in enumerate(rows):
        out[i] = (o, h, l, c, v, v * (o + h + l + c) / 4.0)
    return out


class Forecaster:
    def __init__(self, tokenizer, model, device="cpu", max_context=512):
        self.tokenizer = tokenizer.to(device).eval()
        self.model = model.to(device).eval()
        self.device = device
        self.max_context = max_context

    def paths(self, contexts: np.ndarray, context_ts: list[list[int]],
              anchor_ts: list[int], pred_len: int, n_paths: int,
              T: float = 1.0, top_p: float = 0.9, top_k: int = 0,
              verbose: bool = False) -> np.ndarray:
        """(B, n_paths, pred_len, 6) in ORIGINAL price units.

        contexts   (B, ctx, 6) features, every row the same length — the
                   autoregressive loop is one shared rollout over the batch.
        context_ts per-bar epoch seconds, for the temporal embedding.
        anchor_ts  last observed bar's epoch second, per anchor. The forecast
                   horizon is stamped as anchor + 1..pred_len minutes.
        """
        x = np.asarray(contexts, dtype=np.float32)
        b = x.shape[0]
        mean = x.mean(axis=1, keepdims=True)                    # (B, 1, 6)
        std = x.std(axis=1, keepdims=True)
        xn = np.clip((x - mean) / (std + 1e-5), -CLIP, CLIP)

        xs = np.array([[stamp(t) for t in row] for row in context_ts],
                      dtype=np.float32)                          # (B, ctx, 5)
        ys = np.array([[stamp(a + 60 * (i + 1)) for i in range(pred_len)]
                       for a in anchor_ts], dtype=np.float32)    # (B, pred, 5)

        def rep(arr):
            return np.repeat(arr, n_paths, axis=0)

        with torch.no_grad():
            preds = auto_regressive_inference(
                self.tokenizer, self.model,
                torch.from_numpy(rep(xn)).to(self.device),
                torch.from_numpy(rep(xs)).to(self.device),
                torch.from_numpy(rep(ys)).to(self.device),
                max_context=self.max_context, pred_len=pred_len, clip=CLIP,
                T=T, top_k=top_k, top_p=top_p, sample_count=1, verbose=verbose,
            )                                                    # (B*N, ctx+pred, 6)

        preds = preds[:, -pred_len:, :].reshape(b, n_paths, pred_len, 6)
        return preds * (std[:, None] + 1e-5) + mean[:, None]


def barrier_probabilities(paths: np.ndarray, entry: np.ndarray,
                          risk: np.ndarray) -> dict[str, np.ndarray]:
    """Reduce (B, N, T, 6) sampled paths to the decision this project needs.

    Walks each path bar by bar and asks which barrier the bar touched first,
    using the PREDICTED high and low — the columns their own downstream code
    never uses (`qlib_test.py` builds every signal from close alone).

    A bar that spans both barriers is scored as a loss, matching the
    pessimistic ambiguity policy the backtest already runs under: with only
    OHLC there is no evidence for the favourable ordering.
    """
    b, n, t, _ = paths.shape
    up = (entry + risk)[:, None]                    # (B, 1)
    dn = (entry - risk)[:, None]

    hi, lo = paths[:, :, :, H], paths[:, :, :, L]
    hit_up = hi >= up[:, :, None]
    hit_dn = lo <= dn[:, :, None]

    first_up = np.where(hit_up.any(axis=2), hit_up.argmax(axis=2), t + 1)
    first_dn = np.where(hit_dn.any(axis=2), hit_dn.argmax(axis=2), t + 1)
    win = first_up < first_dn                       # ties -> loss (pessimistic)

    close_r = (paths[:, :, -1, C] - entry[:, None]) / risk[:, None]
    mfe_r = (hi.max(axis=2) - entry[:, None]) / risk[:, None]
    mae_r = (entry[:, None] - lo.min(axis=2)) / risk[:, None]

    return dict(
        p_win=win.mean(axis=1),
        p_touch_up=hit_up.any(axis=2).mean(axis=1),
        exp_mfe_r=mfe_r.mean(axis=1),
        exp_mae_r=mae_r.mean(axis=1),
        exp_close_r=close_r.mean(axis=1),
        med_close_r=np.median(close_r, axis=1),
    )
