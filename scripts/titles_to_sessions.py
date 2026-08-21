#!/usr/bin/env python3
"""Tickers named in his video TITLES, dated by the tape, for one month.

YouTube bot-gates caption and metadata fetches from some hosts, so the
usual route (fetch recap -> read transcript) can be closed. This one is
not: the channel listing in knowledge-base/data names tickers in 184 of
its titles, and daily bars for any month are still public. A ticker is
reported for a session only when the TAPE shows it moved that day — the
title says he covered it, the tape says when.

    python3 scripts/titles_to_sessions.py --from 2026-03-01 --to 2026-03-31

LIMIT: a title proves he made a video about the name, not that he took
the trade. Same union caveat as research/challenge-tickers/.
"""
import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
LISTING = 'knowledge-base/data/daytradewarrior_videos.json'
DOLLAR = re.compile(r'\$([A-Z]{1,5})\b')
CAPS = re.compile(r'\b([A-Z]{3,5})\b')
STOP = {'THE', 'AND', 'FOR', 'WITH', 'THIS', 'THAT', 'FROM', 'HOW', 'WHY',
        'NEW', 'DAY', 'BIG', 'TOP', 'ALL', 'OUT', 'OFF', 'RED', 'CEO', 'FDA',
        'IPO', 'SEC', 'USA', 'ETF', 'AI', 'PDT', 'LIVE', 'WATCH', 'LIST',
        'RECAP', 'STOCK', 'STOCKS', 'TRADING', 'TRADE', 'TRADER', 'MONDAY',
        'FRIDAY', 'MARKET', 'MOMENTUM', 'SHORT', 'SQUEEZE', 'HUGE', 'MAX',
        'LOSS', 'WIN', 'GREEN', 'NEWS', 'MY', 'IN', 'ON', 'UP', 'TO', 'OF',
        'A', 'I', 'IS', 'IT', 'BE', 'DO', 'GO', 'NO', 'SO', 'WE', 'BUY',
        'SELL', 'HOLD', 'GAP', 'HOD', 'VWAP', 'MACD', 'EMA', 'ATR', 'RVOL',
        'YOU', 'ARE', 'CAN', 'GET', 'GOT', 'HAS', 'HAD', 'WAS', 'NOT', 'BUT',
        'ONE', 'TWO', 'NOW', 'WAY', 'SEE', 'SET', 'PLAN', 'RULE', 'RULES',
        'BEST', 'WORST', 'FIRST', 'LAST', 'NEXT', 'BACK', 'OVER', 'INTO',
        'WEEK', 'YEAR', 'TIME', 'MADE', 'MAKE', 'LOST', 'WENT', 'BEEN',
        'BROKE', 'LIVE!', 'PENNY', 'BIOTECH', 'CHINA', 'SPACE'}


def bars(sym, p1, p2):
    url = ('https://query1.finance.yahoo.com/v8/finance/chart/'
           f'{sym}?period1={p1}&period2={p2}&interval=1d')
    try:
        p = subprocess.run(['curl', '-s', '--compressed', '--max-time', '20',
                            '-H', f'User-Agent: {UA}', url],
                           capture_output=True, text=True)
        res = json.loads(p.stdout)['chart']['result'][0]
        ts, q = res['timestamp'], res['indicators']['quote'][0]
        out = []
        for i, t in enumerate(ts):
            if q['close'][i] is None or not q['low'][i]:
                continue
            out.append((dt.datetime.utcfromtimestamp(t).strftime('%Y-%m-%d'),
                        q['open'][i], q['high'][i], q['low'][i],
                        q['close'][i], q['volume'][i]))
        return out
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='dfrom', required=True)
    ap.add_argument('--to', dest='dto', required=True)
    ap.add_argument('--min-range', type=float, default=30.0,
                    help='intraday range %% that counts as a session he could trade')
    ap.add_argument('--caps', action='store_true',
                    help='also mine ALLCAPS tokens, not just $TICKER (noisier)')
    ap.add_argument('--limit', type=int, default=25)
    ap.add_argument('--idx-from', type=int, default=None,
                    help='only mine titles in this listing index band (the listing '
                         'is reverse-chronological; calibrate with known dates)')
    ap.add_argument('--idx-to', type=int, default=None)
    args = ap.parse_args()

    listing = json.load(open(LISTING))['videos']
    lo = args.idx_from if args.idx_from is not None else 0
    hi = args.idx_to if args.idx_to is not None else len(listing)
    cand = {}
    for i, v in enumerate(listing):
        if not (lo <= i <= hi):
            continue
        t = v['title']
        for m in DOLLAR.finditer(t):
            cand.setdefault(m.group(1), []).append((i, t))
        if args.caps:
            for m in CAPS.finditer(t):
                if m.group(1) not in STOP:
                    cand.setdefault(m.group(1), []).append((i, t))
    print(f'titles {lo}..{hi} of {len(listing)} · '
          f'{len(cand)} ticker candidates named in them')

    d1 = dt.datetime.strptime(args.dfrom, '%Y-%m-%d')
    d2 = dt.datetime.strptime(args.dto, '%Y-%m-%d')
    p1 = int((d1 - dt.timedelta(days=5)).timestamp())
    p2 = int((d2 + dt.timedelta(days=5)).timestamp())

    hits = []
    for i, (sym, titles) in enumerate(sorted(cand.items()), 1):
        rows = bars(sym, p1, p2)
        time.sleep(0.35)
        best = None
        for (d, o, h, l, c, vol) in rows:
            if not (args.dfrom <= d <= args.dto):
                continue
            rng = (h - l) / l * 100
            if rng >= args.min_range and (best is None or rng > best[1]):
                best = (d, rng, c, vol)
        if best:
            hits.append(dict(ticker=sym, date=best[0], rng=best[1],
                             close=best[2], vol=best[3], idx=titles[0][0],
                             title=titles[0][1][:70], mentions=len(titles)))
            print(f"  {best[0]}  {sym:6s} range {best[1]:5.0f}%  "
                  f"vol {best[3]:>12,}  [idx {titles[0][0]}]  "
                  f"\"{titles[0][1][:46]}\"", flush=True)
        if len(hits) >= args.limit:
            break
    print(f'\n{len(hits)} tickers named in a title AND moving in '
          f'{args.dfrom}..{args.dto}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
