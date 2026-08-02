#!/usr/bin/env python3
"""One trading day, start to finish, multi-timeframe: 2026-07-31.

Runs the whole chain for a single session so it can be inspected end to end:

    universe -> pre-market watchlist -> multi-timeframe bars -> replay -> report

Timeframes. The corpus uses three, for three different jobs:

    5-minute    setup context      "1-minute chart entries after 5-minute
                                    chart setup" (BFH-0N8S-IA 08:04)
    1-minute    the entry trigger  (PARAMETERS.md:144)
    10-second   "zoom-in for micro pullback patterns" (HMaTY5-x2N0 11:30)

**10-second bars are not obtainable.** Yahoo's API rejects every sub-minute
interval - `Valid intervals: [1m, 2m, 5m, 15m, ...]` - and building them needs
trade-level data, which no keyless source here provides. Per the corpus the
10-second chart is a zoom for placing an entry inside a 1-minute candle, not a
separate signal generator, so its absence costs fill precision rather than
setups. That is recorded, not worked around.

The 5-minute frame is fetched and measured but is NOT wired into the entry gate.
Its corpus support is a single claim (n=1); adding a tenth hard condition on
that basis would be inventing a rule. Instead the 5-minute state at each entry
is reported, and the script measures what a 5-minute trend filter WOULD have
changed - which is evidence about whether it is worth adding, rather than an
assumption that it is.

Usage:
    python pipeline/friday.py            # cached bars if present
    NO_CACHE=1 python pipeline/friday.py # force refetch
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402

import datetime as dt
import json
import subprocess
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from engine20 import run_day
from run20b import build
from sim import Indicators

OUT = _DATA
DAY = '2026-07-31'
ET = dt.timezone(dt.timedelta(hours=-4))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/121.0 Safari/537.36")
CACHE = os.path.join(OUT, 'friday_mtf.json')


def get(url, tries=4):
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


def bars(sym, interval):
    """One day of bars at one interval, split pre-market / session."""
    a = dt.datetime(2026, 7, 30, 20, 0)
    b = dt.datetime(2026, 8, 1, 0, 0)
    url = (f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}'
           f'?period1={int(a.timestamp())}&period2={int(b.timestamp())}'
           f'&interval={interval}&includePrePost=true')
    d = get(url)
    try:
        r = d['chart']['result'][0]
    except (TypeError, KeyError, IndexError):
        return dict(pre=[], session=[])
    ts, q = r.get('timestamp') or [], r['indicators']['quote'][0]
    pre, sess = [], []
    for i, t in enumerate(ts):
        c = q['close'][i]
        if c is None:
            continue
        d_ = dt.datetime.fromtimestamp(t, ET)
        if str(d_.date()) != DAY:
            continue
        bar = dict(t=d_.isoformat(), o=q['open'][i] or c, h=q['high'][i] or c,
                   l=q['low'][i] or c, c=c, v=q['volume'][i] or 0)
        (pre if d_.time() < dt.time(9, 30) else sess).append(bar)
    return dict(pre=pre, session=sess)


def hydrate(side):
    return [dict(dt=dt.datetime.fromisoformat(b['t']), o=b['o'], h=b['h'],
                 l=b['l'], c=b['c'], v=b['v']) for b in side]


def fetch_all(syms):
    if not os.environ.get('NO_CACHE') and os.path.exists(CACHE):
        with open(CACHE) as f:
            return json.load(f)
    out = {}

    def one(sym):
        return sym, {iv: bars(sym, iv) for iv in ('1m', '2m', '5m')}

    with ThreadPoolExecutor(max_workers=5) as ex:
        for sym, d in ex.map(one, syms):
            out[sym] = d
    with open(CACHE, 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    return out


def five_min_state(bars5, upto):
    """5-minute context as of `upto`, using only bars that had closed by then."""
    ind = Indicators()
    closed = [b for b in bars5 if b['dt'].time() <= upto]
    for b in closed:
        ind.update(b, in_session=b['dt'].time() >= dt.time(9, 30))
    if not closed:
        return None
    last = closed[-1]
    return dict(close=last['c'], ema9=ind.ema9, vwap=ind.vwap,
                macd=ind.macd_hist,
                up=(ind.ema9 is not None and last['c'] > ind.ema9))


def main():
    stats = json.load(open(os.path.join(OUT, 'scan20_stats.json')))
    daily = json.load(open(os.path.join(OUT, 'daily20.json')))
    pool = {c['sym']: c for c in json.load(open(os.path.join(OUT, 'pool20.json')))}
    shares_out = {s: c['mcap'] / c['price'] for s, c in pool.items() if c['price']}

    print(f'=== {DAY} — universe and watchlist ===')
    print(f'candidate pool           {len(pool):,} symbols')
    print(f'pre-market records       {sum(1 for r in stats if r["day"] == DAY):,} for this day')

    watch = build(stats, daily, shares_out).get(DAY, [])
    print(f'passing the five pillars {len(watch)}')
    for r in watch:
        print(f'   {r["sym"]:<6} gap +{r["gap_pct"]:>5.1f}%  open ${r["open_px"]:>6.2f}  '
              f'RVOL(5m) {r["rvol5"]:>7.1f}x')
    if not watch:
        print('no qualifying names — nothing to trade')
        return

    syms = [r['sym'] for r in watch]
    mtf = fetch_all(syms)
    print(f'\n=== bars fetched ===')
    print(f'{"sym":<6}{"1m pre":>8}{"1m sess":>9}{"2m sess":>9}{"5m sess":>9}')
    for s in syms:
        d = mtf[s]
        print(f'{s:<6}{len(d["1m"]["pre"]):>8}{len(d["1m"]["session"]):>9}'
              f'{len(d["2m"]["session"]):>9}{len(d["5m"]["session"]):>9}')
    print('10s: unavailable — Yahoo rejects every sub-minute interval')

    per = {s: dict(pre=hydrate(mtf[s]['1m']['pre']),
                   session=hydrate(mtf[s]['1m']['session'])) for s in syms}

    print(f'\n=== replay (1-minute, 09:35–11:30 ET) ===')
    log = []
    res = run_day(dt.date(2026, 7, 31), syms, per, 5, log)
    for line in log:
        print('  ' + line)
    print(f'\nsetups {res["setups"]}   gate passes {res["passes"]}   '
          f'trades {len(res["trades"])}   P&L ${res["pnl"]:+.2f}')
    if res['rejects']:
        print('rejections:')
        for k, v in sorted(res['rejects'].items(), key=lambda x: -x[1]):
            print(f'   {v:>4}  {k}')

    # --- 5-minute context at each entry, measured but not gated on -----------
    if res['trades']:
        print(f'\n=== 5-minute context at entry (not part of the gate) ===')
        print(f'{"sym":<6}{"entry":>7}{"5m close":>10}{"5m 9EMA":>10}'
              f'{"5m MACD":>10}  5m trend')
        agree = 0
        for t in res['trades']:
            hh, mm = t['entry_time'].split(':')
            st = five_min_state(hydrate(mtf[t['sym']]['5m']['session']),
                                dt.time(int(hh), int(mm)))
            if not st:
                continue
            agree += bool(st['up'])
            print(f'{t["sym"]:<6}{t["entry_time"]:>7}{st["close"]:>10.2f}'
                  f'{(st["ema9"] or 0):>10.2f}{(st["macd"] or 0):>+10.3f}'
                  f'  {"up" if st["up"] else "DOWN"}')
        print(f'\nA 5-minute trend filter (close > 5m 9 EMA) would have kept '
              f'{agree} of {len(res["trades"])} trades.')

    json.dump(dict(day=DAY, watch=watch,
                   trades=[{k: v for k, v in t.items() if k != 'checks'}
                           for t in res['trades']],
                   setups=res['setups'], passes=res['passes'],
                   pnl=res['pnl'], rejects=res['rejects'], log=log),
              open(os.path.join(OUT, 'friday_result.json'), 'w'),
              indent=1, default=str)
    print(f'\nwrote data/friday_result.json')


if __name__ == '__main__':
    main()
