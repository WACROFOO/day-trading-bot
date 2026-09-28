#!/usr/bin/env python3
"""The point-in-time runner universe (research/ross-trades/).

What a live "running up" scanner could have shown at every minute, from bars
only: every name whose last price at minute t is >= +X % over its previous
close. Built from data/cache/ross/pit/{day}.json (1-minute bars 04:00-12:00 ET
for every runner day, see ross.fetch_pit), previous closes and 20-day volume
from the raw daily bars, split days removed by Alpaca's corporate actions.

    python3 scripts/edge_hunt/pit.py build     # -> data/cache/ross/pit_store/

Arrays (like edge_hunt.data): minute (0 = 04:00 … 479 = 11:59), o h l c v per
bar; one row per symbol-day with day, sym, prev_close, avg20_volume, [start, end).
Membership in the scanner is decided at minute t from bars stamped <= t only.
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from edge_hunt.data import ET, split_of  # noqa: E402

CACHE = ROOT / "data" / "cache" / "ross"
STORE = CACHE / "pit_store"


def _day(args):
    day, meta = args
    f = CACHE / "pit" / f"{day}.json"
    if not f.exists():
        return day, []
    raw = json.loads(f.read_text())
    noon = datetime.fromisoformat(f"{day}T12:00:00").replace(tzinfo=ET)
    off = int(noon.utcoffset().total_seconds() // 60)
    out = []
    for sym, rows in raw.items():
        if sym not in meta or len(rows) < 5:
            continue
        m = np.array([int(t[11:13]) * 60 + int(t[14:16]) + off - 240 for t, *_ in rows], np.int16)
        a = np.array([r[1:] for r in rows], np.float64)
        keep = (m >= 0) & (m < 480)
        if keep.sum() < 5:
            continue
        m, a = m[keep], a[keep]
        order = np.argsort(m, kind="stable")
        out.append((sym, m[order], a[order], meta[sym]))
    return day, out


def build(workers: int = 4) -> None:
    rd = pd.read_parquet(CACHE / "runner_days.parquet")
    rd = rd[rd["v"] >= 3e5]
    # 20-day average daily volume BEFORE the day (point-in-time), from the daily bars
    avg20 = {}
    for sym in rd["sym"].unique():
        f = CACHE / "daily" / f"{sym}.json"
        d = pd.DataFrame(json.loads(f.read_text()), columns=["day", "o", "h", "l", "c", "v"]).drop_duplicates("day").sort_values("day")
        d["avg20"] = d["v"].shift(1).rolling(20, min_periods=5).mean()
        avg20.update({(sym, dd): a for dd, a in zip(d["day"], d["avg20"])})
    meta = {}
    for r in rd.itertuples():
        meta.setdefault(r.day, {})[r.sym] = (float(r.pc), float(avg20.get((r.sym, r.day), np.nan)), float(r.v))
    days = sorted(meta)
    STORE.mkdir(parents=True, exist_ok=True)
    mins, arrs, rows, pos = [], [], [], 0
    with ProcessPoolExecutor(workers) as ex:
        for day, items in ex.map(_day, [(d, meta[d]) for d in days], chunksize=8):
            for sym, m, a, (pc, a20, dv) in items:
                rows.append({"day": day, "sym": sym, "prev_close": pc, "avg20_volume": a20, "day_volume": dv,
                             "start": pos, "end": pos + len(m)})
                mins.append(m); arrs.append(a.astype(np.float32)); pos += len(m)
    np.save(STORE / "minute.npy", np.concatenate(mins))
    np.save(STORE / "ohlcv.npy", np.concatenate(arrs))
    sd = pd.DataFrame(rows)
    sd["split"] = sd["day"].map(split_of)
    sd.to_parquet(STORE / "symdays.parquet", index=False)
    print(f"{len(sd)} symbol-days · {pos:,} bars · {sd['day'].nunique()} sessions")


class Pit:
    def __init__(self):
        self.minute = np.load(STORE / "minute.npy").astype(np.int64)
        a = np.load(STORE / "ohlcv.npy")
        self.o, self.h, self.l, self.c, self.v = (np.ascontiguousarray(a[:, j], dtype=np.float64) for j in range(5))
        self.sd = pd.read_parquet(STORE / "symdays.parquet")
        self.starts = self.sd["start"].to_numpy(np.int64); self.ends = self.sd["end"].to_numpy(np.int64)
        self.by_day = {d: g.index.to_numpy() for d, g in self.sd.groupby("day")}

    def grid(self, i: int, width: int = 480):
        """Dense per-minute arrays for one symbol-day: last close (ffill),
        cumulative volume, cumulative dollar volume, running high."""
        s, e = self.starts[i], self.ends[i]
        m = self.minute[s:e]
        c = np.full(width, np.nan); v = np.zeros(width); h = np.full(width, np.nan)
        c[m] = self.c[s:e]; v[m] = self.v[s:e]; h[m] = self.h[s:e]
        c = pd.Series(c).ffill().to_numpy(); hh = pd.Series(h).ffill().cummax().to_numpy()
        return c, np.cumsum(v), np.cumsum(np.nan_to_num(c) * v), hh



def selection_of_his_trades() -> pd.DataFrame:
    """For each of his rebuilt trades before 12:00: at the last completed
    minute before his entry, rank his name among every name then up >= 10 %
    over its previous close with a last price $1-30 and >= 50k shares traded
    since 04:00 (the runners a live scanner could list)."""
    out_dir = ROOT / "research" / "ross-trades"
    led = pd.read_csv(out_dir / "ledger_dated.csv", dtype=str, keep_default_na=False)
    rb = pd.read_csv(out_dir / "rebuild.csv")
    d = led.merge(rb, on="row_id")
    d = d[(d["tape"] == "ok") & d["entry_min"].notna()].sort_values("session_date")
    P = Pit()
    key = {(dd, s): i for i, (dd, s) in enumerate(zip(P.sd["day"], P.sd["sym"]))}
    rows = []
    cache: dict[str, dict] = {}
    for r in d.itertuples():
        t = int(r.entry_min) - 1
        if t < 0 or t >= 480:
            continue
        day = r.session_date
        if day not in P.by_day:
            rows.append({"row_id": r.row_id, "in_pit": False}); continue
        if day not in cache:
            g = {}
            for i in P.by_day[day]:
                c, cv, cdv, hh = P.grid(i)
                g[int(i)] = (c, cv, cdv)
            cache = {day: g}
        g = cache[day]
        feats = []
        for i, (c, cv, cdv) in g.items():
            pc = P.sd["prev_close"].iat[i]
            if not (c[t] == c[t]) or pc <= 0:
                continue
            gain = c[t] / pc - 1
            if gain < 0.10 or not (1 <= c[t] <= 30) or cv[t] < 5e4:
                continue
            v5 = cv[t] - (cv[t - 5] if t >= 5 else 0)
            a20 = P.sd["avg20_volume"].iat[i]
            feats.append((i, gain, cdv[t], v5, cv[t] / a20 if a20 == a20 and a20 > 0 else np.nan))
        me = key.get((day, r.ticker))
        rec = {"row_id": r.row_id, "in_pit": me is not None, "n_runners": len(feats)}
        if me is not None and any(f[0] == me for f in feats):
            f = pd.DataFrame(feats, columns=["i", "gain", "dv", "v5", "rvol"])
            for col, name in (("gain", "rank_gain"), ("dv", "rank_dv"), ("v5", "rank_vol5"), ("rvol", "rank_rvol")):
                rec[name] = int((f[col] > f.loc[f.i == me, col].iloc[0]).sum()) + 1
            rec["listed_as_runner"] = True
        else:
            rec["listed_as_runner"] = False
        rows.append(rec)
        if len(cache) > 1:
            cache = {}
    s = pd.DataFrame(rows)
    s.to_csv(out_dir / "selection.csv", index=False)
    return s


if __name__ == "__main__":
    if sys.argv[1:] == ["build"]:
        build()
    elif sys.argv[1:] == ["selection"]:
        print(selection_of_his_trades().describe().T.to_string())
