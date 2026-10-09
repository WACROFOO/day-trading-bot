# The desk after the 07:41 recording — 2026-10-09

The owner's screen recording of 2026-10-09 07:41 ET (VEEA, then SAIQ) raised
eight items. For each one, this document says what was measured, what was
assumed, what was built and what could not be checked. The screenshots and
the stale-plan measurement are in
[`desk-recording-2026-10-09/`](desk-recording-2026-10-09/). The Running Up
measurement is in
[`../research/running-up-2026-10-09/`](../research/running-up-2026-10-09/).

**The bot's trading rules are unchanged** — gates, window and sizing. They
belong to the owner and change only by an amendment in
`docs/preregistration.md` §5. Everything below is display, discovery or read-only
data, and the replays in §4.2 and §4.8 check that nothing reached a decision.

## 1 · Provenance

| what | source | status |
|---|---|---|
| the owner's recording | 2026-10-09 07:41 ET, VEEA then SAIQ, as described in the request | **not in the repo.** VEEA and SAIQ for 2026-10-09 are not exported, so no minute of the recording is replayed |
| stale plans, measured | `research/daily/2026-10-06/` and `research/daily/2026-10-07/`: the desk's own 1-minute bars, rebuilt minute by minute from 07:00 to 11:29 ET through the desk's session builder (`desk-recording-2026-10-09/plan_life.py`) | REPLAY. The export holds no news, quotes or halts, so the catalyst reads UNKNOWN in both the before and the after runs |
| Running Up, measured | the 20 exported days 2026-09-11 … 2026-10-08, 214 name-days (`research/running-up-2026-10-09/measure.py`) | REPLAY, one price a minute (the close). Halts are inferred from the bars. News is UNKNOWN |
| screenshots of Level 2, huge orders and Time & Sales | a fake TWS (`tests/fake_ibkr.py`) behind the real server and page; every price, size and venue is invented | **SYNTHETIC.** The account has no depth subscription, so no live book has been seen |
| IBKR's depth API and error codes | interactivebrokers.github.io/tws-api, `market_depth.html` and `message_codes.html` (both pages call themselves deprecated in favour of IBKR Campus) | fetched 2026-10-09 |
| TradingView products | tradingview.com `widget-docs/faq/data`, `widget-docs/markets/north-america`, `free-charting-libraries`, `charting-library-docs/latest/quick-start`; the Lightweight Charts crosshair tutorial on tradingview.github.io | fetched 2026-10-09 |
| what he says | the corpus, through `scripts/corpus.py` and one named file at a time; each quote carries its video id and timestamp | read 2026-10-09 |
| the desk's thresholds | `src/momentum_platform/depth.py`, `src/momentum_platform/datasources/ibkr_depth.py`, `src/momentum_platform/tape.py`, `src/momentum_platform/order_math.py`, `src/momentum_platform/scanners/running_up_filters.py` | this session |

## 2 · What was considered

| # | the owner's item | outcome |
|---|---|---|
| 1 | The card is too long for a name with nothing to do, and "WAIT · hands off until the level" sits beside "no level yet". | built |
| 2 | Stale plans are drawn as if live. VEEA's 04:03 plan (ENTRY 5.44 / STOP 4.61, a 15.3 % stop, outside the bot's window) was priced in the order block at 07:41. SAIQ showed TARGET 6.72 / ENTRY 6.50 / STOP 6.39 from a plan stopped at 07:37. | built, measured |
| 3 | The five pillars need a clear visual. | built |
| 4 | Level 2 should be a default card, ready for the coming subscription. | built; no live book seen |
| 5 | Alert on a huge buy or sell. | built (Approximation) |
| 6 | Explain Time & Sales on the desk. | built |
| 7 | Charts: the TradingView widget, Advanced Charts, or Lightweight Charts extended. | evaluated: (c) built, (a) and (b) rejected |
| 8 | Running Up should catch every relevant candidate. | built, measured |

Three defects turned up along the way. All three are fixed (§3).

## 3 · What survived, and what did not

