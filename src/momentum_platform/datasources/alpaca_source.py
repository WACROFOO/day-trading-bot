"""Alpaca adapter — free tier, standard library only.

Nothing here needs `pip install`: it speaks HTTP with `urllib` and returns the
same normalized records the replay fixtures use, so every scanner, chart and
card behaves identically on real data.

WHAT THE FREE TIER GIVES YOU
    - real-time trades and 1-minute bars from the IEX feed (not delayed);
    - historical daily and minute bars;
    - news headlines with publication timestamps;
    - the tradable US equity universe (NASDAQ *and* NYSE);
    - a paper trading account.

THE ONE CAVEAT THAT MATTERS FOR THIS STRATEGY
    IEX is a single venue carrying a small share of consolidated volume, so
    IEX volume is NOT comparable to the consolidated volume the course's
    "5x relative volume" pillar assumes.

    This adapter handles that by comparing like with like: today's IEX volume
    is divided by the average of prior days' *IEX* volume. Both sides come
    from the same venue, so the ratio stays meaningful even though neither
    number is the consolidated one. Absolute volume is still understated and
    is labelled `iex` in the session so nothing pretends otherwise.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional
from zoneinfo import ZoneInfo

UTC = timezone.utc
ET = ZoneInfo("America/New_York")

DATA_BASE = "https://data.alpaca.markets"
PAPER_BASE = "https://paper-api.alpaca.markets"


class AlpacaError(RuntimeError):
    """Raised with a message written for a human, not a stack trace."""


class AlpacaClient:
    def __init__(self, key_id: str, secret_key: str, feed: str = "iex",
                 data_base: str = DATA_BASE, trading_base: str = PAPER_BASE,
                 timeout: float = 30.0) -> None:
        if not key_id or not secret_key:
            raise AlpacaError(
                "Missing credentials. Put ALPACA_KEY_ID and ALPACA_SECRET_KEY in a "
                ".env file next to this repository (see .env.example)."
            )
        self.key_id = key_id
        self.secret_key = secret_key
        self.feed = feed
        self.data_base = data_base.rstrip("/")
        self.trading_base = trading_base.rstrip("/")
        self.timeout = timeout

    # -- transport ----------------------------------------------------------

    def _get(self, base: str, path: str, params: Optional[dict] = None) -> dict:
        url = base + path
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            url += "?" + urllib.parse.urlencode(clean)
        req = urllib.request.Request(url, headers={
            "APCA-API-KEY-ID": self.key_id,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")[:300]
            if exc.code in (401, 403):
                raise AlpacaError(
                    "Alpaca rejected the credentials (HTTP %d). Check that the key and "
                    "secret are copied whole with no spaces, and that they are PAPER keys "
                    "if you are using the paper endpoint.\nAlpaca said: %s" % (exc.code, body)
                ) from None
            if exc.code == 429:
                raise AlpacaError(
                    "Rate limited by Alpaca (HTTP 429). The free tier allows roughly 200 "
                    "requests a minute — scan fewer symbols, or wait a minute and retry."
                ) from None
            if exc.code == 422:
                raise AlpacaError(
                    "Alpaca could not understand the request (HTTP 422). This usually means "
                    "a bad symbol, an unsupported timeframe, or a start date outside your "
                    "plan's history.\nAlpaca said: %s" % body
                ) from None
            raise AlpacaError("Alpaca returned HTTP %d for %s\n%s" % (exc.code, path, body)) from None
        except urllib.error.URLError as exc:
            reason = str(exc.reason)
            if "CERTIFICATE_VERIFY" in reason or "SSLCertVerification" in reason:
                # Not a network problem, and not a bad key. A python.org build on
                # macOS ships its own CA store and does not read the system
                # keychain, so every HTTPS call fails until that store is
                # populated. Saying "check your connection" here sends people to
                # regenerate perfectly good credentials.
                raise AlpacaError(
                    "Python on this machine cannot verify HTTPS certificates, so the "
                    "request never left your computer. Your keys and your network are "
                    "fine.\n\n"
                    "On macOS with Python from python.org, fix it once by opening the\n"
                    "Applications folder, then your Python 3.x folder, and double-clicking\n"
                    "the file named: Install Certificates.command\n\n"
                    "From a terminal instead: python3 -m pip install --upgrade certifi\n\n"
                    "Detail: %s" % reason
                ) from None
            raise AlpacaError(
                "Could not reach Alpaca (%s). Check your internet connection, and any "
                "company proxy or VPN that might block api/data.alpaca.markets." % reason
            ) from None

    # -- endpoints ----------------------------------------------------------

    def clock(self) -> dict:
        return self._get(self.trading_base, "/v2/clock")

    def account(self) -> dict:
        return self._get(self.trading_base, "/v2/account")

    def assets(self, status: str = "active") -> list:
        result = self._get(self.trading_base, "/v2/assets",
                           {"status": status, "asset_class": "us_equity"})
        return result if isinstance(result, list) else []

    def snapshots(self, symbols: Iterable[str]) -> dict:
        symbols = list(symbols)
        out: dict = {}
        for chunk in _chunks(symbols, 100):
            payload = self._get(self.data_base, "/v2/stocks/snapshots",
                                {"symbols": ",".join(chunk), "feed": self.feed})
            # The endpoint has returned both {"snapshots": {...}} and a bare map.
            out.update(payload.get("snapshots", payload) or {})
        return out

    def bars(self, symbols: Iterable[str], timeframe: str, start: str,
             end: Optional[str] = None, limit: int = 10000) -> dict:
        symbols = list(symbols)
        out: dict = {}
        for chunk in _chunks(symbols, 100):
            token = None
            while True:
                payload = self._get(self.data_base, "/v2/stocks/bars", {
                    "symbols": ",".join(chunk), "timeframe": timeframe,
                    "start": start, "end": end, "limit": limit,
                    "feed": self.feed, "adjustment": "split",
                    "page_token": token,
                })
                for symbol, rows in (payload.get("bars") or {}).items():
                    out.setdefault(symbol, []).extend(rows or [])
                token = payload.get("next_page_token")
                if not token:
                    break
        return out

    def news(self, symbols: Iterable[str], limit: int = 50,
             start: Optional[str] = None) -> list:
        payload = self._get(self.data_base, "/v1beta1/news", {
            "symbols": ",".join(list(symbols)), "limit": min(limit, 50),
            "start": start, "sort": "desc",
        })
        return payload.get("news", []) or []


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def client_from_env(feed: Optional[str] = None) -> AlpacaClient:
    """Read credentials from the environment or a local .env file."""
    load_dotenv()
    return AlpacaClient(
        key_id=os.environ.get("ALPACA_KEY_ID", "").strip(),
        secret_key=os.environ.get("ALPACA_SECRET_KEY", "").strip(),
        feed=(feed or os.environ.get("ALPACA_FEED", "iex")).strip(),
        trading_base=os.environ.get("ALPACA_TRADING_BASE", PAPER_BASE).strip(),
    )


def load_dotenv(path: str = ".env") -> None:
    """Tiny .env reader so there is nothing to install. Existing environment
    variables always win, and quotes around values are tolerated."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


