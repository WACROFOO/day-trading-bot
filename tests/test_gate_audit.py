"""The gate audit: read-only, prospective-only, and it reports the runners a
gate killed rather than averaging them away."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from journal import actuals, bars, ledger as L  # noqa: E402
from momentum_platform.dashboard.session_builder import build_session  # noqa: E402

import gate_audit  # noqa: E402

FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"


def _ledger():
    conn = L.connect(":memory:")
    build_session(FIXTURE, journal=conn)
    actuals.fill_all(conn, bars.from_fixture(FIXTURE))
    return conn


def test_the_audit_never_writes(capsys):
    """It judges gates; a judge that edits the record is the defect R11 hunts."""
    conn = _ledger()
    before = conn.total_changes
    for g in [r[0] for r in conn.execute(
            "SELECT DISTINCT killed_by FROM decisions WHERE killed_by IS NOT NULL")]:
        gate_audit.audit_gate(conn, g)
    assert conn.total_changes == before
    capsys.readouterr()


def test_a_killed_runner_is_named_not_averaged(capsys):
    """The reason the audit exists: IMCC 2026-09-18, killed on `rising` four
    times while it ran 3 -> 8. A mean over the cohort hides exactly that row,
    so any kill that went on to run at least 2R is listed by name."""
    conn = _ledger()
    row = conn.execute("SELECT decision_id FROM decisions WHERE killed_by IS NOT NULL "
                       "LIMIT 1").fetchone()
    gate = conn.execute("SELECT killed_by FROM decisions WHERE decision_id=?",
                        (row[0],)).fetchone()[0]
    # Make this kill a triggered runner: MFE 3.4R and the tape reached the entry.
    conn.execute("UPDATE actuals SET mfe_r_planned=3.4, trigger_hit=1, risk_share=0.1 "
                 "WHERE decision_id=?", (row[0],))
    gate_audit.audit_gate(conn, gate)
    out = capsys.readouterr().out
    assert "killed, then ran" in out and "+3.40R" in out


def test_backfill_kills_are_not_evidence(capsys):
    """A decision armed on loaded history is a diagnostic, not a miss."""
    conn = _ledger()
    conn.execute("UPDATE decisions SET data_status='replay-backfill'")
    for g in [r[0] for r in conn.execute(
            "SELECT DISTINCT killed_by FROM decisions WHERE killed_by IS NOT NULL")]:
        gate_audit.audit_gate(conn, g)
    out = capsys.readouterr().out
    assert "0 prospective kill(s)" in out
