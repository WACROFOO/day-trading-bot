# Rule spec v0.1 — two-engine systematic portfolio

**Verification status:** ❌ Not validated. These rules were designed in
conversation and have never been backtested. Every number is a **starting value
with a test range**, not a conclusion. ROADMAP.md Steps 4–5 decide what
survives.

This file is the single source of truth for the rules. Code implements exactly
what is written here, and any change to a rule is made here first, with a
version bump.

---

## 0. Assumptions

| Assumption | Why it matters | Confirm in |
|---|---|---|
| You are a **France tax resident** investing in **euros** (the PLAYBOOK is written in Paris time) | Every result is measured in EUR, because that is what you spend. Currency moves are part of the return. | ROADMAP Step 0 |
| You are a **retail client** under EU rules | EU brokers cannot sell US-domiciled ETFs (XLV, IEF, GLD, SPY, QQQ…) to retail clients, because the issuers don't publish the KID document the PRIIPs rules require. Live trading uses **UCITS equivalents**. Single US stocks (MSFT, BRK-B…) are fine. | Step 0 |
| Broker: **Interactive Brokers** (EU entity) | Has a Python API, a paper account, and UCITS ETFs plus US stocks in one account | Step 0 |
| Decisions run once per trading day, **after the US close** | End-of-day data is free and accurate (LESSONS A2) | — |

**Research vs. live instruments.** UCITS ETFs mostly launched after 2010, which
is too little history to test across 2000–02 or 2008. Backtests therefore use
the long-history US ETF (or an index/mutual-fund proxy before the ETF existed)
as the signal and return series. Live orders go to the UCITS equivalent. Step 2
checks that each pair actually tracks the same thing.

---

## 1. Engine 1 — Core (70% of capital)

### 1.1 Target weights (% of the core sleeve)

| Bucket | Holding | Target | Backtest series | Live instrument (choose in Step 2) |
|---|---|---|---|---|
| Defensive equity — 30 | Healthcare | 15 | XLV | S&P 500 Health Care sector UCITS ETF |
| | Consumer staples | 10 | XLP | S&P 500 Consumer Staples sector UCITS ETF |
| | Berkshire Hathaway | 5 | BRK-B | BRK-B |
| Growth — 20 | Quality growth | 15 | **QQQ** (see note) | Nasdaq-100 UCITS ETF *(default)* |
| | International value | 5 | EFV | Developed-markets value UCITS ETF |
| Treasuries — 20 | US Treasuries 7–10y | 20 | IEF | $ Treasury 7–10y UCITS ETF (hedged vs. unhedged is tested) |
| Gold — 10 | Physical gold | 10 | GLD | Physical gold ETC |
| Cash — 20 | Euro cash | 20 | EUR short rate | EUR money-market / overnight-rate ETF, **held at the broker** so the ladder can deploy it |

That is 50% equities / 20% bonds / 10% gold / 20% cash.

**Note on the growth bucket.** The earlier plan named Microsoft, Alphabet,
Amazon and TSMC. A backtest of four stocks picked *today* because they won is
pure hindsight: it would make the strategy look far better than anything we
could have known in 2005. So the growth bucket is tested with QQQ, and the
default live holding is the matching Nasdaq-100 ETF, which already holds those
names heavily. Holding the four stocks directly is allowed, but it is an
untested variant. If you choose it, the 5% single-stock cap (§3) applies.

### 1.2 Rules

**C1 · Hold by default.** No trade unless a rule below fires.

**C2 · Rebalancing bands (the 5/25 rule).** Every day, check each **bucket**
(not each holding). A bucket is out of band when its weight is off target by
**≥ 5 points absolute** or **≥ 25% of its target**, whichever is hit first.
(A flat 5-point band means nothing for the 10% gold bucket, because it would
have to double first.) An out-of-band bucket is traded back to target.

**C3 · Calendar rebalance.** On the first trading day of **January and July**,
rebalance every holding to target, including drift *within* buckets.

**C4 · Crash ladder.**
- Signal series: Nasdaq-100 (QQQ / ^NDX) drawdown from its all-time closing high.
- Three tranches, each worth **1/3 of the cash bucket's target** (6.7% of core).
- A tranche is **armed** the first time the drawdown reaches −20%, −30% or −40%.
- An armed tranche **fires** on the first close of QQQ above its 50-day SMA
  after arming. This is the "only buy once it stops falling" confirmation. At
  most one tranche fires per week.
- A fired tranche moves cash into the growth bucket *and moves the targets with
  it*: growth target +6.7, cash target −6.7. Fully deployed, the core is 70%
  equities and 0% cash. This is the "move toward 70% stocks after a crash"
  rule, made mechanical.
