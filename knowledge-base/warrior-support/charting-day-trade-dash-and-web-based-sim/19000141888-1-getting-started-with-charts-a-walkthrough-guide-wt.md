<!-- source: https://support.warriortrading.com/support/solutions/articles/19000141888-1-getting-started-with-charts-a-walkthrough-guide-wt -->
<!-- category: Using the Warrior Trading Platform (Day Trade Dash, Community, and Simulator) -->
<!-- folder: Charting (Day Trade Dash and Web-Based Sim) -->
<!-- modified: Wed, Oct 8, 2025 at 11:04 AM -->

# 1. Getting Started with Charts: A Walkthrough Guide | WT

This article talks about:

- [How to Access Charting](#How-to-Access-Charting)
- [How to Use the Charting Platform - General Walkthrough](#How-to-Use-the-Charting-Platform---General-Walkthrough)
- [Markets, Data, and Hours Available](#Markets,-Data,-and-Hours-Available)
[How Market Data is Interpreted](#How-Market-Data-is-Interpreted)
- [How Warrior Trading Charts Compare to TradingView](#How-Warrior-Trading-Charts-Compare-to-TradingView)
- [Additional Information](#Additional-Information)

### How to Access Charting

To access our charting platform, you must:

- Have an active tools subscription with charting access (members can add charts via the [](https://www.warriortrading.com/member-renewal-information/)[Renewal Information & Chat Room Tools page](https://www.warriortrading.com/member-renewal-information/)), and
- Use a system that meets [the minimum system specifications specified here](https://support.warriortrading.com/support/solutions/articles/19000106183).

Members with charting access can open the software by following the steps below:

- Sign into the live trading room platform ([click here for detailed steps](https://support.warriortrading.com/support/solutions/articles/19000024073-signing-into-our-live-trading-and-chat-room-wt))[](https://support.daytradedash.ai/support/solutions/articles/19000137605-signing-into-our-live-trading-and-chat-room-dtd)
- In the platform, click the Charting button that appears on the bottom left-hand side under Tools. This will add a new chart widget to your chatroom window.
[image]

- If you receive a message indicating that you need to sign the market data agreements, follow the prompts to [activate or reactivate live market data](https://support.warriortrading.com/support/solutions/articles/19000118834-how-to-sign-market-data-agreements-for-scanners-wt), and then sign out and back into the live trading room platform.

Mobile users, please [read about the mobile experience here](https://support.warriortrading.com/support/solutions/articles/19000128467-mobile-experience-warrior-trading-chat-room-wt), and keep in mind that:

- Only one window or chart can be used at one time.
- Your chart widget will have full capabilities besides color window linking.

### How to Use the Charting Platform - General Walkthrough

The video below is a demo of our charting platform and features. For more details about the individual features of the platform, please be sure to also review [other support articles](https://support.warriortrading.com/support/solutions/folders/19000171870).

Tip: Most features and icons will display more information if you hover over it for more than 2 seconds.
There is also a new search feature that can help you search for drawing tools and functions. Look for the traditional search icon with a lightning bolt (see the below screenshot) to access this feature. 
[image]

### Markets, Data, and Hours Available

Charting is available 24/7. However, live market data from the exchanges is only available from 4 am EST to 8 pm EST.

Our charting software includes all US Equities and ETF level one data:

- NYSE Level 1- Tape A
- Amex Level 1 - Tape B
- Nasdaq Level 1- Tape C
It does not include the following:

- Level two data
- Forex
- Futures
- Crypto
- Non-US exchange data

#### How Market Data is Interpreted

When it comes to market data for trading, Ross understands that he needs to have the best and fastest data available to help get an edge in the market. At times, it is still possible to see slight differences across vendors when it comes to price and volume data. You should even expect it when subscribing to the same data sources across platforms. That doesn’t mean either source is wrong; it usually reflects different data subscriptions and/or processing choices. Here are the main factors:

- Venue coverage (composite vs. primary-only)
Some vendors show only the primary exchange’s volume; others show consolidated/composite volume across all lit exchanges plus off‑exchange venues (e.g., FINRA TRFs). 
- Including or excluding off‑exchange activity is often the biggest source of variance.
- Session scope
Inclusion of pre‑market (typically 4:00 to 9:30 ET) and after‑hours (typically 16:00 to 20:00 ET) prints differs by vendor. If one source shows “regular session only” and another includes extended hours, totals will not match.
- Trade eligibility and condition code filtering
Vendors apply different filters to trade condition codes (like non‑price‑forming, out‑of‑sequence, derivative/benchmark prints, odd‑lots). 
For example, including odd‑lots or certain non‑regular trades will lift volume versus a feed that excludes them.
- Non-price forming data is any trade less than 100 shares. We do not count that as price data for our charts.
- Late reports, cancellations, and corrections
Exchanges and trade reporting facilities submit late prints and corrections throughout the day, and vendors might delay or batch them. We currently disregard any data 20 seconds or older. This is very important for using our scanners. This is why some intraday totals can diverge and converge later, sometimes only after official end‑of‑day publication.
- Aggregation methodology
Differences in bar building (tick‑by‑tick vs. conflated updates), minute boundary definitions, de‑duplication logic, and how “as‑of” trades are dated can create small discrepancies, especially intraday.
We use tick-by-tick data
- Feed mix and latency
Using SIP (consolidated) vs. direct exchange feeds, and the timing/sequence in which messages arrive and are processed, can briefly skew day‑to‑date volume until all messages are reconciled.
In summary, it will be very hard to know for sure the exact reason why another data provider had different data from hours unless we were able to know: composite vs primary‑only; regular‑hours vs full day; whether they include auctions, odd‑lots, and off‑exchange prints; and how they treat late prints/corrections. As it is very possible that the data we can get may be slightly delayed or timestamped to a previous time, depending on when the data is received.

### How Warrior Trading Charts Compare to TradingView

Warrior Trading charts are based on TradingView’s software, a popular third-party service that offers a full suite of charting tools and features to help users analyze and trade the markets. To provide our members with a great experience, we have tailored features of this existing software to meet the standards, requests, and expectations of our members. 

Our members can use our charts within the same browser window as our chatroom and popular scanners, stock quotes, news, and watchlist widgets. This helps reduce the number of separate platforms, apps, and market data subscriptions that traders need.

Our charts offer a mix of features that are available to Pro+ and Premium members at TradingView. Key features included are:

- Unlimited charts per browser window
- Unlimited indicators per chart
- Up to 6 windows per chatroom layout
- Real-time US market data for sub-second price data updates
- 10-,15-, and 24-second timeframe charts
- Volume profile indicators
- The ability to save custom chart and indicator templates
- A linkable watchlist widget for each chatroom window
- Filtering out of [ADF Orders](https://www.warriortrading.com/alternative-display-facility-adf-orders/) for cleaner charts
The key differences between Warrior Trading Charting and TradingView is that we are not connected to the TradingView community and we do not enable PineScript access. If you create or use any custom Pinescript on TradingView, you cannot use or import those scripts in our platform.

### Additional Information

Please remember to refer to our other articles in [the charting section of our support portal here](https://support.warriortrading.com/support/solutions/folders/19000171870) to learn more about the features of our charts.
