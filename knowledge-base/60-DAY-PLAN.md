# The 60-day pre-market challenge

One atomic task a day, 30–45 minutes, each building on the last.

**Your window: 12:00–14:00 France = 06:00–08:00 ET.** Entirely pre-market. The
bell rings at 15:30 France, 90 minutes after you log off.

Three rules that follow from that and never change:

1. **Flat by 14:00 France.** You cannot hold a position into an open you will
   not see. No exceptions, ever.
2. **Paper only, for all 60 days.** Our own replication of these rules over 894
   sessions produced negative expectancy (`reports/2026-08-regime-filter.md`).
   The goal here is *process*, not profit.
3. **One task per day.** Not two. The compounding is in the sequence.

`L` = needs a live weekday market. `S` = study, do it any day.
On a weekend, skip forward to the next `S` task and come back.

---

## Phase 1 · Days 1–10 — The arithmetic and the terrain

You cannot trade what you cannot size. No charts this phase.

| # | | Task | Done when |
|---|---|---|---|
| 1 | S | Write your account rules on one sheet of paper: €500 account, **€10 max risk per trade** (2%), **€30 daily stop** (6%), 3 losses = done, max 2 names/day | The sheet exists and is next to your screen |
| 2 | S | Position sizing drill. `shares = risk ÷ (entry − stop)`. Do 20 by hand: entry 3.14 stop 2.98, entry 9.07 stop 8.25, … | 20 answers, no calculator errors |
| 3 | S | Expectancy. `(win% × avg win) − (loss% × avg loss)`. Compute the breakeven win rate at 1.5:1, 2:1, 3:1 | You can state why 40% wins at 2:1 beats 60% at 1:1 |
| 4 | S | Map your window. Write the FR↔ET table for 12:00–14:00 and mark what is happening in the market at each half hour | You can say what 13:20 France is in ET without thinking |
| 5 | S | Read `strategies/PARAMETERS.md` §13, the misreading traps | You can name three rules that are commonly misread |
| 6 | S | Halts. LULD bands, the 5-minute minimum, why size is the only defence. `corpus.py "halt" --show streams` | You can explain what happens to your order during a halt |
| 7 | S | Float. What it is, where to check it, why under 20M. Look up the float of 5 random tickers | 5 floats found from a source that reconciles with volume |
| 8 | S | The capital-structure check: reverse splits, shelf/ATM vs market cap, short % of float. Read `reports/2026-08-05-recap.md` | You can list the 4 free pre-open checks |
| 9 | S | TradingView: extended hours ON, the three screens, a 10-second chart. `TRADINGVIEW-SETUP.md` | Pre-market bars visible on your chart |
| 10 | S | **Week review.** Write your one-page rulebook from days 1–9 | One page. You will revise it on day 59 |

## Phase 2 · Days 11–20 — Reading the pre-market

Still no trades. You are learning to see.

| # | | Task | Done when |
|---|---|---|---|
| 11 | L | 13:00 FR: run the gapper screen. Write down 5 names. Do nothing else | 5 names on paper |
| 12 | L | Same, then score each on **price** ($2–20) and **float** (<20M) only | 5 names, 2 pillars each |
| 13 | L | Add pillar 3: find the actual catalyst for each. "No news" is an answer | Each name has a named catalyst or "none" |
| 14 | L | Add pillar 4. Relative volume is **not computed pre-market** — use raw pre-market volume against the 20-day average by eye | You know which of your 5 has real volume |
| 15 | L | Add pillar 5: up ≥10% **and still rising**. Check the last 30 minutes of the tape | You can say which names are fading |
| 16 | L | Full 5-pillar score, 0–5, on 5 names. Write the score before you look at what happens | 5 scored names, timestamped |
| 17 | L | Run `python scripts/premarket_dd.py SYM SYM SYM` on your list. Compare the tape to your scoring | You found one name the tape disagreed with you on |
| 18 | L | Run the capital-structure check on your top 2. Reject anything with a live ATM or a recent reverse split | At least one name rejected on filings alone |
| 19 | L | Build a 3-name watchlist with a written one-sentence reason each | 3 names, 3 reasons |
| 20 | S | **Week review.** Of everything you picked in days 11–19, how many actually ran? Count honestly | A hit rate, written down |

## Phase 3 · Days 21–32 — Levels and patterns

