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
        rows = self.conn.execute(
            "SELECT order_id, parent_id, decision_id FROM orders WHERE fill_price IS NULL").fetchall()
        for r in rows:
            p = by_parent.get(r["parent_id"])
            if p is None or p.fill_price is None:
                continue
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
            if p is not None and p.exit_price is not None:
                L.record_exit(self.conn, r["order_id"], reason=p.exit_reason or "bracket",
                              price=p.exit_price, ts=p.exit_time or self.now())
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
            px = self.trader.exit_limit(o["symbol"], int(o["shares"]), bid, offset=offset,
                                        outside_rth=True)
            L.record_exit(self.conn, o["order_id"], reason="monitored_stop", price=px,
                          ts=self.now())
            L.add_order_event(self.conn, o["order_id"],
                              f"watch_stops: bid {bid} <= stop {o['stop']}; SELL LMT {px}")
            done.append(f"{o['symbol']} x{o['shares']} SELL LMT {px} (bid {bid} <= stop {o['stop']})")
        self.conn.commit()
        return done

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
        self.reconcile_unfilled()
        self.conn.commit()
        return done


def _bid_ask(quote: Optional[Quote], symbol: str) -> tuple[float, float]:
    q = quote(symbol) if quote else None
    if not q or q.get("bid") is None:
        raise RuntimeError(f"no quote for {symbol}; cannot price an extended-hours exit")
    return float(q["bid"]), float(q.get("ask") or q["bid"])
