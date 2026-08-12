#!/usr/bin/env python3
"""The standard "where are we" command. One report shape, phase-aware.

    ./now                     phase header + tape of the watchlist
    ./now MSGY WYHG           same, for these symbols (watchlist untouched)
    ./now --set MSGY WYHG     save the watchlist, then report
    ./now --scan              also run the gap scanner (pre-market phases)

The header is always the same four facts: date/time in ET and France, the
market phase, the countdown to the next boundary, and where that leaves us
against the money window (09:35-11:00 ET, hard stop 11:30). The body is the
tape.py workup per symbol - the provenance source - so every number in a
verdict traces to this output.

Phases:  CLOSED -> PRE-MARKET 04:00 -> OPENING DRIVE 09:30 (hands off)
         -> MONEY WINDOW 09:35 -> WIND-DOWN 11:00 -> OFF-BOOK 11:30
         -> AFTER HOURS 16:00 -> CLOSED 20:00.  Weekends: CLOSED.
"""
import argparse
import datetime as dt
import os
import subprocess
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tape  # noqa: E402

ET = ZoneInfo('America/New_York')
FR = ZoneInfo('Europe/Paris')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST = os.path.join(ROOT, 'watchlist.txt')

# (start minute, name, advice) - the phase runs until the next entry's start
PHASES = [
    (0,        'CLOSED',        'nothing to do'),
    (4 * 60,   'PRE-MARKET',    'scan: ./now --scan   (the move can happen HERE - JWEL ran 07:00-07:45)'),
    (9 * 60 + 30, 'OPENING DRIVE', 'HANDS OFF - let the first candles print'),
    (9 * 60 + 35, 'MONEY WINDOW', 'pullbacks 1-2 only, tape.py before every entry'),
    (11 * 60,  'WIND-DOWN',     'new entries only on a perfect setup'),
    (11 * 60 + 30, 'OFF-BOOK',  'past the hard stop - review, do not trade'),
    (16 * 60,  'AFTER HOURS',   'session over - run trade-review if trades were taken'),
    (20 * 60,  'CLOSED',        'nothing to do'),
]


def phase_at(now_et):
    m = now_et.hour * 60 + now_et.minute
    if now_et.weekday() >= 5:
        return 'CLOSED (weekend)', 'nothing to do', None
    cur = PHASES[0]
    nxt = None
    for i, p in enumerate(PHASES):
        if m >= p[0]:
            cur = p
            nxt = PHASES[i + 1] if i + 1 < len(PHASES) else None
    left = ''
    if nxt:
        d = nxt[0] - m
        left = f' -> {nxt[1]} in {d//60}h{d%60:02d}m' if d >= 60 else f' -> {nxt[1]} in {d}m'
    return cur[1], cur[2], left


def header():
    now = dt.datetime.now(ET)
    name, advice, left = phase_at(now)
    print('=' * 64)
    print(f"{now:%a %d %b} · {now:%H:%M:%S} ET ({now.astimezone(FR):%H:%M} France)")
    print(f"phase: {name}{left or ''}")
    print(f"       {advice}")
    print(f"money window 09:35-11:00 ET · hard stop 11:30 · paper only")
    print('=' * 64)
    return name


def watchlist():
    if os.path.exists(WATCHLIST):
        with open(WATCHLIST) as f:
            return [s.strip().upper() for s in f.read().split() if s.strip()]
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('symbols', nargs='*')
    ap.add_argument('--set', nargs='+', metavar='SYM', dest='set_wl',
                    help='save these symbols as the watchlist')
    ap.add_argument('--scan', action='store_true',
                    help='also run premarket_stars (pre-market phases)')
    ap.add_argument('--bars', type=int, default=5)
    args = ap.parse_args()

    if args.set_wl:
        with open(WATCHLIST, 'w') as f:
            f.write('\n'.join(s.upper() for s in args.set_wl) + '\n')
        print(f'watchlist -> {" ".join(s.upper() for s in args.set_wl)}')

    name = header()

    if args.scan:
        subprocess.run([sys.executable,
                        os.path.join(ROOT, 'scripts', 'premarket_stars.py'),
                        '--all'])
        print()

    syms = [s.upper() for s in args.symbols] or (args.set_wl and
            [s.upper() for s in args.set_wl]) or watchlist()
    if not syms:
        print('no watchlist - set one:  ./now --set SYM SYM')
        if name == 'PRE-MARKET' and not args.scan:
            print('or scan the gappers:     ./now --scan')
        return
    if name.startswith('CLOSED') or name == 'AFTER HOURS':
        print(f'[showing the last session for: {" ".join(syms)}]\n')
    for s in syms:
        try:
            tape.study(s, args.bars)
        except Exception as e:
            print(f'{s}: fetch failed ({e})\n')


if __name__ == '__main__':
    main()
