"""Data checks for monthly series (ROADMAP Gate G2, LESSONS C3).

A series that fails a check is not used. Suspicious values (big jumps) are
listed for review instead of being silently dropped or kept.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    items: list = field(default_factory=list)

    def __str__(self) -> str:
        mark = "PASS" if self.ok else "FAIL"
        return f"[{mark}] {self.name}" + (f": {self.detail}" if self.detail else "")


def check_monthly_index(s: pd.Series, name: str) -> list[CheckResult]:
    """Structural checks: sorted, unique, month-end, no gaps, no NaN."""
    idx = s.index
    results = [
        CheckResult(f"{name}: sorted and unique", idx.is_monotonic_increasing and idx.is_unique),
        CheckResult(f"{name}: month-end dates", bool((idx == idx + pd.offsets.MonthEnd(0)).all())),
        CheckResult(f"{name}: no missing values", not s.isna().any(),
                    f"{int(s.isna().sum())} missing" if s.isna().any() else ""),
    ]
    expected = pd.date_range(idx.min(), idx.max(), freq="ME")
    gaps = expected.difference(idx)
    results.append(CheckResult(f"{name}: no gaps", len(gaps) == 0,
                               f"{len(gaps)} missing months" if len(gaps) else "",
                               [d.date() for d in gaps[:12]]))
    return results


def check_jumps(returns: pd.Series, name: str, max_abs: float = 0.25,
                allowed: set | None = None) -> CheckResult:
    """Flag monthly moves beyond ``max_abs`` that are not explicitly allowed.

    Some big months are real (October 2008, March 2020). Those get listed in
    ``allowed`` after a human has looked at them; anything else fails.
    """
    allowed = allowed or set()
    big = returns[returns.abs() > max_abs]
    unexplained = [d for d in big.index if d.strftime("%Y-%m") not in allowed]
    detail = ", ".join(f"{d:%Y-%m} {returns[d]:+.1%}" for d in unexplained[:6])
    return CheckResult(f"{name}: no unexplained moves > {max_abs:.0%}",
                       not unexplained, detail, unexplained)


def annual_returns(levels: pd.Series) -> pd.Series:
    """Calendar-year returns from month-end levels (needs the prior December)."""
    december = levels[levels.index.month == 12]
    years = december.pct_change().dropna()
    years.index = years.index.year
    return years


def compare_annual(levels: pd.Series, reference: dict[int, float], name: str,
                   tol_pts: float = 0.5) -> CheckResult:
    """Annual returns vs. published figures (reference in percent).

    Gate G2 asks for agreement within 0.5 percentage points.
    """
    ours = annual_returns(levels) * 100.0
    misses, compared = [], 0
    for year, ref in sorted(reference.items()):
        if year not in ours.index:
            continue
        compared += 1
        if abs(ours[year] - ref) > tol_pts:
            misses.append(f"{year}: ours {ours[year]:.2f} vs {ref:.2f}")
    if compared == 0:
        return CheckResult(f"{name}: matches published annual returns", False,
                           "no overlapping years to compare")
    return CheckResult(f"{name}: matches published annual returns (±{tol_pts} pt)",
                       not misses,
                       f"{compared} years compared" + (f"; misses: {'; '.join(misses)}" if misses else ""),
                       misses)


def check_conversion(ours: pd.Series, official: pd.Series, name: str,
                     max_cagr_gap: float = 0.0025) -> CheckResult:
    """Our USD->EUR conversion vs. the provider's own EUR returns.

    Month-by-month differences are expected: FRED fixes EUR/USD at noon New
    York, MSCI at 4pm London, so a difference in one month reverses in the
    next. What must hold is the long-run result: the compound growth rates
    over the overlap may differ by at most ``max_cagr_gap`` a year.
    """
    both = pd.concat([ours, official], axis=1, join="inner").dropna()
    if len(both) < 24:
        return CheckResult(f"{name}: EUR conversion", False, "fewer than 24 overlapping months")
    years = len(both) / 12.0
    growth = (1.0 + both).prod() ** (1.0 / years) - 1.0
    gap = float(growth.iloc[0] - growth.iloc[1])
    diffs = both.iloc[:, 0] - both.iloc[:, 1]
    noise = float(diffs.autocorr(1)) if diffs.std() > 1e-12 else float("nan")
    return CheckResult(f"{name}: EUR conversion within {max_cagr_gap:.2%}/yr of official",
                       abs(gap) <= max_cagr_gap,
                       f"{len(both)} months, CAGR gap {gap:+.3%}/yr, "
                       f"lag-1 autocorrelation of differences {noise:+.2f}")
