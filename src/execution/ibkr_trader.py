"""The one writable connection in this repo, pointed at a paper account.

    from execution.ibkr_trader import PaperTrader
    with PaperTrader() as t:
        placed = t.place_bracket(intent)

Design, and why each part is shaped the way it is:

CONNECTION. Client id 31, port 4002, `readonly=False`. The map is 27/28 desk
data, 29 data preflight, 31 this, 32 the order preflight — chosen so two
connections never collide and so a stray order surface would show up under
an id nobody else uses.

PAPER, NOT CONFIGURABLE. `connect` reads the managed account and refuses
anything that does not begin with `DU`. There is no flag, environment
variable or argument that turns this off. Port 4001 is the live Gateway and
4002 is paper; one mistyped digit is the whole difference, so the account id
is checked rather than the port trusted.

BRACKETS, NEVER NAKED. An entry is placed with its stop attached in the same
transmission. A parent that fills while its stop is still a separate call is
an unprotected position for however long the gap lasts, and the gap is
exactly when things go wrong: a halt, a disconnect, a process death. IBKR
attaches children by parentId and holds the whole group until the last leg
carries transmit=True — which is what `transmit` is actually for, as opposed
to the what-if misuse that broke the preflight twice.

REGULAR HOURS ONLY, for now. A bracket needs a resting stop and extended
hours do not permit one — `.claude/skills/extended-hours/SKILL.md`: "No stop
orders of any type [...] Your stop is therefore mental or hotkeyed, never
resting." IBKR does not reject such an order; it queues it to 09:30, which
the first smoke test hit as warning 399. `intent.refusals` therefore refuses
any bracket outside 09:30-16:00 ET. A pre-market mode would need a
different shape (limit entry, no resting stop, a monitored exit) and is a
decision, not a default.

NO PRICES COME FROM HERE. The Gateway session has no market data — the
preflight showed `last=nan bid=-1` — and that is correct. Quotes come from
the live read-only desk feed. This module is a pipe.
"""

from __future__ import annotations

import os
from typing import Optional

from .intent import SIDE, EntryIntent, PlacedOrder, refusals

HOST = os.environ.get("IBKR_PAPER_HOST", "127.0.0.1")
PORT = int(os.environ.get("IBKR_PAPER_PORT", "4002"))
CLIENT = int(os.environ.get("IBKR_EXEC_CLIENT_ID", "31"))

PAPER_PREFIX = "DU"


class NotPaperError(RuntimeError):
    """The connected account is not a paper account. Nothing was sent."""


class OrderRefused(RuntimeError):
    """The intent failed a check here. Nothing was sent. Carries .reasons."""

    def __init__(self, reasons: list[str]):
        super().__init__("; ".join(reasons))
        self.reasons = reasons


def assert_paper(accounts) -> str:
    """Return the paper account, or refuse. Extracted so it is testable.

    An empty account list refuses too. 'No account visible' is not evidence
    of safety — it is evidence the connection is not understood.
    """
    accounts = [a for a in (accounts or []) if a]
    if not accounts:
        raise NotPaperError("no managed account on this connection")
    live = [a for a in accounts if not a.startswith(PAPER_PREFIX)]
    if live:
        raise NotPaperError(
            f"account {live[0]} is not a paper account. Refusing to arm an "
            f"order path. Paper ids begin with {PAPER_PREFIX!r}; port 4001 is "
            f"the live Gateway and 4002 is paper.")
    return accounts[0]


