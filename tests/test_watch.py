"""scripts/watch.py: the live feed of the ledger — killed plans the executor
log never shows, refusals, fills, exits and order events — read-only, and only
what changed on each poll."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))

from journal import ledger as L  # noqa: E402
from momentum_platform.dashboard.session_builder import build_session  # noqa: E402
import watch as W  # noqa: E402

FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"


def _ledger(tmp_path):
    db = tmp_path / "j.sqlite"
    c = L.connect(db)
    build_session(FIXTURE, journal=c)
    allowed = [r["decision_id"] for r in L.decisions(c, plan_allowed=1)]
    c.execute("UPDATE decisions SET outcome='REFUSED', refusal_reasons_json=? WHERE decision_id=?",
              (json.dumps(["Layer 2 not green: below VWAP (verdict WAIT) — chart gates must all be true at entry"]),
               allowed[0]))
    oid = L.record_order(c, allowed[1], symbol="ABCD", account="DU1", session="regular", parent_id=777,
                         stop_id=778, target_id=None, trigger=5.0, stop=4.8, target=None, shares=100,
                         dollar_risk=20.0, protected=True)
    c.execute("UPDATE decisions SET outcome='TAKEN' WHERE decision_id=?", (allowed[1],))
    L.record_fill(c, oid, fill_price=5.01, fill_ts="2026-09-01T13:41:05Z")
    L.add_order_event(c, oid, "STOP ENFORCED ABCD x100: bid 4.75 below the resting stop 4.80 for 16s")
    L.record_exit(c, oid, reason="stop_enforced", price=4.76, ts="2026-09-01T13:45:00Z")
    c.commit()
    return db, c, allowed


def test_the_feed_shows_kills_refusals_fills_exits_and_events(tmp_path):
    db, c, allowed = _ledger(tmp_path)
    w = W.Watcher(W.connect_ro(db), "2026-09-01")
    text = "\n".join(line for _, line in w.poll())
    assert "KILLED" in text and "pillars" in text          # the fixture's A5 kills: absent from the executor log
    assert "REFUSED" in text and "below VWAP" in text
    assert "FILLED" in text and "100 @ 5.01" in text
    assert "EXIT" in text and "@ 4.76" in text and "-1.25 R" in text
    assert "STOP ENFORCED" in text
    assert w.poll() == []                                   # nothing new: nothing printed
    c.execute("UPDATE decisions SET outcome='REFUSED', refusal_reasons_json=? WHERE decision_id=?",
              (json.dumps(["one position at a time (preregistration §2): 1 order(s) alive"]), allowed[2]))
    c.commit()
    again = [line for _, line in w.poll()]
    assert len(again) == 1 and "one position at a time" in again[0]
    assert "refused by the executor" in w.summary()


def test_it_never_writes(tmp_path):
    db, c, _ = _ledger(tmp_path)
    ro = W.connect_ro(db)
    try:
        ro.execute("UPDATE decisions SET outcome='X'")
        wrote = True
    except sqlite3.OperationalError:
        wrote = False
    assert not wrote


def test_the_cli_prints_a_past_day_once(tmp_path):
    db, _, _ = _ledger(tmp_path)
    out = subprocess.run([sys.executable, "scripts/watch.py", "--db", str(db), "--day", "2026-09-01"],
                         cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("WATCH · 2026-09-01") and "KILLED" in out.stdout and "so far:" in out.stdout
