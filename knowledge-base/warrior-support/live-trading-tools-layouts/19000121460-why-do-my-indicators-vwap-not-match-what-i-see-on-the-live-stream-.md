<!-- source: https://support.warriortrading.com/support/solutions/articles/19000121460-why-do-my-indicators-vwap-not-match-what-i-see-on-the-live-stream- -->
<!-- category: Education Portal and Educational Resources -->
<!-- folder: Live Trading Tools & Layouts -->
<!-- modified: Thu, Sep 19, 2024 at 3:42 PM -->

# Why do my indicators/VWAP not match what I see on the live stream?

TABLE OF CONTENTS

- [Not Seeing VWAP appear on DTD Charts:](#Not-Seeing-VWAP-appear-on-DTD-Charts%3A)
[Update your VWAP to the newest version:](#Update-your-VWAP-to-the-newest-version%3A)
- [Comparing our DTD Charts to 3rd party Platforms:](#Comparing-our-DTD-Charts-to-3rd-party-Platforms%3A)

### Not Seeing VWAP appear on DTD Charts:

As of an update on 9/20/2024, our VWAP from TradingView will not appear on your chart unless you scroll back and load all of today's data. This is mainly an issue for smaller timeframes like the 10 second or 1 minute charts.

They implemented this to help with the issue where VWAP did not fully calculate correctly unless you scrolled back.

To update the data without needing to scroll back, we have had to make our own indicator that calculates itself using all of the volume and price data loaded.

#### Update your VWAP to the newest version:

We have already changed the default WT layouts to have this new VWAP indicator. 

So if you have your own layouts you use, you will have to delete your old VWAP and add in the new VWAP titled "Warrior Trading Custom VWAP"

You can add this by simply searching for VWAP in the Indicators section of your charts. and clicking the "Warrior Trading Custom VWAP" 

Once you add the indicator and change it to your liking, make sure to save your chart layouts 

- Note that you cannot save over the WT-labeled default layouts and must rename or make a copy with a new name [per our guide here.](https://support.warriortrading.com/support/solutions/articles/19000141885-6-saving-and-loading-charts-layouts-wt)

You can see how this simple and quick process looks here:

[image]

### Comparing our DTD Charts to 3rd party Platforms:

Traders often notice that the indicators on their own charts are different than what is shown on another trader's charts. In most cases, this is simply due to a difference in calculations.

Here is a list of things to check so that you can better understand why the calculations may be different:

- Are you watching a replay or other delayed stream? If it is a live stream, have you refreshed the video to make sure it is in sync with the current time?
- Is your platform using delayed market data? Platforms typically require fees to be paid for live market data.
- Are you viewing the same exact time frame? For example, if you are looking at Ross's 1-minute chart, are you looking at your own 1-minute chart too?
- Do you have indicators to calculate on candle close? It is not typical to have indicators calculated from open, bid, or ask.
- Are you using the same platform as the trader whose chart you are viewing? It is common for platforms to vary with code or market data results. While this can lead to different indicator results across platforms, that difference is normally no more than a few cents. Ross now uses Day Trade Dash charts, which is based on TradingView. If you are not using the same platform, you might see slight discrepancies. Warrior Trading members interested in access can add on a trading tools subscription that includes charts via our [](https://www.warriortrading.com/member-renewal-information/)[Renewal Information & Chat Room Tools page](https://www.warriortrading.com/member-renewal-information/), or simply choose a trading tools subscription upon initial sign-up if you are not yet a member.
- What moving averages are you using? Ross uses EMAs which move exponentially to the last closed candle and update sooner than a regular SMA.
- What is your start time or "anchor time" on VWAP? If your VWAP indicator is different, make sure that your VWAP price starts calculating at 12 am EST  for a new trading day; a start time of 9:30 am or 4 pm will give different results. You may have to reach out to your broker to confirm your anchor time and see if you can change this setting.

[Click here to view a video from Ross explaining the VWAP](https://www.youtube.com/watch?v=pSTHR41o6_k&feature=youtu.be&ab_channel=WarriorTrading) indicator and how he uses it.

If you have issues with your WT simulator or charts, please [reach out to us here](https://warrior.app/contact), in our Support Room, or via email (simulator@warriortrading.com or [team@warriortrading.com](mailto:team@warriortrading.com)). We will not be able to assist with third-party platforms; please contact those support resources directly.
