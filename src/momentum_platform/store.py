"""Durable event store on SQLite.

Keeps every scanner event (raw values + reasons + definition version) so
history and replay comparisons stay reproducible. Postgres/Timescale can
replace this later; the schema mirrors the spec's core tables.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .models import ScannerEvent

_SCHEMA = """
CREATE TABLE IF NOT EXISTS scanner_events (
    event_id        TEXT PRIMARY KEY,
    idempotency_key TEXT UNIQUE,
    symbol          TEXT NOT NULL,
    scanner_id      TEXT NOT NULL,
    definition_version TEXT NOT NULL,
    branch          TEXT,
    event_type      TEXT NOT NULL,
    severity        TEXT NOT NULL,
    session         TEXT NOT NULL,
    source_ts       TEXT NOT NULL,
    scan_ts         TEXT NOT NULL,
    values_json     TEXT NOT NULL,
    reasons_json    TEXT NOT NULL,
    news_json       TEXT,
    data_quality    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_symbol_ts ON scanner_events(symbol, source_ts);
CREATE INDEX IF NOT EXISTS idx_events_scanner_ts ON scanner_events(scanner_id, source_ts);

CREATE TABLE IF NOT EXISTS watchlist (
    symbol   TEXT PRIMARY KEY,
    added_at TEXT NOT NULL,
    source   TEXT,
    notes    TEXT
);
"""


class EventStore:
    def __init__(self, path: str = "data/momentum_platform.db") -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._conn = sqlite3.connect(path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "EventStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def save_event(self, event: ScannerEvent) -> bool:
        """Insert if the idempotency key is new; returns False on duplicate."""
        try:
            self._conn.execute(
                """INSERT INTO scanner_events
                   (event_id, idempotency_key, symbol, scanner_id,
                    definition_version, branch, event_type, severity, session,
                    source_ts, scan_ts, values_json, reasons_json, news_json,
                    data_quality)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    event.event_id,
                    event.idempotency_key,
                    event.symbol,
                    event.scanner,
                    event.definition_version,
                    event.branch,
                    event.event_type,
                    event.severity,
                    event.session.value,
                    event.source_ts.isoformat(),
                    event.scan_ts.isoformat(),
                    json.dumps(event.values, default=str),
                    json.dumps([r.to_dict() for r in event.reasons], default=str),
                    json.dumps(event.news, default=str) if event.news else None,
                    event.data_quality,
                ),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def events(
        self,
        symbol: Optional[str] = None,
        scanner: Optional[str] = None,
        limit: int = 200,
    ) -> List[dict]:
        query = "SELECT * FROM scanner_events WHERE 1=1"
        params: list = []
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        if scanner:
            query += " AND scanner_id = ?"
            params.append(scanner)
        query += " ORDER BY source_ts DESC LIMIT ?"
        params.append(limit)
        cur = self._conn.execute(query, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    # -- watchlist ------------------------------------------------------------

    def add_to_watchlist(self, symbol: str, source: str = "manual", notes: str = "") -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO watchlist(symbol, added_at, source, notes) VALUES (?,?,?,?)",
            (symbol.upper(), datetime.utcnow().isoformat(), source, notes),
        )
        self._conn.commit()

    def remove_from_watchlist(self, symbol: str) -> None:
        self._conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol.upper(),))
        self._conn.commit()

    def watchlist(self) -> List[str]:
        cur = self._conn.execute("SELECT symbol FROM watchlist ORDER BY symbol")
        return [row[0] for row in cur.fetchall()]
