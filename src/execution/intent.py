"""What may be sent, decided without IBKR in the room.

Every refusal in this module is a refusal to place an order, and each one
exists because of something that has already gone wrong somewhere — on the
desk, in the replication study, or in a session. They are separated from
`ibkr_trader` so that the whole decision surface is testable with no
Gateway, no network and no account.

THE R DENOMINATOR. An intent carries two risk figures and they are not the
same number:

  planned  = (trigger - stop) * shares      what the plan said
  realised = (fill    - stop) * shares      what the market gave

The replication study measured realised risk at a median 1.52x planned, and
reading results in planned R made losses look catastrophic that were merely
bad (-1.7408 R planned against -1.0818 R realised on the same trades). An
executor that records only the planned figure cannot ever measure its own
slippage, so `PlacedOrder` keeps room for both from the first order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from momentum_platform.sessions import ET, REGULAR_END, REGULAR_START

# Importing the desk's calendar rather than restating 09:30 here. The arrow
# only points this way: `momentum_platform` must never import `execution`,
# and a test enforces that. Two definitions of the opening bell would drift,
# and the one that drifts is always the copy.

# Ross's method is long-only small-cap momentum. Shorting is a different
# book with different borrow, halt and squeeze behaviour, and none of the
# replication work covers it. Refused rather than silently unsupported.
SIDE = "BUY"

# A planned risk this far over the stated dollar risk is a sizing error, not
# a rounding artefact. Share counts are integers, so some overshoot is
# unavoidable on a small stop.
RISK_TOLERANCE = 1.05


def in_regular_hours(now: Optional[datetime] = None) -> bool:
    """True only inside 09:30-16:00 ET on a weekday.

    Holidays are not consulted. This is a refusal gate, and being wrong in
    the safe direction on a holiday costs a trade that the market would not
    have filled anyway.
    """
    now = (now or datetime.now(ET)).astimezone(ET)
    if now.weekday() >= 5:
        return False
    return REGULAR_START <= now.time() < REGULAR_END


@dataclass(frozen=True)
class EntryIntent:
    """A proposed entry. Construct it, then ask `refusals()` before placing."""

    symbol: str
    trigger: float                 # limit price of the entry
    stop: float                    # protective stop, always below trigger
    shares: int
    dollar_risk: float             # the user's own stated risk for this trade
    target: Optional[float] = None  # optional profit-taking limit
    plan_allowed: bool = False      # from cascade.CascadeResult.plan_allowed
    verdict: str = ""               # the cascade verdict, recorded not judged
    note: str = ""

    @property
    def risk_per_share(self) -> float:
        return round(self.trigger - self.stop, 4)

    @property
    def planned_risk(self) -> float:
        return round(self.risk_per_share * self.shares, 2)


def refusals(i: EntryIntent,
             now: Optional[datetime] = None) -> list[str]:
    """Every reason this order must not be sent. Empty list = sendable.

    All reasons are collected rather than raised on the first, because a
    refused intent is something a human reads and fixes, and being told one
    problem at a time wastes the window the trade lives in.
    """
    out: list[str] = []

    if not i.symbol or not i.symbol.strip():
        out.append("no symbol")

    # The cascade is upstream and it is the authority. An executor that can
    # be talked into an order the cascade killed is the IMRN defect with a
    # broker attached: last $1.69 against a $2-20 band, plan still armed.
    if not i.plan_allowed:
        out.append(f"cascade forbids a plan (verdict {i.verdict or 'unknown'})")

    if i.trigger <= 0:
        out.append(f"trigger {i.trigger} is not a price")
    if i.stop <= 0:
        out.append(f"stop {i.stop} is not a price")

    # Long-only: a stop at or above the entry is either a typo or a short,
    # and both are refused. It also makes risk_per_share zero or negative,
    # which would divide the whole R accounting by zero downstream.
    if i.trigger > 0 and i.stop > 0 and i.stop >= i.trigger:
        out.append(f"stop {i.stop} is not below trigger {i.trigger}")

    if i.shares <= 0:
        out.append(f"{i.shares} shares is not an order")

    if i.target is not None and i.target <= i.trigger:
        out.append(f"target {i.target} is not above trigger {i.trigger}")

    if i.dollar_risk <= 0:
        out.append("no dollar risk stated")
    elif i.risk_per_share > 0 and i.planned_risk > i.dollar_risk * RISK_TOLERANCE:
        out.append(f"planned risk ${i.planned_risk} exceeds stated "
                   f"${i.dollar_risk} by more than "
                   f"{(RISK_TOLERANCE - 1) * 100:.0f}%")

    # EXTENDED HOURS. A resting stop does not exist outside 09:30-16:00.
    #
    #   "Extended hours accept limit orders only: [...] No stop orders of any
    #    type - banned because thin tape makes stop hunting trivial [...] Your
    #    stop is therefore mental or hotkeyed, never resting."
    #   -- .claude/skills/extended-hours/SKILL.md
    #
    # The same file explains the warning IBKR returned on the first smoke
    # test: orders that cannot participate "sit off-market and fire at
    # 09:30". IBKR does not reject them, it QUEUES them, which is worse than
    # a rejection because it looks like acceptance. The 2026-09-06 smoke test
    # got exactly that: `Warning 399 [...] your order will not be placed at
    # the exchange until 2026-09-08 09:30:00 US/Eastern`.
    #
    # So a bracket armed at 09:15 is not a protected entry with an early
    # start. It is an entry and a stop that both arrive at the bell, in the
    # queue, alongside every other resting order - and the skill names that
    # pile-up as the reason gappers dump at the open. Refused rather than
    # sent, until a deliberate pre-market mode exists.
    if not in_regular_hours(now):
        out.append("outside 09:30-16:00 ET: a resting stop cannot exist, and "
                   "IBKR would queue this bracket to the next open rather "
                   "than reject it")

    # Sub-penny prices are rejected by the exchange, not by IBKR, so the
    # order dies after it leaves. Caught here where the message is readable.
    for name, px in (("trigger", i.trigger), ("stop", i.stop),
                     ("target", i.target)):
        if px is not None and px >= 1.0 and round(px, 2) != round(px, 4):
            out.append(f"{name} {px} is sub-penny; not on the tick grid")

    return out


def shares_for(trigger: float, stop: float, dollar_risk: float) -> int:
    """The only sizing rule: the stop defines the size.

    Core invariant, carried from the mastery bundle — the scanner discovers a
    candidate, the chart defines the setup, the stop defines the size, the
    market decides the result. Never sized from buying power, which on this
    paper account reads $14,291 against $2,143 of equity and is fiction.
    """
    rps = trigger - stop
    if rps <= 0 or dollar_risk <= 0:
        return 0
    # Integer mils, not float floor division. `100 // 0.2` is 499.0, because
    # 0.2 has no exact binary form and the true quotient lands a hair under
    # 500. On a $100 risk against a 20c stop that is one share; on a tighter
    # stop it is worse, and it is silent every time. Prices are on a penny
    # grid, so scaling to tenths of a cent makes the division exact.
    rps_mils = round(rps * 1000)
    if rps_mils <= 0:
        return 0
    return int(round(dollar_risk * 1000)) // rps_mils


@dataclass
class PlacedOrder:
    """What was sent and, later, what came back. Both R denominators."""

    symbol: str
    parent_id: int
    stop_id: Optional[int] = None
    target_id: Optional[int] = None
    trigger: float = 0.0
    stop: float = 0.0
    shares: int = 0
    status: str = "submitted"
    fill_price: Optional[float] = None
    fill_time: Optional[str] = None
    nbbo_bid_at_fill: Optional[float] = None   # Phase 3 reconciliation
    nbbo_ask_at_fill: Optional[float] = None
    intent: Optional[EntryIntent] = None
    events: list[str] = field(default_factory=list)

    @property
    def planned_risk(self) -> float:
        return round((self.trigger - self.stop) * self.shares, 2)

    @property
    def realised_risk(self) -> Optional[float]:
        """None until filled. This is the honest denominator."""
        if self.fill_price is None:
            return None
        return round((self.fill_price - self.stop) * self.shares, 2)

    @property
    def slippage_ratio(self) -> Optional[float]:
        """realised / planned. The study's median was 1.52."""
        planned, real = self.planned_risk, self.realised_risk
        if real is None or planned <= 0:
            return None
        return round(real / planned, 4)
