#!/usr/bin/env python3
"""Mock-trade every CUPR setup on 2026-07-31 and diagnose each loss.

This is a LEARNING EXERCISE, not a strategy result. Every setup the detector
produced is taken regardless of whether it passed the entry gate, so that the
outcome of each can be inspected. Taking setups the gate rejected is exactly
what the strategy says not to do; the point is to see what the gate was right
and wrong about.

Also tests the hypothesis that fell out of the bar-by-bar reading: during the
run to the high of day every dip was one bar long, and the detector needs two,
so it went silent through the biggest move of the session.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402

import datetime as dt
import json

import sim
from sim import (Indicators, PullbackTracker, evaluate, GATE_CONDITIONS,
                 RISK_PER_TRADE, SLIPPAGE, BUYING_POWER, LIQUIDITY_CAP,
                 spread_estimate)

OUT = _DATA
ET = dt.timezone(dt.timedelta(hours=-4))


def hyd(rows):
    return [dict(dt=dt.datetime.fromisoformat(r['t']), o=r['o'], h=r['h'],
                 l=r['l'], c=r['c'], v=r['v']) for r in rows]


def collect(bars, pre, min_dip):
    """Every setup, with min_dip controlling the shortest acceptable pullback."""
    sim_min = sim.MIN_DIP_BARS
    sim.MIN_DIP_BARS = min_dip
    try:
        ind = Indicators()
        for x in pre:
            ind.update(x, in_session=False)
        tr, prev, flipped, out = PullbackTracker(), None, [], []
        for bar in bars:
            ind.update(bar, in_session=True)
            pb = tr.update(bar, prev, ind)
            if pb:
                ok, checks = evaluate(pb, bar, ind, flipped)
                gating = {k: v for k, v in checks.items() if k in GATE_CONDITIONS}
                entry = min(pb['trigger_level'] + SLIPPAGE, bar['h'])
                out.append(dict(i=bars.index(bar), t=bar['dt'].strftime('%H:%M'),
                                entry=entry, stop=pb['low'], idx=pb['index'],
                                dip_bars=len(pb['bars']),
                                leg_low=pb['leg_low'], leg_high=pb['leg_high'],
                                hod=ind.session_high or bar['h'],
                                spread=spread_estimate(ind),
                                score=sum(1 for v in gating.values() if v[0]),
                                fails=[k for k, v in gating.items() if not v[0]]))
            prev = bar
            if ind.session_high and bar['h'] >= ind.session_high:
                flipped = (flipped + [round(bar['h'], 2)])[-6:]
        return out
    finally:
        sim.MIN_DIP_BARS = sim_min


def mock_trade(s, bars):
    """Forward-only from the entry bar, using the documented exits."""
    entry, stop = s['entry'], s['stop']
    risk = entry - stop
    if risk <= 0:
        return None
    t1 = max(s['hod'], s['leg_low'] + (s['leg_high'] - s['leg_low']))
    if t1 - entry < 2 * risk:
        t1 = entry + 2 * risk                      # documented minimum
    shares = max(1, min(int(RISK_PER_TRADE / risk),
                        int(BUYING_POWER / entry),
                        int(bars[s['i']]['v'] * LIQUIDITY_CAP) or 1))
    pnl, held, scaled, cur_stop = 0.0, 0, 0, stop
    for bar in bars[s['i'] + 1:]:
        held += 1
        if bar['l'] <= cur_stop:
            pnl += (cur_stop - entry) * shares
            return dict(**s, shares=shares, t1=t1, pnl=pnl, held=held,
                        exit=cur_stop, why='stop' if scaled == 0 else 'breakeven',
                        R=pnl / (risk * (shares or 1)))
        if scaled == 0 and bar['h'] >= t1:
            q = shares // 2
            pnl += (t1 - entry) * q
            shares -= q
            scaled, cur_stop = 1, entry
        if scaled and bar['c'] < bar['o'] and bar['l'] < bars[s['i']]['l']:
            pnl += (bar['c'] - entry) * shares
            return dict(**s, shares=shares, t1=t1, pnl=pnl, held=held,
                        exit=bar['c'], why='trail', R=pnl / (risk * (shares or 1)))
    last = bars[-1]
    pnl += (last['c'] - entry) * shares
    return dict(**s, shares=shares, t1=t1, pnl=pnl, held=held, exit=last['c'],
                why='end of session', R=pnl / (risk * (shares or 1)))


def main():
    d = json.load(open(os.path.join(OUT, 'cupr_friday.json')))
    b1 = hyd(d['1m'])
    reg = [x for x in b1 if dt.time(9, 30) <= x['dt'].time() < dt.time(16, 0)]
    pre = [x for x in b1 if x['dt'].time() < dt.time(9, 30)]

    print('=== HYPOTHESIS: the 2-bar minimum blinds the detector to fast moves ===')
    for m in (2, 1):
        got = collect(reg, pre, m)
        run = [s for s in got if '09:30' <= s['t'] <= '10:30']
        print(f'  min dip = {m} bar(s):  {len(got):>2} setups on the day, '
              f'{len(run)} during the 09:30-10:30 run to the high')

    setups = collect(reg, pre, 1)
    print(f'\n=== mock trades — ALL {len(setups)} setups taken, gate ignored ===')
    print('(taking gate-rejected setups is what the strategy forbids; the point '
          'is to see what the gate got right)\n')
    print(f'{"time":>6}{"gate":>5}{"dip":>4}{"entry":>7}{"stop":>7}{"T1":>7}'
          f'{"sh":>6}{"held":>6}{"P&L":>9}{"R":>7}  exit')
    rows = []
    for s in setups:
        r = mock_trade(s, reg)
        if not r:
            continue
        rows.append(r)
        print(f'{r["t"]:>6}{r["score"]:>4}/6{r["dip_bars"]:>4}{r["entry"]:>7.2f}'
              f'{r["stop"]:>7.2f}{r["t1"]:>7.2f}{r["shares"]:>6}{r["held"]:>6}'
              f'{r["pnl"]:>9.2f}{r["R"]:>+7.2f}  {r["why"]}')

    wins = [r for r in rows if r['pnl'] > 0]
    print(f'\ntaken {len(rows)}   winners {len(wins)}   '
          f'total ${sum(r["pnl"] for r in rows):+.2f}')

    print(f'\n=== did the gate help? ===')
    for lo, hi, label in ((6, 6, 'passed all 6'), (5, 5, '5 of 6'),
                          (4, 4, '4 of 6'), (0, 3, '3 or fewer')):
        g = [r for r in rows if lo <= r['score'] <= hi]
        if g:
            w = sum(1 for r in g if r['pnl'] > 0)
            print(f'  {label:<14} n={len(g):<3} winners {w}  '
                  f'total ${sum(r["pnl"] for r in g):+8.2f}  '
                  f'mean {sum(r["R"] for r in g)/len(g):+.2f}R')

    print(f'\n=== every loss, and what it teaches ===')
    for r in sorted([x for x in rows if x['pnl'] <= 0], key=lambda x: x['pnl']):
        why = []
        if r['risk'] if 'risk' in r else False:
            pass
        rr = r['entry'] - r['stop']
        if rr < r['spread']:
            why.append(f'stop ${rr:.3f} was inside the ${r["spread"]:.3f} spread '
                       f'— noise alone hits it')
        if r['fails']:
            why.append('gate said no: ' + ', '.join(r['fails']))
        if r['held'] <= 2:
            why.append(f'died in {r["held"]} bar(s) — no room')
        if r['entry'] >= r['hod'] * 0.99:
            why.append('entered at/near the high of day — buying the top of the leg')
        print(f'  {r["t"]}  ${r["pnl"]:>8.2f} ({r["R"]:+.2f}R)  ' +
              (' | '.join(why) if why else 'clean setup, market simply reversed'))

    json.dump(rows, open(os.path.join(OUT, 'cupr_mock.json'), 'w'),
              indent=1, default=str)
    print(f'\nwrote data/cupr_mock.json')


if __name__ == '__main__':
    main()
