"""The daily learning loop: export one day from the ledger, review it (2026-10-06)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

import daily_review as DR  # noqa: E402
import day_export as DX  # noqa: E402
from journal import ledger as L  # noqa: E402
from momentum_platform.dashboard.session_builder import build_session  # noqa: E402

FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"


def test_export_then_review(tmp_path, monkeypatch):
    c = L.connect(":memory:")
    build_session(FIXTURE, journal=c)
    from execution.runner import Runner
    from datetime import datetime, timezone
    Runner(c, mode="LOG_ONLY", dollar_risk=40.0, now=lambda: datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc)).step()
    log = tmp_path / "day.out.log"
    log.write_text("old day\n===== START 2026-09-01 =====\napi_key=abc123 connected\n  09:41 ABCD REFUSED\n")
    monkeypatch.setattr(DR, "DAILY", tmp_path)
    meta = DX.export(c, "2026-09-01", tmp_path / "2026-09-01", log)
    assert meta["counts"]["decisions"] > 0 and meta["counts"]["bars"] > 0
    text = (tmp_path / "2026-09-01" / "day.log").read_text()
    assert "abc123" not in text and "[REDACTED]" in text and "old day" not in text
    out = DR.review("2026-09-01")
    assert "## Funnel" in out and "Every plan, scored" in out and "Nothing on this page changes a rule" in out
    assert (tmp_path / "cohorts.csv").exists()


def test_the_trail_simulation():
    from datetime import datetime, timedelta
    t0 = datetime(2026, 9, 1, 9, 40, tzinfo=DR.ET)
    bars = [(t0 + timedelta(minutes=i), o, h, l, c) for i, (o, h, l, c) in
            enumerate([(5.0, 5.12, 4.99, 5.10), (5.10, 5.40, 5.08, 5.35), (5.35, 5.36, 5.10, 5.12)])]
    r, how = DR.simulate(bars, t0, 5.10, 4.90)
    assert how == "stop" and round(r, 2) == 0.50, (r, how)      # high 5.40, trail 1 R = 5.20
    assert DR.simulate(bars, t0, 6.00, 5.80) == (None, "trigger not reached")


def test_cohorts_are_named_by_the_rule_that_refused():
    assert DR.cohort_of({"outcome": "REFUSED", "refusal_reasons_json": '["Layer 2 not green: MACD warm-up — x"]'}) == "warmup_macd"
    assert DR.cohort_of({"outcome": "REFUSED", "refusal_reasons_json": '["A10: the price ran past the limit 5.30"]'}) == "ran_past"
    assert DR.cohort_of({"outcome": "SUPPRESSED", "killed_by": "price"}) == "killed:price"
