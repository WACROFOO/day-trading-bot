# Daily operating guide — using the workstation from today

> Education, simulation and process-building. Nothing here is a trade
> recommendation. Every threshold labelled **Confirmed course** comes from the
> authenticated Preview material; everything else is a transparent
> approximation you should calibrate against your own recorded observations.

## 0. What this can and cannot do today

Be honest about the feed before building a routine on it.

| Capability | Status today | Consequence |
|---|---|---|
| Universe scan for today's movers | Works (free, ~11,000 names) | A real candidate list every morning |
| 1-minute bars and daily history | Works, **real-time on IEX** | Charts are live, not delayed |
| News headlines with timestamps | Works (provider publish time) | The flame is real, latency is shown |
| SEC filings / dilution risk | Works (free, no account) | `catalyst_score.py` sees live takedowns |
| Float | Not published free | Shown `unknown`; the supply pillar fails rather than guessing |
| 10-second bars | Not on this feed | The micro chart says so instead of inventing candles |
| Level 2 depth | Not licensed | Simulated and labelled; deferred by your own decision |
| Absolute volume | **Understated** | IEX is one venue. Ratios survive, raw share counts do not |

### The one caveat that matters

The free feed is **IEX**, a single exchange, and it is genuinely real-time —
prices, highs and percentage moves are trustworthy. But IEX carries a slice of
total US volume, so **absolute volume is understated**. Relative volume still
works, because the scanner divides today's IEX volume by prior days' *IEX*
volume — both sides come from the same venue, so the ratio holds. Never compare
an IEX volume figure against a website quoting consolidated volume.

What is still missing does not block the three things that build skill:
**building the watchlist**, **rehearsing the funnel**, and **journalling
decisions in R**.

## 1. One-time setup (15 minutes)

```
cd day-trading-bot
bash scripts/setup.sh
```

That one command finds your Python, takes your Alpaca paper keys, writes a
git-ignored `.env`, runs the tests and proves the connection. The desk core
needs no third-party packages — it is Python standard library only.

Verify the workstation runs on the deterministic fixture before pointing it at
real symbols — if this looks wrong, the problem is the install, not the market:

```
bash scripts/start.sh
```

Open http://127.0.0.1:8787 and press Play for a full morning replay. If the
live feed is unavailable the launcher says why and opens the recorded session
instead, so the desk always comes up.

Spend one sitting here. Learn the desk before you learn the market: drag cards
to the slots you want, expand the 1-minute chart with ⛶, click a scanner row
and watch every panel follow it. The layout is saved in your browser.

## 1b. The commands you will actually type

```
./now                     phase header + board for the saved watchlist
./now MSGY WYHG           board for these names (watchlist untouched)
./now --set MSGY WYHG     save the watchlist, then board
./now --scan              scan the market first, then board the survivors
./now --scan --desk       ...and open the workstation on them
bash scripts/morning.sh   scan, grade catalysts, open the desk, keep re-scanning
```

The board is one row per ticker: last, change, RVOL, the gate scorecard
`P F C R V E` (price band · float · catalyst · still rising · above VWAP ·
above 9 EMA; `+` pass, `-` fail, `?` unknown), a verdict word and the catalyst
read. `F` comes from the company's own SEC shares-outstanding figure, which is
an upper bound on float: `+` proves float is under 20M, `?` means the bound
is above it and float is genuinely unknown.

Verdict words are vocabulary, not instructions: REJECT on any hard fail, WATCH
while the chart or catalyst is incomplete, REVIEW when everything is green
inside the session window, LOG outside it.

### Live mode

With `--alpaca` the desk is live: the server rebuilds the session every 60
seconds and the page follows the newest bar on its own (scrub back to study a
pullback and it leaves you there until you return to the live edge). The badge
reads **LIVE**. `morning.sh` adds `--rescan 5`: every five minutes the market
is scanned again and any new runner that passes the pillars joins the desk
without a restart, so Running Up and HOD report the tape as it is now.

IEX is real-time — there is no 15-minute delay on this feed. It is one venue,
so absolute volume is understated; the relative-volume ratios compare IEX to
IEX and hold.

### Windows

