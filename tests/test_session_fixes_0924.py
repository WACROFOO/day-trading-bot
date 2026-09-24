"""Fixes from the 2026-09-24 session: the headline fetch off the rebuild path,
O(window) history queries in the engine, scratches out of the loss streak,
in-memory grading for an unsettled day, and the automatic settle of a day the
desk did not finish."""
from __future__ import annotations

import random
import sys
import threading
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

import day  # noqa: E402
from journal import actuals, bars as B, controls, ledger as L  # noqa: E402
from journal.risk import JournalRiskGate, Limits  # noqa: E402
from momentum_platform.dashboard.session_builder import build_session  # noqa: E402
from momentum_platform.models import Bar  # noqa: E402
from momentum_platform.state import SymbolState  # noqa: E402

FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"
UTC = timezone.utc


# ------------------------------------------------------------ engine queries
def _naive_price(bars, now, minutes):
    cutoff = now - timedelta(minutes=minutes); cand = None
    for b in bars:
        if b.ts <= cutoff: cand = b.close
        else: break
    return cand


def _naive_vol(bars, now, minutes):
    cutoff = now - timedelta(minutes=minutes)
    return sum(b.volume for b in bars if b.ts >= cutoff)


def _naive_5m(bars, count):
    bars = list(bars); out = []
    for i in range(len(bars) - 5, -1, -5):
        chunk = bars[i:i + 5]
        if len(chunk) == 5: out.append(sum(b.volume for b in chunk))
        if len(out) >= count: break
    out.reverse(); return out


def test_history_queries_walk_back_and_give_the_old_answers():
    random.seed(7)
    st = SymbolState("X")
    t0 = datetime(2026, 9, 24, 8, 0, tzinfo=UTC)
    px = 5.0
    # gaps in the tape on purpose: minutes with no prints are absent
    for m in range(0, 420):
        if random.random() < 0.15:
            continue
        px = round(px * (1 + random.gauss(0, 0.003)), 4)
        st.minute_bars.append(Bar(symbol="X", timeframe="1m", ts=t0 + timedelta(minutes=m),
                                  open=px, high=px, low=px, close=px, volume=random.randint(0, 5000)))
    ref = list(st.minute_bars)
    for now_min in (0, 3, 17, 60, 240, 419, 500):
        now = t0 + timedelta(minutes=now_min, seconds=30)
        for w in (1, 5, 10, 30):
            assert st.price_minutes_ago(now, w) == _naive_price(ref, now, w)
            assert st.volume_last_minutes(now, w) == _naive_vol(ref, now, w)
    for count in (1, 3, 20, 100, 1000):
        assert st.completed_5m_volumes(count) == _naive_5m(ref, count)
    assert SymbolState("E").price_minutes_ago(t0, 5) is None and SymbolState("E").completed_5m_volumes() == []


# ------------------------------------------------------------ risk streak
def test_scratches_neither_grow_nor_reset_the_loss_streak(monkeypatch):
    c = L.connect(":memory:")
    from journal import risk
    seq = {"t": []}
    monkeypatch.setattr(risk, "closed_trades", lambda conn, day: list(seq["t"]))
    gate = JournalRiskGate(c, Limits(max_daily_loss_r=99, consecutive_losses=3, max_entries_per_day=99))
    seq["t"] = [{"r": -0.04}, {"r": -0.02}]                       # 2026-09-24 PFSA, GRML
    assert gate.state()["consecutive_losses"] == 0
    seq["t"] = [{"r": -1.0}, {"r": -0.04}, {"r": -1.0}]           # a scratch between two losses keeps the streak
    assert gate.state()["consecutive_losses"] == 2
    seq["t"] = [{"r": -1.0}, {"r": +0.65}, {"r": -1.0}]           # a real win ends it
    assert gate.state()["consecutive_losses"] == 1
    seq["t"] = [{"r": -0.3}, {"r": -0.25}, {"r": -1.0}]           # −0.25 R is a loss, not a scratch
    assert gate.state()["consecutive_losses"] == 3
    assert gate.state()["day_r"] == -1.55                         # the daily sum still counts everything