# -- normalization ----------------------------------------------------------

def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def session_window(day: Optional[datetime] = None) -> tuple:
    """Premarket open (04:00 ET) through now, as RFC3339 strings."""
    now = datetime.now(UTC)
    anchor = (day or now).astimezone(ET)
    start_et = anchor.replace(hour=4, minute=0, second=0, microsecond=0)
    end_et = anchor.replace(hour=20, minute=0, second=0, microsecond=0)
    end = min(end_et.astimezone(UTC), now) if day is None else end_et.astimezone(UTC)
    return _iso(start_et.astimezone(UTC)), _iso(end)


def fetch_records(client: AlpacaClient, symbols: Iterable[str],
                  day: Optional[datetime] = None,
                  daily_lookback_days: int = 400,
                  rvol_window: int = 20) -> List[dict]:
    """Reference + news + 1-minute bar records for the given symbols."""
    symbols = [s.upper().strip() for s in symbols if s.strip()]
    if not symbols:
        raise AlpacaError("No symbols given.")
    records: List[dict] = []
    observed = _iso(datetime.now(UTC))

    daily_start = _iso(datetime.now(UTC) - timedelta(days=daily_lookback_days))
    daily = client.bars(symbols, "1Day", daily_start)
    snaps = client.snapshots(symbols)

    for symbol in symbols:
        rows = daily.get(symbol, [])
        daily_bars = [{
            "d": r["t"][:10], "o": r.get("o"), "h": r.get("h"),
            "l": r.get("l"), "c": r.get("c"), "v": int(r.get("v") or 0),
        } for r in rows]

        snap = snaps.get(symbol, {}) or {}
        prev = snap.get("prevDailyBar") or {}
        prev_close = prev.get("c")
        if prev_close is None and len(daily_bars) >= 2:
            prev_close = daily_bars[-2]["c"]

        # Same-venue comparison: today's IEX volume against prior IEX days.
        recent = [b["v"] for b in daily_bars[-(rvol_window + 1):-1] if b["v"] > 0]
        avg_volume = sum(recent) / len(recent) if recent else None
        high_52w = max((b["h"] for b in daily_bars[-252:] if b["h"]), default=None)

        records.append({
            "type": "reference", "symbol": symbol,
            "prev_close": prev_close,
            "avg_daily_volume": avg_volume,
            "high_52w": high_52w,
            # Alpaca does not publish float. Never guess it: an unknown float
            # fails the supply pillar with a visible reason.
            "float_shares": None, "float_quality": "unknown",
            "daily_bars": daily_bars,
        })

    start, end = session_window(day)
    minute = client.bars(symbols, "1Min", start, end)
    for symbol in symbols:
        for r in minute.get(symbol, []):
            close = r.get("c")
            if not close or close <= 0:
                continue
            records.append({
                "type": "bar", "symbol": symbol, "ts": r["t"],
                "open": r.get("o"), "high": r.get("h"), "low": r.get("l"),
                "close": close, "volume": int(r.get("v") or 0),
            })

    try:
        for item in client.news(symbols, limit=50, start=_iso(datetime.now(UTC) - timedelta(days=2))):
            published = item.get("created_at") or item.get("updated_at")
            headline = item.get("headline")
            if not published or not headline:
                continue
            for symbol in item.get("symbols", []):
                if symbol in symbols:
                    records.append({
                        "type": "news", "symbol": symbol,
                        "provider_id": str(item.get("id")),
                        "published_at": published,
                        "first_observed_at": observed,
                        "headline": headline,
                        "category": (item.get("source") or "news").lower(),
                    })
    except AlpacaError:
        pass          # a missing news entitlement must not break the session

    return records


