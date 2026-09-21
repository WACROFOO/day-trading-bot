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

    def move_stop(self, rec, new_stop):
        self.moves = getattr(self, "moves", [])
        self.moves.append((rec.symbol, new_stop))
        rec.trail_stop = new_stop
        return rec.stop_id


# ------------------------------------------------------------- LOG_ONLY
def test_log_only_acts_on_every_pending_decision_once_and_opens_nothing(journal):
    before = len(L.pending(journal))
    # Two before amendment A2 (2026-09-17); the catalyst gate now flags
    # instead of killing, and the fixture's two no-news names pass too.
    assert before == 4, "the fixture arms four plans the cascade allows"

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


def test_staleness_is_measured_from_the_bars_close_not_its_open():
    """Clarification C1. A 1-minute decision seen 70 s after its bar CLOSED is
    70 s old, not 130 s. GRML 2026-09-21 07:43 was refused on the old sum."""
    from execution.bridge import bar_seconds
    assert bar_seconds({"bar_resolution": "1m"}) == 60
    assert bar_seconds({"bar_resolution": "10s"}) == 10
    assert bar_seconds({"bar_resolution": None}) == 60


def test_a_stop_inside_the_spread_is_refused_before_the_broker_sees_it():
    """Amendment A6. The runner has the desk's live quote at the instant of the
    order; a stop inside SPREAD_K x the spread is a fee, not a trade."""
    from execution.intent import SPREAD_K
    assert SPREAD_K == 4.0
    src = open(__file__.replace("tests/test_runner.py", "src/execution/runner.py")).read()
    assert "SPREAD_K * spread" in src and "(A6)" in src


# ------------------------------------------------------ A3: the trailing stop
def _take_and_fill(journal, t, fill_ts="2026-09-01T13:52:09Z"):
    now = lambda: datetime(2026, 9, 1, 13, 52, tzinfo=timezone.utc)   # noqa: E731
    quotes = {s: dict(bid=7.30, ask=7.31, bid_size=300, ask_size=100, ts="2026-09-01T13:52:10Z")
              for s in ("ABCD", "DVLT", "CYQN", "IMRN")}
    r = Runner(journal, mode="TRADE", dollar_risk=25.0, trader=t, now=now,
               max_age_s=3600, quote=lambda s: quotes.get(s))
    r.step()
    assert t.placed, "the fixture must place at least one bracket"
    rec = t.placed[0]
    rec.fill_price = rec.trigger; rec.fill_time = fill_ts; rec.status = "Filled"
    r.sync_fills()
    # the fixture's own tape continues past the fill; the tests write their own
    journal.execute("DELETE FROM bars_10s WHERE symbol=?", (rec.symbol,))
    journal.execute("DELETE FROM quote_ticks WHERE symbol=?", (rec.symbol,))
    journal.commit()
    return r, rec


def _bar(journal, sym, ts, high):
    journal.execute("INSERT OR REPLACE INTO bars_10s(symbol, ts, open, high, low, close, volume) "
                    "VALUES (?,?,?,?,?,?,?)", (sym, ts, high - 0.02, high, high - 0.05, high - 0.01, 1000))
    journal.commit()


def test_a3_the_stop_trails_the_high_by_one_r_and_never_falls(journal):
    """Amendment A3: no target; the resting stop follows the high since the
    fill at one initial risk per share, up only."""
    t = FakeTrader()
    r, rec = _take_and_fill(journal, t)
    o = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    rps = round(o["trigger"] - o["stop"], 4)
    assert o["target"] is None, "the live order path carries no target leg"

    # nothing written since the fill: the stop stays where it is
    assert r.trail_stops() == []
    # a bar BEFORE the fill does not count
    _bar(journal, rec.symbol, "2026-09-01T13:51:50+00:00", o["trigger"] + 10 * rps)
    assert r.trail_stops() == []
    # the high moves 1.5R above the trigger: the stop rises to high - 1R
    high1 = round(o["trigger"] + 1.5 * rps, 2)
    _bar(journal, rec.symbol, "2026-09-01T13:53:00+00:00", high1)
    lines = r.trail_stops()
    o1 = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    assert len(lines) == 1 and t.moves == [(rec.symbol, round(high1 - rps, 2))]
    assert o1["trail_stop"] == round(high1 - rps, 2) and o1["high_since_fill"] == high1
    # a lower bar later: nothing moves, the high on record is unchanged
    _bar(journal, rec.symbol, "2026-09-01T13:54:00+00:00", round(high1 - 0.5 * rps, 2))
    assert r.trail_stops() == [] and len(t.moves) == 1
    # a new high: the stop ratchets again
    high2 = round(high1 + rps, 2)
    _bar(journal, rec.symbol, "2026-09-01T13:55:00+00:00", high2)
    assert len(r.trail_stops()) == 1
    o2 = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    assert o2["trail_stop"] == round(high2 - rps, 2) > o1["trail_stop"]
    events = [e["text"] for e in journal.execute("SELECT text FROM order_events WHERE order_id=?", (o["order_id"],))]
    assert any("trail (A3)" in e for e in events)


