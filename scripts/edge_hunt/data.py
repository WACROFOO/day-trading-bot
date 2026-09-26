"""Compact bar store for the edge hunt.

The history cache (`data/cache/history/{day}.json`, Alpaca SIP 1-minute bars,
04:00-16:00 ET, raw prices) is ~560 MB of JSON; re-parsing it for every
experiment costs minutes. `build()` converts it once into flat numpy arrays:

    bars   minute (0 = 04:00 ET … 719 = 15:59), o, h, l, c, v — one row per bar
    sd     one row per symbol-day: day, sym, prev_close, universe columns, and
           [start, end) into the bar arrays

Nothing here decides anything; features and entries live elsewhere and only
ever read bars at or before their decision minute (tested in
tests/test_edge_hunt.py).
"""
from __future__ import annotations

import csv
import json
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "data" / "cache" / "history"
STORE = ROOT / "data" / "cache" / "edge"
UNIVERSE_CSV = ROOT / "research" / "first-pullback-edge" / "data" / "candidate_days.csv"
ET = ZoneInfo("America/New_York")

# The split, fixed in research/edge-hunt/PREREGISTRATION.md before any run.
TRAIN = ("2016-01-01", "2022-12-31")
VALID = ("2023-01-01", "2023-12-31")
HOLDOUT = ("2024-01-01", "2026-12-31")


def split_of(day: str) -> str:
    if day <= TRAIN[1]:
        return "train"
    if day <= VALID[1]:
        return "valid"
    return "holdout"


def minute(hh: int, mm: int) -> int:
    """Minutes since 04:00 ET."""
    return (hh - 4) * 60 + mm


def universe_rows() -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {}
    with open(UNIVERSE_CSV) as f:
        for r in csv.DictReader(f):
            if r.get("split_on_day") in ("True", "true", "1"):
                continue
            out.setdefault(r["day"], {})[r["sym"]] = r
    return out


def _fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def _parse_day(args):
    day, syms = args
    f = HISTORY / f"{day}.json"
    if not f.exists():
        return day, []
    raw = json.loads(f.read_text())
    noon = datetime.fromisoformat(f"{day}T12:00:00").replace(tzinfo=ET)
    off = int(noon.utcoffset().total_seconds() // 60)                # -240 or -300
    out = []
    for sym in syms:
        rows = raw.get(sym) or []
        if not rows:
            continue
        m = np.empty(len(rows), np.int16); a = np.empty((len(rows), 5), np.float64)
        k = 0
        for t, o, h, l, c, v in rows:
            if t[:10] != day and not t.startswith(day):
                # a bar stamped on the next UTC date is after 20:00 ET: outside 04:00-16:00
                pass
            hh, mi = int(t[11:13]), int(t[14:16])
            et_min = hh * 60 + mi + off
            mm = et_min - 240
            if t[:10] != day:
                mm += 1440
            if 0 <= mm < 720:
                m[k] = mm; a[k] = (o, h, l, c, v or 0); k += 1
        if k < 40:
            continue
        order = np.argsort(m[:k], kind="stable")
        out.append((sym, m[:k][order], a[:k][order]))
    return day, out


def build(workers: int = 4) -> None:
    uni = universe_rows()
    days = sorted(uni)
    STORE.mkdir(parents=True, exist_ok=True)
    mins, arrs, meta = [], [], []
    pos = 0
    with ProcessPoolExecutor(workers) as ex:
        for day, items in ex.map(_parse_day, [(d, sorted(uni[d])) for d in days], chunksize=8):
            for sym, m, a in items:
                r = uni[day][sym]
                meta.append({"day": day, "sym": sym, "prev_close": _fnum(r["prev_close"]),
                             "open_px": _fnum(r["open_px"]), "gap_pct": _fnum(r["gap_pct"]),
                             "dv20": _fnum(r["prior_dollar_volume_20d"]), "source": r.get("source", ""),
                             "start": pos, "end": pos + len(m)})
                mins.append(m); arrs.append(a); pos += len(m)
    bars_m = np.concatenate(mins); bars = np.concatenate(arrs)
    np.save(STORE / "bars_minute.npy", bars_m)
    np.save(STORE / "bars_ohlcv.npy", bars.astype(np.float64))
    sd = pd.DataFrame(meta)
    sd["split"] = sd["day"].map(split_of)
    sd.to_parquet(STORE / "symdays.parquet", index=False)
    print(f"{len(sd)} symbol-days · {len(bars_m):,} bars · {sd['day'].nunique()} sessions")


class Store:
    """Everything in memory: ~25k symbol-days, ~10M bars."""

    def __init__(self, path: Path = STORE):
        self.minute = np.load(path / "bars_minute.npy")
        self.ohlcv = np.load(path / "bars_ohlcv.npy")
        self.sd = pd.read_parquet(path / "symdays.parquet")

    def bars(self, i: int):
        r = self.sd.iloc[i]
        s, e = int(r["start"]), int(r["end"])
        return self.minute[s:e], self.ohlcv[s:e]


if __name__ == "__main__":
    build()
