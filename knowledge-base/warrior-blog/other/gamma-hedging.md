<!-- source: https://www.warriortrading.com/gamma-hedging/ -->
<!-- lastmod: 2025-01-08 -->

# What Is Gamma Hedging and Why Is Everyone Talking About It?

Gamma hedging has been in the headlines a lot lately, but what is it exactly?

## Intro

The rise of Robinhooders and growth of retail options trading after COVID sparked a cottage industry of traders and analysts who analyze options market order flow to decipher how options market makers are positioned and take advantage of their semi-predictable trading patterns. 

Gamma, which is a factor in options pricing that drives hedging flow from option market makers, has emerged as the most important analytic these folks are using to drive their trading decisions. 

Before we get into what’s going on, if it’s just a fad or the real deal, and how we can understand it ourselves, we have to define basic things like what gamma is, why it’s important and so on. 

## What is Gamma?

Options are contracts with non-linear payoff profiles. When you buy a stock for $10 and it goes down to $9, you lose a dollar, vice versa on the upside. It’s linear. 

The payoff of an options position can vary dramatically based on a number of factors, making it so that a call option might only increase in value a little bit when the underlying stock goes from $10 to $11, but considerably appreciate in value when the stock goes from $11 to $12, hence, non-linear payoffs. 

To understand the more hazy payoff profile of options contracts, some very smart people came up with a number of factors making it possible to mathematically derive the “fair value” of an option with relative ease. The best-known formula for this is the Black-Scholes model and  you’ve probably heard of it. 

These factors are:

- Stock price

- Strike price

- Stock volatility

- Time until the option expires

- Funding rate

- Dividend rate

If you figure out these statistics, you can value an option contract with a simple calculator like [this one](https://goodcalculators.com/black-scholes-calculator/). However, that only helps us right now, because how can we know how the price of this option contract will evolve with the passage of time and the movement of the underlying stock? The Greeks. 

The Greeks are basically statistics that tell you how the value of your option contract will evolve as other things change–like the volatility of the stock, the passage of time, the change in stock price, the change in funding rates, etc. You should have a working understanding of how these factors work, as you can’t understand one without the rest. They’re intimidating but ultimately they’re just fancy names for concepts that are easy to grasp. [This Schwab article](https://www.schwab.com/resource-center/insights/content/how-to-understand-options-greeks) does a great job at breaking things down simply. 

The all important Greeks for us to focus on today are Delta and Gamma. Delta is essentially how sensitive an options contract is to changes in the price of a stock and luckily it’s very easy to grasp. 

 If the Delta of your option contract (nearly all options trading platforms will have this information) is 0.30, then for every $1 that the stock price moves, your option contract will change roughly $0.30 in price in the corresponding direction. 

But delta changes over time. For example, if you own a $10 call option on a stock that has a Delta of maybe 0.50, but then the stock price drops to $5, you’d find that the Delta would change from 0.50 to something in the single digits.

The rate at which Delta changes is known as Gamma. Gamma is essentially the numerical reading of how many shares it will take to adjust a delta hedge per 1% move in a stock. So if you own a .50 Delta option with a Gamma of 2, that means a 1% move in the stock would change the Delta by .02, requiring you to adjust your delta hedge by 2 shares. 

## Why Gamma Is Important to Option Market Makers

Options market makers, we’ll call them for dealers throughout, are essentially arbitrageurs. They make money by buying slightly below fair value and selling slightly above fair value. They do this many times over and over again and make a profit over a large number of trades. 

But it’s vitally important that option dealers reduce their market risk. When they sell you an AAPL call, they’re not trying to make a bearish bet on AAPL stock price, they’re selling you an option for a hair more than it’s worth.

So to neutralize their market risk they have to hedge. And they do this by trading the underlying stock–otherwise known as delta hedging.

Delta hedging is simple. Remember, an option’s delta is the multiple of which an option price will move for each respective $1 move in the underlying stock. So to eliminate that delta risk, you delta hedge. So if the delta of a call option is 0.50 and you sell the option, you can delta hedge that trade by buying 50 shares of the underlying stock per contract you sold. 

So great, now your only risk is in the volatility aspect of the option price. But issues quickly arise. You wake up and the underlying stock has moved, which moves the price of your option. Now your option is 0.80 Delta, to remain hedged, you must buy another 30 shares of stock. 

When this sort of thing happens really fast in one direction, we call it a “gamma squeeze,” because option dealers are all forced to pile into one side of the trade because they’re being forced to adjust their delta hedges. 

Basically, retail traders tend to buy calls and option dealers take the other side of most of those trades. This means that dealers tend to be perpetually short options, and in turn, short gamma. As the price of the stock goes up, they have to buy more shares to adjust their delta hedge. As more traders buy calls, dealers have to buy more shares, creating a positive feedback loop.

## How Traders Look for Gamma Squeezes

By now you should have a rough understanding of how and why a gamma squeeze occurs; option dealers are essentially “short gamma,” which means they’re short a bunch of options and have to continually adjust their hedges as the underlying price moves.

I’m sure you’ve heard all about gamma squeezes in the context of meme stocks like GameStop (GME), AMC (AMC), and so on.

To be clear, many traders will rely on fancy labels like “gamma squeeze” and “option dealer hedging mechanics” to explain a price move when oftentimes stock prices are just moving because of supply/demand imbalances.

However, there are times when the trading activity of option dealers has a disproportionate and convex activity on stock prices. In those cases, smart options traders have staked this out beforehand and will position themselves advantageously. 

While most traders utilize some sort of software to analyze options data like SpotGamma, you can spot some of the basic “red flags” of a potential gamma squeeze through a few simple factors: 

- Much higher than normal options volume. There needs to be outsized activity for dealer hedging to have a big impact on prices

- Specific near-the-money strikes have very high volume and very high gamma, meaning that traders are buying the options aggressively and dealers are heavily short these strikes. Their high gamma level means that dealers will have to constantly readjust their hedges and trading activity will go up, creating potential for a gamma squeeze

- Elevated near-term implied volatility

- Cost of options contracts aren’t massively prohibited to retail traders. (Typically meaning an underlying price <$50)

Beyond simply playing for a short squeeze, just being cogniscent of the most significant strikes where lots of dealer activity is concentrated can help you spot potentially important support and resistance zones which will contain tons of dealer trading and help you pick better entry and exit points. 

## Bottom Line

The options market has changed substantially since the COVID bottom and the entry of retail traders buying tons of calls is hugely responsible. The data coming out of retail brokers in terms of how many of their customers are trading options compared to prior years is astounding and the volume data from options exchanges confirms this. 

Even the members of WallStreetBets are well aware of the effects their trading has on option dealers and they even try to orchestrate gamma squeezes on the forums nowadays, just as they did in early 2021 with the short squeezes in GameStop and AMC. 

The trading activity of option dealers is highly important but just as any potential trading edge, it’s always harder in implementation than theory and the best examples are always cherry-picked.
