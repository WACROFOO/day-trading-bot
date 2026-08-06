<!-- source: https://www.warriortrading.com/payment-for-order-flow/ -->
<!-- lastmod: 2025-10-24 -->

# A Primer on Payment for Order Flow: Brokers Selling Orders to HFTs

## What is Payment for Order Flow?

Payment for order flow is when a third-party firm (usually a high-frequency trading firm) compensates a brokerage firm for first-access to their order flow.

For example, you enter an order to buy 100 shares of Apple stock in your TD Ameritrade account. You might think that order gets routed directly to a stock exchange to interact with the other active orders. But, a discount broker acts as a middleman between you and the stock exchange, and they don’t necessarily have to send your order directly to the exchange, and in fact, they rarely do.

Usually what they do is send the order to a high-frequency trading firm (referred to as a ‘wholesaler’) like Citadel Securities. Citadel then decides if they want to execute your trade or pass it on to the open market to get executed against existing quotes. 

This might sound horrifying, that they could give you any price and pocket a spread, but there are some protections that restrict this behavior.

Each brokerage firm is required to publish a quarterly report with information on their order routing practices, per [rule 606](https://www.ecfr.gov/cgi-bin/retrieveECFR?gp=1&ty=HTML&h=L&mc=true&r=SECTION&n=se17.4.242_1606) laid out by the Electronic Code of Federal Regulations.

## History of Payment for Order Flow

The practice actually started with Bernie Madoff before stock trades were decimalized. He’d pay the discount brokers to access orders before they were routed to the market in the same way the HFT firms do today. 

The start of this practice was actually hugely instrumental in the development of the discount brokerage industry, as the brokerages were able to use the fees that Madoff paid them to lower their commissions. 

As financial markets became more digitized, more automation entered the space, reducing the per-share price that wholesalers pay. Madoff predicted this in an interview with CNN Money in 2000. 

CNNfn.com: Will payment for order flow ever disappear?

Madoff: No. I think it will get lower and lower as the spreads get lower and lower with decimals. No one tells a firm how they can advertise. If I want to hire salesmen to generate order flow, no one is going to object. I don’t have them. So if I want to use Fidelity’s salesmen and pay part of my trading profits in the form of a rebate, why shouldn’t I be allowed to do it? It was characterized as this bribe and kickback and something sinister, which was very easy to do. But if your girlfriend goes to buy stockings at a supermarket, the racks that display those stockings are usually paid for by the company that manufactured the stockings. Order flow is an issue that attracted a lot of attention but is grossly overrated.

## Doesn’t It Promote Price Improvement?

One of the most common arguments in favor of payment for order flow is that it promotes price improvement. In other words, the theory is that the average trade is filled at a better price than the National Best Bid and Offer (NBBO). 

The counterpoint to this argument can be found in the UK. The United Kingdom’s financial authority banned the practice in 2012 and according to [Barron’s](https://www.barrons.com/articles/there-are-more-ways-to-trade-stocks-for-free-but-theres-a-catch-51569929400), “trades executed at the best-quoted prices jumped from 65% to more than 90% between 2010 and 2014, the CFA said in it’s paper.”

A [blog post by the CFA Institute](https://blogs.cfainstitute.org/marketintegrity/2014/12/18/hft-price-improvement-adverse-selection-an-expensive-way-to-get-tighter-spreads/) analyzed the price improvement argument levied by proponents of HFT and came to the conclusion that the benefits “may be a case of penny wise, pound foolish,” due to HFTs stepping in of the orders they interact with and the missed opportunities the practice causes.

Further, a whitepaper published on the SEC’s website by Dennis Dick argued that “price improvement” reduces market liquidity and widens bid-ask spreads. 

## How High-Frequency Firms Profit From Order Flow

Due to regulation NMS, third-parties who interact with client order flow must give you the National Best Bid and Offer, or better. This essentially requires them to give you the best publicly available price. This regulation’s existence gives credence to the “price improvement argument” we discussed above. 

HFTs can never fleece a retail order too bad. It’s more of a death by a thousand cuts.

### Retail Order Sentiment

The way HFTs are able to give you the NBBO and still profit is due to a number of factors. One is order bundling. If several clients at the same brokerage place a buy order on the same stock in the same period, wholesalers often bundle those orders into one. 

These bundled offers give them certain information about future short-term price movements. Because retail traders are generally less informed than their institutional counterparts, wholesalers will often take the opposite side of the trade, if the institutional flow is moving in that direction. 

### Latency Arbitrage

The next is through latency arbitrage. A study of the practice called [Dark Pool Reference Latency Arbitrage](http://ifrogs.org/PDF/CONF_2017/Aquilina_Foley_Oneill_Ruf_2017.pdf) defines the practice:

“In this new world, fast traders impose adverse selection costs on slower ones by acting on information signals faster than their competitors. These signals are not always clear, resulting in competition on interpreting information, as well as reacting to it (Budish et al., 2015). Where these signals are symmetrically interpretable, a race occurs on reaction times alone. These have been labeled ‘toxic arbitrage’ (Foucault et al., 2016) and ‘latency arbitrage’ (Bartlett and McCrary, 2016) and are argued to be harmful to liquidity in financial markets by increasing adverse selection to liquidity providers.”

Most of you have probably heard of [dark pools](https://www.warriortrading.com/dark-pool-definition-day-trading-terminology/), where institutions can make big trades without publicly advertising that information and reducing their market impact. Dark pools rely on lit markets to price their quotes, and HFTs are able to act on the latency between the change in the lit market best-quote and that of a dark pool. Through this, they perform arbitrage on their institutional dark pool counterparties

They can then use the wholesale inventory from dark pools to give retail order flow the NBBO price and still profit.

Due to latency arbitrage, some dark pools do their best to restrict high-frequency trading firms, but even those are [sometimes cannibalized](https://nypost.com/2018/09/14/citi-fined-for-exposing-dark-pool-clients-to-trading-sharks/) by HFTs.

### Other Market Making

Lots of the market making practices of HFT firms operate similarly to the way floor-based market makers used to. Offering liquidity on both sides of the bid-ask spread and attempting to make the spread as many times as possible. This market making activity doesn’t always involve predatory practices.

## How to Avoid Payment for Order Flow

The simplest way to avoid payment for order flow is to use a broker that doesn’t sell your order flow. Due to SEC regulations, brokers must disclose if they receive payment for order flow, and who they sell it to. 

Interactive Brokers is the only large discount brokerage firm aimed at active traders that don’t receive payment for order flow. Due to their business model aimed at more intelligent retail traders, receiving payment for order flow would alienate their clients. You can read their disclosure regarding payment for order flow [here](https://gdcdyn.interactivebrokers.com/Universal/servlet/Registration_v2.formSampleView?ad=order_routing_disclosure.html). 

When it comes to long-term investing, Vanguard has also taken a stance against selling their clients’ order flow for stocks and ETFs, but their tools are likely to be of little help to active traders. 

Another way to avoid having your orders sold to HFTs is to find a broker who will give you [direct market access](https://www.warriortrading.com/direct-access-routing-definition-day-trading-terminology/). This means that the broker won’t act as a middleman between you and the exchanges, and you can send your order through whichever route you please. Some examples of brokers who offer direct market access are Speedtrader, Centerpoint Securities, Lightspeed, TradeStation, and Interactive Brokers.

## How Much Are HFT Firms Paying Each Broker?

For various reasons, each brokerage firm gets different prices for their order flow from wholesalers. Among the biggest discount brokers; TD Ameritrade, E-Trade, Schwab, etc., their revenue per $1 million of the order flow executed is quite similar. Robinhood, on the other hand, receives more than 10x the rest of the industry.

Each US brokerage firm is required to file a 606 disclosure, which details who they sell their order flow to, and for what price. Here are some recent 606 disclosures for top brokerage firms:

- [Robinhood Financial 606 Report](https://cdn.robinhood.com/assets/robinhood/legal/RHF%20SEC%20Rule%20606%20and%20607%20Disclosure.pdf)

- [TD Ameritrade 606 Report](https://www.tdameritrade.com/retail-en_us/resources/pdf/AMTD2054.pdf)

- [E-Trade 606 Report](https://content.etrade.com/etrade/powerpage/pdf/OrderRouting11AC6.pdf)

- [Charles Schwab 606 Report](https://www.schwab.com/public/schwab/nn/legal_compliance/important_notices/order_routing.html)

According to a [scathing report from Logan Kane](https://seekingalpha.com/article/4205379-robinhood-making-millions-selling-millennial-customers-high-frequency-traders) in September 2018, Robinhood receives about $260 per $1 million in order flow they sell, compared to the roughly $22 per $1 million pocketed by the other discount brokers like TD Ameritrade and E-Trade.

There are likely several reasons for this. The first being that Robinhood is populated by the least informed novice traders. The Robinhood app is designed in such a way to gamify stock trading, to reduce as much of the friction present in placing a trade as possible. 

There are a few ways this is done. The first is that there is very little analytics present in the app. Simple line charts and some news headlines are basically all you’re going to get. The only information about your account is your equity curve and your positions. This simplifies things enough that the average untrained individual can get a grasp on it. 

The market order is the default order chosen, that’s because market orders are usually the most profitable for wholesalers, according to Dennis Dick, trader and member of the CFA Institute’s Capital Markets Policy Council. He likens market orders to writing a “blank check” to market makers. 

Dennis Dick also published a whitepaper on the SEC’s 

## TDAmeritrade Announces “Zero Commission” Trading

## Secrecy of High-Frequency Trading Firms

In VPRO’s 2011 documentary [Flash Crash 2010](https://www.youtube.com/watch?v=aq1Ln1UCoEU), a datacenter broker explained the secrecy behind these HFT firms:

Broker: “This is a big financial services firm, here.”

Reporter: “So no name on the door.”

Broker: “Nothing. You would never know what’s going on here, as you noticed it’s guarded, gated. There’s cameras everywhere. They probably know that we’re here right now. So in a period of time they’ll come out and say ‘what are you doing, stop doing that,’ type of thing, and if you rolled up and said ‘I’d like to come in,’ they would not let you in. And also no signage, so you don’t know whose facility this is, you don’t know what’s going on inside of it. You know, completely a nondescript building.”

Reporter: “No windows?”

Broker: “No windows. If this building has a problem, if this building is damaged, if anything happens to this building, they run the risk of not being able to execute trades. So they protect this, this is the heart and lifeblood of this business.”

These firms guard their trading secrets tightly, and for good reason. In 2012, [Citadel attempted](https://www.chicagotribune.com/business/ct-xpm-2012-12-07-ct-biz-1207-citadel-20121207-story.html) to prosecute an employee for downloading trade signal data onto an electronic storage device. It wasn’t the first time that happened either. A former programmer for Goldman Sachs was sentenced to eight years in prison for stealing HFT source code from the firm before the ruling was overturned. 

Some of the top firms buying retail order flow are:

- Citadel Securities

- Virtu Financial (ticker: VIRT)

- Two Sigma Securities

- G1 Execution Services

- Wolverine Securities

## Final Thoughts

The world of high-frequency trading is changing on an almost daily basis. For retail traders and investors on the outside, trying to track their movements in real-time is almost impossible. There’s some hope that the more predatory practices of these firms might be reduced through regulation, but until then, retail traders must adapt. 

To adapt, we have to accept that we generally have to pay the bid-ask spread. If we’re able to buy on the bid, that’s usually an indication that price is about to turn over to the downside (at least in the very short-term). 

Paying the spread necessitates extending the period in which we hold trades, as paying the spread in a scalping trading strategy will drastically reduce our profits. 

[](/free-day-trading-class/)

[](/ultimate-beginner-day-trading-kit/)
