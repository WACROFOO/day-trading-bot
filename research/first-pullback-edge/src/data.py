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
    args = ["curl", "-s", "--compressed", "--max-time", str(timeout),
            "-H", f"User-Agent: {UA}"]
    for k, v in (headers or {}).items():
        args += ["-H", f"{k}: {v}"]
    args.append(url)
    for attempt in range(tries):
        p = subprocess.run(args, capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip():
            return p.stdout
        time.sleep(1.5 * (attempt + 1))
    return None


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
    """polygon.io Stocks Starter (~$29/mo at time of writing).

    The recommended provider for this study: consolidated SIP, 5 years of
    1-minute aggregates, extended hours WITH volume, delisted tickers
    retained, and an explicit `adjusted=false` so raw prices can be used with
    a separate split calendar (which is what an intraday study wants).
    """
    name = "polygon"
    env_key = "POLYGON_API_KEY"
    BASE = "https://api.polygon.io"

    def _agg(self, sym: str, mult: int, span: str, frm: str, to: str,
             adjusted: bool) -> list[Bar]:
        self._require()
        url = (f"{self.BASE}/v2/aggs/ticker/{sym}/range/{mult}/{span}/{frm}/{to}"
               f"?adjusted={'true' if adjusted else 'false'}&sort=asc&limit=50000"
               f"&apiKey={self.key}")
        raw = _curl(url)
        if not raw:
            return []
        d = json.loads(raw)
        return [Bar(int(r["t"] // 1000), r["o"], r["h"], r["l"], r["c"], r.get("v", 0.0))
                for r in (d.get("results") or [])]

    def minute_bars(self, sym: str, day: dt.date, premarket: bool = True) -> list[Bar]:
        key = f"{sym}_{day.isoformat()}"
        cached = self._cache_get("minute", key)
        if cached is not None:
            bars = [Bar(*b) for b in cached]
        else:
            # adjusted=false: raw traded prices. The split calendar is applied
            # separately so a reverse split cannot fabricate a gap.
            bars = self._agg(sym, 1, "minute", day.isoformat(), day.isoformat(), False)
            self._cache_put("minute", key, [list(asdict(b).values()) for b in bars])
        if not premarket:
            bars = [b for b in bars if dt.time(9, 30) <= b.et.time() < dt.time(16, 0)]
        return bars

    def daily_bars(self, sym: str, start: dt.date, end: dt.date) -> list[Bar]:
        return self._agg(sym, 1, "day", start.isoformat(), end.isoformat(), False)

    def splits(self, sym: str) -> list[dict]:
        self._require()
        raw = _curl(f"{self.BASE}/v3/reference/splits?ticker={sym}&limit=1000&apiKey={self.key}")
        return json.loads(raw).get("results", []) if raw else []

    def tickers_on(self, day: dt.date, active: bool | None = None) -> list[dict]:
        """Point-in-time symbol list INCLUDING delisted names - this is the
        call that removes survivorship bias from the universe."""
        self._require()
        out, url = [], (f"{self.BASE}/v3/reference/tickers?market=stocks"
                        f"&date={day.isoformat()}&limit=1000&apiKey={self.key}")
        if active is not None:
            url += f"&active={'true' if active else 'false'}"
        while url:
            raw = _curl(url)
            if not raw:
                break
            d = json.loads(raw)
            out += d.get("results", [])
            nxt = d.get("next_url")
            url = f"{nxt}&apiKey={self.key}" if nxt else None
        return out

    def quotes(self, sym: str, day: dt.date) -> list[dict]:
        """NBBO. Needed for a real spread instead of the range-quartile proxy."""
        self._require()
        raw = _curl(f"{self.BASE}/v3/quotes/{sym}?timestamp={day.isoformat()}"
                    f"&limit=50000&apiKey={self.key}")
        return json.loads(raw).get("results", []) if raw else []

    def capabilities(self) -> Capability:
        return Capability(
            name="Polygon.io Stocks (Starter or above)",
            minute_bars=True, minute_history_days=1825,
            premarket_bars=True, premarket_volume=True,
            delisted_retained=True, quotes=True, trades=True,
            halts=False, news=True,
            corporate_actions="v3/reference/splits + adjusted=false raw bars",
            adjusted="caller's choice; this study requests raw",
            available_here=self.enabled,
            note="Recommended. Satisfies all three hard needs. Halts still "
                 "need a separate source (see data_quality.md).")


class AlpacaProvider(_KeyedProvider):
    """Alpaca market data. NOTE the free tier is IEX-only (~2-3% of
    consolidated volume) - RVOL computed on it is not comparable to any
    threshold calibrated on consolidated tape. Only the SIP feed is usable
    here, which means Algo Trader Plus."""
    name = "alpaca"
    env_key = "ALPACA_API_KEY_ID"
    BASE = "https://data.alpaca.markets/v2"

    def __init__(self):
        super().__init__()
        self.secret = os.environ.get("ALPACA_API_SECRET_KEY", "")
        self.feed = os.environ.get("ALPACA_FEED", "sip")

    @property
    def enabled(self) -> bool:
        return bool(self.key and self.secret)

    def _hdr(self):
        return {"APCA-API-KEY-ID": self.key, "APCA-API-SECRET-KEY": self.secret}

    def minute_bars(self, sym: str, day: dt.date, premarket: bool = True) -> list[Bar]:
        self._require()
        start = dt.datetime.combine(day, dt.time(4, 0), ET)
        end = dt.datetime.combine(day, dt.time(20, 0), ET)
        url = (f"{self.BASE}/stocks/{sym}/bars?timeframe=1Min"
               f"&start={start.isoformat()}&end={end.isoformat()}"
               f"&adjustment=raw&feed={self.feed}&limit=10000")
        out: list[Bar] = []
        while url:
            raw = _curl(url, self._hdr())
            if not raw:
                break
            d = json.loads(raw)
            for r in d.get("bars") or []:
                ts = int(dt.datetime.fromisoformat(r["t"].replace("Z", "+00:00")).timestamp())
                out.append(Bar(ts, r["o"], r["h"], r["l"], r["c"], r.get("v", 0.0)))
            tok = d.get("next_page_token")
            url = (url.split("&page_token")[0] + f"&page_token={tok}") if tok else None
        if not premarket:
            out = [b for b in out if dt.time(9, 30) <= b.et.time() < dt.time(16, 0)]
        return out

    def daily_bars(self, sym: str, start: dt.date, end: dt.date) -> list[Bar]:
        self._require()
        url = (f"{self.BASE}/stocks/{sym}/bars?timeframe=1Day"
               f"&start={start.isoformat()}&end={end.isoformat()}"
               f"&adjustment=raw&feed={self.feed}&limit=10000")
        raw = _curl(url, self._hdr())
        if not raw:
            return []
        d = json.loads(raw)
        return [Bar(int(dt.datetime.fromisoformat(r["t"].replace("Z", "+00:00")).timestamp()),
                    r["o"], r["h"], r["l"], r["c"], r.get("v", 0.0))
                for r in (d.get("bars") or [])]

    def capabilities(self) -> Capability:
        return Capability(
            name=f"Alpaca market data (feed={self.feed})",
            minute_bars=True, minute_history_days=2190,
            premarket_bars=True, premarket_volume=(self.feed == "sip"),
            delisted_retained=None, quotes=True, trades=True,
            halts=False, news=True,
            corporate_actions="adjustment=raw|split|dividend|all",
            adjusted="caller's choice; this study requests raw",
            available_here=self.enabled,
            note="FREE TIER IS IEX-ONLY. Do not compute RVOL on it. "
                 "Delisted retention unverified - test before relying on it.")


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
