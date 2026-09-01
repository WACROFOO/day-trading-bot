"""Evaluation loop (spec section 18): normalized update -> hot state ->
scanners -> persist -> notify. Notification delivery never blocks ingestion
(the router already swallows channel failures)."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from .models import RankedRow, ScannerEvent
from .notify import NotificationRouter
from .scanners.base import Scanner
from .state import HotState, MarketUpdate
from .store import EventStore


class ScannerEngine:
    def __init__(
        self,
        hot: Optional[HotState] = None,
        scanners: Optional[List[Scanner]] = None,
        router: Optional[NotificationRouter] = None,
        store: Optional[EventStore] = None,
    ) -> None:
        self.hot = hot or HotState()
        self.scanners = scanners or []
        self.router = router or NotificationRouter()
        self.store = store
        self.events_emitted: int = 0
        self._prev_snapshots: Dict[str, object] = {}

    def process(self, update: MarketUpdate) -> List[ScannerEvent]:
        """Apply one market update and run every event scanner on the result."""
        previous = self._prev_snapshots.get(update.symbol)
        snapshot = self.hot.apply(update)
        emitted: List[ScannerEvent] = []
        state = self.hot.get(update.symbol)
        for scanner in self.scanners:
            for event in scanner.on_snapshot(snapshot, previous, state, self.hot):
                emitted.append(event)
                self.events_emitted += 1
                if self.store is not None:
                    self.store.save_event(event)
                self.router.handle(event)
        self._prev_snapshots[update.symbol] = snapshot.copy_shallow()
        return emitted

    def rank_all(self, now: datetime) -> Dict[str, List[RankedRow]]:
        """Run every list scanner once; returns scanner_id -> rows."""
        out: Dict[str, List[RankedRow]] = {}
        for scanner in self.scanners:
            rows = scanner.rank(self.hot, now)
            if rows:
                out[scanner.scanner_id] = rows
        return out
