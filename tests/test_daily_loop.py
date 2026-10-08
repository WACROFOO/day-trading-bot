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


def test_the_desk_calls_are_exported_and_scored_beside_the_bot(tmp_path, monkeypatch):
    """The owner's buttons (2026-10-08) reach the review: a `took` closed by hand
    is scored on its own close, a `took` with no close on the bot's exit rule,
    a `passed` on what the card's plan would have done."""
    import json
    from datetime import datetime, timezone
    c = L.connect(":memory:")
    build_session(FIXTURE, journal=c)
    at = lambda h, m: datetime(2026, 9, 1, h + 4, m, tzinfo=timezone.utc)      # EDT
    L.record_manual(c, "ABCD", "took", price=6.30, shares=100, stop=6.10, verdict="REVIEW",
                    reason="first pullback", at=at(9, 33))
    L.record_manual(c, "ABCD", "closed", price=6.70, at=at(9, 40))
    L.record_manual(c, "DVLT", "took", price=3.60, shares=100, stop=3.40, verdict="REVIEW", at=at(9, 35))
    card = {"setup": {"trigger": 2.60, "stop": 2.45}}
    L.record_manual(c, "BRXO", "passed", verdict="WAIT", reason="below the VWAP", card=card, at=at(9, 30))
    monkeypatch.setattr(DR, "DAILY", tmp_path)
    log = tmp_path / "day.out.log"; log.write_text("===== START 2026-09-01 =====\n")
    meta = DX.export(c, "2026-09-01", tmp_path / "2026-09-01", log)
    assert meta["counts"]["desk_calls"] == 4
    out = DR.review("2026-09-01")
    assert "## Your calls on the desk — 4 recorded" in out
    abcd = next(ln for ln in out.splitlines() if "| ABCD | took |" in ln)
    assert "+2.00 (your close 6.70)" in abcd                   # (6.70 − 6.30) / 0.20
    dvlt = next(ln for ln in out.splitlines() if "| DVLT | took |" in ln)
    assert "on the bot's exit" in dvlt and "no close recorded" in dvlt
    brxo = next(ln for ln in out.splitlines() if "| BRXO | passed |" in ln)
    assert "if taken" in brxo and "WAIT: below the VWAP" in brxo
