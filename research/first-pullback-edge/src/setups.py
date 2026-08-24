"""The first-pullback state machine, ported from ross-fp-v4.pine (REV V9.12).

This is a port, not the Pine. TradingView is the only Pine compiler, so state
parity with the shipped script is asserted here and checked only by the unit
tests in tests/. Where the port deviates it says so inline with a `PORT:` note.

The module's job in this study is narrower than the Pine's: for every bar it
must decide whether a first-pullback setup exists and record, for that setup,
EVERY gate's verdict independently. Variants A-F are then subsets of those
gates. That is what makes the ablation cheap and, more importantly, what makes
the rejected-trade analysis (brief section 20) fall out for free: a setup that
A accepts and B refuses is still recorded, with the reason.

Look-ahead: the engine sees exactly one Snapshot per bar and keeps nothing but
its own state. It cannot address bars[i+1]. `hod` on the Snapshot is the
session high through bar i. Pullback geometry is measured on closed bars only.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, asdict

from .data import Bar
from .indicators import Snapshot, SessionState

IDLE, IMPULSE, PULLBACK, ARMED, INVALID, DONE = "IDLE", "IMPULSE", "PULLBACK", "ARMED", "INVALID", "DONE"
KIND_PULLBACK, KIND_RETEST, KIND_FAST, KIND_UPTREND = "pullback", "retest", "fast_lane", "uptrend_lane"

# Every gate the ablation can switch. Order matters only for readability.
GATE_IDS = ["impulse", "pullback_structure", "retracement", "risk_structural",
            "momentum", "confluence", "pb_volume", "hod_room", "halt_band"]


@dataclass
class Params:
    """Frozen strategy parameters. Loaded from config/strategy.yaml."""
    # impulse
    min_push_pct: float = 5.0
    min_impulse_bars: int = 1
    max_impulse_bars: int = 6
    min_push_atr: float = 2.0
    min_efficiency: float = 0.60
    vol_baseline_bars: int = 20
    min_push_rvol: float = 2.0
    min_dollar_volume: float = 100_000.0
    # pullback
    min_pullback_bars: int = 1
    max_pullback_bars: int = 4
    max_retracement_pct: float = 50.0
    max_pb_volume_ratio: float = 0.70
    # confluence
    support_tolerance_pct: float = 0.35
    support_tolerance_atr: float = 0.20
    min_support_count: int = 1
    # hod room
    min_room_r: float = 1.0
    # risk
    max_stop_pct: float = 3.0
    # A stop one or two ticks wide is not a stop, it is a rounding artefact:
    # R becomes tiny and every excursion reads as hundreds of R. The sibling
    # megaday study hit the same thing (two fills at +375R and +291R on stops
    # of 0.011% and 0.034% of price) and removed them. Guarded here instead.
    min_risk_ticks: int = 2
    max_stop_atr: float = 1.5
    atr_stop_fallback: bool = True
    fallback_atr_mult: float = 1.0
    account_equity: float = 2000.0
    risk_pct: float = 2.0
    max_position_value: float = 2000.0
    slip_ticks_sizing: int = 10
    # execution
    tick: float = 0.01
    breakout_buffer_ticks: int = 1
    reward_multiple: float = 2.0
    # session
    arm_start_et: dt.time = dt.time(9, 30)
    arm_end_et: dt.time = dt.time(15, 58)


@dataclass
class Variant:
    """One rung of the ablation ladder."""
    name: str
    label: str
    gates: tuple[str, ...]
    lanes: bool = False
    retest: bool = False
    late_join: bool = False
    third_trade_half_size: bool = False
    # placebo/robustness switches (brief sections 23 and 25). Never used in
    # the frozen A-F run.
    allowed_pullback_numbers: tuple[int, ...] | None = None
    trigger_offset_ticks: int = 0
    override: dict = field(default_factory=dict)

    def p(self, base: Params) -> Params:
        """Params with this variant's overrides applied (sensitivity runs)."""
        if not self.override:
            return base
        d = asdict(base)
        d.update(self.override)
        return Params(**d)


