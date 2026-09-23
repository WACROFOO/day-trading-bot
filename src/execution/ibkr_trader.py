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

from momentum_platform.datasources.ibkr_stream import detach_reconnect_resubscribe

class StopMoveRejected(RuntimeError):
    """The broker refused to re-price a resting stop. `triggered` is True for
    IBKR's "Stop price revision is disallowed after order has triggered": the
    stop is no longer a resting order but a sell in flight, and the runner
    must stop trying to move it and wait for the fill."""

    def __init__(self, code: int, text: str, *, triggered: bool) -> None:
        super().__init__(f"{code}: {text}")
        self.code, self.text, self.triggered = code, text, triggered


from .intent import (SIDE, EntryIntent, PlacedOrder, entry_limit, in_regular_hours,
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
        self.net_liq: Optional[float] = None
        self.ib = None
        self.placed: list[PlacedOrder] = []

    # ------------------------------------------------------------ lifecycle
    def connect(self, timeout: int = 12) -> str:
        from ib_async import IB

        self.ib = IB()
        detach_reconnect_resubscribe(self.ib)     # same 1102 → 322 leak as the desk; see ibkr_stream
        # Broker errors by order id. A modify is asynchronous: placeOrder
        # returns, the rejection (201) arrives a few seconds later. WHLR
        # 2026-09-23 10:15: three trail moves "accepted" and written to the
        # ledger while IBKR refused every one; the stop stayed at 7.34 and
        # the ledger said 7.74. The mover now waits for this and reads it.
        self.order_errors: dict[int, list[tuple[int, str]]] = {}
        try:
            self.ib.errorEvent += self._on_order_error
        except Exception:                            # noqa: BLE001
            pass
        self.ib.connect(self.host, self.port, clientId=self.client_id,
                        readonly=False, timeout=timeout)
        try:
            self.account = assert_paper(self.ib.managedAccounts())
            # One read, at connect: what the account can hold. NetLiquidation,
            # not BuyingPower — small caps carry ~100% initial margin at IBKR,
            # and BuyingPower on this paper account reads 4x equity, which the
            # margin check then refuses (VEEE, 2026-09-21 09:37, error 201).
            try:
                vals = {v.tag: v.value for v in self.ib.accountSummary()
                        if v.tag == "NetLiquidation"}
                self.net_liq = float(vals["NetLiquidation"]) if vals else None
            except Exception:                        # noqa: BLE001
                self.net_liq = None
        except NotPaperError:
            # Disconnect before raising. A refused-but-open writable socket
            # to a live account is the exact thing being refused.
            self.ib.disconnect()
            self.ib = None
            raise
        return self.account

    def _on_order_error(self, reqId, errorCode, errorString, contract=None, *rest) -> None:
        if reqId is None or reqId < 0:
            return
        self.order_errors.setdefault(int(reqId), []).append((int(errorCode), str(errorString)))

    def _await_order_answer(self, order_id: int, seen: int, wait_s: float = 2.0):
        """After a modify: give the broker `wait_s` to answer, return the first
        new error for that order id, or None when none arrived. Works with a
        fake broker that has no event loop (no sleep, no errors)."""
        errors = getattr(self, "order_errors", None)
        if errors is None or not hasattr(self.ib, "sleep"):
            return None
        waited = 0.0
        while waited < wait_s:
            self.ib.sleep(0.5)
            waited += 0.5
            new = errors.get(order_id, [])[seen:]
            if new:
                return new[0]
        return None

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

        from ib_async import StopLimitOrder
        stock = Stock(intent.symbol, "SMART", "USD")
        self.ib.qualifyContracts(stock)
        # A10: rests at the trigger, fills only when the tape reaches it
        parent = StopLimitOrder(SIDE, intent.shares, entry_limit(intent.trigger), intent.trigger)
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

    def exit_market(self, symbol: str, qty: int, now=None) -> int:
        """SELL qty at market, SMART-routed, regular hours only. Returns the
        order id. The manual exit for a held position after a failed hard-stop
        flatten: no quote is needed, so it works with the desk down. Outside
        09:30-16:00 ET no market order exists and this refuses; use
        `exit_limit` with a fresh quote there."""
        from ib_async import MarketOrder, Stock

        if self.ib is None:
            raise RuntimeError("not connected")
        if qty <= 0:
            raise ValueError("exit_market sells a long; qty must be > 0")
        if not in_regular_hours(now):
            raise RuntimeError("no market orders exist outside regular hours; "
                               "use the limit exit with a fresh quote")
        stock = Stock(symbol, "SMART", "USD")
        self.ib.qualifyContracts(stock)
        order = MarketOrder("SELL", qty)
        order.tif = "DAY"
        order.transmit = True
        order.orderId = self.ib.client.getReqId()
        self.ib.placeOrder(stock, order)
        self.last_exit_order_id = order.orderId
        return order.orderId

    def _bracket(self, intent: EntryIntent):
        """Build the three legs by hand rather than via `ib.bracketOrder`.

        The helper insists on a take-profit leg. Ross exits into strength on
        the tape, and a mandatory limit target would either invent a price he
        did not choose or force every trade into a bracket shape the method
        does not use. Here the target is optional and the stop is not.
        """
        from ib_async import LimitOrder, StopLimitOrder, StopOrder

        oca = f"px-{intent.symbol}-{id(intent)}"
        # Pre-market legs must say so or IBKR holds them for 09:30. In regular
        # hours the flag is left False on purpose: a DAY order that is still
        # open at 16:00 must die, not follow the name into after hours.
        ext = intent.session == "premarket"

        # A10 (owner, 2026-09-23): a buy STOP-LIMIT resting at the trigger.
        # A plain limit at the trigger with the tape below it was marketable
        # and filled at once, far under the plan (WHLR 09:44: plan 8.31, fill
        # 7.87). The stop price is the trigger, the limit a small offset above
        # it; the runner cancels it after ENTRY_TTL_MINUTES untriggered.
        parent = StopLimitOrder(SIDE, intent.shares, entry_limit(intent.trigger), intent.trigger)
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
        # An OCA group only means something with TWO exit legs. With the stop
        # alone it did nothing for the bracket and forbade every later
        # modification: IBKR error 10326 "OCA group revision is not allowed"
        # CANCELLED the stop when the A3 trail first moved it (DCOY,
        # 2026-09-22 09:36, 41 shares held with no exit for eleven minutes).
        if target_leg is not None:
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
                    # A3: a stop that the runner had raised above the initial
                    # stop is the trailing exit, and the ledger says so.
                    rec.exit_reason = ("trail" if why == "stop" and rec.trail_stop is not None
                                       and rec.trail_stop > rec.stop else why)
                    t = leg.log[-1].time if leg.log else None
                    rec.exit_time = t.isoformat() if t else None
                    rec.events.append(f"exit {why} at {rec.exit_price}")

            stop = by_id.get(rec.stop_id) if rec.stop_id else None
            if stop is not None:
                # The resting level at the broker outranks the ledger's memory
                # of where the trail put it (WHLR 2026-09-23: three refused
                # moves left the ledger at 7.74 with the stop at 7.34).
                try:
                    resting = float(stop.order.auxPrice)
                    if resting > 0 and stop.orderStatus.status in ("Submitted", "PreSubmitted"):
                        rec.broker_stop_level = resting          # the mark the runner corrects the ledger from
                        if resting > float(rec.stop) + 1e-9 and rec.trail_stop != resting:
                            rec.events.append(f"stop rests at {resting} at the broker (record had {rec.trail_stop})")
                            rec.trail_stop = resting
                        elif abs(resting - float(rec.stop)) < 1e-9 and rec.trail_stop is not None:
                            rec.events.append(f"stop rests at the initial {resting}; the trail {rec.trail_stop} was never accepted")
                            rec.trail_stop = None
                except (TypeError, ValueError, AttributeError):
                    pass
                rec.stop_status = stop.orderStatus.status
                q = getattr(stop.order, "totalQuantity", None)
                rec.stop_qty = float(q) if q is not None else rec.stop_qty
                # Warning 399 on the stop leg is the tell: IBKR is holding it
                # for the open, so it is not protecting anything right now.
                queued = any(e.errorCode == 399 for e in stop.log)
                rec.protected = (not queued and rec.stop_status not in
                                 ("ValidationError", "Inactive", "Cancelled",
                                  "ApiCancelled"))
        return self.placed

    def move_stop(self, rec: PlacedOrder, new_stop: float) -> int:
        """A3: re-price the resting stop leg. Same order id, new trigger price —
        IBKR treats placeOrder on an existing id as a modification, so the
        stop never stops resting. Returns the order id modified; raises when
        the leg cannot be found, and the caller leaves the stop where it is."""
        if self.ib is None:
            raise RuntimeError("not connected")
        trades = list(self.ib.trades())
        leg = next((t for t in trades if rec.stop_id and t.order.orderId == rec.stop_id), None)
        if leg is None:
            leg = next((t for t in trades if getattr(t.order, "parentId", 0) == rec.parent_id
                        and t.order.orderType == "STP"), None)
        if leg is None:
            raise RuntimeError(f"stop leg {rec.stop_id} for {rec.symbol} not found at the broker")
        if leg.orderStatus.status in ("Filled", "Cancelled", "ApiCancelled", "Inactive"):
            raise RuntimeError(f"stop leg {rec.stop_id} is {leg.orderStatus.status}; nothing to move")
        order = leg.order
        was = order.auxPrice
        if getattr(order, "ocaGroup", ""):
            # A leg inside an OCA group cannot be modified (10326). Replace it:
            # the new stop is working BEFORE the old one is cancelled, so the
            # position is never without an exit; the window in which both
            # rest is one round trip to the broker.
            qty = int(order.totalQuantity)
            new_id = self.place_stop(rec.symbol, qty, round(new_stop, 2), ref=getattr(order, "orderRef", None))
            self.ib.cancelOrder(order)
            rec.stop_id = new_id
            rec.trail_stop = round(new_stop, 2)
            rec.events.append(f"stop replaced {was} -> {rec.trail_stop} (A3 trail; OCA leg cannot be modified) "
                              f"new leg {new_id}")
            return new_id
        seen = len(getattr(self, "order_errors", {}).get(order.orderId, []))
        order.auxPrice = round(new_stop, 2)
        order.transmit = True
        self.ib.placeOrder(leg.contract, order)
        answer = self._await_order_answer(order.orderId, seen)
        if answer is not None and answer[0] in (201, 10147, 10148):
            # The broker refused the modify. The stop still rests where it
            # was: put the local order back so nothing downstream reads the
            # refused level as the resting one, and tell the caller why.
            order.auxPrice = was
            code, text = answer
            rec.events.append(f"stop move {was} -> {round(new_stop, 2)} REFUSED by the broker ({code}): {text[:120]}")
            raise StopMoveRejected(code, text, triggered=("after order has triggered" in text.lower()))
        rec.trail_stop = round(new_stop, 2)
        rec.events.append(f"stop moved {was} -> {rec.trail_stop} (A3 trail)")
        return order.orderId

    def cancel_order_id(self, order_id: int) -> bool:
        """Cancel one resting order by id. True when it was found and the
        cancel was sent. The manual exit cancels the stop leg before it
        sells: a stop left resting after a hand sale fills into a SHORT."""
        if self.ib is None:
            raise RuntimeError("not connected")
        for t in self.ib.trades():
            if t.order.orderId == order_id and t.orderStatus.status not in ("Filled", "Cancelled", "ApiCancelled", "Inactive"):
                self.ib.cancelOrder(t.order)
                return True
        return False

    def working_stops(self, symbol: str) -> list[tuple[int, float, float]]:
        """(order id, stop price, quantity) of every SELL stop resting at the
        broker for `symbol`. `Runner.reprotect` reads this before placing a
        stop: a second stop under one position sells it twice."""
        if self.ib is None:
            raise RuntimeError("not connected")
        out = []
        for t in self.ib.trades():
            o = t.order
            if (getattr(t.contract, "symbol", None) == symbol and o.action == "SELL"
                    and o.orderType in ("STP", "STP LMT")
                    and t.orderStatus.status in ("Submitted", "PreSubmitted", "PendingSubmit")):
                out.append((o.orderId, float(o.auxPrice), float(o.totalQuantity)))
        return out

    def place_stop(self, symbol: str, qty: int, stop_price: float, ref: Optional[str] = None) -> int:
        """A standalone protective stop for a position already held. Used to
        re-protect a filled position whose stop leg died, and to replace an
        OCA-grouped leg the broker will not let us modify."""
        if self.ib is None:
            raise RuntimeError("not connected")
        from ib_async import Stock, StopOrder
        stock = Stock(symbol, "SMART", "USD")
        self.ib.qualifyContracts(stock)
        order = StopOrder("SELL", qty, round(stop_price, 2))
        order.orderId = self.ib.client.getReqId() if getattr(self.ib, "client", None) else 0
        order.tif = "DAY"
        order.transmit = True
        if ref:
            order.orderRef = ref
        self.ib.placeOrder(stock, order)
        return order.orderId

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
            if "trail_stop" in keys and r["trail_stop"] is not None:
                rec.trail_stop = r["trail_stop"]
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
        from ib_async import LimitOrder, MarketOrder, Stock

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
            # The sell goes on a SMART contract, never on `pos.contract`: the
            # position record names the listing exchange (NASDAQ), and a market
            # order placed on it is DIRECT-ROUTED, which the API's precautionary
            # settings reject (error 10311, GRML x62 on 2026-09-22 — the stop had
            # already been cancelled, so the hard stop left the position naked).
            stock = Stock(sym, "SMART", "USD")
            if hasattr(self.ib, "qualifyContracts"):
                self.ib.qualifyContracts(stock)
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
            self.ib.placeOrder(stock, order)
            done.append(f"{sym} x{qty} {order.orderType}")
            self.last_flatten.append({"symbol": sym, "qty": qty, "order_id": order.orderId,
                                      "type": order.orderType,
                                      "price": getattr(order, "lmtPrice", None)})
        return done

    def positions_held(self) -> list[tuple[str, int]]:
        """Long positions the broker reports right now — the only source that
        may say "flat" (review 2026-09-21, item 13f). Read-only."""
        if self.ib is None:
            raise RuntimeError("not connected")
        out = []
        for pos in self.ib.positions():
            qty = int(getattr(pos, "position", 0) or 0)
            if qty > 0:
                out.append((pos.contract.symbol, qty))
        return out

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
