# datasources/

Feed adapters. Each returns the **same normalized records** the replay
fixtures use, so every scanner, chart and card behaves identically whichever
source is behind it.

| Module | What |
|---|---|
| `ibkr_stream.py` | the persistent read-only TWS connection (client 27): quotes, 5-second bars, BarStore, LIVE/STALE/DELAYED/OFFLINE health, reconnect and resubscribe |
| `ibkr_tape.py` | the Time & Sales feed: tick-by-tick `Last` + `BidAsk` for the ONE selected name on the same read-only connection, 15-s IBKR pacing per name, history behind a new focus, refusals and reconnects said on the tape (2026-10-08) |
| `ibkr_scanner.py` | the scanner union (client 28), common-stock filter, float from fundamentals |
| `filings_news.py` | SEC 8-K/6-K filings and finviz's "why is it moving" line as headlines; the filings list behind the card's dilution flags |
| `instrument_facts.py` | the split test, instrument type and tick size the cascade's gates 5–7 need |
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
