"""Hot state: per-symbol snapshots, 1-minute bar building and rolling windows.

A single-process, in-memory implementation of the spec's "Hot State" box.
Swappable for Redis later; scanners only see SymbolSnapshot and the helper
queries here.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Deque, Dict, Iterable, Optional

from .formulas import enrich_snapshot, rvol_5m_fallback
from .models import Bar, DataStatus, FloatQuality, NewsItem, Session, SymbolSnapshot
from .sessions import SessionCalendar


@dataclass
class MarketUpdate:
    """Normalized inbound market event (trade tick or completed 1m bar)."""

    symbol: str
    ts: datetime                      # event time, tz-aware UTC
    price: Optional[float] = None     # trade price / bar close
    size: float = 0.0                 # trade size / bar volume
    bid: Optional[float] = None
    ask: Optional[float] = None
    bar: Optional[Bar] = None         # set when the update is a completed bar
    data_status: DataStatus = DataStatus.REPLAY


@dataclass
class ReferenceData:
    """Slow-moving per-symbol reference values, supplied at startup or on
    refresh. Float and shares outstanding are kept distinct on purpose."""

    symbol: str
    prev_close: Optional[float] = None
    avg_daily_volume: Optional[float] = None
    volume_profile: Optional[list] = None      # time-of-day RVOL baseline
    high_52w: Optional[float] = None
    float_shares: Optional[float] = None
    float_quality: FloatQuality = FloatQuality.UNKNOWN


class SymbolState:
    """Rolling per-symbol history the scanners query."""

    def __init__(self, symbol: str, max_minutes: int = 720) -> None:
        self.symbol = symbol
        self.snapshot = SymbolSnapshot(symbol=symbol)
        self.minute_bars: Deque[Bar] = deque(maxlen=max_minutes)
        self._building: Optional[Bar] = None
        self._trading_date = None

    # -- price history queries ------------------------------------------------

    def price_minutes_ago(self, now: datetime, minutes: int) -> Optional[float]:
        """Close of the newest completed bar at least `minutes` old; falls back
        to the oldest known bar so early-session moves are still measurable."""
        cutoff = now - timedelta(minutes=minutes)
        candidate = None
        for bar in self.minute_bars:
            if bar.ts <= cutoff:
                candidate = bar.close
            else:
                break
        return candidate

    def volume_last_minutes(self, now: datetime, minutes: int) -> float:
        cutoff = now - timedelta(minutes=minutes)
        total = sum(b.volume for b in self.minute_bars if b.ts >= cutoff)
        if self._building is not None and self._building.ts >= cutoff:
            total += self._building.volume
        return total

    def completed_5m_volumes(self, count: int = 20) -> list:
        """Volumes of prior completed 5-minute windows (from 1m bars)."""
        bars = list(self.minute_bars)
        out = []
        for i in range(len(bars) - 5, -1, -5):
            chunk = bars[i : i + 5]
            if len(chunk) == 5:
                out.append(sum(b.volume for b in chunk))
            if len(out) >= count:
                break
        out.reverse()
        return out


class HotState:
    """All tracked symbols plus shared session calendar."""

    def __init__(self, calendar: Optional[SessionCalendar] = None) -> None:
        self.calendar = calendar or SessionCalendar()
        self.symbols: Dict[str, SymbolState] = {}

    def get(self, symbol: str) -> SymbolState:
        if symbol not in self.symbols:
            self.symbols[symbol] = SymbolState(symbol)
        return self.symbols[symbol]

    def load_reference(self, refs: Iterable[ReferenceData]) -> None:
        for ref in refs:
            snap = self.get(ref.symbol).snapshot
            snap.prev_close = ref.prev_close
            snap.avg_daily_volume = ref.avg_daily_volume
            if ref.volume_profile:
                snap.volume_profile = list(ref.volume_profile)
            snap.high_52w = ref.high_52w
            snap.float_shares = ref.float_shares
            snap.float_quality = ref.float_quality

    def attach_news(self, item: NewsItem) -> None:
        for symbol in item.symbols:
            snap = self.get(symbol).snapshot
            if snap.latest_news_ts is None or item.published_at > snap.latest_news_ts:
                snap.latest_news_ts = item.published_at
                snap.news_headline = item.headline

    def set_halt(self, symbol: str, status: str) -> None:
        self.get(symbol).snapshot.halt_status = status

    # -- ingestion ------------------------------------------------------------

    def apply(self, update: MarketUpdate) -> SymbolSnapshot:
        """Apply one normalized update; returns the enriched snapshot.

        Daily fields reset when the ET trading date changes so a long-running
        process does not bleed one session into the next.
        """
        state = self.get(update.symbol)
        snap = state.snapshot

        trading_date = self.calendar.trading_date(update.ts)
        if state._trading_date != trading_date:
            state._trading_date = trading_date
            snap.session_high = None
            snap.session_low = None
            snap.volume_today = 0.0
            snap.regular_open = None
            state.minute_bars.clear()
            state._building = None

        session = self.calendar.session_at(update.ts)
        snap.session = session
        snap.event_ts = update.ts
        snap.ingest_ts = datetime.now(tz=update.ts.tzinfo)
        snap.data_status = update.data_status
        if update.bid is not None:
            snap.bid = update.bid
        if update.ask is not None:
            snap.ask = update.ask

        if update.bar is not None:
            self._apply_bar(state, update.bar, session)
        elif update.price is not None:
            self._apply_tick(state, update, session)

        return enrich_snapshot(snap)

    def _apply_common(self, snap: SymbolSnapshot, price: float, volume: float, session: Session, high: float, low: float) -> None:
        snap.last = price
        if session in (Session.PREMARKET, Session.REGULAR, Session.AFTER_HOURS):
            snap.volume_today += volume
            snap.session_high = high if snap.session_high is None else max(snap.session_high, high)
            snap.session_low = low if snap.session_low is None else min(snap.session_low, low)
        if session == Session.REGULAR and snap.regular_open is None:
            snap.regular_open = price

    def _apply_bar(self, state: SymbolState, bar: Bar, session: Session) -> None:
        bar.session = session
        if session == Session.REGULAR and state.snapshot.regular_open is None:
            state.snapshot.regular_open = bar.open
        state.minute_bars.append(bar)
        self._apply_common(state.snapshot, bar.close, bar.volume, session, bar.high, bar.low)
        self._refresh_5m(state)

    def _apply_tick(self, state: SymbolState, update: MarketUpdate, session: Session) -> None:
        price, ts = update.price, update.ts
        minute = ts.replace(second=0, microsecond=0)
        b = state._building
        if b is None or b.ts != minute:
            if b is not None:
                state.minute_bars.append(b)
            state._building = Bar(
                symbol=state.symbol, timeframe="1m", ts=minute,
                open=price, high=price, low=price, close=price,
                volume=update.size, session=session,
            )
        else:
            b.high = max(b.high, price)
            b.low = min(b.low, price)
            b.close = price
            b.volume += update.size
        self._apply_common(state.snapshot, price, update.size, session, price, price)
        self._refresh_5m(state)

    def _refresh_5m(self, state: SymbolState) -> None:
        snap = state.snapshot
        now = snap.event_ts
        if now is None:
            return
        snap.volume_5m = state.volume_last_minutes(now, 5)
        snap.rvol_5m = rvol_5m_fallback(snap.volume_5m, state.completed_5m_volumes())
