"""Monthly EUR total-return series for each sleeve (STRATEGY.md §2, §2.2).

These are the long-history stand-ins the backtests run on. Each function
says what it approximates and where the approximation is weakest, because
the proxy chosen for each sleeve is the largest source of backtest error
(the lesson from PARAMETERS.md §10 in the old project).
"""

from __future__ import annotations

import pandas as pd

from . import transforms as tf
from .catalog import load


# --------------------------------------------------------------------------
# FX and cash
# --------------------------------------------------------------------------

def eurusd() -> pd.Series:
    """Month-end USD per EUR, extended before 1999 through the Deutsche Mark.

    Before 1999 the DEM rate is a monthly average (FRED EXGEUS), not a
    month-end rate, so 1997-98 EUR returns carry some timing noise.
    """
    return tf.eurusd_month_end(load("eurusd_daily"), load("demusd_monthly"))


def cash_eur() -> pd.Series:
    """S7: EUR cash at 3-month Euribor, 1994+.

    Overnight-rate ETFs (XEON) earn a little less than 3-month Euribor and
    charge 0.10%, so this flatters cash by a few basis points a year.
    """
    return tf.cash_returns(load("euribor_3m")).rename("cash_eur")


def cash_usd() -> pd.Series:
    """USD cash at the 3-month T-bill rate (for currency hedging)."""
    return tf.cash_returns(load("us_3m_tbill")).rename("cash_usd")


# --------------------------------------------------------------------------
# Equity sleeves (S1-S3)
# --------------------------------------------------------------------------

def converted_eur(usd_returns: pd.Series) -> pd.Series:
    """USD returns converted to EUR with our month-end FX series."""
    return tf.usd_to_eur_returns(usd_returns, eurusd())


def _official_then_converted(eur_levels: str, usd_returns: pd.Series) -> pd.Series:
    """MSCI's own EUR returns where they exist; our conversion only before.

    MSCI fixes FX at 4pm London and FRED at noon New York, so a converted
    series drifts by about 0.1%/yr (data checks). Using the official EUR
    series wherever it exists keeps that error to the early years only.
    """
    official = tf.returns_from_levels(load(eur_levels))
    return tf.splice_returns(official, converted_eur(usd_returns))


# MSCI serves World net returns only from December 2000. Before that, the
# price index plus this net dividend yield stands in (world yields were about
# 1.5-2% gross in 1997-2000, a little less after withholding tax).
PRE_2001_NET_DIVIDEND_YIELD = 0.015


def world_equity_usd() -> pd.Series:
    """MSCI World net total return in USD, 1997+ (backfilled before 2001)."""
    net = tf.returns_from_levels(load("msci_world_usd"))
    price = tf.returns_from_levels(load("msci_world_usd_price"))
    backfill = price + PRE_2001_NET_DIVIDEND_YIELD / 12.0
    return tf.splice_returns(net, backfill)


def world_equity_eur() -> pd.Series:
    """S1: MSCI World net in EUR, 1997+ (official EUR from Jan 2001)."""
    return _official_then_converted("msci_world_eur", world_equity_usd()).rename("world_equity")


def momentum_eur() -> pd.Series:
    """S2: MSCI World Momentum net in EUR, 1997+ (official EUR from Jan 1999).

    Back-tested by MSCI before its December 2013 launch.
    """
    usd = tf.returns_from_levels(load("msci_world_momentum_usd"))
    return _official_then_converted("msci_world_momentum_eur", usd).rename("momentum")


def quality_eur() -> pd.Series:
    """S3: MSCI World Quality net in EUR, 1997+ (official EUR from Jan 1999).

    Back-tested by MSCI before its launch.
    """
    usd = tf.returns_from_levels(load("msci_world_quality_usd"))
    return _official_then_converted("msci_world_quality_eur", usd).rename("quality")


# --------------------------------------------------------------------------
# Treasuries (S5) and gold (S6)
# --------------------------------------------------------------------------

def treasury_usd() -> pd.Series:
    """7-10y Treasury total return in USD, priced from the 10-year yield.

    A par bond with 8.5 years to maturity, repriced monthly. GS10 is a
    monthly *average* yield, which smooths returns slightly compared with an
    index built from month-end prices.
    """
    return tf.par_bond_returns(load("us_10y_yield"), maturity_years=8.5).rename("treasury_usd")


def treasury_eur_unhedged() -> pd.Series:
    return tf.usd_to_eur_returns(treasury_usd(), eurusd()).rename("treasury_eur_unhedged")


def treasury_eur_hedged() -> pd.Series:
    """S5 default: USD Treasuries hedged to EUR (carry = Euribor - T-bill)."""
    return tf.hedged_returns(treasury_usd(), cash_usd(), cash_eur()).rename("treasury_eur_hedged")


def gold_eur() -> pd.Series:
    """S6: gold in EUR from the World Bank's monthly AVERAGE price.

    Monthly averages smooth the series and lag month-end moves by about two
    weeks, so drawdowns look shallower than they were. Good enough for a
    10-month trend filter; to be replaced by month-end prices before the
    final Test 1 run.
    """
    gold_usd = tf.returns_from_levels(load("wb_prices")["Gold"])
    return tf.usd_to_eur_returns(gold_usd, eurusd()).rename("gold")


# --------------------------------------------------------------------------
# Trend sleeve candidates (S4a, S4b)
# --------------------------------------------------------------------------

def trend_s4a_eur(target_vol: float = 0.12, annual_fee: float = 0.0075,
                  excess_haircut: float = 0.5) -> pd.Series:
    """S4a proxy: AQR time-series momentum, held through a EUR-hedged fund.

    AQR's TSMOM series are paper excess returns (over cash), before trading
    costs and fees. The fund is modelled as: TSMOM excess return rescaled to
    the fund's volatility, cut by ``excess_haircut``, plus EUR cash (the fund
    is EUR-hedged and holds its collateral in cash), minus the fund's 0.75%
    fee.

    The haircut is not optional. Unhaircut, this proxy compounds at ~11%/yr
    since 1994, while the SG Trend index of real, net-of-fee trend funds made
    ~5-6%/yr since 2000 (research report). Halving the excess return (the
    report's 40-60% post-publication decay) lands near that live record.
    Scaling uses full-sample volatility, a mild look-ahead that is acceptable
    for a sleeve-level proxy.
    """
    excess = load("aqr_tsmom")["TSMOM"]
    scaled = tf.scale_to_volatility(excess, target_vol) * (1.0 - excess_haircut)
    cash = cash_eur().reindex(scaled.index)
    return (scaled + cash - annual_fee / 12.0).dropna().rename("trend_s4a")


def commodities_eur() -> pd.Series:
    """Broad commodities in EUR for S4b, from the World Bank total index.

    Weakest proxy in the set: a spot price index of monthly averages. It
    misses the roll yield and collateral return an investable commodity ETF
    earns, so long-run returns can be off by several points a year in either
    direction. Used only for S4b's trend filter test.
    """
    spot_usd = tf.returns_from_levels(load("wb_indices")["Total Index"])
    return tf.usd_to_eur_returns(spot_usd, eurusd()).rename("commodities")


def all_sleeves() -> pd.DataFrame:
    """Every sleeve series side by side, on their common months."""
    return pd.concat([
        world_equity_eur(), momentum_eur(), quality_eur(), trend_s4a_eur(),
        treasury_eur_hedged(), treasury_eur_unhedged(), gold_eur(),
        commodities_eur(), cash_eur(),
    ], axis=1)
