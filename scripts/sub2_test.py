#!/usr/bin/env python3
"""P1 — a $1 price floor instead of $2 (addendum 2026-10-07b).

    python3 scripts/sub2_test.py universe   # daily bars → sub-$2 gapper days (cached)
    python3 scripts/sub2_test.py bars       # 1-minute bars of those days (cached)
    python3 scripts/sub2_test.py run        # plans, portfolios, decision
"""
from __future__ import annotations

import json
import pickle
import sys
import time
from collections import defaultdict
from datetime import time as dtime
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

import backtest_history as H  # noqa: E402
import backtest_recent as E  # noqa: E402
import detector_variants as D  # noqa: E402
import rules_audit as RA  # noqa: E402

START, END = "2024-01-02", "2026-08-21"
CACHE = ROOT / "data" / "cache" / "sub2"
UNIVERSE = CACHE / "universe.json"
BARS = CACHE / "bars"
OUT = ROOT / "research" / "paper-exercise" / "reports" / "sub2_output.txt"


def _get(c, path, params):
    for attempt in range(6):
        try:
            return c._get(c.data_base, path, params)
        except Exception as exc:                          # noqa: BLE001
            if "429" in str(exc) and attempt < 5:
                time.sleep(15 * (attempt + 1)); continue
            raise


