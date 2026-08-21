"""Pull every 1-minute candle the free feed still has for a symbol.

Usage:
    python scripts/fetch_1m_history.py SDOT --today
    python scripts/fetch_1m_history.py SDOT --date 2026-08-20
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
import datetime as dt
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paper_trading import history  # noqa: E402

HISTORY_DIR = ROOT / "data" / "history"


def print_bars(bars: pd.DataFrame, tail: int) -> None:
    shown = bars.tail(tail) if tail else bars
    frame = shown.copy()
    frame.index = frame.index.strftime("%H:%M")
    frame.index.name = "time_ET"
    frame["Volume"] = frame["Volume"].astype("int64")
    with pd.option_context("display.max_rows", None, "display.width", 200,
                           "display.float_format", lambda v: f"{v:.4f}"):
        print(frame.to_string())
    if tail and len(bars) > tail:
        print(f"({len(bars) - tail:,} earlier bars not shown — drop --tail for all)")


def print_anatomy(a: dict) -> None:
    if not a:
        return
    def money(v):
        return f"${v:,.4f}"
    print(f"  bars           {a['bars']:,}  "
          f"({a['premarket_bars']:,} premarket + {a['regular_bars']:,} regular)")
    print(f"  span           {a['first_bar']:%H:%M} -> {a['last_bar']:%H:%M} ET")
    if "premarket_high" in a:
        print(f"  premarket      high {money(a['premarket_high'])}  "
              f"low {money(a['premarket_low'])}  vol {a['premarket_volume']:,.0f}")
    if "open" in a:
        print(f"  open (09:30)   {money(a['open'])}   "
              f"regular vol {a['regular_volume']:,.0f}")
    print(f"  high / low     {money(a['high'])} at {a['high_at']:%H:%M}   "
          f"{money(a['low'])} at {a['low_at']:%H:%M}")
    print(f"  last           {money(a['last_price'])} at {a['last_bar']:%H:%M} ET")
    print(f"  total volume   {a['volume']:,.0f}")
    if "broke_premarket_high" in a:
        verdict = "yes" if a["broke_premarket_high"] else "no"
        print(f"  broke premarket high: {verdict}")


def run_single_day(args, symbol: str, path: Path, archive: pd.DataFrame) -> int:
    """One session, every bar — premarket included unless --no-prepost."""
    try:
        day = (dt.date.fromisoformat(args.date) if args.date
               else history.market_today())
    except ValueError:
        print(f"ERROR: --date must be YYYY-MM-DD, got {args.date!r}", file=sys.stderr)
        return 1

    label = "today" if day == history.market_today() else str(day)
    scope = "premarket included" if not args.no_prepost else "regular session only"
    print(f"Fetching {symbol} 1m bars for {label} ({day}, {scope})...")
    try:
        bars = history.fetch_day(symbol, day, prepost=not args.no_prepost)
    except history.NetworkError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if bars.empty:
        print(f"No 1m bars for {symbol} on {day}. Market holiday or weekend, a "
              "halted/delisted symbol, or the session has not printed yet.")
        return 1

    merged = history.merge(archive, bars)
    history.save_archive(merged, path)

    print(f"\n{symbol} — 1-minute candles, {day} ({history.MARKET_TZ}):")
    print_bars(bars, args.tail)
    print(f"\nSession so far:")
    print_anatomy(history.day_anatomy(bars))
    if args.gaps:
        gaps = history.missing_regular_minutes(bars)
        if not gaps.empty:
            print(f"  regular minutes with no print: "
                  f"{int(gaps['missing_minutes'].iloc[0]):,} "
                  "(gaps inside the traded span — normal on a thin tape)")
    print(f"\nArchive: {path} ({len(merged):,} bars total)")
    return 0


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
    p.add_argument("--today", action="store_true",
                   help="today's session only (04:00 ET -> now), every bar printed")
    p.add_argument("--date", type=str, default=None, metavar="YYYY-MM-DD",
                   help="one specific session, every bar printed")
    p.add_argument("--tail", type=int, default=0, metavar="N",
                   help="with --today/--date, print only the last N bars")
    args = p.parse_args()

    symbol = args.symbol.upper()
    path = history.archive_path(args.out, symbol)
    archive = history.load_archive(path)

    if args.today or args.date:
        return run_single_day(args, symbol, path, archive)

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
