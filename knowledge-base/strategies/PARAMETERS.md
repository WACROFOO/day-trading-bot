# Quantified strategy

Every rule in `STRATEGY.md` as a parameter. Values are what the corpus states,
not what has been tested.

**`n` = how many rule statements across 257 videos invoke that concept.** It
measures emphasis, not correctness. High `n` means he says it constantly. It
does not mean it works.

**Conflict** = the corpus states more than one value. Backtest the range.

---

## 1. Universe filter

Applied before the chart is looked at. All must pass.

| Parameter | Op | Value | Unit | n | Conflict |
|---|---|---|---|---|---|
| `price_min` | >= | 2.00 | $ | 144 | 1.00 also stated |
| `price_max` | <= | 20.00 | $ | 144 | 10.00 also stated |
| `price_sweet_min` | >= | 5.00 | $ | — | 2.00 |
| `price_sweet_max` | <= | 10.00 | $ | — | — |
| `gain_pct_min` | >= | 10 | % on day | 666 | — |
| `rvol_min` | >= | 5.0 | x 50-day avg | 61 | 100x, 500x cited as ideal |
| `float_max` | <= | 20 | M shares | 72 | 10M preferred, 5M ideal |
| `has_catalyst` | == | true | bool | 83 | — |
| `volume_min` | >= | 500,000 | shares cum. | 102 | — |
| `rate_of_change_min` | > | 0 | % gain per minute, rising | — | not numerically stated |

Rejects: `price < 1`, `float > 100M`, no catalyst, faded from pre-market high.

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
| `session_close` | 11:30 | hard stop | 16 |
| `premarket_start` | 07:00 | limit orders only | 38 |
| `midday_avoid` | 11:30–15:00 | no trades | 16 |

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
| `stop_max_distance` | <= | 0.20 | $ per share | — |
| `stop_typical` | ~ | 0.08–0.10 | $ per share | — |
| `stop_min_distance` | >= | spread width | $ | — |
| `breakeven_trigger` | >= | +0.10 | $ or after 1st scale | 30 |
| `widen_stop_allowed` | == | false | bool | 50 |
| `add_to_loser_allowed` | == | false | bool | 50 |
| `vwap_break_exit` | == | true | hard invalidation | 45 |

If `stop_distance > stop_max_distance`: reduce size or skip. Never widen.

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
  gain_pct_min: 10
  rvol_min: 5.0
  float_max_shares: 20_000_000
  volume_min_shares: 500_000
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
  end: "11:30"
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
  max_distance: 0.20
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
257 videos. Values are stated, not validated. See `STRATEGY.md` §12.*
