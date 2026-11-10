# Data: where every number comes from

This covers ROADMAP Step 2. Everything is free, downloaded on demand into
`systematic/data/raw/` (gitignored), and **never committed**: MSCI and AQR data
are for personal research use.

## Run it

```bash
pip install -r systematic/requirements.txt
python systematic/scripts/fetch_data.py            # downloads what's missing, runs the checks
python systematic/scripts/fetch_data.py --refresh  # downloads everything again
python -m pytest systematic/tests                  # offline tests, no network
```

The script prints coverage, the Gate G2 checks and a summary per sleeve. It
exits with status 1 if any check fails.

## Raw sources

| Series | Source | Coverage |
|---|---|---|
| MSCI World, net, USD and EUR | MSCI end-of-month index levels (code 990100) | USD and EUR from Dec 2000; price index from 1997 |
| MSCI World Momentum, net, USD and EUR | MSCI (703755) | 1997 (USD), Dec 1998 (EUR); back-tested by MSCI before Dec 2013 |
| MSCI World Quality, net, USD and EUR | MSCI (702787) | Same as momentum; back-tested before launch |
| US factors, US momentum | Ken French data library | 1926+ |
| Time-series momentum (trend) | AQR data sets | 1985+ |
| US 10-year yield, 3-month T-bill | FRED (GS10, TB3MS) | 1953+, 1934+ |
| EUR/USD; DEM/USD before 1999 | FRED (DEXUSEU daily; EXGEUS monthly average) | 1971+ |
| 3-month Euribor | ECB Data Portal | 1994+ |
| Gold, commodity indices | World Bank Pink Sheet | 1960+ |

## Sleeve series (monthly, EUR, total return)

| Sleeve | How it is built | Weakest point |
|---|---|---|
| S1 world equity | MSCI's official EUR series from 2001; earlier, USD converted to EUR | Before Dec 2000 MSCI only serves the price index, so 1.5%/yr of net dividends is added |
| S2 momentum, S3 quality | Official EUR series from 1999; USD converted before | MSCI back-tests before each launch date |
| S4a trend fund | AQR trend factor scaled to 12% volatility, **excess return halved**, plus EUR cash, minus the fund's 0.75% fee | Paper factor. Unhaircut it compounds at ~11%/yr, against ~5–6%/yr for real trend funds since 2000 |
| S4b commodities | World Bank total commodity index, in EUR | Spot prices of monthly averages: no roll yield, no collateral return. The weakest proxy here |
| S5 Treasuries | Par bond with 8.5 years left, repriced monthly from the 10-year yield; hedged with the Euribor–T-bill carry | The yield is a monthly average, which slightly smooths returns |
| S6 gold | World Bank gold price in EUR | Monthly average prices, so drawdowns look shallower. To be replaced with month-end prices before the final Test 1 run |
| S7 cash | 3-month Euribor | Overnight-rate ETFs earn slightly less, net of their 0.10% fee |

## Gate G2 result (10 Nov 2026): 81 of 81 checks pass

- **Known answers:** MSCI World, World Momentum and World Quality match
  MSCI's published annual returns exactly, for all 13 years from 2013 to 2025.
- **Currency conversion:** our USD→EUR conversion matches MSCI's own EUR
  series to within 0.01% a year over 25+ years. Individual months differ by
  about 0.25 points, because FRED fixes the rate at noon New York and MSCI at
  4pm London. These differences reverse the following month (autocorrelation
  −0.5), so they are timing noise, not drift.
- **Structure:** no missing months, no gaps, month-end dates, and no
  unexplained monthly moves above 25% in the MSCI series.
- **Not yet checked:** each UCITS ETF's tracking against its index. That needs
  daily ETF prices (stage 3), and is listed as an open item in the roadmap.

## What the raw sleeve numbers say, and don't say

The fetch script prints each sleeve's CAGR, volatility and max drawdown since
its series starts. **These are not strategy results.** They are single assets
over different periods, before costs and tax, with no rules applied. Test 1
(ROADMAP Step 4) is where the portfolio is actually evaluated.
