# paper_trading/ — manual practice platform

A local Streamlit app for trading the strategy BY HAND with simulated money.
Not a backtester, not a bot: you click the buttons. It exists so the risk
rules become habit before any real money is involved.

Launch: `streamlit run src/paper_trading/app.py`

| Module | What |
|---|---|
| `app.py` | The UI: Scanner / Charts / Trade / Journal / Risk tabs |
| `scanner.py` | NASDAQ universe scan against the five pillars |
| `datafeed.py` | Free quotes and bars (Yahoo) |
| `indicators.py` | VWAP, EMAs, MACD |
| `broker.py` | Simulated fills, positions, open orders |
| `risk.py` / `risk_gate.py` | The five daily rules (max loss 6%, giveback, green-to-red, 3 losses, drawdown walkaway) and the lockout latch |
| `ledger.py` | Trade journal and stats (win rate, expectancy, avg R) |

The order ticket enforces the documented sizing (`shares = risk / (entry −
stop)`, $0.20 max stop distance). Tests: `../../tests/`.
