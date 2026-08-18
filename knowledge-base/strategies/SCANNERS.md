# The scanner spec — every Day Trade Dash strategy against the corpus

What each named strategy on the platform is actually filtering for, in his own
words, with the register and timestamp that says so. Companion to
`FILTERS.md` (which is the trade gate); this document is the **discovery
layer** only.

---

```
CORPUS · 258 teaching / 69 recaps / 290 streams / 2,090 blog · local, no network call
SOURCE  the 4 videos that walk the scanner library screen by screen:
        yg5E_mqGFGg  Stock Scanners for Beginner Day Trading Strategies   (full library tour)
        w97KlUrVDk0  How to Grow a Small Account with ZERO Experience     (alert anatomy)
        eCSzHYl8apo  scanner layout walkthrough                           (reversal + pullback)
        oKlhUSSHe2Q  How To Start Day Trading in 2026                     (five pillars scan)
        jfe1Zl-5EQI  reversal training                                    (RSI / Bollinger)
! NO LIVE DATA IN THIS DOCUMENT. No price, no float, no RVOL is a market
  observation — every number below is a quoted scanner setting or a stated
  preference. Nothing here was checked against tape.py.
! THE PLATFORM'S OWN THRESHOLDS ARE SERVER-SIDE. They are not in the JS
  bundle (`ross-tradingview-mastery/references/source-analysis.md`). Where he
  never states a number, this document says UNKNOWN rather than guessing.
```

## Funnel

```
28 named strategies in the dumped config (8 alert widgets + 20 toplists)
  → 21 have a definition stated somewhere in the corpus
  → 11 have a NUMBER stated (the rest are qualitative: "low float", "big move")
  →  6 have no corpus coverage at all — listed as UNKNOWN, not inferred
```

## Evidence status, used on every row

`CONFIRMED` he states it · `QUALITATIVE` he defines it without a number ·
`OBSERVED` measured from an alert snapshot, not a threshold proof ·
`APPROXIMATION` our number, declared as ours · `UNKNOWN` not established

---

## Layer A · The shared dials

Every alert strategy is a combination of these four axes. Get these right and
the strategy names become mechanical.

| axis | tier | value | status | source |
|---|---|---|---|---|
| **price** | alert split | **under $20** vs **$20 and up** | CONFIRMED | yg5E [00:15:39], [00:19:05], [00:19:20] |
| | penny tier | shown from **~$0.10 up to $3–5** | CONFIRMED | yg5E [00:13:24] |
| | his own floor | *"56 cents… too cheap"* · *"$32, I won't trade it"* | CONFIRMED | w97 [00:53:20] |
| **float** | bright / act on it | **< 5M** — *"I should pay attention to it"* | CONFIRMED | w97 [00:54:55] |
| | interest fading | **11M, 15M, 20M and higher** — *"not as interested"* | CONFIRMED | w97 [00:55:01] |
| | "medium float" | example given at **48M** | CONFIRMED | yKV3C2DoaFg [00:36:38] |
| | dead | **50M at $1** *"a little too high"* · **667M** *"not even going to look at the chart"* | CONFIRMED | w97 [00:53:12], [00:53:27] |
| **relative volume** | "high" | **≥ 5×** the average | CONFIRMED | oKlhUSSHe2Q [00:30:18] + 6 more claims |
| | "low" | **2.5× is *"pretty low"*** — this is the only stated boundary for the medium tier | CONFIRMED | w97 [00:53:56] |
| | 5-minute RVOL | a separate displayed field, *"helpful for seeing volume spiking up right now"* | CONFIRMED | yg5E [00:08:38] |
| **volume** | floor | *"makes sure you're not trading something with 7,000 shares"* · 33,000 *"not going to work"* | CONFIRMED | w97 [00:54:48], [00:53:47] |
| | ceiling of relevance | **above 10M it stops mattering** — *"it just doesn't really matter"* | CONFIRMED | w97 [00:54:43] |

> **The float tier boundaries are the load-bearing finding here.** `< 5M` is
> not "the sweet spot" as a preference — it is the value at which he sets the
> colour gradient bright enough that he cannot miss it. `11 / 15 / 20` is
> where the colour and the interest both fade. That is a scanner setting
> stated as a scanner setting, which is rarer than it sounds.

