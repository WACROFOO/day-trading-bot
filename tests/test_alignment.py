"""The feed's health reaches the verdict; no order leaves on a stale desk
quote; the alignment table measures the lag instead of assuming it."""
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
from momentum_platform.dashboard.session_builder import (  # noqa: E402
    _feed_is_stale, build_session, build_session_from_records)
import json  # noqa: E402

FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"


def records():
    return [json.loads(l) for l in FIXTURE.read_text().splitlines()
            if l.strip() and not l.startswith("#")]


# ------------------------------------------------------------ feed health
def test_only_live_and_replay_count_as_a_current_tape():
    assert _feed_is_stale("live") is False and _feed_is_stale("replay") is False
    for word in ("stale", "delayed", "offline", "STALE", "", None):
        assert _feed_is_stale(word) is True


def test_a_stale_feed_yields_stale_verdicts_and_no_plans():
    """The screenshot: `1D BEHIND` and `Entry ARMED` in the same frame. The
    stream knew it was stale; the cascade was never told."""
    live = build_session_from_records(records(), "t", "fixture", data_status="live")
    stale = build_session_from_records(records(), "t", "fixture", data_status="stale")
    assert live["plans"], "the fixture arms plans on a live tape"
    assert stale["plans"] == [], "a stale tape arms nothing"
    assert len(stale["suppressedPlans"]) == len(live["plans"]) + len(live["suppressedPlans"])
    assert {c["verdict"] for c in stale["cascade"].values()} == {"STALE"}
    assert all(c["planAllowed"] is False for c in stale["cascade"].values())


def test_delayed_data_is_stale_too():
    s = build_session_from_records(records(), "t", "fixture", data_status="delayed")
    assert s["plans"] == [] and {c["verdict"] for c in s["cascade"].values()} == {"STALE"}


def test_a_stale_session_journals_its_decisions_as_suppressed_with_the_reason():
    c = L.connect(":memory:")
    build_session_from_records(records(), "t", "fixture", data_status="stale", journal=c)
    rows = L.decisions(c)
    assert rows and all(r["outcome"] == "SUPPRESSED" and r["verdict"] == "STALE" for r in rows)


# ------------------------------------------------------- order-time gate
class FakeTrader:
    account = "DUR339781"
    def __init__(self): self.placed = []; self.intents = []
    def place_bracket(self, intent, now=None):
        self.intents.append(intent)
        rec = PlacedOrder(symbol=intent.symbol, parent_id=100 + len(self.placed), stop_id=1,
                          trigger=intent.trigger, stop=intent.stop, shares=intent.shares, protected=True)
        self.placed.append(rec); return rec
    def sync(self): pass


NOW = lambda: datetime(2026, 9, 1, 13, 52, tzinfo=timezone.utc)   # noqa: E731


def test_trade_mode_refuses_when_the_desk_has_no_fresh_quote_for_the_symbol():
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c)
    t = FakeTrader()
    r = Runner(c, mode="TRADE", dollar_risk=20.0, trader=t, now=NOW, max_age_s=3600,
               quote=lambda s: None)
    done = r.step()
    assert done and all(a.outcome == "REFUSED" for a in done)
    assert all(any("no fresh desk quote" in x for x in a.reasons) for a in done)
    assert t.intents == []


def test_trade_mode_places_when_the_desk_quote_is_fresh():
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c)
    t = FakeTrader()
    r = Runner(c, mode="TRADE", dollar_risk=20.0, trader=t, now=NOW, max_age_s=3600,
               quote=lambda s: dict(bid=1.0, ask=1.01, bid_size=1, ask_size=1, ts="2026-09-01T13:52:00Z"))
    assert any(a.outcome == "TAKEN" for a in r.step())


def test_log_only_does_not_need_a_quote():
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c)
    done = Runner(c, mode="LOG_ONLY", dollar_risk=20.0).step()
    assert {a.outcome for a in done} == {"LOG_ONLY"}


# ------------------------------------------------------ alignment table
def test_alignment_rows_measure_the_gap_between_fill_stamp_and_quote_stamp():
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c)
    did = L.decisions(c, plan_allowed=1)[0]["decision_id"]
    oid = L.record_order(c, did, symbol="ABCD", account="DU1", session="regular", parent_id=1,
                         stop_id=2, target_id=None, trigger=7.20, stop=7.05, target=None,
                         shares=100, dollar_risk=15.0, protected=True)
    L.record_fill(c, oid, fill_price=7.23, fill_ts="2026-09-01T13:52:05Z",
                  nbbo=dict(bid=7.22, ask=7.24, bid_size=300, ask_size=100, ts="2026-09-01T13:52:09Z"))
    (row,) = L.alignment_rows(c)
    assert row["d_bid"] is not None and row["fill_price"] == 7.23
    assert row["quote_gap_s"] == 4                        # quote stamped 4s after the fill
    assert row["slippage_ratio"] == pytest.approx(1.2, abs=1e-3)   # (7.23-7.05)/(7.20-7.05)


def test_paper_data_verdict_is_persisted_and_migrated_onto_an_old_db(tmp_path):
    import sqlite3
    db = tmp_path / "old.sqlite"
    # an exercise_state table from before the alignment columns existed
    raw = sqlite3.connect(db)
    raw.execute("""CREATE TABLE exercise_state (key TEXT PRIMARY KEY CHECK (key='state'),
                   phase TEXT NOT NULL DEFAULT 'A', sessions_done INTEGER NOT NULL DEFAULT 0,
                   probe_verdict TEXT, probe_date TEXT, dollar_risk REAL, updated_at TEXT NOT NULL)""")
    raw.execute("INSERT INTO exercise_state (key, updated_at) VALUES ('state','x')"); raw.commit(); raw.close()
    c = L.connect(db)
    st = L.set_state(c, paper_data="delayed", paper_data_date="2026-09-08")
    assert st["paper_data"] == "delayed" and st["phase"] == "A"
