# Quantified strategy

Every rule in `STRATEGY.md` as a parameter. Values are what the corpus states,
not what has been tested.

**`n` = how many rule statements across 257 videos invoke that concept.** It
measures emphasis, not correctness. High `n` means he says it constantly. It
does not mean it works.

**Conflict** = the corpus states more than one value. Backtest the range.

> **Read §13 before implementing any of this.** A full implementation attempt produced ~18 defects and not one was a wrong number here — every one was a misreading of a rule that was already stated correctly. §13 lists each trap with the citation that settles it.

---

## 1. Universe filter

Applied before the chart is looked at. All must pass.

> **A scanner setting is not a trade gate.** See §15. Three of the rows below
> were implemented as gates and are dials: `gain_pct_min`, `rvol_scan`,
> `volume_min`. Getting this wrong is the largest single source of error found
> in the 2026-08 audit.

| Parameter | Op | Value | Unit | n | Conflict |
|---|---|---|---|---|---|
| `price_min` | >= | 2.00 | $ | 144 | 1.00 also stated |
| `price_max` | <= | 20.00 | $ | 144 | 10.00 also stated |
| `price_sweet_min` | >= | 5.00 | $ | — | 2.00 |
| `price_sweet_max` | <= | 10.00 | $ | — | — |
| `gain_pct_scan` | >= | 5 | % — the scanner dial | — | — |
| `gain_pct_min` | >= | 10 | % on day — the pillar | 666 | — |
| `rvol_scan` | >= | 5.0 | x — the scanner dial | 61 | — |
| `rvol_min_trade` | >= | 1.5 | x — where he makes money | — | measured, see below |
| `rvol_preferred` | >= | 3.0 | x — where he does best | — | measured |
| `float_max_hot` | <= | 20 | M shares | 72 | 10M preferred |
| `float_max_cold` | <= | 5 | M shares — cold market | — | regime-conditional |
| `has_catalyst` | == | true | bool | 83 | — |
| `volume_min` | >= | 1,000,000 | shares cum. | 102 | 500k was wrong |
| `premarket_volume_max` | <= | 1,000,000 | shares — **soft** | — | 1.5M accepted once |
| `premarket_volume_min` | — | none | — | — | traded on 8,000 |
| `rate_of_change_min` | > | 0 | % gain per minute, rising | — | not numerically stated |

Rejects: `price < 1`, `float > 100M`, no catalyst, faded from pre-market high,
wide tick (*"TA, five cent tick"*, `starting-off-september-grateful-334`).

### The volume rows, which are measured rather than taught

`volume_min` was 500,000 and is wrong. He has published a split of **his own
broker statements**:

> *"Stocks with a relative volume of **150% and higher** is where I make money.
> I did the best on stocks with relative volume of **300% and higher**...
> **the stocks that have less than a million shares of volume I actually lost
> $8,000 on. I did not make money on those stocks.** The stocks that closed the
> day with one to two and a half million or more in volume are the ones I did
> the best on."* — `blog/risk-psychology/rollercoaster-trader-behind-trades-ep-6`

500,000 sits inside the band he lost money in. And 150% is **1.5×**, not 5× —
the 5× is what he types into the scanner, not what a trade must clear.

### Pre-market volume runs the OTHER WAY

Every other volume rule here has a floor. This one has a ceiling and no floor,
because the gap-and-go is a bet on an imbalance that has not yet resolved:

> *"It already has **2 million shares of premarket volume**. So I already have a
> little bit of a negative bias on it **before I even pull up the chart**."*
> — `ZfwTJAMLroA` [13:21]

> *"stocks that have millions of shares of pre-market volume don't really work
> for the gap and go as much, because **I'm not the first one to see it**."*
> — `blog/recaps/day-2-of-our-nyc-seminar`

No floor: NCTY was traded on **8,000 shares** of pre-market volume, on the
strength of the catalyst alone (`blog/recaps/starting-off-september-grateful-334`).

### `float_max` changes with the tape

> *"I focus on stocks with a float under 20 million shares, and **when the
> market is colder, I tighten that down to under 5 million**."*
> — `blog/risk-psychology/can-you-trade-in-a-cash-account`

