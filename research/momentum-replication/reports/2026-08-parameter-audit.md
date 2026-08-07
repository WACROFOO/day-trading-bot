# Parameter audit — the spec against all four registers

`PARAMETERS.md` closes with: *"Derived from `rules_digest.md` — 2,040 rules,
2,903 numeric figures, **257 videos**."* The 2,063 blog articles were fetched
after it was written and have never been used to check a single number.

This is that check. Every parameter re-read against teaching, recaps, streams
**and blog**, looking specifically for interpretation errors rather than typos —
§13 already establishes that in this corpus the numbers are usually right and
the readings are usually wrong.

**Sixteen corrections across three passes, covering every section of the spec.**
One of them invalidates a tool built three days ago; one rewrites the basis of
the expectancy model. Not a single one is an arithmetic error.

---

## The structural error: a scanner setting is not a trade gate

Six of the sixteen findings are the same mistake wearing different numbers. §1 is
titled *"Universe filter — applied before the chart is looked at. **All must
pass.**"* and lists `gain_pct_min`, `rvol_min` and `volume_min` alongside price
and float as though they were the same kind of object.

They are not. Some of those numbers are what he **types into a scanner** to
produce a list. Others are what he **requires of a trade**. The corpus
distinguishes them constantly and the spec collapses them:

| | scanner setting | what he actually trades |
|---|---|---|
| gap | *"all the stocks gapping up more than **5%**"* (`kicking-back-after-a-7k-day`) | 10% is the pillar; 20–30%+ in the recaps |
| relative volume | 5× (`in-depth-guide-to-my-macd-scalping-strategy`) | *"**150%** and higher is where I make money"* |
| volume | 250,000 minimum (`1zBC9RKwfeU` 1:06:48) | *"less than a million shares of volume I actually **lost $8,000**"* |

A scanner threshold is set **loose** so nothing is missed, then the eye
tightens it. Implemented as a gate, a loose setting lets junk through and a
tight one silently deletes the population you wanted. The replication used them
as gates.

---

## 1. `volume_min` is 1,000,000, not 500,000 — measured, not taught

§1 records `volume_min >= 500,000 shares cum., n=102`. He has published an
analysis of **his own broker statements** that contradicts it:

> *"Stocks with a relative volume of 150% and higher is where I make money. I
> did the best on stocks with relative volume of 300% and higher. Although some
> of those stocks had lighter volume at the time I got in, **the stocks that
> have less than a million shares of volume I actually lost $8,000 on. I did
> not make money on those stocks.** The stocks that closed the day with one to
> two and a half million or more in volume are the ones I did the best on."*
> — `risk-psychology/rollercoaster-trader-behind-trades-ep-6.md`

This is the strongest evidence class anywhere in the corpus: a realised P&L
split by a measurable feature, not a heuristic. 500,000 sits **inside the band
he lost money in**.

**`volume_min: 500_000` → `1_000_000`.** Preferred band 1.0–2.5M+.

## 2. `rvol_min = 5.0` is the scanner dial, not the requirement

Same paragraph. **150% is 1.5×**, not 5×. He makes money from 1.5× and does
best above 3×. The 5× figure is real but comes from the article describing what
he *screens* with:

> *"I look for stocks priced between $2 and $20, up at least 10% on the day,
> with a relative volume of 5x or higher, a float under 20 million shares, and
> any breaking news."* — `indicators/in-depth-guide-to-my-macd-scalping-strategy`

Both are true and they are different objects. As a hard gate, `rvol >= 5.0`
discards the 1.5–5× band his own statements identify as profitable.

**Keep 5.0 as `rvol_scan`. Add `rvol_min_trade: 1.5`, `rvol_preferred: 3.0`.**

## 3. Pre-market volume has a CEILING, and no floor. This is missing entirely.

The spec has no pre-market volume parameter at all. The corpus has a clear one,
in three registers, and it runs the **opposite** way to every other volume rule:

> *"It already has **2 million shares of premarket volume**. So I already have
> a little bit of a negative bias on it **before I even pull up the chart**."*
> — `ZfwTJAMLroA` [13:21] · streams

> *"stocks that have **millions of shares of pre-market volume** don't really
> work for the gap and go as much, because it's almost like, **I'm not the
> first one to see it**... CDNA was still under a million shares though, it
> still looked pretty good."* — `day-2-of-our-nyc-seminar` · blog

