"""microflow — the 10-second micro pullback, confirmed inside the forming
1-minute candle.

One module per responsibility; see README.md for the contracts and for which
modules exist yet. Nothing here places, cancels or amends an order.

    from momentum_platform.microflow import DEFAULT, bars, spread

    fine = bars.load(conn, day="2026-09-18")
    v = spread.gate(trigger=5.10, stop=5.04, bid=5.09, ask=5.10, cfg=DEFAULT)
    if not v.ok:
        print(v.reason)
"""

from . import bars, spread
from .config import DEFAULT, PROVENANCE, MicroflowConfig

__all__ = ["bars", "spread", "DEFAULT", "PROVENANCE", "MicroflowConfig"]
