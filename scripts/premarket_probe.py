#!/usr/bin/env python3
"""Does an IBKR stop order actually protect a position pre-market?

    python3 scripts/premarket_probe.py        # run between 07:00 and 09:30 ET

The corpus is clear about retail brokers in general —
`.claude/skills/extended-hours/SKILL.md`: "No stop orders of any type —
banned because thin tape makes stop hunting trivial [...] Your stop is
therefore mental or hotkeyed, never resting" — and it names thinkorswim,
Lightspeed and Webull. It does not say what IBKR does with a stop carrying
`outsideRth=True`, and IBKR is the broker this desk uses.

That gap matters. If IBKR simulates the stop server-side pre-market, a
pre-market bracket is genuinely protected and the executor can say so. If
IBKR queues it to 09:30 like everything else, then every pre-market entry
is naked from the moment it fills until the bell, and the strategy needs a
monitored exit instead. Those are different systems, and guessing which one
to build is how a plausible answer becomes an expensive one.

So: place an unfillable pre-market bracket, read what IBKR says about the
STOP leg, cancel. The order cannot fill — a BUY limit 99% below the market —
so the only thing under test is what IBKR reports about the resting stop.

Read the verdict at the bottom. Then paste the whole output back, because
the answer decides the design of the pre-market path.

Exit codes:
  0  probe ran; read the verdict
  1  ib_async is not installed
  2  Gateway not reachable
  3  NOT A PAPER ACCOUNT
  6  not pre-market right now — nothing was sent
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from execution.ibkr_trader import NotPaperError, PaperTrader  # noqa: E402
from execution.intent import ET, EntryIntent, in_premarket, shares_for  # noqa: E402

SYMBOL = os.environ.get("PROBE_SYMBOL", "AAPL")
TRIGGER, STOP, RISK = 1.00, 0.90, 20.0

OK, BAD, WARN, DIM = "\033[92m", "\033[91m", "\033[93m", "\033[2m"
END = "\033[0m"


def good(m): print(f"  {OK}ok{END}   {m}")
def bad(m): print(f"  {BAD}xx{END}   {m}")
def warn(m): print(f"  {WARN}!!{END}   {m}")
def note(m): print(f"       {DIM}{m}{END}")


def main() -> int:
    now = datetime.now(ET)
    print(f"\nPre-market stop probe   {SYMBOL}   {now:%H:%M ET, %A}")

    if not in_premarket(now):
        bad("not between 07:00 and 09:30 ET on a weekday")
        note("This probe only means anything during pre-market. Nothing sent.")
        return 6

    try:
        import ib_async  # noqa: F401
    except ImportError:
        bad("ib_async is not installed")
        return 1

    shares = shares_for(TRIGGER, STOP, RISK)
    intent = EntryIntent(
        symbol=SYMBOL, trigger=TRIGGER, stop=STOP, shares=shares,
        dollar_risk=RISK, plan_allowed=True, verdict="PROBE",
        session="premarket", note="unfillable pre-market stop probe",
    )

    trader = PaperTrader()
    try:
        account = trader.connect()
    except NotPaperError as exc:
        bad(str(exc))
        return 3
    except Exception as exc:
        bad(f"cannot reach IB Gateway on {trader.host}:{trader.port} — {exc}")
        return 2
    good(f"{account} — paper")

    try:
        placed = trader.place_bracket(intent, now=now)
        good(f"sent: parent {placed.parent_id}, stop {placed.stop_id}, "
             f"outsideRth=True on every leg")

        trader.ib.sleep(4)
        trader.sync()

        print("\nWhat IBKR says about each leg")
        queued_stop = False
        for t in trader.ib.trades():
            print(f"  {t.order.orderId:>4}  {t.order.orderType:<5} "
                  f"{t.order.action:<4} outsideRth={t.order.outsideRth}  "
                  f"-> {t.orderStatus.status}")
            for e in t.log:
                if e.errorCode:
                    note(f"    {e.errorCode}: {e.message}")
                    if e.errorCode == 399 and t.order.orderId == placed.stop_id:
                        queued_stop = True

        print("\nVERDICT")
        if queued_stop:
            warn("IBKR QUEUED the stop leg to 09:30 — it protects nothing now")
            note("A pre-market entry is naked from its fill until the bell.")
            note("The pre-market path needs a monitored exit, not a bracket.")
        elif placed.protected:
            good("IBKR is holding the stop leg as live pre-market")
            note("A pre-market bracket is genuinely protected. Still verify")
            note("a real fill before trusting it with size.")
        else:
            warn(f"inconclusive — stop status {placed.stop_status!r}")
            note("Paste this whole output back rather than reading it as a no.")
        return 0
    finally:
        try:
            n = trader.cancel_all()
            trader.ib.sleep(2)
            left = [t.order.orderId for t in trader.ib.openTrades()
                    if t.orderStatus.status not in
                    ("Cancelled", "ApiCancelled", "Filled")]
            (warn if left else good)(
                f"cancelled {n}; still open: {left}" if left
                else f"cancelled {n} order(s) — nothing resting")
            if left:
                note("CANCEL THESE BY HAND in the Gateway before leaving.")
        except Exception as exc:                        # noqa: BLE001
            bad(f"CANCEL FAILED: {exc} — cancel by hand in the Gateway")
        finally:
            trader.disconnect()


if __name__ == "__main__":
    sys.exit(main())
