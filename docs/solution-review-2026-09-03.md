# Momentum Workstation — end-to-end solution review

Date: 2026-09-03. Branch: `claude/ross-trading-mastery-setup-q4cz29`.
Milestone: `milestone/ibkr-live-2026-09-03`. Audience: the operator and their
management. Purpose: a faithful account of what the desk is, what it is not,
how every element on the screen is read, and what a demonstration should show.

Evidence labels used throughout, as the knowledge base requires:
**Confirmed** (course material in the 19 exposed Preview videos),
**Observed** (seen on screen or in a transcript, not stated as a rule),
**Approximation** (a clean-room stand-in whose exact production formula is
not public), **Unknown**.

---

## 1. What the desk is

A study and simulation workstation for Ross Cameron / Warrior-style small-cap
momentum trading. It discovers candidates from live market data, evaluates
them against the Confirmed Five Pillars, labels momentum events with
clean-room approximations of the course scanners, draws the first-pullback
plan on the chart, and states a verdict. It does not trade.

| It does | It does not |
|---|---|
| Stream live IBKR data read-only (client 27) and run ten NASDAQ scanner queries every two minutes (client 28) | Place, modify, cancel or transmit any order — there is no order code path, and a test fails if one appears |
| Evaluate the Confirmed pillars: price $2–20, gain ≥10%, daily RVOL ≥5×, float <20M (column), news (column) | Claim the Warrior server-side formulas — every non-pillar scanner is labelled Approximation |
| Build 10-second candles from real 5-second bars, minutes as their sum | Interpolate an empty bucket or show a delayed print under a LIVE badge |
| Label float by evidence: verified, shares-outstanding proxy, unknown | Relabel shares outstanding as float |
| Size a plan from the dollar risk the user types | Assume a risk amount, an account size, or give a personalised recommendation |

---

## 2. Architecture and data path

```
TWS (read-only API, port 7496)
   │ client 27: quotes + 5-second bars for the desk names, daily and minute history, fundamentals
   │ client 28: scanner union (5 codes × 2 NASDAQ tiers, 50 rows each) + snapshot quotes
   ▼
ibkr_stream.py      one persistent connection, BarStore (single source of every timeframe),
                    Health (LIVE / STALE / DELAYED / OFFLINE), reconnect + resubscribe once
ibkr_scanner.py     scan union, common-stock filter, reference records, float from fundamentals
ibkr_desk.py        ONE worker thread owning both connections; every 3 s rebuilds the session
                    in memory (scanner engine over reference + minute history + live candles)
   │
   ├─ stream.py     server-sent events: quote, bar10s, bar1m, health, screener, session, resync
   └─ server.py     HTTP: /, /session.js, /api/v1/stream, /api/v1/health, /api/v1/screener, /api/v1/desk/add
   ▼
web/app.js + live.js   the page: TradingView panes (their data), the desk's 10-second pane (IBKR
                       data), scanner tiles, Five Pillars board, quote/catalyst card, verdict, legend
```

Supporting sources: SEC EDGAR (free, official) for shares outstanding and
company country; Alpaca's free news endpoint (Benzinga headlines) when keys
exist; TradingView's embeddable chart for the two large panes, on TradingView's
data and terms.

Design rules that matter to a reviewer:

- **One store, every timeframe.** 10-second candles and minutes derive from the
  same 5-second bars; a candle exists only when both halves arrived. No two
  panes can disagree, and nothing is invented.
- **Freshness is measured, not assumed.** The badge turns STALE after 20 s
  without a bar in regular hours (60 s extended), DELAYED when the provider
  says types 3/4, OFFLINE on disconnect. Reconnect backs off and resubscribes
  each symbol once.
- **One thread talks to TWS.** ib_async's event loop is pumped by a single
  worker; HTTP handlers only read the last built session and enqueue work.
- **Secrets stay server-side.** Nothing provider-side reaches the browser; the
  `.env` file is git-ignored; no credentials are asked for or stored by the
  desk (TWS holds the login).

