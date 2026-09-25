"""SQLite decision ledger. Append-only, idempotent, point-in-time.

Idempotency matters more here than it usually does. The live desk rebuilds
its whole session from scratch every few seconds (`ibkr_desk.py`), and the
detector's `plan_id` is a fresh uuid each time, so the same plan would be
recorded hundreds of times over a morning. Decisions are therefore keyed on
what makes them the same decision — symbol, the bar that armed the plan,
entry and stop — and a repeat write is a no-op.

Everything in `decisions` is what was knowable AT THAT BAR. The full cascade
`Inputs` are stored as JSON so `replay.py` can re-run the cascade on exactly
what it saw and prove the verdict reproduces (R11). Nothing here is updated
later except the `outcome` columns, which record what the runner did with
the decision, and those record a fact about the runner, not about the market.

Market outcomes live in `actuals`, written later from the forward tape, and
are kept in a separate table so a decision row can never be contaminated by
knowledge of what happened next.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# 07:00 / 09:30 / 16:00 are defined once, in the desk's calendar. The import
# arrow is journal -> momentum_platform.sessions (a leaf module); the desk
# imports journal too, and that is fine because sessions.py imports nothing
# back. Pre-market's 07:00 floor is PARAMETERS.md §2 `premarket_start`.
from momentum_platform.sessions import REGULAR_END, REGULAR_START  # noqa: E402
from datetime import time as _time                                  # noqa: E402
PREMARKET_START = _time(7, 0)


def session_of(ts) -> str:
    """premarket | regular | none — for the bar's ET wall clock."""
    t = datetime.fromisoformat(_et(ts))
    if t.weekday() >= 5:
        return "none"
    if REGULAR_START <= t.time() < REGULAR_END:
        return "regular"
    if PREMARKET_START <= t.time() < REGULAR_START:
        return "premarket"
    return "none"

DEFAULT_DB = Path(os.environ.get(
    "JOURNAL_DB", Path(__file__).resolve().parents[2] / "data" / "journal.sqlite"))

# The runner's verdict on a decision. PENDING until the runner has looked.
# CLAIMED: the runner wrote the intent and is about to send; a row left in
# CLAIMED after a restart is an ambiguous send and is reconciled, never resent.
# UNRESOLVED: the reconciliation could not find the order at the broker.
# EXPIRED: an allowed plan the runner never acted on because no runner was
# alive when it armed (desk up, runner down, or armed after the hard stop).
# Set by the day's close-out, never by the runner. Review 2026-09-21: 66
# allowed − 65 refused − 0 taken = 1 with no named state; every allowed
# decision now reconciles to one of these words (`funnel`, `reconcile_allowed`).
OUTCOMES = ("PENDING", "CLAIMED", "TAKEN", "REFUSED", "NOT_FILLED", "LOG_ONLY", "SUPPRESSED",
            "UNRESOLVED", "EXPIRED")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    decision_id     TEXT PRIMARY KEY,
    ts_et           TEXT NOT NULL,        -- bar time, ET, ISO
    session         TEXT NOT NULL,        -- premarket | regular | none
    symbol          TEXT NOT NULL,
    source          TEXT NOT NULL,        -- pullback | manual
    session_id      TEXT,                 -- the desk session this came from
    source_name     TEXT,                 -- feed provenance, verbatim
    data_status     TEXT,                 -- live | replay | delayed ...
    bar_resolution  TEXT,                 -- '1m' — see the brief on 10-second entries
    -- point in time
    last REAL, bid REAL, ask REAL, session_high REAL, volume REAL, rvol REAL,
    change_pct REAL, float_shares REAL, float_quality TEXT, float_source TEXT,
    catalyst INTEGER, halted INTEGER,
    -- cascade
    verdict TEXT NOT NULL, killed_by TEXT, plan_allowed INTEGER NOT NULL,
    gates_json TEXT NOT NULL, warnings_json TEXT NOT NULL,
    inputs_json TEXT NOT NULL,            -- the cascade Inputs, for replay
    -- the plan
    trigger REAL, stop REAL, target REAL, risk_share REAL, reward_multiple REAL,
    pullback_candles INTEGER, volume_ok INTEGER,
    -- what the runner did (a fact about the runner, not the market)
    outcome TEXT NOT NULL DEFAULT 'PENDING',
    refusal_reasons_json TEXT,
    acted_at TEXT,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_decisions_outcome ON decisions(outcome);
CREATE INDEX IF NOT EXISTS ix_decisions_symbol_ts ON decisions(symbol, ts_et);

-- R1: the denominator. One row per symbol per snapshot of the board.
CREATE TABLE IF NOT EXISTS board_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_et TEXT NOT NULL, session_id TEXT, symbol TEXT NOT NULL,
    verdict TEXT NOT NULL, killed_by TEXT, plan_allowed INTEGER NOT NULL,
    last REAL, recorded_at TEXT NOT NULL,
    UNIQUE(ts_et, session_id, symbol)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT NOT NULL REFERENCES decisions(decision_id),
    symbol TEXT NOT NULL, account TEXT, session TEXT NOT NULL,
    parent_id INTEGER, stop_id INTEGER, target_id INTEGER,
    trigger REAL NOT NULL, stop REAL NOT NULL, target REAL, shares INTEGER NOT NULL,
    dollar_risk REAL NOT NULL, planned_risk REAL NOT NULL,     -- R3 planned
    protected INTEGER NOT NULL DEFAULT 0, stop_status TEXT,
    status TEXT NOT NULL DEFAULT 'submitted',
    fill_price REAL, fill_ts TEXT,
    realised_risk REAL, slippage_ratio REAL,                    -- R3 realised
    nbbo_bid REAL, nbbo_ask REAL, nbbo_bid_size REAL, nbbo_ask_size REAL,
    nbbo_ts TEXT,                                               -- R4
    exit_reason TEXT, exit_price REAL, exit_ts TEXT,
    exit_confirmed_by TEXT,                                     -- AH exception only
    perm_id INTEGER,                                            -- IBKR permId, survives restarts
    placed_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

-- Immutable history of every decision write that changed the row (audit
-- 2026-09-08, F-"preserve the original decision"). The decisions table is the
-- latest-state projection; this is the record of what it said before.
CREATE TABLE IF NOT EXISTS decision_revisions (
    rev_id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT NOT NULL, recorded_at TEXT NOT NULL,
    data_status TEXT, verdict TEXT, killed_by TEXT, plan_allowed INTEGER,
    outcome TEXT, last REAL, bid REAL, ask REAL,
    gates_json TEXT, warnings_json TEXT, inputs_json TEXT
);
CREATE INDEX IF NOT EXISTS ix_revisions_decision ON decision_revisions(decision_id);

-- Every quote change the desk saw, time-indexed, so a fill can be joined to
-- the quote in force AT THE EXECUTION TIME rather than at the poll that
-- noticed the fill (R4). `quotes` keeps only the latest per symbol.
CREATE TABLE IF NOT EXISTS quote_ticks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL, ts TEXT NOT NULL, bid REAL, ask REAL,
    bid_size REAL, ask_size REAL, recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_quote_ticks_symbol_ts ON quote_ticks(symbol, ts);

-- The daily risk latch (journal/risk.py). One row per ET date; once locked,
-- stays locked for the day and survives a restart.
CREATE TABLE IF NOT EXISTS risk_day (
    date TEXT PRIMARY KEY, locked INTEGER NOT NULL DEFAULT 0,
    reason TEXT, locked_at TEXT
);

-- Free-text events against an order: what the runner saw and did, in order.
CREATE TABLE IF NOT EXISTS order_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    ts TEXT NOT NULL, text TEXT NOT NULL
);

-- Halts encountered, with the price either side. PARAMETERS.md §10 says
-- halt-resume fills are unmodellable from OHLCV; the live log is the only
-- place this ever gets measured.
CREATE TABLE IF NOT EXISTS halts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_et TEXT NOT NULL, symbol TEXT NOT NULL, status TEXT NOT NULL,
    last_before REAL, recorded_at TEXT NOT NULL,
    UNIQUE(ts_et, symbol, status)
);