> *"volume **not more than a million pre-market**. You don't want it super
> crowded to the point where people are already actively trading it. You kind
> of want to wait until the bell rings."* — `keeping-my-head-above-water-142`

And there is **no floor**. He traded NCTY on **8,000 shares** of pre-market
volume and made $700, because the catalyst was strong
(`starting-off-september-grateful-334`).

The mechanism is explicit and it is about *edge*, not liquidity: the gap-and-go
is a bet on an imbalance that resolves at the bell. If the pre-market has
already traded millions of shares, the imbalance has already resolved.

Counter-case, so this is a bias and not a veto: *"Pre-market volume 1.5 million
shares, 9 million share float. 44% gap, that looks good"*
(`11th-green-day-in-a-row-3k`). Same shape as `stop_max_distance` and the third
pullback in §13 — a caution answered with size, not a rejection.

**Add `premarket_volume_max: 1_000_000` (soft), `premarket_volume_min: none`.**

### This invalidates `scripts/premarket_stars.py`

That tool awards a **plus** for rotation — pre-market volume as a multiple of
float — and awarded CLRO for **27× the float traded pre-market**. By this rule
that is the single most damning fact about the setup, not its best feature. It
also imposes a 250,000-share pre-market **floor**, which would have rejected
NCTY.

The 250k floor is defensible as a *scanner* setting and is cited as one
(`1zBC9RKwfeU` 1:06:48). Rewarding rotation is not defensible at all. Fixed in
the same commit as this report.

## 4. `float_max` is regime-conditional, and "5M ideal" is a misreading

§1 says `float_max <= 20M`, conflict *"10M preferred, 5M ideal"*. The 5M is not
an ideal — it is a **cold-market setting**:

> *"I focus on stocks with a float under 20 million shares, and **when the
> market is colder, I tighten that down to under 5 million.** Lower supply
> makes it easier for even a moderate amount of demand to create a strong
> move."* — `risk-psychology/can-you-trade-in-a-cash-account.md`

"Ideal" implies a preference you indulge when convenient. "Colder market"
implies a rule that *changes*. Under the first reading a 15M float is always
acceptable-but-not-great; under the second it is fine in a hot tape and a
rejection in a cold one.

This is the only regime-conditional parameter found in the whole spec, and
`reports/2026-08-regime-filter.md` tested regime **as a filter on entries** and
found it useless. It never tested regime as a modifier of the universe. Those
are different experiments and the second one is untried.

**`float_max: 20M` hot / `5M` cold.** Regime definition still open.

## 5. `stop_max_distance` is 0.30, not 0.20

§5 gives `stop_max_distance <= 0.20` with **no `n` and no citation** — one of
only two numbers in §5 with neither. His own numbered rule list says 30:

> *"Rule number four, tight stops, **30 cent max loss**. If I have a 50, 60, 70
> cent loss, that's going to start to trigger the emotions."*
> — `recaps/starting-off-september-grateful-334.md`

Note the justification is **emotional, not mechanical** — the number is where
his discipline breaks, which is why it belongs with the daily limits in §8
rather than with the chart-derived stop in §5.

`stop_typical` 0.08–0.10 is confirmed independently: *"I jump in with a 10 cent
max loss"* (`18558-14-as-i-cruise-over-100k`), *"my entry at 67, my stop is at
57"* (`ross-is-back-in-action`).

**`stop_max_distance: 0.20` → `0.30`.**

## 6. The session is 90 minutes, and it ends before 11:30

§2 gives `session_close 11:30 hard stop`. He frames it as a duration, not a
clock time, and the duration ends earlier:

> *"For me, I'm in the zone... for most days, it's from **9:30 until 10:30 or
> 11:00**. So right around that **90 minute mark**, which is short enough that
> I'm really able to stay focused."*
> — `recaps/starting-off-september-grateful-334.md`

11:30 is the outer edge of a distribution whose centre is 10:30–11:00, and §2
already gives `prime_window 09:30–10:30`. A backtest holding to 11:30 is
trading 30–60 minutes he is not in.

## 7. Pre-market trading is time-conditional — the spec froze the wrong era

§2: `premarket_start 07:00 — limit orders only, n=38`. In 2017 he did not trade
pre-market at all:

