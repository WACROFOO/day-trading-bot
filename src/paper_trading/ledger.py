"""SQLite persistence for the paper-trading account.

DB lives at ``data/paper_trading.db`` (relative to the repo root) and is
created on first use. A single account tracks starting/current cash; every
fill is appended to ``trades`` and an equity snapshot per fill goes to
``equity_snapshots`` for the equity curve.

Schema v2 (migrated in place, non-destructively): ``trades`` gains
``commission``/``order_id``/``reason``, ``account`` gains
``equity_hwm``/``walkaway_locked``, and two tables are added — ``orders``
(order ticket lifecycle incl. bracket stops) and ``risk_day`` (per-day risk
gate latch state, keyed by America/New_York date).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

DEFAULT_STARTING_CASH = 10_000.0

# .../day-trading-bot/src/paper_trading/ledger.py -> repo root is parents[2]
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "paper_trading.db"

_ET = ZoneInfo("America/New_York")

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

_SCHEMA += """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY','SELL')),
    qty REAL NOT NULL,
    order_type TEXT NOT NULL CHECK (order_type IN ('MARKET','LIMIT','STOP')),
    limit_price REAL,
    stop_price REAL,
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','FILLED','CANCELED')),
    reason TEXT,
    filled_at TEXT,
    filled_price REAL
);
CREATE TABLE IF NOT EXISTS risk_day (
    date TEXT PRIMARY KEY,              -- America/New_York date, YYYY-MM-DD
    day_start_equity REAL NOT NULL,
    peak_pnl REAL NOT NULL DEFAULT 0,   -- intraday peak day P&L incl. unrealized
    was_green INTEGER NOT NULL DEFAULT 0,
    locked INTEGER NOT NULL DEFAULT 0,  -- latching: once 1, stays 1 until reset
    lock_reason TEXT,
    updated_at TEXT NOT NULL
);
"""

# Non-destructive column additions for databases created with schema v1.
_MIGRATIONS = [
    ("trades",  "commission", "ALTER TABLE trades ADD COLUMN commission REAL NOT NULL DEFAULT 0"),
    ("trades",  "order_id",   "ALTER TABLE trades ADD COLUMN order_id INTEGER"),
    ("trades",  "reason",     "ALTER TABLE trades ADD COLUMN reason TEXT"),
    ("account", "equity_hwm", "ALTER TABLE account ADD COLUMN equity_hwm REAL"),
    ("account", "walkaway_locked",
     "ALTER TABLE account ADD COLUMN walkaway_locked INTEGER NOT NULL DEFAULT 0"),
]


def _migrate(conn: sqlite3.Connection) -> None:
    """Apply pending column migrations. Idempotent: skips existing columns."""
    for table, col, ddl in _MIGRATIONS:
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if col not in cols:
            conn.execute(ddl)
    conn.commit()


@dataclass
class Account:
    starting_cash: float
    cash: float
    created_at: str


@dataclass
class RoundTrip:
    """One flat->open->flat cycle in a single symbol (avg-cost within cycle)."""
    symbol: str
    opened_at: str
    closed_at: str | None        # None = still open
    qty: float
    entry_avg: float             # average entry price (avg-cost within the cycle)
    exit_avg: float | None
    pnl: float                   # net of commissions, realized portion
    risk_per_share: float | None # entry_avg - stop of the linked entry order, if known


def _connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DB_PATH
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    _migrate(conn)
    return conn


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _et_date(iso_ts: str) -> str:
    """ET calendar date (YYYY-MM-DD) of an ISO timestamp; naive = assumed UTC."""
    dt = datetime.fromisoformat(iso_ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_ET).date().isoformat()


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
    """Wipe all trades/snapshots/orders/risk state and restart with the given cash."""
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM trades")
        conn.execute("DELETE FROM equity_snapshots")
        conn.execute("DELETE FROM orders")
        conn.execute("DELETE FROM risk_day")
        conn.execute("DELETE FROM account")
        # Re-insert relies on column defaults: equity_hwm NULL, walkaway_locked 0.
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


def record_fill(symbol: str, side: str, qty: float, price: float, *,
                commission: float = 0.0, order_id: int | None = None,
                reason: str | None = None,
                current_prices: dict[str, float] | None = None,
                db_path: Path | str | None = None) -> int:
    """Record a fill, update cash, and snapshot equity.

    BUY reduces cash by qty*price + commission; SELL increases it by
    qty*price - commission. Rejects sells larger than the open position (no
    shorting) and buys the account cannot afford incl. commission (no
    margin). Returns the trade id.
    """
    side = side.upper()
    if side not in ("BUY", "SELL"):
        raise ValueError(f"side must be BUY or SELL, got {side!r}")
    if qty <= 0 or price <= 0:
        raise ValueError("qty and price must be positive")
    if commission < 0:
        raise ValueError("commission must be non-negative")
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
        cash = acc["cash"] + (-qty * price - commission if side == "BUY"
                              else qty * price - commission)
        if cash < -1e-9:
            raise ValueError("insufficient cash (no margin)")
        cur = conn.execute(
            "INSERT INTO trades (timestamp, symbol, side, qty, price, commission,"
            " order_id, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (_utcnow(), symbol, side, qty, price, commission, order_id, reason),
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


def get_round_trips(db_path: Path | str | None = None) -> list[RoundTrip]:
    """Replay the full trade log into flat->open->flat cycles per symbol.

    Avg-cost within a cycle (FIFO lot matching is unnecessary once cycles
    are flat-to-flat). Commissions are summed into ``pnl``. A scale-out
    (partial exits) is one cycle, so it counts as a single round trip.
    Closed trips are returned in close order; any still-open cycle comes
    last with ``closed_at=None`` and ``pnl`` = realized portion so far.
    """
    with _connect(db_path) as conn:
        trades = conn.execute(
            "SELECT id, timestamp, symbol, side, qty, price, commission, order_id"
            " FROM trades ORDER BY id"
        ).fetchall()
        stop_by_order = {
            r["id"]: r["stop_price"]
            for r in conn.execute(
                "SELECT id, stop_price FROM orders WHERE stop_price IS NOT NULL"
            ).fetchall()
        }

    def _fresh() -> dict:
        return {"qty": 0.0, "cost": 0.0, "buy_qty": 0.0, "buy_cost": 0.0,
                "sell_qty": 0.0, "sell_value": 0.0, "pnl": 0.0,
                "opened_at": None, "first_buy_order_id": None}

    cycles: dict[str, dict] = {}
    trips: list[RoundTrip] = []
    for t in trades:
        sym = t["symbol"]
        c = cycles.setdefault(sym, _fresh())
        if t["side"] == "BUY":
            if c["buy_qty"] == 0 and c["qty"] <= 1e-9:  # first buy of a cycle
                c["opened_at"] = t["timestamp"]
                c["first_buy_order_id"] = t["order_id"]
            c["qty"] += t["qty"]
            c["cost"] += t["qty"] * t["price"]
            c["buy_qty"] += t["qty"]
            c["buy_cost"] += t["qty"] * t["price"]
            c["pnl"] -= t["commission"]
        else:
            if c["qty"] <= 1e-9:
                continue  # sell with no open cycle (defensive; ledger forbids)
            avg = c["cost"] / c["qty"]
            c["pnl"] += t["qty"] * (t["price"] - avg) - t["commission"]
            c["cost"] -= t["qty"] * avg
            c["qty"] -= t["qty"]
            c["sell_qty"] += t["qty"]
            c["sell_value"] += t["qty"] * t["price"]
            if c["qty"] <= 1e-9:  # cycle closed flat
                entry_avg = c["buy_cost"] / c["buy_qty"]
                stop = stop_by_order.get(c["first_buy_order_id"])
                trips.append(RoundTrip(
                    symbol=sym,
                    opened_at=c["opened_at"],
                    closed_at=t["timestamp"],
                    qty=c["buy_qty"],
                    entry_avg=entry_avg,
                    exit_avg=c["sell_value"] / c["sell_qty"],
                    pnl=c["pnl"],
                    risk_per_share=(entry_avg - stop) if stop is not None else None,
                ))
                cycles[sym] = _fresh()
    for sym, c in cycles.items():
        if c["qty"] > 1e-9:  # still-open cycle
            entry_avg = c["buy_cost"] / c["buy_qty"]
            stop = stop_by_order.get(c["first_buy_order_id"])
            trips.append(RoundTrip(
                symbol=sym,
                opened_at=c["opened_at"],
                closed_at=None,
                qty=c["buy_qty"],
                entry_avg=entry_avg,
                exit_avg=None,
                pnl=c["pnl"],
                risk_per_share=(entry_avg - stop) if stop is not None else None,
            ))
    return trips


def get_daily_pnl(date: str, db_path: Path | str | None = None) -> dict:
    """Realized P&L and trade stats for an America/New_York date (``YYYY-MM-DD``).

    Buys are matched to sells FIFO per symbol across the full trade log;
    each sale's realized P&L is bucketed by the fill's ET exit date, so
    overnight positions attribute to the exit day. ``realized_pnl`` is net
    of all commissions booked that date. ``round_trips`` holds the per-SELL
    realized P&L (gross) for that date.
    """
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT timestamp, symbol, side, qty, price, commission"
            " FROM trades ORDER BY id"
        ).fetchall()

    lots: dict[str, list[list[float]]] = {}
    n_trades = 0
    n_sells = 0
    commissions = 0.0
    realized = 0.0
    round_trips: list[float] = []
    for r in rows:
        is_day = _et_date(r["timestamp"]) == date
        if is_day:
            n_trades += 1
            commissions += r["commission"]
            if r["side"] == "SELL":
                n_sells += 1
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
            if is_day:
                realized += trade_pnl
                round_trips.append(trade_pnl)
    return {
        "date": date,
        "realized_pnl": realized - commissions,
        "n_trades": n_trades,
        "n_sells": n_sells,
        "round_trips": round_trips,
        "commissions": commissions,
    }


def get_equity_curve(db_path: Path | str | None = None) -> list[dict]:
    """Equity snapshots (one per fill), oldest first."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT timestamp, equity, cash FROM equity_snapshots ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------- orders
