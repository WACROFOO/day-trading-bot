#!/usr/bin/env python3
"""Score the catalyst behind a symbol. Selection only — never an order.

    python scripts/catalyst_score.py TSLA AAPL
    python scripts/catalyst_score.py --scan            # today's movers
    python scripts/catalyst_score.py ABCD --days 30    # widen the filing window

For each symbol it prints the desk card's own catalyst read
(`momentum_platform.catalyst.card_read`, rules in
knowledge-base/strategies/CATALYST.md), so the terminal and the desk never
grade the same headlines differently:

    STRONG / MODERATE / WEAK   the grade, its one-line reason and rule id
    type · age · source        FDA, earnings, contract… · today 07:02 pre-market
    the headline, two lines
    flags                      offering in today's news, a 424B in the last 30
                               days, a shelf on file, a foreign filer (rule 7)

A fresh headline on top of a recent 424B takedown means the float is growing
while you hold it; the flag says so in red whatever the grade. (Until
2026-10-08 any 424B inside the 90-day window read AVOID, however old.)

News comes from Alpaca (free tier). Filings come from SEC EDGAR (free, no
account). Either source can be missing; the output says which, and missing
data is never reported as a clean result.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from momentum_platform.catalyst import card_read  # noqa: E402
from momentum_platform.datasources.alpaca_source import (  # noqa: E402
    AlpacaError, client_from_env as alpaca_from_env,
)
from momentum_platform.datasources.sec_source import (  # noqa: E402
    SecError, client_from_env as sec_from_env,
)

G, Y, R, D, B, O = "\033[92m", "\033[93m", "\033[91m", "\033[2m", "\033[1m", "\033[0m"
GRADE_PAINT = {"STRONG": G, "MODERATE": Y, "WEAK": R, "UNKNOWN": Y}
FLAG_PAINT = {"bad": R, "warn": Y, "ok": G, "info": D}


def symbols_from_watchlist(stdout: str) -> list:
    """Pull the ticker list off the watchlist's last line.

    The script prints a human-readable table and finishes with a bare
    comma-separated list. A run with no survivors ends on prose instead, so
    reject anything that does not look like tickers rather than turning a
    sentence into symbols.
    """
    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    if not lines:
        return []
    parts = [p.strip().upper() for p in lines[-1].split(",") if p.strip()]
    if not parts or any(" " in p or not p.isalnum() or len(p) > 6 for p in parts):
        return []
    return parts


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


def news_items(client, symbol: str, lookback_hours: int) -> list:
    """Every headline for `symbol` in the window, in the desk's record shape —
    so `card_read` grades them exactly as the desk card does."""
    from momentum_platform.dashboard.session_builder import shared_tag
    start = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours))
    items = client.news([symbol], start=start.strftime("%Y-%m-%dT%H:%M:%SZ"), limit=50) or []
    out = []
    for n in items:
        ts, head = n.get("created_at"), n.get("headline") or ""
        if not ts or not head:
            continue
        tags = list(n.get("symbols") or [symbol])
        out.append({"headline": head, "publishedAt": ts, "firstObservedAt": ts, "category": "",
                    "tagged": tags, "sharedTag": shared_tag(head, symbol, tags), "url": n.get("url")})
    return out


def _wrap(text: str, width: int = 92, lines: int = 2) -> list:
    words, out, cur = (text or "").split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            out.append(cur); cur = w
            if len(out) == lines:
                break
        else:
            cur = (cur + " " + w).strip()
    if len(out) < lines and cur:
        out.append(cur)
    if len(out) == lines and len(" ".join(out)) < len(text or ""):
        out[-1] = out[-1][: width - 1] + "…"
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Grade the catalyst behind one or more symbols (selection only)")
    ap.add_argument("symbols", nargs="*", help="tickers, e.g. TSLA AAPL")
    ap.add_argument("--scan", action="store_true",
                    help="scan the market first, then score what it finds")
    ap.add_argument("--top", type=int, default=8,
                    help="how many movers --scan should keep (default 8)")
    ap.add_argument("--days", type=int, default=90,
                    help="filing lookback window in days (default 90)")
    ap.add_argument("--news-hours", type=int, default=48,
                    help="news lookback window in hours (default 48)")
    ap.add_argument("--no-filings", action="store_true",
                    help="skip SEC entirely (news grading only)")
    args = ap.parse_args(argv)

    symbols = [s.strip().upper() for s in args.symbols if s.strip()]
    if args.scan and not symbols:
        # Run the watchlist ourselves rather than telling the user to copy
        # symbols between two commands. Its last line is the comma-separated
        # list; everything above it is the human-readable table.
        print(f"{D}scanning the market for today's movers…{O}")
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("alpaca_watchlist.py")),
             "--top", str(args.top)],
            capture_output=True, text=True)
        sys.stdout.write(proc.stdout)
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr)
            return proc.returncode
        symbols = symbols_from_watchlist(proc.stdout)
        if not symbols:
            print(f"\n{Y}Nothing passed the pillars. That is a normal morning — "
                  f"do not widen the filter to manufacture a candidate.{O}\n")
            return 0
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
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    for symbol in symbols:
        items, news_note = [], ""
        news_ok = alpaca is not None
        if alpaca is not None:
            try:
                items = news_items(alpaca, symbol, args.news_hours)
                if not items:
                    news_note = f"no headline in the last {args.news_hours}h"
            except AlpacaError as exc:
                news_note = f"news lookup failed: {exc}"
                news_ok = False
                exit_code = 1

        filings, filings_note, filings_ok = [], "", False
        if sec is not None:
            try:
                # A shelf stays usable for three years: read a full year of forms.
                filings = sec.recent_filings(symbol, since_days=max(args.days, 365), limit=80)
                filings_ok = True
                if not filings:
                    filings_note = "EDGAR returned nothing — supply risk UNVERIFIED, not clean"
            except SecError as exc:
                filings_note = f"filings lookup failed: {exc}"
                exit_code = 1
        else:
            filings_note = "filings skipped (--no-filings) — supply risk UNVERIFIED"

        # The desk card's own read (catalyst.card_read; rules in
        # knowledge-base/strategies/CATALYST.md), so this terminal and the desk
        # can never grade the same headlines differently.
        card = card_read(items, trading_date=today, source_ok=news_ok,
                         filings=filings, filings_checked=filings_ok)
        paint = GRADE_PAINT.get(card["grade"], "")
        print(f"{B}{symbol:<6}{O} {paint}{card['grade']:<9}{O} "
              f"{D}{card['type']} · {card['age']}{(' · ' + card['source']) if card['source'] else ''}{O}")
        print(f"       {card['reason']}  {D}[{card['rule']}]{O}")
        for line in _wrap(card["headline"] or ""):
            print(f"       {line}")
        if not card["headline"] and news_note:
            print(f"       {Y}{news_note}{O}")
        for f in card["flags"]:
            if f["id"] in ("split", "filings_unchecked"):
                continue                      # the CLI runs no split test; the note below says so
            print(f"       {FLAG_PAINT.get(f['level'], '')}{f['text']}{O}")
        if filings_note:
            print(f"       {Y}{filings_note}{O}")
        print()
    print(f"{D}Split test: not run here — scripts/premarket_stars.py runs it (CLAUDE.md rule 6).{O}")
    print(f"{D}The scanner discovers a candidate; the chart defines the setup; "
          f"the stop defines the size.{O}")
    print(f"{D}This tool only does the first half of the first step.{O}\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
