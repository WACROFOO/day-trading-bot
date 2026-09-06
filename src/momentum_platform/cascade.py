"""The reject cascade — the single authority on whether a name is tradeable.

`knowledge-base/strategies/FILTERS.md` Layer 1 opens:

    "Float and price KILL a name BEFORE you look at a chart. That is the
     whole trick, and it is why this runs on published metrics."

The desk did not do that. `dashboard/web/app.js:1350` summed four booleans:

    const technical = [priceOk, gainOk, rvolOk, floatOk].filter(Boolean).length;
    if (technical <= 2) blockers.push("Only " + technical + "/4 …");

A score, not a cascade — so 3-of-4 was merely a WAIT, and a name that failed
the price gate outright still had an entry, a stop and a 2R target computed
and drawn. Observed on IMRN, 2026-09-04: last $1.69 against a $2-20 band,
234.0M shares outstanding against a <20M float gate, halted, and the card
still read `Entry 1.75 ARMED · Stop 1.71`.

Three rules this module exists to enforce:

1.  **A kill is terminal.** `plan_allowed` is False the moment any Layer 1
    gate kills, and no caller may draw a plan against a killed name.
2.  **Six states, not two.** Anything not positively established fails
    closed. An over-cap shares-outstanding bound is
    MANUAL_CONFIRMATION_REQUIRED — it is genuinely unknown, and rendering it
    as a quiet UNKNOWN let the cascade walk past it.
3.  **One word, one meaning.** The desk showed a red banner reading
    "PASS — reject this candidate" above rows whose green "PASS" meant the
    opposite. The reject verdict is REJECT here and nowhere is PASS a verdict.

This module is deliberately pure: no I/O, no clock, no feed. Everything it
needs arrives in `Inputs`, which makes the whole cascade testable against
FILTERS.md without a market.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class GateState(str, Enum):
    """Six states. `UNKNOWN` and `MANUAL_CONFIRMATION_REQUIRED` differ: the
    first is 'we have no value', the second is 'we have a value that cannot
    settle the question'. Collapsing them is how an over-cap float bound got
    treated as merely missing."""

    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    MANUAL_CONFIRMATION_REQUIRED = "MANUAL_CONFIRMATION_REQUIRED"


class Verdict(str, Enum):
    """Non-actionable vocabulary. `REVIEW` means go read the chart yourself —
    it is not an instruction to buy, and the rename from SETUP happened
    because the old word was read as one."""

    STALE = "STALE"
    REJECT = "REJECT"
    WATCH = "WATCH"
    WAIT = "WAIT"
    REVIEW = "REVIEW"
    LOG = "LOG"


@dataclass(frozen=True)
class Gate:
    id: str
    label: str
    state: GateState
    value: str
    reason: str = ""
    kills: bool = False

    #: States that stop the cascade when a gate is marked `kills`.
    #: FAIL is obvious. The other two are the point: "we could not establish
    #: this" must fail CLOSED on a killing gate, or an unknown float and an
    #: over-cap shares-outstanding bound both walk straight through — which is
    #: precisely how the desk armed a plan on a name showing 234.0M shares.
    _TERMINAL = (GateState.FAIL, GateState.UNKNOWN,
                 GateState.MANUAL_CONFIRMATION_REQUIRED)

    @property
    def killed(self) -> bool:
        return self.kills and self.state in self._TERMINAL


@dataclass
class Inputs:
    """Everything the cascade needs. Absent values are None, never guessed."""

    symbol: str
    last: Optional[float] = None
    prev_close: Optional[float] = None
    change_pct: Optional[float] = None
    session_high: Optional[float] = None          # pre-market or day high
    float_shares: Optional[float] = None
    float_is_shares_outstanding: bool = False     # an UPPER BOUND, not float
    float_verified: bool = False
    catalyst_today: bool = False
    live_theme: bool = False                      # a running theme substitutes
    is_fund_or_etf: Optional[bool] = None
    tick_size: Optional[float] = None
    buyout_announced: bool = False
    split_ratio_clean_integer: Optional[float] = None   # from split_check()
    penny_theme: bool = False                     # softens the $2 floor
    # Layer 2 / Layer 3
    above_vwap: Optional[bool] = None
    above_ema9: Optional[bool] = None
    macd_positive_and_above_signal: Optional[bool] = None
    session_volume: Optional[float] = None
    rvol: Optional[float] = None
    premarket_volume: Optional[float] = None
    halted: bool = False
    feed_stale: bool = False
    in_session_window: bool = True


@dataclass
class CascadeResult:
    verdict: Verdict
    killed_by: Optional[str]
    gates: list[Gate] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def plan_allowed(self) -> bool:
        """No entry, stop or target may be computed or drawn when False."""
        return self.killed_by is None and self.verdict is not Verdict.STALE


# --- FILTERS.md Layer 0/1 constants. Change them THERE first, not here. -----
PRICE_MIN = 2.00
PRICE_MAX = 20.00
PRICE_MIN_PENNY_THEME = 1.50      # "the floor moves to roughly $1.50"
FLOAT_MAX = 20_000_000
FADE_MAX_PCT = 25.0
SESSION_VOLUME_FLOOR = 1_000_000  # Layer 3, measured against his broker split
RVOL_TRADE_FLOOR = 1.5            # NOT the 5x scanner dial
PREMARKET_VOLUME_CEILING = 1_000_000   # a ceiling with NO floor


def evaluate(i: Inputs) -> CascadeResult:
    """Run the cascade in FILTERS.md's own order and stop at the first kill.

    Gates after a kill are still reported, as NOT_APPLICABLE, so the operator
    can see the cascade stopped rather than that the checks silently vanished.
    """
    gates: list[Gate] = []
    reasons: list[str] = []
    warnings: list[str] = []
    killed_by: Optional[str] = None

    def add(gate: Gate) -> None:
        nonlocal killed_by
        gates.append(gate)
        if killed_by is None and gate.killed:
            killed_by = gate.id
            reasons.append(gate.reason or f"{gate.label} killed the name.")

    def skipped(gid: str, label: str) -> Gate:
        return Gate(gid, label, GateState.NOT_APPLICABLE, "—",
                    "cascade already stopped")

    # A stale feed decides nothing. Rendering a verdict on data the desk
    # itself flags as behind is how a screenshot reads "1D BEHIND" and shows
    # an armed plan in the same frame.
    if i.feed_stale:
        return CascadeResult(
            Verdict.STALE, None,
            [Gate("feed", "Feed", GateState.STALE, "behind",
                  "The feed is stale; no verdict is computed on it.")],
            ["The feed is stale. No verdict is computed on stale data."])

    # -- gate 1 · price -----------------------------------------------------
    floor = PRICE_MIN_PENNY_THEME if i.penny_theme else PRICE_MIN
    if i.last is None:
        add(Gate("price", "Price", GateState.UNKNOWN, "—",
                 "No price. Nothing downstream can be trusted.", kills=True))
    else:
        ok = floor <= i.last <= PRICE_MAX
        note = f"${i.last:.2f}  band ${floor:.2f}–{PRICE_MAX:.2f}"
        if i.penny_theme:
            note += " (penny-theme floor)"
        add(Gate("price", "Price", GateState.PASS if ok else GateState.FAIL,
                 note,
                 f"${i.last:.2f} is outside ${floor:.2f}–{PRICE_MAX:.2f}.",
                 kills=True))

    # -- gate 2 · float -----------------------------------------------------
    # Shares outstanding is an UPPER BOUND on float, never float itself.
    # Under the cap it proves float is under the cap. Over the cap it proves
    # nothing either way — which is a question for a human, not a pass.
    if killed_by:
        gates.append(skipped("float", "Float"))
    elif i.float_shares is None:
        add(Gate("float", "Float", GateState.UNKNOWN, "unknown",
                 "Float unknown; the cascade fails closed.", kills=True))
    elif i.float_shares < FLOAT_MAX:
        src = "verified" if i.float_verified else (
            "SO upper bound" if i.float_is_shares_outstanding else "reported")
        add(Gate("float", "Float", GateState.PASS,
                 f"{i.float_shares / 1e6:.1f}M ({src})"))
    elif i.float_is_shares_outstanding:
        add(Gate("float", "Float", GateState.MANUAL_CONFIRMATION_REQUIRED,
                 f"{i.float_shares / 1e6:.1f}M shares outstanding",
                 f"{i.float_shares / 1e6:.1f}M outstanding is an upper bound "
                 "over the 20M cap — it proves nothing either way. Verify the "
                 "float by hand.", kills=True))
    else:
        add(Gate("float", "Float", GateState.FAIL,
                 f"{i.float_shares / 1e6:.1f}M",
                 f"Float {i.float_shares / 1e6:.1f}M is over the 20M cap.",
                 kills=True))

    # -- gate 3 · catalyst (a live theme substitutes) -----------------------
    if killed_by:
        gates.append(skipped("catalyst", "Catalyst"))
    elif i.catalyst_today or i.live_theme:
        add(Gate("catalyst", "Catalyst", GateState.PASS,
                 "news today" if i.catalyst_today else "live theme"))
    else:
        add(Gate("catalyst", "Catalyst", GateState.FAIL, "none",
                 "No catalyst dated today and no live theme it belongs to.",
                 kills=True))

    # -- gate 4 · still rising ---------------------------------------------
    if killed_by:
        gates.append(skipped("rising", "Still rising"))
    elif i.session_high is None or i.last is None or i.session_high <= 0:
        add(Gate("rising", "Still rising", GateState.UNKNOWN, "—"))
        warnings.append("No session high; the fade check could not run.")
    else:
        fade = 100.0 * (i.session_high - i.last) / i.session_high
        add(Gate("rising", "Still rising",
                 GateState.PASS if fade <= FADE_MAX_PCT else GateState.FAIL,
                 f"{fade:.1f}% off {i.session_high:.2f}",
                 f"{fade:.1f}% off the high — back side of the move.",
                 kills=True))

    # -- gate 5 · reverse split (arithmetic only) ---------------------------
    # The veto's premise is that the gap IS the split. That is only true when
    # the ratio is a clean integer. MSGY 2026-08-11 was rejected on this gate
    # without its precondition and ran 2.54 -> 5.43.
    if killed_by:
        gates.append(skipped("split", "Reverse split"))
    elif i.split_ratio_clean_integer:
        add(Gate("split", "Reverse split", GateState.FAIL,
                 f"ratio {i.split_ratio_clean_integer:g}",
                 f"The gap is the split ({i.split_ratio_clean_integer:g}x), "
                 "not a move.", kills=True))
    else:
        add(Gate("split", "Reverse split", GateState.PASS,
                 "gap is not arithmetic"))

    # -- gate 6 · instrument ------------------------------------------------
    if killed_by:
        gates.append(skipped("instrument", "Instrument"))
    elif i.is_fund_or_etf is None:
        add(Gate("instrument", "Instrument", GateState.UNKNOWN, "—"))
        warnings.append("Instrument type unknown — ADRs are fine, funds are not.")
    else:
        add(Gate("instrument", "Instrument",
                 GateState.FAIL if i.is_fund_or_etf else GateState.PASS,
                 "fund/ETF" if i.is_fund_or_etf else "common stock / ADR",
                 "Funds and ETFs are out.", kills=True))

    # -- gate 7 · tick size -------------------------------------------------
    if killed_by:
        gates.append(skipped("tick", "Tick size"))
    elif i.tick_size is None:
        add(Gate("tick", "Tick size", GateState.UNKNOWN, "—"))
    else:
        add(Gate("tick", "Tick size",
                 GateState.FAIL if i.tick_size >= 0.05 else GateState.PASS,
                 f"${i.tick_size:g}",
                 f"Quotes in ${i.tick_size:g} increments.", kills=True))

    # -- gate 8 · buyout ----------------------------------------------------
    if killed_by:
        gates.append(skipped("buyout", "Buyout"))
    else:
        add(Gate("buyout", "Buyout",
                 GateState.FAIL if i.buyout_announced else GateState.PASS,
                 "announced" if i.buyout_announced else "none",
                 "Acquisition announced — the price is pinned and volatility "
                 "is gone.", kills=True))

    if killed_by:
        return CascadeResult(Verdict.REJECT, killed_by, gates, reasons, warnings)

    # ---------------------------------------------------------------- Layer 2
    # Chart gates do NOT kill: they decide WAIT vs REVIEW. A name that fails
    # them is still the right name, just not yet.
    chart_unknown = False
    for gid, label, val in (("vwap", "Above VWAP", i.above_vwap),
                            ("ema9", "Above 9 EMA", i.above_ema9),
                            ("macd", "MACD +ve & > signal",
                             i.macd_positive_and_above_signal)):
        if val is None:
            gates.append(Gate(gid, label, GateState.UNKNOWN, "—"))
            chart_unknown = True
        else:
            gates.append(Gate(gid, label,
                              GateState.PASS if val else GateState.FAIL,
                              "yes" if val else "no"))

    # Tape and Level 2 are the operator's. Rendered, never omitted — hiding a
    # check the tool cannot perform is the silent-filter anti-pattern.
    gates.append(Gate("tape", "Tape · Level 2",
                      GateState.MANUAL_CONFIRMATION_REQUIRED, "your eyes",
                      "No tape and no book in this tool."))

    # ---------------------------------------------------------------- Layer 3
    if i.session_volume is not None and i.session_volume < SESSION_VOLUME_FLOOR:
        warnings.append(
            f"Session volume {i.session_volume / 1e6:.2f}M is under the 1M "
            "floor — the band he measured himself losing in.")
    if i.rvol is not None and i.rvol < RVOL_TRADE_FLOOR:
        warnings.append(f"RVOL {i.rvol:.2f}x is under the 1.5x trade floor "
                        "(the 5x is a scanner dial, not a gate).")
    if (i.premarket_volume is not None
            and i.premarket_volume > PREMARKET_VOLUME_CEILING):
        warnings.append(
            f"Pre-market volume {i.premarket_volume / 1e6:.2f}M is over the ~1M "
            "ceiling — you are not the first to see it. This is a CEILING; "
            "there is no floor.")

    # ---------------------------------------------------------------- verdict
    if i.halted:
        reasons.append("Halted — no plan survives a reopen at an unknown price.")
        return CascadeResult(Verdict.WAIT, None, gates, reasons, warnings)

    chart_fail = any(g.state is GateState.FAIL
                     for g in gates if g.id in ("vwap", "ema9", "macd"))
    if chart_fail:
        reasons.append("Every Layer 1 gate passed; the chart is not there yet.")
        return CascadeResult(Verdict.WAIT, None, gates, reasons, warnings)
    if chart_unknown:
        reasons.append("Layer 1 passed; a chart gate could not be evaluated.")
        return CascadeResult(Verdict.WATCH, None, gates, reasons, warnings)

    if not i.in_session_window:
        reasons.append("All gates green, but outside the session window.")
        return CascadeResult(Verdict.LOG, None, gates, reasons, warnings)

    reasons.append("Every evaluable gate is green. Go read the chart, the tape "
                   "and the book yourself.")
    return CascadeResult(Verdict.REVIEW, None, gates, reasons, warnings)
