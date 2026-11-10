# Rule spec v0.2 — one portfolio, seven sleeves, monthly rules

**Verification status:** ❌ Not validated. v0.2 is rebuilt around the evidence
in [the research report](research/reports/Retail%20systematic%20strategy%20candidates.md),
but none of it has been backtested by us yet. Every number is a **starting
value to test**, not a result. ROADMAP Steps 4–5 decide what survives.

This file is the single source of truth for the rules. Code implements exactly
what is written here, and any change is made here first, with a version bump.
v0.1 (two engines: defensive core + swing trading) is in git history; §10 lists
what changed and why.

---

## 0. Assumptions

| Assumption | Why it matters | Confirm in |
|---|---|---|
| You are a **France tax resident** investing in **euros** | Every result is measured in EUR, after French tax | ROADMAP Step 0 |
| **Two accounts:** a PEA (manual orders) and a CTO at Interactive Brokers (automated) | The PEA is tax-advantaged after 5 years but has no API and holds only PEA-eligible equity funds. Everything else needs the CTO. Without a PEA, everything goes in the CTO using accumulating ETFs. | Step 0 |
| You are an EU **retail client** | US-listed ETFs are blocked (PRIIPs). Live trading uses UCITS ETFs. Backtests use long-history index data. | — |
| **Monthly decisions** | Low turnover means low cost and low tax, and the system tolerates a missed day. Short-horizon edges are the most decayed (research report). | — |
| **Benchmarks:** an MSCI World tracker held in a PEA, after tax; and a EUR 60/40 portfolio | The PEA tracker is your real alternative, so it is the bar to clear | — |

---

## 1. Design principles

1. **Harvest durable premia; don't predict.** Every sleeve earns a return that
   has survived publication, costs, and testing in several countries: the
   equity premium, momentum, quality, and trend.
2. **Consistency comes from mixing things that fail at different times.**
   Momentum suffers in violent rebounds. Trend suffers in sudden crashes. Bonds
   suffer in inflation. Gold and managed futures tend to do well when the
   others don't.
3. **Few rules, few parameters.** Each extra rule is another chance to fit
   noise. v0.2 has 7 rules and about 10 parameters, where v0.1 had 17.
4. **The wrapper is a return source.** At 10% a year, a mature PEA is worth
   about 1.8 points a year over a high-turnover CTO strategy (research report).
   That is more than any tilt is likely to add.
5. **The bot's real job is discipline:** following the rules through the
   drawdowns where people usually quit. The behaviour gap costs a typical
   investor about 1.2 points a year (research report).

---

## 2. Sleeves and target weights

| # | Sleeve | Target | Role | Backtest series (long history) | Live instrument (confirm in Step 2) | Account |
|---|---|---|---|---|---|---|
| S1 | World equity | **35%** | The equity premium | MSCI World net, in EUR | PEA-eligible MSCI World ETF (e.g. WPEA, DCAM) | PEA |
| S2 | Momentum tilt | **15%** | Return tilt | MSCI World Momentum (back-tested before its 2013 launch); AQR momentum factors as cross-check | MSCI World Momentum UCITS ETF (e.g. IS3R, XDEM) | CTO |
| S3 | Quality tilt | **10%** | Return tilt that partly offsets momentum crashes | MSCI World Quality | MSCI World Quality UCITS ETF (e.g. IS3Q, XDEQ) | CTO |
| S4 | Managed futures | **15%** | Crisis diversifier: makes money in long bear markets | AQR Time-Series Momentum factor (from 1985) and SG Trend Index (from 2000), net of the fund's fees | iMGP DBi Managed Futures UCITS ETF, EUR-hedged | CTO |
| S5 | US Treasuries 7–10y, EUR-hedged | **10%** | Hedge against deflationary crashes | 7–10y Treasury index, hedged to EUR | $ Treasury 7–10y UCITS ETF, EUR-hedged | CTO |
| S6 | Gold | **5%** | Hedge against inflation and panic | Gold price in EUR | Physical gold ETC (French tax treatment still to confirm) | CTO |
| S7 | EUR cash | **10%** | Dry powder, and where filtered sleeves park | EUR short rate | EUR overnight-rate ETF (e.g. XEON) in the CTO; plain cash in the PEA | both |

That is 60% equities, 15% managed futures, 10% bonds, 5% gold and 10% cash at
target. When the filters are off, the equity share can drop to zero.

---

## 3. Rules

**R1 · Monthly decisions, split across four dates.** Divide the portfolio into
4 equal tranches. Tranche *k* is reviewed on the first trading day on or after
the 1st, 8th, 15th and 22nd of each month respectively, using the previous
close. Results from a single rebalance date are mostly luck: shifting Faber's
rule by one day moved its max drawdown between 19% and 30% (research report).
Splitting the dates removes most of that luck. Turnover is the same; you just
make more, smaller orders.

