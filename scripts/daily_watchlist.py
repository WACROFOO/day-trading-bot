#!/usr/bin/env python3
"""Build today's candidate watchlist, then hand it to the workstation.

Runs the NASDAQ universe scan (price $2-$20, gain >= 10%, RVOL >= 5x,
volume >= 500k — the Confirmed course pillars that are computable from free
data) and prints the survivors as a comma-separated list ready to paste into
the dashboard's --live flag.

    python scripts/daily_watchlist.py --top 8
    PYTHONPATH=src python -m momentum_platform.dashboard.server --live ABCD,BRXO,...

Float and catalyst stay manual checks: free float data is unreliable and a
headline needs reading, not pattern-matching. The workstation shows both as
explicit columns so a missing value never passes silently.

Data is delayed roughly 15 minutes. That is fine for building a list and for
paper trading; it is not an execution feed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Today's momentum candidates")
    ap.add_argument("--top", type=int, default=8, help="how many symbols to keep")
    ap.add_argument("--limit", type=int, default=None,
                    help="only scan the first N symbols (quick test)")
    ap.add_argument("--include-etf", action="store_true")
    ap.add_argument("--save", metavar="PATH", help="also write the symbol list to a file")
    args = ap.parse_args(argv)

    try:
        from paper_trading import scanner
    except ImportError as exc:                     # pandas / yfinance missing
        print(f"scanner unavailable: {exc}\nInstall requirements first: "
              f"pip install -r requirements.txt", file=sys.stderr)
        return 2

    print("scanning the NASDAQ universe (several minutes on a full run)…", file=sys.stderr)
    universe = scanner.fetch_nasdaq_universe(include_etf=args.include_etf)
    symbols = list(universe["symbol"])
    if args.limit:
        symbols = symbols[: args.limit]

    results = scanner.scan(symbols)
    if results.empty:
        print("no symbol passed today's filters — a flat morning is a real answer",
              file=sys.stderr)
        return 1

    top = results.head(args.top)
    print(f"\n{len(results)} passed, showing top {len(top)} by relative volume:\n",
          file=sys.stderr)
    for _, row in top.iterrows():
        print(f"  {row['symbol']:<6} ${row['price']:>7.2f}  {row['change_pct']:>6.1f}%  "
              f"RVOL {row['rvol']:>5.1f}x  vol {int(row['volume']):>10,}", file=sys.stderr)
    print("\n  float and catalyst are still yours to verify.\n", file=sys.stderr)

    line = ",".join(top["symbol"])
    if args.save:
        Path(args.save).write_text(line + "\n")
        print(f"saved to {args.save}", file=sys.stderr)
    print(line)                                    # stdout: pipeable
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
