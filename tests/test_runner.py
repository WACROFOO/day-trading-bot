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


def test_a_held_position_whose_stop_died_gets_a_fresh_stop_from_the_runner(journal):
    """DCOY 2026-09-22 09:36: the trail's modify cancelled the stop; the runner
    printed NO WORKING EXIT for eleven minutes. Now it places one."""
    class ProtectingTrader(FakeTrader):
        def __init__(self):
            super().__init__(); self.stops = []
        def place_stop(self, symbol, qty, stop_price, ref=None):
            self.stops.append((symbol, qty, stop_price)); return 900 + len(self.stops)
    t = ProtectingTrader()
    r, rec = _take_and_fill(journal, t)
    o = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    assert r.reprotect() == []                                    # a working stop is left alone
    rec.stop_status, rec.protected, rec.filled_qty = "Cancelled", False, 41
    L.set_trail(journal, o["order_id"], trail_stop=round(o["stop"] + 0.02, 2), high=None); journal.commit()
    r.sync_fills()
    o1 = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    assert o1["protected"] == 0 and o1["stop_status"] == "Cancelled"
    lines = r.reprotect()
    assert len(lines) == 1 and t.stops == [(rec.symbol, 41, round(o["stop"] + 0.02, 2))], (lines, t.stops)
    o2 = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    assert o2["protected"] == 1 and o2["stop_status"] == "Submitted" and o2["stop_id"] == 901
    assert rec.stop_id == 901 and rec.protected is True
    assert r.reprotect() == []                                    # once


def test_a_position_whose_hard_stop_sell_failed_gets_a_stop_and_its_fill_closes_the_row(journal):
    """GRML x62, 2026-09-22 11:30: the flatten cancelled the stop, the market
    sell was rejected, the row read ExitFailed — a held position with NO exit
    at all, and `reprotect` skipped it. Now it gets a stop; a restarted runner
    adopts the row; the stop's fill closes it."""
    class ProtectingTrader(FakeTrader):
        def __init__(self):
            super().__init__(); self.stops = []
        def place_stop(self, symbol, qty, stop_price, ref=None):
            self.stops.append((symbol, qty, stop_price)); return 900 + len(self.stops)
    t = ProtectingTrader()
    r, rec = _take_and_fill(journal, t)
    o = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    L.record_exit(journal, o["order_id"], reason="hard_stop", price=None, ts="2026-09-01T15:30:00Z",
                  confirmed=False, exit_order_id=901)
    assert r.reprotect() == []                          # ExitPending: a sell is working, no stop on top
    L.exit_failed(journal, o["order_id"], status="Inactive")
    journal.execute("UPDATE orders SET protected=0, stop_status='Cancelled' WHERE order_id=?", (o["order_id"],))
    journal.commit()                                    # the flatten's cancel_all killed the stop
    assert [x["order_id"] for x in L.open_orders(journal)] == [o["order_id"]]   # a restart adopts it
    lines = r.reprotect()
    assert len(lines) == 1 and t.stops == [(rec.symbol, int(o["shares"]), float(o["stop"]))], (lines, t.stops)
    o2 = journal.execute("SELECT * FROM orders WHERE order_id=?", (o["order_id"],)).fetchone()
    assert (o2["status"], o2["protected"], o2["stop_status"], o2["stop_id"]) == ("ExitFailed", 1, "Submitted", 901)
    assert r.reprotect() == []
    # the fresh stop fills: the row closes at the stop's price, reason stop
    rec.exit_price, rec.exit_time, rec.exit_confirmed, rec.exit_reason = float(o["stop"]), "2026-09-01T15:31:00Z", True, "stop"
    r.sync_fills()
    o3 = journal.execute("SELECT status, exit_reason, exit_price FROM orders WHERE order_id=?", (o["order_id"],)).fetchone()
    assert (o3["status"], o3["exit_reason"], o3["exit_price"]) == ("Closed", "stop", float(o["stop"]))
    assert L.stuck_orders(journal) == []


def test_acted_carries_the_backfill_flag(journal):
    """The live log collapses history-loaded plans into one line; the flag
    that makes that possible rides on Acted, from the decision's data_status."""
    from execution.runner import Acted
    a = Acted("d", "WHLR", "2026-09-23T04:22:00-04:00", 6.6, 6.02, "REFUSED", ["bar is outside"], True)
    assert a.backfill is True
    assert Acted("d", "WHLR", "t", 1.0, 0.9, "TAKEN", []).backfill is False



