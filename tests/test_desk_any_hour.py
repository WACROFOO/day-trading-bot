"""The platform at any hour (owner, 2026-10-08: "make the platform available
whenever I launch the command; don't limit it to the window").

The desk comes up whenever scripts/day.py runs — before 06:55, after the bot's
day, on closed days — and stays up until Ctrl-C. The BOT keeps its window, and
a desk outside it writes nothing to the exercise ledger, so the day's report,
the replay check and settle measure what they measured before.
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time as _time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in ("src", "tests", "scripts"):
    sys.path.insert(0, str(ROOT / p))

import day  # noqa: E402
from fake_ibkr import FakeIB, FakeTicker, day_bars  # noqa: E402
from journal import ledger as L  # noqa: E402
from momentum_platform.dashboard import ibkr_desk as desk_mod  # noqa: E402
from momentum_platform.dashboard.cards import RISK_KEY  # noqa: E402
from momentum_platform.dashboard.ibkr_desk import IbkrDesk, _record_until  # noqa: E402
from test_live_chain import T0, pullback_minutes  # noqa: E402

ET = ZoneInfo("America/New_York")
AFTERNOON = datetime(2026, 10, 8, 14, 0, tzinfo=ET)          # a call logged after the day's export
# Every table the desk writes for the exercise. Your calls (manual_decisions)
# and your risk (desk_settings) are not on this list: they are saved at any hour.
EXERCISE = ("decisions", "decision_revisions", "board_snapshots", "halts", "bars", "bars_10s",
            "quotes", "quote_ticks", "five_minute_states", "green_run_signals")


@pytest.fixture(autouse=True)
def _handlers(monkeypatch):
    """day.py installs SIGINT/SIGTERM handlers; give the suite its own back.
    And nothing here may open a browser tab or replace the test process."""
    old = signal.getsignal(signal.SIGINT), signal.getsignal(signal.SIGTERM)
    monkeypatch.setattr(day, "open_page", lambda *a, **k: None)
    monkeypatch.setattr(day.os, "execv", lambda *a: pytest.fail("os.execv in a test"))
    day.STOP["requested"] = False
    yield
    signal.signal(signal.SIGINT, old[0]); signal.signal(signal.SIGTERM, old[1])
    day.STOP["requested"] = False


# -- the desk: one cutoff for every exercise write ---------------------------------

def test_the_record_until_value_is_read_strictly():
    assert _record_until(None) == (None, None)                  # a desk by hand: no cutoff
    assert _record_until("") == (None, None)
    never, why = _record_until("0")
    assert never.year == 1970 and "writes nothing" in why
    at, why = _record_until("2026-10-08T11:31:30-04:00")
    assert why is None and at == datetime(2026, 10, 8, 15, 31, 30, tzinfo=timezone.utc)
    for bad in ("11:30", "2026-10-08T11:31:30", "soon"):          # no offset, or not a time
        until, why = _record_until(bad)
        assert until.year == 1970 and "NOTHING" in why, bad


def _live_desk(tmp_path, monkeypatch, record_until):
    tmp_path.mkdir(parents=True, exist_ok=True)
    db = tmp_path / "j.sqlite"
    monkeypatch.setenv("JOURNAL_DB", str(db))
    monkeypatch.setattr(desk_mod, "_JOURNAL", None)
    monkeypatch.setenv("FLOAT_OVERRIDES", str(tmp_path / "floats.json"))
    (tmp_path / "floats.json").write_text(json.dumps(
        {"date": "2026-09-08", "source": "finviz via premarket_stars.py", "floats": {"AAA": 6_000_000}}))
    if record_until is None:
        monkeypatch.delenv("DESK_RECORD_UNTIL", raising=False)
    else:
        monkeypatch.setenv("DESK_RECORD_UNTIL", record_until)
    conn = L.connect(db)
    L.set_setting(conn, RISK_KEY, "50"); conn.commit()          # your risk, stated on the page
    start = T0 - timedelta(minutes=5)
    ib = FakeIB(daily={"AAA": day_bars(30, 3.0, today="2026-09-08")},
                minutes={"AAA": pullback_minutes(start)},
                quotes={"AAA": FakeTicker(last=4.13, close=3.00, bid=4.12, ask=4.14)})
    said = []
    desk = IbkrDesk(["AAA"], ib_factory=lambda: ib, clock=lambda: T0, headlines=False, sec=False, rescan=0)
    desk.log = said.append
    desk._started = start - timedelta(minutes=1)
    desk._bootstrap()
    session = desk.refresh_session()
    return desk, conn, session, said


def _rows(conn):
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in EXERCISE}


def test_a_desk_outside_the_day_writes_nothing_and_still_reads_your_risk(tmp_path, monkeypatch):
    desk, conn, session, _ = _live_desk(tmp_path, monkeypatch, "0")
    try:
        assert session["frames"] and session["cascade"]["AAA"]["verdict"], "the desk still judges and shows"
        assert sum(_rows(conn).values()) == 0, _rows(conn)
        assert session["cards"]["AAA"]["risk"] == {"dollars": 50.0, "source": "yours"}
        h = desk.health()
        assert h["recording"] is False and h["recordUntil"].startswith("1970")
    finally:
        desk.stop()


def test_the_days_desk_writes_until_its_cutoff_and_not_after(tmp_path, monkeypatch):
    later = (T0 + timedelta(minutes=1)).isoformat()
    desk, conn, _, _ = _live_desk(tmp_path, monkeypatch, later)
    try:
        rows = _rows(conn)
        assert rows["decisions"] and rows["bars"] and rows["board_snapshots"] and rows["quotes"]
        assert desk.health()["recording"] is True
    finally:
        desk.stop()
    earlier = (T0 - timedelta(seconds=1)).isoformat()
    desk, conn, _, _ = _live_desk(tmp_path / "second", monkeypatch, earlier)
    try:
        assert sum(_rows(conn).values()) == 0
    finally:
        desk.stop()


def test_a_desk_started_by_hand_writes_as_it_always_did(tmp_path, monkeypatch):
    desk, conn, _, _ = _live_desk(tmp_path, monkeypatch, None)
    try:
        assert _rows(conn)["decisions"] and desk.health()["recordUntil"] is None
    finally:
        desk.stop()


def test_an_unreadable_cutoff_writes_nothing_and_says_so(tmp_path, monkeypatch, capsys):
    desk, conn, _, _ = _live_desk(tmp_path, monkeypatch, "11:30")
    try:
        assert sum(_rows(conn).values()) == 0
        out = capsys.readouterr().out                   # said at construction, before any log is swapped in
        assert "DESK_RECORD_UNTIL" in out and "NOTHING" in out, out
    finally:
        desk.stop()


def test_ten_second_candles_stop_at_the_cutoff_and_the_buffer_is_written(tmp_path, monkeypatch):
    from test_bars_10s import _desk, five
    from momentum_platform.dashboard.stream import EventHub, UpdatePublisher
    from momentum_platform.datasources.ibkr_stream import BarStore
    desk, conn = _desk(monkeypatch, tmp_path)
    store = BarStore()
    for i in range(14):                                 # seven closed ten-second candles
        store.append(five("AAA", i))
    kept = []
    UpdatePublisher(EventHub()).publish_closed_10s(store, ["AAA"], sink=kept.append)
    now = {"t": kept[0].ts}
    desk.clock = lambda: now["t"]
    desk.record_until = kept[3].ts                      # the cutoff falls inside the run
    for b in kept[:3]:
        desk._keep_10s(b)
    assert conn.execute("SELECT COUNT(*) FROM bars_10s").fetchone()[0] == 0, "batched before the cutoff"
    now["t"] = kept[3].ts                               # the cutoff passes
    for b in kept[3:]:
        desk._keep_10s(b)
    assert conn.execute("SELECT COUNT(*) FROM bars_10s").fetchone()[0] == 3, "the buffer, written; nothing after"
    assert desk._buf10s == []
    pending = getattr(desk, "_green_pending", None) or []
    assert all(b.ts < kept[3].ts for b in pending), "no candle after the cutoff reaches the green run"


# -- day.py: what each moment of the day starts ----------------------------------------

def test_the_days_desk_records_through_the_runners_flatten():
    assert day.record_until(date(2026, 10, 8)) == "2026-10-08T11:31:30-04:00"
    assert day.RUNNER_FLATTEN_S == 90 and day.RECORD_SETTLE_S == 60


def test_the_next_day_starts_at_0655_on_the_next_trading_day():
    at = lambda *a: datetime(*a, tzinfo=ET)  # noqa: E731
    assert day.next_day_start(at(2026, 10, 8, 5, 0)) == at(2026, 10, 8, 6, 55)     # before the day: today
    assert day.next_day_start(at(2026, 10, 8, 6, 55)) == at(2026, 10, 9, 6, 55)    # strictly after
    assert day.next_day_start(at(2026, 10, 9, 12, 0)) == at(2026, 10, 12, 6, 55)   # Friday -> Monday
    assert day.next_day_start(at(2026, 9, 5, 9, 0)) == at(2026, 9, 8, 6, 55)       # Labor Day weekend -> Tuesday


def test_a_calendar_that_never_opens_cannot_hang_the_desk(monkeypatch):
    monkeypatch.setattr(day, "why_closed", lambda d: "test holiday")
    now = datetime(2026, 10, 8, 12, 0, tzinfo=ET)
    assert day.next_day_start(now) == datetime(2026, 10, 9, 6, 55, tzinfo=ET)


def test_the_desk_command_carries_its_recording_window(monkeypatch):
    seen = []

    class Popen:
        def __init__(self, cmd, cwd=None, env=None):
            seen.append(env)
    monkeypatch.setattr(day.subprocess, "Popen", Popen)
    monkeypatch.setenv("DESK_RECORD_UNTIL", "inherited")
    day.start_desk(["AAA"], False, record_until="0")
    day.start_desk(["AAA"], False, record_until="2026-10-08T11:31:30-04:00")
    day.start_desk(["AAA"], False)
    assert [e.get("DESK_RECORD_UNTIL") for e in seen] == ["0", "2026-10-08T11:31:30-04:00", None]


class Frozen:
    """A clock for day.py's `datetime`, moved by the test."""
    def __init__(self, start: datetime, step: timedelta = timedelta(0)):
        self.t, self.step = start, step

    def dt(self):
        clock = self

        class FrozenDT(datetime):
            @classmethod
            def now(cls, tz=None):
                t = clock.t
                clock.t = clock.t + clock.step
                return t if tz else t.replace(tzinfo=None)
        return FrozenDT