| option | outcome | why |
|---|---|---|
| (a) TradingView widget for the charts | ✗ rejected | *"Widgets can only display data provided by TradingView, and we don't have an API for feeding your own data into them"*, so no plan line can come from the desk. US stocks are "Delayed Stocks" from Cboe One on NASDAQ, NYSE and NYSE Arca, and NYSE American is not listed |
| (b) Advanced Charts fed from IBKR | ✗ rejected | *"These licenses are only available to companies for use in public web projects and/or applications"*, and *"we don't provide the Advanced Charts and the Trading Platform libraries for personal use, hobbies, studies, or testing"* |
| (c) Lightweight Charts, extended | ✓ built | *"Lightweight Charts™ are open-source under the Apache 2.0 license"*, and *"you can use the Lightweight Charts™ for personal projects"*. It is already the desk's chart engine (v4.1.3, vendored) |
| a share-count floor on the Running Up filters | ✗ not added | The method sets none pre-market (FILTERS.md: *"Pre-market volume has a CEILING and no floor"*). The measured cost: 43 of the filters' 151 false alarms are moves under 10,000 shares |
| listing every consolidated alert in every tile it touches | ✗ not done | Measured: +17 RUNs for 343 more rows, with one alert on two tiles. Only the 13 rows that showed on no tile at all are now listed |
| Running Up excluding names at their high of day (his rule, `knowledge-base/strategies/SCANNERS.md` §B4) | ✗ not applied | The owner's decision of 2026-09-23 (running_up 3.1.0) keeps runners at their high in this tile |
| ending the detector's "blackout" after a dead plan | ✗ not changed: it is a trading rule | It was measured in addendum 2026-10-06d, where D1 fails both readings (§4.2) |
| **defect:** a refused depth request turned the Time & Sales card to ERROR | ✓ fixed | found while taking the Level 2 screenshots (§4.4) |
| **defect:** an alert filed under `running_down` showed on no tile | ✓ fixed | found while measuring Running Up (§4.8) |
| **defect:** the measurement saw no halts, because a halt in the exported bars is a run of empty minutes rather than a gap | ✓ fixed: the measurement now reads such runs | found while measuring Running Up (§4.8) |

## 4 · Per item

### 4.1 · The card at a glance

| | before (`7aebccc`) | after |
|---|---|---|
| the face | The word and its reason, then "no level yet". Below: nine pillar and chart chips, the setup line, the tape, warnings and the order area | The word with what to do, the reason, the level (or "no price level") and five pillar tiles. "Why, in full" stays folded |
| the action | `WAIT · HANDS OFF UNTIL THE LEVEL` beside `no level yet` (IPDN 2026-10-06 08:30) | `HANDS OFF UNTIL THE MACD CROSSES BACK OVER ITS SIGNAL` · `no price level` |
| the order | An order area on WAIT and WATCH too, with "your risk" and "I passed" | **REVIEW only** |

Each verdict branch in `decision_card.build_card` sets its own action, so a
branch without a level never says "until the level". Before and after:
`before_card_ipdn_0830.png` → `after_card_ipdn_0830.png`, and
`before_card_jagx_1100.png` → `after_card_jagx_1100.png` (WAIT, "hands off
until it reclaims the VWAP", level 6.49).

### 4.2 · Only a live plan is drawn or priced

The rule, from the request: chart lines and the order appear only for a plan
that is live right now — inside its fill window, not stopped, not withdrawn
and not outside the bot's window. The detector now keeps each plan's life
(`pullback.PlanLife`): the bar it formed on, the decision at that bar's close,
and a fill window 3 minutes long (A10, `order_math.ENTRY_TTL_MINUTES = 3`). It
also records whether the plan formed inside the bot's window (`entry_session`:
*"pre-market 07:00–09:30, regular 09:30–11:20 (A8)"*) and how it ended.
`build_card` draws and prices only `live_plan(now)`. The page draws only the
card's plan, and stops the moment its `liveUntil` passes.

Measured on the two days with every minute replayed (`plan_life_output.txt`):

| | 2026-10-06 | 2026-10-07 | both |
|---|---|---|---|
| name-minutes on the desk | 2,640 | 2,430 | 5,070 |
| name-minutes with plan lines drawn, before → after | 307 → 43 | 168 → 20 | **475 → 63** |
| order blocks, before → after | 104 → 13 | 53 → 5 | **157 → 18** |
| … of which priced from a dead plan, before | 18 | 12 | 30 |
| detector plans, before = after | 91 on 10 names | 105 on 9 names | identical, plan by plan |

