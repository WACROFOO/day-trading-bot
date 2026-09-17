"""Ten-second candles reach the ledger, and never contaminate the 1-minute tape.

docs/PLAN-10s-micro-pullback.md M1/M3. The drain in
`UpdatePublisher.publish_closed_10s` is destructive — a candle is emitted
exactly once — so a candle not captured at that moment is gone. And the
grader reads every row of `bars` (`journal.bars.from_ledger`), so a 10-second
row landing there would silently re-grade the whole phase-A cohort against a
six-times-denser tape.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from journal import bars as B, ledger as L  # noqa: E402
from momentum_platform.dashboard.stream import EventHub, UpdatePublisher  # noqa: E402
from momentum_platform.datasources.ibkr_stream import Bar5s, BarStore  # noqa: E402

UTC = timezone.utc
T0 = datetime(2026, 9, 21, 14, 0, 0, tzinfo=UTC)          # 10:00 ET


def five(sym, i, vol=10, base=5.0):
    ts = T0 + timedelta(seconds=5 * i)
    return Bar5s(sym, ts, base + i * 0.01, base + 0.02 + i * 0.01,
                 base - 0.01 + i * 0.01, base + 0.01 + i * 0.01, vol)


def test_record_is_idempotent_and_reads_back_in_order(tmp_path):
    c = L.connect(tmp_path / "j.sqlite")
    rows = [("AAA", "2026-09-21T14:00:00Z", 5.0, 5.1, 4.9, 5.05, 100),
            ("AAA", "2026-09-21T14:00:10Z", 5.05, 5.2, 5.0, 5.15, 120)]
    assert L.record_bars_10s(c, rows) == 2
    assert L.record_bars_10s(c, rows) == 0, "a closed candle is written once"
    out = L.bars_10s_from_ledger(c)
    assert [r[0] for r in out["AAA"]] == ["2026-09-21T14:00:00Z", "2026-09-21T14:00:10Z"]
    assert out["AAA"][1][5] == 120


def test_a_datetime_timestamp_is_accepted(tmp_path):
    c = L.connect(tmp_path / "j.sqlite")
    L.record_bars_10s(c, [("AAA", T0, 5.0, 5.1, 4.9, 5.05, 100)])
    assert list(L.bars_10s_from_ledger(c)["AAA"])[0][0] == "2026-09-21T14:00:00Z"


def test_ten_second_rows_never_land_in_the_one_minute_tape(tmp_path):
    """The safety property. `bars.from_ledger` feeds the grader and the replay
    check; it must see exactly the minute bars it saw before."""
    c = L.connect(tmp_path / "j.sqlite")
    L.record_bars(c, {"AAA": [("2026-09-21T14:00:00Z", 5.0, 5.3, 4.9, 5.2, 600)]})
    L.record_bars_10s(c, [("AAA", f"2026-09-21T14:00:{s:02d}Z", 5.0, 5.1, 4.9, 5.05, 100)
                          for s in range(0, 60, 10)])
    tape = B.from_ledger(c)
    assert len(tape["AAA"]) == 1, "the grader's tape is untouched"
    assert tape["AAA"][0][5] == 600
    assert len(L.bars_10s_from_ledger(c)["AAA"]) == 6


def test_the_sink_captures_every_drained_candle_and_the_drain_is_destructive():
    store = BarStore()
    for i in range(12):                      # 12 five-second bars = 6 ten-second candles
        store.append(five("AAA", i))
    kept = []
    pub = UpdatePublisher(EventHub())
    n = pub.publish_closed_10s(store, ["AAA"], sink=kept.append)
    assert n == 6 and len(kept) == 6
    assert [b.timeframe for b in kept] == ["10s"] * 6
    assert pub.publish_closed_10s(store, ["AAA"], sink=kept.append) == 0
    assert len(kept) == 6, "nothing is emitted twice"


def test_the_ten_second_candles_aggregate_to_their_minute(tmp_path):
    """M3: the two resolutions must describe the same instant. If the sum of a
    minute's ten-second candles disagrees with the minute bar, one of them is
    lying and nothing downstream can tell which."""
    store = BarStore()
    for i in range(12):
        store.append(five("AAA", i))
    kept = []
    UpdatePublisher(EventHub()).publish_closed_10s(store, ["AAA"], sink=kept.append)
    c = L.connect(tmp_path / "j.sqlite")
    L.record_bars_10s(c, kept)
    fine = L.bars_10s_from_ledger(c)["AAA"]
    assert len(fine) == 6
    assert fine[0][1] == kept[0].open                       # open of the first
    assert fine[-1][4] == kept[-1].close                    # close of the last
    assert max(r[2] for r in fine) == max(b.high for b in kept)
    assert min(r[3] for r in fine) == min(b.low for b in kept)
    assert sum(r[5] for r in fine) == sum(b.volume for b in kept) == 120


# -- the desk's own buffering -------------------------------------------------

def _desk(monkeypatch, tmp_path, journal=True):
    sys.path.insert(0, str(ROOT / "tests"))
    from test_ibkr_desk import make_desk
    from momentum_platform.dashboard import ibkr_desk as D
    desk, ib, clock = make_desk()
    conn = L.connect(tmp_path / "j.sqlite") if journal else None
    monkeypatch.setattr(D, "_journal", lambda: conn)
    return desk, conn


def test_the_desk_batches_writes_and_flushes_the_tail_on_stop(monkeypatch, tmp_path):
    desk, conn = _desk(monkeypatch, tmp_path)
    store = BarStore()
    for i in range(10):
        store.append(five("AAA", i))
    kept = []
    UpdatePublisher(EventHub()).publish_closed_10s(store, ["AAA"], sink=kept.append)
    for b in kept:
        desk._keep_10s(b)
    assert conn.execute("SELECT COUNT(*) FROM bars_10s").fetchone()[0] == 0, "batched, not per candle"
    desk.stop()
    assert conn.execute("SELECT COUNT(*) FROM bars_10s").fetchone()[0] == len(kept)


def test_a_write_failure_is_logged_once_and_never_raises(monkeypatch, tmp_path):
    desk, conn = _desk(monkeypatch, tmp_path)
    from journal import ledger as _L
    monkeypatch.setattr(_L, "record_bars_10s",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk full")))
    said = []
    desk.log = said.append
    store = BarStore()
    for i in range(4):
        store.append(five("AAA", i))
    kept = []
    UpdatePublisher(EventHub()).publish_closed_10s(store, ["AAA"], sink=kept.append)
    for b in kept:
        desk._keep_10s(b)
    desk._flush_10s()                       # must not raise
    desk._buf10s = list(kept); desk._flush_10s()
    assert sum("10s bars not persisted" in m for m in said) == 1, "logged once, not every tick"


def test_no_journal_means_no_write_and_no_error(monkeypatch, tmp_path):
    desk, _ = _desk(monkeypatch, tmp_path, journal=False)
    store = BarStore()
    for i in range(4):
        store.append(five("AAA", i))
    kept = []
    UpdatePublisher(EventHub()).publish_closed_10s(store, ["AAA"], sink=kept.append)
    for b in kept:
        desk._keep_10s(b)
    desk._flush_10s()
