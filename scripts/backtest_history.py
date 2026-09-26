#!/usr/bin/env python3
"""The desk's own strategy over ten years of gappers, pre-market included.

Why this exists (2026-09-26). The seven-session backtest (`backtest_recent.py`)
runs on Yahoo, whose 1-minute chart API returns ZERO volume for every
pre-market bar — verified on GRML 2026-09-17..25 — so pre-market VWAP and the
pullback-volume gate could not be judged, and pre-market is where the owner
expects the money. Consolidated feeds carry pre-market volume: Alpaca's SIP
feed (the keys already in the Mac's .env, used for headlines) and IBKR
itself. This script needs one of them, so it runs on the Mac.

What it does, in one strict left-to-right pass per symbol-day:
  * universe — `research/first-pullback-edge/data/candidate_days.csv`:
    25,716 gapper-days 2016-02 .. 2026-08, survivorship-free (open $2-20,
    gap >= 10 %, 20-day dollar volume >= $250k), reverse-split days dropped;
    plus, with --ledger, every symbol-day the live desk decided on
  * bars — Alpaca SIP 1-minute, 04:00-16:00 ET, raw prices, one request per
    session for all its names, cached in data/cache/history/
  * rules — the desk's FirstPullbackDetector, FILTERS.md gates 1 and 4, Layer 2
    with VWAP anchored at 04:00 WITH pre-market volume (the live desk's
    convention), A11 (MACD flags in regular hours), A10 entry (touch within 3
    bars; a bar opening above the stop-limit's cap is NO fill), stops that the
    next bar opens through fill at its open, flatten 11:30
  * costs — IBKR fixed commissions and one cent of slippage a side, at the
    desk's $20 sizing (`backtest_recent.cost_r`); gross and net both printed

It prints: plan-level cohorts per window; the one-position portfolio per
year and per window; a WALK-FORWARD OPTIMIZER (every combination of the five
chart/trend gates x three exits x three windows, chosen on the TRAIN years,
scored once on the TEST years, beside the current rules on the same TEST
years); and, with --ledger, the calibration of the simulator against the live
fills (predicted R vs realised R, trade by trade).

Known limits: the universe is picked on the 09:30 gap, so a name that ran in
pre-market and faded before the open is missing (this FAVOURS pre-market);
no float, no catalyst, no pillar count, no halts, no spread rule.

    python3 scripts/backtest_history.py --sample 300          # ~3 min, a random 300 sessions
    python3 scripts/backtest_history.py                       # all of it, ~20-40 min the first time
    python3 scripts/backtest_history.py --ledger data/journal.sqlite --since 2026-09-01
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import os
import random
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

import backtest_recent as E  # noqa: E402  the engine: detector, gates, simulate, costs

UNIVERSE_CSV = ROOT / "research" / "first-pullback-edge" / "data" / "candidate_days.csv"
CACHE = ROOT / "data" / "cache" / "history"
CHART_GATES = ("vwap", "ema9", "macd", "volume", "rising")
WINDOWS = ("pre-market", "regular", "both")


# ------------------------------------------------------------------ universe
def load_universe(since: str | None, until: str | None) -> dict[str, dict[str, float]]:
    """{day: {sym: prev_close}} from the committed candidate-day list."""
    out: dict[str, dict[str, float]] = defaultdict(dict)
    with open(UNIVERSE_CSV) as f:
        for r in csv.DictReader(f):
            d = r["day"]
            if (since and d < since) or (until and d > until):
                continue
            if r.get("split_on_day") in ("True", "true", "1"):
                continue
            try:
                out[d][r["sym"]] = float(r["prev_close"])
            except (TypeError, ValueError):
                continue
    return dict(out)


def ledger_days(path: str, since: str | None) -> dict[str, dict[str, float | None]]:
    c = sqlite3.connect(path)
    out: dict[str, dict] = defaultdict(dict)
    for sym, d in c.execute("SELECT DISTINCT symbol, substr(ts_et,1,10) FROM decisions"):
        if since and d < since:
            continue
        out[d][sym] = None                          # previous close read from the bars' own day before
    return dict(out)


# ------------------------------------------------------------------ bars
def alpaca_client():
    from momentum_platform.datasources.alpaca_source import client_from_env
    return client_from_env(feed=os.environ.get("HISTORY_FEED", "sip"))


def fetch_day(client, day: str, symbols: list[str], cache: Path) -> dict[str, list]:
    """All symbols of one session, 04:00-16:00 ET, raw prices, one request
    (paged). Cached per day; a symbol with no bars is cached as empty."""
    f = cache / f"{day}.json"
    have = json.loads(f.read_text()) if f.exists() else {}
    need = [s for s in symbols if s not in have]
    if need:
        start = datetime.fromisoformat(f"{day}T04:00:00").replace(tzinfo=E.ET).astimezone(timezone.utc)
        end = datetime.fromisoformat(f"{day}T16:00:00").replace(tzinfo=E.ET).astimezone(timezone.utc)
        for i in range(0, len(need), 100):
            chunk = need[i:i + 100]
            token = None
            got: dict[str, list] = {s: [] for s in chunk}
            while True:
                for attempt in range(4):
                    try:
                        payload = client._get(client.data_base, "/v2/stocks/bars", {
                            "symbols": ",".join(chunk), "timeframe": "1Min",
                            "start": start.isoformat().replace("+00:00", "Z"),
                            "end": end.isoformat().replace("+00:00", "Z"),
                            "limit": 10000, "feed": client.feed, "adjustment": "raw", "page_token": token})
                        break
                    except Exception as exc:                          # noqa: BLE001
                        if "429" in str(exc) and attempt < 3:
                            time.sleep(20 * (attempt + 1)); continue
                        raise
                for sym, rows in (payload.get("bars") or {}).items():
                    got.setdefault(sym, []).extend([[r["t"], r["o"], r["h"], r["l"], r["c"], r["v"]] for r in rows or []])
                token = payload.get("next_page_token")
                if not token:
                    break
            have.update(got)
        cache.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(have))
    return {s: have.get(s, []) for s in symbols}


def to_rows(raw: list) -> list:
    out = []
    for t, o, h, l, c, v in raw:
        ts = datetime.fromisoformat(str(t).replace("Z", "+00:00")).astimezone(E.ET)
        out.append((ts, float(o), float(h), float(l), float(c), float(v or 0)))
    out.sort(key=lambda r: r[0])
    return out


# ------------------------------------------------------------------ rules
def current_rules(p: dict) -> bool:
    """What the desk refuses on today: price, still-rising, VWAP, 9 EMA,
    pullback volume, and MACD only pre-market (A11)."""
    red = set(p["red"])
    if p["window"] == "regular":
        red.discard("macd")
    return not red


def rule_set(required: tuple[str, ...]):
    def ok(p):
        return not [g for g in p["red"] if g in ("price",) or g in required]
    return ok


def in_window(p, w):
    return w == "both" or p["window"] == w


def portfolio_net(plans, allowed, exit_, window="both", net=True):
    key = exit_ + ("_net" if net else "")
    sub = [dict(p, **{exit_: p[key]}) for p in plans if p["touched"] and in_window(p, window)]
    return E.portfolio(sub, allowed, exit_)


def stats(values: list[float]) -> str:
    if not values:
        return "n 0"
    wins = sum(1 for v in values if v > 0)
    return f"n {len(values):>5}  mean {mean(values):+.3f} R  total {sum(values):+8.1f} R  win {wins / len(values):.0%}"


# ------------------------------------------------------------------ report
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since"); ap.add_argument("--until")
    ap.add_argument("--sample", type=int, help="a seeded random sample of this many sessions")
    ap.add_argument("--seed", type=int, default=20260926)
    ap.add_argument("--split", default="2024-01-01", help="walk-forward: train before, test from this date")
    ap.add_argument("--ledger", help="add the live desk's symbol-days and calibrate against its fills")
    ap.add_argument("--json", help="write every plan and table here")
    ap.add_argument("--cache", default=str(CACHE))
    args = ap.parse_args(argv)

    uni = load_universe(args.since, args.until)
    if args.ledger:
        for d, syms in ledger_days(args.ledger, args.since).items():
            uni.setdefault(d, {}).update({s: v for s, v in syms.items() if s not in uni.get(d, {})})
    days = sorted(uni)
    if args.sample and args.sample < len(days):
        days = sorted(random.Random(args.seed).sample(days, args.sample))
    try:
        client = alpaca_client()
    except Exception as exc:                                         # noqa: BLE001
        print(f"no Alpaca credentials: {exc}\nPut ALPACA_KEY_ID and ALPACA_SECRET_KEY in .env (the headline keys).")
        return 2
    cache = Path(args.cache)
    print(f"{len(days)} sessions, {sum(len(uni[d]) for d in days)} symbol-days · feed {client.feed} · cache {cache}")

    plans: list[dict] = []
    t0 = time.monotonic()
    for k, d in enumerate(days, 1):
        try:
            bars = fetch_day(client, d, sorted(uni[d]), cache)
        except Exception as exc:                                     # noqa: BLE001
            print(f"  {d}: fetch failed ({str(exc)[:120]})"); continue
        for sym, raw in bars.items():
            rows = [r for r in to_rows(raw) if E.dtime(4, 0) <= r[0].time() < E.dtime(16, 0)]
            if len(rows) < 40:
                continue
            pc = uni[d].get(sym) or rows[0][1]
            plans += E.plans_for_day(sym, rows, pc, desk_vwap=True, gap_miss=True)
        if k % 50 == 0:
            print(f"  {k}/{len(days)} sessions · {len(plans)} plans · {time.monotonic() - t0:.0f}s", flush=True)
    for p in plans:
        p["year"] = p["day"][:4]
    trig = [p for p in plans if p["touched"]]
    print(f"\n{len(plans)} plans, {len(trig)} filled under A10, {sum(p['gap_missed'] for p in plans)} gapped over "
          f"the entry cap (no fill)\n")

    # 1. plan level, current rules, per window — gross and net
    print("PLAN LEVEL · current rules (A11) · every plan scored as if taken")
    for w in ("pre-market", "regular"):
        ok = [p for p in trig if p["window"] == w and current_rules(p)]
        allp = [p for p in trig if p["window"] == w]
        for ex in ("fixed", "trail", "be"):
            print(f"  {w:<11} {ex:<6} rules gross {stats([p[ex] for p in ok])}")
            print(f"  {'':<11} {'':<6} rules net   {stats([p[ex + '_net'] for p in ok])}")
        print(f"  {w:<11} every plan, trail net {stats([p['trail_net'] for p in allp])}\n")

    # 2. portfolio per year, one position, net
    print("PORTFOLIO · one position · current rules · NET of costs · R per year")
    years = sorted({p["year"] for p in plans})
    print(f"  {'year':<6}" + "".join(f"{w + ' ' + ex:>22}" for w in ("pre-market", "regular", "both") for ex in ("trail",)))
    for y in years:
        yp = [p for p in plans if p["year"] == y]
        cells = [portfolio_net(yp, current_rules, "trail", w) for w in ("pre-market", "regular", "both")]
        print(f"  {y:<6}" + "".join(f"{c['total']:>+14.1f} ({c['trades']:>4})" for c in cells))
    tot = {w: {ex: portfolio_net(plans, current_rules, ex, w) for ex in ("fixed", "trail", "be")} for w in WINDOWS}
    for w in WINDOWS:
        print(f"  all {w:<11} fixed {tot[w]['fixed']['total']:+.1f} · trail {tot[w]['trail']['total']:+.1f} · "
              f"BE+2R {tot[w]['be']['total']:+.1f} R over {tot[w]['trail']['trades']} trades")

    # 3. walk-forward optimizer
    train = [p for p in plans if p["day"] < args.split]
    test = [p for p in plans if p["day"] >= args.split]
    print(f"\nWALK-FORWARD OPTIMIZER · train < {args.split} ({len({p['day'] for p in train})} sessions) · "
          f"test >= {args.split} ({len({p['day'] for p in test})} sessions) · NET · one position")
    grid = []
    for r in range(len(CHART_GATES) + 1):
        for req in itertools.combinations(CHART_GATES, r):
            for ex in ("fixed", "trail", "be"):
                for w in WINDOWS:
                    tr = portfolio_net(train, rule_set(req), ex, w)
                    if tr["trades"] >= 50:
                        grid.append((tr["total"] / tr["trades"], req, ex, w, tr))
    grid.sort(key=lambda g: g[0], reverse=True)
    print(f"  {len(grid)} configurations with >= 50 train trades")
    print(f"  {'rank':<5}{'gates required':<34}{'exit':<7}{'window':<12}{'train R/trade':>14}{'test R/trade':>14}{'test trades':>12}")
    for i, (score, req, ex, w, tr) in enumerate(grid[:8], 1):
        te = portfolio_net(test, rule_set(req), ex, w)
        te_mean = te["total"] / te["trades"] if te["trades"] else float("nan")
        print(f"  {i:<5}{('+'.join(req) or 'none'):<34}{ex:<7}{w:<12}{score:>+14.3f}{te_mean:>+14.3f}{te['trades']:>12}")
    for ex in ("trail",):
        for w in WINDOWS:
            tr = portfolio_net(train, current_rules, ex, w); te = portfolio_net(test, current_rules, ex, w)
            print(f"  {'now':<5}{'current rules (A11)':<34}{ex:<7}{w:<12}"
                  f"{(tr['total'] / tr['trades'] if tr['trades'] else float('nan')):>+14.3f}"
                  f"{(te['total'] / te['trades'] if te['trades'] else float('nan')):>+14.3f}{te['trades']:>12}")

    # 4. calibration against the live fills
    if args.ledger:
        print("\nFORECAST vs ACTUALS · the simulator on the live desk's own taken trades")
        c = sqlite3.connect(args.ledger); c.row_factory = sqlite3.Row
        rows = c.execute("""SELECT o.symbol, o.trigger, o.stop, o.fill_price, o.exit_price, o.filled_qty, o.shares,
                                   o.planned_risk, d.ts_et FROM orders o JOIN decisions d USING(decision_id)
                            WHERE o.fill_price IS NOT NULL AND o.exit_price IS NOT NULL ORDER BY o.fill_ts""").fetchall()
        by = {(p["sym"], p["day"], round(p["entry"], 2), round(p["stop"], 2)): p for p in plans}
        pred, live = [], []
        for r in rows:
            qty = r["filled_qty"] or r["shares"]
            lr = round((r["exit_price"] - r["fill_price"]) * qty / r["planned_risk"], 2) if r["planned_risk"] else None
            p = by.get((r["symbol"], r["ts_et"][:10], round(r["trigger"], 2), round(r["stop"], 2)))
            sim = p["trail_net"] if p and p["touched"] else None
            print(f"  {r['ts_et'][:16]} {r['symbol']:<6} {r['trigger']:.2f}/{r['stop']:.2f}  simulated "
                  f"{('%+.2f' % sim) if sim is not None else '—':>6}  live {('%+.2f' % lr) if lr is not None else '—':>6}")
            if sim is not None and lr is not None:
                pred.append(sim); live.append(lr)
        if pred:
            print(f"  {len(pred)} matched: simulated mean {mean(pred):+.2f} R · live mean {mean(live):+.2f} R · "
                  f"gap {mean(live) - mean(pred):+.2f} R per trade")
    if args.json:
        Path(args.json).write_text(json.dumps({"plans": plans}, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
