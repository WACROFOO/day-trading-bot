"""The bot watcher (owner, 2026-10-09: "how to watch closely the bot execution
decisions"): read-only, prints each decision, order, fill, event, exit and the
risk lock once, as it happens."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

import watch_bot as W  # noqa: E402
from journal import ledger as L  # noqa: E402

DAY = "2026-10-09"
STRIP = __import__("re").compile(r"\033\[[0-9;]*m")


def _decision(c, did, sym, outcome, trigger=5.0, stop=4.8, reasons=None, status="LIVE", ts="09:41:00"):
    c.execute("INSERT INTO decisions (decision_id, ts_et, session, symbol, source, session_id, source_name, data_status,"
              " bar_resolution, last, session_high, verdict, plan_allowed, gates_json, warnings_json, inputs_json,"
              " trigger, stop, volume_ok, outcome, refusal_reasons_json, acted_at, recorded_at)"
              " VALUES (?, ?, 'regular', ?, 'pullback', 's', 'ibkr', ?, '1m', 5.0, 5.2, 'REVIEW', 1, '[]', '[]', '{}',"
              " ?, ?, 1, ?, ?, ?, 'x')",
              (did, f"{DAY}T{ts}-04:00", sym, status, trigger, stop, outcome,
               None if reasons is None else __import__("json").dumps(reasons), f"{DAY}T13:41:30+00:00"))


def test_the_watcher_prints_each_step_once(tmp_path):
    db = tmp_path / "j.sqlite"
    c = L.connect(str(db))
    _decision(c, "d1", "AAA", "REFUSED", reasons=["Layer 2 not green: below VWAP — the bot refuses", "MACD red"])
    _decision(c, "d2", "BBB", "PENDING")
    _decision(c, "d3", "CCC", "SUPPRESSED", trigger=None, stop=None)
    _decision(c, "d4", "DDD", "PENDING", status="LIVE-backfill")
    c.commit()
    lines = []
    w = W.Watcher(W.connect(str(db)), DAY, out=lines.append)
    w.poll()
    text = [STRIP.sub("", x) for x in lines]
    assert any("AAA" in x and "REFUSED" in x and "✗ Layer 2 not green: below VWAP (+1 more)" in x for x in text), text
    assert any("BBB" in x and "ARMED" in x and "5.00/4.80 (4.0%)" in x for x in text)
    assert not any("CCC" in x for x in text), "cascade kills only with --all"
    assert not any("DDD" in x for x in text), "loaded history is not a decision"
    assert w.killed == 1
    lines.clear()
    assert w.poll() == 0 and not lines, "nothing new, nothing printed"
    # the plan is taken, sent, filled, managed, exited; the gate locks
    c.execute("UPDATE decisions SET outcome='TAKEN' WHERE decision_id='d2'")
    c.execute("INSERT INTO orders (order_id, decision_id, symbol, session, trigger, stop, shares, dollar_risk,"
              " planned_risk, status, fill_price, fill_ts, placed_at, updated_at) VALUES"
              " (7, 'd2', 'BBB', 'regular', 5.0, 4.8, 200, 40, 40, 'Filled', 5.01, ?, ?, ?)",
              (f"{DAY}T13:42:10+00:00", f"{DAY}T13:42:00+00:00", f"{DAY}T13:42:10+00:00"))
    c.execute("INSERT INTO order_events (order_id, ts, text) VALUES (7, ?, 'trail raised to 5.10')",
              (f"{DAY}T13:44:00+00:00",))
    c.commit()
    w.poll()
    text = [STRIP.sub("", x) for x in lines]
    assert any("BBB" in x and "TAKEN" in x for x in text)
    assert any("SENT" in x and "BUY x200 trigger 5.00 stop 4.80" in x for x in text)
    assert any("FILLED" in x and "200 @ 5.01" in x and "+1¢ vs the trigger" in x for x in text)
    assert any("event" in x and "trail raised to 5.10" in x for x in text)
    assert "held: BBB x200 @ 5.01 stop 4.80" in STRIP.sub("", w.status())
    lines.clear()
    c.execute("UPDATE orders SET exit_price=5.41, exit_ts=?, exit_reason='trail', status='Closed' WHERE order_id=7",
              (f"{DAY}T13:50:00+00:00",))
    c.execute("INSERT INTO risk_day (date, locked, reason, locked_at) VALUES (?, 1, '3 losses', 'x')", (DAY,))
    c.commit()
    w.poll()
    text = [STRIP.sub("", x) for x in lines]
    assert any("EXIT" in x and "@ 5.41 trail" in x and "+2.00 R" in x and "$+80.00" in x for x in text), text
    assert any("LOCK" in x and "3 losses" in x for x in text)
    st = STRIP.sub("", w.status())
    assert "flat" in st and "today 1 closed, +2.00 R" in st and "risk gate LOCKED" in st


def test_the_watcher_opens_the_ledger_read_only(tmp_path):
    db = tmp_path / "j.sqlite"
    L.connect(str(db)).close()
    c = W.connect(str(db))
    import sqlite3, pytest
    with pytest.raises(sqlite3.OperationalError):
        c.execute("INSERT INTO risk_day (date, locked) VALUES ('x', 1)")
