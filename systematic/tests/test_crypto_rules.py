"""Hand-checkable tests for the frozen crypto rule and its data source."""

import json

import numpy as np
import pandas as pd
import pytest

from portfolio_bot.crypto import rules
from portfolio_bot.data import sources as src


def daily(values, start="2020-01-01"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="D"), dtype=float)


# --------------------------------------------------------------------------
# the frozen file and the code agree
# --------------------------------------------------------------------------

def test_code_defaults_equal_frozen_file():
    assert rules.FrozenRule.load() == rules.FrozenRule()


def test_frozen_file_is_dated_before_forward_record():
    spec = json.loads(rules.FROZEN_RULES_JSON.read_text())
    assert pd.Timestamp(spec["frozen_on"]) < pd.Timestamp(spec["forward_record_starts"])


# --------------------------------------------------------------------------
# signal
# --------------------------------------------------------------------------

def test_signal_is_one_in_a_steady_rise_and_zero_in_a_steady_fall():
    up = daily(100 * 1.001 ** np.arange(400))
    down = daily(100 * 0.999 ** np.arange(400))
    assert rules.ensemble_signal(up).iloc[-1] == 1.0
    assert rules.ensemble_signal(down).iloc[-1] == 0.0


def test_signal_counts_lookbacks_separately():
    # Rise for a year, then fall for 60 days: the 30-day return is negative,
    # the 91/182/365-day returns are still positive -> 3 of 4 votes.
    prices = list(100 * 1.002 ** np.arange(366)) + list(100 * 1.002 ** 365 * 0.999 ** np.arange(1, 61))
    s = rules.ensemble_signal(daily(prices))
    assert s.iloc[-1] == 0.75


def test_signal_is_nan_until_a_full_year_of_history():
    s = rules.ensemble_signal(daily(100 * 1.001 ** np.arange(400)))
    assert s.iloc[:365].isna().all() and s.iloc[365:].notna().all()


# --------------------------------------------------------------------------
# volatility sizing and band
# --------------------------------------------------------------------------

def test_vol_target_scales_exposure_down_when_volatility_is_high():
    # Alternating +4%/-3.85% days: realised vol ~ 0.0392*sqrt(365) ~ 75%/yr
    rets = np.tile([0.04, -0.0385], 250)
    prices = 100 * np.cumprod(1 + np.concatenate([[0.0], rets]))
    close = daily(prices)
    vol = rules.realised_vol(close).iloc[-1]
    target = rules.raw_target(close).iloc[-1]
    signal = rules.ensemble_signal(close).iloc[-1]
    assert vol > 0.5
    assert target == pytest.approx(signal * min(1.0, 0.25 / vol))


def test_vol_target_never_exceeds_full_investment():
    calm = daily(100 * 1.0002 ** np.arange(500))  # near-zero volatility
    assert rules.raw_target(calm).dropna().max() <= 1.0


def test_band_ignores_small_changes_but_always_exits_on_zero():
    target = pd.Series([np.nan, 0.50, 0.55, 0.62, 0.05, 0.0, 0.08, 0.30])
    out = rules.apply_band(target, min_change=0.10)
    assert np.isnan(out.iloc[0])
    assert list(out.iloc[1:]) == [0.50, 0.50, 0.62, 0.05, 0.0, 0.0, 0.30]


# --------------------------------------------------------------------------
# no lookahead: the future cannot change a past decision
# --------------------------------------------------------------------------

def test_changing_future_prices_never_changes_past_exposure():
    rng = np.random.default_rng(7)
    base = 100 * np.cumprod(1 + rng.normal(0.001, 0.03, 900))
    cut = 700
    altered = base.copy()
    altered[cut + 1:] *= rng.uniform(0.3, 3.0, len(base) - cut - 1)
    a = rules.primary_exposure(daily(base))
    b = rules.primary_exposure(daily(altered))
    pd.testing.assert_series_equal(a.iloc[: cut + 1], b.iloc[: cut + 1])


# --------------------------------------------------------------------------
# benchmark and simulation
# --------------------------------------------------------------------------

def test_c1_is_invested_only_above_the_200_day_average():
    prices = list(np.full(200, 100.0)) + [110.0, 90.0]
    e = rules.c1_sma200_exposure(daily(prices))
    assert e.iloc[-2] == 1.0 and e.iloc[-1] == 0.0


def test_simulate_holds_the_previous_days_decision_and_pays_on_changes():
    close = daily([100, 110, 121, 121])
    exposure = pd.Series([1.0, 1.0, 0.0, 0.0], index=close.index)
    out = rules.simulate(close, exposure, fee_per_trade=0.01, spread=0.0)
    # day 2: held 1.0 -> +10%; day 3: held 1.0 -> +10%, then sell (1% fee); day 4: flat
    assert out["nav"].iloc[0] == pytest.approx(1.10)
    assert out["nav"].iloc[1] == pytest.approx(1.10 * 1.10 * 0.99)
    assert out["nav"].iloc[2] == pytest.approx(1.10 * 1.10 * 0.99)


def test_gaps_in_daily_data_are_refused():
    close = daily([100, 101, 102]).drop(pd.Timestamp("2020-01-02"))
    with pytest.raises(ValueError, match="missing days"):
        rules.ensemble_signal(close)


# --------------------------------------------------------------------------
# Bitstamp parser
# --------------------------------------------------------------------------

def test_bitstamp_candles_and_completed_days():
    payload = json.dumps({"data": {"pair": "BTC/EUR", "ohlc": [
        {"timestamp": "1795392000", "open": "1", "high": "2", "low": "1", "close": "54000.5", "volume": "10"},
        {"timestamp": "1795478400", "open": "1", "high": "2", "low": "1", "close": "54500.0", "volume": "12"},
    ]}}).encode()
    df = src.parse_bitstamp_ohlc(payload)
    assert list(df.index) == [pd.Timestamp("2026-11-23"), pd.Timestamp("2026-11-24")]
    assert df["close"].iloc[0] == 54000.5
    # At 2026-11-24 12:00 UTC, the 24th's candle is still open
    done = src.completed_days(df, pd.Timestamp("2026-11-24 12:00", tz="UTC"))
    assert list(done.index) == [pd.Timestamp("2026-11-23")]


def test_bitstamp_empty_page():
    assert src.parse_bitstamp_ohlc(b'{"data": {"pair": "BTC/EUR", "ohlc": []}}').empty


def test_bitstamp_fetch_pages_past_short_first_page(monkeypatch):
    """A first page shortened by pre-listing days must not end the download."""
    day = 86400
    t0 = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())

    def fake_get(url):
        start = int(url.split("start=")[1])
        # listing starts at t0; each page returns up to 3 days, the first page only 2
        first = max(start, t0)
        stop = min(start + 3 * day, t0 + 10 * day)
        ts = list(range(first, stop, day))
        rows = [{"timestamp": str(t), "open": "1", "high": "1", "low": "1",
                 "close": str(100 + (t - t0) // day), "volume": "1"} for t in ts]
        return json.dumps({"data": {"pair": "BTC/EUR", "ohlc": rows}}).encode()

    monkeypatch.setattr(src, "http_get", fake_get)
    df = src.fetch_bitstamp_daily("btceur", start="2025-12-31")
    assert len(df) == 10 and df.index.is_unique
    assert df.index[-1] == pd.Timestamp("2026-01-10")
