#!/usr/bin/env python3
"""The "where are we" command, on the Alpaca stack.

    ./now                     phase header + board for the saved watchlist
    ./now MSGY WYHG           same, for these symbols (watchlist untouched)
    ./now --set MSGY WYHG     save the watchlist, then report
    ./now --scan              scan the market first, board the survivors
    ./now --desk              after the board, open the workstation on them

One report shape, phase-aware. The board is one row per ticker — price, the
gate scorecard, a verdict and the catalyst status — computed from the same
scan, catalyst and session code the desk uses, so board and desk cannot
disagree.

Gates:  P price in band · F float under 20M (SEC shares outstanding is an
upper bound: under the cap proves it, over the cap is unknown) · C catalyst
inside 24h · R still rising (≤25% off the session high) · V above VWAP ·
E above the 9 EMA.   '+' pass · '-' fail · '?' unknown.

Verdict vocabulary is deliberately non-actionable: REJECT on any hard fail,
WATCH while chart or catalyst is incomplete, REVIEW when every gate is green
inside the session window, LOG outside it. Nothing here places an order.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from momentum_platform.catalyst import assess  # noqa: E402
from momentum_platform.datasources.alpaca_source import (  # noqa: E402
    AlpacaError, IEX_VOLUME_FLOOR_SCALE, client_from_env, fetch_records, scan_market,
)
from momentum_platform.datasources.sec_source import SecError, client_from_env as sec_from_env  # noqa: E402
from momentum_platform.scanners.five_pillars import (  # noqa: E402
    FLOAT_MAX_SHARES, PRICE_BAND_EVIDENCE, PRICE_MAX, PRICE_MIN,
)

ET = ZoneInfo("America/New_York")
FR = ZoneInfo("Europe/Paris")
WATCHLIST = ROOT / "watchlist.txt"
G, Y, R, D, B, O = "\033[92m", "\033[93m", "\033[91m", "\033[2m", "\033[1m", "\033[0m"

# (minutes from ET midnight, label, what to do). Carried over from the
# original ./now; the boundaries are the operator's own playbook, not course
# content, and are labelled as such in knowledge-base/daytrade-dash/PLAYBOOK.md.
PHASES = [
    (0,        "CLOSED",        "nothing to do"),
    (4 * 60,   "PRE-MARKET 04", "too thin to act — platform is up, liquidity is not"),
    (7 * 60,   "PRE-MARKET 07", "scan: ./now --scan   (the move can happen HERE)"),
    (8 * 60,   "NEWS WAVE",     "catalyst on the top 2; watch flames turning red on your names"),
    (9 * 60,   "LIST LOCKS",    "final watchlist, 3 names max — stop adding"),
    (9 * 60 + 30, "OPENING DRIVE", "HANDS OFF — let the first candles print"),
    (9 * 60 + 35, "PRIME WINDOW",  "pullbacks 1-2 only; read the chart before every entry"),
    (10 * 60 + 30, "LATE WINDOW",  "reduce — past the 90-minute mark, new entries must be better"),
    (11 * 60,  "WIND-DOWN",     "new entries only on a perfect setup"),
    (11 * 60 + 30, "OFF-BOOK",  "past the hard stop — review, do not trade"),
    (15 * 60,  "POWER HOUR",    "watch only — nothing here has been measured"),
    (16 * 60,  "AFTER HOURS",   "session over — review, then tomorrow's list"),
    (20 * 60,  "CLOSED",        "nothing to do"),
]
PHASE_PAINT = {"PRIME WINDOW": G, "OFF-BOOK": R, "AFTER HOURS": R, "CLOSED": D,
               "PRE-MARKET 04": D, "POWER HOUR": D}


def phase_at(now_et: dt.datetime):
    m = now_et.hour * 60 + now_et.minute
    if now_et.weekday() >= 5:
        return "CLOSED (weekend)", "nothing to do", ""
    cur, nxt = PHASES[0], None
    for i, p in enumerate(PHASES):
        if m >= p[0]:
            cur, nxt = p, (PHASES[i + 1] if i + 1 < len(PHASES) else None)
    left = ""
    if nxt:
        d = nxt[0] - m
        left = f"  -> {nxt[1]} in " + (f"{d // 60}h{d % 60:02d}m" if d >= 60 else f"{d}m")
    return cur[1], cur[2], left


def header() -> None:
    now = dt.datetime.now(ET)
    name, advice, left = phase_at(now)
    paint = PHASE_PAINT.get(name, Y)
    print("=" * 78)
    print(f"{B}{now:%a %d %b}  {now:%H:%M} ET  ({now.astimezone(FR):%H:%M} Paris){O}   "
          f"{paint}{name}{O}{D}{left}{O}")
    print(f"{D}{advice}{O}")
    band = f"${PRICE_MIN:g}-{PRICE_MAX:g}"
    tag = "operator override" if PRICE_BAND_EVIDENCE == "operator_override" else "confirmed course"
    print(f"{D}price band {band} ({tag}) · float cap {FLOAT_MAX_SHARES/1e6:.0f}M · "
          f"IEX volume floor ×{IEX_VOLUME_FLOOR_SCALE}{O}")
    print("=" * 78)


def load_watchlist() -> list:
    try:
        return [s.strip().upper() for s in WATCHLIST.read_text().split() if s.strip()]
    except OSError:
        return []


def save_watchlist(symbols: list) -> None:
    WATCHLIST.write_text("\n".join(symbols) + "\n")


def ema(values: list, n: int):
    k, prev = 2 / (n + 1), None
    for i, v in enumerate(values):
        prev = v if i == 0 else v * k + prev * (1 - k)
    return prev


def board(symbols: list) -> int:
    client = client_from_env()
    records = fetch_records(client, symbols)
    refs = {r["symbol"]: r for r in records if r["type"] == "reference"}
    bars: dict = {}
    for r in records:
        if r["type"] == "bar" and r.get("tf") != "10s":
            bars.setdefault(r["symbol"], []).append(r)
    news = {}
    for r in records:
        if r["type"] == "news":
            cur = news.get(r["symbol"])
            if cur is None or r["published_at"] > cur["published_at"]:
                news[r["symbol"]] = r

    try:
        sec = sec_from_env()
    except Exception:
        sec = None

    inside = phase_at(dt.datetime.now(ET))[0] in ("PRIME WINDOW", "OPENING DRIVE", "LATE WINDOW")
    print(f"\n{B}{'SYM':<6}{'LAST':>8}{'CHG':>8}{'RVOL':>7}   {'P F C R V E':<12} {'VERDICT':<8} {'EXCH':<7}{'COUNTRY':<14}CATALYST{O}")
    for sym in symbols:
        ref, bs = refs.get(sym, {}), bars.get(sym, [])
        if not bs:
            print(f"{sym:<6}{'—':>8}{'—':>8}{'—':>7}   {'? ? ? ? ? ?':<12} {'WATCH':<8} no bars on IEX yet")
            continue
        last, prev = bs[-1]["close"], ref.get("prev_close")
        chg = (last / prev - 1) * 100 if prev else None
        high = max(b["high"] for b in bs)
        vol = sum(b["volume"] for b in bs)
        rvol = vol / ref["avg_daily_volume"] if ref.get("avg_daily_volume") else None
        closes = [b["close"] for b in bs]
        pv = sum(((b["high"] + b["low"] + b["close"]) / 3) * b["volume"] for b in bs)
        vv = sum(b["volume"] for b in bs)
        vwap = pv / vv if vv else None

        # Gates ------------------------------------------------------------
        P = "+" if PRICE_MIN <= last <= PRICE_MAX else "-"
        so = ref.get("float_shares")
        if so is None:
            F = "?"
        elif ref.get("float_quality") == "verified":
            F = "+" if so < FLOAT_MAX_SHARES else "-"
        else:                                    # shares outstanding: a bound
            F = "+" if so < FLOAT_MAX_SHARES else "?"
        hl = news.get(sym)
        published = dt.datetime.fromisoformat(hl["published_at"].replace("Z", "+00:00")) if hl else None
        filings = []
        if sec is not None:
            try:
                filings = sec.recent_filings(sym, since_days=90)
            except SecError:
                filings = []
        read = assess(sym, hl["headline"] if hl else None, published, filings=filings)
        C = "+" if read.flame_color in ("red", "orange", "yellow") else ("-" if hl is not None or news else "?")
        R_ = "+" if high and last >= high * 0.75 else "-"
        V = "+" if vwap and last > vwap else "-"
        E = "+" if len(closes) >= 9 and last > ema(closes, 9) else ("?" if len(closes) < 9 else "-")

        hard = P == "-" or F == "-" or R_ == "-" or read.verdict() == "AVOID"
        unknown = "?" in (F, C, E)
        if hard:
            verdict, paint = "REJECT", R
        elif unknown or C == "-" or V == "-" or E == "-":
            verdict, paint = "WATCH", Y
        else:
            verdict, paint = ("REVIEW", G) if inside else ("LOG", D)

        cat = f"{read.verdict()} · {read.grade.label}"
        if read.has_live_takedown:
            cat += " · 424B LIVE"
        elif read.dilution_filings:
            cat += " · shelf on file"
        gates = " ".join([P, F, C, R_, V, E])
        exch = (ref.get("exchange") or "—")[:6]
        ctry = (ref.get("country") or "—")[:13]
        print(f"{B}{sym:<6}{O}{last:>8.2f}{(f'{chg:+.1f}%' if chg is not None else '—'):>8}"
              f"{(f'{rvol:.1f}x' if rvol else '—'):>7}   {gates:<12} {paint}{verdict:<8}{O} "
              f"{D}{exch:<7}{ctry:<14}{O}{D}{cat}{O}")
        if hl:
            age = read.age_min / 60 if read.age_min is not None else None
            print(f"      {D}{hl['headline'][:80]}"
                  f"{f'  ({age:.1f}h ago)' if age is not None else ''}{O}")
    print(f"\n{D}+ pass  - fail  ? unknown.  F from SEC shares outstanding is an upper bound: "
          f"'+' proves float under the cap, '?' means the bound is above it.{O}")
    print(f"{D}Verdicts are vocabulary, not instructions. The chart still decides.{O}\n")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="phase header + board")
    ap.add_argument("symbols", nargs="*")
    ap.add_argument("--set", action="store_true", help="save the symbols as the watchlist")
    ap.add_argument("--scan", action="store_true", help="scan the market first")
    ap.add_argument("--desk", action="store_true", help="open the workstation afterwards")
    ap.add_argument("--top", type=int, default=6)
    args = ap.parse_args(argv)

    header()
    symbols = [s.upper() for s in args.symbols]
    if args.set and symbols:
        save_watchlist(symbols)
        print(f"{D}watchlist saved: {', '.join(symbols)}{O}")
    try:
        if args.scan:
            print(f"{D}scanning the market…{O}")
            found = scan_market(client_from_env(), min_price=PRICE_MIN, max_price=PRICE_MAX,
                                top=args.top, log=lambda m: print(D + m + O))
            if found["stale"]:
                print(f"{Y}NOTE: these are the {found['session_date']} session's moves — "
                      f"today has no completed bar yet.{O}")
            scanned = [r["symbol"] for r in found["rows"]]
            symbols = list(dict.fromkeys(symbols + scanned))
        if not symbols:
            symbols = load_watchlist()
        if not symbols:
            print(f"{Y}no symbols. Give some, ./now --set them, or ./now --scan.{O}")
            return 1
        board(symbols)
    except AlpacaError as exc:
        print(f"\n{R}{exc}{O}")
        return 2
    if args.desk:
        os.execvp("bash", ["bash", str(ROOT / "scripts" / "start.sh"), ",".join(symbols)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
