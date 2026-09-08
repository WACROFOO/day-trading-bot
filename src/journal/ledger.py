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
from datetime import datetime, timezone
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
OUTCOMES = ("PENDING", "TAKEN", "REFUSED", "NOT_FILLED", "LOG_ONLY", "SUPPRESSED")

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
                       ("last_session_date", "TEXT")),
    "orders": (("perm_id", "INTEGER"), ("symbol", "TEXT"), ("exit_confirmed_by", "TEXT"),
               ("filled_qty", "REAL"), ("exit_order_id", "INTEGER")),
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
                    float_source: Optional[str] = None) -> str:
    """One plan, one row. Returns the decision_id. Repeats are no-ops.

    `plan` is the detector's PullbackPlan (or anything with entry/stop/target
    /risk_share/reward_multiple/pullback_candles/volume_ok). `cascade` is the
    CascadeResult; `inputs` the Inputs it was evaluated on; `snapshot` the
    point-in-time values as a plain dict (last, bid, ask, session_high,
    volume, rvol, change_pct).
    """
    did = decision_key(symbol, armed_at, plan.entry, plan.stop)
    gates = [{"id": g.id, "state": getattr(g.state, "value", g.state),
              "value": g.value, "reason": g.reason, "kills": g.kills}
             for g in cascade.gates]
    outcome = "PENDING" if cascade.plan_allowed else "SUPPRESSED"
    conn.execute("""
        INSERT INTO decisions (
            decision_id, ts_et, session, symbol, source, session_id, source_name,
            data_status, bar_resolution,
            last, bid, ask, session_high, volume, rvol, change_pct,
            float_shares, float_quality, float_source, catalyst, halted,
            verdict, killed_by, plan_allowed, gates_json, warnings_json, inputs_json,
            trigger, stop, target, risk_share, reward_multiple, pullback_candles,
            volume_ok, outcome, recorded_at)
        VALUES (?,?,?,?,?,?,?,?,?, ?,?,?,?,?,?,?, ?,?,?,?,?, ?,?,?,?,?,?, ?,?,?,?,?,?,?, ?,?)
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
        outcome, _now(),
    ))
    return did


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


def set_outcome(conn: sqlite3.Connection, decision_id: str, outcome: str,
                reasons: Optional[list[str]] = None) -> None:
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome {outcome!r} not in {OUTCOMES}")
    conn.execute("""UPDATE decisions SET outcome=?, refusal_reasons_json=?, acted_at=?
                    WHERE decision_id=?""",
                 (outcome, _json(reasons or []), _now(), decision_id))


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
            nbbo_bid=?, nbbo_ask=?, nbbo_bid_size=?, nbbo_ask_size=?, nbbo_ts=?,
            status=?, stop_status=COALESCE(?, stop_status),
            protected=COALESCE(?, protected), updated_at=?
        WHERE order_id=?""",
        (fill_price, _et(fill_ts), realised, ratio,
         nbbo.get("bid"), nbbo.get("ask"), nbbo.get("bid_size"), nbbo.get("ask_size"),
         _et(nbbo["ts"]) if nbbo.get("ts") else None,
         status, stop_status, None if protected is None else int(protected), _now(),
         order_id))


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
        "plans_suppressed": q("SELECT COUNT(*) FROM decisions WHERE outcome='SUPPRESSED'"),
        "plans_allowed": q("SELECT COUNT(*) FROM decisions WHERE plan_allowed=1"),
        "refused_by_executor": q("SELECT COUNT(*) FROM decisions WHERE outcome='REFUSED'"),
        "log_only": q("SELECT COUNT(*) FROM decisions WHERE outcome='LOG_ONLY'"),
        "taken": q("SELECT COUNT(*) FROM decisions WHERE outcome='TAKEN'"),
        "orders": q("SELECT COUNT(*) FROM orders"),
        "fills": q("SELECT COUNT(*) FROM orders WHERE fill_price IS NOT NULL"),
        "fills_with_nbbo": q("SELECT COUNT(*) FROM orders WHERE fill_price IS NOT NULL AND nbbo_bid IS NOT NULL"),
        "actuals": q("SELECT COUNT(*) FROM actuals"),
        "halts": q("SELECT COUNT(*) FROM halts"),
    }



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


def record_quotes(conn: sqlite3.Connection, quotes: dict) -> None:
    """quotes: symbol -> {bid, ask, bid_size, ask_size, ts}. Overwrites."""
    for sym, q in quotes.items():
        if q.get("bid") is None and q.get("ask") is None:
            continue
        conn.execute(
            "INSERT OR REPLACE INTO quotes (symbol, bid, ask, bid_size, ask_size, ts, recorded_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (sym, q.get("bid"), q.get("ask"), q.get("bid_size"), q.get("ask_size"),
             q.get("ts") or _now(), _now()))


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
               "paper_data", "paper_data_date", "last_session_date"}
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


def add_order_event(conn: sqlite3.Connection, order_id: int, text: str) -> None:
    conn.execute("INSERT INTO order_events (order_id, ts, text) VALUES (?,?,?)",
                 (order_id, _now(), text))



# --------------------------------------------------------- stuck positions
MANUAL = "MANUAL_CONFIRMATION_REQUIRED"


def stuck_orders(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Filled and not exited. After the hard-stop flatten there should be
    none; any that remain are the brief's third 'stuck' state."""
    return conn.execute("""SELECT * FROM orders WHERE fill_price IS NOT NULL
                           AND (exit_ts IS NULL OR status='ExitPending')
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
    return conn.execute("""SELECT * FROM orders WHERE exit_ts IS NULL
                           AND status NOT IN ('Cancelled', 'ApiCancelled', 'Closed', 'NotFilled')
                           ORDER BY placed_at""").fetchall()


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


def set_filled_qty(conn: sqlite3.Connection, order_id: int, qty: float) -> None:
    conn.execute("UPDATE orders SET filled_qty=?, updated_at=? WHERE order_id=?", (qty, _now(), order_id))
