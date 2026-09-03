"""NASDAQ universe scanner implementing the strategy §1 universe filter.

Fully local and free: symbol directory from nasdaqtrader.com, daily OHLCV
from yfinance. Free data is ~15 minutes delayed.

Filter (PARAMETERS.md §1): price $2–$20, day gain >= 10%,
rvol >= 5x the 50-day average volume, day volume >= 500,000 shares.
Float and news catalyst cannot be computed reliably from free data — they
are surfaced as manual-check columns instead of being silently dropped.

Coverage is reported alongside the results. A scan where most of the universe
failed to download looks identical to a quiet market — few or no passers — so
`scan()` records how many symbols actually returned usable bars and the CLI
refuses to present a degraded scan as a finished watchlist.
"""

from __future__ import annotations

import io
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "nasdaq_universe.csv"

# Strategy §1 defaults (PARAMETERS.md)
PRICE_MIN = 2.00
PRICE_MAX = 20.00
GAIN_PCT_MIN = 10.0
RVOL_MIN = 5.0
VOLUME_MIN = 500_000
FLOAT_MAX = 20_000_000  # not computed from free data — manual check

# 200 concurrent requests per chunk exhausts the default macOS file-descriptor
# limit and swamps DNS; most of the universe then fails to download.
CHUNK_SIZE = 50
DOWNLOAD_PERIOD = "3mo"
AVG_VOLUME_WINDOW = 50
USER_AGENT = "Mozilla/5.0 (scanner; local paper-trading bot)"

# Below this share of the universe returning bars, results are not a watchlist.
COVERAGE_MIN_PCT = 90.0


class NetworkError(RuntimeError):
    """Raised when the symbol directory cannot be downloaded and no cache exists."""


@dataclass(frozen=True)
class Coverage:
    """How much of the requested universe actually returned usable bars."""

    requested: int
    with_data: int

    @property
    def missing(self) -> int:
        return self.requested - self.with_data

    @property
    def pct(self) -> float:
        return 100.0 * self.with_data / self.requested if self.requested else 0.0

    @property
    def is_degraded(self) -> bool:
        return self.pct < COVERAGE_MIN_PCT

    def summary(self) -> str:
        return (f"{self.with_data:,}/{self.requested:,} symbols returned data "
                f"({self.pct:.1f}%); {self.missing:,} missing")


# ---------------------------------------------------------------- universe list

def parse_nasdaq_listed(text: str, include_etf: bool = False) -> pd.DataFrame:
    """Parse nasdaqlisted.txt content (pipe-delimited) into a symbol DataFrame.

    Drops test issues, the 'File Creation Time' trailer line, and (unless
    include_etf) ETFs. Pure function — no network.
    """
    df = pd.read_csv(io.StringIO(text), sep="|", dtype=str)
    df = df[df["Test Issue"] == "N"]
    if not include_etf:
        df = df[df["ETF"] == "N"]
    out = pd.DataFrame({
        "symbol": df["Symbol"].str.strip(),
        "name": df["Security Name"].str.strip(),
        "is_etf": df["ETF"] == "Y",
    })
    out = out[out["symbol"].notna() & (out["symbol"] != "")]
    return out.reset_index(drop=True)


