"""Measured data-quality report (brief section 29).

Nothing in here is taken from a vendor's marketing page. Every row is the
result of a request made from this container, and the failures are recorded as
failures. No strategy conclusion in this study is allowed to be stronger than
this file.
"""
from __future__ import annotations

import datetime as dt
import json
import time
from collections import Counter
from pathlib import Path

from .data import ET, YahooProvider, capability_matrix, _curl

OUT = Path(__file__).resolve().parent.parent / "results"


def probe_minute_history(provider, sym: str = "AAPL",
                         days_back=(2, 10, 20, 25, 30, 35, 45, 60, 120, 365)) -> list[dict]:
    """How far back does 1-minute data actually go? Measured, per lookback."""
    rows = []
    today = dt.datetime.now(ET).date()
    for d in days_back:
        day = today - dt.timedelta(days=d)
        while day.weekday() >= 5:
            day -= dt.timedelta(days=1)
        try:
            bars = provider.minute_bars(sym, day)
            rows.append(dict(days_back=d, day=day.isoformat(), bars=len(bars),
                             ok=len(bars) > 0, error=None))
        except Exception as e:                                  # noqa: BLE001
            rows.append(dict(days_back=d, day=day.isoformat(), bars=0, ok=False,
                             error=str(e)[:120]))
        time.sleep(0.2)
    return rows


def probe_premarket_volume(provider, syms=("AAPL", "SPY", "TSLA", "NVDA")) -> list[dict]:
    """The decisive test from research/momentum-replication/DATA-SOURCES.md:
    do the 04:00-09:30 bars carry non-zero volume? If the most liquid tickers
    on the market return zero, it is the API, not the tape."""
    rows = []
    today = dt.datetime.now(ET).date()
    day = today - dt.timedelta(days=3)
    while day.weekday() >= 5:
        day -= dt.timedelta(days=1)
    for s in syms:
        bars = provider.minute_bars(s, day, premarket=True)
        pm = [b for b in bars if b.et.time() < dt.time(9, 30)]
        rows.append(dict(symbol=s, day=day.isoformat(), premarket_bars=len(pm),
                         with_volume=sum(1 for b in pm if b.v > 0),
                         rth_bars=len(bars) - len(pm)))
        time.sleep(0.2)
    return rows


def probe_delisted(provider, syms=("MULN", "ATVI", "TWTR", "SIVBQ", "FRCB",
                                   "AMTD", "SNDL", "BBBYQ", "WEWKQ")) -> list[dict]:
    """Survivorship (brief section 3). Names that left the exchange during a
    plausible study period. A 404 means the universe cannot contain them."""
    rows = []
    end = dt.datetime.now(ET).date()
    start = end - dt.timedelta(days=1500)
    for s in syms:
        bars = provider.daily_bars(s, start, end)
        rows.append(dict(symbol=s, daily_bars=len(bars),
                         retained=len(bars) > 0,
                         last_bar=bars[-1].et.date().isoformat() if bars else None))
        time.sleep(0.2)
    return rows


def probe_missing_minutes(provider, syms: list[str], days: list[dt.date]) -> dict:
    """Missing bars inside RTH. Yahoo omits empty minutes, so a gap is either
    'no trade printed' or 'the stock was halted' and the feed cannot tell you
    which. Counted, and every affected trade carries halt_flag."""
    gaps = Counter()
    total_expected = total_present = 0
    per_day = []
    for sym in syms:
        for day in days:
            bars = [b for b in provider.minute_bars(sym, day)
                    if dt.time(9, 30) <= b.et.time() < dt.time(16, 0)]
            if not bars:
                continue
            present = len(bars)
            span = int((bars[-1].ts - bars[0].ts) / 60) + 1
            total_present += present
            total_expected += span
            miss = span - present
            if miss:
                gaps[sym] += miss
            per_day.append(dict(sym=sym, day=day.isoformat(), present=present,
                                span=span, missing=miss))
    return dict(total_expected=total_expected, total_present=total_present,
                missing=total_expected - total_present,
                missing_pct=(100.0 * (total_expected - total_present) / total_expected)
                if total_expected else 0.0,
                by_symbol=dict(gaps), per_day=per_day)


def probe_suspicious(provider, syms: list[str], days: list[dt.date]) -> dict:
    """Bars that fail basic sanity: non-positive prices, high<low, close
    outside [low,high], zero-volume bars with a non-zero range."""
    bad = Counter()
    n = 0
    for sym in syms:
        for day in days:
            for b in provider.minute_bars(sym, day):
                n += 1
                if min(b.o, b.h, b.l, b.c) <= 0:
                    bad["non_positive_price"] += 1
                if b.h < b.l:
                    bad["high_below_low"] += 1
                if not (b.l - 1e-9 <= b.c <= b.h + 1e-9):
                    bad["close_outside_range"] += 1
                if not (b.l - 1e-9 <= b.o <= b.h + 1e-9):
                    bad["open_outside_range"] += 1
                if b.v == 0 and (b.h - b.l) > 0:
                    bad["zero_volume_with_range"] += 1
    return dict(bars_checked=n, issues=dict(bad))


def run(provider=None, syms: list[str] | None = None,
        days: list[dt.date] | None = None) -> dict:
    provider = provider or YahooProvider()
    report = dict(
        generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        provider=provider.name,
        capability_matrix=capability_matrix(),
        minute_history_probe=probe_minute_history(provider),
        premarket_volume_probe=probe_premarket_volume(provider),
        delisted_probe=probe_delisted(provider),
        timezone="America/New_York; DST handled by zoneinfo, bar timestamps "
                 "are epoch seconds converted at read time",
        quote_coverage="NONE. Spread is a proxy: 25th percentile of recent "
                       "1-minute ranges, floored at one tick.",
        trade_coverage="NONE. No tick or trade-level data, so intrabar "
                       "sequence is unknowable and ambiguity is a policy.",
        halt_coverage="NONE. Missing minutes are flagged as possible halts; "
                      "no LULD halt/resume feed is reachable here.",
        news_coverage="NONE point-in-time. Catalyst classification cannot be "
                      "done without a timestamped historical news feed.",
        float_coverage="NONE point-in-time. Float is a current snapshot at "
                       "best, which is not the float on the trade date.",
    )
    if syms and days:
        report["missing_minutes"] = probe_missing_minutes(provider, syms, days)
        report["suspicious_bars"] = probe_suspicious(provider, syms, days)
    return report


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    rep = run()
    (OUT / "data_quality.json").write_text(json.dumps(rep, indent=2))
    print(json.dumps({k: v for k, v in rep.items()
                      if k not in ("capability_matrix",)}, indent=2)[:4000])
