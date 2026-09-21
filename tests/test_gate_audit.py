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


def test_the_float_only_cohort_is_a_re_evaluation_not_the_first_kill_column(capsys):
    """Review item 5. killed_by='float' is the FIRST gate to fail. Two crafted
    rows: one fails nothing but float, one fails float and price. Only the
    first is float-only."""
    import json
    conn = _ledger()
    rows = conn.execute("SELECT decision_id, inputs_json FROM decisions WHERE plan_allowed=1 LIMIT 2").fetchall()
    assert len(rows) == 2
    for i, r in enumerate(rows):
        inp = json.loads(r["inputs_json"])
        inp["float_shares"] = 30_000_000
        inp["float_is_shares_outstanding"] = False
        inp["float_verified"] = True
        if i == 1:
            inp["last"] = 0.50                      # also fails the price gate
        conn.execute("UPDATE decisions SET killed_by='float', plan_allowed=0, inputs_json=? WHERE decision_id=?",
                     (json.dumps(inp), r["decision_id"]))
    conn.commit()
    c = gate_audit.float_only_cohort(conn)
    assert c["float_killed"] == 2 and c["float_only"] == 1 and c["also_failed"] == {"price": 1}
    before = conn.total_changes
    gate_audit.print_float_only(conn)
    assert conn.total_changes == before
    out = capsys.readouterr().out
    assert "1 fail NOTHING but float" in out and "price 1" in out


def test_catalyst_states_keep_unknown_apart_from_none(capsys):
    """Review item 6. A dead feed is UNKNOWN, a healthy feed with no headline
    is NONE, and a kill on UNKNOWN is not evidence about catalysts."""
    import json
    conn = _ledger()
    total = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
    r = conn.execute("SELECT decision_id, inputs_json FROM decisions LIMIT 1").fetchone()
    inp = json.loads(r["inputs_json"]); inp["catalyst_source_ok"] = False; inp["catalyst_today"] = False
    conn.execute("UPDATE decisions SET inputs_json=?, killed_by='catalyst' WHERE decision_id=?",
                 (json.dumps(inp), r["decision_id"])); conn.commit()
    c = gate_audit.catalyst_states(conn)
    assert sum(c["all"].values()) == total
    assert c["all"]["UNKNOWN"] == 1 and c["catalyst_killed"] == {"UNKNOWN": 1}
    assert sum(sum(d.values()) for d in c["by_day"].values()) == total
    gate_audit.print_catalyst_states(conn)
    assert "UNKNOWN 1" in capsys.readouterr().out


def test_a_row_without_the_feed_flag_is_unrecorded_not_none():
    """The owner's run, 2026-09-21: every pre-A2 catalyst kill read NONE
    because the key did not exist yet and the default is True. That is not a
    healthy feed; it is a state the ledger never recorded."""
    import json
    conn = _ledger()
    r = conn.execute("SELECT decision_id, inputs_json FROM decisions LIMIT 1").fetchone()
    inp = json.loads(r["inputs_json"]); inp.pop("catalyst_source_ok", None); inp["catalyst_today"] = False
    conn.execute("UPDATE decisions SET inputs_json=? WHERE decision_id=?", (json.dumps(inp), r["decision_id"])); conn.commit()
    c = gate_audit.catalyst_states(conn)
    assert c["all"].get("UNRECORDED") == 1