def create_order(symbol: str, side: str, qty: float, order_type: str, *,
                 limit_price: float | None = None,
                 stop_price: float | None = None,
                 reason: str | None = None,
                 db_path: Path | str | None = None) -> int:
    """Create an OPEN order row; returns the order id."""
    side = side.upper()
    order_type = order_type.upper()
    if side not in ("BUY", "SELL"):
        raise ValueError(f"side must be BUY or SELL, got {side!r}")
    if order_type not in ("MARKET", "LIMIT", "STOP"):
        raise ValueError(f"order_type must be MARKET, LIMIT or STOP, got {order_type!r}")
    if qty <= 0:
        raise ValueError("qty must be positive")
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO orders (created_at, symbol, side, qty, order_type,"
            " limit_price, stop_price, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (_utcnow(), symbol.upper(), side, qty, order_type,
             limit_price, stop_price, reason),
        )
        conn.commit()
        return cur.lastrowid


def get_open_orders(db_path: Path | str | None = None, *,
                    symbol: str | None = None) -> list[dict]:
    """OPEN orders, oldest first; optionally filtered by symbol."""
    sql = "SELECT * FROM orders WHERE status = 'OPEN'"
    params: tuple = ()
    if symbol is not None:
        sql += " AND symbol = ?"
        params = (symbol.upper(),)
    with _connect(db_path) as conn:
        rows = conn.execute(sql + " ORDER BY id", params).fetchall()
    return [dict(r) for r in rows]


