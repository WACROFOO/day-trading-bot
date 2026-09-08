"""The runner acts on every pending decision exactly once, records why it
refused, and in LOG_ONLY mode never opens a connection.

LOG_ONLY tests run against the real replay fixture through the real desk
builder, so the whole path desk -> ledger -> runner is exercised with no
broker. The fixture is SYNTHETIC; nothing here is evidence about a market.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from execution.intent import PlacedOrder  # noqa: E402
from execution.runner import Runner  # noqa: E402
from journal import ledger as L  # noqa: E402
from momentum_platform.dashboard.session_builder import build_session  # noqa: E402

FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"


@pytest.fixture
def journal():
    conn = L.connect(":memory:")
    build_session(FIXTURE, journal=conn)
    # TRADE mode requires a REVIEW verdict (FILTERS.md Layer 2, all true at
    # entry). The synthetic fixture's chart gates land on WATCH/WAIT, so the
    # placement tests here set REVIEW to exercise the order path itself; the
    # Layer 2 refusal has its own test in test_review_fixes.py.
    conn.execute("UPDATE decisions SET verdict='REVIEW' WHERE plan_allowed=1"); conn.commit()
    L.set_state(conn, phase="B")               # entries exist from phase B on (review round 2)
    yield conn
    conn.close()


class FakeTrader:
    """Records what it was asked to place. Never talks to anything."""
    account = "DUR339781"

    def __init__(self):
        self.placed: list[PlacedOrder] = []
        self.intents = []
        self.flattened = False

    def place_bracket(self, intent, now=None):
        self.intents.append(intent)
        rec = PlacedOrder(symbol=intent.symbol, parent_id=100 + len(self.placed),
                          stop_id=200 + len(self.placed), trigger=intent.trigger,
                          stop=intent.stop, shares=intent.shares, protected=True)
        self.placed.append(rec)
        return rec

    def adopt(self, rows): return 0
    def sync(self):
        pass

    def flatten_all(self, quote=None, now=None):
        self.flattened = True
        return ["TEST x100 MKT"]


# ------------------------------------------------------------- LOG_ONLY
def test_log_only_acts_on_every_pending_decision_once_and_opens_nothing(journal):
    before = len(L.pending(journal))
    assert before == 2, "the fixture arms two plans the cascade allows"

    r = Runner(journal, mode="LOG_ONLY", dollar_risk=25.0)
    done = r.step()
    assert len(done) == before
    assert {a.outcome for a in done} <= {"LOG_ONLY", "REFUSED"}
    assert L.pending(journal) == []
    assert r.step() == []                      # nothing left; idempotent


def test_log_only_judges_each_decision_as_of_its_own_bar_not_the_wall_clock(journal):
    """Both fixture plans arm 09:40-09:51 ET on a Tuesday, inside regular
    hours. Replayed on a Sunday they must still be judged as 09:40 plans."""
    r = Runner(journal, mode="LOG_ONLY", dollar_risk=25.0)
    done = r.step()
    for a in done:
        assert not any("outside 09:30" in x for x in a.reasons), a


def test_the_runner_reports_the_symbol_and_levels_not_just_a_hash(journal):
    """An operator watching a morning of these needs to know WHICH name. A
    16-character decision id is unreadable exactly when it matters."""
    a = Runner(journal, mode="LOG_ONLY", dollar_risk=25.0).step()[0]
    assert a.symbol and a.symbol.isupper()
    assert a.trigger > 0 and a.stop > 0 and a.ts_et.startswith("2026-09-01T")


def test_a_refusal_records_its_reasons_verbatim(journal):
    # $1 of risk against a 15c stop sizes to 6 shares; fine. $0.01 sizes to 0.
    r = Runner(journal, mode="LOG_ONLY", dollar_risk=0.01)
    done = r.step()
    assert all(a.outcome == "REFUSED" for a in done)
    row = journal.execute("SELECT refusal_reasons_json FROM decisions "
                          "WHERE outcome='REFUSED' LIMIT 1").fetchone()
    reasons = json.loads(row[0])
    assert any("not an order" in x for x in reasons)


def test_suppressed_decisions_are_never_offered_to_the_runner(journal):
    r = Runner(journal, mode="LOG_ONLY", dollar_risk=25.0)
    acted = {a.decision_id for a in r.step()}
    suppressed = {row["decision_id"] for row in L.decisions(journal, outcome="SUPPRESSED")}
    assert suppressed and not (acted & suppressed)


# ---------------------------------------------------------------- TRADE
def test_trade_mode_needs_a_trader_and_a_real_dollar_risk(journal):
    with pytest.raises(ValueError, match="PaperTrader"):
        Runner(journal, mode="TRADE", dollar_risk=25.0)
    with pytest.raises(ValueError, match="stated risk"):
        Runner(journal, mode="LOG_ONLY", dollar_risk=0)
    with pytest.raises(ValueError, match="mode"):
        Runner(journal, mode="ARMED", dollar_risk=25.0)


def test_trade_mode_places_records_the_order_and_marks_taken(journal):
    t = FakeTrader()
    # "now" is pinned just after the fixture's last plan so nothing is stale
    now = lambda: datetime(2026, 9, 1, 13, 52, tzinfo=timezone.utc)   # noqa: E731
    r = Runner(journal, mode="TRADE", dollar_risk=25.0, trader=t, now=now, max_age_s=3600,
               quote=lambda s: dict(bid=1.0, ask=1.01, bid_size=1, ask_size=1, ts="2026-09-01T13:52:00Z"))
    done = r.step()
    taken = [a for a in done if a.outcome == "TAKEN"]
    assert taken, done
    assert len(t.intents) == len(taken)
    orders = journal.execute("SELECT * FROM orders").fetchall()
    assert len(orders) == len(taken)
    for o in orders:
        assert o["planned_risk"] == pytest.approx((o["trigger"] - o["stop"]) * o["shares"], abs=0.01)
        assert o["account"] == "DUR339781" and o["protected"] == 1
        assert o["fill_price"] is None            # nothing filled yet


def test_trade_mode_refuses_a_stale_decision(journal):
    """A plan armed at 09:40 seen at 14:00 is not the trade the cascade
    reviewed. LOG_ONLY has no such rule because replay is always 'late'."""
    t = FakeTrader()
    late = lambda: datetime(2026, 9, 1, 18, 0, tzinfo=timezone.utc)    # noqa: E731
    r = Runner(journal, mode="TRADE", dollar_risk=25.0, trader=t, now=late, quote=lambda s: dict(bid=1.0, ask=1.01, bid_size=1, ask_size=1, ts="2026-09-01T13:52:00Z"))
    done = r.step()
    assert all(a.outcome == "REFUSED" for a in done)
    assert all(any("stale" in x for x in a.reasons) for a in done)
    assert t.intents == []                        # nothing reached the trader


def test_a_fill_writes_realised_risk_and_nbbo_together(journal):
    t = FakeTrader()
    now = lambda: datetime(2026, 9, 1, 13, 52, tzinfo=timezone.utc)   # noqa: E731
    quotes = {"ABCD": dict(bid=7.30, ask=7.33, bid_size=300, ask_size=100,
                          ts="2026-09-01T13:52:10Z"),
              "DVLT": dict(bid=4.30, ask=4.31, bid_size=100, ask_size=100,
                          ts="2026-09-01T13:52:10Z")}
    r = Runner(journal, mode="TRADE", dollar_risk=25.0, trader=t, now=now,
               max_age_s=3600, quote=lambda s: quotes.get(s))
    r.step()
    # IBKR reports a fill through the trader's records
    for p in t.placed:
        p.fill_price = round(p.trigger + 0.05, 2)
        p.fill_time = "2026-09-01T13:52:09Z"
        p.status = "Filled"
    assert r.sync_fills() == len(t.placed)
    o = journal.execute("SELECT * FROM orders WHERE symbol='ABCD'").fetchone()
    if o is not None:
        assert o["realised_risk"] > o["planned_risk"]      # 5c through the trigger
        assert o["slippage_ratio"] > 1.0
        assert o["nbbo_bid"] == 7.30 and o["nbbo_ask_size"] == 100


def test_a_risk_veto_propagates_rather_than_being_recorded_as_an_outcome(journal):
    class Latched(FakeTrader):
        def place_bracket(self, intent, now=None):
            raise RuntimeError("RiskVeto: daily loss latched")

    now = lambda: datetime(2026, 9, 1, 13, 52, tzinfo=timezone.utc)   # noqa: E731
    r = Runner(journal, mode="TRADE", dollar_risk=25.0, trader=Latched(), now=now,
               max_age_s=3600, quote=lambda s: dict(bid=1.0, ask=1.01, bid_size=1, ask_size=1, ts="2026-09-01T13:52:00Z"))
    with pytest.raises(RuntimeError, match="latched"):
        r.step()
    # and nothing was marked TAKEN behind the veto
    assert journal.execute("SELECT COUNT(*) FROM decisions WHERE outcome='TAKEN'").fetchone()[0] == 0


def test_end_of_day_flattens_only_in_trade_mode(journal):
    t = FakeTrader()
    assert Runner(journal, mode="LOG_ONLY", dollar_risk=25.0).end_of_day() == []
    r = Runner(journal, mode="TRADE", dollar_risk=25.0, trader=t)
    assert r.end_of_day() == ["TEST x100 MKT"] and t.flattened
