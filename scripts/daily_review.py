#!/usr/bin/env python3
"""The end-of-day review of one exported day (`scripts/day_export.py`).

    python3 scripts/daily_review.py 2026-10-06      # writes research/daily/2026-10-06/review.md
    python3 scripts/daily_review.py --latest

It learns, it does not change: every refused plan is scored on the day's own bars
(fill at the trigger if touched within 3 minutes, A3 trail 1 R, flat 11:30 — an upper
bound, no costs, the `exercise.py missed` convention), grouped by the rule that
refused it, and appended to `research/daily/cohorts.csv`. A cohort is a rule the
ten-year tests already rejected or left OFF (the MACD warm-up, the run-past entry,
the 04:00-07:00 window, the 5-minute trigger); the cohorts file is how those get
their 200 prospective trades. Reaching 200 flags the cohort for a preregistered
decision. Nothing here edits a rule.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / "research" / "daily"
ET = ZoneInfo("America/New_York")
TTL_MIN, FLAT = 3, dtime(11, 30)
PROSPECTIVE_N = 200

# first matching substring of the refusal text -> cohort. Order matters.
COHORTS = [
    ("MACD warm-up", "warmup_macd"),
    ("ran past the limit", "ran_past"),
    ("outside 07:00-09:30", "before_0700"),
    ("bar is outside the 07:00-16:00", "before_0700"),
    ("past the 11:30 hard stop", "after_cutoff"), ("last 10 minutes before", "after_cutoff"),
    ("pullback volume", "volume"), ("below VWAP", "vwap"), ("below the 9 EMA", "ema9"),
    ("MACD not positive", "macd"), ("MACD unknown", "macd_unknown"),
    ("selective (A13): stop", "stop_under_2pct"), ("inside 4x", "stop_inside_spread"),
    ("one position at a time", "one_position"), ("day locked", "risk_lock"),
    ("bar clock", "stale"), ("quote clock", "no_quote"), ("backfill", "backfill"), ("phase ", "phase"),
    ("the ask did not reach", "ask_never_came"), ("no ask quoted", "no_quote"),
]
WATCHED = {"warmup_macd": "B30 (addendum 2026-10-06b)", "ran_past": "RA (addendum 2026-10-06c)",
           "before_0700": "W4 (addendum 2026-10-06d)", "five_min_pb": "E1 (addendum 2026-10-06b)"}


def read(day_dir: Path, name: str) -> list[dict]:
    f = day_dir / name
    if not f.exists() or not f.read_text().strip():
        return []
    with f.open() as fh:
        return list(csv.DictReader(fh))


def num(x):
    try:
        return float(x) if x not in (None, "") else None
    except ValueError:
        return None


def et(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(ET)


def bars_by_symbol(rows):
    out = defaultdict(list)
    for r in rows:
        out[r["symbol"]].append((et(r["ts"]), num(r["open"]), num(r["high"]), num(r["low"]), num(r["close"])))
    for v in out.values():
        v.sort(key=lambda b: b[0])
    return out


def simulate(bars, t_order: datetime, entry: float, stop: float, ttl_min: int = TTL_MIN):
    """(gross R, how) from 1-minute bars: fill at the trigger if a bar from t_order
    within ttl reaches it; then the A3 trail at 1 R; flat at 11:30. None = no fill."""
    rps = entry - stop
    if rps <= 0:
        return None, "bad levels"
    fwd = [b for b in bars if b[0] >= t_order.replace(second=0, microsecond=0)]
    k = next((i for i, b in enumerate(fwd) if (b[0] - t_order).total_seconds() < ttl_min * 60 and b[2] >= entry), None)
    if k is None:
        return None, "trigger not reached"
    fill = max(entry, fwd[k][1]) if fwd[k][1] > entry else entry
    level, high = stop, fill
    for i, (t, o, h, l, c) in enumerate(fwd[k:]):
        if t.time() >= FLAT:
            return (o - fill) / rps, "flat 11:30"
        if l <= level and i > 0:
            return (min(level, o) - fill) / rps, "stop"
        high = max(high, h)
        level = max(level, high - rps)
    return (fwd[-1][4] - fill) / rps if fwd else None, "end of data"


def held_r(bars, t_entry: datetime, entry: float, stop: float):
    """(gross R, how) of a position already filled at `entry` at `t_entry`,
    exited by the bot's own rule: the A3 trail 1 R under the high, flat 11:30."""
    rps = entry - stop
    if rps <= 0:
        return None, "bad levels"
    level, high = stop, entry
    fwd = [b for b in bars if b[0] > t_entry.replace(second=0, microsecond=0)]
    for t, o, h, l, c in fwd:
        if t.time() >= FLAT:
            return (o - entry) / rps, "flat 11:30"
        if l <= level:
            return (min(level, o) - entry) / rps, "stop" if level == stop else "trail"
        high = max(high, h)
        level = max(level, high - rps)
    return ((fwd[-1][4] - entry) / rps, "end of data") if fwd else (None, "no bars after the fill")