Why the 416 dropped drawings were dead: fill window closed 142 · stopped 137 ·
reached 2R 65 · stop broke before the entry 51 · formed outside the bot's
window 21. The lines that remain belong to plans still live (37 + 17), plus
the forming plan on a REVIEW (6 + 3) — `after_ipdn_0920_forming.png`,
`after_ipdn_0923_review.png` ("live until 09:26").

**The blackout, found and left alone.** While a dead plan waits for its stop
or its 2R, the detector cannot form another plan. That cost 763 name-minutes
on the two days (482 + 281). A detector without the blackout (D1) was measured
in addendum 2026-10-06d and failed both readings. In the holdout it nets
−0.525 / −0.547 R a trade against B's −0.477 / −0.475, and in reading A it
totals −1,003.1 R against −712.2 R
(`research/paper-exercise/reports/detector_variants_output.txt`). It is a
trading rule, so it stays. The card now says it outright: "no live plan — the
HH:MM plan holds the detector until its stop X or 2R Y".

### 4.3 · The five pillars

There are five tiles: price · gain · RVOL · float · news. Each shows ✓ / ✗ /
?, the value and the threshold. Above them, a count out of 5 with the minimum
marked (A5: 4). The values are the server's lamps (`card["pillars"]`, read
from the cascade's own pillar gate), and the page computes nothing. Unknown
counts as not passed, as it does in the cascade. See any `after_card_*.png`.

### 4.4 · Level 2

The card reads one book: the selected name's, on the desk's own read-only
connection. It uses `reqMktDepth(contract, numRows, isSmartDepth=True)` and
releases the book with `cancelMktDepth` the moment the selection moves. What
IBKR's pages say:

- SmartDepth gives *"aggregated data from all available exchanges"*, and
  *"the marketMaker field will indicate the exchange from which the quote
  originates"*. The ladder therefore shows price, size and exchange.
- Depth requests are limited *"with a minimum of three and maximum of 60"*.
  The card holds one.
- IBKR states no maximum row count: *"the TWS will simply return the available
  entries"*. ib_async's docstring says 5. The desk asks for 10 and retries an
  unexplained refusal once at 5.

| state | when | what the card says |
|---|---|---|
| STARTING | the request is out | — |
| LIVE | the book is flowing | the ladder: asks above the inside, bids below, one shade per price level, the venue on each row |
| NO SUB | IBKR 354 *"Not subscribed to requested market data."*, 10090 *"Part of requested market data is not subscribed."*, 10186 *"Requested market data is not subscribed. Delayed market data is not enabled"*, or 10089 / 420 | **IBKR's code and words, as sent**. The desk asks again every 120 s, so the book appears by itself once the subscription is live (`after_l2_nosub_SYNTHETIC.png`) |
| PAUSED | 1100 *"Connectivity between IB and the TWS has been lost."*, or 10197 *"No market data during competing session"* | resumes on 1102; 1101 (*"restored- data lost."*) empties the book and asks again, as the tape does |
| — | 316 *"Market depth data has been HALTED. Please re-subscribe."* / 317 *"…RESET. Please empty deep book contents…"* | re-subscribes / empties the book |
| ERROR | anything else, 309 (*"Max number (3) of market depth requests has been reached."*) included | the words; asked again at once with 5 rows, then every 120 s |

The feed is read-only. `ibkr_depth.py` makes no order, cancel-order or
open-order call, and two guards check it: the IBKR guard in
`tests/test_ibkr_desk.py` (extended to the tape and depth modules) and
`test_the_depth_adapter_has_no_order_surface`. Tests run against a fake IB:
`tests/test_depth.py` and `test_the_selected_name_gets_its_book_end_to_end`
in `tests/test_live_ui.py`.

**The defect it surfaced.** IBKR's 354 on the depth request names the same
contract as the tape. For an id it does not know, the tape falls back to the
symbol, so it read the refusal as its own. Every name the owner selected
without a Level 2 subscription would have shown its Time & Sales as ERROR
while the prints still flowed. Now the depth feed remembers every request id
it made (`DepthFeed.owns`), and `IbkrDesk._on_tws_error` hands a book's error
to the book alone. `test_a_refused_book_never_turns_the_tape_to_error` fails
on the old router and passes now.

