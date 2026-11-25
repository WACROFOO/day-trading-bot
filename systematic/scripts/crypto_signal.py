"""Today's decision from the frozen crypto rule, and its forward record.

Usage (from the repo root):
    python systematic/scripts/crypto_signal.py              # fresh data, today's decision + forward record
    python systematic/scripts/crypto_signal.py --reconcile  # also reproduce the research replication

The forward record starts on the date in crypto/frozen_rules.json. Prices are
public Bitstamp daily closes; nothing is traded. Paper record only: no
contributions, cash at 0%, fees per the frozen cost model.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from portfolio_bot.crypto import rules  # noqa: E402
from portfolio_bot.data import catalog  # noqa: E402
from portfolio_bot.data.sources import completed_days  # noqa: E402


def stats(nav: pd.Series, turnover: pd.Series) -> str:
    rets = nav.pct_change().dropna()
    years = len(nav) / 365.0
    cagr = nav.iloc[-1] ** (1.0 / years) - 1.0
    sharpe = rets.mean() / rets.std() * np.sqrt(365.0) if rets.std() > 0 else float("nan")
    max_dd = (nav / nav.cummax() - 1.0).min()
    return (f"CAGR {cagr:6.1%}  Sharpe {sharpe:5.2f}  max DD {max_dd:6.1%}  "
            f"turnover {turnover.sum() / years:4.1f}/yr")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cached", action="store_true", help="use cached prices instead of downloading")
    parser.add_argument("--reconcile", action="store_true",
                        help="reproduce the research replication on BTC/USD (already-logged configuration)")
    args = parser.parse_args()

    rule = rules.FrozenRule.load()
    candles = completed_days(catalog.load("btceur_daily", refresh=not args.cached))
    close = candles["close"]
    day = close.index[-1]
    yesterday = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize() - pd.Timedelta(days=1)
    if day < yesterday - pd.Timedelta(days=1):
        print(f"STALE DATA: last completed day is {day:%Y-%m-%d}, expected {yesterday:%Y-%m-%d}. "
              "No decision computed (STRATEGY.md §5 fresh-data check).")
        return 1

    votes = {L: bool(close.iloc[-1] > close.iloc[-1 - L]) for L in rule.lookback_days}
    vol = rules.realised_vol(close, rule.vol_window_days, rule.annualization_days).iloc[-1]
    raw = rules.raw_target(close, rule).iloc[-1]
    exposure = rules.primary_exposure(close, rule)
    c1 = rules.c1_sma200_exposure(close)
    sma200 = close.rolling(200).mean().iloc[-1]

    print(f"== {rule.name}: decision after the {day:%Y-%m-%d} close (UTC) ==")
    print(f"  BTC/EUR close            {close.iloc[-1]:,.2f}")
    print("  trend votes              " + "  ".join(f"{L}d:{'up' if v else 'down'}" for L, v in votes.items()))
    print(f"  signal                   {rules.ensemble_signal(close, rule.lookback_days).iloc[-1]:.2f}")
    print(f"  60-day volatility        {vol:.1%} a year")
    print(f"  raw target               {raw:.1%} in BTC")
    print(f"  exposure after band      {exposure.iloc[-1]:.1%} in BTC, {1 - exposure.iloc[-1]:.1%} in EURC")
    print(f"  benchmark C1 (200-day)   {'in' if c1.iloc[-1] == 1 else 'out'} "
          f"(200-day average {sma200:,.2f})")

    start = pd.Timestamp(rule.forward_record_starts)
    print(f"\n== Forward record since {start:%Y-%m-%d} (paper, fees {rule.maker_fee:.2%} + spread) ==")
    if day < start:
        print("  not started yet: the first decision counts after the "
              f"{(start - pd.Timedelta(days=1)):%Y-%m-%d} close")
    else:
        prim = rules.simulate(close, exposure, rule.maker_fee, rule.spread, start=str(start.date()))
        bench = rules.simulate(close, c1, rule.maker_fee, rule.spread, start=str(start.date()))
        hold = close[close.index >= start] / close[close.index >= start].iloc[0]
        print(f"  days                     {len(prim)}")
        print(f"  primary                  {prim['nav'].iloc[-1] - 1:+.1%}  "
              f"(exposure changes: {int((prim['turnover'] > 0).sum())})")
        print(f"  C1 benchmark             {bench['nav'].iloc[-1] - 1:+.1%}")
        print(f"  BTC buy and hold         {hold.iloc[-1] - 1:+.1%}")

    if args.reconcile:
        usd = completed_days(catalog.load("btcusd_daily", refresh=not args.cached))["close"]
        if usd.index[-1] < yesterday - pd.Timedelta(days=1):
            print(f"STALE BTC/USD data (last {usd.index[-1]:%Y-%m-%d}); reconciliation skipped.")
            return 1
        usd = usd[usd.index >= "2014-01-01"]
        exp_usd = rules.primary_exposure(usd, rule)
        sim = rules.simulate(usd, exp_usd, fee_per_trade=0.0025, spread=0.0, start="2015-01-01")
        sim = sim[sim.index <= "2026-11-24"]
        print("\n== Reconciliation with the research replication (BTC/USD, 0.25%/trade, 2015-01-01 → 2026-11-24) ==")
        print(f"  ours                     {stats(sim['nav'], sim['turnover'])}")
        print("  research (experiments.csv ext-20261125-06)  CAGR  26.5%  Sharpe  1.25  max DD -30.7%  turnover  5.0/yr")
        print("  Small differences can come from data handling; large ones mean a bug.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