def fill_order(order_id: int, price: float, *, commission: float = 0.0,
               reason: str | None = None,
               db_path: Path | str | None = None) -> int:
    """Fill an OPEN order at ``price``: records the trade and marks it FILLED.

    The trade inherits the order's reason unless ``reason`` overrides it
    (e.g. a fired bracket STOP records the trade as "STOP"). Returns the
    trade id. If the fill is rejected (no margin / oversell) the order is
    left OPEN.
    """
    with _connect(db_path) as conn:
        order = conn.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
    if order is None:
        raise ValueError(f"no order with id {order_id}")
    if order["status"] != "OPEN":
        raise ValueError(f"order {order_id} is {order['status']}, not OPEN")
    trade_id = record_fill(
        order["symbol"], order["side"], order["qty"], price,
        commission=commission, order_id=order_id,
        reason=reason if reason is not None else order["reason"],
        db_path=db_path,
    )
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE orders SET status = 'FILLED', filled_at = ?, filled_price = ?"
            " WHERE id = ?",
            (_utcnow(), price, order_id),
        )
        conn.commit()
    return trade_id


def cancel_order(order_id: int, db_path: Path | str | None = None) -> None:
    """Cancel an OPEN order (no-op if already filled/canceled)."""
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE orders SET status = 'CANCELED' WHERE id = ? AND status = 'OPEN'",
            (order_id,),
        )
        conn.commit()