**What a live book costs** (`docs/day-runbook.md`, "Level 2" — researched
2026-10-09, not verified on the account): $22.00 a month on the live user,
shared to paper, or $17.50 if Networks A, B and C are already held.

### 4.5 · Huge orders (Approximation)

| what alerts | definition (`depth.py`, `tape.py`) |
|---|---|
| a huge order appears or goes | a price level within the first 3 of its side, holding at least 10× the book's median level and never under 2,000 shares, or 25,000 shares outright. When it goes, it is *taken* if the tape printed at least half of it at that price in the last 10 s, otherwise *pulled* |
| a big print | a print at or over the tape's big-print line: 10× the median print, never under 2,000 shares |
| how often | at most one banner and one sound per kind and side every 20 s, for the selected name, live only. A name's first book and first tape count as history, not news. The same side and price says nothing new for 30 s |

What the corpus gives is the need, not a size. *"What actually requires
depth-of-book is `large seller / buyer` (104 mentions, 31 videos)"*
(`knowledge-base/strategies/PARAMETERS.md` §10). The exit signal "large seller
appears on Level 2" counts 47 (§6). The entry checklist reads *"No large seller
sitting on the ask above you"* (`knowledge-base/strategies/PLAYBOOK.md`). Every
number in the table is this desk's own. The alert is a fact and never a gate:
nothing but the page's banner reads it. Synthetic:
`after_l2_tape_alert_SYNTHETIC.png` (a 30,000-share bid one level under the
inside, and a 25,000-share print at the ask) and `after_l2_ladder_SYNTHETIC.png`.

### 4.6 · Time & Sales, explained on the desk

The Legend gains a section on Level 2 and one on Time & Sales. The Time &
Sales card's header carries the one-line hint *"every trade as it prints · ▲
at the ask = buyers lifting · ▼ at the bid = sellers hitting"*. On a REVIEW,
the decision card adds: *"at the trigger, read the Time & Sales: ▲ green
prints at the ask = buyers lifting the offer · ▼ red at the bid = sellers
hitting it"*.

| why it is there | his words | where |
|---|---|---|
| at the entry, his eye is on it | *"So, where is my eye? It's mostly on the time and sales right here and on the ask price. And I glance over at the chart"* | ZfwTJAMLroA @01:08:06 |
| what strength looks like | *"What does continued strength look like? Green on the tape. We want to see more buy orders coming through."* | KzVbXzkoZkA @00:54:47 |
| what each one shows | *"level two, um, shows you the buy and sell orders right here … time and sales, so this shows you where people are buying and where they're selling"* | ZfwTJAMLroA @01:44:36 |
| together | *"they really should always just be together because you can't really, at least for my strategy, use one without the other."* | ZfwTJAMLroA @01:45:34 |

The Legend gives three steps: ① **the word** — REVIEW, or there is nothing to
do · ② **the level** — the trigger line on the 1-minute chart · ③ **the tape
at the trigger** — green prints at the ask as the price reaches it. That last
step is the reader's call: a fact, never a gate.

### 4.7 · Charts

| option | what it gives | what rules it out, or in |
|---|---|---|
| (a) TradingView widget | TradingView's own charts and data | *"Widgets can only display data provided by TradingView"*, and *"As per their requirements we are only allowed to stream delayed data"*. *"Paid upgraded plans do not affect the data in the widgets."* US stocks: NASDAQ, NYSE and NYSE Arca from Cboe One, all "Delayed Stocks"; NYSE American is not listed. The desk could not draw its plan on it |
| (b) Advanced Charts (Charting Library) fed from IBKR | TradingView's full chart UI: "110+ drawing tools and 100+ indicators" (`src/momentum_platform/dashboard/web/README.md`) | licence: companies, public projects, not personal use (quoted in §3). *"The library is not redistributable. It is prohibited to use any part of the library in public repositories."* It is distributed from *"a private GitHub repository"* after an access request form |
| (c) Lightweight Charts, extended | the engine the desk already runs | Apache 2.0, personal use allowed. Crosshair sync is documented: `setCrosshairPosition` *"allows the crosshair position to be set programatically … For example if you want to synchronise the crosshairs of two separate charts."* |

