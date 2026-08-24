"""Fills, costs, ambiguity and halts.

Three things in here decide whether a backtest is honest or decorative.

1. STOP-LIMIT ENTRY (brief section 10). The armed order is a stop with a limit
   cap. A bar that opens above the cap is a MISS, not a fill at the cap and not
   a fill at the trigger. Missed entries are counted and reported; turning every
   breakout into a fill is how a small-cap backtest invents its edge.

2. AMBIGUITY (brief section 5). A 1-minute bar whose range covers both the
   trigger and the stop carries no sequence information. Such a bar is FLAGGED
   and resolved under an explicit policy - pessimistic by default - and the
   optimistic and excluded variants are reported alongside. It is never
   silently booked as a winner. The repo has measured this before: 25% of
   fills on one 11-day tape touched both levels in the entry minute
   (research/momentum-replication/reports/2026-08-pine-v8-benchmark.md).

3. HALTS. A missing minute inside RTH is treated as a possible halt. A stop
   cannot execute while a stock is halted, and reopens are frequently below
   the stop, so trades whose exit crosses a gap are flagged rather than
   assumed to have filled at the stop.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from .data import Bar
from .indicators import Snapshot
from .setups import Setup, Params


@dataclass
class CostModel:
    """One column of brief section 28's gross / realistic / stressed table."""
    name: str
    slip_ticks_min: int = 0
    spread_mult: float = 0.0
    atr_mult: float = 0.0
    commission: bool = True
    commission_per_order: float = 1.0
    max_participation_pct: float = 2.0
    tick: float = 0.01

    def slippage(self, snap_atr: float, spread_est: float, shares: int,
                 bar_volume: float) -> float:
        """Per-share adverse slippage. A function of spread, volatility and how
        much of the printed minute we are trying to be - not one fixed cent
        amount for a $2 shell and a $19 biotech alike (brief section 9)."""
        participation = min(1.0, shares / bar_volume) if bar_volume > 0 else 1.0
        return (self.slip_ticks_min * self.tick
                + self.spread_mult * (spread_est / 2.0)
                + self.atr_mult * snap_atr * participation)

    def fee(self, orders: int) -> float:
        return self.commission_per_order * orders if self.commission else 0.0


GROSS = CostModel("gross", 0, 0.0, 0.00, commission=False)
LOW = CostModel("low", 1, 0.5, 0.02)
REALISTIC = CostModel("realistic", 3, 1.0, 0.05)
STRESSED = CostModel("stressed", 10, 2.0, 0.15)
COST_MODELS = {c.name: c for c in (GROSS, LOW, REALISTIC, STRESSED)}


@dataclass
class Trade:
    """One row of the machine-readable ledger (brief section 11)."""
    sym: str
    day: str
    variant: str
    cost_model: str
    ambiguity_policy: str
    experiment: str
    setup_ts: int
    entry_ts: int
    entry_et: str
    kind: str
    # plan
    trigger: float
    limit_cap: float
    stop: float
    risk_per_share: float
    planned_shares: int
    filled_shares: int
    entry_fill: float
    entry_slippage: float
    # outcome
    exit_ts: int
    exit_et: str
    exit_price: float
    exit_reason: str
    gross_pnl: float
    commissions: float
    slippage_cost: float
    net_pnl: float
    net_r: float
    mae_r: float
    mfe_r: float
    bars_held: int
    ambiguous: bool
    halt_flag: bool
    participation_capped: bool
    # context copied off the setup for the analysis cuts
    context: dict = field(default_factory=dict)


@dataclass
class MissedEntry:
    sym: str
    day: str
    variant: str
    setup_ts: int
    trigger: float
    limit_cap: float
    bar_open: float
    bar_high: float
    reason: str