The Python runs natively; only the `.sh` launchers do not. Use
`powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -Ibkr` and see
`docs/windows-setup.md` for the full path from a clean machine.

### Live on IBKR — the real tape, read-only

This is the mode to use once TWS runs on your Mac. It replaces the single-venue
IEX picture with the consolidated tape and replaces "rebuild every 20 s" with a
stream: five-second bars and quotes reach the page as they happen.

```
cd ~/day-trading-bot
bash scripts/start.sh --ibkr
```

or, to start from names you already chose:

```
bash scripts/start.sh --ibkr CHPT,AEHL
```

What has to be true on your machine:

- TWS is running and logged in. Edit > Global Configuration > API > Settings:
  "Enable ActiveX and Socket Clients" ON, "Read-Only API" ON, socket port 7496.
- Your account has real-time NASDAQ data (Network C/UTP). If TWS only has
  delayed data the desk refuses it and says DELAYED; it never shows a delayed
  print under a LIVE badge.
- `python3 scripts/ibkr_preflight.py` prints "OK — live, read-only". The
  launcher runs it for you and explains each failure.

What the desk does in this mode:

- Client 27 streams the desk symbols (a quote line and a five-second bar line
  each, up to 25 symbols); client 28 runs ten NASDAQ scanner queries every two
  minutes and puts new runners in the band on the desk. Neither client can
  place an order: the connection is opened read-only and the code has no order
  method (a test fails if one appears).
- The ten-second pane is built from real five-second bars; a candle exists only
  when both halves arrived. Minutes are the sum of their ten-second candles.
- The header badge reads LIVE, STALE (no bar for 20 s in regular hours, 60 s
  extended), DELAYED or OFFLINE. The desk reconnects on its own and resubscribes
  once, and the badge shows the generation and reconnect count.
- There is no replay transport on a live desk. The page sits on the live edge
  and updates in place; it does not reload, so your zoom stays where you put it.
- The screener card says "Union of 10/10 NASDAQ scans … not an exhaustive
  list". That is what a scanner union is. The chart still defines the setup.
- Headlines still come from Alpaca's free news endpoint when your keys are in
  `.env`; float is still the SEC shares-outstanding upper bound. IBKR has
  neither for free.
- The centre column is TradingView's own chart, large on top (1 minute,
  their toolbar, drawing tools and indicator dialog, extended hours on), with
  TradingView's 5-minute chart and the desk's 10-second micro pane side by side
  beneath it. TradingView shows US stocks 15 minutes delayed to a viewer who is
  not signed in to tradingview.com (their "D" badge); sign in there in the
  same browser and the pane follows your entitlement. Nothing on this side
  changes their delay, and the desk's numbers stay on the IBKR feed either
  way. The desk's own 1-minute, 5-minute and daily panes (VWAP, 9/20/200 EMAs,
  entry, stop and target drawn) sit in the tray (⊞ Cards) — click one to send
  it to the last card you clicked, or drag it onto the card it should replace.
- The desk shows one trading day: from 04:00 ET to now. At startup it asks
  IBKR for the minutes since 04:00 rather than "one day", which at 04:03 hands
  back the previous session; a desk left running rolls over at 04:00 ET, drops
  yesterday's tape, re-reads the previous close, and the page clears its alert
  timeline and arrival memory. Before 04:00 ET the desk shows the last
  completed session and dates itself accordingly.
- The right column is the Five Pillars check, then Level 2, then the setup
  verdict. In a column the board reads symbol, last, gain, five pillar chips
  (P, G, R, F, N — green PASS, red FAIL, amber UNKNOWN) and the score out of
  five, best first; hover a chip for the value behind it, widen the column past
  640 px and the full thirteen-column table comes back. The list card at the
  top left shows only the names that pass the hard gates; the board shows why
  the others do not. The screener and the alert timeline are in the tray.
- The scanners rebuild every 3 seconds from the live store and the page
  refreshes the moment a rebuild lands; the scanner union on client 28 runs
  every 120 seconds by default (`--ibkr-rescan 60` to run it every minute —
  each round quotes up to 150 names by snapshot, which IBKR bills per snapshot
  on names your streaming subscription does not cover).
