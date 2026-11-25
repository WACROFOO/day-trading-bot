"""Turn raw series into monthly total returns in EUR.

Conventions used everywhere in the project:

- Returns are simple monthly returns, indexed by the month-end they end on.
- ``eurusd`` is USD per 1 EUR (the market quote: 1.08 means 1 EUR = 1.08 USD).
- Annual interest rates are in percent and apply to the month *after* they
  are observed (a rate known at the end of March earns during April).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEM_PER_EUR = 1.95583  # irrevocable conversion rate fixed on 1 Jan 1999


def returns_from_levels(levels: pd.Series) -> pd.Series:
    """Simple period returns from a level series (first period dropped)."""
    return levels.sort_index().pct_change().dropna()


def levels_from_returns(returns: pd.Series, start: float = 100.0) -> pd.Series:
    return start * (1.0 + returns.sort_index()).cumprod()


def month_end_last(daily: pd.Series) -> pd.Series:
    """Last available daily observation of each calendar month."""
    s = daily.dropna().sort_index()
    return s.groupby(s.index + pd.offsets.MonthEnd(0)).last()


def eurusd_month_end(dexuseu_daily: pd.Series, dexgeus_daily: pd.Series | None = None) -> pd.Series:
    """Month-end EUR/USD, extended before 1999 through the Deutsche Mark.

    FRED DEXUSEU (USD per EUR) starts in January 1999. Before that, a
    synthetic rate is DEM_PER_EUR / (DEM per USD) from FRED DEXGEUS, the
    standard way to extend the euro back in time.
    """
    eur = month_end_last(dexuseu_daily)
    if dexgeus_daily is None:
        return eur
    synthetic = DEM_PER_EUR / month_end_last(dexgeus_daily)
    synthetic = synthetic[synthetic.index < eur.index.min()]
    return pd.concat([synthetic, eur]).sort_index()


def usd_to_eur_returns(r_usd: pd.Series, eurusd: pd.Series) -> pd.Series:
    """Unhedged EUR return of a USD asset.

    Value in EUR = value in USD / eurusd, so
    1 + r_eur = (1 + r_usd) * eurusd[t-1] / eurusd[t].
    """
    fx = eurusd.sort_index()
    fx_factor = fx.shift(1) / fx
    out = (1.0 + r_usd) * fx_factor.reindex(r_usd.index) - 1.0
    return out.dropna()


def cash_returns(annual_rate_pct: pd.Series) -> pd.Series:
    """Monthly cash return from an annual rate (percent), earned next month."""
    r = (1.0 + annual_rate_pct.sort_index() / 100.0) ** (1.0 / 12.0) - 1.0
    return r.shift(1).dropna()


def hedged_returns(r_foreign: pd.Series, cash_foreign: pd.Series, cash_home: pd.Series) -> pd.Series:
    """Currency-hedged return: foreign return plus the interest-rate carry.

    A rolling one-month forward hedge earns (home cash - foreign cash) on top
    of the asset's local return (covered interest parity). Hedging costs and
    the small cross term are ignored; that is accurate to a few basis points a
    year for G10 currencies.
    """
    carry = (cash_home - cash_foreign).reindex(r_foreign.index)
    return (r_foreign + carry).dropna()


def par_bond_returns(yield_pct: pd.Series, maturity_years: float = 8.5,
                     coupons_per_year: int = 2) -> pd.Series:
    """Monthly total return of a constant-maturity par bond from its yield.

    Each month: buy a par bond paying last month's yield as its coupon (so it
    costs exactly 1.0), hold it for one month, then value it at this month's
    yield with one month less to maturity. The return is that full value
    (which includes the month's accrued coupon) minus 1. A maturity of 8.5
    years approximates a 7-10 year Treasury index.
    """
    y = yield_pct.sort_index() / 100.0
    out = {}
    for prev_date, date in zip(y.index[:-1], y.index[1:]):
        coupon = y[prev_date]
        value = _bond_full_price(coupon, y[date], maturity_years - 1.0 / 12.0, coupons_per_year)
        out[date] = value - 1.0
    return pd.Series(out, name="bond_return")


def _bond_full_price(coupon: float, ytm: float, years: float, freq: int) -> float:
    """Full (dirty) value per 1.0 face with ``years`` to maturity.

    With n = years * freq periods left, the remaining coupons fall at
    frac, frac + 1, ..., n periods from now (frac = n - floor(n)), the last
    one paid together with the face value.
    """
    n = years * freq
    c, r = coupon / freq, ytm / freq
    whole = int(np.floor(n + 1e-9))
    frac = n - whole
    if frac > 1e-9:
        times = frac + np.arange(0, whole + 1, dtype=float)
    else:
        times = np.arange(1, whole + 1, dtype=float)
    pv_coupons = np.sum(c / (1.0 + r) ** times)
    pv_face = 1.0 / (1.0 + r) ** n
    return float(pv_coupons + pv_face)


def splice_returns(primary: pd.Series, backfill: pd.Series) -> pd.Series:
    """``primary`` where it exists; ``backfill`` only for months before it starts."""
    early = backfill[backfill.index < primary.index.min()]
    return pd.concat([early, primary]).sort_index()


def scale_to_volatility(r: pd.Series, target_annual_vol: float) -> pd.Series:
    """Rescale an excess-return series to a target annualised volatility.

    Used to map a research factor (for example AQR's TSMOM, built at a high
    volatility) onto the volatility of the fund we would actually hold.
    """
    realised = r.std() * np.sqrt(12.0)
    if realised <= 0:
        raise ValueError("cannot scale a series with zero volatility")
    return r * (target_annual_vol / realised)
