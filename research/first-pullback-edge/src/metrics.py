"""Performance metrics and confidence intervals (brief sections 13 and 14).

The only opinionated choice in here is the bootstrap. Trades from the same
session are not independent - one gap-and-go morning produces several
correlated setups on correlated names - so resampling individual trades
would produce confidence intervals that are too narrow, in the direction that
flatters the strategy. Everything below resamples DAYS with replacement and
keeps each day's trades together (a clustered / block bootstrap). Where a
trade-level bootstrap is also computed it is labelled as the optimistic one.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict


def _pct(xs: list[float], q: float) -> float:
    if not xs:
        return float("nan")
    s = sorted(xs)
    k = (len(s) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return s[int(k)] if lo == hi else s[lo] * (hi - k) + s[hi] * (k - lo)


def _mean(xs) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def _median(xs) -> float:
    return _pct(list(xs), 0.5)


def _stdev(xs) -> float:
    xs = list(xs)
    if len(xs) < 2:
        return float("nan")
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def core_metrics(trades: list[dict], be_band: float = 0.05) -> dict:
    """brief section 13. `be_band` is the |R| under which a trade is called
    breakeven rather than a win or a loss."""
    n = len(trades)
    if n == 0:
        return dict(trades=0)
    rs = [t["net_r"] for t in trades]
    pnl = [t["net_pnl"] for t in trades]
    wins = [r for r in rs if r > be_band]
    losses = [r for r in rs if r < -be_band]
    bes = [r for r in rs if abs(r) <= be_band]
    gross_profit = sum(p for p in pnl if p > 0)
    gross_loss = -sum(p for p in pnl if p < 0)
    mfes = [t["mfe_r"] for t in trades]
    maes = [t["mae_r"] for t in trades]

    daily = defaultdict(float)
    for t in trades:
        daily[t["day"]] += t["net_r"]
    dseries = [daily[d] for d in sorted(daily)]
    equity, peak, maxdd = 0.0, 0.0, 0.0
    for r in rs:
        equity += r
        peak = max(peak, equity)
        maxdd = min(maxdd, equity - peak)
    streak = worst_streak = 0
    for r in rs:
        streak = streak + 1 if r <= be_band else 0
        worst_streak = max(worst_streak, streak)

    weekly, monthly = defaultdict(float), defaultdict(float)
    for d, v in daily.items():
        y, m, dd = d.split("-")
        monthly[f"{y}-{m}"] += v
        import datetime as _dt
        weekly[_dt.date(int(y), int(m), int(dd)).strftime("%G-W%V")] += v

    downside = [min(0.0, r) for r in rs]
    return dict(
        trades=n,
        win_rate=len(wins) / n, loss_rate=len(losses) / n, be_rate=len(bes) / n,
        avg_r=_mean(rs), median_r=_median(rs),
        avg_winner_r=_mean(wins) if wins else float("nan"),
        median_winner_r=_median(wins) if wins else float("nan"),
        avg_loser_r=_mean(losses) if losses else float("nan"),
        median_loser_r=_median(losses) if losses else float("nan"),
        realized_rr=(_mean(wins) / abs(_mean(losses))) if wins and losses else float("nan"),
        profit_factor=(gross_profit / gross_loss) if gross_loss > 0 else float("inf"),
        gross_profit=gross_profit, gross_loss=gross_loss,
        net_pnl=sum(pnl), expectancy_r=_mean(rs),
        max_dd_r=maxdd,
        max_dd_pct=(maxdd / peak * 100.0) if peak > 0 else float("nan"),
        longest_losing_streak=worst_streak,
        worst_day_r=min(dseries) if dseries else float("nan"),
        worst_week_r=min(weekly.values()) if weekly else float("nan"),
        worst_month_r=min(monthly.values()) if monthly else float("nan"),
        stdev_r=_stdev(rs), downside_dev_r=_stdev(downside),
        avg_mfe_r=_mean(mfes), avg_mae_r=_mean(maes),
        median_mfe_r=_median(mfes), median_mae_r=_median(maes),
        pct_reach_0p5r=sum(1 for m in mfes if m >= 0.5) / n,
        pct_reach_1r=sum(1 for m in mfes if m >= 1.0) / n,
        pct_reach_2r=sum(1 for m in mfes if m >= 2.0) / n,
        pct_stopped_before_0p5r=sum(1 for t in trades
                                    if t["mfe_r"] < 0.5 and t["net_r"] <= -be_band) / n,
        ambiguous_share=sum(1 for t in trades if t["ambiguous"]) / n,
        halt_share=sum(1 for t in trades if t["halt_flag"]) / n,
        participation_capped_share=sum(1 for t in trades if t["participation_capped"]) / n,
        sessions=len(daily),
    )


def clustered_bootstrap(trades: list[dict], stat: str = "expectancy_r",
                        n_boot: int = 5000, seed: int = 20260824,
                        alpha: float = 0.05) -> dict:
    """Resample SESSIONS with replacement, keeping each session's trades
    together. This is the interval to quote (brief section 14)."""
    if not trades:
        return dict(estimate=float("nan"), lo=float("nan"), hi=float("nan"),
                    n_boot=0, method="day-clustered", days=0)
    by_day: dict[str, list[dict]] = defaultdict(list)
    for t in trades:
        by_day[t["day"]].append(t)
    days = list(by_day)
    rng = random.Random(seed)
    point = _statistic(trades, stat)
    draws = []
    for _ in range(n_boot):
        sample: list[dict] = []
        for _ in range(len(days)):
            sample.extend(by_day[days[rng.randrange(len(days))]])
        v = _statistic(sample, stat)
        if v == v and abs(v) != float("inf"):
            draws.append(v)
    if not draws:
        return dict(estimate=point, lo=float("nan"), hi=float("nan"),
                    n_boot=0, method="day-clustered", days=len(days))
    return dict(estimate=point, lo=_pct(draws, alpha / 2),
                hi=_pct(draws, 1 - alpha / 2), n_boot=len(draws),
                method="day-clustered", days=len(days))


def _statistic(trades: list[dict], stat: str) -> float:
    if not trades:
        return float("nan")
    rs = [t["net_r"] for t in trades]
    if stat in ("expectancy_r", "mean_r"):
        return _mean(rs)
    if stat == "win_rate":
        return sum(1 for r in rs if r > 0.05) / len(rs)
    if stat == "profit_factor":
        gp = sum(t["net_pnl"] for t in trades if t["net_pnl"] > 0)
        gl = -sum(t["net_pnl"] for t in trades if t["net_pnl"] < 0)
        return gp / gl if gl > 0 else float("inf")
    if stat == "mean_winner_r":
        w = [r for r in rs if r > 0.05]
        return _mean(w) if w else float("nan")
    if stat == "mean_loser_r":
        l = [r for r in rs if r < -0.05]
        return _mean(l) if l else float("nan")
    raise ValueError(stat)


def verdict(ci: dict, n: int, min_n: int = 100) -> str:
    """brief section 34's four-way classification, applied mechanically."""
    est, lo, hi = ci.get("estimate"), ci.get("lo"), ci.get("hi")
    if n == 0 or est != est:
        return "NO DATA"
    if n < min_n:
        return f"INSUFFICIENT SAMPLE (n={n} < {min_n})"
    if lo > 0:
        return "STRONG EVIDENCE OF EDGE"
    if hi < 0:
        return "NEGATIVE EDGE"
    if est > 0:
        return "POSSIBLE EDGE (CI spans zero)"
    return "NO DEMONSTRATED EDGE"


