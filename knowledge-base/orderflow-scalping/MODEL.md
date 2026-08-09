# The order-flow scalping model — Fabio Valentino

Dissected from one source: `transcripts/tvERE-Beu2U.txt`, a 3h34m live session
on the Chart Fanatics channel, 2025-09-21, 43,007 words. Futures scalper,
introduced as top-three in the Robbins World Cup futures division with a stated
**500%+ over twelve months** — a claim this repo has not verified.

**Read the caveats at the bottom before anything else here.** One trader, one
video, against 2,680 documents for the Ross Cameron corpus. This document is a
faithful dissection, not an endorsement.

---

## He rejects the word "strategy", and the reason is the method

> *"Why I call it a model and not a strategy? Because the concept of strategy is
> a group of rules that you need to follow strictly. And how can you follow a
> group of rules strictly without understanding the narrative if the market is a
> dynamic entity? It's like trying to cage an animal that is not made to be in a
> cage."* — [00:06:34]

That distinction is load-bearing. The Ross spec in `../strategies/PARAMETERS.md`
is a gate cascade: numeric thresholds, all must pass. This is a **sequence of
conditions on state**, and step three is explicitly not automatable:

> *"The step three is a little bit more difficult because it's the part where
> you really need the experience and **you cannot just automate it**."* — [00:11:00]

Take that at face value when deciding what to build from it.

---

## The three steps

### Step 1 — Location: only trade **out of balance**

The premise. The market is either in balance (rotating around a fair price) or
out of balance (searching for a new one). He claims the filter alone is worth
most of the edge:

> *"if you do this simple change and you wait for the market to get to a
> condition of out of balance your win rate will jump up by **at least 20 to
> 30%**. And this is exactly the building point of the model."* — [00:06:23]

> *"What the market is telling us: look, I'm out of balance. I'm searching for a
> new level of balance that will be down. It can be here, it can be here, but
> I'm telling you that I will go there."* — [00:08:29]

"Inefficiency" is defined mechanically, and he distinguishes it from the retail
term:

> *"inefficiency... is misconcepted nowadays because it used the term fair value
> gap. But what happened really behind the curtains in the concept of
> inefficiency is **when one part is more aggressive than the other**."* — [00:08:01]

### Step 2 — Validate the level, using a volume profile

Draw a profile **from point A to point B** — across the swing that produced the
break — and read where volume was thin.

> *"you can use from point A to point B using profile to watch exactly when
> there are low volume node... **low volume node it's a really good reaction
> level**. So you can use it as a continuation. If we have a low volume node
> here the probability that we will go down is really high."* — [00:10:09]

Order flow is framed as a different alphabet rather than another indicator:

> *"order flow, that is not a concept but it's like an alphabet, a new way of
> reading the market. So 90% of the traders try to understand what is happening
> inside a candle using multi-timeframe analysis... I think the real
> inefficiency is the way traders analyze the market."* — [00:09:11]

### Step 3 — Aggression is the trigger

> *"the step three is getting a location for aggression. So that **the trigger
> of the model is aggression**."* — [00:16:15]

Read from the footprint / bubbles — clusters of large market orders at a price.

> *"When there is **direction, location and aggression**, your ability to
> predict is zero but your ability to read is 100. You are exactly tuning in
> in the market at the correct moment and you are **not predicting** what is
> going to do. **You are waiting.**"* — [00:11:29]

That sentence is the model in one line, and it is also the trailer's stated
diagnosis of why traders lose: *"they try to anticipate what the market is
doing before the market does it"* [00:00:15].

---

## Supporting concepts

### CVD — cumulative volume delta

> *"one tool that is called CVD, that is cumulative volume delta. What
> cumulative volume delta is giving you is **a benchmark for pressure of
> volume**."* — [00:27:45]

Used for two things: confirming that buyers are lifting offers while price
rises, and as the **trigger to move a stop to break-even**:

> *"when you see that cumulative volume delta is pushing up and you see this leg
> already building **you can already put to break even**... because you know
> that as the smallest retracement aggressive buyers will continue to push up
> and you are protected."* — [00:28:48]

He calls this the practical benefit of a leading indicator over a lagging one
[00:29:03].

### The squeeze — the model's payoff pattern

Named 44 times across the session. Definition:

> *"When is the squeeze of the trap sellers? **When you recover all the
> aggressive sellers.** They are getting faked out, so they are willing to close
> the position and the market is accelerating high."* — [01:47:50]

So the sequence is: aggressive sellers print at a level → price recovers past
where they transacted → their stops become buy orders → acceleration. A **second
squeeze** is expected if the same thing happens again on the next leg
[02:22:42].

### Session and instrument — narrow on purpose

> *"the best session to use this model it's **100% New York session**,
> specifically for equities. So for NASDAQ... it's not working properly during
> the first hour of London session."* — [00:16:41]

> *"one concept that I use to remove this is that **I don't trade before New
> York**."* — [00:17:19]

His stated reason is that outside New York the tape gives *"out of balance, back
inside balance, out of balance, back inside balance — this is called by traders
fake outs"* [00:17:02].

---

## Execution

### Entry — break **and** test, or stay out

> *"remember **the model is one. You need to break and test this level.
> Otherwise you just stay out.**"* — [01:48:33]

> *"When this level gets broken, the game starts. You can add the position, you
> can follow up."* — [01:48:38]

He declines a long at a level *"completely dominated by sellers"* even though
price is there — location alone is not enough without the aggression flipping
[01:48:10].

