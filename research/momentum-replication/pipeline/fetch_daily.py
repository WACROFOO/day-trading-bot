#!/usr/bin/env python3
"""Consistently-adjusted daily bars, one request per symbol.

Why this exists: the 1-minute scan stitched five separate 7-day API responses,
and Yahoo adjusts each response independently. When a reverse split falls inside
the month, the previous day's close came from a differently-adjusted response
than the current day's open, and the ratio between them was recorded as a
"gap". That produced FFAI +10,555% and GNPX +2,058% - and the anomalies landed
exactly on the window boundaries (Jul 15, 22, 29), which is the tell.

A single daily request covers the whole month in one response, so every bar in
it shares one adjustment basis. Gaps computed from it are internally
consistent, and reverse splits vanish because the whole series is adjusted
together.

The gap is now measured open-vs-previous-close rather than pre-market-vs-
previous-close. That is still information a trader has at 09:35, which is when
the watchlist is confirmed - so it costs nothing in look-ahead terms.

Output: daily20.json  {sym: [{day, open, close, high, low, vol}, ...]}
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import datetime as dt
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

ET = dt.timezone(dt.timedelta(hours=-4))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/121.0 Safari/537.36")
OUT = _DATA

P1 = int(dt.datetime(2026, 5, 20).timestamp())     # extra history for the
P2 = int(dt.datetime(2026, 8, 2).timestamp())      # trailing volume average


def get(url, tries=3):
    for i in range(tries):
        p = subprocess.run(['curl', '-s', '--max-time', '45',
                            '-H', f'User-Agent: {UA}', url],
                           capture_output=True, text=True)
        o = p.stdout.strip()
        if o.startswith('{') and '"chart"' in o:
            try:
                return json.loads(o)
            except json.JSONDecodeError:
                pass
        time.sleep(1.0 + 2.0 * i)
    return None


def daily(sym):
    url = (f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}'
           f'?period1={P1}&period2={P2}&interval=1d&events=split')
    d = get(url)
    try:
        r = d['chart']['result'][0]
    except (TypeError, KeyError, IndexError):
        return sym, None
    ts, q = r.get('timestamp') or [], r['indicators']['quote'][0]
    rows = []
    for i, t in enumerate(ts):
        c = q['close'][i]
        if c is None:
            continue
        rows.append(dict(day=str(dt.datetime.fromtimestamp(t, ET).date()),
                         o=q['open'][i] or c, h=q['high'][i] or c,
                         l=q['low'][i] or c, c=c, v=q['volume'][i] or 0))
    splits = {}
    for v in ((r.get('events') or {}).get('splits') or {}).values():
        splits[str(dt.datetime.fromtimestamp(v['date'], ET).date())] = v.get('splitRatio')
    return sym, dict(rows=rows, splits=splits)


def main():
    stats = json.load(open(os.path.join(OUT, 'scan20_stats.json')))
    syms = sorted({r['sym'] for r in stats})
    print(f'daily bars for {syms.__len__()} symbols', flush=True)

    out, done = {}, 0
    with ThreadPoolExecutor(max_workers=7) as ex:
        for sym, d in ex.map(daily, syms):
            done += 1
            if d and d['rows']:
                out[sym] = d
            if done % 300 == 0:
                print(f'  {done}/{len(syms)} ok={len(out)}', flush=True)

    json.dump(out, open(os.path.join(OUT, 'daily20.json'), 'w'))
    nsplit = sum(1 for d in out.values() if d['splits'])
    print(f'DONE {len(out)} symbols, {nsplit} with a split in range', flush=True)


if __name__ == '__main__':
    main()