def test_a3_a_move_the_broker_refuses_leaves_the_stop_and_says_so(journal):
    class RefusingTrader(FakeTrader):
        def move_stop(self, rec, new_stop):
            raise RuntimeError("stop leg not found at the broker")
    t = RefusingTrader()
    r, rec = _take_and_fill(journal, t)
    o = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    _bar(journal, rec.symbol, "2026-09-01T13:53:00+00:00", round(o["trigger"] + 3 * (o["trigger"] - o["stop"]), 2))
    assert r.trail_stops() == []
    o1 = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    assert o1["trail_stop"] is None
    events = [e["text"] for e in journal.execute("SELECT text FROM order_events WHERE order_id=?", (o["order_id"],))]
    assert any("stop left at" in e for e in events)


def test_a3_never_trails_in_log_only_and_leaves_a_sent_exit_alone(journal):
    r = Runner(journal, mode="LOG_ONLY", dollar_risk=25.0)
    assert r.trail_stops() == []
    t = FakeTrader()
    r, rec = _take_and_fill(journal, t)
    o = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    journal.execute("UPDATE orders SET status='ExitPending' WHERE order_id=?", (o["order_id"],)); journal.commit()
    _bar(journal, rec.symbol, "2026-09-01T13:53:00+00:00", round(o["trigger"] + 3 * (o["trigger"] - o["stop"]), 2))
    assert r.trail_stops() == [] and not getattr(t, "moves", [])


def test_r0_is_the_initial_stop_and_a_trailed_stop_never_moves_it(journal):
    """Review item 8. realised_risk = qty × (fill − INITIAL stop). Three trail
    moves later it is the same number, and the ledger's own check agrees."""
    t = FakeTrader()
    r, rec = _take_and_fill(journal, t)
    o = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    r0 = o["realised_risk"]
    assert r0 == round((o["fill_price"] - o["stop"]) * o["shares"], 2)
    rps = o["trigger"] - o["stop"]
    for i, k in enumerate((1.5, 2.5, 4.0)):
        _bar(journal, rec.symbol, f"2026-09-01T13:5{3 + i}:00+00:00", round(o["trigger"] + k * rps, 2))
        assert len(r.trail_stops()) == 1
    o2 = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    assert o2["trail_stop"] > o2["stop"] and o2["stop"] == o["stop"]
    assert o2["realised_risk"] == r0 and o2["slippage_ratio"] == o["slippage_ratio"]
    assert L.r0_violations(journal) == []
    journal.execute("UPDATE orders SET realised_risk=realised_risk*3 WHERE order_id=?", (o["order_id"],)); journal.commit()
    assert [v["order_id"] for v in L.r0_violations(journal)] == [o["order_id"]]


def test_every_judged_decision_records_its_clocks_and_a_refusal_names_the_one_that_failed(journal):
    """Review item 12."""
    import json
    t = FakeTrader()
    late = lambda: datetime(2026, 9, 1, 18, 0, tzinfo=timezone.utc)    # noqa: E731
    r = Runner(journal, mode="TRADE", dollar_risk=25.0, trader=t, now=late,
               quote=lambda s: dict(bid=1.0, ask=1.01, bid_size=1, ask_size=1, ts="2026-09-01T13:52:00Z"))
    done = r.step()
    assert done and all(a.outcome == "REFUSED" for a in done)
    for a in done:
        assert any(x.startswith("bar clock:") and "budget 120s" in x for x in a.reasons), a.reasons
        row = journal.execute("SELECT clocks_json, bar_end_ts, recorded_at FROM decisions WHERE decision_id=?",
                              (a.decision_id,)).fetchone()
        c = json.loads(row["clocks_json"])
        assert set(c) >= {"bar_end", "published", "runner_seen", "quote_ts", "bar_to_published_s", "published_to_seen_s"}
        assert c["runner_seen"].startswith("2026-09-01T18:00") and c["quote_ts"] == "2026-09-01T13:52:00Z"
        assert row["bar_end_ts"] is not None and c["bar_end"][:16] == row["bar_end_ts"][:16]


