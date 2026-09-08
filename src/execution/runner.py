"""The loop that turns ledger decisions into refusals, logs, or orders.

    Runner(conn, mode="LOG_ONLY", dollar_risk=25.0).step()

Two modes, and the order they are used in is the exercise's order of build
(`docs/paper-exercise-brief.md` §⑧):

  LOG_ONLY  every pending decision is sized, run through `refusals`, and
            recorded as REFUSED (with reasons) or LOG_ONLY. No connection is
            opened. This is what runs for several sessions first, so the
            replay check can prove the log is faithful before an order exists.
  TRADE     the same, then `PaperTrader.place_bracket` for what survives,
            and the order, fill, realised R and NBBO are written back.

The clock is the decision's own bar, not the wall clock, in both modes.
A plan armed at 10:05 is judged as a 10:05 plan whether the runner sees it
at 10:05 or replays it at midnight; that is what makes the LOG_ONLY replay
and the live run comparable. TRADE mode additionally refuses anything whose
bar is older than `max_age_s` — a stale decision is a different trade from
the one the cascade reviewed.

The runner reads the desk's output from SQLite and never from a live desk
object. That is the whole reason the ledger exists as the bus.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Callable, NamedTuple, Optional

from journal import ledger as L

from .bridge import decision_clock, intent_from_decision
from .ibkr_trader import OrderRefused, PaperTrader
from .intent import ET, refusals
from momentum_platform.sessions import REGULAR_END
from .policy import premarket_allowed, premarket_shape

MODES = ("LOG_ONLY", "TRADE")


class Acted(NamedTuple):
    """What the runner did with one decision, with enough to render a line.

    A decision_id alone is a 16-character hash. An operator watching a
    morning of these needs the symbol and the levels, or the log is
    unreadable exactly when it matters.
    """
    decision_id: str
    symbol: str
    ts_et: str
    trigger: float
    stop: float
    outcome: str
    reasons: list[str]

Quote = Callable[[str], Optional[dict]]     # symbol -> {bid, ask, bid_size, ask_size, ts}


class Runner:
    def __init__(self, conn: sqlite3.Connection, *, mode: str, dollar_risk: float,
                 trader: Optional[PaperTrader] = None, quote: Optional[Quote] = None,
                 max_age_s: int = 120, now: Optional[Callable[[], datetime]] = None):
        if mode not in MODES:
            raise ValueError(f"mode {mode!r} not in {MODES}")
        if mode == "TRADE" and trader is None:
            raise ValueError("TRADE mode needs a connected PaperTrader")
        if dollar_risk <= 0:
            raise ValueError("dollar_risk must be the user's own stated risk, > 0")
        self.conn, self.mode, self.dollar_risk = conn, mode, dollar_risk
        self.trader, self.quote, self.max_age_s = trader, quote, max_age_s
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.acted: list[Acted] = []
        # Entries and exits are separate switches. A risk-gate lock closes
        # entries for the day; the exit side (fill sync, monitored stops, the
        # hard-stop flatten) must keep running in TRADE mode.
        self.entries_enabled = True
        if self.mode == "TRADE":
            # Whatever the ledger says is still alive at the broker is ours to
            # track from the first loop, restart or not.
            adopted = self.trader.adopt(L.open_orders(self.conn))
            if adopted:
                self.acted_note = f"adopted {adopted} open order(s) from the ledger"

    # ------------------------------------------------------------- the loop
    def step(self) -> list["Acted"]:
        """Act on every pending decision once. Returns what was done."""
        done = []
        for row in L.pending(self.conn):
            outcome, reasons = self._act(row)
            L.set_outcome(self.conn, row["decision_id"], outcome, reasons)
            # Commit per decision: an order may already rest at the broker.
            # A crash before the loop-end commit lost its ledger row and left
            # the decision PENDING for a restarted runner to place again.
            self.conn.commit()
            done.append(Acted(row["decision_id"], row["symbol"], row["ts_et"],
                              float(row["trigger"]), float(row["stop"]),
                              outcome, reasons))
        self.conn.commit()
        self.acted.extend(done)
        return done

    def _act(self, row) -> tuple[str, list[str]]:
        intent = intent_from_decision(row, self.dollar_risk)
        clock = decision_clock(row)
        reasons = refusals(intent, now=clock)

        if self.mode == "TRADE":
            age = (self.now() - clock).total_seconds()
            if age > self.max_age_s:
                reasons.append(f"decision is {age:.0f}s old; a stale plan is not "
                               f"the trade the cascade reviewed")
        # Pre-market is an exercise decision before it is an order decision:
        # phase C only, and only in the shape the probe verdict dictates.
        # LOG_ONLY records the refusal too, so phase A shows how many
        # pre-market plans the desk armed that the policy would have stopped.
        shape = "bracket"
        if intent.session == "premarket":
            state = L.get_state(self.conn)
            ok, why = premarket_allowed(state)
            if not ok:
                reasons.append(f"pre-market entry not allowed: {why}")
            else:
                shape = premarket_shape(state)
        if self.mode == "TRADE" and not self.entries_enabled:
            reasons.append("day locked by the risk gate — no new entries")
        if self.mode == "TRADE" and not row["volume_ok"]:
            # FILTERS.md Layer 2: pullback_volume < impulse_volume, all true at
            # entry. The detector computes it; nothing enforced it.
            reasons.append("Layer 2 not green: pullback volume was not lighter than the impulse")
        if self.mode == "TRADE" and row["verdict"] != "REVIEW":
            # FILTERS.md Layer 2: "Chart gates — all true at entry". The cascade
            # says REVIEW only when VWAP, 9 EMA and MACD are all green; WAIT is
            # a red chart gate, WATCH a gate it could not compute. LOG_ONLY
            # records those too, so the funnel shows how many pullbacks the
            # chart turned away.
            reasons.append(f"Layer 2 not green: verdict {row['verdict']} — chart gates must all "
                           f"be true at entry")
        if self.mode == "TRADE" and not reasons:
            # Alignment at the instant of the order. The decision was made on
            # the desk's tape; the order goes to a different session that may
            # see a different (or no) tape. The only alignment that can be
            # enforced here is that the desk's quote for THIS symbol is fresh
            # when the order leaves. `quote_source` returns None past 30s, so
            # a stalled desk cannot place an order on a price it no longer has.
            q = self.quote(intent.symbol) if self.quote else None
            if not q or q.get("bid") is None:
                reasons.append("no fresh desk quote for this symbol — decision and order "
                               "would not be on the same tape")
        if reasons:
            return "REFUSED", reasons
        if self.mode == "LOG_ONLY":
            return "LOG_ONLY", []

        try:
            if shape == "monitored":
                placed = self.trader.place_entry_monitored(intent)
            else:
                placed = self.trader.place_bracket(intent, now=clock)
        except OrderRefused as exc:
            return "REFUSED", list(exc.reasons)
        # RiskVeto and anything else propagates: a latched day or a dead
        # socket is not an outcome to record against one decision, it is the
        # end of the loop, and the caller must see it.
        L.record_order(
            self.conn, row["decision_id"], symbol=intent.symbol,
            account=self.trader.account or "",
            session=intent.session, parent_id=placed.parent_id,
            stop_id=placed.stop_id, target_id=placed.target_id,
            trigger=intent.trigger, stop=intent.stop, target=intent.target,
            shares=intent.shares, dollar_risk=self.dollar_risk,
            protected=placed.protected)
        return "TAKEN", []

    # ------------------------------------------------------------- fills
    def sync_fills(self) -> int:
        """TRADE only. Pull fills from IBKR and write realised R + NBBO."""
        if self.mode != "TRADE":
            return 0
        n = 0
        self.trader.sync()
        by_parent = {p.parent_id: p for p in self.trader.placed}
        for r in self.conn.execute("SELECT order_id, parent_id FROM orders WHERE perm_id IS NULL").fetchall():
            p = by_parent.get(r["parent_id"])
            if p is not None and p.perm_id:
                L.set_perm_id(self.conn, r["order_id"], p.perm_id)
        rows = self.conn.execute(
            "SELECT order_id, parent_id, decision_id FROM orders WHERE fill_price IS NULL").fetchall()
        for r in rows:
            p = by_parent.get(r["parent_id"])
            if p is None or p.fill_price is None:
                continue
            if p.filled_qty is not None:
                L.set_filled_qty(self.conn, r["order_id"], p.filled_qty)
            # NBBO is asked for AT THE MOMENT the fill is seen. Later is wrong
            # and earlier is impossible; the gap between fill and this call is
            # itself recorded through the two timestamps.
            nbbo = self.quote(p.symbol) if self.quote else None
            L.record_fill(self.conn, r["order_id"], fill_price=p.fill_price,
                          fill_ts=p.fill_time or self.now(), nbbo=nbbo,
                          status=p.status, stop_status=p.stop_status,
                          protected=p.protected)
            n += 1
        # Exits: a filled stop or target leg closes the trade in the ledger.
        for r in self.conn.execute("SELECT order_id, parent_id FROM orders WHERE fill_price IS NOT NULL "
                                   "AND exit_ts IS NULL").fetchall():
            p = by_parent.get(r["parent_id"])
            if p is not None and p.exit_price is not None and p.exit_confirmed:
                L.record_exit(self.conn, r["order_id"], reason=p.exit_reason or "bracket",
                              price=p.exit_price, ts=p.exit_time or self.now())
                n += 1
        # Partial fills on a filled row, and exits that were sent earlier
        # (monitored stop, flatten) and have now been reported filled.
        for r in self.conn.execute("SELECT order_id, parent_id, filled_qty FROM orders "
                                   "WHERE fill_price IS NOT NULL").fetchall():
            p = by_parent.get(r["parent_id"])
            if p is not None and p.filled_qty is not None and r["filled_qty"] != p.filled_qty:
                L.set_filled_qty(self.conn, r["order_id"], p.filled_qty)
        for r in L.pending_exits(self.conn):
            p = by_parent.get(r["parent_id"])
            if p is not None and p.exit_confirmed and p.exit_price is not None:
                L.confirm_exit(self.conn, r["order_id"], price=p.exit_price,
                               ts=p.exit_time or self.now())
                L.add_order_event(self.conn, r["order_id"],
                                  f"exit confirmed filled at {p.exit_price}")
                n += 1
        self.conn.commit()
        return n

    def reconcile_unfilled(self) -> list[int]:
        """At the hard stop: every entry that never filled is NOT_FILLED, not
        TAKEN. The actuals still score it — the one that never filled is a
        measurement too — but the funnel must not count it as a trade."""
        done = []
        for r in L.open_orders(self.conn):
            if r["fill_price"] is None:
                L.mark_not_filled(self.conn, r["order_id"])
                done.append(r["order_id"])
        self.conn.commit()
        return done

    # ------------------------------------------------- the monitored stop
    def watch_stops(self, offset: float = 0.10) -> list[str]:
        """TRADE only. For every filled position with no resting stop, exit at
        bid − offset the moment the bid touches the stop.

        This IS the stop for a `queued`-verdict pre-market entry, and it only
        exists while this process runs — `PlacedOrder.protected` is False for
        exactly that reason. A missing or stale quote is recorded as an
        event and acted on by doing nothing; guessing a price to sell at is
        worse than one more loop of exposure, and the operator can read the
        gap in the events.
        """
        if self.mode != "TRADE":
            return []
        done: list[str] = []
        for o in L.open_monitored(self.conn):
            q = self.quote(o["symbol"]) if self.quote else None
            if not q or q.get("bid") is None:
                L.add_order_event(self.conn, o["order_id"], "watch_stops: no fresh quote; held")
                continue
            bid = float(q["bid"])
            if bid > o["stop"]:
                continue
            # Sell what was filled, not what was asked for: a partial fill
            # sold at `shares` would leave the book short the difference.
            qty = int(o["filled_qty"]) if o["filled_qty"] else int(o["shares"])
            px = self.trader.exit_limit(o["symbol"], qty, bid, offset=offset,
                                        outside_rth=True)
            exit_id = getattr(self.trader, "last_exit_order_id", None)
            # Sent, not filled: ExitPending until sync_fills reads the fill.
            L.record_exit(self.conn, o["order_id"], reason="monitored_stop", price=px,
                          ts=self.now(), confirmed=False, exit_order_id=exit_id)
            self._mark_exit_sent(o["parent_id"], exit_id)
            L.add_order_event(self.conn, o["order_id"],
                              f"watch_stops: bid {bid} <= stop {o['stop']}; SELL LMT {px} x{qty} sent "
                              f"(order {exit_id}); fill not yet confirmed")
            done.append(f"{o['symbol']} x{qty} SELL LMT {px} (bid {bid} <= stop {o['stop']})")
        self.conn.commit()
        return done

    def _mark_exit_sent(self, parent_id, exit_id) -> None:
        for p in getattr(self.trader, "placed", []):
            if p.parent_id == parent_id:
                p.exit_order_id = exit_id
                p.exit_confirmed = False

    # -------------------------------------------------------- after 16:00
    def flag_after_hours(self) -> list[int]:
        """Anything still held after the close is flagged, never acted on.

        docs/paper-exercise-brief.md R10. An after-hours continuation is
        exit-only and requires a human to confirm each one — the corpus has
        him measured not net profitable there, with no stops and margin
        auto-liquidated at 16:00. So this method changes a status and writes
        an event; the sell happens only through `exercise.py ah-exit --confirm`,
        which records who confirmed. A runner that could decide this alone
        would be the bot the brief says not to build.
        """
        if self.mode != "TRADE":
            return []
        if self.now().astimezone(ET).time() < REGULAR_END:
            return []
        flagged = []
        for o in L.stuck_orders(self.conn):
            L.flag_manual(self.conn, o["order_id"],
                          f"after 16:00 ET with {o['shares']} {o['symbol']} still held — "
                          f"AH exit needs a human: exercise.py ah-exit {o['order_id']} --confirm")
            flagged.append(o["order_id"])
        self.conn.commit()
        return flagged

    # ------------------------------------------------------- end of day
    def end_of_day(self) -> list[str]:
        """No trade alive. TRADE only: cancel everything, exit everything.

        Called at the hard stop. After-hours continuation is NOT decided
        here — `docs/paper-exercise-brief.md` R10: it is exit-only, requires
        a human to confirm each time, and is logged as an exception. A runner
        that could decide it alone would be the bot the brief says not to
        build.
        """
        if self.mode != "TRADE":
            return []
        done = self.trader.flatten_all(quote=lambda s: _bid_ask(self.quote, s),
                                       now=self.now())
        # Every sell the flatten sent is recorded against the position it
        # closes, as ExitPending. Until now the flatten left the ledger's
        # rows open: the position was gone at the broker and 'stuck' here.
        sent = {f["symbol"]: f for f in getattr(self.trader, "last_flatten", []) or []}
        for o in L.stuck_orders(self.conn):
            if o["status"] == "ExitPending":
                continue
            f = sent.get(o["symbol"])
            if f is None:
                continue
            L.record_exit(self.conn, o["order_id"], reason="hard_stop", price=f.get("price"),
                          ts=self.now(), confirmed=False, exit_order_id=f.get("order_id"))
            self._mark_exit_sent(o["parent_id"], f.get("order_id"))
            L.add_order_event(self.conn, o["order_id"],
                              f"hard stop: SELL {f['type']} x{f['qty']} sent (order {f.get('order_id')}); "
                              f"fill not yet confirmed")
        self.reconcile_unfilled()
        self.conn.commit()
        return done


def _bid_ask(quote: Optional[Quote], symbol: str) -> tuple[float, float]:
    q = quote(symbol) if quote else None
    if not q or q.get("bid") is None:
        raise RuntimeError(f"no quote for {symbol}; cannot price an extended-hours exit")
    return float(q["bid"]), float(q.get("ask") or q["bid"])
