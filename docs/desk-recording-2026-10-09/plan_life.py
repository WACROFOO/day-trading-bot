#!/usr/bin/env python3
"""Stale plans on the recorded days: what the desk drew and priced, before and after.

    python3 docs/desk-recording-2026-10-09/plan_life.py > docs/desk-recording-2026-10-09/plan_life_output.txt

For every minute 07:00–11:29 ET of each exported day (`research/daily/<day>/`),
the day is rebuilt up to and including that minute (`scripts/fixture_from_export.py`)
through the desk's own session builder — the live edge at that minute — and
every name on the desk is read twice:

  BEFORE  the page's rule until 2026-10-09 (`livePlan` in app.js at 7aebccc): the
          last plan armed at or before the minute is drawn unless the cascade has
          killed the name; the card's ticket from `decision_card.build_card` as it
          was at commit 7aebccc (loaded from git, run on the same inputs).
  AFTER   the server card now: `card["plan"]` (the lines) and `card["ticket"]`.

A plan drawn BEFORE and not AFTER is classified by its life
(`pullback.PlanLife`): armed outside the bot's window, fill window closed, stopped,
reached 2R, stop broke before the entry. The export has no news, quotes or halts
(`fixture_from_export.py` says what it reconstructs), so catalyst reads UNKNOWN and
no ticket carries a spread — the same on both sides.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import fixture_from_export as F  # noqa: E402
from momentum_platform.dashboard import cards as C  # noqa: E402
from momentum_platform.dashboard.session_builder import build_session_from_records  # noqa: E402
from momentum_platform.models import Bar  # noqa: E402
from momentum_platform.pullback import FirstPullbackDetector  # noqa: E402

ET = ZoneInfo("America/New_York")
BEFORE_COMMIT = "7aebccc"
DAYS = ("2026-10-06", "2026-10-07")


def _before(path: str, name: str):
    """A module of this package as it was at BEFORE_COMMIT, loaded from git."""
    src = subprocess.run(["git", "show", f"{BEFORE_COMMIT}:{path}"],
                         cwd=ROOT, check=True, capture_output=True, text=True).stdout
    spec = importlib.util.spec_from_loader(f"momentum_platform._{name}_before", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "momentum_platform"
    sys.modules[spec.name] = mod                       # dataclasses look their module up
    exec(compile(src, f"{path}@{BEFORE_COMMIT}", "exec"), mod.__dict__)
    return mod


def _same_plans(day: str) -> tuple:
    """The detector's plans with the new bookkeeping against the detector at
    BEFORE_COMMIT, over every name's whole exported day: (names, plans, identical)."""
    old = _before("src/momentum_platform/pullback.py", "pullback").FirstPullbackDetector
    rows = {}
    import csv
    for r in csv.DictReader(open(ROOT / "research" / "daily" / day / "bars.csv")):
        rows.setdefault(r["symbol"], []).append(r)
    n, same = 0, True
    key = lambda p: (p.symbol, p.armed_at_bar, p.entry, p.stop, p.target, p.pullback_candles, p.volume_ok)
    for sym, rs in rows.items():
        a, b = FirstPullbackDetector(), old()
        for r in rs:
            bar = Bar(symbol=sym, timeframe="1m", ts=datetime.fromisoformat(r["ts"].replace("Z", "+00:00")),
                      open=float(r["open"]), high=float(r["high"]), low=float(r["low"]),
                      close=float(r["close"]), volume=float(r["volume"]))
            a.on_bar(bar); b.on_bar(bar)
            same = same and a.state == b.state
        same = same and [key(p) for p in a.plans] == [key(p) for p in b.plans]
        n += len(a.plans)
    return len(rows), n, same


def _old_page_plan(session, sym, t):
    """app.js livePlan at 7aebccc: the last plan armed at or before t, unless killed."""
    if (session.get("cascade") or {}).get(sym, {}).get("killedBy"):
        return None
    armed = [p for p in session.get("plans") or [] if p["symbol"] == sym and p["armedAt"] <= t]
    return armed[-1] if armed else None


def _why_dead(p, t):
    if not p.get("inWindow"):
        return "armed outside the bot's 07:00–11:20 window"
    end = p.get("end")
    if end and end["t"] <= t and (p.get("liveUntil") is None or end["t"] <= p["liveUntil"]):
        return end["why"]
    return "fill window closed (A10, 3 min)"