- Scanner tiles carry the feed's real state — LIVE, STALE, DELAYED or
  OFFLINE — from the provider health, never REPLAY, on a live desk.
- Level 2 stays labelled SIMULATED. Real depth needs an IBKR NASDAQ TotalView
  subscription; without it TWS gives top of book only, which the quote card
  already shows as bid × ask.
- Two price bands. The Five Pillars analysis keeps the Confirmed $2–20 and
  cannot be widened; the desk ADMITS a wider band of your own ($1–30 by
  default, `DESK_PRICE_MIN` / `DESK_PRICE_MAX` in `.env`) so a runner just
  outside the pillar is still seen, with its price cell FAIL.
- Float on the board says where it came from: IBKR fundamentals total float
  (verified), SEC shares outstanding (upper bound), or unknown. UNKNOWN never
  counts as a pass.
- The scanner union drops leveraged ETFs, ETNs, funds, warrants and units by
  instrument type; the screener note says how many. A 2x daily ETF is not a
  small-cap runner.
- Running Up now means an uptrend, not a spike: up ≥3% over the last 10
  minutes, a fresh 10-minute high in the last 3, price above the 10-minute
  VWAP, liquid, one alert per leg. Approximation.
- **A sound on every new alert.** The arrival memory was keyed by symbol, so
  a second Running Up leg on the same name inside ten minutes made no sound at
  all; it is keyed by the alert now. Only an alert whose own minute is within
  three minutes of now rings — a name the scanner adds mid-session arrives
  carrying its whole morning, and that is history landing late, not twenty
  events firing. Browsers hold a page's audio until it has been clicked once:
  until then the Alerts button shows 🔕 and says so, and the first click
  anywhere unlocks it.
- **The timelines are ordered by the alert's own minute**, never by when the
  page first heard of it. A symbol added at 10:09 was putting its 07:38 alert
  at the top of a grid headed TIME.
- **Top gainers ranks by change from the previous close** — premarket and
  regular alike — not by relative volume. RVOL stays a gate and a column.
- **Scanner grids tick rather than lurch.** A rebuild is pushed as the new
  minute alone (about 8 KB: that minute's ranked lists, its alerts, and every
  symbol's metrics). The page used to refetch the whole session for it, which
  on a ten-name desk at midday is over 1.6 MB every three seconds. The full
  fetch remains the reconciler: whenever the symbol set changes, and once a
  minute regardless.
- **An unknown float says why it is unknown** — not in EDGAR's ticker list, no
  shares-outstanding fact filed, or the lookup failed — and is retried every
  ten minutes instead of being asked for once at subscribe time. EDGAR's
  ticker map is re-downloaded on a miss (a company that listed since the last
  weekly refresh was invisible), and the us-gaap cover-page facts are read
  when the dei one is absent, labelled "shares outstanding" or "shares
  issued". Both bound float from above; neither is float.
- **A live desk opens on the live edge and stays there.** A recording opens
  eight minutes before the bell, which is where the interesting part starts.
  That line ran on live desks too, so every live session started parked at
  09:22 — and the follow-the-edge rule refused to catch up from there, leaving
  every card, list and chart on that one minute for the rest of the session
  while the header still said "live". Stepping back in time is now a
  deliberate act: an alert row click selects the name only, the alert's detail
  carries a "Show the desk at HH:MM" button, and while the desk is parked the
  header chip reads `paused HH:MM` in amber and clicking it returns to live.
- **The lag chip describes the frame on screen.** One of its two callers used
  the newest frame instead, so the chip could say "live" over cards parked
  twenty-four minutes in the past.
- **A list row shows the RVOL it was judged on.** The column carried the daily
  measure while the gate used the time-of-day one, so a name admitted at 30x
  read 1.3x and looked like a scanner bug. The daily figure is in the cell's
  tooltip.
- **TradingView panes default to extended hours**, so their chart covers
  premarket rather than starting at 09:30 beside a desk that is already
  moving.
- **RVOL is measured against the same clock time.** Today's volume divided by
  the mean of prior FULL days is what the desk used to show, and before the
  open it cannot pass: at 08:53 a runner with 93,000 premarket shares against a
  2.2M average day reads 0.04x, so the RVOL pillar failed on every name and the
  Top gainers list was empty all morning. The desk now pulls ten sessions of
  five-minute bars per name and compares today's volume with the median the
  same name had traded by the same clock time. On 2026-09-04 that reads about
  7.7x for AOUT, which is what an independent screener showed. The R chip's
  tooltip says which measure produced the number and what the baseline was;
  the daily figure stays on the row. Threshold Confirmed, method Approximation.
- **An empty list says why it is empty.** The card counts the desk and names
  the blocking pillar ("10 names on the desk · blocked by RVOL on 10 (best
  0.83x of 5x needed), price on 2, gain on 4"). When the tape itself has
  stopped the event tiles say so, because those scanners read bars.
- **A live feed with a dead tape recovers itself.** TWS loses and restores its
  market-data farm (errors 1100/1101/2103/2104) without dropping the API
  socket. Quotes come back by themselves; the five-second bar streams often do
  not, and nothing reports it — the desk then shows a live badge, a live price
  and charts frozen at the last bar before the flap. When quotes keep arriving
  and no bar has for five minutes, the desk re-requests every quote and bar
  stream and refills the gap, at most once every five minutes, and says so in
  the log.
- The feed chip only counts a CHANGED quote as an arrival. It used to stamp
  its clock on every poll, so "live" meant "a ticker object exists".
- Liquidity for Running Up and HOD Momentum is 25,000 shares in the last five
  minutes OR at least three of the five pillars passing (Approximation, not a
  Warrior setting). Before the open a name like a 4/5 on the board trades thin
  tape; the pillars, not the volume floor, let its fresh high through. The
  alert's strategy tag says which gate admitted it (`volume_5m` or
  `pillars_passed`).
