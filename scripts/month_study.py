#!/usr/bin/env python3
"""The month study: our screeners' last month, from the flexible strategy to the solid one.

Preregistered in research/month-study/PREREGISTRATION.md (written before the
first run). The owner, 2026-10-09: take every name our screeners showed in the
last month, run our strategy loose and then stricter, and find the combination
that would have made money — for a paper track record that measures accuracy.

    python3 scripts/month_study.py                          # the preregistered run
    python3 scripts/month_study.py --daily /tmp/x --since 2026-09-04 --until 2026-09-04 --quiet   # smoke test

What it does, in the preregistration's order:
  * universe — every symbol-day in research/daily/<day>/screener.csv,
    board.csv and decisions.csv (the owner's ledger export);
  * bars — Alpaca SIP 1-minute 04:00-16:00 ET (backtest_history.fetch_day,
    cached in data/cache/history/); daily bars for the previous close and the
    30-day average volume; Alpaca headlines; the desk's own float;
  * plans — backtest_recent.plans_for_day(desk_vwap=True, gap_miss=True): the
    desk's detector, A10 fills, gap-through stops — in two regimes, the bot's
    window (07:00-11:20, flatten 11:30) and an open one (04:00-15:50, 15:55);
  * costs — live (primary), old, and measured (the desk's own bid/ask);
  * the ladder — L0 flexible, one lever at a time, the greedy build on the
    selection sessions (09-08..10-01), then the checks on the best found: the
    holdout (10-02..10-08), random entries on the same names, one position.

It writes research/month-study/results.json and prints the tables.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import random
import statistics
import sys
import time
from collections import defaultdict
from datetime import date, datetime, time as dtime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

import backtest_history as H  # noqa: E402  fetch_day, to_rows, alpaca_client
import backtest_recent as E  # noqa: E402  plans_for_day, simulate, cost_r, portfolio

DAILY = ROOT / "research" / "daily"
OUT = ROOT / "research" / "month-study"
CACHE_BARS = ROOT / "data" / "cache" / "history"
CACHE = ROOT / "data" / "cache" / "month_study"

SINCE, UNTIL = "2026-09-08", "2026-10-08"
SEL_END, HOLD_START = "2026-10-01", "2026-10-02"
MIN_SEL, MIN_HOLD, STOP_GAIN = 30, 10, 0.02
EXITS = ("fixed", "trail", "be")
REGIMES = {
    "bot": (dtime(7, 0), dtime(11, 20), dtime(11, 30)),
    "open": (dtime(4, 0), dtime(15, 50), dtime(15, 55)),
}
# (id, levels): the preregistration's lever table, levels in order of strictness
LEVERS = [("G1", [True]), ("G4", [True]), ("VW", [True]), ("E9", [True]), ("MC", [True]), ("PV", [True]),
          ("GN", [0.10, 0.20, 0.30, 0.50]), ("RV", [0.5, 1.0, 2.0, 5.0]), ("FL", [20e6, 10e6]), ("NW", [True]),
          ("SW", [1.0, 2.0, 3.0]), ("WN", ["pre-market", "regular"]), ("FP", [True])]
GATE_OF = {"G1": "price", "G4": "rising", "VW": "vwap", "E9": "ema9", "MC": "macd", "PV": "volume"}
BOT_RULES = {"G1": True, "G4": True, "VW": True, "E9": True, "MC": True, "PV": True}


# ------------------------------------------------------------------ universe
def _read_csv(path: Path) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def load_universe(daily: Path, since: str, until: str) -> dict:
    """{day: {sym: {"float": shares or None, "from": set of sources}}}."""
    uni: dict = {}
    for folder in sorted(p for p in daily.iterdir() if p.is_dir()):
        d = folder.name
        if not (since <= d <= until):
            continue
        day = uni.setdefault(d, {})
        for src, fname in (("screener", "screener.csv"), ("board", "board.csv"), ("decision", "decisions.csv")):
            for r in _read_csv(folder / fname):
                sym = (r.get("symbol") or "").strip().upper()
                if not sym:
                    continue
                e = day.setdefault(sym, {"float": None, "from": set()})
                e["from"].add(src)
                try:
                    fl = float(r.get("float_shares") or "nan")
                    if fl == fl and fl > 0:
                        e["float"] = fl if e["float"] is None else min(e["float"], fl)
                except ValueError:
                    pass
        if not day:
            del uni[d]
    return uni


# ------------------------------------------------------------------ data
def _paged(client, path: str, params: dict, key: str) -> list:
    out, token = [], None
    while True:
        for attempt in range(4):
            try:
                payload = client._get(client.data_base, path, dict(params, page_token=token))
                break
            except Exception as exc:                                  # noqa: BLE001
                if "429" in str(exc) and attempt < 3:
                    time.sleep(20 * (attempt + 1)); continue
                raise
        got = payload.get(key) or []
        if isinstance(got, dict):
            out.append(got)
        else:
            out.extend(got)
        token = payload.get("next_page_token")
        if not token:
            return out


def fetch_daily(client, symbols: list[str], start: str, end: str) -> dict:
    """{sym: [[YYYY-MM-DD, close, volume], ...]} raw daily bars, cached."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"daily_{start}_{end}.json"
    have = json.loads(f.read_text()) if f.exists() else {}
    need = [s for s in symbols if s not in have]
    for i in range(0, len(need), 100):
        chunk = need[i:i + 100]
        pages = _paged(client, "/v2/stocks/bars", {"symbols": ",".join(chunk), "timeframe": "1Day",
                                                     "start": start, "end": end, "limit": 10000,
                                                     "feed": client.feed, "adjustment": "raw"}, "bars")
        got = {s: [] for s in chunk}
        for page in pages:
            for sym, rows in page.items():
                got.setdefault(sym, []).extend([[r["t"][:10], r["c"], r["v"]] for r in rows or []])
        have.update(got)
    f.write_text(json.dumps(have))
    return have