Built on (c):

- one crosshair across the 1-minute, 5-minute and 10-second panes;
- one session VWAP on every pane;
- live, the forming 1-minute candle moves with each 10-second bar;
- on by default, only what the verdict reads: VWAP, the 9 EMA and MACD on
  the 1-minute, volume, the HOD and pre-market high, and the live plan. The
  20 and 200 EMAs are one click away in ƒ.

The 1-minute stays the primary chart and follows the selection. The drawing
tools (level, trend, measure in R, zone, erase) were already in
`chartTools.js`, and the footer credits TradingView Lightweight Charts™.

### 4.8 · Running Up

There are four triggers, and any one fires. Each one's source is in the
module docstring of `src/momentum_platform/scanners/running_up_filters.py`,
and every threshold is an Approximation (§B4: *"Move size and window:
`UNKNOWN`"*).

| trigger | label | fires when | where the number comes from |
|---|---|---|---|
| `pct_in_n` | `5%·low` | the price is 5 % over the lowest low of the last 5 one-minute bars, on a bar that traded and is not red | the platform's 5-in-5 squeeze, *"kind of like a pre-alert for something possibly that will go up 10 in 10 minutes"* (yg5E_mqGFGg @00:17:16) |
| `vol_surge` | `VOL` | +3 % in 2 minutes with 5-minute RVOL ≥ 2× | *"Transparent starting point: 3% in 2 minutes with five-minute RVOL of at least 2x."* (`CLAUDE_ROSS_TRADING_MASTERY_2026-08-31/references/source-analysis.md`, "Running Up") |
| `new_hod` | `HOD·vol` | the high and the close both above the prior HOD, RVOL ≥ 2× | the same file, "Five Pillars HOD alert": *"Recommended starting five-minute RVOL threshold: 2x."* |
| `halt_resume` | `HALT↑` | the first print after an official halt the name ran into | `knowledge-base/strategies/PARAMETERS.md` §8b: *"halted_up → usually resumes higher"*, and the named setup is the dip and rip on resumption |

They are qualified by $2–20, a verified float over 20M (only a verified one
silences them), and 07:00–11:30 ET. There is one alert per leg, re-armed after
three quiet bar minutes. The scanner runs last, so the existing tiles keep
every row.

The ground truth was fixed before scoring (an Approximation). A **RUN** is
≥ 10 % low → high within ≤ 10 minutes, low $2–20, high 07:00–11:30, ≥ 50,000
shares. There are 523 on 104 name-days. A false alarm is an in-window, in-band
alert inside no **MOVE** (≥ 5 % in ≤ 5 minutes, ≥ 10,000 shares).

| on 20 days (`results.txt`) | RUNs caught | first alert after the low (median) | false alarms (share of in-window alerts) |
|---|---|---|---|
| the Running Up tile, before | 389 / 523 | 5.0 min | 210 (16 %) |
| **the Running Up tile, after** | **439 / 523** | **3.0 min** | **312 (16 %)** |
| both tiles on the desk, before → after | 416 → 456 | 5.0 → 3.0 min | 259 → 361 |
| `pct_in_n` alone | 413 | 3.0 min | 104 (11 %) |
| `vol_surge` alone | 246 | 5.0 min | 67 (14 %) |
| `new_hod` alone | 101 | 9.0 min | 43 (24 %) |
| `halt_resume` alone | 20 (27 alerts) | 15.0 min | 3 (11 %) |

- **Every day** catches at least as many RUNs after as before, and every day
  has at least as many false alarms.
- **The filters' 151 false alarms:** 49 moves under 5 % (`vol_surge` and
  `new_hod` fire smaller by design), 59 moves that started under $2 (the alert
  is in the band but the low was not) and 43 moves under 10,000 shares.
- **RUNs with no alert anywhere near them, on either tile: 41 → 11.** Nine of
  the eleven are a single one-minute bar, with the low and high in the same
  minute. A replay gives one price a minute; live, the forming minute is read
  on every print.
- **Discovery only**, checked on all 20 days. With the filters silenced, every
  plan, cascade verdict and card word is identical, and so is every alert row
  the desk's own scanners showed. `tests/test_running_up_filters.py` checks
  the same on the desk's replay fixture.