def _at(monkeypatch, tmp_path, when: datetime, step=timedelta(0)):
    clock = Frozen(when, step)
    monkeypatch.setattr(day, "datetime", clock.dt())
    monkeypatch.setattr(day, "DB", tmp_path / "j.sqlite")
    monkeypatch.setattr(day, "DAY_LOCK", tmp_path / "j.sqlite.day.lock")
    monkeypatch.setattr(day, "RESTART_MARK", tmp_path / "j.sqlite.desk.restart")
    monkeypatch.setattr(day, "PROBE_ONCE", tmp_path / "probe-orders.once")
    monkeypatch.setenv("DAY_EXPORT", "0")
    monkeypatch.setenv("IBKR_PORT", "4002")             # no port probing from a test
    return clock


def _capture_desk_only(monkeypatch):
    calls = []
    monkeypatch.setattr(day, "desk_only", lambda args, conn, why, **kw: calls.append((why, kw)) or 0)
    return calls


def test_after_the_hard_stop_the_day_is_settled_then_the_desk_comes_up(tmp_path, monkeypatch):
    _at(monkeypatch, tmp_path, datetime(2026, 10, 8, 14, 0, tzinfo=ET))
    settled = []
    monkeypatch.setattr(day, "after_close", lambda conn, d, dry: settled.append(d))
    calls = _capture_desk_only(monkeypatch)
    monkeypatch.setattr(day, "start_runner", lambda *a, **k: pytest.fail("no runner after the day"))
    assert day.main([]) == 0
    assert settled == ["2026-10-08"]
    assert calls == [("after the bot's day", {"day": "2026-10-08"})]


