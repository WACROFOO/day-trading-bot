"""Scratch: after a double sale the broker holds -qty. Does any runner path see it?"""
import sys
from pathlib import Path
from types import SimpleNamespace as NS
ROOT = Path("/home/user/day-trading-bot")
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "tests"))
from test_runner import journal, FakeTrader, _take_and_fill  # noqa: F401


class ShortIB:
    def __init__(self, sym, q): self.sym, self.q = sym, q
    def positions(self): return [NS(position=self.q, contract=NS(symbol=self.sym))]
    def trades(self): return []
    def fills(self): return []


def test_a_short_left_by_a_double_sale_is_not_reported(journal):
    t = FakeTrader()
    r, rec = _take_and_fill(journal, t)
    o = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    t.ib = ShortIB(rec.symbol, -int(o["shares"]))
    out = r.reconcile_positions()
    print("reconcile lines with the broker SHORT:", out)
    assert not any("-" + str(int(o["shares"])) in x or "SHORT" in x.upper() for x in out)
