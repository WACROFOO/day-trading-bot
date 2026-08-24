"""Accumulate LULD halts from the free Nasdaq feed.

    python3 -m src.halt_poller            # append new records, dedup, report

The feed is public and needs no key, and it carries what a bar API never
does: the halt time to the millisecond, the resumption time, and the reason
code. What it does NOT carry is history — it is a rolling window of ~100
records. So this cannot backfill the two-year study; it can only build the
archive forward from the day it starts running.

That is why it exists as a separate poller rather than a fetch inside the
backtest. Run it on a schedule (a few times a day is enough — the window
holds ~100 records and a busy session prints far fewer than that) and the
halt model becomes real for every session after today. Sessions before it
stay `halt_flag = UNKNOWN`, which is what the report already says.

Why it matters more than it looks: a stop cannot execute while a stock is
halted, and these names halt on exactly the moves the strategy hunts. A LULD
pause above the stop that reopens below it is a loss the current fill model
books at the stop price, and therefore understates.
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

from .data import NasdaqHaltFeed

OUT = Path(__file__).resolve().parent.parent / "data" / "halts.csv"
FIELDS = ["symbol", "halt_date", "halt_time", "reason", "resume_date",
          "resume_quote_time", "resume_trade_time", "first_seen_utc"]


def _key(r: dict) -> tuple:
    return (r.get("symbol"), r.get("halt_date"), r.get("halt_time"))


def load() -> dict[tuple, dict]:
    if not OUT.exists():
        return {}
    with OUT.open(newline="") as fh:
        return {_key(r): r for r in csv.DictReader(fh)}


def poll() -> dict:
    existing = load()
    fetched = NasdaqHaltFeed.fetch()
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    added = 0
    for r in fetched:
        k = _key(r)
        if k in existing:
            # a resumption time can arrive AFTER the halt is first published,
            # so refresh those two fields rather than skipping the row
            for f in ("resume_date", "resume_quote_time", "resume_trade_time"):
                if r.get(f) and not existing[k].get(f):
                    existing[k][f] = r[f]
            continue
        r["first_seen_utc"] = now
        existing[k] = r
        added += 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for k in sorted(existing, key=lambda x: (x[1] or "", x[2] or "")):
            w.writerow(existing[k])
    dates = {r.get("halt_date") for r in existing.values() if r.get("halt_date")}
    return dict(fetched=len(fetched), added=added, total=len(existing),
                distinct_dates=len(dates),
                earliest=min(dates) if dates else None,
                latest=max(dates) if dates else None)


if __name__ == "__main__":
    s = poll()
    print(f"halt feed: {s['fetched']} in window, {s['added']} new, "
          f"{s['total']} total across {s['distinct_dates']} dates "
          f"({s['earliest']} -> {s['latest']})")
    print(f"-> {OUT}")
    if s["added"] == 0 and s["total"] > 0:
        print("   (no new halts since the last poll — expected off-session)")
