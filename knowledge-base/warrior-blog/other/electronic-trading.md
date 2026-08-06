<!-- source: https://www.warriortrading.com/electronic-trading/ -->
<!-- lastmod: 2025-01-09 -->

# The Unlikely History of Electronic Trading

The stock market has been slowly turned to electronic trading since the 1980s, with staunch push back from the market’s two largest centers of power: the Nasdaq and the New York Stock Exchange. 

Today’s electronic trading market and all of its developments; decimalization, high-frequency trading, low commissions, and payment for order flow, can all be traced back to one unlikely place: a swanky day trading operation in the financial district: Datek Securities.

Last month, we talked about the [SOES bandits of the 1990s](https://www.warriortrading.com/soes-bandits/), and some of the key players from that era. Today they’re making a return because they played a key role in not only the electronification of today’s stock market but also played a key role in the development of [high-frequency trading](https://www.warriortrading.com/high-frequency-trading-definition-day-trading-terminology/). 

## Where It All Started: Datek Securities

Datek Securities sprouted up as a small broker-dealer after founder Schelly Maschler jumped ship from a shady penny stock operation called Russo Securities. With him, he took a sharp young programmer named Josh Levine.

Datek was mostly performing what was an archaic version of high-frequency trading. They would take advantage of uninformed order flow to make a quick buck. In their case, they were leveraging the SOES system to pick off slow market maker’s orders and quickly flip them.

Datek’s SOES trading became Levine’s canvas by which to free the markets from the stranglehold of the exchanges.

Unlike other young Wall Street interns of the era, Levine wasn’t after money or prestige. He had a singular goal: using computers to democratize financial markets. Throughout Levine’s career, he has consistently disregarded money in favor of democratizing markets. That meant working together with competitors and often, allowing others to take credit for his work.

Datek’s focus on [day trading](https://www.warriortrading.com/day-trading/), Maschler’s status as an outsider, and the firm’s muddied reputation due to their numerous NASD infractions, all made Datek an unlikely protagonist in the history of electronic trading. It was this Wall Street-party-crasher culture, however, that made Levine stick around to build technology that would change the stock market forever.

Soon, Levine had developed several pieces of revolutionary technology for Datek, which far surpassed that of the exchanges and even the big banks. Tools like Watcher, which was a day trading platform made for SOES bandits, Monster Key, which took advantage of little-known order routing rules, and most of all: the Island ECN, which revolutionized electronic trading.

## The Island ECN

Island was groundbreaking for electronic trading. It was the first venue completely dedicated to electronic, automatic trading. No human intervention was required. 

It was born out of two seemingly conflicting motives that shared the same goal. Josh Levine’s goal was rooted in the libertarian ideals of hacker culture. He wanted to open what he saw as a closed system by freeing the market from the exchanges’ death grip. On the other hand, you hand Maschler, Citron, and the rest of Datek: their motive was profit, but they were also happy to stick it to the exchanges.

For Levine, Datek’s trading operations were a perfect canvas by which to create trading technology. Seeing the problems they faced in real-time allowed Levine to get a grip on what needed to change about the market. 

### Colocation

Island was the first trading venue to implement colocation, the practice of placing a trading firm’s order routing system right to the trading venue’s computers to reduce the latency between sending an order to the market and the trading venue receiving the order.

Datek’s computers were set up directly next to Island’s server rack, with a direct link, ensuring the lowest routing latency possible. 

Today, colocation is one of the most controversial practices within the HFT space. Many criticize the practice because it gives HFT firms an unfair advantage. By locating their computers next to the stock exchange’s computers, they ensure they’re the fastest in the market.

Colocation is practiced by almost every trading venue in the United States. The exchanges lease space next to their computers so HFT firms can plug their computers in for a direct feed. 

Anyone who has played an online shooter game knows about the latency difference between having a direct link to a router versus a Wi-Fi connection. The HFT firms are the only players in the market with a direct connection, while everyone is else lagging around with a Wi-Fi connection.

[](https://media.warriortrading.com/2019/11/image2.jpg)

## The Maker/Taker Model

Nowadays, most exchanges have a system that provides incentives for providing and taking liquidity. NYSE Arca might offer you $0.003 per share in rebates when providing liquidity to their exchange, but charge you $0.003 per share to take liquidity from their exchange. The business model is meant to provide making markets (i.e. “maker”), and disincentive taking liquidity. 

Island was the exchange that started this practice. Initially, Island was charging customers $1 per trade they routed to the exchange. To attract the high-volume market-making firms of the time, Levine came up with this “maker-taker” business model to attract them. 

There were some unintended consequences to this, as it was the start of designing an exchange’s incentives to appeal to the highest volume players.

## HFT’s Dominance

HFT’s rise to dominance in US markets and beyond can be accurately summed up in one chart:

[](https://media.warriortrading.com/2019/11/image1.jpg)

While HFT has slightly declined since it’s heyday in 2009, the practice still accounts for roughly half of the US equity market’s trading. With such a daunting statistic, it’s difficult to quantify how much the structure of the stock market has changed in such a short period. 

Almost all market making activity (providing liquidity to capture the bid/ask spread) is done by HFT firms now, which has some positive and negative effects.

I think Sviatoslav Rosov put it well when he [called HFT](https://blogs.cfainstitute.org/marketintegrity/2014/12/18/hft-price-improvement-adverse-selection-an-expensive-way-to-get-tighter-spreads/) “an expensive way to get tighter spreads” in his article for the CFA Institute about HFT. Rosov goes into why the idea of HFT firms giving retail orders “price improvement” might be a predatory practice on the part of the HFTs. 

“For a retail order that gains $0.0001 in price improvement for 99 trades of 100 shares (with a 1-cent spread), that’s a 99-cent total gain from price improvement. But if the 100th trade is a limit order for the same 100 shares that do not get executed because internalizers are stepping in front of the trade, you would lose $1 because of the 1-cent spread on 100 shares you would have to pay in order to trade — wiping out the price improvement from the previous 99 trades! This example shows that tight spreads may not necessarily be economically significant.”

In layman’s terms, Rosov is saying that while it is true that HFT firms often fill your order at a better price than the NBBO, there are hidden costs to this, liking missing out on a trade. When you fail to get your order filled, you have to move your order up and pay the spread. These HFT firms “lean on your quote,” a/k/they use your intention to trade against you.

## The Tail Is Wagging the Dog

The SEC’s institution of [Order-Handling Rules](https://www.sec.gov/rules/sro/nd9821o.htm) was a death knell for human market makers. The regulations mandated that exchanges display and honor quotes from ECNs. The immediate result: tighter spreads, increased market liquidity, and more trading venues for investors to choose from. But, like many well-intentioned regulations, the Order-Handling Rules had some unintended consequences.

This created an environment where the non-profit exchanges were forced to compete with ECNs. ECNs typically make money by charging per share traded, so their incentive is to produce as much volume as possible. Further, the best way to get traders to use an ECN is to be highly liquid. And who does the most volume and provides the most liquidity? High-frequency traders.

With new competition springing up every day, it was a race to the bottom and the only way to stay ahead was to cater to HFTs. 

As a result, HFTs became the target client of all ECNs, each offering HFTs volume discounts and unique insight into the inner-workings of the ECN to retain their business. Because HFTs controlled the most volume and liquidity, they had a strong say in how the ECNs were run.

There were some questionable conflicts of interest as this new ECN industry grew. HFT firms hold investments in many ECNs, and some were even founded by the founders of large HFT firms. 

## Consolidated Audit Trail: Sniffing Out Predatory HFT Practices?

For those that view HFT firms as the boogeymen of markets, you might be happy to hear that the SEC is currently working on implementing a new system called the Consolidated Audit Trail (CAT). The CAT intends to track orders from their initial routing to execution, to sniff out illegal trading practices. 

Up until now, the SEC has been blind. HFT firms have such strong technology that enables them to send countless orders per second that it becomes almost impossible for the SEC to track it all.

The SEC put it this way on the [CAT website](https://www.catnmsplan.com/):

“The Consolidated Audit Trail will track orders throughout their life cycle and identify the broker-dealers handling them, thus allowing regulators to more efficiently track activity in Eligible Securities throughout the U.S. markets.”

## Final Thoughts – Electronic Trading

The history of electronic trading began with noble causes, to democratize financial markets, to remove the need for a middleman in markets, whether that middleman is an NYSE specialist or an internalizer like Citadel. While Levine’s vision has partly come to fruition, it’s doubtful that he predicted what has come of today’s markets.

One way to look at it is this: in the markets, there will always be someone trying to make a buck off of your order. Whether it’s market makers on the floor not honoring their quotes or hanging up the phone on small retail traders, or if it’s an HFT firm leaning on your quote, there’s always someone there trying to take advantage of you. It’s the very nature of financial markets.
