#!/usr/bin/env python3
"""Pre-market due diligence from the tape, not from a screener row.

Written after a screener snapshot reported ZJYL at "+21.7%, 2.43M pre-market
volume, 12.5x relative" and it was graded A on that basis. The tape said the
regular session before it had traded 12,117 shares, the move was an after-hours
earnings pop, and price had been making lower highs for twelve hours straight.
Screener rows are point-in-time and carry stale or mislabelled volume; the bar
series does not.

For each symbol this reconstructs the whole arc a gapper actually travels -
prior session, after-hours, pre-market, now - and scores the pieces of the five
pillars that OHLCV can support:

  pillar 1  price band                          decidable here
  pillar 2  float                               NOT decidable - check manually
  pillar 3  news catalyst                       NOT decidable - check manually
  pillar 4  relative volume                     decidable, with a caveat
  pillar 5  rate of change AND still rising     decidable - this is the one
                                                a screener row cannot tell you

Two rules from the corpus are applied to shape:

  * "if a stock is stair stepping down that's not bullish, I'm not a buyer on
    something like that" (xgnqOu_fchA 08:45) - flagged as LOWER HIGHS.
  * the daily 200 MA check - "if it's below it this is bearish"
    (xgnqOu_fchA 27:24).

Yahoo reports zero volume on most extended-hours bars, so pre-market RVOL is
genuinely unavailable - the same hole TradingView has. It is reported as "n/a"
rather than guessed.

Usage:
    python scripts/premarket_dd.py JLHL GTE JDZG
    python scripts/premarket_dd.py --detail JLHL
"""
import argparse
import datetime as dt
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo

ET = ZoneInfo('America/New_York')
OPEN, CLOSE = dt.time(9, 30), dt.time(16, 0)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'


def get(url):
    p = subprocess.run(['curl', '-s', '--max-time', '30', '-H', f'User-Agent: {UA}', url],
                       capture_output=True, text=True)
    try:
        return json.loads(p.stdout)['chart']['result'][0]
    except Exception:
        return None


def bars(sym, rng, iv):
    d = get(f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}'
            f'?range={rng}&interval={iv}&includePrePost=true')
    if not d:
        return None, {}
    q = d['indicators']['quote'][0]
    out = []
    for i, t in enumerate(d['timestamp']):
        c = q['close'][i]
        if c is None:
            continue
        out.append(dict(t=dt.datetime.fromtimestamp(t, ET),
                        o=q['open'][i] or c, h=q['high'][i] or c,
                        l=q['low'][i] or c, c=c, v=q['volume'][i] or 0))
    return out, d['meta']


def lower_highs(seq, buckets=6):
    """Split the run into equal time buckets and count descending peaks.

    A single high followed by a drift is not the same shape as a staircase, so
    this measures the sequence of local peaks rather than just high-versus-last.
    """
    if len(seq) < buckets * 2:
        return None
    n = len(seq) // buckets
    peaks = [max(x['h'] for x in seq[i * n:(i + 1) * n]) for i in range(buckets)]
    desc = sum(1 for i in range(1, len(peaks)) if peaks[i] < peaks[i - 1])
    return desc, len(peaks) - 1, peaks


