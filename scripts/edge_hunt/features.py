"""Point-in-time features. Every value for a decision at minute t (the close
of the bar stamped t) is built from bars stamped <= t, news created <= the
close of that bar, SEC figures FILED before the day, and earlier sessions.

Dense per-symbol-day grids (720 minutes, 04:00-15:59 ET) make every lookup
O(1): cumulative volume, cumulative dollar volume, last close (forward-filled)
and running high. `tests/test_edge_hunt.py` truncates the bars after t and
checks that nothing changes.
"""
from __future__ import annotations

import json
from bisect import bisect_right
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from edge_hunt.data import ET, STORE, Store, minute

NEWS = STORE / "news"
SEC = STORE / "sec"


class Grid:
    def __init__(self, store: Store):
        n = len(store.sd)
        self.cumvol = np.zeros((n, 720)); self.cumdv = np.zeros((n, 720))
        self.close = np.full((n, 720), np.nan); self.high = np.full((n, 720), np.nan)
        self.vol = np.zeros((n, 720))
        for i in range(n):
            m, a = store.bars(i)
            v = np.zeros(720); dv = np.zeros(720); c = np.full(720, np.nan); h = np.full(720, np.nan)
            v[m] = a[:, 4]; dv[m] = a[:, 4] * a[:, 3]; c[m] = a[:, 3]; h[m] = a[:, 1]
            self.vol[i] = v
            self.cumvol[i] = np.cumsum(v); self.cumdv[i] = np.cumsum(dv)
            self.close[i] = pd.Series(c).ffill().to_numpy()
            self.high[i] = pd.Series(h).ffill().cummax().to_numpy()

    def dv_last(self, i: int, t: int, span: int = 5) -> float:
        """Dollar volume of the `span` bars ending at t (inclusive)."""
        lo = t - span
        return float(self.cumdv[i, t] - (self.cumdv[i, lo] if lo >= 0 else 0.0))


def sessions(store: Store) -> list[str]:
    return sorted(store.sd["day"].unique())


def prev_session(days: list[str], day: str) -> str:
    k = bisect_right(days, day) - 2
    return days[k] if k >= 0 else (date.fromisoformat(day) - timedelta(days=1)).isoformat()


def _utc(day: str, mins: int) -> datetime:
    return (datetime.fromisoformat(f"{day}T04:00:00").replace(tzinfo=ET) + timedelta(minutes=mins)).astimezone(timezone.utc)


class News:
    """Alpaca headlines per (day, symbol), as (created_utc) sorted."""

    def __init__(self):
        self.cache: dict[str, dict[str, list[datetime]]] = {}

    def _load(self, day: str) -> dict[str, list[datetime]]:
        if day not in self.cache:
            f = NEWS / f"{day}.json"
            by: dict[str, list[datetime]] = {}
            if f.exists():
                for n in json.loads(f.read_text()):
                    t = datetime.fromisoformat(n["t"].replace("Z", "+00:00"))
                    for s in n.get("s") or []:
                        by.setdefault(s, []).append(t)
            for s in by:
                by[s].sort()
            self.cache[day] = by
        return self.cache[day]

    def available(self, day: str) -> bool:
        return (NEWS / f"{day}.json").exists()

    def count(self, day: str, sym: str, since: datetime, until: datetime) -> int:
        ts = self._load(day).get(sym, [])
        return sum(1 for t in ts if since < t <= until)


class Shares:
    """SEC shares outstanding, point-in-time: the latest value FILED before
    the day, no older than 400 days. None when unmapped (delisted names are
    mostly unmapped — a survivorship bias stated in the report)."""

    def __init__(self):
        self.rows: dict[str, list[tuple[str, float]]] = {}

    def _load(self, sym: str):
        if sym not in self.rows:
            f = SEC / f"{sym}.json"
            out = []
            if f.exists():
                for r in json.loads(f.read_text()).get("rows", []):
                    if r.get("filed") and r.get("val"):
                        out.append((r["filed"], float(r["val"]), r["c"]))
            out.sort()
            self.rows[sym] = out
        return self.rows[sym]

    def at(self, sym: str, day: str) -> float | None:
        cut = (date.fromisoformat(day) - timedelta(days=400)).isoformat()
        best = None
        for filed, val, concept in self._load(sym):
            if filed >= day:
                break
            if filed >= cut and val > 0:
                if best is None or concept == "dei" or filed >= best[0]:
                    best = (filed, val)
        return best[1] if best else None