def test_before_0655_the_desk_comes_up_and_the_probe_file_waits_for_the_day(tmp_path, monkeypatch):
    _at(monkeypatch, tmp_path, datetime(2026, 10, 8, 5, 30, tzinfo=ET))
    (tmp_path / "probe-orders.once").write_text("")
    calls = _capture_desk_only(monkeypatch)
    monkeypatch.setattr(day, "start_runner", lambda *a, **k: pytest.fail("no runner before 06:55"))
    assert day.main([]) == 0
    assert calls == [("before the day", {})]
    assert (tmp_path / "probe-orders.once").exists(), "an evening or early launch does not use it up"


def test_a_second_launch_gives_the_link_and_names_a_stale_desk(tmp_path, monkeypatch, capsys):
    _at(monkeypatch, tmp_path, datetime(2026, 10, 8, 9, 0, tzinfo=ET))
    held, _ = day.day_lock(tmp_path / "j.sqlite.day.lock")       # "the 06:55 job"
    try:
        monkeypatch.setattr(day, "desk_health", lambda timeout=3.0: {"provider": {"state": "LIVE"}})
        monkeypatch.setattr(day, "start_desk", lambda *a, **k: pytest.fail("never a second desk"))
        assert day.main(["--no-open"]) == 0
        out = capsys.readouterr().out
        assert "nothing started" in out and "http://127.0.0.1:8787/" in out and "feed LIVE" in out
        assert "older code" in out and "--restart-desk" in out
        monkeypatch.setattr(day, "desk_health", lambda timeout=3.0: None)
        assert day.main(["--no-open"]) == 0
        assert "does not answer" in capsys.readouterr().out
    finally:
        held.close()


def test_a_desk_on_this_checkouts_code_is_not_called_stale():
    from momentum_platform.dashboard.server import app_build
    head = day._git("rev-parse", "--short", "HEAD").stdout.strip()
    assert day.desk_staleness({"codeAtStart": head, "appBuildAtStart": app_build()}) is None
    why = day.desk_staleness({"codeAtStart": head, "appBuildAtStart": "000000"})
    assert why and "page 000000" in why
    assert "before this check" in day.desk_staleness({"appBuildAtStart": app_build()})


