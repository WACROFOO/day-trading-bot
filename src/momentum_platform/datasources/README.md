# datasources/

Feed adapters. Each returns the **same normalized records** the replay
fixtures use, so every scanner, chart and card behaves identically whichever
source is behind it.

| Module | What |
|---|---|
| `ibkr_stream.py` | the persistent read-only TWS connection (client 27): quotes, 5-second bars, BarStore, LIVE/STALE/DELAYED/OFFLINE health, reconnect and resubscribe |
| `ibkr_scanner.py` | the scanner union (client 28), common-stock filter, float from fundamentals |
| `alpaca_source.py` | free tier, standard library only: real-time IEX trades and 1-minute bars, history, news, the tradable universe |
| `yahoo_quotes.py` · `yfinance_source.py` | Yahoo quotes and bars |
| `sec_source.py` | EDGAR: shares outstanding and company country |
| `screener.py` | the discovery screen |
| `live_session.py` | assembles a live session from a source |
| `replay.py` | plays a recorded fixture back as if live |
| `tls.py` | certificate handling, so a CA failure is distinguishable from a network block |

**Shares outstanding is not float.** It is an upper bound: under the cap
proves float is under the cap; over the cap proves nothing. The label travels
with the number.