def prev_and_adv(rows: list, day: str) -> tuple:
    before = [r for r in rows if r[0] < day]
    if not before:
        return None, None
    vols = [r[2] for r in before[-30:] if r[2]]
    return float(before[-1][1]), (statistics.mean(vols) if vols else None)


def fetch_news(client, symbols: list[str], start: str, end: str) -> dict:
    """{sym: [published_at ISO UTC, ...]}, cached."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"news_{start}_{end}.json"
    have = json.loads(f.read_text()) if f.exists() else {}
    need = [s for s in symbols if s not in have]
    for i in range(0, len(need), 25):
        chunk = need[i:i + 25]
        items = _paged(client, "/v1beta1/news", {"symbols": ",".join(chunk), "start": start + "T00:00:00Z",
                                                 "end": end + "T23:59:59Z", "limit": 50, "sort": "asc"}, "news")
        got = {s: [] for s in chunk}
        for it in items:
            for s in it.get("symbols") or []:
                if s in got:
                    got[s].append(it.get("created_at") or it.get("updated_at"))
        have.update(got)
    f.write_text(json.dumps(have))
    return have


def desk_spreads(daily: Path, day: str) -> dict:
    """{(sym, 'HH:MM' ET): (bid, ask)} from the desk's board_bars, if exported."""
    f = daily / day / "board_bars.csv.gz"
    out = {}
    if not f.exists():
        return out
    with gzip.open(f, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                bid, ask = float(r["bid"]), float(r["ask"])
            except (TypeError, ValueError):
                continue
            if bid > 0 and ask >= bid:
                ts = datetime.fromisoformat(r["ts"].replace("Z", "+00:00")).astimezone(E.ET)
                out[(r["symbol"], ts.strftime("%H:%M"))] = (bid, ask)
    return out


def desk_closes(daily: Path, day: str) -> dict:
    f = daily / day / "board_bars.csv.gz"
    out = {}
    if not f.exists():
        return out
    with gzip.open(f, "rt", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                ts = datetime.fromisoformat(r["ts"].replace("Z", "+00:00")).astimezone(E.ET)
                out[(r["symbol"], ts.strftime("%H:%M"))] = float(r["close"])
            except (TypeError, ValueError):
                continue
    return out


# ------------------------------------------------------------------ costs
def cost_with(model: str, entry: float, stop: float, stop_exit: bool, pm: bool, dv5) -> float:
    saved = E.COST_MODEL
    E.COST_MODEL = model
    try:
        return E.cost_r(entry, stop, stop_exit, pm=pm, dv5=dv5)
    finally:
        E.COST_MODEL = saved


def cost_measured(entry: float, stop: float, stop_exit: bool, half: float) -> float:
    rps = entry - stop
    if rps <= 0:
        return 0.0
    shares = E.live_shares(entry, stop)
    comm = 2 * min(max(1.0, 0.005 * shares), max(1.0, 0.01 * shares * entry))
    fric = shares * (half + 0.01) * (2 if stop_exit else 1)
    return round((comm + fric) / (shares * rps), 3)


# ------------------------------------------------------------------ plans
def build_plans(client, uni: dict, daily: Path, regime: str, info: dict, rows_out: dict) -> list:
    pm_start, cutoff, flat = REGIMES[regime]
    E.PM_START, E.CUTOFF, E.FLAT = pm_start, cutoff, flat
    E.COST_MODEL = "live"
    plans = []
    for d in sorted(uni):
        syms = sorted(uni[d])
        bars = H.fetch_day(client, d, syms, CACHE_BARS)
        spreads = desk_spreads(daily, d)
        for sym in syms:
            rows = [r for r in H.to_rows(bars.get(sym) or []) if E.dtime(4, 0) <= r[0].time() < E.dtime(16, 0)]
            if len(rows) < 40:
                continue
            pc, adv = info["daily"].get((d, sym), (None, None))
            if not pc:
                continue                       # no previous close: the gain cannot be read
            rows_out[(d, sym)] = rows
            for p in E.plans_for_day(sym, rows, pc, desk_vwap=True, gap_miss=True):
                p["regime"] = regime
                p["rv"] = (p["cum_vol"] / adv) if adv else None
                fl = uni[d][sym]["float"]
                if fl is None:
                    so = info["sec"].get(sym)
                    fl = so if (so is not None and so < 20e6) else None   # an upper bound proves only "under"
                p["float"] = fl
                cut = p["ts"].astimezone(timezone.utc)
                prev_close_utc = (datetime.fromisoformat(d).replace(tzinfo=E.ET) - timedelta(days=1)).replace(
                    hour=16).astimezone(timezone.utc)
                heads = info["news"].get(sym) or []
                p["news"] = any(prev_close_utc <= datetime.fromisoformat(h.replace("Z", "+00:00")) <= cut
                                for h in heads if h)
                p["first"] = p["pb_index"] == 1
                p["sources"] = sorted(uni[d][sym]["from"])
                if p["touched"]:
                    q = spreads.get((sym, p["t"]))
                    for v in EXITS:
                        stop_exit = p[v + "_why"] in ("stop", "trail")
                        p[v + "_old"] = round(p[v] - cost_with("old", p["entry"], p["stop"], stop_exit, p["pm"], p["dv5"]), 3)
                        p[v + "_meas"] = (round(p[v] - cost_measured(p["entry"], p["stop"], stop_exit, (q[1] - q[0]) / 2), 3)
                                          if q else None)
                plans.append(p)
    return plans


# ------------------------------------------------------------------ levers
def passes(p: dict, config: dict) -> bool:
    for lid, lvl in config.items():
        if lid in GATE_OF:
            if GATE_OF[lid] in p["red"]:
                return False
        elif lid == "GN":
            if p.get("gain") is None or p["gain"] < lvl:
                return False
        elif lid == "RV":
            if p.get("rv") is None or p["rv"] < lvl:
                return False
        elif lid == "FL":
            if p.get("float") is None or p["float"] >= lvl:
                return False
        elif lid == "NW":
            if not p.get("news"):
                return False
        elif lid == "SW":
            if p["stop_pct"] < lvl:
                return False
        elif lid == "WN":
            if p["window"] != lvl:
                return False
        elif lid == "FP":
            if not p.get("first"):
                return False
    return True


def evaluate(plans: list, config: dict, exit_: str, cost: str = "net") -> dict:
    key = exit_ + {"net": "_net", "gross": "", "old": "_old", "meas": "_meas"}[cost]
    vals = [p[key] for p in plans if p["touched"] and passes(p, config) and p.get(key) is not None]
    gross = [p[exit_] for p in plans if p["touched"] and passes(p, config) and p.get(key) is not None]
    if not vals:
        return {"n": 0, "mean": None, "total": 0.0, "gross": None, "win": None}
    return {"n": len(vals), "mean": round(statistics.mean(vals), 3), "total": round(sum(vals), 2),
            "gross": round(statistics.mean(gross), 3), "win": round(sum(1 for v in vals if v > 0) / len(vals), 2)}


def stricter(lid: str, new, old) -> bool:
    if lid in ("GN", "RV", "SW"):
        return new > old
    if lid == "FL":
        return new < old
    return False


def label(config: dict) -> str:
    if not config:
        return "L0 (no lever)"
    parts = []
    for lid, lvl in config.items():
        if lvl is True:
            parts.append(lid)
        elif lid == "GN":
            parts.append(f"GN≥{lvl:.0%}")
        elif lid == "RV":
            parts.append(f"RV≥{lvl:g}")
        elif lid == "FL":
            parts.append(f"FL<{lvl / 1e6:.0f}M")
        elif lid == "SW":
            parts.append(f"SW≥{lvl:g}%")
        else:
            parts.append(f"{lid}={lvl}")
    return " + ".join(parts)


def greedy(sel: list, exit_: str, counter: list) -> list:
    config, steps = {}, []
    cur = evaluate(sel, config, exit_)
    steps.append({"config": {}, "label": label({}), "exit": exit_, **cur})
    while True:
        best = None
        moves = [(config, ex) for ex in EXITS if ex != exit_]
        for lid, levels in LEVERS:
            for lvl in levels:
                if lid in config and not stricter(lid, lvl, config[lid]):
                    continue
                c2 = dict(config); c2[lid] = lvl
                moves += [(c2, ex) for ex in EXITS]
        for c2, ex in moves:
            r = evaluate(sel, c2, ex)
            counter[0] += 1
            if r["n"] >= MIN_SEL and r["mean"] is not None and (best is None or r["mean"] > best[2]["mean"]):
                best = (c2, ex, r)
        if best is None or cur["mean"] is None or best[2]["mean"] - cur["mean"] < STOP_GAIN:
            return steps
        config, exit_, cur = best[0], best[1], best[2]
        steps.append({"config": dict(config), "label": label(config), "exit": exit_, **cur})


# ------------------------------------------------------------------ checks
def random_baseline(trades: list, rows_by: dict, regime: str, exit_: str, k: int = 20, seed: int = 20261009) -> dict:
    """For each trade, k entries at random minutes of the same symbol-day in the
    same window, the same stop distance in %, the same exit; gross R."""
    pm_start, cutoff, flat = REGIMES[regime]
    E.FLAT = flat
    rng = random.Random(seed)
    out = []
    for p in trades:
        rows = rows_by[(p["day"], p["sym"])]
        lo, hi = (pm_start, E.RTH_START) if p["window"] == "pre-market" else (E.RTH_START, cutoff)
        idx = [i for i, r in enumerate(rows[:-1]) if lo <= r[0].time() < hi]
        if not idx:
            continue
        for _ in range(k):
            i = rng.choice(idx)
            entry = rows[i][4]
            stop = entry * (1 - p["stop_pct"] / 100)
            if entry <= stop:
                continue
            r, _why, _t = E.simulate(rows[i + 1:], entry, stop, exit_)
            out.append(r)
    strat = [p[exit_] for p in trades]
    return {"n_random": len(out), "random_gross": round(statistics.mean(out), 3) if out else None,
            "strategy_gross": round(statistics.mean(strat), 3) if strat else None,
            "difference": round(statistics.mean(strat) - statistics.mean(out), 3) if out and strat else None}


def one_position(plans: list, config: dict, exit_: str) -> dict:
    sub = [dict(p, **{exit_: p[exit_ + "_net"]}) for p in plans if p["touched"] and passes(p, config)]
    r = E.portfolio(sub, lambda p: True, exit_)
    return {"trades": r["trades"], "total": r["total"], "days": r["days"], "days_pos": r["days_pos"]}


def fidelity(uni: dict, daily: Path, rows_by: dict) -> dict:
    diffs = []
    for d in uni:
        closes = desk_closes(daily, d)
        if not closes:
            continue
        for (dd, sym), rows in rows_by.items():
            if dd != d:
                continue
            for r in rows:
                c = closes.get((sym, r[0].strftime("%H:%M")))
                if c and r[4]:
                    diffs.append(abs(c - r[4]) / r[4])
    return {"bars_compared": len(diffs), "median_rel_diff": round(statistics.median(diffs), 5) if diffs else None}


# ------------------------------------------------------------------ main
def fmt(r: dict) -> str:
    if not r or not r.get("n"):
        return "n     0"
    return (f"n {r['n']:>5}  net {r['mean']:+.3f} R/trade  total {r['total']:+8.1f} R  "
            f"gross {r['gross']:+.3f}  win {r['win']:.0%}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--daily", default=str(DAILY))
    ap.add_argument("--since", default=SINCE)
    ap.add_argument("--until", default=UNTIL)
    ap.add_argument("--out", default=str(OUT / "results.json"))
    ap.add_argument("--quiet", action="store_true", help="smoke test: counts only, no R figures")
    args = ap.parse_args(argv)
    daily = Path(args.daily)
    uni = load_universe(daily, args.since, args.until)
    if not uni:
        print(f"no exported days between {args.since} and {args.until} in {daily} — run the export on the Mac first")
        return 1
    n_symdays = sum(len(v) for v in uni.values())
    src_counts = defaultdict(int)
    for v in uni.values():
        for e in v.values():
            for s in e["from"]:
                src_counts[s] += 1
    print(f"universe: {len(uni)} sessions, {n_symdays} symbol-days "
          f"({', '.join(f'{k} {v}' for k, v in sorted(src_counts.items()))})")
    client = H.alpaca_client()
    syms = sorted({s for v in uni.values() for s in v})
    d0 = (date.fromisoformat(min(uni)) - timedelta(days=60)).isoformat()
    dl = fetch_daily(client, syms, d0, max(uni))
    info = {"daily": {}, "news": {}, "sec": {}}
    for d, v in uni.items():
        for s in v:
            info["daily"][(d, s)] = prev_and_adv(dl.get(s) or [], d)
    n0 = (date.fromisoformat(min(uni)) - timedelta(days=1)).isoformat()
    try:
        info["news"] = fetch_news(client, syms, n0, max(uni))
    except Exception as exc:                                          # noqa: BLE001
        print(f"news unavailable: {str(exc)[:160]} — NW fails closed for every plan")
    sec_f = CACHE / "sec_shares_outstanding.json"
    info["sec"] = json.loads(sec_f.read_text()) if sec_f.exists() else {}

    rows_by: dict = {}
    plans = {rg: build_plans(client, uni, daily, rg, info, rows_by) for rg in REGIMES}
    counts = {rg: {"plans": len(ps), "filled": sum(p["touched"] for p in ps)} for rg, ps in plans.items()}
    print("plans: " + " · ".join(f"{rg} {c['plans']} armed, {c['filled']} filled" for rg, c in counts.items()))
    fid = fidelity(uni, daily, rows_by)
    print(f"SIP vs the desk's own bars: {fid['bars_compared']} minutes compared, "
          f"median difference {fid['median_rel_diff']}")
    if args.quiet:
        return 0

    sel = {rg: [p for p in ps if p["day"] <= SEL_END] for rg, ps in plans.items()}
    hold = {rg: [p for p in ps if p["day"] >= HOLD_START] for rg, ps in plans.items()}
    counter = [0]
    res = {"universe": {"sessions": len(uni), "symbol_days": n_symdays, "by_source": dict(src_counts)},
           "plans": counts, "fidelity": fid}

    print("\n1 · FLEXIBLE (L0) — every plan, selection sessions")
    l0 = {}
    for rg in REGIMES:
        for ex in EXITS:
            for w in (None, "pre-market", "regular"):
                cfg = {} if w is None else {"WN": w}
                r = evaluate(sel[rg], cfg, ex); counter[0] += 1
                l0[f"{rg}/{ex}/{w or 'both'}"] = r
                print(f"  {rg:<5} {ex:<6} {w or 'both':<11} {fmt(r)}")
    res["L0"] = l0

    ref = {"selection": evaluate(sel["bot"], BOT_RULES, "trail"), "holdout": evaluate(hold["bot"], BOT_RULES, "trail")}
    print(f"\n  the bot's rules today (G1 G4 VW E9 MC PV, trail, bot window)\n"
          f"    selection {fmt(ref['selection'])}\n    holdout   {fmt(ref['holdout'])}")
    res["bot_today"] = ref

    print("\n2 · ONE LEVER AT A TIME — added alone to L0, selection")
    single = {}
    for rg in REGIMES:
        ex0 = max(EXITS, key=lambda ex: (l0[f"{rg}/{ex}/both"]["mean"] if l0[f"{rg}/{ex}/both"]["mean"] is not None else -9))
        base = l0[f"{rg}/{ex0}/both"]
        print(f"  {rg} window, exit {ex0}: L0 {fmt(base)}")
        for lid, levels in LEVERS:
            for lvl in levels:
                cfg = {lid: lvl}
                r = evaluate(sel[rg], cfg, ex0); counter[0] += 1
                d = (r["mean"] - base["mean"]) if (r["mean"] is not None and base["mean"] is not None) else None
                single[f"{rg}/{label(cfg)}"] = dict(r, delta=None if d is None else round(d, 3))
                print(f"    {label(cfg):<16} {fmt(r)}" + (f"   Δ {d:+.3f}" if d is not None else ""))
    res["single"] = single

    print("\n3 · GREEDY BUILD — selection only, ≥ 30 trades, stop under +0.02 R a trade")
    start_rg, start_ex = max(((rg, ex) for rg in REGIMES for ex in EXITS),
                             key=lambda k: (l0[f"{k[0]}/{k[1]}/both"]["mean"]
                                            if l0[f"{k[0]}/{k[1]}/both"]["mean"] is not None else -9))
    steps = greedy(sel[start_rg], start_ex, counter)
    for i, s in enumerate(steps):
        print(f"  step {i}: {s['label']:<40} exit {s['exit']:<6} {fmt(s)}")
    best = steps[-1]
    res["greedy"] = {"regime": start_rg, "steps": steps}

    print("\n4 · CHECKS OF THE BEST FOUND")
    cfg, ex = best["config"], best["exit"]
    h = evaluate(hold[start_rg], cfg, ex)
    trades_sel = [p for p in sel[start_rg] if p["touched"] and passes(p, cfg)]
    rb = random_baseline(trades_sel, rows_by, start_rg, ex)
    pos_sel, pos_hold = one_position(sel[start_rg], cfg, ex), one_position(hold[start_rg], cfg, ex)
    sens = {c: {"selection": evaluate(sel[start_rg], cfg, ex, c), "holdout": evaluate(hold[start_rg], cfg, ex, c)}
            for c in ("old", "meas")}
    print(f"  best found: {best['label']} · exit {ex} · {start_rg} window")
    print(f"    selection {fmt(best)}\n    holdout   {fmt(h)}")
    print(f"    random entries, same names, gross: strategy {rb['strategy_gross']} vs random {rb['random_gross']} "
          f"(difference {rb['difference']}, {rb['n_random']} random entries)")
    print(f"    one position, net: selection {pos_sel['total']:+.1f} R over {pos_sel['trades']} trades "
          f"({pos_sel['days_pos']}/{pos_sel['days']} days up) · holdout {pos_hold['total']:+.1f} R over {pos_hold['trades']}")
    for c, v in sens.items():
        print(f"    costs {c:<5} selection {fmt(v['selection'])}\n               holdout   {fmt(v['holdout'])}")
    ok1 = best["n"] >= MIN_SEL and (best["mean"] or 0) > 0
    ok2 = h["n"] >= MIN_HOLD and (h["mean"] or 0) > 0
    ok3 = rb["difference"] is not None and rb["difference"] > 0
    verdict = "CANDIDATE" if (ok1 and ok2 and ok3) else "BEST FOUND, NOT A CANDIDATE"
    failed = [name for name, ok in (("selection mean net > 0 on ≥ 30", ok1), ("holdout mean net > 0 on ≥ 10", ok2),
                                    ("gross beats random entries", ok3)) if not ok]
    print(f"\n  VERDICT: {verdict}" + (f" — failed: {'; '.join(failed)}" if failed else ""))
    print(f"  configurations evaluated: {counter[0]}")
    res["best"] = {"config": {k: v for k, v in cfg.items()}, "label": best["label"], "exit": ex, "regime": start_rg,
                   "selection": {k: best[k] for k in ("n", "mean", "total", "gross", "win")}, "holdout": h,
                   "random": rb, "one_position": {"selection": pos_sel, "holdout": pos_hold}, "costs": sens,
                   "verdict": verdict, "failed": failed}
    res["configurations_evaluated"] = counter[0]
    Path(args.out).write_text(json.dumps(res, indent=1, default=str))
    print(f"\nwritten {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
