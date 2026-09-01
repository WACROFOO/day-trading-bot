#!/usr/bin/env python3
"""Score the catalyst behind a symbol. Selection only — never an order.

    python scripts/catalyst_score.py TSLA AAPL
    python scripts/catalyst_score.py --scan            # today's movers
    python scripts/catalyst_score.py ABCD --days 30    # widen the filing window

For each symbol it answers three questions:

    1. Is there news, and how old is it?   -> flame (Confirmed: age only)
    2. What kind of news is it?            -> hard / soft / dilutive
    3. Is the company selling shares?      -> SEC filings

The third is the one a headline alone will never tell you. A fresh, exciting
headline sitting on top of a live 424B takedown means the float is growing
while you hold it — the desk calls that AVOID, no matter how red the flame.

News comes from Alpaca (free tier). Filings come from SEC EDGAR (free, no
account). Either source can be missing; the output says which, and missing
data is never reported as a clean result.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from momentum_platform.catalyst import (  # noqa: E402
    FLAME_BAND, VERDICT_MEANING, assess,
)
from momentum_platform.datasources.alpaca_source import (  # noqa: E402
    AlpacaError, client_from_env as alpaca_from_env,
)
from momentum_platform.datasources.sec_source import (  # noqa: E402
    SecError, client_from_env as sec_from_env,
)

G, Y, R, D, B, O = "\033[92m", "\033[93m", "\033[91m", "\033[2m", "\033[1m", "\033[0m"
FLAME_PAINT = {"red": R, "orange": Y, "yellow": Y, "none": D}
VERDICT_PAINT = {"QUALIFIED": G, "WATCH": Y, "CAUTION": Y, "AVOID": R,
                 "PASS": D, "UNKNOWN": Y}


def latest_news(client, symbol: str, lookback_hours: int) -> tuple:
    """Newest headline for a symbol, or (None, None, '')."""
    start = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours))
    items = client.news([symbol], start=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        limit=50) or []
    if not items:
        return None, None, ""
    newest = max(items, key=lambda n: n.get("created_at") or "")
    ts = newest.get("created_at")
    when = None
    if ts:
        try:
            when = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except ValueError:
            when = None
    return newest.get("headline"), when, " ".join(newest.get("symbols") or [])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Grade the catalyst behind one or more symbols (selection only)")
    ap.add_argument("symbols", nargs="*", help="tickers, e.g. TSLA AAPL")
    ap.add_argument("--scan", action="store_true",
                    help="score whatever passed the pillars today")
    ap.add_argument("--days", type=int, default=90,
                    help="filing lookback window in days (default 90)")
    ap.add_argument("--news-hours", type=int, default=48,
                    help="news lookback window in hours (default 48)")
    ap.add_argument("--no-filings", action="store_true",
                    help="skip SEC entirely (news grading only)")
    args = ap.parse_args(argv)

    symbols = [s.strip().upper() for s in args.symbols if s.strip()]
    if args.scan and not symbols:
        print(f"{D}--scan reads the watchlist. Run this first:{O}\n"
              f"    python scripts/alpaca_watchlist.py --top 8\n"
              f"{D}then pass the symbols it prints on the last line:{O}\n"
              f"    python scripts/catalyst_score.py $(python scripts/alpaca_watchlist.py --top 8 | tail -1 | tr ',' ' ')\n")
        return 2
    if not symbols:
        ap.error("give at least one symbol, e.g. python scripts/catalyst_score.py TSLA")

    print(f"\n{B}Catalyst read{O}  {D}selection only — this places no orders "
          f"and sizes nothing{O}\n")

    alpaca = None
    try:
        alpaca = alpaca_from_env()
    except AlpacaError as exc:
        print(f"  {Y}news unavailable{O}  {D}{exc}{O}\n")

    sec = None if args.no_filings else sec_from_env()

    exit_code = 0
    for symbol in symbols:
        headline = when = None
        category = ""
        news_note = ""
        news_checked = alpaca is not None
        if alpaca is not None:
            try:
                headline, when, category = latest_news(alpaca, symbol, args.news_hours)
                if headline is None:
                    news_note = f"no headline in the last {args.news_hours}h"
            except AlpacaError as exc:
                news_note = f"news lookup failed: {exc}"
                news_checked = False
                exit_code = 1

        filings = []
        filings_note = ""
        if sec is not None:
            try:
                filings = sec.recent_filings(symbol, since_days=args.days)
                if not filings:
                    filings_note = ("EDGAR returned nothing — supply risk UNVERIFIED, "
                                    "not clean")
            except SecError as exc:
                filings_note = f"filings lookup failed: {exc}"
                exit_code = 1
        else:
            filings_note = "filings skipped (--no-filings) — supply risk UNVERIFIED"

        read = assess(symbol, headline=headline, published=when,
                      category=category, filings=filings,
                      news_checked=news_checked)
        verdict = read.verdict()

        paint = VERDICT_PAINT.get(verdict, "")
        flame_paint = FLAME_PAINT.get(read.flame_color, D)
        print(f"{B}{symbol:<6}{O} {paint}{verdict:<10}{O} "
              f"{flame_paint}flame {read.flame_color:<6}{O} "
              f"{D}{FLAME_BAND[read.flame_color]}{O}  {read.grade.label}")
        print(f"       {D}{VERDICT_MEANING[verdict]}{O}")
        if headline:
            age = f"{read.age_min/60:.1f}h ago" if read.age_min is not None else "undated"
            print(f"       {headline[:96]}  {D}({age}){O}")
        elif news_note:
            print(f"       {Y}{news_note}{O}")

        if read.dilution_filings:
            for f in read.dilution_filings[:4]:
                print(f"       {R}filing{O} {f['form']:<8} {f['filed']}  "
                      f"{D}{f['age_days']}d ago{O}")
        elif filings:
            forms = ", ".join(sorted({f["form"] for f in filings})[:6])
            print(f"       {D}filings seen, none dilutive: {forms}{O}")
        if filings_note:
            print(f"       {Y}{filings_note}{O}")
        for note in read.notes:
            print(f"       {D}{note}{O}")
        print()

    print(f"{D}The scanner discovers a candidate; the chart defines the setup; "
          f"the stop defines the size.{O}")
    print(f"{D}This tool only does the first half of the first step.{O}\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