def test_restart_desk_needs_a_running_day_and_asks_its_desk_to_restart(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(day, "DAY_LOCK", tmp_path / "j.sqlite.day.lock")
    monkeypatch.setattr(day, "RESTART_MARK", tmp_path / "j.sqlite.desk.restart")
    killed = []
    assert day.restart_desk(kill=lambda pid, sig: killed.append(pid), find=lambda: [4242]) == 1
    assert killed == [] and "no trading day is running" in capsys.readouterr().out
    held, _ = day.day_lock(tmp_path / "j.sqlite.day.lock")
    try:
        head = day._git("rev-parse", "--short", "HEAD").stdout.strip()
        up = {"mode": "live", "streaming": True, "codeAtStart": head}
        rc = day.restart_desk(kill=lambda pid, sig: killed.append((pid, sig)), find=lambda: [4242],
                              health=lambda: up, sleep=lambda s: None, imports=lambda: None)
        assert rc == 0 and killed == [(4242, signal.SIGINT)]
        assert (tmp_path / "j.sqlite.desk.restart").exists(), "the day reads it: a restart, not an outage"
        assert "back on" in capsys.readouterr().out
    finally:
        held.close()


def test_a_requested_restart_is_consumed_once_and_expires(tmp_path, monkeypatch):
    mark = tmp_path / "m"
    monkeypatch.setattr(day, "RESTART_MARK", mark)
    assert day.restart_asked() is False
    mark.write_text("x")
    assert day.restart_asked() is True and not mark.exists()
    mark.write_text("x")
    old = _time.time() - 600
    os.utime(mark, (old, old))
    assert day.restart_asked() is False and not mark.exists()


# -- the desk alone: until the next day, or Ctrl-C ------------------------------------

class Proc:
    def __init__(self, polls=None):
        self.polls = list(polls or [])
        self.returncode = None
        self.signals = []

    def poll(self):
        if self.polls:
            self.returncode = self.polls.pop(0)
        return self.returncode

    def send_signal(self, sig):
        self.signals.append(sig)
        self.returncode = 0

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.returncode = -9


def _args(**kw):
    return SimpleNamespace(dry_run=False, symbols=None, no_open=True, **kw)


def test_the_desk_alone_hands_over_to_the_next_day_and_ships_late_calls(tmp_path, monkeypatch):
    clock = _at(monkeypatch, tmp_path, datetime(2026, 10, 8, 14, 0, tzinfo=ET))
    conn = L.connect(tmp_path / "j.sqlite")
    started, exported, rolled = [], [], []
    monkeypatch.setattr(day, "start_desk", lambda syms, dry, record_until=None:
                        started.append(record_until) or Proc())
    monkeypatch.setattr(day, "desk_is_on_ibkr", lambda p, timeout_s=420: True)
    monkeypatch.setattr(day, "export_day", lambda c, d: exported.append(d))
    monkeypatch.setattr(day, "rollover", lambda args, before=None: before() or rolled.append(True) or 7)

    def nap(_s):                     # the afternoon: a call logged, then the night passes
        L.record_manual(conn, "AAA", "closed", price=4.2, at=AFTERNOON); conn.commit()
        clock.t = datetime(2026, 10, 9, 6, 55, tzinfo=ET)
    monkeypatch.setattr(day, "_nap", nap)
    assert day.desk_only(_args(), conn, "after the bot's day", day="2026-10-08") == 7
    assert started == ["0"], "a desk outside the day writes nothing"
    assert exported == ["2026-10-08"] and rolled == [True]


def test_the_days_own_desk_carries_on_and_a_dead_desk_comes_back(tmp_path, monkeypatch):
    _at(monkeypatch, tmp_path, datetime(2026, 10, 8, 14, 0, tzinfo=ET))
    conn = L.connect(tmp_path / "j.sqlite")
    days_desk = Proc(polls=[None, 3])                     # alive, then exits
    started = []
    monkeypatch.setattr(day, "start_desk", lambda syms, dry, record_until=None:
                        started.append((syms, record_until)) or Proc())
    monkeypatch.setattr(day, "desk_is_on_ibkr", lambda p, timeout_s=420: True)
    monkeypatch.setattr(day, "_gateway_up", lambda until: True)
    naps = []

    def nap(s):
        naps.append(s)
        if len(naps) == 3:
            day.STOP["requested"] = True                  # Ctrl-C
    monkeypatch.setattr(day, "_nap", nap)
    assert day.desk_only(_args(), conn, "after the bot's day", desk=days_desk, symbols=["AAA"]) == 0
    assert started == [(["AAA"], "0")], "the day's desk was kept; only its replacement was started"


def test_a_closed_day_brings_up_the_desk_alone(tmp_path, monkeypatch):
    _at(monkeypatch, tmp_path, datetime(2026, 10, 10, 11, 0, tzinfo=ET))      # a Saturday
    started = []
    monkeypatch.setattr(day, "start_desk", lambda syms, dry, record_until=None:
                        started.append(record_until))                       # a stub: no process
    monkeypatch.setattr(day, "start_runner", lambda *a, **k: pytest.fail("no runner on a closed day"))
    assert day.main(["--symbols", "AAA"]) == 0
    assert started == ["0"]


def test_the_end_of_the_bots_day_stops_the_runner_keeps_the_desk_then_settles(tmp_path, monkeypatch):
    clock = _at(monkeypatch, tmp_path, datetime(2026, 10, 8, 11, 29, tzinfo=ET), step=timedelta(seconds=20))
    desk, runner, awake = Proc(), Proc(), SimpleNamespace(terminated=False)
    awake.terminate = lambda: setattr(awake, "terminated", True)
    monkeypatch.setattr(day, "start_desk", lambda syms, dry, record_until=None:
                        setattr(desk, "record_until", record_until) or desk)
    monkeypatch.setattr(day, "start_runner", lambda *a, **k: runner)
    monkeypatch.setattr(day, "desk_is_on_ibkr", lambda p, timeout_s=420: True)
    monkeypatch.setattr(day, "keep_awake", lambda dry: awake)
    monkeypatch.setattr(day, "ibkr_port", lambda env=None: ("4002", "IBKR_PORT"))
    monkeypatch.setattr(day, "run_alignment_once", lambda *a: None)
    monkeypatch.setattr(day.time, "sleep", lambda s: None)
    settled, handed = [], []
    monkeypatch.setattr(day, "after_close", lambda conn, d, dry: settled.append((d, clock.t)))
    monkeypatch.setattr(day, "desk_only", lambda args, conn, why, **kw: handed.append((why, kw)) or 0)
    assert day.main(["--symbols", "AAA"]) == 0
    assert desk.record_until == "2026-10-08T11:31:30-04:00"
    assert runner.signals == [signal.SIGINT] and desk.signals == [], "the runner stops, the desk stays"
    assert awake.terminated, "the Mac is not held awake for the desk alone"
    d, when = settled[0]
    assert d == "2026-10-08" and when >= datetime(2026, 10, 8, 11, 32, 30, tzinfo=ET), "settled on a still ledger"
    why, kw = handed[0]
    assert kw["desk"] is desk and kw["day"] == "2026-10-08" and kw["symbols"] == ["AAA"]


# -- the morning: the same run starts the next day, holding the lock ---------------------

def test_the_lock_crosses_the_exec_without_being_let_go(tmp_path, monkeypatch):
    lock = tmp_path / "j.sqlite.day.lock"
    held, _ = day.day_lock(lock)
    dup = os.dup(held.fileno())                          # what the exec'd image inherits
    held.close()
    monkeypatch.setenv("DAY_LOCK_FD", str(dup))
    adopted, other = day.day_lock(tmp_path / "another.lock")
    assert adopted is not None and other is None and "DAY_LOCK_FD" not in os.environ
    third, pid = day.day_lock(lock)
    assert third is None and pid == str(os.getpid()), "the 06:55 job cannot slip in"
    adopted.close()
    fourth, _ = day.day_lock(lock)
    assert fourth is not None
    fourth.close()


def test_the_scheduled_job_rolls_over_in_place_with_the_lock(tmp_path, monkeypatch):
    held, _ = day.day_lock(tmp_path / "j.sqlite.day.lock")
    monkeypatch.setattr(day, "FORCED_PORT", "")
    monkeypatch.setenv("IBKR_PORT", "4002")              # detected yesterday, not forced
    monkeypatch.delenv("DAY_LOCK_FD", raising=False)
    execs, steps = [], []

    def execv(path, argv):
        execs.append((argv, os.environ.get("DAY_LOCK_FD"), os.get_inheritable(held.fileno()),
                      os.environ.get("IBKR_PORT")))
    try:
        rc = day.rollover(SimpleNamespace(_day_lock=held), execv=execv, terminal=False,
                          network=lambda: steps.append("network") or True,
                          before=lambda: steps.append("late calls"), pull=lambda: steps.append("pull"))
        assert rc == 0 and steps == ["network", "late calls", "pull"]
        argv, fd, inheritable, port = execs[0]
        assert argv[1].endswith("scripts/day.py") and argv[2:] == ["--no-open"], "no --symbols, --early, --probe-orders"
        assert fd == str(held.fileno()) and inheritable and port is None
        assert "DAY_LOCK_FD" not in os.environ, "never left for another process to adopt"
    finally:
        held.close()


def test_a_terminal_run_starts_the_day_in_the_background_with_the_jobs_log(tmp_path, monkeypatch, capsys):
    """Review 2026-10-08: rolled over in place, the day would run in the
    terminal window — closing it (SIGHUP) would end the day mid-session, and
    the daily export would find no line of the day in the job's log."""
    held, _ = day.day_lock(tmp_path / "j.sqlite.day.lock")
    monkeypatch.setattr(day, "LOG_DIR", tmp_path / "logs")
    monkeypatch.delenv("DAY_LOCK_FD", raising=False)
    spawned = []

    def spawn(argv, **kw):
        spawned.append((argv, kw, os.environ.get("DAY_LOCK_FD")))
        return SimpleNamespace(pid=4242)
    try:
        rc = day.rollover(SimpleNamespace(_day_lock=held), spawn=spawn, terminal=True,
                          network=lambda: True, pull=lambda: None)
        assert rc == 0
        argv, kw, fd = spawned[0]
        assert argv[2:] == ["--no-open"] and fd == str(held.fileno())
        assert kw["start_new_session"] is True and kw["pass_fds"] == (held.fileno(),)
        assert kw["stdout"].name == str(tmp_path / "logs" / "day.out.log")
        assert kw["stdin"] == day.subprocess.DEVNULL
        out = capsys.readouterr().out
        assert "pid 4242" in out and "kill -INT 4242" in out and "day.out.log" in out
    finally:
        held.close()


def test_ctrl_c_during_the_morning_pull_starts_no_day(tmp_path, monkeypatch):
    held, _ = day.day_lock(tmp_path / "j.sqlite.day.lock")

    def pull():
        day.STOP["requested"] = True                     # Ctrl-C while git works
    try:
        rc = day.rollover(SimpleNamespace(_day_lock=held), terminal=False, network=lambda: True, pull=pull,
                          execv=lambda *a: pytest.fail("the day started after Ctrl-C"),
                          spawn=lambda *a, **k: pytest.fail("the day started after Ctrl-C"))
        assert rc == 0
    finally:
        held.close()


def test_the_morning_pull_is_the_jobs_and_runs_what_is_on_disk_when_it_fails():
    calls = []

    def run(cmd, **kw):
        calls.append((cmd, kw.get("timeout")))
        ok = cmd[3] == "rev-parse"
        return SimpleNamespace(returncode=0 if ok else 1, stdout="claude/branch\n" if ok else "")
    assert day.pull_code(run=run) is False
    assert [c[0][3] for c in calls] == ["rev-parse", "pull"], "once, as scripts/install_daily.sh does"
    assert calls[1][0][-2:] == ["origin", "claude/branch"] and calls[1][1] == 120

    def hangs(cmd, **kw):
        raise day.subprocess.TimeoutExpired(cmd, kw.get("timeout"))
    assert day.pull_code(run=hangs) is False

    def ok(cmd, **kw):
        return SimpleNamespace(returncode=0, stdout="claude/branch\n")
    assert day.pull_code(run=ok) is True


def test_the_network_wait_is_the_jobs_two_minutes_and_ends_on_ctrl_c(monkeypatch):
    import socket
    tries = []

    def no_dns(*a, **k):
        tries.append(1)
        raise OSError("no DNS")
    monkeypatch.setattr(socket, "getaddrinfo", no_dns)
    naps = []
    assert day.wait_for_network(nap=naps.append) is False
    assert len(tries) == 12 and naps == [10] * 11
    tries.clear()
    day.STOP["requested"] = True
    assert day.wait_for_network(nap=naps.append) is False and len(tries) == 1


def _day_harness(monkeypatch, tmp_path, desk_polls=None, start=(11, 29)):
    clock = _at(monkeypatch, tmp_path, datetime(2026, 10, 8, *start, tzinfo=ET), step=timedelta(seconds=20))
    desks, runner = [], Proc()

    def start(syms, dry, record_until=None):
        p = Proc(polls=desk_polls if not desks else None)
        p.record_until = record_until
        desks.append(p)
        return p
    monkeypatch.setattr(day, "start_desk", start)
    monkeypatch.setattr(day, "start_runner", lambda *a, **k: runner)
    monkeypatch.setattr(day, "desk_is_on_ibkr", lambda p, timeout_s=420: True)
    monkeypatch.setattr(day, "keep_awake", lambda dry: None)
    monkeypatch.setattr(day, "ibkr_port", lambda env=None: ("4002", "IBKR_PORT"))
    monkeypatch.setattr(day, "wait_for_gateway", lambda *a, **k: True)
    monkeypatch.setattr(day, "run_alignment_once", lambda *a: None)
    monkeypatch.setattr(day.time, "sleep", lambda s: None)
    handed = []
    monkeypatch.setattr(day, "desk_only", lambda args, conn, why, **kw: handed.append(kw) or 0)
    return clock, desks, runner, handed


def test_a_failed_settle_is_said_and_the_platform_still_comes_up(tmp_path, monkeypatch, capsys):
    _, desks, _, handed = _day_harness(monkeypatch, tmp_path)

    def broken(conn, d, dry):
        raise RuntimeError("ledger locked")
    monkeypatch.setattr(day, "after_close", broken)
    assert day.main(["--symbols", "AAA"]) == 0
    out = capsys.readouterr().out
    assert "after-close block failed" in out and "--settle 2026-10-08" in out
    assert handed and handed[0]["desk"] is desks[0], "the desk goes on regardless"


def test_a_restart_you_asked_for_is_not_counted_as_an_outage(tmp_path, monkeypatch, capsys):
    _, desks, _, _ = _day_harness(monkeypatch, tmp_path, desk_polls=[None, 0], start=(11, 20))
    monkeypatch.setattr(day, "after_close", lambda conn, d, dry: None)
    (tmp_path / "j.sqlite.desk.restart").write_text("x")          # python3 scripts/day.py --restart-desk
    assert day.main(["--symbols", "AAA"]) == 0
    out = capsys.readouterr().out
    assert "desk restarting on the code now on disk" in out and "desk exited with" not in out
    assert len(desks) == 2 and desks[1].record_until == "2026-10-08T11:31:30-04:00", "same cutoff after a restart"


def test_restart_desk_leaves_a_desk_that_is_still_coming_up_or_code_that_cannot_start(tmp_path, monkeypatch,
                                                                                     capsys):
    """Review 2026-10-08: a desk killed while it boots reads to the day as a
    desk that failed to start — "stopping the day"; and a restart onto code
    that cannot import leaves the day with no desk at all."""
    monkeypatch.setattr(day, "DAY_LOCK", tmp_path / "j.sqlite.day.lock")
    monkeypatch.setattr(day, "RESTART_MARK", tmp_path / "j.sqlite.desk.restart")
    held, _ = day.day_lock(tmp_path / "j.sqlite.day.lock")
    killed = []
    try:
        for booting in (None, {"mode": "live", "streaming": False}, {"mode": "replay", "streaming": True}):
            assert day.restart_desk(kill=lambda *a: killed.append(a), find=lambda: [4242],
                                    health=lambda: booting, imports=lambda: None) == 1
        assert "not up yet" in capsys.readouterr().out
        up = {"mode": "live", "streaming": True, "codeAtStart": "abc"}
        assert day.restart_desk(kill=lambda *a: killed.append(a), find=lambda: [4242], health=lambda: up,
                                imports=lambda: "SyntaxError: invalid syntax") == 1
        assert "does not import (SyntaxError" in capsys.readouterr().out
        assert killed == [] and not (tmp_path / "j.sqlite.desk.restart").exists()
    finally:
        held.close()


def test_the_code_check_imports_the_desk_from_this_checkout():
    assert day.code_imports() is None


def test_the_desk_search_matches_day_py_desks_and_not_start_sh_ones(monkeypatch):
    import re
    seen = []

    class Popen:
        def __init__(self, cmd, cwd=None, env=None):
            seen.append(" ".join(cmd))
    monkeypatch.setattr(day.subprocess, "Popen", Popen)
    monkeypatch.delenv("DESK_PORT", raising=False)
    day.start_desk(["AAA", "BBB"], False)
    day.start_desk([], False)                                   # the scanner picks: an empty --ibkr
    pattern = re.compile(day.DESK_CMD_RE.format(port="8787"))
    assert all(pattern.search(cmd) for cmd in seen), seen
    start_sh = "python3 -m momentum_platform.dashboard.server --host 127.0.0.1 --port 8787 --ibkr AAA"
    assert not pattern.search(start_sh)


def test_a_restart_you_asked_for_that_fails_never_ends_the_day(tmp_path, monkeypatch, capsys):
    """Review 2026-10-08: the day used to stop — runner included — when the
    restarted desk did not come up. Now it is an outage like any other."""
    _, desks, runner, handed = _day_harness(monkeypatch, tmp_path, desk_polls=[None, 0], start=(11, 20))
    monkeypatch.setattr(day, "after_close", lambda conn, d, dry: None)
    ups = iter([True, False, True])                       # first boot, the asked restart, the outage restart
    monkeypatch.setattr(day, "desk_is_on_ibkr", lambda p, timeout_s=420: next(ups))
    (tmp_path / "j.sqlite.desk.restart").write_text("x")
    assert day.main(["--symbols", "AAA"]) == 0
    out = capsys.readouterr().out
    assert "handled as an outage" in out and "stopping the day" not in out
    assert len(desks) == 3 and desks[1].signals == [signal.SIGINT]
    assert runner.signals == [signal.SIGINT], "the runner is stopped once, at the end of its day"
    assert handed and handed[0]["desk"] is desks[2]


def test_the_backoff_never_runs_past_the_mornings_start(tmp_path, monkeypatch):
    _at(monkeypatch, tmp_path, datetime(2026, 10, 9, 6, 50, tzinfo=ET))       # five minutes before the day
    conn = L.connect(tmp_path / "j.sqlite")
    naps = []

    def nap(s):
        naps.append(s)
        day.STOP["requested"] = True
    monkeypatch.setattr(day, "_nap", nap)
    monkeypatch.setattr(day, "_gateway_up", lambda until: False)
    for _ in range(3):                                    # a desk that keeps dying: the backoff grows
        naps.clear(); day.STOP["requested"] = False
        assert day.desk_only(_args(), conn, "before the day", desk=Proc(polls=[None, 3])) == 0
        assert naps and max(naps) <= 300, naps


def test_a_relaunch_after_the_day_does_not_settle_it_again(tmp_path, monkeypatch):
    """Review 2026-10-08: each relaunch after 11:30 re-ran the after-close
    block — a report saying "session 2" for a day counted once, and a new
    export commit every time."""
    _at(monkeypatch, tmp_path, datetime(2026, 10, 8, 14, 0, tzinfo=ET))
    monkeypatch.setattr(day, "REPORTS", tmp_path / "reports")
    settled = []
    monkeypatch.setattr(day, "after_close", lambda conn, d, dry: settled.append(d))
    _capture_desk_only(monkeypatch)
    assert day.main([]) == 0 and settled == ["2026-10-08"], "no report yet: settled"
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "2026-10-08.md").write_text("# report")
    assert day.main([]) == 0 and settled == ["2026-10-08"], "settled already: not again"


