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


def test_the_screeners_go_out_with_the_day_and_a_month_goes_in_one_run(tmp_path, monkeypatch):
    """Owner, 2026-10-09: "focus on the last month tickers; all ones that popped
    out in our screeners". The export carries the denominator — every name the
    scan returned (screener.csv) and every name on the board (board.csv) — and
    --since exports each day with ledger data, the log cut at the next day."""
    c = L.connect(":memory:")
    now = "2026-09-0{}T{}"
    for day, sym, verdict in (("2026-09-08", "AAA", "SURVIVOR"), ("2026-09-08", "BBB", "REJECT"),
                              ("2026-09-10", "CCC", "SURVIVOR")):
        c.execute("INSERT INTO candidates (ts_et, source, symbol, verdict, reasons_json, price, gap_pct, float_shares,"
                  " pm_volume, recorded_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                  (f"{day}T07:05:00", "gap_scan", sym, verdict, "[]", 3.1, 42.0, 4.2e6, 9e5, f"{day}T11:05:00Z"))
    for ts, sym in (("2026-09-08T07:06:00", "AAA"), ("2026-09-08T07:30:00", "AAA"), ("2026-09-10T09:31:00", "CCC")):
        c.execute("INSERT INTO board_snapshots (ts_et, session_id, symbol, verdict, killed_by, plan_allowed, last,"
                  " recorded_at) VALUES (?,?,?,?,?,?,?,?)", (ts, "s1", sym, "WAIT", None, 1, 3.2, ts + "Z"))
    c.commit()
    assert DX.days_with_data(c, "2026-09-01", "2026-09-30") == ["2026-09-08", "2026-09-10"]
    log = tmp_path / "day.out.log"
    log.write_text("2026-09-08 07:00 START\napi_key=abc AAA armed\n2026-09-09 07:00 START\nnext day\n"
                   "2026-09-10 07:00 START\nCCC\n")
    monkeypatch.setattr(DX, "OUT_ROOT", tmp_path / "daily")
    (tmp_path / "daily").mkdir()
    (tmp_path / "daily" / "README.md").write_text("# Daily\n\n| day | notes |\n|---|---|\n")
    meta = DX.export(c, "2026-09-08", tmp_path / "daily" / "2026-09-08", log)
    assert meta["counts"]["screener"] == 2 and meta["counts"]["board"] == 1
    import csv as _csv
    rows = list(_csv.DictReader((tmp_path / "daily" / "2026-09-08" / "screener.csv").open()))
    assert {r["symbol"] for r in rows} == {"AAA", "BBB"} and rows[0]["source"] == "gap_scan"
    board = list(_csv.DictReader((tmp_path / "daily" / "2026-09-08" / "board.csv").open()))
    assert board[0]["symbol"] == "AAA" and board[0]["snapshots"] == "2" and board[0]["first_ts"].endswith("07:06:00")
    text = (tmp_path / "daily" / "2026-09-08" / "day.log").read_text()
    assert "AAA armed" in text and "next day" not in text and "abc" not in text, text
    assert "`2026-09-08/`" in (tmp_path / "daily" / "README.md").read_text()


def test_board_bars_carry_the_spread_when_asked(tmp_path):
    """--board-bars ships the desk's own bars with bid and ask for every
    screener and board name, gzipped; off by default."""
    import csv as _csv, gzip
    c = L.connect(":memory:")
    c.execute("INSERT INTO candidates (ts_et, source, symbol, verdict, reasons_json, price, gap_pct, float_shares,"
              " pm_volume, recorded_at) VALUES ('2026-09-08T07:05:00','gap_scan','AAA','SURVIVOR','[]',3,40,4e6,9e5,'x')")
    c.execute("INSERT INTO bars (symbol, ts, open, high, low, close, volume, bid, ask) VALUES "
              "('AAA','2026-09-08T11:06:00+00:00',3,3.1,2.9,3.05,12000,3.04,3.06)")
    c.commit()
    log = tmp_path / "l.log"; log.write_text("")
    m0 = DX.export(c, "2026-09-08", tmp_path / "a", log)
    assert "board_bars" not in m0["counts"] and not (tmp_path / "a" / "board_bars.csv.gz").exists()
    m1 = DX.export(c, "2026-09-08", tmp_path / "b", log, board_bars=True)
    assert m1["counts"]["board_bars"] == 1
    rows = list(_csv.DictReader(gzip.open(tmp_path / "b" / "board_bars.csv.gz", "rt")))
    assert rows[0]["symbol"] == "AAA" and rows[0]["bid"] == "3.04" and rows[0]["ask"] == "3.06"
