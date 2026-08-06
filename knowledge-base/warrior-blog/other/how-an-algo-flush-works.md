<!-- source: https://www.warriortrading.com/how-an-algo-flush-works/ -->
<!-- lastmod: 2025-01-08 -->

# How an Algo Flush Works

What’s up? All right. Well, today, just before I was about to sign off and was finished trading for the day, we had pretty epic algo flush. And I thought this is a good opportunity to do an episode on how the algo flush works.

So, whether you’re a beginner trader or an experienced trader, these algo flush is where a stock drops like 10% in one second. It’s baffling. How does this happen? How’s the stock with, this one’s got 34 million shares of volume. How does it go from trading it in this case, $8.25 to just dropping to $7.40 and halting going down in two seconds.

How does that happen? And so to understand this, you have to understand market structure a little bit, and you have to understand the mechanics of how our orders are sent to the market. The market of courses is an island where it’s processing all the incoming orders from traders all around the world.

We also have to understand the role of market makers and high frequency trading algorithms. Now, I already did an episode, and this is a longer episode, it’s like an hour long, that was specifically getting into the detail of market structure, high frequency, trading algorithms, dark tools, and things like that so if you haven’t already checked out that video, I encourage you to do that.

I’ll put a link at the end of this video so you can watch that. You can watch this video and I think you’ll learn quite a bit about this algo flush and then if you want to keep learning more about how these market makers work and some of the tricks that they play, then you can check out that episode next.

So that’ll be at the end, it’ll be the next video to watch. So what ends up kind of happening here is this is a big part of the algo flush is these high frequency trading algorithms and the market makers. So first you sort of have to understand the role of the market maker in the market.

So when I am wanting to sell a stock, you know, let’s say I’m holding 10,000 shares of a stock, the second I press that sell button, I get filled, right? Now, it may not be the case that there was another trader out there in the world that wanted to buy that same exact stock at the price that I sold at and so who’s the intermediary? It’s a market maker. And so the market maker stands at the ready to buy shares from people who are selling and to sell shares to people who are buying.

And they profit from the spread between the stock. Now they also carry risk by holding by sort of, it’s kind of like a arbitrage because they’re holding for a very short period of time thinking that, okay, I’ll buy these shares from this guy,

Ross, but then I’m going to turn around and resell them a minute later to someone else who wants them or five minutes later or whatever it is so they’re just holding for very short periods of time, but what if all of a sudden, someone starts selling a hundred thousand shares, 200,000, 300,000 a million shares?

A market maker can’t just buy an infinite number of shares. If they do that, they become massively imbalanced in the risk that they have. When they’re providing the market for hundreds, thousands of different stocks, they have these risk models that they have to be, that they’re using to make sure their portfolio doesn’t become imbalanced.

And so they’re adjusting their bids and their offers in real time, based on what’s happening in the market. Of course, they’ve trained in the old days, it was actual market makers and specialists that were sitting at their computers or sitting on the exchange, making the market. Well, that’s not the case anymore.

Now that’s automated to these high frequency trading algorithms that essentially are doing the job instead of having a real person doing it in most cases. So what ends up happening here is, and this was the case with this stock, which we’ll show you when sort of get into the nitty gritty. What happened was someone put out a really big sell order, okay?

So that sell order was received and it was processed and now because all of these market makers subscribe to these incredibly data rich feeds from the exchanges, they see these big sell orders coming through, and now they’re going to start pulling their offers, right?

Because they don’t want to oversell the stock, right? Or in this case, they’re buying so they don’t want to over buy the stock. What if the stock is, you know, the company’s filed for bankruptcy? What if something really bad has happened? So part of their risk model is making sure that they don’t over buy or oversell, they have to maintain a balance on the position.

Ultimately, the best market maker is going to be able to buy and sell the same number of shares in one day, let’s say it’s a million shares and they profit from the spread. So, 10,000 shares a penny is a hundred bucks, a hundred thousand shares a penny is a thousand bucks, a million shares a penny is what, is $10,000, right? It just keeps going up. So, this is where that’s their goal, but that means the algo that they’ve employed needs to respond when there’s sudden surges in demand or in supply.

And so in this case, all of a sudden this big cell order comes in and so it gets filled probably with some slippage and then the person sends another order that was even bigger. And now the market makers have already started to pull their offers. So pulling, sorry, pulling the bids, and then that order gets filled even lower and now what starts to happen is this runaway cycle.

Now you’ve got panic sell. Now you’ve got some stop orders they’re firing, you’ve got some traders who are like, whoa, did this thing just drop 40 cents? And then that sort of triggers this immediate panic sell that goes right into the hall. And now in this case, because there was no actual news associated with it, it was just this algo flush, it’s ended up rallying back up to pretty much where it was before the flush.

So we’re going to get into it in a bit more detail. I’m going to show you the chart and if you’re interested in market structure and you want to learn a little bit more about how market makers work, how these high frequency trading algorithms work, then make sure you check out the episode at the end of this video. I think you’ll get a lot out of it. All right. So I hope you enjoy it and I’ll see you for the next episode.

All right, so let’s jump in and look at this algo flush. So PV this is a stock that is up 33%, it’s actually not up a whole lot, but it had a nice move yesterday and was very volatile yesterday. And it actually had a couple of these moves yesterday, but we just had one that I want to kind of highlight.

