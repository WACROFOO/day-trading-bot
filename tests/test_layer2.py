"""Layer 2 gate by gate (2026-09-24): a refusal names the red chart gate, and
`missed` / `review` score the ledger per gate and per red combination — the
measurement an amendment is written from, never a tuning."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from execution.runner import Runner  # noqa: E402
from journal import controls, layer2 as Z, ledger as L  # noqa: E402
from momentum_platform.dashboard.session_builder import build_session  # noqa: E402

FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"
NOW = lambda: datetime(2026, 9, 1, 14, 5, tzinfo=timezone.utc)   # noqa: E731
FRESH = lambda s: dict(bid=6.02, ask=6.04, bid_size=100, ask_size=100, ts="2026-09-01T14:04:58Z")   # noqa: E731


def _gates(**states):
    base = {"price": "PASS", "float": "PASS", "catalyst": "PASS", "vwap": "PASS", "ema9": "PASS", "macd": "PASS"}
    base.update(states)
    return json.dumps([{"id": k, "state": v, "value": "", "reason": "", "kills": False} for k, v in base.items()])


def test_sub_gates_read_the_row_and_unknown_is_red_not_green():
    s = Z.sub_gates(_gates(vwap="FAIL", macd="UNKNOWN"), 0)
    assert s == {"vwap": "FAIL", "ema9": "PASS", "macd": "UNKNOWN", "volume": "FAIL"}
    assert Z.red(s) == ["vwap", "macd", "volume"]
    assert Z.key(s) == "vwap+macd?+volume"
    assert Z.describe(s) == ("below VWAP; MACD unknown (not computable at the plan); "
                             "pullback volume not lighter than the impulse")
    assert Z.describe(s, only=("vwap", "ema9", "macd")) == "below VWAP; MACD unknown (not computable at the plan)"
    # a row written before the chart gates existed: absent = UNKNOWN, never PASS
    old = Z.sub_gates(json.dumps([{"id": "price", "state": "PASS"}]), None)
    assert Z.red(old) == ["vwap", "ema9", "macd", "volume"] and Z.key(old) == "vwap?+ema9?+macd?+volume?"
    assert Z.key(Z.sub_gates(_gates(), 1)) == "all green" and Z.red(Z.sub_gates(_gates(), 1)) == []
    assert Z.sub_gates("not json", 1)["vwap"] == "UNKNOWN"


def test_a_trade_mode_refusal_names_the_red_chart_gates():
    """Before: 'Layer 2 not green: verdict WAIT — chart gates must all be true
    at entry', thirteen times on 2026-09-24, and no way to tell which gate."""
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c)
    c.execute("UPDATE decisions SET verdict='WAIT', gates_json=? WHERE plan_allowed=1",
              (_gates(vwap="FAIL", macd="UNKNOWN"),)); c.commit()

    class T:
        account = "DU1"; placed = []
        def place_bracket(self, *a, **k): raise AssertionError("must not be reached")
        def adopt(self, rows): return 0
        def sync(self): pass
    done = Runner(c, mode="TRADE", dollar_risk=20.0, trader=T(), now=NOW, max_age_s=3600, quote=FRESH).step()
    assert done
    for a in done:
        assert a.outcome == "REFUSED"
        l2 = [x for x in a.reasons if x.startswith("Layer 2 not green")]
        assert l2 and "below VWAP" in l2[-1] and "MACD unknown" in l2[-1] and "(verdict WAIT)" in l2[-1], a.reasons
        assert "9 EMA" not in l2[-1]                       # a green gate is not named
    # stored on the row, so `missed` reads the same words
    stored = json.loads(L.decisions(c, plan_allowed=1)[0]["refusal_reasons_json"])
    assert any("below VWAP" in x for x in stored)


def test_per_decision_rows_carry_the_four_states_and_reason_key_buckets_the_chart():
    c = L.connect(":memory:"); build_session(FIXTURE, journal=c)
    rows = controls.per_decision(c, {}, "2026-09-01")
    assert rows and all(set(d["l2"]) == set(Z.GATES) for d in rows)
    assert all(d["l2_key"] == Z.key(d["l2"]) and d["l2_red"] == Z.red(d["l2"]) for d in rows)
    d = dict(rows[0]); d["outcome"] = "REFUSED"
    d["refusal_reasons_json"] = json.dumps(["Layer 2 not green: below VWAP (verdict WAIT) — chart gates must all be true at entry"])
    assert controls.reason_key(d) == "refused: Layer 2 not green (chart)"
    d["refusal_reasons_json"] = json.dumps(["Layer 2 not green: pullback volume was not lighter than the impulse"])
    assert controls.reason_key(d) == "refused: Layer 2 not green (volume)"


def test_missed_and_review_print_the_gate_by_gate_block(tmp_path):
    db = tmp_path / "j.sqlite"
    subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "replay", str(FIXTURE), "--risk", "20"],
                   cwd=ROOT, capture_output=True, text=True, check=True)
    ms = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "missed", "--all"],
                        cwd=ROOT, capture_output=True, text=True)
    assert ms.returncode == 0, ms.stderr[-1200:]
    assert "LAYER 2 · GATE BY GATE" in ms.stdout and "by red combination" in ms.stdout
    assert "if ONE gate were dropped" in ms.stdout and "all green" in ms.stdout
    assert "red = FAIL or UNKNOWN" in ms.stdout
    rv = subprocess.run([sys.executable, "scripts/exercise.py", "--db", str(db), "review"],
                        cwd=ROOT, capture_output=True, text=True)
    assert rv.returncode == 0, rv.stderr[-1200:]
    assert "LAYER 2 · GATE BY GATE · cumulative" in rv.stdout
