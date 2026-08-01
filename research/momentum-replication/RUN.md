# Running this

Python 3.11. Requires `curl` on PATH for data fetching. No third-party packages
are needed for the engine or diagnostics — everything uses the standard library.

All scripts resolve paths through `_paths.py`, so they can be run from any
working directory.

---

## Cached data

`data/` ships with the expensive inputs already collected, so the pipeline runs
offline. Unpack the two compressed caches first:

```bash
cd research/momentum-replication
gunzip -kf data/scan20_stats.json.gz    # pre-market stats, 26,107 symbol-days
gunzip -kf data/daily20.json.gz         # daily bars, 1,957 symbols
```

| File | What it is | Cost to regenerate |
|---|---|---|
| `scan20_stats.json` | per-symbol per-day pre-market statistics | ~12 min, ~12k requests |
| `daily20.json` | consistently-adjusted daily bars + split events | ~5 min, ~2k requests |
| `pool20.json` | candidate universe (price + market cap filtered) | seconds |
| `watchlists20.json` | the selected watchlist per day | seconds |
| `premarket_scan.json` | single-day scan (2026-07-31) | ~6 min |
| `run20_max{2,5}.json` | current run output | ~2 min |

Intraday 1-minute bars for the ~47 watchlist symbols are fetched on each run
(~2 min). They are not cached because Yahoo's 1-minute history is a rolling
~30-day window, so the dates used here will age out.

---

## The run

```bash
python pipeline/run20b.py 2 5      # builds watchlists, runs both trade limits
python diagnostics/analyze20.py 5  # per-day table, aggregate stats, trades
```

Current output: 17 trading days, 3 trades, +$128.70.

---

## Verification

```bash
python diagnostics/audit20.py
```

Truncates every session at 10:00, 10:30, 11:00, 11:30 and the full day, re-runs,
and requires that any trade entered before a cut-off comes back identical. This
is the check that the engine does not read future data. **Run it after any
change to the engine.** It currently passes.

---

## Diagnostics

```bash
python diagnostics/loo.py          # leave-one-out: which conditions bind
python diagnostics/probe.py        # setup geometry vs each reference level
python diagnostics/probe2.py       # setup timing, time spent below VWAP
python diagnostics/probe3.py       # what the watchlist symbols actually did
python diagnostics/probe_veee.py   # one symbol, every setup, full check vector
python diagnostics/gradient.py     # results vs number of conditions required
python diagnostics/sweep.py        # level_tolerance x pullback-reset grid
python diagnostics/diag.py         # entry quality vs exit quality
```

`probe_veee.py` is the template for inspecting a single symbol-day in detail —
change the two constants at the top to point it anywhere.

---

## Rebuilding data from scratch

Only needed if the dates are moved. Order matters.

```bash
python pipeline/scan20.py          # pre-market stats over the candidate pool
python pipeline/fetch_daily.py     # daily bars, for cross-day comparisons
python pipeline/run20b.py 2 5
```

`pipeline/scan20.py` reads `data/pool20.json`. That pool is built from a Nasdaq
screener snapshot filtered on price and market capitalisation only — the bands
are deliberately wider than the strategy's so that no symbol enters or leaves
the pool because of how a given day finished.

The date window is defined by `WINDOWS` in `pipeline/scan20.py` and
`pipeline/run20b.py`, and by `P1`/`P2` in `pipeline/fetch_daily.py`. Yahoo
serves 1-minute data in 7-day windows and reaches back ~30 days; responses from
different windows are adjusted independently, so anything comparing across days
must come from a single response.

---

## Querying the source corpus

The evidence behind the strategy documents lives outside this folder.

```bash
python ../../scripts/pipeline/12_build_claims_db.py   # ~30s, builds data/claims.db
python ../../scripts/search.py "profit target high of day"
python ../../scripts/search.py --concept "stop at pullback low"
python ../../scripts/search.py --param "float (shares)"
python ../../scripts/search.py --coverage
python ../../scripts/search.py "third pullback" --layer chunks
python ../../scripts/search.py --explain
```

Two layers: `claims` are the summariser's tagged statements — clean and citable
but lossy; `chunks` are windows of raw caption text — noisy but complete, and
the only layer that can settle whether something was ever said. Every hit
returns a YouTube link with a timestamp.

---

## Engine entry points

| Where | What |
|---|---|
| `engine/sim.py` | account constants, strategy constants, `Indicators`, `PullbackTracker`, `confluence()`, `evaluate()` |
| `engine/sim.py::evaluate` | the entry gate — the 9 conditions and how each is measured |
| `engine/sim.py::PullbackTracker.update` | how a leg, a pullback and a trigger are identified |
| `engine/engine20.py::run_day` | one day: position management, exits, sizing, day-stop rules |
| `pipeline/run20b.py::build` | watchlist construction from pre-market data |

`MIN_PILLARS` in `engine/sim.py` controls how many of the 9 conditions must hold
(currently 9, i.e. all of them). `PULLBACK_RESET` switches between the two
readings of when pullback counting restarts.