---

## 3. How to read every element on the screen

### Header
- **Clock** — ET wall clock. **REGULAR / PREMARKET / AFTER HOURS** — the session.
- **Feed badge** — LIVE (green), STALE (amber), DELAYED or OFFLINE (red),
  REPLAY (blue, a recorded session). Under it: provider, read-only, connection
  generation, reconnect count.
- **TRADINGVIEW** — the chart engine and version served locally.
- **Cards / Layout / Alerts / ? Legend** — tray of parked cards; reset to the
  default layout; audio toggle; the on-screen legend.

### Left column (funnel order)
1. **Top gainers · Five Pillars filter** — names that pass the hard gates
   (price, gain, RVOL). Float and news are columns. Click a row for the
   "why this row is here" drawer with each gate's value and evidence label.
2. **Running Up · live uptrend** — up ≥3% over the last 10 minutes, a fresh
   10-minute high in the last 3, price above the 10-minute VWAP, 5-minute
   volume above the floor; one alert per leg. Approximation.
3. **Small Cap · High of Day Momentum** — a new high of day with momentum,
   branch-labelled by float and RVOL band (LF/MF, HR/MR, <20/20+). The branch
   labels the alert; it is not the filter. Approximation.
4. **Quote · supply · risk · catalyst** — last, previous close, change, spread,
   52-week high, average volume, range position, halt status, the provider's
   last print and quote, float with its source, and the latest headline with
   its flame and catalyst grade.

Every tile's pill reads the feed's real state. **PM / RTH / AH** on an alert
row is the session the alert fired in: PM premarket 04:00–09:30 ET, RTH
regular 09:30–16:00, AH after hours 16:00–20:00. Hover any pill for the
definition.

### Centre
- **1 minute · execution** (large) and **5 minute · structure** — the desk's
  own panes on IBKR real-time data: extended hours shaded, VWAP and the 9, 20
  and 200 EMAs, the plan's entry, stop and target. (Update 2026-09-04: these
  replaced the TradingView embeds as the default stack. The embeds are in the
  tray; to a viewer not signed in to tradingview.com they run 15 minutes
  behind, which their **D** badge states.)
- **10 second · micro** — IBKR data. Shows the last 30 minutes; entry, stop,
  target and HOD lines; extended hours shaded; a note when the tape is thin.
- **Five Pillars · every name on the desk** — one row per symbol: last, volume
  today, average volume, spread, HOD, distance to VWAP, then the five pillar
  cells with value and PASS / FAIL / UNKNOWN, and a score out of five. Sorted
  best first. UNKNOWN is never counted as a pass.

### Right column
- **Screener · the whole band, now** — the scanner union's names in the desk's
  band up ≥10%, source IBKR, age of the quote. The note says the union is a
  discovery set, not an exhaustive list, and how many non-stock instruments
  (leveraged ETFs, ETNs, funds, warrants) were excluded.
- **Setup verdict** — GO / WAIT / PASS with the conditions short, the pillar
  mirror, the technical score, and the plan (entry over the trigger, stop
  under the pullback low, target at 2R). The risk box takes the user's own
  dollar risk; sizing is shown only once it is typed.

### Flames and catalyst grades
Red ≤2 h, orange ≤12 h, yellow ≤24 h since publication: recency only. The
grade (hard / soft / dilutive) is a labelled heuristic on the headline text;
the headline stays visible so it can be overruled in one read.

---

## 4. Price bands, on purpose

Two bands exist and are labelled everywhere:

- **Pillar band $2–20 (Confirmed).** What the Five Pillars list, the pillar
  cells and the verdict evaluate. It does not move.