- **Reset:** when the Nasdaq-100 makes a new all-time closing high, targets
  revert to §1.1, and the bands sell the extra growth back into cash. You buy
  in the crash and refill the cash near the top.

**C5 · Trend filter.** While QQQ closes below its 200-day SMA, rebalancing may
not *buy* into the growth bucket; only ladder tranches can. Selling growth that
is above its band is still allowed. Defensive buckets are unaffected.

**C6 · Never chase.** Buy orders are limit orders at or below the previous
close. If one does not fill, the rule is re-evaluated the next day. That is
"no buying after big up-days" written as an order type. If the same rebalance
buy fails to fill for 5 sessions in a row, the limit moves to previous close
+0.5% (tested in Step 4).

**C7 · Minimum order.** Skip any order under max(€500, 0.5% of the portfolio),
so fees never dominate a trade.

---

## 2. Engine 2 — Swing (30% of capital)

### 2.1 Universe (v1)

| Role | Backtest series | Live |
|---|---|---|
| Momentum rotation | 11 SPDR sector ETFs: XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY (each from its inception) | S&P 500 sector UCITS ETFs (confirm availability per sector in Step 2) |
| Pullback | SPY, QQQ | S&P 500 and Nasdaq-100 UCITS ETFs |

**Why ETFs first, not stocks.** Large sector ETFs essentially never get
delisted, so the backtest has no survivorship bias. Free data for them is
clean, spreads are tight, and UCITS versions exist. A stock universe (v2) is
only worth testing with point-in-time index membership *and* price data for
delisted names, which free yfinance data does not have (LESSONS A3, A5).

### 2.2 Setup A — Momentum rotation

| | Rule |
|---|---|
| When | Last trading day of each month |
| Eligible | Close > 200-day SMA |
| Rank by | Total return over 126 trading days (~6 months) |
| Hold | Top **N = 3** eligible |
| Entry | Limit at the signal day's close, valid 3 sessions |
| Exit 1 | Trailing protective stop at **2 × ATR(20)** below the highest close since entry. Updated daily, only ever raised, and held **at the broker** |
| Exit 2 | Close below the 50-day SMA, so sell next session |
| Exit 3 | Falls out of the top 2N at the monthly ranking |

### 2.3 Setup B — Pullback in an uptrend

| | Rule |
|---|---|
| When | Daily |
| Entry | Close > 200-day SMA **and** RSI(2) < 10, so buy next session (limit at the signal close, valid 1 session) |
| Exit 1 | Close > 5-day SMA, so sell next session |
| Exit 2 | Time stop: 10 sessions |
| Exit 3 | Disaster stop at **3 × ATR(20)** below entry, held at the broker |
| Limit | One open position per instrument |

### 2.4 Sizing

```
risk_per_trade = 1% of Engine 2 equity            (halved while VIX closes > 30)
shares         = risk_per_trade / stop_distance   (2×ATR for A, 3×ATR for B)
position cap   = 20% of Engine 2 equity
max positions  = 5 (A and B combined)  ->  never more than 100% invested, no margin
```

The cap is not decoration. A sector ETF with a 1.5% ATR has a 3% stop distance,
so 1% risk means a 33% position. Without the cap, five positions would need
165% of the sleeve.

### 2.5 Brakes

- Engine 2 down **10% within a calendar month** → no new entries until next
  month. Exits keep working.
