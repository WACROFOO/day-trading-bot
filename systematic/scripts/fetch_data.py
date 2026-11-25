"""Download every series, run the Gate G2 data checks, and print a report.

Usage (from the repo root):
    python systematic/scripts/fetch_data.py            # use the cache where present
    python systematic/scripts/fetch_data.py --refresh  # download everything again

Exits with status 1 if any check fails, so it can gate later steps.
Data lands in systematic/data/raw/ (gitignored) and is never committed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from portfolio_bot.data import catalog, checks, references, sleeves  # noqa: E402
from portfolio_bot.data import transforms as tf  # noqa: E402
from portfolio_bot.data.checks import CheckResult  # noqa: E402

# The column of each table that the backtests actually use.
KEY_COLUMNS = {
    "ff_factors_us": ["Mkt-RF", "RF"],
    "ff_momentum_us": ["Mom"],
    "aqr_tsmom": ["TSMOM"],
    "wb_prices": ["Gold"],
    "wb_indices": ["Total Index"],
}
LEVEL_SERIES = ["msci_world_usd", "msci_world_usd_price", "msci_world_eur",
                "msci_world_momentum_usd", "msci_world_quality_usd",
                "msci_world_momentum_eur", "msci_world_quality_eur"]
REFERENCE_CHECKS = {
    "msci_world_usd": references.MSCI_WORLD_USD_NET,
    "msci_world_momentum_usd": references.MSCI_WORLD_MOMENTUM_USD_NET,
    "msci_world_quality_usd": references.MSCI_WORLD_QUALITY_USD_NET,
}


def summary(r: pd.Series) -> str:
    r = r.dropna()
    years = len(r) / 12.0
    cagr = (1.0 + r).prod() ** (1.0 / years) - 1.0
    vol = r.std() * np.sqrt(12.0)
    wealth = (1.0 + r).cumprod()
    max_dd = (wealth / wealth.cummax() - 1.0).min()
    return (f"{r.index.min():%Y-%m} → {r.index.max():%Y-%m}  "
            f"CAGR {cagr:6.1%}  vol {vol:5.1%}  max DD {max_dd:6.1%}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refresh", action="store_true", help="download everything again")
    args = parser.parse_args()

    results: list[CheckResult] = []
    loaded: dict[str, pd.Series | pd.DataFrame] = {}

    print("== Coverage ==")
    for name, spec in catalog.CATALOG.items():
        try:
            data = catalog.load(name, refresh=args.refresh)
        except Exception as exc:  # report and keep going: one dead source should not hide the rest
            results.append(CheckResult(f"{name}: download", False, str(exc)[:160]))
            print(f"  {name:26s} DOWNLOAD FAILED: {exc}")
            continue
        loaded[name] = data
        print(f"  {name:26s} {data.index.min():%Y-%m-%d} → {data.index.max():%Y-%m-%d}  "
              f"{len(data):6d} rows  {spec.source}")

        if spec.frequency != "monthly":
            continue
        if isinstance(data, pd.DataFrame):
            for col in KEY_COLUMNS.get(name, list(data.columns)):
                results += checks.check_monthly_index(data[col].dropna(), f"{name}[{col}]")
        else:
            results += checks.check_monthly_index(data, name)

    print("\n== Known answers ==")
    for name in LEVEL_SERIES:
        if name in loaded:
            results.append(checks.check_jumps(tf.returns_from_levels(loaded[name]), name,
                                              allowed=references.KNOWN_BIG_MONTHS.get(name)))
    for name, ref in REFERENCE_CHECKS.items():
        if name in loaded:
            results.append(checks.compare_annual(loaded[name], ref, name))

    # Our USD->EUR conversion must reproduce MSCI's own EUR series over time.
    conversions = [
        ("MSCI World", lambda: sleeves.world_equity_usd(), "msci_world_eur"),
        ("MSCI World Momentum", lambda: tf.returns_from_levels(loaded["msci_world_momentum_usd"]),
         "msci_world_momentum_eur"),
        ("MSCI World Quality", lambda: tf.returns_from_levels(loaded["msci_world_quality_usd"]),
         "msci_world_quality_eur"),
    ]
    for label, usd, eur_name in conversions:
        try:
            ours = sleeves.converted_eur(usd())
            official = tf.returns_from_levels(loaded[eur_name])
            results.append(checks.check_conversion(ours, official, label))
        except Exception as exc:
            results.append(CheckResult(f"{label}: EUR conversion", False, str(exc)[:160]))

    for r in results:
        if "published annual returns" in r.name or "EUR conversion" in r.name or not r.ok:
            print(f"  {r}")

    print("\n== Sleeves (EUR, monthly total returns) ==")
    builders = {
        "S1 world equity": sleeves.world_equity_eur,
        "S2 momentum": sleeves.momentum_eur,
        "S3 quality": sleeves.quality_eur,
        "S4a trend fund (proxy)": sleeves.trend_s4a_eur,  # 50% haircut on excess
        "S5 Treasuries hedged": sleeves.treasury_eur_hedged,
        "S5 Treasuries unhedged": sleeves.treasury_eur_unhedged,
        "S6 gold": sleeves.gold_eur,
        "S4b commodities (spot)": sleeves.commodities_eur,
        "S7 EUR cash": sleeves.cash_eur,
    }
    for label, build in builders.items():
        try:
            print(f"  {label:24s} {summary(build())}")
        except Exception as exc:
            results.append(CheckResult(f"{label}: build", False, str(exc)[:160]))
            print(f"  {label:24s} BUILD FAILED: {exc}")

    failed = [r for r in results if not r.ok]
    print(f"\n== Gate G2: {len(results) - len(failed)}/{len(results)} checks passed ==")
    for r in failed:
        print(f"  {r}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
