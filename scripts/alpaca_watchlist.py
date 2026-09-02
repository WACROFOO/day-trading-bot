#!/usr/bin/env python3
"""Today's momentum candidates, scanned from Alpaca — free, no extra packages.

    python scripts/alpaca_watchlist.py              # top 8
    python scripts/alpaca_watchlist.py --top 12 --max-price 20

Two passes, so the whole US market fits inside the free rate limit:

  pass 1  one snapshot request per 100 symbols gives price, today's volume and
          the previous close for every tradable US equity — enough to apply the
          price and gain pillars to roughly 11,000 names in about a minute;
  pass 2  daily history is fetched only for the few hundred survivors, and
          relative volume is computed from it.

Relative volume compares today's IEX volume with the average of prior days'
IEX volume — same venue on both sides, so the ratio holds even though neither
number is the consolidated one.

Float and catalyst stay manual. Alpaca does not publish float, and a headline
needs reading.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from momentum_platform.scanners.five_pillars import PRICE_MIN  # noqa: E402
from momentum_platform.datasources.alpaca_source import (
    scan_market,  # noqa: E402
    AlpacaError, client_from_env, momentum_universe,
)

UTC = timezone.utc
ET = ZoneInfo("America/New_York")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Scan today's market through Alpaca")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--min-price", type=float, default=PRICE_MIN)
    ap.add_argument("--max-price", type=float, default=20.0)
    ap.add_argument("--min-gain", type=float, default=10.0, help="percent vs previous close")
    ap.add_argument("--min-rvol", type=float, default=5.0)
    ap.add_argument("--min-volume", type=float, default=100_000,
                    help="IEX shares today; lower than a consolidated threshold on purpose")
    ap.add_argument("--limit-universe", type=int, default=0, help="scan only the first N (testing)")
    ap.add_argument("--save", metavar="PATH")
    args = ap.parse_args(argv)

    try:
        client = client_from_env()
    except AlpacaError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    log = lambda msg: print(msg, file=sys.stderr)
    try:
        log("fetching the tradable universe…")
        log("pass 1 — price and gain across the whole universe…")
        result = scan_market(client, min_price=args.min_price, max_price=args.max_price,
                             min_gain=args.min_gain, min_rvol=args.min_rvol,
                             min_volume=args.min_volume, top=0,
                             limit_universe=args.limit_universe, log=log)
    except AlpacaError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 2
    if result["stale"]:
        log("")
        log(f"  NOTE: these are the {result['session_date']} session's moves, not today's.")
        log(f"  Alpaca's daily bar is the last COMPLETED session, and today "
            f"({result['today']}) has not")
        log("  produced one yet. Re-run after 09:30 ET for today's move.")
    rows = result["rows"]
    if not rows:
        log("\nNothing qualifies right now. That is a normal answer — "
            "do not widen the filter to manufacture a candidate.")
        return 1

    top = rows[: args.top]
    log(f"\n  {'SYM':<6} {'PRICE':>8} {'GAIN':>8} {'RVOL':>7} {'VOLUME(IEX)':>12}")
    for r in top:
        log(f"  {r['symbol']:<6} {r['price']:>8.2f} {r['gain']:>7.1f}% "
            f"{r['rvol']:>6.1f}x {int(r['volume']):>12,}")
    log("\n  Float and catalyst are still yours to verify — the workstation shows "
        "both as explicit columns.\n")

    line = ",".join(r["symbol"] for r in top)
    if args.save:
        Path(args.save).write_text(line + "\n")
        log(f"saved to {args.save}")
    print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
