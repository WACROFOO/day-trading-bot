#!/usr/bin/env python3
"""Follow the bot live, from its ledger: every plan the desk arms and what
became of it, every order, fill, exit and stop event, as they are written.

Why it exists (2026-10-01). The day's log (`~/Library/Logs/day-trading-bot/
day.out.log` when the 06:55 job runs it, the terminal otherwise) prints only
what the EXECUTOR does — REFUSED, TAKEN, fills, exits. A plan the stock
filters kill (price under $2, pillars, still rising...) never reaches the
executor, so it never appears there; only the ledger has it. This prints
both, in time order, in plain words.

GREEN-RUN rows are setup S (the green-run continuation, addendum 2026-10-05):
the desk LOGS it on every closed 10-second candle and never trades it. One
line per pause: entry/stop and why, or which rule refused it. A shadow, not a
plan — nothing there was ever offered to the executor.

READ-ONLY: it opens the ledger read-only and never writes, sends or cancels
anything. Ctrl-C stops the watch, never the bot. Standard library only, so it
runs against any version of the repo:

    python3 scripts/watch.py                    # today, then follow
    python3 scripts/watch.py --history          # also the plans armed on history loaded at start
    python3 scripts/watch.py --day 2026-09-30   # a past day, printed once
    python3 scripts/watch.py --once             # today so far, no follow
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parents[1]
WORD = {"SUPPRESSED": "KILLED", "PENDING": "TO RUNNER", "CLAIMED": "SENDING", "TAKEN": "TAKEN",
        "REFUSED": "REFUSED", "NOT_FILLED": "NOT FILLED", "EXPIRED": "EXPIRED", "UNRESOLVED": "UNRESOLVED",
        "LOG_ONLY": "LOG ONLY"}
WHY = {"SUPPRESSED": "", "PENDING": "passed the stock filters — the executor decides",
       "CLAIMED": "order being sent", "TAKEN": "order sent", "NOT_FILLED": "the order never filled",
       "EXPIRED": "never acted on before the session ended", "LOG_ONLY": "logged only (no trading in this mode)",
       "UNRESOLVED": "order state unknown after a restart — a human must clear it"}


def default_db() -> Path:
    for cand in (os.environ.get("JOURNAL_DB"), "data/journal.sqlite", str(ROOT / "data" / "journal.sqlite")):
        if cand and Path(cand).exists():
            return Path(cand)
    return Path("data/journal.sqlite")


def connect_ro(path: Path) -> sqlite3.Connection:
    if not Path(path).exists():
        raise SystemExit(f"no ledger at {path} — run from ~/day-trading-bot or pass --db")
    try:
        conn = sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True, timeout=5)
        conn.execute("SELECT 1 FROM decisions LIMIT 1")
    except sqlite3.Error:
        conn = sqlite3.connect(str(path), timeout=5)          # still only SELECTs below
    conn.row_factory = sqlite3.Row
    return conn


def et_clock(iso, with_seconds: bool = True) -> str:
    """Any ISO timestamp -> ET wall clock. Naive is UTC (the ledger's _now())."""
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return str(iso or "")[11:19]
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ET).strftime("%H:%M:%S" if with_seconds else "%H:%M")


