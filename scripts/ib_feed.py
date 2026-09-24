#!/usr/bin/env python3
"""IBKR bars and quote for tape.py — the desk's own source, read-only.

The desk, the runner and the ledger have run on IBKR since 2026-09-08; this
module gives `tape.py` (and through it `now.py` and every hand check) the
same tape instead of Yahoo's. What it adds over Yahoo:

  * 1-minute bars INCLUDING extended hours with the real pre-market volume
    (Yahoo hides most of it — the oldest hole in the board)
  * real-time last / bid / ask from the paper session's subscription
  * the exchange HALTED flag, instead of a halt inferred from missing bars

History (why this file was dead until 2026-09-24): the first version was
written blind in the cloud container for `ib_insync`, port 7497, client 17,
behind an opt-in `IB_GATEWAY=1` that was never set on the Mac. The Mac runs
`ib_async` on port 4002. So `tape.py` silently fell back to Yahoo on every
call for six weeks while the desk next to it sat on IBKR. This version:

  * imports `ib_async` first, `ib_insync` as a fallback
  * takes the port from IBKR_PORT (what the desk and launchd set), else the
    first API port that answers: 4002 paper Gateway, 7497 paper TWS, 7496
    live TWS — labelled in the output either way
  * connects read-only as client 36 (27/28 desk, 29 preflight, 31 executor,
    32–35 probes and backfill): a second client id never disturbs the desk
  * is ON whenever a port answers. TAPE_SOURCE=yahoo forces Yahoo;
    IB_GATEWAY=0 does the same.

Everything falls back to Yahoo when the Gateway is unreachable, and
`tape.py` prints WHY, so the provenance line never lies about where a
number came from.
"""
import datetime as dt
import os
import socket
from zoneinfo import ZoneInfo

ET = ZoneInfo('America/New_York')

# load repo-root .env once (KEY=value lines) so IBKR_PORT set there works
# without shell exports — .env is gitignored, never pushed
_ENV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(_ENV):
    with open(_ENV) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _, _v = _line.partition('=')
                os.environ.setdefault(_k.strip(), _v.strip())

HOST = os.environ.get('IBKR_HOST', '127.0.0.1')
PORTS = ('4002', '7497', '7496')          # paper Gateway, paper TWS, live TWS
PORT_LABEL = {4002: 'paper gateway', 7497: 'paper TWS', 7496: 'LIVE TWS', 4001: 'LIVE gateway'}
CLIENT = int(os.environ.get('IBKR_TAPE_CLIENT_ID', '36'))
SESSION_START = dt.time(4, 0)             # bars before today's 04:00 ET are yesterday's

_port_cache: dict = {}


def port(env=None):
    """(port, how) — IBKR_PORT (or the older IB_PORT) when set; otherwise the
    first port that accepts a TCP connect, cached for the process so a
    watchlist of eight names probes once, not eight times. (None, why) when
    nothing listens."""
    env = os.environ if env is None else env
    forced = (env.get('IBKR_PORT') or env.get('IB_PORT') or '').strip()
    if forced:
        return int(forced), 'IBKR_PORT'
    if 'detected' in _port_cache:
        return _port_cache['detected']
    host = env.get('IBKR_HOST', HOST)
    for p in PORTS:
        try:
            with socket.create_connection((host, int(p)), timeout=0.4):
                _port_cache['detected'] = (int(p), 'detected')
                return _port_cache['detected']
        except OSError:
            continue
    _port_cache['detected'] = (None, 'no IBKR API port answers (4002/7497/7496)')
    return _port_cache['detected']


def enabled(env=None):
    """IBKR is the source whenever a Gateway answers, unless the operator
    forces Yahoo (TAPE_SOURCE=yahoo or IB_GATEWAY=0)."""
    env = os.environ if env is None else env
    if (env.get('TAPE_SOURCE') or '').lower() == 'yahoo' or env.get('IB_GATEWAY') == '0':
        return False
    return port(env)[0] is not None


def _lib():
    try:
        from ib_async import IB, Stock   # the desk's library
        return IB, Stock, 'ib_async'
    except ImportError:
        from ib_insync import IB, Stock  # the older name of the same library
        return IB, Stock, 'ib_insync'


