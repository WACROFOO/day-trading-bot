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
    EntryIntent, PlacedOrder, in_premarket, in_regular_hours, refusals,
    session_for, shares_for,
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


# ------------------------------------------------------ the two sessions
def test_session_boundaries():
    assert in_regular_hours(RTH) is True
    assert in_premarket(PREMARKET) is True
    assert session_for(RTH) == "regular"
    assert session_for(PREMARKET) == "premarket"

    # 07:00 opens pre-market, 09:30 closes it and opens regular, 16:00 ends.
    b = lambda h, m: dt.datetime(2026, 9, 8, h, m, tzinfo=ET)      # noqa: E731
    assert session_for(b(6, 59)) is None
    assert session_for(b(7, 0)) == "premarket"
    assert session_for(b(9, 29)) == "premarket"
    assert session_for(b(9, 30)) == "regular"
    assert session_for(b(15, 59)) == "regular"
    assert session_for(b(16, 0)) is None
    assert session_for(SUNDAY) is None          # weekends are not a session


def test_a_premarket_intent_is_allowed_in_premarket():
    """He trades it, so the executor must. `PARAMETERS.md` §2 puts the
    personal window at 07:00-11:00, and the July 2026 challenge names 07:00
    78 times against 36 for 09:30."""
    assert refusals(intent(session="premarket"), now=PREMARKET) == []


def test_a_regular_intent_arriving_premarket_is_refused_not_converted():
    """Converting it would decide, for the caller, to trade a session they
    did not choose — and a regular bracket pre-market is the queued-to-09:30
    order that looks accepted."""
    r = refusals(intent(session="regular"), now=PREMARKET)
    assert any("outside 09:30-16:00" in x for x in r)


def test_a_premarket_intent_arriving_in_rth_is_refused_too():
    """The check runs both ways. A stale pre-market plan fired at 10:00 has
    outsideRth on every leg and is not the order anyone reviewed."""
    r = refusals(intent(session="premarket"), now=RTH)
    assert any("outside 07:00-09:30" in x for x in r)


def test_no_session_trades_outside_both_windows():
    for clock in (SUNDAY, dt.datetime(2026, 9, 8, 5, 0, tzinfo=ET),
                  dt.datetime(2026, 9, 8, 16, 30, tzinfo=ET)):
        for sess in ("regular", "premarket"):
            assert refusals(intent(session=sess), now=clock) != []


def test_an_unknown_session_is_refused():
    assert any("outside the 07:00-16:00 ET session window" in x
               for x in refusals(intent(session="afterhours"), now=RTH))


# ------------------------------------------------ pre-market protection
def test_a_premarket_entry_is_not_claimed_protected_when_placed():
    """The corpus says no stop of any type rests in extended hours, and IBKR
    queues rather than rejects what it will not work. Until `premarket_probe`
    settles whether IBKR's simulated stop is the exception, a pre-market
    entry must not claim protection it cannot demonstrate."""
    rec = PlacedOrder(symbol="TEST", parent_id=1, trigger=5.0, stop=4.8,
                      shares=100)
    assert rec.protected is False           # the default is unprotected


def test_the_bracket_flags_outside_rth_only_for_a_premarket_intent():
    pytest.importorskip("ib_async")

    class FakeClient:
        def __init__(self): self.n = 100
        def getReqId(self): self.n += 1; return self.n

    t = PaperTrader()
    t.ib = type("FakeIB", (), {"client": FakeClient()})()

    for leg in t._bracket(intent(session="premarket", target=5.6)):
        assert leg.outsideRth is True

    # Regular hours stays False on purpose: a DAY order still open at 16:00
    # must die, not follow the name into after hours.
    for leg in t._bracket(intent(session="regular", target=5.6)):
        assert leg.outsideRth is False


# ------------------------------------------------------- day trades only
def test_flatten_refuses_to_guess_a_price_outside_regular_hours():
    """No market orders exist in extended hours, and prices never come from
    the order session. Refusing beats inventing a level."""
    pytest.importorskip("ib_async")

    class FakePos:
        position = 100
        contract = type("C", (), {"symbol": "TEST"})()

    class FakeIB:
        def positions(self): return [FakePos()]
        def openTrades(self): return []
        def cancelOrder(self, o): pass

    t = PaperTrader()
    t.ib = FakeIB()
    with pytest.raises(RuntimeError, match="without a quote"):
        t.flatten_all(now=PREMARKET)


