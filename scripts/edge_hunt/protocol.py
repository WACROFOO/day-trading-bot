"""The protocol of `research/edge-hunt/PREREGISTRATION.md`, in code.

  * SPLIT        train 2016-2022 · validation 2023 · holdout 2024-2026
  * REGISTRY     every configuration a family evaluates is counted
  * HOLDOUT      `open_holdout(family, …)` is the ONLY way to get holdout rows,
                 and it refuses a second opening of the same family — the
                 ledger (`research/edge-hunt/holdout_ledger.jsonl`) is committed,
                 so an opening cannot be quietly undone
  * ADOPTION     the five-part rule, with the lower bound Bonferroni-corrected
                 over the number of families the preregistration allows
  * BASELINE     random entry on the same symbol-days, same window, same stop
                 distance, same exit, same costs
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "research" / "edge-hunt" / "holdout_ledger.jsonl"
REGISTRY = ROOT / "research" / "edge-hunt" / "results" / "registry.jsonl"

# Fixed before the first run (PREREGISTRATION.md §3).
FAMILIES = ("F1-selection", "F2-premarket", "F3-micro10s", "F4-exits-sizing", "F5-new", "F6-combined")
ALPHA = 0.05
MIN_TRADES = 200
MIN_YEARS_POSITIVE = 2
HOLDOUT_YEARS = ("2024", "2025", "2026")


class HoldoutAlreadyOpened(RuntimeError):
    pass


def _head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, timeout=10).stdout.strip()
    except Exception:                                                # noqa: BLE001
        return "?"


def config_hash(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()[:12]


def ledger_entries(path: Path = LEDGER) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def opened(family: str, path: Path = LEDGER) -> dict | None:
    return next((e for e in ledger_entries(path) if e["family"] == family), None)


def open_holdout(family: str, config: dict, n_configs: int, train: dict, valid: dict,
                 path: Path = LEDGER) -> dict:
    """Record the opening, then allow it. Refuses a family already opened."""
    if family not in FAMILIES:
        raise ValueError(f"{family} is not a preregistered family")
    prior = opened(family, path)
    if prior is not None:
        raise HoldoutAlreadyOpened(f"{family} opened its holdout at {prior['utc']} (config {prior['hash']}); "
                                   "the preregistration allows one opening per family")
    entry = {"family": family, "hash": config_hash(config), "config": config, "n_configs_tried": n_configs,
             "train": train, "valid": valid, "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "git": _head()}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    return entry


def record_result(family: str, result: dict, path: Path = LEDGER) -> None:
    with path.open("a") as f:
        f.write(json.dumps({"family": family + ":result", "result": result,
                            "utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}, default=str) + "\n")


# v1 = the first search (2026-09-26), before the framework review; v2 = after its fixes (fill-bar
# stop at the stop, A10 TTL in minutes, cap-return fills, mean spread). Both runs count as tried.
RUN_TAG = "v2"


def register(family: str, rows: list[dict], path: Path = REGISTRY) -> None:
    """Append every configuration evaluated on train/validation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        for r in rows:
            f.write(json.dumps({"family": family, "run": RUN_TAG, **r}, default=str) + "\n")


def n_registered(family: str, path: Path = REGISTRY) -> int:
    if not path.exists():
        return 0
    return len({(json.loads(x).get("hash")) for x in path.read_text().splitlines()
                if x.strip() and json.loads(x)["family"] == family})


# ------------------------------------------------------------------ statistics
def day_bootstrap(days: np.ndarray, values: np.ndarray, draws: int = 20000, seed: int = 20260926) -> np.ndarray:
    """Means of `values` under resampling whole DAYS with replacement."""
    if len(values) == 0:
        return np.array([np.nan])
    uniq, inv = np.unique(days, return_inverse=True)
    s = np.bincount(inv, weights=values); n = np.bincount(inv).astype(float)
    rng = np.random.default_rng(seed)
    out = np.empty(draws)
    step = 2000
    for a in range(0, draws, step):
        b = min(draws, a + step)
        w = rng.multinomial(len(uniq), np.full(len(uniq), 1 / len(uniq)), size=b - a).astype(float)
        out[a:b] = (w @ s) / np.maximum(w @ n, 1)
    return out