def universe() -> int:
    c = H.alpaca_client()
    assets = []
    for status in ("active", "inactive"):
        assets += c._get(c.trading_base, "/v2/assets", {"status": status, "asset_class": "us_equity"})
    syms = sorted({a["symbol"] for a in assets if a.get("exchange") in ("NASDAQ", "NYSE", "AMEX", "ARCA", "BATS")
                   and a["symbol"].isalpha() and a["symbol"].isupper() and len(a["symbol"]) <= 5})
    print(f"{len(syms)} symbols", flush=True)
    found: dict = defaultdict(dict)
    for i in range(0, len(syms), 100):
        chunk, token, rows = syms[i:i + 100], None, defaultdict(list)
        while True:
            p = _get(c, "/v2/stocks/bars", {"symbols": ",".join(chunk), "timeframe": "1Day", "start": START,
                                            "end": END, "limit": 10000, "feed": c.feed, "adjustment": "raw",
                                            "page_token": token})
            for s, bs in (p.get("bars") or {}).items():
                rows[s] += bs
            token = p.get("next_page_token")
            if not token:
                break
        for s, bs in rows.items():
            bs.sort(key=lambda b: b["t"])
            for k in range(20, len(bs)):
                o, pc = bs[k]["o"], bs[k - 1]["c"]
                if not (1.0 <= o < 2.0) or pc <= 0 or o < pc * 1.10:
                    continue
                ratio = o / pc
                if ratio >= 2 and abs(ratio - round(ratio)) <= 0.02 * round(ratio):
                    continue                                   # a reverse split, not a gap
                dv = sum(b["c"] * b["v"] for b in bs[k - 20:k]) / 20
                if dv < 250_000:
                    continue
                found[bs[k]["t"][:10]][s] = pc
        if i % 2000 == 0:
            print(f"  {i}/{len(syms)} · {sum(len(v) for v in found.values())} symbol-days", flush=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    UNIVERSE.write_text(json.dumps(found))
    print(f"universe: {sum(len(v) for v in found.values())} symbol-days on {len(found)} sessions")
    return 0


def bars() -> int:
    c = H.alpaca_client()
    uni = json.loads(UNIVERSE.read_text())
    BARS.mkdir(parents=True, exist_ok=True)
    for k, (day, syms) in enumerate(sorted(uni.items()), 1):
        for attempt in range(5):
            try:
                H.fetch_day(c, day, sorted(syms), BARS)
                break
            except Exception as exc:                      # noqa: BLE001 — a dropped connection; the day cache resumes
                print(f"  {day}: {exc!r} — retry {attempt + 1}", flush=True)
                time.sleep(10 * (attempt + 1))
        if k % 50 == 0:
            print(f"  {k}/{len(uni)} sessions", flush=True)
    return 0


def day_job(args):
    day, syms = args
    f = BARS / f"{day}.json"
    if not f.exists():
        return []
    data = json.loads(f.read_text())
    out = []
    for sym in syms:
        rows = [r for r in H.to_rows(data.get(sym) or []) if dtime(4, 0) <= r[0].time() < dtime(16, 0)]
        if len(rows) < 40:
            continue
        for p in D.plans_for(sym, day, rows, "B"):
            if p["t"] < "07:00" or not (1.0 <= p["entry"] < 20.0):
                continue
            p["red"] = [x for x in p["red"] if x != "price"]          # the $1 floor
            p["red_prev"] = [x for x in p["red_prev"] if x != "price"]
            p["sub2"] = True
            out.append(p)
    return out


def total(tr):
    return sum(t["net"] for t in tr)


def run() -> int:
    E.COST_MODEL = "live"
    lines = []

    def pr(s=""):
        print(s, flush=True); lines.append(s)
    uni = json.loads(UNIVERSE.read_text())
    with Pool(4) as pool:
        sub = [p for ps in pool.imap(day_job, sorted(uni.items()), chunksize=4) for p in ps]
    base = [p for p in pickle.loads(RA.PLANS_CACHE.read_bytes()) if START <= p["day"] <= END]
    by_b, by_p = defaultdict(list), defaultdict(list)
    for p in base:
        by_b[p["day"]].append(p); by_p[p["day"]].append(p)
    for p in sub:
        by_p[p["day"]].append(p)
    pr(f"addendum 2026-10-07b · {START} → {END} · sub-$2 universe {sum(len(v) for v in uni.values())} symbol-days "
       f"on {len(uni)} sessions · sub-$2 plans {len(sub)} · B plans {len(base)} · costs live (no spread tier under $2)")
    passes = []
    for mode in ("A", "C"):
        c = dict(RA.BASE, mode=mode)
        b = RA.portfolio(by_b, c); v = RA.portfolio(by_p, c)
        sb, sv = RA.split_stats(b), RA.split_stats(v)
        lb = RA.paired_lb(v, b, alpha=0.05)
        keys = {(t["day"], t["sym"], t["t"]) for t in b}
        added = [t for t in v if (t["day"], t["sym"], t["t"]) not in keys]
        yrs = sum(1 for y in ("2024", "2025", "2026") if sv["years"][y].get("mean", -9) > sb["years"][y].get("mean", -9))
        a_net = sum(t["net"] for t in added) / len(added) if added else float("nan")
        a_gross = sum(t["gross"] for t in added) / len(added) if added else float("nan")
        checks = {"mean better": sv["test"]["mean"] > sb["test"]["mean"], "total not worse": total(v) >= total(b),
                  "2 of 3 years": yrs >= 2, "lower bound > 0": lb > 0, "added trades net > 0": a_net > 0}
        passes.append(all(checks.values()))
        pr(f"\n=== reading {mode} ===")
        pr(f"  B ($2 floor)  n {sb['test']['n']} · net {sb['test']['mean']:+.3f} · total {total(b):+.1f} R")
        pr(f"  P1 ($1 floor) n {sv['test']['n']} · net {sv['test']['mean']:+.3f} · total {total(v):+.1f} R · lb {lb:+.3f}")
        pr(f"  sub-$2 trades it adds: n {len(added)} · gross {a_gross:+.3f} · net {a_net:+.3f} · "
           f"won {sum(1 for t in added if t['net'] > 0) / max(1, len(added)):.0%}")
        pr("  " + " · ".join(f"{'✓' if x else '✗'} {k}" for k, x in checks.items()))
    pr("\nDECISION: " + ("P1 passes both readings → to the owner, OFF, 200 prospective trades" if all(passes)
                         else "P1 fails → the $2 floor stays"))
    OUT.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit({"universe": universe, "bars": bars, "run": run}[sys.argv[1]]())
