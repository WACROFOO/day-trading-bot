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
from datetime import datetime, timedelta, timezone
from typing import Callable, NamedTuple, Optional

from journal import ledger as L

from .bridge import bar_seconds, decision_clock, intent_from_decision
from .intent import ENTRY_TTL_MINUTES, SPREAD_K, TRAIL_R, in_regular_hours
from .ibkr_trader import OrderRefused, PaperTrader
from .intent import ET, refusals

# The stop of last resort. WHLR 2026-09-23: the broker's stop rested at 7.34
# ("PreSubmitted") while the stock printed 7.05 at 09:58 and 6.99 at 10:28,
# and it did not execute for fifty minutes; only the restart's modify made it
# fire, at 7.31. A resting stop the tape has passed by this long is not a
# stop. The runner then cancels it and sells at market itself.
STOP_ENFORCE_SECONDS = 15.0
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
    backfill: bool = False      # armed on history loaded at the desk's start; diagnostic cohort

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
        # Broker state the ledger cannot account for (an untracked position, a
        # quantity mismatch). Set by reconcile_positions; while non-empty no
        # new entry is placed (review 2026-09-21, item 13d): reconcile first,
        # order second, after every start and every reconnect.
        self.unreconciled: list[str] = []
        self.flat_confirmed: Optional[bool] = None
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
            # Broker positions and working orders against the ledger BEFORE
            # anything can be sent. Read-only.
            for line in self.reconcile_positions():
                self.startup_notes.append(line)

    # ------------------------------------------------------------- the loop
    def step(self) -> list["Acted"]:
        """Act on every pending decision once. Returns what was done."""
        done = []
        for row in L.pending(self.conn):
            self._clocks = None
            outcome, reasons = self._act(row)
            L.set_outcome(self.conn, row["decision_id"], outcome, reasons, clocks=self._clocks)
            # Commit per decision: an order may already rest at the broker.
            # A crash before the loop-end commit lost its ledger row and left
            # the decision PENDING for a restarted runner to place again.
            self.conn.commit()
            done.append(Acted(row["decision_id"], row["symbol"], row["ts_et"],
                              float(row["trigger"]), float(row["stop"]),
                              outcome, reasons,
                              str(row["data_status"] or "").endswith("-backfill")))
        self.conn.commit()
        self.acted.extend(done)
        return done

    def _act(self, row) -> tuple[str, list[str]]:
        cap = getattr(self.trader, "net_liq", None) if self.mode == "TRADE" else None
        intent = intent_from_decision(row, self.dollar_risk, max_notional=cap)
        clock = decision_clock(row)
        reasons = refusals(intent, now=clock)

        # Several clocks, each recorded, each named when it fails (review
        # 2026-09-21, item 12). bar_end = the age of the market information;
        # published = when the desk wrote the decision (recorded_at — the
        # rebuild that received the bar, so receipt and publication are one
        # clock here); runner_seen = now; quote_ts = the desk quote's own
        # stamp at the check. Freshly published backfill stays backfill: the
        # bar clock is the one the budget applies to, never the publication.
        now = self.now()
        bar_end = clock + timedelta(seconds=bar_seconds(row))
        published = _parse_ts(dict(row).get("recorded_at"))
        q0 = self.quote(intent.symbol) if self.quote else None
        self._clocks = {
            "bar_end": bar_end.isoformat(timespec="seconds"),
            "published": published.isoformat(timespec="seconds") if published else None,
            "runner_seen": now.isoformat(timespec="seconds"),
            "quote_ts": (q0 or {}).get("ts"),
            "bar_to_published_s": round((published - bar_end).total_seconds()) if published else None,
            "published_to_seen_s": round((now - published).total_seconds()) if published else None,
        }
        if self.mode == "TRADE":
            # Age from the bar's CLOSE, not its open (clarification C1,
            # docs/preregistration.md §5). A 1-minute decision cannot exist
            # before its bar has closed, so measuring from the open charged
            # every plan 60 s it never had: a plan seen 70 s after the close
            # read as 130 s old and was refused (GRML, 2026-09-21 07:43).
            age = (now - bar_end).total_seconds()
            if age > self.max_age_s:
                c = self._clocks
                detail = (f" (bar close → published {c['bar_to_published_s']}s, published → runner "
                          f"{c['published_to_seen_s']}s)" if published else "")
                reasons.append(f"bar clock: the bar closed {age:.0f}s before the runner saw it "
                               f"(budget {self.max_age_s}s); a stale plan is not the trade the "
                               f"cascade reviewed{detail}")
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
            reasons.append("backfill decision: armed on loaded history, inputs not point-in-time "
                           "(bar clock: the bar predates the desk's start; a fresh publication "
                           "time does not make it fresh)")
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
        if self.mode == "TRADE" and self.unreconciled:
            reasons.append("broker state not reconciled with the ledger — no new entries until a "
                           "human clears it: " + "; ".join(self.unreconciled)[:160])
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
            q = q0
            if not q or q.get("bid") is None:
                reasons.append("quote clock: no fresh desk quote for this symbol (older than the "
                               "30 s bound, or none) — the execution price is not current and the "
                               "decision and order would not be on the same tape")
            elif q.get("ask") is not None and q["ask"] > q["bid"]:
                # Amendment A6: the stop must clear the spread by SPREAD_K or
                # the round trip costs more than the trade can pay. Measured
                # in Phase 0 of the 10-second study; the 1-minute path had no
                # such gate, and VEEE's 2-cent stop went to the broker.
                spread = round(q["ask"] - q["bid"], 4)
                if intent.risk_per_share < SPREAD_K * spread:
                    reasons.append(f"stop ${intent.risk_per_share:.2f}/sh is inside {SPREAD_K:g}x "
                                   f"the spread (${spread:.2f}) — the round trip would eat the trade (A6)")
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
        out: list[str] = []
        # Every filled share needs its protective exit (item 13c): a stop leg
        # covering fewer shares than were filled is flagged from the ledger
        # alone, before the broker is consulted.
        for r in L.exit_quantity_gaps(self.conn):
            L.add_order_event(self.conn, r["order_id"],
                              f"stop leg covers {r['stop_qty']:g} of {r['filled_qty']:g} filled shares")
            out.append(f"STOP COVERS {r['stop_qty']:g} OF {r['filled_qty']:g} {r['symbol']} "
                       f"(order #{r['order_id']}) — the uncovered shares have no exit")
        ib = getattr(self.trader, "ib", None)
        if ib is None or not hasattr(ib, "positions"):
            self.conn.commit()
            self.unreconciled = [x for x in out if x.startswith("STOP COVERS")]
            return out
        out += self._resolve_gone_entries(ib)
        working = ("Submitted", "PreSubmitted", "monitored", "Triggered")
        for pos in ib.positions():
            qty = int(getattr(pos, "position", 0) or 0)
            if qty <= 0:
                continue
            sym = pos.contract.symbol
            rows = self.conn.execute(
                "SELECT * FROM orders WHERE symbol=? AND fill_price IS NOT NULL "
                "AND (exit_ts IS NULL OR status IN ('ExitPending','ExitFailed')) "
                "AND status NOT IN ('Cancelled','ApiCancelled','Inactive','Closed','NotFilled')", (sym,)).fetchall()
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
                if (r["stop_status"] or "") == "Triggered":
                    out.append(f"STOP TRIGGERED {sym} x{qty} (order #{r['order_id']}) — the broker reports the stop "
                               f"triggered but the position is still held: a sell is in flight (a halted name fills "
                               f"on resume). If the name is trading and this line persists, a human sells: "
                               f"exercise.py ah-exit {r['order_id']} --confirm --market")
                    continue
                if r["status"] == "ExitFailed":
                    cover = (f"stop {r['stop_id']} resting" if r["protected"] and (r["stop_status"] or "") in working
                             else "NO stop")
                    out.append(f"EXIT FAILED {sym} x{qty} (order #{r['order_id']}) — held, {cover}; "
                               f"a human sells it: exercise.py ah-exit {r['order_id']} --confirm --market")
                    continue                          # already flagged by exit_failed
                if not has_exit:
                    L.flag_manual(self.conn, r["order_id"],
                                  f"position {sym} x{qty} at the broker with no working exit "
                                  f"(stop status {r['stop_status']!r}) — a human must place one")
                    out.append(f"NO WORKING EXIT {sym} x{qty} (order #{r['order_id']})")
        self.conn.commit()
        self.unreconciled = [x for x in out if x.split(" ")[0] in ("UNTRACKED", "QUANTITY", "STOP")]
        return out

    def _resolve_gone_entries(self, ib) -> list[str]:
        """An unfilled entry the ledger still calls alive that the broker no
        longer reports anywhere — not among its orders, not in today's
        executions, no position in the name — is dead. After a restart IBKR
        re-reports working orders and today's fills; a rejected or expired
        order is in neither, and until 2026-09-21 such a row stayed alive in
        the ledger for the rest of the session."""
        out: list[str] = []
        try:
            trades = list(ib.trades())
        except Exception:                                   # noqa: BLE001
            return out
        ids = {t.order.orderId for t in trades if getattr(t.order, "orderId", 0)}
        perms = {getattr(t.order, "permId", 0) for t in trades}
        refs = {getattr(t.order, "orderRef", "") for t in trades}
        fills = []
        if hasattr(ib, "fills"):
            try:
                fills = list(ib.fills())
            except Exception:                               # noqa: BLE001
                fills = []
        fill_perms = {getattr(getattr(f, "execution", None), "permId", 0) for f in fills}
        fill_refs = {getattr(getattr(f, "execution", None), "orderRef", "") for f in fills}
        held = {p.contract.symbol for p in ib.positions() if int(getattr(p, "position", 0) or 0) > 0}
        for r in L.open_orders(self.conn):
            if r["fill_price"] is not None or not r["parent_id"]:
                continue
            at_broker = (r["parent_id"] in ids or (r["perm_id"] and r["perm_id"] in perms)
                         or r["decision_id"] in refs or r["decision_id"] in fill_refs
                         or (r["perm_id"] and r["perm_id"] in fill_perms))
            if at_broker or r["symbol"] in held:
                continue
            L.mark_dead(self.conn, r["order_id"], "NotFilled",
                        "not reported by the broker (no order, no execution, no position) — "
                        "treated as never filled; it no longer counts as a live position")
            out.append(f"GONE AT BROKER {r['symbol']} order #{r['order_id']} — marked NotFilled")
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
        # The stop leg's quantity, from the broker, on every row it is known for.
        for r in self.conn.execute("SELECT order_id, parent_id, stop_qty FROM orders "
                                   "WHERE stop_id IS NOT NULL AND exit_ts IS NULL").fetchall():
            p = by_parent.get(r["parent_id"])
            if p is not None and p.stop_qty is not None and p.stop_qty != r["stop_qty"]:
                L.set_stop_qty(self.conn, r["order_id"], p.stop_qty)
        rows = self.conn.execute(
            "SELECT order_id, parent_id, decision_id, status FROM orders WHERE fill_price IS NULL").fetchall()
        for r in rows:
            p = by_parent.get(r["parent_id"])
            if p is None:
                continue
            # The broker's word on an entry that never filled: rejected or
            # cancelled is dead, and the ledger must say so or the
            # one-position rule counts a ghost (VEEE, 2026-09-21 09:37).
            if p.fill_price is None and p.status in L.DEAD_ENTRY_STATUSES \
                    and r["status"] not in L.DEAD_ENTRY_STATUSES + ("NotFilled",):
                L.mark_dead(self.conn, r["order_id"], p.status,
                            f"entry {p.status} at the broker before any fill — not a position")
                n += 1
                continue
            if p.fill_price is None:
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
        # An ExitFailed row is still held; the fresh stop `reprotect` placed
        # for it is a bracket leg like any other, and its fill closes the row.
        for r in self.conn.execute("SELECT order_id, parent_id FROM orders WHERE fill_price IS NOT NULL "
                                   "AND (exit_ts IS NULL OR status='ExitFailed')").fetchall():
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
                                   "AND status NOT IN ('Closed','Cancelled','ApiCancelled','Inactive','NotFilled')").fetchall():
            p = by_parent.get(r["parent_id"])
            if p is None:
                continue
            if p.fill_price is not None and (r["fill_price"] != p.fill_price
                                             or (p.filled_qty is not None and r["filled_qty"] != p.filled_qty)):
                if L.refresh_fill(self.conn, r["order_id"], fill_price=p.fill_price, filled_qty=p.filled_qty):
                    n += 1
            if p.stop_id and p.stop_status and r["stop_status"] not in (L.MANUAL, "monitored", "Triggered"):
                if L.set_protection(self.conn, r["order_id"], stop_status=p.stop_status,
                                    protected=bool(p.protected)):
                    n += 1
            # the broker's resting stop level, when sync read one (a fake broker
            # that reads none leaves the ledger's trail alone)
            if p.stop_id and getattr(p, "broker_stop_level", None) is not None:
                row_trail = self.conn.execute("SELECT trail_stop FROM orders WHERE order_id=?",
                                              (r["order_id"],)).fetchone()[0]
                if p.trail_stop is None and row_trail is not None:
                    self.conn.execute("UPDATE orders SET trail_stop=NULL, updated_at=? WHERE order_id=?",
                                      (L._now(), r["order_id"]))
                    L.add_order_event(self.conn, r["order_id"],
                                      f"trail level {row_trail} corrected to the initial stop: the broker's stop rests there")
                    n += 1
                elif p.trail_stop is not None and (row_trail is None or abs(p.trail_stop - row_trail) > 1e-9):
                    L.set_trail(self.conn, r["order_id"], trail_stop=p.trail_stop, high=None)
                    L.add_order_event(self.conn, r["order_id"],
                                      f"trail level {row_trail} corrected to {p.trail_stop}: the broker's resting level")
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

    # ------------------------------------------------- A10: an entry that did not trigger
    def expire_entries(self, ttl_minutes: int = ENTRY_TTL_MINUTES) -> list[str]:
        """TRADE only. A resting stop-limit entry the tape has not reached
        within `ttl_minutes` of being placed is cancelled and its decision
        reads NOT_FILLED: the break the plan waited for did not come, and a
        resting entry blocks every other name under the one-position rule."""
        if self.mode != "TRADE":
            return []
        done: list[str] = []
        now = self.now()
        for r in L.open_orders(self.conn):
            if r["fill_price"] is not None or not r["parent_id"]:
                continue
            if r["status"] in L.DEAD_ENTRY_STATUSES + ("NotFilled", "intent", "UNRESOLVED", "Filled"):
                continue
            try:
                placed = datetime.fromisoformat(str(r["placed_at"]).replace("Z", "+00:00"))
            except ValueError:
                continue
            if placed.tzinfo is None:
                placed = placed.replace(tzinfo=timezone.utc)
            age_min = (now - placed).total_seconds() / 60.0
            if age_min < ttl_minutes:
                continue
            if hasattr(self.trader, "cancel_order_id"):
                try:
                    self.trader.cancel_order_id(int(r["parent_id"]))
                except Exception as exc:                        # noqa: BLE001
                    L.add_order_event(self.conn, r["order_id"], f"expire_entries: cancel raised {exc!r}; left to the broker")
                    continue
            L.mark_dead(self.conn, r["order_id"], "Cancelled",
                        f"entry not triggered within {ttl_minutes} minutes of placing (A10): cancelled by the runner; "
                        f"the plan's break at {r['trigger']} did not come")
            for p in getattr(self.trader, "placed", []):
                if p.parent_id == r["parent_id"]:
                    p.status = "Cancelled"
                    p.events.append(f"entry expired after {ttl_minutes} min untriggered (A10)")
            done.append(f"{r['symbol']} entry {r['trigger']:.2f} not reached in {ttl_minutes} min — cancelled, NOT_FILLED")
        self.conn.commit()
        return done

    # ------------------------------------------------- the stop of last resort
    def enforce_stops(self, seconds: float = STOP_ENFORCE_SECONDS) -> list[str]:
        """TRADE only. A resting stop whose level the desk's bid has been
        below for `seconds` without the broker filling it has failed. The
        runner cancels that leg and sells at market (regular hours) or at
        bid − 0.10 (extended hours). Recorded as exit reason `stop_enforced`,
        ExitPending until the fill is read. A stale or missing quote does
        nothing: one more loop of exposure beats a sale at a guessed price."""
        if self.mode != "TRADE":
            return []
        below = getattr(self, "_below_since", None)
        if below is None:
            below = self._below_since = {}
        done: list[str] = []
        now = self.now()
        for o in L.open_protected(self.conn):
            # a leg whose status was never read back ("") is still a resting
            # stop the ledger relies on; only a human-flagged or monitored row is skipped
            if (o["stop_status"] or "") not in ("", "Submitted", "PreSubmitted", "Triggered"):
                continue
            level = max(float(o["stop"]), float(o["trail_stop"] or 0.0))
            q = self.quote(o["symbol"]) if self.quote else None
            if not q or q.get("bid") is None:
                continue
            bid = float(q["bid"])
            if bid > level - 0.01:
                below.pop(o["order_id"], None)
                continue
            since = below.setdefault(o["order_id"], now)
            held_for = (now - since).total_seconds()
            if held_for < seconds:
                continue
            qty = int(o["filled_qty"]) if o["filled_qty"] else int(o["shares"])
            if o["stop_id"] and hasattr(self.trader, "cancel_order_id"):
                try:
                    self.trader.cancel_order_id(int(o["stop_id"]))
                except Exception as exc:                        # noqa: BLE001
                    L.add_order_event(self.conn, o["order_id"], f"enforce_stops: cancelling stop leg {o['stop_id']} raised {exc!r}")
            if in_regular_hours(now) and hasattr(self.trader, "exit_market"):
                exit_id = self.trader.exit_market(o["symbol"], qty, now=now)
                px, how = None, "MKT"
            else:
                px = self.trader.exit_limit(o["symbol"], qty, bid, offset=0.10, outside_rth=True)
                exit_id = getattr(self.trader, "last_exit_order_id", None)
                how = f"LMT {px}"
            L.record_exit(self.conn, o["order_id"], reason="stop_enforced", price=px,
                          ts=now, confirmed=False, exit_order_id=exit_id)
            self._mark_exit_sent(o["parent_id"], exit_id)
            L.add_order_event(self.conn, o["order_id"],
                              f"enforce_stops: bid {bid} has been below the resting stop {level} for {held_for:.0f}s and the "
                              f"broker did not fill it; stop leg {o['stop_id']} cancelled, SELL {how} x{qty} sent (order {exit_id})")
            done.append(f"{o['symbol']} x{qty}: bid {bid:.2f} below the resting stop {level:.2f} for {held_for:.0f}s, "
                        f"no fill from the broker — stop cancelled, SELL {how} sent (order {exit_id})")
            below.pop(o["order_id"], None)
        self.conn.commit()
        return done

    # ------------------------------------------------- re-protection
    def reprotect(self) -> list[str]:
        """TRADE only. A filled position whose stop leg is dead (cancelled,
        rejected, flagged) gets a fresh stop from the runner at the level it
        should have — the trailed level if there is one, never below the
        initial stop — for the quantity actually held. Flagging alone left
        DCOY x41 without an exit for eleven minutes on 2026-09-22 while the
        runner printed NO WORKING EXIT every five seconds."""
        if self.mode != "TRADE" or not hasattr(self.trader, "place_stop"):
            return []
        done: list[str] = []
        by_parent = {p.parent_id: p for p in getattr(self.trader, "placed", [])}
        for o in L.unprotected_positions(self.conn):
            qty = int(o["filled_qty"]) if o["filled_qty"] else int(o["shares"])
            level = max(float(o["stop"]), float(o["trail_stop"] or 0.0))
            # The broker first: a stop the ledger lost track of may still rest
            # there (a refused modify shows as Cancelled for a moment, then
            # PreSubmitted again). A second stop under one position sells it
            # twice — the second fill is a short.
            resting = []
            if hasattr(self.trader, "working_stops"):
                try:
                    resting = self.trader.working_stops(o["symbol"])
                except Exception:                           # noqa: BLE001
                    resting = []
            if resting:
                sid, lvl, rq = resting[0]
                L.set_new_stop_leg(self.conn, o["order_id"], stop_id=sid, level=lvl, qty=rq)
                L.add_order_event(self.conn, o["order_id"],
                                  f"reprotect: a SELL stop already rests at the broker (order {sid} at {lvl} x{rq:g}); "
                                  f"adopted, none placed")
                rec = by_parent.get(o["parent_id"])
                if rec is not None:
                    rec.stop_id, rec.stop_status, rec.protected, rec.stop_qty = sid, "Submitted", True, float(rq)
                done.append(f"{o['symbol']} x{qty}: stop {sid} at {lvl:.2f} already resting at the broker — adopted, none placed")
                continue
            try:
                new_id = self.trader.place_stop(o["symbol"], qty, level, ref=o["decision_id"])
            except Exception as exc:                        # noqa: BLE001
                L.add_order_event(self.conn, o["order_id"],
                                  f"reprotect: placing a stop at {level} x{qty} raised {exc!r}; still unprotected")
                continue
            L.set_new_stop_leg(self.conn, o["order_id"], stop_id=new_id, level=level, qty=qty)
            rec = by_parent.get(o["parent_id"])
            if rec is not None:
                rec.stop_id, rec.stop_status, rec.protected, rec.stop_qty = new_id, "Submitted", True, float(qty)
                rec.events.append(f"re-protected: new stop {new_id} at {level} x{qty}")
            done.append(f"{o['symbol']} x{qty}: new stop {new_id} at {level:.2f} (old leg was {o['stop_status']})")
        self.conn.commit()
        return done

    # ------------------------------------------------- the trailing stop
    def trail_stops(self) -> list[str]:
        """TRADE only. Amendment A3: for every filled position whose stop rests
        at the broker, raise that stop to (high since the fill − TRAIL_R ×
        initial risk per share) whenever that is at least a cent above where
        it rests. Never down. The high comes from the desk's own tape in the
        ledger (10-second bars and quote ticks); with nothing written since
        the fill the stop stays put."""
        if self.mode != "TRADE":
            return []
        done: list[str] = []
        by_parent = {p.parent_id: p for p in getattr(self.trader, "placed", [])}
        for o in L.open_protected(self.conn):
            rps = round(float(o["trigger"]) - float(o["stop"]), 4)
            if rps <= 0:
                continue
            high = L.high_since(self.conn, o["symbol"], o["fill_ts"])
            if high is None:
                continue
            current = float(o["trail_stop"]) if o["trail_stop"] is not None else float(o["stop"])
            new = round(high - TRAIL_R * rps, 2)
            if high > float(o["high_since_fill"] or 0):
                L.set_trail(self.conn, o["order_id"], trail_stop=None, high=high)
            if new < current + 0.01:
                continue
            rec = by_parent.get(o["parent_id"])
            if rec is None:
                L.add_order_event(self.conn, o["order_id"],
                                  f"trail: high {high} would put the stop at {new}, but this process holds "
                                  f"no broker record for parent {o['parent_id']}; stop left at {current}")
                continue
            if (o["stop_status"] or "") == "Triggered":
                continue                                    # a sell in flight is not a resting stop to move
            try:
                self.trader.move_stop(rec, new)
            except Exception as exc:                        # noqa: BLE001
                triggered = bool(getattr(exc, "triggered", False))
                if triggered:
                    # IBKR: "Stop price revision is disallowed after order has
                    # triggered". The stop is a sell in flight (a halted name
                    # fills on resume). Stop moving it; reconcile watches it.
                    L.set_protection(self.conn, o["order_id"], stop_status="Triggered", protected=True)
                    rec.stop_status = "Triggered"
                    L.add_order_event(self.conn, o["order_id"],
                                      f"trail: move {current} -> {new} refused — the broker reports the stop TRIGGERED; "
                                      f"a sell is in flight at the resting level; no further moves")
                    done.append(f"{o['symbol']} stop TRIGGERED at the broker ({current:.2f}); sell in flight, "
                                f"no more trail moves — if the name is halted it fills on resume")
                else:
                    L.add_order_event(self.conn, o["order_id"],
                                      f"trail: move {current} -> {new} raised {exc!r}; stop left at {current}")
                continue
            L.set_trail(self.conn, o["order_id"], trail_stop=new, high=high)
            L.add_order_event(self.conn, o["order_id"],
                              f"trail (A3): high {high} since fill, stop {current} -> {new} (1R/sh = {rps})")
            done.append(f"{o['symbol']} stop {current:.2f} -> {new:.2f} (high {high:.2f}, 1R {rps:.2f})")
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
        # "Flat" is the broker's word, never the fact that a sell was sent
        # (item 13f). The market sells above may not have filled yet; the
        # loop keeps asking until positions() is empty.
        return done + self.confirm_flat()

    def confirm_flat(self) -> list[str]:
        """After the hard stop: what the broker still holds. Empty means flat,
        recorded once; anything else is NOT FLAT and is repeated every loop."""
        if self.mode != "TRADE" or not hasattr(self.trader, "positions_held"):
            return []
        held = self.trader.positions_held()
        if held:
            self.flat_confirmed = False
            return [f"NOT FLAT {sym} x{qty} — sell sent or missing, fill not seen; check the broker"
                    for sym, qty in held]
        if self.flat_confirmed is not True:
            self.flat_confirmed = True
            for o in L.pending_exits(self.conn):
                L.add_order_event(self.conn, o["order_id"], "flat confirmed from broker position state")
            self.conn.commit()
            return ["flat confirmed from broker position state"]
        return []


def _parse_ts(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


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
