<!-- source: https://www.warriortrading.com/contingent-orders/ -->
<!-- lastmod: 2025-01-08 -->

# Contingent Orders: How They Work

Contingent orders require an event to occur to trigger their execution. 

They’re contingent on something happening. If that something doesn’t happen, the order is never executed and remains resting with your broker. These might also be referred to as “conditional orders.” 

Here’s how [Nasdaq defines](https://www.nasdaq.com/glossary/c/contingent-order) a contingent order:

“An order which can be executed only if another event occurs; i.e. ‘sell Oct 45 call 7-1/4 with stock 52 or lower’.”

 A stop loss is a basic example of a contingent order. 

The stop-loss order’s execution is contingent on the stock reaching your stop-loss price. As long as the stock doesn’t reach the stop price, the order isn’t executed. 

For example, you enter an order to buy 100 shares of XYZ stock at $10.00, and you attach two contingent orders with it: a stop loss and a take profit. 

The stop loss is at $9, and the take profit is at $13. 

In this situation, your regular buy order at $10.00 is immediately sent to the market for execution, while your stop loss and take profit orders are sitting on your broker’s servers, waiting for their contingency events to occur. 

As long as the price doesn’t reach either $9 or $13, your stop and take profits won’t be executed.

Let’s assume that the price declines and reaches $9. Your stop-loss order is activated and sent to the market. Upon execution of the stop-loss, your take profit order is canceled.

## Types of Contingent Orders

Any order that requires some condition to be true before it can execute is a contingent order. 

There are several different types of these orders, and your access to them depends on which order types your broker offers. 

The most simple contingent order is the classic limit order. 

The condition of the limit order is to only buy or sell at a specified price or better. A buy order at $10 only executes when the price is at $10 or below, else it remains resting on the order book. 

The next level is to stop losses and take profit orders. 

They’re attached as brackets to your main order. Their conditions are similar to the limit order. 

For example, the condition for a stop loss might be that when the price reaches $8.00, submit a sell order at the market.

Most traders and investors will only ever use these basic order types. However, contingent orders can get much more complicated if you want them to.

Here’s a shortlist of contingent orders available on several trading platforms:

- [Stop loss](https://www.warriortrading.com/stop-order-definition-day-trading-terminology/): liquidate position when the stock reaches your stop-loss price.

- [Market-on-close order](https://www.warriortrading.com/market-on-close-order/): buy the closing print

- [Fill-or-kill order](https://www.warriortrading.com/fill-or-kill-fok-definition-day-trading-terminology/): fill the entire position, or else close the order

If you have access to an advanced trading platform that allows you to write scripts that can send orders, you can get much more creative than the preset orders included in standard order tickets.

If you’ve ever learned basic programming, think of contingent orders as if, then statements. Let’s look at very basic code to demonstrate this:

This script loops through a range of numbers, 0-9, and checks if each one is greater than 5. If that condition is true, then the number is printed to the console, like so:

Pretty simple, right? Imagine the same thing with orders, with your only limitation being what your broker will allow you to do. 

Advanced trading platforms like NinjaTrader and Interactive Brokers’ TWS platform will allow you much more leeway than something basic like Fidelity’s web interface.

For example, let’s say we identify a stock in a strong intraday uptrend that we want to buy on a pullback to the [VWAP](https://www.warriortrading.com/vwap/). 

Instead of gluing your eyes to the chart all day waiting for the pullback, your broker might allow you to craft a contingent order around this condition. 

You’d essentially be telling your broker, “buy 100 shares at the market when the last price reaches the intraday VWAP.” 

You might instead place a trailing buy order that moves with the VWAP.

Another example would be to buy a stock when it reaches the lower Bollinger Band.

## Bottom Line

The vast majority of order types in the stock market come down to a computer script dictating how a standard market or limit order will be executed. 

For example, stop losses are standard market or limit orders that are only sent to the market when the stop condition (stock reaching your stop price) becomes true.

When you view it this way, you can get very creative with your orders, as most of the secret sauce contained in special order types takes place on your brokers servers. 

This means that if you can create scripts yourself, you can do basically anything that the exchange and broker rules permit, like buying at indicator values, selling when a stock increases by a certain percentage, etc.

[](/free-day-trading-class/)

[](/ultimate-beginner-day-trading-kit/)