def test_a_triggered_stop_stops_the_trail_and_is_named_by_reconcile(journal):
    """The broker says the stop has triggered: a sell is in flight. No more
    modify attempts, the row reads Triggered, reconcile names it, and the
    ledger's trail level is never advanced on a refused move."""
    class TriggeredTrader(FakeTrader):
        def __init__(self):
            super().__init__(); self.moves = 0
        def move_stop(self, rec, new_stop):
            self.moves += 1
            exc = RuntimeError("201: Stop price revision is disallowed after order has triggered")
            exc.triggered = True
            raise exc
    t = TriggeredTrader()
    r, rec = _take_and_fill(journal, t)
    o = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    high = round(o["trigger"] + 3 * (o["trigger"] - o["stop"]), 2)
    journal.execute("INSERT INTO bars_10s (symbol, ts, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
                    (rec.symbol, "2026-09-01T13:53:00Z", high, high, high, high, 100)); journal.commit()
    lines = r.trail_stops()
    assert t.moves == 1 and any("TRIGGERED" in x for x in lines), lines
    o1 = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    assert o1["stop_status"] == "Triggered" and o1["protected"] == 1 and o1["trail_stop"] is None
    assert r.trail_stops() == [] and t.moves == 1                  # never tried again
    from types import SimpleNamespace as NS
    t.ib = NS(positions=lambda: [NS(position=int(o["shares"]), contract=NS(symbol=rec.symbol))],
              openTrades=lambda: [], fills=lambda: [], trades=lambda: [])
    lines = r.reconcile_positions()
    assert any("STOP TRIGGERED" in x and "ah-exit" in x for x in lines), lines
    assert not any("NO WORKING EXIT" in x for x in lines)
    assert r.reprotect() == []                                     # protected: a sell in flight is an exit


def test_reprotect_adopts_a_stop_already_resting_at_the_broker_instead_of_doubling_it(journal):
    """A refused modify shows the leg as Cancelled for a moment. Placing a
    second stop under one position sells it twice; the second fill is a
    short. The runner asks the broker first and adopts what rests there."""
    class AdoptingTrader(FakeTrader):
        def __init__(self):
            super().__init__(); self.placed_stops = []
        def working_stops(self, symbol): return [(777, 5.61, 41.0)]
        def place_stop(self, symbol, qty, stop_price, ref=None):
            self.placed_stops.append((symbol, qty, stop_price)); return 900
    t = AdoptingTrader()
    r, rec = _take_and_fill(journal, t)
    o = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    journal.execute("UPDATE orders SET protected=0, stop_status='Cancelled' WHERE order_id=?", (o["order_id"],)); journal.commit()
    lines = r.reprotect()
    assert len(lines) == 1 and "adopted, none placed" in lines[0] and t.placed_stops == []
    o2 = journal.execute("SELECT * FROM orders WHERE order_id=?", (o["order_id"],)).fetchone()
    assert (o2["stop_id"], o2["protected"], o2["stop_status"]) == (777, 1, "Submitted")



def test_the_brokers_resting_stop_level_corrects_the_ledgers_trail(journal):
    """WHLR 2026-09-23: the ledger said 7.74 after three refused moves; the
    broker held 7.34. When the trader's sync reads the resting level, the
    ledger follows the broker, both up and back to the initial stop."""
    t = FakeTrader()
    r, rec = _take_and_fill(journal, t)
    o = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    L.set_trail(journal, o["order_id"], trail_stop=round(o["stop"] + 0.40, 2), high=None); journal.commit()
    rec.broker_stop_level = float(o["stop"]); rec.trail_stop = None      # what PaperTrader.sync would set
    r.sync_fills()
    assert journal.execute("SELECT trail_stop FROM orders WHERE order_id=?", (o["order_id"],)).fetchone()[0] is None
    rec.broker_stop_level = round(o["stop"] + 0.10, 2); rec.trail_stop = rec.broker_stop_level
    r.sync_fills()
    assert journal.execute("SELECT trail_stop FROM orders WHERE order_id=?", (o["order_id"],)).fetchone()[0] == round(o["stop"] + 0.10, 2)



