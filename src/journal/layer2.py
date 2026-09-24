"""Layer 2, gate by gate — the same four booleans FILTERS.md requires all
true at entry, read back out of a decision row so a refusal can NAME what
was red and the ledger can be scored per gate.

    vwap    price > VWAP                 cascade gate id 'vwap'
    ema9    price > 9 EMA                cascade gate id 'ema9'
    macd    MACD hist > 0 and > signal   cascade gate id 'macd'
    volume  pullback vol < impulse vol   decisions.volume_ok (the detector's)

The three chart gates live in `decisions.gates_json` with the cascade's own
state word (PASS / FAIL / UNKNOWN…); the volume gate is the detector's
boolean on the same row. Nothing here evaluates a gate — that is the
cascade's and the detector's job at the plan — this module only reads what
they wrote, so `missed`, `review` and the runner's refusal text all describe
the same fact.

Why it exists (2026-09-24, first phase-C morning): thirteen pre-market plans
were refused "Layer 2 not green: verdict WAIT" and the text did not say
WHICH gate. The per-gate split is the measurement an amendment has to be
written from; without it the only options were tuning blind or not at all.
"""

from __future__ import annotations

import json
from typing import Iterable, Optional

GATES = ("vwap", "ema9", "macd", "volume")

LABEL = {
    "vwap": "VWAP",
    "ema9": "9 EMA",
    "macd": "MACD",
    "volume": "pullback volume",
}

# What a red gate reads as, in the refusal and in the reports.
RED_TEXT = {
    ("vwap", "FAIL"): "below VWAP",
    ("ema9", "FAIL"): "below the 9 EMA",
    ("macd", "FAIL"): "MACD not positive and above its signal",
    ("volume", "FAIL"): "pullback volume not lighter than the impulse",
}

GREEN = "PASS"


def sub_gates(gates_json: Optional[str], volume_ok) -> dict[str, str]:
    """The four Layer 2 states for one decision row: PASS, FAIL or UNKNOWN.

    A chart gate absent from gates_json (rows written before the review that
    added them) reads UNKNOWN, never PASS. volume_ok None reads UNKNOWN too:
    a plan whose volume comparison was not recorded is not a plan whose
    volume was fine.
    """
    out = {g: "UNKNOWN" for g in GATES}
    try:
        gates = json.loads(gates_json or "[]")
    except (TypeError, ValueError):
        gates = []
    for g in gates:
        gid = g.get("id") if isinstance(g, dict) else None
        if gid in ("vwap", "ema9", "macd"):
            state = str(g.get("state") or "UNKNOWN").upper()
            out[gid] = "PASS" if state == "PASS" else ("FAIL" if state == "FAIL" else "UNKNOWN")
    if volume_ok is None:
        out["volume"] = "UNKNOWN"
    else:
        out["volume"] = "PASS" if bool(volume_ok) else "FAIL"
    return out


def red(states: dict[str, str]) -> list[str]:
    """Gate names that were not green, in FILTERS.md order. UNKNOWN is red:
    'all true at entry' is not met by a gate nobody could compute."""
    return [g for g in GATES if states.get(g, "UNKNOWN") != GREEN]


def key(states: dict[str, str]) -> str:
    """One label per combination, for grouping: 'all green', 'volume',
    'macd+volume', 'vwap?' (the ? marks UNKNOWN)."""
    parts = []
    for g in GATES:
        s = states.get(g, "UNKNOWN")
        if s == "FAIL":
            parts.append(g)
        elif s != GREEN:
            parts.append(g + "?")
    return "+".join(parts) if parts else "all green"


def describe(states: dict[str, str], only: Optional[Iterable[str]] = None) -> str:
    """Human text for the red gates: 'below VWAP; MACD not positive and above
    its signal; 9 EMA unknown (not computable)'. `only` restricts to a subset
    (the runner names the chart gates in one reason and the volume gate in
    another, as before)."""
    names = list(only) if only is not None else list(GATES)
    bits = []
    for g in names:
        s = states.get(g, "UNKNOWN")
        if s == GREEN:
            continue
        if s == "FAIL":
            bits.append(RED_TEXT[(g, "FAIL")])
        else:
            bits.append(f"{LABEL[g]} unknown (not computable at the plan)")
    return "; ".join(bits)
