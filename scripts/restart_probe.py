#!/usr/bin/env python3
"""Does a restarted runner find its own resting orders at the broker?

    python3 scripts/restart_probe.py        # any time; safe on a closed market

The runner keeps its orders in memory and, after a restart, adopts them
from the ledger and asks IBKR about them. IBKR identifies an order by
orderId only within one API session; an order from an earlier connection
comes back as orderId 0 (seen 2026-09-07). The permId is what survives.

This places the unfillable bracket (BUY AAPL at $1.00, stop $0.90 — cannot
execute), DISCONNECTS WITHOUT CANCELLING, reconnects on the same client id,
and checks whether both legs are found — by orderId, by permId, or not at
all. Then cancels everything and verifies nothing rests. If the script
dies in between, the resting order is a $1.00 bid on a $300 stock: it will
never fill, and it dies at the next close.

Exit codes: 0 ran (read the verdict) · 1 no ib_async · 2 no Gateway ·
3 not a paper account · 5 something still resting after cancel
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from execution.ibkr_trader import NotPaperError, PaperTrader  # noqa: E402
from execution.intent import EntryIntent, shares_for  # noqa: E402

OK, BAD, WARN, DIM, END = "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m"
def good(m): print(f"  {OK}ok{END}   {m}")
def bad(m): print(f"  {BAD}xx{END}   {m}")
def warn(m): print(f"  {WARN}!!{END}   {m}")
def note(m): print(f"       {DIM}{m}{END}")


def main() -> int:
    print("\nRestart probe   does a new session find the last session's orders?")
    try:
        import ib_async  # noqa: F401
    except ImportError:
        bad("ib_async is not installed"); return 1
    intent = EntryIntent(symbol="AAPL", trigger=1.00, stop=0.90, shares=shares_for(1.00, 0.90, 20.0),
                         dollar_risk=20.0, plan_allowed=True, verdict="PROBE", session="regular")
    t1 = PaperTrader()
    try:
        acct = t1.connect()
    except NotPaperError as exc:
        bad(str(exc)); return 3
    except Exception as exc:                        # noqa: BLE001
        bad(f"cannot reach the Gateway: {exc}"); return 2
    good(f"{acct} — session 1, client {t1.client_id}")

    print("\n1. Place the unfillable bracket, then DISCONNECT without cancelling")
    now = datetime(2026, 9, 8, 14, 15, tzinfo=timezone.utc)     # a regular-hours clock for the refusals
    placed = t1.place_bracket(intent, now=now)
    t1.ib.sleep(3); t1.sync()
    good(f"placed parent {placed.parent_id} stop {placed.stop_id} · permId {placed.perm_id}")
    ids = (placed.parent_id, placed.stop_id); perm = placed.perm_id
    t1.disconnect()
    good("disconnected; the orders are resting at the broker")

    print("\n2. Reconnect as a fresh process and look for them")
    t2 = PaperTrader()
    t2.connect(); t2.ib.sleep(3)
    trades = list(t2.ib.trades())
    open_ = [t for t in trades if t.orderStatus.status not in ("Cancelled", "ApiCancelled", "Filled", "Inactive")]
    for t in trades:
        note(f"orderId {t.order.orderId:>4} permId {getattr(t.order, 'permId', 0):>10} "
             f"{t.order.orderType:<4} {t.order.action:<4} -> {t.orderStatus.status}")
    by_id = any(t.order.orderId in ids for t in open_)
    by_perm = any(getattr(t.order, "permId", 0) == perm for t in open_) if perm else False

    print("\nVERDICT")
    if by_id:
        good("found by orderId — the same client id keeps its ids across sessions")
        verdict = "orderId"
    elif by_perm:
        warn("found by permId only — orderId came back as 0; adoption must match on permId")
        verdict = "permId"
    elif open_:
        bad("orders are open at the broker but match neither id — adoption would MISS them")
        verdict = "unmatched"
    else:
        bad("no open orders reported to the new session — the broker did not hand them over")
        verdict = "not-reported"
    print(f"VERDICT: {verdict}")

    print("\n3. Cancel everything, verify nothing rests")
    n = t2.cancel_all(); t2.ib.sleep(3)
    left = [t.order.orderId for t in t2.ib.openTrades()
            if t.orderStatus.status not in ("Cancelled", "ApiCancelled", "Filled")]
    t2.disconnect()
    if left:
        bad(f"still open: {left} — CANCEL BY HAND in the Gateway"); return 5
    good(f"cancelled {n}; nothing resting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
