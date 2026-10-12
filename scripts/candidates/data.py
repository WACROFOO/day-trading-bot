"""Symbol-days for the candidate runner, one session at a time (memory stays flat).

Two sources:

  history  the preregistered one: `research/first-pullback-edge/data/candidate_days.csv`
           (reverse-split rows removed, as `edge_hunt.data.universe_rows`) and Alpaca SIP
           1-minute bars 04:00-16:00 ET from `data/cache/history/{day}.json`. A session
           missing from the cache is fetched with `backtest_history.fetch_day` when Alpaca
           keys are in the environment or `.env` (the Mac); otherwise it is counted missing.
  daily    the exported desk days of `research/daily/` (04:00-12:00 bars) — a smoke test of
           the plumbing, never evidence.

A `SymbolDay` holds plain lists — m (minutes since 04:00 ET), o, h, l, c, v — and the
facts known at 09:30: the previous close, the official open, the prior 20-day dollar
volume. Derived series are causal: the value at bar k reads bars <= k only.
"""
from __future__ import annotations

import csv
import json
import sys
from bisect import bisect_left
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

UNIVERSE_CSV = ROOT / "research" / "first-pullback-edge" / "data" / "candidate_days.csv"
HISTORY = ROOT / "data" / "cache" / "history"
DAILY = ROOT / "research" / "daily"
ET = ZoneInfo("America/New_York")

# research/strategy-candidates/PREREGISTRATION.md §4 — fixed before any run
WINDOW = ("2021-01-01", "2026-08-21")
TRAIN_END, VALID_END = "2022-12-31", "2023-12-31"
OLDER = ("2016-01-01", "2020-12-31")
MIN_BARS = 40


def minute(hh: int, mm: int) -> int:
    """Minutes since 04:00 ET."""
    return (hh - 4) * 60 + mm


RTH = minute(9, 30)


def split_of(day: str) -> str:
    if day < WINDOW[0]:
        return "older"
    if day <= TRAIN_END:
        return "train"
    if day <= VALID_END:
        return "valid"
    return "holdout"