| # | | Task | Done when |
|---|---|---|---|
| 21 | L | Mark the pre-market high and low on 3 charts. These are the only two levels that matter today | 3 charts, 2 lines each |
| 22 | L | Add VWAP. For each name write "above" or "below" and what that implies | 3 names classified |
| 23 | L | Add the 9 EMA. Note where price sits relative to both | You can spot a name holding its 9 EMA |
| 24 | S | **Micro pullback.** Find 10 historical examples on 1-minute charts. Mark the trigger candle | 10 marked examples |
| 25 | S | Bull flag vs **failed** bull flag. Find 5 of each | You can tell them apart before the resolution |
| 26 | S | **ABCD.** Read `strategies/abcd-pattern.md`. Mark A/B/C/D on 5 charts. Remember: entry at C, add through B | 5 charts labelled |
| 27 | S | Flat top breakout. Find 5. Note the ceiling and the rising base | 5 examples |
| 28 | S | Dip and rip off a halt. `corpus.py "dip and rip" --show streams` | You can describe the sequence |
| 29 | S | Support confluence: **two independent reasons or it does not count**. Mark 5 levels that qualify | 5 levels, 2 reasons each |
| 30 | S | The six exit signals. Write them from memory | 6 of 6, no notes |
| 31 | L | Multi-timeframe: a 1-minute ABCD is often a 5-minute bull flag. Check 3 names | 3 alignment checks |
| 32 | S | **Pattern test.** 20 charts, name the setup, no peeking at what happened | Score out of 20, written down |

## Phase 4 · Days 33–44 — Execution

Now you trade. Paper. One setup at a time.

| # | | Task | Done when |
|---|---|---|---|
| 33 | L | Write a complete trade plan for 1 name — entry, stop, **size**, target 1 — and place **no order** | A plan with 4 numbers |
| 34 | L | Same for 3 names. Rank them. Trade none | 3 plans |
| 35 | L | **First paper trade.** Take your highest-ranked setup. Outcome irrelevant | 1 trade, closed before 14:00 |
| 36 | L | Add the rule: move stop to breakeven after target 1 | Applied on one trade |
| 37 | L | The exit ladder: sell half at target 1, trail the rest | Applied on one trade |
| 38 | L | Journal template. Entry, stop, size, exit, reason, **"did I follow the plan?"** | Every trade so far journalled |
| 39 | L | **Discipline drill: take no trade today.** Write why each candidate failed | A written rejection for every name |
| 40 | L | Trade only the single highest-scoring name. Ignore everything else | 1 trade max |
| 41 | L | Hold to your stop without moving it. If it hits, it hits | Stop honoured |
| 42 | L | Trade a name that halts. Note what happens to your order | Halt experienced, or explicitly avoided |
| 43 | L | Full session with the €30 daily stop armed. Stop trading if hit | Rule obeyed |
| 44 | S | **Week review.** Your first 10 paper trades: win rate, avg win, avg loss | 3 numbers |

## Phase 5 · Days 45–54 — The full routine

Same session every day. The repetition *is* the training.

| # | | Task |
|---|---|---|
| 45 | L | Full routine, focus: **the 13:00 scan** — is your list built by 13:30? |
| 46 | L | Full routine, focus: **the catalyst** — no trade without one, whatever the chart |
| 47 | L | Full routine, focus: **size** — recompute shares on every trade, no guessing |
| 48 | L | Full routine, focus: **the entry trigger** — first candle to make a new high, or no entry |
| 49 | L | Full routine, focus: **the stop** — off the chart, never a round number you invented |
| 50 | L | Full routine, focus: **target 1** — sell half, no hesitation |
| 51 | L | Full routine, focus: **flat by 14:00** — no negotiation with yourself |
| 52 | L | Full routine, focus: **the journal** — written within 10 minutes of the close |
| 53 | L | Full routine, focus: **no trade is a position** — best action may be nothing |
| 54 | S | **Week review.** Read all your journals. What sentence recurs? |

## Phase 6 · Days 55–60 — Measure yourself

| # | | Task | Done when |
|---|---|---|---|
| 55 | S | Compute: total trades, win rate, average win, average loss | 4 numbers |
| 56 | S | Compute your **expectancy** in R. Is it positive? | One number, honestly derived |
| 57 | S | Find your single biggest leak — entry, exit, sizing or discipline. Use the journals | One named leak, with evidence |
| 58 | S | **Change one thing.** Only one. Write the rule you are changing and why | One rule changed |
| 59 | S | Re-read your day-10 rulebook. Rewrite it with what you now know | Version 2 exists |
| 60 | S | Write your go/no-go: continue on paper, or stop. **Both are valid answers** | A decision, in writing |

---

## The three numbers that decide whether this worked

Not P&L. At the end you should be able to state:

1. **What fraction of sessions did you follow your plan?** Target: 100%. This is
   the only metric fully in your control.
2. **What fraction of your trades had all five pillars?** If it is under 80%,
   you are taking B setups.
3. **Expectancy in R.** If it is negative after 60 days of discipline, that is
   information about the strategy, not about you — and it matches what this
   repo has measured over 894 sessions.

## A good red day

> *"A good red day is a day where you lost money but followed every rule. A bad
> green day is one where you made money by breaking them."*

Day 39 is a no-trade day on purpose. If that one feels hardest, that is your
answer about which muscle needs the work.

## Standing caveat

Everything above trains *execution discipline*. It does not establish that the
strategy is profitable — our replication says otherwise, and the documented
edge in this population is on the short side and largely unharvestable
(`reports/2026-08-known-edges.md`). Sixty days of clean process is worth having
regardless. Real money is a separate decision, taken later, with evidence.