**Session:** scanners run all day, he uses them **07:00–10:00 ET**
(w97 [00:47:48]) and stops at **11:30** (eCSzHYl8apo [00:09:52]).

---

## Layer B · Alert widgets — the event scanners

An alert fires once, on an event, with a timestamp. Rows do not update.
Exception: the 5 Pillars alert, which is a **state**, not an event — see below.

### B1 · Small Cap High of Day Momentum

The base event, stated three ways and consistent:

> *"the high of day momentum scanner… showing all the stocks that are making
> new highs"* — EHnIFKnJiXA [00:22:06]
> *"a high of day scanner is only giving you an alert when a stock makes a new
> high"* — w97 [01:00:41]
> *"stocks that are hitting a new intra-day high on high relative volume"* —
> blog `how-to-use-stock-scanners.md`

```
EVENT = new intraday high  AND  high relative volume
```

Then the 11 strategies are that event **classified** by the Layer A axes:

| strategy (as named in config) | filter | status |
|---|---|---|
| Low Float × High Rel Vol × under $20 | float low · RVOL ≥5× · price < 20 | CONFIRMED yg5E [00:15:30] |
| Low Float × High Rel Vol × $20+ | same, price ≥ 20 — *"bigger spreads… a little bit choppier"* | CONFIRMED yg5E [00:19:05] |
| Low Float × Medium Rel Vol | *"maybe you're just seeing the stock early in the move"* | CONFIRMED yg5E [00:18:38] |
| Medium Float × High Rel Vol × under $20 | *"high degree of algorithmic trading… more of a grinder, not usually something I'm going to really look at"* | CONFIRMED yg5E [00:17:44] |
| Medium Float × Medium Rel Vol × $20+ | *"not my favorite scanner"* | CONFIRMED yg5E [00:19:20] |
| **Former Momo Stock** | *"a stock that in the past went up **over 100% in one day**, and that's in the recent past"* | **CONFIRMED** w97 [00:58:29] |
| Squeeze Up 5% in 5min | +5% over ~5 minutes — *"kind of like a pre-alert"* for the 10/10 | CONFIRMED yg5E [00:17:16] |
| Squeeze Up 10% in 10min | +10% over ~10 minutes | CONFIRMED w97 [00:58:40], yg5E [00:16:36] |
| Squeeze Alert 52wk Breakout | *"the highest price this stock has been in a year"* | CONFIRMED w97 [00:56:04] |
| Low Float Volatility Hunter | *"it's a low float stock, **sub 1 million shares**"* | CONFIRMED w97 [00:58:35] |
| Squeeze Alert (plain) | rapid % move, window UNKNOWN | UNKNOWN |

**Two operational rules he states about this widget, both easy to miss:**

1. **The Former Momo scanner runs looser on purpose.**
   > *"low float former momo stocks, when they pick up, they can start moving
   > really quickly, and so for that reason I want to see them a little sooner…
   > some of the filters are adjusted a little bit so I could see it quicker.
   > I don't do that for every type of stock because otherwise you start
   > getting a lot of false alerts."* — yg5E [00:16:03]

   A replica that applies one threshold set to all strategies has deleted the
   former-runner early-warning, which is the one thing this widget does that a
   generic HOD scan cannot.

2. **Audio is on for exactly two of the eleven.**
   > *"I only have the audio alerts enabled for low float and squeezing up 10 in
   > 10 minutes. The others I don't use audio alerts for."* — yg5E [00:19:36]

   That is his own priority ranking, stated numerically. Everything else is
   eye-scanned, not interrupt-driven.

3. **Multiple simultaneous alerts is the actual signal.**
   > *"a stock hitting scanners more and more times is definitely a good
   > indicator that it's got some momentum"* — yg5E [00:17:02]; the SLKN
   > example fires Former Momo + Volatility Hunter + Squeeze 10/10 at once
   > (w97 [00:58:25]), the KSPN example the same (yg5E [00:15:26]).

   **Build the alert count, not just the alert.** No single strategy row is the
   trade; the stacking is.

### B2 · Penny High of Day Momentum

Same three events (Squeeze, 52wk Breakout, Volatility Hunter) on the penny
price tier: **~$0.10 to $3–5** (yg5E [00:13:24]). His own note on that tier:
*"which I typically don't trade."*

