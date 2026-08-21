# Day Trading Bot

An intraday trading bot built from scratch. Early stage — architecture and strategy under active development.

## Status

🚧 Early stage. The paper-trading platform runs; the automated bot does not exist yet.

## Paper trading platform

A fully local, free manual paper-trading platform for the Ross Cameron
small-cap momentum strategy (`knowledge-base/strategies/`). You place the
simulated trades yourself — it is not a backtester and not an automated bot.

### Setup

```bash
pip install -r requirements.txt
```

### Launch

```bash
streamlit run src/paper_trading/app.py
```

### Tabs

- **Scanner** — full or quick (first 100 symbols) NASDAQ universe scan with
  a progress bar; results ranked by rvol and capped at 50 rows, kept across
  refreshes; a toast alerts when a symbol newly appears in the hit list;
  "Load" sends a hit into the global ticker.
- **Charts** — 1m / 5m / daily candles (5m resampled locally from 1m),
  EMA9/EMA20 on every timeframe, VWAP on intraday frames, MACD subplot.
  Auto-refreshes every 15s.
- **Trade** — risk-based order ticket: `shares = risk_budget / (entry -
  stop)` (strategy §7), capped at what the cash can actually afford;
  reward:risk and $0.20 max stop-distance (§5) checks; estimated
  commission. Buttons are labeled with the hotkeys they mirror
  (PLATFORM.md §2): "Buy — Shift+2" (attach bracket stop checkbox, default
  on), "Sell Full — Ctrl+Z", "Sell Half — Ctrl+X", "Cancel All — Ctrl+Q".
  Live positions and open orders below, with per-order cancel.
- **Journal** — win rate, expectancy, avg win / avg loss, avg R (for
  entries that carried a bracket stop), per-day net P&L incl. commissions,
  full trade log.
- **Risk** — live 🟢/🔴 status of the 5 daily rules (max daily loss 6%,
  50% giveback, green-to-red, 3 consecutive losses, 20% drawdown walkaway),
  the persisted lockout latch and reason, equity HWM / drawdown %, plus the
  manual resets (new day, walkaway lock, full account reset) behind confirm
  checkboxes.

### Execution model

- **Net-P&L fills**: commission $0.005/share plus $0.02/share slippage on
  every fill; no shorting, no margin.
- **Market and marketable-limit orders** in the broker (marketable limit =
  last ± $0.15, i.e. ask + $0.15 for buys); the ticket sends market orders.
- **Bracket stops** attached on entry fire from a 10-second refresh loop —
  **only while the app is running** — and free yfinance data is ~15 min
  delayed, so stop fills are simulation-grade, not real-time.
- **Hard risk lockout**: `broker.buy` consults the persisted RiskGate
  before pricing and refuses the order (`RiskVeto`) when any of the 5 rules
  is tripped. The latch lives in SQLite, survives restarts, and resets on
  the next trading day; exits are always allowed, even while locked.
  `ledger.record_fill` is the raw ledger and stays unguarded by design —
  UI code must never call it directly; every order path goes through
  `broker`.
- **SQLite persistence** at `data/paper_trading.db`. The schema migrates in
  place on first launch (non-destructive: trades gain commission/order_id/
  reason columns; orders and risk_day tables are added) — back the file up
  first if the history matters.

### Tests

```bash
python -m pytest tests/
```

## Scanner

NASDAQ universe scanner implementing the §1 universe filter from
`knowledge-base/strategies/PARAMETERS.md`: price $2–$20, day gain ≥ 10%,
relative volume ≥ 5x the 50-day average, day volume ≥ 500,000 shares.
Fully local and free — symbol directory from nasdaqtrader.com, daily OHLCV
from yfinance, no API keys. Free data is **~15 minutes delayed**, and a
full scan of the ~3,300-symbol NASDAQ universe takes several minutes.

CLI:

```bash
python scripts/run_scanner.py              # full scan, saves to results/
python scripts/run_scanner.py --limit 50   # quick test
python scripts/run_scanner.py --no-etf     # exclude ETFs
```

Platform: open the Scanner tab, run a full or quick scan, then Load a hit
into the ticker.

Two §1 criteria are **manual checks**, not computed: float ≤ 20M shares
(`floatShares` is not reliably available for free; `--fetch-float` queries
it for passers only, slowly) and the news catalyst. They appear as
manual-check columns rather than being silently dropped.