def _to_et(x):
    """IBKR bar dates: tz-aware datetimes for intraday bars (formatDate=2),
    plain dates for daily bars, strings from some versions."""
    if isinstance(x, dt.datetime):
        return (x if x.tzinfo else x.replace(tzinfo=dt.timezone.utc)).astimezone(ET)
    if isinstance(x, dt.date):
        return dt.datetime.combine(x, dt.time(0, 0), tzinfo=ET)
    d = dt.datetime.fromisoformat(str(x).replace('Z', '+00:00'))
    return (d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)).astimezone(ET)


def bars_to_rows(bars, today=None):
    """IBKR 1-minute bars → tape.py rows [(ET datetime, o, h, l, c, v)],
    today's session only (from 04:00 ET), bars without a close dropped."""
    today = today or dt.datetime.now(ET).date()
    start = dt.datetime.combine(today, SESSION_START, tzinfo=ET)
    rows = []
    for b in bars or []:
        ts = _to_et(b.date)
        if ts < start:
            continue
        close = float(b.close or 0)
        if close <= 0:
            continue
        vol = b.volume
        rows.append((ts, float(b.open), float(b.high), float(b.low), close,
                     int(vol) if vol and vol > 0 else 0))
    return rows


def prev_close(daily, today=None):
    """The last regular-session close BEFORE today, from daily bars."""
    today = today or dt.datetime.now(ET).date()
    for b in reversed(list(daily or [])):
        if _to_et(b.date).date() < today and b.close and float(b.close) > 0:
            return float(b.close)
    return None


def fetch(sym, timeout=8):
    """Returns (rows, meta) in tape.py's shape, or raises.

    rows: [(datetime_ET, open, high, low, close, volume), ...] 1-min bars
    meta: {'last', 'prev', 'bid', 'ask', 'halted', 'quote_time', 'source',
           'port', 'port_label', 'lib', 'quote_error'}
    """
    p, how = port()
    if p is None:
        raise RuntimeError(how)
    IB, Stock, lib = _lib()
    ib = IB()
    ib.connect(HOST, p, clientId=CLIENT, readonly=True, timeout=timeout)
    try:
        c = Stock(sym, 'SMART', 'USD')
        ib.qualifyContracts(c)
        today = dt.datetime.now(ET).date()
        hist = ib.reqHistoricalData(
            c, endDateTime='', durationStr='1 D', barSizeSetting='1 min',
            whatToShow='TRADES', useRTH=False, formatDate=2)
        rows = bars_to_rows(hist, today)
        daily = ib.reqHistoricalData(
            c, endDateTime='', durationStr='5 D', barSizeSetting='1 day',
            whatToShow='TRADES', useRTH=True, formatDate=2)
        meta = {
            'last': rows[-1][4] if rows else None, 'prev': prev_close(daily, today),
            'bid': None, 'ask': None, 'halted': None, 'quote_error': None,
            'quote_time': dt.datetime.now(ET), 'source': 'ibkr',
            'port': p, 'port_label': PORT_LABEL.get(p, str(p)) + (' (IBKR_PORT)' if how == 'IBKR_PORT' else ''),
            'lib': lib,
        }
        # The quote is best effort: bars are the tape, the quote is a bonus.
        # 10197 (a competing live login holds the market data) kills the
        # quote and leaves history working — the desk saw exactly that.
        try:
            [t] = ib.reqTickers(c)
            if t.last and t.last > 0:
                meta['last'] = float(t.last)
            meta['bid'] = float(t.bid) if t.bid and t.bid > 0 else None
            meta['ask'] = float(t.ask) if t.ask and t.ask > 0 else None
            h = t.halted
            meta['halted'] = bool(h >= 1) if h is not None and h == h else None   # nan-safe
        except Exception as exc:          # noqa: BLE001
            meta['quote_error'] = f'{exc.__class__.__name__}: {str(exc)[:80]}'
        return rows, meta
    finally:
        ib.disconnect()


if __name__ == '__main__':
    import sys
    p, how = port()
    print(f"port {p} ({how}) client {CLIENT}")
    rows, meta = fetch(sys.argv[1].upper() if len(sys.argv) > 1 else 'AAPL')
    print(f"bars {len(rows)}  last {meta['last']}  prev {meta['prev']}  bid {meta['bid']} "
          f"ask {meta['ask']}  halted {meta['halted']}  quote_error {meta['quote_error']}")
    for r in rows[-3:]:
        print(r[0].strftime('%H:%M'), r[1:])
