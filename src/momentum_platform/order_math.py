"""The order arithmetic the bot executes and the desk displays — one copy.

`execution.intent` used to hold these numbers. The desk could not read them
there: `momentum_platform` must never import `execution` (a test enforces it,
the desk is read-only by construction). A manual order panel that restated
the formulas would drift from the bot the first time either changed, and a
size on screen that differs from the size the bot sends is a wrong number
that looks right. So the pure arithmetic lives here, `execution.intent`
re-exports it unchanged, and both sides compute from the same lines.

Nothing in this module places, sizes for, or talks to a broker. It turns a
trigger, a stop and a stated dollar risk into the numbers a human types.
"""

from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass, field
from datetime import time
from typing import Optional, Sequence

# --------------------------------------------------------------- the clock
# `PARAMETERS.md` §2: `premarket_start` 07:00, flagged era-dependent (a 2017
# "half a dozen times a year" against 07:00 named 78 times in the July 2026
# challenge). The extended-hours skill gives the mechanical reason for the
# same boundary: "most retail brokers only allow from 07:00". Both point at
# the same clock, for different reasons, so 07:00 it is.
PREMARKET_START = time(7, 0)

# `PARAMETERS.md` §2: `session_close` 11:30 ET "outer edge, not the centre"
# (n=16), `midday_avoid` 11:30-15:00 "no trades". This is the ENTRY cutoff,
# not the exit: after it, no new position is opened.
HARD_STOP = time(11, 30)
# Amendment A8 (owner decision, delegated, 2026-09-22): no NEW entry inside
# the last ENTRY_BUFFER_MIN minutes before the hard stop. GRML was filled at
# 11:28 and force-flattened at 11:30. LOCAL_ADDITION, reasoned not measured.
ENTRY_BUFFER_MIN = 10
ENTRY_CUTOFF = time(11, 20)

# ------------------------------------------------------------- the entry
# Amendment A10 (owner, 2026-09-23): the entry is a buy STOP-LIMIT resting at
# the plan's trigger, not a plain limit. WHLR 2026-09-23 09:44: trigger 8.31,
# tape near 7.50, the plain limit was capped by IBKR to 7.87 and filled there
# — the pullback was bought, not the break. The stop price is the trigger; the
# limit sits ENTRY_LIMIT_OFFSET_PCT above it (one cent floor); an entry not
# triggered within ENTRY_TTL_MINUTES completed minutes is cancelled. Both
# numbers are reasoned, not measured, and are printed with every entry.
ENTRY_LIMIT_OFFSET_PCT = 0.3
ENTRY_TTL_MINUTES = 3

# -------------------------------------------------------------- the exit
# A16 (owner, 2026-10-01): the extended-hours sell is a limit at bid − offset
# (`.claude/skills/extended-hours/SKILL.md`: "10–15¢ ... below the bid — it
# sweeps the levels up to your cap"). The offset is 1% of the bid or one
# spread, whichever is wider, between 3¢ and 10¢. Approximation.
EXIT_OFFSET_PCT = 1.0
EXIT_OFFSET_MIN = 0.03
EXIT_OFFSET_MAX = 0.10

# Amendment A3 (docs/preregistration.md §5): no fixed target. The protective
# stop trails the high since the fill at TRAIL_R initial risks per share,
# ratcheting up and never down.
TRAIL_R = 1.0

# ------------------------------------------------------------ the filters
# The stop must clear the spread by this factor or the round trip eats the
# trade: with a +2 R plan the spread costs (1/k) R per round trip, so k=4 caps
# that cost at 0.25 R. Amendment A6; the runner refuses below it.
SPREAD_K = 4.0

# Amendment A13 (selective): the runner refuses a stop under this share of
# price, and a trigger under this price. Measured in the rules audit
# (research/paper-exercise/reports/rules_audit_output_v2.txt) as the
# selective lever; read by `execution.runner`, displayed by the desk.
SELECTIVE_MIN_STOP_PCT = 2.0
SELECTIVE_MIN_PRICE = 2.0