## 1-minute candle history

Pull every 1-minute candle the free feed still has for a symbol and keep
it in a local archive:

```bash
python scripts/fetch_1m_history.py SDOT --today      # today only, premarket incl.
python scripts/fetch_1m_history.py SDOT --today --tail 30   # last 30 bars only
python scripts/fetch_1m_history.py SDOT --date 2026-08-20   # one past session
python scripts/fetch_1m_history.py SDOT              # trailing 30 days
python scripts/fetch_1m_history.py SDOT --days 7     # just this week
python scripts/fetch_1m_history.py SDOT --no-prepost # regular session only
python scripts/fetch_1m_history.py SDOT --gaps       # + missing-minute count
python scripts/fetch_1m_history.py SDOT --summary-only  # re-read the archive
```

**Yahoo keeps only ~30 calendar days of 1-minute bars**, and caps a single
request at 8 days — so "all the 1m history" means the trailing month, not
the symbol's full life. No free source serves deeper 1m history; that is a
paid feed (Polygon, Databento, Alpaca's historical plans).

The fetcher walks the window in 7-day chunks and merges the result into
`data/history/<SYMBOL>_1m.csv`. The archive is **additive**: each run adds
only bars it doesn't already have, so running it weekly accumulates a
history far past the 30-day window. Bars older than your first run cannot
be recovered from this feed — start the archive early.

`--today` / `--date` fetch one bounded session and print **every bar**
(04:00 ET onward, premarket included unless `--no-prepost`), followed by a
session anatomy: premarket high/low/volume, the 09:30 open, high and low
with their timestamps, last price, total volume, and whether price broke
the premarket high. Those bars are merged into the same archive.

Without `--today`/`--date`, output is one row per session (bar count,
first/last bar, OHLC, volume) plus the last five bars. Timestamps are
`America/New_York` throughout. Pre/post-market bars are included by
default, so a full session runs 04:00–20:00 rather than 390 bars.
`--gaps` counts regular-session minutes with no print, measured only
inside the traded span — on a thin small cap those holes are normal, not
a fetch error.

## Blinded walk-forward replay

Grades strategy decisions candle by candle with the future hidden, then
scores them. The prompt that drives it is
`knowledge-base/strategies/REPLAY_EVAL_PROMPT.md`.

```bash
python scripts/replay_eval.py --symbols SDOT --days 5
python scripts/replay_eval.py --symbols SDOT,ABCD --date 2026-08-20 --sweep
```

At cursor `t` the engine builds `visible = bars.iloc[:t+1]` and every gate,
indicator and level is computed from that slice alone. `assert_causal`
re-derives EMA9/EMA20/VWAP/MACD on the truncated frame and raises
`LookAheadError` if any value at `t` differs from the same value computed on
the full session — and the test suite proves that guard fires by feeding it a
deliberately non-causal (centered-window) indicator. The 5-minute frame is
resampled from `visible`, so its final bar is in-progress, as on a live screen.

Output is one row per candle decision (every §3 gate boolean, the verdict, the
resolved outcome) written to `results/replay_<date>.csv`, plus a confusion
matrix, the §9 comparison, the §12 baselines and the §12.3 tolerance sweep.

What it deliberately will not do: pass off `tape_green` / `no_seller_wall` /
float / catalyst as satisfied (they need Level 2 and paid fundamentals, so
they are carried as UNTESTABLE/UNKNOWN), claim significance below 20 resolved
trades, or report the best cell of a parameter sweep whose sign flips.
Symbols passed with `--symbols` are a manual list, not a point-in-time 09:25
scan — the run says so on every invocation, because choosing tickers that are
known to have run is the fastest way to a fake edge.

## Structure

```
src/paper_trading/   platform package (app, ledger, broker, risk_gate, risk, indicators, datafeed, history, replay, scanner)
scripts/run_scanner.py  scanner CLI
scripts/fetch_1m_history.py  1-minute candle archive CLI
scripts/replay_eval.py  blinded walk-forward replay CLI
tests/               test suite
knowledge-base/      strategy research and specs
```

## Disclaimer

This software is for research and educational purposes only. Nothing here is financial advice. Trading involves substantial risk of loss.
