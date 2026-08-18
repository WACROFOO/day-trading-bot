# The filter bible

Every filter, in the order it fires. Post-audit values — where this disagrees
with an older note, this wins (`reports/2026-08-parameter-audit.md`).

**The one idea that organises all of it:** a number he *types into a scanner* is
not a number he *requires of a trade*. Dials are set loose so nothing is missed;
the eye tightens afterwards. Implemented the wrong way round, a loose dial lets
junk through and a tight one silently deletes the population you wanted.

---

## Layer 0 · Scanner dials — set these once, leave them wide

| filter | value | note |
|---|---|---|
| gap | **≥ 5 %** | *"all the stocks gapping up more than 5% in the entire market"* |
| price | **$2 – 20** | |
| float | **< 20M** | |
| relative volume | **≥ 5×** | a dial, **not** a gate — see Layer 3 |
| volume | **≥ 250,000** | *"the volume threshold is um 250,000 shares minimum"* |

```
finviz.com/screener.ashx?v=111&o=-change&f=sh_price_2to20,sh_float_u20,sh_relvol_o5,ta_change_u10
```

Finviz free serves **last session's** price/change/volume before the bell. Use
it for float, short float and news — never to rank pre-market gappers. For live
`premarket_change`, use TradingView.

The dials above are ours, applied to a finviz/TradingView screen. **What his
own platform's named strategies filter for — Top Gappers at 7%, the squeeze
windows, Former Momo at "over 100% in one day", Running Up's below-high-of-day
exclusion, the V5/V8 reversal split — is `SCANNERS.md`.** That document is
discovery only; nothing in it overrides a gate here.

**Sort by gap % descending and work top-down.** *"This is the way I have it every
morning... if I don't see something right away that I like, I move on."*

---

## Layer 1 · The reject cascade — before the chart is opened

Float and price kill a name **before** you look at a chart. That is the whole
trick, and it is why this runs on published metrics.