`reports/2026-08-regime-filter.md` tested regime as a filter on **entries** and
found nothing. It never tested regime as a modifier of the **universe**. Those
are different experiments and the second is untried.

Funnel: ~8,000 equities → ~50 scanner hits → 3–5 watchlist → 1–2 trades.

### `setup_grade` — the five pillars

"A-quality" was previously listed as unquantifiable. It is not. He states the
decomposition directly: *"trading the five pillars which would constitute an
A-quality setup"* (`3ovOiVIJ_aM` [00:16:07]), and names them as *"price, float,
news, relative volume, and rate of change"* (`0Zh105lq9Rk` [00:06:49]).

```
pillars_passed = price_ok + float_ok + catalyst_ok + rvol_ok + roc_ok
setup_grade    = 'A' if pillars_passed == 5 else 'B'
```

| Parameter | Value | n |
|---|---|---|
| `min_pillars_to_trade` | 5 | 384 mentions / 91 videos |
| `trade_b_quality` | false | — |

He self-reports 72% accuracy in a month where he *was* trading B-quality, and
frames that as the mistake — so the grade split is a testable hypothesis, not
just a slogan. Split backtest results by `pillars_passed` and the claim either
shows up as a monotonic edge gradient or it does not.

Caveat: 61% of actionable "quality setup" mentions name no pillar at all. The
five-pillar reading is what he says when he is explicit; most of the time he is
not. See §10.

---

## 2. Session window

| Parameter | Value | ET | n |
|---|---|---|---|
| `session_open` | 09:30 | — | 44 |
| `entry_blackout_end` | 09:35 | skip first 5 min | 44 |
| `prime_window` | 09:30–10:30 | most edge here | 44 |
| `session_typical_close` | 10:30–11:00 | **the 90-minute mark** | — |
| `session_close` | 11:30 | outer edge, not the centre | 16 |
| `premarket_start` | 07:00 | **era-dependent — see below** | 38 |
| `midday_avoid` | 11:30–15:00 | no trades | 16 |

He frames the session as a **duration**, not a clock time, and it ends earlier
than 11:30:

> *"For me, I'm in the zone... for most days, it's from **9:30 until 10:30 or
> 11:00**. So right around that **90 minute mark**."*
> — `blog/recaps/starting-off-september-grateful-334`

A backtest holding to 11:30 trades 30–60 minutes he is not in.

### `premarket_start` is the 2017 rule, and the practice reversed

> *"**I've traded pre-market maybe half a dozen times in the last year**, so
> probably won't trade pre-market. I'll just trade 9:30 to noontime."*
> — `blog/other/3-lessons-making-60k-1-month-behind-trades-ep-4`,
> lastmod **2017-03-04**

In the July 2026 challenge, `07:00` is named **78 times against 36 for
`09:30`**, and `pre-market` **161 times against 9 for "the close"**
(`reports/2026-07-challenge.md`). "Limit orders only" is a 2017 rule preserved
as present tense.

**Every blog file carries a `<!-- lastmod: -->` header and no pipeline has ever
read it.** Any parameter drawn from a 2017–2019 article needs that date
attached before it is treated as current.

Personal window incl. pre-market: 07:00–11:00, stated as derived from 24,446 of
his own trades. Unverified.

---

## 3. Entry gate

Boolean. All must be true at entry.

| Condition | Value | n |
|---|---|---|
| `macd_hist > 0` | MACD 12/26/9, no custom settings | 66 |
| `price > vwap` | above VWAP | 45 |
| `price > ema9` | holding the 9 EMA | 30 |
| `pullback_volume < impulse_volume` | dip on lighter volume | 168 |
| `pullback_index <= 2` | 1st or 2nd pullback only, never 3rd | 39 |
| `tape_green` | buyers hitting the ask | 47 |
| `no_seller_wall` | Level 2 clear above | 47 |

### `at_support(p)` — confluence, not a single level

"Buy at support" (n=157) was previously listed as unquantifiable. Scanning all
1,834 uses of `support` / `resistance` across 158 videos shows he almost never
means one line — he names two reasons for the same price. Pair co-occurrence is
the evidence: daily level + moving average 54, trend line + whole dollar 54,
former resistance + trend line 53, moving average + whole dollar 31.

