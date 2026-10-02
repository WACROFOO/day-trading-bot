#!/usr/bin/env python3
"""Mechanics replay: run the desk's OWN event scanners and router (same list,
same order, same RouterConfig as session_builder.py:277-293) over cached SIP
1-minute bars of historical candidate days, and record every Running Up /
squeeze event — delivered or suppressed, with the router's reason — plus the
cascade state at that bar (cascade_inputs with the live snapshot and
chart_gates over the bars so far, as session_builder.py:378-385 does for plans).

Inputs the history does not carry, declared:
  * float: none in candidate_days.csv (float_provenance 'unavailable' on all rows)
    -> float_shares None, quality 'unknown' (the desk's common case)
  * news: none -> catalyst False, source_ok True
  * avg_daily_volume: APPROXIMATED as prior_dollar_volume_20d / prev_close
  * no volume profile -> RVOL is the daily measure (volume_today / avg)
  * complete minutes only (the live desk also sees the forming minute)
Forward outcome per event: max high / min low / close over the next 30 one-minute
bars relative to the alert bar's close.
"""
from __future__ import annotations

import csv
import json
import pickle
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/user/day-trading-bot")
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

from momentum_platform.cascade import evaluate as evaluate_cascade  # noqa: E402
from momentum_platform.dashboard.session_builder import cascade_inputs  # noqa: E402
from momentum_platform.engine import ScannerEngine  # noqa: E402
from momentum_platform.indicators import chart_gates  # noqa: E402
from momentum_platform.models import Bar, DataStatus, FloatQuality  # noqa: E402
from momentum_platform.notify import Channel, NotificationRouter, RouterConfig  # noqa: E402
from momentum_platform.scanners import (  # noqa: E402
    Breakout52wScanner, FivePillarsAlert, HodMomentumScanner, RunningMoveScanner,
    UptrendScanner, squeeze_5_in_5, squeeze_10_in_10)
from momentum_platform.scanners.momentum_events import MIN_VOLUME_5M  # noqa: E402
from momentum_platform.state import HotState, MarketUpdate, ReferenceData  # noqa: E402

UNIVERSE = ROOT / "research/first-pullback-edge/data/candidate_days.csv"
CACHE = ROOT / "data/cache/history"
OUT = Path(__file__).resolve().parent / "events.pkl"
TILE = ("running_up", "squeeze_5_in_5", "squeeze_10_in_10")


class Sink(Channel):
    name = "sink"

    def deliver(self, event, consolidated=None):
        pass


def load_universe():
    out = defaultdict(dict)
    with open(UNIVERSE) as f:
        for r in csv.DictReader(f):
            if (r.get("reverse_split_ratio") or "").strip():
                continue
            try:
                pc = float(r["prev_close"]); dv = float(r["prior_dollar_volume_20d"])
            except (TypeError, ValueError):
                continue
            out[r["day"]][r["sym"]] = (pc, dv / pc if pc > 0 else None)
    return out


