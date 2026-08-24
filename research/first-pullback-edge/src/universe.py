"""Point-in-time momentum universe (brief sections 2 and 3).

Two layers, because they answer different questions and have different data
requirements.

  DAILY LAYER  - `candidate_days()` scans every session in the study period
                 using only the open, the PREVIOUS close, and PRIOR-day
                 liquidity. Nothing from the rest of the day is read. It runs
                 on daily bars, which reach back years, so it is what sizes
                 the available sample.

  INTRADAY LAYER - `qualify_intraday()` is the scanner as it would actually
                 have run: at a fixed wall-clock time (09:35 ET by default) it
                 looks at the bars printed SO FAR and decides. It needs minute
                 bars, which is where the data wall is.

SURVIVORSHIP. The symbol list is the weak point and it is stated, not hidden.
`nasdaq_listed()` returns names that are listed TODAY. Every company that
delisted, was acquired or went to the pink sheets during the study period is
missing from it, and this universe delists constantly. Yahoo 404s on delisted
tickers, so there is no way to repair it from the free tier.
`polygon_symbols_on()` is the fix and it needs a key: Polygon's
/v3/reference/tickers accepts a `date` and returns what was listed THAT DAY,
delisted names included.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, asdict

from .data import Bar, BarProvider, PolygonProvider, _curl
from .indicators import SessionState

UA_NASDAQ = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25000&exchange="


@dataclass
class ScanRules:
    """Scanner parameters. DISCOVERY dials, never entry gates - the shipped
    strategy has scanGates=false (ross-fp-v4.pine line 330)."""
    price_min: float = 2.0
    price_max: float = 20.0
    gap_min_pct: float = 10.0
    rvol_min: float = 2.0
    min_dollar_volume: float = 250_000.0
    low_float_max_m: float = 20.0
    scan_time_et: dt.time = dt.time(9, 35)


@dataclass
class CandidateDay:
    sym: str
    day: str
    prev_close: float
    open_px: float
    gap_pct: float
    prior_dollar_volume_20d: float
    split_on_day: bool
    reverse_split_ratio: float | None
    source: str
    # intraday fields, filled only when minute bars exist
    scan_ts: int | None = None
    scan_price: float | None = None
    scan_gap_pct: float | None = None
    scan_cum_volume: float | None = None
    scan_dollar_volume: float | None = None
    scan_rvol_at_time: float | None = None
    qualified_intraday: bool | None = None
    float_m: float | None = None
    float_provenance: str = "unavailable"
    catalyst: str | None = None
    catalyst_source: str | None = None


def nasdaq_listed(exchanges=("NASDAQ", "NYSE", "AMEX")) -> list[dict]:
    """CURRENT listings from the Nasdaq screener. Survivorship-biased by
    construction - see the module docstring."""
    out: dict[str, dict] = {}
    for ex in exchanges:
        raw = _curl(UA_NASDAQ + ex)
        if not raw:
            continue
        try:
            rows = json.loads(raw)["data"]["table"]["rows"]
        except (KeyError, TypeError, json.JSONDecodeError):
            continue
        for r in rows:
            sym = (r.get("symbol") or "").strip().upper()
            if not sym or not sym.isalpha():
                continue
            try:
                price = float((r.get("lastsale") or "$0").lstrip("$").replace(",", ""))
            except ValueError:
                price = 0.0
            try:
                mcap = float((r.get("marketCap") or "0").replace(",", "") or 0)
            except ValueError:
                mcap = 0.0
            out[sym] = dict(sym=sym, price=price, mcap=mcap,
                            name=(r.get("name") or "")[:60], exchange=ex)
    return list(out.values())


def polygon_symbols_on(day: dt.date) -> list[dict]:
    """Point-in-time symbol list including names that later delisted.
    Requires POLYGON_API_KEY; this is the survivorship-bias fix."""
    p = PolygonProvider()
    p._require()
    rows = p.tickers_on(day)
    return [dict(sym=r["ticker"], name=r.get("name", "")[:60],
                 exchange=r.get("primary_exchange", ""), type=r.get("type", ""))
            for r in rows if r.get("type") in ("CS", "ADRC")]


def detect_reverse_split(prev_close: float, open_px: float,
                         tolerance: float = 0.04) -> float | None:
    """CLAUDE.md rule 6: a reverse split is only called when the ratio between
    two independently-adjusted sources is a CLEAN INTEGER. A 2.54x move is a
    move; a 5.00x 'move' with no volume is an adjustment artefact.

    Returns the integer ratio when one is detected, else None.
    """
    if prev_close <= 0 or open_px <= 0:
        return None
    ratio = open_px / prev_close
    for r in (2, 3, 4, 5, 6, 8, 10, 15, 20, 25, 30, 40, 50, 100):
        if abs(ratio - r) / r <= tolerance:
            return float(r)
    return None


def candidate_days(provider: BarProvider, symbols: list[str],
                   start: dt.date, end: dt.date, rules: ScanRules,
                   progress=None) -> list[CandidateDay]:
    """Daily-bar point-in-time universe.

    For each (symbol, session) the only inputs are:
      - the PREVIOUS session's close        (known before the open)
      - today's OPEN                        (known at 09:30:00)
      - the trailing 20-session dollar volume, EXCLUDING today

    Today's high, close, volume and range are never read. tests assert this.
    """
    out: list[CandidateDay] = []
    for n, sym in enumerate(symbols):
        if progress and n % 100 == 0:
            progress(n, len(symbols), sym)
        # one request per symbol: every bar in it shares ONE adjustment basis,
        # which is what stops a reverse split becoming a fabricated +10,000%
        # gap (research/momentum-replication/HISTORY.md defect 1).
        if hasattr(provider, "daily_bundle"):
            bars, splits = provider.daily_bundle(sym, start - dt.timedelta(days=40), end)
        else:
            bars, splits = provider.daily_bars(sym, start - dt.timedelta(days=40), end), {}
        if len(bars) < 25:
            continue
        split_days = set()
        for ev in (splits or {}).values():
            try:
                split_days.add(dt.datetime.fromtimestamp(ev["date"], dt.timezone.utc).date())
            except (KeyError, TypeError, OSError):
                pass
        dollar = [b.v * b.c for b in bars]
        for i in range(21, len(bars)):
            b = bars[i]
            d = b.et.date()
            if not (start <= d <= end):
                continue
            prev = bars[i - 1]
            if prev.c <= 0:
                continue
            gap = (b.o - prev.c) / prev.c * 100.0
            if not (rules.price_min <= b.o <= rules.price_max):
                continue
            if gap < rules.gap_min_pct:
                continue
            prior_dv = sum(dollar[i - 20:i]) / 20.0
            if prior_dv < rules.min_dollar_volume:
                continue
            rs = detect_reverse_split(prev.c, b.o)
            out.append(CandidateDay(
                sym=sym, day=d.isoformat(), prev_close=prev.c, open_px=b.o,
                gap_pct=gap, prior_dollar_volume_20d=prior_dv,
                split_on_day=d in split_days, reverse_split_ratio=rs,
                source=provider.name))
    return out


def candidate_days_grouped(provider, start: dt.date, end: dt.date,
                          rules: ScanRules, warmup_days: int = 40,
                          progress=None) -> list[CandidateDay]:
    """Point-in-time universe built from GROUPED DAILY bars — one call per
    trading date, every ticker that printed that day.

    This is the survivorship-free construction and it is why it exists:
    `candidate_days()` iterates a symbol LIST, and any list is a list of
    things that still exist. Grouped daily is a snapshot of what actually
    traded on the date, so a company that gapped 40% in 2025 and delisted in
    2026 is present on its own day and absent afterwards, with no special
    handling.

    Prices are requested RAW (`adjusted=false`), so a reverse split appears
    as a genuine discontinuity in the series rather than being smoothed away.
    `detect_reverse_split` flags a clean-integer ratio per CLAUDE.md rule 6;
    the flag is recorded, never used as a silent veto.

    Point-in-time discipline is unchanged: for session D the only inputs are
    D's OPEN, D-1's CLOSE, and the trailing-20-session dollar volume that
    EXCLUDES D.
    """
    day = start - dt.timedelta(days=warmup_days)
    prev_close: dict[str, float] = {}
    dv_hist: dict[str, list[float]] = {}
    out: list[CandidateDay] = []
    sessions = 0
    while day <= end:
        if day.weekday() >= 5:
            day += dt.timedelta(days=1)
            continue
        rows = provider.grouped_daily(day)
        if not rows:                       # market holiday
            day += dt.timedelta(days=1)
            continue
        sessions += 1
        if progress:
            progress(day, sessions, len(rows), len(out))
        for r in rows:
            sym = r.get("T")
            o, c, v = r.get("o"), r.get("c"), r.get("v", 0.0)
            if not sym or o is None or c is None:
                continue
            pc = prev_close.get(sym)
            hist = dv_hist.setdefault(sym, [])
            if day >= start and pc and pc > 0 and len(hist) >= 20:
                gap = (o - pc) / pc * 100.0
                prior_dv = sum(hist[-20:]) / 20.0
                if (rules.price_min <= o <= rules.price_max
                        and gap >= rules.gap_min_pct
                        and prior_dv >= rules.min_dollar_volume):
                    out.append(CandidateDay(
                        sym=sym, day=day.isoformat(), prev_close=pc, open_px=o,
                        gap_pct=gap, prior_dollar_volume_20d=prior_dv,
                        split_on_day=False,
                        reverse_split_ratio=detect_reverse_split(pc, o),
                        source=f"{provider.name}:grouped"))
            prev_close[sym] = c
            hist.append(v * c)
            if len(hist) > 25:
                del hist[:-25]
        day += dt.timedelta(days=1)
    return out


def qualify_intraday(sym: str, day: dt.date, bars: list[Bar], prev_close: float | None,
                     rules: ScanRules,
                     same_time_profile: dict[int, float] | None = None) -> CandidateDay | None:
    """The scanner as it would have run, frozen at rules.scan_time_et.

    Only bars whose OPEN time is at or before the scan time are read. The
    returned row carries the scan timestamp so every downstream trade can be
    checked against it: an entry can never precede its own qualification.
    """
    cut = [b for b in bars if b.et.time() <= rules.scan_time_et]
    if not cut:
        return None
    st = SessionState(sym, day, prev_close=prev_close,
                      same_time_cum_volume=same_time_profile)
    snap = None
    for b in cut:
        snap = st.update(b)
    assert snap is not None
    price = snap.bar.c
    gap = snap.gap_pct
    qualifies = (rules.price_min <= price <= rules.price_max
                 and gap is not None and gap >= rules.gap_min_pct
                 and snap.cum_dollar_volume >= rules.min_dollar_volume)
    return CandidateDay(
        sym=sym, day=day.isoformat(), prev_close=prev_close or float("nan"),
        open_px=cut[0].o,
        gap_pct=gap if gap is not None else float("nan"),
        prior_dollar_volume_20d=float("nan"), split_on_day=False,
        reverse_split_ratio=None, source="intraday",
        scan_ts=snap.bar.ts, scan_price=price, scan_gap_pct=gap,
        scan_cum_volume=snap.cum_volume,
        scan_dollar_volume=snap.cum_dollar_volume,
        scan_rvol_at_time=snap.rvol_at_time,
        qualified_intraday=bool(qualifies))


def to_records(rows: list[CandidateDay]) -> list[dict]:
    return [asdict(r) for r in rows]