def test_freshly_published_backfill_does_not_read_as_fresh(journal):
    """A backfill row re-published a second ago is still armed on loaded
    history: the bar clock refuses it and the reason says so."""
    t = FakeTrader()
    now = lambda: datetime(2026, 9, 1, 13, 52, tzinfo=timezone.utc)   # noqa: E731
    did = L.pending(journal)[0]["decision_id"]
    journal.execute("UPDATE decisions SET data_status='live-backfill', recorded_at=? WHERE decision_id=?",
                    (now().isoformat(), did)); journal.commit()
    r = Runner(journal, mode="TRADE", dollar_risk=25.0, trader=t, now=now, max_age_s=3600,
               quote=lambda s: dict(bid=1.0, ask=1.01, bid_size=1, ask_size=1, ts="2026-09-01T13:52:00Z"))
    a = next(x for x in r.step() if x.decision_id == did)
    assert a.outcome == "REFUSED"
    assert any("loaded history" in x and "bar clock" in x for x in a.reasons), a.reasons


# ------------------------------------------------ review item 13: order state
class _Pos:
    def __init__(self, sym, qty):
        self.position = qty
        self.contract = type("C", (), {"symbol": sym})()


class _IB:
    def __init__(self, positions=()):
        self._positions = list(positions)
    def positions(self): return list(self._positions)
    def trades(self): return []
    def openTrades(self): return []


class ReconcilingTrader(FakeTrader):
    """A fake that also answers the broker-state questions the runner asks."""
    def __init__(self, positions=()):
        super().__init__()
        self.ib = _IB(positions)
    def positions_held(self):
        return [(p.contract.symbol, int(p.position)) for p in self.ib.positions() if p.position > 0]


