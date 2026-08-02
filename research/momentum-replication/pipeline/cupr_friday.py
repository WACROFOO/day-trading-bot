#!/usr/bin/env python3
"""CUPR, 2026-07-31, full session including pre- and after-market.

Extracts every candle available, maps what the stock actually did, finds every
setup the detector produces across the whole day, mock-trades them, and
diagnoses each loss.

10-second candles: not obtainable. Yahoo rejects every sub-minute interval;
Nasdaq's realtime-trades endpoint returns zero rows for a past date and
extended-trading is a live snapshot, not history. Building 10s bars needs
trade-level data no keyless source here provides.

Usage:
    python pipeline/cupr_friday.py
    NO_CACHE=1 python pipeline/cupr_friday.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402

import datetime as dt
import json
import subprocess
import time

from sim import (Indicators, PullbackTracker, evaluate, GATE_CONDITIONS,
                 RISK_PER_TRADE, STOP_MAX, SLIPPAGE, BUYING_POWER,
                 LIQUIDITY_CAP, spread_estimate)

OUT = _DATA
SYM = (sys.argv[1] if len(sys.argv) > 1 else 'CUPR').upper()  # SYMBOL_ARG
DAY = dt.date(2026, 7, 31)
ET = dt.timezone(dt.timedelta(hours=-4))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/121.0 Safari/537.36")
CACHE = os.path.join(OUT, f'{SYM.lower()}_friday.json')


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


def fetch(interval):
    a = dt.datetime(2026, 7, 30, 20, 0)
    b = dt.datetime(2026, 8, 1, 4, 0)
    d = get(f'https://query1.finance.yahoo.com/v8/finance/chart/{SYM}'
            f'?period1={int(a.timestamp())}&period2={int(b.timestamp())}'
            f'&interval={interval}&includePrePost=true')
    try:
        r = d['chart']['result'][0]
    except (TypeError, KeyError, IndexError):
        return []
    ts, q = r.get('timestamp') or [], r['indicators']['quote'][0]
    out = []
    for i, t in enumerate(ts):
        c = q['close'][i]
        if c is None:
            continue
        d_ = dt.datetime.fromtimestamp(t, ET)
        if d_.date() != DAY:
            continue
        out.append(dict(t=d_.isoformat(), o=q['open'][i] or c, h=q['high'][i] or c,
                        l=q['low'][i] or c, c=c, v=q['volume'][i] or 0))
    return out


def load():
    if not os.environ.get('NO_CACHE') and os.path.exists(CACHE):
        return json.load(open(CACHE))
    data = {iv: fetch(iv) for iv in ('1m', '2m', '5m')}
    json.dump(data, open(CACHE, 'w'), separators=(',', ':'))
    return data


def hyd(rows):
    return [dict(dt=dt.datetime.fromisoformat(r['t']), o=r['o'], h=r['h'],
                 l=r['l'], c=r['c'], v=r['v']) for r in rows]


def session_of(t):
    if t < dt.time(9, 30):
        return 'pre'
    if t < dt.time(16, 0):
        return 'regular'
    return 'after'


def main():
    data = load()
    b1, b5 = hyd(data['1m']), hyd(data['5m'])

    print(f'=== {SYM} {DAY} — candles extracted ===')
    print(f'{"frame":<7}{"pre":>7}{"regular":>9}{"after":>7}{"total":>7}'
          f'{"w/ volume":>11}')
    for name, bars in (('1m', b1), ('2m', hyd(data['2m'])), ('5m', b5)):
        c = {'pre': 0, 'regular': 0, 'after': 0}
        for x in bars:
            c[session_of(x['dt'].time())] += 1
        vol = sum(1 for x in bars if x['v'] > 0)
        print(f'{name:<7}{c["pre"]:>7}{c["regular"]:>9}{c["after"]:>7}'
              f'{len(bars):>7}{vol:>11}')
    print('10s     -- unavailable (no sub-minute interval, no tick source) --')

    # ---- what the stock actually did -----------------------------------
    reg = [x for x in b1 if session_of(x['dt'].time()) == 'regular']
    pre = [x for x in b1 if session_of(x['dt'].time()) == 'pre']
    aft = [x for x in b1 if session_of(x['dt'].time()) == 'after']
    hod = max(reg, key=lambda x: x['h'])
    lod = min(reg, key=lambda x: x['l'])
    print(f'\n=== the day ===')
    if pre:
        print(f'pre-market   {pre[0]["c"]:.2f} -> {pre[-1]["c"]:.2f}  '
              f'({len(pre)} bars, volume reported: {sum(x["v"] for x in pre):,})')
    print(f'open         {reg[0]["o"]:.2f}   at {reg[0]["dt"].strftime("%H:%M")}')
    print(f'high of day  {hod["h"]:.2f}   at {hod["dt"].strftime("%H:%M")}  '
          f'(+{100*(hod["h"]/reg[0]["o"]-1):.1f}% from open)')
    print(f'low of day   {lod["l"]:.2f}   at {lod["dt"].strftime("%H:%M")}')
    print(f'close        {reg[-1]["c"]:.2f}   ({100*(reg[-1]["c"]/reg[0]["o"]-1):+.1f}% from open)')
    if aft:
        print(f'after-hours  {aft[0]["c"]:.2f} -> {aft[-1]["c"]:.2f}  ({len(aft)} bars)')

    # ---- every setup, whole regular session -----------------------------
    ind = Indicators()
    for x in pre:
        ind.update(x, in_session=False)
    tr, prev, flipped = PullbackTracker(), None, []
    setups = []
    for bar in reg:
        ind.update(bar, in_session=True)
        pb = tr.update(bar, prev, ind)
        if pb:
            ok, checks = evaluate(pb, bar, ind, flipped)
            gating = {k: v for k, v in checks.items() if k in GATE_CONDITIONS}
            entry = min(pb['trigger_level'] + SLIPPAGE, bar['h'])
            stop = pb['low']
            risk = entry - stop
            spread = spread_estimate(ind)
            setups.append(dict(
                t=bar['dt'].strftime('%H:%M'), pb=pb, bar=bar, checks=checks,
                gating=gating, score=sum(1 for v in gating.values() if v[0]),
                entry=entry, stop=stop, risk=risk, spread=spread,
                hod=ind.session_high,
                sized=(spread <= risk),
                gate_ok=all(v[0] for v in gating.values())))
        prev = bar
        if ind.session_high and bar['h'] >= ind.session_high:
            flipped = (flipped + [round(bar['h'], 2)])[-6:]

    print(f'\n=== setups across the whole regular session ({len(setups)}) ===')
    print(f'{"time":>6}{"leg":>14}{"dip":>7}{"#":>3}{"gate":>6}{"$/sh":>7}'
          f'{"sprd":>6}  blocking')
    for s in setups:
        fails = [k for k, v in s['gating'].items() if not v[0]]
        if not s['sized']:
            fails.append(f'stop<spread')
        print(f'{s["t"]:>6}{s["pb"]["leg_low"]:>7.2f}->{s["pb"]["leg_high"]:<6.2f}'
              f'{s["stop"]:>7.2f}{s["pb"]["index"]:>3}{s["score"]:>4}/6'
              f'{s["risk"]:>7.3f}{s["spread"]:>6.3f}  '
              + ('— none, TRADE —' if not fails else '; '.join(fails[:2])))

    json.dump(dict(sym=SYM, day=str(DAY),
                   setups=[dict(t=s['t'], score=s['score'], entry=s['entry'],
                                stop=s['stop'], risk=s['risk'],
                                spread=s['spread'], idx=s['pb']['index'],
                                leg_low=s['pb']['leg_low'],
                                leg_high=s['pb']['leg_high'],
                                hod=s['hod'], gate_ok=s['gate_ok'],
                                sized=s['sized'],
                                fails=[k for k, v in s['gating'].items() if not v[0]])
                           for s in setups]),
              open(os.path.join(OUT, f'{SYM.lower()}_setups.json'), 'w'), indent=1)
    print(f'\nwrote data/cupr_setups.json')
    return setups, b1, b5


if __name__ == '__main__':
    main()