def fetch_nasdaq_universe(include_etf: bool = False,
                          cache_path: Path | str = CACHE_PATH,
                          max_cache_age_days: int = 7) -> pd.DataFrame:
    """Download the official NASDAQ symbol directory, with a dated CSV cache.

    Falls back to the cache if the download fails. Raises NetworkError only
    when neither source is available.
    """
    cache_path = Path(cache_path)
    fetched_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        req = urllib.request.Request(NASDAQ_LISTED_URL,
                                     headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        df = parse_nasdaq_listed(text, include_etf=include_etf)
        df["fetched_date"] = fetched_date
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(cache_path, index=False)
        except OSError:
            pass  # cache is best-effort
        return df
    except (urllib.error.URLError, OSError, ValueError) as exc:
        if cache_path.exists():
            cached = pd.read_csv(cache_path, dtype=str)
            age_days = (datetime.now(timezone.utc).date()
                        - datetime.strptime(cached["fetched_date"].iloc[0],
                                            "%Y-%m-%d").date()).days
            if age_days > max_cache_age_days:
                raise NetworkError(
                    f"download failed ({exc}) and cache {cache_path} is "
                    f"{age_days} days old") from exc
            if not include_etf:
                cached = cached[cached["is_etf"].astype(str) != "True"]
            return cached.reset_index(drop=True)
        raise NetworkError(
            f"could not download {NASDAQ_LISTED_URL} ({exc}) and no cache "
            f"at {cache_path}") from exc


# ---------------------------------------------------------------- stats + filter (pure)

def compute_stats(bars: pd.DataFrame) -> dict | None:
    """Per-symbol scan stats from a daily OHLCV frame (last row = latest day).

    Returns None if there are fewer than 2 usable rows. Pure function.
    """
    bars = bars.dropna(subset=["Close"])
    if len(bars) < 2:
        return None
    last = bars.iloc[-1]
    prev_close = bars["Close"].iloc[-2]
    if not prev_close or pd.isna(prev_close) or prev_close <= 0:
        return None
    price = float(last["Close"])
    volume = float(last["Volume"]) if not pd.isna(last["Volume"]) else 0.0
    history = bars["Volume"].iloc[:-1].tail(AVG_VOLUME_WINDOW).dropna()
    avg_vol = float(history.mean()) if len(history) else float("nan")
    rvol = volume / avg_vol if avg_vol and not pd.isna(avg_vol) and avg_vol > 0 else float("nan")
    return {
        "price": price,
        "change_pct": (price / prev_close - 1.0) * 100.0,
        "volume": volume,
        "avg_volume_50d": avg_vol,
        "rvol": rvol,
    }


def apply_filters(stats: pd.DataFrame,
                  price_min: float = PRICE_MIN,
                  price_max: float = PRICE_MAX,
                  gain_pct_min: float = GAIN_PCT_MIN,
                  rvol_min: float = RVOL_MIN,
                  volume_min: float = VOLUME_MIN) -> pd.DataFrame:
    """Apply the §1 universe filter to a stats DataFrame (index = symbol).

    Adds pass/fail flag columns per criterion, keeps only symbols passing all
    computable criteria, sorts by rvol desc, and appends float_shares /
    catalyst manual-check columns (NaN — not reliably available for free).
    Pure function.
    """
    df = stats.copy()
    cols = ["symbol", "price", "change_pct", "volume", "rvol", "avg_volume_50d",
            "pass_price", "pass_gain", "pass_rvol", "pass_volume",
            "float_shares", "catalyst"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    df["pass_price"] = (df["price"] >= price_min) & (df["price"] <= price_max)
    df["pass_gain"] = df["change_pct"] >= gain_pct_min
    df["pass_rvol"] = df["rvol"] >= rvol_min
    df["pass_volume"] = df["volume"] >= volume_min
    passed = df[df[["pass_price", "pass_gain", "pass_rvol", "pass_volume"]].all(axis=1)]
    passed = passed.sort_values("rvol", ascending=False)
    passed["float_shares"] = float("nan")   # manual check — see module docstring
    passed["catalyst"] = None               # manual check
    return passed.reset_index().rename(columns={"index": "symbol"})


# ---------------------------------------------------------------- batch download

def _download_chunk(symbols: list[str], period: str) -> pd.DataFrame:
    return yf.download(tickers=" ".join(symbols), period=period, interval="1d",
                       group_by="ticker", threads=True, progress=False,
                       auto_adjust=False)


def _extract_symbol_frame(data: pd.DataFrame, symbol: str,
                          chunk_size: int) -> pd.DataFrame | None:
    """Pull one symbol's OHLCV frame out of a yf.download batch result.

    Handles both MultiIndex (ticker, field) and single-level columns, and
    tickers yfinance silently dropped.
    """
    if data is None or data.empty:
        return None
    if isinstance(data.columns, pd.MultiIndex):
        if symbol not in data.columns.get_level_values(0):
            return None
        frame = data[symbol]
    else:  # single ticker came back without the ticker level
        if chunk_size != 1:
            return None
        frame = data
    frame = frame.dropna(how="all")
    return frame if not frame.empty else None


def _collect_stats(symbols: list[str], chunk_size: int, period: str,
                   rows: dict[str, dict], progress_cb, label: str,
                   done_base: int, total: int) -> None:
    """Download `symbols` in chunks and add each one's stats to `rows`."""
    for start in range(0, len(symbols), chunk_size):
        chunk = symbols[start:start + chunk_size]
        try:
            data = _download_chunk(chunk, period)
        except Exception as exc:  # noqa: BLE001 - skip a bad chunk, keep scanning
            data = None
            if progress_cb:
                progress_cb(done_base + start + len(chunk), total,
                            f"chunk failed: {exc}")
        if data is not None:
            for sym in chunk:
                frame = _extract_symbol_frame(data, sym, len(chunk))
                if frame is None:
                    continue  # no data / dropped by yfinance
                stats = compute_stats(frame)
                if stats:
                    rows[sym] = stats
        if progress_cb:
            done = min(start + len(chunk), len(symbols))
            progress_cb(done_base + done, total, f"{label} {done}/{len(symbols)}")


def scan(symbols: list[str] | None = None,
         include_etf: bool = False,
         chunk_size: int = CHUNK_SIZE,
         period: str = DOWNLOAD_PERIOD,
         fetch_float: bool = False,
         retry_missing: bool = True,
         progress_cb=None,
         **thresholds) -> pd.DataFrame:
    """Scan the NASDAQ universe (or a given symbol list) against the §1 filter.

    Downloads daily OHLCV in chunks, computes stats, applies the filter.
    progress_cb(done, total, message) is called after each chunk for UIs.
    fetch_float=True queries Ticker.info['floatShares'] for passers only
    (one slow HTTP call per passer — off by default).
    retry_missing=True re-downloads symbols that returned nothing, in smaller
    chunks, since the usual cause is transient connection exhaustion.

    The returned frame carries a `Coverage` under `.attrs["coverage"]`. Check
    `is_degraded` before treating the result as a complete scan.
    """
    if symbols is None:
        symbols = fetch_nasdaq_universe(include_etf=include_etf)["symbol"].tolist()
    total = len(symbols)
    rows: dict[str, dict] = {}
    _collect_stats(symbols, chunk_size, period, rows, progress_cb,
                   "scanned", 0, total)

    missing = [s for s in symbols if s not in rows]
    if retry_missing and missing:
        if progress_cb:
            progress_cb(total, total, f"retrying {len(missing):,} with no data")
        _collect_stats(missing, max(1, chunk_size // 5), period, rows,
                       progress_cb, "retried", 0, len(missing))

    result = apply_filters(pd.DataFrame.from_dict(rows, orient="index"),
                           **thresholds)
    if fetch_float and not result.empty:
        result["float_shares"] = [
            _fetch_float_shares(sym) for sym in result["symbol"]
        ]
    result.attrs["coverage"] = Coverage(requested=total, with_data=len(rows))
    return result


def _fetch_float_shares(symbol: str) -> float:
    """Best-effort float from yfinance info; NaN when unavailable."""
    try:
        value = yf.Ticker(symbol).info.get("floatShares")
        return float(value) if value else float("nan")
    except Exception:  # noqa: BLE001 - float is a manual-check field anyway
        return float("nan")


def results_path(results_dir: Path | str, now: datetime | None = None) -> Path:
    """results/scanner_YYYY-MM-DD_HHMM.csv path used by the CLI."""
    now = now or datetime.now()
    path = Path(results_dir) / f"scanner_{now.strftime('%Y-%m-%d_%H%M')}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
