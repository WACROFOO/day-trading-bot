"""Owner decision 2026-09-28: the real account ($2,000) caps every position's
value, whatever the paper account's NetLiquidation says."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from execution.intent import sized_for  # noqa: E402
from journal import ledger as L  # noqa: E402


def test_account_cap_bounds_shares():
    # $40 risk on a 10c stop wants 400 shares = $4,000 of a $10 stock; a $2,000 account allows 200
    n, _ = sized_for(10.00, 9.90, 40.0, max_notional=min(1_000_000.0, 2000.0))
    assert n == 200
    n, _ = sized_for(3.00, 2.90, 40.0, max_notional=2000.0)
    assert n == 400                      # $1,200 of stock: the risk decides, not the cap


def test_account_size_is_a_state_field(tmp_path):
    conn = L.connect(tmp_path / "j.sqlite")
    st = L.set_state(conn, dollar_risk=40.0, account_size=2000.0)
    assert st["account_size"] == 2000.0 and st["dollar_risk"] == 40.0
