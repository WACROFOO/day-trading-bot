"""Deterministic replay source: reads JSONL fixtures of normalized updates.

Fixture line format (one JSON object per line):
  {"type": "reference", "symbol": "ABCD", "prev_close": 5.1,
   "avg_daily_volume": 800000, "float_shares": 12000000,
   "float_quality": "verified", "high_52w": 9.8}
  {"type": "news", "symbol": "ABCD", "published_at": "...", "headline": "..."}
  {"type": "tick", "symbol": "ABCD", "ts": "...", "price": 6.7,
   "size": 1200, "bid": 6.69, "ask": 6.71}
  {"type": "bar", "symbol": "ABCD", "ts": "...", "open": .., "high": ..,
   "low": .., "close": .., "volume": ..}
  {"type": "halt", "symbol": "ABCD", "status": "halted"}

Replay is the ground truth for tests: identical input must produce identical
events (spec Phase 1 exit criterion).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Union

from ..models import Bar, DataStatus, FloatQuality, NewsItem
from ..state import HotState, MarketUpdate, ReferenceData


def _ts(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"fixture timestamp must be timezone-aware: {value}")
    return dt


def load_replay_file(path: Union[str, Path]) -> List[dict]:
    records = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                records.append(json.loads(line))
    return records


class ReplaySource:
    """Feeds fixture records into a HotState/engine in order."""

    def __init__(self, records: List[dict]) -> None:
        self.records = records

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "ReplaySource":
        return cls(load_replay_file(path))

    def apply_static(self, hot: HotState) -> None:
        """Load reference/news/halt records (non-market events) into state."""
        for rec in self.records:
            kind = rec.get("type")
            if kind == "reference":
                hot.load_reference(
                    [
                        ReferenceData(
                            symbol=rec["symbol"],
                            prev_close=rec.get("prev_close"),
                            avg_daily_volume=rec.get("avg_daily_volume"),
                            high_52w=rec.get("high_52w"),
                            float_shares=rec.get("float_shares"),
                            float_quality=FloatQuality(
                                rec.get("float_quality", "unknown")
                            ),
                        )
                    ]
                )
            elif kind == "news":
                hot.attach_news(
                    NewsItem(
                        provider=rec.get("provider", "fixture"),
                        provider_id=rec.get("provider_id", rec["headline"][:32]),
                        published_at=_ts(rec["published_at"]),
                        headline=rec["headline"],
                        symbols=[rec["symbol"]],
                        category=rec.get("category"),
                    )
                )
            elif kind == "halt":
                hot.set_halt(rec["symbol"], rec["status"])

    def market_updates(self) -> Iterator[MarketUpdate]:
        """Yields tick/bar records, in file order."""
        for rec in self.records:
            kind = rec.get("type")
            if kind == "tick":
                yield MarketUpdate(
                    symbol=rec["symbol"],
                    ts=_ts(rec["ts"]),
                    price=rec["price"],
                    size=rec.get("size", 0),
                    bid=rec.get("bid"),
                    ask=rec.get("ask"),
                    data_status=DataStatus.REPLAY,
                )
            elif kind == "bar":
                ts = _ts(rec["ts"])
                yield MarketUpdate(
                    symbol=rec["symbol"],
                    ts=ts,
                    price=rec["close"],
                    size=rec["volume"],
                    bid=rec.get("bid"),
                    ask=rec.get("ask"),
                    bar=Bar(
                        symbol=rec["symbol"],
                        timeframe="1m",
                        ts=ts,
                        open=rec["open"],
                        high=rec["high"],
                        low=rec["low"],
                        close=rec["close"],
                        volume=rec["volume"],
                    ),
                    data_status=DataStatus.REPLAY,
                )
