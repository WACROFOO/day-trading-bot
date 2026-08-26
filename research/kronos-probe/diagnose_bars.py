#!/usr/bin/env python3
"""Are the predicted candles even valid candles?

Kronos reconstructs open/high/low/close through a quantiser that was trained
on OHLC but does not CONSTRAIN it: nothing in the decoder enforces
high >= max(open, close) or low <= min(open, close). Their own downstream
never notices, because every signal in the bundled qlib backtest is built
from the close column alone.

This probe reads the predicted high and low directly, so an inconsistent bar
is not a cosmetic defect — it is the input to the barrier test. Measure the
rate before trusting anything built on it.

    python3 diagnose_bars.py --anchors 8 --paths 8
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/user/shiyu-coder/kronos")

from src import anchors as anchor_src          # noqa: E402
from src.bars import context_window            # noqa: E402
from src.forecast import Forecaster, to_features  # noqa: E402
from model import Kronos, KronosTokenizer      # noqa: E402

O, H, L, C, V, A = range(6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchors", type=int, default=8)
    ap.add_argument("--paths", type=int, default=8)
    ap.add_argument("--ctx", type=int, default=150)
    ap.add_argument("--pred", type=int, default=30)
    ap.add_argument("--seed", type=int, default=20260826)
    a = ap.parse_args()

    rng = np.random.default_rng(a.seed)
    df = anchor_src.variant_a()
    items = []
    for i in rng.permutation(len(df)):
        row = df.iloc[int(i)]
        rows = context_window(row.sym, row.day, int(row.setup_ts), a.ctx)
        if rows is None:
            continue
        items.append(dict(ctx=to_features(rows),
                          ctx_ts=[int(r[0]) for r in rows],
                          anchor_ts=int(row.setup_ts)))
        if len(items) >= a.anchors:
            break

    fc = Forecaster(KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base"),
                    Kronos.from_pretrained("NeoQuasar/Kronos-small"), device="cpu")
    p = fc.paths(np.stack([c["ctx"] for c in items]),
                 [c["ctx_ts"] for c in items],
                 [c["anchor_ts"] for c in items],
                 pred_len=a.pred, n_paths=a.paths)

    o, h, l, c, v = p[..., O], p[..., H], p[..., L], p[..., C], p[..., V]
    n = o.size
    checks = {
        "high < low": (h < l),
        "high < open": (h < o),
        "high < close": (h < c),
        "low > open": (l > o),
        "low > close": (l > c),
        "negative volume": (v < 0),
        "non-positive price": (c <= 0),
    }
    report = {k: dict(count=int(m.sum()), pct=round(100.0 * m.sum() / n, 3))
              for k, m in checks.items()}
    any_bad = np.zeros_like(h, dtype=bool)
    for m in checks.values():
        any_bad |= m
    report["ANY inconsistency"] = dict(count=int(any_bad.sum()),
                                       pct=round(100.0 * any_bad.sum() / n, 3))
    report["_bars_checked"] = int(n)

    print(json.dumps(report, indent=2))
    (ROOT / "results" / "bar_validity.json").write_text(json.dumps(report, indent=2))

    if report["ANY inconsistency"]["pct"] > 1.0:
        print("\nWARNING: predicted candles are not reliably valid candles.\n"
              "The barrier test reads high and low directly, so this rate is\n"
              "a ceiling on how much any downstream number can be trusted.")


if __name__ == "__main__":
    main()
