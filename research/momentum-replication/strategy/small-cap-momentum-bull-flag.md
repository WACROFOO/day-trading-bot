# Small-Cap Momentum — Bull Flag Breakout

**Source:** Ross Cameron / Warrior Trading (see `../sources/ross-cameron-warrior-trading.md`)
**Verification status:** ❌ Not validated. Rules transcribed from public material. Never backtested by us. Read the source document's regulatory section before assigning any confidence to this.

## Concept

Trade low-float small-cap stocks that are gapping up on a news catalyst with abnormal volume. Enter on the breakout of a short consolidation ("bull flag") on the 1-minute chart, exit within minutes. High win rate, small winners, tight stops, many trades.

## Scanner criteria (stock selection)

| Filter | Rule |
|---|---|
| Price | $2 – $20 |
| Float | Under 10 million shares |
| Pre-market gap | ≥ 2% minimum, ideally ≥ 10% at the open |
| Relative volume | ≥ 5× the 50-day average volume |
| Catalyst | Required — breaking news (earnings, FDA approval, contract, offering) |

All five must hold. The catalyst requirement is the hardest to automate and the easiest to fake a backtest on — historical news timestamps are frequently wrong or unavailable, which is a serious lookahead-bias risk.

## Entry

- **Timeframe:** 1-minute candles
- **Pattern:** Bull flag — a sharp upward move (the pole), followed by a shallow 2–4 candle pullback (the flag)
- **Trigger:** Entry on the first candle that breaks above the high of the pullback range

## Exit

- **Stop loss:** Low of the pullback swing
- **Target:** Retest of high-of-day, or a measured move equal to the pole height
- **Minimum risk/reward:** 2:1, preferably 3:1

Worked example: entry $7.00, stop $6.50 (risk $0.50), target $8.00 (reward $1.00) → 2:1.

## Position sizing — "profit cushion" method

1. Open the session at **25% of full position size**.
2. Trade at reduced size until 25% of the daily profit goal is banked.
3. Once that cushion exists, scale up to full size.
4. If the cushion is given back, cut size or stop trading for the day.
5. If no valid setup appears within ~30 minutes of the open, end the session.

Management rules: add to winners only (pyramid on confirmation), never average down, move stop toward break-even after adding.

## Claimed performance (51-day challenge — unverified, source is marketing)

| Metric | Claimed value |
|---|---|
| Win rate | 71.4% |
| Average winner | $1,800 |
| Average loser | $761 |
| Win/loss size ratio | ~3:1 |
| Avg hold, winners | 3 minutes |
| Avg hold, losers | 2 minutes |

A 71% win rate combined with a 3:1 payoff ratio implies an extraordinary expectancy. Edges of that magnitude are exceptionally rare and do not usually survive honest out-of-sample testing with realistic costs. Treat this table as the claim to be **disproved**, not the target to be matched.

## Known implementation obstacles

Listed here so they are dealt with before, not after, a backtest produces exciting numbers.

1. **Data cost and quality.** Requires 1-minute intraday bars plus historical float and news data for delisted and heavily diluted small caps. Free sources (yfinance) do not cover this adequately and are badly affected by survivorship bias — companies that reverse-split, delisted, or went to zero often vanish from history.
2. **Slippage dominates.** On a 3-minute hold in a low-float stock, the spread and slippage can exceed the entire expected edge. Any backtest that assumes fills at the trigger price is worthless.
3. **Catalyst detection.** Automating "breaking news" in real time is a hard, separate problem. Backtesting it without lookahead bias is harder still.
4. **PDT rule.** Under $25,000 equity, US margin accounts are capped at 3 day trades per 5 business days. This alone invalidates a naive high-frequency small-account backtest.
5. **Halts.** Low-float momentum names halt frequently (LULD). A stop loss does not protect you through a halt that reopens lower.
6. **Short-side borrow.** If shorting the fade is added later, locate availability and borrow fees become a real constraint.

## Next steps before writing any strategy code

1. Decide on an intraday data source and verify it includes delisted symbols.
2. Build the backtest engine with slippage and commission modeled explicitly and pessimistically.
3. Implement the scanner and confirm it reproduces a plausible list of historical movers on spot-checked dates.
4. Backtest the bull flag entry with no catalyst filter first, to establish a baseline.
5. Reserve the most recent 12 months as untouched out-of-sample data. Do not look at it during development.
