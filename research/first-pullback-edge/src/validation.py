"""Chronological splits, ablation arithmetic, rejected-trade analysis, filter
overlap, placebos and baselines (brief sections 7, 19, 20, 21, 24, 25).

Nothing here shuffles. Every split is a cut on the ordered list of sessions,
because a trade on 2026-08-14 that lands in a "training set" alongside
2026-08-18 has already leaked the regime.
"""
from __future__ import annotations

import datetime as dt
import random
from collections import defaultdict

from .metrics import clustered_bootstrap, core_metrics, _mean


def chronological_splits(days: list[str], dev=0.45, val=0.25, hold=0.30) -> dict:
    """Ordered cut into development / validation / untouched holdout."""
    d = sorted(set(days))
    n = len(d)
    i1 = int(n * dev)
    i2 = int(n * (dev + val))
    return dict(development=d[:i1], validation=d[i1:i2], holdout=d[i2:],
                n_sessions=n,
                boundaries=dict(dev_end=d[i1 - 1] if i1 else None,
                                val_end=d[i2 - 1] if i2 > i1 else None))


def walk_forward_folds(days: list[str], train_frac=0.5, val_frac=0.2,
                       n_folds=4) -> list[dict]:
    """Rolling chronological folds. Returns [] when there is not enough data
    to make folds that mean anything - which is the honest answer on a short
    sample, not a reason to shrink the folds until some exist."""
    d = sorted(set(days))
    n = len(d)
    if n < n_folds * 10:
        return []
    fold_len = n // n_folds
    out = []
    for k in range(n_folds):
        end = fold_len * (k + 1)
        tr = int(end * train_frac)
        va = int(end * (train_frac + val_frac))
        out.append(dict(fold=k, train=d[:tr], validation=d[tr:va], test=d[va:end]))
    return out


def filter_setup(setup_row: dict, gate: str) -> bool:
    return bool(setup_row.get("gates", {}).get(gate, True))


def ablation_marginals(per_variant: dict[str, list[dict]], order: list[str]) -> list[dict]:
    """B-A, C-B, D-C, E-D, F-E on expectancy, PF and drawdown."""
    rows = []
    for a, b in zip(order, order[1:]):
        ma, mb = core_metrics(per_variant.get(a, [])), core_metrics(per_variant.get(b, []))
        ca = clustered_bootstrap(per_variant.get(a, []))
        cb = clustered_bootstrap(per_variant.get(b, []))
        rows.append(dict(
            step=f"{b}-{a}",
            trades_a=ma.get("trades", 0), trades_b=mb.get("trades", 0),
            trades_removed=ma.get("trades", 0) - mb.get("trades", 0),
            exp_a=ma.get("expectancy_r"), exp_b=mb.get("expectancy_r"),
            exp_delta=(mb.get("expectancy_r", float("nan"))
                       - ma.get("expectancy_r", float("nan"))),
            pf_a=ma.get("profit_factor"), pf_b=mb.get("profit_factor"),
            dd_a=ma.get("max_dd_r"), dd_b=mb.get("max_dd_r"),
            dd_improved=(mb.get("max_dd_r", 0) or 0) > (ma.get("max_dd_r", 0) or 0),
            ci_a=f"[{ca['lo']:.3f},{ca['hi']:.3f}]" if ca["lo"] == ca["lo"] else "n/a",
            ci_b=f"[{cb['lo']:.3f},{cb['hi']:.3f}]" if cb["lo"] == cb["lo"] else "n/a",
            ci_width_a=(ca["hi"] - ca["lo"]) if ca["lo"] == ca["lo"] else float("nan"),
            ci_width_b=(cb["hi"] - cb["lo"]) if cb["lo"] == cb["lo"] else float("nan"),
        ))
    return rows


def accepted_vs_rejected(trades_by_gate: dict[str, dict[str, list[dict]]]) -> list[dict]:
    """brief section 20. For each filter: what did it keep, what did it throw
    away, and did the two populations actually perform differently?

    `trades_by_gate[gate] = {"accepted": [...], "rejected": [...]}` where the
    rejected list holds the counterfactual outcome of setups the filter
    removed - traded under the same exit model, for research only.
    """
    rows = []
    for gate, d in trades_by_gate.items():
        acc, rej = d.get("accepted", []), d.get("rejected", [])
        ma, mr = core_metrics(acc), core_metrics(rej)
        ca, cr = clustered_bootstrap(acc), clustered_bootstrap(rej)
        rows.append(dict(
            gate=gate,
            n_accepted=ma.get("trades", 0), n_rejected=mr.get("trades", 0),
            exp_accepted=ma.get("expectancy_r"), exp_rejected=mr.get("expectancy_r"),
            win_accepted=ma.get("win_rate"), win_rejected=mr.get("win_rate"),
            ci_accepted=f"[{ca['lo']:.3f},{ca['hi']:.3f}]" if ca["lo"] == ca["lo"] else "n/a",
            ci_rejected=f"[{cr['lo']:.3f},{cr['hi']:.3f}]" if cr["lo"] == cr["lo"] else "n/a",
            winners_removed=sum(1 for t in rej if t["net_r"] > 0.05),
            losers_removed=sum(1 for t in rej if t["net_r"] < -0.05),
            separation=(ma.get("expectancy_r", float("nan"))
                        - mr.get("expectancy_r", float("nan"))),
        ))
    return rows


