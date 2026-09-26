#!/usr/bin/env python3
"""Fetch the side data the edge hunt needs, cached under data/cache/edge/.

    news    Alpaca historical news for every universe symbol-day, from four
            days before to 16:00 ET on the day (filtered point-in-time later)
    sec     SEC shares outstanding (dei:EntityCommonStockSharesOutstanding),
            a float UPPER BOUND, for every universe symbol the SEC's current
            ticker map knows (delisted names are mostly absent — a stated bias)
    quotes  real NBBO around a sample of moments, to calibrate the spread proxy
    trades  tick trades for a subset of symbol-days, for 10-second bars

Keys come from the environment (ALPACA_KEY_ID / ALPACA_SECRET_KEY); nothing
is written into the repository.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
CACHE = ROOT / "data" / "cache" / "edge"
UNIVERSE_CSV = ROOT / "research" / "first-pullback-edge" / "data" / "candidate_days.csv"
SEC_UA = os.environ.get("SEC_USER_AGENT", "day-trading-bot research contact@example.com")

try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
except Exception:                                                    # noqa: BLE001
    ET = None


def universe() -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    with open(UNIVERSE_CSV) as f:
        for r in csv.DictReader(f):
            if r.get("split_on_day") in ("True", "true", "1"):
                continue
            out[r["day"]].append(r["sym"])
    return dict(out)


class Pacer:
    """At most `per_min` requests a minute, retry 429/5xx with backoff."""

    def __init__(self, per_min: int):
        self.gap = 60.0 / per_min
        self.last = 0.0

    def wait(self):
        d = self.last + self.gap - time.monotonic()
        if d > 0:
            time.sleep(d)
        self.last = time.monotonic()


def alpaca():
    from momentum_platform.datasources.alpaca_source import client_from_env
    return client_from_env(feed=os.environ.get("HISTORY_FEED", "sip"))


def aget(client, pacer, path, params):
    for attempt in range(6):
        pacer.wait()
        try:
            return client._get(client.data_base, path, params)
        except Exception as exc:                                     # noqa: BLE001
            msg = str(exc)
            if ("429" in msg or "Rate" in msg or "timed out" in msg or "50" in msg[:40]) and attempt < 5:
                time.sleep(15 * (attempt + 1)); continue
            raise


def et_utc(day: str, hh: int, mm: int) -> str:
    dt = datetime.fromisoformat(f"{day}T{hh:02d}:{mm:02d}:00").replace(tzinfo=ET).astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


# ------------------------------------------------------------------ news
def fetch_news(days: list[str], uni: dict, per_min: int = 180) -> None:
    client, pacer = alpaca(), Pacer(per_min)
    out_dir = CACHE / "news"; out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    for k, d in enumerate(days, 1):
        f = out_dir / f"{d}.json"
        if f.exists():
            continue
        start = (date.fromisoformat(d) - timedelta(days=4)).isoformat() + "T00:00:00Z"
        end = et_utc(d, 16, 0)
        items = []
        syms = sorted(set(uni[d]))
        for i in range(0, len(syms), 40):
            token = None
            while True:
                p = aget(client, pacer, "/v1beta1/news", {"symbols": ",".join(syms[i:i + 40]), "start": start,
                                                           "end": end, "limit": 50, "sort": "asc",
                                                           "page_token": token})
                for n in p.get("news", []) or []:
                    items.append({"id": n.get("id"), "t": n.get("created_at"), "u": n.get("updated_at"),
                                  "s": n.get("symbols", []), "h": n.get("headline", ""), "src": n.get("source", "")})
                token = p.get("next_page_token")
                if not token:
                    break
        f.write_text(json.dumps(items))
        if k % 100 == 0:
            print(f"news {k}/{len(days)} · {time.monotonic() - t0:.0f}s", flush=True)


# ------------------------------------------------------------------ sec
def sec_get(url: str) -> dict | None:
    for attempt in range(4):
        time.sleep(0.12)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": SEC_UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            time.sleep(2 * (attempt + 1))
        except Exception:                                            # noqa: BLE001
            time.sleep(2 * (attempt + 1))
    return None


def fetch_sec(uni: dict) -> None:
    out_dir = CACHE / "sec"; out_dir.mkdir(parents=True, exist_ok=True)
    tick = sec_get("https://www.sec.gov/files/company_tickers.json") or {}
    cik = {v["ticker"].upper().replace("-", "."): int(v["cik_str"]) for v in tick.values()}
    (out_dir / "ticker_cik.json").write_text(json.dumps(cik))
    syms = sorted({s for ss in uni.values() for s in ss})
    mapped = [s for s in syms if s in cik]
    print(f"sec: {len(syms)} symbols, {len(mapped)} in the SEC's current ticker map", flush=True)
    for k, s in enumerate(mapped, 1):
        f = out_dir / f"{s}.json"
        if f.exists():
            continue
        rows = []
        for concept in ("dei/EntityCommonStockSharesOutstanding", "us-gaap/CommonStockSharesOutstanding"):
            p = sec_get(f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik[s]:010d}/{concept}.json")
            for unit, vals in ((p or {}).get("units") or {}).items():
                for v in vals:
                    rows.append({"c": concept.split("/")[0], "end": v.get("end"), "val": v.get("val"),
                                 "filed": v.get("filed"), "form": v.get("form")})
        f.write_text(json.dumps({"cik": cik[s], "rows": rows}))
        if k % 200 == 0:
            print(f"sec {k}/{len(mapped)}", flush=True)


# ------------------------------------------------------------------ quotes / trades
def fetch_quotes(moments: list[tuple[str, str, str]], per_min: int = 180) -> None:
    """moments: (sym, day, 'HH:MM') ET. Stores every NBBO update in the 60 s
    starting at that minute (capped at 2,000)."""
    client, pacer = alpaca(), Pacer(per_min)
    out_dir = CACHE / "quotes"; out_dir.mkdir(parents=True, exist_ok=True)
    for k, (sym, d, hm) in enumerate(moments, 1):
        f = out_dir / f"{d}_{sym}_{hm.replace(':', '')}.json"
        if f.exists():
            continue
        hh, mm = int(hm[:2]), int(hm[3:])
        p = aget(client, pacer, "/v2/stocks/quotes", {"symbols": sym, "start": et_utc(d, hh, mm),
                                                       "end": et_utc(d, hh, mm + 1) if mm < 59 else et_utc(d, hh + 1, 0),
                                                       "limit": 2000, "feed": client.feed})
        q = (p.get("quotes") or {}).get(sym, []) or []
        f.write_text(json.dumps([[x["t"], x.get("bp"), x.get("ap"), x.get("bs"), x.get("as")] for x in q]))
        if k % 200 == 0:
            print(f"quotes {k}/{len(moments)}", flush=True)


def fetch_trades(symdays: list[tuple[str, str]], start_hm="07:00", end_hm="11:30", per_min: int = 180) -> None:
    client, pacer = alpaca(), Pacer(per_min)
    out_dir = CACHE / "trades"; out_dir.mkdir(parents=True, exist_ok=True)
    for k, (sym, d) in enumerate(symdays, 1):
        f = out_dir / f"{d}_{sym}.json"
        if f.exists():
            continue
        rows, token = [], None
        while True:
            p = aget(client, pacer, "/v2/stocks/trades", {
                "symbols": sym, "start": et_utc(d, int(start_hm[:2]), int(start_hm[3:])),
                "end": et_utc(d, int(end_hm[:2]), int(end_hm[3:])), "limit": 10000,
                "feed": client.feed, "page_token": token})
            for x in (p.get("trades") or {}).get(sym, []) or []:
                rows.append([x["t"], x["p"], x["s"], x.get("c") or []])
            token = p.get("next_page_token")
            if not token:
                break
        f.write_text(json.dumps(rows))
        if k % 20 == 0:
            print(f"trades {k}/{len(symdays)}", flush=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=("news", "sec", "quotes", "trades", "pm_audit"))
    ap.add_argument("--list", help="quotes: CSV sym,day,HH:MM · trades: CSV sym,day")
    args = ap.parse_args(argv)
    uni = universe()
    if args.what == "news":
        fetch_news(sorted(uni), uni)
    elif args.what == "sec":
        fetch_sec(uni)
    elif args.what == "quotes":
        fetch_quotes([tuple(r) for r in csv.reader(open(args.list))])
    elif args.what == "trades":
        fetch_trades([tuple(r[:2]) for r in csv.reader(open(args.list))])
    else:
        fetch_pm_audit([r[0] for r in csv.reader(open(args.list))])
    return 0



# ------------------------------------------------------------------ pre-market universe audit (F2)
def fetch_pm_audit(days: list[str], per_min: int = 180) -> None:
    """For each sampled session: names from the 2016-2026 gapper pool that
    traded +10 % over their previous close at some pre-market minute
    (07:00-09:30), priced $2-20 there, 20-day dollar volume >= $250k — and
    are NOT in that day's 09:30-gap universe. Their bars 04:00-11:30 are
    stored. The pool itself is a stated undercount: a name that never gapped
    at an open in 2016-2026 is not queried."""
    client, pacer = alpaca(), Pacer(per_min)
    uni = universe()
    out_dir = CACHE / "pm_audit"; out_dir.mkdir(parents=True, exist_ok=True)
    all_days = sorted(uni)
    pos = {d: k for k, d in enumerate(all_days)}
    appear: dict[str, list[int]] = defaultdict(list)
    for d, ss in uni.items():
        for s in ss:
            appear[s].append(pos[d])
    for n_day, d in enumerate(days, 1):
        f = out_dir / f"{d}.json"
        if f.exists():
            continue
        k = pos[d]
        pool = sorted(s for s, ks in appear.items() if s not in set(uni[d]) and any(abs(x - k) <= 500 for x in ks))
        start_d = (date.fromisoformat(d) - timedelta(days=45)).isoformat()
        found = {}
        for i in range(0, len(pool), 100):
            chunk = pool[i:i + 100]
            daily: dict[str, list] = defaultdict(list); token = None
            while True:
                p = aget(client, pacer, "/v2/stocks/bars", {"symbols": ",".join(chunk), "timeframe": "1Day",
                                                            "start": start_d, "end": d, "limit": 10000,
                                                            "adjustment": "raw", "feed": client.feed, "page_token": token})
                for s, rows in (p.get("bars") or {}).items():
                    daily[s].extend(rows or [])
                token = p.get("next_page_token")
                if not token:
                    break
            prev = {}
            for s, rows in daily.items():
                past = [r for r in rows if r["t"][:10] < d]
                if len(past) >= 5:
                    last = past[-20:]
                    dv20 = sum(r["c"] * r["v"] for r in last) / len(last)
                    prev[s] = (past[-1]["c"], dv20)
            cands = [s for s in chunk if s in prev and prev[s][1] >= 250_000 and prev[s][0] > 0]
            if not cands:
                continue
            pm: dict[str, list] = defaultdict(list); token = None
            while True:
                p = aget(client, pacer, "/v2/stocks/bars", {"symbols": ",".join(cands), "timeframe": "1Min",
                                                            "start": et_utc(d, 7, 0), "end": et_utc(d, 9, 30),
                                                            "limit": 10000, "adjustment": "raw", "feed": client.feed,
                                                            "page_token": token})
                for s, rows in (p.get("bars") or {}).items():
                    pm[s].extend(rows or [])
                token = p.get("next_page_token")
                if not token:
                    break
            for s, rows in pm.items():
                pc = prev[s][0]
                if any(r["h"] >= 1.10 * pc and 2.0 <= r["h"] <= 20.0 for r in rows):
                    found[s] = {"pc": pc, "dv20": prev[s][1]}
        for s in list(found):
            rows, token = [], None
            while True:
                p = aget(client, pacer, "/v2/stocks/bars", {"symbols": s, "timeframe": "1Min", "start": et_utc(d, 4, 0),
                                                            "end": et_utc(d, 11, 30), "limit": 10000,
                                                            "adjustment": "raw", "feed": client.feed, "page_token": token})
                rows.extend([[r["t"], r["o"], r["h"], r["l"], r["c"], r["v"]] for r in (p.get("bars") or {}).get(s, []) or []])
                token = p.get("next_page_token")
                if not token:
                    break
            found[s]["bars"] = rows
        f.write_text(json.dumps({"pool": len(pool), "in_universe": len(uni[d]), "missing": found}))
        print(f"pm_audit {n_day}/{len(days)} {d}: pool {len(pool)}, missing qualifiers {len(found)}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
