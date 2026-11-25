"""The instrument map: which UCITS fund implements each sleeve.

``config/instruments.csv`` lists, per sleeve, the primary fund and its
alternatives, with ISIN, listing, cost, share class and the backtest series
that stands in for it. Tradability and PEA eligibility still have to be
confirmed in your own accounts (ROADMAP Step 2).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

INSTRUMENTS_CSV = Path(__file__).resolve().parents[2] / "config" / "instruments.csv"


def load_instruments(path: Path = INSTRUMENTS_CSV) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def isin_is_valid(isin: str) -> bool:
    """ISO 6166 check: 2 letters, 9 alphanumerics, 1 check digit (Luhn)."""
    if len(isin) != 12 or not isin[:2].isalpha() or not isin[-1].isdigit() or not isin.isalnum():
        return False
    digits = "".join(str(int(ch, 36)) for ch in isin[:-1].upper())
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        if i % 2 == 0:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return (10 - total % 10) % 10 == int(isin[-1])


def primary(sleeve: str, path: Path = INSTRUMENTS_CSV) -> pd.Series:
    """The primary fund for a sleeve (S1..S7)."""
    df = load_instruments(path)
    rows = df[(df["sleeve"] == sleeve) & (df["choice"] == "primary")]
    if len(rows) != 1:
        raise KeyError(f"expected one primary instrument for {sleeve}, found {len(rows)}")
    return rows.iloc[0]