def main() -> int:
    old_card = _before("src/momentum_platform/decision_card.py", "card").build_card
    print(f"# stale plans, before ({BEFORE_COMMIT}) and after — every minute 07:00–11:29 ET")
    for day in DAYS:
        names, n, same = _same_plans(day)
        print(f"guard {day}: the detector's {n} plans on {names} names, 04:00–12:00, "
              f"{'IDENTICAL' if same else 'DIFFERENT'} to {BEFORE_COMMIT}'s (state by state, plan by plan)")
    grand = Counter()
    for day in DAYS:
        c = Counter()
        why = Counter()
        old_ticket_words = Counter()
        stale = {}                           # (sym, armedAt) -> [plan, why, first minute, minutes]
        start = datetime.fromisoformat(f"{day}T07:00:00").replace(tzinfo=ET)
        for k in range(270):
            minute = start + timedelta(minutes=k)
            until = (minute + timedelta(minutes=1)).strftime("%H:%M")
            recs = F.build(day, until)
            s = build_session_from_records(recs, f"{day}-{until}", "export")
            if not s["frames"]:
                continue
            t = s["frames"][-1]["t"]
            if t != int(minute.timestamp()):
                continue                     # no bar at this minute on any name
            now = datetime.fromtimestamp(t, timezone.utc)
            for sym, meta in s["symbols"].items():
                rows = s["bars"].get(sym) or []
                if not rows:
                    continue
                c["name_minutes"] += 1
                card = s["cards"][sym]
                before = _old_page_plan(s, sym, t)
                after = card["plan"]
                if before:
                    c["lines_before"] += 1
                if after:
                    c["lines_after"] += 1
                    c["lines_after_" + after["kind"]] += 1
                if before and not after:
                    w = _why_dead(before, t)
                    if before.get("liveUntil") is not None and t < before["liveUntil"]:
                        w = "live, but the card's word is NO (stop already broken)"
                    why[w] += 1
                    k2 = (sym, before["armedAt"])
                    if k2 not in stale:
                        stale[k2] = [before, w, minute, 0]
                    stale[k2][3] += 1
                # the card before: same inputs, the old function
                det = FirstPullbackDetector()
                for b in rows:
                    det.on_bar(Bar(symbol=sym, timeframe="1m", ts=datetime.fromtimestamp(b[0], timezone.utc),
                                   open=b[1], high=b[2], low=b[3], close=b[4], volume=b[5]))
                oc = old_card(sym, meta=meta, cascade=s["cascade"].get(sym) or {}, bars=rows, detector=det,
                              now=now, risk=25.0, risk_source="yours")
                if oc["ticket"]:
                    c["ticket_before"] += 1
                    old_ticket_words[oc["verdict"]["word"]] += 1
                    held = det.held_plan()
                    if det.pending() is None and held is not None and not det.life_of(held, now)["live"]:
                        c["ticket_before_dead_plan"] += 1
                if card["ticket"]:
                    c["ticket_after"] += 1
                    assert card["verdict"]["word"] == "REVIEW"
                held = det.held_plan()
                if held is not None and not det.life_of(held, now)["live"]:
                    c["held_by_dead_plan"] += 1
        grand.update(c)
        print(f"\n## {day} — {c['name_minutes']} name-minutes (names on the desk × minutes)")
        print(f"lines drawn   before {c['lines_before']:4d}   after {c['lines_after']:4d} "
              f"(armed, live {c['lines_after_armed']} · forming on a REVIEW {c['lines_after_forming']})")
        dead = sum(why.values())
        print(f"drawn before, not after: {dead}")
        for w, n in why.most_common():
            print(f"    {n:4d}  {w}")
        print(f"order block   before {c['ticket_before']:4d} "
              f"(by word: {', '.join(f'{w} {n}' for w, n in sorted(old_ticket_words.items()))}; "
              f"priced from a dead plan {c['ticket_before_dead_plan']})   after {c['ticket_after']:4d} (REVIEW only)")
        print(f"name-minutes the detector was held by a dead plan (no new plan could arm): {c['held_by_dead_plan']}")
        print("plans drawn after they stopped being live (each plan once):")
        print("    name  armed  entry/stop     first drawn dead  minutes  why")
        for (sym, _), (pl, w, first, mins) in sorted(stale.items(), key=lambda kv: -kv[1][3]):
            print(f"    {sym:5s} {datetime.fromtimestamp(pl['armedAt'], ET):%H:%M}  "
                  f"{pl['entry']:6.2f}/{pl['stop']:<6.2f}  {first:%H:%M}             {mins:4d}     {w}")
    print("\n## both days")
    print(f"name-minutes {grand['name_minutes']} · lines before {grand['lines_before']} → after {grand['lines_after']} · "
          f"order blocks before {grand['ticket_before']} (from a dead plan {grand['ticket_before_dead_plan']}) → "
          f"after {grand['ticket_after']} · held by a dead plan {grand['held_by_dead_plan']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
