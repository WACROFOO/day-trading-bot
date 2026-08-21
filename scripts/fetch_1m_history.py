"""Pull every 1-minute candle the free feed still has for a symbol.

Usage:
    python scripts/fetch_1m_history.py SDOT
    python scripts/fetch_1m_history.py SDOT --days 7 --no-prepost
    python scripts/fetch_1m_history.py SDOT --summary-only

Yahoo keeps ~30 calendar days of 1-minute bars and caps one request at 8
days, so this walks the window in 7-day chunks and merges the result into
data/history/<SYMBOL>_1m.csv. The archive is additive: run it weekly and
it accumulates history past the 30-day window. Bars older than your first
run cannot be recovered from this feed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paper_trading import history  # noqa: E402

HISTORY_DIR = ROOT / "data" / "history"


def main() -> int:
    p = argparse.ArgumentParser(description="Fetch 1-minute candle history")
    p.add_argument("symbol", nargs="?", default="SDOT", help="ticker (default: SDOT)")
    p.add_argument("--days", type=int, default=history.MAX_LOOKBACK_DAYS,
                   help=f"lookback in calendar days (max {history.MAX_LOOKBACK_DAYS})")
    p.add_argument("--no-prepost", action="store_true",
                   help="regular session only (default includes pre/post market)")
    p.add_argument("--out", type=Path, default=HISTORY_DIR,
                   help="archive directory (default: data/history/)")
    p.add_argument("--summary-only", action="store_true",
                   help="re-print the summary of the existing archive, fetch nothing")
    p.add_argument("--gaps", action="store_true",
                   help="also report missing regular-session minutes per day")
    args = p.parse_args()

    symbol = args.symbol.upper()
    path = history.archive_path(args.out, symbol)
    archive = history.load_archive(path)

    if args.summary_only:
        if archive.empty:
            print(f"No archive at {path} — run without --summary-only first.")
            return 1
        bars = archive
    else:
        if args.days > history.MAX_LOOKBACK_DAYS:
            print(f"note: clipping --days {args.days} to the feed's "
                  f"{history.MAX_LOOKBACK_DAYS}-day 1m retention window")

        def progress(done: int, total: int, message: str) -> None:
            print(f"  [{done}/{total}] {message}", flush=True)

        print(f"Fetching 1m bars for {symbol} "
              f"({'incl.' if not args.no_prepost else 'excl.'} pre/post market)...")
        try:
            fresh = history.fetch_1m(symbol, days=args.days,
                                     prepost=not args.no_prepost,
                                     progress_cb=progress)
        except history.NetworkError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

        if fresh.empty and archive.empty:
            print(f"No 1m data returned for {symbol}. Check the ticker — a "
                  "delisted or renamed symbol returns an empty frame.")
            return 1

        before = len(archive)
        bars = history.merge(archive, fresh)
        history.save_archive(bars, path)
        print(f"\nFetched {len(fresh):,} bars, {len(bars) - before:,} new. "
              f"Archive: {path} ({len(bars):,} bars)")

    summary = history.session_summary(bars)
    if args.gaps:
        summary = summary.merge(history.missing_regular_minutes(bars),
                                on="date", how="left")

    with pd.option_context("display.max_rows", None, "display.width", 200):
        print(f"\n{symbol} — 1-minute candles by session "
              f"({history.MARKET_TZ}):")
        print(summary.to_string(index=False))

    print(f"\nTotal: {len(bars):,} 1m bars across {len(summary)} session(s), "
          f"{bars.index.min():%Y-%m-%d %H:%M} -> {bars.index.max():%Y-%m-%d %H:%M} ET")
    print("Last 5 bars:")
    print(bars.tail(5).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