def test_a_report_written_again_keeps_the_session_number_it_was_counted_as(tmp_path, monkeypatch):
    monkeypatch.setattr(day, "REPORTS", tmp_path)
    conn = L.connect(":memory:")
    L.set_state(conn, sessions_done=3, last_session_date="2026-10-08")
    assert "session 3 ·" in day.write_report(conn, "2026-10-08", "x").read_text()
    assert "session 4 ·" in day.write_report(conn, "2026-10-09", "x").read_text()


def test_late_calls_go_out_ten_minutes_after_the_newest_one(tmp_path, monkeypatch):
    conn = L.connect(tmp_path / "j.sqlite")
    sent = []
    monkeypatch.setattr(day, "export_day", lambda c, d: sent.append(d))
    clock = {"t": 1000.0}
    monkeypatch.setattr(day.time, "monotonic", lambda: clock["t"])
    late = day.LateCalls(conn, "2026-10-08")
    late.check()
    assert sent == []
    L.record_manual(conn, "AAA", "took", price=4.0, shares=100, stop=3.8, at=AFTERNOON); conn.commit()
    late.check(); clock["t"] += 300; late.check()
    assert sent == [], "a burst of calls is not one push each"
    clock["t"] += 301; late.check()
    assert sent == ["2026-10-08"]
    late.check(final=True)
    assert sent == ["2026-10-08"], "nothing new: nothing sent"
    L.record_manual(conn, "AAA", "closed", price=4.4, at=AFTERNOON); conn.commit()
    late.check(final=True)
    assert sent == ["2026-10-08", "2026-10-08"]
    assert day.LateCalls(conn, None).sent is None, "no day (closed, before the day): nothing to send"


