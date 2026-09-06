"""The order path may not reach real money, and may not send a killed plan.

Everything here that does not need a Gateway runs everywhere. The two tests
that need `ib_async` skip rather than pretend.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from execution.intent import (  # noqa: E402
    EntryIntent, PlacedOrder, in_regular_hours, refusals, shares_for,
)
from execution.ibkr_trader import (  # noqa: E402
    NotPaperError, OrderRefused, PaperTrader, assert_paper,
)


# Tuesday 2026-09-08, 10:15 ET — inside the prime window, so the session
# gate is never what an unrelated test is accidentally measuring. Every
# refusal test pins the clock; none of them read wall time.
ET = ZoneInfo("America/New_York")
RTH = dt.datetime(2026, 9, 8, 10, 15, tzinfo=ET)
PREMARKET = dt.datetime(2026, 9, 8, 9, 15, tzinfo=ET)
SUNDAY = dt.datetime(2026, 9, 6, 10, 15, tzinfo=ET)


def why(**over) -> list[str]:
    """Refusals for an otherwise-clean intent, at a fixed RTH clock."""
    return refusals(intent(**over), now=RTH)


def intent(**over) -> EntryIntent:
    base = dict(symbol="TEST", trigger=5.00, stop=4.80, shares=100,
                dollar_risk=25.0, plan_allowed=True, verdict="REVIEW")
    base.update(over)
    return EntryIntent(**base)


# ------------------------------------------------------------- paper only
def test_a_live_account_is_refused():
    with pytest.raises(NotPaperError, match="not a paper account"):
        assert_paper(["U1234567"])


def test_the_users_own_paper_account_is_accepted():
    assert assert_paper(["DUR339781"]) == "DUR339781"


def test_no_account_is_refused_rather_than_assumed_safe():
    """An empty list is not evidence of safety, it is evidence of confusion."""
    for empty in ([], None, [""]):
        with pytest.raises(NotPaperError):
            assert_paper(empty)


def test_one_live_account_among_paper_ones_still_refuses():
    with pytest.raises(NotPaperError):
        assert_paper(["DUR339781", "U1234567"])


def test_there_is_no_switch_that_permits_a_live_account():
    """If this ever becomes configurable, that is the bug."""
    src = (ROOT / "src/execution/ibkr_trader.py").read_text()
    assert 'PAPER_PREFIX = "DU"' in src
    for escape in ("allow_live", "ALLOW_LIVE", "force=", "skip_paper"):
        assert escape not in src


# ------------------------------------------------- refusing bad intents
def test_a_clean_intent_is_sendable():
    assert why() == []


def test_a_cascade_kill_forbids_the_order():
    """IMRN with a broker attached. The cascade is upstream and it wins."""
    r = why(plan_allowed=False, verdict="REJECT")
    assert any("cascade forbids" in x for x in r)


def test_a_stop_above_the_entry_is_refused():
    assert any("not below trigger" in x for x in why(trigger=5.00, stop=5.20))


def test_a_stop_equal_to_the_entry_is_refused():
    """Zero risk per share would divide the whole R accounting by zero."""
    assert any("not below trigger" in x for x in why(trigger=5.00, stop=5.00))


def test_zero_shares_is_not_an_order():
    assert any("not an order" in x for x in why(shares=0))


def test_oversized_risk_is_refused_against_the_stated_dollar_risk():
    # 100 shares x $0.20 = $20 planned against $10 stated
    assert any("exceeds stated" in x for x in why(dollar_risk=10.0))


def test_integer_rounding_overshoot_is_tolerated():
    """Share counts are integers; a few cents over is arithmetic, not error."""
    assert why(trigger=5.00, stop=4.80, shares=100, dollar_risk=19.5) == []


def test_a_target_below_the_entry_is_refused():
    assert any("not above trigger" in x for x in why(target=4.90))


def test_sub_penny_prices_are_caught_here_not_by_the_exchange():
    assert any("tick grid" in x for x in why(trigger=5.001))


def test_all_reasons_are_reported_not_just_the_first():
    """A refused intent is read by a human inside the window it lives in."""
    assert len(why(symbol="", shares=-5, plan_allowed=False)) >= 3


# ------------------------------------------------------------- sizing
def test_the_stop_defines_the_size():
    assert shares_for(trigger=5.00, stop=4.80, dollar_risk=100.0) == 500


def test_sizing_refuses_an_inverted_stop_rather_than_returning_a_short():
    assert shares_for(trigger=4.80, stop=5.00, dollar_risk=100.0) == 0


def test_sizing_never_reads_buying_power():
    """Paper buying power is $14,291 against $2,143 of equity. Fiction."""
    src = (ROOT / "src/execution/intent.py").read_text()
    assert "BuyingPower" not in src and "buying_power" not in src


# ------------------------------------------------ both R denominators
def test_planned_and_realised_risk_are_kept_apart():
    """The study's finding: realised risk ran a median 1.52x planned, and
    reading results in planned R made losses look catastrophic that were
    merely bad. An executor recording one number cannot measure its own
    slippage."""
    rec = PlacedOrder(symbol="TEST", parent_id=1, trigger=5.00, stop=4.80,
                      shares=100)
    assert rec.planned_risk == 20.0
    assert rec.realised_risk is None          # nothing realised yet
    assert rec.slippage_ratio is None

    rec.fill_price = 5.10                     # 10c of slippage through
    assert rec.realised_risk == 30.0
    assert rec.slippage_ratio == 1.5


# ------------------------------------------------------- refusal ordering
def test_a_bad_intent_is_refused_before_the_connection_is_even_needed():
    """Reported as malformed, not as 'not connected'. The message a person
    reads should name what they can fix."""
    t = PaperTrader()
    assert t.ib is None
    with pytest.raises(OrderRefused):
        t.place_bracket(intent(plan_allowed=False), now=RTH)


def test_the_risk_gate_is_consulted_before_anything_is_sent():
    class Latched:
        def assert_can_buy(self):
            raise RuntimeError("day locked")

    t = PaperTrader(risk_gate=Latched())
    with pytest.raises(RuntimeError, match="day locked"):
        t.place_bracket(intent(), now=RTH)   # valid intent, latched day


# ------------------------------------------------------------- the guard
def test_the_desk_never_imports_the_order_path():
    """`momentum_platform` is read-only by construction and two other tests
    prove it. That proof only holds while the desk cannot reach this
    package."""
    offenders = [p.relative_to(ROOT) for p in
                 (ROOT / "src/momentum_platform").rglob("*.py")
                 if "import execution" in p.read_text()
                 or "from execution" in p.read_text()]
    assert not offenders, f"desk modules importing the order path: {offenders}"


# --------------------------------------------------- needs the library
def test_the_bracket_holds_until_the_stop_transmits():
    """Only the last leg carries transmit=True, so a failure partway leaves
    nothing released. An entry that reaches the market without its stop is
    an unprotected position for as long as the gap lasts."""
    pytest.importorskip("ib_async")

    class FakeClient:
        def __init__(self): self.n = 100
        def getReqId(self): self.n += 1; return self.n

    t = PaperTrader()
    t.ib = type("FakeIB", (), {"client": FakeClient()})()

    parent, stop_leg, target_leg = t._bracket(intent(target=5.60))
    assert parent.transmit is False
    assert target_leg.transmit is False
    assert stop_leg.transmit is True
    assert stop_leg.parentId == parent.orderId
    assert target_leg.parentId == parent.orderId
    assert stop_leg.ocaGroup == target_leg.ocaGroup


def test_the_stop_leg_is_not_optional_when_the_target_is():
    pytest.importorskip("ib_async")

    class FakeClient:
        def __init__(self): self.n = 100
        def getReqId(self): self.n += 1; return self.n

    t = PaperTrader()
    t.ib = type("FakeIB", (), {"client": FakeClient()})()

    parent, stop_leg, target_leg = t._bracket(intent(target=None))
    assert target_leg is None
    assert stop_leg is not None and stop_leg.transmit is True


# ------------------------------------------------------ extended hours
def test_regular_hours_detection():
    assert in_regular_hours(RTH) is True
    assert in_regular_hours(PREMARKET) is False
    assert in_regular_hours(SUNDAY) is False
    assert in_regular_hours(dt.datetime(2026, 9, 8, 9, 29, tzinfo=ET)) is False
    assert in_regular_hours(dt.datetime(2026, 9, 8, 9, 30, tzinfo=ET)) is True
    assert in_regular_hours(dt.datetime(2026, 9, 8, 16, 0, tzinfo=ET)) is False


def test_a_premarket_bracket_is_refused_because_the_stop_cannot_rest():
    """`.claude/skills/extended-hours/SKILL.md`: extended hours accept limit
    orders only, and "No stop orders of any type — banned because thin tape
    makes stop hunting trivial [...] Your stop is therefore mental or
    hotkeyed, never resting."

    So a bracket armed at 09:15 is not an early protected entry. IBKR does
    not reject it either — the 2026-09-06 smoke test got warning 399, "your
    order will not be placed at the exchange until 09:30" — which is worse
    than a rejection, because a queued order looks like an accepted one."""
    r = refusals(intent(), now=PREMARKET)
    assert any("resting stop cannot exist" in x for x in r)


def test_the_session_gate_is_not_bypassed_by_a_clean_intent():
    for clock in (PREMARKET, SUNDAY,
                  dt.datetime(2026, 9, 8, 16, 30, tzinfo=ET)):   # after hours
        assert refusals(intent(), now=clock) != []


def test_inside_regular_hours_a_clean_intent_still_passes():
    assert refusals(intent(), now=RTH) == []
