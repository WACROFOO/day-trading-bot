#!/usr/bin/env python3
"""Position size, target and stop from a chart level — never from a feeling.

    shares = risk / (entry - stop)

That is the whole formula.  The stop comes off the chart FIRST; the size is
whatever falls out of it.  Sizing first and then picking a stop that fits the
size is the single most common way a €10 risk becomes a €60 loss.

Two constraints the formula alone does not give you:

  ACCOUNT CAP    shares x entry cannot exceed the cash.  A very tight stop
                 asks for a position bigger than the account, and the honest
                 answer is then "you risk less than your limit", not "use
                 margin".  With a 500 account risking 10 (2%), any stop
                 closer than 2% of entry hits this wall.

  STOP FLOOR     PARAMETERS.md section 5 has a stop_min_distance for a reason:
                 a stop inside the spread or inside one ATR of noise is not a
                 stop, it is a coin flip that pays commission.

Expectancy, so the reward:risk is not chosen by taste:

    E = win_rate x (R x risk) - (1 - win_rate) x risk

At a 50% win rate, 1:1 is exactly break-even and every cent of slippage makes
it negative.  2:1 returns +0.5R per trade.  The breakeven win rate for a given
R is 1/(1+R), printed below so the assumption is visible rather than implied.

Usage:
    python scripts/size.py --entry 6.36 --stop 5.90
    python scripts/size.py --entry 6.36 --stop 5.90 --account 500 --risk 10
    python scripts/size.py --entry 11.72 --stop 10.75 --rr 3 --winrate 0.5
"""
import argparse
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--entry', type=float)
    ap.add_argument('--stop', type=float,
                    help='a level READ OFF THE CHART, below support')
    ap.add_argument('--card', action='store_true',
                    help='the one-line rule and its lookup table')
    ap.add_argument('--account', type=float, default=500.0)
    ap.add_argument('--risk', type=float, default=10.0, help='per trade')
    ap.add_argument('--daily-stop', type=float, default=30.0)
    ap.add_argument('--rr', type=float, default=2.0, help='reward:risk target')
    ap.add_argument('--winrate', type=float, default=0.5)
    a = ap.parse_args()

    if a.card:
        # position = risk / (entry-stop) * entry = risk / stop%, so with a
        # fixed per-trade risk the entry price cancels out entirely and the
        # money down depends ONLY on how far the stop is, in percent.
        print(f'\n  put in = {a.risk*100:.0f} / (stop distance in %)'
              f'      [risk {a.risk:.0f}, account {a.account:.0f}]\n')
        print(f'  {"stop is":>9}   {"put in":>8}   {"% of account":>12}')
        for pct in (2, 3, 5, 7, 8, 10, 15, 20, 30):
            pos = a.risk / (pct / 100)
            flag = '   <- your whole account' if pos >= a.account else ''
            print(f'  {pct:>7}%   {min(pos, a.account):>8.0f}'
                  f'   {min(pos, a.account)/a.account*100:>11.0f}%{flag}')
        print(f'\n  shares = put in / price.  Below '
              f'{a.risk/a.account*100:.0f}% the position would exceed the '
              f'account: risk less, never borrow.\n')
        return 0

    if a.entry is None or a.stop is None:
        ap.error('--entry and --stop are required (or use --card)')
    if a.stop >= a.entry:
        print('stop must be below entry for a long', file=sys.stderr)
        return 1

    per_share = a.entry - a.stop
    pct = per_share / a.entry * 100
    want = a.risk / per_share
    cap = a.account / a.entry
    shares = int(min(want, cap))
    capped = want > cap

    real_risk = shares * per_share
    position = shares * a.entry
    target = a.entry + a.rr * per_share
    be_wr = 1 / (1 + a.rr)
    exp_r = a.winrate * a.rr - (1 - a.winrate)

    print(f'\n  entry      {a.entry:>8.2f}')
    print(f'  stop       {a.stop:>8.2f}   {per_share:.2f}/share = {pct:.1f}% away')
    print(f'  target     {target:>8.2f}   {a.rr:.0f}:1')
    print(f'\n  shares     {shares:>8d}' + ('   <- CAPPED by the account, not by the stop'
                                            if capped else ''))
    print(f'  position   {position:>8.2f}   {position/a.account*100:.0f}% of the account')
    print(f'  risking    {real_risk:>8.2f}   of a {a.risk:.2f} limit')
    print(f'  if it wins {a.rr*real_risk:>8.2f}')
    print(f'\n  breakeven win rate at {a.rr:.0f}:1 is {be_wr:.0%}; you assume '
          f'{a.winrate:.0%}')
    print(f'  expectancy {exp_r:+.2f}R per trade = '
          f'{exp_r*real_risk:+.2f} per trade')
    print(f'  {int(a.daily_stop // a.risk)} losers in a row hits the '
          f'{a.daily_stop:.0f} daily stop and you are done for the day')

    if capped:
        need = a.risk / cap
        print(f'\n  The stop is too tight to risk {a.risk:.0f} with '
              f'{a.account:.0f}. To use the full limit the stop would have to '
              f'be at least {need:.2f}/share away ({need/a.entry*100:.1f}%).')
        print('  Risk less. Do not use margin to make the number work.')
    if exp_r <= 0:
        print(f'\n  At {a.winrate:.0%} and {a.rr:.0f}:1 this loses money before '
              f'a cent of slippage. Widen the target or do not take it.')
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
