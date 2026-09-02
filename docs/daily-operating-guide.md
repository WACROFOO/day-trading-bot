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