**R2 · Equity trend filter.** At each review, if MSCI World closes **above its
10-month moving average**, the tranche holds its targets in S1, S2 and S3.
Otherwise those three sleeves move to S7 cash. One signal drives all three:
they are highly correlated, and one signal means fewer parameters and fewer
whipsaws. Inside the PEA, switching between equity and cash is untaxed.

**R3 · Gold trend filter.** Hold S6 while gold (in EUR) is above its 10-month
average; otherwise move it to cash.

**R4 · Bonds must beat cash.** Hold S5 only while its 12-month total return
beats cash's 12-month return; otherwise move it to cash. In 2022, strategies
that applied this rule kept drawdowns to about −8%, against −17% for those
that held long bonds regardless (research report).

**R5 · Managed futures are always held.** S4 is already a trend strategy, so
filtering it would double up. It is only rebalanced (R6).

**R6 · Rebalancing.** At each review, any sleeve outside its band gets traded
back to target. The band is **5 points absolute or 25% of target**, whichever
is hit first. There is also a full rebalance in January. **New money and
distributions go to the most underweight sleeve first**, which rebalances
without selling, so without realising taxable gains in the CTO.

**R7 · Execution.** Orders go in at the next session after the signal, as
marketable limits at the last price ±0.5% (DAY orders), re-placed for up to 3
sessions if unfilled, then an alert. **There are no per-position stop
losses:** the monthly filters are the exits. Stops on ETFs add whipsaw, and
volatility-managed overlays generally failed out of sample (Cederburg et al.,
research report).

---

## 4. Research sleeve (replaces v0.1's Engine 2)

The research sleeve is **0% by default, with a 10% maximum**, taken pro rata
from S1–S3. It is where higher-return ideas can earn a place, but only through
the funnel in §7, followed by paper trading.

Candidate queue, in order:

1. **Self-built European large-cap momentum, inside the PEA.** The
   post-publication evidence is strongest here (European long-short momentum:
   +11.5% a year since 2015). It only makes sense above roughly €100k, because
   of IBKR's €1.25 minimum commission, and it needs point-in-time European
   stock data.
2. **Sector-ETF rotation** (v0.1 Setup A), tested head-to-head against S2.
3. **RSI(2) pullbacks** re-tested on European closing prices. The
   post-publication evidence says this probably fails.

---

## 5. Portfolio-wide limits and kill switch

These live in the execution layer and are modelled on
`src/paper_trading/risk_gate.py` (LESSONS B2–B5).

**Always:**
- No margin, no shorting, no options, no leverage at portfolio level. S4 uses
  futures inside the fund; holding it unlevered means you cannot lose more than
  you put in.
- Max 12 orders per day.
- Max single order: 10% of the portfolio. Max single ETF: 40%.
- Single stocks (research sleeve only): max 5% each.

**Pre-trade checks.** All run before an order exists; any failure means no
order and an alert:
- **Fresh data:** the last bar is the last completed session.
- **Sane data:** no close moved more than 25% without a recorded split.
- **Sane price:** the limit is within 3% of the last close.
- **Reconciled:** broker positions and cash match the internal ledger.
- **Explained P&L:** the portfolio's daily change matches holdings × prices to
  within 0.5%.

**Kill switch.** Latched, persisted, and reset by a human only. While latched:
no new buys, but sells still work. Triggers:
- any unhandled exception in the daily run
- a reconciliation or explained-P&L mismatch
- 2 or more broker rejections in one day
- a failed data check
- portfolio down 4% or more in one day (pause and review)

**Pain limit.** If the portfolio's drawdown from its peak exceeds the Step 0
limit (default −20%), everything stops for a review. That is not a forced
sale; it is a human decision, made with the backtest's distribution in front
of us.

---

## 6. Timing

The **daily job** runs after the US close (17:00 New York, 23:00 Paris). It
fetches data, runs checks, reconciles, and sends a summary. It only **trades
on the tranche dates** (R1). UCITS orders execute at the next European
session; PEA orders are sent to you as instructions.

**No lookahead.** A signal from day *t*'s close fills on day *t+1* at the
earliest, and the backtest uses the European session's prices for UCITS
lines.

---

## 7. The evidence funnel: rules for adding or changing anything

Any new sleeve, rule or parameter has to pass all of these, and every trial
goes in `research/experiments.csv`:

