#!/usr/bin/env python3
"""Every ticker named anywhere in the corpus, dated by its own megaday.

Mines ALL registers — teaching transcripts, summaries, live streams and
daily recaps — not just the recaps. A video's upload date is NOT used as
the trade date: the megaday is a property of the stock, so it is measured
from daily bars (the session with the largest intraday range). That also
filters the noise auto-captions produce: a garbled token is not a symbol
and has no megaday.

    python3 scripts/corpus_tickers.py --dry-run       # candidate counts only
    python3 scripts/corpus_tickers.py --min-files 2 --out out.csv

LIMIT: "named in the corpus" is not "he traded it" — the registers mix
trades taken, watch-list names and teaching examples. The register column
tells you which kind of mention it was.
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB = os.path.join(R, 'knowledge-base')
REGISTERS = ('recaps', 'streams', 'transcripts', 'summaries')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'

TOKEN = re.compile(r'\b([A-Z]{2,5})\b')
STOP = set('''A I AM PM AN AS AT BE BY DO GO IF IN IS IT ME MY NO OF OK ON OR SO TO UP US WE
ALL AND ANY ARE BUT CAN DAY DID FOR GET GOT HAD HAS HER HIM HIS HOW ITS LOT NEW NOT NOW
ONE OUR OUT OWN PUT SEE SHE THE TOO TWO USE WAS WAY WHO WHY YES YOU CEO CFO ETF IPO SEC
USA USD NYSE THAT THIS WITH FROM HAVE JUST LIKE WHEN WHAT BEEN MORE THAN THEN THEY WILL
INTO OVER BACK DOWN GOOD MOST ONLY SOME SUCH TAKE TIME VERY WELL WENT ABLE HERE HIGH LONG
MADE MAKE MANY NEXT ONCE REAL SAME SEEN STOP THEM OKAY YEAH GONNA WANNA REALLY THERE THESE
THOSE WOULD COULD SHOULD BECAUSE PRE GAP LOW BIG RUN OFF BUY SELL RED PDT ATR RSI MACD
VWAP HOD LOD EMA SMA AI FDA SPY QQQ OTC LLC INC LTD CO EST EDT ET LEVEL LEVELS CHART
CHARTS TRADE TRADES TRADING STOCK STOCKS MARKET MONEY RISK ENTRY EXIT SIZE SHARE SHARES
PRICE VOLUME FLOAT NEWS SCAN SCANNER ALERT ALERTS SETUP SETUPS PATTERN GREEN LOSS WIN
WINS PROFIT ACCOUNT DOLLAR CENTS PERCENT FIRST SECOND THIRD LAST BEST WORST TODAY WEEK
YEAR MONDAY TUESDAY FRIDAY SUNDAY GOAL PLAN RULE RULES FAST SLOW HARD EASY LEFT RIGHT
OPEN CLOSE HALT HALTED SHORT LONGS BULL BEAR FLAG WEDGE CANDLE CANDLES MINUTE MINUTES
HOUR HOURS LIVE WATCH LIST RECAP CLASS COURSE VIDEO GUYS OKAY WOW YEP NOPE'''.split())


def texts():
    """(register, filename, text) for every corpus transcript file."""
    for reg in REGISTERS:
        d = os.path.join(KB, reg)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.startswith('README') or not fn.endswith(('.txt', '.md', '.vtt')):
                continue
            try:
                t = open(os.path.join(d, fn), encoding='utf-8', errors='ignore').read()
            except OSError:
                continue
            yield reg, fn, t


def daily(sym, years=5):
    url = ('https://query1.finance.yahoo.com/v8/finance/chart/'
           f'{sym}?range={years}y&interval=1d')
    try:
        p = subprocess.run(['curl', '-s', '--compressed', '--max-time', '20',
                            '-H', f'User-Agent: {UA}', url],
                           capture_output=True, text=True)
        res = json.loads(p.stdout)['chart']['result'][0]
        ts, q = res['timestamp'], res['indicators']['quote'][0]
        rows = []
        for i, t in enumerate(ts):
            if q['close'][i] is None or not q['low'][i] or q['low'][i] <= 0:
                continue
            rows.append((dt.datetime.utcfromtimestamp(t).strftime('%Y-%m-%d'),
                         q['high'][i], q['low'][i], q['close'][i], q['volume'][i] or 0))
        return rows
    except Exception:
        return []


def megaday(sym):
    """Biggest genuine intraday range. Bars whose low is a tiny fraction of
    the close are rejected: on a reverse-split name Yahoo serves prints like
    CRKN 2026-08-13 low $0.0002 / close $0.0003, which computes to a 49,900%
    "range" that never happened (CLAUDE.md rule 6 — check the split, do not
    trust the raw bar). A real momentum day closes in the same order of
    magnitude it traded."""
    rows = daily(sym)
    if len(rows) < 20:
        return None
    best = None
    for i, (d, h, l, c, v) in enumerate(rows):
        if v <= 0 or l < c * 0.25:      # bad print / split artefact
            continue
        rng = (h - l) / l * 100
        if rng > 400:                    # beyond any real 1-day equity move
            continue
        if best is None or rng > best[1]:
            prev_c = rows[i - 1][3] if i else None
            chg = (c / prev_c - 1) * 100 if prev_c else None
            best = (d, rng, chg, v, c)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--min-files', type=int, default=2,
                    help='candidate must appear in at least N distinct files')
    ap.add_argument('--min-range', type=float, default=30.0,
                    help='intraday %% range that qualifies as a megaday')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--out', default=None)
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()

    files_with = defaultdict(set)
    reg_hits = defaultdict(Counter)
    nfiles = 0
    for reg, fn, txt in texts():
        nfiles += 1
        seen = set()
        for m in TOKEN.finditer(txt):
            t = m.group(1)
            if t in STOP:
                continue
            reg_hits[t][reg] += 1
            seen.add(t)
        for t in seen:
            files_with[t].add(f'{reg}/{fn}')

    cand = {t: f for t, f in files_with.items() if len(f) >= args.min_files}
    print(f'{nfiles} fichiers · {len(files_with)} tokens · '
          f'{len(cand)} candidats (>= {args.min_files} fichiers)')
    if args.dry_run:
        top = sorted(cand.items(), key=lambda kv: -len(kv[1]))[:15]
        print('les plus cités :', ', '.join(f'{t}({len(f)})' for t, f in top))
        return 0

    order = sorted(cand, key=lambda t: -len(cand[t]))
    if args.limit:
        order = order[:args.limit]
    out = []
    for i, t in enumerate(order, 1):
        mg = megaday(t)
        time.sleep(0.3)
        if not mg or mg[1] < args.min_range:
            continue
        d, rng, chg, vol, close = mg
        regs = ','.join(f'{r}:{n}' for r, n in reg_hits[t].most_common())
        out.append(dict(ticker=t, megaday=d, range_pct=round(rng, 1),
                        close_chg_pct=round(chg, 1) if chg is not None else '',
                        volume=vol, close=close, files=len(cand[t]), registers=regs))
        print(f"  {d}  {t:6s} range {rng:6.0f}%  vol {vol:>13,}  "
              f"{len(cand[t]):3d} fichiers  [{regs[:38]}]", flush=True)
        if i % 50 == 0:
            print(f'   ... {i}/{len(order)} testés, {len(out)} retenus', flush=True)
    out.sort(key=lambda r: r['megaday'])
    if args.out:
        with open(args.out, 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
            w.writeheader()
            w.writerows(out)
        print(f'\n{len(out)} tickers ecrits dans {args.out}')
    print(f'{len(out)} tickers avec un megaday >= {args.min_range}% '
          f'sur {len(order)} candidats testes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
