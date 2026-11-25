"""Gate CG1 for the frozen crypto rule: the backtest on data before the hold-out.

Usage (from the repo root):
    python systematic/scripts/crypto_cg1.py            # fresh data
    python systematic/scripts/crypto_cg1.py --cached   # cached data

Pre-registered criteria (fixed before this script was first run, 25 Nov 2026,
from crypto/PLAN.md §8). Data: Bitstamp BTC/USD daily closes up to
30 Nov 2024. Costs: the frozen cost model, maker fee plus spread, per unit
of exposure traded.

  A. PRIMARY: strategy max drawdown < half of BTC buy-and-hold's max
     drawdown, in window W1 (2015-2020), window W2 (2021-2023) and the full
     period (2015 - Nov 2024). Window W3 (Jan-Nov 2024) is reported only:
     11 months is too short to judge.
  B. Deflated Sharpe ratio >= 0.95 on the full period, with N = 10 trials
     and the trial Sharpe ratios in research/experiments.csv.
  C. At 2x costs, criterion A still holds on the full period, and the
     strategy's Sharpe is at least buy-and-hold's.
  Reported, not gated: windows by year, the C1 benchmark, turnover, the
  same rule on ETH/USD, and the strategy's max drawdown in EUR (the USDC
  leg converted at FRED EUR/USD) against the -30% pain limit.

Writes systematic/research/results/crypto_cg1.md and logs the run in
systematic/research/experiments.csv (same configuration as
ext-20261125-06, so not a new trial).
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from portfolio_bot.crypto import rules  # noqa: E402
from portfolio_bot.data import catalog  # noqa: E402
from portfolio_bot.data.sources import completed_days  # noqa: E402
from portfolio_bot.engine import metrics as m  # noqa: E402

END = "2024-11-30"
WINDOWS = {
    "W1 2015-2020": ("2015-01-01", "2020-12-31"),
    "W2 2021-2023": ("2021-01-01", "2023-12-31"),
    "W3 Jan-Nov 2024 (reported only)": ("2024-01-01", END),
    "Full 2015 - Nov 2024": ("2015-01-01", END),
}
GATED_WINDOWS = ["W1 2015-2020", "W2 2021-2023", "Full 2015 - Nov 2024"]
N_TRIALS = 10
RESULTS = ROOT / "research" / "results" / "crypto_cg1.md"
EXPERIMENTS = ROOT / "research" / "experiments.csv"


def window_stats(close: pd.Series, exposure: pd.Series, cost: float, start: str, end: str) -> dict:
    sim = rules.simulate(close, exposure, fee_per_trade=cost, spread=0.0, start=start)
    sim = sim[sim.index <= end]
    hold = close[(close.index >= sim.index[0]) & (close.index <= end)]
    hold_nav = hold / hold.iloc[0]
    years = len(sim) / 365.0
    return {
        "nav": sim["nav"],
        "cagr": m.cagr(sim["nav"], 365), "sharpe": m.sharpe(sim["nav"].pct_change(), 365),
        "max_dd": m.max_drawdown(sim["nav"]), "turnover": sim["turnover"].sum() / years,
        "bh_cagr": m.cagr(hold_nav, 365), "bh_sharpe": m.sharpe(hold_nav.pct_change(), 365),
        "bh_max_dd": m.max_drawdown(hold_nav),
    }


def _sharpe_from_field(field: str) -> float | None:
    """Read a Sharpe ratio from 'CAGR / Sharpe / DD' or 'Sharpe x / ...' cells."""
    parts = [p.strip() for p in field.split("/")]
    if len(parts) == 3 and parts[0].endswith("%"):
        return float(parts[1])
    if field.startswith("Sharpe"):
        return float(parts[0].split()[1])
    return None


def trial_sharpes_per_day() -> list[float]:
    """Annual full-period Sharpe ratios of the logged trials, in daily units."""
    out = []
    with EXPERIMENTS.open() as f:
        for row in csv.DictReader(f):
            if row["counts_as_trial"] == "yes" and row["family"] == "crypto_trend":
                sr = _sharpe_from_field(row["full_2015_2026"])
                if sr is not None:
                    out.append(sr / np.sqrt(365.0))
    if len(out) < 2:
        raise ValueError("fewer than 2 logged trial Sharpe ratios")
    return out


def eur_nav(nav_usd: pd.Series, eurusd_daily: pd.Series) -> pd.Series:
    """Value of a USD-denominated NAV for a euro investor (USD per EUR rate)."""
    fx = eurusd_daily.reindex(pd.date_range(eurusd_daily.index.min(), nav_usd.index.max(), freq="D")).ffill()
    fx = fx.reindex(nav_usd.index)
    return nav_usd * (fx.iloc[0] / fx)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cached", action="store_true")
    args = parser.parse_args()
    refresh = not args.cached

    rule = rules.FrozenRule.load()
    cost = rule.maker_fee + rule.spread
    btc = completed_days(catalog.load("btcusd_daily", refresh=refresh))["close"]
    btc = btc[(btc.index >= "2013-01-01") & (btc.index <= END)]
    exp = rules.primary_exposure(btc, rule)
    c1 = rules.c1_sma200_exposure(btc)

    res = {w: window_stats(btc, exp, cost, s, e) for w, (s, e) in WINDOWS.items()}
    res2x = window_stats(btc, exp, 2 * cost, *WINDOWS["Full 2015 - Nov 2024"])
    c1_full = window_stats(btc, c1, cost, *WINDOWS["Full 2015 - Nov 2024"])

    # A. drawdown halving
    a_pass = all(res[w]["max_dd"] > 0.5 * res[w]["bh_max_dd"] for w in GATED_WINDOWS)
    # B. deflated Sharpe
    full_rets = res["Full 2015 - Nov 2024"]["nav"].pct_change().dropna()
    trials = trial_sharpes_per_day()
    dsr = m.deflated_sharpe(full_rets, trials, N_TRIALS)
    b_pass = dsr >= 0.95
    # C. 2x costs
    c_pass = res2x["max_dd"] > 0.5 * res2x["bh_max_dd"] and res2x["sharpe"] >= res2x["bh_sharpe"]

    # reported: ETH, EUR drawdown
    eth = completed_days(catalog.load("ethusd_daily", refresh=refresh))["close"]
    eth = eth[eth.index <= END]
    eth_exp = rules.primary_exposure(eth, rule)
    eth_first = eth_exp.dropna().index[0]
    eth_stats = window_stats(eth, eth_exp, cost, str(eth_first.date()), END)
    fx = catalog.load("eurusd_daily", refresh=refresh)
    nav_eur = eur_nav(res["Full 2015 - Nov 2024"]["nav"], fx)
    eur_dd = m.max_drawdown(nav_eur.dropna())

    verdict = "PASS" if (a_pass and b_pass and c_pass) else "FAIL"
    lines = [
        "# Gate CG1: frozen crypto rule, backtest before the hold-out",
        "",
        f"Run {date.today():%Y-%m-%d}. Rule `{rule.name}` (frozen_rules.json, revision 2). BTC/USD Bitstamp daily "
        f"closes to {END}. Cost {cost:.2%} per unit traded (2× test: {2 * cost:.2%}). Cash 0%, no contributions, "
        "no tax. Criteria are in `scripts/crypto_cg1.py`, fixed before the first run.",
        "",
        f"**Verdict: {verdict}.** A (drawdown halving): {'pass' if a_pass else 'fail'}; "
        f"B (deflated Sharpe {dsr:.3f}, N = {N_TRIALS}): {'pass' if b_pass else 'fail'}; "
        f"C (2× costs): {'pass' if c_pass else 'fail'}.",
        "",
        "| Window | Strategy CAGR / Sharpe / max DD | Buy-and-hold CAGR / Sharpe / max DD | DD ratio | Turnover/yr |",
        "|---|---|---|---|---|",
    ]
    for w, r in res.items():
        lines.append(f"| {w} | {r['cagr']:.1%} / {r['sharpe']:.2f} / {r['max_dd']:.1%} | "
                     f"{r['bh_cagr']:.1%} / {r['bh_sharpe']:.2f} / {r['bh_max_dd']:.1%} | "
                     f"{r['max_dd'] / r['bh_max_dd']:.2f} | {r['turnover']:.1f} |")
    lines += [
        "",
        f"- **2× costs (full period):** {res2x['cagr']:.1%} / {res2x['sharpe']:.2f} / {res2x['max_dd']:.1%}, "
        f"against buy-and-hold Sharpe {res2x['bh_sharpe']:.2f}.",
        f"- **C1 benchmark, 200-day (full period):** {c1_full['cagr']:.1%} / {c1_full['sharpe']:.2f} / "
        f"{c1_full['max_dd']:.1%}, turnover {c1_full['turnover']:.1f}/yr.",
        f"- **Same rule on ETH/USD** ({eth_first:%Y-%m} → {END}): {eth_stats['cagr']:.1%} / "
        f"{eth_stats['sharpe']:.2f} / {eth_stats['max_dd']:.1%}, against buy-and-hold "
        f"{eth_stats['bh_cagr']:.1%} / {eth_stats['bh_sharpe']:.2f} / {eth_stats['bh_max_dd']:.1%}.",
        f"- **Max drawdown in EUR** (USDC leg converted at FRED EUR/USD): {eur_dd:.1%}, against the −30% pain limit.",
        "",
        "In-sample for the literature (2015–2023) and already partly seen by the research replication; the "
        "forward record from 26 Nov 2026 is the true out-of-sample test.",
    ]
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text("\n".join(lines) + "\n")

    full = res["Full 2015 - Nov 2024"]
    with EXPERIMENTS.open("a", newline="") as f:
        csv.writer(f).writerow([
            f"cg1-{date.today():%Y%m%d}", f"{date.today():%Y-%m-%d}", "crypto_trend", "tsmom_ensemble_x_vol25 (frozen rev 2)",
            "BTC/USD", "registered", "scripts/crypto_cg1.py", f"{cost:.2%}",
            f"{res['W1 2015-2020']['cagr']:.1%} / {res['W1 2015-2020']['sharpe']:.2f} / {res['W1 2015-2020']['max_dd']:.1%}",
            f"{res['W2 2021-2023']['cagr']:.1%} / {res['W2 2021-2023']['sharpe']:.2f} / {res['W2 2021-2023']['max_dd']:.1%}",
            "", f"to Nov 2024: {full['cagr']:.1%} / {full['sharpe']:.2f} / {full['max_dd']:.1%}",
            f"{full['turnover']:.1f}", "no", N_TRIALS, "no", f"CG1 {verdict}; DSR {dsr:.3f}",
        ])

    print("\n".join(lines))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
