# The playbook, version 2 — written for a beginner

Every rule below is followed by how many separate statements in the corpus support it, across how many different videos, and links that jump straight to the moment it is said.

Generated from `data/claims.db` by `scripts/pipeline/13_render_v2_docs.py`. Evidence base: 2,050 rule statements from 257 videos.

> **Read this before anything else.** None of this has been tested against historical data. The counts below tell you how often something was *said*, which is not the same as how often it *works*. A rule with 168 mentions and no backtest is a well-repeated opinion. Trade it in a simulator.

---

## Words you need first

Skip this if you already trade. Otherwise the rest will not parse.

| Term | What it means |
|---|---|
| **Candle** | One bar on the chart. A 1-minute candle shows the open, high, low and close for that minute. Green = closed higher than it opened, red = closed lower. |
| **Impulse / push** | The sharp move up that happens before the pullback. Sometimes called the "pole". |
| **Pullback / dip** | The short pause where price drops back after a push. The thing you are actually buying. |
| **Float** | How many shares are actually available to trade. A small float means it takes less buying to move the price. |
| **Relative volume (RVOL)** | How busy the stock is today compared to a normal day. 5x means five times normal. |
| **Catalyst** | The news that explains why the stock is moving — earnings, an FDA decision, a contract. |
| **VWAP** | Volume-weighted average price. The average price paid today, weighted by size. Used as a support line. |
| **EMA** | Exponential moving average. A line of recent average price. The 9 EMA is fast, the 200 MA is slow. |
| **MACD** | A momentum indicator. Positive histogram = upward momentum. |
| **Level 2** | The list of pending buy and sell orders, showing where large orders are waiting. |
| **Spread** | The gap between the best buy price and the best sell price. You pay it on every trade. |
| **Stop** | The price where you exit for a loss, decided before you enter. |
| **Breakeven stop** | Moving your stop up to your entry price, so the trade can no longer lose money. |
| **R / 2:1** | R is one unit of risk. A 2:1 trade aims to make twice what it risks. |

---

## Your trading day, in France time (Paris)

New York time in brackets — that is what your charts will show.

| Paris | New York | What happens |
|---|---|---|
| 13:00 | 07:00 | Pre-market. Build the watchlist. |
| **15:30** | 09:30 | **Market opens.** Watch only. |
| 15:35 | 09:35 | Trading starts. |
| 16:30 | 10:30 | Prime window ends. Most of the edge is gone. |
| **17:30** | 11:30 | **Hard stop. Close the laptop.** |

**The twice-a-year trap.** Europe and the US change clocks on different dates. For about three weeks in late March and one week in late October the gap is 5 hours, not 6, and the market opens at **14:30 Paris**. Set your reminders from the New York time and let your calendar convert.

---

## Set these numbers before the open, while you are calm

| Number | Rule | On a $10,000 account |
|---|---|---|
| Risk per trade | 2% of account | $200 |
| Max loss for the day | 6% of account | $600 |
| Profit goal | same as max loss | $600 |
| Max trades | 2 | 2 |

These do not change during the session. That is the whole point of deciding them now.

---

## Step 1 — Build a watchlist before the market opens

**Do this:** Run the scanner. Keep only stocks where all five filters are true. Expect 3 to 5 names. Zero is a normal day.

**Why:** A "scanner" is a tool that filters every stock on the market down to the few that are moving. You are not looking for a good company — you are looking for a stock that a lot of people are suddenly trading at once, because that is what makes price move far enough, fast enough, to pay for a tight stop.

**Evidence:** 193 rule statements across 99 videos.

Watch it being said:

