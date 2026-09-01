"""Scanner interface (spec section 18).

Two shapes:
- event scanners implement on_snapshot() and emit rising-edge ScannerEvents;
- list scanners implement rank() and return ordered RankedRows.

Every event carries raw values, pass/fail reasons and a definition version so
the UI never has to reverse-engineer why a symbol appeared. All thresholds are
constructor parameters classified `independent_approximation` unless the
docstring says Confirmed.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from ..models import RankedRow, Reason, ScannerEvent, SymbolSnapshot, flame_color
from ..state import HotState, SymbolState


class Scanner:
    scanner_id: str = "base"
    definition_version: str = "base@0.0.0"
    classification: str = "independent_approximation"

    def on_snapshot(
        self,
        current: SymbolSnapshot,
        previous: Optional[SymbolSnapshot],
        state: SymbolState,
        hot: HotState,
    ) -> List[ScannerEvent]:
        return []

    def rank(self, hot: HotState, now: datetime) -> List[RankedRow]:
        return []

    # -- helpers --------------------------------------------------------------

    def _news_block(self, snap: SymbolSnapshot, now: datetime) -> Optional[dict]:
        if snap.latest_news_ts is None:
            return None
        age = (now - snap.latest_news_ts).total_seconds() / 60.0
        return {
            "age_minutes": round(age, 1),
            "flame": flame_color(age),
            "headline": snap.news_headline,
        }

    def _base_values(self, snap: SymbolSnapshot) -> dict:
        return {
            "last": snap.last,
            "change_pct": _round(snap.change_from_close_pct),
            "rvol_daily": _round(snap.rvol_daily),
            "rvol_5m": _round(snap.rvol_5m),
            "volume_today": snap.volume_today,
            "float_m": None if snap.float_shares is None else round(snap.float_shares / 1e6, 2),
            "float_quality": snap.float_quality.value,
            "spread": _round(snap.spread_abs, 4),
        }

    def _event(
        self,
        snap: SymbolSnapshot,
        now: datetime,
        event_type: str,
        severity: str,
        reasons: List[Reason],
        branch: Optional[str] = None,
        extra_values: Optional[dict] = None,
    ) -> ScannerEvent:
        values = self._base_values(snap)
        if extra_values:
            values.update(extra_values)
        return ScannerEvent(
            symbol=snap.symbol,
            scanner=self.scanner_id,
            branch=branch,
            event_type=event_type,
            severity=severity,
            session=snap.session,
            source_ts=snap.event_ts or now,
            scan_ts=now,
            definition_version=self.definition_version,
            values=values,
            reasons=reasons,
            news=self._news_block(snap, now),
            data_quality=snap.data_status.value,
        )


class EdgeTracker:
    """Rising-edge helper: remembers the previous qualifying state per key and
    reports True only on the transition from not-qualifying to qualifying.
    Re-arms after `rearm_after_fails` consecutive non-qualifying evaluations."""

    def __init__(self, rearm_after_fails: int = 1) -> None:
        self.rearm_after_fails = max(1, rearm_after_fails)
        self._qualified: Dict[str, bool] = {}
        self._fail_streak: Dict[str, int] = {}

    def rising_edge(self, key: str, qualifies_now: bool) -> bool:
        was = self._qualified.get(key, False)
        if qualifies_now:
            self._fail_streak[key] = 0
            self._qualified[key] = True
            return not was
        streak = self._fail_streak.get(key, 0) + 1
        self._fail_streak[key] = streak
        if streak >= self.rearm_after_fails:
            self._qualified[key] = False
        return False


def _round(v: Optional[float], nd: int = 2) -> Optional[float]:
    return None if v is None else round(v, nd)
