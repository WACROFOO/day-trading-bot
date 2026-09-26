"""Every plan the live desk's detector arms, over every symbol-day in the
store, computed once and saved (`data/cache/edge/desk_plans.parquet`).

This is the desk's own entry — `momentum_platform.pullback.FirstPullbackDetector`
through `backtest_recent.plans_for_day` with the live conventions (VWAP
anchored at 04:00 with pre-market volume, A10 stop-limit, realistic fills) —
so every family that varies selection, stops or exits around it is testing the
bot that actually runs, not a re-implementation.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

from edge_hunt.data import ET, STORE, Store  # noqa: E402

GATES = ("price", "rising", "vwap", "ema9", "macd", "volume")
_S = None


def rows_for(store: Store, i: int):
    r = store.sd.iloc[i]
    m, a = store.bars(i)
    base = datetime.fromisoformat(f"{r['day']}T04:00:00").replace(tzinfo=ET)
    return [(base + timedelta(minutes=int(mm)), *map(float, a[k])) for k, mm in enumerate(m)], m


def _init():
    global _S
    _S = Store()


def _run(ids):
    import backtest_recent as E
    out = []
    for i in ids:
        r = _S.sd.iloc[i]
        rows, m = rows_for(_S, i)
        pc = r["prev_close"] if r["prev_close"] == r["prev_close"] and r["prev_close"] > 0 else rows[0][1]
        cap = {}

        def hook(rec, ent, fill):
            cap[(rec["t"], rec["entry"], rec["stop"])] = ent[0][0]
        for p in E.plans_for_day(r["sym"], rows, pc, desk_vwap=True, gap_miss=True, hook=hook):
            t = p["ts"]
            tm = (t.hour - 4) * 60 + t.minute
            fts = cap.get((p["t"], p["entry"], p["stop"]))
            fm = (fts.hour - 4) * 60 + fts.minute if fts is not None else -1
            out.append({"sid": i, "day": r["day"], "sym": r["sym"], "plan_min": tm, "fill_min": fm,
                        "window": p["window"], "entry": p["entry"], "stop": p["stop"], "fill": p.get("fill", np.nan),
                        "touched": p["touched"], "gap_missed": p["gap_missed"],
                        "red": sum(1 << GATES.index(g) for g in p["red"]),
                        "pb_index": p["pb_index"], "cum_vol": p["cum_vol"],
                        "pm_high": p["pm_high"] if p["pm_high"] is not None else np.nan,
                        "hod_before": p["hod_before"] if p["hod_before"] is not None else np.nan,
                        "gain": p["gain"] if p["gain"] is not None else np.nan,
                        "trail_desk": p.get("trail", np.nan), "trail_desk_net": p.get("trail_net", np.nan)})
    return out


def build(workers: int = 4, limit: int | None = None) -> pd.DataFrame:
    n = len(pd.read_parquet(STORE / "symdays.parquet", columns=["day"]))
    ids = list(range(n if limit is None else min(n, limit)))
    chunks = [ids[k::workers * 8] for k in range(workers * 8)]
    rows = []
    with ProcessPoolExecutor(workers, initializer=_init) as ex:
        for part in ex.map(_run, chunks):
            rows += part
    df = pd.DataFrame(rows).sort_values(["day", "plan_min", "sym"]).reset_index(drop=True)
    if limit is None:
        df.to_parquet(STORE / "desk_plans.parquet", index=False)
    return df


if __name__ == "__main__":
    import time
    t0 = time.time()
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    df = build(limit=lim)
    print(f"{len(df)} plans · {int(df.touched.sum())} filled · {time.time() - t0:.0f}s")