class PositionSim:
    """Manages one filled position bar by bar.

    Exits, in the order the Pine evaluates them:
      gap through stop  ->  fill at the bar OPEN, adverse (never at the stop)
      stop touched      ->  fill at the stop, adverse
      T1 at +1R         ->  sell floor(qty/2), stop to break-even
      T2 at +2R         ->  the runner
      bailout           ->  Experiment 2 only (F's management)
      time flat         ->  the arm-window edge
    """

    def __init__(self, setup: Setup, entry_px: float, shares: int, entry_i: int,
                 entry_bar: Bar, cost: CostModel, params: Params,
                 stop_active_same_bar: bool, bailout: bool,
                 bailout_bars: int = 2, min_mfe_r: float = 0.5,
                 bail_on_close_below_entry: bool = True):
        self.s = setup
        self.entry = entry_px
        self.stop = setup.stop
        self.rps = setup.risk_per_share            # R unit = structural risk
        self.shares_open = shares
        self.shares = shares
        self.entry_i = entry_i
        self.cost = cost
        self.p = params
        self.stop_active_same_bar = stop_active_same_bar
        self.bailout = bailout
        self.t1 = entry_px + self.rps
        self.t2 = entry_px + self.rps * params.reward_multiple
        self.t1_done = False
        self.banked = 0.0
        self.orders = 1
        self.slip_cost = 0.0
        self.mfe = 0.0
        self.mae = 0.0
        self.halt = False
        self.high_since = entry_bar.h
        self.closed = None       # (exit_ts, exit_px, reason)
        self.bailout_bars = bailout_bars
        self.min_mfe_r = min_mfe_r
        self.bail_on_close_below_entry = bail_on_close_below_entry
        # set by the driver at fill time
        self.entry_slippage = 0.0
        self.entry_ts = setup.ts
        self.entry_et = setup.et
        self.limit_cap = setup.trigger
        self.ambiguous = False
        self.participation_capped = False

    def _slip(self, snap: Snapshot, shares: int) -> float:
        s = self.cost.slippage(snap.atr, snap.spread_est, shares, snap.bar.v)
        self.slip_cost += s * shares
        return s

    def _close_all(self, snap: Snapshot, px: float, reason: str):
        self.banked += self.shares * (px - self.entry)
        self.orders += 1
        self.closed = (snap.bar.ts, px, reason)
        self.shares = 0

    def step(self, snap: Snapshot, i: int) -> bool:
        """Returns True once the position is closed."""
        b = snap.bar
        if snap.halt_gap_before > 0 and snap.in_rth:
            self.halt = True
        stop_live = (i > self.entry_i) or self.stop_active_same_bar

        # excursions, in R, measured on the bar's extremes
        self.high_since = max(self.high_since, b.h)
        self.mfe = max(self.mfe, (b.h - self.entry) / self.rps)
        self.mae = min(self.mae, (b.l - self.entry) / self.rps)

        if stop_live and b.o <= self.stop:
            # gapped/halted through: the open is the first real price
            px = b.o - self._slip(snap, self.shares)
            self._close_all(snap, px, "STOP_GAP")
            return True
        target = self.t2 if self.t1_done else self.t1
        if stop_live and b.l <= self.stop and b.h >= target:
            # both touched inside one minute: caller already flagged ambiguity
            px = self.stop - self._slip(snap, self.shares)
            self._close_all(snap, px, "STOP_AMBIGUOUS")
            return True
        if stop_live and b.l <= self.stop:
            px = self.stop - self._slip(snap, self.shares)
            self._close_all(snap, px, "STOP")
            return True

        if not self.t1_done and b.h >= self.t1:
            half = self.shares // 2
            if half >= 1 and self.shares > 1:
                px = max(b.o, self.t1) - self._slip(snap, half)
                self.banked += half * (px - self.entry)
                self.shares -= half
                self.orders += 1
            self.t1_done = True
            self.stop = self.entry              # break-even on the runner
        if self.t1_done and self.shares > 0 and b.h >= self.t2:
            px = max(b.o, self.t2) - self._slip(snap, self.shares)
            self._close_all(snap, px, "T2")
            return True

        if self.bailout:
            bars_after = i - self.entry_i
            failed_mfe = bars_after >= self.bailout_bars and self.mfe < self.min_mfe_r
            lost_early = (self.bail_on_close_below_entry
                          and bars_after <= self.bailout_bars and b.c < self.entry)
            if failed_mfe or lost_early:
                px = b.c - self._slip(snap, self.shares)
                self._close_all(snap, px, "BAILOUT")
                return True
        return False

    def force_flat(self, snap: Snapshot, reason: str):
        px = snap.bar.c - self._slip(snap, self.shares)
        self._close_all(snap, px, reason)


def entry_limit_cap(trigger: float, params: Params, limit_cap_pct: float,
                    limit_cap_ticks: int) -> float:
    """The highest price the entry may pay.

    The offset is a TRADER decision made before the order goes in, so it must
    not be a function of the cost model - otherwise a stressed-slippage run
    silently widens its own limit and never misses. Two floors, whichever is
    larger:

      * `limit_cap_pct` of the trigger  - proportional, for high-priced names
      * `limit_cap_ticks` ticks         - absolute, and set to the Pine's own
        declared assumption (`slipTicksInput` = 10, ross-fp-v4.pine:404, kept
        equal to `strategy(slippage=10)` on line 7)

    An earlier revision used the percentage alone. On a $3 shell that is 3
    cents, which is inside these names' spread, and 79% of all entries were
    booked as MISSED because the study's OWN modelled slippage exceeded its
    own limit. That is a defect in the model, not a property of the market.
    """
    return trigger + max(trigger * limit_cap_pct / 100.0,
                         limit_cap_ticks * params.tick)


def try_fill(setup: Setup, snap: Snapshot, cost: CostModel, params: Params,
             limit_cap_pct: float,
             limit_cap_ticks: int = 10) -> tuple[str, float, int, float]:
    """Stop-limit entry on one bar.

    Returns (outcome, fill_price, shares, slippage_per_share) where outcome is
    one of NO_TOUCH / FILL / MISS_GAP / MISS_LIQUIDITY.
    """
    b = snap.bar
    cap = entry_limit_cap(setup.trigger, params, limit_cap_pct, limit_cap_ticks)
    if b.h < setup.trigger:
        return "NO_TOUCH", 0.0, 0, 0.0
    raw = max(b.o, setup.trigger)
    if raw > cap:
        # price was already above the permitted range when it printed
        return "MISS_GAP", 0.0, 0, 0.0
    # participation cap: never take more than our share of the printed minute
    max_shares = int(b.v * cost.max_participation_pct / 100.0)
    shares = min(setup.planned_shares, max_shares) if max_shares >= 0 else 0
    if shares < 1:
        return "MISS_LIQUIDITY", 0.0, 0, 0.0
    slip = cost.slippage(snap.atr, snap.spread_est, shares, b.v)
    px = raw + slip
    if px > cap:
        return "MISS_GAP", 0.0, 0, 0.0
    return "FILL", px, shares, slip
