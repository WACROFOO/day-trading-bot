"""Portfolio-level simulation across many tickers on one shared account.

`replay.py` decides one symbol in isolation. This layer answers the question
that actually matters: with ONE account, what would you really have traded?
Capital is finite, only one position is open at a time, §7 caps the day at
two trades and §8 can lock the account outright — so most valid signals are
never actionable, and knowing *which* and *why* is the point of this module.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd

from . import replay


@dataclass
class Config:
    """§7 sizing and §8 daily limits."""
    starting_equity: float = 100_000.0
    risk_pct: float = replay.RISK_PCT          # §7 2% of account
    max_trades_per_day: int = 2                # §7
    max_daily_loss_pct: float = 6.0            # §8
    giveback_pct: float = 50.0                 # §8 of the day's peak gain
    green_to_red_stop: bool = True             # §8
    consecutive_loss_stop: int = 3             # §8
    drawdown_walkaway_pct: float = 20.0        # §8 from equity high-water mark
    one_position_at_a_time: bool = True
    max_participation_pct: float = replay.MAX_PARTICIPATION_PCT


# why a valid signal never became a trade
BLOCK_RISK_GATE = "risk_gate_locked"
BLOCK_MAX_TRADES = "max_trades_per_day"
BLOCK_POSITION_OPEN = "position_already_open"
BLOCK_NO_CASH = "insufficient_cash"
BLOCK_NO_LIQUIDITY = "insufficient_liquidity"


@dataclass
class Trade:
    session: str
    symbol: str
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp | None
    entry: float
    stop: float
    target: float
    shares: int
    risk_per_share: float
    reward_risk: float
    r_multiple: float
    net_pnl: float
    exit_reason: str
    mae_r: float
    mfe_r: float
    bars_held: int
    equity_before: float
    equity_after: float
    size_capped_by_cash: bool
    size_bound_by: str
    confluence_count: int
    support_reasons: str


@dataclass
class Blocked:
    """A signal the strategy generated that the account could not act on."""
    session: str
    symbol: str
    timestamp: pd.Timestamp
    reason: str
    detail: str
    would_be_r: float = float("nan")     # counterfactual, for opportunity cost
    would_be_pnl: float = float("nan")


@dataclass
class DayState:
    date: str
    start_equity: float
    peak_equity: float
    end_equity: float = float("nan")
    trades: int = 0
    consecutive_losses: int = 0
    locked: bool = False
    lock_reason: str = ""
    lock_time: pd.Timestamp | None = None


def risk_check(day: DayState, equity: float, hwm: float,
                cfg: Config) -> tuple[bool, str]:
    """§8 — evaluated after every closed trade. Returns (locked, reason)."""
    loss_pct = (day.start_equity - equity) / day.start_equity * 100.0
    if loss_pct >= cfg.max_daily_loss_pct:
        return True, f"max_daily_loss {loss_pct:.2f}% >= {cfg.max_daily_loss_pct}%"

    peak_gain = day.peak_equity - day.start_equity
    if peak_gain > 0:
        given_back = (day.peak_equity - equity) / peak_gain * 100.0
        if given_back >= cfg.giveback_pct:
            return True, f"giveback {given_back:.0f}% of peak gain"

    if cfg.green_to_red_stop and day.peak_equity > day.start_equity and equity < day.start_equity:
        return True, "green_to_red"

    if day.consecutive_losses >= cfg.consecutive_loss_stop:
        return True, f"{day.consecutive_losses} consecutive losses"

    drawdown = (hwm - equity) / hwm * 100.0 if hwm > 0 else 0.0
    if drawdown >= cfg.drawdown_walkaway_pct:
        return True, f"drawdown {drawdown:.1f}% from high-water mark"

    return False, ""


def _opportunity_cost(bars: pd.DataFrame, cursor: int, row, equity: float,
                      cfg: Config) -> tuple[float, float]:
    """What a blocked signal would have returned, at the size it would have
    been given. Without this, "trades never seen" is an unpriced list."""
    entry, stop = float(row["entry"]), float(row["stop"])
    risk = entry - stop
    if risk <= 0 or bars is None:
        return float("nan"), float("nan")
    shares, _ = replay.size_position(equity, entry, risk, bars.iloc[:cursor + 1],
                                     risk_pct=cfg.risk_pct,
                                     participation_pct=cfg.max_participation_pct)
    if shares <= 0:
        return float("nan"), float("nan")
    shadow = replay.Decision(
        timestamp=row["timestamp"], symbol=row["symbol"], price=float(row["price"]),
        verdict="TAKE", reason="blocked-counterfactual", entry=entry, stop=stop,
        target=float(row["target"]), risk_per_share=risk,
        reward_risk=float(row["reward_risk"]), shares=shares)
    out = replay.resolve(bars, cursor, shadow)
    return (out.r_multiple, out.net_pnl) if out.resolved else (float("nan"), float("nan"))


def simulate(logs: pd.DataFrame,
             bars_by_key: dict[tuple[str, str], pd.DataFrame],
             cfg: Config | None = None) -> dict:
    """Walk every session chronologically on one account.

    `logs` is the concatenated per-candle decision log from
    `replay.replay_session`, carrying `session`, `symbol` and `cursor`.
    Sizing is recomputed at trade time against live equity — a $100k account
    sizing off a $0.08 stop wants more shares than its cash can buy, so the
    §7 cash cap binds and must not be pre-baked into the log.
    """
    cfg = cfg or Config()
    if logs.empty:
        return {"trades": pd.DataFrame(), "blocked": pd.DataFrame(),
                "days": pd.DataFrame(), "equity_curve": pd.DataFrame(),
                "config": asdict(cfg)}

    equity = cfg.starting_equity
    hwm = equity
    account_locked = ""          # §8 walkaway persists across sessions
    trades: list[Trade] = []
    blocked: list[Blocked] = []
    days: list[DayState] = []
    curve = [{"timestamp": None, "equity": equity, "event": "start"}]

    takes = logs[logs["verdict"] == "TAKE"].copy()
    takes["timestamp"] = pd.to_datetime(takes["timestamp"], utc=True)

    for session in sorted(logs["session"].unique()):
        day_takes = takes[takes["session"] == session].sort_values("timestamp")
        day = DayState(date=str(session), start_equity=equity, peak_equity=equity)
        if account_locked:
            # §8's 20% drawdown walkaway is not a daily latch — it stops the
            # account until a human resets it. Releasing it overnight would
            # let the worst drawdown of the run trade straight through.
            day.locked, day.lock_reason = True, account_locked
        open_until: pd.Timestamp | None = None

        for _, row in day_takes.iterrows():
            ts = row["timestamp"]

            key = (row["symbol"], str(session))
            bars_for_row = bars_by_key.get(key)

            def _block(reason: str, detail: str) -> None:
                r, pnl = _opportunity_cost(bars_for_row, int(row["cursor"]), row,
                                           equity, cfg)
                blocked.append(Blocked(day.date, row["symbol"], ts, reason, detail,
                                       would_be_r=r, would_be_pnl=pnl))

            if day.locked:
                _block(BLOCK_RISK_GATE, day.lock_reason)
                continue
            if day.trades >= cfg.max_trades_per_day:
                _block(BLOCK_MAX_TRADES,
                       f"{day.trades} taken (§7 cap {cfg.max_trades_per_day})")
                continue
            if cfg.one_position_at_a_time and open_until is not None and ts <= open_until:
                _block(BLOCK_POSITION_OPEN, f"position open until {open_until:%H:%M}")
                continue

            entry, stop = float(row["entry"]), float(row["stop"])
            risk = entry - stop
            bars = bars_for_row
            cursor = int(row["cursor"])
            visible = bars.iloc[:cursor + 1] if bars is not None else None
            shares, bound = replay.size_position(
                equity, entry, risk, visible, risk_pct=cfg.risk_pct,
                participation_pct=cfg.max_participation_pct)
            if shares <= 0:
                _block(BLOCK_NO_LIQUIDITY if bound == "liquidity" else BLOCK_NO_CASH,
                       f"equity ${equity:,.0f}, bound by {bound}, at ${entry:.2f}")
                continue
            if bars is None:
                continue

            sized = replay.Decision(
                timestamp=ts, symbol=row["symbol"], price=float(row["price"]),
                verdict="TAKE", reason=str(row["reason"]),
                entry=entry, stop=stop, target=float(row["target"]),
                target_source=str(row.get("target_source", "")),
                risk_per_share=risk, reward_risk=float(row["reward_risk"]),
                shares=shares, size_capped_by_cash=bound != "risk")
            out = replay.resolve(bars, cursor, sized)
            if not out.resolved:
                continue

            before = equity
            equity += out.net_pnl
            hwm = max(hwm, equity)
            day.peak_equity = max(day.peak_equity, equity)
            day.trades += 1
            day.consecutive_losses = 0 if out.net_pnl > 0 else day.consecutive_losses + 1

            exit_time = bars.index[min(cursor + out.bars_held - 1, len(bars) - 1)]
            open_until = exit_time
            trades.append(Trade(
                session=day.date, symbol=row["symbol"], entry_time=ts,
                exit_time=exit_time, entry=entry, stop=stop,
                target=float(row["target"]), shares=shares, risk_per_share=risk,
                reward_risk=float(row["reward_risk"]), r_multiple=out.r_multiple,
                net_pnl=out.net_pnl, exit_reason=out.exit_reason,
                mae_r=out.mae_r, mfe_r=out.mfe_r, bars_held=out.bars_held,
                equity_before=before, equity_after=equity,
                size_capped_by_cash=bound != "risk", size_bound_by=bound,
                confluence_count=int(row.get("confluence_count", 0)),
                support_reasons=str(row.get("support_reasons", ""))))
            curve.append({"timestamp": exit_time, "equity": equity,
                          "event": f"{row['symbol']} {out.exit_reason}"})

            day.locked, day.lock_reason = risk_check(day, equity, hwm, cfg)
            if day.locked:
                day.lock_time = exit_time
                if "drawdown" in day.lock_reason:
                    account_locked = day.lock_reason

        day.end_equity = equity
        days.append(day)

    return {
        "trades": pd.DataFrame([asdict(t) for t in trades]),
        "blocked": pd.DataFrame([asdict(b) for b in blocked]),
        "days": pd.DataFrame([asdict(d) for d in days]),
        "equity_curve": pd.DataFrame(curve),
        "config": asdict(cfg),
        "final_equity": equity,
        "return_pct": (equity - cfg.starting_equity) / cfg.starting_equity * 100.0,
    }
