---
video_id: FN-uqfbEVKw
title: "Trading Halts Explained (Common Halt Reasons & Resumption Times)"
url: https://www.youtube.com/watch?v=FN-uqfbEVKw
duration_min: 30
teaching_class: howto
topics: [trading-halts, circuit-breaker, volatility-pause, halt-bands, liquidity, risk-management, level-2]
has_rules: true
---

# Trading Halts Explained

## Summary

Comprehensive overview of three main halt types (volatility halts, pending news halts, SEC suspension halts), halt band calculations, resumption times, and practical strategies for trading around halts. Essential knowledge for volatile stock traders who encounter halts regularly.

## Mechanical rules

- [00:01:24] Volatility halt (LULD or circuit breaker halt) lasts exactly 5 minutes minimum.
- [00:01:31] To find resumption time: check timestamp of last order, add 5 minutes to the second.
- [00:01:48] If doesn't resume at 5-minute mark, will resume at next 5-minute increment (10, 15, 20, 25, 30 min, etc.).
- [00:01:59] T1 halt = stock halted pending news; usually means news is bad (company requested halt).
- [00:02:06] T12 halt = SEC/exchange suspended trading due to investigation or unusual activity request; can last weeks/months.
- [00:05:01] Halt bands prevent stock from moving more than certain % in less than 5 minutes.
- [00:06:25] Tier 1 securities (S&P 500 companies) above $3: halt if move more than 5% in less than 5 minutes (up or down).
- [00:09:00] Tier 2 securities (most small-caps) above $0.75 with previous close above $3: halt bands are 10% from reference price.
- [00:09:55] Tier 2 securities (small-caps) with previous close $0.75-$3: halt bands are 20% (twice as wide as tier above $3).
- [00:10:24] Tier 3 securities below $0.75: halt every 15 cents OR 75%, whichever is lesser.
- [00:12:06] Price band percentage based on previous day's close, not current price.
- [00:12:31] Reference price = average price over last 5 minutes.
- [00:12:39] Reference price updates every 30 seconds if new price is at least 1% different from previous reference.
- [00:13:15] If stock reaches halt level and stays there 15 seconds, halt triggers.
- [00:14:35] No orders can be placed above/below halt band (limit order restriction).
- [00:17:44] First resumption opportunity is 5 minutes from last trade timestamp (to the second).
- [00:19:03] Stock halted going up typically resumes higher; halted going down typically resumes lower.
- [00:23:24] Dip and rip strategy: anticipate panic sellers on halt resumption, then squeeze higher.
- [00:24:29] T1 pending news halt: company usually resumes at ~50% of current price.
- [00:25:55] NYSE/AMEX more likely to request company comment on huge moves vs. NASDAQ.
- [00:26:15] Do not trade NYSE/AMEX small caps expecting to see resumption price like NASDAQ provides.

## Setups and patterns

- **Circuit breaker halt (LULD)** — automatic pause when volatility hits predetermined band; most common halt type. [00:01:27]
- **Volatility trading pause** — same as LULD; 5-minute halt minimum to prevent flash crashes. [00:01:24]
- **Dip and rip** — stock flushes on halt resumption as panic sellers exit, then squeezes higher as smart money buys the dip. [00:23:20]
- **Panic sell flush and recovery** — beginner traders place multiple sell orders during halt, getting liquidated on resumption before recovery. [00:22:48]

## Indicators, tools, platforms

- **Level 2 market data** — shows halt up/down limit levels and order book; required for professional trading of halting stocks. [00:03:57]
- **Limit up/limit down (LULD) levels** — displayed in level 2 showing exact price halt will trigger. [00:04:08]
- **NASDAQ/NYSE halt scanner** — real-time tool showing stocks currently halted and halt codes. [00:25:20]
- **Broker order types** — limit orders, stop orders; critical for managing positions during/around halts. [00:01:34]

## Numbers and thresholds

- [00:04:22] Example halt level: $27.93 on specific stock triggers halt after 15 seconds at that price.
- [00:06:31] Tier 1 securities (S&P 500, Dow): halt if 5% move in less than 5 minutes.
- [00:08:59] Tier 2 securities above $3 (previous close): 10% halt band.
- [00:09:56] Tier 2 securities $0.75-$3 (previous close): 20% halt band.
- [00:10:35] Tier 3 securities below $0.75: 15¢ or 75% halt, whichever is lesser.
- [00:12:02] pH stock (previous close $1.75): falls in Tier 2, so 20% halt band.
- [00:12:43] SLRX previous close $1.55: Tier 2, 20¢ halt band increments.
- [00:12:51] GRRR previous close $12: Tier 1-like, 10% halt bands.
- [00:12:03] GRRR halt level: $13.22 (approx 10% above $12.20 reference).
- [00:18:48] MTSL stock: up 65% on day, previous close ~$1.20, halt bands 20¢.
- [00:17:08] MTSL LULD level: $1.84 (halt triggers here).
- [00:20:15] MTSL halted at $1.84 timestamp 10:20:08 seconds.
- [00:20:11] Resumption time: 10:25:18 seconds (exactly 5 minutes later).
- [00:21:12] Resumption quote moved from $1.84 to $1.90 (6¢ increase) during halt as buyers placed orders.
- [00:21:23] Resumption price updated to $2.24 as more buyers placed larger orders.

## Claims needing verification

- [00:01:19] Circuit breaker halts were created to prevent downward flash crashes, not prevent upwards momentum.
- [00:05:05] High-frequency trading algorithms can cause sudden selling spirals; halts prevent this.
- [00:24:03] Companies are more likely to halt on bad news than good news.
- [00:25:15] NASDAQ listed companies show resumption prices; NYSE/AMEX do not.
- [00:26:32] NYC stocks more likely to get T1 halts when making 1000%+ moves without news.

## Caption quality notes

Potential garbled text: [00:10:24] "every 15 cents" possibly autocorrect issue in caption source, but meaning is clear from context.
