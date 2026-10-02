# Ross-style TradingView scanner setup

This package translates the publicly described Ross/Warrior momentum criteria into a transparent TradingView approximation. It cannot reproduce Warrior Trading's proprietary server-side scanner thresholds.

## What the script implements (v2, October 2026)

The script is the desk's mirror: `src/momentum_platform` and the Pine apply
the same rules, and `tests/test_pine_mirror.py` pins the Pine's defaults to
the platform's constants and to `config/desk-profile.json`.

- Five Pillars technical candidate (Confirmed course values):
  - price from $2 to $20;
  - gain from prior close of at least 10%;
  - relative volume of at least 5x — **measured against the same clock time
    of prior sessions** (today's volume since 04:00 ET against the median the
    name had traded by the same five-minute mark over the prior 10 sessions),
    with the daily measure as a labelled fallback. Dividing a part-day by whole
    prior days reads a fraction of 1x all premarket, so the old script's RVOL
    pillar could never pass before the open;
  - float under 20 million: a verified figure compares directly; TradingView's
    shares outstanding is an upper bound — under the cap it PROVES float under
    the cap (PASS, labelled SO), over the cap it proves nothing (UNKNOWN, never
    FAIL). Unknown never counts as a pass;
  - news/catalyst remains a manual confirmation and is the fifth pillar.
- The desk's discovery band ($1–30, an operator setting) as a separate flag,
  so a runner just outside the pillar band is still seen with its price pillar
  shown FAIL.
- Liquidity gate (Approximation): 25,000 shares in the last five minutes OR at
  least three of the five pillars. Thin premarket tape never reaches a share
  floor written for the regular session.
- HOD Momentum: a new session high at least 0.25% above the prior high (HOD
  Momo does not alert on every print), a day up at least 10%, five-minute
  relative volume of 3x or the pillar path, price at least $1, and a branch
  label (low/medium/unknown float · high/medium RVOL · under/over $20).
- Running Up: a 10-minute uptrend — up at least 3% over the window, a fresh
  10-minute high within the last 3 minutes, price above the window VWAP,
  liquid — one alert per leg, re-armed after three failing bars.
- Squeezes 5% in 5 minutes and 10% in 10 minutes (share floor only) and the
  52-week breakout, once per day.
- The plan is the **first pullback**, as on the desk: an impulse of at least
  two green bars spanning at least 2% (the last six green bars are remembered),
  a pullback of one to four bars that makes no new high, a trigger over the
  previous bar's high; entry = trigger high + $0.01, stop = pullback low −
  $0.01, target = 2R; whether pullback volume was lighter than the impulse is
  recorded. An armed plan expires after five bars.
- A GO / WAIT / PASS verdict with the desk's rules: PASS on two or fewer
  technical pillars, a 52-week high between entry and target, or a heavy
  pullback; WAIT on 3/4 pillars, no confirmed pullback, price more than 1R past
  the trigger, or no momentum event in the last five minutes. Spread and halt
  state are not readable in Pine and the dashboard says so.
- A dashboard mirroring the desk's verdict card, Pine Screener outputs (the
  first ten columns keep their v1 order), alerts, and entry/stop/target bands.

## Recommended chart setup

1. Open TradingView Supercharts and select a US stock.
2. Open Pine Editor, create a new indicator, paste `ross_style_momentum_scanner.pine`, save, **Add to chart**.
3. **Turn on Extended Trading Hours** (right-click the chart → Session → Extended). The session here starts at 04:00 ET as on the desk; without extended hours the RVOL baseline and the premarket events are wrong, and the dashboard's Chart row reads FIX.
4. Use a **1-minute chart**: the 10-minute window, the 5-minute tape and the first-pullback detector are all defined on minute bars. 5-minute works; coarser does not.
5. The RVOL baseline needs prior sessions on the chart. The dashboard's "RVOL baseline" row shows how many it has (FULL at 10, THIN below, FALLBACK while it is on the daily measure). On a 1-minute chart that is a few days of history on free plans and more on paid ones.
6. Enter a verified float for the current ticker when you have one.
7. Confirm news separately, then enable **News / catalyst confirmed manually** for the chart symbol.

## Pine Screener setup

TradingView Pine Screener can apply a custom Pine indicator to a watchlist.

1. Save this script and add it to your TradingView favorites.
2. Open **Products → Screeners → Pine**.
3. Choose a US-stock watchlist. Pine Screener does not dynamically search every listed stock; it scans the symbols in the selected watchlist.
4. Select this indicator.
5. Select the 1-minute or 5-minute timeframe.
6. Add these filters:
   - `Technical 4/4 candidate` equals 1 (or `Pillars passed (0-5)` at least 3 for the desk's liquidity path);
   - optionally `Five Pillars HOD` equals 1;
   - optionally `HOD Momentum` equals 1;
   - optionally `Running Up` equals 1;
   - optionally `Liquidity gate` equals 1.
7. Display and sort by:
   - `Gain from prior close %` descending — the desk's Top gainers order;
   - `RVOL (used)` descending (`RVOL time of day` and `RVOL daily` are also exposed);
   - `5-minute RVOL` descending;
   - `Float/supply M` ascending.
   Note: in the Pine Screener each symbol's RVOL baseline is built from that
   symbol's own loaded history; `Baseline sessions` says how deep it is.
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
- Running Up alert (10-minute uptrend);
- Squeeze: 5% in 5 minutes;
- Squeeze: 10% in 10 minutes;
- 52-week breakout;
- First pullback armed;
- Verdict GO.

Use **Once per bar close** while validating the script. Intrabar alerts react faster but can disappear before a candle closes.

## Entry, stop and target bands

The bands are the desk's first-pullback plan, frozen on the trigger bar:

- Entry: trigger high (the last pullback bar's high) plus $0.01.
- Stop: pullback low minus $0.01.
- Target: two times the initial risk above entry.
- Band width: two cents on each side of each level.
- The dashboard says whether pullback volume was lighter than the impulse
  (the course's volume profile); a heavy pullback is a PASS blocker.

These are visualization and planning levels, not trade recommendations. Size
from your own stated dollar risk; the script never assumes one.

## Known differences from Warrior Trading

- Warrior's exact low/medium-float, RVOL, volatility-hunter and Running Up thresholds are proprietary and are not exposed in Day Trade Dash.
- TradingView's shares-outstanding fundamental is only a proxy for float. Verify float from a reliable source.
- Pine cannot read Warrior's flame/news indicator or determine catalyst quality.
- Relative-volume calculations vary by vendor, session settings and averaging method. This script's time-of-day measure is the desk's method, not Warrior's; an independent screener read 7.7x where the old daily measure read 0.1x on the same name.
- There is no former-momentum proxy in v2; the desk has none either.
- Spread, halt state and news cannot be read in Pine. The verdict says so rather than scoring them.
- Pine Screener scans a watchlist rather than the complete market.

