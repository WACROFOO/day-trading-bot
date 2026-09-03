"""Offline tests for the NASDAQ universe scanner (strategy §1).

All tests are offline: yfinance downloads and the nasdaqtrader.com fetch
are mocked or bypassed via the pure functions.
"""

from __future__ import annotations

import pandas as pd
import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paper_trading import scanner  # noqa: E402


# ------------------------------------------------------------------ helpers

def make_bars(closes, volumes) -> pd.DataFrame:
    """Synthetic daily OHLCV frame; len(closes) rows, last row = today."""
    return pd.DataFrame({
        "Open": closes, "High": closes, "Low": closes,
        "Close": closes, "Volume": volumes,
    })


def stats_row(**overrides) -> pd.DataFrame:
    """A one-row stats frame that passes every filter by default."""
    row = {"price": 10.0, "change_pct": 15.0, "volume": 1_000_000.0,
           "avg_volume_50d": 100_000.0, "rvol": 10.0}
    row.update(overrides)
    return pd.DataFrame(row, index=pd.Index(["TEST"], name="symbol"))


# ------------------------------------------------------------------ compute_stats

def test_compute_stats_basic():
    bars = make_bars([1.0] * 51 + [2.0], [100.0] * 51 + [1000.0])
    s = scanner.compute_stats(bars)
    assert s["price"] == 2.0
    assert s["change_pct"] == pytest.approx(100.0)
    assert s["volume"] == 1000.0
    assert s["avg_volume_50d"] == pytest.approx(100.0)  # excludes today
    assert s["rvol"] == pytest.approx(10.0)


def test_compute_stats_avg_volume_uses_50_days_excluding_today():
    volumes = [float(i) for i in range(1, 61)]  # 60 days history
    bars = make_bars([10.0] * 61, volumes + [999.0])
    s = scanner.compute_stats(bars)
    expected = sum(volumes[-50:]) / 50
    assert s["avg_volume_50d"] == pytest.approx(expected)


def test_compute_stats_too_few_rows_returns_none():
    assert scanner.compute_stats(make_bars([2.0], [1000.0])) is None
    assert scanner.compute_stats(pd.DataFrame(columns=["Close", "Volume"])) is None


# ------------------------------------------------------------------ apply_filters boundaries

@pytest.mark.parametrize("price,ok", [(1.99, False), (2.00, True),
                                      (20.00, True), (20.01, False)])
def test_price_boundary(price, ok):
    out = scanner.apply_filters(stats_row(price=price))
    assert (len(out) == 1) == ok


@pytest.mark.parametrize("gain,ok", [(9.9, False), (10.0, True)])
def test_gain_boundary(gain, ok):
    out = scanner.apply_filters(stats_row(change_pct=gain))
    assert (len(out) == 1) == ok


@pytest.mark.parametrize("rvol,ok", [(4.9, False), (5.0, True)])
def test_rvol_boundary(rvol, ok):
    out = scanner.apply_filters(stats_row(rvol=rvol))
    assert (len(out) == 1) == ok


@pytest.mark.parametrize("volume,ok", [(499_999.0, False), (500_000.0, True)])
def test_volume_boundary(volume, ok):
    out = scanner.apply_filters(stats_row(volume=volume))
    assert (len(out) == 1) == ok


def test_thresholds_are_parameters():
    out = scanner.apply_filters(stats_row(price=1.50), price_min=1.0)
    assert len(out) == 1


def test_flags_and_manual_check_columns():
    out = scanner.apply_filters(stats_row())
    row = out.iloc[0]
    assert row["symbol"] == "TEST"
    for flag in ("pass_price", "pass_gain", "pass_rvol", "pass_volume"):
        assert bool(row[flag]) is True
    assert pd.isna(row["float_shares"])  # manual check, not dropped silently
    assert row["catalyst"] is None       # manual check


def test_sorted_by_rvol_desc():
    stats = pd.concat([stats_row(), stats_row(rvol=20.0)])
    stats.index = ["LOW", "HIGH"]
    out = scanner.apply_filters(stats)
    assert out["symbol"].tolist() == ["HIGH", "LOW"]


# ------------------------------------------------------------------ universe list parsing

NASDAQ_LISTED_SAMPLE = """\
Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares
AAPL|Apple Inc. Common Stock|Q|N|N|100|N|N
TESTCO|Test Company|Q|Y|N|100|N|N
SPY|SPDR S&P 500 ETF Trust|P|N|N|100|Y|N
File Creation Time: 0101202401:01||||||
"""


def test_parse_nasdaq_listed_excludes_test_issues_and_trailer():
    df = scanner.parse_nasdaq_listed(NASDAQ_LISTED_SAMPLE, include_etf=True)
    assert "AAPL" in df["symbol"].values
    assert "TESTCO" not in df["symbol"].values  # Test Issue == 'Y'
    assert not df["symbol"].str.contains("File Creation").any()


def test_parse_nasdaq_listed_etf_flag():
    with_etf = scanner.parse_nasdaq_listed(NASDAQ_LISTED_SAMPLE, include_etf=True)
    without_etf = scanner.parse_nasdaq_listed(NASDAQ_LISTED_SAMPLE, include_etf=False)
    assert "SPY" in with_etf["symbol"].values
    assert "SPY" not in without_etf["symbol"].values
    assert bool(with_etf.loc[with_etf["symbol"] == "SPY", "is_etf"].iloc[0]) is True


