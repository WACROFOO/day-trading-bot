"""The executability gate: is this stop big enough, against this spread, to
be worth taking at all?

Plan M5. The arithmetic that sets it:

A round trip pays roughly one full spread — you buy at the ask and sell at
the bid — so the spread costs `spread / risk_per_share` of one R. The
strategy's own best theoretical case is +0.25 R per trade (a 50% win rate on
the half-at-1R ladder, `MICRO-PULLBACK-SPEC.md`). So a spread worth a quarter
of the risk consumes the entire edge and a spread worth an eighth consumes
half of it, before commissions take another 0.05-0.07 R.

Measured on the owner's 11-17 September tape, 39 prospective setups carrying
a stored quote: median spread $0.020 against a median risk of $0.128, so the
spread was a median **25% of the risk** — precisely the level at which
nothing is left. Five of the 39 had a spread wider than the entire stop.

This gate is why the answer to "does a 10-second stop work for a retail
account" may simply be no, and it is measured before anything is built.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class State(str, Enum):
    """Six states, never two. Anything not positively established fails
    closed — `.claude/skills/trading-report-design/SKILL.md`."""

    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Verdict:
    state: State
    reason: str
    spread: Optional[float] = None
    risk_per_share: Optional[float] = None
    ratio: Optional[float] = None          # spread / risk, the cost in R
    kills: bool = True

    @property
    def ok(self) -> bool:
        return self.state is State.PASS

    @property
    def cost_r(self) -> Optional[float]:
        """What one round trip costs, expressed in R."""
        return self.ratio


def gate(trigger: Optional[float], stop: Optional[float],
         bid: Optional[float], ask: Optional[float], cfg) -> Verdict:
    """PASS when risk_per_share >= k x spread.

    Fails closed on a missing or crossed quote: a spread that cannot be
    established is not a spread of zero. That distinction is the whole
    reason this returns three states instead of a boolean.
    """
    if trigger is None or stop is None:
        return Verdict(State.UNKNOWN, "No trigger or stop — nothing to size against.")
    rps = trigger - stop
    if rps <= 0:
        return Verdict(State.FAIL, f"Stop {stop} is not below the trigger {trigger}.",
                       risk_per_share=rps)
    if bid is None or ask is None:
        return Verdict(State.UNKNOWN,
                       "No quote — the spread could not be established, so the "
                       "gate fails closed rather than assuming zero.",
                       risk_per_share=rps)
    if ask < bid:
        return Verdict(State.UNKNOWN, f"Crossed quote (bid {bid} > ask {ask}).",
                       risk_per_share=rps)
    spread = ask - bid
    if spread <= 0:
        # A locked quote (bid == ask) is not a free round trip; it is a quote
        # the gate cannot price. 2026-09-21: `measure` crashed on 1/ratio with
        # ratio 0 on the owner's 28,708-candle tape. Fails closed.
        return Verdict(State.UNKNOWN, f"Locked quote (bid {bid} == ask {ask}); the spread "
                       "cannot be established, so the gate fails closed.",
                       spread, rps, None)
    ratio = spread / rps
    need = cfg.spread_k * spread
    if rps >= need:
        return Verdict(State.PASS,
                       f"Risk ${rps:.3f} is {1 / ratio:.1f}x the ${spread:.3f} spread "
                       f"(need {cfg.spread_k:g}x); the round trip costs {ratio:.2f} R.",
                       spread, rps, ratio, kills=False)
    return Verdict(State.FAIL,
                   f"Risk ${rps:.3f} is only {1 / ratio:.1f}x the ${spread:.3f} spread "
                   f"(need {cfg.spread_k:g}x). The round trip would cost {ratio:.2f} R "
                   f"of a strategy whose best case is +0.25 R.",
                   spread, rps, ratio)


def cost_in_r(spread: Optional[float], risk_per_share: Optional[float]) -> Optional[float]:
    """One round trip's spread cost, in R. None when it cannot be computed."""
    if not spread or not risk_per_share or risk_per_share <= 0:
        return None
    return spread / risk_per_share


def min_risk_per_share(spread: Optional[float], cfg) -> Optional[float]:
    """The smallest stop distance this spread permits under the gate."""
    if spread is None or spread < 0:
        return None
    return cfg.spread_k * spread
