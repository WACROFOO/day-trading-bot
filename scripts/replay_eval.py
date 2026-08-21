"""Blinded walk-forward self-assessment (see REPLAY_EVAL_PROMPT.md).

Usage:
    python scripts/replay_eval.py --symbols SDOT,ABCD --days 5
    python scripts/replay_eval.py --symbols SDOT --date 2026-08-20 --sweep

Writes results/replay_<date>.csv (one row per candle decision) and prints
the confusion matrix, the §9 comparison, the §12 baselines and the
tolerance sweep.

Selection bias warning: symbols passed with --symbols are NOT a
point-in-time scan. If you chose them knowing how the day turned out, the
result is contaminated and the report says so.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paper_trading import history, replay  # noqa: E402

RESULTS_DIR = ROOT / "results"


def trading_days(days: int, end: dt.date) -> list[dt.date]:
    return [d.date() for d in pd.bdate_range(end=end, periods=days)]


def main() -> int:
    p = argparse.ArgumentParser(description="Blinded walk-forward replay")
    p.add_argument("--symbols", required=True, help="comma-separated tickers")
    p.add_argument("--days", type=int, default=5, help="trailing sessions (default 5)")
    p.add_argument("--date", help="single session, YYYY-MM-DD (overrides --days)")
    p.add_argument("--equity", type=float, default=25_000.0)
    p.add_argument("--tolerance", type=float, default=replay.TOLERANCE_PCT)
    p.add_argument("--sweep", action="store_true", help="run the §12.3 tolerance sweep")
    p.add_argument("--out", type=Path, default=RESULTS_DIR)
    args = p.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if args.date:
        days = [dt.date.fromisoformat(args.date)]
    else:
        days = trading_days(args.days, history.market_today())

    print("SELECTION BIAS: --symbols is a manual list, not a point-in-time "
          "09:25 scan. Treat every metric below as contaminated if these "
          "tickers were chosen knowing how the sessions ended.\n")

    logs, fetched, missing = [], [], []
    for symbol in symbols:
        for day in days:
            try:
                bars = history.fetch_day(symbol, day, prepost=True)
            except history.NetworkError as exc:
                print(f"FEED BLOCKED for {symbol} {day}: {exc}", file=sys.stderr)
                print("\nStopping. A blocked feed is a correct failure — "
                      "synthetic bars would invalidate the run.", file=sys.stderr)
                return 1
            if bars.empty:
                missing.append(f"{symbol} {day}")
                continue
            fetched.append(f"{symbol} {day} ({len(bars)} bars)")
            log = replay.replay_session(bars, symbol, equity=args.equity,
                                        tolerance_pct=args.tolerance)
            if not log.empty:
                log.insert(0, "session", str(day))
                logs.append(log)
            print(f"  {symbol} {day}: {len(bars)} bars -> {len(log)} decisions")

    if not logs:
        print("\nNo decisions produced — nothing to score.", file=sys.stderr)
        return 1

    combined = pd.concat(logs, ignore_index=True)
    args.out.mkdir(parents=True, exist_ok=True)
    out_path = args.out / f"replay_{dt.date.today():%Y-%m-%d}.csv"
    combined.to_csv(out_path, index=False)

    s = replay.score(combined)
    print(f"\n{'=' * 62}\nDECISION SCORECARD\n{'=' * 62}")
    print(f"  sessions fetched : {len(fetched)}")
    if missing:
        print(f"  sessions missing : {len(missing)} ({', '.join(missing[:5])})")
    print(f"  decisions        : {s['n_decisions']:,}")
    print(f"  resolved trades  : {s['n_trades']}")
    print(f"\n                 won    lost")
    print(f"  TAKE       {s['true_positive']:6d}  {s['false_positive']:6d}")
    print(f"  SKIP       {s['false_negative']:6d}  {s['true_negative']:6d}")
    print(f"\n  precision  : {s['precision']:.3f}   (of trades taken, share that won)")
    print(f"  recall     : {s['recall']:.3f}   (of winners available, share taken)")
    print(f"  expectancy : {s['expectancy_r']:.3f} R")
    print(f"  net P&L    : ${s['net_pnl']:,.2f}")
    print(f"\n  §9 breakeven win rate at 2:1 = {s['breakeven_win_rate']:.3f}; "
          f"this sample {'CLEARS' if s['clears_breakeven'] else 'does NOT clear'} it")

    if not s["significant"]:
        print(f"\n  ⚠ N = {s['n_trades']} resolved trades (< 20). NOT SIGNIFICANT.\n"
              "    Do not draw a conclusion from this sample. Reporting it as\n"
              "    an edge would itself be an inaccuracy.")

    print(f"\n{'-' * 62}\n§12 BASELINES\n{'-' * 62}")
    for symbol in symbols:
        for day in days[-1:]:
            try:
                bars = history.fetch_day(symbol, day, prepost=True)
            except history.NetworkError:
                continue
            if bars.empty:
                continue
            bh = replay.baseline_buy_hold(bars)
            rnd = replay.baseline_random(bars, n=20, seed=0)
            print(f"  {symbol} {day}: buy-hold {bh['return_pct']:+.2f}% | "
                  f"random n={rnd['n']} expectancy {rnd['expectancy_r']:+.3f}R")

    if args.sweep:
        print(f"\n{'-' * 62}\n§12.3 TOLERANCE SWEEP\n{'-' * 62}")
        for symbol in symbols:
            for day in days[-1:]:
                try:
                    bars = history.fetch_day(symbol, day, prepost=True)
                except history.NetworkError:
                    continue
                if bars.empty:
                    continue
                sw = replay.sweep_tolerance(bars, symbol)
                print(f"\n  {symbol} {day}:")
                print(sw[["tolerance_pct", "n_trades", "win_rate",
                          "expectancy_r"]].to_string(index=False))
                if sw.attrs.get("sign_flips"):
                    print("  ⚠ expectancy changes sign across the sweep — "
                          "per §12.3 DISCARD this finding, do not report the "
                          "best cell.")

    print(f"\nAudit trail: {out_path}")
    print("Untestable inputs carried as UNKNOWN, not assumed true: "
          "tape_green, no_seller_wall (Level 2), float_ok, catalyst_ok.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