def lower_bound(days, values, alpha: float, draws: int = 20000) -> float:
    return float(np.quantile(day_bootstrap(np.asarray(days), np.asarray(values, float), draws), alpha))


def corrected_alpha() -> float:
    """Two-sided 95 %, Bonferroni over every family the preregistration allows."""
    return ALPHA / 2 / len(FAMILIES)


def summary(values, days=None) -> dict:
    v = np.asarray(values, float)
    if len(v) == 0:
        return {"n": 0}
    wins, losses = v[v > 0], v[v <= 0]
    avg_loss = float(-losses.mean()) if len(losses) else float("nan")
    out = {"n": int(len(v)), "mean": round(float(v.mean()), 4), "total": round(float(v.sum()), 2),
           "win_rate": round(float((v > 0).mean()), 4),
           "avg_win": round(float(wins.mean()), 4) if len(wins) else None,
           "avg_loss": round(avg_loss, 4),
           # Ross's ratios (PARAMETERS.md §9) are in units of his AVERAGE LOSS, not of planned risk
           "win_loss_ratio": round(float(wins.mean()) / avg_loss, 3) if len(wins) and avg_loss > 0 else None,
           "exp_per_avg_loss": round(float(v.mean()) / avg_loss, 3) if avg_loss > 0 else None}
    if days is not None and len(v) >= 5:
        out["lb95"] = round(lower_bound(days, v, 0.025), 4)
    return out


def adoption(values, days, random_diff=None) -> dict:
    """The five-part rule on the holdout. `values`: net R per portfolio trade;
    `random_diff`: per-trade (config − random baseline) on the same trades."""
    v = np.asarray(values, float); d = np.asarray(days)
    years = defaultdict(list)
    for x, day in zip(v, d):
        years[str(day)[:4]].append(x)
    yr = {y: (round(float(np.mean(years[y])), 4), len(years[y])) for y in HOLDOUT_YEARS if years.get(y)}
    a = corrected_alpha()
    lb = lower_bound(d, v, a) if len(v) >= 5 else float("nan")
    res = {"n": int(len(v)), "mean": round(float(v.mean()), 4) if len(v) else None,
           "lb_corrected": round(lb, 4), "alpha_one_sided": a, "years": yr}
    checks = {"1 positive net mean": bool(len(v) and v.mean() > 0),
              "2 corrected lower bound > 0": bool(lb > 0),
              f"3 at least {MIN_TRADES} trades": bool(len(v) >= MIN_TRADES),
              f"4 positive in {MIN_YEARS_POSITIVE} of 3 years": sum(1 for y in yr.values() if y[0] > 0) >= MIN_YEARS_POSITIVE}
    if random_diff is not None:
        rd = np.asarray(random_diff, float)
        ok = ~np.isnan(rd)
        lb_r = lower_bound(d[ok], rd[ok], 0.025) if ok.sum() >= 5 else float("nan")
        res["vs_random_mean"] = round(float(np.nanmean(rd)), 4)
        res["vs_random_lb95"] = round(lb_r, 4)
        checks["5 beats random entry on the same names"] = bool(lb_r > 0)
    else:
        checks["5 beats random entry on the same names"] = False
    res["checks"] = checks
    res["adopted"] = all(checks.values())
    return res


# ------------------------------------------------------------------ portfolio
def one_position(trades: list[dict]) -> list[dict]:
    """The bot's constraint (runner.max_positions = 1): take a trade only when
    nothing is open. `trades` need day, fill_min, exit_min; sorted here."""
    out, busy_until = [], {}
    for t in sorted(trades, key=lambda t: (t["day"], t["fill_min"], t.get("sym", ""))):
        if t["fill_min"] <= busy_until.get(t["day"], -1):
            continue
        out.append(t)
        busy_until[t["day"]] = t["exit_min"]
    return out
