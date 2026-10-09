#!/usr/bin/env python3
"""The shadow strategies' paper track record, from the desk's own decisions.

The owner, 2026-10-09: log the month study's best combination forward to
measure its accuracy. `src/momentum_platform/shadow.py` defines S6 (the best
found) and S3 (its robust core). Every plan the desk armed — `decisions.csv`
of each exported day — is judged by both; each plan a strategy takes is
scored on the desk's own 1-minute bars:
  * the fill as the bot's (A10): a touch within 3 bars; a bar opening above the
    cap fills only if the tape comes back to the cap inside the 3 bars;
  * the exit break-even after 1 R, then 2 R; flat 11:30;
  * the costs at the owner's sizing (backtest_recent COST_MODEL "live").

    python3 scripts/shadow_record.py                      # the forward record, from 2026-10-09
    python3 scripts/shadow_record.py --since 2026-09-11   # with the month it was chosen on (in-sample)
    python3 scripts/shadow_record.py --daily ~/day-trading-exports

It writes `shadow.csv` in the daily folder and prints the record. A day is an
anecdote: the record is read at 30 and at 100 trades per strategy, never
before, and it changes no rule by itself.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

import backtest_recent as E  # noqa: E402  entry_cap, simulate, cost_r, portfolio, TTL_BARS
from momentum_platform.shadow import STRATEGIES, judge  # noqa: E402

DAILY = ROOT / "research" / "daily"
FORWARD_FROM = "2026-10-09"      # the first session after the study


def _f(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def _read(path: Path) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def day_bars(day_dir: Path) -> dict:
    """{sym: [(ts ET, o, h, l, c, v), ...]} from the desk's own bars."""
    out = defaultdict(list)
    for r in _read(day_dir / "bars.csv"):
        try:
            ts = datetime.fromisoformat(r["ts"].replace("Z", "+00:00")).astimezone(E.ET)
            out[r["symbol"]].append((ts, float(r["open"]), float(r["high"]), float(r["low"]),
                                     float(r["close"]), float(r["volume"] or 0)))
        except (KeyError, TypeError, ValueError):
            continue
    for v in out.values():
        v.sort(key=lambda b: b[0])
    return out


def score(bars: list, armed: datetime, trigger: float, stop: float) -> dict:
    """The bot's fill and the break-even exit on the bars after `armed`."""
    E.FLAT = E.dtime(11, 30)
    fwd = [b for b in bars if b[0] > armed]
    touch = next((k for k, b in enumerate(fwd[:E.TTL_BARS]) if b[2] >= trigger), None)
    if touch is None:
        return {"filled": False}
    fill, k = trigger, touch
    cap = E.entry_cap(trigger)
    if fwd[touch][1] > cap:
        back = next((j for j in range(touch, min(len(fwd), touch + E.TTL_BARS)) if fwd[j][3] <= cap), None)
        if back is None:
            return {"filled": False, "why": "opened over the A10 cap"}
        fill, k = cap, back
    elif fwd[touch][1] > trigger:
        fill = fwd[touch][1]
    ent = fwd[k:]
    r, why, t_out = E.simulate(ent, trigger, stop, "be", fill=fill)
    before = [b for b in bars if b[0] <= armed][-5:]
    dv5 = sum(b[4] * b[5] for b in before)
    saved = E.COST_MODEL
    E.COST_MODEL = "live"
    try:
        cost = E.cost_r(trigger, stop, why in ("stop", "trail"), pm=armed.time() < E.RTH_START, dv5=dv5)
    finally:
        E.COST_MODEL = saved
    return {"filled": True, "fill": round(fill, 4), "why": why, "t_in": ent[0][0], "t_out": t_out,
            "r_gross": r, "r_net": round(r - cost, 3)}


def record(daily: Path, since: str, until: str | None = None) -> list[dict]:
    rows = []
    for dd in sorted(p for p in daily.iterdir() if p.is_dir()):
        day = dd.name
        if day < since or (until and day > until) or not (dd / "decisions.csv").exists():
            continue
        bars = day_bars(dd)
        seen = set()
        for d in _read(dd / "decisions.csv"):
            if str(d.get("data_status") or "").endswith("-backfill"):
                continue                                   # loaded history, not live
            trig, stop = _f(d.get("trigger")), _f(d.get("stop"))
            if not trig or stop is None or trig <= stop:
                continue
            key = (d["symbol"], round(trig, 4), round(stop, 4))
            if key in seen:
                continue
            seen.add(key)
            armed = datetime.fromisoformat(d["ts_et"])
            try:
                chart = json.loads(d.get("chart_json") or "{}")
            except ValueError:
                chart = {}
            vol_ok = d.get("volume_ok")
            values = {"trigger": trig, "stop": stop, "armed": armed.time(), "last": _f(d.get("last")),
                      "vwap": _f(chart.get("vwap")), "hod": _f(d.get("session_high")),
                      "volume_ok": None if vol_ok in (None, "") else str(vol_ok) in ("1", "True", "true")}
            for j in judge(values):
                if not j["takes"]:
                    continue
                s = score(bars.get(d["symbol"], []), armed, trig, stop)
                rows.append({"day": day, "strategy": j["id"], "symbol": d["symbol"], "armed": armed.strftime("%H:%M"),
                             "trigger": trig, "stop": stop, "stop_pct": round((trig - stop) / trig * 100, 2),
                             "filled": s["filled"], "fill": s.get("fill"), "exit": s.get("why"),
                             "r_gross": s.get("r_gross"), "r_net": s.get("r_net"),
                             "bot_outcome": d.get("outcome"), "t_in": s.get("t_in"), "t_out": s.get("t_out")})
    return rows


def summary(rows: list[dict]) -> list[str]:
    out = []
    for sid, st in STRATEGIES.items():
        mine = [r for r in rows if r["strategy"] == sid]
        filled = [r for r in mine if r["filled"]]
        nets = [r["r_net"] for r in filled]
        days = defaultdict(float)
        for r in filled:
            days[r["day"]] += r["r_net"]
        port = E.portfolio([dict(r, sym=r["symbol"], touched=True, be=r["r_net"], be_out=r["t_out"])
                            for r in filled], lambda p: True, "be")
        out.append(f"{sid} ({st['label']}): {len(mine)} plans taken, {len(filled)} filled"
                   + (f" · net {statistics.mean(nets):+.3f} R a trade · total {sum(nets):+.1f} R · "
                      f"wins {sum(1 for x in nets if x > 0)}/{len(nets)} · days up {sum(1 for x in days.values() if x > 0)}"
                      f"/{len(days)} · one position {port['total']:+.1f} R over {port['trades']}" if nets else ""))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--daily", default=str(DAILY))
    ap.add_argument("--since", default=FORWARD_FROM)
    ap.add_argument("--until")
    ap.add_argument("--out", help="the CSV to write (default: shadow.csv in the daily folder)")
    args = ap.parse_args(argv)
    daily = Path(args.daily).expanduser()
    rows = record(daily, args.since, args.until)
    out = Path(args.out) if args.out else daily / "shadow.csv"
    cols = ["day", "strategy", "symbol", "armed", "trigger", "stop", "stop_pct", "filled", "fill", "exit",
            "r_gross", "r_net", "bot_outcome"]
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    label = "FORWARD" if args.since >= FORWARD_FROM else "IN-SAMPLE BACKFILL (the month the strategies were chosen on)"
    print(f"shadow record · {label} · {args.since}..{args.until or 'latest'} · {daily}")
    for line in summary(rows):
        print("  " + line)
    print(f"written {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
