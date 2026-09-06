# Day Trading Bot

An attempt to mechanically implement and honestly test the Ross Cameron /
Warrior Trading small-cap momentum strategy, built on ~2,700 transcribed videos
and free 1-minute market data.

## State of play — read this first

**The strategy has not been shown to work, and neither has the opposite.** The
implementation now matches the documented rules closely (20 recorded defects
found and fixed along the way), and over 17 real sessions of July 2026 it
produces 15 trades at −0.43R expectancy. That is not a verdict on the strategy:
the live streams show his entries happen on a **10-second chart** and off
**Level 2**, neither of which 1-minute OHLCV data can represent. The full
argument: `research/momentum-replication/reports/`.

The measurement that matters most so far: of the tickers he demonstrably traded
in July 2026, the engine agrees with him on **22%**
(`research/momentum-replication/diagnostics/calibrate.py`)
— up from 4% before the last bug hunt. That agreement number, not P&L, is the
project's steering metric.

## Map

| Folder | What it is |
|---|---|
| `knowledge-base/` | Everything extracted from the source: transcripts, summaries, recaps, live streams, and the **canonical strategy documents** (`strategies/`) |
| `research/momentum-replication/` | The implementation and its test harness: engine, pipelines, diagnostics, dated reports, defect history |
| `scripts/` | The corpus tooling: scraping, transcription, claims database, search, stream mining |
| `data/` | `claims.db` — 7,937 tagged claims, each deep-linked to a video timestamp |
| `src/paper_trading/` | A manual paper-trading platform (Streamlit) for practising the strategy by hand |
| `src/momentum_platform/` | The live desk — IBKR read-only stream, scanners, first-pullback state machine, browser dashboard. No order path |
| `docs/` | Desk design notes, IBKR and Alpaca setup, the 2026-09-03 solution review |
| `config/` | `desk-profile.json` — the shared rule set two operators run against, so their desks admit the same names |
| `tests/` | Tests for the paper-trading platform and scanner |
| `archive/` | Superseded work, kept for the record — **do not build on it** |

Every folder has a `README.md` saying what is in it.

## The three entry points

**Study the strategy** → `knowledge-base/strategies/PARAMETERS.md`, and read
its §13 (misreading traps) before believing any single rule. Search the raw
evidence with:

```bash
python scripts/search.py "profit target"           # claims, deep-linked
python scripts/mine_streams.py timing              # live-stream evidence by topic
```

**Run the replication** → `research/momentum-replication/RUN.md`. Start with
`research/momentum-replication/reports/README.md` for what has already been
established, `HISTORY.md` for
the 20 defects already found (so the same ground is not covered twice), and
`NEXT-STEPS.md` for what is genuinely open.

**Trade it by hand** →

```bash
pip install -r requirements.txt
streamlit run src/paper_trading/app.py
```

Scanner, charts, risk-based order ticket, journal, and the five daily risk
rules with a lockout latch. Manual only — there is no automated bot, and given
the research findings there should not be one yet.

## House rules

1. Claim and evidence stay separate; marketing numbers are not results.
2. Every rule cites a video id and timestamp; when documents and corpus
   disagree, the corpus wins.
3. No P&L number is a result until the harness measuring it has been audited —
   the sign has flipped on identical data eight times in this project.
4. Superseded work moves to `archive/`, never gets silently edited.

## Paper-trading platform

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

## Workstation dashboard (`src/momentum_platform/dashboard/`)

The scanner-first workstation from
`CLAUDE_ROSS_TRADING_MASTERY_2026-08-31/references/dashboard-scanner-chart-knowledge.md`,
built replay-first (Steps 1–2: shell + deterministic replay, no live feed, no
Level 2, no broker). Stdlib backend, dependency-free frontend.

```bash
PYTHONPATH=src python -m momentum_platform.dashboard.server   # http://127.0.0.1:8787
python scripts/make_replay_fixture.py                          # regenerate the fixture
python scripts/build_dashboard_artifact.py build/workstation.html   # single-file build
```

**Layout** — every card is portable *and* resizable. Drag a card header onto
another card to swap places; drag the gutters between cards or columns to
change their size; ⛶ (or `E`) expands one over the workspace; `⊞ Cards` holds
cards that are off the desk; `⟲ Layout` restores the defaults. Layout and sizes
are saved per browser, and the desk stays inside one viewport at every size.
Default: three scanner cards with quote/supply/risk/catalyst beneath them on
the left; a large 1-minute chart over a 5-minute and 10-second pair in the
centre with the alert timeline below; Level 2 (about 60% of the column) over
the setup verdict on the right. The daily chart starts in the tray.

- **Three scanner cards** in funnel order — Ross-style Five Pillars Scan
  (candidates), Running Up (live acceleration) and Small Cap HOD Momentum
  (breakout). Every row carries the news flame, and alert rows tag the session
  (PM / RTH) plus the branch that fired, matching the captured column sets.
- **Four charts**: 1-minute execution (large), 5-minute structure and
  10-second micro side by side, daily room. The fixture is generated at
  10-second resolution and the 1-minute series the scanners consume is its
  exact aggregate, so no timeframe can disagree with what the scanners saw.
  A feed without sub-minute data says so rather than inventing candles.
