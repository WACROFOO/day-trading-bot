# Daily operating guide — using the workstation from today

> Education, simulation and process-building. Nothing here is a trade
> recommendation. Every threshold labelled **Confirmed course** comes from the
> authenticated Preview material; everything else is a transparent
> approximation you should calibrate against your own recorded observations.

## 0. What this can and cannot do today

Be honest about the feed before building a routine on it.

| Capability | Status today | Consequence |
|---|---|---|
| Universe scan for today's movers | Works (free, NASDAQ) | You get a real candidate list every morning |
| Real 1-minute bars and daily history | Works, **~15 min delayed** | Charts are real; the last 15 minutes are not there |
| Real news headlines with timestamps | Works (provider publish time) | The flame is real, latency is shown |
| Float | Often missing | Shown as an explicit proxy; the supply pillar fails rather than guessing |
| 10-second bars | Not on this feed | The micro chart says so instead of inventing candles |
| Level 2 depth | Not licensed | Simulated and labelled; deferred by your own decision |
| Live 1-minute entries | **No** | A 15-minute delay makes real-time execution impossible |

The delay does not block the three things that actually build skill:
**building the watchlist**, **rehearsing the funnel**, and **journalling
decisions in R**. It only blocks live execution — which you should not be
doing yet anyway.

## 1. One-time setup (15 minutes)

```bash
git clone <your repo>            # or pull the branch
cd day-trading-bot
pip install -r requirements.txt  # pandas, yfinance, streamlit, plotly, pytest
python -m pytest tests/ -q       # everything should pass
```

Verify the workstation runs on the deterministic fixture before pointing it at
real symbols — if this looks wrong, the problem is the install, not the market:

```bash
PYTHONPATH=src python -m momentum_platform.dashboard.server
# open http://127.0.0.1:8787, press Play, watch a full morning replay
```

Spend one sitting here. Learn the desk before you learn the market: drag cards
to the slots you want, expand the 1-minute chart with ⛶, click a scanner row
and watch every panel follow it. The layout is saved in your browser.

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