-- The tape the desk saw, so actuals can run on a real session with no
-- fixture and so the runner can read an NBBO without a second broker
-- connection. One row per symbol per bar; repeats are ignored.
CREATE TABLE IF NOT EXISTS bars (
    symbol TEXT NOT NULL, ts TEXT NOT NULL,          -- ts is UTC ISO, as the feed gave it
    open REAL, high REAL, low REAL, close REAL, volume REAL,
    bid REAL, ask REAL,
    PRIMARY KEY (symbol, ts)
);

-- Ten-second candles, in their OWN table on purpose.
--
-- `bars` is the 1-minute tape the grader and the replay check read
-- (`journal.bars.from_ledger` selects every row in it). Putting 10-second
-- rows there would silently hand the grader six times the bars and re-grade
-- the whole phase-A cohort against a different tape. So: separate table,
-- same shape, no bid/ask (the quote is in `quote_ticks` with its own clock).
--
-- Written by the desk as the BarStore drains each closed candle; that drain
-- is destructive, so a candle not captured here is gone for good.
-- docs/PLAN-10s-micro-pullback.md M1.
CREATE TABLE IF NOT EXISTS bars_10s (
    symbol TEXT NOT NULL, ts TEXT NOT NULL,          -- ts is UTC ISO, bucket start
    open REAL, high REAL, low REAL, close REAL, volume REAL,
    PRIMARY KEY (symbol, ts)
);

-- Latest quote per symbol, overwritten on every desk rebuild. This is the
-- runner's NBBO source at fill time (R4). The gap between a fill and the
-- quote read is recorded through the two timestamps, never hidden.
CREATE TABLE IF NOT EXISTS quotes (
    symbol TEXT PRIMARY KEY,
    bid REAL, ask REAL, bid_size REAL, ask_size REAL,
    ts TEXT NOT NULL, recorded_at TEXT NOT NULL
);

-- Where the exercise is. One row, keyed 'state'. Phase letters follow
-- docs/preregistration.md §3; the probe verdict follows §5.
CREATE TABLE IF NOT EXISTS exercise_state (
    key TEXT PRIMARY KEY CHECK (key = 'state'),
    phase TEXT NOT NULL DEFAULT 'A',             -- A log-only, B regular, C +premarket, D read-out
    sessions_done INTEGER NOT NULL DEFAULT 0,
    probe_verdict TEXT,                          -- held | queued | inconclusive
    probe_date TEXT,
    dollar_risk REAL,
    paper_data TEXT,                             -- realtime | delayed | none  (alignment probe)
    paper_data_date TEXT,
    last_session_date TEXT,                      -- the ET date already counted in sessions_done
    updated_at TEXT NOT NULL
);

-- R1, the denominator BEFORE the desk: every name the morning gap scan
-- returned, survivor or reject, with the reason. Without it the funnel began
-- at the watchlist and the scan's own kills were invisible (audit 2026-09-08).
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_et TEXT NOT NULL, source TEXT NOT NULL, symbol TEXT NOT NULL,
    verdict TEXT, reasons_json TEXT, price REAL, gap_pct REAL, float_shares REAL,
    pm_volume REAL, recorded_at TEXT NOT NULL,
    UNIQUE(ts_et, source, symbol)
);

