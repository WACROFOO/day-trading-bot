#!/usr/bin/env python3
"""The intraday workup, in one command. The provenance tool.

Written after a verdict on WYHG cited prints that existed in no fetch. Every
number ticker-verdict needs on the tape side comes out of one run of this:
VWAP, 9/20 EMA, MACD 12/26/9, halts, the 1-minute range distribution, fade
off the high. If a number is not in this output or in finviz, it does not go
in the answer.

Conventions, matching how the analysis has been done by hand all along:
  * EMAs and MACD run over the full 1-minute series including pre-market,
    so the open does not reset the averages.
  * VWAP is regular-hours only.
  * A halt is >= 3 consecutive missing 1-minute bars during regular hours.
    Yahoo omits bars with no prints; LULD halts are 5 minutes minimum, so 3
    missing minutes separates a halt from a thin tape.
  * Stop check: the median 1-minute range is the smallest stop the tape can
    actually honour. A stop below it is fiction, and the output says so.

Usage:
    python3 scripts/tape.py MSGY
    python3 scripts/tape.py MSGY WYHG TDIC          # compact, one block each
    python3 scripts/tape.py MSGY --bars 15          # more of the recent tape
"""
import argparse
import datetime as dt
import json
import statistics
import subprocess
import sys
from zoneinfo import ZoneInfo

ET = ZoneInfo('America/New_York')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
URL = ('https://query1.finance.yahoo.com/v8/finance/chart/'
       '{}?range=1d&interval=1m&includePrePost=true')


def fetch(sym):
    p = subprocess.run(['curl', '-s', '--compressed', '--max-time', '30',
                        '-H', f'User-Agent: {UA}', URL.format(sym)],
                       capture_output=True, text=True)
    return json.loads(p.stdout)['chart']['result'][0]


def ema(vals, n):
    k = 2 / (n + 1)
    out = [vals[0]]
    for v in vals[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def study(sym, nbars):
    r = fetch(sym)
    meta = r['meta']
    q = r['indicators']['quote'][0]
    rows = []
    for i, t in enumerate(r['timestamp']):
        if q['close'][i] is None:
            continue
        rows.append((dt.datetime.fromtimestamp(t, ET), q['open'][i],
                     q['high'][i], q['low'][i], q['close'][i],
                     q['volume'][i] or 0))
    if not rows:
        print(f'{sym}: no bars'); return

    closes = [b[4] for b in rows]
    e9, e20 = ema(closes, 9), ema(closes, 20)
    macd = [a - b for a, b in zip(ema(closes, 12), ema(closes, 26))]
    sig = ema(macd, 9)

    def minute(b): return b[0].hour * 60 + b[0].minute
    rth = [b for b in rows if 570 <= minute(b) < 960]
    pm = [b for b in rows if minute(b) < 570]

    last = meta.get('regularMarketPrice') or closes[-1]
    prev = meta.get('chartPreviousClose')
    now = dt.datetime.now(ET)
    print(f"## {sym} · {now:%H:%M:%S} ET")
    gap = f' ({(last/prev-1)*100:+.1f}%)' if prev else ''
    print(f'last {last:.2f}  prev {prev:.2f}{gap}' if prev
          else f'last {last:.2f}')

    if pm:
        pmv = sum(b[5] for b in pm)
        print(f'PM   hi {max(b[2] for b in pm):.2f}  lo '
              f'{min(b[3] for b in pm):.2f}  vol {pmv:,}'
              + ('  (yahoo hides most PM volume)' if pmv == 0 else ''))
    if rth:
        hod = max(b[2] for b in rth); lod = min(b[3] for b in rth)
        hodt = next(b[0] for b in rth if b[2] == hod)
        lodt = next(b[0] for b in rth if b[3] == lod)
        vv = sum(b[5] for b in rth)
        pv = sum((b[2] + b[3] + b[4]) / 3 * b[5] for b in rth)
        print(f'RTH  HOD {hod:.2f} @{hodt:%H:%M}  LOD {lod:.2f} @{lodt:%H:%M}'
              f'  fade {(last/hod-1)*100:+.1f}%  vol {vv:,}')
        if vv:
            print(f'VWAP {pv/vv:.3f}  ({"above" if last > pv/vv else "BELOW"})')

        # halts: >=3 consecutive missing RTH minutes
        have = {minute(b) for b in rth}
        halts, run = [], []
        for m in range(570, max(have) + 1):
            if m not in have:
                run.append(m)
            else:
                if len(run) >= 3:
                    halts.append((run[0], run[-1]))
                run = []
        for a, b in halts:
            print(f'HALT {a//60:02d}:{a%60:02d}-{b//60:02d}:{b%60:02d}'
                  f'  ({b-a+1} min)')

        ranges = sorted((b[2] - b[3] for b in rth), reverse=True)
        recent = [b[2] - b[3] for b in rth[-30:]]
        med = statistics.median(recent)
        print(f'1-min range  median(last 30) {med:.2f}  session top3 '
              + ' '.join(f'{x:.2f}' for x in ranges[:3])
              + f'  → smallest honest stop ≈ {med:.2f}'
              + (', wider through halts' if halts else ''))

    print(f'EMA9 {e9[-1]:.3f}  EMA20 {e20[-1]:.3f}  '
          f'({"above both" if closes[-1] > e9[-1] and closes[-1] > e20[-1] else "below 9" if closes[-1] < e9[-1] else "between"})')
    h = macd[-1] - sig[-1]
    ok = macd[-1] > 0 and h > 0
    print(f'MACD {macd[-1]:+.4f}  sig {sig[-1]:+.4f}  hist {h:+.4f}'
          f'  ({"passes" if ok else "FAILS"}: needs positive AND above signal)')

    print(f'{"time":>6} {"open":>6} {"high":>6} {"low":>6} {"close":>6}'
          f' {"vol":>9} {"ema9":>6} {"hist":>8}')
    for i in range(max(0, len(rows) - nbars), len(rows)):
        b = rows[i]
        print(f'{b[0]:%H:%M}  {b[1]:6.2f} {b[2]:6.2f} {b[3]:6.2f} {b[4]:6.2f}'
              f' {b[5]:9,} {e9[i]:6.2f} {macd[i]-sig[i]:+8.4f}')
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('symbols', nargs='+')
    ap.add_argument('--bars', type=int, default=8)
    args = ap.parse_args()
    for s in args.symbols:
        try:
            study(s.upper(), args.bars)
        except Exception as e:
            print(f'{s}: fetch failed ({e})')


if __name__ == '__main__':
    main()