- **Fixed on the way.** The router files same-name alerts of one moment under
  the first scanner to fire. Filed under `running_down`, which has no tile, an
  alert reached no tile at all. That happened 13 times, among them BENF
  2026-09-23 09:40, the halt resumption. The Running Up tile now lists such a
  row, labelled by its member. The measurement's first run also counted 0
  halts, because an exported untraded minute is a zero-volume row rather than
  a gap. It now reads 70 halts.

### 4.9 · Follow-up the same day: a smaller card, one stack, cards that move

The owner, after reading the above: *"make the verdict order card smaller with
non key info (everything below the news) as an expandable section and level
two down and the time and sales even below and make sure news catalyst is
clearly displayed in simple words"*, then *"make sure i can drag and drop these
cards easily and swap them"*.

| | before | after |
|---|---|---|
| the card's face | the word, the level, the pillar tiles; on REVIEW the tape line, the hint and the whole order under them | the word, the level, the pillar tiles and **the news in plain words**. Nothing else |
| everything below the news | partly on the face, partly in "Why, in full" | one fold, **Details**, closed until opened and remembered (a new key, so a desk that kept the old fold open starts small). The order comes first, on REVIEW only, and the closed fold's line says "order". An open position stays on the face |
| the news | a tile reading `no feed` / `STRONG` / `today`, and the full read in the fold | a line under the tiles: STRONG · SOME · WEAK · NONE · ?, one sentence, the headline and any red flag. The words come from the server (`catalyst.card_read`, `plain`) and the grade is unchanged. `after_card_dvlt_news.png`: *"FDA news, today 09:44 — real company news"* |
| the right column | the card over Level 2 beside the Time & Sales | one stack: the card, Level 2, the Time & Sales (layout v13) |
| Level 2 | the ten asks first, so the bids sat below the fold | opens on the inside quote; your own scroll holds for 10 s |
| dragging cards | **only the three scanner tiles could be picked up with a mouse.** The charts, the board, the card, Level 2 and the tape had no draggable header, and the old test dispatched synthetic drag events, which skip that check | every card's header is a handle. `test_ui_every_card_swaps_with_a_real_mouse_drag` drags with the mouse; it fails on the old page and passes now |

## 5 · What this could not check

- **A live book.** The account has no depth subscription. LIVE, the ladder
  and the huge-order banner have only been seen on a fake TWS. Pre-market
  depth, depth on the paper login and NYSE American coverage are unconfirmed
  (`docs/day-runbook.md`, "Level 2").
- **The row count IBKR serves.** 10 rows are asked for, with a fallback to 5,
  and neither has been seen on a live account.
- **The recording's own minutes.** VEEA and SAIQ for 2026-10-09 are not
  exported. The stale-plan rule is shown on 2026-10-06 and 2026-10-07 instead.
- **Running Up live.** The replay reads closes, so one-minute wicks are
  invisible to it. Its halts are inferred and its news is UNKNOWN. The ground
  truth is this desk's, not his, and the filters' thresholds are starting
  points that have not been fitted.
- **What a huge order or a big print is worth.** Nothing in this repository
  has measured it. That is why the alerts are facts and never gates.
- **The sound.** The headless browser counts the beeps but cannot hear them.

## 6 · Verdict

All eight items are on the desk, and the trading rules are untouched.

- **Stale plans are gone.** Drawn lines fell from 475 to 63 name-minutes, and
  order blocks from 157 to 18, on the two measured days.
- **The card answers at a glance**, and its action now matches its level.
  Since the follow-up, the face ends with the news in plain words and
  everything else, the order included, is one click away under Details.
- **Every card can be dragged and swapped**, not just the scanner tiles.
- **Level 2 is ready and waiting for the subscription.** The work also found
  and fixed a defect that would have taken the Time & Sales down on every name
  selected without one.
- **Running Up catches 50 more RUNs (439 vs 389 of 523)**, two minutes earlier
  at the median, at the same false-alarm rate. That rate on more alerts means
  about five more false alarms a day. If that is too noisy, `new_hod` has the
  worst rate (24 %) and would be the first to drop.
- **For the owner, if wanted:** the depth subscription, and any amendment
  about the detector's blackout. D1 was measured worse, so it stays.
