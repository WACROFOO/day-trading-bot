"""The frozen primary crypto rule (crypto/frozen_rules.json) and its benchmarks.

Every function takes a daily close series indexed by completed UTC days and
returns a series on the same index. A value dated D uses only closes up to
and including D. It is the exposure decided at 00:05 UTC on D+1 and held
through day D+1, so it earns day D+1's return (``simulate`` applies that
one-day shift).

The parameters live in ``frozen_rules.json``. ``FrozenRule.load()`` reads
them, and a test checks that the code defaults equal the file, so the rule
cannot drift silently. Changing the rule means changing the file, which
restarts the forward record and adds a trial (crypto/PLAN.md §8).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

FROZEN_RULES_JSON = Path(__file__).resolve().parents[3] / "crypto" / "frozen_rules.json"


@dataclass(frozen=True)
class FrozenRule:
    lookback_days: tuple[int, ...] = (30, 91, 182, 365)
    target_annual_vol: float = 0.25
    vol_window_days: int = 60
    annualization_days: int = 365
    max_exposure: float = 1.0
    band_min_change: float = 0.10
    exit_fully_when_target_zero: bool = True
    maker_fee: float = 0.001
    taker_fee: float = 0.002
    spread: float = 0.0002
    forward_record_starts: str = "2026-11-26"
    name: str = field(default="crypto-primary-v1", compare=False)

    @classmethod
    def load(cls, path: Path = FROZEN_RULES_JSON) -> "FrozenRule":
        spec = json.loads(Path(path).read_text())
        return cls(
            lookback_days=tuple(spec["signal"]["lookback_days"]),
            target_annual_vol=spec["sizing"]["target_annual_vol"],
            vol_window_days=spec["sizing"]["vol_window_days"],
            annualization_days=spec["sizing"]["annualization_days"],
            max_exposure=spec["sizing"]["max_exposure"],
            band_min_change=spec["band"]["min_change"],
            exit_fully_when_target_zero=spec["band"]["exit_fully_when_target_zero"],
            maker_fee=spec["cost_model"]["maker"],
            taker_fee=spec["cost_model"]["taker_fallback"],
            spread=spec["cost_model"]["spread"],
            forward_record_starts=spec["forward_record_starts"],
            name=spec["name"],
        )


def _daily(close: pd.Series) -> pd.Series:
    """Validate a daily close series: sorted, unique, no gaps, all positive."""
    s = close.dropna().sort_index()
    if not s.index.is_unique:
        raise ValueError("duplicate dates in close series")
    expected = pd.date_range(s.index.min(), s.index.max(), freq="D")
    missing = expected.difference(s.index)
    if len(missing):
        raise ValueError(f"{len(missing)} missing days in close series, first {missing[0].date()}")
    if (s <= 0).any():
        raise ValueError("non-positive prices in close series")
    return s


def ensemble_signal(close: pd.Series, lookback_days=(30, 91, 182, 365)) -> pd.Series:
    """Share of lookbacks with a positive return: 0, 0.25, 0.5, 0.75 or 1.

    NaN until the longest lookback has history.
    """
    s = _daily(close)
    votes = [(s / s.shift(L) > 1.0).astype(float).where(s.shift(L).notna()) for L in lookback_days]
    return pd.concat(votes, axis=1).mean(axis=1, skipna=False).rename("signal")


def realised_vol(close: pd.Series, window: int = 60, annualization_days: int = 365) -> pd.Series:
    """Annualised stdev of the last ``window`` daily log returns (ending on D)."""
    s = _daily(close)
    log_ret = np.log(s / s.shift(1))
    return (log_ret.rolling(window).std(ddof=1) * np.sqrt(annualization_days)).rename("vol")


def raw_target(close: pd.Series, rule: FrozenRule = FrozenRule()) -> pd.Series:
    """signal × min(max_exposure, target_vol / realised vol), before the band."""
    signal = ensemble_signal(close, rule.lookback_days)
    vol = realised_vol(close, rule.vol_window_days, rule.annualization_days)
    scale = (rule.target_annual_vol / vol).clip(upper=rule.max_exposure)
    return (signal * scale).rename("raw_target")


def apply_band(target: pd.Series, min_change: float = 0.10,
               exit_fully_when_target_zero: bool = True) -> pd.Series:
    """Executed exposure: move only on changes of at least ``min_change``.

    A zero target always exits fully, so a small leftover position can never
    linger through a downtrend. Days before the target exists stay NaN.
    """
    out, current = [], 0.0
    for value in target.to_numpy():
        if np.isnan(value):
            out.append(np.nan)
            continue
        if (exit_fully_when_target_zero and value == 0.0) or abs(value - current) >= min_change - 1e-12:
            current = float(value)
        out.append(current)
    return pd.Series(out, index=target.index, name="exposure")


def primary_exposure(close: pd.Series, rule: FrozenRule = FrozenRule()) -> pd.Series:
    """The frozen primary rule: banded, volatility-targeted trend ensemble."""
    return apply_band(raw_target(close, rule), rule.band_min_change, rule.exit_fully_when_target_zero)


def c1_sma200_exposure(close: pd.Series, window: int = 200) -> pd.Series:
    """Benchmark C1: 100% while the close is above its 200-day average, else 0."""
    s = _daily(close)
    sma = s.rolling(window).mean()
    return (s > sma).astype(float).where(sma.notna()).rename("c1_exposure")


def simulate(close: pd.Series, exposure: pd.Series, fee_per_trade: float = 0.004,
             spread: float = 0.0002, start: str | None = None) -> pd.DataFrame:
    """Daily NAV for an exposure path (no contributions, cash earns 0%).

    exposure[D] is held during day D+1. Each change in exposure pays
    (fee + spread) on the traded fraction of NAV. Starts at 1.0 on ``start``
    (or on the first day the exposure exists).
    """
    s = _daily(close)
    ret = s.pct_change()
    held = exposure.shift(1)  # decided on D, earns D+1
    frame = pd.DataFrame({"ret": ret, "held": held, "decided": exposure}).dropna()
    if start is not None:
        frame = frame[frame.index >= pd.Timestamp(start)]
    if frame.empty:
        return pd.DataFrame(columns=["nav", "exposure", "turnover"])
    nav, navs, turnovers = 1.0, [], []
    prev_decided = frame["held"].iloc[0]
    for r, held_today, decided in frame[["ret", "held", "decided"]].itertuples(index=False):
        nav *= 1.0 + held_today * r
        traded = abs(decided - prev_decided)
        nav *= 1.0 - traded * (fee_per_trade + spread)
        prev_decided = decided
        navs.append(nav)
        turnovers.append(traded)
    return pd.DataFrame({"nav": navs, "exposure": frame["decided"].to_numpy(),
                         "turnover": turnovers}, index=frame.index)
