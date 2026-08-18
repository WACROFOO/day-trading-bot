# captures/ — raw exports from the Warrior platform

Timestamped, unedited alert exports and screenshots. **Evidence, not
analysis** — nothing in this folder is interpreted; it is what the platform
showed at a moment, kept so a later claim can be checked against it.

| file | what it is |
|---|---|
| `2026-08-18-momo-alerts.csv` | 301 high-day-momentum alert rows, 04:02:48 → 05:42:34 ET, 7 symbols, 6 strategy branches. The first export with a strategy label on every row |
| `2026-08-18-filters-auto.md` | machine-generated filter profile of that CSV (`scripts/dash_filters.py --md`) |

Read them with:

```
python3 scripts/dash_filters.py knowledge-base/daytrade-dash/captures/*.csv --hod
```

It merges every capture, profiles each branch, and runs the single-axis
exclusion search that identifies actual thresholds — graded by support, so a
two-symbol coincidence never prints like a finding.

The capture protocol, and what to compare against, is in the parent README.
Analysis of this data: `research/momentum-replication/reports/2026-08-18-momo-scanner-reverse-engineering.md`.

The export carries **no news/flame field** — that column is only a quote URL.