| # | gate | kill if | |
|---|---|---|---|
| 1 | **price** | outside **$2.00 – 20.00** | preferred **$2.50 – 9** — but a **soft floor under a penny theme**, see below |
| 2 | **float** | over **20M** | sweet spot **< 10M**; **< 5M in a cold market** |
| 3 | **catalyst** | none dated **today** **AND no live theme** | a running theme substitutes — see below |
| 4 | **still rising** | more than **25 %** off the pre-market high | *"stair stepping down… I'm not a buyer"* |
| 5 | **reverse split** | the gap is *arithmetic* | see below — the split alone is not the veto |
| 6 | **instrument** | fund / ETF | ADRs are fine — he trades them |
| 7 | **tick size** | quotes in 5¢ increments | *"TA, five cent tick"* |
| 8 | **buyout** | acquisition announced | *"the value becomes fixed at the buyout price and volatility disappears"* (book, GR#13 discussion). HHS 2026-08-14: pinned under the $5.00 deal all day |

### Gates 1 and 3, softened by the theme — 2026-08-12

Two corrections from his own recap of a day our cascade rejected everything
and he booked +$17,617 (OFAL, RMCF, SPRC):

**The theme substitutes for the catalyst.** *"Chinese Hong Kong stock with no
news starts ripping"* — and he bought it, because SCKT ran Monday and PLAG ran
yesterday. Sympathy momentum IS the same-day reason. JWEL (2026-08-10) was
rejected here on "no catalyst" for the same wrong reading. Gate 3 fires only
when there is neither news **nor** a live theme the name belongs to. A theme
is live when the last 1–3 sessions produced a >100% runner of the same
class (country, sector, price band) — the scanner's job is to say *which*.

**The $2 floor bends under a penny theme.** He rejected JOB at $0.56 and CXDC
at $1.15 in normal tape — and bought RMCF at $1.66 today because *"the theme
today was definitely penny stocks."* When the theme lives below $2, the floor
moves to roughly $1.50; what actually kills a cheap name is the **halt band**,
not the price: prior close **< $0.75 → 15¢ bands** (near-untradeable in RTH),
$0.75–3 → 20%, > $3 → 10%. Check the *prior close*, not the current print —
bands don't update intraday (PLAG halted every 15¢ at $6/share).

**And the clock outranks both.** OFAL's tradeable move was 06:05–08:30
pre-market — *"I actually prefer trading in the pre-market session when
there's no halts."* His volume tell: PM volume highest, declining after the
open = the move is behind you. No scan before 09:30 = no trade, whatever the
gates say. (Error class count: 23 — a preference implemented as a veto.)

### Gate 5, stated precisely — the split is not the veto

The rule is *"the gap is the split, not a move"*. That is a claim about
**arithmetic**, and it has a precondition: the reported previous close must be
**unadjusted**. Test it before firing the gate.

| test | meaning | action |
|---|---|---|
| `prev_close ÷ split_ratio ≈ prev_close_adjusted` | the gap is the ratio | **kill** — there is no move |
| prev close already adjusted, price gapped *on top* | a real move on a newly shrunk float | **gate does not fire** |

A reverse split reduces the float. A tiny float is the thing this whole method
is hunting. Killing every post-split name deletes the population you wanted.

The split still matters — as **context**, not a veto: it means a compliance
problem, a shell balance sheet, and an offering that can land without warning.
Price that in the size, not in the reject.

> **MSGY, 2026-08-11.** Prev close 2.3144 was *already* 1-for-8 adjusted; the
> +114% was real. Every other gate passed — price, 0.56M float, VWAP, 9 EMA,
> MACD positive and above signal, 6.6M volume, 272× RVOL. Rejected on gate 5
> anyway. It ran 2.54 → 5.43. **The gate fired without its precondition.**

### The one that runs backwards

**Pre-market volume has a CEILING and no floor.**

| | |
|---|---|
| over **~1M** shares pre-market | **warning** — *"I'm not the first one to see it"* |
| under 250k | **fine** — he traded NCTY on **8,000** pre-market shares |

Every other volume rule has a floor. This one doesn't, because the gap-and-go
bets on an imbalance that hasn't resolved yet. If the pre-market already traded
millions of shares, it has.

### Capital structure — no screener sees these

- live **ATM** or **shelf** vs market cap (ASTC: $24.5M ATM + $200M shelf against a $21M cap)
- **reverse split** history — a sub-5M share count is the tell
- **short float** ≥ 15 % — squeeze fuel, and a borrow problem
- 52-week high **> 20×** the price — history has been split-adjusted

---

## Layer 2 · Chart gates — all true at entry

| condition | value |
|---|---|
| `price > vwap` | above VWAP |
| `price > ema9` | holding the 9 EMA — a dip that **recovers** is bullish; only sustained trading below is bearish |
| `macd_hist > 0` | MACD 12/26/9, positive **and** above the signal line |
| `pullback_volume < impulse_volume` | the dip comes on lighter volume |
| `pullback_index ≤ 2` | 1st or 2nd pullback; the **3rd is reduced size, not skipped** |
| `at_support` | **two independent reasons at one price** — MA, whole/half dollar, daily level, flipped resistance, VWAP |
| `tape_green` | buyers hitting the ask |
| `no_seller_wall` | Level 2 clear above |

**Trigger:** the first candle to exceed **the previous red candle's** high — not
the high of the move, not the high of day. **Intrabar**, at the break, not on the
close. One red candle is enough for the pullback.

**Confirm the candle. Anticipate the level.** Two different objects: you wait for
the candle, but you position 10–25¢ *below* a whole dollar or the pre-market
high and add through it.

---

## Layer 3 · Live filters — the ones measured against his own P&L

These come from a published split of his broker statements, which outranks
anything taught.

| filter | value | evidence |
|---|---|---|
| **session volume** | **≥ 1,000,000** | *"less than a million shares of volume I actually lost $8,000 on"* |
| best band | **1.0 – 2.5M+** | *"the ones I did the best on"* |
| **relative volume** | **≥ 1.5×** to make money, **≥ 3×** best | *"150% and higher is where I make money"*; the book's scanner floor is **2.0** (GR#1) — between the teaching dial (5×) and the broker-split floor (1.5×) |
| session | **07:00 – 11:00 ET** since 2020 | pre-2020 the money was 09:35–11:00; his post-March-2020 stats start the profit curve at 07:00. 11:30 stays the outer edge |
| midday | **no trades 11:30 – 15:00** | |
| after hours | **no trades 16:00 – 20:00** | *"doesn't look like I'm net profitable trading after hours"* — his own measured stats. Watch, note levels, trade the 07:00 wave instead |

---

## The book's six components of a strong stock (ch. 10, 2023)

The five pillars, restated by the primary source — plus one this repo was
missing:

1. volatile **right now** — already up 15–20%+, *"buy high and sell higher"*
2. fear (FOMO) in the market
3. greed — *"one-day-old FOMO"*, the spillover into tomorrow
4. supply/demand **imbalance** — rotation vs float (his example: OBLN, 321M
   traded on a 6M float). `./now` shows this as the `rot` column
5. high relative volume (`rvol` column; book floor 2.0)
6. **former runner status** — he runs a dedicated scanner with LOWER volume
   thresholds for names that ran before: *"when a former runner starts to
   move, I want to make sure I see it quickly."* This is the day-2 watch
   (FGI 08-14) — and his test for whether a runner is signal or distraction
   is relative volume: *"if it isn't high — former runner or not — that
   stock probably is not the right trade for today"*

Two selection guardrails sit on top: **#13** *"Is this the strongest stock
today?"* (`./now` crowns it by dollar volume) and **#15** *"Is this the
obvious one?"* — if you had to talk yourself into it, it isn't. And the
sizing corollary, **#10**: no single trade weighted to erase more than one
or two previous winners.

---

## Live rejections, in his own words

The fastest way to calibrate. Each is a real name turned down on the scanner:

| name | reason |
|---|---|
| JOB at $0.56 | *"too cheap for me"* |
| CXDC at $1.15 | *"a little too cheap"* |
| a $32 stock | *"at 32 dollars I won't trade it"* |
| a 50M float at $1 | *"a little on the higher side, especially for a stock priced at $1"* |
| TAOP, 23M float | *"maybe a little high on the float"* |
| REPH, 16M float | float fine — *"already selling off pre-market… the pre-market chart was bad"* |
| MNKD | *"the float's too high"* |
| TA | *"five cent tick"* |
| a non-biotech | *"it's not a biotech or pharmaceutical stock, so I'm skeptical"* |

---

## What is NOT a filter — the misreadings that cost the most

| looks like a filter | actually |
|---|---|
| `min_reward_risk ≥ 2.0` | a **realised** ratio from the exit plan, never a pre-entry veto. His best month posted **1.42** |
| `rvol ≥ 5×` | a scanner dial. The profitable floor is **1.5×** |
| `volume ≥ 250,000` | a scanner dial. The real floor is **1M session volume** |
| 3rd pullback | **reduce size**, don't skip |
| `stop_max_distance` 0.30 | **cut size**, don't skip |
| pre-market volume | a **ceiling**, not a floor |
| "5M float ideal" | a **cold-market setting**, not a preference |
| hammer / doji / engulfing | taught constantly, **never traded** — hammer: 208 mentions, 3 in live streams, 0 in recaps |

---

## The morning, in four commands

```bash
python3 scripts/premarket_stars.py --all --notify   # layers 0 and 1
python3 scripts/catalyst_score.py SYM SYM           # layer 1, catalyst, 3 channels
python3 scripts/premarket_dd.py SYM                 # pre-market shape: fade, descending peaks
python3 scripts/tape.py SYM                         # layer 2 live: VWAP, EMAs, MACD, halts, honest stop
python3 scripts/size.py --entry X --stop Y          # after the chart says yes
```

---

**Standing caveat.** All of the above is *selection*. None of it establishes
that the strategy is profitable — replication over 894 sessions produced
negative expectancy (`reports/2026-08-regime-filter.md`), and the documented
edge in this population is on the short side and largely unharvestable
(`reports/2026-08-known-edges.md`). Paper only.
