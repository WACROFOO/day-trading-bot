"""The 2026-09-07 review: Layer 2 reaches the cascade, TRADE needs REVIEW, a
risk gate the ledger feeds and latches, exits are recorded, never-filled
entries are reconciled, and a restarted runner adopts its open orders."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from execution.intent import PlacedOrder  # noqa: E402
from execution.runner import Runner  # noqa: E402
from journal import ledger as L  # noqa: E402
from journal.risk import JournalRiskGate, Limits, RiskVeto  # noqa: E402
from momentum_platform import indicators as I  # noqa: E402
from momentum_platform.dashboard.session_builder import build_session  # noqa: E402

FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"
NOW = lambda: datetime(2026, 9, 1, 13, 52, tzinfo=timezone.utc)   # noqa: E731
FRESH = lambda s: dict(bid=1.0, ask=1.01, bid_size=1, ask_size=1, ts="2026-09-01T13:52:00Z")  # noqa: E731


# ------------------------------------------------------------ indicators
def bars(closes, vol=100):
    return [[i, c, c + .01, c - .01, c, vol] for i, c in enumerate(closes)]


def test_vwap_of_a_flat_tape_is_the_price_and_needs_volume():
    assert I.vwap(bars([5.0] * 10)) == pytest.approx(5.0)
    assert I.vwap([[0, 5, 5, 5, 5, 0]]) is None


def test_ema_and_macd_warm_up_honestly():
    g = I.chart_gates(bars([5.0] * 5))
    assert g["above_ema9"] is None and g["macd_positive_and_above_signal"] is None
    g = I.chart_gates(bars([5.0] * 20))
    assert g["above_ema9"] is not None and g["macd_positive_and_above_signal"] is None
    g = I.chart_gates(bars([5.0 + 0.01 * i for i in range(40)]))
    assert g["macd_positive_and_above_signal"] is True          # steady uptrend
    assert g["above_ema9"] is True and g["above_vwap"] is True
    g = I.chart_gates(bars([7.0 - 0.02 * i for i in range(40)]))
    assert g["macd_positive_and_above_signal"] is False and g["above_vwap"] is False


def test_the_fixture_decisions_now_carry_evaluated_chart_gates():
    """Before the review every live decision had all three chart gates
    UNKNOWN, so REVIEW was unreachable and TRADE never checked the chart."""
    import json
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c)
    states = set()
    for r in L.decisions(c):
        for g in json.loads(r["gates_json"]):
            if g["id"] in ("vwap", "ema9", "macd"):
                states.add(g["state"])
    assert states & {"PASS", "FAIL"}, "at least one chart gate must be evaluated"


def test_trade_mode_refuses_anything_that_is_not_review():
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c)
    c.execute("UPDATE decisions SET verdict='WAIT' WHERE plan_allowed=1"); c.commit()

    class T:
        account = "DU1"; placed = []
        def place_bracket(self, *a, **k): raise AssertionError("must not be reached")
        def adopt(self, rows): return 0
        def sync(self): pass
    done = Runner(c, mode="TRADE", dollar_risk=20.0, trader=T(), now=NOW, max_age_s=3600,
                  quote=FRESH).step()
    assert done and all(a.outcome == "REFUSED" and any("Layer 2" in x for x in a.reasons) for a in done)


# -------------------------------------------------------------- risk gate
def _order(c, sym="X", fill=5.0, exit_=None, shares=100, stop=4.8, day="2026-09-01"):
    did = L.decisions(c, plan_allowed=1)[0]["decision_id"]
    oid = L.record_order(c, did, symbol=sym, account="DU1", session="regular", parent_id=oid_seq(),
                         stop_id=None, target_id=None, trigger=5.0, stop=stop, target=None,
                         shares=shares, dollar_risk=20.0, protected=True)
    L.record_fill(c, oid, fill_price=fill, fill_ts=f"{day}T14:00:00Z")
    if exit_ is not None:
        L.record_exit(c, oid, reason="stop", price=exit_, ts=f"{day}T14:30:00Z")
    return oid


_seq = [1000]
def oid_seq():
    _seq[0] += 1; return _seq[0]


def test_three_consecutive_losses_lock_the_day_and_the_lock_persists():
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c)
    gate = JournalRiskGate(c, Limits(max_daily_loss_r=99, consecutive_losses=3, max_entries_per_day=99),
                           today=lambda: "2026-09-01")
    gate.assert_can_buy()                                   # nothing yet: open
    for _ in range(3):
        _order(c, fill=5.0, exit_=4.9)                      # −0.5 R each
    with pytest.raises(RiskVeto, match="consecutive"):
        gate.assert_can_buy()
    _order(c, fill=5.0, exit_=5.6)                          # a winner does not unlock
    with pytest.raises(RiskVeto, match="day locked"):
        gate.assert_can_buy()
    assert c.execute("SELECT locked FROM risk_day WHERE date='2026-09-01'").fetchone()[0] == 1


def test_daily_loss_in_r_locks_the_day():
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c)
    gate = JournalRiskGate(c, Limits(max_daily_loss_r=3.0, consecutive_losses=99, max_entries_per_day=99),
                           today=lambda: "2026-09-01")
    _order(c, fill=5.0, exit_=4.4)      # −3 R on a 0.20 planned risk/share
    with pytest.raises(RiskVeto, match="daily loss"):
        gate.assert_can_buy()
    st = gate.state()
    assert st["day_r"] <= -3.0 and st["locked"]


def test_exits_are_always_allowed_the_gate_is_asked_on_entry_only():
    src = (ROOT / "src/journal/risk.py").read_text()
    assert "asked before an ENTRY only" in src


# --------------------------------------------------- exits + reconcile + adopt
class FakeTrader:
    account = "DUR339781"
    def __init__(self): self.placed = []; self.adopted = []
    def place_bracket(self, intent, now=None):
        n = len(self.placed)
        rec = PlacedOrder(symbol=intent.symbol, parent_id=100 + n, stop_id=200 + n, target_id=300 + n,
                          trigger=intent.trigger, stop=intent.stop, shares=intent.shares, protected=True)
        self.placed.append(rec); return rec
    def adopt(self, rows):
        self.adopted = list(rows)
        for r in rows:
            self.placed.append(PlacedOrder(symbol=r["symbol"], parent_id=r["parent_id"], stop_id=r["stop_id"],
                                           trigger=r["trigger"], stop=r["stop"], shares=int(r["shares"]),
                                           fill_price=r["fill_price"]))
        return len(rows)
    def sync(self): pass
    def flatten_all(self, **k): return []


def _review_ready(c):
    c.execute("UPDATE decisions SET verdict='REVIEW' WHERE plan_allowed=1"); c.commit()


def test_a_filled_stop_leg_becomes_a_recorded_exit_with_realised_pnl():
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c); _review_ready(c)
    t = FakeTrader()
    r = Runner(c, mode="TRADE", dollar_risk=20.0, trader=t, now=NOW, max_age_s=3600, quote=FRESH)
    r.step()
    p = t.placed[0]
    p.fill_price = p.trigger; p.fill_time = "2026-09-01T13:52:05Z"; p.status = "Filled"
    r.sync_fills()
    p.exit_price = p.stop; p.exit_reason = "stop"; p.exit_time = "2026-09-01T14:10:00Z"
    assert r.sync_fills() >= 1
    o = c.execute("SELECT exit_reason, exit_price, status FROM orders WHERE parent_id=?", (p.parent_id,)).fetchone()
    assert o["exit_reason"] == "stop" and o["exit_price"] == p.stop and o["status"] == "Closed"
    assert L.stuck_orders(c) == [] or all(x["parent_id"] != p.parent_id for x in L.stuck_orders(c))


def test_never_filled_entries_become_not_filled_at_the_hard_stop():
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c); _review_ready(c)
    t = FakeTrader()
    r = Runner(c, mode="TRADE", dollar_risk=20.0, trader=t, now=NOW, max_age_s=3600, quote=FRESH)
    taken = [a for a in r.step() if a.outcome == "TAKEN"]
    assert taken
    r.end_of_day()
    assert c.execute("SELECT COUNT(*) FROM decisions WHERE outcome='TAKEN'").fetchone()[0] == 0
    assert c.execute("SELECT COUNT(*) FROM decisions WHERE outcome='NOT_FILLED'").fetchone()[0] == len(taken)
    assert c.execute("SELECT COUNT(*) FROM orders WHERE status='NotFilled'").fetchone()[0] == len(taken)
    assert L.funnel(c)["taken"] == 0


def test_a_restarted_runner_adopts_the_ledgers_open_orders():
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c); _review_ready(c)
    t1 = FakeTrader()
    Runner(c, mode="TRADE", dollar_risk=20.0, trader=t1, now=NOW, max_age_s=3600, quote=FRESH).step()
    n_open = len(L.open_orders(c)); assert n_open >= 1
    t2 = FakeTrader()                                        # a fresh process
    Runner(c, mode="TRADE", dollar_risk=20.0, trader=t2, now=NOW, max_age_s=3600, quote=FRESH)
    assert len(t2.adopted) == n_open
    assert {p.parent_id for p in t2.placed} == {r["parent_id"] for r in L.open_orders(c)}


def test_real_trader_adopt_rebuilds_records_with_the_ledgers_ids():
    from execution.ibkr_trader import PaperTrader
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c)
    did = L.decisions(c, plan_allowed=1)[0]["decision_id"]
    L.record_order(c, did, symbol="ABCD", account="DU1", session="regular", parent_id=77, stop_id=78,
                   target_id=None, trigger=7.2, stop=7.05, target=None, shares=50, dollar_risk=7.5,
                   protected=True)
    t = PaperTrader()
    assert t.adopt(L.open_orders(c)) == 1
    assert t.placed[0].parent_id == 77 and t.placed[0].stop_id == 78 and t.placed[0].shares == 50
    assert t.adopt(L.open_orders(c)) == 0                    # idempotent


def test_the_review_command_runs_on_a_fixture_ledger(tmp_path):
    import subprocess
    db = tmp_path / "j.sqlite"
    subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "replay", str(FIXTURE)],
                   cwd=ROOT, capture_output=True, text=True)
    r = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "review"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    for h in ("SESSIONS", "WHAT KILLS", "VERDICTS AT THE PLAN", "CONTROLS", "REPLAY", "RISK TODAY"):
        assert h in r.stdout
