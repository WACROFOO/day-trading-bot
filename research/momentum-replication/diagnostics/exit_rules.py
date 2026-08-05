#!/usr/bin/env python3
"""Which EXIT rule turns the open-to-close basket around?

`reports/2026-08-score-basket.md` established that entry selection is not what
is broken - the pillar score has negative information value, and equal weight
beats it in 16 of 16 matched pairs. What IS broken is measurable: across 130
qualifying symbol-days the average name offers **+16.0% at its high** and closes
at **+0.24%**. The move is there and the close gives it all back.

Testing exits needs the intrabar SEQUENCE. Daily OHLC cannot supply it: these
names routinely print -10% and +16% on the same day, so any stop/target pair
must conservatively assume the stop filled first, which forces a loss onto
nearly every trade that would also have been a winner. That is an artefact of
the data, not a result.

So this runs on the 1-minute bars in data/bars_cache, where the order of events
is known. Coverage is 55 of the 130 qualifying symbol-days across 38 symbols
and all 17 sessions.

SELECTION CAVEAT: those 55 are the ones the pipeline happened to fetch, i.e.
names that passed the watchlist build. They are a subset chosen by pipeline
history, not by outcome, but they are not a random sample of the 130 and the
absolute numbers should not be read as the strategy's expectancy.

Entry is the 09:30 open for every rule, so only the exit varies.

Usage:
    python diagnostics/exit_rules.py
    python diagnostics/exit_rules.py --detail
"""
import argparse
import datetime as dt
import glob
import json
import os
import statistics as st
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402

OPEN, CLOSE = dt.time(9, 30), dt.time(16, 0)
HARD_STOP = dt.time(11, 30)          # PLAYBOOK.md - flat by 11:30 regardless


def load():
    """-> {(sym, day): [session bars]} for the qualifying set."""
    stats = json.load(open(os.path.join(_DATA, 'scan20_stats.json')))
    daily = json.load(open(os.path.join(_DATA, 'daily20.json')))
    split = {s for s, d in daily.items() if d.get('splits')}
    opens = {}
    for s, d in daily.items():
        if s in split:
            continue
        for r in d['rows']:
            opens[(s, r['day'])] = r['o']

    qual = set()
    for r in stats:
        k = (r['sym'], r['day'])
        o = opens.get(k)
        if not o or not (2.0 <= o <= 20.0):
            continue
        if (r.get('gap_pct') or 0) < 10.0:
            continue
        qual.add(k)

    out = {}
    for p in glob.glob(os.path.join(_DATA, 'bars_cache', '*.json')):
        sym = os.path.basename(p)[:-5]
        if '.' in sym:
            continue
        try:
            raw = json.load(open(p))
        except (json.JSONDecodeError, OSError):
            continue
        for day, sides in raw.items():
            if (sym, day) not in qual:
                continue
            bars = [dict(t=dt.datetime.fromisoformat(b['t']), o=b['o'], h=b['h'],
                         l=b['l'], c=b['c'], v=b['v'])
                    for b in (sides.get('session') or [])]
            bars = [b for b in bars if OPEN <= b['t'].time() < CLOSE]
            if len(bars) > 60:
                out[(sym, day)] = bars
    return out


# --- exit rules. Each takes the bar list and the entry price, returns % ------

def r_close(bars, e, **kw):
    return (bars[-1]['c'] / e - 1) * 100


def r_time(bars, e, cut=HARD_STOP, **kw):
    """His documented hard stop: flat at 11:30 whatever the P&L."""
    b = [x for x in bars if x['t'].time() < cut] or bars[:1]
    return (b[-1]['c'] / e - 1) * 100


def r_stop(bars, e, stop=10.0, **kw):
    lvl = e * (1 - stop / 100)
    for b in bars:
        if b['l'] <= lvl:
            return -stop
    return (bars[-1]['c'] / e - 1) * 100


def r_target(bars, e, target=10.0, **kw):
    lvl = e * (1 + target / 100)
    for b in bars:
        if b['h'] >= lvl:
            return target
    return (bars[-1]['c'] / e - 1) * 100