def study(sym):
    today = dt.datetime.now(ET).date()
    m1, meta = bars(sym, '5d', '1m')
    if not m1:
        return dict(sym=sym, err='no intraday data')
    daily, _ = bars(sym, '1y', '1d')

    days = sorted({b['t'].date() for b in m1})
    prior = [d for d in days if d < today]
    prev = prior[-1] if prior else None

    sess = [b for b in m1 if prev and b['t'].date() == prev and OPEN <= b['t'].time() < CLOSE]
    post = [b for b in m1 if prev and b['t'].date() == prev and b['t'].time() >= CLOSE]
    pre = [b for b in m1 if b['t'].date() == today and b['t'].time() < OPEN]
    live = [b for b in m1 if b['t'].date() == today and b['t'].time() >= OPEN]

    r = dict(sym=sym, err=None, prev_close=sess[-1]['c'] if sess else None,
             sess_vol=sum(b['v'] for b in sess),
             ah_high=max((b['h'] for b in post), default=None),
             pm_high=max((b['h'] for b in pre), default=None),
             pm_low=min((b['l'] for b in pre), default=None),
             pm_bars=len(pre), pm_first=pre[0]['t'] if pre else None,
             last=(live or pre or sess or [{}])[-1].get('c'))

    # the peak of the whole event, wherever it happened
    r['peak'] = max([x for x in (r['ah_high'], r['pm_high']) if x], default=None)
    if r['last'] and r['peak']:
        r['off_peak'] = (r['last'] / r['peak'] - 1) * 100
    if r['last'] and r['prev_close']:
        r['gap'] = (r['last'] / r['prev_close'] - 1) * 100

    run = post + pre
    r['stair'] = lower_highs(run)

    if daily:
        cl = [b['c'] for b in daily]
        r['ma200'] = sum(cl[-200:]) / min(200, len(cl))
        r['vs_ma200'] = (r['last'] / r['ma200'] - 1) * 100 if r['last'] else None
        r['hi52'] = max(b['h'] for b in daily)
        r['lo52'] = min(b['l'] for b in daily)
        # typical session volume, excluding the event day itself
        v = sorted(b['v'] for b in daily[-21:-1] if b['v'])
        r['typ_vol'] = v[len(v) // 2] if v else 0
        r['rvol_prev'] = (r['sess_vol'] / r['typ_vol']) if r.get('typ_vol') else None
    r['name'] = (meta or {}).get('shortName') or ''
    return r


def line(r):
    if r['err']:
        return f"{r['sym']:<7}  {r['err']}"
    f = lambda x, d=2: ('-' if x is None else f'{x:.{d}f}')                # noqa: E731
    stair = ''
    if r.get('stair'):
        desc, tot, _ = r['stair']
        stair = f'{desc}/{tot}'
    return (f"{r['sym']:<7}{f(r['prev_close']):>8}{f(r['peak']):>8}"
            f"{f(r['last']):>8}{f(r.get('gap'), 1):>8}{f(r.get('off_peak'), 1):>9}"
            f"{stair:>7}{r['sess_vol']:>11,}{f(r.get('rvol_prev'), 1):>7}"
            f"{f(r.get('vs_ma200'), 0):>8}")


def detail(r):
    print(f"\n=== {r['sym']}  {r['name']} ===")
    if r['err']:
        print(' ', r['err'])
        return
    print(f"  prior close      {r['prev_close']}   (session volume {r['sess_vol']:,},"
          f" typical {r.get('typ_vol', 0):,})")
    print(f"  after-hours high {r['ah_high']}")
    print(f"  pre-market       {r['pm_low']} - {r['pm_high']}  "
          f"({r['pm_bars']} bars with a print since "
          f"{r['pm_first']:%H:%M})" if r['pm_first'] else '  pre-market       none')
    print(f"  now              {r['last']}   {r.get('gap', 0):+.1f}% vs close, "
          f"{r.get('off_peak', 0):+.1f}% off the {r['peak']} peak")
    if r.get('stair'):
        desc, tot, peaks = r['stair']
        verdict = 'LOWER HIGHS - stair-stepping down' if desc >= tot - 1 else 'mixed'
        print(f"  shape            {desc}/{tot} descending peaks -> {verdict}")
        print(f"                   {' '.join(f'{p:.2f}' for p in peaks)}")
    if r.get('ma200'):
        side = 'BELOW - bearish' if r['vs_ma200'] < 0 else 'above'
        print(f"  200-day MA       {r['ma200']:.2f}  price is {side} "
              f"({r['vs_ma200']:+.0f}%)")
        print(f"  52-week          {r['lo52']:.2f} - {r['hi52']:.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('symbols', nargs='+')
    ap.add_argument('--detail', action='store_true')
    a = ap.parse_args()

    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(study, [s.upper() for s in a.symbols]))

    print(f'{dt.datetime.now(ET):%Y-%m-%d %H:%M} ET\n')
    print(f'{"sym":<7}{"pClose":>8}{"peak":>8}{"now":>8}{"gap%":>8}'
          f'{"offPk%":>9}{"lowHi":>7}{"prevVol":>11}{"rvol":>7}{"vs200":>8}')
    for r in res:
        print(line(r))
    print('\ngap%   = vs prior close        offPk% = vs the after-hours/pre-market peak')
    print('lowHi  = descending peaks / total, over the after-hours + pre-market run')
    print('rvol   = PRIOR session volume vs its 20-day median. Pre-market rvol is')
    print('         not available - Yahoo reports no extended-hours volume.')
    print('\nFloat and news are NOT scored here. Check both by hand on whatever')
    print('survives - they are pillars 2 and 3 and no OHLCV feed carries them.')
    if a.detail:
        for r in res:
            detail(r)
    return 0


if __name__ == '__main__':
    sys.exit(main())