def test_flatten_sells_at_bid_minus_offset_outside_regular_hours():
    """The skill's fill trick, run backwards: "sell = bid - offset"."""
    pytest.importorskip("ib_async")

    sent = []

    class FakePos:
        position = 100
        contract = type("C", (), {"symbol": "TEST"})()

    class FakeIB:
        def positions(self): return [FakePos()]
        def openTrades(self): return []
        def cancelOrder(self, o): pass
        def placeOrder(self, c, o): sent.append(o)

    t = PaperTrader()
    t.ib = FakeIB()
    done = t.flatten_all(quote=lambda s: (4.50, 4.60), now=PREMARKET)

    assert done == ["TEST x100 LMT"]
    assert sent[0].lmtPrice == 4.40          # bid 4.50 - 10c
    assert sent[0].outsideRth is True


def test_flatten_uses_a_market_order_inside_regular_hours():
    pytest.importorskip("ib_async")
    sent = []

    class FakePos:
        position = 100
        contract = type("C", (), {"symbol": "TEST"})()

    class FakeIB:
        def positions(self): return [FakePos()]
        def openTrades(self): return []
        def cancelOrder(self, o): pass
        def placeOrder(self, c, o): sent.append(o)

    t = PaperTrader()
    t.ib = FakeIB()
    assert t.flatten_all(now=RTH) == ["TEST x100 MKT"]
    assert sent[0].orderType == "MKT"


def test_flatten_routes_the_sell_on_smart_not_on_the_position_contract():
    """GRML x62, 2026-09-22 11:30: the market sell went on `pos.contract`,
    whose exchange is NASDAQ — a direct-routed order the API's precautionary
    settings rejected (10311). The stop had already been cancelled; the
    position sat naked. Every flatten sell now goes on a SMART contract."""
    pytest.importorskip("ib_async")
    sent = []

    class FakePos:
        position = 62
        contract = type("C", (), {"symbol": "GRML", "exchange": "NASDAQ"})()

    class FakeIB:
        def positions(self): return [FakePos()]
        def openTrades(self): return []
        def cancelOrder(self, o): pass
        def qualifyContracts(self, *c): return list(c)
        def placeOrder(self, c, o): sent.append((c, o))

    t = PaperTrader()
    t.ib = FakeIB()
    assert t.flatten_all(now=RTH) == ["GRML x62 MKT"]
    c, o = sent[0]
    assert c.exchange == "SMART" and c.symbol == "GRML" and c.currency == "USD"
    assert c is not FakePos.contract
    t.ib = FakeIB(); sent.clear()
    t.flatten_all(quote=lambda s: (4.50, 4.60), now=PREMARKET)
    assert sent[0][0].exchange == "SMART" and sent[0][1].orderType == "LMT"


def test_exit_market_sells_on_smart_inside_regular_hours_and_refuses_outside():
    """The manual exit that needs no desk quote, for the ExitFailed row."""
    pytest.importorskip("ib_async")
    sent = []

    class FakeIB:
        client = type("Cl", (), {"getReqId": staticmethod(lambda: 4242)})()
        def qualifyContracts(self, *c): return list(c)
        def placeOrder(self, c, o): sent.append((c, o))

    t = PaperTrader()
    t.ib = FakeIB()
    assert t.exit_market("GRML", 62, now=RTH) == 4242
    c, o = sent[0]
    assert (c.exchange, o.orderType, o.action, o.totalQuantity) == ("SMART", "MKT", "SELL", 62)
    assert t.last_exit_order_id == 4242
    with pytest.raises(RuntimeError, match="outside regular hours"):
        t.exit_market("GRML", 62, now=PREMARKET)
    assert len(sent) == 1
    with pytest.raises(ValueError):
        t.exit_market("GRML", 0, now=RTH)


# ------------------------------------------------------ the hard stop
def test_no_new_entry_after_the_1130_hard_stop():
    """`PARAMETERS.md` §2: `session_close` 11:30 "outer edge, not the
    centre", `midday_avoid` 11:30-15:00 "no trades".

    The cascade will not catch this. An out-of-window name comes back
    Verdict.LOG with plan_allowed True — correct for the cascade, since a
    downgrade is not a kill — so an executor reading only plan_allowed would
    open a position at 14:00."""
    late = dt.datetime(2026, 9, 8, 14, 0, tzinfo=ET)
    assert any("hard stop" in x for x in refusals(intent(), now=late))


