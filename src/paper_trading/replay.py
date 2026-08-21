"""Blinded walk-forward replay of the strategy, one candle at a time.

The rule this module exists to enforce: at cursor `t`, nothing may be
computed from a bar later than `t`. Every function here takes a `visible`
frame that has already been truncated, and `assert_causal` proves the
truncation actually mattered.

Section numbers refer to knowledge-base/strategies/PARAMETERS.md.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd

from . import indicators

# --- §2 session window -------------------------------------------------
ENTRY_START = dt.time(9, 35)      # blackout ends
SESSION_END = dt.time(11, 30)     # hard stop

# --- §3 / §5 / §6 / §7 parameters (frozen before the run) --------------
CONFLUENCE_MIN = 2
TOLERANCE_PCT = 0.25
TOLERANCE_FLOOR = 0.01   # §3 tolerance_floor: spread; one tick without quote data
MAX_PULLBACK_INDEX = 2
STOP_MAX_DISTANCE = 0.20
MIN_REWARD_RISK = 2.0
RISK_PCT = 2.0
MAX_PARTICIPATION_PCT = 10.0   # share of the tape you can take without moving it
PARTICIPATION_WINDOW = 20      # bars of volume history used for the estimate

# --- execution model (matches the paper-trading broker) ----------------
COMMISSION_PER_SHARE = 0.005
SLIPPAGE_PER_SHARE = 0.02
MAX_SLIPPAGE = 0.15

UNTESTABLE = "UNTESTABLE"   # needs Level 2, which free data does not provide


class LookAheadError(AssertionError):
    """An indicator at the cursor changed when future bars were removed."""


# ------------------------------------------------------------------ blinding

def visible_slice(bars: pd.DataFrame, cursor: int) -> pd.DataFrame:
    """Bars 0..cursor inclusive — the only data a decision may consult."""
    if cursor < 0 or cursor >= len(bars):
        raise IndexError(f"cursor {cursor} outside 0..{len(bars) - 1}")
    return bars.iloc[:cursor + 1]


def resample_5m(visible: pd.DataFrame) -> pd.DataFrame:
    """5-minute frame from 1-minute bars; the final bar is in-progress.

    Because `visible` already ends at the cursor, the last bucket contains
    only elapsed minutes — which is exactly what a live screen shows.
    """
    if visible.empty:
        return visible.copy()
    out = visible.resample("5min", label="left", closed="left").agg(
        {"Open": "first", "High": "max", "Low": "min",
         "Close": "last", "Volume": "sum"}
    )
    return out.dropna(subset=["Close"])


def assert_causal(full: pd.DataFrame, cursor: int, *, rtol: float = 1e-9) -> None:
    """Prove EMA/VWAP/MACD at the cursor don't move when the future is cut.

    Raises LookAheadError on any mismatch. A passing assertion is not proof
    the *strategy* is causal — only that these indicators are.
    """
    visible = visible_slice(full, cursor)
    checks = {
        "ema9": (indicators.ema9(full["Close"]), indicators.ema9(visible["Close"])),
        "ema20": (indicators.ema20(full["Close"]), indicators.ema20(visible["Close"])),
        "vwap": (indicators.vwap(full), indicators.vwap(visible)),
        "macd_hist": (indicators.macd(full["Close"])["hist"],
                      indicators.macd(visible["Close"])["hist"]),
    }
    for name, (whole, truncated) in checks.items():
        a, b = float(whole.iloc[cursor]), float(truncated.iloc[-1])
        if not (np.isnan(a) and np.isnan(b)) and not np.isclose(a, b, rtol=rtol):
            raise LookAheadError(
                f"{name} at cursor {cursor}: full={a!r} truncated={b!r} — leak")


# ------------------------------------------------------------------ §7 sizing

def size_position(equity: float, entry: float, risk_per_share: float,
                  visible: pd.DataFrame | None = None, *,
                  risk_pct: float = RISK_PCT,
                  participation_pct: float = MAX_PARTICIPATION_PCT) -> tuple[int, str]:
    """Shares to trade, and which constraint bound. §7 plus two realities.

    §7 sizes purely from risk, which on an 8-cent stop asks a $100k account
    for ~25,000 shares of a $5 stock — the entire account, in one sub-20M
    float name. Two caps make the number fillable: cash (no margin) and
    participation (you cannot be most of the tape without becoming the
    price). §7 concedes the second itself: "fill quality degrades with size
    on sub-20M float. The edge does not scale linearly."
    """
    if risk_per_share <= 0 or entry <= 0:
        return 0, "invalid"
    # floor division on floats silently loses a share: 2000 // 0.10 == 19999.0
    by_risk = int((equity * risk_pct / 100.0) / risk_per_share + 1e-9)
    affordable = int(equity / entry + 1e-9)              # cash only, no margin
    caps = {"risk": by_risk, "cash": affordable}
    if visible is not None and len(visible) and participation_pct > 0:
        tape = float(visible["Volume"].tail(PARTICIPATION_WINDOW).median())
        if np.isfinite(tape) and tape > 0:
            caps["liquidity"] = int(tape * participation_pct / 100.0)
    shares = min(caps.values())
    bound = min(caps, key=lambda k: caps[k])
    return max(0, shares), bound


# ------------------------------------------------------------------ §3 support

def swing_highs(visible: pd.DataFrame, left: int = 2, right: int = 2) -> list[float]:
    """Confirmed local highs. Only highs with `right` bars after them count,
    so a pivot is never claimed before the market confirmed it."""
    highs = visible["High"].to_numpy()
    out = []
    for i in range(left, len(highs) - right):
        window = highs[i - left:i + right + 1]
        if highs[i] == window.max() and (window.argmax() == left):
            out.append(float(highs[i]))
    return out


def support_reasons(price: float, visible: pd.DataFrame,
                    tolerance_pct: float = TOLERANCE_PCT,
                    tolerance_floor: float = TOLERANCE_FLOOR) -> list[str]:
    """Which of the §3 confluence components sit at `price`.

    §3 floors the tolerance at the spread width. Free OHLCV carries no
    quotes, so one tick stands in — without it a $2.00 stock gets a
    half-cent window and no level can match except by exact equality,
    making the gate unreachable across the bottom of the §1 price range.
    """
    if visible.empty or not np.isfinite(price):
        return []
    tol = max(abs(price) * tolerance_pct / 100.0, tolerance_floor)
    close = visible["Close"]
    reasons = []

    if abs(price - round(price * 2) / 2) <= tol:
        reasons.append("whole_half_dollar")
    for name, series in (("ema9", indicators.ema9(close)),
                         ("ema20", indicators.ema20(close)),
                         ("vwap", indicators.vwap(visible))):
        val = float(series.iloc[-1])
        if np.isfinite(val) and abs(price - val) <= tol:
            reasons.append(name)
    if len(close) >= 200:
        ma200 = float(close.rolling(200).mean().iloc[-1])
        if np.isfinite(ma200) and abs(price - ma200) <= tol:
            reasons.append("ma200")
    # flipped level: an earlier confirmed high, now at or below price
    for high in swing_highs(visible.iloc[:-1]):
        if abs(price - high) <= tol and price >= high - tol:
            reasons.append("flipped_level")
            break
    return reasons


# ------------------------------------------------------------------ §3 pullback

@dataclass
class Pullback:
    """State of the current impulse/pullback leg at the cursor."""
    in_pullback: bool = False
    index: int = 0             # 1st, 2nd, 3rd... pullback of this move
    length: int = 0            # candles in the current dip
    low: float = float("nan")  # dip low -> §5 stop
    impulse_volume: float = float("nan")
    pullback_volume: float = float("nan")
    just_resolved: bool = False   # the trigger candle broke out of this dip


def detect_pullback(visible: pd.DataFrame) -> Pullback:
    """Walk the visible bars and report the leg the cursor sits in.

    Three resets keep the §3 counter meaning "1st or 2nd pullback of *this*
    move" rather than "dips so far today":

    - a new high of day starts a new leg, so earlier dips (premarket noise
      included) stop counting against it;
    - losing VWAP is a §5 hard invalidation — the move is over;
    - closing under the previous dip low breaks the leg.

    Without them the index climbs all session and the gate can never open.

    The §4 trigger candle is also, by definition, the candle that ends the
    pullback: at the moment of entry the dip is already over. The dip it
    broke out of is reported with `just_resolved=True`, carrying its own
    index, so the §3 volume test still has something to measure.
    """
    if len(visible) < 3:
        return Pullback()

    high = visible["High"].to_numpy()
    low = visible["Low"].to_numpy()
    close = visible["Close"].to_numpy()
    vwap = indicators.vwap(visible).to_numpy()
    last = len(visible) - 1

    idx = 0                       # pullbacks in the current leg
    in_pb = False
    pb_start = 0
    impulse_start = 0
    leg_low = -np.inf             # low of the last completed dip
    hod = float(high[0])
    resolved: tuple[int, int, int, int] | None = None   # start, end, imp, index

    for i in range(1, len(visible)):
        if (np.isfinite(vwap[i]) and close[i] < vwap[i]) or close[i] < leg_low:
            idx, in_pb, leg_low, impulse_start = 0, False, -np.inf, i
            resolved, hod = None, max(hod, float(high[i]))
            continue

        new_hod = high[i] > hod
        if high[i] > high[i - 1]:                  # impulse continues
            if in_pb:                              # ...and the dip resolves
                leg_low = float(low[pb_start:i].min())
                resolved = (pb_start, i, impulse_start, idx)
                in_pb = False
                impulse_start = i
        elif not in_pb:                            # a new dip begins
            in_pb, pb_start = True, i
            idx += 1

        if new_hod:                                # new leg — dips start over
            idx, hod = 0, float(high[i])

    if in_pb:
        dip_start, dip_end, imp_start, index = pb_start, len(visible), impulse_start, idx
        just_resolved = False
    elif resolved and resolved[1] == last:         # the cursor is the trigger
        dip_start, dip_end, imp_start, index = resolved
        just_resolved = True
    else:
        return Pullback(in_pullback=False, index=idx, length=0)

    dip = visible.iloc[dip_start:dip_end]
    impulse = visible.iloc[imp_start:dip_start]
    return Pullback(
        in_pullback=in_pb,
        index=index,
        length=len(dip),
        low=float(low[dip_start:dip_end].min()),
        impulse_volume=float(impulse["Volume"].mean()) if len(impulse) else float("nan"),
        pullback_volume=float(dip["Volume"].mean()),
        just_resolved=just_resolved,
    )


# ------------------------------------------------------------------ decision

@dataclass
class Decision:
    timestamp: pd.Timestamp
    symbol: str
    price: float
    verdict: str                       # TAKE | SKIP
    reason: str
    # §3 gate, each evaluated independently
    macd_positive: bool = False
    above_vwap: bool = False
    above_ema9: bool = False
    pullback_volume_lighter: bool = False
    pullback_index_ok: bool = False
    confluence_count: int = 0
    at_support: bool = False
    trigger: bool = False
    tape_green: str = UNTESTABLE
    no_seller_wall: str = UNTESTABLE
    # order (§4/§5/§6/§7), populated when the trigger fires
    entry: float = float("nan")
    stop: float = float("nan")
    target: float = float("nan")
    target_source: str = ""
    risk_per_share: float = float("nan")
    reward_risk: float = float("nan")
    shares: int = 0
    size_capped_by_cash: bool = False
    size_bound_by: str = ""
    support_reasons: str = ""


def evaluate(visible: pd.DataFrame, symbol: str, *,
             equity: float = 25_000.0,
             tolerance_pct: float = TOLERANCE_PCT) -> Decision:
    """Evaluate the §3 gate and §4 trigger at the cursor. No future access."""
    bar = visible.iloc[-1]
    ts, price = visible.index[-1], float(bar["Close"])
    close = visible["Close"]

    d = Decision(timestamp=ts, symbol=symbol, price=price,
                 verdict="SKIP", reason="")

    hist = float(indicators.macd(close)["hist"].iloc[-1])
    vwap_now = float(indicators.vwap(visible).iloc[-1])
    ema9_now = float(indicators.ema9(close).iloc[-1])
    d.macd_positive = bool(np.isfinite(hist) and hist > 0)
    d.above_vwap = bool(np.isfinite(vwap_now) and price > vwap_now)
    d.above_ema9 = bool(np.isfinite(ema9_now) and price > ema9_now)

    pb = detect_pullback(visible)
    d.pullback_index_ok = 1 <= pb.index <= MAX_PULLBACK_INDEX
    d.pullback_volume_lighter = bool(
        np.isfinite(pb.pullback_volume) and np.isfinite(pb.impulse_volume)
        and pb.pullback_volume < pb.impulse_volume)

    dip_low = pb.low if np.isfinite(pb.low) else float(bar["Low"])
    reasons = support_reasons(dip_low, visible, tolerance_pct)
    d.confluence_count = len(reasons)
    d.at_support = len(reasons) >= CONFLUENCE_MIN
    d.support_reasons = "|".join(reasons)

    # §4: the trigger is this candle taking out the prior candle's high
    prior_high = float(visible["High"].iloc[-2])
    d.trigger = bool(float(bar["High"]) > prior_high)

    gate = {
        "macd_hist<=0": d.macd_positive,
        "price<=vwap": d.above_vwap,
        "price<=ema9": d.above_ema9,
        "pullback_volume>=impulse": d.pullback_volume_lighter,
        f"pullback_index>{MAX_PULLBACK_INDEX}": d.pullback_index_ok,
        "no_confluence": d.at_support,
        "no_trigger": d.trigger,
    }
    failed = [name for name, ok in gate.items() if not ok]
    if failed:
        d.reason = "gate: " + ",".join(failed)
        return d

    # §4 entry: the break of the prior high, plus slippage (capped §4)
    d.entry = prior_high + min(SLIPPAGE_PER_SHARE, MAX_SLIPPAGE)
    d.stop = dip_low                                    # §5
    d.risk_per_share = d.entry - d.stop
    if d.risk_per_share <= 0:
        d.reason = "stop above entry"
        return d
    if d.risk_per_share > STOP_MAX_DISTANCE:            # §5 never widen
        d.reason = f"stop distance {d.risk_per_share:.3f} > {STOP_MAX_DISTANCE}"
        return d

    hod = float(visible["High"].max())                  # §6 target_1
    if hod > d.entry:
        d.target, d.target_source = hod, "hod_retest"
    else:
        d.target, d.target_source = d.entry + 2 * d.risk_per_share, "2R_fallback"
    d.reward_risk = (d.target - d.entry) / d.risk_per_share
    if d.reward_risk < MIN_REWARD_RISK:                 # §6
        d.reason = f"reward:risk {d.reward_risk:.2f} < {MIN_REWARD_RISK}"
        return d

    d.shares, d.size_bound_by = size_position(equity, d.entry, d.risk_per_share,
                                              visible)          # §7
    d.size_capped_by_cash = d.size_bound_by != "risk"
    if d.shares <= 0:
        d.reason = "size rounds to zero"
        return d

    d.verdict = "TAKE"
    d.reason = f"all testable gates pass ({d.support_reasons})"
    return d


# ------------------------------------------------------------------ outcome

@dataclass
class Outcome:
    resolved: bool = False
    exit_price: float = float("nan")
    exit_reason: str = ""
    r_multiple: float = float("nan")
    net_pnl: float = float("nan")
    mae_r: float = float("nan")
    mfe_r: float = float("nan")
    bars_held: int = 0


def resolve(future: pd.DataFrame, d: Decision) -> Outcome:
    """Manage the position on bars strictly after the entry candle (§5/§6).

    Half the position leaves at target_1 (§6 scale_1_pct), the stop moves to
    breakeven after that scale (§5), and the remainder exits on the first
    hard-exit signal or the stop. Costs: commission + slippage on every fill.
    """
    if future.empty:
        return Outcome()

    risk, entry = d.risk_per_share, d.entry
    stop, scaled = d.stop, False
    mae = mfe = 0.0
    vwap_s = indicators.vwap(future)
    hist_s = indicators.macd(future["Close"])["hist"]
    realized = 0.0          # R banked by the scaled half
    prior_low = float(future["Low"].iloc[0])

    for i in range(len(future)):
        bar = future.iloc[i]
        mae = min(mae, (float(bar["Low"]) - entry) / risk)
        mfe = max(mfe, (float(bar["High"]) - entry) / risk)

        if float(bar["Low"]) <= stop:                    # stop first: worst case
            fill = stop - SLIPPAGE_PER_SHARE
            r = realized + (1 - 0.5 * scaled) * (fill - entry) / risk
            return _outcome(d, fill, "stop" if not scaled else "breakeven_stop",
                            r, mae, mfe, i + 1)

        if not scaled and float(bar["High"]) >= d.target:
            fill = d.target - SLIPPAGE_PER_SHARE
            realized = 0.5 * (fill - entry) / risk
            scaled, stop = True, entry                   # §5 breakeven

        exit_reason = _hard_exit(bar, future, i, prior_low,
                                 float(vwap_s.iloc[i]), float(hist_s.iloc[i]))
        prior_low = float(bar["Low"])
        if exit_reason:
            fill = float(bar["Close"]) - SLIPPAGE_PER_SHARE
            r = realized + (1 - 0.5 * scaled) * (fill - entry) / risk
            return _outcome(d, fill, exit_reason, r, mae, mfe, i + 1)

    last = float(future["Close"].iloc[-1]) - SLIPPAGE_PER_SHARE
    r = realized + (1 - 0.5 * scaled) * (last - entry) / risk
    return _outcome(d, last, "session_end", r, mae, mfe, len(future))


def _hard_exit(bar, future, i, prior_low, vwap_now, hist_now) -> str:
    """§6 hard exits, in the order they invalidate the thesis."""
    if float(bar["Low"]) < prior_low and i > 0:
        return "first_candle_new_low"
    if np.isfinite(hist_now) and hist_now < 0:
        return "macd_negative"
    if np.isfinite(vwap_now) and float(bar["Close"]) < vwap_now:
        return "vwap_break"
    red = float(bar["Close"]) < float(bar["Open"])
    avg_vol = float(future["Volume"].iloc[:i + 1].mean())
    if red and np.isfinite(avg_vol) and float(bar["Volume"]) > 2 * avg_vol:
        return "high_volume_red"
    return ""


def _outcome(d: Decision, fill: float, reason: str, r: float,
             mae: float, mfe: float, bars: int) -> Outcome:
    commission = COMMISSION_PER_SHARE * d.shares * 2
    net = r * d.risk_per_share * d.shares - commission
    return Outcome(resolved=True, exit_price=fill, exit_reason=reason,
                   r_multiple=r, net_pnl=net, mae_r=mae, mfe_r=mfe,
                   bars_held=bars)


# ------------------------------------------------------------------ session

def decision_window(bars: pd.DataFrame) -> pd.DataFrame:
    """§2: entries only between 09:35 and the 11:30 hard stop."""
    if bars.empty:
        return bars
    t = bars.index.time
    return bars[(t >= ENTRY_START) & (t <= SESSION_END)]


def replay_session(bars: pd.DataFrame, symbol: str, *,
                   equity: float = 25_000.0,
                   tolerance_pct: float = TOLERANCE_PCT,
                   check_causality: bool = True) -> pd.DataFrame:
    """Walk one session candle by candle; one row per decision.

    SKIP decisions whose trigger fired are resolved counterfactually, so
    recall is measurable and not just precision.
    """
    bars = bars.sort_index()
    window = decision_window(bars)
    if window.empty:
        return pd.DataFrame()

    positions = {ts: i for i, ts in enumerate(bars.index)}
    rows = []
    for ts in window.index:
        cursor = positions[ts]
        if cursor < 2:
            continue
        if check_causality:
            assert_causal(bars, cursor)
        visible = visible_slice(bars, cursor)
        d = evaluate(visible, symbol, equity=equity, tolerance_pct=tolerance_pct)

        row = asdict(d)
        row["cursor"] = cursor
        # counterfactual: resolve anything that triggered, taken or not
        if d.trigger and np.isfinite(d.entry) and d.shares > 0:
            out = resolve(bars.iloc[cursor + 1:], d)
        elif d.trigger:
            out = _counterfactual(bars, cursor, d, equity)
        else:
            out = Outcome()
        row.update({f"outcome_{k}": v for k, v in asdict(out).items()})
        rows.append(row)

    return pd.DataFrame(rows)


def _counterfactual(bars: pd.DataFrame, cursor: int, d: Decision,
                    equity: float) -> Outcome:
    """What a SKIP would have done, priced by the same §4/§5 rules."""
    visible = visible_slice(bars, cursor)
    prior_high = float(visible["High"].iloc[-2])
    pb = detect_pullback(visible)
    stop = pb.low if np.isfinite(pb.low) else float(visible["Low"].iloc[-1])
    entry = prior_high + SLIPPAGE_PER_SHARE
    risk = entry - stop
    if risk <= 0:
        return Outcome()
    shadow = Decision(timestamp=d.timestamp, symbol=d.symbol, price=d.price,
                      verdict="SKIP", reason="counterfactual",
                      entry=entry, stop=stop,
                      target=entry + 2 * risk, target_source="2R_counterfactual",
                      risk_per_share=risk,
                      shares=max(1, int((equity * RISK_PCT / 100.0) // risk)))
    return resolve(bars.iloc[cursor + 1:], shadow)


# ------------------------------------------------------------------ scoring

def score(log: pd.DataFrame) -> dict:
    """Confusion matrix over decisions, plus the §9 metrics."""
    if log.empty:
        return {"n_decisions": 0, "n_resolved": 0, "note": "no decisions"}

    took = log["verdict"] == "TAKE"
    resolved = log["outcome_resolved"].fillna(False).astype(bool)
    won = log["outcome_r_multiple"] > 0

    tp = int((took & resolved & won).sum())
    fp = int((took & resolved & ~won).sum())
    fn = int((~took & resolved & won).sum())
    tn = int((~took & resolved & ~won).sum())

    taken_r = log.loc[took & resolved, "outcome_r_multiple"]
    out = {
        "n_decisions": int(len(log)),
        "n_resolved": int(resolved.sum()),
        "n_trades": int((took & resolved).sum()),
        "true_positive": tp, "false_positive": fp,
        "false_negative": fn, "true_negative": tn,
        "precision": tp / (tp + fp) if (tp + fp) else float("nan"),
        "recall": tp / (tp + fn) if (tp + fn) else float("nan"),
        "win_rate": tp / (tp + fp) if (tp + fp) else float("nan"),
        "expectancy_r": float(taken_r.mean()) if len(taken_r) else float("nan"),
        "net_pnl": float(log.loc[took & resolved, "outcome_net_pnl"].sum()),
        "breakeven_win_rate": 1 / (1 + MIN_REWARD_RISK),   # §9
    }
    out["clears_breakeven"] = bool(
        np.isfinite(out["win_rate"]) and out["win_rate"] > out["breakeven_win_rate"])
    out["significant"] = out["n_trades"] >= 20
    return out


def baseline_buy_hold(bars: pd.DataFrame) -> dict:
    """§12 baseline: buy the 09:35 close, sell at the 11:30 stop."""
    window = decision_window(bars)
    if len(window) < 2:
        return {"baseline": "buy_hold", "return_pct": float("nan")}
    entry = float(window["Close"].iloc[0]) + SLIPPAGE_PER_SHARE
    exit_ = float(window["Close"].iloc[-1]) - SLIPPAGE_PER_SHARE
    return {"baseline": "buy_hold", "entry": entry, "exit": exit_,
            "return_pct": (exit_ - entry) / entry * 100.0}


def baseline_random(bars: pd.DataFrame, *, n: int = 20, seed: int = 0,
                    stop_distance: float = 0.10) -> dict:
    """§12 control: random entries, same 2R bracket, same costs."""
    window = decision_window(bars)
    positions = {ts: i for i, ts in enumerate(bars.index)}
    candidates = [positions[ts] for ts in window.index if positions[ts] < len(bars) - 2]
    if not candidates:
        return {"baseline": "random", "n": 0, "expectancy_r": float("nan")}

    rng = np.random.default_rng(seed)
    picks = rng.choice(candidates, size=min(n, len(candidates)), replace=False)
    results = []
    for cursor in picks:
        entry = float(bars["Close"].iloc[cursor]) + SLIPPAGE_PER_SHARE
        d = Decision(timestamp=bars.index[cursor], symbol="RANDOM",
                     price=entry, verdict="TAKE", reason="random control",
                     entry=entry, stop=entry - stop_distance,
                     target=entry + 2 * stop_distance, target_source="2R",
                     risk_per_share=stop_distance, shares=100)
        out = resolve(bars.iloc[cursor + 1:], d)
        if out.resolved:
            results.append(out.r_multiple)
    return {"baseline": "random", "n": len(results),
            "expectancy_r": float(np.mean(results)) if results else float("nan"),
            "win_rate": float(np.mean([r > 0 for r in results])) if results else float("nan")}


def sweep_tolerance(bars: pd.DataFrame, symbol: str,
                    tolerances=(0.10, 0.25, 0.50), **kwargs) -> pd.DataFrame:
    """§12.3: run the free parameter across its range. Do not pick a winner.

    If the sign of expectancy flips across the sweep, the finding is noise
    and must be discarded rather than reported at its best cell.
    """
    rows = []
    for tol in tolerances:
        s = score(replay_session(bars, symbol, tolerance_pct=tol, **kwargs))
        rows.append({"tolerance_pct": tol, **s})
    out = pd.DataFrame(rows)
    if "expectancy_r" in out:
        signs = {np.sign(v) for v in out["expectancy_r"].dropna() if v != 0}
        out.attrs["sign_flips"] = len(signs) > 1
    return out
