# Free APIs — what to sign up for, and what each one actually fixes

```
CHECKED 2026-08-24 from this container. Vendor claims are quoted from the
docs pages named below; everything marked MEASURED was requested and the
response inspected. Free tiers change — re-run `python3 run.py verify`
after adding any key rather than trusting this page.

✓ REMEDIATED 2026-08-24 — a free Massive key was supplied and the five
  decisive checks now PASS. The verification output is below in §2a and in
  results/provider_verification.json. The Yahoo limitations in
  data_quality.md are no longer the study's constraint; they are kept there
  as the record of what was wrong and how it was found.
```

**Short answer: one free key does it — Massive (formerly Polygon.io), the
free "Stocks Basic" plan.** It fixes all three of the blockers in
`data_quality.md`, at 2 years of history instead of 5. A second free key
(Alpaca) is worth having as a cross-check. Nothing else is needed to run
this study, and no money is needed either.

---

## 1. The blockers, and which free tier clears each

| blocker (measured on Yahoo) | Massive free | Alpaca free | Alpha Vantage free |
|---|:-:|:-:|:-:|
| 1-minute history beyond 25 days | **✓ 2 years** | **✓ since 2016** | **✓ ~2 years** |
| extended-hours bars **with volume** | **✓** | ✓ (IEX-only volume) | ✓ `extended_hours=true` |
| delisted tickers retained | **✓** | UNKNOWN | UNKNOWN |
| point-in-time symbol list incl. delisted | **✓** | ✗ | partial (`LISTING_STATUS`) |
| consolidated tape (not one exchange) | **✓** | see §3 | claimed |
| cost | **$0** | $0 | $0 |
| throughput | 5 calls/min | 200 calls/min | **25 calls/DAY** |

---

## 2a. MEASURED on a real free key — all five checks pass

`python3 run.py verify --provider polygon`, 2026-08-24:

```
[1] pre-market VOLUME on 2026-08-21 (AAPL)
    252 pre-market bars, 252 carry volume            -> PASS
[2] delisted retention
    MULN   229 daily bars · SIVBQ  51 daily bars     -> PASS
    BBBYQ / ATVI  0 bars — both delisted in 2023, i.e. OUTSIDE the free
    plan's 2-year window. Not a retention failure; a depth limit.
[3] minute-bar history depth (AAPL)
     30d back  791 bars ·  90d  866 ·  365d  642 ·  700d  746
    1200d back    0 bars   -> the 2-year boundary, exactly as documented
[4] point-in-time symbol list
    5,000 INACTIVE tickers listed a year ago         -> PASS
[5] halt feed
    100 records in the rolling Nasdaq RSS window     -> live
```

Also measured directly:

| thing | result |
|---|---|
| `grouped_daily` on one date | **12,483 tickers in one 1.8s call** |
| grouped-daily history boundary | 2024-08-26 works, 2024-08-01 returns nothing → **exactly 2 years** |
| rate limit | **5 calls/min, enforced by HTTP 429** |

**A defect this turn, recorded because it is the kind that hides:** a 429
comes back as *valid JSON* with no `results` key. `json.loads` succeeds and
`.get("results", [])` returns an empty list, so a throttled request was
becoming "no data for this date" — a silent hole in the universe. `_curl2`
now returns the HTTP status, `PolygonProvider._get` treats 429 and
`status: ERROR` as retryable, and five poisoned cache entries written before
the fix were purged. **Status codes are never optional when the error path is
also valid JSON.**

---

## 2. Massive / Polygon.io — free "Stocks Basic" · **get this one**

Sign up: <https://massive.com> (the site rebranded from polygon.io in 2026;
`api.polygon.io` still answers, which is why `src/data.py` needed no change).

```bash
export POLYGON_API_KEY=...        # MASSIVE_API_KEY also accepted
python3 run.py verify --provider polygon
```

**What the free plan includes** — quoted from the vendor docs, checked
2026-08-24:

| claim | source |
|---|---|
| minute aggregates are *"Included in all Stocks plans"* — Basic, Starter, Developer, Advanced | `massive.com/docs/rest/stocks/aggregates/custom-bars` |
| bars cover *"pre-market, regular market, and after-hours sessions"* | same |
| **2 years** of history on Basic; 5 years on Starter ($29/mo) | `massive.com/pricing` |
| **5 API calls / minute** on Basic; unlimited on Starter | same |
| data recency on Basic is **end-of-day** | custom-bars docs |
| grouped daily returns *"all U.S. stocks on a specified trading date"* in ONE call, *"Included in all Stocks plans"* | `massive.com/docs/rest/stocks/aggregates/daily-market-summary` |
| the tickers reference takes `date=` and `active=false`, returns names since delisted with a `delisted_utc` field, *"Included in all Stocks plans"*, history back to 2003-09-10 | `massive.com/docs/rest/stocks/tickers/all-tickers` |

Four things follow, and they matter:

1. **End-of-day recency is not a limitation here.** A historical backtest
   wants yesterday and older. The free plan's only real cost is throughput.
2. **The 5-calls/minute limit is affordable because of grouped daily.**
   Building the four-year universe costs one call *per date*, not per
   symbol: ~500 trading days in two years ≈ **1.7 hours**, versus 22 hours
   if it were 6,742 symbol requests. `PolygonProvider.grouped_daily()` is
   written for exactly this and the throttle is built in.
3. **Minute bars cost one call per ticker-MONTH, not per ticker-day.** The
   aggregate limit is 50,000 bars and a month of 1-minute extended-hours
   data is ~20,000, so `PolygonProvider.minute_month()` pulls a whole month
   in one request and serves every day out of it — including the prior
   sessions the RVOL-at-time denominator needs, which would otherwise have
   cost three extra calls each. That is the difference between a study that
   fits the free tier and one that does not.
4. **`active=false` with a past `date` is the survivorship fix.** It is the
   single thing Yahoo cannot do at any price, and it is on the free plan.

Request `adjusted=false` for intraday and apply `/v3/reference/splits`
separately — that keeps a reverse split from fabricating a gap. The adapter
already does this.

**What it still does not give:** halts (§5), point-in-time float (§6), and
quotes/NBBO are a paid endpoint, so the spread stays a proxy.

---

## 3. Alpaca — free "Basic" · worth having as a second opinion

Sign up at <https://alpaca.markets> (a paper account is enough; no funding).

```bash
export ALPACA_API_KEY_ID=...
export ALPACA_API_SECRET_KEY=...
export ALPACA_FEED=sip            # see the caveat below
python3 run.py verify --provider alpaca
```

| claim | source |
|---|---|
| historical data *"since 2016"*, 200 requests/min on Basic | `docs.alpaca.markets/docs/about-market-data-api` |
| real-time on Basic is **IEX only** — *"approximately 2.5% of US equity volume"* | Alpaca support / community |
| *"For historical queries, the `end` parameter must be at least 15 minutes old to query SIP data without a subscription"* | `docs.alpaca.markets/us/docs/market-data-faq` |
| the default `feed` is *"the 'best' available feed based on the user's subscription"* — which for a free account means IEX unless `feed=sip` is passed explicitly | same |

**MEASURED 2026-08-25 on a real free Basic key — the claim holds.**

```
IEX vs SIP, same symbol, same session, free account:

  SGLY 2026-08-20   iex   188 bars   total volume        91,167
                    sip   827 bars   total volume    45,041,453
  AAPL 2026-08-20   iex   392 bars   total volume     1,163,164
                    sip   821 bars   total volume    41,127,645

history depth (feed=sip, one RTH session, 100-bar probe):
  2026 · 2025 · 2024 · 2022 · 2020 · 2018 · 2016  -> ALL return data

rate limit: 30 rapid calls, 0 rejected, 5.1s -> 351 calls/min observed
            (documented 200/min; this study throttles to 180)
```

Three things follow, and the middle one is a warning worth repeating:

1. **A free Alpaca account reads consolidated SIP historical bars back to
   2016 at 180+ calls/min.** That is 5 years deeper and 36x faster than the
   Massive free tier, and it is what made an eleven-year intraday study
   possible at all.
2. **IEX is 0.2% of consolidated volume on a small cap** — not the ~2.5%
   quoted for the market as a whole — and it carries **23% of the minutes**.
   Never compute RVOL on it. Worse for this study specifically: a feed
   missing 77% of the minutes will miss the print that formed the session
   high, and the entry trigger *is* a high.
3. **The month-end clamp matters.** A free account may only read SIP when
   `end` is at least 15 minutes old. For the CURRENT month the month-end is
   in the future, and the request silently returns nothing rather than
   erroring. `minute_month()` clamps `end` to now-20min; without it the most
   recent month is quietly empty.

Alpaca also has a free news API back to 2015, which is the only realistic
free route to the catalyst analysis (`final_report.md` records it as
impossible; it becomes possible with that key).

### What Alpaca does NOT give — and why both keys are needed

`run.py verify --provider alpaca` fails one check that Massive passes:
**there is no point-in-time symbol list.** Alpaca's `/v2/assets` is
current-state. That single endpoint — Massive's
`/v3/reference/tickers?date=&active=false` — is the whole survivorship fix,
and it is why this study uses **Massive for the universe and Alpaca for the
bars**. Neither alone is sufficient:

| | Massive free | Alpaca free |
|---|:-:|:-:|
| point-in-time symbol list incl. delisted | **✓** | ✗ |
| historical ticker list with `delisted_utc` | **✓** (12,613 tickers, 6,701 delisted) | ✗ |
| grouped daily (whole market, one call) | **✓** | ✗ |
| minute-bar depth | 2 years | **✓ 2016** |
| throughput | 5/min | **✓ 180+/min** |

### Cross-check: the two feeds agree exactly

