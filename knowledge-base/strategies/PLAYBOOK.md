# The screen playbook

One trade, start to finish. Everything here is `PARAMETERS.md` reordered into
the sequence you actually execute it in.

Read this once before the open, not during. During the session you should be
running the checklist, not reading the reasoning.

---

## Before the open — 07:00 to 09:30

**Set your numbers first, while you are calm.** These do not change during the
session under any circumstances.

| Number | How to get it | Example on $10,000 |
|---|---|---|
| Risk per trade | 2% of account | $200 |
| Max loss for the day | 6% of account | $600 |
| Profit goal | same as max loss | $600 |
| Max trades | 2 | 2 |

Write them down. The whole system depends on these being decided before you have
any money on the line.

**Build the watchlist.** Run the scanner and keep only names where *all five*
are true:

1. Price between $2 and $20
2. Up 10%+ on the day already
3. Relative volume 5x or more
4. Float under 20M shares
5. There is actual news — an earnings beat, an FDA result, a contract, something

Five out of five. Four is a pass — that is a B setup, and B setups are the
documented mistake, not a smaller version of the trade.

You should end with **3 to 5 names**. If you have 15, your filter is too loose.
If you have zero, today is a no-trade day and that is a normal outcome.

---

## At the open — 09:30 to 09:35

**Do nothing.** Watch. The first five minutes are the widest spreads and the
worst fills of the day. You are letting the stock show you where it wants to go.

---

## Finding the entry — 09:35 to 10:30

This is the whole window. Almost all of the edge is here.

### Step 1 — Wait for a pullback

You are not buying a stock that is going up. You are buying the *first or second
dip* inside a move that is going up.

- Stock makes a strong push up (the impulse)
- It pulls back 2–3 candles on the 1-minute chart
- **The pullback candles must be on lower volume than the push.** Heavy volume on
  the dip means real sellers, not a pause. Skip it.
- First or second pullback only. Never the third — by then the move is tired.

### Step 2 — Check where the dip landed

The dip should stop at a price that has **two independent reasons** to matter.
Not one. Two.

Pick from:
- a whole or half dollar ($5.00, $5.50)
- the 9 EMA
- the 20 EMA
- VWAP
- the 200 MA
- a level that was resistance earlier and has now flipped to support

If the dip stops at $5.00 *and* that is also the 20 EMA — that is your level.
If it just stopped at a random price, there is nothing holding it up. Pass.

### Step 3 — Confirm the state of the chart

All four must be true, no exceptions:

- [ ] Price is above VWAP
- [ ] Price is above the 9 EMA
- [ ] MACD histogram is positive
- [ ] No large seller sitting on the ask above you

Any one false — no trade. This is a checklist, not a weighing exercise.

### Step 4 — Wait for the trigger

**The trigger is the first 1-minute candle that trades above the high of the
previous candle.**

That is it. Not "it looks like it's turning." Not "it should bounce here." The
candle has to actually take out the prior candle's high while you are watching.

If you buy before that, you have anticipated, and anticipating is how the losing
version of this strategy works.

---

## Sizing the trade — takes 10 seconds, do it before you click

```
Stop     = the low of the pullback candle
Risk/sh  = entry price − stop price
Shares   = your risk per trade ÷ risk per share
```

Worked example, $10,000 account:

- Risk per trade: **$200**
- Entry: **$5.20**
- Pullback low: **$5.10**
- Risk per share: **$0.10**
- Shares: $200 ÷ $0.10 = **2,000 shares**

Position value is $10,400 — but you are only risking $200, because the stop is
ten cents away. Those are different numbers and confusing them is the single
most common way people blow up on this strategy.

**If the stop is more than $0.20 away, cut your size or skip the trade.** Do not
move the stop further away to make the size you wanted fit. Typical stops here
are 8–10 cents.

Order: limit at the ask plus $0.15. If you cannot get filled within 15 cents,
let it go — the trade was priced on a fill you did not get.

---

## Managing the trade

You should already know all three exits before you are filled.

**Exit 1 — the stop.** Pullback low. It does not move down, ever. Not once.

**Exit 2 — the target.** Sell **half** at the first target, usually a retest of
the high of the day, typically 15–20 cents up. Once you have taken that half,
move your stop to breakeven. Now the trade cannot lose.

Then sell **25%** at the next level, and let the last **25%** run with a trailing
stop.

**Exit 3 — it broke.** Get out immediately, full position, on any of these:

- First 1-minute candle that makes a *new low*
- A big red candle on heavy volume
- MACD crosses negative
- Price loses VWAP
- A large seller appears on the ask
- Green candles getting visibly smaller — the move is done

You do not need to be right about *why*. You just leave.

**The minimum trade is 2:1.** If the target is 20 cents up and the stop is 10
cents down, that works. If the stop has to be 20 cents to make sense and the
target is only 20 cents, that is a 1:1 and you skip it — at 1:1 you need to be
right more than half the time just to break even.

---

## When to stop for the day

Stop immediately if any of these happens. All of them. No exceptions, no "one
more trade to get it back."

- You are down your max daily loss ($600 on a $10k account)
- You have given back half of what you were up at your peak today
- You were green and the day has gone red
- Three losses in a row
- You have taken 2 trades
- It is 11:30

The claim attached to that first rule is that breaking it leads to *doubling*
that loss about 80% of the time. That number is unverified — but the rule costs
you nothing on the days it does not bind, and everything on the day it does.

Also stop when you hit your profit goal. Hitting $600 and then trading is how
$600 becomes $0.

---

## The whole thing on one card

```
Pre-market  →  5 of 5 filters  →  3-5 names
09:30-09:35 →  watch, don't trade
09:35+      →  wait for pullback 1 or 2, on lower volume
            →  did it stop at 2 overlapping levels?     no → pass
            →  above VWAP + above 9EMA + MACD positive? no → pass
            →  candle breaks prior candle high?         no → wait
            →  size = risk ÷ (entry - pullback low)
            →  buy, limit at ask + 0.15
            →  sell 50% at target, stop to breakeven
            →  sell 25%, trail 25%
            →  any break signal = out, all of it
Stop at:    2 trades │ -6% │ +goal │ 3 losses │ green-to-red │ 11:30
```

---

## One thing to be clear about

None of this has been backtested. The numbers come from what he says across 257
videos, not from a validated result — and §9 of `PARAMETERS.md` works out that
the stated win rate and reward:risk imply roughly +3.2% *per day*, which is
implausibly high. Something in the stated version is optimistic, and the most
likely candidates are the real win rate, slippage eating a 10-cent stop, and
fills at size on a 20M float.

Trade this in a simulator first, and size it as though the edge might be zero,
because it might be. The daily loss limits are the part that works regardless of
whether the entry does.
