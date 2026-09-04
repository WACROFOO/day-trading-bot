"""Event alert scanners: HOD Momentum, Running Up/Down, squeezes (5-in-5,
10-in-10) and 52-week breakout.

The branch NAMES follow the captured platform inventory (Confirmed platform);
every numeric threshold here is an independent approximation — Warrior's
production values were never exposed. All thresholds are constructor inputs.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from ..formulas import effective_rvol
from ..models import Reason, ScannerEvent, SymbolSnapshot
from ..state import HotState, SymbolState
from .base import EdgeTracker, Scanner, _round

MIN_TICK_BUFFER = 0.0001

# Liquidity in thin tape. The 25,000-shares-in-five-minutes floor is stated
# against a busy regular session; at 04:40 ET a name up 26% on 3,000 shares
# never reaches it, so HOD Momentum and Running Up stayed silent all
# premarket on exactly the names the desk was built to surface. A name that
# already carries three of the five pillars is admitted on those instead.
# Approximation: the course never states a premarket volume rule.
MIN_PILLARS_FOR_LIQUIDITY = 3


def _liquidity(current: SymbolSnapshot, min_volume_5m: float, min_pillars: int):
    """(passed, volume_ok, pillars_passed) — the share floor OR the pillars."""
    from .five_pillars import pillars_passed
    vol_ok = (current.volume_5m or 0) >= min_volume_5m
    passed = pillars_passed(current, current.event_ts) if current.event_ts is not None else 0
    return vol_ok or passed >= min_pillars, vol_ok, passed


class HodMomentumScanner(Scanner):
    """New high-of-day + momentum confirmation.

    Confirmed platform behavior reproduced: HOD Momo intentionally does NOT
    alert on every high-of-day print — it requires both a new HOD and the
    momentum conditions, and repeated HOD ticks inside the cooldown are the
    notification router's job to suppress. Float bands / RVOL bands are
    independent approximations used only to label the branch.
    """

    scanner_id = "hod_momentum"
    definition_version = "hod_momentum@1.0.0"

    def __init__(
        self,
        min_change_pct: float = 10.0,
        min_recent_rvol: float = 3.0,
        min_price: float = 1.0,
        min_volume_5m: float = 25_000,
        low_float_max: float = 20_000_000,
        medium_float_max: float = 100_000_000,
        high_rvol_min: float = 5.0,
        price_band_split: float = 20.0,
        min_hod_advance_pct: float = 0.25,
        min_pillars: int = MIN_PILLARS_FOR_LIQUIDITY,
    ) -> None:
        self.min_change_pct = min_change_pct
        self.min_recent_rvol = min_recent_rvol
        self.min_price = min_price
        self.min_volume_5m = min_volume_5m
        self.min_pillars = min_pillars
        self.low_float_max = low_float_max
        self.medium_float_max = medium_float_max
        self.high_rvol_min = high_rvol_min
        self.price_band_split = price_band_split
        # Confirmed platform: HOD Momo does NOT alert on every high-of-day
        # print. Requiring a minimum advance over the prior high is this
        # application's independent approximation of that behaviour.
        self.min_hod_advance_pct = min_hod_advance_pct
        self._prior_hod: dict = {}

    def _branch(self, snap: SymbolSnapshot) -> Optional[str]:
        """Label the event with the closest captured branch name."""
        f = snap.float_shares
        rvol = snap.rvol_5m or effective_rvol(snap) or 0.0
        band = "high_rvol" if rvol >= self.high_rvol_min else "medium_rvol"
        if f is not None and f <= self.low_float_max:
            prefix = "low_float"
        elif f is not None and f <= self.medium_float_max:
            prefix = "medium_float"
        elif f is not None:
            # Float is known and larger than every captured band: this is not a
            # small-cap momentum name, so there is no branch for it.
            return None
        else:
            # Float is unknown, which is the normal case on a free feed. The
            # branch is a LABEL, as this class's docstring says; letting a
            # missing label suppress the alert entirely means the scanner goes
            # permanently silent on exactly the data most people have.
            prefix = "unknown_float"
        price_tag = "price_20_plus" if (snap.last or 0) >= self.price_band_split else "price_under_20"
        return f"{prefix}_{band}_{price_tag}"

    def on_snapshot(
        self,
        current: SymbolSnapshot,
        previous: Optional[SymbolSnapshot],
        state: SymbolState,
        hot: HotState,
    ) -> List[ScannerEvent]:
        now = current.event_ts
        if now is None or current.last is None:
            return []
        key = current.symbol
        prior_hod = self._prior_hod.get(key)
        current_high = current.session_high or current.last
        self._prior_hod[key] = current_high
        if prior_hod is None:
            return []  # first observation seeds the HOD; no alert
        advance_needed = max(
            MIN_TICK_BUFFER, prior_hod * self.min_hod_advance_pct / 100.0
        )
        new_hod = current_high > prior_hod + advance_needed
        if not new_hod:
            return []

        rvol_recent = current.rvol_5m if current.rvol_5m is not None else effective_rvol(current)
        liquid, vol_ok, pillars = _liquidity(current, self.min_volume_5m, self.min_pillars)
        # In thin tape the recent-RVOL check is the same wall as the share
        # floor (both count shares that have not printed yet); the pillars
        # stand in for both, never for the new high or the gain.
        rvol_ok = (rvol_recent is not None and rvol_recent >= self.min_recent_rvol) or (liquid and not vol_ok)
        reasons = [
            Reason("new_hod", _round(current_high, 4), True,
                   _round(prior_hod + advance_needed, 4)),
            Reason("change_pct", _round(current.change_from_close_pct),
                   (current.change_from_close_pct or 0) >= self.min_change_pct, self.min_change_pct),
            Reason("recent_rvol", _round(rvol_recent), rvol_ok, self.min_recent_rvol),
            Reason("price_min", _round(current.last), current.last >= self.min_price, self.min_price),
            Reason("volume_5m", current.volume_5m, liquid, self.min_volume_5m),
            Reason("pillars_passed", pillars, liquid, self.min_pillars),
        ]
        if not all(r.passed for r in reasons):
            return []
        branch = self._branch(current)
        if branch is None:
            return []
        return [
            self._event(
                current, now, "qualified", "high", reasons,
                branch=branch,
                extra_values={"hod": _round(current_high, 4), "prior_hod": _round(prior_hod, 4)},
            )
        ]


class RunningMoveScanner(Scanner):
    """Running Up / Running Down: rapid N-minute move with volume and
    liquidity guards, detectable before a new HOD. Direction, window and
    threshold are configuration; the Warrior formula is Unknown."""

    def __init__(
        self,
        direction: str = "up",
        window_minutes: int = 5,
        threshold_pct: float = 5.0,
        min_volume_5m: float = 25_000,
        min_price: float = 1.0,
        version: str = "1.0.0",
    ) -> None:
        self.direction = direction
        self.scanner_id = f"running_{direction}"
        self.definition_version = f"{self.scanner_id}@{version}"
        self.window_minutes = window_minutes
        self.threshold_pct = threshold_pct
        self.min_volume_5m = min_volume_5m
        self.min_price = min_price
        self._edges = EdgeTracker(rearm_after_fails=3)

    def on_snapshot(
        self,
        current: SymbolSnapshot,
        previous: Optional[SymbolSnapshot],
        state: SymbolState,
        hot: HotState,
    ) -> List[ScannerEvent]:
        now = current.event_ts
        if now is None or current.last is None:
            return []
        ref = state.price_minutes_ago(now, self.window_minutes)
        if ref is None or ref <= 0:
            return []
        move_pct = 100.0 * (current.last / ref - 1.0)
        if self.direction == "up":
            move_ok = move_pct >= self.threshold_pct
        else:
            move_ok = move_pct <= -self.threshold_pct
        volume_ok = (current.volume_5m or 0) >= self.min_volume_5m
        price_ok = current.last >= self.min_price
        qualifies = move_ok and volume_ok and price_ok
        if not self._edges.rising_edge(current.symbol, qualifies):
            return []
        reasons = [
            Reason(f"move_{self.window_minutes}m_pct", _round(move_pct), move_ok,
                   self.threshold_pct if self.direction == "up" else -self.threshold_pct),
            Reason("volume_5m", current.volume_5m, volume_ok, self.min_volume_5m),
            Reason("price_min", _round(current.last), price_ok, self.min_price),
        ]
        return [
            self._event(
                current, now, "qualified", "medium", reasons,
                extra_values={"reference_price": _round(ref, 4), "window_minutes": self.window_minutes},
            )
        ]


class UptrendScanner(Scanner):
    """Running Up, refined: a name in a live uptrend right now.

    "Up 5% in 5 minutes" fires on a single spike and is silent while a runner
    grinds higher on a series of higher highs — the tape a momentum trader
    actually wants to be alerted to. This scanner asks, over the last
    `window_minutes` (10 by default — long enough to be a trend, short enough
    to still be current):

      1. momentum   — last is at least `threshold_pct` above the price
                      `window_minutes` ago (3% default);
      2. fresh high — the window's high was printed within the last
                      `fresh_minutes` (3 default): the move is still making
                      highs, not fading from a spike;
      3. control    — last is above the window's volume-weighted average
                      price: buyers, not sellers, have the last ten minutes;
      4. liquidity  — 5-minute volume at or above the floor;
      5. price      — at or above `min_price`.

    Every threshold is an Approximation: the Warrior formula is Unknown. The
    event fires on the rising edge and re-arms after the condition has failed
    for three snapshots, so a name that keeps trending fires once per leg."""

    def __init__(
        self,
        window_minutes: int = 10,
        threshold_pct: float = 3.0,
        fresh_minutes: int = 3,
        min_volume_5m: float = 25_000,
        min_price: float = 1.0,
        version: str = "2.0.0",
        min_pillars: int = MIN_PILLARS_FOR_LIQUIDITY,
    ) -> None:
        self.scanner_id = "running_up"
        self.definition_version = f"running_up@{version}"
        self.window_minutes = window_minutes
        self.threshold_pct = threshold_pct
        self.fresh_minutes = fresh_minutes
        self.min_volume_5m = min_volume_5m
        self.min_price = min_price
        self._edges = EdgeTracker(rearm_after_fails=3)
        self.min_pillars = min_pillars

    def _window(self, state: SymbolState, now) -> list:
        from datetime import timedelta
        cutoff = now - timedelta(minutes=self.window_minutes)
        bars = [b for b in state.minute_bars if b.ts >= cutoff]
        building = getattr(state, "_building", None)
        if building is not None and building.ts >= cutoff:
            bars.append(building)
        return bars

    def on_snapshot(
        self,
        current: SymbolSnapshot,
        previous: Optional[SymbolSnapshot],
        state: SymbolState,
        hot: HotState,
    ) -> List[ScannerEvent]:
        from datetime import timedelta
        now = current.event_ts
        if now is None or current.last is None:
            return []
        ref = state.price_minutes_ago(now, self.window_minutes)
        bars = self._window(state, now)
        if ref is None or ref <= 0 or len(bars) < 3:
            return []
        move_pct = 100.0 * (current.last / ref - 1.0)
        move_ok = move_pct >= self.threshold_pct
        window_high = max(b.high for b in bars)
        fresh_cut = now - timedelta(minutes=self.fresh_minutes)
        recent_high = max((b.high for b in bars if b.ts >= fresh_cut), default=None)
        fresh_ok = recent_high is not None and recent_high >= window_high
        vol = sum(b.volume for b in bars)
        vwap = (sum(b.close * b.volume for b in bars) / vol) if vol > 0 else None
        vwap_ok = vwap is not None and current.last >= vwap
        volume_ok, _vol_only, pillars = _liquidity(current, self.min_volume_5m, self.min_pillars)
        price_ok = current.last >= self.min_price
        qualifies = move_ok and fresh_ok and vwap_ok and volume_ok and price_ok
        if not self._edges.rising_edge(current.symbol, qualifies):
            return []
        reasons = [
            Reason(f"move_{self.window_minutes}m_pct", _round(move_pct), move_ok, self.threshold_pct),
            Reason(f"fresh_high_{self.fresh_minutes}m", _round(recent_high), fresh_ok, _round(window_high)),
            Reason(f"above_vwap_{self.window_minutes}m", _round(current.last), vwap_ok, _round(vwap)),
            Reason("volume_5m", current.volume_5m, volume_ok, self.min_volume_5m),
            Reason("pillars_passed", pillars, volume_ok, self.min_pillars),
            Reason("price_min", _round(current.last), price_ok, self.min_price),
        ]
        severity = "high" if move_pct >= 2 * self.threshold_pct else "medium"
        return [
            self._event(
                current, now, "qualified", severity, reasons, branch=f"uptrend_{self.window_minutes}m",
                extra_values={"reference_price": _round(ref, 4), "window_minutes": self.window_minutes,
                              "window_high": _round(window_high), "vwap_window": _round(vwap)},
            )
        ]


def squeeze_5_in_5(**kw) -> RunningMoveScanner:
    """Squeeze branch name Confirmed platform: up 5% in 5 minutes."""
    s = RunningMoveScanner(direction="up", window_minutes=5, threshold_pct=5.0, **kw)
    s.scanner_id = "squeeze_5_in_5"
    s.definition_version = "squeeze_5_in_5@1.0.0"
    return s


def squeeze_10_in_10(**kw) -> RunningMoveScanner:
    """Squeeze branch name Confirmed platform: up 10% in 10 minutes."""
    s = RunningMoveScanner(direction="up", window_minutes=10, threshold_pct=10.0, **kw)
    s.scanner_id = "squeeze_10_in_10"
    s.definition_version = "squeeze_10_in_10@1.0.0"
    return s


class Breakout52wScanner(Scanner):
    """New 52-week high: current high exceeds the prior 252-session maximum
    (which excludes the current session). Rising-edge per day."""

    scanner_id = "breakout_52w"
    definition_version = "breakout_52w@1.0.0"

    def __init__(self, min_volume_5m: float = 25_000) -> None:
        self.min_volume_5m = min_volume_5m
        self._edges = EdgeTracker(rearm_after_fails=10_000)  # once per run/day

    def on_snapshot(
        self,
        current: SymbolSnapshot,
        previous: Optional[SymbolSnapshot],
        state: SymbolState,
        hot: HotState,
    ) -> List[ScannerEvent]:
        now = current.event_ts
        if now is None or current.last is None or current.high_52w is None:
            return []
        session_high = current.session_high or current.last
        breakout = session_high > current.high_52w
        volume_ok = (current.volume_5m or 0) >= self.min_volume_5m
        if not self._edges.rising_edge(current.symbol, breakout and volume_ok):
            return []
        reasons = [
            Reason("above_52w_high", _round(session_high, 4), True, _round(current.high_52w, 4)),
            Reason("volume_5m", current.volume_5m, volume_ok, self.min_volume_5m),
        ]
        return [self._event(current, now, "qualified", "medium", reasons)]