-- Written later, from the forward tape. Separate table on purpose: a
-- decision row must never know what happened next.
CREATE TABLE IF NOT EXISTS actuals (
    decision_id TEXT PRIMARY KEY REFERENCES decisions(decision_id),
    ref_price REAL NOT NULL, risk_share REAL,
    h5 REAL, l5 REAL, c5 REAL, h15 REAL, l15 REAL, c15 REAL,
    h30 REAL, l30 REAL, c30 REAL, h60 REAL, l60 REAL, c60 REAL,
    h_close REAL, l_close REAL, c_close REAL,
    mfe_r_planned REAL, mae_r_planned REAL,      -- planned-R; the name says so
    stop_hit INTEGER, stop_hit_ts TEXT, target_hit INTEGER, target_hit_ts TEXT,
    first_hit TEXT,                               -- stop | target | neither | untriggered
    trigger_hit INTEGER, trigger_hit_ts TEXT,     -- did price ever reach the entry?
    bars_available INTEGER NOT NULL, computed_at TEXT NOT NULL
);
"""


# --------------------------------------------------------------- plumbing
def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: the live desk rebuilds on a worker thread and
    # the runner reads on another. Writes are single-statement and idempotent,
    # so SQLite's own locking is enough; nothing here holds a transaction open.
    conn = sqlite3.connect(str(path), timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    if str(path) != ":memory:":
        # Two processes share this file: the desk writes a whole rebuild per
        # transaction, the runner reads and writes every 5 s. WAL lets the
        # reader proceed during the writer's commit instead of hitting
        # "database is locked" after the busy timeout.
        conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    _migrate(conn)
    return conn


# Columns added after a table already existed somewhere. CREATE IF NOT EXISTS
# does not add them; this does, once, and is a no-op afterwards.
_ADDED_COLUMNS = {
    "exercise_state": (("paper_data", "TEXT"), ("paper_data_date", "TEXT"),
                       ("last_session_date", "TEXT"),
                       # Amendment A1 (docs/preregistration.md §5) is accepted by a
                       # human, by command, with a name and a time — never by code.
                       ("a1_accepted", "TEXT"), ("a1_accepted_by", "TEXT"),
                       # owner decision 2026-09-22: the B→C unprotected-fill count restarts
                       # at a named defect fix, recorded by `exercise.py reset-unprotected`
                       ("unprotected_reset_at", "TEXT"), ("unprotected_reset_by", "TEXT"),
                       ("unprotected_reset_fix", "TEXT"),
                       # owner decision 2026-09-23: phase C opened before 30 trades, by command
                       ("phase_c_opened_by", "TEXT"), ("phase_c_opened_at", "TEXT"), ("phase_c_opened_why", "TEXT"),
                       ("a1_accepted_at", "TEXT"),
                       ("code_commit", "TEXT"), ("rules_hash", "TEXT")),
    # Several clocks, not one (review 2026-09-21, item 12): bar_end_ts is
    # the age of the market information; recorded_at is when the desk
    # published the decision (the same rebuild that received the bar, so
    # receipt and publication coincide in this architecture); clocks_json is
    # what the runner saw when it judged the row — its own clock and the
    # desk quote's timestamp — written with the outcome.
    "decisions": (("rules_hash", "TEXT"), ("code_commit", "TEXT"),
                  ("bar_end_ts", "TEXT"), ("clocks_json", "TEXT")),
    "orders": (("perm_id", "INTEGER"), ("symbol", "TEXT"), ("exit_confirmed_by", "TEXT"),
               ("filled_qty", "REAL"), ("exit_order_id", "INTEGER"),
               ("rules_hash", "TEXT"), ("code_commit", "TEXT"), ("nbbo_source", "TEXT"),
               # A3: the stop leg's current level and the high it trails
               ("trail_stop", "REAL"), ("high_since_fill", "REAL"),
               # the resting stop leg's quantity, from the broker (item 13c)
               ("stop_qty", "REAL"),
               # a human named this fill's exit as a code defect's (A3 kill rule, 2026-09-22)
               ("defect_note", "TEXT")),
    "actuals": (("trigger_hit", "INTEGER"), ("trigger_hit_ts", "TEXT")),
}


def _migrate(conn: sqlite3.Connection) -> None:
    for table, cols in _ADDED_COLUMNS.items():
        have = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        for name, typ in cols:
            if name not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ}")
    conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _et(ts) -> str:
    """Any timestamp -> ET ISO string. Naive is assumed UTC, never local:
    blotter clocks in this project are France = ET + 6h, and that has already
    caused confusion once."""
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if isinstance(ts, (int, float)):
        ts = datetime.fromtimestamp(ts, tz=timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(ET).isoformat(timespec="seconds")


def decision_key(symbol: str, armed_at, entry: float, stop: float) -> str:
    """Deterministic across desk rebuilds. Same bar, same levels: same decision."""
    raw = f"{symbol}|{_et(armed_at)}|{round(entry, 4)}|{round(stop, 4)}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _json(obj) -> str:
    if is_dataclass(obj) and not isinstance(obj, type):
        obj = asdict(obj)
    return json.dumps(obj, default=_coerce, sort_keys=True)


def _coerce(o):
    if hasattr(o, "value"):          # Enum
        return o.value
    if isinstance(o, datetime):
        return o.isoformat()
    return str(o)


# --------------------------------------------------------------- writes
def record_decision(conn: sqlite3.Connection, *, symbol: str, armed_at, plan,
                    cascade, inputs, snapshot: dict, session: str,
                    session_id: str = "", source_name: str = "",
                    data_status: str = "", bar_resolution: str = "1m",
                    source: str = "pullback",
                    float_quality: Optional[str] = None,
                    float_source: Optional[str] = None,
                    rules_hash: Optional[str] = None,
                    code_commit: Optional[str] = None) -> str:
    """One plan, one row. Returns the decision_id. Repeats are no-ops.

    `plan` is the detector's PullbackPlan (or anything with entry/stop/target
    /risk_share/reward_multiple/pullback_candles/volume_ok). `cascade` is the
    CascadeResult; `inputs` the Inputs it was evaluated on; `snapshot` the
    point-in-time values as a plain dict (last, bid, ask, session_high,
    volume, rvol, change_pct).
    """
    did = decision_key(symbol, armed_at, plan.entry, plan.stop)
    bar_end = _bar_end(armed_at, bar_resolution)
    gates = [{"id": g.id, "state": getattr(g.state, "value", g.state),
              "value": g.value, "reason": g.reason, "kills": g.kills}
             for g in cascade.gates]
    outcome = "PENDING" if cascade.plan_allowed else "SUPPRESSED"
    cur = conn.execute("""
        INSERT INTO decisions (
            decision_id, ts_et, session, symbol, source, session_id, source_name,
            data_status, bar_resolution,
            last, bid, ask, session_high, volume, rvol, change_pct,
            float_shares, float_quality, float_source, catalyst, halted,
            verdict, killed_by, plan_allowed, gates_json, warnings_json, inputs_json,
            trigger, stop, target, risk_share, reward_multiple, pullback_candles,
            volume_ok, outcome, recorded_at, rules_hash, code_commit, bar_end_ts)
        VALUES (?,?,?,?,?,?,?,?,?, ?,?,?,?,?,?,?, ?,?,?,?,?, ?,?,?,?,?,?, ?,?,?,?,?,?,?, ?,?, ?,?, ?)
        ON CONFLICT(decision_id) DO UPDATE SET
            -- A row first seen during a STALE build is a fact about the FEED,
            -- not the name. The next LIVE build may replace it; nothing else
            -- may (audit 2026-09-08: first write won forever).
            data_status=excluded.data_status, last=excluded.last, bid=excluded.bid,
            ask=excluded.ask, session_high=excluded.session_high, volume=excluded.volume,
            rvol=excluded.rvol, change_pct=excluded.change_pct,
            verdict=excluded.verdict, killed_by=excluded.killed_by,
            plan_allowed=excluded.plan_allowed, gates_json=excluded.gates_json,
            warnings_json=excluded.warnings_json, inputs_json=excluded.inputs_json,
            outcome=excluded.outcome, recorded_at=excluded.recorded_at
        WHERE decisions.verdict='STALE' AND excluded.verdict<>'STALE'
              AND decisions.outcome IN ('SUPPRESSED','PENDING')
    """, (
        did, _et(armed_at), session, symbol, source, session_id, source_name,
        data_status, bar_resolution,
        snapshot.get("last"), snapshot.get("bid"), snapshot.get("ask"),
        snapshot.get("session_high"), snapshot.get("volume"), snapshot.get("rvol"),
        snapshot.get("change_pct"),
        inputs.float_shares, float_quality, float_source,
        int(bool(inputs.catalyst_today or inputs.live_theme)), int(bool(inputs.halted)),
        getattr(cascade.verdict, "value", cascade.verdict), cascade.killed_by,
        int(cascade.plan_allowed), _json(gates), _json(list(cascade.warnings)),
        _json(inputs),
        plan.entry, plan.stop, getattr(plan, "target", None),
        getattr(plan, "risk_share", None), getattr(plan, "reward_multiple", None),
        getattr(plan, "pullback_candles", None),
        int(bool(getattr(plan, "volume_ok", False))),
        outcome, _now(), rules_hash, code_commit, bar_end,
    ))
    if cur.rowcount == 1:
        # The row was inserted or actually updated: keep what it now says as an
        # immutable revision. A no-op conflict (the same plan re-armed by the
        # next rebuild) writes nothing here.
        conn.execute("""INSERT INTO decision_revisions (decision_id, recorded_at, data_status,
                            verdict, killed_by, plan_allowed, outcome, last, bid, ask,
                            gates_json, warnings_json, inputs_json)
                        SELECT decision_id, recorded_at, data_status, verdict, killed_by,
                               plan_allowed, outcome, last, bid, ask, gates_json, warnings_json,
                               inputs_json FROM decisions WHERE decision_id=?""", (did,))
    return did


def revisions(conn: sqlite3.Connection, decision_id: str) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM decision_revisions WHERE decision_id=? ORDER BY rev_id",
                        (decision_id,)).fetchall()


def record_board(conn: sqlite3.Connection, ts, session_id: str,
                 rows: Iterable[dict]) -> int:
    """R1. `rows`: dicts with symbol, verdict, killed_by, plan_allowed, last."""
    n = 0
    for r in rows:
        cur = conn.execute("""
            INSERT OR IGNORE INTO board_snapshots
              (ts_et, session_id, symbol, verdict, killed_by, plan_allowed, last, recorded_at)
            VALUES (?,?,?,?,?,?,?,?)""",
            (_et(ts), session_id, r["symbol"], r["verdict"], r.get("killed_by"),
             int(bool(r["plan_allowed"])), r.get("last"), _now()))
        n += cur.rowcount
    return n


def record_halt(conn: sqlite3.Connection, ts, symbol: str, status: str,
                last_before: Optional[float]) -> None:
    conn.execute("""INSERT OR IGNORE INTO halts (ts_et, symbol, status, last_before, recorded_at)
                    VALUES (?,?,?,?,?)""", (_et(ts), symbol, status, last_before, _now()))


def _bar_end(armed_at, bar_resolution) -> str:
    """The bar's close — the market-information clock. ts_et is the OPEN."""
    res = str(bar_resolution or "1m").strip().lower()
    secs = 60
    if res.endswith("s") and res[:-1].isdigit():
        secs = int(res[:-1])
    elif res.endswith("m") and res[:-1].isdigit():
        secs = int(res[:-1]) * 60
    ts = armed_at
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return _et(ts + timedelta(seconds=secs))


def set_outcome(conn: sqlite3.Connection, decision_id: str, outcome: str,
                reasons: Optional[list[str]] = None, clocks: Optional[dict] = None) -> None:
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome {outcome!r} not in {OUTCOMES}")
    conn.execute("""UPDATE decisions SET outcome=?, refusal_reasons_json=?, acted_at=?,
                    clocks_json=COALESCE(?, clocks_json) WHERE decision_id=?""",
                 (outcome, _json(reasons or []), _now(), _json(clocks) if clocks else None, decision_id))