def gate_overlap(setups: list[dict], gates: list[str]) -> list[dict]:
    """brief section 21. Phi coefficient between every pair of gate decisions
    plus each gate's individual pass rate. Two filters that agree 95% of the
    time are one filter wearing two hats."""
    rows = []
    n = len(setups)
    if n == 0:
        return rows
    vec = {g: [1 if s["gates"].get(g, True) else 0 for s in setups] for g in gates}
    for i, g1 in enumerate(gates):
        for g2 in gates[i + 1:]:
            a, b = vec[g1], vec[g2]
            n11 = sum(1 for x, y in zip(a, b) if x and y)
            n10 = sum(1 for x, y in zip(a, b) if x and not y)
            n01 = sum(1 for x, y in zip(a, b) if not x and y)
            n00 = n - n11 - n10 - n01
            den = ((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00)) ** 0.5
            phi = ((n11 * n00 - n10 * n01) / den) if den > 0 else float("nan")
            rows.append(dict(gate_a=g1, gate_b=g2, phi=phi,
                             agree_pct=(n11 + n00) / n * 100.0,
                             pass_a=sum(a) / n * 100.0, pass_b=sum(b) / n * 100.0,
                             both_pass=n11, only_a=n10, only_b=n01, neither=n00))
    return rows


def parameter_neighbourhood(base: float, steps=(-0.15, -0.075, 0.0, 0.075, 0.15)) -> list[float]:
    """brief section 23: perturb, do not search. A robust rule shows a plateau
    across this neighbourhood; a fitted one shows a spike at the shipped value.
    """
    return [round(base * (1 + s), 6) for s in steps]


def placebo_shuffle_labels(trades: list[dict], gate: str, seed: int = 20260824) -> dict:
    """brief section 25. Reassign the filter's pass/fail labels at random,
    keeping the pass RATE, and re-measure the split. A real filter should beat
    its own shuffled twin; if it does not, the separation was arithmetic on
    noise."""
    rng = random.Random(seed)
    flags = [bool(t.get(f"gate_{gate}", True)) for t in trades]
    rng.shuffle(flags)
    acc = [t for t, f in zip(trades, flags) if f]
    rej = [t for t, f in zip(trades, flags) if not f]
    return dict(gate=gate, n_accepted=len(acc), n_rejected=len(rej),
                exp_accepted=core_metrics(acc).get("expectancy_r"),
                exp_rejected=core_metrics(rej).get("expectancy_r"),
                separation=(core_metrics(acc).get("expectancy_r", float("nan"))
                            - core_metrics(rej).get("expectancy_r", float("nan"))))


def regime_buckets(trades: list[dict]) -> list[dict]:
    """brief section 16's time-of-day cut. The market-environment cut needs an
    index series and is done separately in run.py when one is available."""
    windows = [("09:30-10:00", 9 * 60 + 30, 10 * 60),
               ("10:00-10:30", 10 * 60, 10 * 60 + 30),
               ("10:30-11:30", 10 * 60 + 30, 11 * 60 + 30),
               ("11:30-16:00", 11 * 60 + 30, 16 * 60),
               ("premarket", 4 * 60, 9 * 60 + 30)]
    out = []
    for name, lo, hi in windows:
        sel = []
        for t in trades:
            e = dt.datetime.fromisoformat(t["entry_et"])
            m = e.hour * 60 + e.minute
            if lo <= m < hi:
                sel.append(t)
        m = core_metrics(sel)
        m["window"] = name
        out.append(m)
    return out


def baseline_random_entry(bars_by_day: dict, params, cost, n_per_day: int = 1,
                          seed: int = 20260824) -> list[dict]:
    """brief section 24, baseline 1: a random entry minute in the early
    session on a qualifying candidate, same stop distance and same exit
    ladder. If the strategy cannot beat this, the pattern is not the edge.

    Implemented in run.py where the bar data and the execution model are both
    in scope; this function documents the contract and is exercised by tests.
    """
    raise NotImplementedError("driven from run.py::baseline_random")