# ------------------------------------------------------------ in-memory grading
def test_per_decision_grades_ungraded_rows_in_memory_and_matches_the_settle():
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c)
    bars = B.from_fixture(FIXTURE)
    before = controls.per_decision(c, bars, "2026-09-01")
    assert before and all(d["actuals_source"] == "in-memory" for d in before if d["has_actuals"])
    assert any(d["trigger_hit"] == 1 and d["strategy_r"] is not None for d in before), "the fixture has triggered plans"
    assert c.execute("SELECT COUNT(*) FROM actuals").fetchone()[0] == 0        # nothing written
    actuals.fill_all(c, bars)
    after = controls.per_decision(c, bars, "2026-09-01")
    assert all(d["actuals_source"] == "ledger" for d in after if d["has_actuals"])
    key = lambda d: (d["decision_id"], d["trigger_hit"], d["first_hit"], d["strategy_r"], d["trail_r"], d["mfe_r_planned"])   # noqa: E731
    assert sorted(map(key, before)) == sorted(map(key, after))


# ------------------------------------------------------------ settle at the next start
def test_an_unsettled_previous_day_is_settled_at_the_next_start(tmp_path, monkeypatch):
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c)
    L.record_bars(c, B.from_fixture(FIXTURE)); c.commit()
    monkeypatch.setattr(day, "REPORTS", tmp_path)
    called = []
    monkeypatch.setattr(day, "_backfill", lambda d: called.append(d) or 0)
    monkeypatch.setattr(day, "ibkr_port", lambda env=None: ("4002", "detected"))
    n0 = L.get_state(c)["sessions_done"]
    assert day.settle_unsettled(c, "2026-09-01", dry=False) is None            # never for today
    assert day.settle_unsettled(c, "2026-09-02", dry=False) == "2026-09-01"
    assert called == ["2026-09-01"]
    st = L.get_state(c)
    assert st["sessions_done"] == n0 + 1 and st["last_session_date"] == "2026-09-01"
    assert c.execute("SELECT COUNT(*) FROM decisions d LEFT JOIN actuals a USING(decision_id) WHERE a.decision_id IS NULL").fetchone()[0] == 0
    assert day.settle_unsettled(c, "2026-09-02", dry=False) is None            # graded: nothing to do
    assert L.get_state(c)["sessions_done"] == n0 + 1


# ------------------------------------------------------------ headlines off the worker
def test_headlines_are_fetched_off_the_worker_and_merged_on_it(monkeypatch):
    from momentum_platform.dashboard import ibkr_desk as D
    desk = D.IbkrDesk.__new__(D.IbkrDesk)
    desk._news, desk._news_note, desk._news_thread = [], None, None
    desk.scan_in_thread = True
    desk.logs = []
    desk.log = lambda line: desk.logs.append(line)
    submitted = []
    desk.submit = lambda fn, *a: submitted.append((fn, a))
    fetch_thread = {}
    def fake_news(symbols):
        fetch_thread["name"] = threading.current_thread().name
        return [{"type": "news", "symbol": symbols[0], "provider_id": "p1", "headline": "h"}], None
    monkeypatch.setattr(D, "news_records", fake_news)
    desk._pull_headlines(["AAA"])
    desk._news_thread.join(5)
    assert fetch_thread["name"] == "desk-headlines"                # the HTTP call left the worker
    assert desk._news == []                                        # nothing merged until the worker runs the job
    fn, args = submitted[0]; fn(*args)
    assert len(desk._news) == 1 and desk.logs == ["  headlines: 1 new"]
    fn(*args)                                                      # the same records again: deduped
    assert len(desk._news) == 1
    # inline path (tests, bootstrap): merged at once
    desk.scan_in_thread = False
    monkeypatch.setattr(D, "news_records", lambda symbols: ([], "headlines unavailable: boom"))
    desk._pull_headlines(["AAA"])
    assert desk._news_note == "headlines unavailable: boom"
