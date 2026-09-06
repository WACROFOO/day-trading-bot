#!/usr/bin/env python3
"""Check the IBKR read-only data path before the desk starts.

    python3 scripts/ibkr_preflight.py

Exit codes:
  0  live data confirmed (type 1, real-time bars arriving, scanner answers)
  1  ib_async is not installed          -> python3 -m pip install ib_async==2.1.0
  2  TWS is not reachable               -> start TWS, API > Settings > Enable ActiveX and Socket Clients,
                                           Read-Only API ON, port 7496, trusted IP 127.0.0.1
  3  market data is DELAYED (type 3/4)  -> the account has no live NASDAQ (Network C/UTP) subscription
  4  no real-time bars arrived          -> outside market hours, or the symbol is not trading
  5  scanner returned nothing           -> scanner permissions, or a quiet band

Nothing here transmits anything: the connection is opened read-only with a
client id the desk does not use, and only data requests are made.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

HOST = os.environ.get("IBKR_HOST", "127.0.0.1")
PORT = int(os.environ.get("IBKR_PORT", "7496"))
CLIENT = int(os.environ.get("IBKR_PREFLIGHT_CLIENT_ID", "29"))
PROBE = os.environ.get("IBKR_PREFLIGHT_SYMBOL", "QQQ")


def main() -> int:
    try:
        from ib_async import IB, ScannerSubscription, Stock
    except ImportError:
        print("ib_async is not installed. Run:  python3 -m pip install ib_async==2.1.0")
        return 1
    ib = IB()
    try:
        from momentum_platform.datasources.ibkr_stream import read_only_connect
        read_only_connect(ib, HOST, PORT, CLIENT, 10)
    except Exception as exc:
        print(f"cannot reach TWS at {HOST}:{PORT} — {exc}")
        print("TWS must be running with the API enabled: Edit > Global Configuration > API > Settings:")
        print("  Enable ActiveX and Socket Clients: ON   Read-Only API: ON   Socket port: 7496")
        return 2
    try:
        ver = ib.client.serverVersion()
        print(f"connected read-only to TWS {HOST}:{PORT}, client {CLIENT}, server version {ver}")
        ib.reqMarketDataType(1)
        c = Stock(PROBE, "SMART", "USD")
        ib.qualifyContracts(c)
        t = ib.reqMktData(c, "", False, False)
        ib.sleep(3)
        mdt = t.marketDataType
        last = t.last if t.last == t.last else None
        print(f"{PROBE}: market data type {mdt}, last {last}, bid {t.bid}, ask {t.ask}")
        if mdt in (3, 4):
            print("DELAYED data. The desk refuses delayed data. Subscribe to NASDAQ (Network C/UTP) "
                  "real-time in Account Management, then rerun.")
            return 3
        bars = ib.reqRealTimeBars(c, 5, "TRADES", False)
        ib.sleep(12)
        n = len(bars)
        print(f"{PROBE}: {n} five-second bars in 12 s" + (f", last close {bars[-1].close}" if n else ""))
        ib.cancelRealTimeBars(bars)
        ib.cancelMktData(c)
        if n == 0:
            print("no real-time bars arrived. Outside 04:00-20:00 ET this is expected; during the "
                  "session it means the real-time bar entitlement is missing.")
            return 4
        sub = ScannerSubscription(instrument="STK", locationCode="STK.NASDAQ.SCM",
                                  scanCode="TOP_PERC_GAIN", abovePrice=1, belowPrice=20, numberOfRows=10)
        hits = ib.reqScannerData(sub)
        syms = [h.contractDetails.contract.symbol for h in hits]
        print(f"scanner TOP_PERC_GAIN (NASDAQ Capital Market, $1-20): {len(syms)} rows " + " ".join(syms[:10]))
        if not syms:
            print("the scanner answered with nothing; check scanner permissions in TWS or widen the band")
            return 5
        try:
            mins = ib.reqHistoricalData(c, "", "900 S", "1 min", "TRADES", False, formatDate=2)
            print(f"{PROBE}: {len(mins or [])} one-minute bars for a '900 S' window (the desk's rolling refresh)")
        except Exception as exc:
            print(f"{PROBE}: '900 S' minute history refused ({exc}); the desk falls back to a day window")
        print("OK — live, read-only, real-time bars flowing, scanner answering.")
        return 0
    finally:
        ib.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
