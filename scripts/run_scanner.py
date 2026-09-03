"""CLI for the NASDAQ universe scanner (strategy §1).

Usage:
    python scripts/run_scanner.py [--limit N] [--no-etf] [--fetch-float]

Saves results to results/scanner_YYYY-MM-DD_HHMM.csv.
Note: free yfinance data is ~15 minutes delayed and a full scan of the
~3,300-symbol NASDAQ universe takes several minutes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paper_trading import scanner  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"


def main() -> int:
    parser = argparse.ArgumentParser(description="NASDAQ universe scanner (strategy §1)")
    parser.add_argument("--limit", type=int, default=None,
                        help="scan only the first N symbols (quick test)")
    parser.add_argument("--no-etf", action="store_true",
                        help="exclude ETFs from the universe")
    parser.add_argument("--fetch-float", action="store_true",
                        help="query floatShares for passers (slow — one call per passer)")
    parser.add_argument("--chunk-size", type=int, default=scanner.CHUNK_SIZE,
                        help=f"symbols per download batch (default {scanner.CHUNK_SIZE}); "
                             "lower it if downloads fail")
    parser.add_argument("--no-retry", action="store_true",
                        help="skip the retry pass over symbols that returned no data")
    args = parser.parse_args()

    print("Fetching NASDAQ symbol directory...")
    try:
        universe = scanner.fetch_nasdaq_universe(include_etf=not args.no_etf)
    except scanner.NetworkError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    symbols = universe["symbol"].tolist()
    if args.limit:
        symbols = symbols[:args.limit]
    print(f"Scanning {len(symbols)} symbols "
          f"(filter: ${scanner.PRICE_MIN:.2f}-${scanner.PRICE_MAX:.2f}, "
          f"gain >= {scanner.GAIN_PCT_MIN:.0f}%, rvol >= {scanner.RVOL_MIN:.1f}x, "
          f"vol >= {scanner.VOLUME_MIN:,})...")

    def progress(done: int, total: int, message: str) -> None:
        print(f"\r  {message}   ", end="", flush=True)

    results = scanner.scan(symbols=symbols, fetch_float=args.fetch_float,
                           chunk_size=args.chunk_size,
                           retry_missing=not args.no_retry,
                           progress_cb=progress)
    print()

    coverage = results.attrs.get("coverage")
    if coverage and coverage.is_degraded:
        print(f"\nWARNING: incomplete scan — {coverage.summary()}.")
        print("These results are NOT a watchlist: most of the universe never "
              "returned data, so passers cannot be distinguished from a quiet "
              "market. Fix the downloads and re-run before trading off this.")
        print("Common causes: missing CA certificates, a low open-file limit "
              "(try `ulimit -n 4096`), or too much concurrency "
              "(try --chunk-size 20).\n")
    elif coverage:
        print(f"Coverage: {coverage.summary()}.")

    if results.empty:
        print("No symbols passed the universe filter.")
    else:
        cols = ["symbol", "price", "change_pct", "volume", "rvol",
                "avg_volume_50d", "float_shares", "catalyst"]
        print(results[cols].to_string(index=False))
        print(f"\n{len(results)} symbol(s) passed. "
              "float_shares / catalyst are manual checks (see README).")

    out = scanner.results_path(RESULTS_DIR)
    results.to_csv(out, index=False)
    print(f"Saved: {out}")
    return 2 if coverage and coverage.is_degraded else 0


if __name__ == "__main__":
    raise SystemExit(main())