def _short(text: str, n: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def kill_reason(row) -> str:
    gate = row["killed_by"] or "?"
    try:
        gates = json.loads(row["gates_json"] or "[]")
    except ValueError:
        gates = []
    g = next((x for x in gates if isinstance(x, dict) and x.get("id") == gate), None)
    detail = (g or {}).get("reason") or (g or {}).get("value") or ""
    return f"{gate}: {detail}" if detail else gate


def refusal_text(row) -> str:
    try:
        reasons = json.loads(row["refusal_reasons_json"] or "[]")
    except ValueError:
        reasons = []
    return " · ".join(_short(r, 90) for r in reasons) or "?"


class Watcher:
    """Remembers what it has printed; each poll returns the new lines, in time order."""

    def __init__(self, conn: sqlite3.Connection, day: str, history: bool = False):
        self.conn, self.day, self.history = conn, day, history
        self.seen_decisions: dict[str, str] = {}
        self.seen_orders: dict[int, tuple] = {}
        self.seen_green: dict[tuple, str] = {}
        self.last_event = 0
        self.history_count = 0
        self.locked = None

    def _decision_line(self, row) -> str:
        out = row["outcome"] or "?"
        word = WORD.get(out, out)
        plan = f"{row['trigger']:.2f}/{row['stop']:.2f}" if row["trigger"] and row["stop"] else "—"
        if out == "SUPPRESSED":
            why = kill_reason(row)
        elif out == "REFUSED":
            why = refusal_text(row)
        else:
            why = WHY.get(out, "")
        tag = " [history]" if str(row["data_status"] or "").endswith("-backfill") else ""
        return f"{str(row['ts_et'])[11:16]:>8}  {row['symbol']:<6} {word:<10} {plan:>11}  {_short(why, 170)}{tag}"

    @staticmethod
    def _green_line(g) -> str:
        """Setup S, logged not traded: the levels and why, or the rule that refused it."""
        plan = f"{g['entry']:.2f}/{g['stop']:.2f}" if g["entry"] and g["stop"] else "—"
        if g["status"] == "SIGNAL":
            spread = f"${g['spread']:.3f} {g['spread_source']}" if g["spread"] is not None else "?"
            why = (f"green 1-min run (2 green, new high, > VWAP & 9 EMA, MACD > signal) + 10-s pause · "
                   f"stop = 1-min bar low, {g['stop_pct']:.1f}% · spread {spread} · SHADOW: no order")
            word = "GREEN-RUN"
        else:
            try:
                why = " · ".join(_short(r, 90) for r in json.loads(g["refusals_json"] or "[]")) or "?"
            except ValueError:
                why = "?"
            why = f"green run refused — {why}"
            word = "GR REFUSED"
        arms = f" [{g['n_arms']} closes]" if (g["n_arms"] or 1) > 1 else ""
        return f"{str(g['ts_et'])[11:16]:>8}  {g['symbol']:<6} {word:<10} {plan:>11}  {_short(why, 170)}{arms}"

    def _green(self) -> list[tuple[str, str]]:
        try:
            rows = self.conn.execute(
                "SELECT symbol, pause_id, ts_et, status, entry, stop, stop_pct, spread, spread_source, "
                "refusals_json, n_arms FROM green_run_signals WHERE substr(ts_et,1,10)=? ORDER BY ts_et",
                (self.day,)).fetchall()
        except sqlite3.OperationalError as exc:
            if "no such table" in str(exc):
                return []                          # a ledger from before the green-run log
            raise
        out = []
        for g in rows:
            key = (g["symbol"], g["pause_id"])
            if self.seen_green.get(key) == g["status"]:
                continue
            self.seen_green[key] = g["status"]
            out.append((str(g["ts_et"])[11:19], self._green_line(g)))
        return out

    def poll(self) -> list[tuple[str, str]]:
        """[(sort key, line)] for everything new since the last poll."""
        new: list[tuple[str, str]] = []
        rows = self.conn.execute(
            "SELECT decision_id, ts_et, symbol, verdict, killed_by, plan_allowed, gates_json, trigger, stop, "
            "outcome, refusal_reasons_json, data_status, recorded_at, acted_at FROM decisions "
            "WHERE substr(ts_et,1,10)=? ORDER BY ts_et", (self.day,)).fetchall()
        hist = 0
        for r in rows:
            backfill = str(r["data_status"] or "").endswith("-backfill")
            if backfill:
                hist += 1
                if not self.history:
                    continue
            prev = self.seen_decisions.get(r["decision_id"])
            if prev == r["outcome"]:
                continue
            self.seen_decisions[r["decision_id"]] = r["outcome"]
            # first sight sorts by the bar's minute; a later change by when it happened
            when = et_clock(r["acted_at"] or r["recorded_at"]) if prev is not None else str(r["ts_et"])[11:19]
            new.append((when, self._decision_line(r)))
        if hist > self.history_count and not self.history:
            new.append(("00:00:00", f"{'':>8}  {hist} plan(s) armed on history loaded at start — never traded"
                                    f" (--history lists them)"))
        self.history_count = hist
        for o in self.conn.execute(
                "SELECT o.order_id, o.symbol, o.status, o.shares, o.filled_qty, o.trigger, o.stop, o.fill_price, "
                "o.fill_ts, o.exit_price, o.exit_ts, o.exit_reason, o.planned_risk, o.placed_at FROM orders o "
                "JOIN decisions d USING(decision_id) WHERE substr(d.ts_et,1,10)=? ORDER BY o.order_id",
                (self.day,)).fetchall():
            state = (o["status"], o["fill_price"], o["exit_price"])
            prev = self.seen_orders.get(o["order_id"])
            if prev == state:
                continue
            self.seen_orders[o["order_id"]] = state
            qty = o["filled_qty"] or o["shares"]
            if o["fill_price"] and (prev is None or prev[1] != o["fill_price"]):
                new.append((et_clock(o["fill_ts"]), f"{et_clock(o['fill_ts']):>8}  {o['symbol']:<6} {'FILLED':<10} "
                            f"{qty:g} @ {o['fill_price']:.2f}  (trigger {o['trigger']:.2f}, stop {o['stop']:.2f})"))
            if o["exit_price"] and (prev is None or prev[2] != o["exit_price"] or prev[0] != o["status"]):
                if o["status"] == "ExitPending":
                    # SENT, not filled (AMOD 2026-10-02 08:25 printed a P&L for a
                    # sell that then filled 466 of 666): the limit is a plan.
                    new.append((et_clock(o["exit_ts"]), f"{et_clock(o['exit_ts']):>8}  {o['symbol']:<6} "
                                f"{'SELL SENT':<10} LMT {o['exit_price']:.2f} x{qty:g}  {o['exit_reason'] or ''}"
                                f" · waiting for the broker's fill"))
                else:
                    pnl = (o["exit_price"] - (o["fill_price"] or o["exit_price"])) * (qty or 0)
                    r = f" · {pnl / o['planned_risk']:+.2f} R" if o["planned_risk"] else ""
                    new.append((et_clock(o["exit_ts"]), f"{et_clock(o['exit_ts']):>8}  {o['symbol']:<6} {'EXIT':<10} "
                                f"@ {o['exit_price']:.2f}  {o['exit_reason'] or ''} · ${pnl:+.2f}{r}"))
            if not o["fill_price"] and o["status"] not in ("intent", "submitted", "Submitted", "PreSubmitted") \
                    and (prev is None or prev[0] != o["status"]):
                new.append((et_clock(o["placed_at"]), f"{et_clock(o['placed_at']):>8}  {o['symbol']:<6} "
                            f"{'ORDER':<10} {o['status']}"))
        for e in self.conn.execute(
                "SELECT e.id, e.ts, e.text, o.symbol FROM order_events e JOIN orders o USING(order_id) "
                "JOIN decisions d USING(decision_id) WHERE substr(d.ts_et,1,10)=? AND e.id > ? ORDER BY e.id",
                (self.day, self.last_event)).fetchall():
            self.last_event = max(self.last_event, e["id"])
            new.append((et_clock(e["ts"]), f"{et_clock(e['ts']):>8}  {e['symbol']:<6} {'event':<10} {_short(e['text'], 170)}"))
        new += self._green()
        lock = self.conn.execute("SELECT locked, reason FROM risk_day WHERE date=?", (self.day,)).fetchone()
        if lock and lock["locked"] and self.locked != lock["reason"]:
            self.locked = lock["reason"]
            new.append(("99:99:99", f"{'':>8}  DAY LOCKED — {lock['reason']} · no more entries today; exits continue"))
        return sorted(new, key=lambda x: x[0])

    def summary(self) -> str:
        c: dict[str, int] = {}
        for out in self.seen_decisions.values():
            c[out] = c.get(out, 0) + 1
        return (f"so far: {c.get('SUPPRESSED', 0)} killed by the stock filters · {c.get('REFUSED', 0)} refused by "
                f"the executor · {c.get('TAKEN', 0) + c.get('CLAIMED', 0)} sent · "
                f"{len([o for o in self.seen_orders.values() if o[1]])} filled · "
                f"{sum(1 for v in self.seen_green.values() if v == 'SIGNAL')} green-run signal(s) logged, never traded")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=None, help="ledger path (default: $JOURNAL_DB or data/journal.sqlite)")
    ap.add_argument("--day", help="ET date YYYY-MM-DD (default: today; a past day prints once)")
    ap.add_argument("--history", action="store_true", help="also list plans armed on history loaded at start")
    ap.add_argument("--once", action="store_true", help="print the day so far and exit")
    ap.add_argument("--every", type=float, default=3.0, help="seconds between polls (default 3)")
    args = ap.parse_args(argv)
    db = Path(args.db) if args.db else default_db()
    conn = connect_ro(db)
    today = datetime.now(ET).date().isoformat()
    day = args.day or today
    follow = not args.once and day == today
    w = Watcher(conn, day, history=args.history)
    print(f"WATCH · {day} · ledger {db} · read-only" + (" · following — Ctrl-C stops the watch, never the bot"
                                                         if follow else ""))
    print(f"{'ET':>8}  {'symbol':<6} {'what':<10} {'trig/stop':>11}  why")
    try:
        while True:
            try:
                for _, line in w.poll():
                    print(line, flush=True)
            except sqlite3.OperationalError as exc:              # the bot is mid-write: try again
                print(f"  (ledger busy: {exc}; retrying)", flush=True)
            if not follow:
                break
            time.sleep(args.every)
    except KeyboardInterrupt:
        pass
    print(w.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
