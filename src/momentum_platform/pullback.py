"""First-pullback state machine and frozen planning bands (spec section 11).

Confirmed course structure: impulse -> 2-4 candle pullback on declining
volume -> first candle to break the prior candle's high is the trigger.
Entry = trigger high + buffer; stop = complete pullback low - buffer;
minimum planning target = 2R. Plans FREEZE when armed and never repaint.

This fixes the documented gap in the bundled Pine script, which armed bands
on any HOD/Running Up signal bar instead of detecting the true pullback.

Impulse/volume thresholds are independent approximations (configurable).
A qualified plan is a planning aid, never an order.

A plan's LIFE (2026-10-09) is bookkeeping beside the machine, never part of
it: `life_of(plan, now)` says whether a frozen plan is live at `now` — inside
the bot's entry window, inside its A10 fill window, not stopped, not done. The
transitions are unchanged, so the bot's plans are the same plans; the desk
reads the life so that it draws and prices only a plan that is live now.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from .models import Bar
from .order_math import ENTRY_TTL_MINUTES, entry_session

ET = ZoneInfo("America/New_York")
_SPAN = {"10s": 10, "30s": 30, "1m": 60, "2m": 120, "5m": 300, "15m": 900}


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
class PlanLife:
    """What became of one frozen plan, bar by bar. Observed, never decided:
    the machine's transitions do not read it.

    Why (owner, 2026-10-09 07:41): the desk drew VEEA's 04:03 plan — armed
    outside the bot's entry window, a 15 % stop — three and a half hours
    later, and priced it in the order block; it drew SAIQ's plan four minutes
    after it stopped. A plan is live only while all of these hold:

    - armed inside the bot's entry window (`order_math.entry_session` of the
      armed bar, the ledger's own session stamp);
    - inside its fill window: A10 cancels an entry not filled within
      `ENTRY_TTL_MINUTES` of being placed, and the bot places it when the
      trigger bar closes;
    - not stopped, not at 2R, not expired (the bars after the break)."""

    plan_id: str
    armed_bar: datetime             # the trigger bar's start (plan.armed_at_bar)
    decided_at: datetime            # that bar's close: the first moment anyone can act on the plan
    fill_until: datetime            # decided_at + ENTRY_TTL_MINUTES: the bot's entry rests until then
    in_window: bool                 # armed inside 07:00–11:20 ET, the bot's entry window
    triggered_bar: Optional[datetime] = None    # start of the bar in which the entry printed
    ended_bar: Optional[datetime] = None        # start of the bar that ended it
    end: Optional[str] = None       # "stop broke before the entry" | "stopped" | "reached 2R" | "expired"

    def live_until(self) -> Optional[datetime]:
        """The first bar time at which the plan is no longer live, or None
        when it never was (armed outside the window)."""
        if not self.in_window:
            return None
        if self.ended_bar is not None and self.ended_bar < self.fill_until:
            return self.ended_bar
        return self.fill_until


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
      is >= min_impulse_range_pct of price. Volume is NOT checked on the
      impulse (an earlier version of this line said "with rising/elevated
      volume"; the code never did — rules audit 2026-10-01). Ross states rising
      push volume as a preference with no threshold; the two measured versions
      lost more than the current rule (research/paper-exercise/reports/
      rules_audit_output.txt, "Ross volume" rows);
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
        self.lives: Dict[str, PlanLife] = {}

    @property
    def state(self) -> SetupState:
        return self._w.state

    @property
    def active_plan(self) -> Optional[PullbackPlan]:
        return self._w.plan

    # -- a plan's life (read-only bookkeeping, 2026-10-09) ---------------------

    def life_of(self, plan: Optional[PullbackPlan], now: datetime) -> dict:
        """Is `plan` live at `now` (the bar time the caller has read up to)?

        {"live", "why", "until"}: `why` says in words why a plan is not live
        (or what keeps it live), `until` is the bar time at which it stops
        being live. A plan is judged on the bars this detector has seen; `now`
        is the newest of them (a forming minute on the live desk)."""
        if plan is None:
            return {"live": False, "why": "no plan", "until": None}
        life = self.lives.get(plan.plan_id)
        if life is None:                            # a plan this detector never froze
            return {"live": False, "why": "not this detector's plan", "until": None}
        at = life.armed_bar.astimezone(ET).strftime("%H:%M")
        if not life.in_window:
            return {"live": False, "until": None,
                    "why": f"the {at} plan was armed outside the bot's 07:00–11:20 entry window"}
        if life.ended_bar is not None and life.ended_bar <= now:
            when = life.ended_bar.astimezone(ET).strftime("%H:%M")
            return {"live": False, "until": life.ended_bar, "why": f"the {at} plan {life.end} {when}"}
        if now >= life.fill_until:
            shut = life.fill_until.astimezone(ET).strftime("%H:%M")
            done = ("triggered, then its fill window closed" if life.triggered_bar is not None
                    else "never triggered; its fill window closed")
            return {"live": False, "until": life.fill_until,
                    "why": f"the {at} plan {done} {shut} (A10: {ENTRY_TTL_MINUTES} min)"}
        return {"live": True, "until": life.fill_until,
                "why": f"live until {life.fill_until.astimezone(ET):%H:%M} (A10: {ENTRY_TTL_MINUTES} min)"}

    def live_plan(self, now: datetime) -> Optional[PullbackPlan]:
        """The frozen plan that is live at `now`, else None. The machine holds
        at most one plan, so this is the active plan or nothing."""
        plan = self._w.plan
        if plan is None or self._w.state not in (SetupState.ARMED, SetupState.TRIGGERED):
            return None
        return plan if self.life_of(plan, now)["live"] else None

    def held_plan(self) -> Optional[PullbackPlan]:
        """A plan that still HOLDS the machine (ARMED or TRIGGERED): while it
        does, no new pullback can arm (the blackout — kept on purpose: removing
        it lost money in both readings, research/edge-hunt/PREREGISTRATION.md
        addendum 2026-10-06d, research/paper-exercise/reports/detector_variants_output.txt)."""
        if self._w.state in (SetupState.ARMED, SetupState.TRIGGERED):
            return self._w.plan
        return None

    def _note_end(self, bar: Bar, end: str) -> None:
        plan = self._w.plan
        life = self.lives.get(plan.plan_id) if plan is not None else None
        if life is not None and life.end is None:
            life.end, life.ended_bar = end, bar.ts

    def progress(self) -> dict:
        """Where the search stands, for the desk card: how many green bars the
        current push holds and how far it has run, without exposing the
        working state. Read-only."""
        w = self._w
        imp = w.impulse_bars
        rng = 0.0
        if imp and imp[0].open > 0:
            rng = 100.0 * (max(b.high for b in imp) - imp[0].open) / imp[0].open
        return {"state": w.state.value, "impulse_bars": len(imp), "impulse_pct": round(rng, 2),
                "impulse_valid": self._impulse_valid(imp), "pullback_bars": len(w.pullback_bars),
                "min_impulse_bars": self.min_impulse_bars, "min_impulse_pct": self.min_impulse_range_pct}

    def pending(self) -> Optional[dict]:
        """While a pullback forms, the levels the NEXT break would freeze.

        Read-only, for the manual order panel (2026-10-08): a plan exists only
        after the break, which is too late to have the order ready. The values
        are exactly what `_freeze_plan` would use if the next bar traded over
        the last pullback bar's high: entry = that high + entry_buffer, stop =
        the pullback low − stop_buffer, volume_ok the same comparison. They
        move as each pullback bar forms; nothing here arms anything."""
        w = self._w
        if w.state != SetupState.PULLBACK or not w.pullback_bars or not w.impulse_bars:
            return None
        trigger_high = w.pullback_bars[-1].high
        low = min(b.low for b in w.pullback_bars)
        entry = round(trigger_high + self.entry_buffer, 4)
        stop = round(low - self.stop_buffer, 4)
        imp = sum(b.volume for b in w.impulse_bars) / len(w.impulse_bars)
        pul = sum(b.volume for b in w.pullback_bars) / len(w.pullback_bars)
        return {"trigger_high": trigger_high, "entry": entry, "stop": stop,
                "risk_share": round(entry - stop, 4), "bars": len(w.pullback_bars),
                "max_bars": self.max_pullback_bars, "volume_ok": pul < imp,
                "impulse_high": max(b.high for b in w.impulse_bars),
                "trigger_bar_ts": w.pullback_bars[-1].ts}

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
                decided = bar.ts + timedelta(seconds=_SPAN.get(bar.timeframe, 60))
                self.lives[plan.plan_id] = PlanLife(
                    plan_id=plan.plan_id, armed_bar=bar.ts, decided_at=decided,
                    fill_until=decided + timedelta(minutes=ENTRY_TTL_MINUTES),
                    in_window=entry_session(bar.ts.astimezone(ET).time()) is not None)
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
                self._note_end(bar, "stop broke before the entry")
            elif bar.high >= plan.entry:
                w.state = SetupState.TRIGGERED
                life = self.lives.get(plan.plan_id)
                if life is not None:
                    life.triggered_bar = bar.ts
            elif self._armed_age > self.expire_armed_after_bars:
                w.state = SetupState.EXPIRED
                self._note_end(bar, "expired")
            return None

        if w.state == SetupState.TRIGGERED:
            plan = w.plan
            assert plan is not None
            if bar.low <= plan.stop:
                w.state = SetupState.STOPPED
                self._note_end(bar, "stopped")
            elif bar.high >= plan.target:
                w.state = SetupState.TARGET_HIT
                self._note_end(bar, "reached 2R")
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
