"""yfinance data wrappers with a small in-memory TTL cache."""

from __future__ import annotations

import time

import pandas as pd
import yfinance as yf

from . import broker

QUOTE_TTL = 15.0   # seconds
BARS_TTL = 60.0    # seconds

_cache: dict[str, tuple[float, object]] = {}


def _cached(key: str, ttl: float, fetch):
    now = time.monotonic()
    hit = _cache.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    value = fetch()
    _cache[key] = (now, value)
    return value


def get_quote(symbol: str) -> broker.Quote:
    """Quote with a 15s TTL so Streamlit reruns don't hammer yfinance."""
    return _cached(f"q:{symbol.upper()}", QUOTE_TTL, lambda: broker.quote(symbol))


def get_intraday_bars(symbol: str, period: str = "1d",
                      interval: str = "1m") -> pd.DataFrame:
    """1-minute intraday bars (regular session only)."""
    def fetch() -> pd.DataFrame:
        df = yf.Ticker(symbol.upper()).history(
            period=period, interval=interval, prepost=False
        )
        if df.empty:
            raise ValueError(f"no intraday data for {symbol}")
        return df
    return _cached(f"b:{symbol.upper()}:{period}:{interval}", BARS_TTL, fetch)


def get_daily_bars(symbol: str, period: str = "3mo") -> pd.DataFrame:
    """Daily bars for context."""
    def fetch() -> pd.DataFrame:
        df = yf.Ticker(symbol.upper()).history(period=period, interval="1d")
        if df.empty:
            raise ValueError(f"no daily data for {symbol}")
        return df
    return _cached(f"d:{symbol.upper()}:{period}", BARS_TTL, fetch)