def _f(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


@dataclass
class SymbolDay:
    day: str
    sym: str
    pc: float                       # previous close
    open_px: float | None           # the official 09:30 open (universe), None if unknown
    dv20: float | None              # prior 20-day dollar volume (universe), None if unknown
    split: str
    m: list = field(default_factory=list)
    o: list = field(default_factory=list)
    h: list = field(default_factory=list)
    l: list = field(default_factory=list)
    c: list = field(default_factory=list)
    v: list = field(default_factory=list)
    _vwap: list | None = None

    def __len__(self) -> int:
        return len(self.m)

    @property
    def vwap(self) -> list:
        """04:00-anchored VWAP on the typical price, as `momentum_platform.indicators.vwap`."""
        if self._vwap is None:
            out, pv, vv = [], 0.0, 0.0
            for h, l, c, v in zip(self.h, self.l, self.c, self.v):
                pv += (h + l + c) / 3.0 * v
                vv += v
                out.append(pv / vv if vv > 0 else c)
            self._vwap = out
        return self._vwap

    def first_at(self, mm: int) -> int:
        """Index of the first bar stamped at or after minute `mm` (len(self) if none)."""
        return bisect_left(self.m, mm)

    def gap(self) -> float | None:
        """Gap at the open: the official open if known, else the first bar at or after 09:30."""
        px = self.open_px
        if px is None:
            k = self.first_at(RTH)
            px = self.o[k] if k < len(self) else None
        return px / self.pc - 1 if px and self.pc > 0 else None

    def dv5_before(self, k: int) -> float:
        """Dollar volume of the five bars before bar k — what the spread proxy reads at an
        order placed at bar k's open (`backtest_recent`'s dv5 at the plan bar)."""
        return sum(self.c[j] * self.v[j] for j in range(max(0, k - 5), k))


def symbol_day(day: str, sym: str, pc: float, raw: list, open_px=None, dv20=None, split=None) -> SymbolDay | None:
    """From Alpaca rows [t_utc_iso, o, h, l, c, v]; None when under MIN_BARS bars in 04:00-16:00."""
    noon = datetime.fromisoformat(f"{day}T12:00:00").replace(tzinfo=ET)
    off = int(noon.utcoffset().total_seconds() // 60)                # -240 (EDT) or -300 (EST)
    rows = []
    for t, o, h, l, c, v in raw:
        t = str(t)
        mm = int(t[11:13]) * 60 + int(t[14:16]) + off - 240
        if t[:10] != day:
            mm += 1440
        if 0 <= mm < 720:
            rows.append((mm, float(o), float(h), float(l), float(c), float(v or 0)))
    if len(rows) < MIN_BARS:
        return None
    rows.sort(key=lambda r: r[0])
    sd = SymbolDay(day, sym, pc, open_px, dv20, split or split_of(day))
    for mm, o, h, l, c, v in rows:
        if sd.m and mm == sd.m[-1]:
            continue                                                 # a duplicated stamp keeps its first bar
        sd.m.append(mm); sd.o.append(o); sd.h.append(h); sd.l.append(l); sd.c.append(c); sd.v.append(v)
    return sd


# ------------------------------------------------------------------ history (the preregistered source)
def universe(since: str = WINDOW[0], until: str = WINDOW[1], path: Path = UNIVERSE_CSV) -> dict[str, dict[str, dict]]:
    """{day: {sym: row}} — split days and reverse-split rows removed."""
    out: dict[str, dict[str, dict]] = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            d = r["day"]
            if d < since or d > until:
                continue
            if r.get("split_on_day") in ("True", "true", "1") or (r.get("reverse_split_ratio") or "").strip():
                continue
            if _f(r.get("prev_close")) is None or _f(r.get("prev_close")) <= 0:
                continue
            out.setdefault(d, {})[r["sym"]] = r
    return out


class History:
    """Reads `data/cache/history/{day}.json`; fetches what is missing when keys exist."""

    def __init__(self, cache: Path = HISTORY, fetch: bool = True):
        self.cache = Path(cache)
        self.client = None
        self.fetch_errors = 0
        if fetch:
            try:
                import backtest_history as BH
                from momentum_platform.datasources.alpaca_source import PLACEHOLDER
                c = BH.alpaca_client()
                if c.key_id and c.secret_key and not PLACEHOLDER.match(c.key_id):
                    self.client, self._bh = c, BH
            except Exception:                                            # noqa: BLE001
                self.client = None

    def rows(self, day: str, syms: list[str]) -> dict[str, list]:
        f = self.cache / f"{day}.json"
        have = json.loads(f.read_text()) if f.exists() else {}
        if self.client is not None and any(s not in have for s in syms):
            try:
                return self._bh.fetch_day(self.client, day, sorted(syms), self.cache)
            except Exception as exc:                                     # noqa: BLE001
                self.fetch_errors += 1
                if "401" in str(exc) or "403" in str(exc):
                    raise SystemExit(f"Alpaca refused the keys ({exc}); fix .env or run with --no-fetch")
        return {s: have.get(s) or [] for s in syms}


def history_days(uni: dict, hist: History, days: list[str] | None = None, coverage: dict | None = None):
    """Yield (day, [SymbolDay]) session by session. `coverage[split]` counts
    [universe rows, rows with >= MIN_BARS bars]."""
    for d in (days if days is not None else sorted(uni)):
        syms = sorted(uni[d])
        raw = hist.rows(d, syms)
        out = []
        for s in syms:
            r = uni[d][s]
            sd = symbol_day(d, s, float(r["prev_close"]), raw.get(s) or [], _f(r.get("open_px")),
                            _f(r.get("prior_dollar_volume_20d")))
            if coverage is not None:
                cv = coverage.setdefault(split_of(d), [0, 0])
                cv[0] += 1
                cv[1] += sd is not None
            if sd is not None:
                out.append(sd)
        yield d, out


# ------------------------------------------------------------------ daily (smoke test only)
SMOKE_TRAIN_END = "2026-10-01"


def daily_days(coverage: dict | None = None):
    """The exported desk days, through the Reddit replay's own readers. Split for the
    smoke test only: days to 2026-10-01 'train', later 'valid'; there is no holdout."""
    sys.path.insert(0, str(ROOT / "research" / "reddit-bot-rules-2026-10-12"))
    saved, sys.argv = sys.argv, sys.argv[:1]          # their_rules reads argv[1] as the repo root
    try:
        import their_rules as T
    finally:
        sys.argv = saved
    uni = T.universe()
    for d in sorted(uni):
        bars = T.bars_for_day(d)
        split = "train" if d <= SMOKE_TRAIN_END else "valid"
        out = []
        for sym in sorted(uni[d]):
            pc = uni[d][sym]["prev"]
            rows = bars.get(sym) or []
            if not pc or pc <= 0:
                continue
            raw = [(ts.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ"), o, h, l, c, v)
                   for ts, o, h, l, c, v in rows]
            sd = symbol_day(d, sym, float(pc), raw, None, None, split)
            if coverage is not None:
                cv = coverage.setdefault(split, [0, 0])
                cv[0] += 1
                cv[1] += sd is not None
            if sd is not None:
                out.append(sd)
        yield d, out
