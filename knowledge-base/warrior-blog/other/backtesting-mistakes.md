<!-- source: https://www.warriortrading.com/backtesting-mistakes/ -->
<!-- lastmod: 2025-01-08 -->

# The Biggest Backtesting Mistakes You Can Make

Backtesting is testing trading strategies against historical data. 

It serves as a research tool for traders and analysts to stress test their current strategies, find new strategies, or find which factor contributes the most to a strategy’s success. 

Most backtesting is done with code, using libraries from languages like Python and R and hence, you can pretty much backtest anything if you have the coding skills to create it. 

There are also some no-code or low-code backtesting solutions like TradeStation or MultiCharts, but they tend not to be flexible enough for professionals. 

An example of backtesting would be to download a decade’s worth of market data, let’s say 2007 to 2017, and test a trading strategy you’re curious about. You need to be able to put the strategy into a strict quantitative format, like “buy when the 50-day moving average crosses above the 200-day moving average,” instead of “buy a bull flag.” 

After the computer is done running the test, you get results like an equity curve, the list of trades, and some metrics like Sharpe ratio and max drawdown.

Here’s an example of a “tearsheet” of analytics generated when you [run a backtest on the Zipline Trader library](https://zipline-trader.readthedocs.io/en/latest/notebooks/Alphalens.html), an updated version of now-defunct Quantopian’s Zipline library:

[](https://media.warriortrading.com/2021/07/20093825/Backtesting.jpg)

This tearsheet is of course tailored by the user for illustration purposes. 

Backtesting can feel like magic. 

Download a bunch of market data, run some parameters against it, tweak them a bit until the test shows a smooth equity curve and presto, you have a profitable trading system that will print money. It can seem like the only barriers are learning to code and understanding which indicators and parameters will yield the best results.

But doing that is simply data mining and using this method of backtesting has little utility because your tests will have no predictive power. It represents a mistake even the most sophisticated researchers repeatedly make: mistaking correlation for causation. I’ll demonstrate this with an example: 

You’ve run thousands of tests using machine learning to find the most profitable trading system. 

The best test shows that the optimal strategy is to buy XYZ stock at 10:53 AM on a Tuesday when on the previous day, the price advanced at least 1.04% and the RSI is at 38 or more. Obviously, this means nothing. If I told you this was my trading system, you’d laugh at me for having such a pointless system that doesn’t exploit any real imbalances in the market. 

All this test did is find the perfect parameters to fit to that exact historical data. 

While data mining when backtesting is rarely this blatantly pointless, you have to constantly check every bias you introduce into a test. 

Here’s a few of the most common mistakes that are crucial to avoid if you don’t want to incinerate money when trading with backtested strategies. 

## Look-Ahead Bias

It’s 2021 and the market has more or less gone straight up for the last decade, save for a huge crash in 2020. 

Knowing this, you can go create a backtest against the historical data to reflect this. For example, you might say, buy the S&P 500 on 5x margin, but sell when the price drops 5% or more in one day. You know that this system will kill it, because it avoids most of the 2020 market crash, while reaping huge gains from the rest of the bull market. 

A test like this will look really nice and can make you wish you only had the system in 2010, because you’d be rich right now. 

But you’re basically cheating. 

It’s like watching a replay of a football game, and then concluding that the best way to win that game was to run the ball on 4th & goal, because passing the ball failed. 

You’re just looking at what actually happened in the past, and pretending like you knew the right answer all along. It might be a fun exercise, but it won’t have any future predictive power. 

Of course, look-ahead bias creeps into our backtests in more subtle ways. Using the same bull market example, momentum strategies on growth stocks have worked excellently, and traders who used those strategies over the last decade won big. 

This can easily lead you to believe that momentum strategies are inherently superior and tailor your entire style to what is working in recent backtests. 

## Over Fitting or Over Optimization

This mistake goes hand-in-hand with look-ahead bias. It’s the act of continually iterating on a backtest and using previous backtest results to inform the new ones. While this can be a valid practice used by many professionals, it’s very easy to get wrong.

Let’s say you’re using a simple RSI mean reversion strategy. 

You buy when RSI is below 20 and close the position when RSI is above 60. The backtest results look pretty good, but when you analyze a few individual trades you find that the biggest losers result in you buying too early; in other words, you think a lower RSI value might result in a better test. So you try testing buying below 15 and selling above 60. 

The test looks better, but again, when analyzing individual trades, you find that some of your winning trades go on runs, so you decide to extend your holding period and close trades when RSI is above 70. 

This process might feel like a productive process of slowly optimizing your trading strategy to get the best results, but in reality, you’re really just “p-hacking.” 

You’re throwing several observations on one set of data until a test shows the desired result. This is a problem in many scientific fields, and is the reason that most academic studies aren’t replicable.

Let’s simplify with a real-life example. You love basketball and you want to show off your skills. You record yourself throwing ten free-throws over and over again until you finally hit ten in a row. Of course, that’s the video you upload to YouTube. 

You’re simply performing the same test over and over again until you get the result you want. Of course, that’s not representative of your actual basketball skills. 

One way to mitigate this bias is by using out-of-sample data. This is when you test and optimize your data on say, market data from 2007-2012, then once you’re done optimizing it, you see if you can repeat similar performance on data that your model hasn’t seen, like, 2013-2018. 

It’s kind of like endlessly trying to get ten free throws in a row, then, once you’ve done it, you try out your new tactics completely fresh, to see if you can repeat the results. If you hit four of ten, your previous test was probably an anomaly. 

Of course, there are legitimate methods of optimizing backtest results. 

Many heavily utilize walk-forward optimization, which tests the strategy on unseen data, preventing you from that snooping bias that we’ve labored so heavily in this article. 

There are many professionals that don’t use optimization methods at all, and instead stick with very rough backtests that test the core idea, rather than specific parameters. 

Read the works of Ernie Chan and Kevin Davey for some good commentary on this issue.

## Treating Backtesting As An Engineering Problem

The primary obstacle to start backtesting is learning to code and understanding how to handle financial data. As a result, a huge number of programmers hear that you can test trading strategies by writing some Python and are rightly intrigued.

But being programmers and not experienced traders, many suffer from treating it as an “engineering problem,” meaning they focus more on shiny objects like machine learning, high-level math, and cool tools, rather than figuring out trading strategies that have a logical grounding. 

By no means am I saying that machine learning or math aren’t important. Not at all. But they’re just tools. If you don’t have a specific reason to utilize them, it’s no different than a new trader trying every combination of technical indicators on TradeStation backtests. 

With modern computer hardware, it’s a pretty trivial task to run thousands of simulations against financial data. 

You can come up with all kinds of crazy results. You might find that buying oil stocks in January after the price of gold has declined three days in a row is a strategy with 100% win-rate. But think about it, why would that work in the real world, going forward? 

What are you exploiting, or what service are you providing to the market by making these trades? 

## Neglecting Transaction Costs

Over time, you’ll find that transaction costs, while they’ve declined significantly over the last two decades, will still eat up a big chunk of your profits.

But it really depends on the type of strategy you’re employing. If you’re a hyper-aggressive day trader who trades high-flying stocks, transaction costs eat up a huge portion of your profits. 

But the position trader who holds trades in highly liquid futures contracts for a few weeks at a time will be less affected by them.

### Illiquid Stocks

One “hidden” transaction cost is the difficulty of getting filled in an illiquid stock. 

For example, let’s say you’re employing a share class arbitrage strategy. It’s very easy to fool yourself with this type of trade because when you don’t account for the transaction costs, it looks like a high sharpe ratio strategy. 

We’ll use Lennar’s two share classes as an example. 

You have Lennar’s A-class shares, trading under the ticker $LEN, which is the highly liquid side of the pair, then you have the B-class shares, trading under $LEN.B, which trades very seldomly throughout the day and regularly has a very wide bid-ask spread.

The simple way to run a backtest is to assume you could trade at or near the last price traded. 

For instruments like the S&P 500 or mega-cap stocks, this is an okay assumption to make when you’re trading in trivial size. But, if you go and try to trade $LEN.B or a similliary illiquid stock, you’ll find that it’s often difficult to get filled at the last price, and if you want to get filled instantly, you’ll have to cross the spread, and take liquidity out of the market. 

And, most of the time, this crossing of the spread negates the profitability of the trade altogether.

There’s a few other pesky issues (which you could argue are also hidden transaction costs that are difficult to model for) that get in the way of executing this strategy successfully, but those are beyond the scope of this section.

In general, transaction costs are the most influential to a few types of trading strategies, making these much more difficult to get a realistic backtest:

- Multi-legged trades, like pairs trades, or arbitrage trades.

- Higher-frequency trading, like intraday trading.

- Trading less liquid products, like microcap and small-cap stocks.

In pairs trades, you have to cross the spread or provide liquidity in two different stocks, and you’ll often get filled at different times for each.

A higher frequency of trades means you’re paying commissions and crossing the spread more often (or, if you’re passive, you often won’t get the same price in live trading that your model assumes you’ll get). 

And you kind of have to throw the book away when trading less liquid products because a historical backtest can’t tell you when someone will come around to trade with you, and at which price. 

## How Do I Learn to Backtest Trading Strategies?

There’s yet to be a streamlined platform like CodeAcademy for learning to backtest trading strategies that I know of. 

And most tutorials are tailored to a specific library or source of data. Many examples, for example, rely on Zipline, the backtesting library for Python that now-defunct Quantopian developed. But the company stopped maintaining the library after they were acquired by Robinhood. 

So as of now, since there’s no “official” path to learn backtesting, your learning path really depends on your level of competency with programming. 

If you’re brand new, you’re best off starting with Python, because it’s the most popular language for manipulating financial data and is pretty easy to get started with. [DataCamp](http://datacamp.com) has some decent courses that teach you to mess around with financial data, but it’s not very trading-focused. 

A decent book with some code “recipes” is [Andreas Clenow’s ](https://www.amazon.com/Trading-Evolved-Anyone-Killer-Strategies-ebook/dp/B07VDLX55H)[Trading Evolved](https://www.amazon.com/Trading-Evolved-Anyone-Killer-Strategies-ebook/dp/B07VDLX55H). Yes, it utilizes the Zipline library which is no longer maintained, but if you’re brand new, the most important aspect is understanding how to manipulate financial data. 

Once you’ve learned the essential libraries for this: numpy and pandas, it becomes a lot easier to go and piece together your own algorithms from StackOverflow and related websites. 

## Bottom Line

It’s way too easy to be fooled by a backtest. Sophisticated high-net worth investors are frequently fooled into investing into questionable hedge funds based on fancy backtests and simulations.

It’s healthy to be cynical when you see any backtest results, but don’t be a defeatist. There’s a reason that backtesting is a vital tool in the professional trader’s toolbox. The problem isn’t with backtesting, it’s with the misunderstanding that a successful backtest “proves” anything.

It’s a research tool, and when approached that way, it’s rewarding.
