#!/usr/bin/env python3
"""Ship one trading day from the Mac's ledger to the repo, for the daily review.

The owner, 2026-10-06: learn from each day's log, analysed at each day's end. The
ledger and the bot's log live on the Mac; the review runs in the cloud. This file
is the bridge: it writes `research/daily/<ET date>/` and, with --push, commits
and pushes it on the current branch. `scripts/daily_review.py` reads that folder.

    python3 scripts/day_export.py                 # today, written only
    python3 scripts/day_export.py --push          # today, committed and pushed
    python3 scripts/day_export.py --day 2026-10-06 --push

What goes out: decisions with their refusal reasons, gates and chart values,
their actuals; orders and order events; the 5-minute states, green-run signals and
the owner's trades of the day from research/trade-journal/journal.csv; the 1-minute bars 04:00-12:00 ET of every name with a
decision; the day's part of ~/Library/Logs/day-trading-bot/day.out.log. Anything
that looks like a key, secret, token or password is redacted from the log. The
paper account id stays (it is in the repo already).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from journal import ledger as L  # noqa: E402

OUT_ROOT = ROOT / "research" / "daily"
LOG = Path.home() / "Library" / "Logs" / "day-trading-bot" / "day.out.log"
SECRET = re.compile(r"(?i)((?:api[_-]?)?(?:key|secret|token|password|passwd)\s*[=:]\s*)\S+")


def _rows(conn, q, args=()):
    try:
        return [dict(r) for r in conn.execute(q, args)]
    except Exception as exc:                               # noqa: BLE001 — an old ledger lacks a table
        if "no such table" in str(exc):
            return []
        raise


def _csv(path: Path, rows: list[dict]) -> int:
    if not rows:
        path.write_text("")
        return 0
    cols = list(rows[0].keys())
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def log_excerpt(day: str, log: Path = LOG) -> str:
    """The day's part of the bot's log: from the first START marker or day.py line
    stamped with `day`, else the last 4,000 lines. Secrets redacted."""
    if not log.exists():
        return ""
    lines = log.read_text(errors="replace").splitlines()
    start = None
    for i, ln in enumerate(lines):
        if day in ln:
            start = i
            break
    keep = lines[start:] if start is not None else lines[-4000:]
    return "\n".join(SECRET.sub(r"\1[REDACTED]", ln) for ln in keep) + "\n"


def export(conn, day: str, out: Path, log: Path = LOG) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    n = {}
    dec = _rows(conn, """SELECT d.*, a.ref_price, a.mfe_r_planned, a.mae_r_planned, a.stop_hit, a.target_hit,
                                a.first_hit, a.trigger_hit, a.trigger_hit_ts, a.h30, a.l30, a.c_close
                         FROM decisions d LEFT JOIN actuals a USING(decision_id)
                         WHERE substr(d.ts_et,1,10)=? ORDER BY d.ts_et""", (day,))
    n["decisions"] = _csv(out / "decisions.csv", dec)
    n["orders"] = _csv(out / "orders.csv", _rows(conn, """SELECT o.* FROM orders o JOIN decisions d USING(decision_id)
                                                           WHERE substr(d.ts_et,1,10)=? ORDER BY o.order_id""", (day,)))
    n["order_events"] = _csv(out / "order_events.csv", _rows(conn, """SELECT e.*, o.symbol FROM order_events e
        JOIN orders o USING(order_id) JOIN decisions d USING(decision_id) WHERE substr(d.ts_et,1,10)=? ORDER BY e.id""",
                                                               (day,)))
    n["five_minute"] = _csv(out / "five_minute.csv", _rows(conn, "SELECT * FROM five_minute_states WHERE substr(ts_et,1,10)=?", (day,)))
    n["green_run"] = _csv(out / "green_run.csv", _rows(conn, """SELECT symbol, pause_id, ts_et, session, status, entry, stop,
        stop_pct, spread, refusals_json FROM green_run_signals WHERE substr(ts_et,1,10)=?""", (day,)))
    jf = ROOT / "research" / "trade-journal" / "journal.csv"      # the owner's trades: scripts/trade_log.py
    manual = []
    if jf.exists():
        with jf.open(newline="") as fh:
            manual = [r for r in csv.DictReader(fh) if r.get("date") == day]
    n["manual"] = _csv(out / "manual_trades.csv", manual)
    # The owner's calls from the desk's buttons (2026-10-08): took / passed /
    # closed, each with the card the desk showed at that moment.
    try:
        calls = _rows(conn, "SELECT * FROM manual_decisions WHERE substr(ts_et,1,10)=? ORDER BY ts_et, id", (day,))
    except Exception:                                   # noqa: BLE001 — a ledger from before the table
        calls = []
    n["desk_calls"] = _csv(out / "desk_calls.csv", calls)
    syms = sorted({r["symbol"] for r in dec} | {r["sym"].upper() for r in manual if r.get("sym")}
                  | {r["symbol"] for r in calls})
    d0 = datetime.fromisoformat(f"{day}T04:00:00").replace(tzinfo=L.ET).astimezone(timezone.utc)
    d1 = d0 + timedelta(hours=8)
    bars = []
    for s in syms:
        bars += _rows(conn, """SELECT symbol, ts, open, high, low, close, volume FROM bars
                               WHERE symbol=? AND ts>=? AND ts<? ORDER BY ts""",
                      (s, d0.strftime("%Y-%m-%dT%H:%M"), d1.strftime("%Y-%m-%dT%H:%M")))
    n["bars"] = _csv(out / "bars.csv", bars)
    text = log_excerpt(day, log)
    (out / "day.log").write_text(text)
    n["log_lines"] = text.count("\n")
    meta = {"day": day, "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "counts": n,
            "ledger": str(conn.execute("PRAGMA database_list").fetchone()[2])}
    (out / "export.json").write_text(json.dumps(meta, indent=1))
    _index_day(out.parent, day)
    readme = out / "README.md"
    if not readme.exists():
        readme.write_text(f"# {day} — one day exported from the owner's Mac\n\n"
                          "The files are described in `../README.md`; `review.md` is the day read on its\n"
                          "own bars. Exported by `scripts/day_export.py` (counts in `export.json`).\n")
    return meta


def _index_day(daily: Path, day: str) -> None:
    """Name the new day in research/daily/README.md, the folder's index: the
    index doctor fails a README that omits a subdirectory, and an unnamed day
    is a day the next reader does not find."""
    readme = daily / "README.md"
    if not readme.exists():
        return
    text = readme.read_text()
    if f"`{day}/`" in text:
        return
    readme.write_text(text.rstrip() + f"\n| `{day}/` | exported {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC |\n")


def push(day: str) -> bool:
    rel = f"research/daily/{day}"
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, capture_output=True,
                            text=True).stdout.strip()
    cmds = [["git", "add", rel], ["git", "commit", "-q", "-m", f"Daily export {day} (decisions, orders, bars, log)"],
            ["git", "pull", "-q", "--rebase", "--autostash", "origin", branch], ["git", "push", "-q", "origin", branch]]
    for c in cmds:
        r = subprocess.run(c, cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0 and not (c[1] == "commit" and "nothing to commit" in (r.stdout + r.stderr)):
            print(f"  {' '.join(c)} failed: {(r.stderr or r.stdout).strip()[:300]}")
            return False
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=os.environ.get("JOURNAL_DB") or str(L.DEFAULT_DB))
    ap.add_argument("--day", default=datetime.now(L.ET).date().isoformat())
    ap.add_argument("--log", default=str(LOG))
    ap.add_argument("--push", action="store_true", help="commit and push research/daily/<day>")
    args = ap.parse_args(argv)
    conn = L.connect(args.db)
    meta = export(conn, args.day, OUT_ROOT / args.day, Path(args.log))
    print(f"exported {args.day} → research/daily/{args.day}: " + " · ".join(f"{k} {v}" for k, v in meta["counts"].items()))
    if args.push:
        print("pushed" if push(args.day) else "NOT pushed — run the git commands above by hand")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
