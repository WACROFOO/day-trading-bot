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
    # still blocked: the paper session's tape has not been measured. The first
    # real orders must not be judged against prices the decision never saw.
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
