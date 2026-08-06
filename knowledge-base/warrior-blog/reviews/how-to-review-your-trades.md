<!-- source: https://www.warriortrading.com/how-to-review-your-trades/ -->
<!-- lastmod: 2025-01-08 -->

# How To Review Your Trades Effectively

You make trades in the moment. 

Ideally, you’re in a ‘flow’ state and not thinking too much about technical details, and applying your training and reviewing later. 

Think about professional fighters. They don’t think through each punch and slip during the fight. The thinking is done in their training, and then they review how they applied their training, and what can be changed about the training after the fight. 

While us traders are sitting at a keyboard clicking buttons and not in a steel cage, we should treat our trading performance with the same respect that high-level athletes and performers do, because our hard-earned money is on the line. 

And one of the key ways to continually improve and iterate on our trading is to review our past trades and trading performance as a whole. Because you won’t notice the mistakes in the moment. And you can’t take a big picture view when you’re focusing on the micro aspects of each trade.

Trading isn’t the time to reflect on your trade setups or to consider changing your stop losses and profit targets. It’s the post-trade analysis, when you’re not in performance-mode, and when your view isn’t colored by the emotions of the trade. 

For that reason, in this article we’re going to talk about how to review your trades effectively. 

It’s not enough just to look at your trades and marvel at the greatness of that runner you caught, or repeat some trading psychology quotes when examining your trading mistakes. 

Just like placing and managing trades, you should have a thought-out process for reviewing trades. 

## Part One: Managing Your Trade Data and History

In many ways, the finance and trading world, at least at the lower levels, is at least a decade behind technology-wise. 

Popular trading platforms like ThinkOrSwim or IBKR TWS still don’t have efficient ways to format your trade data and review trades in the box. We’re left to export our trade history into a spreadsheet and figure it out for ourselves. 

If you’re lucky enough to have a provider that formats your trading data in such a way where you can review key metrics like your Sharpe ratio, profit factor, average win/loss, etc., (TradeStation is pretty solid at this), then you can skip to the next section.

For the rest of you, be willing to either change your trading platform/broker, or to invest time or money in a trade review solution.

## Out of the Box Trade Review Services

There’s a number of services that connect directly to your brokerage accounts and read your statements, or show you how to upload your brokerage statements in the correct format. 

From there, they format all of the data in a fashion that is meaningful to traders. 

Here’s a few of those services and their current pricing:

