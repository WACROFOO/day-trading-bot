# The micro pullback — detection spec

```
WHAT THIS IS · the one pattern he trades, written as instructions a
     machine can follow. Shape and rules from STRATEGY.md §5-6 (this
     repo's canonical spec); numbers from PARAMETERS.md. FILTERS.md wins
     any conflict with this file.
SPOKEN SOURCES · "Buy the first candle that makes a new high after the
     pullback" — IwDORxvXAAs @00:48:34. Micro pullback = smallest
     pullback within a move, lowest-risk entry — ZpiWEMTpvoo @00:17:31.
     He claims 65-70% accuracy for it — Gf791LDEsQI @00:39:41 (his
     claim, unverified here).
PAPER ONLY · this repo's own 894-session replication of this strategy
     was NEGATIVE expectancy (reports/2026-08-regime-filter.md). The
     spec describes what to look for, not a promise it pays.
```

## The shape, in four states

```
IDLE     → nothing yet
PUSH     a stock is running up hard, on volume
DIP      it pauses and drops for 1-3 candles, on LIGHTER volume
TRIGGER  a candle trades above the previous candle's high  ← BUY HERE
```

The trigger is the whole entry. Not the pause. Not the bottom of the dip.
Not a candle close. The moment price exceeds the prior candle's high,
buyers are back and you are in.

## Detection rules

**1. Find the PUSH** (context, not the signal)
- price moving up over the last 1-6 candles
- volume above its own recent average
- the move is the day's high or close to it

**2. Find the DIP**
- 1 to 3 candles, red or flat, coming off the push high
- volume **falls** vs the push candles
- price stays above the 9 EMA and above VWAP
- the dip gives back a small part of the move, not most of it
- **deep dip = skip the trade** (not "use a wider stop")

**3. Fire the TRIGGER**
- BUY when price > high of the previous candle
- stop = **low of the dip**, minus one tick
- if that stop is far away, the trade is too risky → skip

**4. Refuse the trade if any of these is true**
- MACD is negative / has crossed below signal → no long, ever
- price is below VWAP or below the 9 EMA
- volume rose during the dip (real selling)
- this is the **3rd pullback** of the move (the third usually fails)
- the dip is deep enough that the stop is wider than your risk allows

## Scenarios and what to do

| what happens after entry | action |
|---|---|
| price runs | sell half at +1R, move stop to break-even, let the rest run to +2R |
| price stalls, no follow-through in ~2 candles | get out — "breakout or bailout" |
| price closes back below your entry | get out |
| price hits the dip low | you are already out — the stop did it |
| you were stopped, then it sets up again | it is a NEW setup — re-check every rule |
| it is the 3rd pullback | do not trade it |

Never: move a stop down, add to a loser, or re-enter out of anger.

## Sizing — €2,000 account, 50% win rate

Rule (PARAMETERS.md §7, n=125): `shares = risk_budget ÷ (entry − stop)`,
risk budget = **2% of account = €40**.

```
entry 8.10, stop 7.95  → risk/share 0.15 → 266 shares (€2,155 > account)
                        → capped by cash: 246 shares ≈ €2,000
entry 3.20, stop 3.05  → risk/share 0.15 → 266 shares ≈ €851  ✓
```
Two hard caps, whichever binds first: **€40 of risk** and **your €2,000 of
cash** (no margin).

**What 50% actually pays with the 2R ladder** — one loser is −1R, one
winner is +1.5R (half at 1R, half at 2R):

```
50 trades: 25 × +1.5R  = +37.5R
           25 × −1.0R  = −25.0R
                       = +12.5R  ≈ +0.25R per trade ≈ +€10
```
Minus commissions: at ~$1/order a round trip is €2–3, i.e. **5–7% of the
€40 budget every trade** (measured: reports/2026-08-pine-v8-benchmark.md).
Net ≈ **+€7 to +€8 per trade** — if the 50% holds and every winner reaches
the full ladder. If half your winners only get the T1 half before the
runner stops at break-even, expectancy falls to ≈ +0.12R (+€5).

**Discipline caps that come with it:** 2–4 trades per day maximum
(PARAMETERS.md §7, n=22), quarter size at the open until the day is
green, and from the 3rd trade of the day take half size.

## The one-line version

> A stock running up pauses 1–3 candles on lighter volume while holding
> the 9 EMA, VWAP and a positive MACD; buy the instant price takes out
> the previous candle's high; stop under the dip's low; half off at 1R,
> rest at 2R; skip the third pullback.
