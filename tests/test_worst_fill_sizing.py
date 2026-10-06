"""A18 (owner, 2026-10-06): size from the worst fill the order allows.

shares = dollar risk ÷ ((entry limit − stop) + spread at the decision + $0.01)

The 2024-26 replay (research/paper-exercise/reports/2026-10-05-ross-recent-and-
execution/execution_audit/vx2.txt) put 437 of 1,873 trades over a $42 loss when
sized from the trigger, 89 when sized this way."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from execution import intent as I  # noqa: E402
from execution.bridge import intent_from_decision  # noqa: E402
from execution.intent import entry_limit, shares_for, sized_for, sizing_reserve  # noqa: E402
from execution.runner import Runner, _spread  # noqa: E402
from journal import ledger as L  # noqa: E402

import test_runner as TR  # noqa: E402
from test_runner import journal  # noqa: E402,F401  (the fixture)


def _row(**over):
    d = dict(decision_id="d1", symbol="T", trigger=6.00, stop=5.80, plan_allowed=1,
             verdict="REVIEW", session="regular")
    d.update(over)
    return d


# ------------------------------------------------------------------ the rule
def test_the_reserve_is_the_limit_headroom_the_spread_and_the_commission():
    assert entry_limit(6.00) == 6.02
    assert sizing_reserve(6.00, 0.02) == pytest.approx(0.02 + 0.02 + 0.01)
    assert sizing_reserve(6.00, None) == pytest.approx(0.03), "no quote: the spread reads as 0, not as a guess"
    assert sizing_reserve(6.00, -0.01) == pytest.approx(0.03), "a crossed quote is not a spread"


def test_the_worst_fill_sizes_smaller_than_the_trigger():
    assert shares_for(6.00, 5.80, 40.0) == 200
    assert shares_for(6.00, 5.80, 40.0, reserve=0.05) == 160          # 40 / 0.25
    assert shares_for(6.00, 6.00, 40.0, reserve=0.05) == 0, "no stop distance is still no order"


def test_the_worst_case_loss_at_the_stop_fits_the_stated_risk():
    for trig, stop, sp in ((6.00, 5.80, 0.02), (2.41, 2.33, 0.03), (16.33, 15.90, 0.05), (3.05, 2.98, 0.01)):
        n = shares_for(trig, stop, 40.0, reserve=sizing_reserve(trig, sp))
        assert n > 0
        assert (entry_limit(trig) - stop + sp + 0.01) * n <= 40.0 + 1e-9


def test_the_account_still_bounds_the_size():
    # VEEE 2026-09-21: 222 shares by the worst fill, 140 by the account
    assert sized_for(16.33, 16.31, 20.0, max_notional=2288.0, reserve=sizing_reserve(16.33, 0.01)) == (140, "funds")
    assert sized_for(4.00, 3.00, 40.0, max_notional=100.0, reserve=0.03) == (25, "funds")


# ------------------------------------------------------------------ the bridge
def test_the_intent_says_what_it_was_sized_from():
    i = intent_from_decision(_row(), 40.0, spread=0.02)
    assert i.shares == 160 and i.sizing_reserve == pytest.approx(0.05) and i.sizing_spread == 0.02
    assert "worst fill (A18)" in i.note and "limit 6.02" in i.note and "spread 0.02" in i.note
    assert i.planned_risk == pytest.approx(32.0), "planned R stays (trigger − stop) × shares"
    old = intent_from_decision(_row(), 40.0, spread=0.02, worst_fill=False)
    assert old.shares == 200 and old.sizing_reserve == 0.0 and "A18" not in old.note


def test_the_live_switch_is_the_default():
    assert I.WORST_FILL_SIZING is True
    assert intent_from_decision(_row(), 40.0).sizing_reserve == pytest.approx(0.03)


def test_spread_from_a_desk_quote():
    assert _spread({"bid": 6.00, "ask": 6.03}) == 0.03
    assert _spread({"bid": 6.00, "ask": None}) is None
    assert _spread({"bid": 6.03, "ask": 6.00}) is None
    assert _spread(None) is None


# ------------------------------------------------------------------ the runner
def test_the_runner_sizes_from_the_quote_it_read_first(journal):
    t = TR.FakeTrader()
    now = lambda: datetime(2026, 9, 1, 13, 52, tzinfo=timezone.utc)   # noqa: E731
    q = dict(bid=1.0, ask=1.03, bid_size=1, ask_size=1, ts="2026-09-01T13:52:00Z")
    r = Runner(journal, mode="TRADE", dollar_risk=25.0, trader=t, now=now, max_age_s=3600, quote=lambda s: q)
    taken = [a for a in r.step() if a.outcome == "TAKEN"]
    assert taken and t.intents
    for i in t.intents:
        assert i.sizing_spread == 0.03
        assert i.shares == shares_for(i.trigger, i.stop, 25.0, reserve=sizing_reserve(i.trigger, 0.03))
    rows = journal.execute("SELECT sizing_reserve, sizing_spread, shares FROM orders").fetchall()
    assert rows and all(o["sizing_spread"] == 0.03 and o["sizing_reserve"] > 0 for o in rows)


def test_a_premarket_plan_is_sized_again_at_the_touch_from_the_spread_then():
    c = TR._premarket_journal(); t = TR._MonitoredTrader()
    clock = {"t": datetime(2026, 9, 1, 12, 41, 10, tzinfo=timezone.utc)}
    q = {"bid": 7.10, "ask": 7.12, "bid_size": 200, "ask_size": 200, "ts": "2026-09-01T12:41:05Z"}
    r = Runner(c, mode="TRADE", dollar_risk=20.0, trader=t, now=lambda: clock["t"], max_age_s=120, quote=lambda s: q)
    armed = [a for a in r.step() if a.outcome == "PENDING"]
    assert len(armed) == 1
    at_arm = r.armed[armed[0].decision_id]["intent"]
    assert at_arm.sizing_spread == pytest.approx(0.02)
    q.update(bid=7.15, ask=7.21); clock["t"] += timedelta(seconds=40)
    fired = r.fire_armed()
    assert fired and fired[0].outcome == "TAKEN"
    sent = t.monitored[0]
    assert sent.sizing_spread == pytest.approx(0.06)
    assert sent.shares == shares_for(sent.trigger, sent.stop, 20.0, reserve=sizing_reserve(sent.trigger, 0.06))
    assert sent.shares < at_arm.shares, "a wider spread at the touch sizes smaller"
    o = c.execute("SELECT shares, sizing_spread FROM orders").fetchone()
    assert (o["shares"], o["sizing_spread"]) == (sent.shares, pytest.approx(0.06))


def test_the_new_columns_exist_on_an_old_ledger():
    c = L.connect(":memory:")
    cols = {r["name"] for r in c.execute("PRAGMA table_info(orders)")}
    assert {"sizing_reserve", "sizing_spread", "commission_in", "commission_out"} <= cols
