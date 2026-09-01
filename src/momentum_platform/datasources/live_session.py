"""Build a dashboard session from REAL market data (delayed, free tier).

Honest limits, stated wherever the data surfaces:
- yfinance quotes and 1-minute bars are typically ~15 minutes delayed and are
  not an exchange-entitled feed;
- intraday history is limited (roughly the last 7 days at 1-minute
  granularity) and premarket coverage is partial;
- `floatShares` is often missing, so shares outstanding is used as an
  explicitly labelled proxy and the supply pillar fails rather than silently
  passing on the wrong number;
- news carries the provider's publication time; first-observed is set to the
  moment we fetched it, so flame latency stays measurable.

This is the same normalized record format the replay fixtures use, so the
scanner engine, the dashboard and every test behave identically. Swap this
module for a licensed provider adapter when one is chosen — nothing
downstream changes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, List

UTC = timezone.utc


def _iso(ts) -> str:
    return ts.astimezone(UTC).isoformat().replace("+00:00", "Z")


def fetch_records(symbols: Iterable[str], days: int = 1, daily_lookback: str = "1y") -> List[dict]:
    """Return normalized reference/news/bar records for the given symbols."""
    import yfinance as yf  # deferred so the core package stays stdlib-only

    records: List[dict] = []
    observed = _iso(datetime.now(UTC))

    for symbol in symbols:
        ticker = yf.Ticker(symbol)
        try:
            info = ticker.info or {}
        except Exception:
            info = {}

        float_shares = info.get("floatShares")
        quality = "verified" if float_shares else "unknown"
        if not float_shares and info.get("sharesOutstanding"):
            float_shares = info["sharesOutstanding"]
            quality = "shares_outstanding_proxy"

        daily_bars = []
        try:
            hist = ticker.history(period=daily_lookback, interval="1d", auto_adjust=False)
            for idx, row in hist.iterrows():
                daily_bars.append({
                    "d": idx.strftime("%Y-%m-%d"),
                    "o": round(float(row["Open"]), 4), "h": round(float(row["High"]), 4),
                    "l": round(float(row["Low"]), 4), "c": round(float(row["Close"]), 4),
                    "v": int(row["Volume"] or 0),
                })
        except Exception:
            pass

        prev_close = info.get("previousClose")
        if prev_close is None and len(daily_bars) >= 2:
            prev_close = daily_bars[-2]["c"]

        records.append({
            "type": "reference", "symbol": symbol,
            "prev_close": prev_close,
            "avg_daily_volume": info.get("averageVolume"),
            "high_52w": info.get("fiftyTwoWeekHigh"),
            "float_shares": float_shares,
            "float_quality": quality,
            "daily_bars": daily_bars,
        })

        # Real catalyst headlines, with the provider's own publication time.
        try:
            for item in (ticker.news or [])[:5]:
                content = item.get("content") or item
                published = content.get("pubDate") or item.get("providerPublishTime")
                if isinstance(published, (int, float)):
                    published_iso = _iso(datetime.fromtimestamp(published, UTC))
                elif isinstance(published, str):
                    published_iso = published.replace("+00:00", "Z")
                else:
                    continue
                headline = content.get("title") or item.get("title")
                if not headline:
                    continue
                records.append({
                    "type": "news", "symbol": symbol,
                    "provider_id": str(item.get("id") or item.get("uuid") or headline[:40]),
                    "published_at": published_iso,
                    "first_observed_at": observed,
                    "headline": headline,
                    "category": (content.get("contentType") or "unclassified").lower(),
                })
        except Exception:
            pass

        try:
            intraday = ticker.history(period=f"{days}d", interval="1m", prepost=True)
            for idx, row in intraday.iterrows():
                ts = idx.to_pydatetime()
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
                close = float(row["Close"])
                if close <= 0:
                    continue
                records.append({
                    "type": "bar", "symbol": symbol, "ts": _iso(ts),
                    "open": round(float(row["Open"]), 4), "high": round(float(row["High"]), 4),
                    "low": round(float(row["Low"]), 4), "close": round(close, 4),
                    "volume": int(row["Volume"] or 0),
                })
        except Exception:
            pass

    return records


def build_live_session(symbols: Iterable[str], max_rows: int = 10) -> dict:
    from ..dashboard.session_builder import build_session_from_records

    symbols = [s.upper() for s in symbols]
    records = fetch_records(symbols)
    if not any(r["type"] == "bar" for r in records):
        raise RuntimeError(
            "no intraday bars returned — the provider may be unreachable, the "
            "symbols invalid, or the market closed beyond the 1-minute history window"
        )
    session = build_session_from_records(
        records, session_id="live-" + "-".join(symbols[:3]),
        source_name="yfinance (delayed ~15m)", max_rows=max_rows, data_status="delayed",
    )
    session["disclaimer"] = (
        "Delayed market data (~15 minutes), not an entitled feed. Scanner events are "
        "research candidates, never entry signals or orders."
    )
    return session