| Step | Rule |
|---|---|
| Admit | Only families that replicate across studies and countries: momentum, value, quality, low-risk, time-series trend. No size, seasonality, microcap or intraday signals. |
| Haircut first | Plan on 40–60% of the published premium. Subtract costs (at least 1% of monthly turnover), 0.57% a year of timing luck for single-date tests, and the 31.4% PFU on realised gains. |
| Trial budget | At most ~10 configurations per family, counted honestly, quick looks included. |
| History | Years of data ≥ 2·ln(trials)/Sharpe². That is about 18 years for 10 trials at a Sharpe of 0.5, so use index and factor histories, not ETF histories. |
| Significance | t ≥ 3 for a new signal (t ≈ 2 for an established family confirmed elsewhere). Deflated Sharpe ≥ 0.95. |
| Hold-out | The last ~5 years plus one region, looked at **once**. |
| Costs | Everything also run at 2× costs. |
| Plausibility | A backtest Sharpe above ~1 for a long-only equity tilt, or more than 20–25% a year, is a red flag, not a result. |

---

## 8. Parameters and pre-registered variants

| Parameter | Default | Variants tested (and nothing else) | Test |
|---|---|---|---|
| `equity_filter` | Price > 10-month average | 12-month return > cash | 1 |
| `filter_scope` | Full sleeve | Half sleeve (filter moves only 50% to cash) | 1 |
| `bond_rule` | On | Off (always hold S5) | 1 |
| `treasury_hedge` | EUR-hedged | Unhedged | 1 |
| `crash_ladder` | Off | On: cash buys equity in thirds at −20/−30/−40% from the peak, once price is back above its 50-day average | 1 |
| `tranches` | 4 | 1 (to measure timing luck, not to choose) | 1 |
| `mf_weight` | 15% | 0, 10, 20% | 3 |
| `momentum_sleeve` | MSCI World Momentum ETF | Sector rotation; GEM-style regional momentum | 2 |
| `quality_weight` | 10% | 0% | 2 |
| `bands` | 5 pts / 25% | — fixed | — |

That is about 8 trials for Test 1, 3 for Test 2 and 3 for Test 3. Each family
stays inside the §7 budget.

---

## 9. What it should do in each market (hypotheses to test, not results)

| Market | Expected behaviour | What makes it work, or hurt |
|---|---|---|
| Strong bull market (2017, 2021, 2023–24) | Trails 100% equity by a few points a year | 40% is not in equities; managed futures and gold may be flat |
| Slow bear market (2000–02, 2008, 2022) | Much smaller loss than equities | The filter moves equity to cash within months; managed futures historically gained (2022: +27%); bonds held only if beating cash |
| Sudden crash and rebound (2020, April 2025) | A loss and a late re-entry | The filter whipsaws and momentum lags the rebound. Quality cushions it, and the crash-ladder variant is designed for this case. |
| Inflation shock (2022) | Bonds out via R4 | Gold and managed futures carry the defensive load |
| Sideways or choppy market | A slow bleed from whipsaws | Split dates (R1) reduce it; this is the price of crash protection |

Step 4 replaces this table with backtested numbers per regime.

---

## 10. Changes from v0.1

| v0.1 | v0.2 | Why (research report) |
|---|---|---|
| Healthcare, staples and Berkshire (30 of 50 equity points) | Broad world equity plus momentum and quality tilts | The defensive slice was a minimum-volatility bet, a style that lagged ~3.3 pts/yr over 2015–25 |
| QQQ growth bucket | Dropped | The same hindsight problem the four-stock pick had, at index level |
| Treasuries always held | Held only while beating cash (R4) | Bonds failed as a defence in 2022 |
| Swing engine: sector rotation + RSI(2), daily, ATR stops, VIX sizing | Replaced by monthly sleeves; ideas moved to the research sleeve (0% by default) | Short-horizon edges are the most decayed and most taxed; RSI(2)'s post-publication Sharpe is 0.68 vs 0.87 for buy-and-hold |
| Crash ladder on by default | A pre-registered variant only | No published evidence; four episodes can't validate it |
| "Never chase" limits at or below the prior close | Marketable limits ±0.5% | No supporting evidence; executing late "significantly hurt" TAA results |
| One rebalance date | Four split dates | Timing luck |
| 17 parameters with ranges to sweep | ~10, with pre-registered variants | Trial budget and minimum backtest length |
| Managed futures absent | 15% sleeve | The one genuine diversifier available as a UCITS ETF |

---

## 11. What would change the status

| Gate (ROADMAP) | Evidence required | Status |
|---|---|---|
| G4 · Portfolio backtest (Tests 1 and 3) | After-tax EUR results vs. the PEA world tracker and 60/40 across 1990s–2026, including 2000–02, 2008, 2020 and 2022 | ❌ not run |
| G5 · Momentum sleeve (Test 2) | Positive net excess return in the full history and in the held-out region | ❌ not run |
| G7 · Shadow run | Bot proposals match the backtest 100% | ❌ not run |
| G8 · Automation | Automated orders match the proposals; costs ≤ 1.5× the model | ❌ not run |