# ----------------------------------------------------------------- sizing
# Amendment A18 (owner, 2026-10-06; docs/preregistration.md §5): size from the
# worst fill the order allows, not from the trigger. A10 lets the entry fill up
# to `entry_limit(trigger)`, the round trip pays the spread, and IBKR Fixed
# charges $0.005 a share each way, so the per-share risk the size is computed
# from is (limit − stop) + spread at the decision + $0.01. On the 1,873 replayed
# fills of 2024-26 (research/paper-exercise/reports/2026-10-05-ross-recent-and-
# execution/execution_audit/vx2.txt) losses over $42 fall from 437 to 89 and the
# worst trade from −$493.64 to −$365.69, for −0.006 R a trade. It narrows
# losses; it does not change expectancy. False restores sizing from the trigger.
WORST_FILL_SIZING = True
COMMISSION_RESERVE_PER_SHARE = 0.01

# `tape.py`: "the median 1-minute range of the last 30 regular-hours bars is
# the smallest stop the tape can honour. Below it is fiction."
HONEST_STOP_BARS = 30


def entry_limit(trigger: float) -> float:
    """The stop-limit's limit price for a plan whose trigger is `trigger`."""
    return round(trigger + max(0.01, trigger * ENTRY_LIMIT_OFFSET_PCT / 100.0), 2)


def exit_offset(bid: float, ask: Optional[float] = None) -> float:
    """A16: how far under the bid an extended-hours limit sell is priced."""
    spread = (ask - bid) if ask is not None and ask > bid else 0.0
    raw = max(bid * EXIT_OFFSET_PCT / 100.0, spread)
    return round(min(EXIT_OFFSET_MAX, max(EXIT_OFFSET_MIN, raw)), 2)


def sizing_reserve(trigger: float, spread: Optional[float]) -> float:
    """A18: dollars per share added to (trigger − stop) before sizing — the
    entry limit's headroom, the spread (0 when no quote was read) and the
    round-trip commission."""
    sp = spread if spread is not None and spread > 0 else 0.0
    return round((entry_limit(trigger) - trigger) + sp + COMMISSION_RESERVE_PER_SHARE, 4)


def shares_for(trigger: float, stop: float, dollar_risk: float, reserve: float = 0.0) -> int:
    """The only sizing rule: the stop defines the size.

    Never sized from buying power. `reserve` (A18) widens the per-share risk
    the size is divided by; it never moves the stop. Integer mils, not float
    floor division: `100 // 0.2` is 499.0 because 0.2 has no exact binary
    form; prices are on a penny grid, so tenths of a cent divide exactly.
    """
    rps = trigger - stop
    if rps <= 0 or dollar_risk <= 0:
        return 0
    rps_mils = round((rps + max(reserve, 0.0)) * 1000)
    if rps_mils <= 0:
        return 0
    return int(round(dollar_risk * 1000)) // rps_mils


