"""Bars for the actuals, from a fixture or from anything shaped like one.

The ledger does not store bars — it is a record of decisions, not a tape.
Actuals need the forward tape, so it is loaded separately and passed in.
The shape is one dict: symbol -> list of (ts_utc_iso, o, h, l, c, v),
sorted by time. Live sessions get here from the desk's BarStore; replays
from the fixture; either way `actuals.py` neither knows nor cares.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

Bar = tuple[str, float, float, float, float, float]


def from_fixture(path: str | Path) -> dict[str, list[Bar]]:
    """Minute bars from a fixture, aggregated exactly as the desk aggregates.

    The replay fixture is entirely 10-second bars; the desk rolls them into
    minutes itself (`session_builder.py`: group by symbol and minute, open of
    the first, high/low over the chunk, close of the last, volume summed).
    The same rule is applied here so the fixture path and the live path —
    which reads the desk's own minutes back out of the ledger — describe
    the same tape. A minute-tagged record is a chunk of one and passes
    through unchanged.
    """
    groups: dict[tuple[str, str], list[dict]] = {}
    order: list[tuple[str, str]] = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rec = json.loads(line)
        if rec.get("type") != "bar":
            continue
        minute = rec["ts"][:17] + "00Z" if len(rec["ts"]) > 17 else rec["ts"]
        key = (rec["symbol"], minute)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(rec)
    out: dict[str, list[Bar]] = defaultdict(list)
    for sym, minute in order:
        chunk = groups[(sym, minute)]
        out[sym].append((minute, chunk[0]["open"], max(c["high"] for c in chunk),
                         min(c["low"] for c in chunk), chunk[-1]["close"],
                         sum(c["volume"] for c in chunk)))
    for sym in out:
        out[sym].sort()
    return dict(out)


def from_ledger(conn) -> dict[str, list[Bar]]:
    """The tape the desk wrote during a live session. Same shape as a fixture."""
    out: dict[str, list[Bar]] = defaultdict(list)
    for r in conn.execute("SELECT symbol, ts, open, high, low, close, volume FROM bars "
                          "ORDER BY symbol, ts"):
        out[r["symbol"]].append((r["ts"], r["open"], r["high"], r["low"], r["close"], r["volume"]))
    return dict(out)
