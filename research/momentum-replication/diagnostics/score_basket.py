#!/usr/bin/env python3
"""Buy-the-open / sell-the-close basket, sized by a 0-100 pillar score.

The strategy under test, as specified:
  1. screen the whole pool near the open on the five pillars
  2. give each survivor a score from 0 to 100
  3. distribute a fixed EUR100 across them in proportion to score
  4. buy at the open, sell at the close, every day

Two things decide whether the answer means anything, and both are handled here.

LOOK-AHEAD. `rvol5` in scan20_stats is confirmed at 09:35, so scoring with it
and buying the 09:30 open would be buying on information from after the entry.
This scores on PRE-MARKET FIELDS ONLY - gap, pre-market price, pre-market print
count, and shares outstanding - all of which exist before the bell. Run with
--rvol to include rvol5, which then requires --entry 0935 to stay honest.

SELECTION. The pool is scan20_stats: every symbol scanned that morning, ~1,500
per day, not the ones that turned out to move. Screening a list of known movers
would manufacture an edge out of nothing.

Pillar 3 (news) CANNOT be scored - no feed here - so the maximum is four
pillars at 25 points each. Every result below is therefore an upper bound on
what the screen knows and a lower bound on what a human with a news terminal
would know.

SPLIT CONVENTION. scan20_stats carries SPLIT-ADJUSTED prices; daily20 carries
RAW ones. Taking the entry from one and the exit from the other silently
manufactured a -99% on DFNS (scan open 9.21 against a daily open of 0.074 -
exactly its 1:125 ratio). Entry and exit now BOTH come from the same daily20
row, and any symbol with a split anywhere in the window is dropped outright.

Usage:
    python diagnostics/score_basket.py
    python diagnostics/score_basket.py --min-score 60 --max-names 5
    python diagnostics/score_basket.py --equal-weight      # control
"""
import argparse
import json
import os
import sys
import statistics as st
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402

BUDGET = 100.0


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def score_price(px):
    """25 pts. Full marks in his stated sweet spot, partial across the band.

    "the sweet spot is 5 to 10" - PARAMETERS.md sec.1; the band is 2-20.
    """
    if px is None or not (2.0 <= px <= 20.0):
        return 0.0
    if 5.0 <= px <= 10.0:
        return 25.0
    if px < 5.0:
        return 25.0 * clamp((px - 2.0) / 3.0)
    return 25.0 * clamp((20.0 - px) / 10.0)


def score_float(so):
    """25 pts. Full below 10M shares, zero at 20M+. Shares outstanding is a
    PROXY for float - it is always >= float, so this is conservative."""
    if not so or so <= 0:
        return 0.0
    if so <= 10e6:
        return 25.0
    return 25.0 * clamp((20e6 - so) / 10e6)


def score_gap(gap):
    """25 pts. 10% is the documented floor; 30%+ is full marks."""
    if gap is None or gap < 10.0:
        return 0.0
    return 25.0 * clamp((gap - 10.0) / 20.0)


def score_activity(pre_bars):
    """25 pts, standing in for relative volume BEFORE the bell.

    rvol5 is a 09:35 quantity. The only pre-open liquidity signal in the scan
    is how many pre-market minutes actually printed. A name printing 150+
    minutes is being traded; one printing 5 is a quote, not a market.
    """
    if not pre_bars:
        return 0.0
    return 25.0 * clamp(pre_bars / 150.0)


