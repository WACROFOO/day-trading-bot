"""The driver: universe -> setups -> fills -> ledger.

One `run_day` per (symbol, day, variant, cost model, ambiguity policy). The
engine is a single strict left-to-right pass over closed bars; there is no
second pass and nothing is re-derived from a completed day. That is the
structural half of the anti-look-ahead argument. The other half is
tests/test_lookahead.py, which truncates a session at successive cut-offs and
demands identical trades for everything entered before the cut.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict

from .data import Bar, BarProvider
from .execution import (COST_MODELS, CostModel, MissedEntry, PositionSim, Trade,
                        entry_limit_cap, try_fill)
from .indicators import SessionState, Snapshot
from .setups import Params, SetupEngine, Setup, Variant


class DayResult:
    def __init__(self):
        self.trades: list[Trade] = []
        self.missed: list[MissedEntry] = []
        self.observed: list[Setup] = []
        self.armed: list[Setup] = []
        self.ambiguous = 0
        self.halted = 0


def _ctx(s: Setup) -> dict:
    """The analysis cuts of brief section 17, copied onto each trade so the
    ledger is self-contained."""
    return dict(
        gap_pct=s.gap_pct, price=s.price, rvol_at_time=s.rvol_at_time,
        push_pct=s.push_pct, push_rvol=s.push_rvol,
        pullback_number=s.pullback_number, pullback_bars=s.pullback_bars,
        pullback_depth_pct=s.pullback_depth_pct,
        pullback_volume_ratio=s.pullback_volume_ratio,
        confluence_count=s.confluence_count, support_reasons=s.support_reasons,
        room_to_hod_r=s.room_to_hod_r, is_new_high_trigger=s.is_new_high_trigger,
        hod_at_time=s.hod_at_time, vwap=s.vwap, ema9=s.ema9, ema20=s.ema20,
        macd=s.macd, macd_hist=s.macd_hist, atr=s.atr, uses_atr_stop=s.uses_atr_stop,
        risk_pct=s.risk_pct, scan_ts=s.scan_ts, kind=s.kind,
        float_m=None, float_provenance="unavailable",
        catalyst=None, catalyst_source=None,
    )


def run_day(sym: str, day: dt.date, bars: list[Bar], params: Params,
            variant: Variant, cost: CostModel, ambiguity_policy: str,
            experiment: str = "exp1_common_exits",
            prev_close: float | None = None,
            same_time_profile: dict[int, float] | None = None,
            scan_ts: int | None = None,
            limit_cap_pct: float = 1.0,
            limit_cap_ticks: int = 10,
            max_setups_per_day: int | None = None,
            governor: dict | None = None) -> DayResult:
    """Replay one symbol-day. Bars must be chronological and closed."""
    res = DayResult()
    if len(bars) < 40:
        return res

    st = SessionState(sym, day, prev_close=prev_close,
                      same_time_cum_volume=same_time_profile)
    eng = SetupEngine(sym, day, params, variant)
    eng.scan_ts = scan_ts

    pos: PositionSim | None = None
    pending: Setup | None = None
    day_r = 0.0
    peak_r = 0.0
    consec_losses = 0
    filled_today = 0
    halted_day = False
    stopped_out_for_day = False

    for i, b in enumerate(bars):
        snap = st.update(b)
        if snap.halt_gap_before > 0 and snap.in_rth:
            halted_day = True

        # ---- 1. manage an open position on this bar -------------------
        if pos is not None:
            done = pos.step(snap, i)
            in_window = params.arm_start_et <= snap.et.time() < params.arm_end_et
            if not done and not in_window and pos.shares > 0:
                pos.force_flat(snap, "SESSION_FLAT")
                done = True
            if not done and i == len(bars) - 1:
                pos.force_flat(snap, "DAY_END")
                done = True
            if done:
                t = _book(pos, sym, day, variant, cost, ambiguity_policy,
                          experiment, snap, i)
                if t is not None:
                    res.trades.append(t)
                    day_r += t.net_r
                    peak_r = max(peak_r, day_r)
                    consec_losses = 0 if t.net_r > 0 else consec_losses + 1
                    if governor and _governor_stop(governor, day_r, peak_r,
                                                   consec_losses, filled_today):
                        stopped_out_for_day = True
                pos = None
                eng.free()
            else:
                eng.step(snap, in_position=True)
                continue

        # ---- 2. a live armed order tries to fill on this bar ----------
        if pending is not None and pos is None:
            in_window = params.arm_start_et <= snap.et.time() < params.arm_end_et
            touched_trigger = b.h >= pending.trigger
            touched_stop = b.l <= pending.stop
            if not in_window:
                pending = None
            elif touched_stop and not touched_trigger:
                # price hit the stop level before the trigger could print:
                # the order dies (ross-fp-v4.pine 1494-1500).
                pending = None
            elif touched_trigger:
                ambiguous = touched_stop
                if ambiguous:
                    res.ambiguous += 1
                if ambiguous and ambiguity_policy == "exclude":
                    pending = None
                else:
                    pos, pending = _open(pending, snap, i, cost, params, variant,
                                         res, ambiguity_policy, experiment)
                    if pos is not None:
                        filled_today += 1
                        pos.halt = pos.halt or (snap.halt_gap_before > 0 and snap.in_rth)
                        # THE ENTRY BAR IS RESOLVED HERE, not on the next one.
                        # Under the pessimistic policy an entry bar that also
                        # touched the stop books the stop immediately; under
                        # the optimistic policy the stop is not yet live and
                        # the target may fill on the same minute. Deferring
                        # this to bar i+1 would silently make every ambiguous
                        # bar optimistic (the defect the repo's own V7.5/V8
                        # benchmark measured at 25% of fills).
                        if pos.step(snap, i):
                            t = _book(pos, sym, day, variant, cost,
                                      ambiguity_policy, experiment, snap, i)
                            if t is not None:
                                res.trades.append(t)
                                day_r += t.net_r
                                peak_r = max(peak_r, day_r)
                                consec_losses = 0 if t.net_r > 0 else consec_losses + 1
                                if governor and _governor_stop(governor, day_r, peak_r,
                                                               consec_losses, filled_today):
                                    stopped_out_for_day = True
                            pos = None
                            eng.free()

        # ---- 3. advance the setup machine on the closed bar -----------
        if pos is None and not stopped_out_for_day:
            armed = eng.step(snap, in_position=False)
            if armed is not None:
                if max_setups_per_day is not None and filled_today >= max_setups_per_day:
                    pass
                else:
                    if variant.third_trade_half_size and filled_today >= 2:
                        armed.planned_shares = max(1, armed.planned_shares // 2)
                    pending = armed
                    res.armed.append(armed)
        elif pos is not None:
            eng.step(snap, in_position=True)

    if pos is not None and st.bars:
        last = st.bars[-1]
        snap = Snapshot(i=len(bars) - 1, bar=last, ema9=0, ema20=0, macd=0,
                        macd_signal=0, macd_hist=0, macd_hist_prev=0, atr=pos.s.atr,
                        vwap=None, hod=0, lod=0, cum_volume=0, cum_dollar_volume=0,
                        vol_baseline=None, vol_baseline_hist=[], rvol_at_time=None,
                        prev_close=None, gap_pct=None, session_minute=0, in_rth=True,
                        et=last.et, dollar_per_min_5=0, dollar_per_min_20=0,
                        dollar_per_min_day=0, spread_est=0.01, halt_gap_before=0)
        pos.force_flat(snap, "DAY_END")
        t = _book(pos, sym, day, variant, cost, ambiguity_policy, experiment,
                  snap, len(bars) - 1)
        if t is not None:
            res.trades.append(t)

    res.observed = eng.observed
    res.halted = 1 if halted_day else 0
    return res


def _governor_stop(g: dict, day_r: float, peak_r: float, consec: int,
                   trades: int) -> bool:
    """brief section 27. None of this is in the Pine; it is an overlay so the
    with/without comparison can be run."""
    if g.get("max_trades_per_day") and trades >= g["max_trades_per_day"]:
        return True
    if g.get("max_daily_loss_r") and day_r <= -abs(g["max_daily_loss_r"]):
        return True
    if g.get("consecutive_loss_stop") and consec >= g["consecutive_loss_stop"]:
        return True
    if g.get("green_to_red_stop") and peak_r > 0 and day_r < 0:
        return True
    if g.get("giveback_pct_of_peak") and peak_r > 0 and \
            day_r <= peak_r * (1 - g["giveback_pct_of_peak"] / 100.0):
        return True
    return False


def _open(setup: Setup, snap: Snapshot, i: int, cost: CostModel, params: Params,
          variant: Variant, res: DayResult, ambiguity_policy: str,
          experiment: str, limit_cap_pct: float = 1.0,
          limit_cap_ticks: int = 10):
    outcome, px, shares, slip = try_fill(setup, snap, cost, params,
                                         limit_cap_pct=limit_cap_pct,
                                         limit_cap_ticks=limit_cap_ticks)
    if outcome != "FILL":
        if outcome != "NO_TOUCH":
            res.missed.append(MissedEntry(
                sym=setup.sym, day=setup.day, variant=variant.name,
                setup_ts=setup.ts, trigger=setup.trigger,
                limit_cap=setup.trigger * 1.01, bar_open=snap.bar.o,
                bar_high=snap.bar.h, reason=outcome))
        return None, None
    ambiguous = snap.bar.l <= setup.stop
    # policy decides whether the stop is live on the entry bar itself
    stop_same_bar = ambiguous and ambiguity_policy == "pessimistic"
    p = PositionSim(setup, px, shares, i, snap.bar, cost, params,
                    stop_active_same_bar=stop_same_bar,
                    bailout=(experiment == "exp2_full_management"))
    p.entry_slippage = slip
    p.entry_ts = snap.bar.ts
    p.entry_et = snap.et.isoformat()
    p.limit_cap = entry_limit_cap(setup.trigger, params, limit_cap_pct,
                                  limit_cap_ticks)
    p.ambiguous = ambiguous
    p.participation_capped = shares < setup.planned_shares
    return p, None


def _book(pos: PositionSim, sym: str, day: dt.date, variant: Variant,
          cost: CostModel, ambiguity_policy: str, experiment: str,
          snap: Snapshot, i: int) -> Trade | None:
    if pos.closed is None:
        return None
    exit_ts, exit_px, reason = pos.closed
    gross = pos.banked
    fees = cost.fee(pos.orders)
    net = gross - fees
    r_unit = pos.rps * pos.shares_open
    return Trade(
        sym=sym, day=day.isoformat(), variant=variant.name,
        cost_model=cost.name, ambiguity_policy=ambiguity_policy,
        experiment=experiment, setup_ts=pos.s.ts, entry_ts=pos.s.ts,
        entry_et=pos.entry_et, kind=pos.s.kind,
        trigger=pos.s.trigger, limit_cap=pos.limit_cap, stop=pos.s.stop,
        risk_per_share=pos.rps, planned_shares=pos.s.planned_shares,
        filled_shares=pos.shares_open, entry_fill=pos.entry,
        entry_slippage=getattr(pos, "entry_slippage", 0.0),
        exit_ts=exit_ts, exit_et=dt.datetime.fromtimestamp(exit_ts, snap.et.tzinfo).isoformat(),
        exit_price=exit_px, exit_reason=reason,
        gross_pnl=gross + pos.slip_cost, commissions=fees,
        slippage_cost=pos.slip_cost, net_pnl=net,
        net_r=net / r_unit if r_unit else 0.0,
        mae_r=pos.mae, mfe_r=pos.mfe, bars_held=i - pos.entry_i,
        ambiguous=bool(getattr(pos, "ambiguous", False)), halt_flag=pos.halt,
        participation_capped=bool(getattr(pos, "participation_capped", False)),
        context=_ctx(pos.s))


def trade_records(trades: list[Trade]) -> list[dict]:
    out = []
    for t in trades:
        d = asdict(t)
        ctx = d.pop("context")
        d.update({f"ctx_{k}": v for k, v in ctx.items()})
        out.append(d)
    return out
