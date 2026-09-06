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
    out: dict[str, list[Bar]] = defaultdict(list)
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rec = json.loads(line)
        if rec.get("type") != "bar":
            continue
        out[rec["symbol"]].append((rec["ts"], rec["open"], rec["high"], rec["low"],
                                   rec["close"], rec["volume"]))
    for sym in out:
        out[sym].sort()
    return dict(out)
