#!/usr/bin/env python3
"""Watch the bot's decisions live, in a second terminal tab — read-only.

The owner, 2026-10-09: "how to watch closely the bot execution decisions".
The day's terminal mixes the desk, the probes and the runner; this reads the
ledger the runner writes (data/journal.sqlite, opened READ-ONLY) and prints,
as they happen:

  ARMED     a plan the bot is waiting on: trigger / stop (stop as % of price)
  REFUSED   a plan the bot will not take, with the rule that refused it
  TAKEN     the bot sent the order
  NOT FILL  the entry never filled inside its window (A10), cancelled
  FILLED    the fill: price, shares, slippage against the trigger
  event     each step the bot took on an order (stop watch, trail, sell sent)
  EXIT      price, reason, R and dollars
  LOCK      the daily risk gate closed (no new entries today)

plus a status line every minute: positions held with their R now, today's R,
the lock. A plan the shadow strategies would take is marked `S6 ✓` / `S3 ✓`
(src/momentum_platform/shadow.py) — the bot's rules are not theirs.
Plans the cascade killed before the bot saw them (SUPPRESSED) are counted,
and listed only with --all.

    python3 scripts/watch_bot.py              # today, from the start of the day
    python3 scripts/watch_bot.py --all        # also every cascade kill
    python3 scripts/watch_bot.py --db PATH    # another ledger

Ctrl-C stops the watcher; it never touches the bot.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from momentum_platform.shadow import judge  # noqa: E402

ET = ZoneInfo("America/New_York")
DEFAULT_DB = ROOT / "data" / "journal.sqlite"
G, Y, R, D, B, X = "\033[92m", "\033[93m", "\033[91m", "\033[2m", "\033[1m", "\033[0m"
WORD = {"PENDING": ("ARMED", Y), "REFUSED": ("REFUSED", Y), "TAKEN": ("TAKEN", G), "LOG_ONLY": ("LOG ONLY", D),
        "NOT_FILLED": ("NOT FILL", D), "SUPPRESSED": ("KILLED", D)}


def connect(path: str) -> sqlite3.Connection:
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
    c.row_factory = sqlite3.Row
    return c


def _rows(c, q, args=()):
    try:
        return c.execute(q, args).fetchall()
    except sqlite3.OperationalError:                    # an older ledger without the table or column
        return []


def _hm(ts: str | None) -> str:
    if not ts:
        return "--:--:--"
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(ET).strftime("%H:%M:%S")
    except ValueError:
        return str(ts)[11:19]


def _first_reason(raw) -> str:
    try:
        reasons = json.loads(raw or "[]")
    except ValueError:
        reasons = [str(raw)]
    if not reasons:
        return ""
    more = f" (+{len(reasons) - 1} more)" if len(reasons) > 1 else ""
    return str(reasons[0]).split(" — ")[0][:150] + more


def _shadow_mark(d) -> str:
    if d["trigger"] is None or d["stop"] is None:
        return ""
    try:
        armed = datetime.fromisoformat(d["ts_et"]).time()
    except ValueError:
        return ""
    vwap = None
    try:
        vwap = (json.loads(d["chart_json"] or "{}") or {}).get("vwap") if "chart_json" in d.keys() else None
    except ValueError:
        vwap = None
    takes = [j["id"] for j in judge({"trigger": d["trigger"], "stop": d["stop"], "armed": armed, "last": d["last"],
                                     "vwap": vwap, "hod": d["session_high"],
                                     "volume_ok": None if d["volume_ok"] is None else bool(d["volume_ok"])})
             if j["takes"]]
    return ("  " + " ".join(f"\033[95m{t} ✓{X}" for t in takes)) if takes else ""


class Watcher:
    """Remembers what it printed; each poll prints only what changed."""

    def __init__(self, conn, day: str, show_all: bool = False, out=print):
        self.c, self.day, self.all, self.out = conn, day, show_all, out
        self.dec: dict = {}            # decision_id -> outcome printed
        self.orders: dict = {}         # order_id -> (placed, filled, exited) printed
        self.event_id = 0
        self.locked = None
        self.killed = 0

    def poll(self) -> int:
        n = 0
        for d in _rows(self.c, "SELECT * FROM decisions WHERE substr(ts_et,1,10)=? ORDER BY ts_et, rowid", (self.day,)):
            if str(d["data_status"] or "").endswith("-backfill"):
                continue
            oc = d["outcome"] or "PENDING"
            if self.dec.get(d["decision_id"]) == oc:
                continue
            first = d["decision_id"] not in self.dec
            self.dec[d["decision_id"]] = oc
            if oc == "SUPPRESSED":
                self.killed += first
                if not self.all:
                    continue
            word, col = WORD.get(oc, (oc, ""))
            plan = ""
            if d["trigger"] is not None and d["stop"] is not None and d["trigger"] > 0:
                pct = (d["trigger"] - d["stop"]) / d["trigger"] * 100
                plan = f"{d['trigger']:.2f}/{d['stop']:.2f} ({pct:.1f}%)"
            why = ""
            if oc == "REFUSED":
                why = "  ✗ " + _first_reason(d["refusal_reasons_json"])
            elif oc == "SUPPRESSED":
                why = f"  killed by {d['killed_by'] or 'the cascade'}"
            when = _hm(d["acted_at"]) if oc != "PENDING" and d["acted_at"] else d["ts_et"][11:19]
            self.out(f"{when}  {B}{d['symbol']:<6}{X} {col}{word:<9}{X} {plan:<22}{why}"
                     + (_shadow_mark(d) if oc in ("PENDING", "REFUSED", "TAKEN") else ""))
            n += 1
        for o in _rows(self.c, "SELECT * FROM orders WHERE substr(placed_at,1,10) >= ? ORDER BY order_id",
                       (self.day,)):
            seen = self.orders.get(o["order_id"], (False, False, False))
            placed, filled, exited = True, o["fill_price"] is not None, o["exit_ts"] is not None
            if not seen[0]:
                self.out(f"{_hm(o['placed_at'])}  {B}{o['symbol']:<6}{X} {G}SENT     {X} BUY x{o['shares']} trigger "
                         f"{o['trigger']:.2f} stop {o['stop']:.2f} · {o['session']} · order {o['order_id']}")
                n += 1
            if filled and not seen[1]:
                slip = (o["fill_price"] - o["trigger"]) if o["trigger"] else 0.0
                qty = o["filled_qty"] if "filled_qty" in o.keys() and o["filled_qty"] else o["shares"]
                self.out(f"{_hm(o['fill_ts'])}  {B}{o['symbol']:<6}{X} {G}FILLED   {X} {int(qty)} @ {o['fill_price']:.2f}"
                         f" · {slip * 100:+.0f}¢ vs the trigger")
                n += 1
            if exited and not seen[2] and o["exit_price"] is not None and o["fill_price"] is not None:
                rps = (o["trigger"] - o["stop"]) if o["trigger"] and o["stop"] else None
                qty = o["filled_qty"] if "filled_qty" in o.keys() and o["filled_qty"] else o["shares"]
                r = (o["exit_price"] - o["fill_price"]) / rps if rps else None
                usd = (o["exit_price"] - o["fill_price"]) * float(qty or 0)
                col = G if usd >= 0 else R
                self.out(f"{_hm(o['exit_ts'])}  {B}{o['symbol']:<6}{X} {col}EXIT     {X} @ {o['exit_price']:.2f} "
                         f"{o['exit_reason'] or ''} · " + (f"{r:+.2f} R · " if r is not None else "") + f"${usd:+.2f}")
                n += 1
            self.orders[o["order_id"]] = (placed, filled or seen[1], exited or seen[2])
        for e in _rows(self.c, "SELECT e.id, e.ts, e.text, o.symbol FROM order_events e JOIN orders o USING(order_id) "
                               "WHERE e.id > ? AND substr(o.placed_at,1,10) >= ? ORDER BY e.id",
                       (self.event_id, self.day)):
            self.event_id = e["id"]
            self.out(f"{_hm(e['ts'])}  {B}{e['symbol']:<6}{X} {D}event{X}     {e['text'][:170]}")
            n += 1
        lock = _rows(self.c, "SELECT locked, reason FROM risk_day WHERE date=?", (self.day,))
        locked = bool(lock and lock[0]["locked"])
        if locked != self.locked:
            if locked:
                self.out(f"{datetime.now(ET):%H:%M:%S}  {R}LOCK{X}      no new entries today — {lock[0]['reason'] or ''}")
                n += 1
            self.locked = locked
        return n

    def status(self) -> str:
        held = _rows(self.c, """SELECT * FROM orders WHERE fill_price IS NOT NULL
                                AND (exit_ts IS NULL OR status IN ('ExitPending', 'ExitFailed'))""")
        parts = []
        for o in held:
            last = _rows(self.c, "SELECT close FROM bars WHERE symbol=? ORDER BY ts DESC LIMIT 1", (o["symbol"],))
            px = last[0]["close"] if last else None
            rps = (o["trigger"] - o["stop"]) if o["trigger"] and o["stop"] else None
            now_r = f" now {px:.2f} ({(px - o['fill_price']) / rps:+.2f} R)" if px and rps else ""
            parts.append(f"{o['symbol']} x{o['shares']} @ {o['fill_price']:.2f} stop {o['stop']:.2f}{now_r}")
        done = _rows(self.c, """SELECT * FROM orders WHERE exit_price IS NOT NULL AND fill_price IS NOT NULL
                                AND substr(placed_at,1,10) >= ?""", (self.day,))
        tot_r = sum(((o["exit_price"] - o["fill_price"]) / (o["trigger"] - o["stop"]))
                    for o in done if o["trigger"] and o["stop"] and o["trigger"] > o["stop"])
        lock = "LOCKED" if self.locked else "open"
        return (f"{D}── {datetime.now(ET):%H:%M} ET · {'held: ' + '; '.join(parts) if parts else 'flat'} · "
                f"today {len(done)} closed, {tot_r:+.2f} R · risk gate {lock} · cascade kills {self.killed}{X}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=os.environ.get("JOURNAL_DB") or str(DEFAULT_DB))
    ap.add_argument("--day", default=datetime.now(ET).date().isoformat())
    ap.add_argument("--all", action="store_true", help="also list the plans the cascade killed")
    ap.add_argument("--every", type=float, default=2.0, help="seconds between looks at the ledger")
    ap.add_argument("--once", action="store_true", help="print what is there and exit")
    ap.add_argument("--history", type=int, default=40, help="lines of the day so far shown at the start")
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        print(f"no ledger at {args.db}"); return 1
    earlier: list = []
    w = Watcher(connect(args.db), args.day, args.all, out=earlier.append)
    print(f"{B}watching the bot · {args.day} · {args.db} (read-only){X} — Ctrl-C stops the watcher, never the bot")
    w.poll()
    if len(earlier) > args.history:
        print(f"{D}… {len(earlier) - args.history} earlier lines (--history to see more){X}")
    for line in earlier[-args.history:]:
        print(line)
    w.out = print
    print(w.status())
    if args.once:
        return 0
    last_status = time.monotonic()
    try:
        while True:
            time.sleep(args.every)
            if w.poll() or time.monotonic() - last_status >= 60:
                print(w.status())
                last_status = time.monotonic()
    except KeyboardInterrupt:
        print("\nwatcher stopped — the bot keeps running")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
