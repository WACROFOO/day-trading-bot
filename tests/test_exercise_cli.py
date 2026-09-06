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
    assert "REJECTS" in out.stdout and "✗ float" in out.stdout

    chk = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "check"],
                         cwd=ROOT, capture_output=True, text=True)
    assert chk.returncode == 0 and "5/5 reproduced" in chk.stdout
