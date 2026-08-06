<!-- source: https://www.warriortrading.com/quantitative-trading/ -->
<!-- lastmod: 2025-01-09 -->

# The Beginners Guide to Quantitative Trading

The phrase ‘quantitative trading’ has quickly entered the finance lexicon, so much so that everyday investors have become familiar with quants enough to know it means computer trading. In this article, we’ll try to explain the concept a bit further for the market layman.

[](https://media.warriortrading.com/2019/11/image1.png)

Frequency of the phrase “quantitative trading” in Google Books

## What is Quantitative Trading?

Many are under the impression that a quant has to be a programming whiz, creating highly sophisticated algorithms for use in [high-frequency trading](https://www.warriortrading.com/high-frequency-trading-definition-day-trading-terminology/) (HFT). While that is one thing a quant might do, it represents a misunderstanding of what quantitative trading truly is.

Quantitative trading is the process of quantifying the probabilities of market events and using that data to create a rules-based trading system. It’s the application of the scientific method to financial markets. 

Quantitative trading strategies vary in their complexity and computing power requirements. 

They can be as complicated as an HFT algorithm, making markets in picoseconds, or as simple as buying the 10 Dow stocks with the highest dividend yield and rebalancing each year. 

Both strategies are based on the identification of repeatable patterns in historical data and have quantitative criteria.

## The Difference Between Quantitative Trading and Qualitative Trading

Qualitative traders use their intuition and pattern recognition skills, coupled with looser criteria, to make trading decisions. 

Quantitative traders still use their intuition and pattern recognition skills. Still, they typically use them to generate hypotheses which they test over several asset classes, time frames, and time periods to measure the strategy’s robustness.

A qualitative trader might think, “I see a lot of momentum flowing into this ticker, and a trend is forming. I’m going to buy on the next pullback.”

A quantitative trader might think, “Buying trend pullbacks within momentum names seems like a good strategy. I’m going to backtest it to see it’s profitability.”

## Types of Quantitative Trading

Their speed and trading goals typically distinguish different quantitative trading strategies.

When distinguishing by speed, you have a few classes of quantitative traders. There are no hard and fast rules when applying these labels, but our explanations below are quick rules of thumb.

### Low-Frequency Trading

Low-frequency trading typically refers to trading that uses end-of-day data, rather than intraday data in their models. Trades tend to last more than one day. 

Various strategies exist within this time frame.

One example of a simple strategy, even accessible to retail traders, would be a swing trading strategy based on mean reversion. Perhaps the core idea of the strategy is to buy pullbacks within uptrends. 

We can use trend identification criteria to establish our universe of stocks to trade, then apply our entry, exit, and risk management criteria and build an algorithm around it.

Low-frequency trading can still get quite sophisticated. One example would be trading based on purchasing trends in anonymized credit card data. Through massaging this data, an analyst might conclude that Walmart might beat or miss their future earnings expectations. 

Point72 Asset Management, a hedge fund run by Steve Cohen, is an example of a firm applying credit card data to their trading.

### Medium-Frequency Trading

Medium-frequency trading refers to trading that takes place intraday, usually within minutes to hours. Two critical differentiators between MFT and HFT is that MFT doesn’t generally take advantage of market microstructure, and the importance of market impact is significantly smaller. 

The use of special order types, minute differences between exchanges, or order latency doesn’t play much of a role in MFT strategies like they do in HFT.

MFTs focus less on market impact because their trades last longer, and they’re taking advantage of more significant price moves, requiring less capital per trade. 

### High-Frequency Trading

High-frequency trading is characterized by trading on time frames impossible for humans to trade on (ranging between picoseconds and seconds), and the need for considerable infrastructure and talent investment, making the barrier to entry very high.

HFT strategies generally have very high Sharpe ratios, which necessitates many firms to stop raising outside capital quite quickly at all. 

The strategies of HFTs are based primarily on taking advantage of inefficiencies or inequities in market structure. To simplify things, there are three aspects that HFTs use to get an edge in these tiny time frames:

- Speed

- Access

- Exclusivity

### Speed

When you hear about HFT in the media, the speed advantage is the most often mentioned. They achieve this advantage through colocation, efficient code, and exclusive data feeds. 

They have their computers plugged directly into the data centers of stock exchanges, which reduces the latency between order sending and delivery, they hire the best programmers and purchase exclusive data packages from exchanges.

### Access

HFT firms have access to things the rest of the market doesn’t. The most notable difference in access they have is special order types. They’re given access to special order types by exchanges, often consulting with the exchange in the creation of the order. 

An example of a special order type that we saw highly reported in the media was the “hide not slide” order.

### Exclusivity

Through relationships, access to capital, and the ability to colocate, HFT firms have exclusive access to specific data feeds. Market structure expert and software developer Eric Hunsader of Nanex [determined that](https://www.marketwatch.com/story/heres-the-advantage-high-frequency-trading-firms-have-over-everyone-else-2015-08-13) HFT firms have a 500-microsecond speed advantage in their Nasdaq data feeds. In the HFT realm, this is a lifetime.

## Quantitative Trading Strategies

### Market Making

A market maker provides liquidity on both the buy-side and sell-side, to capture the bid-ask spread. In the last few decades, the maker-taker business model for stock exchanges has sprouted up, which pays liquidity providers to make a market. Maker rebates are another profit center for market makers.

In the modern market, the majority market making is automated by quantitative traders, most of the HFT variety. They use highly sophisticated algorithms to make markets for thousands of securities quickly. 

QuantInsti published a useful graphic that encapsulates why HFTs have taken over the market-making business in recent decades.

[](https://media.warriortrading.com/2019/11/image2-1.jpg)

### Arbitrage

At it’s most basic, arbitrage is the act of buying an asset in one market and selling it in another market for a profit. As computing power advanced and automated trading came about, most pure arbitrage strategies no longer meaningfully exist.

Arbitrage trading strategies are still a considerable part of today’s market, though – They’re just more complicated. Most of them fall under what is known as statistical arbitrage, which aims to take advantage of statistical relationships between securities. 

The most basic example of statistical arbitrage is pairs trading. Perhaps we identify that JP Morgan and Goldman Sachs stocks tend to move together. This relationship is known as correlation, which refers to how positively or negatively, the two prices are related.

### Mean Reversion

Most trading and investing strategies can be categorized as mean reversion or trend following. Mean reversion strategies 

## Example of a Basic Quantitative Trading System

First, we have to set some trend identification criteria to ensure we’re trading stocks that are trending. For the sake of this example, this will be our long criteria (all based on daily bars):

- Stock is trading above its 50-day simple moving average

- Stock’s 20-day moving average is above stock’s 50-day moving average

- Stock’s Average Directional Index (ADX) is above 25

- Stock is trading within 5% of its 52-week high

Now, we have a list of stocks in uptrends that we can use to find trading opportunities. From there, we have to set our trade entry criteria. For the sake of this example, we’ll use the 2-period RSI to identify a short-term pullback:

- Stock’s 2-day RSI is below 10

Now we need to plan our trade exit. We’ll continue to use the exit criteria established by Larry Connors in his RSI2 writings:

- Stock’s 2-day RSI crosses above 50

- Stock closes above its 5-day simple moving average 

After this, there’s still plenty of work to do, depending on how deep you want to go. Here are some questions you must answer?

- How will I size my positions?

- How will I choose which setups to trade when there are multiple opportunities?

- Will I implement any conditions? For example, only trade on the long side when the broad market is uptrending, and vice versa?

- Will I use stop losses?

- How many positions will I take at once? Do I care about the correlation between those positions

## Final Thoughts

The advent of quantitative trading has turned Wall Street on its head. No longer are the big banks seeking out MBAs with competitive sports backgrounds, they’ve shifted their hiring preferences to those with math and engineering backgrounds. 

Offices packed with terminals replaced trading floors, and soft skills like talking to customers and analyzing financial statements have seen their value diminished. 

Whether or not you intend to become a quant or work on Wall Street, getting a base understanding of the strategies that dominate today’s markets will improve your trading.
