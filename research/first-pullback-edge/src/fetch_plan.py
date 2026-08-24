"""Cost the intraday fetch BEFORE spending hours on it.

On a rate-limited free tier the binding constraint is requests, not bytes,
and the request count is decided by a scanner cap that is a judgement call.
This prints the trade-off so the cap is chosen against a number instead of a
guess: for each candidate cap, how many ticker-days the study would cover,
how many distinct ticker-MONTHS that costs (one request each), and the
wall-clock at the plan's rate limit.

    python3 -m src.fetch_plan --start 2024-09-24 --end 2026-08-21
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def plan(start: str, end: str, caps=(2, 3, 5, 8, 12, 0),
         calls_per_min: int = 5) -> list[dict]:
    import pandas as pd
    cd = pd.read_csv(ROOT / "data" / "candidate_days.csv")
    cd = cd[(cd["day"] >= start) & (cd["day"] <= end)]
    cd = cd[cd["reverse_split_ratio"].isna()]
    cd = cd.sort_values(["day", "gap_pct"], ascending=[True, False])
    rows = []
    for cap in caps:
        sel = cd.groupby("day", group_keys=False).head(cap) if cap else cd
        months = {(r.sym, r.day[:7]) for r in sel.itertuples()}
        hours = len(months) / calls_per_min / 60.0
        rows.append(dict(
            cap=cap or "none",
            ticker_days=len(sel),
            sessions=int(sel["day"].nunique()),
            names=int(sel["sym"].nunique()),
            ticker_months=len(months),
            requests=len(months),
            hours_at_limit=round(hours, 1),
            in_brief_band=1000 <= len(sel) <= 3000,
        ))
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--calls-per-min", type=int, default=5)
    a = ap.parse_args()
    rows = plan(a.start, a.end, calls_per_min=a.calls_per_min)
    w = f"{'cap':>5} {'ticker-days':>12} {'sessions':>9} {'names':>7} " \
        f"{'requests':>9} {'hours':>7}  brief band"
    print(w)
    print("-" * len(w))
    for r in rows:
        print(f"{str(r['cap']):>5} {r['ticker_days']:>12} {r['sessions']:>9} "
              f"{r['names']:>7} {r['requests']:>9} {r['hours_at_limit']:>7} "
              f"  {'YES' if r['in_brief_band'] else '-'}")
    print("\nOne request = one ticker-MONTH of 1-minute bars; every candidate "
          "day in that month, and the prior sessions the RVOL denominator "
          "needs, are served from it.")