def test_1119_still_trades_1120_and_1129_do_not_a8():
    """Amendment A8 (owner decision, delegated, 2026-09-22): GRML filled at
    11:28 and was force-flattened at 11:30. No new entry inside the last ten
    minutes before the hard stop; the refusal names A8, and 11:30 onward
    still names the hard stop itself."""
    assert refusals(intent(), now=dt.datetime(2026, 9, 8, 11, 19, tzinfo=ET)) == []
    r = refusals(intent(), now=dt.datetime(2026, 9, 8, 11, 20, tzinfo=ET))
    assert r and "A8" in r[0] and "last 10 minutes" in r[0]
    r = refusals(intent(), now=dt.datetime(2026, 9, 8, 11, 29, tzinfo=ET))
    assert r and "A8" in r[0]
    r = refusals(intent(), now=dt.datetime(2026, 9, 8, 11, 30, tzinfo=ET))
    assert r and "hard stop" in r[0] and "A8" not in r[0]


def test_the_hard_stop_does_not_reach_back_into_the_premarket_session():
    assert refusals(intent(session="premarket"), now=PREMARKET) == []


def test_the_account_bounds_the_size_and_a_rejected_order_is_dead():
    """VEEE, 2026-09-21 09:37: 2-cent stop, 1,000 shares, $16,330 on $2,288 of
    equity, rejected by IBKR (201). The stop defines the size; the account
    bounds it — and fewer shares is LESS risk, never more."""
    from execution.intent import EntryIntent, refusals, shares_for, sized_for
    assert shares_for(16.33, 16.31, 20.0) == 1000
    n, by = sized_for(16.33, 16.31, 20.0, max_notional=2288.0)
    assert n == 140 and by == "funds"
    assert n * 16.33 <= 2288.0 and n * 0.02 < 20.0
    assert sized_for(6.00, 5.80, 20.0, max_notional=2288.0) == (100, "risk")
    big = EntryIntent(symbol="VEEE", trigger=16.33, stop=16.31, shares=1000, dollar_risk=20.0,
                      plan_allowed=True, max_notional=2288.0)
    assert any("exceeds what the account can hold" in r for r in refusals(big))


def test_ibkr_inactive_means_rejected_and_does_not_hold_the_one_position_rule():
    from journal import ledger as L
    conn = L.connect(":memory:")
    conn.execute("""INSERT INTO decisions (decision_id, ts_et, session, symbol, source, verdict,
                    killed_by, plan_allowed, gates_json, warnings_json, inputs_json, recorded_at)
                    VALUES ('d1', '2026-09-21T09:37:00-04:00', 'regular', 'VEEE', 'pullback',
                            'REVIEW', NULL, 1, '[]', '[]', '{}', 'x')""")
    oid = L.record_order(conn, "d1", symbol="VEEE", account="DUR339781", session="regular",
                         parent_id=4, stop_id=5, target_id=None, trigger=16.33, stop=16.31,
                         target=None, shares=1000, dollar_risk=20.0, protected=True)
    assert L.positions_alive(conn) == 1
    conn.execute("UPDATE orders SET status='Inactive' WHERE order_id=?", (oid,))
    assert L.positions_alive(conn) == 0
    assert L.open_orders(conn) == []


# ------------------------------------------------------ A3: moving the stop leg
def test_move_stop_reprices_the_resting_stop_leg_in_place():
    """Same order id, new auxPrice, transmitted: IBKR's modify. The stop never
    stops resting, and the record remembers where it sits now."""
    pytest.importorskip("ib_async")
    from ib_async import StopOrder
    sent = []
    stop = StopOrder("SELL", 100, 4.40); stop.orderId = 202; stop.parentId = 101

    class Status:
        status = "Submitted"

    class Trade:
        order = stop
        contract = type("C", (), {"symbol": "TEST"})()
        orderStatus = Status()

    class FakeIB:
        def trades(self): return [Trade()]
        def placeOrder(self, c, o): sent.append((c, o))

    t = PaperTrader()
    t.ib = FakeIB()
    rec = PlacedOrder(symbol="TEST", parent_id=101, stop_id=202, trigger=4.60, stop=4.40, shares=100)
    assert t.move_stop(rec, 4.55) == 202
    assert sent[0][1] is stop and stop.auxPrice == 4.55 and stop.transmit is True
    assert rec.trail_stop == 4.55 and any("A3" in e for e in rec.events)