- Engine 2 down **20% from its peak** → no new entries at all; open positions
  run off through their normal exits. Restarts only after a review (the old
  project's walkaway rule, kept).

---

## 3. Portfolio-wide limits and kill switch

These live in the execution layer and apply to both engines. Modelled on
`src/paper_trading/risk_gate.py` (LESSONS B2–B4).

**Always:**
- No margin, no shorting, no leverage, no options.
- Entries are limit orders. Protective stops are GTC stop orders held at the
  broker (LESSONS B7).
- Max 10 orders per day, bot-wide.
- Max single order: 10% of the portfolio (fat-finger guard; the initial
  deployment happens in tranches, see ROADMAP Step 4).
- Max single stock: 5% of the portfolio. ETFs: 25%.

**Pre-trade checks.** All run before an order exists; any failure means no
order and an alert:
- **Fresh data:** the last bar is the last completed session per the exchange
  calendar.
- **Sane data:** no close moved more than 25% day-over-day without a recorded
  split.
- **Sane price:** the limit is within 3% of the last close.
- **Reconciled:** broker positions and cash match the internal ledger.
- **Explained P&L:** today's portfolio change matches yesterday's holdings ×
  today's prices to within 0.5%. A gap means a phantom fill, a wrong quantity
  or bad data.

**Kill switch.** Latched, persisted, and reset by a human only. While latched:
no new buys; exits and broker-held stops still work. Triggers:
- any unhandled exception in the daily run
- a reconciliation or explained-P&L mismatch
- 2 or more broker rejections in one day
- a failed data check
- portfolio down 4% or more in one day (pause and review; the ladder buys on
  recoveries, not on crash days, so this rarely blocks it)

**Alerts:** a daily summary, plus an immediate message on any latch.

---

## 4. Timing

| Event | New York | Paris (normal) |
|---|---|---|
| US close | 16:00 | 22:00 |
| Daily run: fetch data → signals → targets → orders | 17:00 | 23:00 |
| UCITS orders execute (Xetra/LSE) | — | from 09:00 next day |
| US-stock orders execute | 09:30 next day | 15:30 next day |

Jobs are scheduled in `America/New_York`, never in Paris time (LESSONS C4).

**No lookahead.** A signal computed from day *t*'s close is filled on day
*t+1* at the earliest: at the open, or at a resting limit if price trades
through it. Live UCITS fills happen earlier in the European day than the US
open the backtest assumes; Step 7 measures the difference.

---

## 5. Parameters

| Parameter | Start | Test range | Rule |
|---|---|---|---|
| `band_abs_pts` | 5 | 3–7 | C2 |
| `band_rel_pct` | 25 | 15–35 | C2 |
| `ladder_levels` | −20/−30/−40% | −15…−25 first step | C4 |
| `ladder_confirm_sma` | 50 | 20–100 | C4 |
| `trend_sma` | 200 | 150–250 | C5, A, B |
| `mom_lookback` | 126 | 63–252, ± skip last 21 | A |
| `mom_top_n` | 3 | 2–4 | A |
| `atr_stop_mult_A` | 2.0 | 1.5–4.0 | A |
| `exit_sma_A` | 50 | 20–100 | A |
| `rsi2_entry` | 10 | 5–20 | B |
| `exit_sma_B` | 5 | 3–10 | B |
| `time_stop_B` | 10 | 5–15 | B |
| `atr_stop_mult_B` | 3.0 | 2.0–5.0 | B |
| `risk_per_trade` | 1% | 0.5–1.5% | 2.4 |
| `vix_halve_above` | 30 | 25–40 | 2.4 |
| `position_cap` | 20% | fixed | 2.4 |
| `max_positions` | 5 | fixed | 2.4 |

`fixed` means a risk limit, not something to optimise. Ranges are for the
sensitivity check (ROADMAP Step 5): the chosen value has to sit on a plateau,
where its neighbours also work.

---

## 6. Changes from the chat version

The plan discussed in chat had seven issues that would have surfaced in
backtests or with real money:

1. **US ETFs can't be bought by EU retail clients.** XLV, IEF and GLD become
   UCITS equivalents live, with US data for research (§0).
2. **Euro investor.** Results are measured in EUR. Unhedged vs. EUR-hedged
   Treasuries is tested rather than assumed (§1.1).
3. **Hindsight in the growth picks.** The bucket is tested with QQQ, not four
   stocks chosen today (§1.1).
4. **A 5-point band does nothing for small slices.** Replaced by the 5/25 rule
   on buckets (C2).
5. **The trend filter conflicted with rebalancing.** Below the 200-day SMA,
   rebalancing may not buy growth; only the ladder can (C5).
6. **The VIX rule would have cancelled the crash ladder,** which buys precisely
   when VIX is high. VIX sizing now applies to Engine 2 only (§2.4).
7. **1% risk with ATR stops implied positions over 100%.** Positions are now
   capped at 20% of the sleeve (§2.4).

Also flagged for Step 4: **in 2022, stocks and Treasuries fell together.**
The bond bucket is not a guaranteed hedge, so 2022 is a mandatory stress
window.

---

## 7. What would change the status

| Gate (ROADMAP) | Evidence required | Status |
|---|---|---|
| G4 · Core backtest | Drawdown, return and ladder-value criteria met in EUR across 2000–02, 2007–09, 2020, 2022 | ❌ not run |
| G5 · Swing out-of-sample | Beats the S&P 500 in EUR, risk-adjusted, out-of-sample, at 2× costs, on a parameter plateau | ❌ not run |
| G7 · Paper | Signals match the backtest 100%; slippage ≤ 1.5× the model | ❌ not run |
| G8 · Live | Live results inside the backtest's range at each size step | ❌ not run |
