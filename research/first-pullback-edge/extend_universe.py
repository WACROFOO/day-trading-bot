#!/usr/bin/env python3
"""Extend the survivorship-free universe back to 2016.

    python3 extend_universe.py --start 2016-01-04 --end 2024-09-23

Grouped daily is the better construction and the free tier caps it at two
years. This covers everything before that by the other route:

  1. Massive's reference DB for the FULL historical ticker list — active AND
     delisted, each delisted row carrying a `delisted_utc`. That is the
     survivorship fix: a company that left the exchange in 2019 is in the
     list, gets screened on the days it traded, and is absent afterwards.
  2. Alpaca's multi-symbol daily endpoint to screen that list — open,
     previous close, trailing-20 dollar volume, all point-in-time.

The result is appended to data/candidate_days.parquet, and the merged table
carries a `source` column so the two construction methods stay separable in
the report rather than being silently blended.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.data import AlpacaProvider, PolygonProvider          # noqa: E402
from src.universe import (ScanRules, candidate_days_multi,     # noqa: E402
                          to_records)

DATA = ROOT / "data"
RESULTS = ROOT / "results"


def load_symbol_universe(refresh: bool = False) -> list[dict]:
    path = DATA / "symbol_universe_historical.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    p = PolygonProvider()
    print("pulling the full historical ticker list (active + delisted) …")
    rows = p.all_tickers(types=("CS", "ADRC"))
    path.write_text(json.dumps(rows))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2016-01-04")
    ap.add_argument("--end", default="2024-09-23")
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--refresh-symbols", action="store_true")
    a = ap.parse_args()

    import yaml
    cfg = yaml.safe_load((ROOT / "config" / "strategy.yaml").read_text())
    u = cfg["universe"]

    def _v(n):
        return n["value"] if isinstance(n, dict) and "value" in n else n

    rules = ScanRules(price_min=_v(u["price_min"]), price_max=_v(u["price_max"]),
                      gap_min_pct=_v(u["gap_min_pct"]),
                      min_dollar_volume=_v(u["min_premarket_dollar_volume"]))

    rows = load_symbol_universe(a.refresh_symbols)
    start = dt.date.fromisoformat(a.start)
    end = dt.date.fromisoformat(a.end)

    # A ticker only needs screening if it was listed during the window: keep
    # everything still active, plus anything delisted AFTER the window opens.
    keep = []
    for r in rows:
        t = (r.get("ticker") or "").strip().upper()
        if not t or not t.isalpha() or len(t) > 5:
            continue
        dl = r.get("delisted_utc")
        if dl and dl[:10] < start.isoformat():
            continue
        keep.append(t)
    syms = sorted(set(keep))
    n_delisted = sum(1 for r in rows if r.get("delisted_utc"))
    print(f"symbol universe: {len(rows)} rows, {n_delisted} carrying a "
          f"delisted_utc · {len(syms)} in scope for {start} -> {end}")

    alp = AlpacaProvider()
    alp._require()

    def prog(done, total, tag, cands):
        print(f"  {done}/{total} symbols · {tag} · {cands} candidate-days",
              flush=True)

    out = candidate_days_multi(alp, syms, start, end, rules,
                               batch=a.batch, progress=prog)
    print(f"\n{len(out)} candidate ticker-days, {start} -> {end}")

    import pandas as pd
    new = pd.DataFrame(to_records(out))
    old_path = DATA / "candidate_days.parquet"
    if old_path.exists():
        old = pd.read_parquet(old_path)
        old = old[old["day"] > a.end]        # keep the grouped-daily era intact
        merged = pd.concat([new, old], ignore_index=True)
    else:
        merged = new
    merged = (merged.sort_values(["day", "gap_pct"], ascending=[True, False])
                    .drop_duplicates(subset=["sym", "day"], keep="first"))
    merged.to_parquet(DATA / "candidate_days.parquet", index=False)
    merged.to_csv(DATA / "candidate_days.csv", index=False)

    by_year = (merged.assign(year=merged["day"].str[:4])
                     .groupby("year")
                     .agg(ticker_days=("sym", "size"), sessions=("day", "nunique"),
                          names=("sym", "nunique")).reset_index())
    summary = dict(
        construction="grouped_daily 2024-09-24+ ; historical ticker list x "
                     "multi-symbol daily before that (both survivorship-free)",
        total_candidate_days=int(len(merged)),
        sessions=int(merged["day"].nunique()),
        names=int(merged["sym"].nunique()),
        span=[merged["day"].min(), merged["day"].max()],
        symbols_screened=len(syms),
        symbols_with_delisted_date=n_delisted,
        by_year=by_year.to_dict("records"),
        by_source=merged["source"].value_counts().to_dict(),
    )
    (RESULTS / "universe_summary.json").write_text(json.dumps(summary, indent=2))
    by_year.to_csv(RESULTS / "universe_by_year.csv", index=False)
    print(json.dumps(summary, indent=2)[:2200])


if __name__ == "__main__":
    main()
