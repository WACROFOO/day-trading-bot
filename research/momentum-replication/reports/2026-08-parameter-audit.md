# Parameter audit — the spec against all four registers

`PARAMETERS.md` closes with: *"Derived from `rules_digest.md` — 2,040 rules,
2,903 numeric figures, **257 videos**."* The 2,063 blog articles were fetched
after it was written and have never been used to check a single number.

This is that check. Every parameter re-read against teaching, recaps, streams
**and blog**, looking specifically for interpretation errors rather than typos —
§13 already establishes that in this corpus the numbers are usually right and
the readings are usually wrong.

Seven corrections. One of them invalidates a tool built three days ago.

---

## The structural error: a scanner setting is not a trade gate

Six of the seven findings are the same mistake wearing different numbers. §1 is
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

## Confirmed unchanged

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

## Still not audited

§4 trigger, §7 sizing ladder, §8b halts, §9 expectancy. The blog has not been
searched for any of them.

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

Ten for ten. The next implementation should be reviewed against *that* list
rather than against the numbers.

One new rejection reason appeared and has no home in the spec: *"TA, **five
cent tick**"* (`starting-off-september-grateful-334`) — a tick-size / spread
gate, rejected at the scanner before price or float. §10 lists `spread width`
(66 mentions) under tape reading as "a liquidity gate that quote data gives
you", but §1 has no such filter.
