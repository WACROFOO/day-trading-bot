"""1-minute bar history: chunked fetching, on-disk archive, session summaries.

Yahoo only serves ~30 calendar days of 1-minute data and caps a single
request at 8 days, so "all of it" means: pull the trailing window in
chunks, then merge into an on-disk archive that keeps growing every time
you run it. Anything older than the first run is simply not available
from the free feed.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Callable, Iterator

import pandas as pd

MARKET_TZ = "America/New_York"

MAX_LOOKBACK_DAYS = 30   # Yahoo's 1m retention window
CHUNK_DAYS = 7           # per-request span (Yahoo caps at 8)

OHLCV = ["Open", "High", "Low", "Close", "Volume"]

REGULAR_OPEN = dt.time(9, 30)
REGULAR_CLOSE = dt.time(16, 0)


class NetworkError(RuntimeError):
    """yfinance download failed."""


# ------------------------------------------------------------------ windows

def chunk_windows(end: dt.datetime, days: int,
                  chunk_days: int = CHUNK_DAYS) -> Iterator[tuple[dt.datetime, dt.datetime]]:
    """Walk back from `end` in `chunk_days` slices, oldest window first."""
    days = max(1, min(days, MAX_LOOKBACK_DAYS))
    start = end - dt.timedelta(days=days)
    windows = []
    cursor = end
    while cursor > start:
        lo = max(start, cursor - dt.timedelta(days=chunk_days))
        windows.append((lo, cursor))
        cursor = lo
    return iter(reversed(windows))


# ------------------------------------------------------------------ shaping

def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Tz-aware (market time) index, OHLCV columns only, sorted, deduped."""
    if df is None or df.empty:
        return pd.DataFrame(columns=OHLCV,
                            index=pd.DatetimeIndex([], tz=MARKET_TZ, name="timestamp"))
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):          # yf.download shape
        out.columns = out.columns.get_level_values(0)
    idx = pd.DatetimeIndex(out.index)
    idx = idx.tz_localize("UTC") if idx.tz is None else idx
    out.index = idx.tz_convert(MARKET_TZ)
    out.index.name = "timestamp"
    for col in OHLCV:
        if col not in out.columns:
            out[col] = pd.NA
    out = out[OHLCV].apply(pd.to_numeric, errors="coerce")
    out = out[~out.index.duplicated(keep="last")].sort_index()
    return out.dropna(subset=["Close"])


def merge(old: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """Union of two bar frames; on a timestamp collision the new bar wins."""
    old, new = normalize(old), normalize(new)
    if old.empty:
        return new
    if new.empty:
        return old
    return normalize(pd.concat([old, new]))


# ------------------------------------------------------------------ fetching

def _yf_fetch(symbol: str, start: dt.datetime, end: dt.datetime,
              prepost: bool) -> pd.DataFrame:
    import yfinance as yf
    return yf.Ticker(symbol.upper()).history(
        start=start, end=end, interval="1m", prepost=prepost, auto_adjust=False,
    )


def fetch_1m(symbol: str, days: int = MAX_LOOKBACK_DAYS, *,
             prepost: bool = True,
             now: dt.datetime | None = None,
             chunk_days: int = CHUNK_DAYS,
             fetch: Callable[..., pd.DataFrame] | None = None,
             progress_cb: Callable[[int, int, str], None] | None = None) -> pd.DataFrame:
    """Every 1-minute bar Yahoo still has for `symbol`, oldest to newest.

    Chunks the request because Yahoo refuses 1m spans longer than 8 days.
    A chunk that comes back empty is normal (holidays, halted names) and is
    skipped; every chunk failing raises NetworkError.
    """
    fetch = fetch or _yf_fetch
    end = now or dt.datetime.now(dt.timezone.utc)
    windows = list(chunk_windows(end, days, chunk_days))
    frames, failures = [], []
    for i, (lo, hi) in enumerate(windows, start=1):
        if progress_cb:
            progress_cb(i, len(windows),
                        f"{symbol.upper()} {lo:%Y-%m-%d} -> {hi:%Y-%m-%d}")
        try:
            frames.append(normalize(fetch(symbol, lo, hi, prepost)))
        except Exception as exc:                        # noqa: BLE001 - reported below
            failures.append(f"{lo:%Y-%m-%d}..{hi:%Y-%m-%d}: {exc}")
    if failures and len(failures) == len(windows):
        raise NetworkError(f"all {len(windows)} chunk(s) failed — " + "; ".join(failures))
    out = normalize(pd.concat(frames)) if frames else normalize(None)
    return out


# ------------------------------------------------------------------ archive

def archive_path(root: Path, symbol: str) -> Path:
    return Path(root) / f"{symbol.upper()}_1m.csv"


def load_archive(path: Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return normalize(None)
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return normalize(df)


def save_archive(df: pd.DataFrame, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalize(df).to_csv(path)
    return path


# ------------------------------------------------------------------ summaries

def session_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per trading day: bar count, span, OHLC and volume."""
    df = normalize(df)
    if df.empty:
        return pd.DataFrame(columns=["date", "bars", "first_bar", "last_bar",
                                     "open", "high", "low", "close", "volume"])
    g = df.groupby(df.index.date)
    out = pd.DataFrame({
        "bars": g.size(),
        "first_bar": g.apply(lambda x: x.index.min().strftime("%H:%M")),
        "last_bar": g.apply(lambda x: x.index.max().strftime("%H:%M")),
        "open": g["Open"].first(),
        "high": g["High"].max(),
        "low": g["Low"].min(),
        "close": g["Close"].last(),
        "volume": g["Volume"].sum(),
    })
    out.index.name = "date"
    return out.reset_index()


def missing_regular_minutes(df: pd.DataFrame) -> pd.DataFrame:
    """Per-day count of 9:30-15:59 minutes with no bar (thin-tape gaps)."""
    df = normalize(df)
    if df.empty:
        return pd.DataFrame(columns=["date", "missing_minutes"])
    reg = df.between_time(REGULAR_OPEN, dt.time(15, 59))
    rows = []
    for day, chunk in reg.groupby(reg.index.date):
        expected = pd.date_range(
            pd.Timestamp(day).tz_localize(MARKET_TZ) + pd.Timedelta(hours=9, minutes=30),
            periods=390, freq="1min",
        )
        rows.append({"date": day,
                     "missing_minutes": int(len(expected.difference(chunk.index)))})
    return pd.DataFrame(rows)
