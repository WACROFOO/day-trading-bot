"""Scratch (not in the repo): does HEAD's enforce_stops sell on top of a stop that
(a) the broker already reports Filled (cancel_order_id -> False), or
(b) fills while the cancel is in flight (cancel 'sent' -> True, then the leg fills)?
Counts shares sold by the stop leg + by the runner's sell; > qty = a short."""
import random, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
ROOT = Path("/home/user/day-trading-bot")
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "tests"))
import test_runner as TRN  # noqa
from test_runner import journal, FakeTrader, _take_and_fill  # noqa: F401  (fixture)
from journal import ledger as L  # noqa


class RaceTrader(FakeTrader):
    """cancel latency L and stop-fill instant F (s after the cancel is sent); the leg fills iff F < L.
    already_filled: the leg filled before the cancel (broker says Filled, cancel_order_id -> False)."""
    def __init__(self, L_s, F_s, already_filled=False):
        super().__init__(); self.L, self.F, self.already = L_s, F_s, already_filled
        self.sold_by_runner = 0; self.sold_by_stop = 0; self.qty = None
    def cancel_order_id(self, oid):
        if self.already:
            self.sold_by_stop = self.qty; return False
        if self.F < self.L:
            self.sold_by_stop = self.qty          # the in-flight stop executes before the cancel lands
        return True
    def exit_market(self, symbol, qty, now=None):
        self.sold_by_runner += qty; self.last_exit_order_id = 4242; return 4242


def _fire(journal, t):
    r, rec = _take_and_fill(journal, t)
    o = journal.execute("SELECT * FROM orders WHERE parent_id=?", (rec.parent_id,)).fetchone()
    t.qty = int(o["filled_qty"] or o["shares"])
    stop = float(o["stop"])
    clock = {"t": datetime(2026, 9, 1, 14, 30, tzinfo=timezone.utc)}
    r.now = lambda: clock["t"]; r.quote = lambda s: {"bid": stop - 0.05, "ask": stop - 0.03}
    r.enforce_stops(); clock["t"] += timedelta(seconds=16); r.enforce_stops()
    return t.sold_by_stop + t.sold_by_runner - t.qty     # > 0 = short


def test_head_sells_on_top_of_a_stop_already_filled(journal):
    t = RaceTrader(1.0, 2.0, already_filled=True)
    over = _fire(journal, t)
    print("already-filled leg: oversold", over)
    assert over == t.qty          # HEAD: short of the full quantity


def test_head_race_randomised(journal):
    rnd = random.Random(7); n_short = 0; N = 200
    for i in range(N):
        conn = L.connect(":memory:")
        TRN.build_session(TRN.FIXTURE, journal=conn)
        conn.execute("UPDATE decisions SET verdict='REVIEW' WHERE plan_allowed=1"); conn.commit()
        L.set_state(conn, phase="B")
        t = RaceTrader(rnd.uniform(0, 3), rnd.uniform(0, 3))
        n_short += _fire(conn, t) > 0
        conn.close()
    print(f"HEAD randomised: short in {n_short}/{N} runs (expected ~50% when F,L ~ U(0,3))")
    assert n_short > 0
