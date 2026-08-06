---
name: premarket-stars
description: Pick the pre-market movers worth watching, the way Ross Cameron runs his gap scanner — sorted by gap %, rejected top-down on float and price before the chart, with every decision metric taken from finviz (Shs Float, Shs Outstand, Short Float, Avg Volume, Market Cap, sector, dated catalyst) rather than from OHLCV bars. Use whenever asked "what are the stars of the pre-market", "what's gapping", "what should I watch this morning", or to vet a single pre-market name.
---

# Pre-market stars

Any pre-market hour, 04:00–09:30 ET. There is no 12:00–14:00 window here — the
whole pre-market is in scope, and the answer changes minute to minute, so
always re-run rather than quoting an earlier list.

## The one command

```bash
python scripts/premarket_stars.py                 # gappers ≥10%, survivors only
python scripts/premarket_stars.py --all           # show what was rejected and why
python scripts/premarket_stars.py --min-gap 20 --top 30
python scripts/premarket_stars.py --json          # for further work
```

Print the surviving names with their reasons. Then add the two things the
script cannot do: the filings check and the chart shape (below).

## Where the numbers come from — and why it is split

| | source | why |
|---|---|---|
| who is gapping, gap %, pre-market volume/high/low | TradingView screener endpoint | the only free feed publishing **live** `premarket_change` |
| float, shares out, short float, avg volume, market cap, sector, catalyst | **finviz quote page** | published metrics, not derived from bars |

Finviz's free tier serves **last session's** price/change/volume before the
bell, so it cannot rank a pre-market list — but every number that *decides* a
name comes from it. Never quote finviz's `Change`, `Price`, `Volume` or
`Rel Volume` as pre-market figures; they are yesterday's.

## His method: a reject cascade, not a score

> *"I start at the top of the gap scanner. This is the way I have it every
> morning. And I have the gap scanner sorted by the percentage of the gap. So
> the biggest gapper is going to be at the top. Some people might sort by
> highest volume, some might sort by float, but I sort by the biggest
> percentage gap."* — `ZfwTJAMLroA` 12:15–12:35

> *"Before I even pulled up the chart, I saw that it was a 50 million share
> float. 50 million shares is a little on the higher side, especially for a
> stock priced at $1."* — `ZfwTJAMLroA` 12:49

Float and price kill a name **before the chart is opened**. That is the whole
trick, and it is why this runs on published metrics.

> *"Usually around 9:15 I want to move pretty quickly through the gap scanner,
> and if I don't see something right away that I like, then I just move on to
> the next one."* — `ZfwTJAMLroA` 30:26

### The gates, in order

| # | gate | threshold | provenance |
|---|---|---|---|
| 1 | price | $2.00–$20.00 hard; **$2.50–$9 preferred** | `PARAMETERS.md` §1; *"I prefer stocks generally between $2.50 and $8 or $9"* `ZfwTJAMLroA` 13:13 |
| 2 | float | **< 20M**, sweet spot < 10M | `PARAMETERS.md` §1 |
| 3 | volume | **≥ 250,000 shares** or it is not even on the scanner | *"the volume threshold is um 250,000 shares minimum"* `1zBC9RKwfeU` 1:06:48 |
| 4 | catalyst | a dated, same-day reason | finviz `whyMoving` block carries a `catalyst` boolean |
| 5 | still rising | **≤ 25% off the pre-market high** | *"if a stock is stair stepping down that's not bullish, I'm not a buyer on something like that"* `xgnqOu_fchA` 08:57 |

Not gates, but they separate a STAR from a WATCH:

- **rotation** — pre-market volume ÷ float. Above 1× the entire float has
  changed hands before the bell.
- **% of an average day** — pre-market volume ÷ finviz `Avg Volume`. Note the
  denominator is a 3-month **full-day** average and self-contaminates: a name
  that ran yesterday drags its own average up. Rotation vs float is cleaner.
- **short float ≥ 15%** — squeeze fuel, and a borrow problem if you ever short it.
- **sector** — he is warmer on biotech/pharma: *"it's not a biotech or
  pharmaceutical stock, so I'm skeptical"* `ZfwTJAMLroA` 13:31.

**No 0–100 score is produced, on purpose.** `reports/2026-08-score-basket.md`
measured the pillar score against equal weight and it lost **16 of 16** matched
pairs — the score carries negative information. Gates, then eyes.

## What the script cannot see — always add these by hand

1. **Capital structure.** finviz has no shelf and no ATM. On 2026-08-05 this
   was the decisive check: ASTC carried a **$24.5M ATM plus a $200M shelf
   against a $21M market cap**. Look for a live ATM, a recent reverse split
   (a sub-5M share count is the tell), and a dilution vote. See
   `reports/2026-08-05-recap.md`.
2. **The chart shape.** Metrics say a name qualifies; they never say it is
   *setting up*. Where is price against the pre-market VWAP? *"The fact that
   the price is below this level shows that it's weak"* `ZfwTJAMLroA` 14:12.
   Descending peaks? Run `python scripts/premarket_dd.py SYM` for the tape.
3. **The float number itself.** finviz's float is stale after an offering.
   Reconcile it against volume: if 3× the float has traded, one of the two
   numbers is wrong.

## Failure modes this project has actually hit

- **A stale screener row.** ZJYL was graded A on "2.43M pre-market volume,
  12.5× relative" from a screener snapshot. The tape said the prior regular
  session traded **12,117 shares** and the move was a 12-hour-old after-hours
  fade. Screener rows are point-in-time; published float and average volume
  are not. This is the reason for the source split above.
- **Faded ≠ dead.** JLHL was called dead at 08:45 (−32.6% off its peak, four
  descending peaks) and then ran **+125.7%** at the open — the day's biggest
  winner. Faded names run *more* on average, but only ~7% take out their
  pre-market high. Report the fade as a fact, not as a verdict, and say which
  way the base rate cuts.
- **The wrong RVOL denominator.** Using regular-session volume for a
  pre-market trader understates it wildly. CLRO's extended-hours volume was
  **771× its typical extended-hours volume and 3.7× its entire float**.
  Say which denominator you used, every time.
- **Late news.** WebSearch returns stale results for same-day moves. finviz's
  own `whyMoving` block is dated to the minute and is the faster read — it
  will even say *"No clear catalyst identified"*, which is an answer.

## Answering the question

When asked for the stars:

1. Run the script. State the ET timestamp — a pre-market list has a shelf life
   of minutes.
2. Give the survivors in **gap-% order**, each with float, price, rotation and
   the catalyst headline.
3. Name what was rejected and on which gate. The rejections are most of the
   value; they are what stops a $1.18 stock with a 4.4M float from being
   "interesting because it's up 17%".
4. Add the filings check and the chart shape for the top one or two only.
5. **If nothing survives, say so.** That is a normal morning:
   *"sitting down to a fairly sparse gap scanner — we really don't have a lot
   that looks interesting"* `fy1NpvXJq0U` 01:49.

Standing caveat: everything here is selection, not expectancy. Our replication
over 894 sessions was negative from the open
(`reports/2026-08-regime-filter.md`), and the documented edge in this
population is on the short side and largely unharvestable
(`reports/2026-08-known-edges.md`). Paper only.
