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

**Sort by gap % descending and work top-down.** *"This is the way I have it every
morning... if I don't see something right away that I like, I move on."*

---

## Layer 1 · The reject cascade — before the chart is opened

Float and price kill a name **before** you look at a chart. That is the whole
trick, and it is why this runs on published metrics.

| # | gate | kill if | |
|---|---|---|---|
| 1 | **price** | outside **$2.00 – 20.00** | preferred **$2.50 – 9** |
| 2 | **float** | over **20M** | sweet spot **< 10M**; **< 5M in a cold market** |
| 3 | **catalyst** | none dated **today** | non-negotiable |
| 4 | **still rising** | more than **25 %** off the pre-market high | *"stair stepping down… I'm not a buyer"* |
| 5 | **reverse split** | the gap is *arithmetic* | see below — the split alone is not the veto |
| 6 | **instrument** | fund / ETF | ADRs are fine — he trades them |
| 7 | **tick size** | quotes in 5¢ increments | *"TA, five cent tick"* |

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
| **relative volume** | **≥ 1.5×** to make money, **≥ 3×** best | *"150% and higher is where I make money"* |
| session | **09:35 – 11:00 ET** | *"the 90 minute mark"*; 11:30 is the outer edge |
| midday | **no trades 11:30 – 15:00** | |

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
