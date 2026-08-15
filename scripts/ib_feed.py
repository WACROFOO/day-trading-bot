#!/usr/bin/env python3
"""IBKR real-time feed for tape.py — runs ONLY next to a local IB Gateway.

Requires: IB Gateway (or TWS) logged into the PAPER account, API enabled,
port 7497, Read-Only API ON, and `pip3 install ib_insync`. Activated by
IB_GATEWAY=1 in the environment (via .env); everything falls back to yahoo
silently-but-labelled when the gateway is unreachable.

What this adds over yahoo:
  * true real-time last / bid / ask (subscription-gated)
  * 1-min bars INCLUDING extended hours with real pre-market volume
    (yahoo hides most of it — the board's oldest hole)
  * the HALTED flag, straight from the exchange feed — tape.py currently
    infers halts from missing bars; this is the real thing

UNTESTED against a live gateway as of 2026-08-15 — written blind in the
cloud container, which cannot reach a localhost gateway. First local run
is the test: report errors back.
"""
import datetime as dt
import os
from zoneinfo import ZoneInfo

ET = ZoneInfo('America/New_York')

# load repo-root .env once (KEY=value lines) so IB_GATEWAY=1 set there works
# without shell exports — .env is gitignored, never pushed
_ENV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(_ENV):
    with open(_ENV) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _, _v = _line.partition('=')
                os.environ.setdefault(_k.strip(), _v.strip())

PORT = int(os.environ.get('IB_PORT', '7497'))   # 7497 paper / 7496 live


def enabled():
    return os.environ.get('IB_GATEWAY') == '1'


def fetch(sym, timeout=8):
    """Returns (rows, meta) in tape.py's shape, or raises.

    rows: [(datetime_ET, open, high, low, close, volume), ...] 1-min bars
    meta: {'last':, 'prev':, 'bid':, 'ask':, 'halted':, 'quote_time':,
           'source': 'ibkr'}
    """
    from ib_insync import IB, Stock, util  # import here: optional dep

    ib = IB()
    ib.connect('127.0.0.1', PORT, clientId=17, timeout=timeout)
    try:
        c = Stock(sym, 'SMART', 'USD')
        ib.qualifyContracts(c)

        bars = ib.reqHistoricalData(
            c, endDateTime='', durationStr='1 D', barSizeSetting='1 min',
            whatToShow='TRADES', useRTH=False, formatDate=2)
        rows = [(b.date.astimezone(ET), b.open, b.high, b.low, b.close,
                 int(b.volume) if b.volume and b.volume > 0 else 0)
                for b in bars]

        [t] = ib.reqTickers(c)
        prev_bars = ib.reqHistoricalData(
            c, endDateTime='', durationStr='2 D', barSizeSetting='1 day',
            whatToShow='TRADES', useRTH=True, formatDate=2)
        prev = prev_bars[-2].close if len(prev_bars) >= 2 else None

        meta = {
            'last': t.last if t.last and t.last > 0 else (rows[-1][4] if rows else None),
            'prev': prev,
            'bid': t.bid if t.bid and t.bid > 0 else None,
            'ask': t.ask if t.ask and t.ask > 0 else None,
            # ib_insync: 0/nan = trading, >=1 = halted
            'halted': bool(t.halted and t.halted >= 1),
            'quote_time': dt.datetime.now(ET),
            'source': 'ibkr',
        }
        return rows, meta
    finally:
        ib.disconnect()


if __name__ == '__main__':
    import sys
    rows, meta = fetch(sys.argv[1].upper() if len(sys.argv) > 1 else 'AAPL')
    print(f"bars {len(rows)}  last {meta['last']}  bid {meta['bid']} "
          f"ask {meta['ask']}  halted {meta['halted']}")
    for r in rows[-3:]:
        print(r[0].strftime('%H:%M'), r[1:])