def desk_calls_section(calls: list, bars: dict, rows: list) -> list:
    """The owner's calls from the desk's buttons, scored beside the bot's plans
    (owner, 2026-10-08: "score my manual calls next to the bot's"). A `took`
    is scored on its own close when one was recorded, else on the bot's exit
    rule; a `passed` on what the card's plan would have done. Gross R, upper
    bounds, same caveats as above."""
    out = [f"## Your calls on the desk — {len(calls)} recorded", ""]
    if not calls:
        return out + ["None. The desk's buttons (I took it / I passed / I closed it) write them.", ""]
    closes = {}
    for c in calls:
        if c.get("action") == "closed":
            closes.setdefault(c["symbol"], []).append(c)
    out += ["| ET | symbol | your call | the card said | result (gross R) | the bot near then |",
            "|---|---|---|---|---|---|"]
    for c in calls:
        if c.get("action") == "closed":
            continue
        sym, t = c["symbol"], et(c["ts_et"])
        said = f"{c.get('verdict') or '—'}: {(c.get('reason') or '')[:60]}"
        res = "—"
        if c.get("action") == "took":
            px, stp = num(c.get("price")), num(c.get("stop"))
            exit_ = next((x for x in closes.get(sym, []) if et(x["ts_et"]) >= t), None)
            if px and stp and px > stp:
                if exit_ and num(exit_.get("price")):
                    res = f"{(num(exit_['price']) - px) / (px - stp):+.2f} (your close {num(exit_['price']):.2f})"
                else:
                    r, how = held_r(bars.get(sym, []), t, px, stp)
                    res = "—" if r is None else f"{r:+.2f} on the bot's exit ({how}; no close recorded)"
        else:
            try:
                setup = json.loads(c.get("card_json") or "{}").get("setup") or {}
            except ValueError:
                setup = {}
            trig, stp = num(setup.get("trigger")), num(setup.get("stop"))
            if trig and stp:
                r, how = simulate(bars.get(sym, []), t, trig, stp)
                res = f"if taken: {'—' if r is None else f'{r:+.2f}'} ({how})"
            else:
                res = "no plan on the card"
        near = [r for r in rows if r[1] == sym and abs((et(f"{c['ts_et'][:11]}{r[0]}:00{c['ts_et'][19:]}") - t)
                                                       .total_seconds()) <= 900]
        bot = "; ".join(f"{r[0]} {r[4]}" for r in near) or "no plan within 15 min"
        out.append(f"| {c['ts_et'][11:16]} | {sym} | {c['action']} | {said} | {res} | {bot} |")
    return out + [""]


def cohort_of(d: dict) -> str:
    if d["outcome"] == "SUPPRESSED":
        return "killed:" + (d.get("killed_by") or "?")
    if d["outcome"] in ("TAKEN", "CLAIMED"):
        return "taken"
    try:
        reasons = " | ".join(json.loads(d.get("refusal_reasons_json") or "[]"))
    except ValueError:
        reasons = d.get("refusal_reasons_json") or ""
    for needle, name in COHORTS:
        if needle in reasons:
            return name
    return (d["outcome"] or "?").lower()


