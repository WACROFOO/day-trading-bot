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

Rejects: `price < 1`, `float > 100M`, no catalyst, faded from pre-market high.

Funnel: ~8,000 equities → ~50 scanner hits → 3–5 watchlist → 1–2 trades.

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

These carry high `n` but no measurable definition. They are where a backtest and
a live result will diverge.

| Concept | n | Why it resists encoding |
|---|---|---|
| support and resistance | 157 | level selection is discretionary |
| emotional control | 65 | not observable in price data |
| "A-quality setup only" | 22 | no stated discriminator vs B-quality |
| reversal timing | 102 | "10–15 candles one direction" is loose |
| halt behaviour | 46 | halt-resume fills are unmodellable from OHLCV |
| news quality | 83 | requires NLP on the catalyst itself |
| Level 2 / tape reading | 47 | needs full order-book data, not bars |

Anything above needs a proxy before it can be tested, and the proxy is the
biggest source of backtest error.

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
3. **Sensitivity** — sweep `rvol_min`, `float_max`, `price_max`. Does the edge survive, or does it sit on one lucky cell?
4. **Costs** — re-run with realistic spread and slippage on sub-20M float. This is where most momentum edges die.
5. **Regime** — split by year. 2017 / 2021 / now. An edge in one regime only is not an edge.

Baseline to beat: buy-and-hold the same universe, same holding period. If the
strategy does not clear that, the rules are noise.

---

*Derived from `../data/rules_digest.md` — 2,040 rules, 2,903 numeric figures,
257 videos. Values are stated, not validated. See `STRATEGY.md` §12.*
