"""Exercise policy the runner must consult before a pre-market entry.

Kept out of `runner.py` so `scripts/day.py` and the runner read the same
rule, and out of `intent.py` because it is a fact about the EXERCISE
(phase, probe verdict) rather than about the order.

docs/preregistration.md §5: the pre-market path takes the shape the probe
dictates. `held` — IBKR keeps the stop live, so a bracket protects. `queued`
— IBKR parks the stop for 09:30, so the position is naked until the bell
and needs a monitored exit; §5 says phase C does not start on that verdict
until the monitored design is pre-registered as an amendment. The design
is `runner.watch_stops`; the amendment is recorded in the doc.
"""

from __future__ import annotations


def premarket_allowed(state: dict) -> tuple[bool, str]:
    if state.get("phase") != "C":
        return False, f"phase {state.get('phase')} — pre-market entries start in phase C"
    v = state.get("probe_verdict")
    if v is None:
        return False, "no probe verdict recorded — run scripts/premarket_probe.py pre-market"
    if v == "held":
        return True, "probe: IBKR holds the stop live pre-market — brackets"
    if v == "queued":
        # §5: phase C does not start on this verdict until the owner accepts
        # amendment A1. Until 2026-09-08 the code allowed the monitored shape
        # on the verdict alone (audit F1); acceptance is now a recorded human
        # act — `exercise.py accept-a1 --confirm` — and nothing else.
        if state.get("a1_accepted") != "yes":
            return False, ("probe: stop queued to 09:30 — the monitored exit is amendment A1, "
                           "not yet accepted by the owner (exercise.py accept-a1 --confirm)")
        return True, (f"probe: stop queued to 09:30 — monitored exit, positions UNPROTECTED "
                      f"(A1 accepted by {state.get('a1_accepted_by') or '?'} "
                      f"{str(state.get('a1_accepted_at') or '')[:10]})")
    return False, f"probe inconclusive ({v!r}) — paste the probe output back"


def premarket_shape(state: dict) -> str:
    """'bracket' | 'monitored' | 'none' — what an allowed pre-market entry looks like."""
    ok, _ = premarket_allowed(state)
    if not ok:
        return "none"
    return "bracket" if state.get("probe_verdict") == "held" else "monitored"