- The header is one slim row: brand, ET clock, session badge, feed chip, and
  the buttons. The chip beside the clock says whether the desk is receiving:
  `live` while quotes or bars arrived in the last 90 seconds; `live · last
  print HH:MM` when the feed is alive but the newest bar is older than five
  minutes — thin premarket tape, IBKR sends no 5-second bar without a trade,
  so a name that last printed at 04:00 shows that time rather than an alarm;
  the age in amber, then red, only when NOTHING has arrived; `no prints yet`
  when nothing has traded since 04:00 ET. A green feed badge means the
  CONNECTION is alive; the chip tells you the numbers under it are moving.
- The alert grids read Time, then the move (`PM %` before 09:30, `Day %`
  after, both against the previous close), then Symbol, Price and the
  strategy label. Hover the time for the age.
- Minute history is re-pulled one symbol at a time every 20 seconds, so the
  session keeps advancing even on a name that prints no trades for an hour.
  One symbol per cycle keeps the desk inside IBKR's historical-request pacing
  limit of roughly 60 requests per ten minutes.
- Audio alerts are on by default on a live desk; the first click or key
  unlocks the browser's sound. New alerts beep once at the highest severity
  and flash the tile. The A key toggles; the ? key (or "? Legend" in the
  header) opens the legend that explains every pill, state and verdict.

### Premarket, honestly

IEX is one venue. Before roughly 07:00 ET a $2–20 microcap may have printed
on other venues (what TradingView shows) and not once on IEX. Then the desk:

- says so in the header note and steps back to the last session IEX carried;
- shows **IEX last print** with its time on the quote card, so a thin tape
  reads as "IEX last print 04:12" rather than as silence;
- offers the **TradingView card** (drag it from the Cards tray): TradingView's
  own chart for the selected symbol, with their consolidated premarket price.
  It is their data under their terms and cannot draw this desk's entry, stop
  or target — the annotated panes do that.

The only thing that gives the scanners consolidated premarket volume is a
consolidated feed: `ALPACA_FEED=sip` in `.env`, which is Alpaca's paid tier.
Nothing free provides it. Decide that with the journal in hand, not before.

### The screener card — the current situation, at every time

The tall right card is the screener: **every name in the price band that is
moving in the current session**, refreshed every 60 seconds on the server and
polled by the page every 20, independent of the desk's bars. Each row shows
price, change against yesterday's close, the source, and how old the print is.