def test_an_earlier_day_that_fails_to_settle_does_not_keep_the_platform_down(tmp_path, monkeypatch, capsys):
    _at(monkeypatch, tmp_path, datetime(2026, 10, 10, 11, 0, tzinfo=ET))      # a Saturday
    monkeypatch.setattr(day, "settle_unsettled", lambda *a: (_ for _ in ()).throw(RuntimeError("locked")))
    calls = _capture_desk_only(monkeypatch)
    assert day.main([]) == 0 and calls and "settling an earlier day failed" in capsys.readouterr().out


def test_a_restart_mark_left_behind_is_void_when_a_desk_starts(tmp_path, monkeypatch):
    mark = tmp_path / "j.sqlite.desk.restart"
    monkeypatch.setattr(day, "RESTART_MARK", mark)
    monkeypatch.setattr(day.subprocess, "Popen", lambda *a, **k: None)
    mark.write_text("x")
    day.start_desk(["AAA"], False)
    assert not mark.exists(), "a real crash after it must still be counted"


# -- one command: update, then the day (owner, 2026-10-09) ---------------------------

def _sandbox(tmp_path, update_rc: int):
    """go.sh beside stand-ins for update.sh and day.py that say what they got."""
    import shutil
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy(ROOT / "scripts" / "go.sh", scripts / "go.sh")
    (scripts / "update.sh").write_text(f'echo "update ran GO_SH=${{GO_SH:-}}"\nexit {update_rc}\n')
    (scripts / "day.py").write_text("import os, sys\nprint('day.py', sys.argv[1:], 'IBKR_PORT=' + os.environ.get('IBKR_PORT', ''))\n")
    return scripts / "go.sh"


