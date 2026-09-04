"""IBKR market scanner union and reference data, read-only.

The screener half of the handoff audit: ten TWS scanner queries (five scan
codes on the two NASDAQ tiers), fifty rows each, in the operator's price band,
merged into one candidate set and quoted from live snapshots. The union is a
DISCOVERY set — it is not exhaustive, the payload says so, and the chart still
defines the setup.

Also here: the reference and minute-history records the desk session is
built from (previous close, average volume, 52-week high, daily bars, the
day's one-minute bars), because they come from the same TWS connection.

Nothing here transmits anything. Every call is a request for data.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Callable, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
# 04:00-20:00 ET in five-minute buckets: the extended session, the finest bar
# size IBKR will return for ten sessions in a single historical request.
PROFILE_BUCKETS = 192
PROFILE_BUCKET_MINUTES = 5

SCAN_CODES = ("TOP_PERC_GAIN", "HOT_BY_VOLUME", "TOP_VOLUME_RATE", "TOP_TRADE_RATE", "MOST_ACTIVE")
LOCATIONS = ("STK.NASDAQ.NMS", "STK.NASDAQ.SCM")     # Global (Select) Market, Capital Market
ROWS_PER_SCAN = 50
DELAYED_TYPES = (3, 4)


class IbkrError(RuntimeError):
    pass


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _num(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def _scanner_subscription(code: str, location: str, min_price: float, max_price: float, rows: int):
    try:
        from ib_async import ScannerSubscription
    except ImportError:
        ScannerSubscription = _PlainSubscription
    return ScannerSubscription(instrument="STK", locationCode=location, scanCode=code,
                               abovePrice=min_price, belowPrice=max_price, numberOfRows=rows)


class _PlainSubscription:
    def __init__(self, **kw):
        self.__dict__.update(kw)


NOT_STOCK = ("ETF", "ETN", "FUND", "PREFERRED", "WARRANT", "RIGHT", "UNIT", "TRUST", "NOTE")


def is_common_stock(stock_type: Optional[str]) -> bool:
    """Ross's universe is common stock (ADRs included: many of the runners are
    Chinese listings). Leveraged ETFs, ETNs, funds, preferreds, warrants,
    rights and units gap and run too, and they are not what the strategy is
    about — a 2x daily ETF on a runner was the desk's top "gainer" once.
    Unknown types are kept and the row says so."""
    if not stock_type:
        return True
    t = stock_type.upper()
    return not any(word in t for word in NOT_STOCK)


_STOCK_TYPES: Dict[str, str] = {}          # symbol -> stockType, resolved once per process


def stock_type_of(ib, contract, symbol: Optional[str] = None) -> Optional[str]:
    """The instrument type from contract details, cached per symbol. Scanner
    hits carry only a thin contract (no stockType), so a leveraged ETF looked
    like a stock until this lookup was added."""
    sym = symbol or getattr(contract, "symbol", None)
    if sym in _STOCK_TYPES:
        return _STOCK_TYPES[sym]
    st = getattr(contract, "stockType", None) if contract is not None else None
    if not st:
        try:
            details = ib.reqContractDetails(contract)
            st = getattr(details[0], "stockType", None) if details else None
        except Exception:
            st = None
    if sym:
        _STOCK_TYPES[sym] = st or ""
    return st or None


def scan_union(ib, min_price: float, max_price: float, rows: int = ROWS_PER_SCAN,
               codes: Iterable[str] = SCAN_CODES, locations: Iterable[str] = LOCATIONS,
               log: Optional[Callable[[str], None]] = None) -> Dict[str, dict]:
    """Run every (code, location) scan and merge the hits by symbol.

    Returns symbol -> {symbol, exchange, name, scans, contract}. A query that
    fails is logged and skipped; the caller's notes say how many ran."""
    say = log or (lambda m: None)
    found: Dict[str, dict] = {}
    excluded: Dict[str, str] = {}
    ran = failed = 0
    for location in locations:
        for code in codes:
            sub = _scanner_subscription(code, location, min_price, max_price, rows)
            try:
                hits = ib.reqScannerData(sub)
                ran += 1
            except Exception as exc:
                failed += 1
                say(f"  scan {code} {location} failed: {exc}")
                continue
            for hit in hits or []:
                cd = getattr(hit, "contractDetails", None)
                c = getattr(cd, "contract", None)
                sym = getattr(c, "symbol", None)
                if not sym:
                    continue
                stock_type = getattr(cd, "stockType", None)
                if not is_common_stock(stock_type):
                    excluded[sym] = stock_type
                    continue
                entry = found.setdefault(sym, {
                    "symbol": sym, "exchange": getattr(c, "primaryExchange", None) or "NASDAQ",
                    "name": getattr(cd, "longName", None), "scans": [], "contract": c,
                    "stock_type": stock_type,
                })
                if code not in entry["scans"]:
                    entry["scans"].append(code)
    found["__meta__"] = {"ran": ran, "failed": failed, "excluded": excluded}
    return found


