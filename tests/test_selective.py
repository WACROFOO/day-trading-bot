"""A13 selective mode: stop >= 2 % of price, price >= $5, first two plans of
the symbol's day. Each refusal is named; a plan that meets all three is left
to the other gates."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from execution import runner as RN  # noqa: E402
from types import SimpleNamespace  # noqa: E402

pytestmark = pytest.mark.selective


def _runner(c):
    r = RN.Runner.__new__(RN.Runner)
    r.conn = c
    return r


def _plan(c, sym, ts, trigger, stop):
    c.execute("INSERT INTO decisions (symbol, ts_et) VALUES (?, ?)", (sym, ts))
    return {"symbol": sym, "ts_et": ts, "trigger": trigger, "stop": stop,
            "decision_id": f"{sym}{ts}", "session": "regular"}


def _intent(row):
    return SimpleNamespace(trigger=row["trigger"], risk_per_share=round(row["trigger"] - row["stop"], 4))


def test_switch_is_on():
    assert RN.SELECTIVE is True


def test_each_refusal_is_named_and_a_clean_plan_passes(monkeypatch):
    monkeypatch.setattr(RN, "SELECTIVE_MAX_PLAN_INDEX", 2)
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE decisions (symbol TEXT, ts_et TEXT)")
    r = _runner(c)
    row = _plan(c, "AAA", "2026-09-29T09:40:00", 10.00, 9.70)          # 3 % stop, $10, plan 1
    assert r._selective(row, _intent(row)) == []
    row = _plan(c, "AAA", "2026-09-29T09:45:00", 10.00, 9.90)          # 1 % stop, plan 2
    out = r._selective(row, _intent(row))
    assert len(out) == 1 and "stop 1.0%" in out[0]
    row = _plan(c, "AAA", "2026-09-29T09:50:00", 10.00, 9.70)          # plan 3
    out = r._selective(row, _intent(row))
    assert len(out) == 1 and "plan 3" in out[0]
    row = _plan(c, "BBB", "2026-09-29T09:50:00", 3.00, 2.80)           # under $5
    out = r._selective(row, _intent(row))
    assert len(out) == 1 and "under $5" in out[0]


def test_plan_index_lever_is_off_by_default():
    assert RN.SELECTIVE_MAX_PLAN_INDEX is None
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE decisions (symbol TEXT, ts_et TEXT)")
    r = _runner(c)
    for m in range(5):
        row = _plan(c, "AAA", f"2026-09-29T09:4{m}:00", 10.00, 9.70)
    assert r._selective(row, _intent(row)) == []