def test_go_updates_then_starts_the_day_with_the_flags(tmp_path, monkeypatch):
    import subprocess
    go = _sandbox(tmp_path, 0)
    monkeypatch.delenv("IBKR_PORT", raising=False)
    out = subprocess.run(["bash", str(go), "--symbols", "AAA,BBB"], capture_output=True, text=True,
                         timeout=60, cwd=tmp_path).stdout
    assert out.index("update ran GO_SH=1") < out.index("day.py ['--symbols', 'AAA,BBB'] IBKR_PORT=4002")
    out = subprocess.run(["bash", str(go)], capture_output=True, text=True, timeout=60, cwd=tmp_path,
                         env={**os.environ, "IBKR_PORT": "7497"}).stdout
    assert "day.py [] IBKR_PORT=7497" in out, "no flags, and a port you set is kept"


def test_go_starts_the_day_on_the_code_on_disk_when_the_update_fails(tmp_path):
    import subprocess
    out = subprocess.run(["bash", str(_sandbox(tmp_path, 1))], capture_output=True, text=True,
                         timeout=60, cwd=tmp_path).stdout
    assert "update failed — starting on the code on disk" in out and "day.py []" in out


def test_go_is_read_whole_before_it_runs():
    """The update rewrites go.sh while bash runs it; bash reads a script as it
    goes. Everything sits in a function that is parsed before it starts."""
    text = (ROOT / "scripts" / "go.sh").read_text()
    body = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    assert body[-1] == 'main ${1+"$@"}' and "main() {" in body
    upd = (ROOT / "scripts" / "update.sh").read_text()
    assert 'if [ -z "${GO_SH:-}" ]; then' in upd, "go.sh's own update does not repeat the start hints"


def test_a_second_launch_restarts_an_idle_desk_on_new_code_and_never_a_recording_one(tmp_path, monkeypatch,
                                                                                   capsys):
    _at(monkeypatch, tmp_path, datetime(2026, 10, 9, 5, 15, tzinfo=ET))
    held, _ = day.day_lock(tmp_path / "j.sqlite.day.lock")       # the run in another terminal
    restarted = []
    monkeypatch.setattr(day, "restart_desk", lambda *a, **k: restarted.append(True) or 0)
    try:
        # the desk alone before 06:55: records nothing, older code — restarted
        monkeypatch.setattr(day, "desk_health", lambda timeout=3.0: {
            "provider": {"state": "LIVE", "recording": False}})
        assert day.main(["--no-open"]) == 0 and restarted == [True]
        assert "restarts on this code now" in capsys.readouterr().out
        # the bot's day: the desk records — told, never touched
        monkeypatch.setattr(day, "desk_health", lambda timeout=3.0: {
            "provider": {"state": "LIVE", "recording": True}})
        assert day.main(["--no-open"]) == 0 and restarted == [True]
        assert "--restart-desk" in capsys.readouterr().out
    finally:
        held.close()


# -- one command to restart a day already started (owner, 2026-10-09) --------------