So the algo flush it’s when basically the stock is trading and then all of a sudden it feels like the bid disappears and… You get this flush and all of a sudden all these stop borders are firing, and then they’re hitting the bid and it sort of is this, it’s like self-fulfilling, accelerating sell off and then into a circuit breaker halt. If there weren’t circuit breaker halts, this could keep accelerating, but the circuit breaker halt stops it when it drops more than 10% within a period of five minutes.

So PV you know, was sort of trading fine today. I mean, a little choppy in a couple spots, there was a red candle here, red candle here, but generally it was pretty good, squeezes up to about 850, is pulling back, consolidating nothing really on the one minute, super alarming.

I mean, yes, it did have a false breakout right here, well kind of just a double top, you know? It tried to break this level, couldn’t break it so you’ve got a double top sort of higher red volume, you know, but again, nothing super, super crazy. And then all of a sudden it drops right here in a one minute candle from 828 to 740 boom, halts down. That’s a one minute candle. So now let’s zoom in on that one minute candle on this timeframe right here, we can look at a ten second chart.

So on a ten second chart, basically, it’s like this thing just instantly dropped right there. Let’s zoom it in one more time. Five second chart. So on a five second chart. Wow. That basically was like one candle. Let’s look at this on a one second chart. On a one second chart, what you’re going to see is that basically this thing just instantly dropped to eight first and then it went all the way to 747. It held there for a second and then it dropped lower.

So how does something like that happen? The stock was trading at 825, I mean, what’s the deal? And over on, of course, when you’re watching a stock trade, you could see the orders going through, you could see the prints going through. One of the things that some traders will do is they’ll and you can do this on think or swim very easily. You can filter the level two to show or filter the time in sales to just show you orders over a certain share size.

And so I’m going to show you this here, and this is small, but we’ll make it a little bit bigger. So this shows you, oops, sorry, where do we go? There we go, sorry. This shows you, we’ll zoom it back in. This is right in this candle and so what you see here, and I’ll just move this out of the way because it’s distracting is, there’s a buy order of 7,000 shares, whatever and then all of a sudden there’s a 30,000 share sell order at eight… It fills at 810. So think about that for a second.

The order fills at 810, which most likely means that someone pressed the sell button for 30,141 shares when it was trading at around 825. And what do we know about the way market makers and ECNs, how their high frequency trading algorithms, the way the algorithms match orders. What do they do when they see those big orders come in?

Now, if you’ve watched the video on the truth about high frequency trading algorithms and market makers, you already know all the details of this, but to summarize, what happens is that order is received, it starts to fill and then all of a sudden you’re going to see the bids start to get pulled and I mean, you would have to slow this down to like the nanosecond. It happened so fast. The bids start to get pulled order receives slippage. Then a second order’s executed for 38,925 shares at 801. A second big block order and it’s those big block orders like that, that all of a sudden now the market maker’s moving out of the way again and now as it’s moving out, flush, and that becomes that accelerating self-fulfilling prophecy.

So this is all around how, I mean, this is, I mean, this gets into the topic of how computers ultimately are kind of governing the price of stocks. Yes, individual traders, we’re adding liquidity to the market, we’re coming in, we’re pressing the buy button, we’re pressing the sell button and then there’s everything behind the scenes that’s matching those orders.

So all of that order matching. And what you know is that market makers provide liquidity. They sit on both the bid and the offer so when you have someone that comes in and hits the bid with a really big order, the market maker algo doesn’t know, you know, it cannot just absorb a million shares if someone just tries to sell a million shares on the bid, right? They can’t just buy an infinite number of shares so they are responding by moving their bids and moving their offers based on current market, based on the way their algo works.

And so when you have this moment where all of a sudden there’s a influx of selling, you get the algo flush. And so we call it this algo flush, I mean these are actual real orders that are going through, but it’s sort of fueled by the way the algo responds to these orders where you get this rug pull effect, and then you have stop orders that are firing, right? Stop orders fire.

They hit at market price, as market orders and then that fuels it even more. And the reason we need these circuit breaker halts is to prevent flash crashes because otherwise we would see just the snowballing accelerate. So on a stock like this, it instantly drops, you know, 10% and then that kind of stops the algo. It stops everything. Now the stock’s halted for five minutes. All right? So during that time, traders get a chance to kind of catch their bearings and then that’s when some traders say, “Well, wait a second. That was overdone.” And they come in, they buy the dip and then you get that, you know, sometimes you get the rally back up.

Now, if it had actual news that something terrible, you know, I don’t know an offering or something was happening, then it would probably continue lower and we would say that it was most likely an algo that received a high frequency trading algorithm that received the breaking news first and that was what created and began the selloff. But in this case, it may have very likely been a couple of really big orders.

Now, these are 30, 40,000 share orders. These are big orders that are going through and then a couple more go through here. It’s not clear that those are necessarily related to the same order, but those might just be other traders that hit the bit. So I don’t want to, I’m not going to go into all the details of high frequency trading algorithms and market makers.

If you guys are really interested in that, you want to learn more about that, you want to learn more about dark pull routing, then check out the other video I did on it. I think you’ll really enjoy it.

So I’ll put the link up here in the top corner, check out that video, the truth on market makers and high frequency trading algorithms.

This was a good example. You got the algo flush and you can also get algo spikes, it goes both ways. So learning how to sort of read the algo and understand how it works, I think is very helpful if you’re trying to trade actively in these markets. All right, so that’s it for me, check out that video and we’ll see you guys first thing tomorrow morning.
