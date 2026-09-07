import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import alignment_probe as ap  # noqa: E402


def test_same_port_is_single_login_mode():
    assert ap.probe_mode(4002, 4002, live_reachable=False) == "single"
    assert ap.probe_mode(4002, 4002, live_reachable=True) == "single"


def test_two_ports_compare_only_when_the_live_side_answers():
    assert ap.probe_mode(7496, 4002, live_reachable=True) == "compare"
    assert ap.probe_mode(7496, 4002, live_reachable=False) == "paper-only"


def test_account_ids_are_masked_in_output():
    assert ap.mask("U27412209") == "U****2209"
    assert ap.mask("DUR339781") == "D****9781"
