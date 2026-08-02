#!/usr/bin/env python3
"""Pass 1: per-symbol, per-day pre-market statistics for 2026-07-06 .. 07-31.

Yahoo caps 1-minute history at 7 days per request, so each symbol needs four
windowed calls to cover the month. Bars are reduced to a compact per-day record
and then discarded - keeping 2,486 symbols x 20 days x ~960 bars would be
gigabytes for data that is only used to rank a watchlist.

Everything recorded for day D is computable before D's opening bell, except
`open_px` and `v5`/`hi5`/`lo5`, which cover 09:30-09:34 and are used for the
09:35 relative-volume confirmation - the same compromise as the single-day run,
forced by Yahoo returning null volume on pre-market bars.

`prior_avg_vol` is a trailing average over the sessions BEFORE D only.

Output: scan20_stats.json  [{sym, day, ...}, ...]
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import datetime as dt
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ET = dt.timezone(dt.timedelta(hours=-4))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/121.0 Safari/537.36")
OUT = _DATA

OPEN_T, CLOSE_T = dt.time(9, 30), dt.time(16, 0)
PRE_START = dt.time(4, 0)

WINDOWS = [(dt.datetime(2026, 7, 1), dt.datetime(2026, 7, 8)),
           (dt.datetime(2026, 7, 8), dt.datetime(2026, 7, 15)),
           (dt.datetime(2026, 7, 15), dt.datetime(2026, 7, 22)),
           (dt.datetime(2026, 7, 22), dt.datetime(2026, 7, 29)),
           (dt.datetime(2026, 7, 29), dt.datetime(2026, 8, 1, 12))]


def get(url, tries=3):
    for i in range(tries):
        p = subprocess.run(['curl', '-s', '--max-time', '50',
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


def fetch_all(sym):
    """Merge the windowed calls into one timestamp-keyed bar map."""
    bars = {}
    for a, b in WINDOWS:
        url = (f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}'
               f'?period1={int(a.timestamp())}&period2={int(b.timestamp())}'
               f'&interval=1m&includePrePost=true')
        d = get(url)
        try:
            r = d['chart']['result'][0]
        except (TypeError, KeyError, IndexError):
            continue
        ts, q = r.get('timestamp') or [], r['indicators']['quote'][0]
        for i, t in enumerate(ts):
            c = q['close'][i]
            if c is None:
                continue
            bars[t] = (q['open'][i] or c, q['high'][i] or c,
                       q['low'][i] or c, c, q['volume'][i] or 0)
    return bars


def analyse(sym):
    try:
        bars = fetch_all(sym)
    except Exception:
        return None
    if len(bars) < 500:
        return None

    byday = {}
    for t in sorted(bars):
        d_ = dt.datetime.fromtimestamp(t, ET)
        byday.setdefault(d_.date(), []).append((d_.time(), bars[t]))

    days = sorted(byday)
    out, prior_vols = [], []
    prev_close = None

    for day in days:
        rows = byday[day]
        regular = [(tm, v) for tm, v in rows if OPEN_T <= tm < CLOSE_T]
        pre = [(tm, v) for tm, v in rows if PRE_START <= tm < OPEN_T]

        if regular and prev_close and prior_vols and pre:
            first5 = [v for tm, v in regular if tm < dt.time(9, 35)]
            pre_last = pre[-1][1][3]
            pre_high = max(v[1] for _, v in pre)
            avg = sum(prior_vols) / len(prior_vols)
            v5 = sum(v[4] for v in first5)
            out.append(dict(
                sym=sym, day=str(day),
                prev_close=round(prev_close, 4),
                gap_pct=round((pre_last / prev_close - 1) * 100, 2),
                gap_high_pct=round((pre_high / prev_close - 1) * 100, 2),
                pre_last=round(pre_last, 4), pre_bars=len(pre),
                prior_avg_vol=int(avg),
                open_px=round(first5[0][0], 4) if first5 else None,
                v5=int(v5),
                # last price of the 5-minute confirmation window,
                # so rate-of-change can be measured at 09:35
                px5=round(first5[-1][3], 4) if first5 else None,
                # like-for-like: 5 minutes vs the average 5-minute slice of a
                # 390-minute session
                rvol5=round(v5 / (avg * 5 / 390), 2) if avg else 0,
            ))

        if regular:
            prev_close = regular[-1][1][3]
            prior_vols.append(sum(v[4] for _, v in regular))
            prior_vols[:] = prior_vols[-10:]
    return out


def main():
    pool = json.load(open(os.path.join(OUT, 'pool20.json')))
    syms = [c['sym'] for c in pool]
    print(f'pass 1: {len(syms)} symbols x {len(WINDOWS)} windows', flush=True)

    recs, done, ok = [], 0, 0
    with ThreadPoolExecutor(max_workers=7) as ex:
        for r in ex.map(analyse, syms):
            done += 1
            if r:
                ok += 1
                recs.extend(r)
            if done % 200 == 0:
                print(f'  {done}/{len(syms)}  symbols_ok={ok}  '
                      f'records={len(recs)}', flush=True)

    json.dump(recs, open(os.path.join(OUT, 'scan20_stats.json'), 'w'))
    print(f'DONE {ok} symbols, {len(recs)} symbol-days', flush=True)


if __name__ == '__main__':
    main()