```
at_support(p) = count([
    abs(p - round(p * 2) / 2) <= tol,     # whole or half dollar
    abs(p - ema9)             <= tol,
    abs(p - ema20)            <= tol,
    abs(p - ma200)            <= tol,
    abs(p - vwap)             <= tol,
    abs(p - flipped_level)    <= tol,     # broken earlier, retested from other side
]) >= 2
```

| Component | mentions | videos |
|---|---|---|
| moving average (9 / 20 / 200) | 295 | 64 |
| whole / half dollar | 299 | 57 |
| daily / weekly chart level | 157 | 42 |
| former resistance, flipped | 142 | 28 |
| VWAP | 77 | 25 |

Supporting mechanics, both computable from OHLCV alone:

| Parameter | Value | Support |
|---|---|---|
| `confluence_min` | 2 | pair counts above |
| `touch_count` | 3 | 23 of 41 explicit counts say "third"; 4 → 9, 2 → 8 |
| `flip_after_break` | true | 133 hits / 30 videos |
| `level_tolerance` (`tol`) | **unstated** | sweep 0.1–0.5% of price, floor at spread width |

Every term is arithmetic on bars. `tol` is the one genuinely free parameter and
is the place this definition can still go wrong — sweep it and report the spread
of results, do not tune it.

Citation: *"500 shares right off the 20 moving average this is psychological
support"* (`2kMgCjsmFzY` [00:41:52]) — one price, two independent reasons, which
is the whole rule in a sentence.

---

## 4. Entry trigger

| Parameter | Value | n |
|---|---|---|
| `trigger` | first candle to exceed prior candle high | 80 |
| `timeframe` | 1 | min |
| `order_type` | market / limit at ask + 0.15 | — |
| `max_slippage` | 0.15 | $ per share |
| `confirm_before_entry` | true — no anticipating | 47 |

Bull flag variant: flagpole → 2–3 candle consolidation → break of consolidation
high. Same trigger, larger scale.

---

## 5. Stop-loss

| Parameter | Op | Value | Unit | n |
|---|---|---|---|---|
| `stop_price` | = | low of pullback candle | $ | 50 |
| `stop_max_distance` | <= | 0.30 | $ per share | — |
| `stop_typical` | ~ | 0.08–0.10 | $ per share | — |
| `stop_min_distance` | >= | spread width | $ | — |
| `breakeven_trigger` | >= | +0.10 | $ or after 1st scale | 30 |
| `widen_stop_allowed` | == | false | bool | 50 |
| `add_to_loser_allowed` | == | false | bool | 50 |
| `vwap_break_exit` | == | true | hard invalidation | 45 |

If `stop_distance > stop_max_distance`: reduce size or skip. Never widen.

`stop_max_distance` was 0.20 with no citation and no `n`. His own numbered rule
list gives 0.30, and the justification is emotional rather than mechanical —
which is why it behaves like a §8 limit, not a chart-derived stop:

> *"Rule number four, tight stops, **30 cent max loss**. If I have a 50, 60, 70
> cent loss, that's going to start to trigger the emotions."*
> — `blog/recaps/starting-off-september-grateful-334`

---

## 6. Exit

| Parameter | Op | Value | Unit | n |
|---|---|---|---|---|
| `min_reward_risk` | >= | 2.0 | ratio | 37 |
| `target_1` | = | retest of high of day | $ | 21 |
| `target_typical` | ~ | 0.15–0.20 | $ per share | — |
| `scale_1_pct` | = | 50 | % of position at target_1 | 36 |
| `scale_2_pct` | = | 25 | % at next level | 36 |
| `runner_pct` | = | 25 | % trailed | 10 |

Hard exit signals (any one fires):

| Signal | n |
|---|---|
| first candle to make a new low | 13 |
| large topping tail | 8 |
| high-volume red candle | 168 |
| MACD crosses negative | 66 |
| large seller appears on Level 2 | 47 |
| green candles shrinking / momentum stalls | 168 |

---

## 7. Position sizing

```
risk_per_share  = entry_price - stop_price
shares          = risk_budget / risk_per_share
position_value  = shares * entry_price          # NOT the risk
```

