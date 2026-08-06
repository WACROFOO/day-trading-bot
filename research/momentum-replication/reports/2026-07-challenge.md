# The July 2026 small-account challenge — what he traded, when, and why

All 36 July 2026 recaps, read as one series. `scripts/challenge_july.py`.

**The setup:** a **$2,000 account at Charles Schwab**, day-numbered, profits
donated to charity. Day 16 falls on 7 July and day 27 on 28 July, so the
challenge runs roughly one number per trading day through the month.

## The account

| date | state |
|---|---|
| start | **$2,000** |
| 3 Jul | "over $20,000 from a $2,000 starting balance" |
| 7 Jul | **+930%**, $18,605 of profit |
| 13 Jul | "a little over $23,000" |
| 16 Jul | **$29,471, up over 1,300%** |
| 20 Jul | +1,400% |
| 23 Jul | +1,600% |
| 27 Jul | **"just shy of 2,000%"** ≈ $42,000 |

$2,000 → ~$42,000 in about 26 sessions.

## WHEN — and this is the finding

Clock times named across the 36 recaps:

| time | mentions |
|---|---|
| **07:00** | **78** |
| 09:30 | 36 |
| 04:00 | 32 |
| 08:30 | 14 |
| 07:30 | 13 |
| 09:00 | 13 |
| 08:00 | 12 |

Session-phase language:

| phrase | mentions |
|---|---|
| **pre-market** | **161** |
| after hours | 72 |
| the open | 62 |
| opening bell | 33 |
| **the close** | **9** |

**07:00 is named more than twice as often as 09:30, and "pre-market" 18 times
more often than "the close".** Entry statements carry pre-market context 15
times against 8 for the open. Actual entries quoted in the recaps include
**07:06** and **07:15**.

One July recap is titled, in full, **"The REAL Reason Pre-Market Trading Is
Better…"**

## The failure mode, in his own words

The month's max-loss day (28 July, DFNS):

> *"Today was one of those days where we had **no action during the pre-market
> session**. So I sat down quarter of 7:00, was watching 7:00, 7:30, 8:00, 8:30,
> 9:00, 9:30. **There was nothing moving.** Coming into 7:00 a.m. our leading
> gainer was only up about 40%. And so **this is the type of day that I'm really
> susceptible to falling victim to FOMO. When a stock randomly squeezes up $15 a
> share after the opening bell** — and that's exactly what happened. **DFNS pops
> up just after the opening bell.**"

His biggest loss of the month is a **post-open entry taken because the
pre-market gave him nothing**. He names it as the mistake while describing it.

## WHAT — the names

Most-mentioned across the month: **BIYA (6), DFNS (6), ZCMD (5), CLRO (5)**,
then GMM, VEEE, ERNA, CJMB, ZYBT, CPHI, INLF, TC.

Of 36 recap titles: **8 say "squeeze"**, 4 "breaking news", 3 name a Chinese or
Taiwanese stock, 2 say "no news" explicitly.

```
07-06  346% Short Squeeze on Chinese Stock with No News!
07-09  250% Short Squeeze on Breaking News!
07-10  ANOTHER 250% Short Squeeze
07-14  A Reverse Merger Catalyst Sends Stock Squeezing Shorts
07-14  A 350% Short Squeeze!
07-15  Biotech Stock Squeezes 372% in 5 Minutes
07-20  Scaling into the Squeeze!
07-23  Another Chinese No News Short Squeeze!
```

## WHY — pattern and catalyst

Patterns named, by number of recaps:

| n | pattern |
|---|---|
| 9 | micro pullback |
| 9 | high-of-day break |
| 3 | dip and rip |
| 2 | break of VWAP |
| 2 | flat top |
| 1 each | ABCD, bull flag, reversal |

Catalysts:

| n | catalyst |
|---|---|
| 14 | **no news / squeeze** |
| 11 | breaking news |
| 3 | reverse merger |
| 1 | earnings |

**"No news" outnumbers "breaking news".** Pillar 3 as documented — *"a real
catalyst, or no trade"* — is not what he actually traded in July. The month's
signature trade is a low-float foreign small cap squeezing on nothing.

## How he frames risk (day 26, the record green day)

A viewer asked whether he was risking $30,000 on one trade:

> *"If I was risking $30,000 then it would mean I was going to hold until this
> went to zero… On this trade today I was taking probably more like **40 cents
> of risk per share**. So risk based on the number of shares and cents per
> share, that's the actual amount that was at risk. And in this trade my profit
> was about **two times the amount I was risking**."*

Position size ≠ risk. Risk is cents-per-share × shares. That is the same
formula in `PARAMETERS.md`, stated live under challenge.

## What this means for the replication

**Every backtest in this repo buys the 09:30 open.**
`2026-08-score-basket.md`, `2026-08-strategy-v2.md`, `2026-08-short-hold.md`
and `2026-08-regime-filter.md` all enter at or just before the bell — and
`2026-08-short-hold.md` even measured the 09:29 → 09:30 leg as **−1.50% median,
positive only 34% of the time**.

We have been testing, over 894 sessions, the entry he identifies as his own
FOMO mistake, while he is trading a window our data barely covers.

That does not make the pre-market window profitable — it is untested, and
`2026-08-vwap-condition.md` already showed our VWAP does not even include
pre-market volume. But it does mean the negative results so far are evidence
about **09:30 entries**, not about his method.

**Next:** rebuild the harness around a 07:00–09:30 entry window. That needs
pre-market bars with volume, which Yahoo does not supply (it reports 0 for
every extended-hours bar). It is the same data wall as the 10-second question,
approached from a different side — and it is now the highest-value thing to buy.
