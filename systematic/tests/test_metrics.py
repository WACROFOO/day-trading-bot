"""Known-answer tests for the shared metrics, including the deflated Sharpe ratio."""

import math
from statistics import NormalDist

import numpy as np
import pandas as pd
import pytest

from portfolio_bot.engine import metrics


def test_max_drawdown_and_cagr():
    nav = pd.Series([100.0, 120.0, 90.0, 130.0])
    assert metrics.max_drawdown(nav) == pytest.approx(-0.25)
    assert metrics.cagr(pd.Series([100.0, 110.0, 121.0]), periods_per_year=1) == pytest.approx(0.10)


def test_expected_max_sharpe_grows_with_trials():
    trials = [0.02, 0.05, 0.03, 0.06, 0.04]
    assert metrics.expected_max_sharpe(trials, 10) < metrics.expected_max_sharpe(trials, 100)


def test_deflated_sharpe_matches_hand_formula_for_normal_returns():
    rng = np.random.default_rng(1)
    r = pd.Series(rng.normal(0.001, 0.01, 2000))
    trials = [0.01, 0.03, 0.02, 0.05]
    got = metrics.deflated_sharpe(r, trials, n_trials=10)
    sr = r.mean() / r.std(ddof=1)
    c = r - r.mean()
    skew = (c ** 3).mean() / r.std(ddof=0) ** 3
    kurt = (c ** 4).mean() / r.std(ddof=0) ** 4
    sr0 = metrics.expected_max_sharpe(trials, 10)
    want = NormalDist().cdf((sr - sr0) * math.sqrt(len(r) - 1) / math.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr ** 2))
    assert got == pytest.approx(want)


def test_more_trials_lower_the_deflated_sharpe():
    rng = np.random.default_rng(2)
    r = pd.Series(rng.normal(0.0008, 0.01, 1500))
    trials = [0.01, 0.04, 0.02, 0.06, 0.03]
    assert metrics.deflated_sharpe(r, trials, 50) < metrics.deflated_sharpe(r, trials, 5)


def test_one_trial_is_refused():
    with pytest.raises(ValueError):
        metrics.expected_max_sharpe([0.1, 0.2], 1)