def test_fetch_universe_falls_back_to_cache(tmp_path, monkeypatch):
    cache = tmp_path / "nasdaq_universe.csv"
    pd.DataFrame({
        "symbol": ["CACHED"], "name": ["Cached Corp"],
        "is_etf": [False], "fetched_date": ["2099-01-01"],
    }).to_csv(cache, index=False)

    def boom(*a, **k):
        raise OSError("network down")

    monkeypatch.setattr(scanner.urllib.request, "urlopen", boom)
    df = scanner.fetch_nasdaq_universe(cache_path=cache)
    assert df["symbol"].tolist() == ["CACHED"]


def test_fetch_universe_no_cache_raises_network_error(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise OSError("network down")

    monkeypatch.setattr(scanner.urllib.request, "urlopen", boom)
    with pytest.raises(scanner.NetworkError):
        scanner.fetch_nasdaq_universe(cache_path=tmp_path / "missing.csv")


# ------------------------------------------------------------------ batch download handling

def fake_download(tickers: str, **kwargs) -> pd.DataFrame:
    """Mimic yf.download MultiIndex output, silently dropping 'BAD'."""
    symbols = [s for s in tickers.split() if s != "BAD"]
    cols = pd.MultiIndex.from_product(
        [symbols, ["Open", "High", "Low", "Close", "Volume"]])
    df = pd.DataFrame(index=pd.date_range("2024-01-01", periods=3), columns=cols)
    for s in symbols:
        df[(s, "Close")] = [1.0, 1.0, 2.0]
        df[(s, "Volume")] = [100.0, 100.0, 1_000_000.0]
    return df


def test_scan_handles_missing_tickers(monkeypatch):
    monkeypatch.setattr(scanner.yf, "download", fake_download)
    out = scanner.scan(symbols=["GOOD", "BAD"], chunk_size=2)
    assert out["symbol"].tolist() == ["GOOD"]
    row = out.iloc[0]
    assert row["change_pct"] == pytest.approx(100.0)
    assert row["rvol"] == pytest.approx(10_000.0)


def test_scan_empty_download_returns_empty(monkeypatch):
    monkeypatch.setattr(scanner.yf, "download",
                        lambda *a, **k: pd.DataFrame())
    out = scanner.scan(symbols=["AAA", "BBB"])
    assert out.empty


def test_scan_progress_callback(monkeypatch):
    monkeypatch.setattr(scanner.yf, "download", fake_download)
    calls = []
    scanner.scan(symbols=["GOOD"], chunk_size=1,
                 progress_cb=lambda d, t, m: calls.append((d, t)))
    assert calls and calls[-1] == (1, 1)


# ------------------------------------------------------------------ coverage

def test_coverage_arithmetic():
    cov = scanner.Coverage(requested=200, with_data=50)
    assert cov.missing == 150
    assert cov.pct == pytest.approx(25.0)
    assert cov.is_degraded


def test_coverage_full_scan_is_not_degraded():
    cov = scanner.Coverage(requested=100, with_data=100)
    assert cov.pct == pytest.approx(100.0)
    assert not cov.is_degraded
    assert cov.missing == 0


def test_coverage_empty_universe_does_not_divide_by_zero():
    assert scanner.Coverage(requested=0, with_data=0).pct == 0.0


def test_scan_reports_degraded_coverage(monkeypatch):
    """A scan where nearly everything fails must not look like a quiet market."""
    monkeypatch.setattr(scanner.yf, "download", fake_download)
    out = scanner.scan(symbols=["GOOD"] + ["BAD"] * 19, chunk_size=20)
    cov = out.attrs["coverage"]
    assert cov.requested == 20
    assert cov.with_data == 1
    assert cov.is_degraded


def test_scan_reports_full_coverage(monkeypatch):
    monkeypatch.setattr(scanner.yf, "download", fake_download)
    out = scanner.scan(symbols=["GOOD", "ALSOGOOD"], chunk_size=2)
    assert not out.attrs["coverage"].is_degraded


def test_scan_retries_symbols_that_returned_no_data(monkeypatch):
    """First pass drops BAD; the retry pass sees it recover."""
    attempts = {"n": 0}

    def flaky(tickers: str, **kwargs) -> pd.DataFrame:
        attempts["n"] += 1
        drop = "BAD" if attempts["n"] == 1 else None
        symbols = [s for s in tickers.split() if s != drop]
        cols = pd.MultiIndex.from_product(
            [symbols, ["Open", "High", "Low", "Close", "Volume"]])
        df = pd.DataFrame(index=pd.date_range("2024-01-01", periods=3), columns=cols)
        for s in symbols:
            df[(s, "Close")] = [1.0, 1.0, 2.0]
            df[(s, "Volume")] = [100.0, 100.0, 1_000_000.0]
        return df

    monkeypatch.setattr(scanner.yf, "download", flaky)
    out = scanner.scan(symbols=["GOOD", "BAD"], chunk_size=2)
    assert sorted(out["symbol"]) == ["BAD", "GOOD"]
    assert out.attrs["coverage"].with_data == 2


def test_scan_no_retry_leaves_missing_symbols(monkeypatch):
    monkeypatch.setattr(scanner.yf, "download", fake_download)
    out = scanner.scan(symbols=["GOOD", "BAD"], chunk_size=2, retry_missing=False)
    assert out.attrs["coverage"].with_data == 1


def test_scan_chunk_exception_does_not_abort_scan(monkeypatch):
    """One exploding chunk must not lose the symbols in the other chunks."""
    def sometimes_boom(tickers: str, **kwargs) -> pd.DataFrame:
        if "BOOM" in tickers:
            raise RuntimeError("connection reset")
        return fake_download(tickers, **kwargs)

    monkeypatch.setattr(scanner.yf, "download", sometimes_boom)
    out = scanner.scan(symbols=["BOOM", "GOOD"], chunk_size=1, retry_missing=False)
    assert out["symbol"].tolist() == ["GOOD"]
    assert out.attrs["coverage"].with_data == 1
