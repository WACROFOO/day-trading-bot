#!/usr/bin/env python3
"""Price the Kronos probe before spending anything on it.

Same discipline as `first-pullback-edge/src/fetch_plan.py`: measure a small
batch, report throughput, extrapolate to the real run, and write the number
down. Estimating a transformer's cost from parameter counts is how you end up
surprised in either direction.

    python3 price_run.py --anchors 24 --paths 8 --batch 4

Reports seconds per anchor-path and what the full populations would cost on
this box, plus a stated GPU speedup band rather than a single invented number.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/user/shiyu-coder/kronos")

from src import anchors as anchor_src            # noqa: E402
from src.bars import context_window              # noqa: E402
from src.forecast import Forecaster, to_features  # noqa: E402
from model import Kronos, KronosTokenizer        # noqa: E402

CTX = 150
PRED = 30


def build(df, ctx_len: int, want: int):
    """Materialise up to `want` usable anchors; count why the rest dropped."""
    out, dropped = [], 0
    for row in df.itertuples():
        rows = context_window(row.sym, row.day, int(row.setup_ts), ctx_len)
        if rows is None:
            dropped += 1
            continue
        out.append(dict(sym=row.sym, day=row.day, anchor_ts=int(row.setup_ts),
                        ctx=to_features(rows),
                        ctx_ts=[int(r[0]) for r in rows],
                        span_min=(rows[-1][0] - rows[0][0]) / 60.0,
                        entry=float(row.entry_fill),
                        risk=float(row.risk_per_share),
                        net_r=float(row.net_r), mfe_r=float(row.mfe_r)))
        if len(out) >= want:
            break
    return out, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchors", type=int, default=24)
    ap.add_argument("--paths", type=int, default=8)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--ctx", type=int, default=CTX)
    ap.add_argument("--pred", type=int, default=PRED)
    ap.add_argument("--model", default="NeoQuasar/Kronos-small")
    ap.add_argument("--tokenizer", default="NeoQuasar/Kronos-Tokenizer-base")
    ap.add_argument("--threads", type=int, default=0)
    a = ap.parse_args()

    if a.threads:
        torch.set_num_threads(a.threads)

    print(f"box: {platform.processor() or 'x86_64'} · "
          f"{torch.get_num_threads()} torch threads · cuda="
          f"{torch.cuda.is_available()}")

    df = anchor_src.variant_a()
    print(f"variant A population: {len(df)} trades")

    t0 = time.time()
    items, dropped = build(df, a.ctx, a.anchors)
    t_build = time.time() - t0
    print(f"anchors materialised: {len(items)} (dropped {dropped} for "
          f"<{a.ctx} same-session bars) in {t_build:.1f}s")
    if not items:
        sys.exit("no usable anchors")
    spans = np.array([i["span_min"] for i in items])
    print(f"context span: median {np.median(spans):.0f} wall-minutes for "
          f"{a.ctx} bars (perfectly dense would be {a.ctx})")

    tok = KronosTokenizer.from_pretrained(a.tokenizer)
    mdl = Kronos.from_pretrained(a.model)
    fc = Forecaster(tok, mdl, device="cpu")
    n_params = sum(p.numel() for p in mdl.parameters())
    print(f"model: {a.model} · {n_params:,} params")

    # one tiny warm-up so lazy kernel init is not billed to the measurement
    fc.paths(np.stack([items[0]["ctx"]]), [items[0]["ctx_ts"]],
             [items[0]["anchor_ts"]], pred_len=2, n_paths=1)

    timings = []
    for s in range(0, len(items), a.batch):
        chunk = items[s:s + a.batch]
        t0 = time.time()
        p = fc.paths(np.stack([c["ctx"] for c in chunk]),
                     [c["ctx_ts"] for c in chunk],
                     [c["anchor_ts"] for c in chunk],
                     pred_len=a.pred, n_paths=a.paths)
        dt = time.time() - t0
        timings.append(dt)
        print(f"  batch {s // a.batch + 1}: {len(chunk)} anchors x {a.paths} "
              f"paths = {len(chunk) * a.paths} rollouts in {dt:.1f}s "
              f"({dt / (len(chunk) * a.paths):.2f}s per rollout) "
              f"shape={p.shape}", flush=True)

    total = sum(timings)
    rollouts = len(items) * a.paths
    per_rollout = total / rollouts
    per_anchor = per_rollout * a.paths

    print(f"\nMEASURED on this box: {per_rollout:.3f}s per rollout "
          f"({a.pred} bars, ctx {a.ctx}), {per_anchor:.2f}s per anchor at "
          f"{a.paths} paths")

    pops = {"variant A trades": 3627, "qualified ticker-days": 8505,
            "random-entry baseline": 42510}
    proj = {}
    for name, n in pops.items():
        for np_ in (8, 20):
            hrs = n * np_ * per_rollout / 3600.0
            proj[f"{name} @ {np_} paths"] = round(hrs, 1)
            print(f"  {name:24s} @ {np_:2d} paths: {hrs:8.1f} CPU-hours")

    out = dict(
        measured_on=dict(threads=torch.get_num_threads(), device="cpu",
                         cuda=torch.cuda.is_available()),
        model=a.model, params=int(n_params),
        ctx=a.ctx, pred_len=a.pred, paths=a.paths, batch=a.batch,
        anchors_timed=len(items), anchors_dropped=dropped,
        context_span_median_min=float(np.median(spans)),
        seconds_per_rollout=round(per_rollout, 4),
        seconds_per_anchor=round(per_anchor, 3),
        cpu_hours_projection=proj,
    )
    (ROOT / "results" / "pricing.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {ROOT / 'results' / 'pricing.json'}")


if __name__ == "__main__":
    main()