- **TradingView Lightweight Charts** is the renderer (real crosshair, price and
  time scales, zoom and pan), pinned from cdnjs, with a canvas fallback and an
  honest engine badge when the library cannot load.
- **One selected symbol** drives the header, every chart and both side columns,
  with the ticker in the URL for deep links.
- **Row-order freeze** pins a ranking while values keep updating.
- **Explainable rows**: expanding a Five Pillars row shows each pillar's
  arithmetic against the Confirmed course threshold plus gap, 5m RVOL, 5m
  volume, position in range and spread.
- **Catalyst, graded** — the card shows the flame band (RED · 0–2h), a
  hard / soft / dilutive grade classified from the headline, the age drawn
  against the 24-hour window, feed latency, and a plain-language read against
  the funnel ("Fresh hard catalyst on a 4/4 candidate — the chart still decides
  the entry"; "Dilution risk — a red flame on an offering is not the same
  signal as a red flame on a contract").
- **Level 2 and Time & Sales** — depth ladder with size bars and wall
  detection, plus a coloured tape. The book is **simulated**, generated
  deterministically from the replay snapshot and labelled on the card.
- **Setup verdict** — mirrors the bundled Pine dashboard's eleven rows, applies
  the playbook GO / WAIT / PASS matrix, always states why, and sizes from the
  operator's own dollar risk.

### Real market data — Alpaca free tier (recommended)

```bash
cp .env.example .env                 # paste your paper keys, git ignores this file
python scripts/verify_alpaca.py      # nine checks with plain-language fixes
python scripts/alpaca_watchlist.py --top 8
PYTHONPATH=src python -m momentum_platform.dashboard.server --alpaca AAPL,TSLA
```

Standard library only — no extra packages. Gives real-time IEX bars, daily
history, real news headlines with publication timestamps, and the tradable US
universe across NASDAQ *and* NYSE. `docs/alpaca-setup.md` is the step-by-step.

The one caveat: IEX is a single venue, so **absolute volume is understated**
while prices and percentage moves are exact. Relative volume divides today's
IEX volume by prior days' IEX volume — same venue on both sides — so the ratio
stays meaningful and is labelled `iex` wherever it appears. Alpaca publishes no
float, so the supply pillar reads `unknown` rather than guessing.

### Real market data (delayed, yfinance fallback)

```bash
PYTHONPATH=src python -m momentum_platform.dashboard.server --live AAPL,TSLA,SOFI
```

Pulls real 1-minute bars, daily history, reference data and **real news
headlines** through yfinance and runs them through the same scanner engine, so
every card behaves identically on live symbols. Limits are stated on screen:
data is ~15 minutes delayed and not exchange-entitled, 1-minute history is
roughly the last seven days, premarket coverage is partial, and `floatShares`
is frequently missing — in which case shares outstanding is shown as an
explicit proxy and the supply pillar fails rather than passing on the wrong
number. This path was written but could not be exercised in the build
container, whose proxy blocks the provider.

### Using it from day one

`docs/daily-operating-guide.md` is the step-by-step routine: build today's
watchlist with `python scripts/daily_watchlist.py --top 8`, pipe the symbols
into `--live`, rehearse the funnel during the prime window, replay the whole
session after the close (where the 15-minute delay stops mattering), and paper
trade the plans through the risk-gated simulator. It also states plainly what
the delayed feed cannot do — live 1-minute entries — and the 30-session
progression before that question comes up.

`docs/wiring-market-data.md` is the integration manual: the one normalized
record contract every card is fed by, a card-to-stream dependency map, and
step-by-step adapters for market data, reference/float, news, halts and Level 2
— with the five mistakes that corrupt RVOL, a go-live checklist, and the cost
ladder in the order each upgrade becomes worth paying for.

Ten **synthetic** symbols exercise the behaviours worth testing: a 5/5 leader
with a clean first pullback, a low-float runner with no news, a gapper that
fades after the open, a halt and resumption, a proxy-float name, a squeeze
ladder, a spread-blown name that qualifies numerically but not practically, and
a quiet control. The session is produced by running the production scanner
engine over the fixture, so the prototype cannot drift from the engine.

## Structure

```
src/momentum_platform/  event-driven scanner + alert engine (models, sessions, formulas, state, scanners/, notify, store, engine, pullback, datasources/, cli)
src/momentum_platform/dashboard/  replay workstation (session_builder, server, web/)
docs/dashboard-plan.md  component tree, state contract, chart sync, fixture schemas, acceptance map
src/paper_trading/   manual simulator package (app, ledger, broker, risk_gate, risk, indicators, datafeed, scanner)
fixtures/market_replay/  deterministic replay fixtures (golden tests)
scripts/run_scanner.py  scanner CLI
tests/               test suite
knowledge-base/      strategy research extracted from the YouTube corpus
CLAUDE_ROSS_TRADING_MASTERY_2026-08-31/  canonical knowledge bundle (course-derived)
```

## Disclaimer

This software is for research and educational purposes only. Nothing here is financial advice. Trading involves substantial risk of loss.
