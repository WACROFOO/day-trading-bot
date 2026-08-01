#!/usr/bin/env python3
"""Summarise a 20-day run: per-day table, aggregate stats, rejection reasons."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import json
import os
import sys
from collections import Counter

OUT = _DATA


def load(n):
    return json.load(open(os.path.join(OUT, f'run20_max{n}.json')))


def stats(results):
    trades = [t for r in results for t in r['trades']]
    pnls = [t['pnl'] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    total = sum(r['pnl'] for r in results)

    eq, peak, dd = 0.0, 0.0, 0.0
    for r in results:
        eq += r['pnl']
        peak = max(peak, eq)
        dd = min(dd, eq - peak)

    return dict(
        days=len(results),
        traded_days=sum(1 for r in results if r['trades']),
        no_watchlist=sum(1 for r in results if r['halted'] == 'no watchlist'),
        trades=len(trades),
        setups=sum(r['setups'] for r in results),
        passes=sum(r['passes'] for r in results),
        total=total,
        win_rate=(100 * len(wins) / len(trades)) if trades else 0,
        avg_win=(sum(wins) / len(wins)) if wins else 0,
        avg_loss=(sum(losses) / len(losses)) if losses else 0,
        profit_factor=(sum(wins) / abs(sum(losses))) if losses and sum(losses) else float('inf'),
        expectancy=(total / len(trades)) if trades else 0,
        max_dd=dd,
        best=max((r['pnl'] for r in results), default=0),
        worst=min((r['pnl'] for r in results), default=0),
        green=sum(1 for r in results if r['pnl'] > 0),
        red=sum(1 for r in results if r['pnl'] < 0),
    )


def main():
    limits = [int(x) for x in sys.argv[1:]] or [5]
    runs = {n: load(n) for n in limits}

    main_n = limits[-1]
    res = runs[main_n]['results']

    print(f'PER-DAY  (max_trades={main_n})\n')
    print(f'{"day":<12} {"names":>5} {"setups":>7} {"pass":>5} {"trades":>7} '
          f'{"P&L":>9} {"cum":>9}  stopped because')
    cum = 0.0
    for r in res:
        cum += r['pnl']
        print(f'{r["day"]:<12} {len(r.get("watch", [])):>5} {r["setups"]:>7} '
              f'{r["passes"]:>5} {len(r["trades"]):>7} {r["pnl"]:>9.2f} '
              f'{cum:>9.2f}  {r["halted"] or ""}')

    print('\n\nAGGREGATE\n')
    hdr = f'{"metric":<22}' + ''.join(f'{"max=" + str(n):>14}' for n in limits)
    print(hdr)
    print('-' * len(hdr))
    S = {n: stats(runs[n]['results']) for n in limits}
    rows = [('trading days', 'days', '{:.0f}'), ('days with a trade', 'traded_days', '{:.0f}'),
            ('days no watchlist', 'no_watchlist', '{:.0f}'),
            ('setups evaluated', 'setups', '{:.0f}'), ('setups passing gate', 'passes', '{:.0f}'),
            ('trades taken', 'trades', '{:.0f}'),
            ('total P&L $', 'total', '{:+.2f}'), ('win rate %', 'win_rate', '{:.1f}'),
            ('avg winner $', 'avg_win', '{:+.2f}'), ('avg loser $', 'avg_loss', '{:+.2f}'),
            ('profit factor', 'profit_factor', '{:.2f}'),
            ('expectancy/trade $', 'expectancy', '{:+.2f}'),
            ('max drawdown $', 'max_dd', '{:.2f}'),
            ('best day $', 'best', '{:+.2f}'), ('worst day $', 'worst', '{:+.2f}'),
            ('green days', 'green', '{:.0f}'), ('red days', 'red', '{:.0f}')]
    for label, key, fmt in rows:
        cells = ''.join(f'{fmt.format(S[n][key]):>14}' for n in limits)
        print(f'{label:<22}{cells}')

    print('\n\nWHY SETUPS WERE REJECTED (max_trades=%d)\n' % main_n)
    rej = Counter()
    for r in res:
        for k, v in (r['rejects'] or {}).items():
            rej[k] += v
    for k, v in rej.most_common():
        print(f'  {v:>5}  {k}')

    print('\n\nTRADES\n')
    print(f'{"day":<12} {"sym":<6} {"in":>6} {"entry":>8} {"stop":>7} '
          f'{"$/sh":>6} {"sh":>6} {"out":>6} {"exit":>8} {"P&L":>9}  reason')
    for r in res:
        for t in r['trades']:
            print(f'{r["day"]:<12} {t["sym"]:<6} {t["entry_time"]:>6} '
                  f'{t["entry"]:>8.2f} {t["stop"]:>7.2f} {t["risk_ps"]:>6.2f} '
                  f'{t["full"]:>6} {t["exit_time"]:>6} {t["exit"]:>8.2f} '
                  f'{t["pnl"]:>9.2f}  {t["reason"]}')


if __name__ == '__main__':
    main()