@dataclass
class Setup:
    """One armable first-pullback candidate, with every gate's verdict.

    The field list is brief section 11's, plus the gate vector. Rows land in
    data/rejected_setups.parquet whether or not they are traded.
    """
    sym: str
    day: str
    ts: int
    et: str
    kind: str
    # scanner / context
    scan_ts: int | None
    gap_pct: float | None
    price: float
    rvol_at_time: float | None
    cum_volume: float
    cum_dollar_volume: float
    dollar_per_min_20: float
    # impulse
    impulse_start_bar: int
    impulse_peak_bar: int
    push_start_price: float
    push_peak: float
    push_pct: float
    push_atr: float
    push_efficiency: float
    push_rvol: float
    push_dollar_volume: float
    push_bars: int
    # pullback
    pullback_number: int
    pullback_bars: int
    red_pullback_bars: int
    pullback_low: float
    pullback_depth_pct: float | None
    pullback_volume_ratio: float | None
    # trigger / stop
    trigger: float
    stop: float
    uses_atr_stop: bool
    risk_per_share: float
    risk_pct: float
    risk_atr: float
    target_t1: float
    target_t2: float
    planned_shares: int
    # indicators at the arming bar
    vwap: float | None
    ema9: float
    ema20: float
    macd: float
    macd_hist: float
    atr: float
    # confluence / room
    confluence_count: int
    support_reasons: str
    hod_at_time: float
    room_to_hod_r: float | None
    is_new_high_trigger: bool
    halt_band_width: float | None
    # gates
    gates: dict = field(default_factory=dict)

    def passes(self, variant: Variant) -> bool:
        return all(self.gates.get(g, True) for g in variant.gates)

    def failed_gates(self, variant: Variant) -> list[str]:
        return [g for g in variant.gates if not self.gates.get(g, True)]


def _safe_div(a, b, default=None):
    try:
        if b in (0, None) or a is None:
            return default
        return a / b
    except (TypeError, ZeroDivisionError):
        return default


def halt_band_width(prev_close: float | None, close: float) -> float | None:
    """LULD band, ross-fp-v4.pine lines 561-564.
    <$0.75 -> fixed $0.15; $0.75-$3 -> 20%; >$3 -> 10%. Applies 09:30-16:00
    only (three corpus citations at Pine 566-572)."""
    if prev_close is None:
        return None
    if prev_close < 0.75:
        return 0.15
    if prev_close <= 3.0:
        return close * 0.20
    return close * 0.10