### Stop — under the aggression, and deliberately *inside* the high

Two separate rules, and the second is the sharpest practical detail in the
video.

**Where:** under the cluster of large orders, not under the swing.

> *"if you are wrong you want to be wrong immediately. If you have big sell
> orders here, immediately here it's your stop loss."* — [00:44:41]

> *"you don't have a huge stop loss above the high, but you can get protected
> exactly **above the big sell aggression**. So your risk-to-reward ratio it's
> really big but at the same time the probability of your trades is really
> [high]."* — [00:11:54]

**The slippage trick:** place it one or two ticks *before* the obvious level,
not beyond it.

> *"a way to avoid slippage or at least minimize slippage: put the stop loss
> **not above the high**. Because above the high there are a lot of orders and
> what you see is that market will accelerate... So you lose an additional
> amount of ticks that you can protect. Just **put your stop loss one or two
> ticks below the high**. So you are taken out before everyone, before
> acceleration takes place."* — [00:44:48]

> *"I tested it and it's worth it because sometimes you get five ticks, six
> ticks of [slippage] and it's a lot."* — [00:45:33]

Note what this trades away: a slightly higher stop-out rate in exchange for a
smaller loss when stopped. He asserts *"the overall chances of price getting to
one or two ticks below that high and then not going for [it] is almost zero"*
and then immediately corrects himself — *"no, it's not zero"* [00:45:41].

### Target — the previous daily high, first

> *"the first target is the one with **the highest win rate. It's the previous
> daily high.**"* — [01:59:33]

Three targets are framed at the moment of validation, not invented later:
*"you have three possible take-profits that you can frame by watching at the
other area"* [00:08:55].

### Management — break-even early, scale half, re-enter at the LVN

> *"immediately break even... be able to move at break even"* — [01:51:02]

> *"if this one goes to half profit and half break even, I would use half the
> profit that I made to wait for the trades there because I'm pretty sure that
> if we get back to the low volume node we get aggressive buyers, we are going
> to run to the high."* — [02:23:27]

The scale-out is **triggered by the tape**, not by a fixed R:

> *"when I told you I will scale out, it's exactly because when you see this,
> the next step is aggressive sellers."* — [00:00:36]

---

## The daily-P&L model

> *"How I did this performance in the world trading cup is **building profit for
> the day, building profit for the day, building profit for the day.** And in
> directional days, I risk for example..."* — [01:08]

The stated shape: accumulate small wins to build a cushion, then take real
directional risk only once the day is already green. That is the same asymmetry
Ross describes in `../strategies/PARAMETERS.md` §7 — start at a quarter size,
size up only after +$1,000 — arrived at independently.

He is explicit that win rate is traded against R, not maximised:

> *"the win rate gets lower... but"* — [03:17:45], and *"one setup with high win
> rate"* [01:38:29] versus *"the win rate it's lower on this but if..."*
> [01:41:15]

---

## How this differs from the Ross corpus

| | Ross Cameron (`../strategies/`) | This model |
|---|---|---|
| instrument | US small-cap equities, $2–20, float <20M | **Nasdaq futures** |
| what selects the trade | five pillars: price, float, catalyst, RVOL, gap | **market state: out of balance** |
| news | mandatory catalyst | **never mentioned** |
| session | pre-market through ~11:00 ET | **New York only; explicitly not before** |
| chart | 1-minute and 10-second candles | **footprint / volume profile / CVD** |
| entry trigger | first candle to exceed the prior red candle's high | **aggression at a validated level, after break *and* test** |
| stop | low of the pullback candle | **above/below the aggression cluster, 1–2 ticks inside the high** |
| first target | retest of high of day | **previous daily high** |
| break-even | after +$0.10 or first scale | **when CVD confirms the leg** |

Two genuine convergences, reached from different directions: **scale half and
move to break-even early**, and **build the day's cushion before taking size**.

The deepest difference is epistemic. Ross's method is a filter you can encode —
which is why `PARAMETERS.md` exists and why 21 interpretation errors could be
found in it. This one is a *reading* of state that its author says cannot be
automated at step three. Any implementation has to decide what to do about that
sentence rather than route around it.

---

## Caveats — read before using any of this

1. **One source.** 43,007 words from a single interview. The Ross corpus is
   2,680 documents across four registers, and the whole method of this repo is
   that a lopsided register split is itself a finding. There is no split here to
   check — no recaps, no independent streams, nothing dated differently.
2. **The 500% is unverified.** Robbins World Cup results are published; this
   repo has not checked them, and a percentage return says nothing about the
   capital base or the drawdown path.
3. **A live session is a demonstration.** The register is closest to `streams`
   (decisions before the outcome is known), which is the most trustworthy
   register — but it is one session, and a demonstration selects for a day the
   model works.
4. **Step three is stated as non-automatable by its own author.** Anything built
   from this must say explicitly which part it has replaced with a proxy, and
   `PARAMETERS.md` §10 is the standing warning about what proxies do to a
   backtest.
5. **Futures are leveraged.** Every sizing rule in `../../scripts/size.py`
   assumes cash equities and a €500 account. A single Nasdaq futures contract
   has notional far beyond that. **None of the sizing work in this repo
   transfers.** Micro contracts change the arithmetic but not the point.
6. **This repo's own record.** Its replication of a far better-documented
   strategy produced negative expectancy over 894 sessions
   (`../../research/momentum-replication/reports/2026-08-regime-filter.md`).
   That is the prior to hold against any new method, including this one.
