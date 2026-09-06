#!/usr/bin/env python3
"""Send one bracket to the paper account, read it back, cancel it.

    python3 scripts/paper_trade_smoke.py

This is the first thing in the repo that actually places an order, so it is
built to be run while the market is CLOSED and to be unfillable even if it
were not. The probe is a BUY limit at $1.00 on a $300 stock: for it to fill,
the name would have to fall 99%, and the order is DAY with no outside-RTH
flag, so it is not live outside the session at all. Two independent reasons
it cannot trade, because one reason is a single typo away from none.

What it proves, which the preflight could not: that a real bracket is
accepted by IBKR with its stop attached, that the legs come back readable,
and that the cancel path works. A `whatIfOrder` proves permissions; it does
not prove the group holds together.

The cancel runs in a `finally`. If anything below throws, the orders still
come back. An uncancelled resting order left by a crashed smoke test is the
worst outcome available here, so it is the one thing guaranteed not to
happen.

Exit codes:
  0  placed, read back, and cancelled
  1  ib_async is not installed
  2  Gateway not reachable
  3  NOT A PAPER ACCOUNT — nothing was sent
  5  IBKR rejected the bracket
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from execution.ibkr_trader import (  # noqa: E402
    NotPaperError, OrderRefused, PaperTrader,
)
from execution.intent import EntryIntent, shares_for  # noqa: E402

SYMBOL = os.environ.get("SMOKE_SYMBOL", "AAPL")
TRIGGER = 1.00      # ~99% below the market. Cannot fill.
STOP = 0.90
DOLLAR_RISK = 20.0

OK, BAD, WARN, DIM = "\033[92m", "\033[91m", "\033[93m", "\033[2m"
END = "\033[0m"


def good(m): print(f"  {OK}ok{END}   {m}")
def bad(m): print(f"  {BAD}xx{END}   {m}")
def warn(m): print(f"  {WARN}!!{END}   {m}")
def note(m): print(f"       {DIM}{m}{END}")


def main() -> int:
    print(f"\nPaper bracket smoke test   {SYMBOL}  "
          f"BUY {TRIGGER} / stop {STOP}")
    note("deliberately unfillable — 99% below the market, DAY, RTH only")

    try:
        import ib_async  # noqa: F401
    except ImportError:
        bad("ib_async is not installed")
        note("python3 -m pip install ib_async==2.1.0")
        return 1

    shares = shares_for(TRIGGER, STOP, DOLLAR_RISK)
    intent = EntryIntent(
        symbol=SYMBOL, trigger=TRIGGER, stop=STOP, shares=shares,
        dollar_risk=DOLLAR_RISK,
        # Hand-set: this probe is not a trade and no cascade ran on it. A
        # real entry gets this from `cascade.evaluate(...).plan_allowed` and
        # the executor refuses it when False.
        plan_allowed=True, verdict="SMOKE-TEST",
        note="unfillable probe, cancelled immediately",
    )
    print("\n1. Intent")
    good(f"{shares} shares, planned risk ${intent.planned_risk} "
         f"of ${DOLLAR_RISK} stated")

    trader = PaperTrader()
    print("\n2. Connect")
    try:
        account = trader.connect()
    except NotPaperError as exc:
        bad(str(exc))
        return 3
    except Exception as exc:
        bad(f"cannot reach IB Gateway on {trader.host}:{trader.port} — {exc}")
        note("Start IB Gateway, logged in to the PAPER account, port 4002.")
        return 2
    good(f"{account} — paper, client {trader.client_id}")

    try:
        print("\n3. Place the bracket")
        try:
            placed = trader.place_bracket(intent)
        except OrderRefused as exc:
            bad("refused before sending:")
            for r in exc.reasons:
                note(f"- {r}")
            return 5
        good(f"parent {placed.parent_id}, stop {placed.stop_id}")
        note("the stop leg is what carries transmit=True, so the group was")
        note("released as one — no entry existed without its stop")

        print("\n4. Read it back")
        trader.ib.sleep(2)
        trader.sync()
        for t in trader.ib.trades():
            good(f"order {t.order.orderId:>4}  {t.order.orderType:<5} "
                 f"{t.order.action} {t.order.totalQuantity:g} "
                 f"-> {t.orderStatus.status}")
        if placed.fill_price is not None:
            warn(f"FILLED at {placed.fill_price} — this should be impossible")
            note("Investigate before going further. Cancelling anyway.")
        else:
            good("nothing filled, as intended")

        print("\n5. Cancel")
        return 0
    finally:
        # Runs on every path, including the returns above and any exception.
        try:
            n = trader.cancel_all()
            trader.ib.sleep(2)
            still_open = [t.order.orderId for t in trader.ib.openTrades()
                          if t.orderStatus.status not in
                          ("Cancelled", "ApiCancelled", "Filled")]
            if still_open:
                warn(f"cancel sent for {n}, still open: {still_open}")
                note("CANCEL THESE BY HAND in the Gateway before leaving.")
            else:
                good(f"cancelled {n} order(s) — nothing resting")
                print(f"\n{OK}PASS{END} — the bracket path works end to end.")
        except Exception as exc:                       # noqa: BLE001
            bad(f"CANCEL FAILED: {exc}")
            note("Open IB Gateway and cancel any resting order BY HAND.")
        finally:
            trader.disconnect()


if __name__ == "__main__":
    sys.exit(main())