MAX_QUOTES = 150


def prioritise(found: Dict[str, dict], limit: int = MAX_QUOTES) -> List[dict]:
    """Which hits to quote, in order: every TOP_PERC_GAIN hit first (that scan
    is already sorted by the gain we screen on), then names several scans
    agree on, then the rest — capped, because a snapshot of an illiquid name
    can take eleven seconds and a union of ten scans can be four hundred names."""
    entries = [v for k, v in found.items() if k != "__meta__"]
    entries.sort(key=lambda e: (0 if "TOP_PERC_GAIN" in e["scans"] else 1, -len(e["scans"]), e["symbol"]))
    return entries[:limit] if limit else entries


def snapshot_rows(ib, found: Dict[str, dict], clock: Callable[[], datetime] = lambda: datetime.now(UTC),
                  chunk: int = 75, limit: int = MAX_QUOTES,
                  log: Optional[Callable[[str], None]] = None) -> tuple:
    """Quote the prioritised scan hits from live snapshots. Returns (rows, notes)."""
    say = log or (lambda m: None)
    entries = prioritise(found, limit)
    skipped = max(0, len(found) - 1 - len(entries))
    # Scanner hits do not say what kind of instrument they are. Ask once per
    # symbol (cached for the life of the process) and drop the funds here,
    # before a snapshot quote is spent on them.
    excluded = found.get("__meta__", {}).get("excluded")
    kept = []
    for e in entries:
        st = e.get("stock_type") or stock_type_of(ib, e["contract"], e["symbol"])
        e["stock_type"] = st
        if not is_common_stock(st):
            if excluded is not None:
                excluded[e["symbol"]] = st
            continue
        kept.append(e)
    if len(kept) < len(entries):
        say(f"  {len(entries) - len(kept)} non-stock instruments dropped before quoting")
    entries = kept
    rows: List[dict] = []
    notes: List[str] = []
    delayed = 0
    now = clock()
    for i in range(0, len(entries), chunk):
        batch = entries[i:i + chunk]
        say(f"  quoting {i + 1}-{i + len(batch)} of {len(entries)} scan hits")
        try:
            tickers = ib.reqTickers(*[e["contract"] for e in batch])
        except Exception as exc:
            notes.append(f"snapshot batch failed: {exc}")
            continue
        for e, t in zip(batch, tickers):
            mdt = getattr(t, "marketDataType", None)
            if mdt in DELAYED_TYPES:
                delayed += 1
                continue
            price = _num(getattr(t, "last", None))
            if price is None and hasattr(t, "marketPrice"):
                try:
                    price = _num(t.marketPrice())
                except Exception:
                    price = None
            prev = _num(getattr(t, "close", None))
            if price is None or price <= 0 or not prev:
                continue
            rows.append({
                "symbol": e["symbol"], "price": round(price, 4),
                "change_pct": round((price / prev - 1) * 100, 2),
                "source": "ibkr", "as_of": _iso(now), "session": None,
                "prev_close": prev, "exchange": e["exchange"], "name": e.get("name"),
                "volume": _num(getattr(t, "volume", None)),
                "bid": _num(getattr(t, "bid", None)), "ask": _num(getattr(t, "ask", None)),
                "scans": list(e["scans"]), "stock_type": e.get("stock_type"),
            })
    if delayed:
        notes.append(f"{delayed} names reported DELAYED market data and were dropped — "
                     "the desk never shows a delayed print as live.")
    if skipped:
        notes.append(f"{skipped} further scan hits were not quoted (cap {limit}); every "
                     "TOP_PERC_GAIN hit in the band was.")
    return rows, notes


