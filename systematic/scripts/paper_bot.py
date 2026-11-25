"""Daily paper bot for the frozen crypto rule (no API key, nothing traded).

Usage (from the repo root):
    python systematic/scripts/paper_bot.py [--out-dir systematic/paper]

Each run:
  1. downloads public Bitstamp daily closes (BTC/USD, ETH/USD) and refuses to
     continue if the last completed day isn't yesterday (fresh-data check);
  2. recomputes record.csv (exposures and NAVs since the forward start);
  3. logs today's decision with the live OKX BTC-USDC / ETH-USDC bid and ask
     in decisions.csv, once per date.

Exit codes: 0 ok, 2 stale data. In GitHub Actions a failed run emails the
repo owner, which is the alert.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from portfolio_bot.crypto import paper, rules  # noqa: E402
from portfolio_bot.data import catalog  # noqa: E402
from portfolio_bot.data.sources import completed_days, http_get  # noqa: E402

OKX_HOSTS = ("eea.okx.com", "www.okx.com")


def okx_quotes() -> tuple[str, dict]:
    """Live bid/ask from OKX's public ticker; tries the EEA host first."""
    for host in OKX_HOSTS:
        try:
            out = {}
            for coin in ("btc", "eth"):
                bid, ask = paper.parse_okx_ticker(
                    http_get(f"https://{host}/api/v5/market/ticker?instId={coin.upper()}-USDC", retries=2))
                out[f"{coin}_usdc_bid"], out[f"{coin}_usdc_ask"] = bid, ask
            return host, out
        except Exception:  # unreachable or blocked from this runner: try the next host
            continue
    return "unavailable", {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", default=str(ROOT / "paper"))
    args = parser.parse_args()
    out_dir = Path(args.out_dir)

    rule = rules.FrozenRule.load()
    btc = completed_days(catalog.load("btcusd_daily", refresh=True))["close"]
    eth = completed_days(catalog.load("ethusd_daily", refresh=True))["close"]
    now = pd.Timestamp.now(tz="UTC")
    yesterday = now.tz_localize(None).normalize() - pd.Timedelta(days=1)
    if btc.index[-1] < yesterday or eth.index[-1] < yesterday:
        print(f"STALE DATA: last BTC close {btc.index[-1]:%Y-%m-%d}, ETH {eth.index[-1]:%Y-%m-%d}, "
              f"expected {yesterday:%Y-%m-%d}. Nothing recorded.")
        return 2

    record = paper.build_record(btc, eth, rule, rule.forward_record_starts)
    out_dir.mkdir(parents=True, exist_ok=True)
    record.to_csv(out_dir / "record.csv", float_format="%.6f")

    row = paper.decision(btc, eth, rule)
    source, quotes = okx_quotes()
    row.update({"run_utc": now.strftime("%Y-%m-%d %H:%M"), "quote_source": source, **quotes})
    written = paper.append_decision(out_dir / "decisions.csv", row)

    print(f"Decision for {row['decision_date']} (after the {row['based_on_close']} close):")
    print(f"  primary {row['primary']:.0%} BTC | V1 {row['v1_btc']:.0%} BTC + {row['v1_eth']:.0%} ETH | "
          f"V2 {row['v2_weekly']:.0%} BTC | C1 {row['c1_sma200']:.0%} BTC")
    print(f"  OKX quotes: {source}{'' if written else ' (decision already logged; not duplicated)'}")
    if len(record):
        last = record.iloc[-1]
        navs = "  ".join(f"{s} {last[f'{s}_nav'] - 1:+.1%}" for s in paper.STRATEGIES if f"{s}_nav" in record)
        print(f"  Forward record, {len(record)} day(s) since {rule.forward_record_starts}: {navs}")
    else:
        print(f"  Forward record starts {rule.forward_record_starts}; no completed forward day yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
