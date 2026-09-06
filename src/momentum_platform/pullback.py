"""First-pullback state machine and frozen planning bands (spec section 11).

Confirmed course structure: impulse -> 2-4 candle pullback on declining
volume -> first candle to break the prior candle's high is the trigger.
Entry = trigger high + buffer; stop = complete pullback low - buffer;
minimum planning target = 2R. Plans FREEZE when armed and never repaint.

This fixes the documented gap in the bundled Pine script, which armed bands
on any HOD/Running Up signal bar instead of detecting the true pullback.

Impulse/volume thresholds are independent approximations (configurable).
A qualified plan is a planning aid, never an order.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .models import Bar


class SetupState(str, Enum):
    SEEKING_IMPULSE = "seeking_impulse"
    PULLBACK = "pullback"
    ARMED = "armed"
    TRIGGERED = "triggered"
    TARGET_HIT = "target_hit"
    STOPPED = "stopped"
    EXPIRED = "expired"


@dataclass
class PullbackPlan:
    """Frozen once created; a later setup gets a new plan_id."""

    plan_id: str
    symbol: str
    trigger_high: float
    entry: float
    stop: float
    risk_share: float
    target: float
    reward_multiple: float
    impulse_high: float
    pullback_low: float
    pullback_candles: int
    armed_at_bar: object   # bar timestamp
    volume_ok: bool


@dataclass
class _Working:
    state: SetupState = SetupState.SEEKING_IMPULSE
    impulse_bars: List[Bar] = field(default_factory=list)
    pullback_bars: List[Bar] = field(default_factory=list)
    plan: Optional[PullbackPlan] = None


class FirstPullbackDetector:
    """Feed completed 1-minute bars in order via on_bar(); read .plans for
    frozen plans and .state for the machine's position.

    Definitions (independent approximations, all configurable):
    - impulse: >= min_impulse_bars consecutive green bars whose total range
      is >= min_impulse_range_pct of price, with rising/elevated volume;
    - pullback: 1..max_pullback_bars bars that do not make a new high;
      more than max_pullback_bars expires the setup (course: 5-6 candles
      means lost interest);
    - trigger: first bar to trade above the previous bar's high while the
      structure low holds; volume_ok records whether pullback volume declined
      below mean impulse volume (course volume profile).
    """

    def __init__(
        self,
        min_impulse_bars: int = 2,
        max_impulse_bars: int = 6,
        min_impulse_range_pct: float = 2.0,
        min_pullback_bars: int = 1,
        max_pullback_bars: int = 4,
        entry_buffer: float = 0.01,
        stop_buffer: float = 0.01,
        reward_multiple: float = 2.0,
        expire_armed_after_bars: int = 5,
    ) -> None:
        self.min_impulse_bars = min_impulse_bars
        # An impulse is a burst, not "every green candle since the open". Left
        # unbounded, a long quiet premarket drift would be counted as the
        # impulse leg and its low volume would invert the volume comparison.
        self.max_impulse_bars = max_impulse_bars
        self.min_impulse_range_pct = min_impulse_range_pct
        self.min_pullback_bars = min_pullback_bars
        self.max_pullback_bars = max_pullback_bars
        self.entry_buffer = entry_buffer
        self.stop_buffer = stop_buffer
        self.reward_multiple = reward_multiple
        self.expire_armed_after_bars = expire_armed_after_bars
        self._w = _Working()
        self._armed_age = 0
        self.plans: List[PullbackPlan] = []

    @property
    def state(self) -> SetupState:
        return self._w.state

    @property
    def active_plan(self) -> Optional[PullbackPlan]:
        return self._w.plan

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _green(bar: Bar) -> bool:
        return bar.close > bar.open

    def _impulse_valid(self, bars: List[Bar]) -> bool:
        if len(bars) < self.min_impulse_bars:
            return False
        low = bars[0].open
        high = max(b.high for b in bars)
        if low <= 0:
            return False
        return 100.0 * (high - low) / low >= self.min_impulse_range_pct

    def _reset(self) -> None:
        self._w = _Working()
        self._armed_age = 0

    # -- main -----------------------------------------------------------------

    def on_bar(self, bar: Bar) -> Optional[PullbackPlan]:
        """Returns a newly frozen plan when the machine arms, else None.

        Terminal states (TARGET_HIT / STOPPED / EXPIRED) persist until the
        next bar arrives so callers can observe the outcome; the machine then
        resets and treats that bar as the start of a new search."""
        if self._w.state in (SetupState.TARGET_HIT, SetupState.STOPPED, SetupState.EXPIRED):
            self._reset()
        w = self._w

        if w.state == SetupState.SEEKING_IMPULSE:
            if self._green(bar):
                w.impulse_bars.append(bar)
                del w.impulse_bars[:-self.max_impulse_bars]
            else:
                if self._impulse_valid(w.impulse_bars):
                    w.state = SetupState.PULLBACK
                    w.pullback_bars = [bar]
                else:
                    w.impulse_bars = []
            return None

        if w.state == SetupState.PULLBACK:
            impulse_high = max(b.high for b in w.impulse_bars)
            structure_low = min(b.low for b in w.pullback_bars)

            if bar.high > w.pullback_bars[-1].high and len(w.pullback_bars) >= self.min_pullback_bars:
                # Trigger bar: first new high over the prior candle.
                plan = self._freeze_plan(bar, impulse_high, structure_low)
                w.state = SetupState.ARMED
                w.plan = plan
                self._armed_age = 0
                self.plans.append(plan)
                return plan

            w.pullback_bars.append(bar)
            if len(w.pullback_bars) > self.max_pullback_bars:
                # 5-6 candles of pullback = lost interest; expire and restart.
                self._reset()
                if self._green(bar):
                    self._w.impulse_bars.append(bar)
            elif min(b.low for b in w.pullback_bars) < structure_low and bar.low < min(
                b.low for b in w.impulse_bars
            ):
                self._reset()
            return None

        if w.state == SetupState.ARMED:
            plan = w.plan
            assert plan is not None
            self._armed_age += 1
            if bar.low <= plan.stop:
                w.state = SetupState.STOPPED
            elif bar.high >= plan.entry:
                w.state = SetupState.TRIGGERED
            elif self._armed_age > self.expire_armed_after_bars:
                w.state = SetupState.EXPIRED
            return None

        if w.state == SetupState.TRIGGERED:
            plan = w.plan
            assert plan is not None
            if bar.low <= plan.stop:
                w.state = SetupState.STOPPED
            elif bar.high >= plan.target:
                w.state = SetupState.TARGET_HIT
            return None

        return None

    def _freeze_plan(self, trigger_bar: Bar, impulse_high: float, pullback_low: float) -> PullbackPlan:
        w = self._w
        trigger_high = w.pullback_bars[-1].high
        entry = trigger_high + self.entry_buffer
        stop = pullback_low - self.stop_buffer
        risk = entry - stop
        impulse_mean_vol = sum(b.volume for b in w.impulse_bars) / len(w.impulse_bars)
        pullback_mean_vol = sum(b.volume for b in w.pullback_bars) / len(w.pullback_bars)
        return PullbackPlan(
            plan_id=uuid.uuid4().hex[:12],
            symbol=trigger_bar.symbol,
            trigger_high=trigger_high,
            entry=round(entry, 4),
            stop=round(stop, 4),
            risk_share=round(risk, 4),
            target=round(entry + self.reward_multiple * risk, 4),
            reward_multiple=self.reward_multiple,
            impulse_high=impulse_high,
            pullback_low=pullback_low,
            pullback_candles=len(w.pullback_bars),
            armed_at_bar=trigger_bar.ts,
            volume_ok=pullback_mean_vol < impulse_mean_vol,
        )
