"""Forward paper record for the frozen crypto rule, its variants and benchmarks.

Two files, both free of personal amounts (NAVs start at 1.0):

- ``record.csv``: one row per completed UTC day since the forward start,
  with each strategy's exposure and NAV. It is recomputed in full from
  public prices on every run, so a re-run always gives the same result
  (frozen band: "the exposure path matches a re-run").
- ``decisions.csv``: one row per decision date. It holds the targets
  decided after the previous day's close, plus the live OKX bid/ask seen at
  that moment. It is append-only, written once per date, so re-running the
  job never adds a duplicate (LESSONS B5). The quotes are what CG3 uses to
  check realised costs against the model.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import rules

STRATEGIES = ("primary", "v1_btc_eth", "v2_weekly", "c1_sma200", "btc_buy_hold")
DECISION_FIELDS = [
    "decision_date", "based_on_close", "run_utc",
    "primary", "v1_btc", "v1_eth", "v2_weekly", "c1_sma200",
    "btc_close", "eth_close", "quote_source",
    "btc_usdc_bid", "btc_usdc_ask", "eth_usdc_bid", "eth_usdc_ask",
]


def simulate_multi(closes: dict[str, pd.Series], exposures: pd.DataFrame, cost: float,
                   start: str) -> pd.Series:
    """NAV of a multi-coin exposure path (exposure on D earns D+1; cash 0%)."""
    rets = pd.DataFrame({k: v.pct_change() for k, v in closes.items()})
    held = exposures.shift(1)
    idx = rets.index.intersection(held.dropna().index)
    idx = idx[idx >= pd.Timestamp(start)]
    nav, out = 1.0, {}
    prev = held.loc[idx[0]] if len(idx) else None
    for day in idx:
        nav *= 1.0 + float((held.loc[day] * rets.loc[day]).sum())
        traded = float((exposures.loc[day] - prev).abs().sum())
        nav *= 1.0 - traded * cost
        prev = exposures.loc[day]
        out[day] = nav
    return pd.Series(out, name="nav", dtype=float)


def build_record(btc: pd.Series, eth: pd.Series, rule: rules.FrozenRule, start: str) -> pd.DataFrame:
    """Exposures and NAVs of every tracked strategy, from ``start`` to the last close."""
    cost = rule.maker_fee + rule.spread
    common = btc.index.intersection(eth.index)
    btc_c, eth_c = btc.loc[common], eth.loc[common]
    exp = {
        "primary": rules.primary_exposure(btc, rule),
        "v2_weekly": rules.v2_weekly_exposure(btc, rule),
        "c1_sma200": rules.c1_sma200_exposure(btc),
    }
    v1 = rules.v1_btc_eth_exposures(btc_c, eth_c, rule)
    navs = {name: rules.simulate(btc, e, cost, 0.0, start=start)["nav"] for name, e in exp.items()}
    navs["v1_btc_eth"] = simulate_multi({"BTC": btc_c, "ETH": eth_c}, v1, cost, start)
    window = btc[btc.index >= pd.Timestamp(start)]
    if len(window):
        prior = btc[btc.index < pd.Timestamp(start)].iloc[-1]
        navs["btc_buy_hold"] = window / prior
    frame = pd.DataFrame(index=window.index)
    frame["btc_close"] = window
    frame["eth_close"] = eth.reindex(window.index)
    for name, e in exp.items():
        frame[f"{name}_exposure"] = e.reindex(window.index)
    frame["v1_btc_exposure"] = v1["BTC"].reindex(window.index)
    frame["v1_eth_exposure"] = v1["ETH"].reindex(window.index)
    for name in STRATEGIES:
        if name in navs:
            frame[f"{name}_nav"] = navs[name].reindex(window.index)
    frame.index.name = "date"
    return frame


def decision(btc: pd.Series, eth: pd.Series, rule: rules.FrozenRule) -> dict:
    """Targets decided after the last completed close, held during the next UTC day."""
    common = btc.index.intersection(eth.index)
    v1 = rules.v1_btc_eth_exposures(btc.loc[common], eth.loc[common], rule).iloc[-1]
    last = btc.index[-1]
    return {
        "decision_date": str((last + pd.Timedelta(days=1)).date()),
        "based_on_close": str(last.date()),
        "primary": round(float(rules.primary_exposure(btc, rule).iloc[-1]), 4),
        "v1_btc": round(float(v1["BTC"]), 4),
        "v1_eth": round(float(v1["ETH"]), 4),
        "v2_weekly": round(float(rules.v2_weekly_exposure(btc, rule).iloc[-1]), 4),
        "c1_sma200": float(rules.c1_sma200_exposure(btc).iloc[-1]),
        "btc_close": float(btc.iloc[-1]),
        "eth_close": float(eth.iloc[-1]),
    }


def parse_okx_ticker(payload: bytes) -> tuple[float, float]:
    """OKX public ticker JSON -> (bid, ask)."""
    data = json.loads(payload)
    if str(data.get("code")) != "0" or not data.get("data"):
        raise ValueError(f"OKX ticker error: {data.get('msg', data)}")
    row = data["data"][0]
    return float(row["bidPx"]), float(row["askPx"])


def append_decision(path: Path, row: dict) -> bool:
    """Append a decision row unless its date is already logged. True if written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with path.open() as f:
            if any(r["decision_date"] == row["decision_date"] for r in csv.DictReader(f)):
                return False
    new = not path.exists()
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=DECISION_FIELDS, extrasaction="ignore")
        if new:
            writer.writeheader()
        writer.writerow({k: ("" if (isinstance(v, float) and np.isnan(v)) else v) for k, v in row.items()})
    return True
