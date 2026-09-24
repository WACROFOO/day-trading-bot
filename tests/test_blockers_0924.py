"""2026-09-24 evening, the blocker pass: a third exit variant scored beside
the two, the Layer 1 kills scored gate by gate with the penny-theme split,
EXIT lines in the live loop, and a desk that comes back after the Gateway."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

import day  # noqa: E402
import exercise  # noqa: E402
from journal import bars as B, controls, ledger as L  # noqa: E402
from momentum_platform.dashboard.session_builder import build_session  # noqa: E402

FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"


def _bars(seq):
    return [(f"2026-09-01T14:{i:02d}:00Z", o, h, l, c, 100) for i, (o, h, l, c) in enumerate(seq)]


def test_be_target_moves_to_breakeven_after_one_r_and_keeps_the_fixed_target():
    sim = controls.simulate_exit
    trig, stop = 10.0, 9.5                                   # 1 R = 0.50, target 11.00
    # +1 R prints, then the pullback to the trigger: breakeven, not −1 R, not a trail
    e = _bars([(10.0, 10.6, 9.9, 10.5), (10.5, 10.55, 9.99, 10.0), (10.0, 10.1, 9.0, 9.1)])
    assert sim(e, trig, stop, "be_target", target=11.0) == {"r": 0.0, "exit": "trail", "bars_held": 2}
    assert sim(e, trig, stop, "baseline", target=11.0)["r"] == -1.0
    # the target is untouched: +2 R when it prints
    e = _bars([(10.0, 10.6, 9.9, 10.5), (10.5, 11.2, 10.4, 11.0)])
    assert sim(e, trig, stop, "be_target", target=11.0)["r"] == 2.0
    # never +1 R: the original stop, −1 R
    e = _bars([(10.0, 10.3, 9.9, 10.1), (10.1, 10.2, 9.4, 9.5)])
    assert sim(e, trig, stop, "be_target", target=11.0)["r"] == -1.0
    assert "be_target" in controls.VARIANTS


def test_per_decision_and_the_kill_rule_carry_the_third_variant():
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c)
    rows = controls.per_decision(c, B.from_fixture(FIXTURE), "2026-09-01")
    hit = [d for d in rows if d["trigger_hit"] == 1]
    assert hit and all("be_r" in d for d in rows) and any(d["be_r"] is not None for d in hit)
    k = controls.kill_rule_read(c, B.from_fixture(FIXTURE))
    assert "be_sim_mean" in k


def test_penny_theme_is_read_from_the_ledgers_own_scan_rows():
    c = L.connect(":memory:")
    from datetime import datetime, timezone
    L.record_candidates(c, datetime(2026, 9, 22, 11, 0, tzinfo=timezone.utc), "gap_scan",
                        [{"sym": "PMAX", "price": 1.85, "gap": 111.0}, {"sym": "GRML", "price": 14.0, "gap": 30.0}])
    L.record_candidates(c, datetime(2026, 9, 23, 11, 0, tzinfo=timezone.utc), "gap_scan",
                        [{"sym": "WETO", "price": 1.9, "gap": 40.0}])
    hit = controls.penny_theme_live(c, "2026-09-24")
    assert hit and hit["symbol"] == "PMAX" and hit["day"] == "2026-09-22"
    assert controls.penny_theme_live(c, "2026-09-22") is None          # nothing before that day
    assert controls.penny_theme_live(c, "2026-09-24", sessions=1) is None   # only 09-23 in the window: no runner


def test_missed_and_review_print_the_killed_by_gate_block(tmp_path):
    db = tmp_path / "j.sqlite"
    subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "replay", str(FIXTURE), "--risk", "20"],
                   cwd=ROOT, capture_output=True, text=True, check=True)
    ms = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "missed", "--all"],
                        cwd=ROOT, capture_output=True, text=True)
    assert ms.returncode == 0, ms.stderr[-1500:]
    assert "KILLED PLANS BY GATE" in ms.stdout and "BE+2R" in ms.stdout and "nothing here bends it" in ms.stdout
    rv = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "review"],
                        cwd=ROOT, capture_output=True, text=True)
    assert rv.returncode == 0, rv.stderr[-1500:]
    assert "KILLED PLANS BY GATE · cumulative" in rv.stdout and "BE+2R" in rv.stdout   # the kill-rule header waits for a fill


def test_exit_lines_name_every_position_closed_by_the_fill_sync():
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c)
    did = L.decisions(c, plan_allowed=1)[0]["decision_id"]
    oid = L.record_order(c, did, symbol="PFSA", account="DU1", session="regular", parent_id=700, stop_id=701,
                         target_id=None, trigger=3.73, stop=3.49, target=None, shares=83, dollar_risk=20.0,
                         protected=True)
    L.record_fill(c, oid, fill_price=3.74, fill_ts="2026-09-24T13:38:40Z")
    held = {o["order_id"] for o in L.stuck_orders(c)}
    assert held == {oid} and exercise.exit_lines(c, held) == []                  # still held: nothing to say
    L.record_exit(c, oid, reason="trail", price=3.73, ts="2026-09-24T13:40:00Z")
    lines = exercise.exit_lines(c, held)
    assert lines == ["PFSA x83 @ 3.73 trail (-0.04 R)"]


def test_the_day_waits_for_the_gateway_and_gives_up_after_the_deadline():
    attempts = {"n": 0}
    class Sock:
        def __enter__(self): return self
        def __exit__(self, *a): return False
    def connect(addr, timeout=2):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise OSError("refused")
        return Sock()
    slept = []
    assert day.wait_for_gateway("127.0.0.1", "4002", 600, sleep=slept.append, connect=connect) is True
    assert attempts["n"] == 3 and slept == [15, 15]
    def never(addr, timeout=2): raise OSError("refused")
    clock = {"t": 0.0}
    import time as _t
    real = _t.monotonic
    try:
        day.time.monotonic = lambda: clock["t"]
        def tick(s): clock["t"] += s
        assert day.wait_for_gateway("127.0.0.1", "4002", 60, sleep=tick, connect=never) is False
        assert clock["t"] >= 60
    finally:
        day.time.monotonic = real