> *"**I've traded pre-market maybe half a dozen times in the last year**, so
> probably won't trade pre-market. I'll just trade 9:30 to noontime."*
> — `other/3-lessons-making-60k-1-month-behind-trades-ep-4.md`, lastmod
> **2017-03-04**

In the July 2026 small-account challenge, `07:00` is named **78 times against
36 for `09:30`**, and `pre-market` **161 times against 9 for "the close"**
(`reports/2026-07-challenge.md`).

**The practice reversed.** "Limit orders only" is the 2017 rule preserved as if
it were current. Any parameter sourced from the 2017–2019 blog needs a date
stamp before it is trusted as present tense — the blog carries `lastmod` in
every file header, and nothing in the pipeline has ever read it.

---

## Confirmed unchanged (first pass)

Worth stating, because the audit could have found rot everywhere and did not:

- **The five pillars, verbatim.** *"$2 and $20, up at least 10%, relative
  volume of 5x or higher, float under 20 million shares, and any breaking
  news"* — an exact match for §1 in a register §1 never consulted.
- **`price_min` $2.00** — reinforced by `candlesticks/mastering-candlestick-charts`
  and `chart-patterns/how-to-trade-the-bull-flag-pattern-with-confidence`.
  The stray "$1 and $20" in `the-simple-scalping-strategy` remains the minority.
- **`price_sweet` $5–10** — *"My sweet spot is stocks priced between $5 and $10
  per share"* (`getting-started/how-much-do-day-traders-make`).
- **§8 in full**, from the numbered rule list: max daily loss equal to the daily
  goal ($2,000 / $2,000), broker-enforced; three reds and done; give back half
  the day's peak and walk away. Every §8 row has a blog citation now.

---

# Second pass — §3 and §6

## 8. `price > ema9` as an instantaneous boolean rejects the setup it defines

§3 lists `price > ema9` (n=30) as a hard condition evaluated at entry. The blog
states it with a qualifier that changes what it tests:

> *"The price should **generally** stay above the 9 EMA. **When prices dip below
> the 9 EMA but then recover, it often signals a robust potential for a bounce
> back.** However, **sustained** trading below this line usually suggests a more
> profound bearish sentiment."*
> — `blog/core-strategy/my-journey-from-breakout-to-pullback-trading`

A dip below the 9 EMA that recovers is **bullish** — it is the micro-pullback.
Only *sustained* trading below is bearish. Evaluated bar-locally as
`price > ema9`, the gate rejects precisely the recovery the strategy is built
on, and admits only setups that never dipped.

This is §13's *"first candle to make a new low"* defect exactly: a rule about a
**sustained state** implemented as an **instantaneous test**. That defect
dropped median hold to 2 minutes; this one silently removes the pullbacks.

**Needs a persistence term** — `n` consecutive closes below, not one touch.

## 9. The MACD condition may be two conditions, and §3 encodes one

§3: `macd_hist > 0`, *"MACD 12/26/9, no custom settings"*. §13 settles "front
side of the move" with:

> *"Only trade when MACD is **positive and above the signal line**"*
> — `iIC62xnblLc` [26:20]

Those are two different tests. **MACD line > 0** means the 12 EMA is above the
26 EMA. **Histogram > 0** means the MACD line is above its signal. The blog
confirms the second reading is what the histogram measures —

> *"When the histogram crosses above the zero-line, that means that the MACD
> line has crossed above the signal line"*
> — `blog/core-strategy/best-momentum-indicators`

— which means the histogram test does **not** cover "positive". The spec
encodes one of the two conditions in the sentence it cites.

Flagged rather than fixed: §13 records that adding three extra gate conditions
cut the pass rate from 6.7% to 3.5%. Test `macd_line > 0` as a **separate
variant**, do not merge it into the gate on the strength of one sentence.

## 10. The scale ladder is setup-dependent, not 50/25/25 everywhere

§6: `scale_1_pct 50`, `scale_2_pct 25`, `runner_pct 25` (n=36). The article
dedicated to the pullback setup gives a different ladder and a nearer target:

> *"First target is the quick breakout — **10 to 15 cents**. I usually sell
> **75%** of my position into strength and hold the rest for the next breakout
> level. Once partial profits are taken, I move my stop to breakeven."*
> — `blog/core-strategy/pull-back-trading-strategy`