def sized_for(trigger: float, stop: float, dollar_risk: float,
              max_notional: Optional[float] = None, reserve: float = 0.0) -> tuple[int, str]:
    """Shares and how they were bounded: 'risk' (the stop sized it) or 'funds'
    (the account could not hold the risk-sized position; fewer shares, and so
    LESS than the stated dollar risk — never more)."""
    n = shares_for(trigger, stop, dollar_risk, reserve=reserve)
    if max_notional is None or trigger <= 0 or n <= 0:
        return n, "risk"
    fit = int(max_notional // trigger)
    if fit < n:
        return max(fit, 0), "funds"
    return n, "risk"


# ---------------------------------------------------- what the desk shows
def halt_band_pct(prev_close: Optional[float]) -> Optional[float]:
    """The LULD band width the prior close puts the stock in, as a % of price.

    FILTERS.md, gates 1 and 3: "prior close < $0.75 → 15¢ bands (near-
    untradeable in RTH), $0.75–3 → 20%, > $3 → 10%. Check the prior close, not
    the current print — bands don't update intraday." Under $0.75 the band is
    15 cents, returned here as that share of the prior close. None = unknown.
    """
    if prev_close is None or prev_close <= 0:
        return None
    if prev_close < 0.75:
        return round(0.15 / prev_close * 100.0, 1)
    if prev_close <= 3.0:
        return 20.0
    return 10.0


def honest_stop(ranges: Sequence[float]) -> Optional[float]:
    """The median 1-minute range of the last HONEST_STOP_BARS bars
    (`scripts/tape.py`): the smallest stop the tape can honour."""
    xs = [float(r) for r in ranges if r is not None and r >= 0][-HONEST_STOP_BARS:]
    if len(xs) < 5:
        return None
    return round(statistics.median(xs), 4)


@dataclass
class Check:
    """One line of the order panel: a rule the bot applies, its value here."""

    id: str
    label: str
    ok: Optional[bool]          # None = could not be evaluated (fails closed on screen)
    value: str
    rule: str                   # where the rule lives, in words a trader reads


@dataclass
class Ticket:
    """Everything a human needs to type the bot's order by hand."""

    session: Optional[str]              # "premarket" | "regular" | None (no entries now)
    trigger: float
    limit: float
    stop: float
    risk_share: float
    target_2r: float                    # a planning reference: A3 has no fixed target
    dollar_risk: float
    shares: int
    bound_by: str                       # "risk" | "funds"
    reserve: float
    spread: Optional[float]
    notional_worst: float               # shares × limit
    max_notional: Optional[float]
    loss_at_stop: float                 # shares × (trigger − stop): the plan's loss
    loss_worst: float                   # shares × (limit − stop + spread + commission)
    stop_pct: float
    exit_text: str
    order_line: str
    checks: list[Check] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def ticket(symbol: str, trigger: float, stop: float, dollar_risk: float, *,
           session: Optional[str], bid: Optional[float] = None, ask: Optional[float] = None,
           max_notional: Optional[float] = None, prev_close: Optional[float] = None,
           ranges: Sequence[float] = (), halts_today: int = 0, halted: bool = False,
           worst_fill: Optional[bool] = None) -> Optional[Ticket]:
    """The order the bot would send for this plan, as numbers to type.

    `trigger` is the plan's entry (trigger high + 1¢), `stop` its stop. The
    arithmetic is the runner's: limit = `entry_limit`, size = `sized_for` with
    A18's reserve and the account bound. The checks are the runner's refusals
    that depend on the order itself (A13, A6) plus the stop's enforceability
    (CLAUDE.md rule 5: a tight stop on a halting stock is the finding).
    Returns None when there is no valid long plan (stop at or above trigger).
    """
    trigger, stop = round(float(trigger), 2), round(float(stop), 2)
    if trigger <= 0 or stop <= 0 or stop >= trigger:
        return None
    spread = round(ask - bid, 4) if ask is not None and bid is not None and ask > bid else None
    worst = WORST_FILL_SIZING if worst_fill is None else worst_fill
    reserve = sizing_reserve(trigger, spread) if worst else 0.0
    shares, bound = sized_for(trigger, stop, dollar_risk, max_notional, reserve=reserve)
    limit = entry_limit(trigger)
    rps = round(trigger - stop, 4)
    stop_pct = round(rps / trigger * 100.0, 2)
    target = round(trigger + 2.0 * rps, 2)
    sp = spread or 0.0
    checks: list[Check] = []

    checks.append(Check(
        "stop_pct", "stop vs price", stop_pct >= SELECTIVE_MIN_STOP_PCT,
        f"{stop_pct:.1f}% of price",
        f"the bot refuses a stop under {SELECTIVE_MIN_STOP_PCT:g}% of price (A13)"))
    checks.append(Check(
        "price", "price floor", trigger >= SELECTIVE_MIN_PRICE,
        f"${trigger:.2f}", f"the bot refuses a trigger under ${SELECTIVE_MIN_PRICE:g} (A13)"))
    if spread is None:
        checks.append(Check("spread", "stop vs spread", None, "no quote",
                            f"the bot refuses a stop inside {SPREAD_K:g}× the spread (A6)"))
    else:
        checks.append(Check(
            "spread", "stop vs spread", rps >= SPREAD_K * spread,
            f"spread {spread * 100:.0f}¢ = {spread / rps * 100:.0f}% of the stop",
            f"the bot refuses a stop inside {SPREAD_K:g}× the spread (A6)"))
    hs = honest_stop(ranges)
    if hs is None:
        checks.append(Check("noise", "stop vs 1-min range", None, "too few bars",
                            "tape.py: the median 1-min range is the smallest stop the tape honours"))
    else:
        checks.append(Check(
            "noise", "stop vs 1-min range", rps >= hs,
            f"stop {rps:.2f} vs median range {hs:.2f}",
            "tape.py: the median 1-min range (last 30 traded minutes) is the smallest stop the tape honours"))
    band = halt_band_pct(prev_close)
    if halted:
        checks.append(Check("halt", "halt risk", False, "HALTED now",
                            "no stop executes during a halt; the reopen sets the price"))
    else:
        halt_ok = halts_today == 0 and (band is None or stop_pct < band)
        why = []
        if halts_today:
            why.append(f"halted {halts_today}× today")
        if band is not None:
            why.append(f"LULD band {band:g}%")
        checks.append(Check(
            "halt", "halt risk", halt_ok if (halts_today or band is not None) else None,
            " · ".join(why) or "band unknown",
            "a stop wider than the halt band, or on a halting stock, can be skipped by a reopen gap"))
    if max_notional is not None:
        checks.append(Check(
            "funds", "account bound", bound == "risk",
            f"{shares} sh × {limit:.2f} = ${shares * limit:,.0f} of ${max_notional:,.0f}",
            "sized by funds = less than your stated risk, never more"))

    if session == "premarket":
        off = exit_offset(bid, ask) if bid else EXIT_OFFSET_MAX
        exit_text = (f"pre-market: IBKR does not hold a stop before 09:30 (probe 2026-09-18, warning 2109) — "
                     f"watch {stop:.2f}; exit = SELL LMT at bid − {off:.2f}, outside RTH")
        order_line = (f"BUY {shares} {symbol} LMT {limit:.2f} · outside RTH ✓ · DAY — "
                      f"place it when the ask reaches {trigger:.2f}; no stop leg pre-market")
    elif session == "regular":
        exit_text = (f"stop {stop:.2f} rests at the broker; the bot trails it {TRAIL_R:g}R under the high "
                     f"since the fill (A3); 2R = {target:.2f} is a reference, not an order")
        order_line = (f"BUY {shares} {symbol} STP LMT · stop {trigger:.2f} · limit {limit:.2f} · DAY "
                      f"· attach SELL STP {stop:.2f}")
    else:
        exit_text = "outside the entry window — no new position (07:00–11:20 ET)"
        order_line = "no entry now"
    return Ticket(
        session=session, trigger=trigger, limit=limit, stop=stop, risk_share=rps,
        target_2r=target, dollar_risk=dollar_risk, shares=shares, bound_by=bound,
        reserve=reserve, spread=spread, notional_worst=round(shares * limit, 2),
        max_notional=max_notional, loss_at_stop=round(shares * rps, 2),
        loss_worst=round(shares * (limit - stop + sp + COMMISSION_RESERVE_PER_SHARE), 2),
        stop_pct=stop_pct, exit_text=exit_text, order_line=order_line, checks=checks)


def entry_session(t: time) -> Optional[str]:
    """Which session a NEW entry placed at ET wall-clock `t` belongs to, under
    the bot's clock: pre-market 07:00–09:30, regular 09:30–11:20 (A8), else
    None. Weekends and holidays are the caller's business."""
    if PREMARKET_START <= t < time(9, 30):
        return "premarket"
    if time(9, 30) <= t < ENTRY_CUTOFF:
        return "regular"
    return None


@dataclass
class Position:
    """A manual position's live levels, under the bot's exit rule (A3)."""

    entry: float
    stop: float
    shares: int
    risk_share: float
    high_since: float
    trail: float                 # max(stop, high_since − TRAIL_R × risk)
    target_2r: float
    last: Optional[float]
    r_now: Optional[float]
    pnl: Optional[float]
    breach: Optional[str]        # "stop" | "trail" | "2R" | None

    def to_dict(self) -> dict:
        return asdict(self)


def position(entry: float, stop: float, shares: int, high_since: Optional[float],
             last: Optional[float]) -> Optional[Position]:
    """Where a manual position stands, read with the bot's own exit rule:
    the stop trails TRAIL_R initial risks under the high since the entry and
    never moves down (A3). `breach` names the level the last price is
    through, worst first, so an alert can say which one."""
    if entry <= 0 or stop <= 0 or stop >= entry or shares <= 0:
        return None
    rps = round(entry - stop, 4)
    hi = max(entry, high_since or entry)
    trail = round(max(stop, hi - TRAIL_R * rps), 2)
    target = round(entry + 2.0 * rps, 2)
    r_now = round((last - entry) / rps, 2) if last is not None else None
    pnl = round((last - entry) * shares, 2) if last is not None else None
    breach = None
    if last is not None:
        if last <= stop:
            breach = "stop"
        elif trail > stop and last <= trail:
            breach = "trail"
        elif last >= target:
            breach = "2R"
    return Position(entry=entry, stop=stop, shares=shares, risk_share=rps, high_since=hi,
                    trail=trail, target_2r=target, last=last, r_now=r_now, pnl=pnl, breach=breach)
