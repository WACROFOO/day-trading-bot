> # ⚠ SAMPLE — NOT A RESULT
>
> **Every number below is generated from synthetic bars.** The tickers AAAA /
> BBBB / CCCC / DDDD do not exist. No market data was used, because the
> environment this was built in blocks every data feed.
>
> This file exists so you can see the report's *shape* before running it for
> real. Do not read a single figure in it as evidence about the strategy.
>
> To produce a real one:
>
> ```bash
> python scripts/paper_trade_eval.py --scan --days 5 --equity 100000
> ```

# Performance & accuracy report (SAMPLE / SYNTHETIC)

_Generated 2026-08-21 17:42 · account $100,000 · 4 symbol(s) · 5 session(s)_

## Data provenance and what this cannot tell you

Tickers were supplied manually with `--symbols`. This is **not** a point-in-time scan. If they were chosen knowing how the sessions ended, every metric below is contaminated by selection bias.

Bars are 1-minute OHLCV from the free Yahoo feed via `paper_trading.history.fetch_day`, premarket included, covering 5 session(s) from 2026-08-17 to 2026-08-21. That feed is ~15 minutes delayed and retains only ~30 days of 1-minute history, which is the hard ceiling on sample size here. Every requested symbol-session returned data.

Inputs the free feed cannot supply are carried as UNKNOWN, never as passing:

- `tape_green`, `no_seller_wall` (§3) need Level 2 depth-of-book

- `float_max` ≤ 20M and `has_catalyst` (§1) need paid fundamentals and news

Every TAKE below therefore rests on an unverified assumption that those four conditions held. Treat the win rate as an upper bound.

## Headline

| trades | win_rate | expectancy_R | profit_factor | avg_win_$ | avg_loss_$ | net_$ | return_% | final_equity_$ |
|---|---|---|---|---|---|---|---|---|
| 3 | 1.000 | 0.672 | inf | 262.765 | 0.000 | 788.296 | 0.788 | 100788.296 |


§9's breakeven win rate is **33.3%** at the 2:1 the rules aim for. But the reward:risk actually achieved here was **7.95:1**, which moves the real breakeven to **11.2%**. This sample ran **100.0%** over **3** trades — above it.


Scaling half the position at target_1 caps the upside well below 2R while a stop still costs a full R plus costs, so the achieved ratio is structurally lower than the target one. Judging the result against the nominal 33.3% can pass a losing system.


> ⚠ **N = 3. Not significant.** Do not read an edge into this. The corpus claims 65–75% (§9); distinguishing that from 33% at 95% confidence needs roughly 40+ trades. This sample cannot separate skill from noise in either direction.


## Losing trades — what killed each one

_No losing trades in this sample._


## Winners that were skipped — and the rule that skipped them

_72 profitable SKIP candles collapse to **60 distinct opportunities** — every candle inside one move resolves profitably, so the raw count would overstate this by 1×._

| token | gate | winners_blocked | sole_blocker | median_R_forgone | total_R_forgone |
|---|---|---|---|---|---|
| no_confluence | fewer than 2 support reasons (§3) | 56 | 18 | 1.01 | 124.59 |
| price<=ema9 | price below EMA9 (§3) | 29 | 1 | 0.71 | 54.14 |
| macd_hist<=0 | MACD histogram not positive (§3) | 27 | 0 | 0.69 | 26.73 |


`sole_blocker` is the column that matters: those are winners where that condition was the **only** thing in the way. A high count there means the rule is either mis-encoded or genuinely costing money — and per §12.3 you investigate it, you do not quietly relax it.


## Signals the account never got to trade

| reason | signals | median_would_be_R | total_would_be_R | total_would_be_usd |
|---|---|---|---|---|
| max_trades_per_day | 1 | 1.40 | 1.40 | 1117.88 |
| position_already_open | 1 | -0.11 | -0.11 | -143.82 |


These are not strategy failures — they are capacity limits. §7 caps the day at two trades and only one position is held at a time, so a third good setup is unreachable by construction. If `total_would_be_usd` is large and positive, the binding constraint on this account is **capacity, not signal quality**.


<details><summary>Every blocked signal</summary>


| session | symbol | timestamp | reason | detail | would_be_r | would_be_pnl |
|---|---|---|---|---|---|---|
| 2026-08-17 | CCCC | 08-17 14:01 | position_already_open | position open until 10:02 | -0.11 | -143.82 |
| 2026-08-18 | CCCC | 08-18 14:22 | max_trades_per_day | 2 taken (§7 cap 2) | 1.40 | 1117.88 |