75/25 on the quick breakout against 50/25/25 in general, and 10–15¢ against the
spec's `target_typical` 15–20¢. Both are his. Which applies depends on the
setup, and §6 presents one as universal.

This matters more than it looks: §13 records that removing the 2:1 veto turned
expectancy negative *"because target 1 then sits under 2R and half the position
books a sub-1R gain"*. **At 75% rather than 50%, three-quarters books that
sub-1R gain** — so the open target question in `NEXT-STEPS.md` §4 is
load-bearing on a scale figure the spec has wrong for this setup.

`breakeven_trigger` is confirmed by the same sentence: stop to breakeven after
the first scale.

---

# Third pass — §7, §8b, §9

## 11. §9's `min_reward_risk = 2.0` never happened. His best month was 1.42.

This is the largest finding in the audit, and the corpus contained the answer
the whole time. `behind-trades-get-trading-rut-ep-7` puts two months of his own
TraderVue report side by side:

| | April (lost money) | February (best of the year) |
|---|---|---|
| accuracy | **60%** | **68%** |
| average winner | **$781** | **$1,870** |
| average loser | **$1,364** | **$1,318** |
| **win/loss ratio** | **0.57** | **1.42** |
| net | −$4,229 | +$70,000 |

§9 builds its expectancy table on `min_reward_risk >= 2.0` and concludes:

> *"At 2:1 and 60%, expectancy is +0.8R per trade. Two trades a day at 2% risk
> is +3.2% daily — which is implausibly high and is exactly why this needs
> testing rather than believing."*

It was implausible because **the input was wrong**. He has never posted a 2.0.
His *best month of the year* was **1.42**, and the 60% month in the same report
ran at **0.57** and lost money. §13 already established that `min_reward_risk`
is a realised ratio rather than a veto; this supplies the realised values, and
they are half the spec's figure.

Recomputed on his own numbers: 0.68 × 1.42 − 0.32 = **+0.65R**, not +0.80R.

## 12. The decisive variable is `avg_win`, not `win_rate` — he says so

Between his worst month and his best, accuracy moved 8 points (60 → 68) while
the average winner moved **2.4×** ($781 → $1,870). The average *loser* barely
moved at all ($1,364 → $1,318).

> *"This shows me that my **risk wasn't actually any different** between April
> and February. What was different was that **I wasn't getting the home run
> trade**... Now, accuracy was only slightly better. **The big difference was
> the profit/loss ratio.**"*

Everything §1 gates on — price, float, catalyst, rvol — is selection, and
selection moves the win rate. The variable that decided a −$4,229 month from a
+$70,000 one is on the **exit** side. `reports/2026-08-score-basket.md` found
selection features predict only risk and never upside (max |r| = 0.19); this is
the same result stated from inside his own P&L.

`NEXT-STEPS.md` §4 ("what should target 1 be") is therefore not one open
question among several. It is the one that decides the strategy.

## 13. §9's accuracy figures are understated, and verified

§9: *"Stated accuracy targets: 50% floor, 65–75% claimed."* "Claimed" undersells
it — the number is third-party-tracked and repeated over enormous samples:

> *"I've taken over **24,268 day trades**... Currently, I'm trading with an
> accuracy of **69%**."* — `blog/core-strategy/bull-flag-trading`

> *"since 1/1/2017 accuracy is **70%**... over **15,000 trades**"*
> — `blog/recaps/trade-recap-max-loss`

An article is titled *"Momentum Day Trading Strategies Gave a **Verified**
Accuracy of 69%"*. Monthly accuracy swings 60–68%; the lifetime figure is
69–70%. **Use 69% as the prior and treat the month-to-month spread as the
uncertainty**, rather than the spec's 50% floor.

## 14. `size_ladder` is linear, not geometric

§7: `size_ladder 100 → 200 → 400 → 800` — doubling. The blog states the ramp
he actually teaches:

> *"this approach of **starting with 100 shares and then increasing by 100
> shares each week** has been very successful."*
> — `blog/getting-started/5-steps-to-success-trading-online`

100 → 200 → 300 → 400. By week 4 the spec has a beginner at **800 shares**
against his 400 — double the risk at the point in the ramp where a beginner is
least equipped to carry it.

The spec also has no ceiling. He states one: *"I'll probably **max out share
size at 20,000 shares**"* (`3-lessons-making-60k`), corroborated by *"I don't
think I had any trades in the month where I had more than 20,001 position"*.

