#!/usr/bin/env python3
"""Check the Alpaca connection, one step at a time.

    python scripts/verify_alpaca.py
    python scripts/verify_alpaca.py --symbols AAPL,TSLA

Each check prints PASS, WARN or FAIL with what to do about it. Nothing here
places an order or spends money — it only reads.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from momentum_platform.datasources.tls import describe as describe_tls  # noqa: E402
from momentum_platform.datasources.alpaca_source import (  # noqa: E402
    AlpacaError, client_from_env, fetch_records, load_dotenv, session_window,
)

ET = ZoneInfo("America/New_York")
UTC = timezone.utc
GREEN, YELLOW, RED, DIM, OFF = "\033[92m", "\033[93m", "\033[91m", "\033[2m", "\033[0m"
_state = {"failed": 0, "warned": 0, "step": 0}


def step(title: str) -> None:
    _state["step"] += 1
    print(f"\n{DIM}── step {_state['step']} ─{OFF} {title}")


def ok(msg: str) -> None:
    print(f"  {GREEN}PASS{OFF}  {msg}")


def warn(msg: str, fix: str = "") -> None:
    _state["warned"] += 1
    print(f"  {YELLOW}WARN{OFF}  {msg}")
    if fix:
        print(f"        {DIM}{fix}{OFF}")


def fail(msg: str, fix: str = "") -> None:
    _state["failed"] += 1
    print(f"  {RED}FAIL{OFF}  {msg}")
    if fix:
        print(f"        {DIM}{fix}{OFF}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verify the Alpaca setup")
    ap.add_argument("--symbols", default="AAPL,MSFT",
                    help="symbols to test with (default: AAPL,MSFT)")
    args = ap.parse_args(argv)
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    print("Alpaca connection check — reads only, places no orders.")

    # ---------------------------------------------------------------- 1
    step("credentials")
    print(f"  {DIM}trust store: {describe_tls()}{OFF}")
    load_dotenv()
    import os
    key = os.environ.get("ALPACA_KEY_ID", "").strip()
    secret = os.environ.get("ALPACA_SECRET_KEY", "").strip()
    if not key or not secret:
        fail("ALPACA_KEY_ID or ALPACA_SECRET_KEY is missing.",
             "cp .env.example .env  then paste your keys into .env")
        return 1
    ok(f"key {key[:4]}…{key[-4:]} and a secret of {len(secret)} characters were found")
    if not key.startswith("PK"):
        warn("the key does not start with PK, which is the paper-key prefix.",
             "Live keys start with AK. Use paper keys while learning.")

    try:
        client = client_from_env()
    except AlpacaError as exc:
        fail(str(exc)); return 1

    # ---------------------------------------------------------------- 2
    step("account (proves the keys work)")
    try:
        account = client.account()
        ok(f"account {account.get('status')} · buying power "
           f"${float(account.get('buying_power', 0)):,.0f} (paper money)")
        if account.get("status") != "ACTIVE":
            warn(f"account status is {account.get('status')}, not ACTIVE.",
                 "Finish any onboarding steps in the Alpaca dashboard.")
    except AlpacaError as exc:
        fail(str(exc)); return 1

    # ---------------------------------------------------------------- 3
    step("market clock")
    try:
        clock = client.clock()
        now_et = datetime.now(UTC).astimezone(ET)
        state = "OPEN" if clock.get("is_open") else "closed"
        ok(f"market is {state} · it is {now_et:%H:%M} in New York")
        if not clock.get("is_open"):
            print(f"        {DIM}next open {clock.get('next_open','?')}{OFF}")
            print(f"        {DIM}A closed market is fine — you can still replay today "
                  f"or the last session.{OFF}")
    except AlpacaError as exc:
        fail(str(exc))

    # ---------------------------------------------------------------- 4
    step(f"daily history for {', '.join(symbols)}")
    try:
        start = (datetime.now(UTC) - timedelta(days=40)).isoformat(timespec="seconds").replace("+00:00", "Z")
        daily = client.bars(symbols, "1Day", start)
        for symbol in symbols:
            rows = daily.get(symbol, [])
            if rows:
                ok(f"{symbol}: {len(rows)} daily bars, last close ${rows[-1]['c']:.2f}")
            else:
                fail(f"{symbol}: no daily bars returned.",
                     "Check the spelling, or try a very liquid symbol like AAPL.")
    except AlpacaError as exc:
        fail(str(exc))

    # ---------------------------------------------------------------- 5
    step("intraday 1-minute bars (this is what the charts and scanners eat)")
    try:
        window_start, window_end = session_window()
        minute = client.bars(symbols, "1Min", window_start, window_end)
        total = sum(len(v) for v in minute.values())
        if total:
            for symbol in symbols:
                rows = minute.get(symbol, [])
                if rows:
                    last = rows[-1]
                    when = datetime.fromisoformat(last["t"].replace("Z", "+00:00")).astimezone(ET)
                    age = (datetime.now(UTC) - datetime.fromisoformat(
                        last["t"].replace("Z", "+00:00"))).total_seconds() / 60
                    ok(f"{symbol}: {len(rows)} minute bars today · last {when:%H:%M} ET "
                       f"(${last['c']:.2f}) · {age:.0f} min old")
                else:
                    warn(f"{symbol}: no minute bars in today's session yet.")
        else:
            warn("no minute bars for today at all.",
                 "Normal before 04:00 ET, at weekends, and on holidays. "
                 "Re-run during market hours.")
    except AlpacaError as exc:
        fail(str(exc))

    # ---------------------------------------------------------------- 6
    step("snapshots (previous close, needed for the % change pillar)")
    try:
        snaps = client.snapshots(symbols)
        for symbol in symbols:
            snap = snaps.get(symbol) or {}
            prev = (snap.get("prevDailyBar") or {}).get("c")
            if prev:
                ok(f"{symbol}: previous close ${prev:.2f}")
            else:
                warn(f"{symbol}: no previous close in the snapshot.")
    except AlpacaError as exc:
        fail(str(exc))

    # ---------------------------------------------------------------- 7
    step("news (this is what lights the flames)")
    try:
        items = client.news(symbols, limit=5)
        if items:
            ok(f"{len(items)} recent headlines available")
            for item in items[:3]:
                when = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
                age = (datetime.now(UTC) - when).total_seconds() / 3600
                flame = "red" if age <= 2 else "orange" if age <= 12 else "yellow" if age <= 24 else "none"
                print(f"        {DIM}{age:5.1f}h ({flame:6}) {item['headline'][:70]}{OFF}")
        else:
            warn("no headlines returned for these symbols.",
                 "Normal for quiet symbols. Try a name that is moving today.")
    except AlpacaError as exc:
        warn(f"news unavailable: {exc}",
             "The platform still works — the catalyst card will read 'no headline'.")

    # ---------------------------------------------------------------- 8
    step("tradable universe (replaces the NASDAQ-only symbol file)")
    try:
        assets = client.assets()
        tradable = [a for a in assets if a.get("tradable")]
        ok(f"{len(tradable):,} tradable US equities across "
           f"{len({a.get('exchange') for a in tradable})} exchanges")
    except AlpacaError as exc:
        warn(f"asset list unavailable: {exc}")

    # ---------------------------------------------------------------- 9
    step("end-to-end: build a dashboard session")
    try:
        records = fetch_records(client, symbols)
        bars = sum(1 for r in records if r["type"] == "bar")
        news = sum(1 for r in records if r["type"] == "news")
        if bars:
            ok(f"{bars} bar records and {news} news records normalized — "
               f"the dashboard can run on this")
        else:
            warn("no bar records; the dashboard would have nothing to draw.",
                 "Re-run during or after a trading session.")
    except AlpacaError as exc:
        fail(str(exc))

    # ---------------------------------------------------------------- done
    print()
    if _state["failed"]:
        print(f"{RED}{_state['failed']} check(s) failed{OFF} — fix those first, then re-run.")
        return 1
    if _state["warned"]:
        print(f"{YELLOW}All essential checks passed{OFF} with {_state['warned']} warning(s). "
              f"Warnings are usually just 'the market is closed'.")
    else:
        print(f"{GREEN}Everything passed.{OFF}")
    print("\nNext:  PYTHONPATH=src python -m momentum_platform.dashboard.server "
          f"--alpaca {','.join(symbols)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
