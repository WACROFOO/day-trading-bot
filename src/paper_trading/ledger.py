"""SQLite persistence for the paper-trading account.

DB lives at ``data/paper_trading.db`` (relative to the repo root) and is
created on first use. A single account tracks starting/current cash; every
fill is appended to ``trades`` and an equity snapshot per fill goes to
``equity_snapshots`` for the equity curve.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_STARTING_CASH = 10_000.0

# .../day-trading-bot/src/paper_trading/ledger.py -> repo root is parents[2]
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "paper_trading.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS account (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    starting_cash REAL NOT NULL,
    cash REAL NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    qty REAL NOT NULL,
    price REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS equity_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    trade_id INTEGER,
    equity REAL NOT NULL,
    cash REAL NOT NULL
);
"""


@dataclass
class Account:
    starting_cash: float
    cash: float
    created_at: str


def _connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DB_PATH
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_account(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT id FROM account WHERE id = 1").fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO account (id, starting_cash, cash, created_at) VALUES (1, ?, ?, ?)",
            (DEFAULT_STARTING_CASH, DEFAULT_STARTING_CASH, _utcnow()),
        )
        conn.commit()


def get_account(db_path: Path | str | None = None) -> Account:
    """Return the single account, creating it with default cash on first use."""
    with _connect(db_path) as conn:
        _ensure_account(conn)
        row = conn.execute("SELECT * FROM account WHERE id = 1").fetchone()
        return Account(row["starting_cash"], row["cash"], row["created_at"])


def reset_account(starting_cash: float = DEFAULT_STARTING_CASH,
                  db_path: Path | str | None = None) -> Account:
    """Wipe all trades/snapshots and restart with the given cash."""
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM trades")
        conn.execute("DELETE FROM equity_snapshots")
        conn.execute("DELETE FROM account")
        conn.execute(
            "INSERT INTO account (id, starting_cash, cash, created_at) VALUES (1, ?, ?, ?)",
            (starting_cash, starting_cash, _utcnow()),
        )
        conn.commit()
    return get_account(db_path)


def get_open_positions(db_path: Path | str | None = None) -> list[dict]:
    """Open long positions with average cost, derived from the trade log."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT symbol, side, qty, price FROM trades ORDER BY id"
        ).fetchall()
    positions: dict[str, dict] = {}
    for r in rows:
        p = positions.setdefault(r["symbol"], {"qty": 0.0, "cost": 0.0})
        if r["side"] == "BUY":
            p["cost"] += r["qty"] * r["price"]
            p["qty"] += r["qty"]
        else:
            if p["qty"] > 0:
                avg = p["cost"] / p["qty"]
                p["cost"] -= r["qty"] * avg
                p["qty"] -= r["qty"]
    out = []
    for sym, p in positions.items():
        if p["qty"] > 1e-9:
            out.append({
                "symbol": sym,
                "qty": p["qty"],
                "avg_cost": p["cost"] / p["qty"],
            })
    return out


def _positions_value(conn: sqlite3.Connection, prices: dict[str, float]) -> float:
    rows = conn.execute(
        "SELECT symbol, side, qty, price FROM trades ORDER BY id"
    ).fetchall()
    positions: dict[str, dict] = {}
    for r in rows:
        p = positions.setdefault(r["symbol"], {"qty": 0.0, "cost": 0.0})
        if r["side"] == "BUY":
            p["cost"] += r["qty"] * r["price"]
            p["qty"] += r["qty"]
        else:
            if p["qty"] > 0:
                avg = p["cost"] / p["qty"]
                p["cost"] -= r["qty"] * avg
                p["qty"] -= r["qty"]
    return sum(
        p["qty"] * prices.get(sym, p["cost"] / p["qty"])
        for sym, p in positions.items() if p["qty"] > 1e-9
    )


def record_fill(symbol: str, side: str, qty: float, price: float,
                current_prices: dict[str, float] | None = None,
                db_path: Path | str | None = None) -> int:
    """Record a fill, update cash, and snapshot equity.

    BUY reduces cash by qty*price; SELL increases it. Rejects sells larger
    than the open position (no shorting). Returns the trade id.
    """
    side = side.upper()
    if side not in ("BUY", "SELL"):
        raise ValueError(f"side must be BUY or SELL, got {side!r}")
    if qty <= 0 or price <= 0:
        raise ValueError("qty and price must be positive")
    symbol = symbol.upper()

    with _connect(db_path) as conn:
        _ensure_account(conn)
        if side == "SELL":
            open_qty = sum(
                (1 if t["side"] == "BUY" else -1) * t["qty"]
                for t in conn.execute(
                    "SELECT side, qty FROM trades WHERE symbol = ?", (symbol,)
                ).fetchall()
            )
            if qty > open_qty + 1e-9:
                raise ValueError(
                    f"cannot sell {qty} of {symbol}: only {open_qty} open"
                )
        acc = conn.execute("SELECT cash FROM account WHERE id = 1").fetchone()
        cash = acc["cash"] + (-qty * price if side == "BUY" else qty * price)
        if cash < -1e-9:
            raise ValueError("insufficient cash (no margin)")
        cur = conn.execute(
            "INSERT INTO trades (timestamp, symbol, side, qty, price) VALUES (?, ?, ?, ?, ?)",
            (_utcnow(), symbol, side, qty, price),
        )
        conn.execute("UPDATE account SET cash = ? WHERE id = 1", (cash,))
        prices = dict(current_prices or {})
        prices[symbol] = price
        equity = cash + _positions_value(conn, prices)
        conn.execute(
            "INSERT INTO equity_snapshots (timestamp, trade_id, equity, cash) VALUES (?, ?, ?, ?)",
            (_utcnow(), cur.lastrowid, equity, cash),
        )
        conn.commit()
        return cur.lastrowid


def get_trade_history(db_path: Path | str | None = None) -> list[dict]:
    """All fills, newest first."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM trades ORDER BY id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_daily_pnl(date: str, db_path: Path | str | None = None) -> dict:
    """Realized P&L and trade stats for a UTC date (``YYYY-MM-DD``).

    Matches buys to sells FIFO per symbol. Returns realized pnl, trade count,
    and per-symbol round-trip results (signed, newest-first irrelevant).
    """
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT symbol, side, qty, price FROM trades "
            "WHERE substr(timestamp, 1, 10) = ? ORDER BY id",
            (date,),
        ).fetchall()

    lots: dict[str, list[list[float]]] = {}
    realized = 0.0
    round_trips: list[float] = []
    for r in rows:
        sym = r["symbol"]
        q, px = r["qty"], r["price"]
        if r["side"] == "BUY":
            lots.setdefault(sym, []).append([q, px])
        else:
            trade_pnl = 0.0
            remaining = q
            while remaining > 1e-9 and lots.get(sym):
                lot = lots[sym][0]
                take = min(remaining, lot[0])
                trade_pnl += take * (px - lot[1])
                lot[0] -= take
                remaining -= take
                if lot[0] <= 1e-9:
                    lots[sym].pop(0)
            realized += trade_pnl
            round_trips.append(trade_pnl)
    return {
        "date": date,
        "realized_pnl": realized,
        "n_trades": len(rows),
        "n_sells": len(round_trips),
        "round_trips": round_trips,
    }


def get_equity_curve(db_path: Path | str | None = None) -> list[dict]:
    """Equity snapshots (one per fill), oldest first."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT timestamp, equity, cash FROM equity_snapshots ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]