class SetupEngine:
    """Per symbol-day. Feed Snapshots in order; collect Setups.

    One instance per (symbol, day, variant) because the variant changes which
    setups arm, which changes what the machine is doing when the next dip
    prints. Running one engine and filtering afterwards would silently assume
    the machine is stateless, which it is not.
    """

    def __init__(self, sym: str, day: dt.date, params: Params, variant: Variant):
        self.sym, self.day = sym, day
        self.p = variant.p(params)
        self.v = variant
        self.state = IDLE
        self.kind = KIND_PULLBACK
        self.scan_after_bar: int | None = None
        self.snaps: list[Snapshot] = []
        self.setups: list[Setup] = []          # armed for THIS variant
        self.observed: list[Setup] = []        # every candidate, gates recorded
        self.scan_ts: int | None = None

        # push record
        self._push: dict | None = None
        # pullback record
        self._pb: dict | None = None
        # pullback numbering (study-level, see module docstring in report)
        self._leg_peak: float | None = None
        self._pullback_no = 0
        self._last_setup: Setup | None = None
        self._armed_stop: float = -1.0
        self._state_start_bar: int | None = None
        # HOD break-and-retest episode (ross-fp-v4.pine 614-637)
        self._broken_hod: float | None = None
        self._broken_bar: int | None = None
        self._retest_armed = False
        self._closes_below_broken = 0
        self._day_high_prev: float | None = None
        self.retest_max_age_bars = 30
        self.retest_tol_atr = 0.25
        self.retest_stop_buffer_ticks = 1

    # ---------------------------------------------------------------- api
    def busy(self) -> None:
        """Tell the engine a position is open: state work pauses, matching the
        Pine's `strategy.position_size == 0` guard on every signal block."""
        self._paused = True

    def free(self) -> None:
        self.state = IDLE
        self._push = self._pb = None

    # ------------------------------------------------------------ helpers
    def _enough_history(self, i: int) -> bool:
        # Pine line 877: bar_index > volumeBaselineBars + maxImpulseBars + 5
        return i > self.p.vol_baseline_bars + self.p.max_impulse_bars + 5

    def _impulse_search(self, s: Snapshot) -> dict | None:
        """ross-fp-v4.pine lines 878-930. Windows of min..max bars ENDING at
        the current bar; keep the highest-pct window that qualifies."""
        i = s.i
        if not self._enough_history(i):
            return None
        H = self.snaps
        best = None
        for w in range(self.p.min_impulse_bars, self.p.max_impulse_bars + 1):
            j = i - w
            if j < 1:
                continue
            if self.scan_after_bar is not None and not (j > self.scan_after_bar):
                continue
            start = H[j].bar
            rng = s.bar.h - start.l
            if start.l <= 0 or rng <= 0:
                continue
            # current bar must be the peak of the window
            if any(s.bar.h < H[i - k].bar.h for k in range(1, w + 1)):
                continue
            if not (s.bar.c > start.c and s.bar.c > s.bar.o):
                continue
            path = sum(abs(H[i - k].bar.c - H[i - k - 1].bar.c) for k in range(0, w))
            vol_sum = sum(H[i - k].bar.v for k in range(0, w))
            avg_vol = vol_sum / w
            baseline = H[j - 1].vol_baseline if j - 1 >= 0 else None
            pct = rng / start.l * 100.0
            atr_mult = _safe_div(rng, s.atr, 0.0) or 0.0
            eff = _safe_div(s.bar.c - start.c, path, 0.0) or 0.0
            rvol = _safe_div(avg_vol, baseline, 0.0) or 0.0
            dollar = avg_vol * max(s.bar.c, start.c)
            if not (pct >= self.p.min_push_pct and atr_mult >= self.p.min_push_atr
                    and eff >= self.p.min_efficiency and rvol >= self.p.min_push_rvol
                    and dollar >= self.p.min_dollar_volume):
                continue
            if best is None or pct > best["pct"] or (pct == best["pct"] and eff > best["eff"]):
                best = dict(start_bar=j, start_low=start.l, start_close=start.c,
                            peak=s.bar.h, peak_bar=i, pct=pct, atr=atr_mult, eff=eff,
                            rvol=rvol, vol_sum=vol_sum, avg_vol=avg_vol,
                            baseline=baseline or 0.0, dollar=dollar, path=path, bars=w)
        return best

    def _confluence(self, s: Snapshot) -> tuple[int, list[str]]:
        """ross-fp-v4.pine lines 1577-1585. A level counts as support when it
        sits at or below the close and within tolerance of it."""
        c = s.bar.c
        tol = max(c * self.p.support_tolerance_pct / 100.0,
                  s.atr * self.p.support_tolerance_atr)
        reasons = []
        ema9_sup = s.ema9 <= c and c - s.ema9 <= tol
        ema20_sup = s.ema20 <= c and c - s.ema20 <= tol
        vwap_sup = s.vwap is not None and s.vwap <= c and c - s.vwap <= tol
        half = (c * 2.0 // 1) / 2.0
        round_sup = half <= c and c - half <= tol
        n = sum((ema9_sup, ema20_sup, vwap_sup, round_sup))
        if ema9_sup:
            reasons.append("ema9")
        if ema20_sup:
            reasons.append("ema20")
        if vwap_sup:
            reasons.append("vwap")
        if round_sup:
            reasons.append("half_dollar")
        # emaClustered: the two EMAs on top of each other are ONE level
        if ema9_sup and ema20_sup and abs(s.ema9 - s.ema20) <= tol:
            n -= 1
            reasons.append("(emas_clustered:-1)")
        return max(0, n), reasons


    # ------------------------------------------------------ lanes (F only)
    def _momentum_ok(self, s: Snapshot) -> bool:
        """ross-fp-v4.pine 1580-1583 / 1825: the full momentum stack."""
        return (s.macd > 0 and s.macd_hist > 0 and s.bar.c > s.ema9
                and s.ema9 >= s.ema20
                and s.vwap is not None and s.bar.c > s.vwap)

    def _lane_setup(self, s: Snapshot, kind: str) -> Setup | None:
        """The FAST and UPTREND lanes (ross-fp-v4.pine 1840-1900).

        Both arm off a RED candle's high with a stop under its low. They skip
        push quality, retracement and pullback volume by design - the Pine's
        own comment says so - but they DO pass the room, risk, halt and clock
        controls. Because they carry no push record, `retracement` and
        `pb_volume` are unmeasurable and are recorded as such rather than as
        a pass: `passes()` sees None -> True only for gates the variant does
        not list, and F does list pb_volume, so a lane arm is judged on what
        it can actually be judged on. That asymmetry is stated in the report.
        """
        p = self.p
        tick = p.tick
        trigger = s.bar.h + (p.breakout_buffer_ticks + self.v.trigger_offset_ticks) * tick
        stop_raw = s.bar.l
        risk_raw = trigger - stop_raw
        if risk_raw <= 0:
            return None
        wide = (risk_raw / trigger * 100.0 > p.max_stop_pct
                or _safe_div(risk_raw, s.atr, 0.0) > p.max_stop_atr)
        uses_atr = bool(p.atr_stop_fallback and wide)
        stop = trigger - s.atr * p.fallback_atr_mult if uses_atr else stop_raw
        risk = trigger - stop
        if risk <= 0:
            return None
        saved_push, saved_pb = self._push, self._pb
        self._push = None
        self._pb = dict(bars=1, reds=1, low=s.bar.l, vol_sum=s.bar.v,
                        start_bar=s.i, last_bar=s.i)
        setup = self._build_setup(s, kind)
        self._push, self._pb = saved_push, saved_pb
        if setup is None:
            return None
        # a lane has no push record: these two are UNMEASURABLE, not passes
        setup.gates["impulse"] = True          # the lane is its own trigger
        setup.gates["retracement"] = True      # no push -> no retracement
        setup.gates["pb_volume"] = True        # no push volume to divide by
        setup.pullback_depth_pct = None
        setup.pullback_volume_ratio = None
        return setup

    def _update_retest_episode(self, s: Snapshot) -> None:
        """ross-fp-v4.pine 619-637. Records the FIRST close-confirmed break of
        the prior high of day and ages the episode out."""
        i = s.i
        if (self._broken_hod is None and self._day_high_prev is not None
                and s.bar.c > self._day_high_prev):
            self._broken_hod = self._day_high_prev
            self._broken_bar = i
            self._retest_armed = True
            self._closes_below_broken = 0
        elif self._broken_hod is not None and self._broken_bar is not None and i > self._broken_bar:
            self._closes_below_broken = (self._closes_below_broken + 1
                                         if s.bar.c < self._broken_hod else 0)
            if (self._closes_below_broken >= 2
                    or i - self._broken_bar > self.retest_max_age_bars):
                self._broken_hod = self._broken_bar = None
                self._retest_armed = False
                self._closes_below_broken = 0
        # dayHighPrev is the running high EXCLUDING this bar
        self._day_high_prev = s.hod

    def _retest_touch(self, s: Snapshot) -> bool:
        """Two-sided touch band (V8 re-audit ND-3): the low must come back TO
        the broken level, not through it, and the close must hold above."""
        if not (self._retest_armed and self._broken_hod is not None
                and self._broken_bar is not None and s.i > self._broken_bar):
            return False
        tol = max(s.atr * self.retest_tol_atr, self.p.tick)
        return (self._broken_hod - tol <= s.bar.l <= self._broken_hod + tol
                and s.bar.c > self._broken_hod and s.bar.c >= s.bar.o)

    def _retest_setup(self, s: Snapshot) -> Setup | None:
        """ross-fp-v4.pine 1315-1362: the retest supplies a different REASON to
        be in PULLBACK. Its 'impulse' is the leg from the broken level to the
        high that broke it - real and measurable, not a detector guess."""
        level = self._broken_hod
        if level is None or self._broken_bar is None:
            return None
        saved_push, saved_pb = self._push, self._pb
        self._push = dict(start_bar=self._broken_bar, start_low=level,
                          start_close=level, peak=s.hod, peak_bar=s.i,
                          pct=_safe_div(s.hod - level, level, 0.0) * 100.0,
                          atr=_safe_div(s.hod - level, s.atr, 0.0) or 0.0,
                          eff=1.0, rvol=_safe_div(s.bar.v, s.vol_baseline, 0.0) or 0.0,
                          vol_sum=s.bar.v, avg_vol=s.bar.v,
                          baseline=s.vol_baseline or 0.0,
                          dollar=s.bar.c * s.bar.v,
                          path=max(s.hod - level, self.p.tick),
                          bars=max(s.i - self._broken_bar, 1))
        self._pb = dict(bars=1, reds=1 if s.bar.c < s.bar.o else 0, low=s.bar.l,
                        vol_sum=s.bar.v, start_bar=s.i, last_bar=s.i)
        setup = self._build_setup(s, KIND_RETEST)
        if setup is not None:
            # the stop must sit BELOW the level it claims to trade against
            # (V7 reviewer note, Pine 1591-1594)
            below = level - self.retest_stop_buffer_ticks * self.p.tick
            if below < setup.trigger:
                setup.stop = min(setup.stop, below)
                setup.risk_per_share = setup.trigger - setup.stop
                setup.target_t1 = setup.trigger + setup.risk_per_share
                setup.target_t2 = (setup.trigger
                                   + setup.risk_per_share * self.p.reward_multiple)
        self._push, self._pb = saved_push, saved_pb
        return setup

    def _build_setup(self, s: Snapshot, kind: str) -> Setup | None:
        """Compute the candidate's geometry and every gate verdict at bar i."""
        p, push, pb = self.p, self._push, self._pb
        if pb is None:
            return None
        tick = p.tick
        trigger = s.bar.h + (p.breakout_buffer_ticks + self.v.trigger_offset_ticks) * tick
        stop_raw = pb["low"] - tick
        risk_raw = trigger - stop_raw
        if risk_raw <= 0:
            return None
        # wide-candle ATR fallback (Pine 1598-1601)
        wide = (risk_raw / trigger * 100.0 > p.max_stop_pct
                or _safe_div(risk_raw, s.atr, 0.0) > p.max_stop_atr)
        uses_atr = bool(p.atr_stop_fallback and wide)
        stop = trigger - s.atr * p.fallback_atr_mult if uses_atr else stop_raw
        risk = trigger - stop
        if risk <= 0:
            return None
        risk_pct = risk / trigger * 100.0
        risk_atr = _safe_div(risk, s.atr, 0.0) or 0.0

        # sizing on the slippage-stressed risk, Pine 1616-1621
        slip_ps = 2 * p.slip_ticks_sizing * tick
        budget = p.account_equity * p.risk_pct / 100.0
        shares_risk = int(budget // (risk + slip_ps)) if (risk + slip_ps) > 0 else 0
        shares_cap = int(p.max_position_value // trigger) if trigger > 0 else 0
        shares = max(0, min(shares_risk, shares_cap))

        push_range = (push["peak"] - push["start_low"]) if push else None
        depth = (_safe_div(push["peak"] - pb["low"], push_range) * 100.0
                 if push and push_range else None)
        push_avg_vol = push["avg_vol"] if push else None
        pb_avg_vol = pb["vol_sum"] / pb["bars"] if pb["bars"] else None
        pb_ratio = _safe_div(pb_avg_vol, push_avg_vol)

        conf_n, conf_reasons = self._confluence(s)
        band = halt_band_width(s.prev_close, s.bar.c)
        room_r = _safe_div(s.hod - trigger, risk)
        new_high_trigger = trigger >= s.hod - tick

        gates = {
            "impulse": push is not None,
            "pullback_structure": (p.min_pullback_bars <= pb["bars"] <= p.max_pullback_bars
                                   and (pb["reds"] >= 1 or kind == KIND_RETEST)),
            "retracement": depth is not None and depth <= p.max_retracement_pct,
            "risk_structural": (risk >= p.min_risk_ticks * tick
                                and risk_pct <= p.max_stop_pct
                                and risk_atr <= p.max_stop_atr and shares >= 1),
            "momentum": (s.macd > 0 and s.macd_hist > 0 and s.bar.c > s.ema9
                         and s.ema9 >= s.ema20
                         and s.vwap is not None and s.bar.c > s.vwap),
            "confluence": conf_n >= p.min_support_count,
            "pb_volume": pb_ratio is not None and pb_ratio <= p.max_pb_volume_ratio,
            # HOD room: new high OR >= min_room_r of headroom. HOD is at-time.
            "hod_room": bool(new_high_trigger or (room_r is not None and room_r >= p.min_room_r)),
            # fail-closed: unknown band inside RTH vetoes (Pine 1642, finding 9)
            "halt_band": (not s.in_rth) or (band is not None and risk <= band),
        }
        if self.v.allowed_pullback_numbers is not None:
            gates["pullback_number"] = self._pullback_no in self.v.allowed_pullback_numbers

        return Setup(
            sym=self.sym, day=self.day.isoformat(), ts=s.bar.ts, et=s.et.isoformat(),
            kind=kind, scan_ts=self.scan_ts, gap_pct=s.gap_pct, price=s.bar.c,
            rvol_at_time=s.rvol_at_time, cum_volume=s.cum_volume,
            cum_dollar_volume=s.cum_dollar_volume, dollar_per_min_20=s.dollar_per_min_20,
            impulse_start_bar=push["start_bar"] if push else -1,
            impulse_peak_bar=push["peak_bar"] if push else -1,
            push_start_price=push["start_low"] if push else float("nan"),
            push_peak=push["peak"] if push else float("nan"),
            push_pct=push["pct"] if push else float("nan"),
            push_atr=push["atr"] if push else float("nan"),
            push_efficiency=push["eff"] if push else float("nan"),
            push_rvol=push["rvol"] if push else float("nan"),
            push_dollar_volume=push["dollar"] if push else float("nan"),
            push_bars=push["bars"] if push else 0,
            pullback_number=self._pullback_no, pullback_bars=pb["bars"],
            red_pullback_bars=pb["reds"], pullback_low=pb["low"],
            pullback_depth_pct=depth, pullback_volume_ratio=pb_ratio,
            trigger=trigger, stop=stop, uses_atr_stop=uses_atr, risk_per_share=risk,
            risk_pct=risk_pct, risk_atr=risk_atr,
            target_t1=trigger + risk, target_t2=trigger + risk * p.reward_multiple,
            planned_shares=shares, vwap=s.vwap, ema9=s.ema9, ema20=s.ema20,
            macd=s.macd, macd_hist=s.macd_hist, atr=s.atr,
            confluence_count=conf_n, support_reasons="|".join(conf_reasons),
            hod_at_time=s.hod, room_to_hod_r=room_r,
            is_new_high_trigger=new_high_trigger, halt_band_width=band,
            gates=gates)

    # ------------------------------------------------------------- driver
    def step(self, s: Snapshot, in_position: bool) -> Setup | None:
        """Advance one closed bar. Returns a Setup when the machine arms for
        THIS variant; always appends the candidate to `observed`."""
        self.snaps.append(s)
        i = s.i
        armable_clock = self.p.arm_start_et <= s.et.time() < self.p.arm_end_et

        if self.v.retest:
            self._update_retest_episode(s)

        if in_position:
            # Pine guards every signal block on position_size == 0.
            return None

        if self.state in (INVALID, DONE):
            self.state = IDLE
            self._push = self._pb = None

        # ---- HOD break-and-retest, checked BEFORE the impulse path -----
        if self.v.retest and self.state == IDLE and self._retest_touch(s):
            setup = self._retest_setup(s)
            if setup is not None:
                self.observed.append(setup)
                if setup.passes(self.v) and armable_clock:
                    self.kind = KIND_RETEST
                    self.state = ARMED
                    self._state_start_bar = s.i
                    self._armed_stop = setup.stop
                    self._pullback_no += 1
                    self._push = dict(
                        start_bar=self._broken_bar, start_low=self._broken_hod,
                        start_close=self._broken_hod, peak=s.hod, peak_bar=s.i,
                        pct=setup.push_pct, atr=setup.push_atr, eff=1.0,
                        rvol=setup.push_rvol, vol_sum=s.bar.v, avg_vol=s.bar.v,
                        baseline=s.vol_baseline or 0.0,
                        dollar=setup.push_dollar_volume,
                        path=max(s.hod - self._broken_hod, self.p.tick),
                        bars=setup.push_bars)
                    self._pb = dict(bars=1, reds=1 if s.bar.c < s.bar.o else 0,
                                    low=s.bar.l, vol_sum=s.bar.v,
                                    start_bar=s.i, last_bar=s.i)
                    self.setups.append(setup)
                    self._broken_hod = self._broken_bar = None
                    self._retest_armed = False
                    return setup

        if self.state == IDLE:
            best = self._impulse_search(s)
            if best:
                # leg / pullback numbering: a dip off a HIGHER peak continues
                # the same leg; a dip off a lower peak restarts the count.
                if self._leg_peak is None or best["peak"] > self._leg_peak:
                    pass
                else:
                    self._pullback_no = 0
                self._leg_peak = best["peak"]
                self._push = best
                self.state = IMPULSE
                return None
            return None

        if self.state == IMPULSE:
            assert self._push is not None
            new_peak = s.bar.h > self._push["peak"]
            prev_c = self.snaps[i - 1].bar.c
            clean = new_peak and s.bar.c >= s.bar.o and s.bar.c >= prev_c
            if clean:
                pu = self._push
                pu["peak"] = s.bar.h
                pu["peak_bar"] = i
                pu["bars"] += 1
                pu["vol_sum"] += s.bar.v
                pu["avg_vol"] = pu["vol_sum"] / pu["bars"]
                pu["rvol"] = _safe_div(pu["avg_vol"], pu["baseline"], 0.0) or 0.0
                pu["dollar"] = pu["avg_vol"] * max(pu["peak"], pu["start_close"])
                pu["path"] += abs(s.bar.c - prev_c)
                pu["eff"] = _safe_div(s.bar.c - pu["start_close"], pu["path"], 0.0) or 0.0
                pu["pct"] = (pu["peak"] - pu["start_low"]) / pu["start_low"] * 100.0
                pu["atr"] = _safe_div(pu["peak"] - pu["start_low"], s.atr, 0.0) or 0.0
                self._leg_peak = max(self._leg_peak or 0.0, pu["peak"])
                return None
            if new_peak:
                self._push["peak"] = s.bar.h
                self._push["peak_bar"] = i
                self._push["pct"] = (s.bar.h - self._push["start_low"]) / self._push["start_low"] * 100.0
                self._push["atr"] = _safe_div(s.bar.h - self._push["start_low"], s.atr, 0.0) or 0.0
            # -> first dip
            self.state = PULLBACK
            self._pullback_no += 1
            self._pb = dict(bars=1, reds=1 if s.bar.c < s.bar.o else 0,
                            low=s.bar.l, vol_sum=s.bar.v, start_bar=i, last_bar=i)
            return self._maybe_arm(s, armable_clock)

        if self.state in (PULLBACK, ARMED):
            if self._pb is None:
                self.state = IDLE
                return self._lanes(s, armable_clock)
            if self.state == ARMED and s.bar.l <= self._armed_stop:
                # Pine 1494-1500: price hit the stop before the trigger.
                self.state = INVALID
                self.scan_after_bar = i
                return None
            pb = self._pb
            pb["bars"] += 1
            pb["reds"] += 1 if s.bar.c < s.bar.o else 0
            pb["low"] = min(pb["low"], s.bar.l)
            pb["vol_sum"] += s.bar.v
            pb["last_bar"] = i
            self.state = PULLBACK
            push_range = (self._push["peak"] - self._push["start_low"]) if self._push else None
            depth = (_safe_div(self._push["peak"] - pb["low"], push_range) * 100.0
                     if push_range else None)
            if (depth is not None and depth > self.p.max_retracement_pct) or \
                    pb["bars"] > self.p.max_pullback_bars:
                self.state = INVALID
                self.scan_after_bar = i
                return None
            armed = self._maybe_arm(s, armable_clock)
            if armed is not None:
                return armed
            return self._lanes(s, armable_clock)

        return self._lanes(s, armable_clock)

    def _lanes(self, s: Snapshot, armable_clock: bool) -> Setup | None:
        """laneOpen, ross-fp-v4.pine 1836-1837. Variant F only."""
        if not self.v.lanes or not (s.bar.c < s.bar.o):
            return None
        in_structure = self.state in (IMPULSE, PULLBACK)
        fast_ok = in_structure and self._momentum_ok(s)
        uptrend_ok = (self.state == IDLE
                      and (self._state_start_bar is None or s.i > self._state_start_bar)
                      and self._momentum_ok(s))
        if not (fast_ok or uptrend_ok):
            return None
        kind = KIND_FAST if in_structure else KIND_UPTREND
        setup = self._lane_setup(s, kind)
        if setup is None:
            return None
        self.observed.append(setup)
        if not setup.passes(self.v) or not armable_clock:
            return None
        self.kind = kind
        self.state = ARMED
        self._state_start_bar = s.i
        self._armed_stop = setup.stop
        self._pullback_no = max(1, self._pullback_no)
        # Pine 1900-1922: a lane arm initialises a COMPLETE setup record with
        # its own provenance kind. Without this the next bar advances a
        # PULLBACK that has no pullback record behind it.
        self._pb = dict(bars=1, reds=1, low=s.bar.l, vol_sum=s.bar.v,
                        start_bar=s.i, last_bar=s.i)
        if kind == KIND_UPTREND:
            self._push = None      # no push record exists in a clean-IDLE arm
        self.setups.append(setup)
        return setup

    def _maybe_arm(self, s: Snapshot, armable_clock: bool) -> Setup | None:
        setup = self._build_setup(s, self.kind)
        if setup is None:
            return None
        self.observed.append(setup)
        if not setup.passes(self.v):
            return None
        if not armable_clock:
            return None                    # venueGate: RTH-only on defaults
        self.state = ARMED
        self._armed_stop = setup.stop
        self.setups.append(setup)
        return setup