`FILTERS.md` softens this to a ~$1.50 floor **under a live penny theme** and
puts the real kill on the halt band, not the price. The scanner tier and the
trade gate genuinely differ here — that is the intended relationship, not a
conflict.

### B3 · Large Cap High Of Day Momentum

Same HOD event on large-cap names. No corpus statement of the market-cap or
float boundary. `UNKNOWN`. He describes the large-cap **room** as existing and
having its own HOD and reversal scanners (yg5E [00:20:42]); he does not trade
it in this corpus.

### B4 · Running Up / Running Down

The definition that a replica most often gets wrong:

> *"the running up scanner tells me when a stock is squeezing up right now even
> if it's below its high of day. **In fact, it has to be below the high of day.
> Otherwise we'll put it on the high of day momentum scanner.**"*
> — w97 [01:00:52]

```
EVENT = fast upward move  AND  price < high of day        ← the exclusion is the rule
```

The two widgets are **mutually exclusive by construction**. Running Up is not
"HOD momentum with a lower bar" — it is the complement set. He shows a trade
(VNCE) that HOD momentum structurally could not have alerted him to, because
his entry was below the day's high (w97 [01:00:34]).

Move size and window: `UNKNOWN`.

### B5 · Ross's 5 Pillars Alert

The only strategy whose full filter he states as a list, and the most recent
statement in the corpus (2026 training video):

| # | pillar | value | source |
|---|---|---|---|
| 1 | change on day | **up at least 10%** | oKlhUSSHe2Q [00:30:16] |
| 2 | relative volume | **5×** | [00:30:18] |
| 3 | catalyst | **news** — *"there are exceptions where we'll have sector-wide catalyst that I will trade, but those are always going to be a little riskier"* | [00:30:20] |
| 4 | price | **$2–20**, *"but between 5 and 10 is even better"* | [00:30:35] |
| 5 | float | **less than 10 million shares**, *"but lower is also better"* | [00:30:38] |

**This alert is a state machine, not an event log:**

> *"this is showing stocks that currently meet all five pillars… sometimes a
> stock will meet all five pillars, but then it'll sell off… at that point it
> was no longer worth considering. **So it dropped off this scanner.**"*
> — oKlhUSSHe2Q [00:31:00]

Rows appear **and disappear**. Implementing it as an append-only alert feed
produces a list that only grows and is wrong within twenty minutes.

### B6 · Reversal (10 strategies)

The one cluster with real numeric depth in the corpus — and the one with the
worst register split. See §Register warnings.

| component | value | source |
|---|---|---|
| **V5 variant** | **3 consecutive candles** — *"the filter is a little bit lower"* | eCSzHYl8apo [00:11:56] |
| **V8 variant** | **4 or more consecutive candles** | eCSzHYl8apo [00:11:49] |
| candle timeframe | **5-minute** (a 1-min variant also ships) | yg5E [00:21:08] |
| direction | consecutive **green** → top reversal (short) · consecutive **red** → bottom reversal (buy) | eCSzHYl8apo [00:10:03] |
| his stated ideal | **5 to 10 consecutive candles ending with a pin bar or a doji** | jfe1Zl-5EQI [00:18:10] |
| RSI, what interests him | **> 90 or < 10** | jfe1Zl-5EQI [00:17:55] |
| RSI, what the shipped hybrid filters | **> 80 or < 20** | jfe1Zl-5EQI [00:20:07] |
| Bollinger Bands | **20 period, 2 standard deviations**; a candle **fully** outside is the extreme | jfe1Zl-5EQI [00:20:41], eCSzHYl8apo [00:11:17] |
| 1-min confirmation variants | *"slightly different filters to try to help you find confirmation"* — the specific test is UNKNOWN | yg5E [00:21:58] |
| entry (from the scanner alert) | short the **first candle that makes a new low**, stop at the high | eCSzHYl8apo [00:10:30] |

**V5 vs V8 is a volume-of-alerts dial, and he switches it during the day:**

> *"there are some days where we'll have so many alerts on this you can't
> follow them all, so you go to the V8. There's other days where there are so
> few alerts on the V8 you want more ideas, so you look at the V5."*
> — eCSzHYl8apo [00:12:04]