def run_day(day: str, syms: dict, raw: dict) -> list:
    hot = HotState()
    refs, bars_by = [], {}
    for s, (pc, adv) in syms.items():
        rows = raw.get(s) or []
        if len(rows) < 30:
            continue
        refs.append(ReferenceData(symbol=s, prev_close=pc, avg_daily_volume=adv,
                                  high_52w=None, float_shares=None,
                                  float_quality=FloatQuality.UNKNOWN))
        bars_by[s] = rows
    if not refs:
        return []
    hot.load_reference(refs)
    router = NotificationRouter(RouterConfig(), [Sink()])
    engine = ScannerEngine(hot=hot, router=router, scanners=[
        FivePillarsAlert(),
        HodMomentumScanner(min_volume_5m=MIN_VOLUME_5M),
        UptrendScanner(min_volume_5m=MIN_VOLUME_5M),
        RunningMoveScanner(direction="down", min_volume_5m=MIN_VOLUME_5M),
        squeeze_5_in_5(), squeeze_10_in_10(),
        Breakout52wScanner(),
    ])
    # minute-major order, like session_builder.py:302-310
    minutes = defaultdict(list)
    for s, rows in bars_by.items():
        for i, (t, o, h, l, c, v) in enumerate(rows):
            minutes[t].append((s, i))
    seen_bars = {s: [] for s in bars_by}
    meta = {s: {"symbol": s, "floatShares": None, "floatQuality": "unknown",
                "news": [], "newsSourceOk": True, "tradingDate": day} for s in bars_by}
    out = []
    for t in sorted(minutes):
        ts = datetime.fromisoformat(t.replace("Z", "+00:00"))
        for s, i in minutes[t]:
            _, o, h, l, c, v = bars_by[s][i]
            bar = Bar(symbol=s, timeframe="1m", ts=ts, open=o, high=h, low=l, close=c, volume=v or 0)
            seen_bars[s].append([int(ts.timestamp()), o, h, l, c, v or 0])
            n0 = len(router.deliveries)
            evs = engine.process(MarketUpdate(symbol=s, ts=ts, price=c, size=v or 0, bar=bar,
                                              data_status=DataStatus.REPLAY))
            if not evs:
                continue
            dl = router.deliveries[n0:]
            status = {}
            for d in dl:
                status[d.event.event_id] = (d.status, d.detail)
            fired = [e.scanner for e in evs]
            for e in evs:
                if e.scanner not in TILE and e.scanner != "hod_momentum":
                    continue
                snap = hot.symbols[s].snapshot
                cg = chart_gates(seen_bars[s])
                res = evaluate_cascade(cascade_inputs(meta[s], None, False, snap=snap, chart=cg))
                fwd = bars_by[s][i + 1:i + 31]
                fh = max((r[2] for r in fwd), default=None)
                fl = min((r[3] for r in fwd), default=None)
                fc = fwd[-1][4] if fwd else None
                eod = bars_by[s][-1][4]
                st, det = status.get(e.event_id, ("?", ""))
                rv = {r.filter: r.value for r in e.reasons}
                out.append({
                    "day": day, "sym": s, "ts": t, "scanner": e.scanner, "branch": e.branch,
                    "severity": e.severity, "status": st, "detail": det, "fired_same_bar": fired,
                    "last": c, "chg": snap.change_from_close_pct, "rvol": snap.rvol if snap.rvol is not None else snap.rvol_daily,
                    "vol5m": snap.volume_5m, "hod": snap.session_high, "vol_today": snap.volume_today,
                    "move": rv.get("move_10m_pct", rv.get("move_5m_pct")), "at_hod": rv.get("at_hod"),
                    "pillars_scanner": rv.get("pillars_passed"),
                    "verdict": res.verdict.value, "killed_by": res.killed_by,
                    "gates": {g.id: g.state.value for g in res.gates},
                    "pillar_value": next((g.value for g in res.gates if g.id == "pillars"), None),
                    "above_vwap": cg.get("above_vwap"), "above_ema9": cg.get("above_ema9"),
                    "macd_ok": cg.get("macd_positive_and_above_signal"),
                    "mfe30": None if fh is None else 100 * (fh / c - 1),
                    "mae30": None if fl is None else 100 * (fl / c - 1),
                    "ret30": None if fc is None else 100 * (fc / c - 1),
                    "ret_eod": 100 * (eod / c - 1), "nfwd": len(fwd),
                })
    return out


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    uni = load_universe()
    days = sorted(d for d in uni if (CACHE / f"{d}.json").exists())
    random.Random(seed).shuffle(days)
    days = sorted(days[:n])
    allev = []
    for k, d in enumerate(days):
        raw = json.loads((CACHE / f"{d}.json").read_text())
        allev += run_day(d, uni[d], raw)
        if k % 20 == 0:
            print(f"{k}/{len(days)} {d} events={len(allev)}", flush=True)
    OUT.write_bytes(pickle.dumps({"days": days, "events": allev, "seed": seed, "n": n}))
    print("done", len(days), "days", len(allev), "events ->", OUT)


if __name__ == "__main__":
    main()