def r_bracket(bars, e, stop=10.0, target=10.0, **kw):
    """Both, with the SEQUENCE known - the whole reason for minute bars."""
    slvl, tlvl = e * (1 - stop / 100), e * (1 + target / 100)
    for b in bars:
        hit_s, hit_t = b['l'] <= slvl, b['h'] >= tlvl
        if hit_s and hit_t:
            return -stop                       # same bar: still resolve against us
        if hit_s:
            return -stop
        if hit_t:
            return target
    return (bars[-1]['c'] / e - 1) * 100


def r_trail(bars, e, trail=10.0, **kw):
    """Trail `trail`% below the running high, from the entry bar."""
    peak = e
    for b in bars:
        peak = max(peak, b['h'])
        if b['l'] <= peak * (1 - trail / 100):
            return (max(peak * (1 - trail / 100), b['l']) / e - 1) * 100
    return (bars[-1]['c'] / e - 1) * 100


def r_ladder(bars, e, target=10.0, trail=15.0, **kw):
    """His documented ladder, simplified: half off at target 1, stop to
    breakeven, trail the rest. PLAYBOOK.md sec.6."""
    tlvl = e * (1 + target / 100)
    peak, half_out, be = e, False, None
    for b in bars:
        peak = max(peak, b['h'])
        if not half_out and b['h'] >= tlvl:
            half_out, be = True, e             # bank half, stop to breakeven
            continue
        if half_out:
            stop_lvl = max(be, peak * (1 - trail / 100))
            if b['l'] <= stop_lvl:
                return 0.5 * target + 0.5 * (stop_lvl / e - 1) * 100
        elif b['l'] <= e * (1 - target / 100):
            return -target                     # full stop before target 1
    tail = (bars[-1]['c'] / e - 1) * 100
    return 0.5 * target + 0.5 * tail if half_out else tail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--detail', action='store_true')
    a = ap.parse_args()
    data = load()
    if not data:
        print('no intraday coverage')
        return 1
    print(f'{len(data)} symbol-days with 1-minute bars, '
          f'{len({s for s, _ in data})} symbols, {len({d for _, d in data})} sessions')
    print('entry = 09:30 open for every rule; only the exit differs\n')

    RULES = [
        ('sell at close (baseline)', r_close, {}),
        ('flat at 11:30', r_time, {}),
        ('flat at 10:30', r_time, dict(cut=dt.time(10, 30))),
        ('stop -10%', r_stop, dict(stop=10)),
        ('stop -15%', r_stop, dict(stop=15)),
        ('target +10%', r_target, dict(target=10)),
        ('target +20%', r_target, dict(target=20)),
        ('bracket -10/+10', r_bracket, dict(stop=10, target=10)),
        ('bracket -10/+20', r_bracket, dict(stop=10, target=20)),
        ('bracket -15/+30', r_bracket, dict(stop=15, target=30)),
        ('trail 10%', r_trail, dict(trail=10)),
        ('trail 15%', r_trail, dict(trail=15)),
        ('trail 20%', r_trail, dict(trail=20)),
        ('ladder +10 / trail 15', r_ladder, dict(target=10, trail=15)),
        ('ladder +20 / trail 15', r_ladder, dict(target=20, trail=15)),
    ]
    print(f'{"exit rule":<26}{"mean%":>8}{"median%":>9}{"win%":>7}{"worst%":>8}{"stdev":>8}{"m/sd":>7}')
    res = []
    for name, fn, kw in RULES:
        p = [fn(b, b[0]['o'], **kw) for b in data.values()]
        m, sd = st.mean(p), st.stdev(p)
        res.append((m, name, p))
        print(f'{name:<26}{m:>+8.2f}{st.median(p):>+9.2f}'
              f'{100 * sum(1 for x in p if x > 0) / len(p):>7.0f}'
              f'{min(p):>+8.1f}{sd:>8.2f}{m / sd if sd else 0:>+7.2f}')
    base = next(m for m, n, _ in res if n.startswith('sell at close'))
    print(f'\nbest by mean: {max(res)[1]} ({max(res)[0]:+.2f}% vs baseline {base:+.2f}%)')
    if a.detail:
        bm, bn, bp = max(res)
        print(f'\nper-trade under "{bn}":')
        for (s, d), v in sorted(zip(data, bp), key=lambda x: -x[1]):
            print(f'  {d}  {s:<6}{v:>+8.2f}%')
    return 0


if __name__ == '__main__':
    sys.exit(main())