| Parameter | Value | Unit | n | Conflict |
|---|---|---|---|---|
| `risk_pct_per_trade` | 2.0 | % of account | 125 | 3–5% also stated |
| `risk_flat_beginner` | 50 | $ | 125 | — |
| `size_ladder` | 100 → 200 → 400 → 800 | shares | 125 | 50 start also stated |
| `scale_priority` | size before frequency | — | 125 | — |
| `max_trades_per_day` | 1–2 | count | 22 | — |

Yield per share size, at the stated $0.20/share edge:

| Shares | Gross per trade |
|---|---|
| 100 | $20 |
| 1,000 | $200 |
| 10,000 | $2,000 |

Constraint: fill quality degrades with size on sub-20M float. The edge does not
scale linearly and the corpus admits percentage returns fall as the account grows.

---

## 8. Daily risk limits

| Parameter | Op | Value | n |
|---|---|---|---|
| `max_daily_loss` | = | daily profit goal (same magnitude) | 68 |
| `max_daily_loss_pct` | <= | 6 | % of account | 68 |
| `giveback_stop` | >= | 50 | % of day's peak gain → stop | 68 |
| `green_to_red_stop` | == | true — day turns negative, stop | 68 |
| `consecutive_loss_stop` | >= | 3 | losses in a row → stop | 68 |
| `drawdown_walkaway` | >= | 20 | % from equity high | 68 |

Claim: breaking `max_daily_loss` carries ~80% probability of doubling that loss.
Unverified, and the single highest-leverage rule in the set if true.

---

## 8b. Halts

