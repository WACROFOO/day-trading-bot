"""The gap scan rejects what IBKR cannot trade as a stock. 2026-09-15: finviz
typed PSNYW (a Polestar warrant) as a stock, the scan passed it, IBKR had no
security definition for it, and the desk died on the name before the first
minute of the session."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("premarket_stars", ROOT / "scripts" / "premarket_stars.py")
stars = importlib.util.module_from_spec(spec)
sys.modules["premarket_stars"] = stars
spec.loader.exec_module(stars)


def row(sym, typ="stock"):
    return {"sym": sym, "pm_close": 4.20, "prev_close": 3.00, "pm_high": 4.40,
            "float": 6_000_000, "pm_vol": 900_000, "why_catalyst": True, "type": typ}


def test_a_five_letter_w_r_or_u_suffix_is_rejected_as_not_common_stock():
    for sym, kind in (("PSNYW", "warrant"), ("ABCDR", "right"), ("ABCDU", "unit")):
        verdict, reasons = stars.grade(row(sym))
        assert verdict == "REJECT", (sym, reasons)
        assert any(kind in r and "not common stock" in r for r in reasons), reasons
        assert "instrument" in stars.kill_reason({"reasons": reasons})


def test_four_letter_names_and_other_fifth_letters_are_untouched():
    for sym in ("TNON", "GROW", "BDRX", "ABCDA", "ABCDY"):
        verdict, reasons = stars.grade(row(sym))
        assert verdict != "REJECT", (sym, reasons)
        assert not any("suffix" in r for r in reasons)


def test_a_typed_fund_still_reads_as_a_fund_not_a_suffix():
    verdict, reasons = stars.grade(row("ORCUW", typ="fund"))
    assert verdict == "REJECT"
    assert any('type "fund"' in r for r in reasons) and not any("suffix" in r for r in reasons)
