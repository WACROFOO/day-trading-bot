"""The exercise CLI runs the whole path on the fixture and exits 0, and the
replay check exits non-zero on divergence."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"


def test_replay_then_check_on_the_fixture(tmp_path):
    db = tmp_path / "j.sqlite"
    out = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "replay",
                          str(FIXTURE), "--risk", "20"], cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "SYNTHETIC FIXTURE" in out.stdout          # labelled, always
    assert "5 plans armed" in out.stdout and "5/5 decisions reproduce" in out.stdout
    assert "REJECTS" in out.stdout and "✗ pillars" in out.stdout   # A5

    chk = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "check"],
                         cwd=ROOT, capture_output=True, text=True)
    assert chk.returncode == 0 and "5/5 reproduced" in chk.stdout


def test_missed_scores_every_armed_plan_of_the_day_and_groups_by_reason(tmp_path):
    """2026-09-22: three taken, 18 refused, 72 killed, and no tool output on
    what the refused and killed plans went on to do. `missed` scores each
    one like a taken trade (fill at trigger, planned R) and sums per reason,
    backfill rows excluded from the sums."""
    db = tmp_path / "j.sqlite"
    out = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "replay",
                          str(FIXTURE), "--risk", "20"], cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    ms = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "missed", "--all"],
                        cwd=ROOT, capture_output=True, text=True)
    assert ms.returncode == 0, ms.stderr[-1200:]
    assert "NOT TAKEN vs TAKEN · 2026-09-01" in ms.stdout and "BY REASON" in ms.stdout
    assert "killed: pillars" in ms.stdout                    # the fixture's A5 kills, scored
    assert "upper bound, not a trade" in ms.stdout
    none = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "missed", "--day", "2031-01-01"],
                          cwd=ROOT, capture_output=True, text=True)
    assert none.returncode == 1 and "no decisions on 2031-01-01" in none.stdout


def test_missed_counts_thin_stops_as_a_measurement_not_a_gate(tmp_path):
    """A9 is written from a number: plans whose stop sits inside 0.5% of the
    trigger are marked ‡ and summed. Nothing refuses on the mark."""
    import sqlite3
    db = tmp_path / "j.sqlite"
    subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "replay", str(FIXTURE), "--risk", "20"],
                   cwd=ROOT, capture_output=True, text=True, check=True)
    c = sqlite3.connect(db)
    did = c.execute("SELECT decision_id FROM decisions WHERE data_status NOT LIKE '%-backfill' OR data_status IS NULL LIMIT 1").fetchone()[0]
    c.execute("UPDATE decisions SET trigger=17.19, stop=17.17 WHERE decision_id=?", (did,)); c.commit(); c.close()
    ms = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "missed", "--all"],
                        cwd=ROOT, capture_output=True, text=True)
    assert ms.returncode == 0, ms.stderr[-1200:]
    assert "‡thin stop" in ms.stdout and "THIN STOPS" in ms.stdout and "17.19/17.17" in ms.stdout
    assert "0.12% of price" in ms.stdout and "not a gate" in ms.stdout