- [12:43](https://www.youtube.com/watch?v=iBNcF_lPBIg&t=763s) — Stock selection criteria: trending higher daily, up 10%+, high relative volume (5x minimum = 500% normal volume), price sweet spot $5-7, low float, news catalyst  
  <sub>How to Start Trading with $1,000 💥 Small Account Challenge Ep. 1</sub>
- [35:15](https://www.youtube.com/watch?v=EzHEGVb_9-c&t=2115s) — Focus scanner on low-float stocks with high relative volume (5x or higher)  
  <sub>Year in Review: 2016 +$222,244.91 Day Trading Momentum Strategies</sub>
- [2:53](https://www.youtube.com/watch?v=8h1xWOkgrpI&t=173s) — Low float stock (e.g., 4.28 million shares) with fresh catalyst can move quickly and break resistance  
  <sub>Day Trading Tips: How To Build A Watch List</sub>

*float (shares):* `<= 20M` (18x), `<= 10M` (16x), `= 20M` (6x) — from 185 figures across 98 videos.
  **Disputed in the source.** Two values are stated about equally often. Do not pick one and forget the other.

*share price ($):* `range 2–20` (23x), `= 20` (6x), `range 2–10` (5x) — from 144 figures across 98 videos.

*relative volume (x):* `>= 5` (27x), `= 5` (10x), `>= 500` (2x) — from 80 figures across 57 videos.

---

## Step 2 — Watch the first five minutes. Do not trade them

**Do this:** Market opens. Sit on your hands until 5 minutes have passed.

**Why:** At the open the gap between the buy price and the sell price (the "spread") is at its widest, so you pay the most to get in and get out. Waiting costs you nothing and removes the worst fills of the day.

**Evidence:** 63 rule statements across 42 videos.

Watch it being said:

- [33:47](https://www.youtube.com/watch?v=SmSOboqGPgs&t=2027s) — Pre-market: 4:00am-9:30am; more volatility from earnings releases  
  <sub>These Candlestick Tricks Will Change How You Trade</sub>
- [44:17](https://www.youtube.com/watch?v=tR-tyjV1WQ0&t=2657s) — Only trade stocks between 9:30 and lunchtime (no pre-market trading)  
  <sub>I Want to Improve My Trading Over The Next 4 Weeks…Here's How I'd Do It</sub>
- [31:02](https://www.youtube.com/watch?v=pYx756KSvR4&t=1862s) — Use trailing stops only in regular market hours (after 9:30am ET), not pre-market  
  <sub>How to Trade Penny Stocks for Beginners (with ZERO experience)</sub>

---

## Step 3 — Wait for a pullback — the dip inside a move that is going up

**Do this:** Find a stock that just pushed up hard. Wait for it to dip for 2-3 one-minute candles. Take only the first or second dip, never the third.

**Why:** You are not buying the push up. You are buying the pause after it. This is the single most important idea in the strategy, and the reason is not that dips are cheap — it is that a dip gives you a nearby place to put your stop. Buying mid-push leaves you with no sensible exit closer than "wherever it last paused", which is usually too far away to size the trade properly. By the third dip the buyers who missed the first move have already bought, so each dip after that is deeper and slower to recover.

**Evidence:** 70 rule statements across 51 videos.

Watch it being said:

- [9:00](https://www.youtube.com/watch?v=vvXX2ycveuw&t=540s) — Micro pullbacks, bull flags, and ABCD patterns are strongest entry setups  
  <sub>The Simple MACD Strategy to Spot Big Winners Early (5,712% Example)</sub>
- [18:36](https://www.youtube.com/watch?v=ZRRCyIoZnHE&t=1116s) — Add back on micro pullbacks when price comes down slightly  
  <sub>I blew up my small account… 🤯 Small Account Challenge Day 6</sub>
- [48:34](https://www.youtube.com/watch?v=IwDORxvXAAs&t=2914s) — First candle making new high on micro pullback is the entry trigger  
  <sub>How to BUY THE DIP the RIGHT WAY</sub>

---

## Step 4 — Check the dip happened on lighter volume than the push

**Do this:** Compare the volume bars. The dip candles must be shorter than the push candles. If the dip is on heavy volume, skip the trade.

**Why:** "Volume" is how many shares changed hands in that candle. This is the most-repeated condition in the entire corpus, and it is what separates a pause from a top. Same price drop, opposite meaning: on light volume it means buyers briefly stepped back; on heavy volume it means someone is actively selling into the move. The chart looks identical. Only the volume tells you which one it is.

**Evidence:** 169 rule statements across 101 videos.

Watch it being said:

- [10:20](https://www.youtube.com/watch?v=4Pc_von1wS4&t=620s) — Buy pullbacks, dips, and breakouts on quality high-volume stocks  
  <sub>Reading Candlestick Charts Was HARD Until I Learned This 3 Step Trick</sub>
- [31:10](https://www.youtube.com/watch?v=A3sbJBOLGuI&t=1870s) — Light volume on pullback indicates buyers are resting, not panic selling  
  <sub>PROVEN 3hr Day Trading Strategy (Highest Win Rate) — DAY 8 & 9 Small Account Challenge</sub>
- [9:57](https://www.youtube.com/watch?v=aIqF9OvWYZ4&t=597s) — Trade the break of volume-weighted average price after consolidation pullback  
  <sub>Trading the Break of VWAP Setup</sub>

---

## Step 5 — Check the dip stopped somewhere that matters — two reasons, not one

**Do this:** The dip must stop at a price that has TWO independent reasons to matter: a whole or half dollar, the 9 EMA, the 20 EMA, VWAP, the 200 MA, or a price that was resistance earlier.

**Why:** An "EMA" is a line showing the average price over the last N minutes; "VWAP" is the average price weighted by volume. Traders and algorithms put orders at these lines, and separately, ordinary people put orders at round numbers like $5.00. When two of those land on the same price, two unrelated groups are bidding there — so there is genuinely more demand holding it up. A dip that stops at $5.13 for no reason has nothing underneath it.

**Evidence:** 226 rule statements across 100 videos.

Watch it being said:

- [5:40](https://www.youtube.com/watch?v=4Pc_von1wS4&t=340s) — Use only essential indicators: 9 EMA, 20 EMA, 200 EMA, VWAP, volume bars, MACD  
  <sub>Reading Candlestick Charts Was HARD Until I Learned This 3 Step Trick</sub>
- [38:07](https://www.youtube.com/watch?v=aAmmKTLbAts&t=2287s) — Use technical indicators (9 EMA, 20 EMA, 200 EMA, VWAP, MACD) but keep charts uncluttered  
  <sub>+$100,176.35 TODAY Using This SIMPLE Day Trading Strategy</sub>
- [20:31](https://www.youtube.com/watch?v=aqTXoV923OE&t=1231s) — Use 9 EMA and 20 EMA as support levels on intraday (1-minute, 5-minute) charts; 200 EMA on daily charts  
  <sub>7 Candlestick Patterns I'M ACTUALLY USING Every Day</sub>

---

## Step 6 — Check the chart state — four boxes, all must be ticked

**Do this:** Price above VWAP. Price above the 9 EMA. MACD histogram positive. No large seller sitting above you on Level 2. Any one false: no trade.

**Why:** These confirm the dip happened inside a trend that is still healthy, rather than at the start of a collapse. "MACD" is a momentum indicator — positive means the recent average is pulling away from the slower one. "Level 2" is the list of pending orders; a big one sitting above you is a wall your trade has to get through. This is a checklist, not a score. Three out of four is a no.

**Evidence:** 178 rule statements across 84 videos.

Watch it being said:

- [5:40](https://www.youtube.com/watch?v=4Pc_von1wS4&t=340s) — Use only essential indicators: 9 EMA, 20 EMA, 200 EMA, VWAP, volume bars, MACD  
  <sub>Reading Candlestick Charts Was HARD Until I Learned This 3 Step Trick</sub>
- [38:07](https://www.youtube.com/watch?v=aAmmKTLbAts&t=2287s) — Use technical indicators (9 EMA, 20 EMA, 200 EMA, VWAP, MACD) but keep charts uncluttered  
  <sub>+$100,176.35 TODAY Using This SIMPLE Day Trading Strategy</sub>
- [36:38](https://www.youtube.com/watch?v=w2owyBNunDQ&t=2198s) — Use MACD crosses 20/9 EMA (faster crossover than alligator indicator)  
  <sub>The Moving Average Trading Strategy You Need! (Full Training)</sub>

---

## Step 7 — Wait for the trigger — do not anticipate

**Do this:** Buy the first 1-minute candle that trades ABOVE the high of the previous candle. Not before.

**Why:** Everything up to here says a bounce is plausible. This says it has started. The difference matters more than any other rule: a dip that ticks every box and then keeps falling costs you nothing if you waited, and a full stop if you jumped early. "It looks like it is turning" is not the trigger. The candle actually taking out the prior high, while you watch, is the trigger.

**Evidence:** 85 rule statements across 67 videos.

Watch it being said:

- [42:01](https://www.youtube.com/watch?v=js25lIZMUSY&t=2521s) — Entry on first candle making new high after pullback  
  <sub>The Simplest Day Trading Strategy for Beginners (with ZERO experience)</sub>
- [1:27](https://www.youtube.com/watch?v=DP4ayEWhmvM&t=87s) — Entry: buy first candle to make new high after pullback  
  <sub>Master the Bull Flag Trading Pattern TODAY (Step-by-Step Guide)</sub>
- [2:16](https://www.youtube.com/watch?v=SrYGENemM1w&t=136s) — Stock scanners use level one data to identify new highs  
  <sub>How to Choose the RIGHT Market Data for Day Trading</sub>

---

## Step 8 — Size the trade from the stop, not from your account

**Do this:** Stop = the low of the pullback candle. Risk per share = entry minus stop. Shares = your dollar risk divided by risk per share.

**Why:** This is where beginners blow up, so read it twice. If you risk $200 and the stop is $0.10 below your entry, you buy 2,000 shares — a position worth over $10,000 while risking $200. Those are two completely different numbers. The position size looks terrifying and is not the thing that can hurt you; the distance to the stop is. If the stop needs to be more than $0.20 away, trade smaller or skip it — never move the stop to fit the size you wanted.

**Evidence:** 216 rule statements across 122 videos.

Watch it being said:

- [10:06](https://www.youtube.com/watch?v=xgnqOu_fchA&t=606s) — Stop-loss placement: at the low of the last pullback wave, minimizing max loss distance  
  <sub>High Probability Candlestick Chart Patterns</sub>
- [11:17](https://www.youtube.com/watch?v=nfCqhdfyLKo&t=677s) — During choppy price action, reduce position size to cap maximum loss (e.g., 2,000-5,000 shares vs. full 15,000-20,000 share size)  
  <sub>How Read PRICE ACTION on Candlestick Charts (with ZERO experience)</sub>
- [14:30](https://www.youtube.com/watch?v=VNsh-8cS2Tg&t=870s) — Share size: take 5,000–15,000 shares on tight-stop bull flags because probability is high. Target is not just high of day but new highs beyond  
  <sub>Learn how to Day Trade Gappers and Gaps (Beginner Momentum Trading Strategies)</sub>

*position size (shares):* `= 10k` (20x), `= 1k` (14x), `= 100` (11x) — from 296 figures across 131 videos.
  **Disputed in the source.** Two values are stated about equally often. Do not pick one and forget the other.

*max loss ($):* `<= 5k` (3x), `<= 10` (2x), `<= 2` (1x) — from 17 figures across 15 videos.
  **Disputed in the source.** Two values are stated about equally often. Do not pick one and forget the other.

---

## Step 9 — Know all three exits before you are filled

**Do this:** Stop at the pullback low (it never moves down). Sell half at the first target, then move the stop to breakeven. Sell 25% at the next level, trail the last 25%. Exit everything immediately on any break signal. The first target is whichever comes FIRST above your entry — a retest of the day's high, or a move the size of the push that just happened. Typically 15-20 cents.

**Why:** Deciding an exit while holding a losing position is how a small loss becomes a large one — you will find reasons. Selling half and moving the stop to your entry price is the key move: from that point the trade cannot lose money, which is what lets you hold the rest calmly. The break signals are things like a new low, a big red candle on heavy volume, MACD going negative, or losing VWAP. You do not need to know why. You just leave.

**Evidence:** 103 rule statements across 66 videos.

Watch it being said:

- [29:32](https://www.youtube.com/watch?v=QstdS67Iyv0&t=1772s) — In colder market, sell half when up 10%, hold rest with trailing stop  
  <sub>How to Start Day Trading (with ZERO experience)</sub>
- [40:45](https://www.youtube.com/watch?v=4Pc_von1wS4&t=2445s) — Scale out: sell half at first profit, adjust stop to breakeven on remaining  
  <sub>Reading Candlestick Charts Was HARD Until I Learned This 3 Step Trick</sub>
- [28:51](https://www.youtube.com/watch?v=vvXX2ycveuw&t=1731s) — Scaling out: sell half at first target, adjust stop to breakeven on remainder  
  <sub>The Simple MACD Strategy to Spot Big Winners Early (5,712% Example)</sub>

---

## Step 10 — Minimum 2:1 — the arithmetic that makes the whole thing work

**Do this:** Target must be at least twice the distance of your stop. 20 cents up against 10 cents down is fine. 20 against 20 is not — skip it. Measure it against the target you actually expect to reach.

**Why:** At 1:1 you need to win more than half your trades just to break even. At 2:1 you only need to win about a third. That is the entire reason a tight stop matters: it is not about losing less per trade, it is about lowering the win rate you need in order to be profitable at all. One trap: apply the 2:1 test to a target you can genuinely reach. Measured against the high of the day after the stock has already collapsed away from it, every trade passes and the rule protects nothing.

**Evidence:** 74 rule statements across 48 videos.

Watch it being said:

- [13:38](https://www.youtube.com/watch?v=8SWCCRLg1p0&t=818s) — Risk $1 to make $2 (2:1 profit-to-loss ratio) to only need 33% accuracy for break-even  
  <sub>Ultimate Guide to Trading in a Small Account</sub>
- [36:04](https://www.youtube.com/watch?v=RLGDwe2m70E&t=2164s) — On first green month, target 60% accuracy with one trade per day and 2:1 profit-to-loss ratio  
  <sub>I Day Traded This ONE Strategy For 21 days...Here Are The Results</sub>
- [17:28](https://www.youtube.com/watch?v=WQi0KvdLnwM&t=1048s) — Realistic win rate: Aim for 50%+ accuracy; 33% with 2:1 ratio just breaks even psychologically  
  <sub>When to BUY & SELL using Candlestick Charts (with ZERO experience)</sub>

*profit-loss ratio:* `= 0` (14x), `= 7` (8x), `= 4` (7x) — from 107 figures across 67 videos.
  **Disputed in the source.** Two values are stated about equally often. Do not pick one and forget the other.

---

## Step 10.5 — Halts — what to do when trading stops

**Do this:** If the stock halts going UP: wait for the resumption, expect a brief flush as panicked sellers get out, then buy that dip and sell the rip. If it halts going DOWN, or the halt is for pending news (T1), stay out.

**Why:** Low-float stocks that move this fast hit circuit breakers all the time, so this is normal, not an emergency. A "LULD" or volatility halt lasts at least 5 minutes and fires when price moves outside a band - 10% for most small caps over $3, 20% between $0.75 and $3, doubled at the open. A halt going up usually resumes higher; one going down usually resumes lower. The one to avoid entirely is a "T1" news halt: the company asked for it, that almost always means bad news, and it often reopens near half the price it stopped at. While halted you cannot place an order past the band, and the reopening price keeps moving as orders pile up - so you are not missing anything by waiting for the resumption.

**Evidence:** 46 rule statements across 20 videos.

Watch it being said:

- [23:24](https://www.youtube.com/watch?v=FN-uqfbEVKw&t=1404s) — Dip and rip strategy: anticipate panic sellers on halt resumption, then squeeze higher  
  <sub>Trading Halts Explained (Common Halt Reasons & Resumption Times)</sub>
- [5:52](https://www.youtube.com/watch?v=nm-rhysU96k&t=352s) — Dip and rip timing: enter on resumption after halt down, betting on bounce back above previous levels  
  <sub>$SQL +261% Gap and Go Setup!</sub>
- [1:32](https://www.youtube.com/watch?v=ag5JoiOlUy4&t=92s) — Entry on resume from halt if stock breaks halt high with volume  
  <sub>Surprise Daily Breakout Setup at 9:30am ET</sub>

---

## Step 11 — Stop for the day — the rules that work even if the entry does not

**Do this:** Stop on ANY of: max daily loss hit, gave back half your peak profit, green day turned red, three losses in a row, two trades taken, or the clock hits your hard stop. Also stop when you hit your goal.

**Why:** These are the only rules here that do not depend on the strategy having an edge. An entry rule can be wrong; a daily loss limit cannot be — it just bounds how much a bad day costs. If you follow nothing else in this document, follow this section, and follow it in a simulator first.

**Evidence:** 164 rule statements across 81 videos.

Watch it being said:

- [13:51](https://www.youtube.com/watch?v=LdLtyeZHbPU&t=831s) — Exit discipline: Get green and shut down; don't overstay welcome  
  <sub>How to Travel & Trade the RIGHT WAY (Don't make the same mistakes as me)</sub>
- [15:10](https://www.youtube.com/watch?v=2higxJXgl6o&t=910s) — Set internal circuit breaker when FOMO triggers are hit; walk away from trading  
  <sub>How I Deal With FOMO</sub>
- [21:38](https://www.youtube.com/watch?v=5qu6YfbC7tM&t=1298s) — Exit discipline: take profit and walk away; do not overstay once choppy price action begins  
  <sub>$PCSA +175% on the Reverse Split Setup</sub>

*max loss ($):* `<= 5k` (3x), `<= 10` (2x), `<= 2` (1x) — from 17 figures across 15 videos.
  **Disputed in the source.** Two values are stated about equally often. Do not pick one and forget the other.

*account size ($):* `= 1k` (7x), `= 2k` (7x), `= 100k` (5x) — from 162 figures across 78 videos.
  **Disputed in the source.** Two values are stated about equally often. Do not pick one and forget the other.

---

## The whole thing on one card

```
PARIS TIME                    (New York)

13:00       ->  5 of 5 filters  ->  3-5 names       (07:00)
15:30-15:35 ->  watch, do not trade                 (09:30-09:35)
15:35+      ->  pullback 1 or 2, on LIGHTER volume
            ->  did it stop at 2 overlapping levels?   no -> pass
            ->  above VWAP + 9EMA + MACD positive?     no -> pass
            ->  candle breaks prior candle high?       no -> wait
            ->  size = risk / (entry - pullback low)
            ->  buy, limit at ask + 0.15
            ->  sell 50% at target, stop to breakeven
            ->  sell 25%, trail 25%
            ->  any break signal = out, all of it
16:30       ->  prime window over                    (10:30)
17:30       ->  hard stop, close the laptop          (11:30)

Stop at: 2 trades | -6% | +goal | 3 losses | green-to-red | 17:30

Clock warning: late March and late Oct, open is 14:30 Paris.
```

## If you remember four things

1. **Buy the dip inside the move, not the move.** The dip is what gives you a stop you can afford.
2. **Light volume on the dip, or skip it.** Most-repeated rule in the corpus.
3. **Wait for the candle to actually break the prior high.** Not "it looks like it will".
4. **Size from the stop.** A $10,000 position risking $200 is normal. Confusing those two numbers is how people blow up.

And the one that survives even if the strategy does not: **stop trading when you hit your daily loss limit.**
