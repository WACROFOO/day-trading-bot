"""Command-line entry points.

  python -m momentum_platform.cli replay fixtures/market_replay/demo.jsonl
  python -m momentum_platform.cli track AAPL BXRX ...   # delayed yfinance poll
  python -m momentum_platform.cli watchlist add|remove|show SYMBOL...
  python -m momentum_platform.cli events [--symbol X] [--scanner Y]

Alerts print to the console, append to data/alerts.jsonl, and POST to
$MOMENTUM_WEBHOOK_URL when set (Slack-compatible; keep the URL out of git).
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

from .engine import ScannerEngine
from .notify import ConsoleChannel, JsonlChannel, NotificationRouter, RouterConfig, WebhookChannel
from .scanners import (
    Breakout52wScanner,
    FivePillarsAlert,
    FivePillarsList,
    HodMomentumScanner,
    RunningMoveScanner,
    TopGappersScanner,
    low_float_top_gainers,
    squeeze_10_in_10,
    squeeze_5_in_5,
    top_gainers,
    top_relative_volume,
)
from .store import EventStore


def default_scanners() -> list:
    return [
        FivePillarsAlert(),
        HodMomentumScanner(),
        RunningMoveScanner(direction="up"),
        squeeze_5_in_5(),
        squeeze_10_in_10(),
        Breakout52wScanner(),
        # list scanners (rank-only; no per-tick events)
        FivePillarsList(),
        top_gainers(),
        low_float_top_gainers(),
        top_relative_volume(),
        TopGappersScanner(),
    ]


def build_router(jsonl_path: str = "data/alerts.jsonl") -> NotificationRouter:
    channels = [ConsoleChannel(), JsonlChannel(jsonl_path)]
    webhook = os.environ.get("MOMENTUM_WEBHOOK_URL")
    if webhook:
        channels.append(WebhookChannel(webhook))
    return NotificationRouter(RouterConfig(), channels)


def cmd_replay(args: argparse.Namespace) -> int:
    from .datasources.replay import ReplaySource

    source = ReplaySource.from_file(args.fixture)
    store = EventStore(args.db)
    engine = ScannerEngine(scanners=default_scanners(), router=build_router(), store=store)
    source.apply_static(engine.hot)
    updates = 0
    last_ts = None
    for update in source.market_updates():
        engine.process(update)
        updates += 1
        last_ts = update.ts
    print(f"\nreplay complete: {updates} updates, {engine.events_emitted} events, "
          f"{engine.router.suppressed_count} suppressed")
    if last_ts is not None:
        for scanner_id, rows in engine.rank_all(last_ts).items():
            print(f"\n== {scanner_id} ==")
            for row in rows[:10]:
                print(f"  {row.symbol:6s} metric={row.rank_metric:.2f} {row.values.get('metric','')}")
    store.close()
    return 0


def cmd_track(args: argparse.Namespace) -> int:
    from .datasources.yfinance_source import fetch_reference, poll_quotes

    store = EventStore(args.db)
    symbols = [s.upper() for s in args.symbols] or store.watchlist()
    if not symbols:
        print("no symbols: pass them on the command line or add to the watchlist")
        return 1
    print(f"tracking {len(symbols)} symbols (yfinance is DELAYED ~15m; "
          "research candidates only, never entry signals)")
    engine = ScannerEngine(scanners=default_scanners(), router=build_router(), store=store)
    print("fetching reference data (prev close, avg volume, float)...")
    engine.hot.load_reference(fetch_reference(symbols))
    try:
        for update in poll_quotes(symbols, interval_seconds=args.interval,
                                  iterations=args.iterations):
            engine.process(update)
    except KeyboardInterrupt:
        pass
    print(f"\ndone: {engine.events_emitted} events")
    now = datetime.now(timezone.utc)
    for scanner_id, rows in engine.rank_all(now).items():
        print(f"\n== {scanner_id} ==")
        for row in rows[:10]:
            print(f"  {row.symbol:6s} metric={row.rank_metric:.2f}")
    store.close()
    return 0


def cmd_watchlist(args: argparse.Namespace) -> int:
    store = EventStore(args.db)
    if args.action == "add":
        for s in args.symbols:
            store.add_to_watchlist(s)
        print("added:", ", ".join(s.upper() for s in args.symbols))
    elif args.action == "remove":
        for s in args.symbols:
            store.remove_from_watchlist(s)
        print("removed:", ", ".join(s.upper() for s in args.symbols))
    else:
        wl = store.watchlist()
        print("\n".join(wl) if wl else "(watchlist empty)")
    store.close()
    return 0


def cmd_events(args: argparse.Namespace) -> int:
    store = EventStore(args.db)
    for ev in store.events(symbol=args.symbol, scanner=args.scanner, limit=args.limit):
        print(f"{ev['source_ts']}  {ev['symbol']:6s} {ev['scanner_id']}"
              f"{'/' + ev['branch'] if ev['branch'] else ''} [{ev['severity']}] "
              f"{ev['values_json']}")
    store.close()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="momentum_platform")
    parser.add_argument("--db", default="data/momentum_platform.db")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("replay", help="run a deterministic replay fixture")
    p.add_argument("fixture")
    p.set_defaults(fn=cmd_replay)

    p = sub.add_parser("track", help="poll a watchlist via yfinance (delayed)")
    p.add_argument("symbols", nargs="*")
    p.add_argument("--interval", type=float, default=30.0)
    p.add_argument("--iterations", type=int, default=None)
    p.set_defaults(fn=cmd_track)

    p = sub.add_parser("watchlist", help="manage the tracked watchlist")
    p.add_argument("action", choices=["add", "remove", "show"])
    p.add_argument("symbols", nargs="*")
    p.set_defaults(fn=cmd_watchlist)

    p = sub.add_parser("events", help="query stored scanner events")
    p.add_argument("--symbol")
    p.add_argument("--scanner")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(fn=cmd_events)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
