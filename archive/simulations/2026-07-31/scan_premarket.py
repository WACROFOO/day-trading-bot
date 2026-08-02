#!/usr/bin/env python3
"""Pre-market scan for Friday 2026-07-31, using only data available at 09:29 ET.

The whole validity of the simulation rests on this file. Everything it computes
comes from bars timestamped before the opening bell:

    prior closes / volumes   Mon 7/27 - Thu 7/30 regular sessions
    gap and pre-market vol   Fri 04:00 - 09:29 ET

Nothing reads a Friday regular-session bar. The candidate pool was filtered on
price and market cap only - never on Friday's move - so a name is not in here
because of how it finished.
"""
import datetime as dt
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ET = dt.timezone(dt.timedelta(hours=-4))          # EDT on 2026-07-31
FRI = dt.date(2026, 7, 31)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/121.0 Safari/537.36")
OUT = os.path.dirname(os.path.abspath(__file__))

OPEN_T = dt.time(9, 30)
PRE_START = dt.time(4, 0)


def get(url, tries=4):
    for i in range(tries):
        p = subprocess.run(['curl', '-s', '--max-time', '45',
                            '-H', f'User-Agent: {UA}', url],
                           capture_output=True, text=True)
        out = p.stdout.strip()
        if out.startswith('{') and '"chart"' in out:
            try:
                return json.loads(out)
            except json.JSONDecodeError:
                pass
        time.sleep(1.5 + 2.5 * i)
    return None


def bars(sym):
    url = (f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}'
           f'?range=5d&interval=1m&includePrePost=true')
    d = get(url)
    try:
        r = d['chart']['result'][0]
    except (TypeError, KeyError, IndexError):
        return None
    ts = r.get('timestamp') or []
    q = r['indicators']['quote'][0]
    out = []
    for i, t in enumerate(ts):
        o, h, l, c, v = (q['open'][i], q['high'][i], q['low'][i],
                         q['close'][i], q['volume'][i])
        if c is None:
            continue
        d_ = dt.datetime.fromtimestamp(t, ET)
        out.append(dict(t=t, dt=d_, o=o or c, h=h or c, l=l or c, c=c,
                        v=v or 0))
    return out


def analyse(sym):
    b = bars(sym)
    if not b or len(b) < 50:
        return None

    prior_regular = {}          # date -> [bars] for Mon-Thu regular hours
    fri_pre, fri_rest = [], []
    for x in b:
        d_, tm = x['dt'].date(), x['dt'].time()
        regular = OPEN_T <= tm < dt.time(16, 0)
        if d_ < FRI:
            if regular:
                prior_regular.setdefault(d_, []).append(x)
        elif d_ == FRI:
            if PRE_START <= tm < OPEN_T:
                fri_pre.append(x)
            else:
                fri_rest.append(x)

    if not prior_regular or not fri_pre:
        return None

    days = sorted(prior_regular)
    prev_day = days[-1]                                  # Thu 7/30
    prev_close = prior_regular[prev_day][-1]['c']
    if not prev_close or prev_close <= 0:
        return None

    # Average full-session volume over the prior days -> the RVOL denominator.
    prior_vols = [sum(x['v'] for x in prior_regular[d]) for d in days]
    avg_vol = sum(prior_vols) / len(prior_vols) if prior_vols else 0

    pre_vol = sum(x['v'] for x in fri_pre)
    pre_last = fri_pre[-1]['c']
    pre_high = max(x['h'] for x in fri_pre)
    gap = (pre_last / prev_close - 1) * 100
    gap_high = (pre_high / prev_close - 1) * 100

    return dict(
        sym=sym, prev_close=round(prev_close, 4),
        prev_day=str(prev_day), avg_prior_vol=int(avg_vol),
        pre_vol=int(pre_vol), pre_last=round(pre_last, 4),
        pre_high=round(pre_high, 4), gap_pct=round(gap, 2),
        gap_high_pct=round(gap_high, 2),
        pre_bars=len(fri_pre), fri_bars=len(fri_rest),
        # pre-market RVOL: the only volume signal that exists before the bell
        pre_rvol=round(pre_vol / avg_vol, 3) if avg_vol else 0,
    )


def main():
    pool = json.load(open(os.path.join(OUT, 'pool.json')))
    syms = [c['sym'] for c in pool if c['sym'].isalpha()]
    print(f'scanning {len(syms)} symbols', flush=True)

    results, done = [], 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(analyse, syms):
            done += 1
            if r:
                results.append(r)
            if done % 100 == 0:
                print(f'  {done}/{len(syms)} ok={len(results)}', flush=True)

    results.sort(key=lambda r: -r['gap_pct'])
    json.dump(results, open(os.path.join(OUT, 'premarket_scan.json'), 'w'),
              indent=1)
    print(f'DONE {len(results)} symbols with usable data', flush=True)


if __name__ == '__main__':
    main()