def shadow_section(day: str) -> list:
    """The shadow strategies' plans of the day (2026-10-09, research/month-study/):
    S6 the best found, S3 its robust core — scored like the bot's fill, exit
    break-even then 2 R, net of costs at the owner's sizing. Logged, never traded."""
    import shadow_record as SR
    rows = SR.record(DAILY, day, day)
    L = [f"## Shadow strategies — {len(rows)} plans taken today, logged, never traded", "",
         "Exit: break-even after 1 R, then 2 R; flat 11:30; net of costs at the owner's sizing. "
         "The record across days: `python3 scripts/shadow_record.py`.", ""]
    if rows:
        L += ["| strategy | symbol | armed | trigger / stop | stop % | filled | exit | net R | the bot |",
              "|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            net = "—" if r["r_net"] is None else f"{r['r_net']:+.2f}"
            L.append(f"| {r['strategy']} | {r['symbol']} | {r['armed']} | {r['trigger']:.2f} / {r['stop']:.2f} | "
                     f"{r['stop_pct']:.1f} | {'yes' if r['filled'] else 'no'} | {r['exit'] or '—'} | "
                     f"{net} | {r['bot_outcome'] or '—'} |")
    L += [""] + ["- " + x for x in SR.summary(rows)] + [""]
    return L


def review(day: str) -> str:
    dd = DAILY / day
    meta = json.loads((dd / "export.json").read_text())
    dec = read(dd, "decisions.csv")
    bars = bars_by_symbol(read(dd, "bars.csv"))
    orders, manual, five = read(dd, "orders.csv"), read(dd, "manual_trades.csv"), read(dd, "five_minute.csv")
    L = [f"# Daily review — {day}", "", "```",
         f"SOURCE · research/daily/{day}/ exported {meta['exported_at']} from {meta.get('ledger')}",
         "       · " + " · ".join(f"{k} {v}" for k, v in meta["counts"].items()),
         "SCORING · refused plans: fill at the trigger if touched within 3 min, A3 trail 1 R, flat 11:30,",
         "          1-minute bars from the desk's own ledger — an UPPER BOUND, no costs, no slippage",
         "! A day is an anecdote. Cohorts decide only at 200 prospective trades, under a preregistered rule.",
         "```", ""]
    live = [d for d in dec if not str(d.get("data_status") or "").endswith("-backfill")]
    by = Counter(cohort_of(d) for d in live)
    L += [f"## Funnel — {len(dec)} plans armed ({len(dec) - len(live)} on loaded history, not counted)", "",
          "| what happened | plans |", "|---|---|"] + [f"| {k} | {v} |" for k, v in by.most_common()] + [""]

    rows, cohort_rows = [], []
    for d in live:
        trig, stop = num(d.get("trigger")), num(d.get("stop"))
        if trig is None or stop is None:
            continue
        t_arm = et(d["ts_et"])
        r, how = simulate(bars.get(d["symbol"], []), t_arm.replace(second=0) + timedelta(minutes=1), trig, stop)
        c = cohort_of(d)
        rows.append((d["ts_et"][11:16], d["symbol"], trig, stop, c, r, how))
        if c in WATCHED:
            cohort_rows.append({"day": day, "ts_et": d["ts_et"], "symbol": d["symbol"], "cohort": c,
                                "trigger": trig, "stop": stop, "gross_r": None if r is None else round(r, 3),
                                "how": how})
    L += ["## Every plan, scored on the day's bars", "",
          "| ET | symbol | trigger / stop | refused by | if taken (gross R) | how |", "|---|---|---|---|---|---|"]
    for t, s, trig, stop, c, r, how in rows:
        L.append(f"| {t} | {s} | {trig:.2f} / {stop:.2f} | {c} | {'—' if r is None else f'{r:+.2f}'} | {how} |")
    L.append("")
    agg = defaultdict(list)
    for t, s, trig, stop, c, r, how in rows:
        if r is not None:
            agg[c].append(r)
    if agg:
        L += ["| refused by | filled if taken | mean gross R | best | worst |", "|---|---|---|---|---|"]
        for c, v in sorted(agg.items(), key=lambda kv: -len(kv[1])):
            L.append(f"| {c} | {len(v)} | {sum(v) / len(v):+.2f} | {max(v):+.2f} | {min(v):+.2f} |")
        L.append("")

    for st in five:
        if st.get("state") != "5M PULLBACK":
            continue
        trig, stop = num(st.get("trigger")), num(st.get("stop"))
        t0 = et(st["ts_et"]).replace(second=0)
        r, how = simulate(bars.get(st["symbol"], []), t0 + timedelta(minutes=5), trig, stop, ttl_min=5)
        cohort_rows.append({"day": day, "ts_et": st["ts_et"], "symbol": st["symbol"], "cohort": "five_min_pb",
                            "trigger": trig, "stop": stop, "gross_r": None if r is None else round(r, 3), "how": how})

    taken = [o for o in orders if o.get("fill_price")]
    L += [f"## The bot's own trades — {len(taken)} filled", ""]
    for o in taken:
        fp, ep, pr = num(o["fill_price"]), num(o.get("exit_price")), num(o.get("planned_risk"))
        qty = num(o.get("filled_qty")) or num(o["shares"])
        pnl = (ep - fp) * qty if ep is not None else None
        comm = (num(o.get("commission_in")) or 0) + (num(o.get("commission_out")) or 0)
        L.append(f"- {o['symbol']} {qty:g} @ {fp:.2f} → {'held' if ep is None else f'{ep:.2f}'} "
                 + ("" if pnl is None else f"· ${pnl:+.2f} on the fills, {pnl / pr:+.2f} R · commission ${comm:.2f}"))
    L.append("")

    L += [f"## Your trades beside the bot — {len(manual)} recorded", ""]
    for m in manual:                                   # research/trade-journal/journal.csv rows
        sym, me = (m.get("sym") or "").upper(), num(m.get("entry"))
        near = [r for r in rows if r[1] == sym]
        L.append(f"- **{sym}** {m.get('shares')} @ {m.get('entry')} ({m.get('entry_hhmm')}) → "
                 f"{m.get('exit') or 'open'} ({m.get('exit_hhmm') or '—'}) · {m.get('note') or ''}")
        for t, s, trig, stop, c, r, how in near:
            L.append(f"    - bot plan {t} {trig:.2f}/{stop:.2f}: {c}, if taken {'—' if r is None else f'{r:+.2f} R'}")
        if not near:
            L.append("    - the bot armed no plan on this name — the detector or the watchlist missed it")
    L.append("")

    calls = read(dd, "desk_calls.csv") if (dd / "desk_calls.csv").exists() else []
    L += desk_calls_section(calls, bars, rows)

    # cohort ledger
    cf = DAILY / "cohorts.csv"
    old = []
    if cf.exists() and cf.read_text().strip():
        with cf.open() as fh:
            old = [r for r in csv.DictReader(fh) if r["day"] != day]
    allr = old + cohort_rows
    with cf.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["day", "ts_et", "symbol", "cohort", "trigger", "stop", "gross_r", "how"])
        w.writeheader(); w.writerows(allr)
    L += ["## Cohorts toward their prospective test (all days so far)", "",
          "| cohort | rule it would test | plans | filled | mean gross R | to go |", "|---|---|---|---|---|---|"]
    for c, rule in WATCHED.items():
        v = [num(r["gross_r"]) for r in allr if r["cohort"] == c]
        f = [x for x in v if x is not None]
        L.append(f"| {c} | {rule} | {len(v)} | {len(f)} | {'—' if not f else f'{sum(f) / len(f):+.2f}'} | "
                 f"{max(0, PROSPECTIVE_N - len(f))} |")
    L += ["", "Gross R before costs: the ten-year tests put costs near 0.27-0.39 R a trade, so a cohort needs "
          "a gross mean well above that to matter. Nothing on this page changes a rule.", ""]
    L += shadow_section(day)
    text = "\n".join(L)
    (dd / "review.md").write_text(text)
    return text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("day", nargs="?")
    ap.add_argument("--latest", action="store_true")
    args = ap.parse_args(argv)
    day = args.day
    if args.latest or not day:
        days = sorted(p.name for p in DAILY.iterdir() if p.is_dir() and (p / "export.json").exists())
        if not days:
            print("no exported day under research/daily/"); return 1
        day = days[-1]
    print(review(day))
    print(f"\nwritten research/daily/{day}/review.md · research/daily/cohorts.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
