#!/usr/bin/env python3
"""Tick replay: the rules audit's plans, filled and exited on the real trade
sequence instead of 1-minute bars.

Why (2026-10-02). The ten-year backtest only sees whole 1-minute candles, so
it cannot tell whether the trigger or the stop traded first inside a minute;
the rules audit runs four bar readings (modes A, C, CA, H) because of it, and
its costs use a modelled spread. This replays each plan on Alpaca SIP trades
in time order and reads the real bid/ask at the fill and at the exit.

What is replayed, the live executor's rules (src/execution):
  * order sent at the trigger bar's close (rules audit mode C's `order_t`);
  * entry: buy STOP-LIMIT, stop = trigger, limit = trigger + 0.3 % (A10):
    triggered by the first print at or above the trigger, filled by the
    first print at or under the limit from then on, cancelled after 3 min;
  * stop at the plan's stop; A3 trail 1 R under the high since the fill,
    moved every 5 s (the runner loop); a stop fills at the first print at or
    under it (a stop-market: the print IS the slippage);
  * flat at 11:30 ET at the last print before it.
Prints that do not set a last sale are dropped (TRADE_EXCLUDE). Within one
print the order is exact; nothing is inferred from a candle.

The outcome is stored in the plan's `out` under mode "T" in the same shape
the rules audit uses, so `rules_audit.portfolio` runs on it unchanged, and
the real spreads under `p["tick"]` for the "real" cost model.

    python3 scripts/tick_replay.py fetch   [--since 2024-01-01] [--limit N]
    python3 scripts/tick_replay.py report  [--since 2024-01-01]
    python3 scripts/tick_replay.py live    [--db data/journal.sqlite]   (your IBKR fills vs the tape)

Ticks are cached per symbol, day and 10-minute chunk under
data/cache/ticks/ (compressed), outcomes in data/cache/tick_outcomes.pkl;
both resume where they stopped. Needs ALPACA_KEY_ID / ALPACA_SECRET_KEY.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import rules_audit as RA  # noqa: E402

TICKS = ROOT / "data" / "cache" / "ticks"
OUTCOMES = ROOT / "data" / "cache" / "tick_outcomes.pkl"
CHUNK_S = 600                       # one cached file per 10 minutes of tape
TTL_S = 180                         # A10 ENTRY_TTL_MINUTES
CAP_PCT = 0.3                       # A10 ENTRY_LIMIT_OFFSET_PCT
TRAIL_R = 1.0                       # A3
TRAIL_EVERY_S = 5                   # the runner loop
FLAT = "11:30"
MIN_INTERVAL_S = 0.33               # ~180 requests a minute, under Alpaca's 200
# SIP sale conditions that do not set the last sale price, so cannot trigger
# a stop: odd lot, average price, out of sequence (regular and extended),
# derivatively priced, qualified contingent, cash, next day, seller, prior
# reference, contingent. An approximation of the CTA/UTP eligibility tables.
TRADE_EXCLUDE = {"I", "W", "Z", "U", "4", "7", "C", "N", "R", "P", "V"}


# ------------------------------------------------------------------ the replay
def replay(ticks_t: np.ndarray, ticks_p: np.ndarray, entry: float, stop: float, t_order: int,
           flat_t: int, cap_pct: float = CAP_PCT, ttl_s: int = TTL_S, trail_r: float = TRAIL_R,
           trail_every: int = TRAIL_EVERY_S):
    """One plan on one print sequence (times in epoch milliseconds, sorted).
    Returns None (never filled) or dict(t_in, t_out, fill, exit, r, stopish, how)."""
    cap = RA.cap_of(entry, cap_pct)
    rps = entry - stop
    if rps <= 0:
        return None
    i = int(np.searchsorted(ticks_t, t_order * 1000, side="left"))
    end_entry = (t_order + ttl_s) * 1000
    n = len(ticks_t)
    triggered = False
    fill_i = None
    while i < n and ticks_t[i] < end_entry:
        p = ticks_p[i]
        if not triggered and p >= entry:
            triggered = True
        if triggered and p <= cap:
            fill_i = i
            break
        i += 1
    if fill_i is None:
        return None
    # A triggered buy fills against the ask, not at whatever print came next:
    # in a fast tape a stray low print after the trigger (NXL 2026-10-01
    # 09:30, 8.74 against a live fill of 8.89) would hand the replay a price
    # nobody could buy at. So no better than the trigger, no worse than the cap.
    fill = float(min(cap, max(entry, ticks_p[fill_i])))
    t_fill = int(ticks_t[fill_i])
    level, high = stop, fill
    next_trail = t_fill + trail_every * 1000
    j = fill_i + 1
    flat_ms = flat_t * 1000
    while j < n:
        tj, pj = int(ticks_t[j]), float(ticks_p[j])
        if tj >= flat_ms:
            return {"t_in": t_fill, "t_out": int(ticks_t[j - 1]), "fill": fill, "exit": float(ticks_p[j - 1]),
                    "r": (float(ticks_p[j - 1]) - fill) / rps, "stopish": False, "how": "flat"}
        while tj >= next_trail:                      # the runner's loop moves the stop
            level = max(level, round(high - trail_r * rps, 4))
            next_trail += trail_every * 1000
        if pj <= level:
            return {"t_in": t_fill, "t_out": tj, "fill": fill, "exit": pj, "r": (pj - fill) / rps,
                    "stopish": True, "how": "trail" if level > stop else "stop"}
        high = max(high, pj)
        j += 1
    return {"t_in": t_fill, "t_out": int(ticks_t[n - 1]), "fill": fill, "exit": float(ticks_p[n - 1]),
            "r": (float(ticks_p[n - 1]) - fill) / rps, "stopish": False, "how": "end-of-data"}


# ------------------------------------------------------------------ data
class Fetcher:
    def __init__(self, client, cache: Path = TICKS):
        self.c, self.cache, self._last = client, cache, 0.0
        self.requests = 0

    def _get(self, path: str, params: dict) -> dict:
        for attempt in range(6):
            wait = MIN_INTERVAL_S - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            self.requests += 1
            try:
                return self.c._get(self.c.data_base, path, params)
            except Exception as exc:                                    # noqa: BLE001
                if attempt < 5 and ("429" in str(exc) or "timed out" in str(exc).lower()
                                    or "502" in str(exc) or "503" in str(exc)):
                    time.sleep(10 * (attempt + 1))
                    continue
                raise
        return {}

    def chunk(self, sym: str, day: str, k: int, day0: int, sizes: bool = False):
        """Prints of chunk k (CHUNK_S seconds from day0, 04:00 ET), cached.
        Returns (t, p), or (t, p, s) with `sizes` (a file cached before sizes
        were stored is fetched again)."""
        f = self.cache / day / f"{sym}_{k:03d}.npz"
        if f.exists():
            z = np.load(f)
            # float32 on disk: 8.87 reads back as 8.8699999, which would miss a
            # trigger at exactly 8.87. Prices are quoted to 4 decimals at most.
            pz = np.round(z["p"].astype(np.float64), 4)
            if not sizes:
                return z["t"], pz
            if "s" in z.files:
                return z["t"], pz, z["s"]
        start, end = day0 + k * CHUNK_S, day0 + (k + 1) * CHUNK_S
        iso = lambda s: datetime.fromtimestamp(s, timezone.utc).isoformat().replace("+00:00", "Z")  # noqa: E731
        ts, ps, ss, token = [], [], [], None
        while True:
            payload = self._get(f"/v2/stocks/{sym}/trades", {"start": iso(start), "end": iso(end), "limit": 10000,
                                                              "feed": "sip", "page_token": token})
            for x in payload.get("trades") or []:
                if TRADE_EXCLUDE.intersection(x.get("c") or ()):
                    continue
                ts.append(_ms(x["t"]))
                ps.append(x["p"])
                ss.append(x.get("s") or 0)
            token = payload.get("next_page_token")
            if not token:
                break
        t = np.array(ts, dtype=np.int64)
        p = np.array(ps, dtype=np.float64)
        sz = np.array(ss, dtype=np.int64)
        o = np.argsort(t, kind="stable")
        t, p, sz = t[o], p[o], sz[o]
        f.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(f, t=t, p=p.astype(np.float32), s=sz.astype(np.int32))
        p = np.round(p, 4)
        return (t, p, sz) if sizes else (t, p)

    def spread_at(self, sym: str, t_ms: int) -> float | None:
        """The NBBO prevailing at t (the last valid quote at or before it,
        within 60 s): ask - bid. None when the book was crossed or empty."""
        iso = lambda ms: datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")  # noqa: E731
        q = self._get(f"/v2/stocks/{sym}/quotes", {"start": iso(t_ms - 60_000), "end": iso(t_ms + 1), "limit": 20,
                                                    "feed": "sip", "sort": "desc"})
        for x in q.get("quotes") or []:
            bp, ap = x.get("bp") or 0, x.get("ap") or 0
            if bp > 0 and ap > bp:
                return round(ap - bp, 4)
        return None


def _ms(iso: str) -> int:
    """RFC 3339 with up to nanoseconds -> epoch ms (fromisoformat takes 6 digits)."""
    head, _, frac = iso.rstrip("Z").partition(".")
    dt = datetime.fromisoformat(head).replace(tzinfo=timezone.utc)
    return int(dt.timestamp()) * 1000 + int((frac + "000")[:3])


def day_open(day: str) -> int:
    return int(datetime.fromisoformat(f"{day}T04:00:00").replace(tzinfo=RA.E.ET).timestamp())


def at_et(day: str, hm: str) -> int:
    return int(datetime.fromisoformat(f"{day}T{hm}:00").replace(tzinfo=RA.E.ET).timestamp())


def replay_plan(fx: Fetcher, p: dict) -> dict | None:
    """Fetch only the chunks the plan needs, in order, until it has exited."""
    day0 = day_open(p["day"])
    t_order = p["arm"] + 60
    flat_t = at_et(p["day"], FLAT)
    if t_order >= flat_t:
        return None
    k = (t_order - day0) // CHUNK_S
    last_k = (flat_t - day0) // CHUNK_S
    ts, ps = [], []
    while k <= last_k:
        t, pr = fx.chunk(p["sym"], p["day"], int(k), day0)
        ts.append(t); ps.append(pr)
        T, P = np.concatenate(ts), np.round(np.concatenate(ps).astype(np.float64), 4)
        out = replay(T, P, p["entry"], p["stop"], t_order, flat_t)
        chunk_end = (day0 + (k + 1) * CHUNK_S) * 1000
        if out is None and len(T) and T[-1] >= (t_order + TTL_S) * 1000:
            return {"filled": False}
        if out is None and chunk_end >= (t_order + TTL_S) * 1000:
            return {"filled": False}
        if out is not None and out["how"] != "end-of-data":
            out["filled"] = True
            return out
        k += 1
    if out is None:
        return {"filled": False}
    out["filled"] = True
    return out


# ------------------------------------------------------------------ costs
def cost_real(p: dict, stopish: bool, risk: float = 40.0, notional: float | None = 2000.0) -> float | None:
    """`rules_audit.cost_live` with the measured spreads in place of the proxy:
    commission both ways + (half the real spread + 1 cent) on the entry and,
    on a stop exit, on the exit too."""
    tk = p.get("tick") or {}
    s_in, s_out = tk.get("spread_in"), tk.get("spread_out")
    if s_in is None or (stopish and s_out is None):
        return None
    rps = p["entry"] - p["stop"]
    sh = int(risk // rps)
    if notional:
        sh = min(sh, int(notional // p["entry"]))
    sh = max(1, sh)
    comm = 2 * min(max(1.0, 0.005 * sh), max(1.0, 0.01 * sh * p["entry"]))
    fric = sh * (s_in / 2 + 0.01) + (sh * (s_out / 2 + 0.01) if stopish else 0.0)
    return round((comm + fric) / (sh * rps), 3)


# ------------------------------------------------------------------ commands
def load_plans(since: str, until: str | None):
    plans = pickle.loads(RA.PLANS_CACHE.read_bytes())
    sel = [p for p in plans if p["day"] >= since and (until is None or p["day"] <= until)]
    return sel


def cmd_fetch(args) -> int:
    from momentum_platform.datasources.alpaca_source import client_from_env
    fx = Fetcher(client_from_env(feed="sip"))
    plans = [p for p in load_plans(args.since, args.until) if RA.passes(p, RA.BASE)]
    plans.sort(key=lambda p: (p["day"], p["sym"], p["arm"]))
    done = pickle.loads(OUTCOMES.read_bytes()) if OUTCOMES.exists() else {}
    todo = [p for p in plans if (p["sym"], p["arm"]) not in done]
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(plans)} plans pass the live gates since {args.since}; {len(done)} replayed, {len(todo)} to go",
          flush=True)
    t0 = time.monotonic()
    for k, p in enumerate(todo, 1):
        try:
            out = replay_plan(fx, p)
            if out and out.get("filled"):
                out["spread_in"] = fx.spread_at(p["sym"], out["t_in"])
                out["spread_out"] = fx.spread_at(p["sym"], out["t_out"]) if out["stopish"] else None
        except Exception as exc:                                        # noqa: BLE001
            print(f"  {p['day']} {p['sym']} {p['t']}: {exc}", flush=True)
            continue
        done[(p["sym"], p["arm"])] = out
        if k % 25 == 0 or k == len(todo):
            OUTCOMES.write_bytes(pickle.dumps(done))
            rate = k / max(1e-9, time.monotonic() - t0) * 60
            print(f"  {k}/{len(todo)} · {fx.requests} requests · {rate:.0f} plans/min", flush=True)
    OUTCOMES.write_bytes(pickle.dumps(done))
    return 0


def attach(plans: list[dict], done: dict) -> int:
    n = 0
    for p in plans:
        o = done.get((p["sym"], p["arm"]))
        if o is None:
            continue
        n += 1
        if not o.get("filled"):
            p["out"][("T", "base")] = None
            continue
        p["out"][("T", "base")] = (o["t_in"] // 1000, o["t_out"] // 1000, round(o["r"], 4), o["stopish"], o["fill"])
        p["tick"] = {"spread_in": o.get("spread_in"), "spread_out": o.get("spread_out"), "how": o["how"],
                     "exit": o["exit"]}
    return n


def cmd_report(args) -> int:
    done = pickle.loads(OUTCOMES.read_bytes())
    plans = load_plans(args.since, args.until)
    n = attach(plans, done)
    have = {(p["sym"], p["day"]) for p in plans if ("T", "base") in p["out"]}
    days = sorted({p["day"] for p in plans if ("T", "base") in p["out"]})
    # Same universe for every mode: the days whose every gate-passing plan was replayed.
    by_day = defaultdict(list)
    for p in plans:
        by_day[p["day"]].append(p)
    full = {d for d in days if all(("T", "base") in p["out"] for p in by_day[d] if RA.passes(p, RA.BASE))}
    sub = {d: by_day[d] for d in full}
    print(f"tick replay · {n} plans replayed on {len(have)} symbol-days · {len(full)} complete sessions "
          f"{min(full) if full else '-'}..{max(full) if full else '-'}")
    rows = []
    for name, c in (("A  bars, as preregistered", dict(RA.BASE, mode="A")),
                    ("C  bars, corrected order", dict(RA.BASE, mode="C")),
                    ("T  ticks, proxy spread", dict(RA.BASE, mode="T")),
                    ("T  ticks, gross", dict(RA.BASE, mode="T", costs="none"))):
        tr = RA.portfolio(sub, c)
        rows.append((name, tr))
    tr_real = []
    for t in RA.portfolio(sub, dict(RA.BASE, mode="T", costs="none")):
        p = next(x for x in sub[t["day"]] if x["sym"] == t["sym"] and x["t"] == t["t"])
        o = p["out"][("T", "base")]
        cr = cost_real(p, o[3])
        if cr is not None:
            tr_real.append(dict(t, net=t["gross"] - cr, cost=cr))
    rows.append(("T  ticks, REAL spreads", tr_real))
    print(f"\n  {'model':<28}{'n':>6}{'net R/trade':>13}{'total R':>10}{'win %':>8}{'max DD':>8}")
    for name, tr in rows:
        s = RA.stats(tr)
        print(f"  {name:<28}{s.get('n', 0):>6}{s.get('mean', float('nan')):>+13.3f}{s.get('total', 0):>+10.1f}"
              f"{100 * s.get('win', 0):>7.1f}%{s.get('max_dd', 0):>8.1f}")
    # Per plan: how far the bar readings sit from the tape.
    pairs = defaultdict(list)
    for d in full:
        for p in sub[d]:
            if not RA.passes(p, RA.BASE):
                continue
            t = p["out"].get(("T", "base"))
            for m in ("A", "C", "H", "CA"):
                b = p["out"].get((m, "base"))
                if t is not None and b is not None:
                    pairs[m].append(b[2] - t[2])
                elif (t is None) != (b is None):
                    pairs[m + "-fill"].append(1)
    print("\n  per plan, bar reading minus tick replay (gross R, plans both filled):")
    for m in ("A", "C", "CA", "H"):
        v = np.array(pairs[m]) if pairs[m] else np.array([np.nan])
        print(f"    {m:<3} n {len(pairs[m]):>5} · mean {np.nanmean(v):+.3f} · median {np.nanmedian(v):+.3f}"
              f" · fill disagreements {len(pairs[m + '-fill'])}")
    sp = [p["tick"]["spread_in"] for d in full for p in sub[d] if p.get("tick") and p["tick"].get("spread_in")]
    prox = [RA.PROXY.spread(p["entry"], p["pm"], p["dv5"]) for d in full for p in sub[d]
            if p.get("tick") and p["tick"].get("spread_in")]
    if sp:
        print(f"\n  spread at the fill: real median {np.median(sp):.4f} · proxy median {np.median(prox):.4f}"
              f" · real/proxy median {np.median(np.array(sp) / np.array(prox)):.2f}")
    costs = [t["cost"] for t in tr_real]
    if costs:
        print(f"  real cost per trade: median {np.median(costs):.3f} R · mean {np.mean(costs):.3f} R")
    if args.json:
        Path(args.json).write_text(json.dumps({name: RA.stats(tr) for name, tr in rows}, indent=1))
    return 0


def _epoch(iso) -> int | None:
    """A ledger timestamp (naive = UTC, the ledger's _now()) -> epoch seconds."""
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def cmd_live(args) -> int:
    """Calibration: every filled order in the ledger, replayed on the tape from
    the moment it was placed, next to what IBKR actually did."""
    import sqlite3
    from momentum_platform.datasources.alpaca_source import client_from_env
    fx = Fetcher(client_from_env(feed="sip"))
    conn = sqlite3.connect(f"file:{Path(args.db).resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT symbol, trigger, stop, fill_price, fill_ts, exit_price, exit_ts, exit_reason, "
                        "placed_at FROM orders WHERE fill_price IS NOT NULL AND exit_price IS NOT NULL "
                        "ORDER BY placed_at").fetchall()
    now = time.time()
    print(f"{'day':<11}{'sym':<6}{'trig/stop':>12}  {'fill live/tick':>15}  {'exit live/tick':>15}  "
          f"{'R live/tick':>13}  tick exit")
    gaps = defaultdict(list)
    for r in rows:
        placed = _epoch(r["placed_at"])
        if placed is None or now - placed < 20 * 60:          # Alpaca SIP: nothing from the last 15 minutes
            continue
        day = datetime.fromtimestamp(placed, timezone.utc).astimezone(RA.E.ET).date().isoformat()
        plan = {"sym": r["symbol"], "day": day, "arm": placed - 60, "entry": float(r["trigger"]),
                "stop": float(r["stop"])}
        try:
            out = replay_plan(fx, plan)
        except Exception as exc:                                        # noqa: BLE001
            print(f"{day:<11}{r['symbol']:<6} replay failed: {exc}")
            continue
        rps = float(r["trigger"]) - float(r["stop"])
        r_live = (float(r["exit_price"]) - float(r["fill_price"])) / rps
        if not out or not out.get("filled"):
            print(f"{day:<11}{r['symbol']:<6}{r['trigger']:>6.2f}/{r['stop']:<5.2f}  "
                  f"{r['fill_price']:>7.2f}/  none  — the tape never filled it; live did")
            gaps["fill missing"].append(1)
            continue
        print(f"{day:<11}{r['symbol']:<6}{r['trigger']:>6.2f}/{r['stop']:<5.2f}  {r['fill_price']:>7.2f}/{out['fill']:<7.2f}"
              f"  {r['exit_price']:>7.2f}/{out['exit']:<7.2f}  {r_live:>+6.2f}/{out['r']:<+6.2f}  {out['how']}")
        gaps["fill"].append(float(r["fill_price"]) - out["fill"])
        gaps["R"].append(r_live - out["r"])
    if gaps["R"]:
        print(f"\n{len(gaps['R'])} trades · live minus tick: fill {np.mean(gaps['fill']):+.3f} $/sh · "
              f"R {np.mean(gaps['R']):+.3f} per trade (median {np.median(gaps['R']):+.3f})"
              + (f" · {len(gaps['fill missing'])} the tape would not have filled" if gaps["fill missing"] else ""))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    lv = sub.add_parser("live", help="calibration: the ledger's real fills against the tick replay")
    lv.add_argument("--db", default=str(ROOT / "data" / "journal.sqlite"))
    for name in ("fetch", "report"):
        s = sub.add_parser(name)
        s.add_argument("--since", default="2024-01-01")
        s.add_argument("--until")
        if name == "fetch":
            s.add_argument("--limit", type=int)
        else:
            s.add_argument("--json")
    args = ap.parse_args(argv)
    RA.E.COST_MODEL = "live"
    return {"fetch": cmd_fetch, "report": cmd_report, "live": cmd_live}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
