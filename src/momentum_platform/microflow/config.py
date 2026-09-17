"""Every microflow parameter, in one place, each carrying its provenance.

The rule this file exists to enforce: **a number is written once**. The
repo has been bitten twice by the same value living in two places and
drifting — the roundup word list (browser and server disagreed for weeks,
2026-09-17) and the third-pullback rule (`MICRO-PULLBACK-SPEC.md` says skip,
`PARAMETERS.md` says reduced size).

`origin` and `evidence_status` follow the convention in
`research/first-pullback-edge/config/strategy.yaml`:

  SOURCE            he states it; the citation is in `note`
  LOCAL_ADDITION    this project's own, and it must justify itself here
  STUDY             a value a measurement in this repo produced

  MEASURED                  a number came out of data
  REASONED_NOT_MEASURED     defensible arithmetic, no data yet
  UNKNOWN                   a placeholder awaiting Phase 0
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict

#: Documentation for every field, keyed by name. Kept beside the values
#: rather than in prose so a reader of the object can always find the why.
PROVENANCE: Dict[str, Dict[str, str]] = {
    "spread_k": {
        "origin": "LOCAL_ADDITION",
        "evidence_status": "REASONED_NOT_MEASURED",
        "note": (
            "The stop must be at least k times the spread. A round trip pays "
            "roughly one full spread, so the spread costs 1/k of R. The "
            "strategy's own best case is +0.25 R per trade (50% wins on the "
            "half-at-1R ladder, MICRO-PULLBACK-SPEC.md). k=4 therefore costs "
            "0.250 R and leaves exactly nothing; k=8 costs 0.125 R and leaves "
            "+0.125 R before commissions, which take a further 0.05-0.07 R. "
            "An earlier draft of the plan proposed 4 and was wrong by "
            "arithmetic. Owner-confirmed 8 on 2026-09-17. Phase 0 may raise "
            "it; lowering it below 8 needs a dated note in the plan."
        ),
    },
    "min_dip_bars_10s": {
        "origin": "SOURCE",
        "evidence_status": "REASONED_NOT_MEASURED",
        "note": "1-3 candles of pause, MICRO-PULLBACK-SPEC.md §2. At 10s that is 10-30 seconds.",
    },
    "max_dip_bars_10s": {
        "origin": "SOURCE", "evidence_status": "REASONED_NOT_MEASURED",
        "note": "Upper end of the same 1-3 range. A longer pause is no longer a MICRO pullback.",
    },
    "max_dip_retrace_pct": {
        "origin": "SOURCE", "evidence_status": "UNKNOWN",
        "note": (
            "'the dip gives back a small part of the move, not most of it' and "
            "'deep dip = skip the trade (not use a wider stop)', "
            "MICRO-PULLBACK-SPEC.md §2/§4. He gives no number. 50% is a "
            "placeholder; Phase 0 measures the real distribution."
        ),
    },
    "dip_volume_must_fall": {
        "origin": "SOURCE", "evidence_status": "REASONED_NOT_MEASURED",
        "note": "'volume falls vs the push candles'; rising volume in the dip is real selling.",
    },
    "require_above_vwap": {
        "origin": "SOURCE", "evidence_status": "REASONED_NOT_MEASURED",
        "note": "Below VWAP = refuse, MICRO-PULLBACK-SPEC.md §4.",
    },
    "require_above_ema9": {
        "origin": "SOURCE", "evidence_status": "REASONED_NOT_MEASURED",
        "note": "Below the 9 EMA = refuse, same section.",
    },
    "require_macd_positive": {
        "origin": "SOURCE", "evidence_status": "REASONED_NOT_MEASURED",
        "note": "'MACD is negative / has crossed below signal -> no long, ever', same section.",
    },
    "reward_multiple": {
        "origin": "SOURCE", "evidence_status": "REASONED_NOT_MEASURED",
        "note": (
            "Second target of the ladder. The full rule is half off at +1R, "
            "stop to break-even, the rest to +2R — see `scale_out_at_r`."
        ),
    },
    "scale_out_at_r": {
        "origin": "SOURCE", "evidence_status": "REASONED_NOT_MEASURED",
        "note": "'sell half at +1R, move stop to break-even, let the rest run to +2R'.",
    },
    "bailout_bars_10s": {
        "origin": "SOURCE", "evidence_status": "UNKNOWN",
        "note": (
            "'price stalls, no follow-through in ~2 candles -> get out' — "
            "breakout or bailout. Those are 1-minute candles in the spec; at "
            "10s the equivalent count is unmeasured. 12 = two minutes."
        ),
    },
    "max_concurrent_positions": {
        "origin": "LOCAL_ADDITION", "evidence_status": "REASONED_NOT_MEASURED",
        "note": (
            "Owner allows more than one position (2026-09-17). Capped at 3 "
            "because every name on this desk is a low-float momentum runner "
            "in the same session: three positions is three times one bet, not "
            "diversification. The PDT rule is NOT the constraint — it was "
            "eliminated in spring 2026 and margin accounts need $2,000 "
            "(knowledge-base/warrior-blog/rules-regulation/pattern-day-trader-rule.md)."
        ),
    },
    "max_open_risk_r": {
        "origin": "LOCAL_ADDITION", "evidence_status": "REASONED_NOT_MEASURED",
        "note": (
            "Total risk across open positions. One adverse market minute can "
            "take every correlated position at once, so the cap is on the sum, "
            "not only on the count."
        ),
    },
    "allow_margin": {
        "origin": "LOCAL_ADDITION", "evidence_status": "REASONED_NOT_MEASURED",
        "note": (
            "False in v1. A tight stop produces a large share count: $20 of "
            "risk on a 3-cent stop is 666 shares, $2,331 of stock at $3.50 — "
            "already the whole account for one position. Cash binds before "
            "risk does, and leverage on a correlated basket is how a small "
            "account goes to zero."
        ),
    },
    "dollar_risk": {
        "origin": "LOCAL_ADDITION", "evidence_status": "REASONED_NOT_MEASURED",
        "note": "Matches the phase-A exercise so nothing changes shape between cohorts.",
    },
    "session_start_et": {
        "origin": "SOURCE", "evidence_status": "MEASURED",
        "note": "PARAMETERS.md §2, the prime window opens 09:35 ET.",
    },
    "session_end_et": {
        "origin": "SOURCE", "evidence_status": "MEASURED",
        "note": "PARAMETERS.md §2, 11:30 ET is the outer edge for new entries, n=44/16.",
    },
}


@dataclass(frozen=True)
class MicroflowConfig:
    """Frozen so nothing can tune it mid-session. Build a new one instead."""

    # -- the executability gate (plan M5) --------------------------------
    spread_k: float = 8.0

    # -- Layer B, the 10-second micro pullback ---------------------------
    min_dip_bars_10s: int = 1
    max_dip_bars_10s: int = 3
    max_dip_retrace_pct: float = 50.0
    dip_volume_must_fall: bool = True

    # -- Layer A, the 1-minute context -----------------------------------
    require_above_vwap: bool = True
    require_above_ema9: bool = True
    require_macd_positive: bool = True

    # -- exits ------------------------------------------------------------
    reward_multiple: float = 2.0
    scale_out_at_r: float = 1.0
    bailout_bars_10s: int = 12

    # -- risk and position caps (plan M5b) --------------------------------
    max_concurrent_positions: int = 3
    max_open_risk_r: float = 3.0
    allow_margin: bool = False
    dollar_risk: float = 20.0

    # -- session window ---------------------------------------------------
    session_start_et: str = "09:35"
    session_end_et: str = "11:30"

    def provenance(self, field_name: str) -> Dict[str, str]:
        """Where this value came from and whether anything measured it."""
        return PROVENANCE.get(field_name, {
            "origin": "UNDECLARED", "evidence_status": "UNKNOWN",
            "note": "No provenance recorded — that is a defect, not a default.",
        })

    def undeclared(self) -> list[str]:
        """Fields with no provenance entry. A test asserts this stays empty."""
        return [k for k in asdict(self) if k not in PROVENANCE]

    def unmeasured(self) -> list[str]:
        """Fields still waiting on a measurement. Reported, never hidden."""
        return [k for k in asdict(self)
                if self.provenance(k).get("evidence_status") == "UNKNOWN"]

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        """Stable hash of the values, for stamping on every decision."""
        import hashlib
        import json
        blob = json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(blob).hexdigest()[:12]


#: The one instance the live path uses. Tests build their own.
DEFAULT = MicroflowConfig()