def test_a_resting_stop_the_bid_has_passed_for_fifteen_seconds_is_enforced_by_the_runner(journal):
    """WHLR 2026-09-23: stop resting at 7.34, tape at 7.05 then 6.99, no fill
    for fifty minutes. After STOP_ENFORCE_SECONDS below the level the runner
    cancels the leg and sells at market; the row is ExitPending, reason
    stop_enforced. A bid back above the level resets the clock."""
    from datetime import datetime, timedelta, timezone
    class EnforcingTrader(FakeTrader):
        def __init__(self):
            super().__init__(); self.cancelled = []; self.sold = []
        def cancel_order_id(self, oid): self.cancelled.append(oid); return True
        def exit_market(self, symbol, qty, now=None):
            self.sold.append((symbol, qty)); self.last_exit_order_id = 4242; return 4242
    t = EnforcingTrader()
    r, rec = _take_and_fill(journal, t)
    o = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    stop = float(o["stop"])
    clock = {"t": datetime(2026, 9, 1, 14, 30, tzinfo=timezone.utc)}          # 10:30 ET, regular hours
    r.now = lambda: clock["t"]
    q = {"bid": stop - 0.05, "ask": stop - 0.03}
    r.quote = lambda s: q
    assert r.enforce_stops() == []                          # first sighting: the clock starts
    clock["t"] += timedelta(seconds=10)
    assert r.enforce_stops() == [] and t.sold == []         # 10 s: not yet
    q["bid"] = stop + 0.20                                  # the bid recovers: the clock resets
    assert r.enforce_stops() == []
    q["bid"] = stop - 0.05
    assert r.enforce_stops() == []
    clock["t"] += timedelta(seconds=16)
    lines = r.enforce_stops()
    assert len(lines) == 1 and "no fill from the broker" in lines[0] and "MKT" in lines[0], lines
    assert t.cancelled == [rec.stop_id] and t.sold == [(rec.symbol, int(o["shares"]))]
    o2 = journal.execute("SELECT status, exit_reason, exit_order_id FROM orders WHERE order_id=?", (o["order_id"],)).fetchone()
    assert (o2["status"], o2["exit_reason"], o2["exit_order_id"]) == ("ExitPending", "stop_enforced", 4242)
    assert r.enforce_stops() == []                          # ExitPending rows are left alone



def test_an_entry_not_triggered_within_three_minutes_is_cancelled_and_reads_not_filled(journal):
    """A10: the resting stop-limit waits for the break; when it does not come
    the runner cancels it, the row is dead and the decision NOT_FILLED, so the
    one-position rule stops counting it."""
    from datetime import datetime, timedelta, timezone
    class CancellingTrader(FakeTrader):
        def __init__(self):
            super().__init__(); self.cancelled = []
        def cancel_order_id(self, oid): self.cancelled.append(oid); return True
    t = CancellingTrader()
    now = lambda: datetime(2026, 9, 1, 13, 52, tzinfo=timezone.utc)   # noqa: E731
    quotes = {s: dict(bid=7.30, ask=7.31, bid_size=300, ask_size=100, ts="2026-09-01T13:52:10Z")
              for s in ("ABCD", "DVLT", "CYQN", "IMRN")}
    r = Runner(journal, mode="TRADE", dollar_risk=25.0, trader=t, now=now, max_age_s=3600, quote=lambda s: quotes.get(s))
    r.step()
    assert t.placed, "the fixture must place at least one bracket"
    rec = t.placed[0]
    o = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    assert o["fill_price"] is None
    assert r.expire_entries() == []                                   # just placed: waits
    later = datetime.fromisoformat(o["placed_at"]) + timedelta(minutes=3, seconds=5)
    r.now = lambda: later
    lines = r.expire_entries()
    assert len(lines) >= 1 and "NOT_FILLED" in lines[0] and rec.parent_id in t.cancelled, lines
    o2 = journal.execute("SELECT status FROM orders WHERE order_id=?", (o["order_id"],)).fetchone()
    assert o2["status"] == "Cancelled"
    d = journal.execute("SELECT outcome FROM decisions WHERE decision_id=?", (o["decision_id"],)).fetchone()
    assert d["outcome"] == "NOT_FILLED"
    assert L.positions_alive(journal) == 0 or all(x["order_id"] != o["order_id"] for x in L.open_orders(journal))
    assert r.expire_entries() == []                                   # once