- **Yahoo · delayed** — consolidated premarket/regular/after-hours quotes,
  about 15 minutes behind, unofficial (no key, no contract). Before the open
  this is the only free number that reflects a move IEX has not printed.
- **IEX · real-time** — the entitled feed, one venue. Thin before ~07:00 ET,
  whole from 09:30.

Click a row: if the name is on the desk it is selected; if not, the server
adds it and it joins on the next refresh (the desk holds up to eight). The
scanners and the verdict still run on IEX bars — the screener finds, the
entitled feed decides. If Yahoo is unavailable the card says so and shows
IEX; it never goes quiet without a reason.

### Following live, with the delay you accept

1. **Discovery** is the screener (Yahoo, delayed). Watch the top rows.
2. **The desk** is IEX (real-time, sparse premarket). Click a screener row to
   put a runner on it; from ~07:00 ET its IEX bars fill in, at 09:30 they are
   whole, and the scanners and verdict work on them.
3. **The TradingView card** shows the consolidated chart for the selected
   symbol on TradingView's delay rules.

Two different clocks on one screen is the honest picture of a free stack. The
paid consolidated feed (`ALPACA_FEED=sip`) collapses them into one.

### Live refresh

A live desk refreshes **every 20 seconds** — incrementally, fetching only the
prints since the last bar, so it stays inside the free tier's request budget.
Zoom survives the refresh: each pane hands its visible range back after the
reload. `--refresh SECONDS` changes the cadence.

### Screener columns and filters

Every row carries its listing exchange and the registrant's country from SEC
records — a Chinese ADR on NASDAQ shows Cayman Islands or Beijing, a Canadian
cross-list shows British Columbia or Ontario. Hover a Five Pillars row for
name · exchange · country. The scan takes filters:

```
python3 scripts/alpaca_watchlist.py --exchange NASDAQ --exchange NYSE
python3 scripts/alpaca_watchlist.py --country China --country Cayman
python3 scripts/alpaca_watchlist.py --country "British Columbia" --country Ontario
```

### Your own price band

The Confirmed course pillar is $2–20. To widen the low end for your universe
put `DESK_PRICE_MIN=1` in `.env`. Every place the band appears then labels it
as **yours** — the board header, the verdict card, the scan — so the course
value is never misattributed.

## 2. The daily loop

Times are ET, with Paris in brackets (subtract 6 hours; for about three weeks
in late March and one week in late October the gap is 5 hours — set alarms from
the New York time and let your calendar convert).

### 06:45 ET (12:45 Paris) — before you look at a single chart

Write down, while you are calm, the three numbers you will not change today:

- risk per trade in dollars;
- maximum loss for the day (the corpus's convention: the same magnitude as your
  daily goal);
- maximum number of trades (1–2 while learning).

These are the only rules that work even if the entry logic does not.

### 07:00–09:00 ET (13:00–15:00 Paris) — build the list

```bash
python scripts/daily_watchlist.py --top 8
```

It prints today's survivors of the four computable pillars — price $2–$20,
gain ≥ 10%, RVOL ≥ 5×, volume ≥ 500k — ranked by relative volume, and emits a
comma-separated list. A full scan takes several minutes; `--limit 400` gives a
fast partial pass while you are learning.

**Zero names is a normal morning.** Do not widen the filter to manufacture a
candidate.

For each survivor, do the two things software should not do for you:

1. **Read the catalyst.** What happened, at what time, is it new, does it have
   quantifiable economic value, is there dilution risk? A shelf or an offering
   headline is risk context, not an automatic reject.
2. **Check the float.** If you cannot verify it, mark it unknown — the
   workstation will fail the supply pillar rather than pass on a proxy.

### 09:00 ET (15:00 Paris) — load the desk

```bash
PYTHONPATH=src python -m momentum_platform.dashboard.server \
  --live $(python scripts/daily_watchlist.py --top 6)
```

You now have, on real symbols: the Five Pillars scan with live arithmetic, the
Running Up and HOD Momentum alert streams, real headlines with flame ages,
1-minute / 5-minute / daily charts, and the setup verdict mirroring the Pine
dashboard.

