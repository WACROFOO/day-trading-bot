```
SOURCE · 1 export(s): 2026-08-18-momo-alerts.csv
         301 unique alert rows (from 301 raw; duplicates merged)
         2026-08-18 · 04:02:48 → 05:42:34 ET
         7 distinct symbols · 6 branches
CLEAN-ROOM · inferred from exported output only. Server thresholds UNDISCLOSED.
! OBSERVED BOUNDS BRACKET A THRESHOLD, THEY DO NOT REVEAL IT.
! EFFECTIVE n IS 7 SYMBOLS, NOT 301 ROWS — names re-alert continuously.
```

## Branches present

| branch | rows | symbols | price | float M | vol min | rvolD min | chg min |
|---|---:|---|---|---|---:|---:|---:|
| Former Momo Stock | 102 | 5 | 3.47–12.77 | 0.61–8.40 | 25,181 | 2.13 | 15.2% |
| Low Float - High Rel Vol | 48 | 2 | 3.99–9.83 | 0.90–8.40 | 531,073 | 5.34 | 46.3% |
| Low Float Volatility Hunter | 9 | 3 | 3.84–38.16 | 0.66–1.60 | 37,236 | 28.86 | 43.0% |
| Medium Float - High Rel Vol - Price under $20 | 21 | 1 | 2.48–2.97 | 41.92–41.92 | 833,554 | 519.10 | 22.8% |
| Squeeze Alert - Up 10% in 10min | 111 | 4 | 2.48–12.77 | 0.61–41.92 | 25,181 | 5.34 | 22.8% |
| Squeeze Alert - Up 5% in 5min | 10 | 2 | 3.99–6.22 | 0.90–8.40 | 78,616 | 114.78 | 38.3% |

`event` values: **New High** ×301

**HOD verification vs continuous 1-min bars:** alert bar sets a new high in **299/299** measurable cases (100.0%), against a baseline of 32/691 (4.6%) across all bars of these names.

## Identified filters (single-axis exclusions)

A symbol that never fired a branch, yet clears that branch's observed range on
every axis but one. The surviving axis is a real filter; the gap brackets it.

Graded by **support** — how many distinct symbols built the branch envelope.
FIRM ≥4 · TENTATIVE 3 · WEAK 2 (an "envelope" of two points) · SUSPECT = the
axis is not a plausible scanner filter. Only FIRM rows deserve a dial change.

| grade | branch | excluded | axis | evidence | bracket | support |
|---|---|---|---|---|---|---:|
| **TENTATIVE** | Low Float Volatility Hunter | XOS | **float_M** | best 8.40 > branch ceiling 1.60 | **ceiling in [1.601, 8.397)** | 3 sym |
| **WEAK** | Low Float - High Rel Vol | PFSA | **price** | best 10.20 > branch max 9.83 | **ceiling in [9.83, 10.2)** | 2 sym |
| **WEAK** | Squeeze Alert - Up 5% in 5min | PFSA | **price** | best 10.20 > branch max 6.22 | **ceiling in [6.22, 10.2)** | 2 sym |
| **SUSPECT** | Squeeze Alert - Up 10% in 10min | XOS | **short_int** | best 547,619.00 > branch max 26,350.00 | **ceiling in [2.635e+04, 5.476e+05)** | 4 sym |

## Not identified (excluded on 2+ axes — reported, not hidden)

- `Former Momo Stock` × **WETO** — fails 2: price, short_int
- `Former Momo Stock` × **WFF** — fails 2: price, float_M
- `Low Float - High Rel Vol` × **HCWB** — fails 2: price, volume
- `Low Float - High Rel Vol` × **IPST** — fails 4: volume, rvol_daily, rvol_5min, change_pct
- `Low Float - High Rel Vol` × **WETO** — fails 4: price, volume, rvol_5min, short_int
- `Low Float - High Rel Vol` × **WFF** — fails 2: price, float_M
- `Low Float Volatility Hunter` × **IPST** — fails 3: rvol_daily, rvol_5min, change_pct
- `Low Float Volatility Hunter` × **WFF** — fails 2: price, float_M
- `Medium Float - High Rel Vol - Price under $20` × **HCWB** — fails 5: price, volume, rvol_daily, rvol_5min, short_int
- `Medium Float - High Rel Vol - Price under $20` × **IPST** — fails 6: price, volume, rvol_daily, rvol_5min, change_pct, short_int
- `Medium Float - High Rel Vol - Price under $20` × **PFSA** — fails 2: price, short_int
- `Medium Float - High Rel Vol - Price under $20` × **SGLY** — fails 4: price, rvol_daily, rvol_5min, short_int
- `Medium Float - High Rel Vol - Price under $20` × **WETO** — fails 5: price, volume, rvol_daily, rvol_5min, short_int
- `Medium Float - High Rel Vol - Price under $20` × **XOS** — fails 2: price, short_int
- `Squeeze Alert - Up 10% in 10min` × **IPST** — fails 3: rvol_daily, rvol_5min, change_pct
- `Squeeze Alert - Up 10% in 10min` × **WETO** — fails 3: price, rvol_5min, short_int
- `Squeeze Alert - Up 5% in 5min` × **HCWB** — fails 2: price, volume
- `Squeeze Alert - Up 5% in 5min` × **IPST** — fails 5: price, volume, rvol_daily, rvol_5min, change_pct
- `Squeeze Alert - Up 5% in 5min` × **WETO** — fails 4: price, rvol_daily, rvol_5min, short_int
- `Squeeze Alert - Up 5% in 5min` × **WFF** — fails 2: price, float_M

## Limitations

- **7 symbols.** Envelope edges are set by which names qualified, not by a boundary being approached.
- Row counts are not observation counts; a name re-alerts every few seconds.
- Single-axis exclusion identifies an axis, not a value. The bracket is the claim.
- The export carries no news/catalyst field — the flame is UI-only.
- HOD cross-check uses yahoo pre-market bars, thinner than the platform feed.
- Paper only. Selection evidence, not edge.