Neither is "the setting". The pair is a rate control targeting a followable
number of alerts. Also stated: consecutive candles alone are not enough —
> *"they may be drifting down slowly but not quickly enough… we look for a
> combination of these indicators all occurring at the same time."*
> — jfe1Zl-5EQI [00:18:18]

### B7 · Halt

A list of halted symbols with timestamps, up-halts and down-halts both
(yg5E [00:14:23]). No filter. `FILTERS.md` carries the trading consequence
(bands by prior close); the scanner itself is unfiltered.

### B8 · Short Squeeze (beta) · Blue sky test (disabled)

- **Short Squeeze:** no corpus definition. Short interest and short ratio are
  displayed columns on every list (yg5E [00:09:00]). `FILTERS.md` uses **short
  float ≥ 15%** as squeeze fuel — that is our number, `APPROXIMATION`, not his.
- **Blue sky:** *"blue sky is all-time highs"* — and he explicitly separates it
  from the 52-week breakout: *"52-week highs can just be something that's at
  52-week highs but has been selling off for like 10 years, so it's not going
  to be a blue sky setup in that case"* (yg5E [00:20:22]). 254 corpus hits,
  **177 of them in live streams** — this is a concept he uses in real time far
  more than he teaches it.

---

## Layer C · Toplist scanners — the ranked lists

A list is sorted, capped and continuously refreshed. *"At least 50"* rows,
sometimes 100 (yg5E [00:12:48]).

| list | filter / sort | status | source |
|---|---|---|---|
| **Top Gappers** | **gap up > 7% or gap down > 7%**, sorted by gap % | **CONFIRMED** | yg5E [00:06:36] |
| **Top Gainers** | sorted by **% change from the previous close** | CONFIRMED | w97 [00:49:28] |
| Ross's Top Gappers | a curated variant — contents UNKNOWN | UNKNOWN | — |
| Low Float Top Gainers | Top Gainers ∩ low float | QUALITATIVE | Layer A tiers |
| **Top Relative Volume** | RVOL leaders — *"these are the stocks generally that we're going to be focusing on"* | CONFIRMED | yg5E [00:09:50] |
| **Top Volume 5 Minutes** | highest volume in the last 5 min — *"although I typically would use my high of day momentum scanner for that"* | CONFIRMED | yg5E [00:10:33] |
| **Continuation** | *"stocks that have made big moves in the **last two weeks**… some could be setting up for a daily breakout, a bull flag, a flat top breakout"* | CONFIRMED (see conflict C1) | yg5E [00:11:39] |
| **Top of Trend** | *"stocks positioned in the **top 80% of their range** and meeting the volatility criteria"* | CONFIRMED | blog `the-premarket-break-of-vwap-strategy.md` |
| Top of Trend (Large Cap) | same on large caps | UNKNOWN | — |
| **Top RSI / Top RSI Trend** | highest and lowest RSI **over the last 5 minutes** — *"a bit more of a reversal list"* | CONFIRMED | yg5E [00:10:09] |
| **Penny Top Gainers / Gappers** | the penny price tier, ~$0.10–$5 | CONFIRMED | yg5E [00:13:24] |
| Penny Top Losers / Top Losers | mirror of the gainers lists | QUALITATIVE | yg5E [00:10:48] |
| Large Cap Top Gappers | large-cap tier — boundary UNKNOWN | QUALITATIVE | yg5E [00:13:48] |
| **Large Cap Earnings With Gap** | gapping large caps with earnings **within ~48 hours** (before or after) | CONFIRMED | yg5E [00:14:03] |
| Large Cap Highest Volume | — | UNKNOWN | — |
| **Recent IPO Top Moving** | recent-IPO momentum names — he describes it as a beta he was building | CONFIRMED (as concept) | yg5E [00:12:12] |
| **Recent Reverse Splits** | exists and he reads it aloud on a live session (ILLR) | CONFIRMED (exists) | S6AyP-2ziFc [00:16:58] |
| **After Hours Top Gainers** | *"this starts working at 4pm… it doesn't work during regular trading hours, it is just an after hours scanner"* | CONFIRMED | yg5E [00:11:16] |
| Top Change Since Open | change measured from 09:30, not from the previous close | QUALITATIVE | — |
| **Pullback** *(in the layout, not in the dumped list)* | *"recently made a big move up, now consolidating **in the top 25% of the range**… at least **20 cents off the high** or at least **2% off the high** depending on the price range"* | CONFIRMED | eCSzHYl8apo [00:12:56] |

