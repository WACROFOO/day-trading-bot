# What the live streams say that the rest of the corpus does not

The whole project has been built on two registers: 257 teaching videos and 68
daily recaps. Both are hindsight — the teaching videos explain a setup with the
chart already finished, the recaps narrate a session that has ended. A third
register existed the entire time and was never touched: **480 live streams on
the channel's `/streams` tab, none of them in the 2,211-video index**, which was
scraped from `/videos` only.

**All 289 of the selection that YouTube would serve are transcribed —
~1,336,000 words, 241 hours.** This is what they change.

---

## 1. The micro-pullback is often a **10-second** pattern. Our detector cannot see it.

The single most consequential finding. He narrates entries like this:

> *"this is a 10 second micro pullback so let it pull back and then we'll get
> that curl up through 20"* — [`6xIr761eZj8` 41:38](https://youtu.be/6xIr761eZj8?t=2498)

> *"So there's 12 on the ask, 13 on the ask. This is a 10-second micro pullback.
> Looking for the break of 14 and 15."* — [`XIQUoLyUWuw` 33:32](https://youtu.be/XIQUoLyUWuw?t=2012)

> *"this is a 10 second pullback one minute pullback so looking for 48 65 4870"*
> — [`9OK-AaPJens` 55:08](https://youtu.be/9OK-AaPJens?t=3308)

Not an aside. Across 289 streams:

| | mentions | streams |
|---|---:|---:|
| "10 second" | 250 | 117 of 289 |
| "10 second" near pullback/dip/curl/candle | 173 | 93 of 289 |
| "micro pullback" | 229 | 117 of 289 |
| "tick chart" | 7 | 5 of 289 |

And when a "micro pullback" is explicitly qualified by a timeframe: **1-minute
59 times, 10-second 19 times**, 141 unqualified. Both charts are in live use;
the 10-second one is what he reaches for on the fastest movers.

**It is not a 2021-era habit.** The streams are almost all 2021–2023 (see
Caveats), so the practice was checked against the other two registers, which
run to July 2026:

| register | "10 second" | files |
|---|---:|---:|
| streams (2021–23) | 250 | 117 of 289 |
| **daily recaps (Jun–Jul 2026)** | **24** | **15 of 68** |
| teaching videos (to 2026) | 233 | 80 of 257 |

All three agree. The 10-second chart is current practice, not something he
stopped doing.

**Why this matters more than any parameter we have argued about.** The engine
runs on 1-minute bars with `MIN_DIP_BARS = 2`, so the shortest thing it will
call a pullback is a **two-minute** dip. His is often twenty seconds. On a
1-minute chart a 10-second pullback is not a candle — it is the wick of one.

That is a mechanical explanation for the finding in
`2026-08-target-and-entries.md`: setups reach target 1 on 56% of signals, but
the median excursion first runs **−1.56R**, and 43% go past −2R. We are not
entering his pullback. We are waiting for a dip deep and slow enough to be
visible at our resolution, which on a fast mover means the pullback he bought
is already over and what we are buying is the one that fails.

`PARAMETERS.md` §13 already flagged this as a suspicion — *"the source also
reads a 10-second chart, where a 1-minute pause IS a 2-3 candle pullback"*. The
streams turn the suspicion into evidence. It also means **the fix is not a
parameter change**: 1-minute bars cannot represent a 10-second pullback at any
setting. `DATA-SOURCES.md` records that sub-minute data needs a paid feed. That
decision now has a specific thing to buy and a specific reason.

---

## 2. He trades a **position**, not a trade. We model a trade.

The engine takes one entry, scales out at target 1 and target 2, exits, and
increments a counter toward `max_trades`. That is not what the streams show.

> *"Taking little profit and then looking to add back. Flat. Watching for
> another dip."* — [`0uunIYE_wVY` 15:19](https://youtu.be/0uunIYE_wVY?t=919)

> *"Add back 67. Now looking for the break of 70. Buying the dip off the flat
> bottom, 56. Going flat 51 for now. Add back at 51, bought the dip."*
> — [`1NZS5CqCnj8` 42:13](https://youtu.be/1NZS5CqCnj8?t=2533)

> *"Adding at 68 right there. Now looking for the rip through seven. Adding at
> 88, scaling into this."* — [`0zXUMrYyTx0` 56:22](https://youtu.be/0zXUMrYyTx0?t=3382)

And stated as a method, not a habit:

> *"in phase five, we're also scaling into trades. Starter position, half size,
> full size, then scaling out."* — [`-KcmoPm_skg` 57:50](https://youtu.be/-KcmoPm_skg?t=3470)

"Add back" and "scaling in" appear **328 times, in 138 of 289 streams**. A single name in
a single morning absorbs eight or ten entries and exits.

**What this does to our numbers.** `PARAMETERS.md` §6 has `scale_1_pct`,
`scale_2_pct` and `runner_pct`, so the exit ladder is modelled — but there is no
re-entry, and `max_trades` counts what he would call one position. Two
consequences:

- **The 65–75% accuracy is not comparable to our 27% win rate.** His is measured
  over many small scale-outs around a core, most of which are taken into
  strength. Ours is measured over 11 all-or-nothing positions.
- **Our trade limit is binding on the wrong unit.** Five "trades" a day in his
  vocabulary is five *names*; in ours it is five entries, which he would spend
  on one stock before 10:00.

---

## 3. The third pullback is **traded**, not banned

`PARAMETERS.md` cites `BUCPPCXOHbs` [52:17] for "third means stop", and the
engine enforces `pullback index <= 2` as a hard gate condition. Live, he counts
pullbacks constantly and then takes the third anyway:

> *"this is the third pullback. We had first pullback at 1282, second pullback
> here at 1350. Now we're on the third pullback. **Bought the dip at 68.**"*
> — [`0uunIYE_wVY` 19:22](https://youtu.be/0uunIYE_wVY?t=1162)

> *"second pull back now we're coming into third pullback range and you guys
> know my feeling about that **and what it needs to do in order for me** ..."*
> — [`RABUjMVS6pI` 52:34](https://youtu.be/RABUjMVS6pI?t=3154)

> *"the only problem is that we've already had the first second and third
> pullback — third pullback was the weakest of them all"*
> — [`txPT1JwFUJQ` 24:42](https://youtu.be/txPT1JwFUJQ?t=1482)

The rule is real but it is a **caution with conditions attached**, not a veto.
Ours is a boolean that discards the setup.

**Applied.** `pullback index <= 2` moves out of `GATE_CONDITIONS` and becomes a
half-size reduction (`LATE_PULLBACK_SIZE`). Over the 17 sessions: 11 trades →
**13**, −$601.65 → **−$588.90**, win rate 27% → 31%. A correct reading, not a
fix — nothing here closes the gap, and §1 is the reason why.

---

## 4. "Too extended" means **smaller size**, never "skip"

The same shape as the `stop_max_distance` misreading already corrected in
`HISTORY.md` #7 — and here it is in his own voice, in real time:

> *"It's obviously strong. But I got to go with smaller size cuz I'm chasing it
> a little bit."* — [`0zXUMrYyTx0` 49:27](https://youtu.be/0zXUMrYyTx0?t=2967)

> *"Holding 700 shares. Sizing down to smaller size right now, watching this 1
> minute pullback."* — [`GqAr6Dj8I6k` 39:57](https://youtu.be/GqAr6Dj8I6k?t=2397)

> *"it's a little extended here but we're coming into the open so a little dip
> there"* — [`6xIr761eZj8` 38:17](https://youtu.be/6xIr761eZj8?t=2297)

Extension is a **risk dial**, continuous. The engine has no such dial: a setup
either passes eight booleans or does not exist.

---

## 5. `price_min` resolves to **$2.00** — and my earlier suggestion was wrong

`NEXT-STEPS.md` §7 had this open, and the July calibration suggested lowering
the floor to $1.00 because it nearly doubled recall of names he mentions.
The streams settle it the other way:

> *"JOB is 56 cents. So, that's too cheap for me. I don't like that. Not even
> sure exactly how it made its way onto the gap scanner."*
> — [`1zBC9RKwfeU` 10:36](https://youtu.be/1zBC9RKwfeU?t=636)

> *"naov 56 cents that's too cheap — Ruby 58 cents that's too cheap"*
> — [`1bOSP_Tz7_g` 24:40](https://youtu.be/1bOSP_Tz7_g?t=1480)

> *"cxdc 115 it's a little too cheap"* — [`SwkXSGUHvHY` 04:20](https://youtu.be/SwkXSGUHvHY?t=260)

That last one is decisive: **$1.15 is "a little too cheap."** "Too cheap" is a
routine rejection phrase, and it is applied at and above $1. **Keep
`PRICE_MIN = 2.0`.**

This also revises the July calibration's reading. Sub-$2 names appearing in the
recaps — IQST at $1.14, TGHL $1.28, CJMB $1.27, ZYBT $1.27 — were most likely
*discussed and rejected*, not traded. It is direct support for the caveat that
"named in a recap" is not "traded that session", and it means one of that
report's two headline scanner fixes should be dropped.

---

## 6. The float ceiling is soft, and 20M is about right

Live commentary spans the range rather than cutting at a number:

| float | verdict | source |
|---|---|---|
| 7.1M | traded it (AMLX) | [`0uunIYE_wVY` 02:11](https://youtu.be/0uunIYE_wVY?t=131) |
| 7.7M | *"float is pretty low"* — but news weak, passed | [`HRYd26U6Gbk` 58:00](https://youtu.be/HRYd26U6Gbk?t=3480) |
| 23M | *"a little higher"* — still watched | [`0uunIYE_wVY` 1:09:43](https://youtu.be/0uunIYE_wVY?t=4183) |
| 35M | *"float's too high"* | [`1zBC9RKwfeU` 10:36](https://youtu.be/1zBC9RKwfeU?t=636) |
| 50M | *"a little too expensive also"* | [`1NZS5CqCnj8` 05:01](https://youtu.be/1NZS5CqCnj8?t=301) |
| 200M | *"isn't something that I would really look at"* | [`1zBC9RKwfeU` 10:02](https://youtu.be/1zBC9RKwfeU?t=602) |

`NEXT-STEPS.md` §7 asked 20M vs 10M. Answer: **20M as a soft ceiling is
defensible**, 10M would be too tight — he traded a 23M float and watched a 28M
one. Leave it.

---

## 7. A "no trade day" is a **result**, not a failure

The engine halts on max daily loss, profit goal, three straight losses, or the
trade limit. It has no concept of *nothing was good enough today*, and the
17-day run's low frequency has been treated throughout this project as a defect
to be fixed. He treats it as correct behaviour:

> *"a no trade day is certainly better than red trades. ENTX, NLSP, neither of
> those are looking great right now."* — [`0zXUMrYyTx0` 23:18](https://youtu.be/0zXUMrYyTx0?t=1398)

> *"green is good, better than yesterday where I didn't take any trades —
> yesterday was a no trade day"* — [`KqqbeeA8Kec` 30:03](https://youtu.be/KqqbeeA8Kec?t=1803)

> *"At this point, I probably wouldn't take a trade given that we're only 10
> minutes to the bell."* — [`0zXUMrYyTx0` 19:30](https://youtu.be/0zXUMrYyTx0?t=1170)

This does not excuse our 11 trades in 17 sessions — his frequency is far higher
than ours once §2 is accounted for. But it does remove "the engine trades too
rarely" as a standalone bug. Frequency is an output, not a target.

---

## 8. Halts: he reads a resumption price we do not have

1,570 mentions across 162 of 289 streams, with operational detail absent from
the teaching corpus:

> *"BTMD, hitting our scans. **I can see the halt level is at 709.**"*
> — [`0uunIYE_wVY` 1:09:43](https://youtu.be/0uunIYE_wVY?t=4183)

> *"B Q halted, let's take a look. **NYSE stock, so we're not going to see a
> resumption price.**"* — [`0uunIYE_wVY` 53:53](https://youtu.be/0uunIYE_wVY?t=3233)

> *"it's looking like a real halt so no trade going into that spot"*
> — [`fy1NpvXJq0U` 1:03:37](https://youtu.be/fy1NpvXJq0U?t=3817)

Our halt model (`PARAMETERS.md` §8b) infers a halt from a gap in the bars and
applies a 5-minute minimum. He sees the *indicative resumption price* during the
halt on Nasdaq names, and knows he is blind on NYSE ones. That is a real
information asymmetry, and it is the input to "not resumed lower after a halt" —
a gate condition we currently evaluate from price action after the fact.

---

## 9. What he says at the moment of entry is mostly about the **tape**

With 1.1M words there are enough live entries to ask what he mentions *while
buying*. 1,803 utterances match "bought the dip / buying the dip / added at /
adding at / I'm a buyer / took the entry". Against a 4,000-sample random
baseline from the same text, so the numbers are enrichment and not word
frequency:

| said within ~120 chars of an entry | near entry | random text | enrichment |
|---|---:|---:|---:|
| **Level 2 / the tape** (bid, ask, seller) | **17%** | 7% | **2.5×** |
| 1-minute chart | 9% | 3% | 2.8× |
| "curl" / "curling up" | 7% | 3% | 2.8× |
| 10-second chart | 3% | 1% | 4.3× |

Two things follow.

**He does not verbalise the gate.** No condition appears near even a fifth of
entries. Most are terse — *"added at 68"*, *"bought the dip"*. The eight
booleans our engine requires simultaneously are not what he is checking out
loud in the moment.

**The most frequent companion of a live entry is the order book** — and it is
the one input the engine structurally does not have. `PARAMETERS.md` §3 lists
`tape_green` and `no_seller_wall` as gate conditions, and `sim.py` records both
as *unverifiable* because OHLCV contains no depth. So the thing he cites most
at the moment of entry is the thing we cannot see at all.

That is a second, independent reason the timing is off, and it points at the
same purchase as §1: sub-minute bars and Level 2 come from the same feed.

---

## What to change, in order

| | change | cost | confidence |
|---|---|---|---|
| 1 | ~~`pullback index <= 2` from a gate condition to a size reduction~~ **done** | one line | high — §3 |
| 2 | keep `PRICE_MIN = 2.0`; drop the July calibration's $1.00 suggestion | one line | high — §5 |
| 3 | keep float 20M | none | high — §6 |
| 4 | stop treating low trade frequency as a bug | none | high — §7 |
| 5 | model re-entry: allow adding back into a name after a scale-out, and count *positions* not *entries* against `max_trades` | substantial | high — §2 |
| 6 | sub-minute bars for the entry trigger, and Level 2 depth | paid data | **this is the timing answer** — §1 and §9, same feed |

Items 1–4 are free and are done. Together they moved the 17-session run from
11 trades / −$601.65 to 13 / −$588.90 — which is the point: the free changes
were never going to close a gap that §1 says is a resolution problem. Item 5
is the largest modelling gap in the engine. Item 6 cannot be done on free data,
and it is now the clearest justification for the `DATA-SOURCES.md` decision
that this project has produced: not "more sample", but *the resolution at which
the entry actually happens*.

---

## Caveats

- **Auto-captions.** Prices lose their decimal point routinely — "added at 710"
  is $7.10, "first pullback at 1282" is $12.82. Tickers garble.
- **Selection bias.** Titles were filtered for live trading, and stream titles
  skew to good days ("+$28k", "Green Day"). Use these for *what he does*, never
  for *how often it works*.
- **289 of 296.** The first pass lost 27 to YouTube's bot check, and because
  the fetch list was sorted by duration those were the 27 *longest* streams —
  losing exactly the long tail would have biased every per-stream count. A
  slower sequential retry recovered all 27. Every count above was recomputed at
  82, 154, 266 and 289 streams and the ratios did not move: "10 second" held at
  36–41% of streams throughout.
- **The streams are 2021–2023, not 2026.** Of 274 with a real upload date: 47
  from 2021, 174 from 2022, 45 from 2023, and **one** from 2026. The live
  Morning Show largely stopped after 2023. **None fall inside the
  2026-07-09..07-31 bar-data window**, so — contrary to what I suggested when I
  found the tab — they cannot be used as a labelled set against our minute
  bars. The recaps remain the only calibration set. What the streams give is
  *method*, checked against 2026 in §1.
- **No dates on most.** The flat listing carries no `upload_date`, so these are
  not yet mapped to sessions. Several are visibly from 2021 (`4/15/2021` in a
  title), so this is not a July-specific picture — it is how he trades.

## Reproduce

```bash
python scripts/mine_streams.py --list
python scripts/mine_streams.py timing timeframe add-back
python scripts/mine_streams.py price-floor float halt
```
