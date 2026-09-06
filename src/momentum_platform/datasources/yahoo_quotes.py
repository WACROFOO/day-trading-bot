"""Delayed premarket quotes from Yahoo Finance's public quote endpoint.

Why this exists. The free Alpaca feed is IEX, a single venue that carries
almost no premarket volume in microcaps: at 06:00 ET a name can be up 70% on
other venues and have printed zero trades on IEX. Yahoo's quote endpoint
returns a consolidated, delayed premarket price and change for hundreds of
symbols per request. It is what the operator's earlier yfinance tooling used,
and it is the "15-minute delay I understand".

What it is not. It is unofficial — no key, no contract, no SLA — and Yahoo has
changed its cookie/crumb handshake before. Every consumer of this module must
treat an outage as "no premarket quote", never as "no premarket move". It is
also display and discovery data only: the pillars and the scanners stay on the
entitled feed.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, Iterable, List, Optional

from .tls import ssl_context

COOKIE_URL = "https://fc.yahoo.com"
CRUMB_URL = "https://query1.finance.yahoo.com/v1/test/getcrumb"
QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
BATCH = 400          # symbols per request; keeps the URL well under limits


class YahooError(RuntimeError):
    """Raised with a message written for a human."""


def parse_quotes(payload: dict) -> Dict[str, dict]:
    """Normalise a v7 quote response. Pure, so it is testable offline."""
    out: Dict[str, dict] = {}
    for q in ((payload.get("quoteResponse") or {}).get("result") or []):
        sym = q.get("symbol")
        if not sym:
            continue
        state = q.get("marketState") or ""
        pre_p, pre_c = q.get("preMarketPrice"), q.get("preMarketChangePercent")
        reg_p, reg_c = q.get("regularMarketPrice"), q.get("regularMarketChangePercent")
        post_p, post_c = q.get("postMarketPrice"), q.get("postMarketChangePercent")
        # The "current" number is the one for the session Yahoo says we are in.
        if state.startswith("PRE") and pre_p is not None:
            cur_p, cur_c, cur_t, session = pre_p, pre_c, q.get("preMarketTime"), "premarket"
        elif state.startswith("POST") and post_p is not None:
            cur_p, cur_c, cur_t, session = post_p, post_c, q.get("postMarketTime"), "afterhours"
        else:
            cur_p, cur_c, cur_t, session = reg_p, reg_c, q.get("regularMarketTime"), "regular"
        out[sym] = {
            "symbol": sym, "state": state, "session": session,
            "price": cur_p, "change_pct": cur_c, "as_of": cur_t,
            "pre_price": pre_p, "pre_change_pct": pre_c,
            "regular_price": reg_p, "regular_change_pct": reg_c,
            "regular_volume": q.get("regularMarketVolume"),
            "avg_volume_10d": q.get("averageDailyVolume10Day"),
            "prev_close": q.get("regularMarketPreviousClose"),
            "exchange": q.get("fullExchangeName") or q.get("exchange"),
            "name": q.get("shortName") or q.get("longName"),
            "float_shares": q.get("floatShares"),
            "shares_outstanding": q.get("sharesOutstanding"),
        }
    return out


class YahooQuotes:
    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout
        self._cookie: Optional[str] = None
        self._crumb: Optional[str] = None
        self._last_call = 0.0

    # -- handshake ------------------------------------------------------------

    def _open(self, url: str, headers: Optional[dict] = None):
        req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
        return urllib.request.urlopen(req, timeout=self.timeout, context=ssl_context())

    def _bootstrap(self) -> None:
        """One cookie, one crumb. Yahoo rejects quote calls without both."""
        try:
            with self._open(COOKIE_URL) as resp:
                raw = resp.headers.get_all("Set-Cookie") or []
        except urllib.error.HTTPError as exc:
            # fc.yahoo.com answers 404 but still sets the cookie
            raw = exc.headers.get_all("Set-Cookie") or []
        except urllib.error.URLError as exc:
            raise YahooError(f"could not reach Yahoo for a session cookie ({exc.reason})") from None
        cookie = "; ".join(c.split(";", 1)[0] for c in raw if c)
        if not cookie:
            raise YahooError("Yahoo did not hand out a session cookie — the handshake may have changed")
        try:
            with self._open(CRUMB_URL, {"Cookie": cookie}) as resp:
                crumb = resp.read().decode().strip()
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            raise YahooError(f"Yahoo refused the crumb request ({exc})") from None
        if not crumb or "<" in crumb:
            raise YahooError("Yahoo returned an invalid crumb — the handshake may have changed")
        self._cookie, self._crumb = cookie, crumb

    # -- quotes ---------------------------------------------------------------

    def quotes(self, symbols: Iterable[str]) -> Dict[str, dict]:
        syms = [s.strip().upper() for s in symbols if s and s.strip()]
        if not syms:
            return {}
        if not self._crumb:
            self._bootstrap()
        out: Dict[str, dict] = {}
        for i in range(0, len(syms), BATCH):
            chunk = syms[i:i + BATCH]
            gap = time.monotonic() - self._last_call
            if gap < 0.5:
                time.sleep(0.5 - gap)
            self._last_call = time.monotonic()
            url = QUOTE_URL + "?" + urllib.parse.urlencode({
                "symbols": ",".join(chunk), "crumb": self._crumb,
                "fields": ",".join([
                    "marketState", "preMarketPrice", "preMarketChangePercent", "preMarketTime",
                    "regularMarketPrice", "regularMarketChangePercent", "regularMarketTime",
                    "regularMarketVolume", "regularMarketPreviousClose", "postMarketPrice",
                    "postMarketChangePercent", "postMarketTime", "averageDailyVolume10Day",
                    "fullExchangeName", "shortName", "floatShares", "sharesOutstanding"]),
            })
            try:
                with self._open(url, {"Cookie": self._cookie or ""}) as resp:
                    payload = json.loads(resp.read().decode())
            except urllib.error.HTTPError as exc:
                if exc.code in (401, 403, 429):
                    self._crumb = None            # force a fresh handshake next time
                    raise YahooError(f"Yahoo refused the quote request (HTTP {exc.code}); "
                                     "the crumb expired or the rate limit tripped") from None
                raise YahooError(f"Yahoo returned HTTP {exc.code}") from None
            except urllib.error.URLError as exc:
                raise YahooError(f"could not reach Yahoo ({exc.reason})") from None
            out.update(parse_quotes(payload))
        return out
