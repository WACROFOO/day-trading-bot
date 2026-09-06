"""Free delayed polling source built on yfinance — for development and
watchlist tracking only.

Honest limitations, stated everywhere the data surfaces:
- quotes/bars are delayed (typically ~15 minutes) and there is no premarket
  tick stream on the free tier;
- a polling loop cannot reach the sub-second cadence real momentum alerts
  need. Events from this source carry data_status=DELAYED so the UI and the
  notification text never present them as live.

For real-time operation plug a licensed provider (Alpaca/Polygon/Databento)
into the same MarketUpdate interface.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Iterable, Iterator, List, Optional

from ..models import DataStatus, FloatQuality
from ..state import MarketUpdate, ReferenceData


def fetch_reference(symbols: Iterable[str]) -> List[ReferenceData]:
    """Prev close, average volume, 52-week high and shares outstanding
    (explicitly a float PROXY unless floatShares is present)."""
    import yfinance as yf  # deferred: keeps the core package stdlib-only

    refs: List[ReferenceData] = []
    for symbol in symbols:
        try:
            info = yf.Ticker(symbol).info or {}
        except Exception:
            info = {}
        float_shares = info.get("floatShares")
        quality = FloatQuality.VERIFIED if float_shares else FloatQuality.UNKNOWN
        if not float_shares and info.get("sharesOutstanding"):
            float_shares = info["sharesOutstanding"]
            quality = FloatQuality.SHARES_OUTSTANDING
        refs.append(
            ReferenceData(
                symbol=symbol,
                prev_close=info.get("previousClose"),
                avg_daily_volume=info.get("averageVolume"),
                high_52w=info.get("fiftyTwoWeekHigh"),
                float_shares=float_shares,
                float_quality=quality,
            )
        )
    return refs


def poll_quotes(
    symbols: Iterable[str],
    interval_seconds: float = 30.0,
    iterations: Optional[int] = None,
) -> Iterator[MarketUpdate]:
    """Yields one MarketUpdate per symbol per polling round. Volume deltas are
    derived from cumulative day volume between polls."""
    import yfinance as yf

    last_volume: dict = {}
    rounds = 0
    symbols = list(symbols)
    while iterations is None or rounds < iterations:
        for symbol in symbols:
            try:
                fi = yf.Ticker(symbol).fast_info
                price = fi.get("lastPrice") or fi.get("last_price")
                day_volume = fi.get("lastVolume") or fi.get("last_volume") or 0
            except Exception:
                continue
            if not price:
                continue
            prev = last_volume.get(symbol, 0)
            delta = max(0, (day_volume or 0) - prev)
            last_volume[symbol] = day_volume or prev
            yield MarketUpdate(
                symbol=symbol,
                ts=datetime.now(timezone.utc),
                price=float(price),
                size=float(delta),
                data_status=DataStatus.DELAYED,
            )
        rounds += 1
        if iterations is None or rounds < iterations:
            time.sleep(interval_seconds)
