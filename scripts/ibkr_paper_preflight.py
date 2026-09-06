#!/usr/bin/env python3
"""Check the IBKR PAPER order path before any executor is built.

    python3 scripts/ibkr_paper_preflight.py

This is the order-side twin of `scripts/ibkr_preflight.py`, which checks the
read-only DATA path on TWS. They are separate on purpose and must stay
separate: data comes from the live login on 7496 read-only, orders go to the
paper login on the Gateway. The desk never gains an order surface.

NOTHING IS TRANSMITTED. The only order-shaped call is `whatIfOrder`, which
asks IBKR to price an order's margin impact and explicitly does not place it.
No order-placing API is called anywhere in this file — deliberately spelled
out rather than named, so a grep for the placing verb finds nothing here at
all.

`whatIf` is the belt, and it is the ONLY belt available. An earlier draft also
set `transmit=False` on the probe, reasoning that two guards beat one. IBKR
rejects that combination outright:

    321  Error validating request.-'bC' : cause -
         What-If order should have transmit flag set to TRUE.

and then never answers, so the call hangs until the socket drops. The flags
mean different things: `transmit` decides whether a PLACED order goes to the
market or waits in TWS, while `whatIf` decides whether the order is placed at
all. Setting transmit=False on a what-if asks IBKR to park an order it was
never going to accept, and the extra guard removed the only real one by making
the request invalid.

Exit codes:
  0  paper order path confirmed
  1  ib_async is not installed     -> python3 -m pip install ib_async==2.1.0
  2  Gateway not reachable         -> start IB Gateway, API settings below
  3  NOT A PAPER ACCOUNT           -> refuses to continue; see the note below
  4  no account found on the connection
  5  order permissions not confirmed

Exit 3 is the one that matters. A live IBKR account id begins with `U`; a
paper account id begins with `DU`. If this script finds a `U` account it
stops and changes nothing, because the entire point of the exercise is that
the order path cannot reach real money. Port 4001 is the LIVE Gateway port
and 4002 is paper — a single mistyped digit is the whole difference, which is
exactly why this check exists rather than being left to care.
"""

from __future__ import annotations

import asyncio
import os
import sys

HOST = os.environ.get("IBKR_PAPER_HOST", "127.0.0.1")
PORT = int(os.environ.get("IBKR_PAPER_PORT", "4002"))     # 4002 = Gateway paper
CLIENT = int(os.environ.get("IBKR_PAPER_PREFLIGHT_CLIENT_ID", "32"))
PROBE = os.environ.get("IBKR_PAPER_PROBE_SYMBOL", "AAPL")

# Client id map, so two connections never collide:
#   27, 28  desk data (live TWS, read-only)
#   29      data preflight
#   31      the executor, when it exists
#   32      this script
OK, BAD, WARN, DIM = "\033[92m", "\033[91m", "\033[93m", "\033[2m"
END = "\033[0m"


def good(msg: str) -> None:
    print(f"  {OK}ok{END}   {msg}")


def bad(msg: str) -> None:
    print(f"  {BAD}xx{END}   {msg}")


def warn(msg: str) -> None:
    print(f"  {WARN}!!{END}   {msg}")


def note(msg: str) -> None:
    print(f"       {DIM}{msg}{END}")


