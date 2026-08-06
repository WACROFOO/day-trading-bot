<!-- source: https://www.warriortrading.com/options-pricing/ -->
<!-- lastmod: 2025-01-08 -->

# Options Pricing – How it Works

Figuring out the value of a stock or bond is a pretty straightforward problem. 

For [stocks](https://www.warriortrading.com/common-stock-definition-day-trading-terminology/), the price of the shares is directly tied to the underlying value of the company. 

Successful companies that project strong forward sales growth will be rewarded with a high valuation and rising share prices. 

For companies bogged down by poor sales, high debt, or murky legal situations, the valuation will be low and the price of the shares will reflect the poor performance. 

Bond pricing is even more simple – it’s just discounted cash flows. Sure, the formulas are a bit more complex than that, but it’s easy to create a simple heuristic for how stocks and bonds are priced. 

But when it comes to derivatives like options, the math gets a little more high level. 

Options are priced based on a variety of factors, but the main two components are value and time. Unlike a share of stock, the options contract has a set expiration – you can’t hold it forever like you (theoretically) could with an equity share. 

Options with similar strike prices but different expirations could have vast differences in their premiums. 

How does options pricing work? 

There are a couple different models, but all of them operate within the ‘value vs time’ framework.

## How Options Work

An options contract is an agreement between the buyer and writer. 

The buyer pays the premium for the contract and the writer agrees to sell the buyer 100 shares of a certain stock at a specific price (the strike price) at a specific date in the future (the expiration). 

The buyer has the right (but not the obligation) to purchase those shares at the contract’s expiration, but the option will only be exercised if the contract is ‘in the money’. 

Otherwise, the contract will expire worthless without being exercised. 

A put option is a bearish bet on a stock, while a call option is a bullish bet. An option buyer only risks losing their initial investment, which is the price of the premium. 

An option seller collects the premium from the buyer when the option is purchased, but could be on the hook for unlimited losses if the underlying share price melts up (for calls) or down (for puts).

## Options Pricing Models

The most crucial factors that make up options pricing are the underlying value of the stock, the time left to expiration, the volatility of the shares, and the strike price of the option. 

Dividend yield and interest rates also work their way into the equation. The most well-known options pricing formula was devised in 1973 by American economists Fisher Black and Myron Scholes. 

You can probably guess the name already.

### Black-Scholes Formula 

[](https://media.warriortrading.com/2020/09/10091909/Black-Sholes-Model.jpg)

Scholes won the Nobel Prize in Economics for his work on this options pricing model, which takes into account five major factors: 

- Strike price

- Underlying stock price

- Volatility

- Time to expiry

- Interest rates 

By combining these five factors together, the two economists developed an effective method for pricing derivatives. 

However, the Black-Scholes model does have several limitations. Since it assumes options are held to expiration, the formula works better for pricing European-style options than their American counterparts, which can be sold at any time before the expiry date. 

Additionally, the Black-Scholes formula puts a lot of weight behind the underlying stock price and may fail to properly value an option if volatility is currently having a greater effect on the option. 

### Binomial and Trinomial Pricing Models

The Black-Scholes model runs into trouble when attempting to accurately price American options, which can be exercised whenever the buyer chooses as long as it predates expiration. 

Other models try to account for this factor by assuming different probabilities of prices at different points in time using lattice-style pricing trees. 

The binomial pricing model comprises a pricing tree with two nodes: one assuming a price going up, another assuming a price going down. 

Attached to each of these nodes are two more nodes assuming an increase or decrease in price at a point closer to expiry than the previous iteration. Binomial models assume two possible paths: up or down. 

On the other hand, a trinomial pricing model incorporates a third node to the tree – one where price is constant. 

While all models have their flaws, binomial and trinomial pricing trees are better for determining the probabilities of American option values.

## Intrinsic vs Extrinsic Value 

Black-Scholes and binomial/trinomial pricing models all involve some heavy duty math and computer processing power. 

But thankfully, you don’t need to fully grasp all the variables in each formula to successfully trade options. All options pricing models can be whittled down to the competing forces of intrinsic value vs extrinsic value. 

Intrinsic value is the underlying stock price and its relationship to the strike price of the option. If a call option is ‘in the money’ (ITM) as expiration approaches, it will have more intrinsic value than a put option at the same strike price. 

To figure out the intrinsic value of a call option, subtract the strike price from the price of the underlying stock. For a put option, subtract the underlying stock price from the strike price. 

Note that only ITM options have instrinsic value. 

Extrinsic value is often referred to as time value. Since ‘out of the money’ (OTM) options have no instrinsic value, they must have extrinsic value due to the time left before expiration. 

An option writer sells this time value as the premium, which is the writer’s reward for undertaking the risk of delivering on the contract. The further an option is from expiration, the more time value it has and the higher the premium will be. 

If an options contract purchased for $10 rises to $12 despite the underlying stock not reaching the strike price (meaning the option is still OTM), the additional $2 is extrinsic value. 

Extrinsic value will decrease over time as the contract approaches expiration no matter what the underlying asset does. 

## Bottom Line 

Options pricing models are often complex formulas, but most traders won’t need to memorize them. 

However, an options trader does need to understand the factors that go into these formulas in order to properly manage risk. Options are risky derivatives, especially if you’re writing them instead of buying them. 

If it were as easy as picking whether a stock would go up or down, we wouldn’t need mathematical formulas, just a coin to flip. But the world of financial instruments is just never that simple.
