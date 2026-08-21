#!/usr/bin/env python3
"""The trade journal — the raw material of the improvement loop.

TradingView's Paper Trading is a sandbox Pine cannot see, so YOUR trades
only enter this repo through this file. One row per round trip, ET times.

Usage:
    python3 scripts/trade_log.py add JUNS 2026-08-21 10:01 8.80 10:05 9.40 200
    python3 scripts/trade_log.py add JUNS 2026-08-21 10:01 8.80 10:05 9.40 200 --note "reclaim after deep dip"
    python3 scripts/trade_log.py list
    python3 scripts/trade_log.py list --sym JUNS

Then:  python3 scripts/trade_audit.py       # engine verdict vs each trade

Have a TradingView paper-account export? Send one sample CSV and the
import command gets built against its REAL columns — guessing a format
this repo has never seen is how invented data starts.
"""
import argparse
import csv
import os
import sys

JOURNAL = os.path.join(os.path.dirname(__file__), '..',
                       'research', 'trade-journal', 'journal.csv')
FIELDS = ['date', 'sym', 'side', 'entry_hhmm', 'entry', 'exit_hhmm', 'exit',
          'shares', 'pnl', 'note']


def load():
    if not os.path.exists(JOURNAL):
        return []
    with open(JOURNAL, newline='') as fh:
        return list(csv.DictReader(fh))


def save(rows):
    os.makedirs(os.path.dirname(JOURNAL), exist_ok=True)
    with open(JOURNAL, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('add')
    a.add_argument('sym')
    a.add_argument('date', help='YYYY-MM-DD')
    a.add_argument('entry_hhmm', help='ET, e.g. 10:01')
    a.add_argument('entry', type=float)
    a.add_argument('exit_hhmm')
    a.add_argument('exit', type=float)
    a.add_argument('shares', type=int)
    a.add_argument('--side', default='long', choices=['long', 'short'])
    a.add_argument('--note', default='')
    ls = sub.add_parser('list')
    ls.add_argument('--sym', default=None)
    args = ap.parse_args()

    rows = load()
    if args.cmd == 'add':
        sign = 1 if args.side == 'long' else -1
        pnl = round(sign * (args.exit - args.entry) * args.shares, 2)
        rows.append(dict(date=args.date, sym=args.sym.upper(), side=args.side,
                         entry_hhmm=args.entry_hhmm, entry=args.entry,
                         exit_hhmm=args.exit_hhmm, exit=args.exit,
                         shares=args.shares, pnl=pnl, note=args.note))
        save(rows)
        print(f'logged: {args.sym.upper()} {args.date} {args.entry_hhmm} '
              f'{args.entry} -> {args.exit_hhmm} {args.exit} x{args.shares} '
              f'= {pnl:+.2f}$  ({len(rows)} trades in journal)')
    else:
        n = w = 0
        tot = 0.0
        for r in rows:
            if args.sym and r['sym'] != args.sym.upper():
                continue
            n += 1
            p = float(r['pnl'])
            tot += p
            w += p > 0
            print(f"  {r['date']} {r['sym']:6s} {r['side']:5s} "
                  f"{r['entry_hhmm']}@{r['entry']} -> {r['exit_hhmm']}@{r['exit']} "
                  f"x{r['shares']:>5s} {float(r['pnl']):+9.2f}  {r['note']}")
        if n:
            print(f'{n} trades · {w}W/{n-w}L · net {tot:+.2f}$')
        else:
            print('journal empty — add trades first (see --help)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
