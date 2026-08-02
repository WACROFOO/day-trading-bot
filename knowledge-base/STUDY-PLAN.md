# Study plan — everything Ross Cameron teaches, in learning order

A curriculum covering the full corpus (2,691 videos, 2,040 extracted rules),
ordered by **dependency** rather than by his publishing order. His videos are
sequenced for YouTube — strategy first, because that is the hook. Learned in
that order you get the exciting part before the arithmetic that decides whether
it works, which is the documented way people lose money at this.

Coverage is checked against `data/rules_digest.md` concept frequency, so
nothing he emphasises is missing and nothing here is invented. Numbers in
brackets are how many extracted rules invoke that concept — his emphasis,
measured.

**Pace:** ~8 weeks at 6–8 h/week to complete Phases 1–7. Phase 8 is permanent.
Nothing here is a recommendation to trade with real money.

---

## Phase 0 — Decide if this applies to you (1 evening)

Before any content: the structural facts that determine whether the strategy is
even available to you.

- **PDT rule** [24 rules] — under $25,000 in a US margin account you get 3 day
  trades per rolling 5 business days. This strategy assumes several trades a
  day. Check what your broker and country allow *first*.
- Costs that dominate small accounts: commissions, FX if you are not in USD,
  borrow fees.

| Watch | Why |
|---|---|
| [How to Start Day Trading (with ZERO experience)](https://youtu.be/QstdS67Iyv0) 53m | The honest overview |
| [How to BLOW UP Your Trading Account (Don't Do This)](https://youtu.be/hLtPtEVBBBQ) 30m | Watch the failure modes *before* the method |

**Gate:** you can state your own PDT status and per-trade cost in numbers.

---

## Phase 1 — The arithmetic (week 1)

The part that decides everything, taught last by nearly everyone. Do not skip.

Concepts: position sizing by risk [125], daily loss limit [68], accuracy /
win rate [48], max loss per trade [41], profit-loss ratio 2:1 [37].

- `shares = risk_budget ÷ (entry − stop)` — size is an *output*, never a guess
- Expectancy: `(win% × avg win) − (loss% × avg loss)`; breakeven win rate is
  `1 ÷ (1 + reward:risk)`
- The daily rules: max loss 6%, 3 consecutive losses, giveback, green-to-red

| Watch | Why |
|---|---|
| [Year in Review: 2023 +$306,548](https://youtu.be/4t3GDiAXW18) 54m | Where the 2:1 and 65% accuracy claims come from |
| [I Day Traded This ONE Strategy For 21 Days](https://youtu.be/RLGDwe2m70E) 59m | The same maths against a real sample |

**Gate:** given entry, stop and a $500 account, compute share size in your head.
Then compute what win rate you need at 1.5:1 to break even.

---

## Phase 2 — Market structure and the clock (week 2)

Concepts: first hour / market open [44], halts [46], pre-market activity [38],
midday avoidance [16].

- The session: pre-market 7:00, open 9:30, skip the first 5 min, prime window
  9:30–10:30, hard stop ~11:30
- **Halts** — LULD circuit breakers, the 5-minute minimum, resumption prices,
  why you can be locked into a falling position. On these stocks this is not an
  edge case, it is the terrain.

| Watch | Why |
|---|---|
| [Trading Halts Explained](https://youtu.be/FN-uqfbEVKw) 30m | The one dedicated halt video |
| [The REAL Reason Pre-Market Trading Is Better](https://youtu.be/BZwJFPk3cBM) | Pre-market's role |

**Gate:** explain what happens to your order during a halt, and why size is the
only defence.

---

## Phase 3 — Stock selection: the five pillars (week 3)

Concepts: news catalyst [83], float size [72], relative volume [61], small cap
focus [29], scanner alert [30].

In his own words: *"price, float, news, relative volume, and rate of change"*.
All five = A-quality [22]; four = B; he says he does not trade Bs.

| # | Pillar | Passing |
|---|---|---|
| 1 | Price | $2–$20 (sweet spot $5–10) |
| 2 | Float | < 20M shares (10M preferred) |
| 3 | News | a real catalyst, or no trade |
| 4 | Relative volume | ≥ 5× normal |
| 5 | Rate of change | up ≥10% and rising *now* |

| Watch | Why |
|---|---|
| [How to Grow a Small Account with ZERO Experience](https://youtu.be/w97KlUrVDk0) 108m | Selection end to end |
| [Day 11: Scanner Alert Sends My Account +220%](https://youtu.be/0Zh105lq9Rk) 15m | Where he names the five pillars |

**Gate:** score 10 real pre-market gappers 0–5 without looking at what they did.

---

## Phase 4 — Reading the chart (weeks 4–5, the longest phase)

Concepts: volume confirmation [168], support and resistance [157], MACD [66],
VWAP [45], 9 EMA [30], 20 EMA [21], 200 MA [20], daily chart context [29].

**4a — Candlesticks.** Doji, hammer, shooting star, topping/bottoming tail,
gravestone and dragonfly, spinning top, candle-over-candle.

**4b — Levels.** Support is *confluence*, never one line — two independent
reasons at the same price (moving average + whole dollar, former resistance +
trend line). Broken resistance flips to support.

**4c — Indicators.** VWAP, 9/20/200 EMA, MACD (12/26/9, no custom settings),
volume bars.

| Watch | Why |
|---|---|
| [How to Read Candlestick Shapes & Charts (ZERO experience)](https://youtu.be/myUKta-wicQ) 71m | Start here |
| [7 Candlestick Patterns I'M ACTUALLY USING Every Day](https://youtu.be/aqTXoV923OE) 85m | Narrows to what he uses |
| [The ONLY Technical Analysis Guide You'll Ever Need](https://youtu.be/BUCPPCXOHbs) 101m | Levels and structure — the densest single source |
| [How to Read Technical Indicators on Candlestick Charts](https://youtu.be/LNDd7rf-9FU) 74m | VWAP / EMAs / MACD |
| [The Simple MACD Strategy to Spot Big Winners Early](https://youtu.be/vvXX2ycveuw) 31m | MACD specifically |

**Gate:** on a blank chart, mark every level you would trade against, and say
why each one qualifies — two reasons or it does not count.

---

## Phase 5 — The patterns (week 6)

Concepts: reversal [102], micro pullback [39], bull flag [32], abcd [16],
gap and go, dip and rip, flat top breakout.

Learn in this order — each is a variation of the one before:

1. **Micro pullback** [27 videos] — the core. Strong up-move, small dip, buy
   the first candle making a new high
2. **Bull flag** [42 videos] — the same shape, larger scale
3. **Dip and rip**, **gap and go**, **flat top breakout**, **ABCD**
4. **Reversal** setups — a different trade; learn last

| Watch | Why |
|---|---|
| [Master the Bull Flag Trading Pattern TODAY](https://youtu.be/DP4ayEWhmvM) 58m | The canonical pattern lesson |
| [The ONLY Pattern I'm Trading for BIG Winners](https://youtu.be/iIC62xnblLc) 59m | Micro pullback, in isolation |
| [Master the Dip Trading Strategy](https://youtu.be/ORWJzImSTdE) 65m | Buying dips properly |
| [How to Buy the Dip (with ZERO experience)](https://youtu.be/ywim_dUSXe4) 95m | Longer, live |

**Gate:** find 20 historical examples yourself, marking entry, stop and target
on each *before* revealing what happened.

---

## Phase 6 — Execution (week 7)

Concepts: first candle to make a new high [80], level 2 / time and sales [47],
hotkeys [35], stop at pullback low [50], scaling out [36], break-even stop [30],
adding to a winner [19], trailing stop [10].

**Entry:** the trigger is the first candle to exceed the previous candle's
high, after a 2–3 candle dip. Stop goes under the pullback low (~$0.08–0.10).

**Exit — the planned ladder:** sell half at target 1 (retest of high of day,
typically $0.15–0.20 away) → stop to breakeven → sell 25% at the next level →
trail the last 25%.

**Exit — the six warning signs (any one, sell now):** big red candle on heavy
volume, green candles shrinking, MACD turns negative, a large seller on Level 2,
first candle to make a new low below the flag, big topping tail.

**Position building:** starter → half → full, adding *after* banking profit,
never into a loser.

| Watch | Why |
|---|---|
| [Ultimate Beginners Guide to Timing Entries & Exits](https://youtu.be/ZS8x6xK8-Vk) 83m | The single best entry/exit lesson (1.6M views) |
| [How to use Level 2 (with ZERO experience)](https://youtu.be/q5DRctM5C-Q) 44m | The order book |
| [How to use Level 2 and Time & Sales as a Momentum Day Trader](https://youtu.be/pJuG5YtVF84) 28m | Reading the tape |
| [Ultimate Guide on ADDING to Winners with Scaling](https://youtu.be/KzVbXzkoZkA) 97m | Building a position |
| [How to Scalp Trade (with ZERO experience)](https://youtu.be/-0slMH7N6eI) 106m | Fast execution |

**Gate:** hotkeys configured, and 50 simulator round-trips executed without
looking at the keyboard.

---

## Phase 7 — Platform and tooling (week 8, ~1 day)

Concepts: hotkeys [35], scanners [30].

Three separate jobs, three separate tools — he has never used one for all
three: **scanning** (his own momentum scanners), **charting** (ThinkorSwim),
**execution** (Lightspeed → Sterling → DAS Trader).

| Watch | Why |
|---|---|
| [DAS Trader Review — connecting to Schwab and IBKR](https://youtu.be/nOJu4dKNmu0) 59m | His current stack (2025) |
| [How I use Thinkorswim for Day Trading](https://youtu.be/C4XZ_67c0Fo) 28m | Chart setup |
| [Is ThinkorSwim Worth it?](https://youtu.be/KwNq51h-yKk) / [Webull](https://youtu.be/WSfbGzYuCxE) / [IBKR](https://youtu.be/TNwPpPo4uYM) | Broker choice, 2025 |

Local practice tool: `streamlit run src/paper_trading/app.py`.

---

## Phase 8 — Psychology and the permanent loop (ongoing)

Concepts: emotional control [65], paper trading / simulator [37].

| Watch | Why |
|---|---|
| [How to Deal with FOMO](https://youtu.be/8eLtork_M50) 54m | The most common failure |
| [I made a mistake today…](https://youtu.be/3ovOiVIJ_aM) 24m | Him diagnosing his own error |
| [Live Day Trading a 500% Short Squeeze](https://youtu.be/YuNvqwJftVY) 272m | 4½ hours unedited — the reference for what the job actually looks like |

The loop: journal every trade → weekly review of win rate, avg win, avg loss,
profit-loss ratio → change **one** thing at a time.

---

## Two long-form options

If you prefer one continuous source over modules:

- [27 Years of Trading Knowledge in 3hrs 5mins](https://youtu.be/B81TMhUpz50) — 185m
- [The Ultimate Day Trading Guide (Chapters 1–10)](https://youtu.be/oxob0x0Xz7s) — 186m

Both cover Phases 1–6 in his own order. Use them as a first pass, then work the
modules for depth.

---

## What this plan deliberately flags

Findings from `../research/momentum-replication/reports/` that a learner should
carry from day one:

1. **His teaching order ≠ his trading order.** The videos front-load strategy.
   The live streams show risk control is what he never breaks and entry rules
   are what he bends constantly.
2. **The entry timing is on a 10-second chart.** He teaches on 1-minute charts,
   but 40% of his live streams reference a 10-second chart for the actual dip.
   A 1-minute chart cannot show you what he is seeing.
3. **Two of his exit signals need Level 2**, which most free platforms do not
   provide in usable form.
4. **None of this is verified.** Our own replication of the documented rules
   over 17 real sessions produced negative expectancy. That is a statement
   about the replication, not proof the strategy fails — but it means the
   correct posture through every phase above is *simulator, not real money*.
