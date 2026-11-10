"""Named raw series, downloaded once and cached locally as CSV.

``load("msci_world_usd")`` returns the cached copy if there is one, and
otherwise downloads it, writes it to the cache with a small metadata file
(source, download time), and returns it. ``refresh=True`` forces a fresh
download.

The cache lives in ``systematic/data/raw/``, which is gitignored: none of this
data is ever committed (several providers restrict redistribution).
Override the location with the PORTFOLIO_BOT_DATA_DIR environment variable.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

from . import sources as src

Data = pd.Series | pd.DataFrame


@dataclass(frozen=True)
class Spec:
    name: str
    fetch: Callable[[], Data]
    description: str
    source: str
    frequency: str = "monthly"  # "monthly" series get the structural checks


def _fred_monthly(series: str) -> pd.Series:
    s = src.fetch_fred(series)
    s.index = src.to_month_end(s.index)
    return s


CATALOG: dict[str, Spec] = {spec.name: spec for spec in [
    # --- equities: MSCI end-of-month, net total return, 1997+ -------------
    Spec("msci_world_usd", lambda: src.fetch_msci("990100", currency="USD"),
         "MSCI World, net total return, USD (S1 proxy)", "MSCI index 990100"),
    Spec("msci_world_usd_price", lambda: src.fetch_msci("990100", currency="USD", variant="STRD"),
         "MSCI World price index (no dividends), USD, 1997+ (backfill before Dec 2000)",
         "MSCI index 990100"),
    Spec("msci_world_eur", lambda: src.fetch_msci("990100", currency="EUR"),
         "MSCI World, net total return, EUR (from Dec 2000; FX cross-check)", "MSCI index 990100"),
    Spec("msci_world_momentum_usd", lambda: src.fetch_msci("703755", currency="USD"),
         "MSCI World Momentum, net, USD (S2 proxy; back-tested before Dec 2013)", "MSCI index 703755"),
    Spec("msci_world_quality_usd", lambda: src.fetch_msci("702787", currency="USD"),
         "MSCI World Quality, net, USD (S3 proxy; back-tested before launch)", "MSCI index 702787"),
    Spec("msci_world_momentum_eur", lambda: src.fetch_msci("703755", currency="EUR"),
         "MSCI World Momentum, net, EUR (from Dec 1998)", "MSCI index 703755"),
    Spec("msci_world_quality_eur", lambda: src.fetch_msci("702787", currency="EUR"),
         "MSCI World Quality, net, EUR (from Dec 1998)", "MSCI index 702787"),
    # --- long-history factors ------------------------------------------------
    Spec("ff_factors_us", lambda: src.fetch_ken_french("F-F_Research_Data_Factors"),
         "Fama-French US factors incl. market and T-bill, 1926+", "Ken French data library"),
    Spec("ff_momentum_us", lambda: src.fetch_ken_french("F-F_Momentum_Factor"),
         "US momentum factor (long-short), 1927+", "Ken French data library"),
    Spec("aqr_tsmom", lambda: src.fetch_aqr("Time-Series-Momentum-Factors-Monthly"),
         "Time-series momentum excess returns (all assets and by class), 1985+ (S4a proxy)",
         "AQR data sets"),
    # --- rates and FX -------------------------------------------------------
    Spec("us_10y_yield", lambda: _fred_monthly("GS10"),
         "US 10-year Treasury constant-maturity yield, %, monthly average", "FRED GS10"),
    Spec("us_3m_tbill", lambda: _fred_monthly("TB3MS"),
         "US 3-month T-bill rate, %, monthly (USD cash)", "FRED TB3MS"),
    Spec("eurusd_daily", lambda: src.fetch_fred("DEXUSEU"),
         "USD per EUR, daily, 1999+", "FRED DEXUSEU", frequency="daily"),
    Spec("demusd_monthly", lambda: _fred_monthly("EXGEUS"),
         "DEM per USD, monthly average, 1971-2001 (pre-euro extension; the daily "
         "DEXGEUS series was removed from FRED)", "FRED EXGEUS"),
    Spec("euribor_3m", lambda: src.fetch_ecb("FM", "M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA"),
         "3-month Euribor, %, monthly, 1994+ (EUR cash)", "ECB Data Portal"),
    # --- commodities --------------------------------------------------------
    Spec("wb_prices", lambda: src.fetch_world_bank("Monthly Prices"),
         "World Bank Pink Sheet prices, monthly AVERAGES, USD, 1960+ (gold)", "World Bank"),
    Spec("wb_indices", lambda: src.fetch_world_bank("Monthly Indices"),
         "World Bank commodity price indices, monthly averages, 2010=100, 1960+", "World Bank"),
]}


def data_dir() -> Path:
    override = os.environ.get("PORTFOLIO_BOT_DATA_DIR")
    base = Path(override) if override else Path(__file__).resolve().parents[3] / "data"
    path = base / "raw"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load(name: str, *, refresh: bool = False, catalog: dict[str, Spec] | None = None) -> Data:
    """Cached copy of a named series, downloading it if needed."""
    catalog = catalog or CATALOG
    if name not in catalog:
        raise KeyError(f"unknown series {name!r}; known: {sorted(catalog)}")
    spec = catalog[name]
    csv_path, meta_path = data_dir() / f"{name}.csv", data_dir() / f"{name}.meta.json"

    if csv_path.exists() and meta_path.exists() and not refresh:
        return _read(csv_path, json.loads(meta_path.read_text()).get("kind", "frame"))

    data = spec.fetch()
    data.to_csv(csv_path)
    meta = {
        "name": name,
        "description": spec.description,
        "source": spec.source,
        "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "first": str(data.index.min().date()),
        "last": str(data.index.max().date()),
        "rows": int(len(data)),
        "kind": "series" if isinstance(data, pd.Series) else "frame",
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    return data


def metadata(name: str) -> dict | None:
    path = data_dir() / f"{name}.meta.json"
    return json.loads(path.read_text()) if path.exists() else None


def _read(path: Path, kind: str) -> Data:
    """Read a cached CSV back as the same type that was downloaded."""
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.index.name = None
    if kind == "series":
        s = df.iloc[:, 0]
        s.name = None if s.name == "0" else s.name
        return s
    return df