28 shared RTH sessions compared bar-for-bar: **identical minute counts,
identical session highs and lows, volume within 0.7%, zero disagreements.**
Two independent consolidated sources agreeing is the defence this repo
lacked when a stitched-window adjustment fabricated +10,555% gaps
(`research/momentum-replication/HISTORY.md` defect 1). Running one feed
unchecked is how that happened; running two is cheap.

---

## 4. Alpha Vantage — free, but 25 requests/day

Sign up: <https://www.alphavantage.co/support/#api-key>.

MEASURED: the shared `demo` key refuses real queries
(`"The **demo** API key is for demo purposes only"`), so a personal key is
required to test anything. The free tier is **25 API requests per day**
(`alphavantage.co/premium`).

One request of `TIME_SERIES_INTRADAY` with `month=YYYY-MM&outputsize=full&
extended_hours=true` returns a **whole ticker-month of 1-minute bars**, so 25
requests/day is not as small as it sounds — it is roughly 25 ticker-months
per day. Still far too slow to be the primary source for 3,000 ticker-days,
but genuinely useful as an **independent cross-check**: pull the same ten
ticker-days from Alpha Vantage and from Massive and compare the highs, lows
and volumes. Two sources agreeing is the only cheap defence against a silent
feed defect, and this repo has been burned by one before
(`research/momentum-replication/HISTORY.md` defect 1).

---

## 5. Halts — free, but only going forward

**MEASURED 2026-08-24:** `https://www.nasdaqtrader.com/rss.aspx?feed=tradehalts`
returns 200 with no key and carries, per halt: symbol, halt date, halt time
to the millisecond, reason code, resumption date, resumption quote time and
resumption trade time.

```
DAIC · 08/24/2026 15:21:45.456 · LUDP · resume 15:21:45
PSIG · 08/24/2026 15:14:41.026 · LUDP · resume trade 15:19:41
reason codes seen: LUDP 69 · T12 12 · T3 10 · M 6 · H11 2
```

**The catch, and it decides how this can be used: it is a rolling window, not
an archive.** The feed held 99 items spanning a handful of dates. There is no
historical download, so this cannot backfill halt flags on a two-year study.

Poll it daily into a local table and the halt model becomes real for every
session *after* you start. Sessions before that stay `halt_flag = UNKNOWN`,
which is what `final_report.md` §15 already reports. `NasdaqHaltFeed.fetch()`
in `src/data.py` parses it; wiring a daily cron is a small, separate job.

This matters more than it looks. A stop cannot execute while a stock is
halted, and these names halt on exactly the moves the strategy hunts — a
LULD pause above the stop that reopens below it is a loss the current model
books at the stop price and therefore understates.

---

## 6. What no free tier fixes

| gap | why | the paid answer |
|---|---|---|
| **point-in-time float** | float ≠ shares outstanding, and vendors serve a current snapshot. EDGAR is free and has cover-page shares outstanding, but reconstructing *float* on a given past date in a universe that dilutes constantly is a project, not an API call | a fundamentals vendor with as-of snapshots; still needs auditing |
| **quotes / NBBO** | a paid endpoint everywhere. Without it the spread stays a 25th-percentile-of-ranges proxy, and that proxy drives the slippage model, which drives the headline number | Massive Advanced, or Databento |
| **tick / trade data** | the only thing that resolves the **30.6% of fills that are intrabar-ambiguous** — three studies in this repo now measure that at 25–31% | Databento (see below) |
| **halt archive** | see §5 | a vendor halt feed, or accumulate the free RSS from today |

**Databento** is worth naming because it is pay-as-you-go rather than a
subscription: **$125 in free credits on signup, expiring after 6 months**
(`databento.com/pricing`, checked 2026-08-24), billed per GB. That is not a
free tier, but it is enough to buy one scoped pull of trades-and-quotes for a
few hundred ticker-days — which is precisely what would settle the ambiguity
question that 1-minute OHLC cannot. Adapter not written; it would be a day's
work if that question becomes the priority.

---

## 7. Recommended order

1. **Massive free key.** Ten minutes. Then `python3 run.py verify --provider
   polygon` and read the five checks.
2. If it passes, `run.py universe --provider polygon --start 2024-08-01
   --end 2026-08-21` (grouped daily, ~1.7h), then `run.py ablation
   --provider polygon --days 500` overnight. That is the brief's sample
   target, on a free key.
3. **Alpaca free key** in parallel, and settle the SIP-on-free question. If
   it holds, history extends to 2016 and throughput goes up 40×.
4. **Alpha Vantage key** for a ten-ticker-day cross-check of the other two.
   Do this before believing any number, not after.
5. Start the halt poller whenever convenient. Its value compounds.
6. Only then consider paying: $29/mo Massive Starter buys 5 years and
   removes the throttle; $125 of Databento credit buys the answer to the
   ambiguity question.

**Nothing above changes a line of the strategy code.** The provider is one
seam (`src/data.py`), the config is frozen and hashed, and the 33 tests do
not care where bars come from. The study re-runs with a `--provider` flag.
