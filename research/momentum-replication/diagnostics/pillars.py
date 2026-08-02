#!/usr/bin/env python3
"""Which pillar rejects the names he actually traded?

calibrate.py established that the five-pillar scanner drops two thirds of the
tickers the recaps name, including most of the ones the entry gate would then
have accepted. This re-runs the scanner's own criteria over exactly those
session-ticker pairs and records the FIRST one that fails, so the loss is
attributable to a parameter rather than to "the scanner".

Order matters here: a name failing several criteria is charged to the first,
so read the table as "cheapest fix first", not as a count of violations. The
per-criterion column on the right is the unconditional count and does not sum
to the total.

Usage:
    python diagnostics/pillars.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402

import datetime as dt
import json
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

from run20 import fetch_symbol
from run20b import (build, PRICE_MIN, GAP_SANITY_CAP, SPLIT_BUFFER, MAX_NAMES)

OUT = _DATA
# The pillars as run20b.build applies them, named so a failure points at a line.
TESTS = [
    ('gap >= 10%',            lambda m: m['gap'] >= 10.0),
    ('gap <= 200% (artifact)', lambda m: m['gap'] <= GAP_SANITY_CAP),
    (f'open >= ${PRICE_MIN:.2f}',  lambda m: m['open'] >= PRICE_MIN),
    ('open <= $20',           lambda m: m['open'] <= 20.0),
    ('float <= 20M',          lambda m: 0 < m['so'] <= 20e6),
    ('RVOL(5m) >= 5x',        lambda m: m['rvol5'] >= 5.0),
]


def main():
    cal = json.load(open(os.path.join(OUT, 'calibration.json')))
    stats = json.load(open(os.path.join(OUT, 'scan20_stats.json')))
    daily = json.load(open(os.path.join(OUT, 'daily20.json')))
    pool = {c['sym']: c for c in json.load(open(os.path.join(OUT, 'pool20.json')))}
    shares_out = {s: c['mcap'] / c['price'] for s, c in pool.items() if c['price']}
    watch = build(stats, daily, shares_out)

    v5_by = {(r['sym'], r['day']): r['v5'] for r in stats}
    days_all = sorted({r['day'] for r in stats})

    # rebuild the per-symbol daily context build() computes internally
    ctx = {}
    for sym, d in daily.items():
        rows = d['rows']
        idx = {r['day']: i for i, r in enumerate(rows)}
        split_days = set()
        for sd in d['splits']:
            if sd in idx:
                i = idx[sd]
                for j in range(max(0, i - SPLIT_BUFFER),
                               min(len(rows), i + SPLIT_BUFFER + 1)):
                    split_days.add(rows[j]['day'])
            else:
                split_days.add(sd)
        for i, r in enumerate(rows):
            if i == 0 or r['day'] not in days_all:
                continue
            prev = rows[i - 1]
            hist = rows[max(0, i - 10):i]
            avg = sum(x['v'] for x in hist) / len(hist) if hist else 0
            v5 = v5_by.get((sym, r['day']))
            ctx[(sym, r['day'])] = dict(
                split=r['day'] in split_days,
                gap=(r['o'] / prev['c'] - 1) * 100 if prev['c'] else None,
                open=r['o'], so=shares_out.get(sym, 0),
                rvol5=(v5 / (avg * 5 / 390)) if (avg and v5 is not None) else None)

    pairs, seen = [], set()
    for r in cal['rows']:
        if r[2] == '?':
            continue
        key = (r[0], r[1].rstrip('*'))
        if key in seen:
            continue
        seen.add(key)
        pairs.append(dict(day=r[0], sym=r[1].rstrip('*'), on_wl=bool(r[5]),
                          setups=r[6], gate=r[7]))

    need = sorted({p['sym'] for p in pairs})
    bars = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        for sym, d in ex.map(fetch_symbol, need):
            bars[sym] = d

    first_fail, unconditional, rows = Counter(), Counter(), []
    for p in pairs:
        m = ctx.get((p['sym'], p['day']))
        reason = None
        if m is None:
            reason = 'no daily bar / no prior close'
        elif m['split']:
            reason = 'inside a split buffer'
        elif m['gap'] is None or m['rvol5'] is None:
            reason = 'missing gap or RVOL input'
        else:
            for name, t in TESTS:
                if not t(m):
                    unconditional[name] += 1
                    if reason is None:
                        reason = name
        if reason is None:
            # passed every criterion - so it was the ranking or the ROC filter
            ranked = [x['sym'] for x in watch.get(p['day'], [])]
            if p['sym'] in ranked:
                d = bars.get(p['sym'], {}).get(p['day'])
                f5 = [b for b in (d or {}).get('session', [])
                      if b['dt'].time() < dt.time(9, 35)]
                if not f5:
                    reason = 'no 09:30-09:34 bars (ROC untestable)'
                elif f5[-1]['c'] <= f5[0]['o']:
                    reason = 'rate_of_change <= 0 at 09:35'
                else:
                    reason = 'PASSED'
            else:
                reason = f'ranked outside the top {MAX_NAMES} by gap'
        first_fail[reason] += 1
        rows.append(dict(p, reason=reason,
                         gap=(m or {}).get('gap'), open=(m or {}).get('open'),
                         so=(m or {}).get('so'), rvol5=(m or {}).get('rvol5')))

    n = len(rows)
    print(f'=== why the scanner drops the names he traded ===')
    print(f'{n} session-ticker pairs from the July recaps\n')
    print(f'{"first criterion to fail":<34}{"pairs":>6}{"%":>6}{"any":>6}')
    for name, c in first_fail.most_common():
        print(f'{name:<34}{c:>6}{100 * c / n:>5.0f}%'
              f'{unconditional.get(name, ""):>6}')

    lost = [r for r in rows if r['gate'] and r['reason'] != 'PASSED']
    print(f'\n=== the {len(lost)} pairs the entry gate accepted but the scanner '
          f'never listed ===')
    print(f'{"day":<12}{"sym":<7}{"gap%":>7}{"open":>7}{"float":>9}{"rvol":>7}'
          f'{"gated":>7}  blocked by')
    for r in sorted(lost, key=lambda x: -x['gate']):
        print(f'{r["day"]:<12}{r["sym"]:<7}'
              f'{(r["gap"] or 0):>7.0f}{(r["open"] or 0):>7.2f}'
              f'{(r["so"] or 0) / 1e6:>8.1f}M{(r["rvol5"] or 0):>7.0f}'
              f'{r["gate"]:>7}  {r["reason"]}')

    print(f'\n=== if one criterion were relaxed, how many of those {len(lost)} '
          f'return? ===')
    for name, _ in TESTS + [('ranked outside the top %d by gap' % MAX_NAMES, None),
                            ('rate_of_change <= 0 at 09:35', None)]:
        c = sum(1 for r in lost if r['reason'] == name)
        if c:
            print(f'  {name:<34}{c:>4}')

    json.dump(rows, open(os.path.join(OUT, 'pillars.json'), 'w'), indent=1)
    print('\nwrote data/pillars.json')


if __name__ == '__main__':
    main()
