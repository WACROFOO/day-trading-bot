# Order-flow scalping — the playbook

The executable form of `MODEL.md`. Every rule traces to a timestamp in
`transcripts/tvERE-Beu2U.txt`. Where the source is vague, this says so instead
of inventing a number — that discipline is the one thing carried over from the
Ross spec, where 21 of 21 audit findings turned out to be interpretation errors
rather than wrong numbers.

**Instrument: Nasdaq futures. Session: New York only.** Nothing below applies
to cash equities and none of this repo's sizing tools apply to futures.

---

## Pre-conditions — if any fails, there is no trade

| # | condition | source |
|---|---|---|
| 1 | It is the **New York session**. Not London, not before. | [00:16:41], [00:17:19] |
| 2 | The market is **out of balance** — not rotating around a fair price | [00:06:23] |
| 3 | A **low volume node** has been identified from a profile drawn A→B across the swing that broke | [00:10:09] |
| 4 | **Aggression** is visible at that level on the footprint | [00:16:15] |

> *"When there is direction, location and aggression, your ability to predict is
> zero but your ability to read is 100."* — [00:11:29]

All three words matter and they are ordered. Direction comes from the imbalance,
location from the profile, aggression from the tape. **Two out of three is not
a trade.**

---

## The trigger

**Break AND test. No exceptions stated anywhere in 3½ hours.**

> *"remember the model is one. You need to break and test this level. Otherwise
> you just stay out."* — [01:48:33]

```
level identified  ->  price BREAKS it  ->  price comes BACK and TESTS it
                  ->  aggression confirms on the test  ->  entry
```

Entering on the break alone is the error the video opens by naming: *"they try
to anticipate what the market is doing before the market does it"* [00:00:15].

**Rejection example, from the session itself:** price reached the level and he
did not take it, because *"if you see who created the swing... is completely
dominated by sellers. This is a really risky position"* [01:48:10]. Location was
present, aggression was the wrong way. No trade.

---

## The stop

Two rules, both explicit.

**1. Place it beyond the aggression cluster, not beyond the swing.**

> *"if you are wrong you want to be wrong immediately. If you have big sell
> orders here, immediately here it's your stop loss."* — [00:44:41]

This is what produces the claimed R:R — the stop is tight because it sits on the
order cluster, not because it was chosen to be tight [00:11:54].

**2. Put it one or two ticks INSIDE the high, never beyond it.**

> *"put the stop loss **not above the high**. Because above the high there are a
> lot of orders and what you see is that market will accelerate... just put your
> stop loss one or two ticks below the high. So you are taken out before
> everyone, before acceleration takes place."* — [00:44:48]

The trade-off, stated plainly: you get stopped slightly more often, and you save
*"five ticks, six ticks"* of slippage when you are [00:45:33]. He claims the
chance of price tagging 1–2 ticks inside the high and then not going through is
*"almost zero"*, then corrects himself to *"it's not zero"* [00:45:41] — so this
is a positive-expectancy tweak, not a free lunch.

---

## Targets

| target | level | note |
|---|---|---|
| **1** | **previous daily high** | *"the one with the highest win rate"* [01:59:33] |
| 2–3 | framed at validation, from the profile | *"three possible take-profits that you can frame by watching at the other area"* [00:08:55] |

Targets are chosen **before** entry, at the moment the level is validated. They
are not invented once the trade is running.

---

## Management

**Break-even is triggered by CVD, not by a fixed number of ticks.**

> *"when you see that cumulative volume delta is pushing up and you see this leg
> already building you can already put to break even... because you know that as
> the smallest retracement aggressive buyers will continue to push up and you
> are protected."* — [00:28:48]

**Scale out when the tape turns, not at a fixed R.**

> *"when I told you I will scale out, it's exactly because when you see this,
> the next step is aggressive sellers."* — [00:00:36]

**Re-entry at the low volume node is part of the plan, funded by the first
scale.**

> *"if this one goes to half profit and half break even, I would use half the
> profit that I made to wait for the trades there because I'm pretty sure that
> if we get back to the low volume node we get aggressive buyers, we are going
> to run to the high."* — [02:23:27]

---

## The squeeze — what you are actually being paid for

> *"When is the squeeze of the trap sellers? When you recover all the aggressive
> sellers. They are getting faked out, so they are willing to close the position
> and the market is accelerating high."* — [01:47:50]

```
aggressive sellers transact at a level
        v
price recovers ABOVE where they transacted
        v
their stops become buy orders
        v
acceleration  ->  this is the squeeze
        v
if it repeats on the next leg  ->  second squeeze   [02:22:42]
```

Reading this correctly is what tells you whether to scale out or add. It is also
step three, the part he says cannot be automated [00:11:00].

---

## The daily model

> *"building profit for the day, building profit for the day, building profit
> for the day. And in directional days, I risk for example..."* — [00:01:08]

Small wins first; directional size only on a cushion. Independently the same
shape as `../strategies/PARAMETERS.md` §7 — start at a quarter size, size up
after +$1,000.

Win rate is explicitly traded against R rather than maximised: he contrasts *"one
setup with high win rate"* [01:38:29] against setups where *"the win rate it's
lower on this but..."* [01:41:15].

---

## What this playbook does NOT contain, because the source does not

Recorded so nobody fills these in from imagination later:

- **No risk-per-trade percentage.** Never stated.
- **No daily loss limit.** Never stated. Contrast Ross, who names $2,000,
  broker-enforced, and three-reds-and-done.
- **No maximum trades per day.**
- **No definition of "out of balance" precise enough to code.** It is read off a
  profile by eye.
- **No numeric threshold for "aggression".** Contract counts are mentioned in
  passing — *"each one of these is 40... but these big balls, maybe it's 100"*
  [02:22:53] — but as observation, not as a rule.
- **No stop distance in ticks.** Only "beyond the cluster" and "1–2 ticks inside
  the high".

Five of those six are risk controls. **That is the largest gap between this
document and the Ross spec, and it is the gap that matters most.**

---

## If you want to test it

In falsification order, cheapest first — the same structure as
`../strategies/PARAMETERS.md` §12.

1. **Data.** This needs footprint / delta / volume-profile data. Nothing in this
   repo has it; every tool here runs on OHLCV plus published metrics. **Without
   tick-level bid/ask trade data none of steps 2 or 3 can be evaluated at all.**
   Settle this before writing any code.
2. **Step 1 alone.** Does an "out of balance" filter — however crudely proxied —
   improve a baseline on Nasdaq futures? He claims +20–30% win rate for this
   step by itself [00:06:23]. It is the only claim here testable on ordinary
   bars, and it is the one worth testing first.
3. **The stop tweak.** 1–2 ticks inside the high versus 1–2 ticks beyond it,
   same entries. Purely mechanical, needs no order flow, and settles a specific
   falsifiable claim about slippage.
4. **Target 1.** Is the previous daily high really the highest-win-rate first
   target? Testable on daily + intraday bars alone.
5. Only then the parts needing a footprint.

Items 2, 3 and 4 need no order-flow data. **Start there** — and note that if
they fail, the model's own author would not consider that a fair test of it,
because steps 2 and 3 are missing. Say which one you ran.