def test_move_stop_refuses_a_leg_that_is_gone():
    pytest.importorskip("ib_async")

    class FakeIB:
        def trades(self): return []
        def placeOrder(self, c, o): raise AssertionError("nothing may be sent")

    t = PaperTrader()
    t.ib = FakeIB()
    rec = PlacedOrder(symbol="TEST", parent_id=101, stop_id=202, trigger=4.60, stop=4.40, shares=100)
    with pytest.raises(RuntimeError):
        t.move_stop(rec, 4.55)
    assert rec.trail_stop is None


def test_a_raised_stop_that_fills_is_the_trailing_exit():
    """sync() names the exit: a stop the runner moved above the initial stop
    is 'trail', so the ledger can split the two rules."""
    pytest.importorskip("ib_async")
    from ib_async import LimitOrder, StopOrder

    parent = LimitOrder("BUY", 100, 4.60); parent.orderId = 101
    stop = StopOrder("SELL", 100, 4.55); stop.orderId = 202; stop.parentId = 101

    class Status:
        def __init__(self, status, px, filled=100):
            self.status, self.avgFillPrice, self.filled = status, px, filled

    class Trade:
        def __init__(self, order, status):
            self.order, self.orderStatus, self.log = order, status, []

    class FakeIB:
        def sleep(self, s): pass
        def trades(self): return [Trade(parent, Status("Filled", 4.61)), Trade(stop, Status("Filled", 4.54))]

    t = PaperTrader()
    t.ib = FakeIB()
    rec = PlacedOrder(symbol="TEST", parent_id=101, stop_id=202, trigger=4.60, stop=4.40, shares=100)
    rec.trail_stop = 4.55
    t.placed.append(rec)
    t.sync()
    assert rec.exit_reason == "trail" and rec.exit_price == 4.54


# ------------------------------------------------------ 2026-09-22: the stop that died
def test_a_bracket_without_a_target_has_no_oca_group_so_the_stop_can_be_modified():
    """DCOY 09:36: IBKR 10326 "OCA group revision is not allowed" cancelled the
    stop when the trail first moved it. With one exit leg an OCA group has no
    purpose and forbids the modify."""
    pytest.importorskip("ib_async")

    class Client:
        _n = 100
        def getReqId(self): Client._n += 1; return Client._n

    class FakeIB:
        client = Client()

    t = PaperTrader(); t.ib = FakeIB()
    intent = EntryIntent(symbol="TEST", trigger=6.0, stop=5.5, shares=41, dollar_risk=20.0,
                         plan_allowed=True, verdict="REVIEW", session="regular")
    parent, stop_leg, target_leg = t._bracket(intent)
    assert target_leg is None and not getattr(stop_leg, "ocaGroup", "") and stop_leg.parentId == parent.orderId
    with_target = EntryIntent(symbol="TEST", trigger=6.0, stop=5.5, shares=41, dollar_risk=20.0,
                              plan_allowed=True, verdict="REVIEW", session="regular", target=7.0)
    _, stop2, target2 = t._bracket(with_target)
    assert target2 is not None and stop2.ocaGroup == target2.ocaGroup != ""


def test_move_stop_on_an_oca_leg_places_the_new_stop_before_cancelling_the_old():
    pytest.importorskip("ib_async")
    from ib_async import StopOrder
    sent, cancelled = [], []
    stop = StopOrder("SELL", 41, 5.50); stop.orderId = 11; stop.parentId = 10; stop.ocaGroup = "px-old"

    class Status:
        status = "PreSubmitted"

    class Trade:
        order = stop
        contract = type("C", (), {"symbol": "DCOY"})()
        orderStatus = Status()

    class Client:
        _n = 200
        def getReqId(self): Client._n += 1; return Client._n

    class FakeIB:
        client = Client()
        def trades(self): return [Trade()]
        def qualifyContracts(self, c): return [c]
        def placeOrder(self, c, o): sent.append(o)
        def cancelOrder(self, o): cancelled.append(o)

    t = PaperTrader(); t.ib = FakeIB()
    rec = PlacedOrder(symbol="DCOY", parent_id=10, stop_id=11, trigger=5.98, stop=5.50, shares=41)
    new_id = t.move_stop(rec, 5.52)
    assert sent and sent[0].orderType == "STP" and sent[0].auxPrice == 5.52 and sent[0].totalQuantity == 41
    assert not getattr(sent[0], "ocaGroup", "")
    assert cancelled == [stop] and rec.stop_id == new_id != 11 and rec.trail_stop == 5.52
