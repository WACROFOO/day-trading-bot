#!/usr/bin/env python3
"""Fetch a past day's 1-minute bars from IBKR for the names the ledger decided
on that day, so the grading can run when the desk did not record the tape.

    python3 scripts/backfill_tape.py 2026-09-09            # Gateway on 4002, read-only
    python3 scripts/backfill_tape.py 2026-09-09 --dry-run  # say what would be fetched

When the desk stopped early (Ctrl-C, a sleeping Mac, a crash), the decisions
of that day exist but the bars after the stop do not, and the after-close
block records them as 'no tape'. This asks IBKR for the day's 1-minute bars
(extended hours included) for every symbol with a decision that day, writes
them into the ledger's `bars`, drops the 'no tape' actuals of that day so
they are computed again, and runs the grading. Read-only: one connection,
market data history, nothing order-shaped.

The bars come from the same provider the desk streams from, but they were
not watched live; the report's REPLAY block still holds (decisions replay
from their stored inputs), the grading is what changes. Then settle the day:

    python3 scripts/day.py --settle 2026-09-09
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from journal import actuals, bars as B, ledger as L  # noqa: E402

HOST = os.environ.get("IBKR_HOST", "127.0.0.1")
PORT = int(os.environ.get("IBKR_PORT", "4002"))
CLIENT = 35          # its own id: 27/28 desk, 29 preflight, 31 executor, 32-34 probes


def symbols_for(conn, day: str) -> list[str]:
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT symbol FROM decisions WHERE substr(ts_et,1,10)=? ORDER BY symbol", (day,))]


def to_records(hist) -> list[tuple]:
    out = []
    for b in hist or []:
        ts = b.date if isinstance(b.date, datetime) else datetime.fromisoformat(str(b.date))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        iso = ts.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        out.append((iso, float(b.open), float(b.high), float(b.low), float(b.close), float(b.volume or 0)))
    return out


def reset_no_tape(conn, day: str) -> int:
    cur = conn.execute("""DELETE FROM actuals WHERE bars_available = 0 AND decision_id IN
                          (SELECT decision_id FROM decisions WHERE substr(ts_et,1,10)=?)""", (day,))
    conn.commit()
    return cur.rowcount


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", help="YYYY-MM-DD, ET")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    conn = L.connect(os.environ.get("JOURNAL_DB") or L.DEFAULT_DB)
    syms = symbols_for(conn, args.day)
    have = {r[0]: r[1] for r in conn.execute(
        "SELECT symbol, COUNT(*) FROM bars WHERE substr(ts,1,10)=? GROUP BY symbol", (args.day,))}
    print(f"{args.day}: {len(syms)} symbol(s) with decisions; bars already recorded: "
          + (", ".join(f"{s} {have.get(s, 0)}" for s in syms) or "none"))
    if not syms:
        return 0
    if args.dry_run:
        print("dry run — nothing fetched"); return 0
    try:
        from ib_async import IB, Stock
    except ImportError:
        print("ib_async is not installed"); return 1
    ib = IB()
    try:
        ib.connect(HOST, PORT, clientId=CLIENT, readonly=True, timeout=15)
    except Exception as exc:                          # noqa: BLE001
        print(f"cannot reach the Gateway on {HOST}:{PORT} — {exc}"); return 2
    total = 0
    try:
        for sym in syms:
            c = Stock(sym, "SMART", "USD")
            ib.qualifyContracts(c)
            end = f"{args.day.replace('-', '')} 20:00:00 US/Eastern"
            hist = ib.reqHistoricalData(c, end, "1 D", "1 min", "TRADES", False, formatDate=2)
            recs = [r for r in to_records(hist) if r[0][:10] == args.day]
            n = L.record_bars(conn, {sym: recs}) if recs else 0
            total += n
            print(f"  {sym:<6} {len(recs)} bars from IBKR, {n} new in the ledger")
        conn.commit()
    finally:
        ib.disconnect()
    dropped = reset_no_tape(conn, args.day)
    res = actuals.fill_all(conn, B.from_ledger(conn))
    print(f"{total} bars added · {dropped} 'no tape' grading(s) reset · actuals: {res['computed']} computed, "
          f"{len(res['no_tape'])} still without tape")
    print(f"next: python3 scripts/day.py --settle {args.day}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
