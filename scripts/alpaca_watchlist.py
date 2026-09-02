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

from momentum_platform.datasources.alpaca_source import (  # noqa: E402
    AlpacaError, client_from_env, momentum_universe,
)

UTC = timezone.utc
ET = ZoneInfo("America/New_York")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Scan today's market through Alpaca")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--min-price", type=float, default=2.0)
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
        universe = momentum_universe(client, max_symbols=args.limit_universe)
        log(f"  {len(universe):,} tradable US equities")

        log("pass 1 — price and gain across the whole universe…")
        survivors = []
        snaps = client.snapshots(universe)
        # Which session do these numbers describe? Alpaca's dailyBar is the most
        # recent COMPLETED daily bar, so before the open it is yesterday's. The
        # scan must say so: printing a completed session's move under the
        # heading "today's movers" invites acting on a move that already ended.
        bar_dates: dict = {}
        for symbol, snap in snaps.items():
            if not snap:
                continue
            day = snap.get("dailyBar") or {}
            prev = snap.get("prevDailyBar") or {}
            stamp = str(day.get("t") or "")[:10]
            if stamp:
                bar_dates[stamp] = bar_dates.get(stamp, 0) + 1
            last = (snap.get("latestTrade") or {}).get("p") or day.get("c")
            prev_close, volume = prev.get("c"), day.get("v") or 0
            if not last or not prev_close or prev_close <= 0:
                continue
            gain = (last / prev_close - 1) * 100
            if (args.min_price <= last <= args.max_price
                    and gain >= args.min_gain and volume >= args.min_volume):
                survivors.append({"symbol": symbol, "price": last, "gain": gain,
                                  "volume": volume})
        log(f"  {len(survivors)} passed price, gain and volume")
        session_date = max(bar_dates, key=bar_dates.get) if bar_dates else ""
        today_et = datetime.now(ET).date().isoformat()
        if session_date and session_date != today_et:
            log("")
            log(f"  NOTE: these are the {session_date} session's moves, not today's.")
            log(f"  Alpaca's daily bar is the last COMPLETED session, and today "
                f"({today_et}) has not")
            log("  produced one yet. Re-run after 09:30 ET for today's move.")
        if not survivors:
            log("\nNothing qualifies right now. That is a normal answer — "
                "do not widen the filter to manufacture a candidate.")
            return 1

        log("pass 2 — relative volume for the survivors…")
        symbols = [s["symbol"] for s in survivors]
        start = (datetime.now(UTC) - timedelta(days=40)).isoformat(
            timespec="seconds").replace("+00:00", "Z")
        daily = client.bars(symbols, "1Day", start)
        rows = []
        for item in survivors:
            history = [b for b in daily.get(item["symbol"], []) if (b.get("v") or 0) > 0]
            prior = [b["v"] for b in history[-21:-1]]
            if len(prior) < 5:
                continue
            avg = sum(prior) / len(prior)
            item["rvol"] = item["volume"] / avg if avg else 0
            if item["rvol"] >= args.min_rvol:
                rows.append(item)
        rows.sort(key=lambda r: r["rvol"], reverse=True)
        log(f"  {len(rows)} also passed relative volume ≥ {args.min_rvol}x")
    except AlpacaError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 2

    if not rows:
        log("\nNo candidate cleared all four computable pillars today.")
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
