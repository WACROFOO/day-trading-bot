"""Market-data providers, behind one interface.

The study needs three things the free tier cannot all give at once:
  1. 1-minute OHLCV including extended hours, with real pre-market VOLUME
  2. multi-year history (1,000-3,000 ticker-days needs years, not weeks)
  3. delisted-symbol retention (this universe delists constantly)

`YahooProvider` is the only one that runs without credentials here, and it
satisfies none of those three fully. The others are written against each
vendor's documented REST shape and activate the moment a key is present in the
environment. `capabilities()` is what the data-quality section of the report
prints - it is measured where it can be, declared where it cannot.
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import os
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/121.0 Safari/537.36")

CACHE = Path(__file__).resolve().parent.parent / "data" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Bar:
    ts: int          # epoch seconds, bar OPEN time
    o: float
    h: float
    l: float
    c: float
    v: float

    @property
    def et(self) -> dt.datetime:
        return dt.datetime.fromtimestamp(self.ts, ET)


@dataclass
class Capability:
    name: str
    minute_bars: bool
    minute_history_days: int | None      # measured where possible
    premarket_bars: bool
    premarket_volume: bool | None        # None = untested
    delisted_retained: bool | None
    quotes: bool
    trades: bool
    halts: bool
    news: bool
    corporate_actions: str               # how splits are handled
    adjusted: str
    available_here: bool
    note: str


def _curl(url: str, headers: dict[str, str] | None = None, tries: int = 3,
          timeout: int = 45) -> str | None:
    return _curl2(url, headers, tries, timeout)[1]


def _curl2(url: str, headers: dict[str, str] | None = None, tries: int = 3,
           timeout: int = 45) -> tuple[int, str | None]:
    """As `_curl`, but returns the HTTP status too.

    This exists because of a defect found on 2026-08-24: Polygon answers a
    rate-limit with HTTP 429 and a JSON body. `json.loads` succeeds,
    `.get("results")` returns [], and the caller records "no data for this
    date" — a throttled request became a silent hole in the universe. Status
    codes are never optional when the error path is also valid JSON.
    """
    args = ["curl", "-s", "--compressed", "--max-time", str(timeout),
            "-o", "-", "-w", "\n%{http_code}", "-H", f"User-Agent: {UA}"]
    for k, v in (headers or {}).items():
        args += ["-H", f"{k}: {v}"]
    args.append(url)
    for attempt in range(tries):
        p = subprocess.run(args, capture_output=True, text=True)
        if p.returncode == 0 and p.stdout:
            body, _, code = p.stdout.rpartition("\n")
            try:
                return int(code.strip()), body
            except ValueError:
                return 0, body
        time.sleep(1.5 * (attempt + 1))
    return 0, None


class BarProvider:
    """Interface. Every method is point-in-time by contract: it returns bars
    for a closed period and nothing about what happened after it."""
    name = "abstract"

    def minute_bars(self, sym: str, day: dt.date, premarket: bool = True) -> list[Bar]:
        raise NotImplementedError

    def daily_bars(self, sym: str, start: dt.date, end: dt.date) -> list[Bar]:
        raise NotImplementedError

    def capabilities(self) -> Capability:
        raise NotImplementedError

    # -- shared cache plumbing -------------------------------------------
    def _cache_path(self, kind: str, key: str) -> Path:
        d = CACHE / self.name / kind
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{key}.json.gz"

    def _cache_get(self, kind: str, key: str):
        p = self._cache_path(kind, key)
        if p.exists():
            with gzip.open(p, "rt") as fh:
                return json.load(fh)
        return None

    def _cache_put(self, kind: str, key: str, obj) -> None:
        with gzip.open(self._cache_path(kind, key), "wt") as fh:
            json.dump(obj, fh)


class YahooProvider(BarProvider):
    """Yahoo chart v8. Free, no key, and the only one live in this container.

    Three limitations that the study inherits and must state, not paper over:
      - 1-minute history reaches roughly 30 calendar days; a period1 older
        than that returns HTTP 422. MEASURED, see reports/data_quality.md.
      - Extended-hours bars are returned but their volume is 0 for EVERY
        symbol including AAPL/SPY. An API limitation, not thin tape.
      - Delisted tickers 404. Anything that left the exchange is invisible,
        which is textbook survivorship bias for this universe.

    Adjustment: each chart response is adjusted independently, so bars from
    two different requests are NOT comparable across a split boundary. Daily
    series are therefore always fetched in ONE request per symbol.
    """
    name = "yahoo"

    def _chart(self, sym: str, p1: int, p2: int, interval: str,
               prepost: bool) -> dict | None:
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
               f"?period1={p1}&period2={p2}&interval={interval}"
               f"&includePrePost={'true' if prepost else 'false'}"
               f"&events=div%2Csplit")
        raw = _curl(url)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _to_bars(res: dict) -> list[Bar]:
        ts = res.get("timestamp") or []
        q = (res.get("indicators", {}).get("quote") or [{}])[0]
        out = []
        for i, t in enumerate(ts):
            o, h, l, c, v = (q.get("open") or [])[i], (q.get("high") or [])[i], \
                            (q.get("low") or [])[i], (q.get("close") or [])[i], \
                            (q.get("volume") or [])[i]
            if None in (o, h, l, c):
                continue
            out.append(Bar(int(t), float(o), float(h), float(l), float(c),
                           float(v or 0.0)))
        return out

    def minute_bars(self, sym: str, day: dt.date, premarket: bool = True) -> list[Bar]:
        key = f"{sym}_{day.isoformat()}_{int(premarket)}"
        cached = self._cache_get("minute", key)
        if cached is not None:
            return [Bar(*b) for b in cached]
        # one request per calendar day, so a split inside the window cannot
        # straddle two differently-adjusted responses
        start = dt.datetime.combine(day, dt.time(0, 0), ET)
        p1 = int(start.timestamp())
        p2 = int((start + dt.timedelta(days=1)).timestamp())
        d = self._chart(sym, p1, p2, "1m", premarket)
        bars: list[Bar] = []
        if d and not (d.get("chart") or {}).get("error"):
            res = (d["chart"].get("result") or [None])[0]
            if res:
                bars = [b for b in self._to_bars(res) if b.et.date() == day]
        self._cache_put("minute", key, [list(asdict(b).values()) for b in bars])
        return bars

    def daily_bundle(self, sym: str, start: dt.date, end: dt.date) -> tuple[list[Bar], dict]:
        """Bars AND the split calendar from ONE response.

        One request matters: every bar in a single response shares one
        adjustment basis, so a reverse split inside the window cannot appear
        as a gap between two differently-adjusted halves. That defect
        (fabricated +10,555% gaps) is HISTORY.md #1 in the sibling package.
        """
        key = f"{sym}_{start.isoformat()}_{end.isoformat()}"
        cached = self._cache_get("daily", key)
        if cached is not None:
            return [Bar(*b) for b in cached["bars"]], cached.get("splits", {})
        p1 = int(dt.datetime.combine(start, dt.time(0, 0), ET).timestamp())
        p2 = int(dt.datetime.combine(end + dt.timedelta(days=1), dt.time(0, 0), ET).timestamp())
        d = self._chart(sym, p1, p2, "1d", False)
        bars: list[Bar] = []
        splits: dict = {}
        if d and not (d.get("chart") or {}).get("error"):
            res = (d["chart"].get("result") or [None])[0]
            if res:
                bars = self._to_bars(res)
                splits = (res.get("events") or {}).get("splits") or {}
        self._cache_put("daily", key, {"bars": [list(asdict(b).values()) for b in bars],
                                       "splits": splits})
        return bars, splits

    def daily_bars(self, sym: str, start: dt.date, end: dt.date) -> list[Bar]:
        return self.daily_bundle(sym, start, end)[0]

    def splits(self, sym: str, start: dt.date, end: dt.date) -> dict:
        return self.daily_bundle(sym, start, end)[1]

    def capabilities(self) -> Capability:
        return Capability(
            name="Yahoo chart v8 (unauthenticated)",
            minute_bars=True,
            minute_history_days=30,
            premarket_bars=True,
            premarket_volume=False,
            delisted_retained=False,
            quotes=False, trades=False, halts=False, news=False,
            corporate_actions="split calendar in-response; each response "
                              "independently adjusted - never stitch windows",
            adjusted="adjusted, basis varies per response",
            available_here=True,
            note="Only provider reachable without credentials in this "
                 "environment. Fails all three of the study's hard data needs.")


class _KeyedProvider(BarProvider):
    env_key = ""

    def __init__(self):
        self.key = os.environ.get(self.env_key, "")

    @property
    def enabled(self) -> bool:
        return bool(self.key)

    def _require(self):
        if not self.enabled:
            raise RuntimeError(
                f"{self.name}: set {self.env_key} in the environment. "
                f"See reports/data_quality.md for the acquisition steps.")


class PolygonProvider(_KeyedProvider):
    """Polygon.io — rebranded to Massive (massive.com) in 2026. The API host
    `api.polygon.io` still answers, so nothing here changed but the name.

    THE FREE "Stocks Basic" PLAN IS ENOUGH TO RUN THIS STUDY. Verified from
    the vendor docs 2026-08-24 (reports/data_acquisition.md carries the
    quotes):
      - minute aggregates are "Included in all Stocks plans" and cover
        "pre-market, regular market, and after-hours sessions"
      - 2 years of history (Starter, $29/mo, extends this to 5)
      - the tickers reference takes `date=` and `active=false` and returns
        names that have since delisted, with a `delisted_utc` field —
        also included in all plans. THIS IS THE SURVIVORSHIP FIX.
      - grouped daily returns EVERY US ticker for one date in ONE call, so
        the whole universe costs ~500 calls for two years
      - free-tier data recency is end-of-day, which is exactly what a
        historical backtest wants and no obstacle at all
    The only free-tier cost is 5 calls/minute, handled by `_throttle` below.
    """
    name = "polygon"
    env_key = "POLYGON_API_KEY"
    BASE = "https://api.polygon.io"
    # free tier: 5 calls/min. Set POLYGON_CALLS_PER_MIN=0 to disable on paid.
    _last_calls: list[float] = []

    def __init__(self):
        super().__init__()
        if not self.key:
            # the rebrand shipped a second env var name; accept either
            self.key = os.environ.get("MASSIVE_API_KEY", "")
        self.calls_per_min = int(os.environ.get("POLYGON_CALLS_PER_MIN", "5"))

    def _get(self, url: str, what: str) -> dict:
        """One request, with the rate limit respected and 429 treated as an
        ERROR to retry rather than as an empty result."""
        for attempt in range(6):
            self._throttle()
            code, body = _curl2(url, tries=1)
            if code == 200 and body:
                try:
                    d = json.loads(body)
                except json.JSONDecodeError:
                    d = {}
                if d.get("status") != "ERROR":
                    return d
            if code == 429 or (body and '"status":"ERROR"' in body):
                wait = min(60.0, 5.0 * (attempt + 1))
                time.sleep(wait)
                continue
            if code in (403, 404):
                return {}
            time.sleep(2.0 * (attempt + 1))
        raise RuntimeError(f"{self.name}: {what} failed after retries "
                           f"(last HTTP {code}). Rate limit or plan gate.")

    def _throttle(self):
        """Free tier is 5 calls/min. Sleeping is cheaper than a 429 storm."""
        if self.calls_per_min <= 0:
            return
        now = time.time()
        PolygonProvider._last_calls = [t for t in PolygonProvider._last_calls
                                       if now - t < 60.0]
        if len(PolygonProvider._last_calls) >= self.calls_per_min:
            wait = 60.0 - (now - PolygonProvider._last_calls[0]) + 0.25
            if wait > 0:
                time.sleep(wait)
            now = time.time()
            PolygonProvider._last_calls = [t for t in PolygonProvider._last_calls
                                           if now - t < 60.0]
        PolygonProvider._last_calls.append(time.time())

    def grouped_daily(self, day: dt.date, include_otc: bool = False) -> list[dict]:
        """EVERY US ticker's daily bar for one date, in ONE request.

        This is what makes a multi-year universe affordable on 5 calls/min:
        ~500 trading days in two years is ~500 calls, not 6,742.
        """
        self._require()
        key = f"grouped_{day.isoformat()}_{int(include_otc)}"
        cached = self._cache_get("grouped", key)
        if cached is not None:
            return cached
        url = (f"{self.BASE}/v2/aggs/grouped/locale/us/market/stocks/"
               f"{day.isoformat()}?adjusted=false"
               f"&include_otc={'true' if include_otc else 'false'}&apiKey={self.key}")
        rows = self._get(url, f"grouped_daily {day}").get("results", [])
        self._cache_put("grouped", key, rows)
        return rows

    def _agg(self, sym: str, mult: int, span: str, frm: str, to: str,
             adjusted: bool) -> list[Bar]:
        self._require()
        url = (f"{self.BASE}/v2/aggs/ticker/{sym}/range/{mult}/{span}/{frm}/{to}"
               f"?adjusted={'true' if adjusted else 'false'}&sort=asc&limit=50000"
               f"&apiKey={self.key}")
        d = self._get(url, f"aggs {sym} {frm}")
        return [Bar(int(r["t"] // 1000), r["o"], r["h"], r["l"], r["c"], r.get("v", 0.0))
                for r in (d.get("results") or [])]

    def minute_month(self, sym: str, year: int, month: int) -> dict[str, list[Bar]]:
        """A whole ticker-MONTH of minute bars in ONE request, split by day.

        This is the difference between a study that fits in the free tier and
        one that does not. At 5 calls/minute, fetching per ticker-day costs
        one call per day plus one per prior day needed for the RVOL profile;
        per ticker-month it costs one call for roughly 21 sessions AND hands
        back the prior days for free. The aggregate limit is 50,000 bars and
        a month of 1-minute extended-hours data is ~20,000, so a month fits.
        """
        key = f"{sym}_{year}-{month:02d}"
        cached = self._cache_get("minute_month", key)
        if cached is None:
            first = dt.date(year, month, 1)
            last = (dt.date(year + (month == 12), (month % 12) + 1, 1)
                    - dt.timedelta(days=1))
            # adjusted=false: raw traded prices. The split calendar is applied
            # separately so a reverse split cannot fabricate a gap.
            bars = self._agg(sym, 1, "minute", first.isoformat(), last.isoformat(), False)
            by_day: dict[str, list] = {}
            for b in bars:
                by_day.setdefault(b.et.date().isoformat(), []).append(
                    list(asdict(b).values()))
            self._cache_put("minute_month", key, by_day)
            cached = by_day
        return {d: [Bar(*r) for r in rows] for d, rows in cached.items()}

    def minute_bars(self, sym: str, day: dt.date, premarket: bool = True) -> list[Bar]:
        # served out of the month cache, so a whole month costs one request
        bars = self.minute_month(sym, day.year, day.month).get(day.isoformat(), [])
        if not premarket:
            bars = [b for b in bars if dt.time(9, 30) <= b.et.time() < dt.time(16, 0)]
        return bars

    def daily_bars(self, sym: str, start: dt.date, end: dt.date) -> list[Bar]:
        return self._agg(sym, 1, "day", start.isoformat(), end.isoformat(), False)

    def splits(self, sym: str) -> list[dict]:
        self._require()
        return self._get(f"{self.BASE}/v3/reference/splits?ticker={sym}"
                         f"&limit=1000&apiKey={self.key}",
                         f"splits {sym}").get("results", [])

    def tickers_on(self, day: dt.date, active: bool | None = None) -> list[dict]:
        """Point-in-time symbol list INCLUDING delisted names - this is the
        call that removes survivorship bias from the universe."""
        self._require()
        out, url = [], (f"{self.BASE}/v3/reference/tickers?market=stocks"
                        f"&date={day.isoformat()}&limit=1000&apiKey={self.key}")
        if active is not None:
            url += f"&active={'true' if active else 'false'}"
        while url:
            d = self._get(url, f"tickers {day}")
            out += d.get("results", [])
            nxt = d.get("next_url")
            url = f"{nxt}&apiKey={self.key}" if nxt else None
        return out

    def all_tickers(self, types=("CS", "ADRC"), active=None) -> list[dict]:
        """Every ticker the reference DB holds, active and/or delisted.

        `active=false` with no date returns the whole historical delisted set
        with a `delisted_utc` on each row — page one alone spans 2004-2017.
        Union that with `active=true` and you have a symbol universe that a
        company leaving the exchange does not fall out of, which is the
        survivorship fix for any period grouped-daily cannot reach.
        """
        self._require()
        out: list[dict] = []
        for t in types:
            for act in ([active] if active is not None else [True, False]):
                url = (f"{self.BASE}/v3/reference/tickers?market=stocks"
                       f"&type={t}&active={'true' if act else 'false'}"
                       f"&limit=1000&apiKey={self.key}")
                page = 0
                while url and page < 60:
                    d = self._get(url, f"tickers {t} active={act} p{page}")
                    out += d.get("results", [])
                    nxt = d.get("next_url")
                    url = f"{nxt}&apiKey={self.key}" if nxt else None
                    page += 1
        seen, uniq = set(), []
        for r in out:
            k = (r.get("ticker"), r.get("delisted_utc"))
            if k not in seen:
                seen.add(k)
                uniq.append(r)
        return uniq

    def quotes(self, sym: str, day: dt.date) -> list[dict]:
        """NBBO. Needed for a real spread instead of the range-quartile proxy."""
        self._require()
        return self._get(f"{self.BASE}/v3/quotes/{sym}?timestamp={day.isoformat()}"
                         f"&limit=50000&apiKey={self.key}",
                         f"quotes {sym}").get("results", [])

    def capabilities(self) -> Capability:
        paid = self.calls_per_min <= 0
        return Capability(
            name=("Polygon.io / Massive — Stocks "
                  + ("Starter or above" if paid else "Basic (FREE)")),
            minute_bars=True, minute_history_days=1825 if paid else 730,
            premarket_bars=True, premarket_volume=True,
            delisted_retained=True, quotes=True, trades=True,
            halts=False, news=True,
            corporate_actions="v3/reference/splits + adjusted=false raw bars",
            adjusted="caller's choice; this study requests raw",
            available_here=self.enabled,
            note=("Recommended. The FREE Basic plan already satisfies all "
                  "three hard needs (minute bars with extended hours, 2 years "
                  "of history, delisted retention) at 5 calls/min; $29/mo "
                  "Starter lifts that to 5 years and unlimited calls. Halts "
                  "still need a separate source — see data_acquisition.md."))


class AlpacaProvider(_KeyedProvider):
    """Alpaca market data. NOTE the free tier is IEX-only (~2-3% of
    consolidated volume) - RVOL computed on it is not comparable to any
    threshold calibrated on consolidated tape. Only the SIP feed is usable
    here, which means Algo Trader Plus."""
    name = "alpaca"
    env_key = "ALPACA_API_KEY_ID"
    BASE = "https://data.alpaca.markets/v2"

    @property
    def enabled(self) -> bool:
        return bool(self.key and self.secret)

    def _hdr(self):
        return {"APCA-API-KEY-ID": self.key, "APCA-API-SECRET-KEY": self.secret}

    # documented 200/min on Basic; 351/min observed in a burst on 2026-08-25.
    # Throttled below the observed figure, not at it.
    _calls: list[float] = []

    def __init__(self):
        super().__init__()
        self.secret = os.environ.get("ALPACA_API_SECRET_KEY", "")
        self.feed = os.environ.get("ALPACA_FEED", "sip")
        self.calls_per_min = int(os.environ.get("ALPACA_CALLS_PER_MIN", "180"))

    def _throttle(self):
        if self.calls_per_min <= 0:
            return
        now = time.time()
        AlpacaProvider._calls = [t for t in AlpacaProvider._calls if now - t < 60.0]
        if len(AlpacaProvider._calls) >= self.calls_per_min:
            time.sleep(max(0.0, 60.0 - (now - AlpacaProvider._calls[0]) + 0.2))
            now = time.time()
            AlpacaProvider._calls = [t for t in AlpacaProvider._calls if now - t < 60.0]
        AlpacaProvider._calls.append(time.time())

    def _bars(self, sym: str, start: dt.datetime, end: dt.datetime,
              timeframe: str = "1Min") -> list[Bar]:
        """Paged bar pull. `end` is always well in the past for a backtest,
        which is what lets a free account read the SIP feed at all:
        'the end parameter must be at least 15 minutes old to query SIP data
        without a subscription' (docs.alpaca.markets/us/docs/market-data-faq).
        """
        self._require()
        base = (f"{self.BASE}/stocks/{sym}/bars?timeframe={timeframe}"
                f"&start={start.isoformat()}&end={end.isoformat()}"
                f"&adjustment=raw&feed={self.feed}&limit=10000")
        out: list[Bar] = []
        url = base
        for _ in range(50):                       # page cap: a month is ~3
            self._throttle()
            code, raw = _curl2(url, self._hdr(), tries=3)
            if code != 200 or not raw:
                if code in (403, 404):
                    break
                raise RuntimeError(f"alpaca {sym}: HTTP {code} {(raw or '')[:100]}")
            d = json.loads(raw)
            for r in d.get("bars") or []:
                ts = int(dt.datetime.fromisoformat(r["t"].replace("Z", "+00:00")).timestamp())
                out.append(Bar(ts, r["o"], r["h"], r["l"], r["c"], r.get("v", 0.0)))
            tok = d.get("next_page_token")
            if not tok:
                break
            url = base + f"&page_token={tok}"
        return out

    def minute_month(self, sym: str, year: int, month: int) -> dict[str, list[Bar]]:
        """A whole ticker-month of SIP minute bars, split by session date.
        Same contract as PolygonProvider.minute_month so the driver does not
        care which provider it is talking to."""
        key = f"{sym}_{year}-{month:02d}_{self.feed}"
        cached = self._cache_get("minute_month", key)
        if cached is None:
            first = dt.datetime.combine(dt.date(year, month, 1), dt.time(4, 0), ET)
            nxt = dt.date(year + (month == 12), (month % 12) + 1, 1)
            last = dt.datetime.combine(nxt, dt.time(4, 0), ET)
            # A free account may only read SIP when `end` is at least 15
            # minutes old. For the CURRENT month the month-end is in the
            # future, which silently returns nothing — clamp it.
            cutoff = dt.datetime.now(ET) - dt.timedelta(minutes=20)
            if last > cutoff:
                last = cutoff
            if last <= first:
                return {}
            bars = self._bars(sym, first, last)
            by_day: dict[str, list] = {}
            for b in bars:
                by_day.setdefault(b.et.date().isoformat(), []).append(
                    list(asdict(b).values()))
            self._cache_put("minute_month", key, by_day)
            cached = by_day
        return {d: [Bar(*r) for r in rows] for d, rows in cached.items()}

    def minute_bars(self, sym: str, day: dt.date, premarket: bool = True) -> list[Bar]:
        bars = self.minute_month(sym, day.year, day.month).get(day.isoformat(), [])
        if not premarket:
            bars = [b for b in bars if dt.time(9, 30) <= b.et.time() < dt.time(16, 0)]
        return bars

    def daily_bars(self, sym: str, start: dt.date, end: dt.date) -> list[Bar]:
        return self._bars(sym, dt.datetime.combine(start, dt.time(0, 0), ET),
                          dt.datetime.combine(end + dt.timedelta(days=1), dt.time(0, 0), ET),
                          timeframe="1Day")

    def daily_bars_multi(self, symbols: list[str], start: dt.date,
                         end: dt.date) -> dict[str, list[Bar]]:
        """Daily bars for MANY symbols per request.

        The screening layer needs open / previous close / trailing dollar
        volume for thousands of names over years. One symbol per request is
        tens of thousands of calls; the multi-symbol endpoint carries a
        comma-separated list and pages through 10,000 bars at a time, which
        turns the same job into hundreds.
        """
        self._require()
        out: dict[str, list[Bar]] = {s: [] for s in symbols}
        base = (f"{self.BASE}/stocks/bars?symbols={','.join(symbols)}"
                f"&timeframe=1Day&start={start.isoformat()}&end={end.isoformat()}"
                f"&adjustment=raw&feed={self.feed}&limit=10000")
        url = base
        for _ in range(400):
            self._throttle()
            code, raw = _curl2(url, self._hdr(), tries=3)
            if code != 200 or not raw:
                if code in (403, 404):
                    break
                raise RuntimeError(f"alpaca multi: HTTP {code} {(raw or '')[:120]}")
            d = json.loads(raw)
            for sym, rows in (d.get("bars") or {}).items():
                out.setdefault(sym, [])
                for r in rows:
                    ts = int(dt.datetime.fromisoformat(
                        r["t"].replace("Z", "+00:00")).timestamp())
                    out[sym].append(Bar(ts, r["o"], r["h"], r["l"], r["c"],
                                        r.get("v", 0.0)))
            tok = d.get("next_page_token")
            if not tok:
                break
            url = base + f"&page_token={tok}"
        return out

    def capabilities(self) -> Capability:
        return Capability(
            name=f"Alpaca market data (Basic, feed={self.feed})",
            minute_bars=True, minute_history_days=3650,
            premarket_bars=True, premarket_volume=(self.feed == "sip"),
            delisted_retained=True, quotes=True, trades=True,
            halts=False, news=True,
            corporate_actions="adjustment=raw|split|dividend|all",
            adjusted="caller's choice; this study requests raw",
            available_here=self.enabled,
            note="MEASURED 2026-08-25 on a free Basic key: feed=sip returns "
                 "CONSOLIDATED historical bars back to 2016 at 351 calls/min "
                 "observed. feed=iex on the same SGLY session returned 0.2% "
                 "of consolidated volume and 23% of the minutes - never "
                 "compute RVOL on it, and never trust its session high.")


class NasdaqHaltFeed:
    """Free LULD halt/resume data — but PROSPECTIVE ONLY.

    `nasdaqtrader.com/rss.aspx?feed=tradehalts` is public, needs no key, and
    carries the halt timestamp AND the resumption timestamp to the second,
    with the reason code (LUDP = LULD pause, T1/T12 = news, M = market-wide).
    MEASURED 2026-08-24: 99 items, five reason codes present.

    The catch, stated because it decides how the feed can be used: it is a
    ROLLING window, not an archive. The 99 items span a handful of dates.
    There is no historical download here, so this cannot backfill the halt
    flags on a two-year study — it can only accumulate them going forward.
    Poll it daily into a local table and the halt model becomes real for
    every session AFTER you start; sessions before it stay flagged-unknown.
    """
    URL = "https://www.nasdaqtrader.com/rss.aspx?feed=tradehalts"

    @staticmethod
    def fetch() -> list[dict]:
        import re
        raw = _curl(NasdaqHaltFeed.URL)
        if not raw:
            return []
        out = []
        for block in re.findall(r"<item>(.*?)</item>", raw, re.S):
            def f(tag):
                m = re.search(rf"<ndaq:{tag}>(.*?)</ndaq:{tag}>", block, re.S)
                return m.group(1).strip() if m else None
            sym = f("IssueSymbol")
            if not sym:
                continue
            out.append(dict(symbol=sym, halt_date=f("HaltDate"),
                            halt_time=f("HaltTime"), reason=f("ReasonCode"),
                            resume_date=f("ResumptionDate"),
                            resume_quote_time=f("ResumptionQuoteTime"),
                            resume_trade_time=f("ResumptionTradeTime")))
        return out


PROVIDERS: dict[str, type[BarProvider]] = {
    "yahoo": YahooProvider,
    "polygon": PolygonProvider,
    "alpaca": AlpacaProvider,
}


def get_provider(name: str | None = None) -> BarProvider:
    """Resolve a provider. Prefers an explicitly requested one, then the best
    credentialed one, then Yahoo with its limitations intact."""
    if name:
        return PROVIDERS[name]()
    for cand in ("polygon", "alpaca"):
        p = PROVIDERS[cand]()
        if getattr(p, "enabled", False):
            return p
    return YahooProvider()


def capability_matrix() -> list[dict]:
    return [asdict(PROVIDERS[n]().capabilities()) for n in PROVIDERS]