def build(args):
    stats = json.load(open(os.path.join(_DATA, 'scan20_stats.json')))
    daily = json.load(open(os.path.join(_DATA, 'daily20.json')))
    pool = {c['sym']: c for c in json.load(open(os.path.join(_DATA, 'pool20.json')))}
    shares_out = {s: c['mcap'] / c['price']
                  for s, c in pool.items() if c.get('price')}

    # entry AND exit from the same row, so the split convention cancels
    oc_by = {}
    split_syms = set()
    for sym, d in daily.items():
        if d.get('splits'):
            split_syms.add(sym)          # any split at all - drop the name
            continue
        for r in d['rows']:
            oc_by[(sym, r['day'])] = (r['o'], r['c'])

    days = defaultdict(list)
    dropped_split = 0
    for r in stats:
        sym, day = r['sym'], r['day']
        if sym in split_syms:
            dropped_split += 1
            continue
        oc = oc_by.get((sym, day))
        if not oc:
            continue
        entry, exit_ = oc
        # score the price you would actually pay, from the same series
        px = entry
        # HARD GATES. The pillars are gates - "all five or it is not a trade"
        # (PLAYBOOK.md). Scoring them purely as weights let CJMB in at $1.27
        # and KUST at $1.76 on 75/100, both outside the price band entirely.
        if not (2.0 <= px <= 20.0):
            continue
        if (r.get('gap_pct') or 0) < 10.0:
            continue
        s = (score_price(px) + score_float(shares_out.get(sym))
             + score_gap(r.get('gap_pct')) + score_activity(r.get('pre_bars')))
        if args.rvol:
            rv = r.get('rvol5') or 0
            s = s * 0.8 + 20.0 * clamp(rv / 5.0)
        if s < args.min_score:
            continue
        if not entry or not exit_ or entry <= 0:
            continue
        days[day].append(dict(sym=sym, score=s, entry=entry, exit=exit_,
                              gap=r.get('gap_pct'), pre_bars=r.get('pre_bars'),
                              so=shares_out.get(sym)))
    print(f'(dropped {dropped_split} symbol-days on names with a split in the window)\n')
    return days


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--min-score', type=float, default=50.0)
    ap.add_argument('--max-names', type=int, default=8)
    ap.add_argument('--equal-weight', action='store_true',
                    help='control: ignore the score, split the budget evenly')
    ap.add_argument('--rvol', action='store_true',
                    help='include rvol5 - LOOK-AHEAD unless you also enter at 09:35')
    ap.add_argument('--detail', action='store_true')
    a = ap.parse_args()

    days = build(a)
    if not days:
        print('no qualifying day')
        return 1

    print(f'EUR{BUDGET:.0f} per day, score >= {a.min_score:.0f}, '
          f'top {a.max_names} by score, '
          f'{"EQUAL weight (control)" if a.equal_weight else "SCORE weighted"}'
          f'{", rvol5 INCLUDED (look-ahead)" if a.rvol else ""}\n')
    print(f'{"day":<12}{"n":>3}{"medScore":>9}{"cost":>9}{"value":>9}{"P/L":>9}{"%":>8}  top holding')

    tot_pl = 0.0
    rets, wins = [], 0
    for day in sorted(days):
        picks = sorted(days[day], key=lambda r: -r['score'])[:a.max_names]
        if not picks:
            continue
        if a.equal_weight:
            w = {p['sym']: BUDGET / len(picks) for p in picks}
        else:
            ts = sum(p['score'] for p in picks)
            w = {p['sym']: BUDGET * p['score'] / ts for p in picks}
        cost = value = 0.0
        for p in picks:
            # fractional shares, so the whole allocation is deployed
            sh = w[p['sym']] / p['entry']
            cost += sh * p['entry']
            value += sh * p['exit']
        pl = value - cost
        tot_pl += pl
        rets.append(pl / cost * 100)
        wins += pl > 0
        best = max(picks, key=lambda p: p['score'])
        print(f'{day:<12}{len(picks):>3}{st.median(p["score"] for p in picks):>9.0f}'
              f'{cost:>9.2f}{value:>9.2f}{pl:>+9.2f}{pl / cost * 100:>+8.1f}  '
              f'{best["sym"]} ({best["score"]:.0f}, {best["entry"]:.2f}->{best["exit"]:.2f})')
        if a.detail:
            for p in picks:
                print(f'{"":<12}    {p["sym"]:<6} score {p["score"]:>5.1f}  '
                      f'EUR{w[p["sym"]]:>6.2f}  {p["entry"]:>7.2f} -> {p["exit"]:>7.2f}  '
                      f'{(p["exit"] / p["entry"] - 1) * 100:>+6.1f}%')

    n = len(rets)
    print(f'\n{n} sessions, EUR{BUDGET:.0f} deployed each')
    print(f'  total P/L        EUR{tot_pl:>+9.2f}   ({tot_pl / (BUDGET * n) * 100:+.1f}% of capital deployed)')
    print(f'  mean day         {st.mean(rets):>+9.2f}%')
    print(f'  median day       {st.median(rets):>+9.2f}%')
    print(f'  win rate         {wins}/{n} = {wins / n * 100:.0f}%')
    print(f'  best / worst     {max(rets):+.1f}% / {min(rets):+.1f}%')
    if n > 1:
        sd = st.stdev(rets)
        print(f'  daily stdev      {sd:.2f}%   ->  mean/stdev = {st.mean(rets) / sd:+.2f}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
