<!-- source: https://www.warriortrading.com/intermarket-sweep-order/ -->
<!-- lastmod: 2025-01-09 -->

# Intermarket Sweep Order (ISO) Explained

An Intermarket Sweep Order (ISO) is typically a large order that gets sent to several exchanges simultaneously for the purpose of quickly taking as much liquidity as possible.

The factor that divides the ISO from other order types is that it is exempt from the ‘trade-through’ aspect of the SEC’s Order Protection Rule (Rule 611) outlined in Regulation National Market System (NMS). 

This exemption enables traders using the ISO to take liquidity that is outside the posted best bid and offer.

Before we get into the technicalities and importance of the ISO, let’s roughly review the mechanics of the order. 

The ISO enables a trader to send an order to a market, sweep the inside quote, and then route the rest of the order to take liquidity from a given exchange. 

For example, let’s say you’re a hedge fund and you quickly want to buy 1,000 shares of a stock. The offer side of the order book is as follows: 

[](https://media.warriortrading.com/2022/01/25132311/ISO1.jpg)

You want the shares now, and you’re willing to pay up a few pennies. However, if you just send a [market order](https://www.warriortrading.com/market-order-definition/), by the time you’ve bought the 100 shares on ARCA and the 300 on BATS, HFTs will sniff out your game in a tiny fraction of a second.  

If they were quoting on EDGX, they’ll raise their quote, or alternatively, they’ll buy the shares on EDGX and then try to sell them to you a few cents higher. This might sound like ridiculous HFT boogie man speak, but ask an execution trader if their orders are being (legally) front-run by HFTs like this and the answer will be an unequivocal “yes.” 

The ISO provides a way around this. It is exempt from the ‘trade-through’ rule, meaning that ISO rule can trade directly with the EDGX order at a worse price if it pleases to, as long as it also sweeps the inside quote (the best offer on ARCA).

Here’s how that would work. 

If you routed an intermarket sweep order to buy 1,000 shares on EDGX, your broker would first purchase the 100 shares on ARCA (because remember, you have to sweep the inside quote), while simultaneously buying the other 900 shares on EDGX. 

This ensures that large institutional traders can access the liquidity they see on their screens. 

## How Intermarket Sweep Orders Were Created

Many unique order types are created as a result of or in spite of regulation. After all, exchanges have to follow the regulations set forth by the SEC and find ways to operate within them.

The rule that spawned the intermarket sweep order is Regulation National Market System (NMS). 

The SEC introduced Regulation NMS in June 2005, which is a set of rules for broker-dealers and exchanges to follow. It basically established the modern US equity market structure. 

One of the primary rules within Regulation NMS is the “best execution” rule, which protects investor orders from being mistreated by an exchange or broker-dealer in various ways. 

Within the ‘best execution’ rule, there is a trade-through provision which forces broker-dealers to get the best price for their customer orders. This typically means not trading at prices outside the inside quote or National Best Bid and Offer. The NBBO is simply what a trader would call the ‘bid/ask.’ If the highest bid is $10.00, your broker can’t sell your shares for $9.94. 

So the intermarket sweep order grew out of a need for institutional traders to make very large very quickly.

## Why Use Intermarket Sweep Orders?

Most retail traders will never use an intermarket sweep orders. Most of the time their orders are too small and their trading goals don’t align with what the order does. 

However, institutional traders love ISOs. In fact, according to a study called Clean Sweep: The Role of Intermarket Sweep Orders in the Regulation NMS Market, ISOs account for roughly 42% of shares traded in the US stock market, or at least at the time of the study’s publishing in 2012. 

The reason institutional traders utilize ISOs so much is because of costs. 

Or more specifically, the cost of not trading. Most institutional funds have mandates which force them to trade at specified times. So they need to access liquidity at a moment’s notice and are willing to pay for that. The same study said that institutional traders incur $8.9 billion a year as a result of trade execution failures. 

And using ISOs greatly increases the fill rate of institutional orders.

## How Some Traders Analyze Intermarket Sweep Orders for an Edge

Have you ever had an order resting on the book, outside of the inside quote, only to see an order fly by on the time & sales trade at a worse price than your order? That was almost certainly an ISO. 

And some time & sales data feeds provide a flag on transactions that use the intermarket sweep order designation, making it easy to identify when large institutional traders are desperate to find liquidity. 

The reason that some traders look for ISOs is because there’s real information within them. 

The Clean Sweep study we cited in the last section found that ISOs provide significantly more information content than the average order, as well as have a far greater price impact. In other words, clustering ISOs can indicate that a big short-term price move is coming. 

[](https://media.warriortrading.com/2022/01/25132321/ISO.png)

This is a figure from the study which quantifies the “information share” of intermarket sweep orders in the large cap stocks studied. I’ll spare you my hand-wavy explanation of the concept and [link you to the paper](https://www.bauer.uh.edu/rsusmel/phd/hasbrouck95.pdf) which minted information share. 

## Bottom Line

Many traders, especially in the options market, are paying more attention to the price impact of intermarket sweep orders and the trading opportunities they can present. 

Most traders will never use the order themselves, but understanding how it works, and why institutional traders use it allows you to understand how to take advantage of it. 

Find other traders that need to buy or sell, and hop on the train while it’s running. ISOs are one way to spot the footprints of the Fidelitys of the world.