def by_bucket(trades: list[dict], key, buckets: list[tuple[str, float, float]]) -> list[dict]:
    """Group trades into named numeric buckets and metric each one."""
    out = []
    for name, lo, hi in buckets:
        sel = []
        for t in trades:
            v = key(t)
            if v is None or v != v:
                continue
            if lo <= v < hi:
                sel.append(t)
        m = core_metrics(sel)
        m["bucket"] = name
        out.append(m)
    return out


def account_simulation(trades: list[dict], equity0: float = 2000.0,
                       risk_pct: float = 2.0, max_position_value: float = 2000.0,
                       commission_per_order: float = 1.0) -> dict:
    """brief section 26. R performance and dollar performance are different
    things and this keeps them apart: the ledger's R is the strategy, this is
    what a $2,000 cash account would actually have done, compounding, with the
    position cap and the per-order toll applied at the size the account could
    afford at the time.
    """
    eq = equity0
    peak = equity0
    maxdd = 0.0
    curve = []
    skipped = 0
    for t in sorted(trades, key=lambda x: (x["day"], x["entry_ts"])):
        risk_budget = eq * risk_pct / 100.0
        rps = t["risk_per_share"]
        if rps <= 0:
            continue
        shares = min(int(risk_budget // rps), int(max_position_value // t["entry_fill"]),
                     t["filled_shares"])
        if shares < 1:
            skipped += 1
            continue
        scale = shares / t["filled_shares"] if t["filled_shares"] else 0.0
        pnl = (t["net_pnl"] + t["commissions"]) * scale - t["commissions"]
        eq += pnl
        peak = max(peak, eq)
        maxdd = min(maxdd, eq - peak)
        curve.append(round(eq, 2))
        if eq <= 0:
            break
    return dict(start_equity=equity0, end_equity=round(eq, 2),
                return_pct=round((eq / equity0 - 1) * 100.0, 2),
                max_dd_dollar=round(maxdd, 2),
                max_dd_pct=round(maxdd / peak * 100.0, 2) if peak > 0 else float("nan"),
                trades_taken=len(curve), trades_skipped_too_small=skipped,
                ruined=eq <= 0, curve=curve)
