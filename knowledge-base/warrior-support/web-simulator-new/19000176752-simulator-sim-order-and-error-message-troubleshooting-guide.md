<!-- source: https://support.warriortrading.com/support/solutions/articles/19000176752-simulator-sim-order-and-error-message-troubleshooting-guide -->
<!-- category: Using the Warrior Trading Platform (Day Trade Dash, Community, and Simulator) -->
<!-- folder: Web Simulator (New!) -->
<!-- modified: Fri, Aug 14, 2026 at 1:41 PM -->

# Simulator (Sim) Order and Error Message Troubleshooting Guide

Note: This guide covers troubleshooting for the Simulator only. For other Day Trade Dashboard (DTD) issues, please refer to our DTD Troubleshooting Guide here:
[Issues with Live Stream or Day Trade Dash (WT)](https://support.warriortrading.com/support/solutions/articles/19000108691-issues-with-live-stream-or-day-trade-dash-wt)
TABLE OF CONTENTS

- [Order Troubleshooting](#Order-Troubleshooting)
[Order Delays](#Order-Delays)
- [Hotkeys Not Responding](#Hotkeys-Not-Responding)
- [Risk Check: Short Sale Restriction (SSR)](#Risk-Check%3A-Short-Sale-Restriction-(SSR))
- [Running Out of Buying Power](#Running-Out-of-Buying-Power)
- [Computer / System Issues](#Computer-/-System-Issues)
- [Error Messaging](#Error-Messaging)
[Common Error Messages](#Common-Error-Messages)
- [Issues to Report to Support](#Issues-to-Report-to-Support)
- [Session Timeout](#Session-Timeout)
- [Multiple Concurrent Logins](#Multiple-Concurrent-Logins)
- [Experience on Mobile Devices](#Experience-on-Mobile-Devices)
- [Resetting Settings to Default](#Resetting-Settings-to-Default)
- [Pop Out Windows and Widget Limitations](#Pop-Out-Windows-and-Widget-Limitations)

### Order Troubleshooting

#### Order Delays

There are times when it may feel like there is a delay when placing an order. As with all browser-based applications, some inherent display and front-end delays are expected. You should expect a marketable order to have approximately a 100–200 ms delay to display the order, and then an additional 100–200 ms delay to populate in your Positions widget — for a total of 200–400 ms. CPU usage in a browser is handled very differently than in a desktop application.

First steps to check:

- If your order is still open and showing a yellow "Open" status, hover over the order to see the reason it has not filled.
- Check whether your limit price has been met on the Level 2, based on the Order Logic described in the next section.
- Check the Time Entered column and make sure it aligns within 1 second of the Time Updated column if the order did fill.
Why did my order not fill at the price I set?

- The bid or ask never reached your limit price. This commonly occurs when a stock has a very wide spread between the bid and the ask. In this case, it is best to use offsets.
- The price gapped up or down through your limit price too quickly for the simulator to fill your order.
- Review the Order Logic below to determine how your order fills in the simulator:

The Simulator's order logic is designed to help traders learn to trade in a worst-case scenario environment. There are no partial fills, and trades do not execute based on the Last Traded Price or Time and Sales price or size — they execute based on the Bid and Ask price.

- Buy Limit Orders — Fill when the limit price reaches the Ask. If the limit price is higher than the Ask, it fills at the current Ask.
- Sell Limit Orders — Fill when the limit price reaches the Bid. If the limit price is lower than the Bid, it fills at the current Bid.
- Buy Market Orders — Fill at the Ask.
- Sell Market Orders — Fill at the Bid.
Because of this logic, you may see trades print through your limit price on Time and Sales without your order filling. This occurs because the Bid/Ask criteria may not yet have been met.
Why was there a delay in my fill for a marketable order?

- There is normally a very small delay of under 1 second for a filled order to display. It likely filled shortly after submission but took time to reach our servers and return to display in your Activity Monitor.
- Check the Time Sent vs. Time Updated columns to confirm whether a significant delay occurred.
TIF (Time in Force) Order Type Errors
An incorrect TIF setting will prevent your order from filling or may cause it to be rejected. Please review the TIF types below and make sure you are using the correct one. DAY+ is recommended for general all-day use.

To see the reason for a rejection, hover over the Rejected status on your order.

| 
| 

TIF Type | 

Description
| 
Day | 
True day order; active from 9:30 AM – 4:00 PM EST. Cancels after 4:00 PM EST.
| 
EXT | 
Pre- and post-market only. Will not fill during regular market hours.
| 
DAY+ / DAY+EXT | 
Day plus extended hours; cancels after 8:00 PM EST.
| 
GTC | 
Good Till Cancelled. Same as DAY+EXT, but the order stays open across multiple days. 
  
Signs Your CPU Is Being Overloaded

- If your Positions widget updates before your Activity widget, or vice versa, this is a strong indicator that your CPU is being overloaded.
- If your streams or other applications also slow down simultaneously, you likely have too much data running on the platform. You will need to either upgrade your computer or reduce the number of charts and Level 2 widgets on your Simulator platform.
Charting and Level 2 data rely on tick data, which is very CPU-intensive. Your computer must process all incoming market data in real time for your widgets to function properly.

Please review our performance optimization guide and minimum system requirements here: [Simulator Performance & Latency Troubleshooting Guide : Warrior Trading](https://support.warriortrading.com/support/solutions/articles/19000176267-simulator-performance-latency-troubleshooting-guide) 

#### Hotkeys Not Responding

If your hotkeys appear to not be working, the most likely cause is that the Level 2 and Order Entry widget is not the active window in your browser.
Hotkeys require the Order Entry window to be in focus in order to function. To activate it:

-  Click inside the Order Entry window to bring it into focus.
-  You will know it is active when you see a blue highlight around the border of the widget.
-  Once the blue border is visible, your hotkeys should work as expected.
This is one of the most common reasons hotkeys appear to stop working. Before troubleshooting further, always confirm that the Order Entry window is active first.

#### Risk Check: Short Sale Restriction (SSR)

If you receive the message "Risk Check: Stock has Short Sale Restriction (SSR)", it means the platform has detected that one or more of your pending orders, if filled simultaneously, would result in a net short position on a stock that currently has a Short Sale Restriction in place.
Steps to resolve:

-  Open your Trade Activity widget and review all open orders for the affected ticker.
-  Check whether you have more than one open order that, if both filled, would put you into a short position — that is, selling more shares than you currently own.
-  Cancel any duplicate or excess open orders to ensure your total open sell orders do not exceed your current share position.
If you are already in an unintended short position:

- Purchase an equivalent number of shares to close the short position. For example, if you are short 100 shares, buy 100 shares to flatten your position.
SSR is triggered on stocks that have dropped more than 10% from the prior day's close. During SSR, short selling is restricted to certain conditions. The Simulator enforces this rule just as a live trading environment would.

#### Running Out of Buying Power

If you are unable to place an order due to insufficient buying power, follow these steps to recover:

-  Open your Trade Activity widget and check for any open, unfilled orders. These orders reserve buying power even if they have not yet executed. Cancel any orders you no longer need to free up that reserved capital. You may need to look at orders from 7 Days up to 6 Months ago. Click the drop down to select 7 Days / 6 Months to see if you have any older open orders.
-  Close or reduce open long positions to free up additional buying power.
- Add or adjust your Account Balance to increase your buying power (BP). See: [Understanding Simulator Profile and Settings | Web Simulator : Warrior Trading](https://support.warriortrading.com/support/solutions/articles/19000175677-understanding-simulator-profile-and-settings-web-simulator#Account-Value-and-Reset-Trade-History)  
Important: The Simulator does not automatically reset buying power each day. Your buying power carries over from session to session, meaning losses and reserved capital will persist until manually addressed.

#### Computer / System Issues

System Clock Incorrectly Set
Your charts are tied to your computer's system clock. If your charts appear out of sync with others or are running behind, your CPU may be overworked or your system clock may need to be re-synced. See this support article: [Simulator Performance & Latency Troubleshooting Guide : Warrior Trading](https://support.warriortrading.com/support/solutions/articles/19000176267-simulator-performance-latency-troubleshooting-guide)
Disconnection from Data Feed
If you experience a lost connection to market data, check your network connection and the website connection. We may be experiencing an outage. Try logging out and back in. See this support article: [Simulator Performance & Latency Troubleshooting Guide : Warrior Trading](https://support.warriortrading.com/support/solutions/articles/19000176267-simulator-performance-latency-troubleshooting-guide) 

### Error Messaging

#### Common Error Messages

"Rejected to subscribe to chart of symbol"
This message means the symbol entered is invalid. However, if you know the symbol is valid, this is likely a network or browser issue.
Steps to resolve:

-  Refresh the page.
-  Try an alternative browser.
-  If the issue persists, try a different network or connect directly to your router via ethernet cable.
"Canceling order failed, order has already filled"
This means the order filled before your cancel request was processed. This can happen due to network or hardware latency on your system, or because the cancel was submitted too quickly after the order was placed.
Try slowing down the speed at which you submit cancel requests.
"Position Limits Reached" (Risk Settings)
This error is triggered by your account's risk settings. Common causes include:

- Maximum position size exceeded
- Account restrictions set within your risk settings
Review your Risk Settings to adjust your limits as needed. See: [Understanding Simulator Profile and Settings | Web Simulator : Warrior Trading](https://support.warriortrading.com/support/solutions/articles/19000175677-understanding-simulator-profile-and-settings-web-simulator#Account-and-Risk-Settings) 

#### Issues to Report to Support

The following are not normal platform behaviors and should be reported to our support team.
Bid/Ask Data Issues

- Invalid or missing bid/ask price data
- The simulator is not receiving proper market data updates
Before reporting, please confirm the stock is not delisted. If the stock is no longer tradable, see below.

Delisted Stocks
If a stock has no data due to being delisted, please contact us so we can remove the position from your account.

High-Volume Timing Issues
Orders placed right at market open or close may occasionally be skipped over. Please report these instances to our support team.

#### Session Timeout

Sessions are currently limited to 12 hours. When your session is about to expire, you will receive a prompt asking if you are still active. If no action is taken, you will be automatically logged out.

#### Multiple Concurrent Logins

You may only be logged in to one instance of the platform at a time. If you log in on a second device, your first session will be automatically logged out.

#### Experience on Mobile Devices

The Warrior Trading Simulator platform has not been optimized for mobile devices or tablets. For the best experience, please use a desktop or laptop computer.

#### Resetting Settings to Default

There is currently no single full platform reset option. Settings must be reset individually. The following areas can each be reset independently:

- Reset Layout
- Reset Hotkeys
- Reset Risk Settings
- Reset Positions Widget
- Reset Trade Activity Widget

#### Pop Out Windows and Widget Limitations

Layouts are limited to a maximum of 5 Pop Out Windows (5 for the Sim and 5 for Day Trade Dash). For more information on this topic, see: [How to Adjust, Save, & Load Day Trade Dash and Chat Room Layouts | WT : Warrior Trading](https://support.warriortrading.com/support/solutions/articles/19000126510-how-to-adjust-save-load-day-trade-dash-and-chat-room-layouts-wt) 

To ensure optimal browser and platform performance, the platform enforces the following widget and window limits. If these restrictions impact your ability to use the platform effectively, please share your use case and computer specifications with our support team so we can better understand your needs and consider adjusting your settings.

| 
| 

Widget Type | 

Max Per Window | 

Max Per Platform
| 
Browser Windows | 
— | 
6
| 
Total Widgets | 
14 | 
40
| 
Scanners | 
12 | 
24
| 
Charting Widgets | 
12 | 
24
| 
Level 2 Widgets | 
4 | 
8
| 
Stock Quote Widgets | 
3 | 
6
| 
Watchlist Widgets | 
3 | 
6
| 
Trade Activity Widgets | 
3 | 
6
| 
Positions Widgets | 
1 | 
6 
  
Still need help? Submit a support ticket or email us at [team@warriortrading.com](mailto:team@warriortrading.com). For fastest service, include "Simulator Issue" in the subject line.
