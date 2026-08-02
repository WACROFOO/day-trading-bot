#!/usr/bin/env python3
"""Pull full Friday 1-minute bars for the pre-market watchlist candidates."""
import datetime as dt
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

ET = dt.timezone(dt.timedelta(hours=-4))
FRI = dt.date(2026, 7, 31)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/121.0 Safari/537.36")
OUT = os.path.dirname(os.path.abspath(__file__))


def get(url, tries=5):
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
        time.sleep(1.5 + 2 * i)
    return None


def day(sym):
    url = (f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}'
           f'?range=5d&interval=1m&includePrePost=true')
    d = get(url)
    try:
        r = d['chart']['result'][0]
    except (TypeError, KeyError, IndexError):
        return sym, None
    ts, q = r.get('timestamp') or [], r['indicators']['quote'][0]
    pre, sess, prior = [], [], {}
    for i, t in enumerate(ts):
        c = q['close'][i]
        if c is None:
            continue
        d_ = dt.datetime.fromtimestamp(t, ET)
        rec = dict(t=t, iso=d_.isoformat(), o=q['open'][i] or c,
                   h=q['high'][i] or c, l=q['low'][i] or c, c=c,
                   v=q['volume'][i] if q['volume'][i] is not None else None)
        if d_.date() == FRI:
            (pre if d_.time() < dt.time(9, 30) else sess).append(rec)
        elif d_.date() < FRI and dt.time(9, 30) <= d_.time() < dt.time(16, 0):
            prior.setdefault(str(d_.date()), []).append(rec)
    return sym, dict(sym=sym, pre=pre, session=sess, prior=prior)


def main():
    cands = json.load(open(os.path.join(OUT, 'watchlist_candidates.json')))
    syms = [c['sym'] for c in cands]
    out = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        for sym, d in ex.map(day, syms):
            if d:
                out[sym] = d
                nv = sum(1 for b in d['session'] if b['v'])
                print(f'{sym:<6} pre={len(d["pre"]):>4} sess={len(d["session"]):>4} '
                      f'bars_with_vol={nv:>4}', flush=True)
    json.dump(out, open(os.path.join(OUT, 'friday_bars.json'), 'w'))
    print('saved', len(out), 'symbols')


if __name__ == '__main__':
    main()