### 09:30–11:30 ET (15:30–17:30 Paris) — rehearse, do not chase

The prime window. With a delayed feed your job is **decision reps**, not fills.

For every alert that appears:

1. Click the row. Everything links to that symbol.
2. Before reading the verdict card, say out loud: GO, WAIT or PASS, and why.
3. Then read the verdict card and compare. Where you disagree, the reason rows
   tell you which input you misread.
4. If it is a GO, write the plan: entry, stop, target, and the one-sentence
   invalidation. Type your dollar risk into the verdict card for the size.
5. Log it — even the passes. Especially the passes.

The scoring that matters is not P&L. It is: *did I reach the same decision the
funnel reaches, from the same evidence, before seeing the answer?*

### After 11:30 ET (17:30 Paris) — stop

The corpus is unusually consistent that the edge lives in the first two hours
and that midday is where discipline goes to die. Close the laptop.

### After 16:00 ET (22:00 Paris) — the drill that actually compounds

This is the highest-value use of a delayed feed, because after the close the
delay is irrelevant — the whole session is available:

```bash
PYTHONPATH=src python -m momentum_platform.dashboard.server --live <today's symbols>
```

Then scrub to 09:25 and press Play at 4×. You are replaying today's real market
with the same scanners, the same charts and the same verdict logic. Pause at
each alert, make the call, then step forward and find out. Twenty minutes of
this per day is worth more than a week of watching live.

## 3. Paper trading the plans

The workstation plans; the paper-trading app executes and remembers.

```bash
streamlit run src/paper_trading/app.py
```

- Enter the plan you wrote: entry, stop, target. Size comes from your risk, not
  your account balance.
- The **risk gate is a hard lockout**, not advice: max daily loss 6%, 50%
  giveback of the day's peak, green-to-red, three consecutive losses, 20%
  drawdown walkaway. It refuses the order and the latch survives a restart.
  Exits are never blocked.
- Fills carry $0.005/share commission and $0.02/share slippage. On a $0.10 stop
  that is a fifth of your risk budget — which is the point.

Log every trade with: pillars passed, setup type, pullback candle count,
planned versus actual entry, slippage, result in **R**, the first preventable
error, and one corrective exercise.

## 4. The progression

Adapted from the playbook's 30-session programme. Do not skip forward because a
week went well.

| Sessions | Focus | Done when |
|---|---|---|
| 1–5 | Recognition. No trades, not even paper. Score every candidate GO/WAIT/PASS and check against the verdict card. | Your call matches the funnel ~80% of the time |
| 6–10 | Replay only. Mark trigger, pullback low and 2R target on the 1-minute chart before pressing play. | You can find the structural stop without hesitating |
| 11–20 | Paper, one setup only — the first pullback. Identical risk every trade. Stop at the daily limit, every time. | 20 logged trades, rules followed on all of them |
| 21–25 | Robustness. Compare premarket / open / late morning, hot versus cold tape, wide versus tight spreads. | You can say which conditions your process fails in |
| 26–30 | Validation. Expectancy, profit factor, rule adherence, all in R, sliced by pillar score and time of day. | The edge is not one lucky trade, and adherence is above 90% |

Reaching session 30 is not permission to go live. That decision depends on the
statistics, the stability of your process, and whether you can take a
predefined loss without flinching — and on a real-time data feed, which you do
not have yet.

## 5. What to fix first, when you outgrow this

1. **A real-time market-data provider.** Everything else is downstream. Until
   this is chosen, live execution is off the table.
2. **A licensed news feed.** The flame is only as good as its timestamps.
3. **Level 2**, once the first two are working — you deferred it, correctly.

## 6. Guardrails worth repeating

- The scanner discovers a candidate. The chart defines the setup. The stop
  defines the size. The market decides the result.
- 4/5 pillars can qualify; 3/5 is normally a reject; even 5/5 can be a PASS on
  spread, extension, resistance or inadequate reward-to-risk.
- A flame means recent news. Not good news, not a passing setup.
- Never widen a stop. Never average down. Never re-enter to "make it back".
- A valid setup can lose. Process adherence is the only variable you control.
