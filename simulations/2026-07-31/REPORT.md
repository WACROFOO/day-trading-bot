# Friday 2026-07-31 — one trader, one day, no look-ahead

A forward-only replay of `PLAYBOOK_V2.md` on real 1-minute data, run as though
sitting at the screen. Every decision uses only bars that existed at that
timestamp.

**Result: 2 trades, 2 losses, −$160.96 on a $10,000 account (−1.61%). Day over
at 09:40 ET on the 2-trade limit, 1h50m before the hard stop.**

---

## Method

| Stage | What was used | Look-ahead risk |
|---|---|---|
| Universe | 7,131 US symbols (Nasdaq screener) | none — symbol list only |
| Candidate pool | price $1.20–$30, market cap ≤ $400M | low — bands deliberately wider than the strategy's, so a name is not included because of how Friday ended |
| Pre-market scan | 1,528 symbols, bars 04:00–09:29 ET | none |
| Watchlist | gap ≥ +10%, price $2–20, ≥5 pre-market bars | none |
| 09:35 confirmation | RVOL from bars 09:30–09:34 only | none |
| Execution | bar-by-bar, 09:35–11:30 | audited, see below |

Data: Yahoo 1-minute OHLCV including pre/post. Prior-session baselines from
Mon 7/27 – Thu 7/30.

### Look-ahead audit

`audit_lookahead.py` truncates the day at 09:41, 10:00, 10:30, 11:30 and the
full session, then re-runs. A forward-only engine must produce identical
decisions regardless of how much future data exists in the file.

```
cut-off     trades    day P&L  identical?
09:41            2    -160.96  YES
10:00            2    -160.96  YES
10:30            2    -160.96  YES
11:30            2    -160.96  YES
full             2    -160.96  YES
PASS - the engine is forward-only.
```

### Conservative choices

- A bar that breaks the stop **and** reaches the target is recorded as a stop —
  a 1-minute bar does not say which came first.
- Entry fills at `min(trigger + $0.02 slippage, bar high)`. Capping at the bar
  high matters: the first version priced trade 2 at $4.41 when that bar's high
  was $4.40, a fill that could not have happened.
- Size capped at 10% of the entry bar's volume, and at 4× buying power.

---

## The morning

**07:00 ET — scan.** 1,528 candidates → 1,003 with usable data → 21 gapping
≥ +10% → 10 survive a sanity filter.

Two of the largest "gaps" were rejected as data artifacts: NEXR showed +858%
on 7 pre-market bars against an 11M-share prior average with 13k shares traded
in the first five minutes — a reverse split, not a move.

**Pre-market volume was unavailable.** Yahoo returns null volume on pre-market
bars for these names, so relative volume could not be checked before the bell.
It was verified instead at 09:35 from the first five minutes of real session
volume — later than the playbook wants, but not look-ahead.

**09:35 — watchlist confirmed.**

| Symbol | Open | 5-min RVOL | Est. shares out | 5 pillars |
|---|---:|---:|---:|---|
| FCUV | $10.22 | very high | 0.8M | 4/5 ✓ |
| CUPR | $3.28 | 61× | 2.4M | 4/5 ✓ |
| TCX | $11.10 | 21× | 15.4M | 4/5 ✓ |
| JFB | $4.03 | 47× | 15.1M | 4/5 ✓ |
| DUOT, LFS, PLYX, AIBZ | — | — | 25–47M | fail float |

Four names. The fifth pillar — a news catalyst — could not be verified
programmatically and is assumed, which is a real gap in this run.

---

## The two trades

Both on JFB, both inside five minutes.

**09:35 — buy 1,038 @ $4.41, stop $4.22.** First pullback, low $4.22 sitting on
the 9 EMA and VWAP (two reasons), pullback volume 7,605 vs impulse 14,838,
MACD positive, price above VWAP and the 9 EMA. Every check passed. Risk
$0.19/share × 1,038 = $200.

**09:36 — out at $4.36, −$51.** The next candle made a new low and closed red.
That is Exit 3 in the playbook, and it fired one minute after entry, well
before the $4.22 stop.

**09:38 — buy 914 @ $4.40, stop $4.28.** Second pullback, all checks passed
again. Size capped by the liquidity rule, so risk was $110 rather than the full
$200.