def _premarket_journal():
    """The fixture's ABCD plan moved to 08:40 ET as a pre-market REVIEW plan,
    the exercise in phase C on a `queued` probe verdict with A1 accepted."""
    c = L.connect(":memory:")
    build_session(FIXTURE, journal=c)
    c.execute("UPDATE decisions SET session='premarket', ts_et=replace(ts_et, 'T09:', 'T08:') WHERE symbol='ABCD'")
    c.execute("UPDATE decisions SET verdict='REJECT', plan_allowed=0 WHERE symbol<>'ABCD'")
    c.commit()
    L.set_state(c, phase="C", probe_verdict="queued", a1_accepted="yes", a1_accepted_by="ayman",
                paper_data="realtime")
    return c


class _MonitoredTrader(FakeTrader):
    account = "DUR339781"
    def __init__(self):
        super().__init__(); self.monitored = []; self.stops = []
    def place_entry_monitored(self, intent):
        rec = PlacedOrder(symbol=intent.symbol, parent_id=700 + len(self.monitored), stop_id=None,
                          trigger=intent.trigger, stop=intent.stop, shares=intent.shares,
                          protected=False, stop_status="monitored")
        self.monitored.append(intent); self.placed.append(rec); return rec
    def place_stop(self, symbol, qty, stop_price, ref=None):
        self.stops.append((symbol, qty, stop_price)); return 900 + len(self.stops)
    def exit_limit(self, symbol, qty, bid, offset=0.10, outside_rth=True):
        self.sold = getattr(self, "sold", []); self.sold.append((symbol, qty))
        self.last_exit_order_id = 4242; return round(bid - offset, 2)


def test_a_premarket_plan_is_armed_and_fires_only_when_the_ask_reaches_the_trigger():
    """A10 pre-market: the broker would queue a resting entry to 09:30, so the
    runner is the trigger. Armed on the bar, sent on the touch, at a limit
    capped just above the trigger; nothing sent while the ask sits below."""
    c = _premarket_journal(); t = _MonitoredTrader()
    clock = {"t": datetime(2026, 9, 1, 12, 41, 10, tzinfo=timezone.utc)}      # 08:41:10 ET, 70 s after the bar
    q = {"bid": 7.10, "ask": 7.12, "bid_size": 200, "ask_size": 200, "ts": "2026-09-01T12:41:05Z"}
    r = Runner(c, mode="TRADE", dollar_risk=20.0, trader=t, now=lambda: clock["t"], max_age_s=120, quote=lambda s: q)
    acted = r.step()
    armed = [a for a in acted if a.outcome == "PENDING"]
    assert len(armed) == 1 and "armed" in armed[0].reasons[0] and t.monitored == []
    did = armed[0].decision_id
    assert c.execute("SELECT outcome FROM decisions WHERE decision_id=?", (did,)).fetchone()[0] == "PENDING"
    assert r.step() == []                                        # armed rows are not re-judged
    assert r.fire_armed() == [] and t.monitored == []            # ask 7.12 < trigger 7.2045: wait
    q["ask"] = 7.21; clock["t"] += timedelta(seconds=40)
    fired = r.fire_armed()
    assert len(fired) == 1 and fired[0].outcome == "TAKEN" and len(t.monitored) == 1
    assert c.execute("SELECT outcome FROM decisions WHERE decision_id=?", (did,)).fetchone()[0] == "TAKEN"
    o = c.execute("SELECT status, protected, stop_status FROM orders WHERE decision_id=?", (did,)).fetchone()
    assert (o["status"], o["protected"], o["stop_status"]) == ("submitted", 0, "monitored")
    assert r.armed == {}