class PaperTrader:
    """A writable IBKR connection that cannot reach real money."""

    def __init__(self, host: str = HOST, port: int = PORT,
                 client_id: int = CLIENT, risk_gate=None):
        self.host, self.port, self.client_id = host, port, client_id
        self.risk_gate = risk_gate
        self.account: Optional[str] = None
        self.ib = None
        self.placed: list[PlacedOrder] = []

    # ------------------------------------------------------------ lifecycle
    def connect(self, timeout: int = 12) -> str:
        from ib_async import IB

        self.ib = IB()
        self.ib.connect(self.host, self.port, clientId=self.client_id,
                        readonly=False, timeout=timeout)
        try:
            self.account = assert_paper(self.ib.managedAccounts())
        except NotPaperError:
            # Disconnect before raising. A refused-but-open writable socket
            # to a live account is the exact thing being refused.
            self.ib.disconnect()
            self.ib = None
            raise
        return self.account

    def disconnect(self) -> None:
        if self.ib is not None:
            self.ib.disconnect()
            self.ib = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.disconnect()
        return False

    # --------------------------------------------------------------- orders
    def place_bracket(self, intent: EntryIntent,
                      now=None) -> PlacedOrder:
        """Entry, stop and optional target, transmitted as one group."""
        # Checks first, library second. An earlier draft imported ib_async at
        # the top of this method, so a refused intent died with
        # ModuleNotFoundError instead of naming the thing the reader can fix.
        # Refusal ordering is not cosmetic: the message is read inside the
        # window the trade lives in.
        reasons = refusals(intent, now=now)
        if reasons:
            raise OrderRefused(reasons)

        # The daily risk gate is asked last, so a badly-formed intent is
        # reported as badly-formed rather than as a risk violation. It raises
        # RiskVeto, which is deliberately not caught: a latched gate means
        # the day is over and the caller must see that, not a return value.
        if self.risk_gate is not None:
            self.risk_gate.assert_can_buy()

        if self.ib is None:
            raise RuntimeError("not connected")

        from ib_async import Stock

        stock = Stock(intent.symbol, "SMART", "USD")
        self.ib.qualifyContracts(stock)

        parent, stop_leg, target_leg = self._bracket(intent)

        trades = [self.ib.placeOrder(stock, o)
                  for o in (parent, target_leg, stop_leg) if o is not None]

        rec = PlacedOrder(
            symbol=intent.symbol,
            parent_id=parent.orderId,
            stop_id=stop_leg.orderId if stop_leg is not None else None,
            target_id=target_leg.orderId if target_leg is not None else None,
            trigger=intent.trigger, stop=intent.stop, shares=intent.shares,
            intent=intent,
        )
        rec.events.append(f"placed {len(trades)} legs on {self.account}")
        self.placed.append(rec)
        return rec

    def _bracket(self, intent: EntryIntent):
        """Build the three legs by hand rather than via `ib.bracketOrder`.

        The helper insists on a take-profit leg. Ross exits into strength on
        the tape, and a mandatory limit target would either invent a price he
        did not choose or force every trade into a bracket shape the method
        does not use. Here the target is optional and the stop is not.
        """
        from ib_async import LimitOrder, StopOrder

        oca = f"px-{intent.symbol}-{id(intent)}"

        parent = LimitOrder(SIDE, intent.shares, intent.trigger)
        parent.orderId = self.ib.client.getReqId()
        parent.transmit = False
        parent.tif = "DAY"

        target_leg = None
        if intent.target is not None:
            target_leg = LimitOrder("SELL", intent.shares, intent.target)
            target_leg.orderId = self.ib.client.getReqId()
            target_leg.parentId = parent.orderId
            target_leg.ocaGroup = oca
            target_leg.transmit = False
            target_leg.tif = "DAY"

        stop_leg = StopOrder("SELL", intent.shares, intent.stop)
        stop_leg.orderId = self.ib.client.getReqId()
        stop_leg.parentId = parent.orderId
        stop_leg.ocaGroup = oca
        stop_leg.tif = "DAY"
        # Last leg transmits, releasing the whole group at once. The stop is
        # deliberately the one that carries it: if anything in this sequence
        # fails partway, the group is never released and no unprotected entry
        # can exist.
        stop_leg.transmit = True

        return parent, stop_leg, target_leg

    # ------------------------------------------------------------- read back
    def sync(self) -> list[PlacedOrder]:
        """Refresh fills from IBKR. Records the realised R denominator."""
        if self.ib is None:
            raise RuntimeError("not connected")
        self.ib.sleep(0)
        by_id = {t.order.orderId: t for t in self.ib.trades()}
        for rec in self.placed:
            trade = by_id.get(rec.parent_id)
            if trade is None:
                continue
            rec.status = trade.orderStatus.status
            filled = trade.orderStatus.avgFillPrice
            if filled and filled > 0 and rec.fill_price != filled:
                rec.fill_price = filled
                rec.events.append(f"filled {filled} vs trigger {rec.trigger}")
        return self.placed

    def cancel_all(self) -> int:
        """Cancel every open order on this connection. The kill switch.

        Cancels orders only. It does not sell positions: an automated exit
        needs a price, and prices do not come from this session.
        """
        if self.ib is None:
            raise RuntimeError("not connected")
        n = 0
        for trade in self.ib.openTrades():
            self.ib.cancelOrder(trade.order)
            n += 1
        return n
