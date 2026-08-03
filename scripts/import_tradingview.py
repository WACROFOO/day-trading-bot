#!/usr/bin/env python3
"""Convert a TradingView "Export chart data" CSV into the engine's bar cache.

Why this exists: the project's central open question is that his entries happen
on a 10-second chart (NEXT-STEPS.md sec.5) and free 1-minute data cannot
represent them. TradingView Premium charts seconds-based intervals AND can
export the loaded bars as CSV. That is a route to sub-minute bars without a
market-data subscription.

The exported CSV is whatever the chart was showing, so it carries two things
worth having:

  * OHLCV at the chart's interval - 10S, 1, 5, whatever was selected
  * one column per indicator on the pane at export time

The indicator columns are not decoration. If VWAP was on the chart, the export
contains TradingView's VWAP alongside ours, which is the cheapest way to settle
whether his VWAP includes pre-market (reports/2026-08-vwap-condition.md).
Those columns are written to a sidecar rather than dropped.

Input format varies by TradingView version. Both are handled:
  time,open,high,low,close,Volume,...        # time = unix seconds
  time,open,high,low,close,Volume,...        # time = ISO-8601 with offset

Timezone: bars are bucketed into sessions by US/Eastern, because that is what
the engine's session windows mean. A naive timestamp is ASSUMED to be Eastern
already - set the chart's timezone to New York before exporting, or pass
--tz to say what it actually was.

Usage:
    python scripts/import_tradingview.py CUPR_10S.csv --symbol CUPR
    python scripts/import_tradingview.py CUPR.csv --symbol CUPR --interval 10s
    python scripts/import_tradingview.py *.csv --dry-run
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
from collections import Counter, defaultdict
from zoneinfo import ZoneInfo

ET = ZoneInfo('America/New_York')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'research', 'momentum-replication', 'data', 'bars_cache')
SIDECAR = os.path.join(ROOT, 'research', 'momentum-replication', 'data', 'tv_indicators')

# The engine's session window. Bars outside it are 'pre' - which on this data
# also collects after-hours, exactly as the Yahoo path does.
OPEN, CLOSE = dt.time(9, 30), dt.time(16, 0)

OHLCV = {'open': 'o', 'high': 'h', 'low': 'l', 'close': 'c', 'volume': 'v'}


def parse_time(raw, tz):
    """TradingView writes either unix seconds or an ISO-8601 string."""
    raw = raw.strip()
    if re.fullmatch(r'-?\d+', raw):
        return dt.datetime.fromtimestamp(int(raw), ET)
    # fromisoformat handles the offset form; a naive value means the chart was
    # showing wall-clock in some timezone and did not say which.
    t = dt.datetime.fromisoformat(raw.replace('Z', '+00:00'))
    return t.astimezone(ET) if t.tzinfo else t.replace(tzinfo=tz).astimezone(ET)


def dedupe(header):
    """TradingView names a column after the indicator, so two EMAs on the pane
    both export as "EMA". csv.DictReader would silently keep only the last one.
    Suffix repeats instead: EMA, EMA.2, EMA.3."""
    seen, out = {}, []
    for h in header:
        h = h.strip()
        seen[h] = seen.get(h, 0) + 1
        out.append(h if seen[h] == 1 else f'{h}.{seen[h]}')
    return out


def read_csv(path, tz):
    """-> (bars, indicator_rows, extra_column_names)"""
    with open(path, newline='') as f:
        raw = list(csv.reader(f))
    if len(raw) < 2:
        raise ValueError(f'{path}: empty')
    header = dedupe(raw[0])
    rows = [dict(zip(header, r)) for r in raw[1:] if any(x.strip() for x in r)]

    cols = {c.lower(): c for c in header}
    tcol = cols.get('time') or cols.get('date') or cols.get('datetime')
    if not tcol:
        raise ValueError(f'{path}: no time column in {list(rows[0])}')
    missing = [k for k in OHLCV if k not in cols]
    if missing:
        raise ValueError(f'{path}: missing {missing}. Export from a chart pane, '
                         'not from the screener.')

    extra = [c for c in header
             if c.lower() not in OHLCV and c != tcol]

    bars, ind = [], []
    for r in rows:
        # TradingView pads columns with NaN before an indicator warms up, and
        # writes empty cells for bars with no trades. Either makes float() throw;
        # a bar with no close is not a bar.
        try:
            vals = {k: float(r[cols[name]])
                    for name, k in OHLCV.items() if r[cols[name]].strip()}
        except ValueError:
            continue
        if 'c' not in vals:
            continue
        t = parse_time(r[tcol], tz)
        bars.append(dict(dt=t, o=vals.get('o', vals['c']), h=vals.get('h', vals['c']),
                         l=vals.get('l', vals['c']), c=vals['c'], v=vals.get('v', 0)))
        if extra:
            # TradingView writes NaN for bars before an indicator has warmed up.
            # Keeping the literal string would hand downstream code a value that
            # is neither a number nor absent.
            ind.append(dict(t=t.isoformat(),
                            **{c: r[c] for c in extra
                               if r[c].strip() and r[c].strip().lower() != 'nan'}))
    bars.sort(key=lambda b: b['dt'])
    return bars, ind, extra


def to_cache(bars):
    """Bucket into the {day: {pre: [], session: []}} shape run20 caches."""
    days = defaultdict(lambda: dict(pre=[], session=[]))
    for b in bars:
        side = 'session' if OPEN <= b['dt'].time() < CLOSE else 'pre'
        days[b['dt'].strftime('%Y-%m-%d')][side].append(
            dict(t=b['dt'].isoformat(), o=b['o'], h=b['h'],
                 l=b['l'], c=b['c'], v=b['v']))
    return dict(days)


def infer_interval(bars):
    """The MODE of the bar spacing, not the median.

    TradingView emits a bar only where a trade occurred, so a thin name is full
    of holes: LNAI exported at 1-minute had a median gap of 240s across 12 days
    and the median read it as a 4-minute chart. The most common gap is the
    interval; everything larger is a hole.
    """
    if len(bars) < 3:
        return None
    gaps = Counter((bars[i + 1]['dt'] - bars[i]['dt']).total_seconds()
                   for i in range(len(bars) - 1))
    s = gaps.most_common(1)[0][0]
    return f'{int(s)}s' if s < 60 else f'{int(s // 60)}m'


def sparsity(bars, interval_s):
    """Fraction of in-session slots with no bar at all. The engine's EMA/MACD
    advance once per bar, so a gappy series silently ages the indicators faster
    than wall-clock - worth printing rather than discovering later."""
    got = missing = 0
    by_day = defaultdict(list)
    for b in bars:
        if OPEN <= b['dt'].time() < CLOSE:
            by_day[b['dt'].date()].append(b['dt'])
    for day, times in by_day.items():
        span = (max(times) - min(times)).total_seconds()
        got += len(times)
        missing += max(0, int(span // interval_s) + 1 - len(times))
    return missing / (got + missing) if got + missing else 0.0


def symbol_from(path):
    # "CUPR_2026-07-31_10S.csv", "BATS_CUPR, 10S.csv" -> CUPR
    stem = os.path.splitext(os.path.basename(path))[0]
    for tok in re.split(r'[_,\s\-.]+', stem):
        if re.fullmatch(r'[A-Z]{1,5}', tok) and tok not in {'BATS', 'NASDAQ',
                                                            'NYSE', 'AMEX', 'S'}:
            return tok
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('csv', nargs='+')
    ap.add_argument('--symbol', help='ticker; inferred from the filename if omitted')
    ap.add_argument('--interval', help='label for the sub-minute cache, e.g. 10s. '
                                       'Inferred from the bar spacing if omitted.')
    ap.add_argument('--tz', default='America/New_York',
                    help='timezone of NAIVE timestamps (default: the chart was '
                         'set to New York)')
    ap.add_argument('--dry-run', action='store_true',
                    help='report what would be written, write nothing')
    a = ap.parse_args()

    if len(a.csv) > 1 and a.symbol:
        sys.exit('--symbol with several files would overwrite each import with '
                 'the next; drop it and let the filenames decide.')
    tz = ZoneInfo(a.tz)
    rc = 0
    for path in a.csv:
        sym = a.symbol or symbol_from(path)
        if not sym:
            print(f'{path}: cannot infer a ticker from the name; pass --symbol')
            rc = 1
            continue
        try:
            bars, ind, extra = read_csv(path, tz)
        except (ValueError, OSError) as e:
            print(e)
            rc = 1
            continue
        if not bars:
            print(f'{path}: no usable bars')
            rc = 1
            continue

        interval = a.interval or infer_interval(bars) or '1m'
        days = to_cache(bars)
        # 1-minute bars are what the engine reads. Anything else is a separate
        # resolution and must NOT overwrite the 1m cache the July runs used.
        name = f'{sym}.json' if interval == '1m' else f'{sym}.{interval}.json'
        dest = os.path.join(CACHE, name)

        unit = int(interval[:-1]) * (1 if interval.endswith('s') else 60)
        holes = sparsity(bars, unit)
        span = f'{bars[0]["dt"]:%Y-%m-%d %H:%M} .. {bars[-1]["dt"]:%Y-%m-%d %H:%M}'
        pre = sum(len(d['pre']) for d in days.values())
        ses = sum(len(d['session']) for d in days.values())
        print(f'{sym:<6} {interval:>4}  {len(bars):>6} bars  {len(days):>3} days  '
              f'{ses} session / {pre} extended  {span}')
        if extra:
            print(f'       indicator columns: {", ".join(extra)}')
        if holes > 0.02:
            print(f'       WARNING: {holes:.0%} of in-session slots have no bar. '
                  'TradingView emits a bar only where a trade happened; the '
                  'engine advances its EMAs once per bar, so a series this '
                  'gappy is not equivalent to padded 1-minute data.')
        if os.path.exists(dest) and not a.dry_run:
            print(f'       NOTE: overwriting {name}')

        if a.dry_run:
            continue
        os.makedirs(CACHE, exist_ok=True)
        with open(dest, 'w') as f:
            json.dump(days, f, separators=(',', ':'))
        if ind:
            os.makedirs(SIDECAR, exist_ok=True)
            with open(os.path.join(SIDECAR, f'{sym}.{interval}.json'), 'w') as f:
                json.dump(ind, f, separators=(',', ':'))
        print(f'       -> {dest}')
    return rc


if __name__ == '__main__':
    sys.exit(main())
