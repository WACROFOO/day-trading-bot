<!-- source: https://support.warriortrading.com/support/solutions/articles/19000141884-4-chart-indicators-wt -->
<!-- category: Using the Warrior Trading Platform (Day Trade Dash, Community, and Simulator) -->
<!-- folder: Charting (Day Trade Dash and Web-Based Sim) -->
<!-- modified: Mon, Aug 4, 2025 at 3:05 PM -->

# 4. Chart Indicators | WT

This article talks about:

- [Adding Indicators](#Adding-Indicators)
- [Removing and Hiding Indicators](#Removing-and-Hiding-Indicators)
- [Our Default Indicators](#Our-Default-Indicators)
- [Customizing Indicator Settings](#Customizing-Indicator-Settings)
[Saving Changes, Resetting to Default, and Overriding Defaults](#Saving-Changes,-Resetting-to-Default,-and-Overriding-Defaults)
- [Favoriting Indicators ](#Favoriting-Indicators%C2%A0) [](#Favoriting-an-Indicator-Template)
- [Favoriting an Indicator Template](#Favoriting-an-Indicator-Template)
- [Definitions of Indicator Settings](#Definitions-of-Indicator-Settings)
[Inputs](#Inputs)
- [Style](#Style)
- [Visibility](#Visibility)
- [Troubleshooting Common Indicator Issues](#Troubleshooting-Common-Indicator-Issues)
[Indicator shows zero.](#Indicator-shows-zero.)
- [VWAP is not calculating correctly on different time frames.](#VWAP-is-not-calculating-correctly-on-different-time-frames.)
- [Cannot see my indicator or VWAP.](#Cannot-see-my-indicator-or-VWAP.)
- [I cannot find an indicator.](#I-cannot-find-an-indicator.)
- [](#Additional-Information-&-Next-Steps)[Additional Information & Next Steps](#Additional-Information-&-Next-Steps)

## Adding Indicators

Read below or use the video as a guide for understanding how to add indicators on the charting software in our live trading room platform.

To add an indicator:

- Click on the indicator icon shown below, or use keyboard shortcut /

[image]

- A new window will pop up. Use the search or scroll function to select a new indicator to add.

[image]

Note: This is our list of current indicators. You are not able to import or add custom indicators at this time. If you have any suggestions for future indicators to add please request or give feedback [through our portal here.](https://warrior.app/contact)

## Removing and Hiding Indicators

To remove an individual indicator, you have the option to hide it temporarily or to delete it completely. To see these options, hover over the indicator name from the top left of your chart.

- Click the eye icon to hide it or make it reappear.
[image]

- Click the X icon to remove it completely.
[image]

To remove all indicators from your charts to start fresh while keeping the ticker, link, and timeframe, you can right-click on the chart and select Remove Indicators.

[image]

## Our Default Indicators

Default indicators load on your charts for your first login. They are also found in our default layout templates and indicator templates (link coming soon). These indicators can be edited, hidden, or changed to your liking as shown in our guide below.

The indicators in the default template and layout include (click any of the names to learn more about the terminology):
[](https://www.warriortrading.com/float-definition-day-trading-terminology/)

- [Float](https://www.warriortrading.com/float-definition-day-trading-terminology/)
- [Market Cap](https://www.warriortrading.com/market-capitalization-definition-day-trading-terminology/)
- [VWAP ](https://www.warriortrading.com/vwap/)(orange - only displayed on intraday timeframes)
- 9 [EMA](https://www.warriortrading.com/exponential-moving-average/) (gray)
- 20 [EMA](https://www.warriortrading.com/exponential-moving-average/) (green)
- 200 [EMA](https://www.warriortrading.com/exponential-moving-average/) (purple)
- [Volume](https://www.warriortrading.com/volume-definition-day-trading-terminology/)
- [MACD](https://www.warriortrading.com/moving-average-convergence-divergence-macd-definition-day-trading-terminology/)

In the image below, you can see how each indicator from the chart is easy to identify by referencing the color in the key that appears in the upper left-hand corner of the chart.[
[image]
](https://www.warriortrading.com/moving-average-convergence-divergence-macd-definition-day-trading-terminology/)

## Customizing Indicator Settings

To view your indicator's settings, hover over it from the list of indicators and click the 3 dots that appear.

[image]

Go to Settings, and adjust accordingly, using the information below to guide you on the definitions of each option that appears for that indicator.

### Saving Changes, Resetting to Default, and Overriding Defaults

Once you have made changes to your settings, you have the option to:

- save your changes by clicking Ok
- undo the changes you've made since you last clicked Ok, by clicking Cancel
- override our default settings by clicking Defaults > Save As Default (the next time you add this indicator, it will load the default settings that you last saved)
- revert the settings back to our own default settings by selecting Defaults > Reset Settings
[image]

### Favoriting Indicators

Favoriting indicators is useful if you only use a few indicators very often and prefer that indicators display at the top of your list.

To save an indicator as a favorite, please follow the steps below:

- Click your indicator drop-down menu.
- Hover over the indicator for the star to appear at the left of the indicator name.
- Click the star to sort it to the top of your indicator list.
See example below:

[image]

### Favoriting an Indicator Template

Indicator templates hold saved chart indicators with the option also to save the ticker and timeframe. This feature might be useful if you want to see how it would look with a suite of indicators without disrupting the symbol or time frame of current open charts.

To do this, click the Indicator Templates symbol on the top bar of your chart, followed by Save Indicator template.

[image]

When saving an indicator template, you can save the template without saving the symbol or time interval and simply naming the template and clicking save on the bottom right.
[image]

After saving, you should be able to return to the indicator template section and star your favorites.

[image]

The first letter of favorited layouts will display on the top bar for you to easily select, as demonstrated below:

[image]

## Definitions of Indicator Settings

Note: Each indicator may have more or fewer setting options than in the examples below.

### Inputs

Inputs are either the length, source, or settings the indicator uses for its calculations.

- Length: For moving averages, this is how many previous candles it will take to calculate the current moving average price.
- Source: This is for how to calculate the price of the previous candle. By default, most indicators use the close of the previous candle. However, you can set it to a combination to factor in the averages when there is higher volatility.
- Example: ohlc4 means the calculation is from the candle Open, High, Low, and Close, and then divided by 4.

##### 

- Offset:  This moves the indicator forward or back a certain number of candles. The default is 0.
- Smoothing/ Smoothed MA: This can help "smooth out" an indicator so that it does not factor in large price swings or volatility. We do not suggest using this function. Try using longer moving averages instead.

### Style

Style adjusts the color and visual of the indicator.

- Plot - color: Select the plot's current color to bring up the drop-down menu of options. You have this option for each plot an indicator might have and can then choose the color, opacity, and thickness of the indicator.

[image]

- Note: 100% opacity means that you cannot see through the indicator. If you have an indicator that uses a shaded area as a function, you can use this function to reduce the opacity to see through the shaded area better.
[image]

- Plot - Price line: If you toggle this setting on, a horizontal line on the chart where the current price of the indicator is.

[image]

In the image below, a price line is added:
[image]

### Visibility

This section of the settings indicates which timeframes to display for the indicator.
[image]

## Troubleshooting Common Indicator Issues

### Indicator shows zero.

- This error means that not enough data has loaded in for the indicator to calculate. For example, an IPO that only had 1 hour's worth of data will not yet be able to calculate the 200 EMA on any time frame.

### VWAP is not calculating correctly on different time frames.

- The VWAP is not calculated on a per-tick basis, but on candle OHLC data. Because of the difference, the time frame's candles also have different OHLC data, making the VWAP slightly different across timeframes. This is normal.
- If you feel the VWAP is incorrect, please load all of today's data or click 1d on the bottom of the chart to load all data for the day to ensure it syncs with today's data.

### Cannot see my indicator or VWAP.

- VWAP, by default, is set only to be displayed on intraday timeframes. If it is another indicator, we suggest checking:
if you accidentally deleted it and no longer see it from your indicator list on the top left
- if you accidentally hid your indicator (see the image below), in which case you should click the eye symbol

[image]

### I cannot find an indicator.

- We do not support all indicators at this time. If you have a suggestion or idea for an indicator, please send it to us for consideration at [team@warriortrading.com](mailto:team@warriortrading.com) or through [https://warrior.app/contact](https://warrior.app/contact)

To learn how to save you indicators to your charts along with the your chart settings, see our [guide here on saving chart layouts](https://support.warriortrading.com/support/solutions/articles/19000141885-6-saving-and-loading-charts-layouts). To learn how to save your charts and indicators to your chatroom layout when using multiple windows please [see our guide here.](https://support.warriortrading.com/support/solutions/articles/19000126510-how-to-adjust-save-load-chat-room-layouts-wt#How-to-Save-a-Layout-as-Default-(to-Appear-on-Login))

## Additional Information & Next Steps

We have a basic guide on our site for other indicators that you might want to consider experimenting with: [https://www.warriortrading.com/technical-analysis/](https://www.warriortrading.com/technical-analysis/)

Please remember to refer to our other articles in [the charting section of our support portal here](https://support.warriortrading.com/support/solutions/folders/19000171870) to learn more about other features of our charts.
