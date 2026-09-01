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

## Momentum scanner + alert platform (`src/momentum_platform/`)

The replay-first, event-driven scanner and alerting engine specified in
`CLAUDE_ROSS_TRADING_MASTERY_2026-08-31/references/scanner-alert-platform-spec.md`.
Stdlib-only core (no pandas/yfinance needed except for the optional live
tracker), so it runs and tests anywhere.

What it implements:

- **Session calendar** — premarket 04:00–09:30, regular, after-hours in
  `America/New_York`, DST-safe, daily state reset.
- **Hot state** — per-symbol snapshots, 1-minute bar building from ticks or
  bars, rolling 5-minute volume and RVOL.
- **Scanners** (every event carries raw values, pass/fail reasons and a
  definition version): Top Gainers / Losers / Gappers (gappers freeze at
  09:30 ET), Low Float Top Gainers, Top RVOL, Top 5m Volume, Five Pillars
  list + rising-edge alert (Confirmed course thresholds: $2–$20, +10%,
  RVOL ≥ 5x, float < 20M; news scored separately, never silently required),
  HOD Momentum with branch labeling, Running Up/Down, Squeeze 5-in-5 and
  10-in-10, 52-week breakout. All non-course thresholds are labeled
  independent approximations.
- **First-pullback detector** — impulse → 2–4 candle pullback on declining
  volume → new-high trigger; frozen entry/stop/2R planning bands that never
  repaint (fixes the documented gap in the bundled Pine script).
- **Notification router** — idempotency keys, per-scanner cooldowns with
  price-tier override, same-symbol consolidation, severity filter; console,
  JSONL timeline (`data/alerts.jsonl`) and Slack-compatible webhook
  channels (`MOMENTUM_WEBHOOK_URL`, kept out of git). Channel failure never
  blocks scanning.
- **SQLite event store** — every alert persisted with reasons, plus a
  watchlist.
- **News flame** — Confirmed platform mapping (red 0–2h, orange 2–12h,
  yellow 12–24h) computed from publication time; a flame means recent news,
  not good news.

CLI:

```bash
export PYTHONPATH=src
python -m momentum_platform.cli replay fixtures/market_replay/demo_momentum_day.jsonl
python -m momentum_platform.cli watchlist add ABCD QUIE
python -m momentum_platform.cli track --interval 30        # yfinance, ~15m DELAYED
python -m momentum_platform.cli events --symbol ABCD
```

Scanner events are research candidates, never entry signals or orders. The
yfinance tracker is for development and delayed watchlist tracking only; a
licensed real-time feed (Alpaca/Polygon/Databento) plugs into the same
`MarketUpdate` interface when ready.

## Structure

```
src/momentum_platform/  event-driven scanner + alert engine (models, sessions, formulas, state, scanners/, notify, store, engine, pullback, datasources/, cli)
src/paper_trading/   manual simulator package (app, ledger, broker, risk_gate, risk, indicators, datafeed, scanner)
fixtures/market_replay/  deterministic replay fixtures (golden tests)
scripts/run_scanner.py  scanner CLI
tests/               test suite
knowledge-base/      strategy research extracted from the YouTube corpus
CLAUDE_ROSS_TRADING_MASTERY_2026-08-31/  canonical knowledge bundle (course-derived)
```

## Disclaimer

This software is for research and educational purposes only. Nothing here is financial advice. Trading involves substantial risk of loss.
