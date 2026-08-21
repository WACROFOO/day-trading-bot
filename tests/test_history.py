"""Offline tests for the 1-minute history fetcher. No network."""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paper_trading import history  # noqa: E402


def bars(start: str, n: int, tz: str | None = "America/New_York",
         price: float = 5.0) -> pd.DataFrame:
    idx = pd.date_range(start, periods=n, freq="1min", tz=tz)
    return pd.DataFrame({"Open": price, "High": price + 0.1, "Low": price - 0.1,
                         "Close": price, "Volume": 1000.0}, index=idx)


# ------------------------------------------------------------------ windows

def test_chunk_windows_cover_the_span_without_gaps():
    end = dt.datetime(2026, 8, 21, 20, 0, tzinfo=dt.timezone.utc)
    w = list(history.chunk_windows(end, days=30, chunk_days=7))
    assert w[0][0] == end - dt.timedelta(days=30)
    assert w[-1][1] == end
    for (_, hi), (lo, _) in zip(w, w[1:]):
        assert hi == lo


def test_chunk_windows_clip_to_the_retention_limit():
    end = dt.datetime(2026, 8, 21, tzinfo=dt.timezone.utc)
    w = list(history.chunk_windows(end, days=365))
    assert w[0][0] == end - dt.timedelta(days=history.MAX_LOOKBACK_DAYS)


# ------------------------------------------------------------------ shaping

def test_normalize_localizes_naive_index_to_market_tz():
    out = history.normalize(bars("2026-08-20 09:30", 3, tz=None))
    assert str(out.index.tz) == history.MARKET_TZ


def test_normalize_drops_duplicate_timestamps_keeping_last():
    df = bars("2026-08-20 09:30", 2, price=5.0)
    dup = bars("2026-08-20 09:30", 2, price=9.0)
    out = history.normalize(pd.concat([df, dup]))
    assert len(out) == 2
    assert (out["Close"] == 9.0).all()


def test_normalize_empty_returns_typed_empty_frame():
    out = history.normalize(None)
    assert out.empty and list(out.columns) == history.OHLCV


def test_merge_unions_and_prefers_new_bars():
    old = bars("2026-08-20 09:30", 3, price=5.0)
    new = bars("2026-08-20 09:32", 3, price=7.0)
    out = history.merge(old, new)
    assert len(out) == 5                       # 3 + 3 with one overlap
    assert out["Close"].iloc[2] == 7.0         # overlap resolved to the new bar
    assert out.index.is_monotonic_increasing


# ------------------------------------------------------------------ fetching

def test_fetch_1m_concatenates_every_chunk():
    calls = []

    def fake(symbol, start, end, prepost):
        calls.append((start, end))
        return bars(start.strftime("%Y-%m-%d %H:%M"), 5)

    out = history.fetch_1m("SDOT", days=21, chunk_days=7, fetch=fake,
                           now=dt.datetime(2026, 8, 21, tzinfo=dt.timezone.utc))
    assert len(calls) == 3
    assert len(out) == 15


def test_fetch_1m_tolerates_an_empty_chunk():
    def fake(symbol, start, end, prepost):
        if start.day % 2:
            return pd.DataFrame()
        return bars(start.strftime("%Y-%m-%d %H:%M"), 4)

    out = history.fetch_1m("SDOT", days=21, chunk_days=7, fetch=fake,
                           now=dt.datetime(2026, 8, 21, tzinfo=dt.timezone.utc))
    assert not out.empty


def test_fetch_1m_raises_when_every_chunk_fails():
    def boom(symbol, start, end, prepost):
        raise RuntimeError("403")

    with pytest.raises(history.NetworkError):
        history.fetch_1m("SDOT", days=14, chunk_days=7, fetch=boom,
                         now=dt.datetime(2026, 8, 21, tzinfo=dt.timezone.utc))


def test_fetch_1m_survives_one_failing_chunk():
    def flaky(symbol, start, end, prepost):
        if start.day == 14:
            raise RuntimeError("timeout")
        return bars(start.strftime("%Y-%m-%d %H:%M"), 3)

    out = history.fetch_1m("SDOT", days=21, chunk_days=7, fetch=flaky,
                           now=dt.datetime(2026, 8, 21, tzinfo=dt.timezone.utc))
    assert len(out) == 6


# ------------------------------------------------------------------ archive

def test_archive_roundtrip_preserves_bars_and_tz(tmp_path):
    df = bars("2026-08-20 09:30", 10)
    path = history.save_archive(df, history.archive_path(tmp_path, "sdot"))
    assert path.name == "SDOT_1m.csv"
    back = history.load_archive(path)
    assert len(back) == 10
    assert str(back.index.tz) == history.MARKET_TZ
    pd.testing.assert_series_equal(back["Close"], history.normalize(df)["Close"],
                                  check_freq=False)


def test_load_archive_missing_file_is_empty(tmp_path):
    assert history.load_archive(tmp_path / "nope.csv").empty


def test_archive_accumulates_beyond_one_fetch(tmp_path):
    path = history.archive_path(tmp_path, "SDOT")
    history.save_archive(bars("2026-07-20 09:30", 5), path)
    grown = history.merge(history.load_archive(path), bars("2026-08-20 09:30", 5))
    history.save_archive(grown, path)
    assert len(history.load_archive(path)) == 10


# ------------------------------------------------------------------ summaries

def test_session_summary_one_row_per_day():
    two_days = pd.concat([bars("2026-08-20 09:30", 5, price=5.0),
                          bars("2026-08-21 09:30", 3, price=6.0)])
    out = history.session_summary(two_days)
    assert len(out) == 2
    assert out["bars"].tolist() == [5, 3]
    assert out["first_bar"].tolist() == ["09:30", "09:30"]
    assert out["volume"].tolist() == [5000.0, 3000.0]


def test_missing_regular_minutes_counts_the_holes():
    out = history.missing_regular_minutes(bars("2026-08-20 09:30", 10))
    assert out["missing_minutes"].iloc[0] == 380   # 390 - 10


def test_missing_regular_minutes_ignores_extended_hours():
    premarket = bars("2026-08-20 07:00", 30)
    assert history.missing_regular_minutes(premarket).empty


def test_fetch_1m_default_feed_is_resolved_at_call_time(monkeypatch):
    """The yfinance call is looked up per call, so it stays patchable."""
    seen = []

    def fake(symbol, start, end, prepost):
        seen.append(symbol)
        return bars("2026-08-20 09:30", 2)

    monkeypatch.setattr(history, "_yf_fetch", fake)
    out = history.fetch_1m("SDOT", days=7, chunk_days=7,
                           now=dt.datetime(2026, 8, 21, tzinfo=dt.timezone.utc))
    assert seen == ["SDOT"] and len(out) == 2
