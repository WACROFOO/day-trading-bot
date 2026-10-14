"""The protocol of `research/strategy-candidates/PREREGISTRATION.md` §6 and §8, in code.

  REGISTRY  every configuration evaluated is one JSON line: locally in
            `results/registry.jsonl` (git-ignored: the Mac cannot push) and, once a run
            comes back, in the committed `registry.jsonl`. A family's count is the number
            of distinct hashes in both, plus the prior reads recorded for it.
  LEDGER    `open_holdout` is the only way to holdout rows. It writes the opening before
            anything is read and refuses a second configuration for a family already
            opened in EITHER ledger; the same configuration may be re-read (deterministic).
  ADOPTION  criteria 1-7 on the holdout's one-position portfolio.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from candidates.data import ROOT
from candidates.rules import OPENABLE, ROUNDS

FOLDER = ROOT / "research" / "strategy-candidates"
RESULTS = FOLDER / "results"
COMMITTED_LEDGER = FOLDER / "holdout_ledger.jsonl"
LOCAL_LEDGER = RESULTS / "holdout_ledger.jsonl"
COMMITTED_REGISTRY = FOLDER / "registry.jsonl"
LOCAL_REGISTRY = RESULTS / "registry.jsonl"

# fixed before any run (PREREGISTRATION.md §6)
ALPHA = 0.05
MIN_TRAIN, MIN_VALID, MIN_HOLDOUT, MIN_YEARS_POSITIVE = 100, 30, 200, 2
HOLDOUT_YEARS = ("2024", "2025", "2026")
BORROW_MIN_PCT = 0.5
BORROW_SWEEP = (0.0, 0.25, 0.5, 1.0, 2.0)


class HoldoutAlreadyOpened(RuntimeError):
    pass


def corrected_alpha(n_families: int | None = None, family: str | None = None) -> float:
    """One-sided: 95 % two-sided, Bonferroni over the families allowed to open — those of the
    family's round (amendment 2026-10-14: round 1's three can no longer open)."""
    if n_families is None:
        rnd = next((r for r in ROUNDS if family in r), ROUNDS[0])
        n_families = len(rnd)
    return ALPHA / 2 / n_families


def head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, timeout=10).stdout.strip() or "?"
    except Exception:                                                    # noqa: BLE001
        return "?"


def config_hash(family: str, cfg: dict) -> str:
    return hashlib.sha256(json.dumps({"family": family, **cfg}, sort_keys=True, default=str).encode()).hexdigest()[:12]


def _lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------ the holdout ledger
def opened(family: str, ledgers=None) -> dict | None:
    # defaults resolve at call time, so a redirected ledger (a test, another machine) is the one read
    for p in ledgers or (COMMITTED_LEDGER, LOCAL_LEDGER):
        for e in _lines(Path(p)):
            if e.get("family") == family and "hash" in e:
                return e
    return None


def open_holdout(family: str, cfg: dict, n_configs: int, train: dict, valid: dict,
                 ledger: Path | None = None, ledgers=None) -> dict:
    """Record the opening, then allow it. Refuses another configuration of a family
    already opened in any ledger; returns the old entry, flagged, for the same one."""
    if family not in OPENABLE:
        raise ValueError(f"{family} is not allowed to open a holdout (PREREGISTRATION.md §6)")
    h = config_hash(family, cfg)
    ledger = Path(ledger or LOCAL_LEDGER)
    prior = opened(family, ledgers or (COMMITTED_LEDGER, ledger))
    if prior is not None:
        if prior["hash"] != h:
            raise HoldoutAlreadyOpened(f"{family} opened its holdout at {prior['utc']} for {prior['hash']}; "
                                       f"{h} can never be read on it (one opening per family)")
        return {**prior, "reread": True}
    entry = {"family": family, "hash": h, "config": cfg, "n_configs_tried": n_configs, "train": train,
             "valid": valid, "utc": utc_now(), "git": head()}
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    return entry


def record_result(family: str, result: dict, ledger: Path | None = None) -> None:
    ledger = Path(ledger or LOCAL_LEDGER)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a") as f:
        f.write(json.dumps({"family": family + ":result", "result": result, "utc": utc_now()}, default=str) + "\n")


# ------------------------------------------------------------------ the registry
def register(rows: list[dict], path: Path | None = None) -> None:
    path = Path(path or LOCAL_REGISTRY)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + "\n")


def n_configs(family: str, registries=None) -> int:
    """Distinct configurations of `family` ever evaluated, plus the prior reads that
    relate to it (rows carrying `n_configs` and `relates_to`)."""
    hashes, prior = set(), 0
    for p in registries or (COMMITTED_REGISTRY, LOCAL_REGISTRY):
        for r in _lines(Path(p)):
            if r.get("family") == family and "hash" in r:
                hashes.add(r["hash"])
            elif r.get("relates_to") == family and "n_configs" in r:
                prior += int(r["n_configs"])
    return len(hashes) + prior


# ------------------------------------------------------------------ the portfolio
def portfolio(trades: list[dict], done_after_loss: bool = False) -> list[dict]:
    """One position at a time across names (the bot's max_positions = 1): a trade filled
    at or before the open one's exit minute is not taken. `done_after_loss` (L3): no new
    trade on a day after a losing one."""
    out, busy, blocked = [], {}, set()
    for t in sorted(trades, key=lambda t: (t["day"], t["fill_min"], t["sym"])):
        d = t["day"]
        if d in blocked or t["fill_min"] <= busy.get(d, -1):
            continue
        out.append(t)
        busy[d] = t["exit_min"]
        if done_after_loss and t["net"] < 0:
            blocked.add(d)
    return out


# ------------------------------------------------------------------ statistics
def lower_bound(days: list, values: list, alpha: float, draws: int = 20000) -> float:
    """Day-clustered bootstrap quantile of the mean (the edge hunt's own routine)."""
    import numpy as np
    from edge_hunt.protocol import lower_bound as lb
    if len(values) < 5:
        return float("nan")
    return lb(np.asarray(days), np.asarray(values, float), alpha, draws)


def break_even_borrow(trades: list[dict]) -> float | None:
    """The borrow cost, in % of the entry price a round trip, that brings the mean net R
    to zero: mean(net) / mean(entry / risk), in percent."""
    if not trades:
        return None
    inv = sum(t["entry"] / t["risk"] for t in trades) / len(trades)
    return 100.0 * (sum(t["net"] for t in trades) / len(trades)) / inv if inv > 0 else None


def with_borrow(trades: list[dict], pct: float) -> list[float]:
    return [t["net"] - pct / 100.0 * t["entry"] / t["risk"] for t in trades]


def adoption(port: list[dict], side: int, older: list[dict] | None, real: dict | None = None,
             family: str | None = None) -> dict:
    """Criteria 1-7 of PREREGISTRATION.md §6 on the holdout portfolio; with `real` (the same
    trades re-priced on quotes, amendment 2026-10-12c) also criterion 8."""
    v = [t["net"] for t in port]
    d = [t["day"] for t in port]
    n = len(v)
    mean = sum(v) / n if n else float("nan")
    a = corrected_alpha(family=family)
    lb = lower_bound(d, v, a)
    years = defaultdict(list)
    for t in port:
        years[t["day"][:4]].append(t["net"])
    yr = {y: (sum(years[y]) / len(years[y]), len(years[y])) for y in HOLDOUT_YEARS if years.get(y)}
    rd = [(t["day"], t["net"] - t["rnd"]) for t in port if t.get("rnd") is not None]
    lb_r = lower_bound([x[0] for x in rd], [x[1] for x in rd], 0.025)
    be = break_even_borrow(port)
    om = (sum(t["net"] for t in older) / len(older)) if older else None
    checks = {
        "1 mean net > 0": n > 0 and mean > 0,
        f"2 lower bound > 0 at {a:.2%}": lb == lb and lb > 0,
        f"3 at least {MIN_HOLDOUT} trades": n >= MIN_HOLDOUT,
        f"4 positive in {MIN_YEARS_POSITIVE} of 3 years": sum(1 for y in yr.values() if y[0] > 0) >= MIN_YEARS_POSITIVE,
        "5 beats random entry on the same names": lb_r == lb_r and lb_r > 0,
        f"6 break-even borrow >= {BORROW_MIN_PCT} % (shorts)": side > 0 or (be is not None and be >= BORROW_MIN_PCT),
        "7 2016-2020 mean net > 0": om is not None and om > 0,
    }
    if real is not None:
        checks["8 real quotes keep the mean net > 0"] = bool(real.get("n") and real["resolved"] >= 0.9 * real["n"]
                                                             and real["mean"] is not None and real["mean"] > 0)
    return {"n": n, "mean": mean, "lb": lb, "alpha": a, "years": yr,
            "vs_random": (sum(x[1] for x in rd) / len(rd)) if rd else None, "vs_random_lb": lb_r,
            "break_even_borrow": be, "older_mean": om, "older_n": len(older or []), "real": real,
            "checks": checks, "adopted": all(checks.values())}


COST_CHECK_FILES = ("results/cost_check.json", "cost_check.json")


def cost_verdict() -> dict | None:
    """The real-quote cost check's verdict (amendment 2026-10-12c): the Mac's local copy first,
    then the committed one."""
    for rel in COST_CHECK_FILES:
        f = FOLDER / rel
        if f.exists():
            v = json.loads(f.read_text())
            if not v.get("smoke"):
                return v
    return None
