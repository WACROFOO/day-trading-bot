"""Technical indicators on OHLCV dataframes. Pure functions, unit-testable."""

from __future__ import annotations

import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=period, adjust=False).mean()


def ema9(close: pd.Series) -> pd.Series:
    """9-period EMA of close (strategy's trend filter)."""
    return ema(close, 9)


def vwap(df: pd.DataFrame) -> pd.Series:
    """Intraday VWAP, reset each calendar day of the index.

    Expects columns High/Low/Close/Volume and a DatetimeIndex.
    """
    typical = (df["High"] + df["Low"] + df["Close"]) / 3.0
    tpv = typical * df["Volume"]
    days = df.index.date
    cum_tpv = tpv.groupby(days).cumsum()
    cum_vol = df["Volume"].groupby(days).cumsum()
    return cum_tpv / cum_vol


def macd(close: pd.Series, fast: int = 12, slow: int = 26,
         signal: int = 9) -> pd.DataFrame:
    """MACD(12,26,9): macd line, signal line, histogram."""
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({
        "macd": macd_line,
        "signal": signal_line,
        "hist": macd_line - signal_line,
    })
