"""A fake ib_async.IB surface for offline tests of the IBKR desk and scanner.

It answers every request the modules make (scanner data, snapshots, daily
and minute history, real-time bars, tickers) from data the test seeds, and
records readonly/clientId on connect so the read-only invariant is testable.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

UTC = timezone.utc


class FakeEvent:
    def __init__(self):
        self.handlers = []

    def __iadd__(self, fn):
        self.handlers.append(fn)
        return self

    def emit(self, *args):
        for h in list(self.handlers):
            h(*args)


class FakeBarList(list):
    def __init__(self, contract):
        super().__init__()
        self.contract = contract
        self.updateEvent = FakeEvent()


class Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class FakeTicker:
    def __init__(self, last=math.nan, close=math.nan, bid=math.nan, ask=math.nan, volume=math.nan,
                 mdt=1, time=None):
        self.last, self.close, self.bid, self.ask, self.volume = last, close, bid, ask, volume
        self.lastSize = 0
        self.marketDataType = mdt
        self.time = time

    def marketPrice(self):
        return self.last


class FakeIB:
    """Seed with `daily` {sym: [(date, o,h,l,c,v)]}, `minutes` {sym: [(dt, o,h,l,c,v)]},
    `fives` {sym: [(dt, ...)]} for backfill, `quotes` {sym: FakeTicker},
    `scans` {code: [sym, ...]}, `names` {sym: longName}."""

    def __init__(self, daily=None, minutes=None, fives=None, quotes=None, scans=None,
                 names=None, fail_connects=0, delayed=()):
        self.daily, self.minutes, self.fives = daily or {}, minutes or {}, fives or {}
        self.quotes, self.scans, self.names = quotes or {}, scans or {}, names or {}
        self.fail_connects = fail_connects
        self.delayed = set(delayed)
        self.connected = False
        self.connect_calls = []
        self.md_type = None
        self.tickers = {}
        self.bar_lists = {}
        self.live_lines = []
        self.cancelled = []
        self.hist_calls = []
        self.scan_calls = []
        self.slept = 0.0
        self.client = Obj(serverVersion=lambda: 178)

    # -- connection
    def connect(self, host, port, clientId, readonly=False, timeout=0):
        self.connect_calls.append({"host": host, "port": port, "clientId": clientId,
                                   "readonly": readonly, "timeout": timeout})
        if self.fail_connects > 0:
            self.fail_connects -= 1
            raise ConnectionRefusedError("TWS not listening")
        self.connected = True

    def disconnect(self):
        self.connected = False

    def isConnected(self):
        return self.connected

    def reqMarketDataType(self, n):
        self.md_type = n

    def sleep(self, seconds):
        self.slept += seconds
        return True

    # -- contracts
    def qualifyContracts(self, *contracts):
        for c in contracts:
            c.longName = self.names.get(c.symbol)
        return list(contracts)

    # -- market data
    def reqMktData(self, contract, *args):
        t = self.tickers.setdefault(contract.symbol, self.quotes.get(contract.symbol) or FakeTicker())
        self.live_lines.append(("mkt", contract.symbol))
        return t

    def cancelMktData(self, contract):
        self.cancelled.append(("mkt", contract.symbol))

    def reqTickers(self, *contracts, regulatorySnapshot=False):
        out = []
        for c in contracts:
            t = self.quotes.get(c.symbol) or FakeTicker()
            if c.symbol in self.delayed:
                t.marketDataType = 3
            out.append(t)
        return out

    def reqRealTimeBars(self, contract, size, what, use_rth):
        assert size == 5 and what == "TRADES"
        lst = FakeBarList(contract)
        self.bar_lists[contract.symbol] = lst
        self.live_lines.append(("rtb", contract.symbol))
        return lst

    def cancelRealTimeBars(self, lst):
        self.cancelled.append(("rtb", lst.contract.symbol))

    def reqHistoricalData(self, contract, end, duration, size, what, use_rth, formatDate=2, **kw):
        self.hist_calls.append((contract.symbol, duration, size, use_rth))
        sym = contract.symbol
        if size == "1 day":
            return [Obj(date=d, open=o, high=h, low=l, close=c, volume=v) for d, o, h, l, c, v in self.daily.get(sym, [])]
        if size == "1 min":
            return [Obj(date=d, open=o, high=h, low=l, close=c, volume=v) for d, o, h, l, c, v in self.minutes.get(sym, [])]
        if size == "5 secs":
            return [Obj(date=d, open=o, high=h, low=l, close=c, volume=v) for d, o, h, l, c, v in self.fives.get(sym, [])]
        return []

    # -- scanner
    def reqScannerData(self, sub, *args, **kw):
        self.scan_calls.append((sub.scanCode, sub.locationCode, sub.abovePrice, sub.belowPrice, sub.numberOfRows))
        hits = []
        for i, sym in enumerate(self.scans.get(sub.scanCode, [])):
            c = Obj(symbol=sym, primaryExchange="NASDAQ", exchange="SMART", currency="USD")
            hits.append(Obj(rank=i, contractDetails=Obj(contract=c, longName=self.names.get(sym))))
        return hits

    # -- test helpers
    def push_bar(self, symbol, ts, o, h, l, c, v):
        lst = self.bar_lists[symbol]
        lst.append(Obj(time=ts, open_=o, high=h, low=l, close=c, volume=v))
        lst.updateEvent.emit(lst, True)


def day_bars(n=30, last_close=4.0, today="2026-09-03"):
    """n completed daily bars ending the day before `today`, closes rising to last_close."""
    end = datetime.fromisoformat(today).date()
    out = []
    for i in range(n, 0, -1):
        d = end - timedelta(days=i)
        c = last_close - 0.01 * i
        out.append((d.isoformat(), c - 0.05, c + 0.1, c - 0.1, c, 100_000 + i * 1000))
    return out


def minute_bars(start: datetime, n: int, price=4.0, vol=2000):
    out = []
    for i in range(n):
        p = price + 0.01 * i
        out.append((start + timedelta(minutes=i), p, p + 0.02, p - 0.02, p + 0.01, vol))
    return out
