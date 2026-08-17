# Ross-style TradingView scanner setup

This package translates the publicly described Ross/Warrior momentum criteria into a transparent TradingView approximation. It cannot reproduce Warrior Trading's proprietary server-side scanner thresholds.

## What the script implements

The script implements:

- Five Pillars technical candidate:
  - price from $2 to $20;
  - gain from prior close of at least 10%;
  - daily relative volume of at least 5x;
  - verified float, or a conservative shares-outstanding proxy, at or below 20 million;
  - news/catalyst remains a manual confirmation.
- High-of-day momentum with adjustable five-minute relative-volume confirmation.
- Running Up with adjustable percentage move and time window.
- Explicit 5% in 5 minutes and 10% in 10 minutes squeeze checks.
- 52-week breakout and former-momentum proxies.
- Approximate low-float, medium-float, medium-RVOL and high-RVOL branches.
- A chart dashboard showing every filter and whether it passes.
- TradingView alert conditions.
- Entry, stop and target zones rendered as colored bands.

## Recommended chart setup

1. Open TradingView Supercharts and select a US stock.
2. Open Pine Editor, create a new indicator, and paste `ross_style_momentum_scanner.pine`.
3. Save the script and choose **Add to chart**.
4. Use ordinary candles and enable extended-hours data when reviewing premarket stocks.
5. Start with a 1-minute chart. The 5-minute and 10-minute movement calculations are most literal on a 1-minute chart.
6. In the indicator settings, enter a verified float for the current ticker when available.
7. Confirm news separately, then enable **News/catalyst confirmed manually** for the chart symbol.

## Pine Screener setup

TradingView Pine Screener can apply a custom Pine indicator to a watchlist.

1. Save this script and add it to your TradingView favorites.
2. Open **Products → Screeners → Pine**.
3. Choose a US-stock watchlist. Pine Screener does not dynamically search every listed stock; it scans the symbols in the selected watchlist.
4. Select this indicator.
5. Select the 1-minute or 5-minute timeframe.
6. Add these filters:
   - `Technical 4/4 candidate` equals 1;
   - optionally `Five Pillars HOD` equals 1;
   - optionally `HOD Momentum` equals 1;
   - optionally `Running Up` equals 1.
7. Display and sort by:
   - `Gain from prior close %` descending;
   - `Daily RVOL` descending;
   - `5-minute RVOL` descending;
   - `Float/supply proxy M` ascending.
8. Leave **Manual float** at zero in Pine Screener. One indicator input applies to the entire screen, so a manual per-symbol float cannot be used there.

## Suggested watchlists

Pine Screener works on watchlists, not the entire US market. For broader coverage, create or import lists such as:

- NASDAQ stocks priced below $20;
- NYSE/AMEX stocks priced below $20;
- known recent runners;
- recent reverse splits;
- premarket percentage gainers from TradingView's built-in stock screener.

Use TradingView's built-in Stock Screener first to produce a broad premarket list, then run the custom Pine Screener against that watchlist for the Ross-style technical rules.

## Alert setup

On a chart, open **Create alert**, choose this indicator, and select one of:

- Technical Five Pillars candidate;
- Full Five Pillars candidate;
- Five Pillars HOD alert;
- HOD Momentum alert;
- Running Up alert;
- Squeeze: 5% in 5 minutes;
- Squeeze: 10% in 10 minutes;
- 52-week breakout.

Use **Once per bar close** while validating the script. Intrabar alerts react faster but can disappear before a candle closes.

## Entry, stop and target bands

The default band model is mechanical and intentionally configurable:

- Entry: signal-bar high plus $0.01.
- Stop: signal-bar low minus $0.01, or one ATR below entry.
- Target: two times the initial risk above entry.
- Band width: two cents on each side of each level.

These are visualization and planning levels, not trade recommendations. Adjust them to the stock's spread, volatility, liquidity and your tested risk rules.

## Known differences from Warrior Trading

- Warrior's exact low/medium-float, RVOL, volatility-hunter and Running Up thresholds are proprietary and are not exposed in Day Trade Dash.
- TradingView's shares-outstanding fundamental is only a proxy for float. Verify float from a reliable source.
- Pine cannot read Warrior's flame/news indicator or determine catalyst quality.
- Relative-volume calculations vary by vendor, session settings and averaging method.
- The former-momentum rule here means a prior daily gain above the chosen threshold within roughly 120 sessions; it is not Warrior's private former-runner database.
- Pine Screener scans a watchlist rather than the complete market.

