"""Known-answer tests for EUR conversion, cash, hedging, bonds and checks."""

import numpy as np
import pandas as pd
import pytest

from portfolio_bot.data import checks
from portfolio_bot.data import transforms as tf


def me(*dates):
    return pd.DatetimeIndex(pd.to_datetime(list(dates))) + pd.offsets.MonthEnd(0)


# --------------------------------------------------------------------------
# FX
# --------------------------------------------------------------------------

def test_usd_asset_loses_in_eur_when_euro_rises():
    idx = me("2024-01-31", "2024-02-29")
    eurusd = pd.Series([1.00, 1.25], index=idx)
    r_usd = pd.Series([0.0], index=idx[1:])
    r_eur = tf.usd_to_eur_returns(r_usd, eurusd)
    assert r_eur.iloc[0] == pytest.approx(-0.20)  # 1 USD: 1.00 EUR -> 0.80 EUR


def test_usd_and_fx_gains_compound():
    idx = me("2024-01-31", "2024-02-29")
    eurusd = pd.Series([1.10, 1.00], index=idx)  # euro falls 9.1%
    r_usd = pd.Series([0.10], index=idx[1:])
    assert tf.usd_to_eur_returns(r_usd, eurusd).iloc[0] == pytest.approx(1.10 * 1.10 - 1)


def test_eurusd_extended_before_1999_through_dem():
    dem = pd.Series([1.95583, 1.95583 / 1.1],
                    index=pd.to_datetime(["1998-11-30", "1998-12-31"]))
    eur = pd.Series([1.17, 1.16], index=pd.to_datetime(["1999-01-04", "1999-01-29"]))
    fx = tf.eurusd_month_end(eur, dem)
    assert fx["1998-11-30"] == pytest.approx(1.0)
    assert fx["1998-12-31"] == pytest.approx(1.1)
    assert fx["1999-01-31"] == pytest.approx(1.16)  # last daily value of January


# --------------------------------------------------------------------------
# cash and hedging
# --------------------------------------------------------------------------

def test_cash_rate_earns_in_the_following_month():
    idx = me("2024-01-31", "2024-02-29", "2024-03-31")
    rate = pd.Series([12.0, 0.0, 0.0], index=idx)
    r = tf.cash_returns(rate)
    assert r.index[0] == idx[1]
    assert r.iloc[0] == pytest.approx(1.12 ** (1 / 12) - 1)
    assert r.iloc[1] == pytest.approx(0.0)


def test_hedged_return_adds_rate_carry():
    idx = me("2024-02-29")
    r = tf.hedged_returns(pd.Series([0.010], idx), pd.Series([0.004], idx), pd.Series([0.002], idx))
    assert r.iloc[0] == pytest.approx(0.008)


# --------------------------------------------------------------------------
# bonds
# --------------------------------------------------------------------------

def test_par_bond_with_flat_yield_earns_its_coupon():
    idx = me("2024-01-31", "2024-02-29", "2024-03-31")
    r = tf.par_bond_returns(pd.Series([4.0, 4.0, 4.0], index=idx))
    assert r.iloc[0] == pytest.approx(0.04 / 12, abs=2e-4)


def test_par_bond_loses_about_its_duration_when_yields_rise():
    idx = me("2024-01-31", "2024-02-29")
    r = tf.par_bond_returns(pd.Series([4.0, 5.0], index=idx), maturity_years=8.5)
    assert -0.08 < r.iloc[0] < -0.05  # ~6.7 years of duration


def test_scale_to_volatility_hits_target():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0, 0.05, 240))
    assert tf.scale_to_volatility(r, 0.12).std() * np.sqrt(12) == pytest.approx(0.12)


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------

def test_structural_checks_catch_gaps_and_bad_dates():
    good = pd.Series([1.0, 2.0, 3.0], index=me("2024-01-31", "2024-02-29", "2024-03-31"))
    assert all(c.ok for c in checks.check_monthly_index(good, "good"))

    gappy = good.drop(good.index[1])
    gap = [c for c in checks.check_monthly_index(gappy, "gappy") if "gaps" in c.name][0]
    assert not gap.ok and gap.items == [pd.Timestamp("2024-02-29").date()]

    mid = pd.Series([1.0], index=pd.to_datetime(["2024-01-15"]))
    assert not [c for c in checks.check_monthly_index(mid, "mid") if "month-end" in c.name][0].ok


def test_jump_check_respects_reviewed_months():
    r = pd.Series([0.01, -0.30, 0.02], index=me("2008-09-30", "2008-10-31", "2008-11-30"))
    assert not checks.check_jumps(r, "x").ok
    assert checks.check_jumps(r, "x", allowed={"2008-10"}).ok


def test_annual_returns_and_reference_comparison():
    idx = me("2022-12-31", "2023-06-30", "2023-12-31", "2024-12-31")
    levels = pd.Series([100.0, 105.0, 110.0, 99.0], index=idx)
    years = checks.annual_returns(levels)
    assert years[2023] == pytest.approx(0.10)
    assert years[2024] == pytest.approx(-0.10)
    assert checks.compare_annual(levels, {2023: 10.2, 2024: -10.0}, "x").ok
    assert not checks.compare_annual(levels, {2023: 11.0}, "x").ok
    assert not checks.compare_annual(levels, {1990: 5.0}, "x").ok  # nothing to compare


def test_splice_uses_backfill_only_before_primary():
    primary = pd.Series([0.02, 0.03], index=me("2001-01-31", "2001-02-28"))
    backfill = pd.Series([0.10, 0.11, 0.99], index=me("2000-11-30", "2000-12-31", "2001-01-31"))
    out = tf.splice_returns(primary, backfill)
    assert list(out.values) == [0.10, 0.11, 0.02, 0.03]


def test_conversion_check_tolerates_reversing_timing_noise():
    idx = pd.date_range("2001-01-31", periods=120, freq="ME")
    official = pd.Series(0.006, index=idx)
    noise = pd.Series(np.tile([0.004, -0.004], 60), index=idx)  # reverses every month
    assert checks.check_conversion(official + noise, official, "x").ok
    drift = official + 0.0005  # 0.6%/yr systematic gap: a real bug
    assert not checks.check_conversion(drift, official, "x").ok
