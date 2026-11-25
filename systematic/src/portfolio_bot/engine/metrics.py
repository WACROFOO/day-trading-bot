"""Performance metrics shared by both tracks (ENGINE.md §6)."""

from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pandas as pd

EULER_GAMMA = 0.5772156649015329
_N = NormalDist()


def max_drawdown(nav: pd.Series) -> float:
    """Worst peak-to-trough fall of a NAV path (negative number)."""
    return float((nav / nav.cummax() - 1.0).min())


def sharpe(returns: pd.Series, periods_per_year: float) -> float:
    """Annualised Sharpe ratio of periodic returns (risk-free rate 0)."""
    r = returns.dropna()
    sd = r.std(ddof=1)
    return float(r.mean() / sd * math.sqrt(periods_per_year)) if sd > 0 else float("nan")


def cagr(nav: pd.Series, periods_per_year: float) -> float:
    years = (len(nav) - 1) / periods_per_year
    return float((nav.iloc[-1] / nav.iloc[0]) ** (1.0 / years) - 1.0) if years > 0 else float("nan")


def expected_max_sharpe(trial_sharpes: list[float], n_trials: int) -> float:
    """SR0: the best Sharpe expected from ``n_trials`` skill-less trials.

    Bailey & López de Prado (2014), using the variance of the Sharpe ratios
    actually observed across trials. Same units as ``trial_sharpes``.
    """
    if n_trials < 2:
        raise ValueError("need at least 2 trials")
    var = float(np.var(trial_sharpes, ddof=1))
    z1 = _N.inv_cdf(1.0 - 1.0 / n_trials)
    z2 = _N.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
    return math.sqrt(var) * ((1.0 - EULER_GAMMA) * z1 + EULER_GAMMA * z2)


def deflated_sharpe(returns: pd.Series, trial_sharpes_per_period: list[float], n_trials: int) -> float:
    """Probability that the true Sharpe exceeds what ``n_trials`` lucky trials would show.

    Bailey & López de Prado (2014), "The Deflated Sharpe Ratio". Everything is
    in per-period units (not annualised). It corrects for skewness and fat
    tails of ``returns`` and for the number of strategies tried. A value of at
    least 0.95 is the evidence funnel's bar (STRATEGY.md §7).
    """
    r = returns.dropna()
    t = len(r)
    sr = r.mean() / r.std(ddof=1)
    skew = float(((r - r.mean()) ** 3).mean() / r.std(ddof=0) ** 3)
    kurt = float(((r - r.mean()) ** 4).mean() / r.std(ddof=0) ** 4)  # normal = 3
    sr0 = expected_max_sharpe(trial_sharpes_per_period, n_trials)
    denom = math.sqrt(max(1e-12, 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr ** 2))
    return _N.cdf((sr - sr0) * math.sqrt(t - 1) / denom)