def build_ibkr_screener(ib, min_price: float, max_price: float, min_gain: float = 10.0,
                        top: int = 30, log: Optional[Callable[[str], None]] = None,
                        clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> dict:
    """The screener payload the page renders: same shape as the Alpaca/Yahoo
    screener, source "ibkr", with honest notes about what a scan union is."""
    say = log or (lambda m: None)
    say(f"  scanning NASDAQ: {len(SCAN_CODES) * len(LOCATIONS)} queries, ${min_price:g}-{max_price:g}")
    found = scan_union(ib, min_price, max_price, log=log)
    meta = found.get("__meta__", {"ran": 0, "failed": 0})
    say(f"  scan union: {len(found) - 1} names from {meta['ran']} queries")
    rows, notes = snapshot_rows(ib, found, clock=clock, log=log)
    kept = [r for r in rows if min_price <= r["price"] <= max_price and r["change_pct"] >= min_gain]
    kept.sort(key=lambda r: -r["change_pct"])
    total = meta["ran"] + meta["failed"]
    notes.insert(0, f"Union of {meta['ran']}/{total} NASDAQ scans ({', '.join(SCAN_CODES)}, "
                    f"{ROWS_PER_SCAN} rows each) — a discovery set, not an exhaustive list.")
    if meta["failed"]:
        notes.append(f"{meta['failed']} scan queries failed; see the server log.")
    excluded = meta.get("excluded") or {}
    if excluded:
        sample = ", ".join(f"{k} ({v})" for k, v in list(excluded.items())[:4])
        notes.append(f"{len(excluded)} non-stock instruments excluded (ETFs, ETNs, funds, warrants): {sample}"
                     + (" …" if len(excluded) > 4 else ""))
    return {"rows": kept[:top] if top else kept, "source": "ibkr", "asof": _iso(clock()),
            "notes": notes, "band": [min_price, max_price], "min_gain": min_gain,
            "scanned": len(found) - 1}


# ---------------------------------------------------------- reference -----

def _bar_date(b) -> str:
    d = getattr(b, "date", None)
    if isinstance(d, datetime):
        return d.date().isoformat()
    return str(d)[:10]


def daily_bars(ib, contract, lookback: str = "1 Y") -> List[dict]:
    hist = ib.reqHistoricalData(contract, "", lookback, "1 day", "TRADES", True, formatDate=2)
    return [{"d": _bar_date(b), "o": _num(b.open), "h": _num(b.high), "l": _num(b.low),
             "c": _num(b.close), "v": int(_num(b.volume) or 0)} for b in hist or []]


def reference_record(symbol: str, bars: List[dict], ticker=None, exchange: Optional[str] = None,
                     name: Optional[str] = None, today: Optional[str] = None,
                     sec: Optional[dict] = None, clock: Callable[[], datetime] = lambda: datetime.now(UTC),
                     ibkr_float: Optional[dict] = None) -> dict:
    """The reference record the session builder consumes. Previous close is
    the last COMPLETED day's close, never today's partial bar."""
    today = today or clock().astimezone(timezone(timedelta(hours=-4))).date().isoformat()
    completed = [b for b in bars if b["d"] < today and b["c"]]
    prev_close = completed[-1]["c"] if completed else None
    recent = [b["v"] for b in completed[-20:] if b["v"] > 0]
    avg_volume = sum(recent) / len(recent) if recent else None
    high_52w = max((b["h"] for b in bars[-252:] if b["h"]), default=None)
    last = _num(getattr(ticker, "last", None)) if ticker is not None else None
    last_ts = getattr(ticker, "time", None) if ticker is not None else None
    sec = sec or {}
    ibkr_float = ibkr_float or {}
    # Float, by evidence: IBKR's fundamentals float (a stated float figure) is
    # verified; SEC shares outstanding is an upper bound and says so; nothing
    # else is unknown. Shares outstanding is never relabelled as float.
    if ibkr_float.get("float"):
        float_shares, float_quality, float_asof, float_source = (
            ibkr_float["float"], "verified", ibkr_float.get("as_of"), "IBKR fundamentals (Refinitiv) total float")
    elif sec.get("shares"):
        float_shares, float_quality, float_asof, float_source = (
            sec["shares"], "shares_outstanding_proxy", sec.get("as_of"),
            "SEC " + (sec.get("basis") or "shares outstanding") + " (upper bound)")
    elif ibkr_float.get("shares_out"):
        float_shares, float_quality, float_asof, float_source = (
            ibkr_float["shares_out"], "shares_outstanding_proxy", ibkr_float.get("as_of"), "IBKR shares outstanding (upper bound)")
    else:
        float_shares, float_quality, float_asof, float_source = None, "unknown", None, None
        # Why it is unknown, in the record, so the board can say it.
        float_source = sec.get("note") or ibkr_float.get("note")
    return {
        "type": "reference", "symbol": symbol,
        "prev_close": prev_close, "avg_daily_volume": avg_volume, "high_52w": high_52w,
        "iex_last_price": last, "iex_last_ts": _iso(last_ts) if isinstance(last_ts, datetime) else None,
        "iex_bid": _num(getattr(ticker, "bid", None)) if ticker is not None else None,
        "iex_ask": _num(getattr(ticker, "ask", None)) if ticker is not None else None,
        "last_source": "ibkr",
        "exchange": exchange, "name": name,
        "country": sec.get("country"), "incorporated_in": sec.get("incorporated_in"),
        "float_shares": float_shares,
        "float_quality": float_quality,
        "float_asof": float_asof,
        "float_source": float_source,
        "daily_bars": bars,
    }


def session_start(now: Optional[datetime] = None) -> datetime:
    """04:00 ET of the trading day the desk should show, as a UTC datetime.

    Before 04:00 ET the day rolls back to the last weekday (see
    `session_day`), so a pre-dawn desk shows the last completed session and
    says so; from 04:00 the window is today's, however few prints it holds."""
    from .alpaca_source import session_day
    day = session_day(now)
    return day.replace(hour=4, minute=0, second=0, microsecond=0).astimezone(UTC)


def session_duration(now: Optional[datetime] = None) -> str:
    """The IBKR duration string that reaches back to the session start.

    IBKR takes second-based durations up to one day; a longer reach (a weekend
    desk looking at Friday) is asked for in days and cut to the window after."""
    now = now or datetime.now(UTC)
    secs = int((now - session_start(now)).total_seconds())
    if secs <= 86400:
        return f"{max(secs, 60)} S"
    return f"{-(-secs // 86400)} D"


def minute_records(ib, contract, symbol: str, duration: str = "1 D",
                   start: Optional[datetime] = None) -> List[dict]:
    """One-minute bars, extended hours included, as bar records.

    `duration` is the IBKR window: the seconds since 04:00 ET at startup, a
    short window such as "900 S" for the rolling refresh that keeps the desk's
    newest minute current without spending the historical-request budget.
    Bars before `start` are dropped: IBKR's "1 D" at 04:03 ET hands back the
    previous session, and a desk built from it showed yesterday's tape as
    "19 h behind" instead of today's first prints."""
    try:
        hist = ib.reqHistoricalData(contract, "", duration, "1 min", "TRADES", False, formatDate=2)
    except Exception:
        # A seconds-form window IBKR will not take is not a reason to run the
        # desk on last night's tape: ask for the day and cut it to the window.
        if duration.endswith(" S"):
            hist = ib.reqHistoricalData(contract, "", "2 D", "1 min", "TRADES", False, formatDate=2)
        else:
            raise
    out = []
    for b in hist or []:
        ts = b.date if isinstance(b.date, datetime) else datetime.fromisoformat(str(b.date))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        if start is not None and ts < start:
            continue
        close = _num(b.close)
        if not close or close <= 0:
            continue
        out.append({"type": "bar", "tf": "1m", "symbol": symbol, "ts": _iso(ts),
                    "open": _num(b.open), "high": _num(b.high), "low": _num(b.low),
                    "close": close, "volume": int(_num(b.volume) or 0)})
    return out


def intraday_volume_profile(ib, contract, days: int = 10,
                            exclude_day: Optional[object] = None) -> List[float]:
    """Median cumulative volume by five-minute bucket after 04:00 ET.

    This is the baseline for time-of-day relative volume. The simple daily
    measure divides part of a day by whole prior days, so before the open a
    premarket runner reads a fraction of 1x however violent its tape is and
    the RVOL pillar can never pass. Here each prior session is walked from
    04:00 ET, its cumulative share count recorded at every five-minute mark,
    and the sessions compared at the same mark.

    A bucket's baseline is the median across the prior sessions THAT HAD
    TRADED by that time; sessions still at zero are left out rather than
    dragging the median to zero and making every multiple infinite. A bucket
    no prior session traded in has no baseline (0.0) and the caller falls back
    to the daily measure and says so.

    Approximation: the threshold RVOL >= 5 is the course's; measuring it this
    way is this desk's own method, not a Warrior production setting.
    """
    hist = ib.reqHistoricalData(contract, "", f"{int(days)} D", "5 mins",
                                "TRADES", False, formatDate=2)
    per_day: Dict[object, List[float]] = {}
    for b in hist or []:
        ts = b.date if isinstance(b.date, datetime) else datetime.fromisoformat(str(b.date))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        et = ts.astimezone(ET)
        idx = ((et.hour - 4) * 60 + et.minute) // PROFILE_BUCKET_MINUTES
        if idx < 0 or idx >= PROFILE_BUCKETS:
            continue
        day = et.date()
        if exclude_day is not None and day == exclude_day:
            continue          # today is the thing being measured, not a baseline
        per_day.setdefault(day, [0.0] * PROFILE_BUCKETS)[idx] += float(_num(b.volume) or 0.0)
    if not per_day:
        return []
    cumulative: List[List[float]] = []
    for day in sorted(per_day):
        run, row = 0.0, []
        for v in per_day[day]:
            run += v
            row.append(run)
        if run > 0:
            cumulative.append(row)
    if not cumulative:
        return []
    profile = []
    for i in range(PROFILE_BUCKETS):
        traded = [row[i] for row in cumulative if row[i] > 0]
        profile.append(float(median(traded)) if traded else 0.0)
    return profile


def store_records(store, symbol: str) -> List[dict]:
    """Complete ten-second candles from the live store as bar records."""
    return [{"type": "bar", "tf": "10s", "symbol": symbol, "ts": _iso(b.ts),
             "open": b.open, "high": b.high, "low": b.low, "close": b.close, "volume": b.volume}
            for b in store.candles_10s(symbol)]


def float_from_ibkr(ib, contract) -> dict:
    """Float from IBKR's fundamentals snapshot (Refinitiv ReportSnapshot):
    the SharesOut element carries TotalFloat. Returns {} when the account has
    no fundamentals entitlement or the element is absent — never a guess."""
    try:
        xml = ib.reqFundamentalData(contract, "ReportSnapshot")
    except Exception:
        return {}
    return parse_float_xml(xml or "")


def parse_float_xml(xml: str) -> dict:
    import re
    m = re.search(r'<SharesOut([^>]*)>\s*([\d.eE+]+)\s*</SharesOut>', xml)
    if not m:
        return {}
    attrs, shares_out = m.group(1), m.group(2)
    fl = re.search(r'TotalFloat="([\d.eE+]+)"', attrs)
    date = re.search(r'Date="([^"]+)"', attrs)
    out = {"shares_out": _num(shares_out), "as_of": date.group(1) if date else None}
    if fl and _num(fl.group(1)):
        out["float"] = _num(fl.group(1))
    return out


def sec_profile(symbol: str) -> dict:
    """Shares outstanding (an upper bound on float) and country from EDGAR,
    free and official.

    A failure is reported in `note` rather than swallowed: an unknown float
    that is a network hiccup and one that is a genuine EDGAR gap look
    identical on the board, and only one of the two is worth retrying."""
    try:
        from .sec_source import client_from_env
        sec = client_from_env()
    except Exception as exc:
        return {"note": f"EDGAR client unavailable: {exc}"}
    try:
        so = sec.shares_outstanding(symbol) or {}
    except Exception as exc:
        return {"note": f"EDGAR lookup failed: {exc}"}
    note = None
    if not so.get("shares"):
        try:
            known = sec.cik_for(symbol) is not None
        except Exception:
            known = False
        note = ("EDGAR has no shares-outstanding figure for this registrant"
                if known else "ticker is not in EDGAR's company list")
    try:
        prof = sec.company_profile(symbol) or {}
    except Exception:
        prof = {}
    return {"shares": so.get("shares"), "as_of": so.get("as_of"),
            "basis": so.get("basis"), "note": note,
            "country": prof.get("business_country") or prof.get("incorporation_desc"),
            "incorporated_in": prof.get("incorporation_desc") or prof.get("state_of_incorporation")}


def news_records(symbols: List[str], since: Optional[datetime] = None) -> tuple:
    """Headlines from Alpaca's free news endpoint when keys exist; IBKR news
    needs its own subscriptions. Returns (records, note)."""
    try:
        from .alpaca_source import client_from_env
        client = client_from_env()
    except Exception as exc:
        return [], f"no headline source: {exc}"
    start = _iso(since or datetime.now(UTC) - timedelta(days=2))
    out = []
    try:
        for item in client.news(symbols, limit=50, start=start):
            published = item.get("created_at") or item.get("updated_at")
            headline = item.get("headline")
            if not published or not headline:
                continue
            for symbol in item.get("symbols", []):
                if symbol in symbols:
                    out.append({"type": "news", "symbol": symbol, "provider_id": str(item.get("id")),
                                "published_at": published, "first_observed_at": published,
                                "headline": headline, "category": item.get("source")})
    except Exception as exc:
        return [], f"headlines unavailable: {exc}"
    return out, None
