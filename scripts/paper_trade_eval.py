"""Multi-ticker blinded paper trading on one account, with a full report.

Usage:
    # eligible tickers from the §1 scanner (point-in-time as of now)
    python scripts/paper_trade_eval.py --scan --days 5 --equity 100000

    # or an explicit list
    python scripts/paper_trade_eval.py --symbols SDOT,ABCD,WXYZ --days 5

Writes:
    results/performance_<date>.md    the performance / accuracy report
    results/decisions_<date>.csv     every candle decision (audit trail)
    results/trades_<date>.csv        the executed trades

Decisions are made candle by candle with the future hidden (see
knowledge-base/strategies/REPLAY_EVAL_PROMPT.md). A blocked data feed is a
hard stop: synthetic bars would invalidate the whole report.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paper_trading import history, portfolio, replay, report, scanner  # noqa: E402

RESULTS = ROOT / "results"


def eligible_from_scanner(limit: int | None) -> list[str]:
    """§1 universe filter. Point-in-time as of NOW, not as of each session."""
    universe = scanner.fetch_nasdaq_universe(include_etf=False)
    symbols = universe["symbol"].tolist()
    if limit:
        symbols = symbols[:limit]
    hits = scanner.scan(symbols=symbols)
    return [] if hits.empty else hits["symbol"].tolist()


def main() -> int:
    p = argparse.ArgumentParser(description="Multi-ticker blinded paper trading")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--symbols", help="comma-separated tickers")
    src.add_argument("--scan", action="store_true",
                     help="discover eligible tickers with the §1 scanner")
    p.add_argument("--scan-limit", type=int, default=None,
                   help="only scan the first N symbols (quick test)")
    p.add_argument("--days", type=int, default=5, help="trailing sessions")
    p.add_argument("--equity", type=float, default=100_000.0)
    p.add_argument("--max-symbols", type=int, default=15,
                   help="cap how many scanner hits are replayed")
    p.add_argument("--out", type=Path, default=RESULTS)
    args = p.parse_args()

    if args.scan:
        print("Scanning the NASDAQ universe for §1-eligible tickers...")
        try:
            symbols = eligible_from_scanner(args.scan_limit)
        except Exception as exc:                      # noqa: BLE001 - reported
            print(f"FEED BLOCKED during scan: {exc}", file=sys.stderr)
            return 1
        if not symbols:
            print("No symbols passed the §1 filter. Nothing to trade — that is a "
                  "result, not an error (§12.1: if <1/day passes, the strategy is "
                  "untradeable regardless of edge).")
            return 0
        selection_note = (
            f"Tickers came from the §1 scanner run at {dt.datetime.now():%Y-%m-%d %H:%M}. "
            "The scan is point-in-time as of NOW, not as of each replayed session — "
            "a name that passed §1 today may not have passed on an earlier day, so "
            "earlier sessions carry survivorship bias.")
        symbols = symbols[:args.max_symbols]
    else:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
        selection_note = (
            "Tickers were supplied manually with `--symbols`. This is **not** a "
            "point-in-time scan. If they were chosen knowing how the sessions "
            "ended, every metric below is contaminated by selection bias.")

    print(f"Symbols: {', '.join(symbols)}")
    days = [d.date() for d in pd.bdate_range(end=history.market_today(),
                                             periods=args.days)]

    logs, bars_by_key, missing = [], {}, []
    for symbol in symbols:
        for day in days:
            try:
                bars = history.fetch_day(symbol, day, prepost=True)
            except history.NetworkError as exc:
                print(f"\nFEED BLOCKED for {symbol} {day}: {exc}", file=sys.stderr)
                print("Stopping. Synthetic bars would invalidate the report.",
                      file=sys.stderr)
                return 1
            if bars.empty:
                missing.append(f"{symbol} {day}")
                continue
            bars_by_key[(symbol, str(day))] = bars
            log = replay.replay_session(bars, symbol, equity=args.equity)
            if not log.empty:
                log.insert(0, "session", str(day))
                logs.append(log)
            print(f"  {symbol} {day}: {len(bars)} bars -> {len(log)} decisions")

    if not logs:
        print("\nNo decisions produced — nothing to report.", file=sys.stderr)
        return 1

    combined = pd.concat(logs, ignore_index=True)
    cfg = portfolio.Config(starting_equity=args.equity)
    sim = portfolio.simulate(combined, bars_by_key, cfg)

    data_note = (
        f"{selection_note}\n\n"
        f"Bars are 1-minute OHLCV from the free Yahoo feed via "
        f"`paper_trading.history.fetch_day`, premarket included, covering "
        f"{len(days)} session(s) from {days[0]} to {days[-1]}. That feed is "
        f"~15 minutes delayed and retains only ~30 days of 1-minute history, "
        f"which is the hard ceiling on sample size here. "
        + (f"{len(missing)} symbol-session(s) returned no data and were dropped."
           if missing else "Every requested symbol-session returned data."))

    args.out.mkdir(parents=True, exist_ok=True)
    today = dt.date.today()
    md = report.build(combined, sim, symbols=symbols, sessions=[str(d) for d in days],
                      data_note=data_note)
    report_path = args.out / f"performance_{today:%Y-%m-%d}.md"
    report_path.write_text(md)
    combined.to_csv(args.out / f"decisions_{today:%Y-%m-%d}.csv", index=False)
    if not sim["trades"].empty:
        sim["trades"].to_csv(args.out / f"trades_{today:%Y-%m-%d}.csv", index=False)

    print(f"\n{'=' * 60}")
    print(f"  starting equity : ${cfg.starting_equity:,.2f}")
    print(f"  final equity    : ${sim['final_equity']:,.2f} "
          f"({sim['return_pct']:+.2f}%)")
    print(f"  trades          : {len(sim['trades'])}")
    print(f"  blocked signals : {len(sim['blocked'])}")
    print(f"  decisions       : {len(combined):,}")
    print(f"{'=' * 60}")
    print(f"\nReport: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