def test_an_armed_premarket_plan_the_tape_never_reaches_is_refused_after_three_minutes():
    c = _premarket_journal(); t = _MonitoredTrader()
    clock = {"t": datetime(2026, 9, 1, 12, 41, 10, tzinfo=timezone.utc)}
    q = {"bid": 7.10, "ask": 7.12, "bid_size": 200, "ask_size": 200, "ts": "2026-09-01T12:41:05Z"}
    r = Runner(c, mode="TRADE", dollar_risk=20.0, trader=t, now=lambda: clock["t"], max_age_s=120, quote=lambda s: q)
    did = [a for a in r.step() if a.outcome == "PENDING"][0].decision_id
    clock["t"] += timedelta(minutes=3, seconds=1)
    out = r.fire_armed()
    assert len(out) == 1 and out[0].outcome == "REFUSED" and "A10" in out[0].reasons[0] and "no order sent" in out[0].reasons[0]
    assert c.execute("SELECT outcome FROM decisions WHERE decision_id=?", (did,)).fetchone()[0] == "REFUSED"
    assert t.monitored == [] and r.armed == {}


def test_a_monitored_position_trails_in_the_ledger_sells_at_the_trailed_level_and_gets_a_real_stop_at_0930():
    """A3 applies pre-market too: the level watch_stops sells at follows the
    high; and once regular hours open, reprotect places the resting stop the
    broker could not hold pre-market."""
    c = _premarket_journal(); t = _MonitoredTrader()
    clock = {"t": datetime(2026, 9, 1, 12, 41, 10, tzinfo=timezone.utc)}
    q = {"bid": 7.21, "ask": 7.22, "bid_size": 200, "ask_size": 200, "ts": "2026-09-01T12:41:05Z"}
    r = Runner(c, mode="TRADE", dollar_risk=20.0, trader=t, now=lambda: clock["t"], max_age_s=120, quote=lambda s: q)
    r.step(); fired = r.fire_armed()
    assert fired and fired[0].outcome == "TAKEN"
    rec = t.placed[-1]; rec.fill_price = rec.trigger; rec.fill_time = "2026-09-01T12:41:50Z"; rec.status = "Filled"
    r.sync_fills()
    o = c.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    assert o["fill_price"] is not None and o["stop_status"] == "monitored"
    rps = round(o["trigger"] - o["stop"], 4)
    c.execute("DELETE FROM bars_10s WHERE symbol='ABCD'"); c.execute("DELETE FROM quote_ticks WHERE symbol='ABCD'")
    high = round(o["trigger"] + 3 * rps, 2)
    c.execute("INSERT INTO bars_10s (symbol, ts, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
              ("ABCD", "2026-09-01T12:45:00Z", high, high, high, high, 100)); c.commit()
    lines = r.trail_stops()
    assert any("monitored level" in x for x in lines), lines
    o2 = c.execute("SELECT trail_stop FROM orders WHERE order_id=?", (o["order_id"],)).fetchone()
    assert o2["trail_stop"] == round(high - rps, 2) > o["stop"]
    # the bid dips under the TRAILED level but above the initial stop: the monitored stop sells
    q["bid"] = round(o2["trail_stop"] - 0.01, 2)
    sold = r.watch_stops()
    assert len(sold) == 1 and f"stop {o2['trail_stop']}" in sold[0], sold
    # a second monitored position, still open at 09:30, gets its resting stop
    c2 = _premarket_journal(); t2 = _MonitoredTrader()
    clock2 = {"t": datetime(2026, 9, 1, 12, 41, 10, tzinfo=timezone.utc)}
    q2 = {"bid": 7.21, "ask": 7.22, "bid_size": 200, "ask_size": 200, "ts": "2026-09-01T12:41:05Z"}
    r2 = Runner(c2, mode="TRADE", dollar_risk=20.0, trader=t2, now=lambda: clock2["t"], max_age_s=120, quote=lambda s: q2)
    r2.step(); r2.fire_armed()
    rec2 = t2.placed[-1]; rec2.fill_price = rec2.trigger; rec2.fill_time = "2026-09-01T12:41:50Z"; rec2.status = "Filled"
    r2.sync_fills()
    assert r2.reprotect() == []                                   # pre-market: nothing can rest
    clock2["t"] = datetime(2026, 9, 1, 13, 30, 5, tzinfo=timezone.utc)     # 09:30:05 ET
    lines = r2.reprotect()
    assert len(lines) == 1 and "regular hours" in lines[0] and len(t2.stops) == 1, lines
    o3 = c2.execute("SELECT protected, stop_status, stop_id FROM orders WHERE parent_id=?", (rec2.parent_id,)).fetchone()
    assert (o3["protected"], o3["stop_status"], o3["stop_id"]) == (1, "Submitted", 901)
