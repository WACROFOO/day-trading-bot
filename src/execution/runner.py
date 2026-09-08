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
        self.startup_notes: list[str] = []
        # docs/preregistration.md §2: one name at a time. Counted from the
        # ledger — resting, filled, exit pending, or an unresolved intent.
        self.max_positions = 1
        self.rules_hash, self.code_commit = _versions()
        # Entries and exits are separate switches. A risk-gate lock closes
        # entries for the day; the exit side (fill sync, monitored stops, the
        # hard-stop flatten) must keep running in TRADE mode.
        self.entries_enabled = True
        if self.mode == "TRADE":
            # An intent whose acknowledgement was never saved is matched at the
            # broker by orderRef, or marked UNRESOLVED. Never resent.
            for line in self.reconcile_intents():
                self.startup_notes.append(line)
            # Whatever the ledger says is still alive at the broker is ours to
            # track from the first loop, restart or not.
            adopted = self.trader.adopt(L.open_orders(self.conn))
            if adopted:
                self.startup_notes.append(f"adopted {adopted} open order(s) from the ledger")

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
        if str(row["data_status"] or "").endswith("-backfill"):
            # Armed on loaded history with inputs from later. Diagnostic
            # cohort only: not prospective evidence, never an order (audit F3).
            reasons.append("backfill decision: armed on loaded history, inputs not point-in-time")
        if self.mode == "TRADE":
            # The phase gate at the execution boundary, not only in the day
            # command: `exercise.py live --trade` in phase A must place nothing
            # (review round 2). Pre-market has its own check below.
            phase = L.get_state(self.conn).get("phase", "A")
            if phase not in ("B", "C"):
                reasons.append(f"phase {phase}: log only — entries start in phase B "
                               f"(docs/preregistration.md §3; exercise.py advance)")
        if self.mode == "TRADE" and not self.entries_enabled:
            reasons.append("day locked by the risk gate — no new entries")
        if self.mode == "TRADE" and L.positions_alive(self.conn) >= self.max_positions:
            reasons.append(f"one position at a time (preregistration §2): "
                           f"{L.positions_alive(self.conn)} order(s) alive or unresolved")
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

        # The intent is durable BEFORE the send (audit F4). The decision is
        # CLAIMED and an orders row exists with status 'intent'; a crash
        # between here and the acknowledgement leaves exactly that, and the
        # next start reconciles it by orderRef instead of placing it again.
        oid = L.record_intent(
            self.conn, row["decision_id"], symbol=intent.symbol, session=intent.session,
            trigger=intent.trigger, stop=intent.stop, target=intent.target,
            shares=intent.shares, dollar_risk=self.dollar_risk,
            rules_hash=self.rules_hash, code_commit=self.code_commit)
        self.conn.commit()
        try:
            if shape == "monitored":
                placed = self.trader.place_entry_monitored(intent)
            else:
                placed = self.trader.place_bracket(intent, now=clock)
        except OrderRefused as exc:
            # Nothing was sent: the trader refuses before it touches the socket.
            self.conn.execute("UPDATE orders SET status='Refused', updated_at=? WHERE order_id=?",
                              (L._now(), oid))
            L.add_order_event(self.conn, oid, "refused by the trader before sending: "
                              + "; ".join(exc.reasons))
            return "REFUSED", list(exc.reasons)
        except Exception as exc:                        # noqa: BLE001
            # The send may or may not have reached the broker. The row stays
            # 'intent' and the decision CLAIMED; reconcile_intents() decides.
            L.add_order_event(self.conn, oid, f"send raised {exc!r} — acknowledgement unknown; "
                              f"reconciled by orderRef on the next start, never resent")
            self.conn.commit()
            raise
        # RiskVeto and anything else propagates: a latched day or a dead
        # socket is not an outcome to record against one decision, it is the
        # end of the loop, and the caller must see it.
        L.set_order_ids(
            self.conn, oid, parent_id=placed.parent_id, stop_id=placed.stop_id,
            target_id=placed.target_id, account=self.trader.account or "",
            protected=placed.protected, status="submitted",
            perm_id=getattr(placed, "perm_id", None))
        return "TAKEN", []

    # ------------------------------------------------------ reconciliation
    def reconcile_intents(self) -> list[str]:
        """Intents whose acknowledgement was never saved: find them at the
        broker by orderRef (the decision_id on every leg) or mark UNRESOLVED.
        Nothing here sends anything."""
        out: list[str] = []
        rows = L.intents(self.conn)
        if not rows:
            return out
        ib = getattr(self.trader, "ib", None)
        trades = list(ib.trades()) if ib is not None and hasattr(ib, "trades") else []
        for r in rows:
            legs = [t for t in trades if getattr(t.order, "orderRef", "") == r["decision_id"]]
            parent = next((t for t in legs if t.order.action == "BUY"), None)
            if parent is None:
                L.mark_unresolved(self.conn, r["order_id"],
                                  "intent recorded, acknowledgement never saved, and no order with "
                                  "this reference at the broker — NOT resent; check the broker by hand")
                out.append(f"UNRESOLVED intent #{r['order_id']} {r['symbol']} — not at the broker; "
                           f"blocks new entries until a human clears it")
                continue
            stop = next((t for t in legs if t.order.action == "SELL"
                         and t.order.orderType == "STP"), None)
            target = next((t for t in legs if t.order.action == "SELL"
                           and t.order.orderType == "LMT"), None)
            L.set_order_ids(self.conn, r["order_id"], parent_id=parent.order.orderId,
                            stop_id=stop.order.orderId if stop else None,
                            target_id=target.order.orderId if target else None,
                            account=self.trader.account or "", protected=stop is not None,
                            status=parent.orderStatus.status,
                            perm_id=getattr(parent.order, "permId", None) or None)
            L.set_outcome(self.conn, r["decision_id"], "TAKEN", [])
            L.add_order_event(self.conn, r["order_id"],
                              f"reconciled by orderRef after a restart: parent {parent.order.orderId}, "
                              f"stop {stop.order.orderId if stop else 'NONE'}")
            out.append(f"reconciled intent #{r['order_id']} {r['symbol']} by orderRef "
                       f"(stop {'present' if stop else 'MISSING'})")
        self.conn.commit()
        return out

    def reconcile_positions(self) -> list[str]:
        """Broker positions against the ledger's exits. A long the broker holds
        that no ledger row covers, or that has no working exit (a resting stop,
        a monitored stop, or a sell already sent), is flagged for a human.
        Read-only against the broker; it sends nothing."""
        if self.mode != "TRADE":
            return []
        ib = getattr(self.trader, "ib", None)
        if ib is None or not hasattr(ib, "positions"):
            return []
        out: list[str] = []
        working = ("Submitted", "PreSubmitted", "monitored")
        for pos in ib.positions():
            qty = int(getattr(pos, "position", 0) or 0)
            if qty <= 0:
                continue
            sym = pos.contract.symbol
            rows = self.conn.execute(
                "SELECT * FROM orders WHERE symbol=? AND fill_price IS NOT NULL "
                "AND (exit_ts IS NULL OR status IN ('ExitPending','ExitFailed')) "
                "AND status NOT IN ('Cancelled','ApiCancelled','Closed','NotFilled')", (sym,)).fetchall()
            if not rows:
                out.append(f"UNTRACKED position {sym} x{qty} at the broker — no ledger row; "
                           f"exit by hand (exercise.py stuck)")
                continue
            covered = sum(int(r["filled_qty"] or r["shares"]) for r in rows)
            if covered != qty:
                for r in rows:
                    L.add_order_event(self.conn, r["order_id"],
                                      f"quantity mismatch: broker holds {qty}, ledger covers {covered}")
                out.append(f"QUANTITY MISMATCH {sym}: broker {qty}, ledger {covered}")
            for r in rows:
                has_exit = (r["status"] == "ExitPending"
                            or (r["stop_status"] or "") in working)
                if r["status"] == "ExitFailed":
                    out.append(f"EXIT FAILED {sym} x{qty} (order #{r['order_id']}) — held, needs a human")
                    continue                          # already flagged by exit_failed
                if not has_exit:
                    L.flag_manual(self.conn, r["order_id"],
                                  f"position {sym} x{qty} at the broker with no working exit "
                                  f"(stop status {r['stop_status']!r}) — a human must place one")
                    out.append(f"NO WORKING EXIT {sym} x{qty} (order #{r['order_id']})")
        self.conn.commit()
        return out

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
            # NBBO in force at the broker's execution time, from the desk's
            # time-indexed quote ticks (audit 2026-09-08: the poll that notices
            # a fill can lag it by a loop). The poll-time quote is the fallback
            # and says so in nbbo_source.
            nbbo = L.nbbo_at(self.conn, p.symbol, p.fill_time) if p.fill_time else None
            if nbbo is None:
                nbbo = self.quote(p.symbol) if self.quote else None
                if nbbo:
                    nbbo = {**nbbo, "source": "poll"}
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
        # Filled rows: the CURRENT state of the stop leg, a later partial fill
        # that moved the average price or the quantity, and exits sent earlier
        # (monitored stop, flatten) now reported filled — or dead.
        for r in self.conn.execute("SELECT order_id, parent_id, filled_qty, fill_price, stop_status, status "
                                   "FROM orders WHERE fill_price IS NOT NULL "
                                   "AND status NOT IN ('Closed','Cancelled','ApiCancelled','NotFilled')").fetchall():
            p = by_parent.get(r["parent_id"])
            if p is None:
                continue
            if p.fill_price is not None and (r["fill_price"] != p.fill_price
                                             or (p.filled_qty is not None and r["filled_qty"] != p.filled_qty)):
                if L.refresh_fill(self.conn, r["order_id"], fill_price=p.fill_price, filled_qty=p.filled_qty):
                    n += 1
            if p.stop_id and p.stop_status and r["stop_status"] not in (L.MANUAL, "monitored"):
                if L.set_protection(self.conn, r["order_id"], stop_status=p.stop_status,
                                    protected=bool(p.protected)):
                    n += 1
        for r in L.pending_exits(self.conn):
            p = by_parent.get(r["parent_id"])
            if p is None:
                continue
            if p.exit_confirmed and p.exit_price is not None:
                L.confirm_exit(self.conn, r["order_id"], price=p.exit_price,
                               ts=p.exit_time or self.now())
                L.add_order_event(self.conn, r["order_id"],
                                  f"exit confirmed filled at {p.exit_price}")
                n += 1
            elif p.exit_status in ("Cancelled", "ApiCancelled", "Inactive", "Rejected"):
                # "Sent once" is not "still working" (review round 2). The row
                # is a held position again, flagged; nothing is resent by code.
                L.exit_failed(self.conn, r["order_id"], status=p.exit_status)
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


def _versions() -> tuple[Optional[str], Optional[str]]:
    """(rules hash, code commit) stamped on every intent and order, so a row
    can be tied to the configuration and code that produced it (audit F2)."""
    try:
        from momentum_platform import desk_profile as DP
        return DP.fingerprint().get("hash"), DP.build_commit()
    except Exception:                                   # noqa: BLE001
        return None, None


def _bid_ask(quote: Optional[Quote], symbol: str) -> tuple[float, float]:
    q = quote(symbol) if quote else None
    if not q or q.get("bid") is None:
        raise RuntimeError(f"no quote for {symbol}; cannot price an extended-hours exit")
    return float(q["bid"]), float(q.get("ask") or q["bid"])
