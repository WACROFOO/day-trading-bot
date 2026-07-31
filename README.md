# Day Trading Bot

An intraday trading bot built from scratch. Early stage — architecture and strategy under active development.

## Status

🚧 Early stage. The paper-trading dashboard runs; the automated bot does not exist yet.

## Paper trading dashboard

A fully local, free manual paper-trading dashboard for the Ross Cameron
small-cap momentum strategy (`knowledge-base/strategies/`). You place the
simulated trades yourself — it is not a backtester and not an automated bot.

- Streamlit UI with 1-minute candlesticks, EMA9, VWAP, MACD (plotly)
- Live quotes and 1m bars via yfinance (small TTL cache)
- Simulated market fills with $0.02/share slippage; no shorting, no margin
- Position sizing: `shares = risk_budget / (entry - stop)` (strategy §7)
- Daily risk-rule panel (strategy §8): max daily loss 6%, 50% giveback,
  green-to-red, 3 consecutive losses
- SQLite persistence at `data/paper_trading.db` (created on first use)

### Setup

```bash
pip install -r requirements.txt
```

### Launch

```bash
streamlit run src/paper_trading/dashboard.py
```

### Tests

```bash
python -m pytest tests/
```

## Structure

```
src/paper_trading/   dashboard package (ledger, broker, indicators, risk, datafeed, dashboard)
tests/               test suite
knowledge-base/      strategy research and specs
```

## Disclaimer

This software is for research and educational purposes only. Nothing here is financial advice. Trading involves substantial risk of loss.
