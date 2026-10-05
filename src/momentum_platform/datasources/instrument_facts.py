"""What the cascade's Layer 1 gates 5-7 need about the instrument itself.

Review 2026-10-03: the desk never passed the split ratio, the instrument type or
the tick size to the cascade, so gate 5 read PASS untested and gates 6-7 read
UNKNOWN on every name. These are looked up once per symbol per session day:

  instrument  IBKR contract details `stockType` (the scanner's own check,
              `ibkr_scanner.is_common_stock`): funds, ETFs, ETNs, warrants,
              units and preferreds are not the strategy's universe;
  tick size   IBKR contract details `minTick` — the exchange's increment, read,
              not assumed;
  split       `scripts/premarket_stars.split_check`: finviz's previous close
              against Yahoo's not-yet-adjusted one; a CLEAN integer ratio is a
              split (CLAUDE.md rule 6). The test ran only when both prices were
              read; otherwise the gate stays UNKNOWN.

Every lookup fails soft: a missing fact stays None and the gate says UNKNOWN.
"""
from __future__ import annotations

import os
import sys
from typing import Callable, Optional

from .ibkr_scanner import is_common_stock


def ibkr_instrument(ib, contract) -> dict:
    """{stock_type, is_fund_or_etf, min_tick} from IBKR contract details; {} on failure."""
    try:
        details = ib.reqContractDetails(contract)
    except Exception:                                     # noqa: BLE001
        return {}
    if not details:
        return {}
    d = details[0]
    st = getattr(d, "stockType", None) or None
    mt = getattr(d, "minTick", None)
    return {"stock_type": st,
            "is_fund_or_etf": None if not st else (not is_common_stock(st)),
            "min_tick": float(mt) if mt else None}


def _premarket_stars():
    scripts = os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts")
    scripts = os.path.abspath(scripts)
    if scripts not in sys.path:
        sys.path.append(scripts)
    import premarket_stars
    return premarket_stars


def split_facts(symbol: str, prev_close_fv: Optional[float],
                check: Optional[Callable[[str, float], dict]] = None) -> dict:
    """{split_checked, split_ratio} — split_ratio only for a clean integer."""
    if not prev_close_fv:
        return {"split_checked": False, "split_ratio": None}
    try:
        res = (check or _premarket_stars().split_check)(symbol, prev_close_fv)
    except Exception:                                     # noqa: BLE001
        res = {}
    return {"split_checked": bool(res.get("checked") or res.get("split_today")),
            "split_ratio": float(res["split_today"]) if res.get("split_today") else None}
