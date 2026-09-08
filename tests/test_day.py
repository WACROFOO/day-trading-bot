"""The day runner's decisions are pure and testable: which names, which mode,
whether pre-market is allowed, what blocks a phase advance, and the report."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

import day  # noqa: E402
from journal import actuals, bars, ledger as L  # noqa: E402
from momentum_platform.dashboard.session_builder import build_session  # noqa: E402

FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"


def test_watchlist_is_stars_then_watch_and_rejects_keep_their_reason():
    rows = [dict(sym="AAA", verdict="WATCH", reasons=["x"]),
            dict(sym="BBB", verdict="STAR", reasons=[]),
            dict(sym="CCC", verdict="REJECT", reasons=["float over 20M"]),
            dict(sym="DDD", verdict="STAR", reasons=[])]
    picked, rejects = day.pick_watchlist(rows, cap=8)
    assert picked == ["BBB", "DDD", "AAA"]
    assert rejects == [("CCC", "float over 20M")]
    assert day.pick_watchlist(rows, cap=2)[0] == ["BBB", "DDD"]


def test_mode_follows_the_phase():
    assert day.mode_for({"phase": "A"}) == "LOG_ONLY"
    assert day.mode_for({"phase": "B"}) == "TRADE"
    assert day.mode_for({"phase": "C"}) == "TRADE"
    assert day.mode_for({"phase": "D"}) == "LOG_ONLY"


def test_premarket_needs_phase_c_and_a_probe_verdict():
    assert day.premarket_allowed({"phase": "B", "probe_verdict": "held"})[0] is False
    assert day.premarket_allowed({"phase": "C", "probe_verdict": None})[0] is False
    ok, why = day.premarket_allowed({"phase": "C", "probe_verdict": "held"})
    assert ok and "brackets" in why
    ok, why = day.premarket_allowed({"phase": "C", "probe_verdict": "queued"})
    assert ok and "UNPROTECTED" in why
    assert day.premarket_allowed({"phase": "C", "probe_verdict": "inconclusive"})[0] is False


@pytest.fixture
def journal():
    c = L.connect(":memory:")
    build_session(FIXTURE, journal=c)
    actuals.fill_all(c, bars.from_ledger(c))
    yield c
    c.close()


def test_phase_a_is_blocked_until_sessions_and_probe(journal):
    nxt, blockers = day.gates_for_advance(journal, L.get_state(journal))
    assert nxt == "B"
    assert any("5 sessions or 40 decisions" in b for b in blockers)
    assert any("probe" in b for b in blockers)
    L.set_state(journal, sessions_done=5, probe_verdict="held", probe_date="2026-09-08")
    nxt, blockers = day.gates_for_advance(journal, L.get_state(journal))
    # still blocked twice over: "5 sessions or 40 decisions, whichever is
    # later" means BOTH; the fixture has 5 decisions. And the paper tape has
    # not been measured.
    assert any("40 decisions" in b for b in blockers)
    assert any("paper session data" in b for b in blockers)
    # Fabricate the decision count by cloning a real row: the padding must
    # replay (R11 runs inside the gate), so its inputs must reproduce its verdict.
    tmpl = journal.execute("SELECT verdict, killed_by, plan_allowed, inputs_json FROM decisions LIMIT 1").fetchone()
    for _ in range(35):
        journal.execute("INSERT INTO decisions (decision_id, ts_et, session, symbol, source, verdict, killed_by, plan_allowed, gates_json, warnings_json, inputs_json, recorded_at) "
                        "VALUES (?, '2026-09-01T10:00:00-04:00', 'regular', 'PAD', 'pullback', ?, ?, ?, '[]', '[]', ?, 'x')",
                        (f"pad{_}", tmpl["verdict"], tmpl["killed_by"], tmpl["plan_allowed"], tmpl["inputs_json"]))
    journal.commit()
    nxt, blockers = day.gates_for_advance(journal, L.get_state(journal))
    assert blockers and all("paper session data" in b for b in blockers)
    L.set_state(journal, paper_data="realtime", paper_data_date="2026-09-08")
    nxt, blockers = day.gates_for_advance(journal, L.get_state(journal))
    assert blockers == []


def test_phase_b_is_blocked_by_too_few_trades_and_by_any_unprotected_fill(journal):
    L.set_state(journal, phase="B", probe_verdict="held", paper_data="realtime")
    nxt, blockers = day.gates_for_advance(journal, L.get_state(journal))
    assert nxt == "C" and any("30 taken" in b for b in blockers)
    did = L.decisions(journal, plan_allowed=1)[0]["decision_id"]
    oid = L.record_order(journal, did, symbol="X", account="DU1", session="regular", parent_id=1,
                         stop_id=2, target_id=None, trigger=5.0, stop=4.8, target=None,
                         shares=10, dollar_risk=2.0, protected=False)
    L.record_fill(journal, oid, fill_price=5.02, fill_ts="2026-09-01T14:00:00Z")
    _, blockers = day.gates_for_advance(journal, L.get_state(journal))
    assert any("unprotected" in b for b in blockers)


def test_a_replay_divergence_blocks_every_advance(journal):
    import json
    row = journal.execute("SELECT decision_id, inputs_json FROM decisions LIMIT 1").fetchone()
    inp = json.loads(row["inputs_json"]); inp["last"] = 1.0
    journal.execute("UPDATE decisions SET inputs_json=? WHERE decision_id=?", (json.dumps(inp), row["decision_id"]))
    L.set_state(journal, sessions_done=9, probe_verdict="held")
    _, blockers = day.gates_for_advance(journal, L.get_state(journal))
    assert any("replay check" in b for b in blockers)


def test_the_report_is_written_in_the_design_layout(journal, tmp_path, monkeypatch):
    monkeypatch.setattr(day, "REPORTS", tmp_path)
    path = day.write_report(journal, "2026-09-01", "fixture", synthetic=True)
    txt = path.read_text()
    assert txt.startswith("# Paper exercise — 2026-09-01")
    assert "SYNTHETIC FIXTURE" in txt
    for h in ("## Funnel", "## Rejects", "## Controls", "## Replay", "## Not checked"):
        assert h in txt
    assert "| EPHZ | REJECT | SUPPRESSED |" in txt and "float" in txt
    assert "5/5 decisions reproduce" in txt


def test_dry_run_touches_nothing_and_exits_zero(tmp_path):
    out = subprocess.run([sys.executable, "scripts/day.py", "--dry-run", "--symbols", "AAPL"],
                         cwd=ROOT, env={**__import__("os").environ, "JOURNAL_DB": str(tmp_path / "j.sqlite")},
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    # whichever branch the clock took, nothing may have been started
    assert "Popen" not in out.stdout and out.stderr == ""


def test_advance_refuses_when_blocked(tmp_path):
    db = tmp_path / "j.sqlite"
    subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "replay", str(FIXTURE)],
                   cwd=ROOT, capture_output=True, text=True)
    r = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "advance"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 1 and "blocked" in r.stdout
    st = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "state"],
                        cwd=ROOT, capture_output=True, text=True)
    assert "phase          A" in st.stdout


def test_a_day_with_no_bars_is_not_counted_as_a_session(tmp_path, monkeypatch):
    """2026-09-07, Labor Day: the whole chain ran and the feed was rightly
    STALE all morning. That must not count toward the five log-only sessions."""
    monkeypatch.setattr(day, "REPORTS", tmp_path)
    c = L.connect(":memory:")                     # no bars at all
    monkeypatch.setattr(day, "DB", tmp_path / "j.sqlite")
    before = L.get_state(c)["sessions_done"]
    day.after_close(c, "2026-09-07", dry=False)
    assert L.get_state(c)["sessions_done"] == before


def test_the_stop_probe_is_deferred_not_skipped_when_the_day_starts_at_0655():
    src = (ROOT / "scripts/day.py").read_text()
    assert "deferred to 07:00" in src
    assert "PREMARKET_START <= t < REGULAR_START" in src


def test_rehearsal_runs_on_a_closed_market_forced_log_only_and_is_not_a_session(tmp_path, monkeypatch):
    """The desk had never connected through the Gateway before Tuesday. A
    rehearsal exercises desk -> ledger -> runner on a shut market, log-only,
    for a bounded time, and counts nothing."""
    import day as d
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    frozen = datetime(2026, 9, 7, 9, 0, tzinfo=ZoneInfo("America/New_York"))   # Labor Day

    class FrozenDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen if tz else frozen.replace(tzinfo=None)
    monkeypatch.setattr(d, "datetime", FrozenDT)
    monkeypatch.setattr(d, "DB", tmp_path / "j.sqlite")
    monkeypatch.setattr(d.time, "sleep", lambda s: None)
    started = []

    class P:
        returncode = 0
        def poll(self): return None
        def send_signal(self, *_): pass
        def wait(self, timeout=None): pass
    monkeypatch.setattr(d, "start_desk", lambda syms, dry: started.append(("desk", syms)) or P())
    monkeypatch.setattr(d, "desk_is_on_ibkr", lambda proc, timeout_s=150: True)
    monkeypatch.setattr(d, "start_runner", lambda mode, risk, dry: started.append(("runner", mode)) or P())
    # the loop must terminate: make the deadline already past on the second look
    calls = {"n": 0}
    real_now = FrozenDT.now
    def ticking(tz=None):
        calls["n"] += 1
        return real_now(tz) + timedelta(minutes=calls["n"] * 5)
    monkeypatch.setattr(FrozenDT, "now", classmethod(lambda cls, tz=None: ticking(tz)))
    rc = d.main(["--rehearsal", "1", "--symbols", "AAPL"])
    assert rc == 0
    assert ("desk", ["AAPL"]) in started
    assert ("runner", "LOG_ONLY") in started
    assert L.get_state(L.connect(tmp_path / "j.sqlite"))["sessions_done"] == 0
