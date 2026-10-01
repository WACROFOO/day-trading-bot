"""2026-09-30: the desk re-UPSERTed every bar of the day on every 3-second
rebuild. The tape write is now incremental: a second identical build writes
no bar, a grown minute is written again, and a fresh connection starts empty."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from journal import ledger as L  # noqa: E402
from momentum_platform.dashboard import session_builder as SB  # noqa: E402

FIXTURE = ROOT / "fixtures/market_replay/workstation_open_2026-09-01.jsonl"


def _records():
    return [json.loads(l) for l in FIXTURE.read_text().splitlines() if l.strip() and not l.startswith("#")]


def test_second_identical_build_writes_no_bars_and_a_grown_bar_is_rewritten(monkeypatch):
    c = L.connect(":memory:")
    written = []
    real = L.record_bars
    monkeypatch.setattr(L, "record_bars", lambda conn, by, count=True: (
        written.append(sum(len(v) for v in by.values())), real(conn, by, count=count))[1])
    recs = _records()
    t = {}
    SB.build_session_from_records(recs, "t", "fixture", data_status="live", journal=c, timings=t)
    assert written and written[0] > 0 and {"build", "journal"} <= set(t)
    n_rows = c.execute("SELECT COUNT(*) FROM bars").fetchone()[0]
    written.clear()
    SB.build_session_from_records(recs, "t", "fixture", data_status="live", journal=c)
    assert written == []                                    # nothing changed: nothing written
    last = max((r for r in recs if r.get("type") == "bar"), key=lambda r: r["ts"])
    grown = [dict(r, volume=r["volume"] + 1000) if r is last else r for r in recs]
    SB.build_session_from_records(grown, "t", "fixture", data_status="live", journal=c)
    assert written and written[0] >= 1                      # the growing minute is written again
    assert c.execute("SELECT COUNT(*) FROM bars").fetchone()[0] == n_rows
    c2 = L.connect(":memory:")                              # a new ledger is written in full
    SB.build_session_from_records(recs, "t", "fixture", data_status="live", journal=c2)
    assert c2.execute("SELECT COUNT(*) FROM bars").fetchone()[0] == n_rows
