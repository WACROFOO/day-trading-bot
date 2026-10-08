#!/usr/bin/env python3
"""A replay fixture from a day the owner's Mac exported, cut at a given ET minute.

    python3 scripts/fixture_from_export.py 2026-10-06 --until 07:30 --out /tmp/f.jsonl
    PYTHONPATH=src python3 -m momentum_platform.dashboard.server --fixture /tmp/f.jsonl

Why (desk assessment 2026-10-08): the only replay fixture is synthetic and starts
at 08:00, so the desk could not be walked at 07:30 and every card was judged at
the end of the replay. This builds a fixture from the real exported tape
(`research/daily/<day>/bars.csv`, the desk's own 1-minute bars) for the names
the desk decided on that day, cut at `--until`, so the card is read as of that
minute.

What it carries and what it cannot:
  - bars: the desk's 1-minute bars 04:00 → the cut, as recorded (UTC stamps)
  - reference: previous close and float from the day's `decisions.csv` (previous
    close = last ÷ (1 + change %), the decision's own snapshot); the RVOL baseline
    reconstructed as volume ÷ RVOL at the first decision — an Approximation, since
    the export carries neither the 20-day average nor the time-of-day profile
  - news: NOT exported. The fixture says so with a `news_source` record, so the
    catalyst reads UNKNOWN rather than "no news" — never a guess
  - halts and quotes: not exported; the card has no spread and no halt history
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
ET = ZoneInfo("America/New_York")


def build(day: str, until: str) -> list[dict]:
    base = ROOT / "research" / "daily" / day
    refs: dict[str, dict] = {}
    for r in csv.DictReader(open(base / "decisions.csv")):
        sym = r["symbol"]
        try:
            last, chg = float(r["last"]), float(r["change_pct"])
        except (TypeError, ValueError):
            continue
        if sym in refs or chg <= -100:
            continue
        fs = r.get("float_shares")
        ref = {"type": "reference", "symbol": sym, "prev_close": round(last / (1 + chg / 100.0), 4),
               "float_shares": float(fs) if fs not in (None, "", "nan") else None,
               "float_quality": r.get("float_quality") or "unknown",
               "float_source": (r.get("float_source") or "") + " (from the day's decision export)"}
        # The RVOL baseline is not exported. Reconstructed from the decision's own
        # snapshot — volume ÷ RVOL at that bar — which reads the desk's time-of-day
        # RVOL back as a daily average: an APPROXIMATION, stated in the header.
        try:
            v, rv = float(r["volume"]), float(r["rvol"])
            if v > 0 and rv > 0:
                ref["avg_daily_volume"] = round(v / rv)
        except (TypeError, ValueError, KeyError):
            pass
        refs[sym] = ref
    cut_h, cut_m = (int(x) for x in until.split(":"))
    out: list[dict] = [{"type": "news_source", "ok": False}] + list(refs.values())
    bars = []
    for r in csv.DictReader(open(base / "bars.csv")):
        if r["symbol"] not in refs:
            continue
        t = datetime.fromisoformat(r["ts"].replace("Z", "+00:00"))
        et = t.astimezone(ET)
        if (et.hour, et.minute) >= (cut_h, cut_m):
            continue
        bars.append({"type": "bar", "tf": "1m", "symbol": r["symbol"], "ts": r["ts"],
                     "open": float(r["open"]), "high": float(r["high"]), "low": float(r["low"]),
                     "close": float(r["close"]), "volume": float(r["volume"])})
    bars.sort(key=lambda b: (b["ts"], b["symbol"]))
    return out + bars


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", help="an exported day, YYYY-MM-DD (research/daily/<day>/)")
    ap.add_argument("--until", default="16:00", help="ET minute to cut at, HH:MM (bars before it are kept)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    recs = build(a.day, a.until)
    head = (f"# Replay of {a.day} up to {a.until} ET, from research/daily/{a.day}/ (the desk's own bars)\n"
            f"# Built by scripts/fixture_from_export.py. No news, quotes or halts were exported;\n"
            f"# the RVOL baseline is reconstructed (volume / RVOL at the first decision).\n")
    Path(a.out).write_text(head + "\n".join(json.dumps(r) for r in recs) + "\n")
    n = sum(1 for r in recs if r["type"] == "bar")
    print(f"{a.out}: {len(recs) - n - 1} names, {n} bars up to {a.until} ET")
    return 0


if __name__ == "__main__":
    sys.exit(main())