</details>


## Diagnostics


### Exit attribution — where the R actually came from

| exit_reason | n | total_R | mean_R | net |
|---|---|---|---|---|
| macd_negative | 3 | 2.02 | 0.67 | 788.30 |


### Are stops being hit by noise?

- Median MAE of **winning** trades: **-0.38R**



If winners routinely dip below −0.5R before working, the §5 stop at the pullback low is inside the noise band and is converting winners into losers. If losers rarely exceed +0.3R, entries are simply early.


### Time of day vs the §2 prime window

| bucket | n | total_R | mean_R |
|---|---|---|---|
| 14:00 | 2 | 0.69 | 0.35 |
| 14:20 | 1 | 1.32 | 1.32 |


§2 puts the edge in 09:30–10:30. If mean R is negative after 10:30, the hard stop should move earlier, not later.


### What the gate rejected, across every candle

| condition | candles_blocked | pct_of_decisions |
|---|---|---|
| fewer than 2 support reasons (§3) | 1229 | 97.2 |
| pullback volume not lighter than impulse (§3) | 993 | 78.5 |
| 3rd+ pullback of the move (§3) | 677 | 53.5 |
| MACD histogram not positive (§3) | 443 | 35.0 |
| no break of the prior candle high (§4) | 288 | 22.8 |
| price below EMA9 (§3) | 203 | 16.0 |
| price below VWAP (§3) | 24 | 1.9 |


Out of **1,265** candle decisions. A condition sitting at ~100% is a red flag: it means the gate can effectively never open, which looks identical to 'the strategy is selective' from the outside. That exact failure was found and fixed in the pullback counter.


### Cost drag — what the spread does to an 8-cent stop

- Round-trip cost is **$0.050/share** ($0.02 slippage + $0.005 commission, each way).

- Median stop distance: **$0.080** → costs eat **0.62R** per round trip.


That is the number that decides whether this strategy is viable. §5 wants a $0.08–0.10 stop; at $0.08 the round trip costs 0.62R, so a "1R" loss is really 1.62R and §9's breakeven win rate moves from 33.3% to roughly 44.8%. Tight stops do not reduce risk here — they amplify the cost ratio.


### Sizing — which constraint actually bound

| bound_by | trades |
|---|---|
| liquidity | 3 |


- Median position: **6,000 shares**, **$39,480** notional on a $100,000 account (**39%** of equity).


When anything other than `risk` binds, §7's risk-based sizing is not what is being traded: realised risk per trade is below the intended 2%, and §9's expectancy scales down with it. When `liquidity` binds, the position is limited by what the tape could actually absorb — §7 concedes this itself, warning that fill quality degrades on sub-20M float and that the edge does not scale linearly. A backtest without that cap reports fills that never existed.


## Decision accuracy (confusion matrix)

|  | won | lost |
|---|---|---|
| TAKE | 4 | 1 |
| SKIP | 72 | 580 |


- precision **0.800** — of setups taken, the share that won

- recall **0.062** — of the **64** distinct winning opportunities, the share actually taken

- raw candle recall **0.053** — the same figure before overlapping candles inside a single move are collapsed. It understates recall and is shown only so the two are not confused

- decisions evaluated: **1,265** across 4 symbol(s)


Low recall with high precision means the rules are leaving money on the table but are not wrong. High recall with low precision means the opposite. They are different problems with different fixes.


## Day by day (§8 risk gate)

| date | trades | start_equity | end_equity | pnl | consecutive_losses | locked | lock_reason |
|---|---|---|---|---|---|---|---|
| 2026-08-17 | 1 | 100000.00 | 100156.18 | 156.18 | 0 | False |  |
| 2026-08-18 | 2 | 100156.18 | 100788.30 | 632.11 | 0 | False |  |
| 2026-08-19 | 0 | 100788.30 | 100788.30 | 0.00 | 0 | False |  |
| 2026-08-20 | 0 | 100788.30 | 100788.30 | 0.00 | 0 | False |  |
| 2026-08-21 | 0 | 100788.30 | 100788.30 | 0.00 | 0 | False |  |


---

_Generated by the blinded walk-forward replay (`scripts/paper_trade_eval.py`). Decisions were made candle by candle with the future hidden; no bar after the cursor influenced any verdict._