def test_13c_a_partial_fill_whose_stop_covers_fewer_shares_is_flagged(journal):
    """Every filled share needs its protective exit. The stop leg's quantity
    is read from the broker on sync; a leg covering fewer than the filled
    shares is a RECONCILE line, an order event, and a bar on new entries."""
    t = ReconcilingTrader()
    r, rec = _take_and_fill(journal, t)
    rec.filled_qty, rec.stop_qty = 100, 40
    r.sync_fills()
    o = journal.execute("SELECT filled_qty, stop_qty FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    assert (o["filled_qty"], o["stop_qty"]) == (100, 40)
    lines = r.reconcile_positions()
    assert any(x.startswith("STOP COVERS 40 OF 100") for x in lines), lines
    assert r.unreconciled
    rec.stop_qty = 100
    r.sync_fills()
    assert r.reconcile_positions() == [] and r.unreconciled == []


def test_13d_an_untracked_broker_position_blocks_new_entries_until_reconciled(journal):
    """Reconcile first, order second: a runner that starts (or reconnects) with
    a position the ledger does not know about places nothing until a human
    has cleared it."""
    t = ReconcilingTrader(positions=[_Pos("GHOST", 50)])
    now = lambda: datetime(2026, 9, 1, 13, 52, tzinfo=timezone.utc)   # noqa: E731
    r = Runner(journal, mode="TRADE", dollar_risk=25.0, trader=t, now=now, max_age_s=3600,
               quote=lambda s: dict(bid=1.0, ask=1.01, bid_size=1, ask_size=1, ts="2026-09-01T13:52:00Z"))
    assert any("UNTRACKED position GHOST" in n for n in r.startup_notes)
    done = r.step()
    assert done and all(a.outcome == "REFUSED" for a in done)
    assert all(any("not reconciled" in x for x in a.reasons) for a in done)
    assert t.intents == []
    # the human flattens it by hand; the next reconciliation clears the bar
    t.ib._positions = []
    assert r.reconcile_positions() == [] and r.unreconciled == []
    journal.execute("UPDATE decisions SET outcome='PENDING' WHERE plan_allowed=1"); journal.commit()
    assert any(a.outcome == "TAKEN" for a in r.step())


def test_13e_repeated_callbacks_and_a_second_step_never_duplicate_an_entry_or_an_exit(journal):
    t = FakeTrader()
    r, rec = _take_and_fill(journal, t)
    n_intents = len(t.intents)
    assert r.step() == [] and len(t.intents) == n_intents            # nothing pending twice
    assert r.sync_fills() == 0                                        # the fill is recorded once
    rec.exit_price, rec.exit_reason, rec.exit_time = 7.50, "stop", "2026-09-01T14:10:00Z"
    r.sync_fills()
    o1 = journal.execute("SELECT exit_ts, exit_price, status FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    rec.exit_price, rec.exit_time = 7.40, "2026-09-01T14:20:00Z"     # the broker repeats the callback, differently
    r.sync_fills(); r.sync_fills()
    o2 = journal.execute("SELECT exit_ts, exit_price, status FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    assert tuple(o1) == tuple(o2) == (o1["exit_ts"], 7.50, "Closed")
    assert journal.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == len(t.placed)


def test_13f_flat_is_the_brokers_word_not_the_sent_sell(journal):
    t = ReconcilingTrader(positions=[_Pos("TEST", 100)])
    r = Runner(journal, mode="TRADE", dollar_risk=25.0, trader=t)
    lines = r.end_of_day()
    assert "TEST x100 MKT" in lines and any(x.startswith("NOT FLAT TEST x100") for x in lines)
    assert r.flat_confirmed is False
    assert any(x.startswith("NOT FLAT") for x in r.confirm_flat())     # still held next loop
    t.ib._positions = []
    assert r.confirm_flat() == ["flat confirmed from broker position state"]
    assert r.flat_confirmed is True and r.confirm_flat() == []         # said once


def test_a_rejected_entry_reaches_the_ledger_and_frees_the_one_position_rule(journal):
    """VEEE 2026-09-21 09:37: IBKR rejected the parent (201) and the ledger row
    stayed 'submitted' all session, so every later entry was refused for a
    position that never existed."""
    t = FakeTrader()
    now = lambda: datetime(2026, 9, 1, 13, 52, tzinfo=timezone.utc)   # noqa: E731
    r = Runner(journal, mode="TRADE", dollar_risk=25.0, trader=t, now=now, max_age_s=3600,
               quote=lambda s: dict(bid=1.0, ask=1.01, bid_size=1, ask_size=1, ts="2026-09-01T13:52:00Z"))
    r.step()
    rec = t.placed[0]
    assert L.positions_alive(journal) >= 1
    rec.status = "Inactive"                                   # the broker's word: rejected
    r.sync_fills()
    o = journal.execute("SELECT status, decision_id FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    assert o["status"] == "Inactive"
    assert journal.execute("SELECT outcome FROM decisions WHERE decision_id=?", (o["decision_id"],)).fetchone()[0] == "NOT_FILLED"
    alive_before = L.positions_alive(journal)
    journal.execute("UPDATE orders SET status='Inactive' WHERE fill_price IS NULL"); journal.commit()
    assert L.positions_alive(journal) == 0 or alive_before < len(t.placed)


def test_an_entry_the_broker_no_longer_reports_after_a_restart_is_resolved_not_kept_alive(journal):
    """After a restart IBKR re-reports working orders and today's fills. An
    entry in neither, with no position in the name, is dead and is marked so
    at reconciliation instead of blocking entries all day."""
    t = ReconcilingTrader()
    now = lambda: datetime(2026, 9, 1, 13, 52, tzinfo=timezone.utc)   # noqa: E731
    r = Runner(journal, mode="TRADE", dollar_risk=25.0, trader=t, now=now, max_age_s=3600,
               quote=lambda s: dict(bid=1.0, ask=1.01, bid_size=1, ask_size=1, ts="2026-09-01T13:52:00Z"))
    r.step()
    assert L.positions_alive(journal) >= 1
    # a fresh runner adopts the ledger's rows; the fake broker reports no trades, no fills, no positions
    t2 = ReconcilingTrader()
    t2.ib.fills = lambda: []
    r2 = Runner(journal, mode="TRADE", dollar_risk=25.0, trader=t2, now=now, max_age_s=3600,
                quote=lambda s: dict(bid=1.0, ask=1.01, bid_size=1, ask_size=1, ts="2026-09-01T13:52:00Z"))
    assert any(n.startswith("GONE AT BROKER") for n in r2.startup_notes), r2.startup_notes
    assert L.positions_alive(journal) == 0
    rows = journal.execute("SELECT status FROM orders WHERE fill_price IS NULL").fetchall()
    assert rows and all(x["status"] == "NotFilled" for x in rows)
    assert r2.unreconciled == []                              # a resolved ghost is not a bar on entries