- [TraderVue](https://www.warriortrading.com/tradervue-trading-journal-review/): from $30 to $50/month 

- EdgeWonk: $170/year

- TraderSync: from $30 to $80/month

- Trademetria: $20 or $30/month 

Each of these services perform the same basic function: formatting your trade history into a series of tables, charts, and graphs, as well as calculating vital statistics like Sharpe ratio and profit factor over your entire trade history. 

They each have their own special sauce as far as their design and formatting goes, but for all intents and purposes, they’re all quite similar. 

Most of them have free versions or free trials so test a few out and pick your favorite. 

## Creating Your Own Solution

Like I said, if your platform or broker doesn’t provide you the post-trade analytics that you need, you’re going to have to invest either time or money. If you’re frugal or looking for a fun project, there’s plenty of ways to do this yourself. 

The most basic method would be to build a spreadsheet with the inputs you desire and manually enter each trade. 

This is fine if you’re a swing trader who makes a few trades per week but highly active day traders will see their they have a lot of inputs. 

Manually updating the sheet has the added benefit of keeping you more in touch with your trades. 

Whereas with the automated paid services, you can quickly import that week’s trades and glance at your top-level indicators like your equity curve and profit factor and call it a day. 

While this isn’t a trade review process, it’s easy to allow an initially disciplined process to become a “check-off the box” activity, and manually entering your trades is one way to interrupt that pattern. 

You can get more advanced and semi-automated when you integrate Excel’s [index match](https://corporatefinanceinstitute.com/resources/excel/study/index-match-formula-excel/) function. 

If you’re a Python guy, Quantopian created a great library called Pyfolio which in many ways, does what the sites like TraderVue does.

 It’ll take some bodging around to get your broker’s statements to agree with Pyfolio, but again, this is the solution that takes a time investment rather than a monetary investment. 

## Step Two: Big Picture Review

Continuing on with our fight analogy, this is where we review the top-level statistics of the fight(s). Who landed more strikes? Who spent more time in control?

By now, you have your trade history formatted to easily analyze your trades both from an individual and big picture perspective. 

We’ll start by reviewing our trading performance from the 30,000 foot view using some key performance indicators that show us how we’re doing in our trading overall. 

Here are the key performance indicators to pay attention to:

- Profit Factor: This is essentially your realized reward risk ratio. If you have a profit factor of two, that means your total gross profits are two times higher than your total gross losses.

- Sharpe Ratio: the Sharpe Ratio puts your returns in context by putting a yardstick on your returns in relation to how much risk you take to achieve said returns. The higher your Sharpe Ratio, the better your strategy. You could have a strategy that only returns 4% a year with a very high (>2) Sharpe Ratio because it takes so little risk to earn that 5% so you could theoretically leverage that strategy to earn better returns, while a strategy that returns 100% could have a poor Sharpe Ratio (<1) because it takes so much risk (measured in volatility) to achieve said returns.

- Equity Curve: the equity curve is essentially a chart of your running account balance. There’s no complexity to it, anyone should be able to take one look at your equity curve and see if you’re trading well or poorly.

There’s several more metrics to pay attention to, and you could make the argument that the Sortino Ratio is better at evaluating the performance of short-term trading strategies, but the vast majority of platforms have the above three metrics built-in, so let’s keep it simple. 

Let’s start with the equity curve, which is essentially your rolling P&L over time. 

Of course you want to see this steadily going up but that won’t always be the case and isn’t necessarily indicative poor trading. 

We all go through extended bad runs and have the occasional large, unavoidable loss (like when a stock gaps through your stop), but in the long-term we’d like to see a smooth upward trend line.

Here are some key factors to consider when analyzing your trading equity curve: 

- Trading Style

- Long-term trend

- More Strategies?

- Profit Factor

## Your Trading Style

Experienced options traders will tell you that the P&L of most trading strategies emulates either a short-volatility strategy (frequent small wins, infrequent massive losses), or a long volatility strategy (frequent small losses, infrequent massive gains). 

So if you’re unfamiliar with the typical payoff profile of the strategy you’re trading, your post-trade analysis will be ineffective. If your strategy is very similar to selling volatility, you might fool yourself into thinking that you’re a trading genius when you see that your win-rate is north of 75%, only to be surprised by a huge loss. 

You can’t know if your implementation is successful if you don’t have some baseline expectations to measure your performance against.

So, yes, of course you want your P&L to smoothly trend upwards, but you also want to know the “shape” of your equity curve, in terms of how smooth or jagged it should be, whether or not you should expect upward/downward spikes, etc.

## Your Long-Term Trend

This is where you can employ tools like moving averages or a trendline. If over a large sample of trades, you’re going sideways or trending downwards, you should re-evaluate your trading strategy, or consider whether you’re actually following your strategy.

Every strategy is different and no strategy is optimal in all trading environments. 

For example, if you trade a mean reversion style like pairs trading, you might sit through some sideways periods for several months, waiting for your trades to mean revert. This doesn’t mean that it’s time to change strategies, this is just a fact of life for most conventional trading strategies. 

## Should You Implement More Strategies?

If you only trade one style, like short volatility, or [pairs trading](https://www.warriortrading.com/pairs-trading/), you’re going to sit through some long equity drawdowns when the market regime doesn’t match this style. 

If you like keeping it simple and can handle the drawdowns, it’s completely fine to just grit your teeth and sit through the drawdown. 

However, many traders opt to manage a portfolio of different strategies to smooth out the drawdowns. 

For example, if you typically trade a simple equity momentum strategy, you might choose to supplement that strategy with some mean reversion trading, because typically when a momentum strategy goes out of favor, the mean reversion-type strategies come into favor.

This is especially important if you trade for a living and need somewhat consistent income from trading, but it can never be forced. 

Consider how long it took you to tweak and ‘perfect’ your current trading strategy. 

Now imagine developing a completely new strategy contrary to your current style, all the while managing and optimizing your current strategy. It’s not a trivial feat for casual, part-time traders.

## Your Rolling Profit Factor

“If you torture the data long enough, it will confess.” – Ronald H. Coase 

The profit factor basically calculates our realized reward/risk ratio. A profit factor of 1 means that you break even on the average trade. 

Most post-trade analysis software will display your profit factor as a static number, representing your profit factor over your entire trading history. 

This is useful, but it doesn’t tell us how we’re improving, and if you’ve significantly altered your trading style over time, this metric is useless. 

Instead, you should view your profit factor as a rolling number, over perhaps the previous 50 trades. 

This way, you can see how your trading efficiency evolves over time. This too, shouldn’t be viewed with too much granularity, as all strategies go through tough periods. 

## Sharpe Ratio: Are You Doing Useless Work?

The [Sharpe Ratio](https://www.warriortrading.com/sharpe-ratio-definition-day-trading-terminology/) is a mathematical formula created by William F. Sharpe, also co-creator of the famous Capital Asset Pricing Model (CAPM). 

The Sharpe Ratio is used to evaluate investments, or investment strategies in comparison to each other. As stated earlier, many times a strategy with very low returns can be more ‘efficient’ than a strategy with very high returns because you’re getting more returns per unit of risk.

According to conventional financial economics, it’d be better to leverage up the low-return, high Sharpe strategy, than to utilize the high-return, low Sharpe strategy. 

When studying your own trading strategies, I like to think like a wealthy hedge fund investor. 

You have all of these famous hedge funds to pick from. Some of them are bespoke strategies with a famous manager at the helm. Others are fine-tuned ‘off-the-shelf’ strategies which don’t have much special sauce, but a well-defined historic risk and return profile. 

If a custom, ‘special sauce’ strategy takes work in the form of manual trade execution, research, emotional/psychological discipline, etc., leading the hedge fund to charge high fees, and has a Sharpe Ratio of 0.8 over the past five years, but the Hypothetical Passive Stock 100 Index has a Sharpe of 1.0, why pay the high fees? 

Just throw the money in an index fund or find a better strategy. 

When viewing trading strategies from this point of view, you get out of that all-too-familiar trading tunnel vision where you’re just focusing on your equity curve going up. 

Sure, you might be making consistent money from trading, but if a zero-effort strategy makes the same or more while taking less risk, you’re actually trading poorly because you’re not maximizing your return per unit of risk. 

## Step 3: Individual Trade Review

Now we get to reviewing individual trades. 

Continuing with the fight analogy, if the big picture review looks at factors like how many significant strikes are thrown, how much time is spent in dominant positions, etc., this is where you break down individual exchanges with your opponents while taking your strategy into consideration. 

If you’re a counter-puncher, this is where we break down how you responded to opportunities to counter your opponents. 

The individual trade review is not the area where you should be focused on auditing your entire strategy, but instead evaluating your implementation of said strategy. 

The big picture review is the place for strategy evaluation. So don’t switch your strategy off a few individual trade reviews, let the rolling top-level metrics tell that story. 

However, the right insights can be priceless for you. To maximize the value of this process, you should be taking notes inside of your analysis platform. Most of the popular platforms that I’m familiar with have the ability to do this

Before we move on, we have to keep in mind how strong our hindsight bias will be throughout this process. Be careful reading too far into any insights you make here. When you know the future, you’re a genius compared to your past self. 

I like to follow a checklist process. 

Here are some criteria to consider:

- Which setup did this fall into, if any?

- What were my initial goals with this trade?

- What was the market environment like at the time of the trade?

- Did I follow my basic entry and exit rules?

- Trying to discount my ability to see the future, should I have taken this trade?

- Did I miss anything? Were there legitimate warning signs that I should have avoided?

- Scaling in/out: were there better opportunities to take a piece off or add to the trade? Did I scale in/out according to my own guidelines?

## The Basics

- Did you carry out the bare necessities of the trade?

- Did I have a stop loss sitting in the market?

- Did I override any of my rules? Why?

- Was I in the right state of mind to be trading?

## What Was the Trade Setup?

 Which setup criteria did this trade meet originally? You should be able to identify it just by looking at the chart without trying to remember. With the benefit of hindsight, did this trade fully meet this setup’s criteria?

While many traders have concrete quantitative criteria like “20-day average crosses 50-day average and Indicator X > Y,” but for those of you that trade more based off intuition, scroll your chart back to the point where you initiated the trade, so that you’re only seeing information you had at the time of the trade. 

Would you take the trade again if you didn’t know the outcome?  

## What Were My Goals For This Trade?

There are some truly excellent traders out there that see something in the chart or order flow that we don’t. 

They hit a hotkey and within seconds they have a massive position. Seconds or minutes later, they hit the hotkey again and they’re out. They can’t fully explain what happened, but they make boatloads of money and don’t owe any of us an explanation. 

But unless you have the skills of that guy, don’t try to emulate him. For each trade, we should have some pretty tangible goals for the trade. 

That could be a technical indicator or price reaching a point, or the trade simply earning a multiple of your initial risk. These are crutches that not only let us turn on autopilot and not think about where to exit, but it lets us look back later and evaluate the performance of those parameters. 

Compare your goals to your outcomes. It’s no problem to have a losing trade, but consider both how realistic your goals are in the space of this individual trade, and if you fulfilled your goals on the trade. Did you make the best of this trade, given your goals? 

## The Market Environment

The S&P 500’s performance and which sector and sub-industries are hot drive the behavior of nearly all equity traders. Odd behavior in one trade might be logically explained by that day/week’s broad market environment.

Given the prevailing market dynamics at that time, does your trading make more or less sense? 

Did you fail to adapt to a change in the short-term market regime? Were you trying to trade counter-trend on a strong trend day? Or were you forcing trend days on a choppy range day? 

## How Did I Scale In/Out?

One of the biggest plagues of trend traders is that they reach a huge P&L high, only for the stock to come off that extreme high (low), and you feel dumb for not selling into the strength. 

And there’s no right answer to this. Some choose to live with the reversals in the hopes for tremendous runaway trend trades. Others look for more stability and seek out places to take partial profits in these situations. 

As we’ve discussed earlier, this is the type of decision that you should have made already. In each trade review, consider the implications of this decision on the trade.

If you do scale out of trend trades, consider how your specific exit methodology is working on the trade where the trend quickly reverses on you. Are you frequently getting the opportunity to take partial profits? 

## Bottom Line

At this point, you should have a good idea of where your trading is at.

 It’s so healthy for your trading to make performance review a ritual, whether that’s weekly for day traders, or perhaps monthly for swing traders. 

This isn’t a homework assignment, so you get no credit for doing it halfheartedly, that’s just wasting your own time.

Without going back and reviewing your trades, you could be repeating errors that compound to slowly degrade your trading performance over time.