**09:40 — stopped out at $4.28, −$110.** JFB printed its high of day at $4.48
on the 09:39 bar, one minute after the second entry, then rolled over.

**09:40 — two trades taken. Day over.**

---

## What the strategy missed, and why

JFB closed −1.5% from the open. Two names on the same watchlist did this:

| Symbol | Open | High of day | Close | vs open |
|---|---:|---:|---:|---:|
| **FCUV** | $10.22 | $18.77 | $17.05 | **+66.8%** |
| **TCX** | $11.10 | $16.09 | $15.14 | **+36.4%** |
| JFB | $4.03 | $4.48 | $3.97 | −1.5% |
| CUPR | $3.28 | $5.77 | $2.93 | −10.7% |

The obvious conclusion is that the 2-trade limit locked the account out of the
winners. **That is wrong, and the counterfactual disproves it.**

Re-running with the trade limit removed produces **exactly the same two trades
and the same −$160.96**. Across the full 09:35–11:30 window the engine
evaluated **50 pullbacks and only 2 passed the gate.** Every FCUV and TCX setup
was rejected by the entry rules themselves.

Rejection reasons (a setup can fail several):

| Reason | Count |
|---|---:|
| support confluence ≥ 2 | 42 |
| pullback index ≤ 2 | 36 |
| stop > $0.20 | 14 |
| pullback volume < impulse volume | 13 |
| MACD histogram > 0 | 12 |
| price > 9 EMA | 8 |

**The structural finding: the $0.20 stop cap and the strategy's own price band
are in conflict.** FCUV's pullbacks were 36–78 cents deep. On a $12 stock
moving 60% in a session, a pullback low is *never* within 20 cents of the
trigger. The cap is calibrated for $2–5 stocks, but the price filter admits
names up to $20. On this day, that combination excluded every large winner and
admitted only the one name whose pullbacks were small enough to qualify —
because it was not really moving.

TCX shows the second half of it: by 10:26 the tracker was on pullback #13.
A stock that trends all morning never resets its count, so the "first or second
pullback only" rule permanently locks you out after the first hour.

---

## Sensitivity

`level_tolerance` is the one parameter with no value anywhere in the corpus.
Sweeping it changed nothing on this day:

| Tolerance | Setups | Passed | Day P&L |
|---|---:|---:|---:|
| 0.10% | 50 | 2 | −$160.96 |
| 0.25% | 50 | 2 | −$160.96 |
| 0.50% | 50 | 2 | −$160.96 |

One day is weak evidence, but the result does not sit on that parameter.

---

## Honest limits

1. **One day, four symbols, two trades.** Nothing here is statistically
   meaningful. It is an existence check on the rules, not a backtest.
2. **The news pillar was assumed, not verified.** All four names are 4/5
   setups, which the playbook explicitly calls the documented mistake.
3. **Level 2 conditions could not be evaluated** — `no_seller_wall` and
   `tape_green` are logged as `N/A`, so the gate here is weaker than the real
   one. Both trades might have been filtered by a seller wall.
4. **Free retail data.** Yahoo 1-minute bars, no pre-market volume, no real
   spread. Fills assume $0.02 slippage; on a 12-cent stop that is 17% of risk,
   and the true figure on a sub-20M float is likely worse.
5. **The pullback tracker is my interpretation.** "Pullback", "impulse" and
   the index reset (on losing VWAP) are mechanical definitions I chose. Other
   defensible readings would produce different trades.
6. **Candidate pool contamination.** Price and market cap come from a Saturday
   snapshot. Bands were widened to reduce the effect, but a name that moved
   200% on Friday had a different market cap on Friday morning.

---

## What this day actually argues

The risk rules did their job. Two losses, both small, day closed at −1.61%
against a −6% limit, with no revenge trade available because the trade counter
had run out. That is the system working.

The entry rules are the problem, and not in the way it looks. They did not
merely miss the winners — they were *structurally incapable* of taking them,
because a 20-cent stop cannot exist on a $12 stock in a 60% move. That is a
falsifiable claim about the parameter set, and it is testable across many days
with the code in this directory.

Reproduce:

```bash
python simulations/2026-07-31/scan_premarket.py     # pre-market scan
python simulations/2026-07-31/fetch_day.py          # session bars
python simulations/2026-07-31/run_sim.py            # the day
python simulations/2026-07-31/audit_lookahead.py    # prove no look-ahead
```