def main() -> int:
    print(f"\nIBKR paper order preflight   {HOST}:{PORT}  client {CLIENT}")
    note("nothing here transmits an order")

    try:
        from ib_async import IB, LimitOrder, Stock, util
    except ImportError:
        bad("ib_async is not installed")
        note("python3 -m pip install ib_async==2.1.0")
        return 1

    ib = IB()

    # --- 1. reach the Gateway -------------------------------------------
    print("\n1. Gateway connection")
    try:
        # readonly=False on purpose: this is the ORDER path. It is the one
        # connection in this repo allowed to be writable, and it is pointed
        # at a paper account, which step 2 verifies before anything else.
        ib.connect(HOST, PORT, clientId=CLIENT, readonly=False, timeout=12)
    except Exception as exc:
        bad(f"cannot reach IB Gateway on {HOST}:{PORT} — {exc}")
        note("IB Gateway > Configure > Settings > API > Settings:")
        note("  Enable ActiveX and Socket Clients : ON")
        note("  Read-Only API                     : OFF   (orders need write)")
        note("  Socket port                       : 4002  (paper)")
        note("  Trusted IPs                       : 127.0.0.1")
        note("And check you are logged in to the PAPER account, not live.")
        return 2

    good(f"connected — server version {ib.client.serverVersion()}")

    try:
        # --- 2. is it really paper? --------------------------------------
        print("\n2. Account identity   (the check that matters)")
        accounts = list(ib.managedAccounts())
        if not accounts:
            bad("no managed account on this connection")
            return 4
        for acct in accounts:
            if acct.startswith("DU"):
                good(f"{acct} — PAPER account")
            elif acct.startswith("U"):
                bad(f"{acct} — this is a LIVE account. Refusing to continue.")
                note("Port 4001 is live Gateway; 4002 is paper. Check the port")
                note("and which account the Gateway is logged in to.")
                return 3
            else:
                warn(f"{acct} — cannot classify this account id")
                note("Expected DU… for paper. Stopping to be safe.")
                return 3

        # --- 3. buying power ---------------------------------------------
        print("\n3. Buying power")
        vals = {v.tag: v.value for v in ib.accountSummary()
                if v.tag in ("NetLiquidation", "BuyingPower", "TotalCashValue")}
        for tag, val in vals.items():
            good(f"{tag:16s} {val}")
        try:
            netliq = float(vals.get("NetLiquidation", "0"))
        except ValueError:
            netliq = 0.0
        if netliq > 100_000:
            warn(f"NetLiquidation is {netliq:,.0f}")
            note("IBKR paper defaults to about $1,000,000. Leave it and every")
            note("share count is fiction — you would size hundreds of times too")
            note("large and learn nothing about real fills. Reset the paper")
            note("balance in Client Portal to the size you actually intend.")

        # --- 4. can we price an order without placing one? ----------------
        print("\n4. Order permission   (whatIf — never transmitted)")
        stock = Stock(PROBE, "SMART", "USD")
        ib.qualifyContracts(stock)
        probe = LimitOrder("BUY", 1, 1.00)      # far from the market
        # transmit stays True — see the module docstring. IBKR error 321
        # rejects a what-if with transmit=False and then stops replying.
        # `whatIf` is what keeps this off the market, not `transmit`.
        #
        # Bounded rather than `ib.whatIfOrder(...)`: when IBKR refuses a
        # request it simply never answers, and the blocking call waits for a
        # reply that is not coming until the socket drops minutes later. A
        # preflight that hangs reports nothing; this one names the timeout and
        # points at the API log, which is where the refusal reason lives.
        try:
            if hasattr(ib, "whatIfOrderAsync"):
                state = util.run(asyncio.wait_for(
                    ib.whatIfOrderAsync(stock, probe), timeout=20))
            else:
                # Fallback for an ib_async without the async twin. Unbounded,
                # so it can still hang — but the transmit fix above is what
                # actually stops it hanging, and this keeps the check working
                # rather than raising AttributeError on a version I cannot
                # test against from here.
                state = ib.whatIfOrder(stock, probe)
        except asyncio.TimeoutError:
            bad("IBKR never answered the whatIf request (20s)")
            note("This means the request was refused, not that it was slow.")
            note("Open the Gateway API log and read the last error line:")
            note("  Gateway > Configure > Settings > API > Settings > ")
            note("  'Create API message log file', then look for error 321.")
            return 5
        if state and (state.initMarginChange or state.commission is not None):
            good("order permissions confirmed — IBKR priced the order")
            if state.commission is not None:
                note(f"commission on 1 share: {state.commission} "
                     f"{state.commissionCurrency or ''}")
        else:
            bad("IBKR did not price the order — permissions unconfirmed")
            note("Check the paper account has US stock trading permissions.")
            return 5

        # --- 5. market data on this session (informational) --------------
        print("\n5. Market data on the ORDER session   (informational only)")
        ticker = ib.reqMktData(stock, "", False, False)
        ib.sleep(3)
        if ticker.last or ticker.bid or ticker.close:
            good(f"data present — last={ticker.last} bid={ticker.bid} "
                 f"close={ticker.close}")
        else:
            warn("no market data on this session")
        note("This does NOT block anything. The executor places orders with")
        note("explicit prices; the desk supplies the prices from the live")
        note("read-only session. The order path is a pipe, not a quote source.")
        ib.cancelMktData(stock)

        print(f"\n{OK}PASS{END} — paper order path is usable.")
        note("Next: the executor connects on client 31 with the same settings.")
        return 0
    finally:
        ib.disconnect()


if __name__ == "__main__":
    sys.exit(main())