def build_alpaca_session(symbols: Iterable[str], feed: Optional[str] = None,
                         day: Optional[datetime] = None, max_rows: int = 10) -> dict:
    from ..dashboard.session_builder import build_session_from_records

    client = client_from_env(feed)
    symbols = [s.upper().strip() for s in symbols if s.strip()]
    records = fetch_records(client, symbols, day=day)
    if not any(r["type"] == "bar" for r in records):
        raise AlpacaError(
            "Alpaca returned no 1-minute bars for %s.\n"
            "Most likely reasons, in order:\n"
            "  1. the market has not opened yet today (premarket starts 04:00 ET);\n"
            "  2. these symbols simply have not traded on the IEX feed yet;\n"
            "  3. the symbols are wrong or not tradable.\n"
            "Run `python scripts/verify_alpaca.py` for a step-by-step check."
            % ", ".join(symbols)
        )
    session = build_session_from_records(
        records, session_id="alpaca-" + "-".join(symbols[:3]),
        source_name="alpaca %s feed" % client.feed,
        max_rows=max_rows, data_status="live" if client.feed == "sip" else "iex",
    )
    session["disclaimer"] = (
        "Alpaca %s feed. IEX is one venue, so absolute volume is a fraction of "
        "consolidated volume; relative volume compares IEX to IEX and stays meaningful. "
        "Scanner events are research candidates, never entry signals or orders."
        % client.feed
    )
    return session


def momentum_universe(client: AlpacaClient, max_symbols: int = 0) -> List[str]:
    """Tradable US common stocks — NASDAQ and NYSE, not just NASDAQ."""
    out = []
    for asset in client.assets():
        if (asset.get("tradable") and asset.get("status") == "active"
                and asset.get("class") == "us_equity"
                and asset.get("exchange") in ("NASDAQ", "NYSE", "ARCA", "AMEX")):
            out.append(asset["symbol"])
    out.sort()
    return out[:max_symbols] if max_symbols else out
