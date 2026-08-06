<!-- source: https://www.warriortrading.com/market-on-open-order/ -->
<!-- lastmod: 2025-01-08 -->

# Market-On-Open Order: Should You Use Them?

A market-on-open order is used to participate in the opening auction of an exchange. Because the MOO order is a market order, it guarantees execution, but not price.

[Interactive Brokers defines](https://www1.interactivebrokers.com/en/index.php?f=598) the market-on-open order as:

“A Market-on-Open (MOO) order combines a market order with the OPG time in force to create an order that is automatically submitted at the market’s open and fills at the market price.” 

The specific mechanisms of MOO orders vary by exchange. NYSE MOOs work slightly differently from Nasdaq MOOs. 

You can find detailed information on the Nasdaq auction [here](http://www.nasdaqtrader.com/Trader.aspx?id=OpenClose) and information on the NYSE opening auction [here](https://www.nyse.com/publicdocs/nyse/markets/nyse/NYSE_Opening_and_Closing_Auctions_Fact_Sheet.pdf). 

## What is the Opening Auction?

Each trading day at the open, there is an auction facilitated by market makers to determine each stock’s opening price. Each exchange hires market makers to reduce volatility and provide liquidity. 

To better achieve their goals, they get special privileges that everyday traders don’t get, but the exchanges attempt to balance it out by obligating the market makers to facilitate trade, even if they don’t want to. 

These market makers used to be called specialists, but now they’re known as designated market makers (DMMs). 

In addition to maintaining orderly markets, DMMs are responsible for facilitating the opening and closing auctions. 

Because the open and close are the periods of highest trading activity, they reduce the volatility that one massive order from a mutual fund or ETF provider might create by providing liquidity to the other side of the trade.

Overnight and early in the morning, traders are entering buy and sell orders at a myriad of prices. 

Some of them are market orders, others have limit prices. The DMM’s job is to balance out the supply and demand. Many times there’s an imbalance on one side of the market. 

For example, there might be 10,000 shares in XYZ stock in buy orders but 30,000 shares in sell orders. When there’s a significant imbalance like this, the DMMs will be buying to offset the imbalance and maintain an orderly market at the open.

Even as an individual trader, you can view the [order imbalances](https://www.warriortrading.com/order-imbalance/) at both the open and close, although it does require a data feed subscription through your broker. 

Some traders track imbalance data over several days or weeks to identify which stocks or sectors big money is flowing into. 

Using the order flow information they have, DMMs determine an opening price that will clear the market, this is most likely the fill price you’ll get with a market-on-open order. 

When you submit a market-on-open order, you’re accepting the price that the DMMs determine to be “fair value” based on the current order flow. 

You’re guaranteed to get an execution because it’s a market order, but not at any specific price. 

## Are You Guaranteed to Get the Opening Price?

There’s an old and now defunct trading blog called Puppet Master Trading that penned a piece called [Execution Quality at the Open & Close](https://web.archive.org/web/20150112110359/http:/www.puppetmastertrading.com:80/blog/2008/08/01/execution-quality-at-the-open-close). 

He analyzed the difference between his fill price and the actual open/close price for 846 market-on-open and market-on-close orders. He found that his MOC orders were almost always filled at the closing print, while his MOO fills deviated much more. 

Here’s a distribution he created displaying the deviations between his fill prices and the actual open and close:

This survey was performed in 2008. A lot has probably changed over 12-13 years, so it’s hard to know how these findings would hold up today, but at the least shows that there can be deviations from the listed opens and closes, for whatever reason. 

I’m sure the deviations could be explained through some minutia related to Regulation NMS or the specific mechanisms of each exchange, but that’s beyond the scope of this article.

 A poster at the Elite Trader forums explains that any deviations are likely because the opening print wasn’t through NYSE, and NYSE MOO orders are filled at the first NYSE print, not the first NMS print. [Read on here](https://www.elitetrader.com/et/threads/moo-market-on-open-does-one-always-get-the-open-price.129284/page-2).

## Bottom Line

Outside of personal preference, the most likely uses for a market-on-open for retail traders are for market-impacting orders or because you need to get the opening print.

In the case of market impact, if you trade in nano-cap stocks, even a small 1,000 share order can dramatically impact the market, so it might make sense to use the increased liquidity of the open or close to trade.

On the other hand, some quantitative systems require you to enter on the open. The market-on-open order is the best way to consistently match your backtesting if you trade one of these systems.

[](/free-day-trading-class/)

[](/ultimate-beginner-day-trading-kit/)
