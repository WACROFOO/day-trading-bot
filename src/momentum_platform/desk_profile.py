"""The shared trading rules, and a fingerprint that proves two desks match.

Two traders running their own IBKR connection want the same scanners and the
same alerts. Everything that decides what a desk admits and what it fires
lives in one committed file, `config/desk-profile.json`; secrets and
machine-specific settings stay in each machine's `.env` and are never part of
this. `fingerprint()` hashes the EFFECTIVE rules — the file, any environment
override in force, the Confirmed course constants read out of the code, and
each scanner's definition version — so two desks can be compared in one line
instead of by reading two screens side by side.

A difference in the hash is a difference in what the desks will alert on.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "config" / "desk-profile.json"

# What a desk falls back to when the file is missing. Kept in step with the
# committed file; the file is what actually ships between two traders.
DEFAULTS: Dict[str, Dict[str, Any]] = {
    "desk": {"priceMin": 1.0, "priceMax": 30.0, "minGainPct": 10.0,
             "maxSymbols": 8, "scanTop": 30},
    "cadence": {"rebuildSeconds": 3, "rescanSeconds": 120, "historyEverySeconds": 20,
                "volumeProfileDays": 10, "barStallSeconds": 300},
    "liquidity": {"minVolume5m": 25000, "minPillars": 3},
}

# Environment overrides, by rule. Each one is recorded in the fingerprint, so a
# desk running an override cannot silently disagree with its partner.
ENV_OVERRIDES = {
    ("desk", "priceMin"): "DESK_PRICE_MIN",
    ("desk", "priceMax"): "DESK_PRICE_MAX",
    ("desk", "minGainPct"): "DESK_MIN_GAIN_PCT",
    ("desk", "maxSymbols"): "DESK_MAX_SYMBOLS",
    ("cadence", "rescanSeconds"): "DESK_RESCAN_SECONDS",
    ("cadence", "volumeProfileDays"): "DESK_VOLUME_PROFILE_DAYS",
    ("cadence", "barStallSeconds"): "DESK_BAR_STALL_SECONDS",
    ("liquidity", "minVolume5m"): "DESK_MIN_VOLUME_5M",
    ("liquidity", "minPillars"): "DESK_MIN_PILLARS",
}

_CACHE: Optional[Dict[str, Any]] = None


def _coerce(default: Any, raw: str) -> Any:
    try:
        return int(raw) if isinstance(default, int) and not isinstance(default, bool) else float(raw)
    except (TypeError, ValueError):
        return default


def load(path: Optional[Path] = None, use_env: bool = True, refresh: bool = False) -> Dict[str, Any]:
    """The effective rules: the committed file, then any environment override.

    Never raises. A missing or unreadable file falls back to DEFAULTS and says
    so in `source`, because a desk that silently invents its own rules is the
    thing this module exists to prevent."""
    global _CACHE
    target = Path(path) if path else PROFILE_PATH
    # The file is read once; the environment is re-read on every call. A cached
    # override would let a desk keep answering with a rule its own .env no
    # longer sets, which is exactly the drift this module is here to catch.
    if _CACHE is not None and not refresh and path is None:
        return _with_env(_CACHE, use_env)
    rules = {k: dict(v) for k, v in DEFAULTS.items()}
    source, note = str(target), None
    try:
        loaded = json.loads(target.read_text())
        for section, values in loaded.items():
            if section in rules and isinstance(values, dict):
                rules[section].update({k: v for k, v in values.items() if k in rules[section]})
        version = loaded.get("profileVersion")
    except FileNotFoundError:
        source, note, version = "defaults", f"{target} not found; running built-in defaults", None
    except Exception as exc:
        source, note, version = "defaults", f"{target} unreadable ({exc}); running built-in defaults", None
    out = {"rules": rules, "source": source, "note": note,
           "profileVersion": version, "envOverrides": {}}
    if path is None:
        _CACHE = out
    return _with_env(out, use_env)


def _with_env(base: Dict[str, Any], use_env: bool) -> Dict[str, Any]:
    rules = {k: dict(v) for k, v in base["rules"].items()}
    overrides: Dict[str, Any] = {}
    if use_env:
        for (section, key), var in ENV_OVERRIDES.items():
            raw = os.environ.get(var)
            if raw in (None, ""):
                continue
            value = _coerce(rules[section][key], raw)
            if value != rules[section][key]:
                overrides[var] = value
                rules[section][key] = value
    return dict(base, rules=rules, envOverrides=overrides)


def rules(section: str, key: str) -> Any:
    return load()["rules"][section][key]


def build_commit() -> Optional[str]:
    """The short commit this desk is running, when git can say."""
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None
    except Exception:
        return None


def confirmed_constants() -> Dict[str, Any]:
    """The Confirmed course pillars, read out of the code they live in.

    They are not operator settings and are not in the profile file — but an
    edit to them changes every list on the desk, so the fingerprint carries
    them and a partner's mismatched hash points straight at it."""
    from .scanners import five_pillars as fp
    return {
        "priceMin": fp.PRICE_MIN_CONFIRMED, "priceMax": fp.PRICE_MAX_CONFIRMED,
        "gainMinPct": fp.GAIN_MIN_PCT, "rvolMin": fp.RVOL_MIN,
        "floatMaxShares": fp.FLOAT_MAX_SHARES, "newsMaxAgeMinutes": fp.NEWS_MAX_AGE_MINUTES,
    }


def scanner_versions() -> Dict[str, str]:
    """Each scanner's definition version: the logic behind the alerts."""
    try:
        from .scanners.five_pillars import FivePillarsAlert, FivePillarsList
        from .scanners.momentum_events import (Breakout52wScanner, HodMomentumScanner,
                                               RunningMoveScanner, UptrendScanner)
        made = [FivePillarsAlert(), FivePillarsList(), HodMomentumScanner(), UptrendScanner(),
                RunningMoveScanner(direction="down"), Breakout52wScanner()]
        return {s.scanner_id: s.definition_version for s in made}
    except Exception:
        return {}


def fingerprint(entitlements: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """What this desk will scan and alert on, as one comparable block.

    `rules` hashes only what changes the output: the profile, the overrides in
    force, the Confirmed constants and the scanner definitions. The build
    commit is reported beside it rather than inside it, so a documentation
    commit does not read as a rule change.

    Entitlements are reported, never hashed: a partner without IBKR
    fundamentals or without news keys scores the float and news pillars
    differently, which moves the three-of-five liquidity gate and therefore
    the alerts. That is a real difference between two desks and it has to be
    visible without pretending the rules disagree."""
    prof = load()
    payload = {
        "rules": prof["rules"],
        "envOverrides": prof["envOverrides"],
        "confirmed": confirmed_constants(),
        "scanners": scanner_versions(),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return {
        "hash": hashlib.sha256(blob).hexdigest()[:12],
        "build": build_commit(),
        "profileVersion": prof["profileVersion"],
        "source": prof["source"],
        "note": prof["note"],
        "entitlements": entitlements or {},
        **payload,
    }
