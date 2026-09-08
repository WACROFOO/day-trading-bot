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

TWO SESSIONS, STATED NOT INFERRED. A regular-hours intent gets the bracket
described above. A pre-market intent (07:00-09:30) gets every leg flagged
outsideRth=True, and the stop leg's protection is UNCONFIRMED until read
back: `.claude/skills/extended-hours/SKILL.md` says no stop of any type
rests in extended hours, and IBKR queues rather than rejects what it will
not work (warning 399 on the first smoke test). Whether IBKR's own
simulated stop is the exception is not in the corpus; `premarket_probe.py`
answers it empirically. Until then `PlacedOrder.protected` is False for
every pre-market entry and the caller is expected to read it.

DAY TRADES ONLY. `flatten_all()` is the primitive for "no trade alive":
cancel everything, then exit every position. In regular hours that is a
market order. Outside them a market order does not exist, so it needs a
quote and sells at bid minus an offset - the skill's fill trick, "sell =
bid - offset" - and refuses without one rather than guess.

NO PRICES COME FROM HERE. The Gateway session has no market data — the
preflight showed `last=nan bid=-1` — and that is correct. Quotes come from
the live read-only desk feed. This module is a pipe.
"""

from __future__ import annotations

import os
from typing import Optional

from .intent import (SIDE, EntryIntent, PlacedOrder, in_regular_hours,
                     refusals)

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


def _fill_time(trade):
    """The broker's own stamp for the fill, from the trade log; None if the
    log carries none. The poll time is the wrong number here — it can lag the
    fill by a whole loop interval."""
    for e in reversed(getattr(trade, "log", []) or []):
        if getattr(e, "status", "") == "Filled" and getattr(e, "time", None):
            return e.time.isoformat()
    log = getattr(trade, "log", None)
    if log and getattr(log[-1], "time", None):
        return log[-1].time.isoformat()
    return None


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
        ext = intent.session == "premarket"

        # The record exists BEFORE anything is sent, and is kept whatever
        # happens after. 2026-09-07: this method sent both legs and then
        # raised on a name that only existed inside _bracket(); the smoke
        # test's cleanup cancelled them, but the live runner would have died
        # with orders resting at the broker and no trace of them here.
        rec = PlacedOrder(
            symbol=intent.symbol,
            parent_id=parent.orderId,
            stop_id=stop_leg.orderId if stop_leg is not None else None,
            target_id=target_leg.orderId if target_leg is not None else None,
            trigger=intent.trigger, stop=intent.stop, shares=intent.shares,
            intent=intent,
        )
        # Regular hours: the stop rests, IBKR confirmed the group. Pre-market:
        # not known until the stop leg's status is read back by sync().
        rec.protected = not ext
        self.placed.append(rec)
        try:
            trades = [self.ib.placeOrder(stock, o)
                      for o in (parent, target_leg, stop_leg) if o is not None]
        except Exception as exc:                        # noqa: BLE001
            rec.status = "error"
            rec.events.append(f"placeOrder raised: {exc!r} — CHECK THE BROKER for resting legs")
            raise
        rec.events.append(f"placed {len(trades)} legs on {self.account}"
                          + (" (pre-market, protection unconfirmed)" if ext
                             else ""))
        return rec

    def place_entry_monitored(self, intent: EntryIntent) -> PlacedOrder:
        """A pre-market entry with NO resting stop, by explicit design.

        Only for the probe verdict `queued`: IBKR would park a stop leg for
        09:30 and report it as accepted, which is worse than no stop because
        it looks like one. So none is sent, `protected` is False from the
        first line, `stop_status` says 'monitored', and `Runner.watch_stops`
        is the stop — a limit sell at bid − offset the moment the bid touches
        the level, which is the only exit that exists pre-market
        (.claude/skills/extended-hours/SKILL.md: limit orders only, sell =
        bid − offset). This depends on the runner being alive, and the
        record says so; an operator reading `protected=0` knows exactly what
        they are holding.
        """
        from ib_async import LimitOrder, Stock

        reasons = refusals(intent)
        if reasons:
            raise OrderRefused(reasons)
        if intent.session != "premarket":
            raise OrderRefused(["a monitored entry is a pre-market shape only; "
                                "regular hours get a bracket"])
        if self.risk_gate is not None:
            self.risk_gate.assert_can_buy()
        if self.ib is None:
            raise RuntimeError("not connected")

        stock = Stock(intent.symbol, "SMART", "USD")
        self.ib.qualifyContracts(stock)
        parent = LimitOrder(SIDE, intent.shares, intent.trigger)
        parent.orderId = self.ib.client.getReqId()
        parent.tif = "DAY"
        parent.outsideRth = True
        parent.transmit = True
        if intent.ref:
            parent.orderRef = intent.ref
        self.ib.placeOrder(stock, parent)

        rec = PlacedOrder(symbol=intent.symbol, parent_id=parent.orderId,
                          stop_id=None, target_id=None, trigger=intent.trigger,
                          stop=intent.stop, shares=intent.shares, intent=intent,
                          protected=False, stop_status="monitored")
        rec.events.append(f"placed MONITORED entry on {self.account} — no resting stop; "
                          f"runner.watch_stops is the stop")
        self.placed.append(rec)
        return rec

    def exit_limit(self, symbol: str, qty: int, bid: float, offset: float = 0.10,
                   outside_rth: bool = True) -> float:
        """SELL qty at bid − offset, limit, extended hours. Returns the price.

        The skill's fill trick, on the sell side: "place the limit 10-15c
        [...] below the bid — it sweeps the levels up to your cap and fills
        immediately." A market order does not exist outside regular hours.
        """
        from ib_async import LimitOrder, Stock

        if self.ib is None:
            raise RuntimeError("not connected")
        if qty <= 0:
            raise ValueError("exit_limit sells a long; qty must be > 0")
        px = round(bid - offset, 2)
        stock = Stock(symbol, "SMART", "USD")
        self.ib.qualifyContracts(stock)
        order = LimitOrder("SELL", qty, px)
        order.tif = "DAY"
        order.outsideRth = outside_rth
        order.transmit = True
        order.orderId = self.ib.client.getReqId()
        self.ib.placeOrder(stock, order)
        # The caller records this id against the position so sync() can
        # confirm the fill; the return value stays the price for compatibility.
        self.last_exit_order_id = order.orderId
        return px

    def _bracket(self, intent: EntryIntent):
        """Build the three legs by hand rather than via `ib.bracketOrder`.

        The helper insists on a take-profit leg. Ross exits into strength on
        the tape, and a mandatory limit target would either invent a price he
        did not choose or force every trade into a bracket shape the method
        does not use. Here the target is optional and the stop is not.
        """
        from ib_async import LimitOrder, StopOrder

        oca = f"px-{intent.symbol}-{id(intent)}"
        # Pre-market legs must say so or IBKR holds them for 09:30. In regular
        # hours the flag is left False on purpose: a DAY order that is still
        # open at 16:00 must die, not follow the name into after hours.
        ext = intent.session == "premarket"

        parent = LimitOrder(SIDE, intent.shares, intent.trigger)
        parent.orderId = self.ib.client.getReqId()
        parent.transmit = False
        parent.tif = "DAY"
        parent.outsideRth = ext
        if intent.ref:
            parent.orderRef = intent.ref

        target_leg = None
        if intent.target is not None:
            target_leg = LimitOrder("SELL", intent.shares, intent.target)
            target_leg.orderId = self.ib.client.getReqId()
            target_leg.parentId = parent.orderId
            target_leg.ocaGroup = oca
            target_leg.transmit = False
            target_leg.tif = "DAY"
            target_leg.outsideRth = ext
            if intent.ref:
                target_leg.orderRef = intent.ref

        stop_leg = StopOrder("SELL", intent.shares, intent.stop)
        stop_leg.orderId = self.ib.client.getReqId()
        stop_leg.parentId = parent.orderId
        stop_leg.ocaGroup = oca
        stop_leg.tif = "DAY"
        stop_leg.outsideRth = ext
        if intent.ref:
            stop_leg.orderRef = intent.ref
        # Last leg transmits, releasing the whole group at once. The stop is
        # deliberately the one that carries it: if anything in this sequence
        # fails partway, the group is not released. That is IBKR's documented
        # use of the transmit flag while a bracket is assembled — it says
        # nothing about a child rejected or cancelled later, a disconnect, or
        # a quantity mismatch, which is what sync() and
        # Runner.reconcile_positions() are for (audit 2026-09-08 F5).
        stop_leg.transmit = True

        return parent, stop_leg, target_leg

    # ------------------------------------------------------------- read back
    def sync(self) -> list[PlacedOrder]:
        """Refresh fills from IBKR. Records the realised R denominator."""
        if self.ib is None:
            raise RuntimeError("not connected")
        self.ib.sleep(0)
        all_trades = list(self.ib.trades())
        by_id = {t.order.orderId: t for t in all_trades if t.order.orderId}
        by_perm = {t.order.permId: t for t in all_trades if getattr(t.order, "permId", 0)}

        def find(order_id, perm_id):
            # orderId is per API session; after a restart IBKR reports earlier
            # orders as orderId 0 and only the permId survives.
            t = by_id.get(order_id) if order_id else None
            if t is None and perm_id:
                t = by_perm.get(perm_id)
            return t

        for rec in self.placed:
            trade = find(rec.parent_id, rec.perm_id)
            if trade is None:
                continue
            if getattr(trade.order, "permId", 0) and not rec.perm_id:
                rec.perm_id = trade.order.permId
                rec.events.append(f"permId {rec.perm_id}")
            rec.status = trade.orderStatus.status
            filled = trade.orderStatus.avgFillPrice
            qty = getattr(trade.orderStatus, "filled", None)
            if qty and qty > 0 and rec.filled_qty != qty:
                rec.filled_qty = qty
                if qty < rec.shares:
                    rec.events.append(f"PARTIAL fill {qty:g} of {rec.shares}")
            if filled and filled > 0 and rec.fill_price != filled:
                rec.fill_price = filled
                rec.fill_time = _fill_time(trade)
                rec.events.append(f"filled {filled} vs trigger {rec.trigger}")

            # A sent-but-unconfirmed exit (monitored stop, hard-stop flatten):
            # the fill, when IBKR reports it, is the exit price. Until then the
            # ledger row says ExitPending and the position counts as held.
            if rec.exit_order_id and not rec.exit_confirmed:
                ex = by_id.get(rec.exit_order_id)
                if ex is not None:
                    rec.exit_status = ex.orderStatus.status
                if (ex is not None and ex.orderStatus.status == "Filled"
                        and ex.orderStatus.avgFillPrice and ex.orderStatus.avgFillPrice > 0):
                    rec.exit_price = ex.orderStatus.avgFillPrice
                    rec.exit_time = _fill_time(ex)
                    rec.exit_confirmed = True
                    rec.events.append(f"exit order {rec.exit_order_id} filled at {rec.exit_price}")
                elif ex is not None and ex.orderStatus.status in ("Cancelled", "ApiCancelled", "Inactive"):
                    rec.events.append(f"exit order {rec.exit_order_id} {ex.orderStatus.status} — "
                                      f"position may still be held; CHECK THE BROKER")

            # The exit legs. A filled stop or target is the trade's end and
            # its P&L; without reading them the ledger never learns either.
            for leg_id, why in ((rec.stop_id, "stop"), (rec.target_id, "target")):
                leg = by_id.get(leg_id) if leg_id else None
                if leg is None and leg_id:
                    # a child leg from a previous session: same parent permId group
                    leg = next((t for t in all_trades
                                if getattr(t.order, "parentId", 0) == rec.parent_id
                                and t.order.orderType == ("STP" if why == "stop" else "LMT")), None)
                if (leg is not None and rec.exit_price is None
                        and leg.orderStatus.status == "Filled"
                        and leg.orderStatus.avgFillPrice
                        and leg.orderStatus.avgFillPrice > 0):
                    rec.exit_price = leg.orderStatus.avgFillPrice
                    rec.exit_reason = why
                    t = leg.log[-1].time if leg.log else None
                    rec.exit_time = t.isoformat() if t else None
                    rec.events.append(f"exit {why} at {rec.exit_price}")

            stop = by_id.get(rec.stop_id) if rec.stop_id else None
            if stop is not None:
                rec.stop_status = stop.orderStatus.status
                # Warning 399 on the stop leg is the tell: IBKR is holding it
                # for the open, so it is not protecting anything right now.
                queued = any(e.errorCode == 399 for e in stop.log)
                rec.protected = (not queued and rec.stop_status not in
                                 ("ValidationError", "Inactive", "Cancelled",
                                  "ApiCancelled"))
        return self.placed

    def adopt(self, rows) -> int:
        """Rebuild the in-memory records from the ledger's open orders.

        `self.placed` lives only as long as this process. A runner restarted
        mid-morning would otherwise sync nothing for orders it placed before
        the restart, and a filled position could sit with its exit unrecorded.
        Adopted records carry the ledger's ids, so `sync()` finds them at the
        broker exactly as if this process had placed them.
        """
        n = 0
        have = {p.parent_id for p in self.placed}
        for r in rows:
            if not r["parent_id"] or r["parent_id"] in have:
                continue        # an intent without ids is reconciled, not adopted
            rec = PlacedOrder(symbol=r["symbol"], parent_id=r["parent_id"],
                              stop_id=r["stop_id"], target_id=r["target_id"],
                              trigger=r["trigger"], stop=r["stop"], shares=int(r["shares"]),
                              status=r["status"], fill_price=r["fill_price"],
                              fill_time=r["fill_ts"], protected=bool(r["protected"]),
                              stop_status=r["stop_status"],
                              perm_id=(r["perm_id"] if "perm_id" in r.keys() else None))
            keys = r.keys()
            if "filled_qty" in keys and r["filled_qty"] is not None:
                rec.filled_qty = r["filled_qty"]
            if "exit_order_id" in keys and r["exit_order_id"] and r["status"] == "ExitPending":
                rec.exit_order_id = r["exit_order_id"]
                rec.exit_confirmed = False
            rec.events.append("adopted from the ledger after a restart")
            self.placed.append(rec)
            n += 1
        return n

    def flatten_all(self, quote=None, offset: float = 0.10,
                    now=None) -> list[str]:
        """No trade alive. Cancel every order, then exit every position.

        `quote(symbol) -> (bid, ask)` is only needed outside regular hours,
        where a market order does not exist. The default offset is the
        skill's: "place the limit 10-15c above the ask (selling: below the
        bid) - it sweeps the levels up to your cap and fills immediately".
        Prices never come from this session, so the quote is injected.
        """
        from ib_async import LimitOrder, MarketOrder

        if self.ib is None:
            raise RuntimeError("not connected")
        done: list[str] = []
        # What was sent, with ids, for the runner to record as pending exits.
        self.last_flatten: list[dict] = []
        self.cancel_all()
        rth = in_regular_hours(now)
        for pos in self.ib.positions():
            qty = int(pos.position)
            if qty <= 0:
                continue        # long-only book; a short here is not ours
            sym = pos.contract.symbol
            if rth:
                order = MarketOrder("SELL", qty)
            else:
                if quote is None:
                    raise RuntimeError(
                        f"cannot flatten {sym} outside regular hours without "
                        f"a quote: no market orders exist there and prices do "
                        f"not come from this session")
                bid, _ask = quote(sym)
                order = LimitOrder("SELL", qty, round(bid - offset, 2))
                order.outsideRth = True
            order.tif = "DAY"
            order.orderId = self.ib.client.getReqId() if getattr(self.ib, "client", None) else 0
            self.ib.placeOrder(pos.contract, order)
            done.append(f"{sym} x{qty} {order.orderType}")
            self.last_flatten.append({"symbol": sym, "qty": qty, "order_id": order.orderId,
                                      "type": order.orderType,
                                      "price": getattr(order, "lmtPrice", None)})
        return done

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
