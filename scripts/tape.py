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
  * A halt is >= 3 consecutive missing 1-minute bars during regular hours
    (09:30-16:00). Yahoo omits bars with no prints; LULD halts are 5 minutes
    minimum, so 3 missing minutes separates a halt from a thin tape.
  * Stop check: the median 1-minute range of the last 30 regular-hours bars
    is the smallest stop the tape can honour. Below it is fiction.

Usage:
    python3 scripts/tape.py MSGY
    python3 scripts/tape.py MSGY WYHG TDIC          # compact, one block each
    python3 scripts/tape.py MSGY --bars 15          # more of the recent tape

`compute(sym)` returns the numbers as a dict; `render(d)` prints them.
`now.py` builds its summary table from compute() so the table and the detail
blocks can never disagree.
"""
import argparse
import datetime as dt
import json
import statistics
import subprocess
from zoneinfo import ZoneInfo

ET = ZoneInfo('America/New_York')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
URL = ('https://query1.finance.yahoo.com/v8/finance/chart/'
       '{}?range=1d&interval=1m&includePrePost=true')

# ---- colour: on for terminals, off when piped, NO_COLOR respected ----------
import os
_TTY = (os.environ.get('FORCE_COLOR') or
        (sys_stdout_isatty := __import__('sys').stdout.isatty())) and \
       not os.environ.get('NO_COLOR')


def c(txt, code):
    """ANSI wrap. Codes: 32 green, 31 red, 33 yellow, 2 dim, 1 bold, 7 invert."""
    return f'\033[{code}m{txt}\033[0m' if _TTY else str(txt)


GOOD = lambda t: c(t, '1;32')
BAD = lambda t: c(t, '1;31')
WARN = lambda t: c(t, '33')
DIM = lambda t: c(t, '2')


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


def compute(sym):
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
        return None

    closes = [b[4] for b in rows]
    e9, e20 = ema(closes, 9), ema(closes, 20)
    macd = [a - b for a, b in zip(ema(closes, 12), ema(closes, 26))]
    sig = ema(macd, 9)

    def minute(b): return b[0].hour * 60 + b[0].minute
    rth = [b for b in rows if 570 <= minute(b) < 960]
    pm = [b for b in rows if minute(b) < 570]

    # Pre-market quirk: until today's regular session prints, Yahoo leaves
    # regularMarketPrice at yesterday's close and chartPreviousClose one
    # session further back. The latest bar is the truth; when the regular
    # session hasn't traded today, yesterday's close IS regularMarketPrice.
    rmt = meta.get('regularMarketTime')
    rth_today = (rmt and
                 dt.datetime.fromtimestamp(rmt, ET).date() == rows[-1][0].date())
    d = {
        'sym': sym,
        'last': closes[-1],
        'prev': (meta.get('chartPreviousClose') if rth_today
                 else meta.get('regularMarketPrice')),
        'rows': rows, 'e9': e9, 'e20': e20, 'macd': macd, 'sig': sig,
        'hist': macd[-1] - sig[-1],
        'macd_pass': macd[-1] > 0 and macd[-1] > sig[-1],
        'pm_hi': max((b[2] for b in pm), default=None),
        'pm_lo': min((b[3] for b in pm), default=None),
        'pm_vol': sum(b[5] for b in pm),
        'vwap': None, 'hod': None, 'lod': None, 'fade': None,
        'rth_vol': 0, 'halts': [], 'med_range': None, 'top_ranges': [],
        'hv_red': 'NOT_MEASURED',  # absent ≠ measured-clean
    }
    d['gap'] = (d['last'] / d['prev'] - 1) * 100 if d['prev'] else None
    d['above_e9'] = closes[-1] > e9[-1]

    if rth:
        d['hod'] = max(b[2] for b in rth)
        d['lod'] = min(b[3] for b in rth)
        d['hod_t'] = next(b[0] for b in rth if b[2] == d['hod'])
        d['lod_t'] = next(b[0] for b in rth if b[3] == d['lod'])
        d['fade'] = (d['last'] / d['hod'] - 1) * 100
        d['rth_vol'] = sum(b[5] for b in rth)
        pv = sum((b[2] + b[3] + b[4]) / 3 * b[5] for b in rth)
        d['vwap'] = pv / d['rth_vol'] if d['rth_vol'] else None

        have = {minute(b) for b in rth}
        run = []
        for m in range(570, max(have) + 1):
            if m not in have:
                run.append(m)
            else:
                if len(run) >= 3:
                    d['halts'].append((run[0], run[-1]))
                run = []

        ranges = sorted((b[2] - b[3] for b in rth), reverse=True)
        d['med_range'] = statistics.median([b[2] - b[3] for b in rth[-30:]])
        d['top_ranges'] = ranges[:3]
        # in RANGE: 100% = at the day's high (front side) · 0% = back side
        span = d['hod'] - d['lod']
        d['in_range'] = (d['last'] - d['lod']) / span * 100 if span else None
        d['day_open'] = rth[0][1]
        # gatekeeper 2: a recent red candle on outsized volume kills the entry
        vols = [b[5] for b in rth if b[5]]
        avg_v = sum(vols) / len(vols) if vols else 0
        d['hv_red'] = None
        for back, b in enumerate(reversed(rth[-10:])):
            if b[4] < b[1] and avg_v and b[5] > 2 * avg_v:
                d['hv_red'] = (back, b[5] / avg_v)
                break
    return d


def render(d, nbars=8):
    if d is None:
        return
    now = dt.datetime.now(ET)
    print(f"## {d['sym']} · {now:%H:%M:%S} ET")
    gap = f" ({d['gap']:+.1f}%)" if d['gap'] is not None else ''
    prev = f"  prev {d['prev']:.2f}" if d['prev'] else ''
    print(f"last {d['last']:.2f}{prev}{gap}")
    if d['pm_hi'] is not None:
        print(f"PM   hi {d['pm_hi']:.2f}  lo {d['pm_lo']:.2f}  vol {d['pm_vol']:,}"
              + ('  (yahoo hides most PM volume)' if d['pm_vol'] == 0 else ''))
    if d['vwap'] is not None:
        fade_s = f"{d['fade']:+.1f}%"
        fade_s = BAD(fade_s) if d['fade'] <= -25 else (
            WARN(fade_s) if d['fade'] <= -15 else fade_s)
        rng = (f"  in RANGE {d['in_range']:.0f}%"
               if d.get('in_range') is not None else '')
        print(f"RTH  HOD {d['hod']:.2f} @{d['hod_t']:%H:%M}  LOD {d['lod']:.2f}"
              f" @{d['lod_t']:%H:%M}  fade {fade_s}{rng}  vol {d['rth_vol']:,}")
        if rng:
            print(DIM('     in RANGE: 100% = at the day high (front side) · '
                      '0% = at the low (back side, move over)'))
        above = d['last'] > d['vwap']
        print(f"VWAP {d['vwap']:.3f}  "
              + (GOOD('(above)') if above else BAD('(BELOW)')))
        for a, b in d['halts']:
            print(BAD(f"HALT {a//60:02d}:{a%60:02d}-{b//60:02d}:{b%60:02d}"
                      f"  ({b-a+1} min)"))
        print(f"1-min range  median(last 30) {d['med_range']:.2f}  session top3 "
              + ' '.join(f'{x:.2f}' for x in d['top_ranges'])
              + f"  → smallest honest stop ≈ {d['med_range']:.2f}"
              + (', wider through halts' if d['halts'] else ''))
    e9, e20 = d['e9'][-1], d['e20'][-1]
    if d['last'] > e9 and d['last'] > e20:
        state = GOOD('(above both)')
    elif d['last'] < e9:
        state = BAD('(below 9)')
    else:
        state = WARN('(between)')
    print(f"EMA9 {e9:.3f}  EMA20 {e20:.3f}  {state}")
    # the two gatekeepers, sub-conditions exposed (design device 7)
    m_lamp = GOOD('✓') if d['macd_pass'] else BAD('✗')
    above_sig = d['macd'][-1] > d['sig'][-1]
    print(f"{m_lamp} ① MACD 12/26/9  {d['macd'][-1]:+.4f}"
          f"  {'above' if d['macd'][-1] > 0 else 'BELOW'} zero"
          f" · {'above' if above_sig else 'BELOW'} signal ({d['sig'][-1]:+.4f})"
          f" · hist {d['hist']:+.4f}")
    hv = d.get('hv_red')
    if hv == 'NOT_MEASURED':
        print(DIM('○ ② VOLUME  not measured — no regular-session bars yet'))
    elif hv is None:
        print(f"{GOOD('✓')} ② VOLUME  clean — no high-volume red in the last 10 bars")
    else:
        back, mult = hv
        print(f"{BAD('✗')} ② VOLUME  HIGH-VOLUME RED {mult:.1f}x avg, "
              f"{back} bar(s) ago — gatekeeper says no")
    print(f"{'time':>6} {'open':>6} {'high':>6} {'low':>6} {'close':>6}"
          f" {'vol':>9} {'ema9':>6} {'hist':>8}")
    rows = d['rows']
    for i in range(max(0, len(rows) - nbars), len(rows)):
        b = rows[i]
        print(f"{b[0]:%H:%M}  {b[1]:6.2f} {b[2]:6.2f} {b[3]:6.2f} {b[4]:6.2f}"
              f" {b[5]:9,} {d['e9'][i]:6.2f} {d['macd'][i]-d['sig'][i]:+8.4f}")
    print()


def study(sym, nbars=8):
    render(compute(sym), nbars)


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