- **Desk band $1–30 (the operator's).** What the scanner union, the screener
  and the desk admit. A runner at $24 is seen, with its price pillar FAIL,
  rather than being invisible. Set in `.env` as `DESK_PRICE_MIN` /
  `DESK_PRICE_MAX`.

---

## 5. Demonstration script (15 minutes)

1. **Preflight** (terminal): `python3 scripts/ibkr_preflight.py` — read-only
   connection, server version, market data type 1, five-second bars counted,
   a scanner sample. Say: "nothing here can transmit an order".
2. **Start**: `bash scripts/start.sh --ibkr` — watch the scan union run, the
   names join, "desk ready".
3. **Header**: point at LIVE, the generation counter, and the clock. Stop TWS
   for 30 seconds if you want to show STALE then OFFLINE, restart it, show
   the reconnect count go to 1 with no duplicate candles.
4. **Left column**: read the funnel top to bottom; open one "why this row is
   here" drawer and show the evidence labels.
5. **Board**: show a name with UNKNOWN float and explain why it is not a pass;
   show a name outside $2–20 with its price cell FAIL.
6. **Charts**: 1-minute TradingView pane for structure, 10-second pane for the
   micro pullback with entry, stop, target drawn. Point at the D badge and
   explain whose data each pane is.
7. **Verdict**: type a dollar risk; show the share count and that nothing
   else changes. Say: "the app never assumes a risk amount".
8. **Legend**: open it. Everything just said is written there.

---

## 6. Limits and risks to state plainly

| Item | Status | Consequence |
|---|---|---|
| Level 2 | Simulated, labelled | Real depth needs an IBKR NASDAQ TotalView subscription |
| Halts | Not detected | An IBKR halted flag exists on the ticker; wiring it is the next step |
| Float | IBKR fundamentals would give a verified total float, but this account is not entitled (TWS error 10358, seen 2026-09-03); SEC shares outstanding is shown as an upper bound; otherwise unknown | The supply pillar can read UNKNOWN on thin names — that is honest, not broken. Verify float by hand before sizing |
| News | Alpaca's free endpoint (Benzinga headlines), polled | A real-time news API (Benzinga's own) would push headlines the moment they print; Ross is Observed with Benzinga Pro open; QuoteMedia is not evidenced anywhere in the corpus |
| TradingView panes | Their data, their delay rules, their terms | The desk's numbers are IBKR; the panes are for reading structure |
| Scanner union | Ten queries, 50 rows each, 150 quoted per round; leveraged ETFs, ETNs, funds and warrants dropped by instrument type (resolved once per symbol) | A discovery set, never claimed exhaustive; raising the cadence multiplies snapshot quotes IBKR may bill |
| Scanner formulas | Approximations except the Confirmed pillars | Never presented as Warrior production settings |
| Mastery boundary | Basics chapters 1–6 Preview videos only | Private chapters, strategies and answer keys are not mastered and never claimed |
| Orders | None | Simulation happens by hand in the TWS paper account |

---

## 7. Verification evidence

- Automated: 350+ tests, run before every push. They cover: no order surface
  in any IBKR module; delayed data types refused; 10-second candles need both
  halves; no duplicate timestamps across backfill and live; minutes equal
  their candles; staleness from an injected clock; reconnect resubscribes
  once; SSE replay and resync; the page with a fake TWS behind the real
  server (transport hidden, provider badge, streamed candles, board rows,
  session refresh); the uptrend scanner on synthetic tapes; the two price
  bands; ETF exclusion; float parsing.
- Manual, on the operator's machine (2026-09-03): preflight green (server
  version 178, type 1, bars flowing, scanner answering); desk ran live from
  10:43 ET with eight names, screener refreshing, alerts firing; the
  recording at 11:09 shows the badge, quotes, candles and screener advancing
  with no reload.

---

## 8. Operating commands

```
cd ~/day-trading-bot
python3 scripts/ibkr_preflight.py
bash scripts/start.sh --ibkr
```

Stop with Ctrl-C. Update with `bash scripts/update.sh`. Everything runs
locally on 127.0.0.1; nothing is exposed to the network.

---

## 9. Final assessment before sharing (recording of 2026-09-03, 14:13–14:14 ET)

What the recording shows working, end to end, on live data:

- The feed badge reads LIVE with the provider, read-only flag and generation
  beneath it; the clock, quote card, ten-second candles and screener rows
  advance every few seconds with no reload.
- The scanner union admits the $1–30 band (ORBS at $1.02 appears), drops 33
  non-stock instruments and says so in the screener note.
- Running Up fires as an uptrend (BIAF 13:58, GRI 13:12, AEHL 13:07) with
  RTH pills; High of Day carries PM alerts from 08:03 and 08:24, so premarket
  prints reach the scanners.
- The board scores every desk name; the verdict states the one condition
  short (no live momentum event) and arms an entry, stop and target.
- Audio alerts are on, the legend is one click away.

What the recording exposed, fixed in this round:

- The board marked NTRB's 12.2M shares-outstanding proxy FAIL while the
  verdict marked it PASS. One rule now applies everywhere: under the cap the
  proxy proves float under the cap (pass, labelled SO); over the cap it proves
  nothing (unknown); a verified figure is compared directly.
- A Benzinga market wrap ("12 Health Care Stocks Moving In Thursday's Intraday
  Session") earned a red flame and a News PASS. Roundup headlines are now
  classified as such, carry no flame, and do not satisfy the news pillar.
- The quote card showed "$—" for spread while the board had a value; both
  now fall back to the provider's live bid and ask.
- The TradingView panes opened on a multi-day view for thin names; they now
  open on the session (1D) and the week (5D).

## 10. What remains before relying on it for day trading, concretely

Ordered by how much each one changes outcomes.

1. **A results ledger, in R.** Every armed plan should be recorded (symbol,
   time, entry, stop, target) and resolved by the tape: triggered or not,
   stop or target first, R gained or lost. Twenty sessions of that is the
   evidence that the setup, as this desk defines it, has an edge before any
   real money is at risk. Nothing on the desk does this yet; it is the most
   important missing piece.
2. **Halt detection.** IBKR reports a halted flag on each ticker. A halted
   name must show HALTED on the tile, invalidate any armed plan, and never
   fire an alert. Not wired yet.
3. **Real-time news.** Headlines are polled from Alpaca's free Benzinga
   relay. For a catalyst-driven strategy the headline has to arrive as it
   prints: IBKR sells Benzinga Pro through the API (provider code BZ, read
   with the same read-only connection), or Benzinga's own API pushes it.
   Either is a subscription decision.
4. **Verified float.** This account is not entitled to IBKR fundamentals
   (error 10358). The IBKR fundamentals add-on gives total float per name;
   until then the supply pillar is an upper bound or unknown, and float must
   be verified by hand before sizing.
5. **Level 2.** The ladder is simulated. NASDAQ TotalView through IBKR gives
   real depth on the same read-only connection. Until then, the bid and ask
   on the quote card are the only real book data.
6. **Faster discovery.** A runner that starts between two-minute scan rounds
   is seen up to two minutes late. A streaming scanner subscription (IBKR
   updates it every ~30 s) replaces the ten one-shot queries and the 150
   snapshot quotes per round.
7. **Execution discipline, by hand.** The desk places no orders by design.
   A written routine is needed: read entry, stop and target from the desk,
   enter a bracket order in the TWS paper account, size from the R risk
   typed on the desk, log the outcome in the ledger. Only after the ledger
   shows an edge in paper does any of this move to a live account.
8. **Operational hardening.** Run whole sessions for two weeks: TWS restarts
   overnight (the desk reconnects, but the morning start should be a single
   command), logs to a file, a daily health summary, and an automatic
   restart if the process dies.
9. **Cost awareness.** Snapshot quotes on names outside a streaming
   subscription are billed per snapshot by IBKR; the two-minute cadence and
   150-name cap keep that bounded. Raising either multiplies the bill.
10. **Scope honesty for the team.** The scanners are approximations of the
    course scanners, the pillars are the Confirmed ones, the mastery covers
    Basics chapters 1–6 only. Every number on the desk carries its label, and
    the review page states the limits. That is what makes it presentable.