> **`Recent Reverse Splits` is the list `FILTERS.md` gate 5 exists to survive.**
> A reverse split shrinks the float into exactly the band this method hunts.
> The list is a candidate source; the split test (`prev_close ÷ ratio ≈
> adjusted`) decides whether the gap is arithmetic. MSGY 2026-08-11 is the
> logged failure of running that gate without its precondition.

---

## Conflicts — stated more than once, differently

| # | thing | values in the corpus | how to read it |
|---|---|---|---|
| C1 | Continuation lookback | **2 weeks** (yg5E [00:11:41]) vs **1 week** (stream tZH65KeM01o [00:10:44]) | teaching vs stream. Per corpus rule 4 the stream wins for *what he uses*; the 2-week value is what the shipped list does. Build 2 weeks, read the last week first. |
| C2 | the gap number | **7%** (Top Gappers list) · **5%** (*"all the stocks gapping up more than 5%"*, FILTERS Layer 0) · **4%** (*"a stock in play if it is surging more than 4% with a strong catalyst"*, blog) · **10%** (pillar 2, but that is **change on the day**, not the gap) | four different jobs. 7% is the platform list. 5% is his personal dial. 4% is the definition of "in play". 10% is a **trade gate on a different quantity**. Do not collapse them. |
| C3 | float ceiling | pillar 5 says **< 10M**; the scanner dial in FILTERS is **< 20M**; the colour goes bright at **< 5M** | the pillar is the gate, the dial is the net, the colour is the eye. Three layers, all correct. |
| C4 | RSI extreme | *"above 90 or below 10"* interests him; the shipped hybrid filters **80 / 20** | the scanner is looser than the preference — same relationship as C3. Scan 80/20, act on 90/10. |
| C5 | range position | Pullback list = **top 25% of range**; Top of Trend = **top 80% of range** | different scans with different jobs, not a contradiction. Top of Trend is a wide net; Pullback is the setup. |

---

## Register warnings — say these out loud

| finding | counts |
|---|---|
| **Reversal is taught, not traded.** The platform ships **10** reversal strategies — more than any other cluster. In the corpus: 5 teaching files, **0 video recaps**, 2 streams. `bollinger` is 23 teaching / 97 blog / **0 streams / 0 recaps**. | `corpus.py "reversal scanner"`, `"bollinger"` |
| **HOD momentum is traded, and the video recaps hide it.** 18 hits in teaching, **0 in the 69 video recaps** — but **29 blog files**, and the blog's 419 written recaps carry it as a labelled trade source (MYND, HEBT, XSPL, ELTK). The lopsided count is a register artefact, not a signal. | `corpus.py "high of day momentum" --files` |
| **`5 pillars` barely exists as a phrase** (2 blog hits) while `pillar` has 130 teaching hits. The branding is new; the criteria are old. | `corpus.py "pillar"` |
| **Blue sky lives in the streams** (177 of 254 hits) — a real-time concept, and the platform's Blue Sky strategy is *disabled*. | `corpus.py "blue sky"` |

---

## What is NOT a filter on this platform

| looks like a filter | actually |
|---|---|
| every displayed column | a **data field**. Short interest, ATR, short ratio and 5-min RVOL are shown on lists he does not filter on. Displayed ≠ required. |
| the V5 / V8 split | an **alert-rate dial**, switched intraday to keep the alert count followable |
| a single alert firing | *"kspn hit the low float former momo stock but only triggered it once… probably not going to trade it"* (yg5E [00:16:47]). **The count is the signal.** |
| the 52-week breakout | *"it can sometimes indicate a blue sky setup… but it's not a guarantee of that"* |
| Top Gainers membership | he only works the **top 10** — *"they should be in the top 10 of this list"* (w97 [00:53:37]) |
| the whole layout | *"you could fill your whole screen with scanners… keep it simple, focus on the gap scanner out of the gates"* (eCSzHYl8apo [00:14:19]) — he names **three** he uses daily: top gainers, HOD momentum, running up (w97 [01:01:11]) |

---

## Corrections this research makes to our own spec

`ross-tradingview-mastery/references/source-analysis.md` carried four numbers
that the corpus now overrides. Recorded in place rather than deleted.

