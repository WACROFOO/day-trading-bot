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
from datetime import datetime, time
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


# `PARAMETERS.md` §2: `premarket_start` 07:00, flagged era-dependent (a 2017
# "half a dozen times a year" against 07:00 named 78 times in the July 2026
# challenge). The extended-hours skill gives the mechanical reason for the
# same boundary: "most retail brokers only allow from 07:00". Both point at
# the same clock, for different reasons, so 07:00 it is.
PREMARKET_START = time(7, 0)

SESSIONS = ("regular", "premarket")

# `PARAMETERS.md` §2: `session_close` 11:30 ET "outer edge, not the centre"
# (n=16), `midday_avoid` 11:30-15:00 "no trades". CLAUDE.md carries the same
# line with the typical close at 11:00. This is the ENTRY cutoff, not the
# exit: after it, no new position is opened. Exits are always permitted, so a
# position opened at 11:29 can still be managed and flattened.
#
# It is enforced here because the cascade does not enforce it. An
# out-of-window name comes back Verdict.LOG with plan_allowed True, which is
# correct for the cascade — LOG means "record it, do not trade it", and a
# downgrade is not a kill. But an executor reading only plan_allowed would
# open a position at 14:00, which is the one thing §2 is most explicit about.
HARD_STOP = time(11, 30)


def in_premarket(now: Optional[datetime] = None) -> bool:
    """True only inside 07:00-09:30 ET on a weekday."""
    now = (now or datetime.now(ET)).astimezone(ET)
    if now.weekday() >= 5:
        return False
    return PREMARKET_START <= now.time() < REGULAR_START


def session_for(now: Optional[datetime] = None) -> Optional[str]:
    """Which session an intent placed now belongs to, or None (no trading)."""
    if in_regular_hours(now):
        return "regular"
    if in_premarket(now):
        return "premarket"
    return None


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
    # Which session this intent is FOR. Not derived from the clock: the caller
    # states it, and refusals() checks the clock agrees. A regular-hours
    # intent that arrives pre-market is a mistake about the time, and the
    # honest response is to refuse it, not to quietly convert it.
    session: str = "regular"
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

    # SESSIONS. Two are tradable and they have different order mechanics.
    #
    # REGULAR, 09:30-16:00. Brackets with a resting stop, the shape the rest
    # of this module assumes.
    #
    # PRE-MARKET, 07:00-09:30. The corpus is explicit about what does not
    # work there, .claude/skills/extended-hours/SKILL.md:
    #
    #   "Extended hours accept limit orders only: [...] No stop orders of any
    #    type - banned because thin tape makes stop hunting trivial [...] Your
    #    stop is therefore mental or hotkeyed, never resting."
    #
    # and about what happens to an order that cannot participate: it "sit[s]
    # off-market and fire[s] at 09:30". IBKR does not reject such an order,
    # it QUEUES it, which looks like acceptance. The 2026-09-06 smoke test
    # got exactly that: `Warning 399 [...] will not be placed at the
    # exchange until 2026-09-08 09:30:00 US/Eastern`.
    #
    # That rule is stated for retail brokers in general - the skill names
    # thinkorswim, Lightspeed and Webull. Whether IBKR honours a stop that
    # carries outsideRth=True as a server-side simulated stop pre-market is
    # NOT in the corpus, and `scripts/premarket_probe.py` exists to find out
    # empirically before anything is built on either answer. Until it has
    # run, a pre-market intent is permitted only when the caller has said
    # "premarket" in so many words, and the executor marks the position as
    # unconfirmed-protected until the stop leg's status is read back.
    #
    # An intent whose stated session disagrees with the clock is refused
    # outright. Converting it would be deciding, on the caller's behalf, to
    # trade a session they did not choose.
    # DAY TRADES ONLY, and the day ends at 11:30. Checked before the session
    # gate so that an 14:00 attempt is told the real reason rather than being
    # told it is inside regular hours, which it is.
    clock = (now or datetime.now(ET)).astimezone(ET)
    if clock.time() >= HARD_STOP:
        out.append(f"{clock:%H:%M} ET is past the {HARD_STOP:%H:%M} hard stop; "
                   f"no new entries (exits are always allowed)")

    if i.session not in SESSIONS:
        out.append(f"unknown session {i.session!r}; expected one of {SESSIONS}")
    elif i.session == "regular" and not in_regular_hours(now):
        out.append("outside 09:30-16:00 ET: a regular-hours bracket needs a "
                   "resting stop, and IBKR would queue this to the next open "
                   "rather than reject it")
    elif i.session == "premarket" and not in_premarket(now):
        out.append("outside 07:00-09:30 ET: not the pre-market session this "
                   "intent was built for")

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
    stop_status: str = ""
    # False until the stop leg is known to be resting and active. Always True
    # for a regular-hours bracket once placed; for a pre-market one it stays
    # False until sync() has read the stop leg back without warning 399.
    protected: bool = False
    fill_price: Optional[float] = None
    fill_time: Optional[str] = None
    nbbo_bid_at_fill: Optional[float] = None   # Phase 3 reconciliation
    nbbo_ask_at_fill: Optional[float] = None
    # The exit, read from the stop or target leg. Until the 2026-09-07 review
    # only the entry leg was ever synced, so no P&L or exit reason existed.
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None            # stop | target
    exit_time: Optional[str] = None
    # IBKR's permanent id. orderId is per API session: orders from an earlier
    # connection come back as orderId 0 (seen 2026-09-07 in the smoke test's
    # read-back), so a restarted runner must be able to find its orders by
    # permId. None until the broker has reported it.
    perm_id: Optional[int] = None
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