46 claims across the corpus, with two dedicated videos: `FN-uqfbEVKw`
("Trading Halts Explained", 38 claims) and `StpXbe3Ga3Y` ("Circuit Breaker Halt
Explained", 12). Low-float momentum names halt constantly, so this is a
first-class part of the strategy rather than an edge case.

### Halt types

| Code | Meaning | Duration |
|---|---|---|
| LULD / volatility | price moved outside the band | **5 minutes minimum** |
| T1 | pending news, company-requested | until news is released |
| T12 | SEC / exchange suspension | weeks to months |

`T1` usually means the news is **bad** — the company asked for it — and the
stock commonly resumes near **50% of the pre-halt price**. `T12` is
untradeable.

### LULD bands, measured from a rolling reference price

| Tier | Previous close | Band |
|---|---|---|
| 1 (S&P 500 / Dow) | > $3 | 5% |
| 2 (most small caps) | > $3 | 10% |
| 2 | $0.75 – $3 | 20% |
| 3 | < $0.75 | 15¢ or 75%, whichever is **lesser** |

Bands are **doubled in the opening and closing auctions** (`StpXbe3Ga3Y`
[08:37]). The move must be outside the band **within 5 minutes**.

### Trigger and order mechanics

| Parameter | Value |
|---|---|
| `halt_trigger_dwell` | price must sit at the band **15 seconds** |
| `orders_beyond_band` | rejected — no order may be placed past the limit |
| `resumption_quote` | moves during the halt as orders accumulate |

### Direction

`halted_up → usually resumes higher`; `halted_down → usually resumes lower`.

### The tradeable setup — dip and rip on resumption

The named pattern (`2kMgCjsmFzY` [02:06], `ORWJzImSTdE`): on resumption,
beginners' stacked sell orders flush the price first; the dip is bought and the
stock squeezes to a new high. A second halt on the continuation is common.

```
halt (up) -> resumption -> brief flush -> buy the dip -> sell the rip
```

Rejects: `T12`, and halt-down scenarios. On a halt-down or a $2–3 whipsaw the
documented action is to **exit**, not to manage.

### Data requirement

Halt levels are not shown by every platform — Thinkorswim does not display
them, Webull does on funded accounts, and a third-party addon costs
$150–175/month. Programmatically, a halt appears in a minute series as a **gap
in the bars**, which is the only signal available from OHLCV alone.

---

## 9. Expectancy model

This is the arithmetic that decides whether any of the above matters.

```
expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
breakeven_win_rate = 1 / (1 + reward_risk)
```

| Reward:Risk | Breakeven win rate | At 60% win rate, E per $1 risked |
|---|---|---|
| 1:1 | 50.0% | +$0.20 |
| 1.5:1 | 40.0% | +$0.50 |
| **2:1** | **33.3%** | **+$0.80** |
| 3:1 | 25.0% | +$1.40 |

Stated accuracy targets: 50% floor, 65–75% claimed. `win_rate` n=48.

At 2:1 and 60%, expectancy is +0.8R per trade. Two trades a day at 2% risk is
+3.2% daily — which is implausibly high and is exactly why this needs testing
rather than believing. The likely failure points: real win rate below 50%,
slippage eating the 0.10 stop, and no fills at scale.

---

## 10. What does not quantify

An earlier version of this section listed support/resistance and "A-quality" as
unquantifiable. Both were wrong, and the way they were wrong is worth keeping:
the definition was in the transcripts the whole time, and the instinct to invent
a proxy instead of going to look was the actual error. Both now live in §1 and
§3 respectively. The method is `scripts/pipeline/08_define_support.py` and
`10_define_discretionary.py` — tag every mention with the concrete things named
alongside it, then count.

What survives that treatment:

| Concept | Unresolved | Why it resists encoding |
|---|---|---|
| trend lines | — | he says so himself: *"more abstract because different traders will draw them differently"* (`BUCPPCXOHbs` [01:12:11]) |
| support, residual | 424 / 963 (44%) | mentions carrying an instruction that name no level at all |
| "quality setup", residual | 72 / 118 (61%) | mentions asserting quality that name no pillar |
| Level 2 / tape reading | 339 / 542 (63%) | see below |
| emotional control | 462 / 602 (77%) | not observable in price data |
| reversal timing | — | "10–15 candles one direction" is loose |
| halt behaviour | — | halt-resume fills are unmodellable from OHLCV |
| news quality | — | requires NLP on the catalyst itself |

**Tape reading is two separate problems, not one.** Roughly half its resolved
uses restate rules already encoded elsewhere: `confirmation to act` (43) is the
§4 entry trigger, `whole-dollar orders` (29) is a §3 confluence component,
`spread width` (66) is a liquidity gate that quote data gives you. What actually
requires depth-of-book is `large seller / buyer` (104 mentions, 31 videos) and
`refresh / reload` (29). So the data question is narrower than "needs Level 2" —
tick and quote data cover most of it, and only seller-wall detection needs the
book.

**Emotional control is the control case.** It was run through the same procedure
expecting it to resist, and it did: 77% unresolved, the highest in the set, and
the resolvers that do fire are not states but rules — `rules as the fix` (214),
`walk away` (107). That is the useful result. He does not treat discipline as a
feeling to manage; he treats it as §8 being enforced by something other than
the trader. §8 is already coded. A bot has no emotions to control, which means
this row costs nothing in a backtest and everything in live discretionary
trading — the one asymmetry that favours automation.

Anything still on this list needs a proxy before it can be tested, and the proxy
is the biggest source of backtest error. Freeze it before running, test three to
five reasonable versions, and if the sign of the result flips between them,
discard the finding rather than picking the one that worked.

Full workings: `../data/support_definition.md`,
`../data/discretionary_definitions.md`.

---

## 11. Config

```yaml
universe:
  price_min: 2.00
  price_max: 20.00
  gain_pct_scan: 5            # scanner dial
  gain_pct_min: 10            # the pillar
  rvol_scan: 5.0              # scanner dial
  rvol_min_trade: 1.5         # measured floor
  rvol_preferred: 3.0
  float_max_shares_hot: 20_000_000
  float_max_shares_cold: 5_000_000
  volume_min_shares: 1_000_000        # was 500_000 - he LOST money there
  premarket_volume_max: 1_000_000     # soft: a ceiling, not a floor
  require_catalyst: true
  min_pillars: 5            # price, float, news, rvol, rate_of_change

support:
  confluence_min: 2
  tolerance_pct: 0.25       # UNSTATED in corpus - sweep 0.10-0.50
  tolerance_floor: spread
  components: [whole_half_dollar, ema9, ema20, ma200, vwap, flipped_level]
  touch_count: 3
  flip_after_break: true

session:
  timezone: America/New_York
  start: "09:35"
  end: "11:00"          # the 90-minute mark; 11:30 is the outer edge
  prime_end: "10:30"

entry:
  timeframe_min: 1
  trigger: first_candle_new_high
  max_pullback_index: 2
  require_macd_positive: true
  require_above_vwap: true
  require_above_ema9: true
  require_declining_pullback_volume: true
  max_slippage: 0.15

stop:
  rule: pullback_low
  max_distance: 0.30
  breakeven_at: 0.10
  allow_widen: false
  allow_average_down: false

exit:
  min_reward_risk: 2.0
  target_1: high_of_day_retest
  scale_pct: [50, 25, 25]
  hard_exits: [first_candle_new_low, macd_negative, vwap_break, high_volume_red]

sizing:
  risk_pct_per_trade: 2.0
  max_trades_per_day: 2
  size_ladder: [100, 200, 400, 800]

daily_limits:
  max_loss_pct: 6.0
  giveback_pct: 50
  green_to_red_stop: true
  consecutive_loss_stop: 3
```

---

## 12. Test order

Cheapest falsification first. Stop when one fails.

1. **Universe** — how many US equities per day pass §1? If <1/day the strategy is untradeable regardless of edge.
2. **Trigger** — on those names, does `first_candle_new_high` reach 2R before the pullback low, more than 33.3% of the time?
3. **Sensitivity** — sweep `rvol_min`, `float_max`, `price_max`, and `support.tolerance_pct`. Does the edge survive, or does it sit on one lucky cell? Tolerance is the one number nowhere in the corpus, so it is the most likely place to fool yourself.
   Also split by `pillars_passed` (3, 4, 5). If A-quality is real, the gradient is monotonic. If it is flat, §1's five-pillar gate is costing trades for nothing.
4. **Costs** — re-run with realistic spread and slippage on sub-20M float. This is where most momentum edges die.
5. **Regime** — split by year. 2017 / 2021 / now. An edge in one regime only is not an edge.

Baseline to beat: buy-and-hold the same universe, same holding period. If the
strategy does not clear that, the rules are noise.

---

*Derived from `../data/rules_digest.md` — 2,040 rules, 2,903 numeric figures,
257 videos, **plus a 2026-08 audit against the 2,063-article blog corpus**
(`reports/2026-08-parameter-audit.md`). Values are stated, not validated.
See `STRATEGY.md` §12.*

---

## 13. Clarifications — where this spec has been misread

Every parameter in this document was already correct. A full implementation
attempt (`research/momentum-replication/`) nevertheless produced ~18 defects,
and **not one was a wrong number** — all were wrong readings. They are recorded
here with the citation that settles each, because the same traps will catch the
next implementation.

### The entry gate is §3, and only §3

Six evaluable conditions plus two that need Level 2. Rules that describe the
*pattern* (`PLAYBOOK.md:99`'s "2–3 candles") or appear elsewhere in the corpus
are **not** gate conditions. Adding three such extras cut the pass rate from
6.7% to 3.5% — nearly half of all legitimate setups rejected by rules the gate
never had.

### "Front side of the move" is the MACD condition

Not a separate test. *"Only trade when MACD is positive and above the signal
line (front side of move)"* — `iIC62xnblLc` [26:20]. Implementing it separately
duplicates a gate condition with an invented threshold.

### `target_1` is the NEAREST objective, not the furthest

`target_1` = retest of high of day, **or** a measured move equal to the pole
(`small-cap-momentum-bull-flag.md`), and `target_typical` is 15–20 cents — i.e.
*near*. Taking the furthest of the two makes the high of day the target even
after price has collapsed away from it, and `min_reward_risk` is then satisfied
by a target the stock cannot reach. **The 2:1 is a filter applied to the
target, never the target itself.**

### `min_reward_risk` is a realised ratio, not a pre-entry veto

Fixing the entry above exposed the reading underneath it. `min_reward_risk >=
2.0` (§8, n=37) was implemented as a veto: skip any setup whose nearest
objective sits closer than twice the stop distance. Every citation behind the
number is retrospective and aggregate —

- *"~2:1 profit-to-loss ratio **achieved**"* — `Wsq8zdtCcis` [02:58]
- *"Profit-loss ratio **this week**: 46:1"* — `8eLtork_M50` [04:26]
- *"Profit/loss ratio **for month**"* — `hLtPtEVBBBQ` [14:34]
- *"$500 **average** winners, 61% accuracy"* — `bvy1pyzTrG4` [00:56]
- *"Trade 2:1 minimum. **If accuracy around 65%**, this ratio ensures
  profitability"* — `4t3GDiAXW18` [40:07]

— and §9 above uses it the same way, as `avg_win`/`avg_loss` inside an
expectancy formula. A ratio of averages is produced by the **exit** plan, not
by refusing entries.

It also contradicts the setup it filters. A micro-pullback enters just under
the high of day, so the nearest objective is cents away while the stop is the
depth of the dip; requiring 2× of that rejects the entry this document is
built around. Measured, it is the largest single rejection reason in the
replication — 66 of them, more than any gate condition.

**The consequence is a target question, not an entry question.** Removing the
veto raises trade frequency 5× and turns expectancy negative (+0.89R → −0.27R),
because target 1 then sits under 2R and half the position books a sub-1R gain
before the stop moves to breakeven. What target 1 should be when the high of
day is only cents above entry is open:
`research/momentum-replication/NEXT-STEPS.md` §4.

### The micro-pullback is often a **10-second** pattern

`MIN_DIP_BARS = 2` on 1-minute bars makes the shortest acceptable pullback two
minutes long. The live streams show that is far slower than what he trades:

> *"this is a 10 second micro pullback so let it pull back and then we'll get
> that curl up through 20"* — `6xIr761eZj8` [41:38]

> *"This is a 10-second micro pullback. Looking for the break of 14 and 15."*
> — `XIQUoLyUWuw` [33:32]

Across 289 transcribed streams "10 second" appears 250 times in 117 of them,
and of the "micro pullback" mentions carrying an explicit timeframe, 19 are
10-second against 59 one-minute. The streams are 2021–2023, so it was checked
forward: the June–July 2026 daily recaps use the phrase in 15 of 68 files and
the teaching corpus in 80 of 257. Current practice, not a habit he dropped. On a 1-minute chart a 10-second pullback is
not a candle — it is the wick of one.

**This is not a parameter error, it is a resolution error.** No setting of
`MIN_DIP_BARS` on 1-minute data can represent it, and it is the mechanical
explanation for why replicated entries sit in front of a median −1.56R
excursion (`research/momentum-replication/reports/2026-08-streams-roundup.md`).

### The third pullback is traded at reduced size, not skipped

`BUCPPCXOHbs` [52:17] gives "third means stop", and it was implemented as a
boolean that discards the setup. Live, he counts the pullbacks and takes the
third anyway — *"this is the third pullback... bought the dip at 68"*
(`0uunIYE_wVY` [19:22]); *"coming into third pullback range and you guys know
my feeling about that **and what it needs to do** in order for me"*
(`RABUjMVS6pI` [52:34]).

A caution with conditions, not a veto — the same shape as `stop_max_distance`
below, and as "too extended", which he also answers with size: *"I got to go
with smaller size cuz I'm chasing it a little bit"* (`0zXUMrYyTx0` [49:27]).

### `price_min` is $2.00, not $1.00

§1 records "1.00 also stated". The live rejections settle it at $2.00: *"JOB is
56 cents. So, that's too cheap for me"* (`1zBC9RKwfeU` [10:36]), and decisively
*"cxdc 115 it's a little too cheap"* (`SwkXSGUHvHY` [04:20]) — $1.15 rejected.

### "First candle to make a new low" means below the flag

*"first candle to make new low **below flag**"* — `Xdw5azEqs6o`. Below the
pullback structure, which is the stop. Fired bar-locally on any lower low with
a red close, it exits on ordinary noise: median hold drops to 2 minutes.

### `stop_max_distance` means cut size, not skip

"If `stop_distance > stop_max_distance`: reduce size or skip" (§5), and
`PLAYBOOK.md:166` is explicit — *"cut your size **or** skip"*. The sizing
formula already reduces shares as the stop widens, so a wide stop is not a
rejection. Treating it as one excludes every strong mover and leaves the engine
trading whichever watchlist name is moving least.

### `stop_min_distance` is not optional

A stop tighter than the spread cannot survive noise. Unimplemented, it admitted
a 2-cent stop on a $15 stock. It accounted for 5 of 16 losses in one
symbol-day study.

### `pullback_index` counts pullbacks, not dips

The count runs within a continuous advance — squeeze, first pullback, squeeze,
second pullback, third means stop (`BUCPPCXOHbs` [52:17]), starting when the
stock first moves up on the catalyst (`m5zu_X-_51I` [46:43]), with
*"careful not to overstay my welcome"* (`aqTXoV923OE` [58:59]). A 1-candle
pause is **not** a pullback and must not consume the count, or the first real
flag arrives numbered #3 and is rejected.

### The 2–3 candle pullback is chart-relative

`PLAYBOOK.md:99` says 2–3 candles, but the source reads a **10-second** chart
as well as the 1-minute — *"the first pullbacks on the lower time frames, like
10-second, one minute"* (`m5zu_X-_51I` [46:43]). On a 1-minute chart a fast
mover's dips are frequently a single bar. Requiring two 1-minute bars therefore
removes setups exactly where the move is fastest; a 1-minute pause **is** a 2–3
candle pullback at 10-second resolution. Unresolved without sub-minute data.

### §1's rejects are rules, not commentary

`faded from pre-market high`, `rate_of_change_min > 0` and
`volume_min >= 500,000` are as binding as the five pillars. Omitting them
produced watchlists where 13 of 19 names had already broken from their
pre-market high before the bell, on a week where the median name spent 16% of
the session above VWAP.

### `volume_min` is cumulative, not a window

"500,000 shares **cum.**" — accumulated over the session, checked at the setup.
Applied to the first five minutes it excludes names that later run hard.

---

## 14. Recaps as an evidence layer

`knowledge-base/transcripts/` holds a **teaching** shortlist, which by
construction excludes the daily recaps — so the corpus documented the strategy
as taught and nothing about the trades actually taken.

`knowledge-base/recaps/` now holds recap transcripts. They name the tickers
traded and walk the entries, which makes them the labelled examples any
calibration needs. A first comparison
(`research/momentum-replication/RECAP-COMPARISON.md`) found every ticker he
named was independently on a watchlist the five pillars produced — the first
external confirmation of any part of the pipeline.

Their dates cannot be taken from the index (see `data/README.md`); they are a
numbered series and should be ordered by their own sequence.

---

## 15. A scanner setting is not a trade gate

§13 records that ~18 defects were all misreadings rather than wrong numbers.
The 2026-08 audit against the blog corpus found six more, and they are all the
**same** misreading:

§1 is titled *"Universe filter — applied before the chart is looked at. All
must pass"*, and it lists price, float, gap %, relative volume and volume as
though those five were one kind of object. They are two.

| | he types this into a scanner | he requires this of a trade |
|---|---|---|
| gap | **5%** — *"all the stocks gapping up more than 5% in the entire market"* (`kicking-back-after-a-7k-day`) | 10% is the pillar |
| relative volume | **5×** (`in-depth-guide-to-my-macd-scalping-strategy`) | *"**150%** and higher is where I make money"* |
| volume | **250,000** minimum (`1zBC9RKwfeU` 1:06:48) | *"less than a million... I actually **lost $8,000**"* |
| float | 20M | 20M hot, **5M cold** |

A scanner dial is set **loose** so that nothing is missed; the eye tightens it
afterwards. Implemented as a gate, a loose dial admits junk and a tight one
silently deletes the population you were trying to find. Both failure modes
look like the strategy not working.

**The test that separates them:** ask whether the number appears in a sentence
about *finding* stocks or about *trading* them. *"I look for stocks priced
between $2 and $20, up at least 10%, with a relative volume of 5x or higher"* —
that is a lookup. *"The stocks that closed the day with one to two and a half
million or more in volume are the ones I did the best on"* — that is a result.

Where they disagree, the **result wins**, because it is measured against
realised P&L and the dial is not measured against anything.

### The same shape, one register up

§13's traps are all "a caution implemented as a veto": `stop_max_distance`,
the third pullback, "too extended". §15's are "a dial implemented as a gate".
Both come from the same habit — reading a statement as more binding than it is.
When a rule and a behaviour disagree in this corpus, the behaviour is the rule
and the statement is the emphasis.

### Dates are evidence too

Every blog file carries `<!-- lastmod: -->` and no pipeline has ever read it.
`premarket_start` is a 2017 rule (§2) that the 2026 recaps reverse. Undated,
the corpus reads as one voice speaking at once; dated, it shows a practice that
changed. Attach the date before treating anything as present tense.