## 15. §7 is missing the intraday size ramp entirely

Size is not a per-trade constant re-derived from the stop. It **starts reduced
each day and is earned back within the session**:

> *"I began each day by trading with **a quarter of my normal share size**. So
> if I usually trade 20,000 shares, I'd start with 5,000 instead. I told myself
> — **don't size up until you're already up at least $1,000 on the day.**"*
> — `blog/other/how-being-a-great-loser-can-lead-to-day-trading-success`

Seen live too: *"I would typically start with 2,500 shares, but I know how
quickly I could lose 30 cents... I'm just gonna start with 1,500"*
(`day-102-100k-challenge`).

This is §8's daily-limit logic running **forward** instead of backward — the
account is protected at the open, not only after losses. A backtest sizing every
trade identically overstates early-session risk on every single day.

And the mirror image, which he names as a **mistake**: *"I start with 5,000
shares, it goes up $0.20, I'm up $1,000 and **I double to 10,000**... it comes
back down to break even and I stop out flat"* (`day-72-583-challenge`).

`max_trades_per_day: 1–2` is also low. Observed: *"Three trades today"*
(`profit-trading-day`), *"four stocks... four individual trades and a total of
like 22 individual [executions]"* (`day-90-live-las-vegas`).

## 16. §8b is CORRECT and part of the corpus is wrong — do not "fix" it

The dedicated article confirms the spec verbatim:

> *"All Tier 2 stocks that closed the previous day below 75 cents will have
> trading halt thresholds at **the lessor of 15 cents or 75%**."*
> — `blog/rules-regulation/circuit-breaker-halts`

Another blog article contradicts it: *"if a stock priced under 75 cents
experiences a **15% price jump or drop**, it triggers a halt"*
(`blog/risk-psychology/rollercoaster-day-of-trading`). **That is wrong** — 15%
is not the rule, 15 *cents* or 75% is. The spec took the regulatory version and
should keep it.

Recorded here because the obvious next move on finding a conflict is to
"reconcile" it, and reconciling toward the majority would corrupt a correct
parameter. `halt_trigger_dwell` 15 seconds and the 10% / 20% tiers are
independently confirmed (`a-wild-ride-through-40-halts`,
`rollercoaster-day-of-trading`).

Two additions §8b lacks:

- **The doubling window has exact times**: *"the volatility bands are doubled
  to accommodate increased volatility near the closing bell **between
  3:35pm–4pm**"*. §8b says "opening and closing auctions" without hours. The
  opening window's exact times are still unstated in the corpus.
- **A halt is 5 minutes *minimum*, and downside halts run long**: *"At 9:36 a.m.
  trading halted from a circuit breaker down at $17.36. It took **20 minutes**
  before trading resumed... shares dropped to begin trading at $13"*
  (`blog/market-news/peck-electric-700-epic-short-squeeze-archives`). A bot
  modelling halts as 5-minute gaps will mis-handle the case that costs most.

---

## Still not audited

§4 entry trigger. The blog's uses of *"first candle to make a new high"* are
illustrative rather than definitional (`3-lessons-making-60k` walks failed
examples), and nothing was found that qualifies or contradicts §4. `order_type`
and `max_slippage 0.15` have **no blog support in either direction** — they
remain the least-evidenced parameters in the spec.

## The pattern, across both passes

Every one of the ten findings is a **type error**, never an arithmetic one:

| the corpus says | the spec encodes |
|---|---|
| a scanner dial | a hard gate (§15) |
| a sustained state | an instantaneous test (§13, and finding 8) |
| a caution | a veto (§13) |
| a conditional rule | a universal one (findings 4, 10) |
| a dated practice | a timeless rule (finding 7) |
| two conditions | one (finding 9) |

Ten for ten at that point, and sixteen for sixteen by the end. The next
implementation should be reviewed against *that* list rather than against the
numbers — the numbers were almost never the problem.

One new rejection reason appeared and has no home in the spec: *"TA, **five
cent tick**"* (`starting-off-september-grateful-334`) — a tick-size / spread
gate, rejected at the scanner before price or float. §10 lists `spread width`
(66 mentions) under tape reading as "a liquidity gate that quote data gives
you", but §1 has no such filter.
