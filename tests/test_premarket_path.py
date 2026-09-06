"""Pre-market entries take the shape the probe verdict dictates, and only in
phase C. A `queued` verdict means no resting stop and the runner IS the stop."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from execution.intent import EntryIntent, PlacedOrder  # noqa: E402
from execution.policy import premarket_allowed, premarket_shape  # noqa: E402
from execution.runner import Runner  # noqa: E402
from journal import ledger as L  # noqa: E402
from momentum_platform.cascade import Inputs, evaluate  # noqa: E402
from types import SimpleNamespace as NS  # noqa: E402

PM_ARMED = "2026-09-08T12:45:00Z"      # 08:45 ET Tuesday — pre-market
NOW = lambda: datetime(2026, 9, 8, 12, 46, tzinfo=timezone.utc)   # noqa: E731


def good_inputs():
    return Inputs(symbol="PMX", last=6.00, prev_close=4.00, change_pct=50.0, session_high=6.20,
                  float_shares=4_000_000, float_verified=True, catalyst_today=True,
                  is_fund_or_etf=False, tick_size=0.01, above_vwap=True, above_ema9=True,
                  macd_positive_and_above_signal=True, session_volume=3_000_000, rvol=8.0)


@pytest.fixture
def journal():
    c = L.connect(":memory:")
    inp = good_inputs(); res = evaluate(inp)
    plan = NS(entry=6.05, stop=5.90, target=None, risk_share=0.15, reward_multiple=None,
              pullback_candles=3, volume_ok=True)
    L.record_decision(c, symbol="PMX", armed_at=PM_ARMED, plan=plan, cascade=res, inputs=inp,
                      snapshot=dict(last=6.0, bid=5.99, ask=6.01), session="premarket",
                      session_id="t", source_name="test", data_status="live")
    yield c
    c.close()


class FakeTrader:
    account = "DUR339781"

    def __init__(self):
        self.placed, self.brackets, self.monitored, self.exits = [], [], [], []

    def place_bracket(self, intent, now=None):
        self.brackets.append(intent)
        rec = PlacedOrder(symbol=intent.symbol, parent_id=1, stop_id=2, trigger=intent.trigger,
                          stop=intent.stop, shares=intent.shares, protected=False,
                          stop_status="PreSubmitted")          # pre-market: unconfirmed until read-back
        self.placed.append(rec); return rec

    def place_entry_monitored(self, intent):
        self.monitored.append(intent)
        rec = PlacedOrder(symbol=intent.symbol, parent_id=1, stop_id=None, trigger=intent.trigger,
                          stop=intent.stop, shares=intent.shares, protected=False,
                          stop_status="monitored")
        self.placed.append(rec); return rec

    def exit_limit(self, symbol, qty, bid, offset=0.10, outside_rth=True):
        px = round(bid - offset, 2); self.exits.append((symbol, qty, px, outside_rth)); return px

    def sync(self): pass


# ------------------------------------------------------------- policy
def test_policy_is_phase_c_and_a_definite_verdict():
    assert premarket_allowed({"phase": "B", "probe_verdict": "held"})[0] is False
    assert premarket_allowed({"phase": "C", "probe_verdict": None})[0] is False
    assert premarket_allowed({"phase": "C", "probe_verdict": "inconclusive"})[0] is False
    assert premarket_shape({"phase": "C", "probe_verdict": "held"}) == "bracket"
    assert premarket_shape({"phase": "C", "probe_verdict": "queued"}) == "monitored"
    assert premarket_shape({"phase": "A", "probe_verdict": "held"}) == "none"


# ------------------------------------------------------------- runner
def test_premarket_plan_is_refused_outside_phase_c_and_the_reason_is_recorded(journal):
    t = FakeTrader()
    r = Runner(journal, mode="TRADE", dollar_risk=20.0, trader=t, now=NOW, max_age_s=3600)
    (a,) = r.step()
    assert a.outcome == "REFUSED" and any("pre-market entry not allowed" in x for x in a.reasons)
    assert not t.brackets and not t.monitored


def test_log_only_also_records_the_policy_refusal(journal):
    """Phase A must show how many pre-market plans the policy would have stopped."""
    (a,) = Runner(journal, mode="LOG_ONLY", dollar_risk=20.0).step()
    assert a.outcome == "REFUSED" and any("phase A" in x for x in a.reasons)


def test_held_verdict_places_a_bracket_and_protection_waits_for_read_back(journal):
    L.set_state(journal, phase="C", probe_verdict="held", probe_date="2026-09-08")
    t = FakeTrader()
    r = Runner(journal, mode="TRADE", dollar_risk=20.0, trader=t, now=NOW, max_age_s=3600)
    (a,) = r.step()
    assert a.outcome == "TAKEN" and len(t.brackets) == 1 and not t.monitored
    o = journal.execute("SELECT * FROM orders").fetchone()
    assert o["session"] == "premarket" and o["protected"] == 0     # unconfirmed until sync()


def test_queued_verdict_places_a_monitored_entry_with_no_stop_leg(journal):
    L.set_state(journal, phase="C", probe_verdict="queued", probe_date="2026-09-08")
    t = FakeTrader()
    r = Runner(journal, mode="TRADE", dollar_risk=20.0, trader=t, now=NOW, max_age_s=3600)
    (a,) = r.step()
    assert a.outcome == "TAKEN" and len(t.monitored) == 1 and not t.brackets
    o = journal.execute("SELECT * FROM orders").fetchone()
    assert o["stop_id"] is None and o["protected"] == 0


def _fill(journal, r, t):
    r.step()
    t.placed[0].fill_price = 6.06; t.placed[0].fill_time = "2026-09-08T12:46:10Z"; t.placed[0].status = "Filled"
    r.sync_fills()


def test_the_runner_is_the_stop_when_the_bid_touches_it(journal):
    L.set_state(journal, phase="C", probe_verdict="queued", probe_date="2026-09-08")
    t = FakeTrader()
    quotes = {"PMX": dict(bid=6.02, ask=6.04, bid_size=100, ask_size=100, ts="2026-09-08T12:46:10Z")}
    r = Runner(journal, mode="TRADE", dollar_risk=20.0, trader=t, now=NOW, max_age_s=3600,
               quote=lambda s: quotes.get(s))
    _fill(journal, r, t)
    assert r.watch_stops() == []                          # bid 6.02 > stop 5.90: hold
    quotes["PMX"]["bid"] = 5.90                            # touches
    done = r.watch_stops()
    assert len(done) == 1 and t.exits == [("PMX", t.monitored[0].shares, 5.80, True)]
    o = journal.execute("SELECT exit_reason, exit_price, status FROM orders").fetchone()
    assert o["exit_reason"] == "monitored_stop" and o["exit_price"] == 5.80 and o["status"] == "Closed"
    assert r.watch_stops() == []                          # exited: no longer watched


def test_no_fresh_quote_means_hold_and_say_so_never_guess_a_price(journal):
    L.set_state(journal, phase="C", probe_verdict="queued", probe_date="2026-09-08")
    t = FakeTrader()
    r = Runner(journal, mode="TRADE", dollar_risk=20.0, trader=t, now=NOW, max_age_s=3600,
               quote=lambda s: None)
    _fill(journal, r, t)
    assert r.watch_stops() == [] and t.exits == []
    ev = journal.execute("SELECT text FROM order_events").fetchall()
    assert any("no fresh quote" in e[0] for e in ev)


def test_watch_stops_is_inert_in_log_only(journal):
    assert Runner(journal, mode="LOG_ONLY", dollar_risk=20.0).watch_stops() == []