def _restart_sandbox(tmp_path):
    """restart.sh beside stand-ins: exercise.py answers `busy` with $BUSY_RC;
    day.py with --hold runs until SIGINT (ignores it with --stubborn), else says
    what it got."""
    import shutil
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy(ROOT / "scripts" / "restart.sh", scripts / "restart.sh")
    (scripts / "exercise.py").write_text(
        "import os, sys\nprint('busy asked')\nsys.exit(int(os.environ.get('BUSY_RC', '0')))\n")
    (scripts / "day.py").write_text(
        "import os, signal, sys, time\n"
        "if '--hold' in sys.argv:\n"
        "    signal.signal(signal.SIGINT, signal.SIG_IGN if '--stubborn' in sys.argv else (lambda *_: sys.exit(0)))\n"
        "    time.sleep(120); sys.exit(0)\n"
        "print('day.py', sys.argv[1:], 'IBKR_PORT=' + os.environ.get('IBKR_PORT', ''))\n")
    return scripts


def _running_day(scripts, *flags):
    import subprocess, time
    p = subprocess.Popen(["python3", str(scripts / "day.py"), "--hold", *flags])
    time.sleep(0.5)
    return p


def test_restart_starts_the_day_when_none_runs(tmp_path, monkeypatch):
    import subprocess
    scripts = _restart_sandbox(tmp_path)
    monkeypatch.delenv("IBKR_PORT", raising=False)
    out = subprocess.run(["bash", str(scripts / "restart.sh")], capture_output=True, text=True, timeout=60,
                         cwd=tmp_path).stdout
    assert "no trading day running" in out and "day.py [] IBKR_PORT=4002" in out
    assert "busy asked" not in out


def test_restart_stops_a_flat_day_cleanly_then_starts_it_again(tmp_path):
    import subprocess
    scripts = _restart_sandbox(tmp_path)
    day = _running_day(scripts)
    try:
        out = subprocess.run(["bash", str(scripts / "restart.sh"), "--symbols", "AAA"], capture_output=True,
                             text=True, timeout=60, cwd=tmp_path, env={**os.environ, "BUSY_RC": "0"}).stdout
        assert day.poll() is not None, "the running day was stopped"
        assert out.index("stopping the running day cleanly") < out.index("day.py ['--symbols', 'AAA']")
    finally:
        if day.poll() is None:
            day.kill()


def test_restart_never_stops_a_day_holding_a_position(tmp_path):
    """A stopped runner leaves a monitored stop unwatched: with a position or
    a working entry the day keeps running and only the desk restarts."""
    import subprocess
    scripts = _restart_sandbox(tmp_path)
    day = _running_day(scripts)
    try:
        out = subprocess.run(["bash", str(scripts / "restart.sh")], capture_output=True, text=True, timeout=60,
                             cwd=tmp_path, env={**os.environ, "BUSY_RC": "3"}).stdout
        assert day.poll() is None, "the day holding a position is still running"
        assert "holds a position or a working entry" in out and "day.py ['--restart-desk']" in out
    finally:
        day.kill()


def test_restart_starts_nothing_when_the_day_will_not_stop(tmp_path):
    import subprocess
    scripts = _restart_sandbox(tmp_path)
    day = _running_day(scripts, "--stubborn")
    try:
        r = subprocess.run(["bash", str(scripts / "restart.sh")], capture_output=True, text=True, timeout=60,
                           cwd=tmp_path, env={**os.environ, "BUSY_RC": "0", "RESTART_WAIT_S": "2"})
        assert r.returncode == 1 and "nothing started" in r.stdout and "day.py [" not in r.stdout
        assert day.poll() is None
    finally:
        day.kill()


def test_busy_reads_positions_and_fresh_entries_only(tmp_path):
    """exercise.py busy: a filled, un-exited order or an entry placed in the
    last ten minutes and not in a terminal state; an old unfilled row is a
    ledger that never heard the cancel."""
    import importlib, sys as _sys
    from datetime import datetime, timedelta, timezone
    _sys.path.insert(0, str(ROOT / "scripts"))
    ex = importlib.import_module("exercise")
    from journal import ledger as L
    c = L.connect(str(tmp_path / "j.sqlite"))
    now = datetime(2026, 10, 9, 14, 0, tzinfo=timezone.utc)
    c.execute("INSERT INTO decisions (decision_id, ts_et, session, symbol, source, session_id, source_name, data_status,"
              " bar_resolution, verdict, plan_allowed, gates_json, warnings_json, inputs_json, recorded_at, rules_hash,"
              " code_commit) VALUES ('d1','2026-10-09T09:55:00-04:00','regular','AAA','t','s','t','LIVE','1m','REVIEW',1,"
              "'[]','[]','{}','x','h','c')")

    def order(oid, status, placed, fill=None, exit_ts=None):
        c.execute("INSERT INTO orders (order_id, decision_id, symbol, session, trigger, stop, shares, dollar_risk,"
                  " planned_risk, status, fill_price, exit_ts, placed_at, updated_at) VALUES"
                  " (?, 'd1', 'AAA', 'regular', 5.0, 4.8, 100, 20, 20, ?, ?, ?, ?, ?)",
                  (oid, status, fill, exit_ts, placed.isoformat(), placed.isoformat()))
    order(1, "Cancelled", now - timedelta(minutes=2))
    order(2, "submitted", now - timedelta(minutes=45))          # stale row, not a live order
    c.commit()
    held, working = ex.busy_rows(c, now=now)
    assert held == [] and working == []
    order(3, "submitted", now - timedelta(minutes=3))
    c.commit()
    assert [o["order_id"] for o in ex.busy_rows(c, now=now)[1]] == [3]
    order(4, "Filled", now - timedelta(minutes=30), fill=5.01)
    c.commit()
    assert [o["order_id"] for o in ex.busy_rows(c, now=now)[0]] == [4]


def test_restart_is_read_whole_before_it_runs():
    """The update before it may rewrite restart.sh; bash reads a script as it
    goes, so everything sits in a function parsed before it starts."""
    text = (ROOT / "scripts" / "restart.sh").read_text()
    body = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    assert body[-1] == 'main ${1+"$@"}' and "main() {" in body