def record_order(conn: sqlite3.Connection, decision_id: str, *, symbol: str,
                 account: str, session: str, parent_id: int, stop_id: Optional[int],
                 target_id: Optional[int], trigger: float, stop: float,
                 target: Optional[float], shares: int, dollar_risk: float,
                 protected: bool) -> int:
    cur = conn.execute("""
        INSERT INTO orders (decision_id, symbol, account, session, parent_id, stop_id,
            target_id, trigger, stop, target, shares, dollar_risk, planned_risk, protected,
            placed_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (decision_id, symbol, account, session, parent_id, stop_id, target_id,
         trigger, stop, target, shares, dollar_risk,
         round((trigger - stop) * shares, 2), int(protected), _now(), _now()))
    return int(cur.lastrowid)


def record_intent(conn: sqlite3.Connection, decision_id: str, *, symbol: str, session: str,
                  trigger: float, stop: float, target: Optional[float], shares: int,
                  dollar_risk: float, rules_hash: Optional[str] = None,
                  code_commit: Optional[str] = None) -> int:
    """The durable intent, written and COMMITTED before anything is sent.

    Audit 2026-09-08 F4: a ledger row written after the send is not an
    atomic transaction with the broker. If the process dies between the
    broker's acceptance and the row, the decision was still PENDING and a
    restarted runner would place it again. Now the decision is CLAIMED and
    an orders row exists with status 'intent' before `placeOrder`; a row
    still 'intent' after a restart is reconciled against the broker by its
    orderRef, and never resent."""
    cur = conn.execute("""
        INSERT INTO orders (decision_id, symbol, account, session, parent_id, stop_id,
            target_id, trigger, stop, target, shares, dollar_risk, planned_risk, protected,
            status, rules_hash, code_commit, placed_at, updated_at)
        VALUES (?,?,?,?,NULL,NULL,NULL,?,?,?,?,?,?,0,'intent',?,?,?,?)""",
        (decision_id, symbol, "", session, trigger, stop, target, shares, dollar_risk,
         round((trigger - stop) * shares, 2), rules_hash, code_commit, _now(), _now()))
    conn.execute("UPDATE decisions SET outcome='CLAIMED', acted_at=? WHERE decision_id=?",
                 (_now(), decision_id))
    return int(cur.lastrowid)


def set_order_ids(conn: sqlite3.Connection, order_id: int, *, parent_id: int,
                  stop_id: Optional[int], target_id: Optional[int], account: str,
                  protected: bool, status: str = "submitted",
                  perm_id: Optional[int] = None, stop_status: Optional[str] = None) -> None:
    """The broker's acknowledgement, written against the intent. A pre-market
    entry carries stop_status 'monitored' from the send: the runner is its
    stop, and `open_monitored` must find the row even before the fill syncs."""
    conn.execute("""UPDATE orders SET parent_id=?, stop_id=?, target_id=?, account=?, protected=?,
                    status=?, perm_id=COALESCE(?, perm_id), stop_status=COALESCE(?, stop_status),
                    updated_at=? WHERE order_id=?""",
                 (parent_id, stop_id, target_id, account, int(protected), status, perm_id,
                  stop_status, _now(), order_id))


def intents(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Rows written before a send whose acknowledgement was never saved."""
    return conn.execute("SELECT * FROM orders WHERE status='intent' ORDER BY placed_at").fetchall()


def mark_unresolved(conn: sqlite3.Connection, order_id: int, text: str) -> None:
    """An intent that cannot be matched at the broker. It blocks new entries
    (the one-position rule counts it) and it is NEVER resent; a human looks."""
    row = conn.execute("SELECT decision_id FROM orders WHERE order_id=?", (order_id,)).fetchone()
    if row is None:
        raise KeyError(order_id)
    conn.execute("UPDATE orders SET status='UNRESOLVED', stop_status=?, updated_at=? WHERE order_id=?",
                 (MANUAL, _now(), order_id))
    conn.execute("UPDATE decisions SET outcome='UNRESOLVED', acted_at=? WHERE decision_id=?",
                 (_now(), row["decision_id"]))
    add_order_event(conn, order_id, text)


def record_fill(conn: sqlite3.Connection, order_id: int, *, fill_price: float,
                fill_ts, nbbo: Optional[dict] = None, status: str = "Filled",
                stop_status: Optional[str] = None,
                protected: Optional[bool] = None) -> None:
    """R3 realised and R4 NBBO, in one write so they cannot drift apart."""
    row = conn.execute("SELECT stop, shares, planned_risk FROM orders WHERE order_id=?",
                       (order_id,)).fetchone()
    if row is None:
        raise KeyError(order_id)
    realised = round((fill_price - row["stop"]) * row["shares"], 2)
    ratio = round(realised / row["planned_risk"], 4) if row["planned_risk"] > 0 else None
    nbbo = nbbo or {}
    conn.execute("""
        UPDATE orders SET fill_price=?, fill_ts=?, realised_risk=?, slippage_ratio=?,
            nbbo_bid=?, nbbo_ask=?, nbbo_bid_size=?, nbbo_ask_size=?, nbbo_ts=?, nbbo_source=?,
            status=?, stop_status=COALESCE(?, stop_status),
            protected=COALESCE(?, protected), updated_at=?
        WHERE order_id=?""",
        (fill_price, _et(fill_ts), realised, ratio,
         nbbo.get("bid"), nbbo.get("ask"), nbbo.get("bid_size"), nbbo.get("ask_size"),
         _et(nbbo["ts"]) if nbbo.get("ts") else None, nbbo.get("source"),
         status, stop_status, None if protected is None else int(protected), _now(),
         order_id))


def set_protection(conn: sqlite3.Connection, order_id: int, *, stop_status: Optional[str],
                   protected: bool) -> bool:
    """Persist the stop leg's CURRENT state on a filled row. Until 2026-09-08
    the ledger kept the state seen at the first fill, so a stop cancelled
    later still read healthy (review round 2). Returns True when it changed."""
    row = conn.execute("SELECT stop_status, protected FROM orders WHERE order_id=?", (order_id,)).fetchone()
    if row is None:
        raise KeyError(order_id)
    if row["stop_status"] == stop_status and bool(row["protected"]) == bool(protected):
        return False
    if row["stop_status"] in (MANUAL, "monitored") and stop_status in (None, ""):
        return False                      # a monitored/flagged row has no broker stop to report
    conn.execute("UPDATE orders SET stop_status=?, protected=?, updated_at=? WHERE order_id=?",
                 (stop_status, int(protected), _now(), order_id))
    add_order_event(conn, order_id, f"stop leg now {stop_status!r}; protected={int(protected)}"
                    + ("" if protected else " — position has NO working stop at the broker"))
    return True


def exit_failed(conn: sqlite3.Connection, order_id: int, *, status: str) -> None:
    """The sell that was sent did not work (cancelled, inactive, rejected).
    The row is ExitFailed: still a position, flagged for a human, counted by
    the one-position rule, and never resent by code (review round 2)."""
    conn.execute("UPDATE orders SET status='ExitFailed', stop_status=?, updated_at=? WHERE order_id=?",
                 (MANUAL, _now(), order_id))
    add_order_event(conn, order_id, f"exit order {status}: the position is STILL HELD — a human must exit it "
                                    f"(exercise.py stuck / ah-exit); nothing is resent automatically")


def refresh_fill(conn: sqlite3.Connection, order_id: int, *, fill_price: float,
                 filled_qty: Optional[float]) -> bool:
    """A later partial fill moved the average price or the quantity: the
    realised risk is (avg fill − stop) × shares actually held, and the row
    says so (review round 2). Returns True when anything changed."""
    row = conn.execute("SELECT fill_price, filled_qty, stop, shares, planned_risk FROM orders WHERE order_id=?",
                       (order_id,)).fetchone()
    if row is None:
        raise KeyError(order_id)
    if row["fill_price"] == fill_price and (filled_qty is None or row["filled_qty"] == filled_qty):
        return False
    qty = filled_qty if filled_qty else (row["filled_qty"] or row["shares"])
    realised = round((fill_price - row["stop"]) * qty, 2)
    ratio = round(realised / row["planned_risk"], 4) if row["planned_risk"] else None
    conn.execute("""UPDATE orders SET fill_price=?, filled_qty=COALESCE(?, filled_qty), realised_risk=?,
                    slippage_ratio=?, updated_at=? WHERE order_id=?""",
                 (fill_price, filled_qty, realised, ratio, _now(), order_id))
    add_order_event(conn, order_id, f"fill updated: avg {fill_price} × {qty:g} — realised risk {realised}")
    return True


def record_exit(conn: sqlite3.Connection, order_id: int, *, reason: str,
                price: Optional[float], ts, confirmed_by: Optional[str] = None,
                confirmed: bool = True, exit_order_id: Optional[int] = None) -> None:
    """The trade's end. `confirmed=True` is a fill IBKR reported (a stop or
    target leg read back). `confirmed=False` is a sell that was SENT — the
    monitored stop, the hard-stop flatten, the after-hours exit — and the
    row reads ExitPending until `confirm_exit` writes the fill. The limit
    price of a sent order is a plan; the ledger must not call it a fill."""
    status = "Closed" if confirmed else "ExitPending"
    conn.execute("""UPDATE orders SET exit_reason=?, exit_price=?, exit_ts=?,
                    exit_confirmed_by=?, exit_order_id=COALESCE(?, exit_order_id),
                    status=?, updated_at=? WHERE order_id=?""",
                 (reason, price, _et(ts), confirmed_by, exit_order_id, status, _now(), order_id))


def confirm_exit(conn: sqlite3.Connection, order_id: int, *, price: float, ts) -> None:
    """The broker reported the pending exit filled: the real price, Closed."""
    conn.execute("""UPDATE orders SET exit_price=?, exit_ts=?, status='Closed', updated_at=?
                    WHERE order_id=? AND status='ExitPending'""",
                 (price, _et(ts), _now(), order_id))


def pending_exits(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM orders WHERE status='ExitPending'").fetchall()


def record_actuals(conn: sqlite3.Connection, decision_id: str, a: dict) -> None:
    cols = ["ref_price", "risk_share", "h5", "l5", "c5", "h15", "l15", "c15",
            "h30", "l30", "c30", "h60", "l60", "c60", "h_close", "l_close", "c_close",
            "mfe_r_planned", "mae_r_planned", "stop_hit", "stop_hit_ts",
            "target_hit", "target_hit_ts", "first_hit", "trigger_hit", "trigger_hit_ts",
            "bars_available"]
    conn.execute(
        f"INSERT OR REPLACE INTO actuals (decision_id, {', '.join(cols)}, computed_at) "
        f"VALUES (?, {', '.join('?' * len(cols))}, ?)",
        (decision_id, *[a.get(c) for c in cols], _now()))


# ---------------------------------------------------------------- reads
def pending(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Plan-allowed decisions the runner has not acted on, oldest first."""
    return conn.execute("""SELECT * FROM decisions WHERE outcome='PENDING' AND plan_allowed=1
                           ORDER BY ts_et""").fetchall()


def decisions(conn: sqlite3.Connection, **where: Any) -> list[sqlite3.Row]:
    sql, args = "SELECT * FROM decisions", []
    if where:
        sql += " WHERE " + " AND ".join(f"{k}=?" for k in where)
        args = list(where.values())
    return conn.execute(sql + " ORDER BY ts_et", args).fetchall()


def without_actuals(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("""SELECT d.* FROM decisions d LEFT JOIN actuals a USING(decision_id)
                           WHERE a.decision_id IS NULL ORDER BY d.ts_et""").fetchall()


def funnel(conn: sqlite3.Connection) -> dict:
    """The denominator at every stage. Never a survivor count on its own."""
    q = lambda sql: conn.execute(sql).fetchone()[0]           # noqa: E731
    return {
        "board_rows": q("SELECT COUNT(*) FROM board_snapshots"),
        "board_symbols": q("SELECT COUNT(DISTINCT symbol) FROM board_snapshots"),
        "board_plan_allowed": q("SELECT COUNT(*) FROM board_snapshots WHERE plan_allowed=1"),
        "plans_armed": q("SELECT COUNT(*) FROM decisions"),
        # Backfill: armed on bars older than the desk's start, with inputs from
        # later. Diagnostic cohort; never prospective evidence (audit F3).
        "plans_backfill": q("SELECT COUNT(*) FROM decisions WHERE data_status LIKE '%-backfill'"),
        "plans_prospective": q("SELECT COUNT(*) FROM decisions WHERE data_status IS NULL "
                               "OR data_status NOT LIKE '%-backfill'"),
        "plans_suppressed": q("SELECT COUNT(*) FROM decisions WHERE outcome='SUPPRESSED'"),
        "plans_allowed": q("SELECT COUNT(*) FROM decisions WHERE plan_allowed=1"),
        "refused_by_executor": q("SELECT COUNT(*) FROM decisions WHERE outcome='REFUSED'"),
        "log_only": q("SELECT COUNT(*) FROM decisions WHERE outcome='LOG_ONLY'"),
        "taken": q("SELECT COUNT(*) FROM decisions WHERE outcome='TAKEN'"),
        "orders": q("SELECT COUNT(*) FROM orders"),
        "orders_unresolved": q("SELECT COUNT(*) FROM orders WHERE status IN ('intent','UNRESOLVED')"),
        "fills": q("SELECT COUNT(*) FROM orders WHERE fill_price IS NOT NULL"),
        "fills_with_nbbo": q("SELECT COUNT(*) FROM orders WHERE fill_price IS NOT NULL AND nbbo_bid IS NOT NULL"),
        "actuals": q("SELECT COUNT(*) FROM actuals"),
        "halts": q("SELECT COUNT(*) FROM halts"),
        # Every allowed decision, by the word the runner (or the close-out)
        # left on it. The sum equals plans_allowed by construction; the
        # report prints the residual so a reader never has to subtract.
        "allowed_by_outcome": {r["outcome"]: r["n"] for r in conn.execute(
            "SELECT outcome, COUNT(*) AS n FROM decisions WHERE plan_allowed=1 "
            "GROUP BY outcome ORDER BY outcome")},
    }


def mark_defect(conn: sqlite3.Connection, order_id: int, note: str, *, by: str) -> None:
    """A human names a fill whose EXIT was a code defect's, not the rule's
    (owner decision 2026-09-22: DCOY x41 exited at the restart price after the
    OCA modify killed its stop; GRML x62 sold by hand after the flatten was
    refused). Such a row stays in every P&L and R figure — the loss was real
    — but is excluded from the A3 kill-rule comparison, which judges the
    exit RULE. The note and the name are written into the row."""
    row = conn.execute("SELECT order_id FROM orders WHERE order_id=?", (order_id,)).fetchone()
    if row is None:
        raise KeyError(order_id)
    conn.execute("UPDATE orders SET defect_note=?, updated_at=? WHERE order_id=?",
                 (f"{note} — marked by {by} {_now()}", _now(), order_id))
    add_order_event(conn, order_id, f"exit marked as a DEFECT exit by {by}: {note}; excluded from the A3 "
                                    f"kill-rule comparison, kept in every P&L figure")


def clean_closed_fills(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Closed fills whose exit was the rule's: a broker-confirmed exit with a
    reason, no defect note. The rows the A3 kill rule is read on."""
    return conn.execute("""SELECT * FROM orders WHERE fill_price IS NOT NULL AND status='Closed'
                           AND exit_price IS NOT NULL AND defect_note IS NULL
                           AND exit_reason IN ('stop', 'trail', 'target', 'hard_stop', 'stop_enforced')
                           ORDER BY fill_ts""").fetchall()


def unprotected_fills(conn: sqlite3.Connection, since: Optional[str] = None) -> int:
    """Filled entries that lost their protection, counted from `since` (an
    ISO instant, the owner's reset after a named defect fix) or from the
    start of the ledger. The B→C gate's count."""
    if since:
        return conn.execute("SELECT COUNT(*) FROM orders WHERE protected=0 AND fill_price IS NOT NULL "
                            "AND fill_ts > ?", (since,)).fetchone()[0]
    return conn.execute("SELECT COUNT(*) FROM orders WHERE protected=0 AND fill_price IS NOT NULL").fetchone()[0]


def reconciled_lifecycles(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Orders that went the whole way and every step is the broker's word:
    a fill IBKR reported, a protective stop leg that existed at the broker
    (stop_id), an exit IBKR reported filled (status Closed with a price —
    never a sent-but-unconfirmed ExitPending), and no human flag on the row.
    The B→C readiness gate (review 2026-09-21, item 11) needs at least one.
    A monitored (stop-less) entry does not qualify however it ended."""
    return conn.execute("""SELECT * FROM orders WHERE fill_price IS NOT NULL AND stop_id IS NOT NULL
                           AND protected=1 AND status='Closed' AND exit_price IS NOT NULL
                           AND exit_reason IN ('stop', 'trail', 'target', 'hard_stop', 'stop_enforced')
                           AND COALESCE(stop_status, '') <> ?""", (MANUAL,)).fetchall()


def r0_violations(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """R0 = quantity × |fill − INITIAL stop| is the only realised-risk
    denominator (review 2026-09-21, item 8). A trailed stop (A3) moves
    `trail_stop`, never `stop`, and `record_fill` / `refresh_fill` divide by
    `stop`; this lists any filled row whose stored realised_risk disagrees
    with that arithmetic, so a future change that redefined R shows up in
    the report instead of in a mean."""
    out = []
    for r in conn.execute("SELECT order_id, symbol, fill_price, stop, shares, filled_qty, realised_risk "
                          "FROM orders WHERE fill_price IS NOT NULL"):
        qty = r["filled_qty"] if r["filled_qty"] else r["shares"]
        expect = round((r["fill_price"] - r["stop"]) * qty, 2)
        if r["realised_risk"] is None or abs(r["realised_risk"] - expect) > 0.011:
            out.append(r)
    return out


def reconcile_allowed(conn: sqlite3.Connection) -> dict:
    """plans_allowed against the sum of its outcomes. `residual` is the
    number of allowed decisions carrying an outcome outside OUTCOMES — zero
    unless the schema and the code have drifted apart."""
    f = funnel(conn)
    by = f["allowed_by_outcome"]
    known = sum(n for k, n in by.items() if k in OUTCOMES)
    return {"allowed": f["plans_allowed"], "by_outcome": by,
            "residual": f["plans_allowed"] - known}


def expire_pending(conn: sqlite3.Connection, day: str) -> int:
    """Close-out: an allowed plan still PENDING for `day` (ET date) was
    armed while no runner was alive to judge it. Name it EXPIRED so it is
    neither re-offered tomorrow nor counted as a trade that was refused."""
    cur = conn.execute("""UPDATE decisions SET outcome='EXPIRED', acted_at=?,
                              refusal_reasons_json=?
                          WHERE outcome='PENDING' AND plan_allowed=1 AND substr(ts_et,1,10)=?""",
                       (_now(), _json(["no runner was alive to act on this plan before the close-out"]), day))
    conn.commit()
    return cur.rowcount



# ----------------------------------------------------------- the tape
def record_bars(conn: sqlite3.Connection, bars_by_symbol: dict) -> int:
    """bars_by_symbol: symbol -> iterable of (ts, o, h, l, c, v[, bid, ask])."""
    before = conn.execute("SELECT COUNT(*) FROM bars").fetchone()[0]
    for sym, rows in bars_by_symbol.items():
        for r in rows:
            bid, ask = (r[6], r[7]) if len(r) >= 8 else (None, None)
            conn.execute(
                # UPSERT, replacing only when the new aggregate carries at least
                # as much volume. The live desk hands the builder the CURRENT
                # minute mid-way; INSERT OR IGNORE froze that first partial
                # aggregate forever and every actual was computed on a
                # truncated tape (audit 2026-09-08).
                "INSERT INTO bars (symbol, ts, open, high, low, close, volume, bid, ask) "
                "VALUES (?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(symbol, ts) DO UPDATE SET open=excluded.open, high=excluded.high, "
                "low=excluded.low, close=excluded.close, volume=excluded.volume, "
                "bid=COALESCE(excluded.bid, bars.bid), ask=COALESCE(excluded.ask, bars.ask) "
                "WHERE excluded.volume >= bars.volume",
                (sym, r[0], r[1], r[2], r[3], r[4], r[5], bid, ask))
    return conn.execute("SELECT COUNT(*) FROM bars").fetchone()[0] - before


def record_bars_10s(conn: sqlite3.Connection, bars) -> int:
    """Persist closed 10-second candles. `bars` is an iterable of objects with
    symbol/ts/open/high/low/close/volume, or of (symbol, ts, o, h, l, c, v).

    INSERT OR IGNORE, not UPSERT: a 10-second candle is only ever emitted once
    and already closed, unlike the 1-minute aggregate the builder re-sends
    mid-minute. Returns the number of rows actually added.
    """
    before = conn.execute("SELECT COUNT(*) FROM bars_10s").fetchone()[0]
    for b in bars:
        if isinstance(b, (tuple, list)):
            sym, ts, o, h, l, c, v = b[0], b[1], b[2], b[3], b[4], b[5], b[6]
        else:
            sym, o, h, l, c, v = b.symbol, b.open, b.high, b.low, b.close, b.volume
            ts = b.ts
        if hasattr(ts, "isoformat"):
            ts = ts.isoformat().replace("+00:00", "Z")
        conn.execute(
            "INSERT OR IGNORE INTO bars_10s (symbol, ts, open, high, low, close, volume) "
            "VALUES (?,?,?,?,?,?,?)", (sym, str(ts), o, h, l, c, v))
    return conn.execute("SELECT COUNT(*) FROM bars_10s").fetchone()[0] - before


def bars_10s_from_ledger(conn, symbol: str | None = None) -> dict:
    """symbol -> [(ts, o, h, l, c, v)], the same shape as journal.bars."""
    from collections import defaultdict
    out = defaultdict(list)
    q = "SELECT symbol, ts, open, high, low, close, volume FROM bars_10s"
    args: tuple = ()
    if symbol:
        q += " WHERE symbol = ?"
        args = (symbol,)
    for r in conn.execute(q + " ORDER BY symbol, ts", args):
        out[r["symbol"]].append((r["ts"], r["open"], r["high"], r["low"], r["close"], r["volume"]))
    return dict(out)


def record_quotes(conn: sqlite3.Connection, quotes: dict) -> None:
    """quotes: symbol -> {bid, ask, bid_size, ask_size, ts}. `quotes` keeps the
    latest per symbol; every CHANGE is appended to `quote_ticks` so a fill can
    be joined to the quote in force at its execution time."""
    for sym, q in quotes.items():
        if q.get("bid") is None and q.get("ask") is None:
            continue
        ts = q.get("ts") or _now()
        prev = conn.execute("SELECT bid, ask, bid_size, ask_size, ts FROM quotes WHERE symbol=?",
                            (sym,)).fetchone()
        changed = prev is None or (prev["bid"], prev["ask"], prev["bid_size"], prev["ask_size"], prev["ts"]) != \
            (q.get("bid"), q.get("ask"), q.get("bid_size"), q.get("ask_size"), ts)
        conn.execute(
            "INSERT OR REPLACE INTO quotes (symbol, bid, ask, bid_size, ask_size, ts, recorded_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (sym, q.get("bid"), q.get("ask"), q.get("bid_size"), q.get("ask_size"), ts, _now()))
        if changed:
            conn.execute(
                "INSERT INTO quote_ticks (symbol, ts, bid, ask, bid_size, ask_size, recorded_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (sym, _et(ts), q.get("bid"), q.get("ask"), q.get("bid_size"), q.get("ask_size"), _now()))


def nbbo_at(conn: sqlite3.Connection, symbol: str, ts, max_age_s: int = 30):
    """The desk's quote in force at `ts`: the latest tick at or before it, if
    not older than max_age_s. None otherwise — an absent NBBO is recorded as
    absent, never replaced by a later one (R4)."""
    at = _et(ts)
    r = conn.execute("""SELECT * FROM quote_ticks WHERE symbol=? AND ts<=? ORDER BY ts DESC LIMIT 1""",
                     (symbol, at)).fetchone()
    if r is None:
        return None
    age = (datetime.fromisoformat(at) - datetime.fromisoformat(r["ts"])).total_seconds()
    if age > max_age_s:
        return None
    return {"bid": r["bid"], "ask": r["ask"], "bid_size": r["bid_size"], "ask_size": r["ask_size"],
            "ts": r["ts"], "source": "exec_time_join", "age_s": round(age, 1)}


def quote_source(conn: sqlite3.Connection, max_age_s: int = 30):
    """A `quote(symbol)` callable for the runner, reading the desk's latest.

    Returns None when the quote is older than max_age_s — a stale NBBO
    recorded as if current is exactly the kind of plausible wrong number
    this repo exists to prevent. The runner then records the fill with no
    NBBO, and the report counts it as unverified rather than verified.
    """
    def quote(symbol: str):
        r = conn.execute("SELECT * FROM quotes WHERE symbol=?", (symbol,)).fetchone()
        if r is None:
            return None
        recorded = datetime.fromisoformat(r["recorded_at"])
        age = (datetime.now(timezone.utc) - recorded).total_seconds()
        if age > max_age_s:
            return None
        # recorded_at says when the desk WROTE the row; the desk rewrites it
        # on every rebuild, so a stalled feed keeps re-recording an old quote
        # with a fresh stamp. The quote's own ts must be recent too. The bound
        # is loose (the desk's ts may be the minute bar's start) but finite.
        try:
            qts = datetime.fromisoformat(str(r["ts"]).replace("Z", "+00:00"))
            if qts.tzinfo is None:
                qts = qts.replace(tzinfo=timezone.utc)
            if (recorded - qts).total_seconds() > max(120, 4 * max_age_s):
                return None
        except (TypeError, ValueError):
            pass
        return {"bid": r["bid"], "ask": r["ask"], "bid_size": r["bid_size"],
                "ask_size": r["ask_size"], "ts": r["ts"]}
    return quote


# ------------------------------------------------------- exercise state
def get_state(conn: sqlite3.Connection) -> dict:
    r = conn.execute("SELECT * FROM exercise_state WHERE key='state'").fetchone()
    if r is None:
        conn.execute("INSERT INTO exercise_state (key, updated_at) VALUES ('state', ?)", (_now(),))
        conn.commit()
        r = conn.execute("SELECT * FROM exercise_state WHERE key='state'").fetchone()
    return dict(r)


def set_state(conn: sqlite3.Connection, **fields) -> dict:
    allowed = {"phase", "sessions_done", "probe_verdict", "probe_date", "dollar_risk",
               "paper_data", "paper_data_date", "last_session_date",
               "a1_accepted", "a1_accepted_by", "a1_accepted_at", "code_commit", "rules_hash",
               "unprotected_reset_at", "unprotected_reset_by", "unprotected_reset_fix",
               "phase_c_opened_by", "phase_c_opened_at", "phase_c_opened_why"}
    bad = set(fields) - allowed
    if bad:
        raise ValueError(f"unknown state fields {sorted(bad)}")
    if "phase" in fields and fields["phase"] not in ("A", "B", "C", "D", "E"):
        raise ValueError(f"phase {fields['phase']!r} is not one of A-E")
    get_state(conn)
    sets = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE exercise_state SET {sets}, updated_at=? WHERE key='state'",
                 (*fields.values(), _now()))
    conn.commit()
    return get_state(conn)


def open_monitored(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Filled, un-exited orders with no resting stop. The runner's watch list."""
    return conn.execute("""SELECT * FROM orders WHERE protected=0 AND stop_status='monitored'
                           AND fill_price IS NOT NULL AND exit_ts IS NULL""").fetchall()


def open_protected(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Filled, un-exited orders whose stop rests at the broker: the trailing
    exit's list (A3). An exit already sent (ExitPending) is left alone."""
    return conn.execute("""SELECT * FROM orders WHERE stop_id IS NOT NULL AND protected=1
                           AND fill_price IS NOT NULL AND exit_ts IS NULL
                           AND status NOT IN ('Cancelled', 'ApiCancelled', 'Inactive', 'Closed',
                                              'NotFilled', 'ExitPending', 'ExitFailed')""").fetchall()


def set_trail(conn: sqlite3.Connection, order_id: int, *, trail_stop: Optional[float],
              high: Optional[float]) -> None:
    conn.execute("UPDATE orders SET trail_stop=COALESCE(?, trail_stop), "
                 "high_since_fill=COALESCE(?, high_since_fill), updated_at=? WHERE order_id=?",
                 (trail_stop, high, _now(), order_id))


def high_since(conn: sqlite3.Connection, symbol: str, since_ts) -> Optional[float]:
    """The highest print the desk recorded for `symbol` at or after `since_ts`:
    10-second bar highs and quote-tick bids, whichever is higher. None when
    the desk has written nothing since — the trail then waits rather than
    guessing. Timestamps are compared as instants; the ledger stores fills
    in ET and bars in UTC."""
    if since_ts is None:
        return None
    since = since_ts if isinstance(since_ts, datetime) else datetime.fromisoformat(str(since_ts).replace("Z", "+00:00"))
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    best: Optional[float] = None
    for table, col in (("bars_10s", "high"), ("quote_ticks", "bid")):
        for r in conn.execute(f"SELECT ts, {col} AS v FROM {table} WHERE symbol=? AND {col} IS NOT NULL",
                              (symbol,)).fetchall():
            try:
                ts = datetime.fromisoformat(str(r["ts"]).replace("Z", "+00:00"))
            except ValueError:
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= since and (best is None or r["v"] > best):
                best = float(r["v"])
    return best


def add_order_event(conn: sqlite3.Connection, order_id: int, text: str) -> None:
    conn.execute("INSERT INTO order_events (order_id, ts, text) VALUES (?,?,?)",
                 (order_id, _now(), text))



# --------------------------------------------------------- stuck positions
MANUAL = "MANUAL_CONFIRMATION_REQUIRED"


def stuck_orders(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Filled and not exited. After the hard-stop flatten there should be
    none; any that remain are the brief's third 'stuck' state."""
    return conn.execute("""SELECT * FROM orders WHERE fill_price IS NOT NULL
                           AND (exit_ts IS NULL OR status IN ('ExitPending', 'ExitFailed'))
                           ORDER BY placed_at""").fetchall()


def flag_manual(conn: sqlite3.Connection, order_id: int, text: str) -> None:
    """Mark a position as needing a human. Idempotent; the event is written once."""
    row = conn.execute("SELECT stop_status FROM orders WHERE order_id=?", (order_id,)).fetchone()
    if row is None:
        raise KeyError(order_id)
    if row["stop_status"] == MANUAL:
        return
    conn.execute("UPDATE orders SET stop_status=?, updated_at=? WHERE order_id=?",
                 (MANUAL, _now(), order_id))
    add_order_event(conn, order_id, text)



def trade_rows(conn: sqlite3.Connection) -> list[dict]:
    """Every filled order with its exit, oldest first: entry, exit, reason,
    who confirmed a manual exit, dollars and R. R is against the PLANNED
    risk (trigger − initial stop) × shares, the exercise's unit; the dollar
    figure uses the quantity actually filled. Rows still held carry exit
    None. Until 2026-09-22 neither `report` nor `review` printed this, and
    "how did the trades do" had no answer in any tool output."""
    rows = conn.execute("""SELECT order_id, symbol, fill_ts, fill_price, exit_ts, exit_price, exit_reason,
                                  exit_confirmed_by, status, shares, filled_qty, planned_risk, stop, trail_stop
                           FROM orders WHERE fill_price IS NOT NULL ORDER BY fill_ts""").fetchall()
    out = []
    for r in rows:
        qty = int(r["filled_qty"]) if r["filled_qty"] else int(r["shares"])
        closed = r["exit_price"] is not None and r["status"] not in ("ExitPending", "ExitFailed")
        pnl = round((r["exit_price"] - r["fill_price"]) * qty, 2) if closed else None
        rr = round(pnl / r["planned_risk"], 2) if closed and r["planned_risk"] else None
        # Stop slippage (2026-09-25, GRML: trailed stop 16.22, filled 15.99):
        # exit price minus the stop level in force, for stop-type exits; and
        # the median 1-minute range of the 30 bars before the fill — the
        # smallest stop the tape can honour (tape.py convention). Both are
        # measurements for the read-out; nothing refuses on them.
        level = max(float(r["stop"] or 0), float(r["trail_stop"] or 0)) or None
        slip = (round(r["exit_price"] - level, 4)
                if closed and level and (r["exit_reason"] or "") in ("stop", "trail", "stop_enforced", "monitored_stop", "bracket")
                else None)
        rps = (r["planned_risk"] / r["shares"]) if r["planned_risk"] and r["shares"] else None
        out.append({**dict(r), "qty": qty, "closed": closed, "pnl": pnl, "r": rr,
                    "stop_slip": slip, "stop_slip_r": round(slip / rps, 2) if slip is not None and rps else None,
                    "range30": median_range_before(conn, r["symbol"], r["fill_ts"]), "rps": rps})
    return out


def median_range_before(conn: sqlite3.Connection, symbol: str, fill_ts: Optional[str], n: int = 30) -> Optional[float]:
    """Median high−low of the last `n` 1-minute bars before `fill_ts`, from
    the ledger's own bars; None when fewer than 5 exist."""
    if not fill_ts:
        return None
    try:
        cut = datetime.fromisoformat(str(fill_ts).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None
    rows = conn.execute("""SELECT high, low FROM bars WHERE symbol=? AND ts < ? ORDER BY ts DESC LIMIT ?""",
                        (symbol, cut.isoformat().replace("+00:00", "Z"), n)).fetchall()
    ranges = sorted(float(h) - float(l) for h, l in rows if h is not None and l is not None)
    if len(ranges) < 5:
        return None
    m = len(ranges) // 2
    return round(ranges[m] if len(ranges) % 2 else (ranges[m - 1] + ranges[m]) / 2, 4)


def alignment_rows(conn: sqlite3.Connection) -> list[dict]:
    """Per fill: what the desk saw at the decision, what IBKR filled, what the
    desk saw at the fill, and the seconds between IBKR's fill stamp and the
    desk quote attached to it. This is the whole lag question, measured.

    The gap is computed in Python: the ledger stores ET ISO strings with a
    UTC offset, and SQLite's julianday() silently returns NULL on those.
    """
    rows = conn.execute("""
        SELECT o.order_id, o.symbol, o.session, d.ts_et AS decision_ts, d.bid AS d_bid, d.ask AS d_ask,
               o.trigger, o.fill_price, o.fill_ts, o.nbbo_bid, o.nbbo_ask, o.nbbo_ts,
               o.slippage_ratio, o.protected
        FROM orders o JOIN decisions d USING(decision_id)
        WHERE o.fill_price IS NOT NULL ORDER BY o.fill_ts""").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        gap = None
        if d["nbbo_ts"] and d["fill_ts"]:
            gap = int((datetime.fromisoformat(d["nbbo_ts"])
                       - datetime.fromisoformat(d["fill_ts"])).total_seconds())
        d["quote_gap_s"] = gap
        out.append(d)
    return out


def open_orders(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Orders that may still be alive at the broker: not exited, not cancelled.
    What a restarted runner must adopt before it can sync anything."""
    return conn.execute("""SELECT * FROM orders WHERE (exit_ts IS NULL OR status='ExitFailed')
                           AND status NOT IN ('Cancelled', 'ApiCancelled', 'Inactive', 'Closed', 'NotFilled',
                                              'intent', 'UNRESOLVED')
                           ORDER BY placed_at""").fetchall()


def positions_alive(conn: sqlite3.Connection) -> int:
    """How many orders could still become or be a position: resting, filled and
    not exited, an exit sent but unconfirmed, an intent whose acknowledgement
    was never saved, or an unresolved intent. The one-position rule
    (docs/preregistration.md §2) counts every one of these.

    `Inactive` is IBKR's word for REJECTED (error 201 — VEEE, 2026-09-21
    09:37, margin). It was not in the dead list, so the first order the
    exercise ever sent, refused by the broker inside a second, counted as a
    live position and blocked every entry for the rest of the session."""
    return conn.execute("""SELECT COUNT(*) FROM orders WHERE (exit_ts IS NULL OR status IN ('ExitPending', 'ExitFailed'))
                           AND status NOT IN ('Cancelled', 'ApiCancelled', 'Inactive', 'Closed', 'NotFilled')""").fetchone()[0]


DEAD_ENTRY_STATUSES = ("Inactive", "Cancelled", "ApiCancelled", "Rejected")


def mark_dead(conn: sqlite3.Connection, order_id: int, status: str, why: str) -> None:
    """An entry the broker reports dead (rejected, cancelled) or no longer
    reports at all: the row takes the broker's word and the decision reads
    NOT_FILLED. 2026-09-21: VEEE was rejected at 09:37 (error 201) and its
    row stayed 'submitted' all session — the runner only wrote fills back —
    so the one-position rule refused every entry until 11:28 on a position
    that never existed."""
    row = conn.execute("SELECT decision_id, status FROM orders WHERE order_id=?", (order_id,)).fetchone()
    if row is None:
        raise KeyError(order_id)
    conn.execute("UPDATE orders SET status=?, updated_at=? WHERE order_id=?", (status, _now(), order_id))
    add_order_event(conn, order_id, why)
    conn.execute("UPDATE decisions SET outcome='NOT_FILLED', acted_at=? WHERE decision_id=? "
                 "AND outcome IN ('TAKEN', 'CLAIMED')", (_now(), row["decision_id"]))


def mark_not_filled(conn: sqlite3.Connection, order_id: int) -> None:
    """An entry that never filled by the hard stop. The decision's outcome
    becomes NOT_FILLED — a different fact from TAKEN, and one the actuals
    still score, because 'the one that never filled' is a measurement too."""
    row = conn.execute("SELECT decision_id FROM orders WHERE order_id=?", (order_id,)).fetchone()
    if row is None:
        raise KeyError(order_id)
    conn.execute("UPDATE orders SET status='NotFilled', updated_at=? WHERE order_id=?",
                 (_now(), order_id))
    conn.execute("UPDATE decisions SET outcome='NOT_FILLED', acted_at=? WHERE decision_id=?",
                 (_now(), row["decision_id"]))



def set_perm_id(conn: sqlite3.Connection, order_id: int, perm_id: int) -> None:
    conn.execute("UPDATE orders SET perm_id=?, updated_at=? WHERE order_id=? AND perm_id IS NULL",
                 (perm_id, _now(), order_id))


def record_candidates(conn: sqlite3.Connection, ts, source: str, rows) -> int:
    """R1 before the desk: every gap-scan row, survivor or reject."""
    n = 0
    for r in rows:
        cur = conn.execute("""INSERT OR IGNORE INTO candidates
            (ts_et, source, symbol, verdict, reasons_json, price, gap_pct, float_shares, pm_volume, recorded_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (_et(ts), source, str(r.get("sym") or r.get("symbol") or "").upper(), r.get("verdict"),
             _json(r.get("reasons") or []), r.get("price") or r.get("last"), r.get("gap") or r.get("gap_pct"),
             r.get("float"), r.get("pm_vol"), _now()))
        n += cur.rowcount
    conn.commit()
    return n


def set_new_stop_leg(conn: sqlite3.Connection, order_id: int, *, stop_id: int, level: float,
                     qty: Optional[float]) -> None:
    """A fresh protective stop was placed for a held position (the old leg died
    or could not be modified). The row is protected again at `level`."""
    conn.execute("""UPDATE orders SET stop_id=?, trail_stop=CASE WHEN ? > stop THEN ? ELSE trail_stop END,
                    stop_status='Submitted', protected=1, stop_qty=COALESCE(?, stop_qty), updated_at=?
                    WHERE order_id=?""", (stop_id, level, level, qty, _now(), order_id))
    add_order_event(conn, order_id, f"new protective stop {stop_id} placed at {level}"
                    + (f" x{qty:g}" if qty else ""))


def unprotected_positions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Filled bracket rows still held whose stop leg is dead or flagged: the
    rows `Runner.reprotect` places a fresh stop for. Monitored (stop-less by
    design) rows are not included, nor ExitPending rows (a sell is working).
    An ExitFailed row IS included: the flatten cancelled its stop and then
    the sell was rejected (GRML x62, 2026-09-22), so it is a held position
    with no exit at all — the fresh stop protects it until a human sells."""
    return conn.execute("""SELECT * FROM orders WHERE fill_price IS NOT NULL
                           AND stop_id IS NOT NULL AND protected=0
                           AND ((exit_ts IS NULL AND status NOT IN ('Cancelled', 'ApiCancelled', 'Inactive',
                                                                    'Closed', 'NotFilled', 'ExitPending'))
                                OR status='ExitFailed')""").fetchall()


def set_stop_qty(conn: sqlite3.Connection, order_id: int, qty: float) -> None:
    conn.execute("UPDATE orders SET stop_qty=?, updated_at=? WHERE order_id=?", (qty, _now(), order_id))


def exit_quantity_gaps(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Filled, un-exited rows whose resting stop covers fewer shares than
    were filled. Every filled share needs its protective exit (item 13c)."""
    return conn.execute("""SELECT * FROM orders WHERE fill_price IS NOT NULL AND exit_ts IS NULL
                           AND filled_qty IS NOT NULL AND stop_qty IS NOT NULL AND stop_qty < filled_qty
                           AND status NOT IN ('Cancelled', 'ApiCancelled', 'Inactive', 'Closed', 'NotFilled')""").fetchall()


def set_filled_qty(conn: sqlite3.Connection, order_id: int, qty: float) -> None:
    conn.execute("UPDATE orders SET filled_qty=?, updated_at=? WHERE order_id=?", (qty, _now(), order_id))
