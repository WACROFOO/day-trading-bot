"""The cache downloads once, then serves the local copy with the same type."""

import pandas as pd
import pytest

from portfolio_bot.data import catalog


@pytest.fixture
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("PORTFOLIO_BOT_DATA_DIR", str(tmp_path))
    return tmp_path


def _counting_spec(name, data):
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return data.copy()

    return catalog.Spec(name, fetch, "test", "test"), calls


IDX = pd.DatetimeIndex(["2024-01-31", "2024-02-29"])


def test_downloads_once_then_reads_cache(tmp_cache):
    spec, calls = _counting_spec("s", pd.Series([1.0, 2.0], index=IDX))
    cat = {"s": spec}
    first = catalog.load("s", catalog=cat)
    second = catalog.load("s", catalog=cat)
    assert calls["n"] == 1
    assert isinstance(second, pd.Series)
    pd.testing.assert_series_equal(first, second, check_names=False, check_freq=False)
    assert catalog.metadata("s")["rows"] == 2


def test_refresh_downloads_again(tmp_cache):
    spec, calls = _counting_spec("s", pd.Series([1.0, 2.0], index=IDX))
    catalog.load("s", catalog={"s": spec})
    catalog.load("s", catalog={"s": spec}, refresh=True)
    assert calls["n"] == 2


def test_single_column_table_stays_a_table(tmp_cache):
    spec, _ = _counting_spec("t", pd.DataFrame({"Mom": [0.01, -0.02]}, index=IDX))
    catalog.load("t", catalog={"t": spec})
    again = catalog.load("t", catalog={"t": spec})
    assert isinstance(again, pd.DataFrame) and list(again.columns) == ["Mom"]


def test_unknown_name_raises(tmp_cache):
    with pytest.raises(KeyError):
        catalog.load("nope", catalog={})