| rule | was | now | why |
|---|---|---|---|
| Former momentum proxy | *"highest one-day gain in preceding 120 sessions ≥ **50%**, transparent starting threshold"* | **≥ 100% in one day, in the recent past** | he states it: w97 [00:58:29]. `APPROXIMATION` → `CONFIRMED`. 50% roughly doubles the candidate pool. |
| Five Pillars list, float | `verified float <= 20 million` | **< 10 million** | pillar 5 verbatim, oKlhUSSHe2Q [00:30:38]. 20M is the *scanner dial*, not the pillar. |
| Running Up | `move ≥ X% over N min AND 5-min RVOL ≥ threshold` | **+ `price < high of day`** | the exclusion is stated as definitional, w97 [01:00:56]. Without it, Running Up duplicates HOD momentum. |
| Low Float Volatility Hunter | *"low float + high ATR percentage"* | **float sub-1M** is the stated component; ATR is our inference | w97 [00:58:35]. The ATR half stays `APPROXIMATION`. |
| Reversal branches | not specified | **V5 = 3 consecutive · V8 = 4+ · BB 20/2 · RSI 80/20 scan, 90/10 preference** | eCSzHYl8apo, jfe1Zl-5EQI |

Unchanged and still ours: the 5-min RVOL threshold (2×), the Running Up move
size and window, all large-cap boundaries, the short-squeeze definition.

---

## Translating this to a screen you can actually run

Neither finviz nor TradingView has his event engine. What each can do:

**finviz — Layer 0 net, the pre-market pass (`premarket_stars.py` runs this):**
```
finviz.com/screener.ashx?v=111&o=-change&f=sh_price_2to20,sh_float_u20,sh_relvol_o5,ta_change_u10
```
Reproduces pillars 1, 2, 4, 5 as a list. Cannot do: the HOD event, the squeeze
windows, former-runner status, 5-min RVOL. Serves **last session's** price and
volume before the bell — float and short float only.

**TradingView — the closest to the alert engine.** The Pine implementation and
its per-strategy formulas live in
`.claude/skills/ross-tradingview-mastery/` (`assets/ross_style_momentum_scanner.pine`,
`references/source-analysis.md`). Apply the five corrections above before
using it.

**Not reproducible anywhere in this repo:** true float feed, news/catalyst
classification, the former-runner database, and the loosened Former-Momo
threshold set — which is precisely the strategy he says fires earliest.

---

## What this document did not check

- **No threshold here was validated against a live alert.** Every number is
  quoted from a video, not measured from the scanner's behaviour. The
  calibration procedure (20 days of Scanner History, recall before precision)
  is unrun — see `source-analysis.md` §Calibration.
- **The observed float/price ranges in `source-analysis.md` came from a
  40-alert snapshot.** That is one session. It bounds nothing.
- **Six strategies have no corpus coverage** and are marked UNKNOWN, not
  approximated: Ross's Top Gappers, Large Cap Highest Volume, Top Change Since
  Open, Top of Trend (Large Cap), Short Squeeze, plain Squeeze Alert.
- **None of this is evidence of profitability.** Replication over 894 sessions
  produced negative expectancy (`reports/2026-08-regime-filter.md`), and the
  documented edge in this population is on the short side and largely
  unharvestable (`reports/2026-08-known-edges.md`). This is a **selection**
  document. Paper only.

---

## Verdict

**The right screen is three scanners, not twenty-eight.** He says so directly:
top gainers, high-of-day momentum, running up (w97 [01:01:11]), plus the gap
list out of the gates (eCSzHYl8apo [00:14:37]). Everything else in the config
is either a price-tier or float-tier restatement of those, a reversal cluster
the corpus shows him teaching far more than trading, or a list he reads for
context rather than entries.

The two settings worth copying exactly, because they are stated as settings
and are usually implemented wrong:

1. **Running Up must exclude the high of day.** It is the complement of HOD
   momentum, not a weaker version of it.
2. **Former Momo runs on loosened thresholds** so it fires before the others,
   and it means *over 100% in one day in the recent past* — not 50%.

And the one that governs how you read the whole board: **the alert count is
the signal, not the alert.** A name lighting three strategies at once is the
event; a single trigger is noise he passes on by his own account.