def former_runner(store: Store, grid: Grid, lookback: int = 250, run: float = 0.5) -> np.ndarray:
    """For each symbol-day: did the SAME symbol appear in the universe in the
    previous `lookback` sessions and reach +run over its previous close
    (session high, 04:00-16:00)? Only earlier sessions are read."""
    sd = store.sd
    days = sessions(store); pos = {d: k for k, d in enumerate(days)}
    runmax = np.nanmax(grid.high, axis=1) / sd["prev_close"].to_numpy() - 1
    last_run: dict[str, int] = {}
    out = np.zeros(len(sd), bool)
    order = np.argsort(sd["day"].to_numpy(), kind="stable")
    k = 0
    while k < len(order):
        d = sd["day"].iat[order[k]]
        j = k
        while j < len(order) and sd["day"].iat[order[j]] == d:
            j += 1
        for idx in order[k:j]:
            s = sd["sym"].iat[idx]
            if s in last_run and pos[d] - last_run[s] <= lookback:
                out[idx] = True
        for idx in order[k:j]:
            if runmax[idx] >= run:
                last_run[sd["sym"].iat[idx]] = pos[d]
        k = j
    return out


def session_rank(store: Store, grid: Grid, sid: int, t: int) -> tuple[int, int]:
    """(rank by cumulative dollar volume at t among the session's universe
    names, number of names up >= 30 % at t)."""
    day = store.sd["day"].iat[sid]
    peers = store.sd.index[store.sd["day"] == day].to_numpy()
    dv = grid.cumdv[peers, t]
    rank = int((dv > grid.cumdv[sid, t]).sum()) + 1
    pc = store.sd["prev_close"].to_numpy()[peers]
    gain = grid.close[peers, t] / pc - 1
    hot = int(np.nansum(gain >= 0.30))
    return rank, hot


def plan_features(store: Store, grid: Grid, plans: pd.DataFrame) -> pd.DataFrame:
    """One row per plan, aligned with `plans`, decision minute = plan_min."""
    news, shares = News(), Shares()
    days = sessions(store)
    fr = former_runner(store, grid)
    sd = store.sd
    by_day = {d: g.index.to_numpy() for d, g in sd.groupby("day")}
    out = []
    pc_all = sd["prev_close"].to_numpy(); dv20 = sd["dv20"].to_numpy()
    for p in plans.itertuples(index=False):
        i, t = int(p.sid), int(p.plan_min)
        pc = pc_all[i]
        pm_t = min(t, minute(9, 29))
        peers = by_day[p.day]
        dvs = grid.cumdv[peers, t]
        gains = grid.close[peers, t] / pc_all[peers] - 1
        first = np.argmax(grid.high[i] >= 1.10 * pc) if np.nanmax(grid.high[i]) >= 1.10 * pc else -1
        prev = prev_session(days, p.day)
        since = _utc(prev, minute(16, 0)) if prev < p.day else _utc(p.day, 0)
        until = _utc(p.day, t + 1)
        n_news = news.count(p.day, p.sym, since, until) if news.available(p.day) else -1
        sh = shares.at(p.sym, p.day)
        out.append({
            "pm_vol": float(grid.cumvol[i, pm_t]) if t >= 0 else 0.0,
            "cum_dv": float(grid.cumdv[i, t]),
            "rvol": float(grid.cumvol[i, t] / (dv20[i] / pc)) if dv20[i] > 0 and pc > 0 else np.nan,
            "dv5": grid.dv_last(i, t, 5),
            "rank_dv": int((dvs > grid.cumdv[i, t]).sum()) + 1,
            "n_session": int(len(peers)),
            "hot30": int(np.nansum(gains >= 0.30)),
            "first_move_min": int(first) if 0 <= first <= t else -1,
            "news_n": n_news,
            "shares_out": sh if sh is not None else np.nan,
            "former_runner": bool(fr[i]),
        })
    return pd.DataFrame(out, index=plans.index)