def cancel_all_open_orders(db_path: Path | str | None = None, *,
                           symbol: str | None = None) -> int:
    """Cancel every OPEN order (optionally one symbol's); returns the count."""
    sql = "UPDATE orders SET status = 'CANCELED' WHERE status = 'OPEN'"
    params: tuple = ()
    if symbol is not None:
        sql += " AND symbol = ?"
        params = (symbol.upper(),)
    with _connect(db_path) as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.rowcount


def sync_stops_with_positions(db_path: Path | str | None = None) -> None:
    """Reconcile OPEN STOP orders with open positions after a sell.

    STOPs for flat symbols are canceled; a STOP larger than the remaining
    open qty is shrunk to match.
    """
    positions = {p["symbol"]: p["qty"] for p in get_open_positions(db_path)}
    with _connect(db_path) as conn:
        stops = conn.execute(
            "SELECT id, symbol, qty FROM orders"
            " WHERE status = 'OPEN' AND order_type = 'STOP'"
        ).fetchall()
        for s in stops:
            open_qty = positions.get(s["symbol"], 0.0)
            if open_qty <= 1e-9:
                conn.execute(
                    "UPDATE orders SET status = 'CANCELED' WHERE id = ?", (s["id"],)
                )
            elif s["qty"] > open_qty + 1e-9:
                conn.execute(
                    "UPDATE orders SET qty = ? WHERE id = ?", (open_qty, s["id"])
                )
        conn.commit()


# ------------------------------------------------- risk_day / risk state
def get_risk_day(date: str, day_start_equity: float,
                 db_path: Path | str | None = None) -> dict:
    """Return the risk_day row for ``date``, creating it if absent."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM risk_day WHERE date = ?", (date,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO risk_day (date, day_start_equity, updated_at)"
                " VALUES (?, ?, ?)",
                (date, day_start_equity, _utcnow()),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM risk_day WHERE date = ?", (date,)
            ).fetchone()
    return dict(row)


def save_risk_day(date: str, *, peak_pnl: float, was_green: bool,
                  locked: bool, lock_reason: str | None,
                  db_path: Path | str | None = None) -> None:
    """Persist risk_day state for ``date`` (row must exist — see get_risk_day)."""
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE risk_day SET peak_pnl = ?, was_green = ?, locked = ?,"
            " lock_reason = ?, updated_at = ? WHERE date = ?",
            (peak_pnl, int(was_green), int(locked), lock_reason, _utcnow(), date),
        )
        conn.commit()


def get_equity_hwm(db_path: Path | str | None = None) -> float:
    """Account equity high-water mark; falls back to starting_cash if unset."""
    with _connect(db_path) as conn:
        _ensure_account(conn)
        row = conn.execute(
            "SELECT equity_hwm, starting_cash FROM account WHERE id = 1"
        ).fetchone()
    if row["equity_hwm"] is None:
        return row["starting_cash"]
    return row["equity_hwm"]


def set_equity_hwm(value: float, db_path: Path | str | None = None) -> None:
    with _connect(db_path) as conn:
        _ensure_account(conn)
        conn.execute("UPDATE account SET equity_hwm = ? WHERE id = 1", (value,))
        conn.commit()


def is_walkaway_locked(db_path: Path | str | None = None) -> bool:
    """Account-level 20%-drawdown walkaway latch (spans days)."""
    with _connect(db_path) as conn:
        _ensure_account(conn)
        row = conn.execute(
            "SELECT walkaway_locked FROM account WHERE id = 1"
        ).fetchone()
    return bool(row["walkaway_locked"])


def set_walkaway_locked(locked: bool, db_path: Path | str | None = None) -> None:
    with _connect(db_path) as conn:
        _ensure_account(conn)
        conn.execute(
            "UPDATE account SET walkaway_locked = ? WHERE id = 1", (int(locked),)
        )
        conn.commit()
