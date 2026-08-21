#!/usr/bin/env python3
"""Which tickers he traded, by session — extracted, then VALIDATED.

Auto-captions garble spelled-out symbols (the recaps README records one
video rendering INLF as INFL, INLX and INFS in a single paragraph), so
extraction alone produces noise. Every candidate is therefore checked
against the REAL tape for that date: a symbol he traded on a small-cap
momentum day moved that day, and one the captions invented did not
exist. The output carries the check, not just the claim.

    python3 scripts/challenge_tickers.py --meta <aug_meta.json> --vtt <dir>
    python3 scripts/challenge_tickers.py ... --json out.json

Classes:
  CONFIRMED   symbol resolves AND moved >= 20% intraday range that day
  WEAK        symbol resolves, move below the bar (mentioned, not the star)
  NO-MOVE     symbol resolves, flat day — probably a caption artefact
  NO-DATA     symbol does not resolve (delisted, or garbled beyond repair)
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
CACHE = {}

# Words that look like tickers in ALLCAPS captions but are not.
STOP = {
    'A', 'I', 'AM', 'PM', 'AN', 'AS', 'AT', 'BE', 'BY', 'DO', 'GO', 'IF', 'IN',
    'IS', 'IT', 'ME', 'MY', 'NO', 'OF', 'OK', 'ON', 'OR', 'SO', 'TO', 'UP', 'US',
    'WE', 'ALL', 'AND', 'ANY', 'ARE', 'BUT', 'CAN', 'DAY', 'DID', 'FOR', 'GET',
    'GOT', 'HAD', 'HAS', 'HER', 'HIM', 'HIS', 'HOW', 'ITS', 'LOT', 'NEW', 'NOT',
    'NOW', 'ONE', 'OUR', 'OUT', 'OWN', 'PUT', 'SEE', 'SHE', 'THE', 'TOO', 'TWO',
    'USE', 'WAS', 'WAY', 'WHO', 'WHY', 'YES', 'YOU', 'CEO', 'CFO', 'ETF', 'IPO',
    'SEC', 'USA', 'USD', 'NYSE', 'THAT', 'THIS', 'WITH', 'FROM', 'HAVE', 'JUST',
    'LIKE', 'WHEN', 'WHAT', 'BEEN', 'MORE', 'THAN', 'THEN', 'THEY', 'WILL',
    'INTO', 'OVER', 'BACK', 'DOWN', 'GOOD', 'MOST', 'ONLY', 'SOME', 'SUCH',
    'TAKE', 'TIME', 'VERY', 'WELL', 'WENT', 'ABLE', 'HERE', 'HIGH', 'LONG',
    'MADE', 'MAKE', 'MANY', 'NEXT', 'ONCE', 'REAL', 'SAME', 'SEEN', 'STOP',
    'THEM', 'TRADE', 'TODAY', 'STOCK', 'MARKET', 'ABOUT', 'AFTER', 'AGAIN',
    'BUY', 'SELL', 'RED', 'PDT', 'ATR', 'RSI', 'MACD', 'VWAP', 'HOD', 'LOD',
    'EMA', 'SMA', 'AI', 'FDA', 'SPY', 'QQQ', 'OTC', 'LLC', 'INC', 'LTD', 'CO',
    'EST', 'EDT', 'ET', 'YOUR', 'THEIR', 'THERE', 'THESE', 'THOSE', 'WOULD',
    'COULD', 'SHOULD', 'BECAUSE', 'PRE', 'GAP', 'LOW', 'BIG', 'RUN', 'OFF',
}

TICKER_RE = re.compile(r'\b([A-Z]{2,5})\b')
# spelled out: "s c k t" / "s-c-k-t" / "S. C. K. T."
SPELLED_RE = re.compile(r'\b(?:[A-Za-z][\s.\-]+){1,4}[A-Za-z]\b')


def caption_text(path):
    """VTT (fetched) or the corpus's timestamped .txt — same cleanup."""
    out = []
    for line in open(path, encoding='utf-8', errors='ignore'):
        line = line.strip()
        if (not line or line.startswith(('WEBVTT', 'Kind:', 'Language:', 'NOTE'))
                or '-->' in line or line.isdigit()):
            continue
        line = re.sub(r'^\[\d{2}:\d{2}:\d{2}\]\s*', '', line)   # corpus .txt stamps
        out.append(re.sub(r'<[^>]+>', '', line))
    # captions repeat lines for the rolling effect — dedupe consecutive
    ded = []
    for l in out:
        if not ded or ded[-1] != l:
            ded.append(l)
    return ' '.join(ded)


def candidates(text):
    found = {}
    for m in TICKER_RE.finditer(text):
        t = m.group(1)
        if t not in STOP:
            found[t] = found.get(t, 0) + 1
    for m in SPELLED_RE.finditer(text):
        letters = re.sub(r'[^A-Za-z]', '', m.group(0)).upper()
        if 2 <= len(letters) <= 5 and letters not in STOP:
            found[letters] = found.get(letters, 0) + 1
    return found


def daily(sym):
    if sym in CACHE:
        return CACHE[sym]
    url = ('https://query1.finance.yahoo.com/v8/finance/chart/'
           f'{sym}?range=3mo&interval=1d')
    try:
        p = subprocess.run(['curl', '-s', '--compressed', '--max-time', '20',
                            '-H', f'User-Agent: {UA}', url],
                           capture_output=True, text=True)
        res = json.loads(p.stdout)['chart']['result'][0]
        ts = res['timestamp']
        q = res['indicators']['quote'][0]
        rows = {}
        for i, t in enumerate(ts):
            if q['close'][i] is None:
                continue
            d = dt.datetime.utcfromtimestamp(t).strftime('%Y-%m-%d')
            rows[d] = dict(o=q['open'][i], h=q['high'][i], l=q['low'][i],
                           c=q['close'][i], v=q['volume'][i])
        CACHE[sym] = rows
    except Exception:
        CACHE[sym] = {}
    time.sleep(0.4)
    return CACHE[sym]


def classify(sym, date):
    rows = daily(sym)
    if not rows:
        return 'NO-DATA', ''
    bar = rows.get(date)
    if not bar:
        return 'NO-DATA', 'no bar that session'
    if not bar['l'] or bar['l'] <= 0:
        return 'NO-DATA', ''
    rng = (bar['h'] - bar['l']) / bar['l'] * 100
    prev = sorted(d for d in rows if d < date)
    chg = ((bar['c'] / rows[prev[-1]]['c'] - 1) * 100) if prev else None
    note = f"range {rng:.0f}%" + (f" · close {chg:+.0f}%" if chg is not None else '')
    if rng >= 20:
        return 'CONFIRMED', note
    if rng >= 8:
        return 'WEAK', note
    return 'NO-MOVE', note


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--meta', required=True, help='video metadata json')
    ap.add_argument('--vtt', default=None, help='directory of .en.vtt caption files')
    ap.add_argument('--since', default='20260730')
    ap.add_argument('--min-hits', type=int, default=2,
                    help='mentions needed before a candidate is checked')
    ap.add_argument('--json', default=None)
    args = ap.parse_args()

    meta = json.load(open(args.meta))
    vids = sorted(((v, m) for v, m in meta.items()
                   if m.get('upload_date', '') >= args.since),
                  key=lambda kv: kv[1]['upload_date'], reverse=True)
    print(f'{len(vids)} videos since {args.since}\n')

    out = []
    for vid, m in vids:
        date_iso = dt.datetime.strptime(m['upload_date'], '%Y%m%d').strftime('%Y-%m-%d')
        text = (m.get('title', '') + ' ' + (m.get('description') or ''))
        src = 'title+description'
        cap = None
        if args.vtt:
            for ext in ('.en.vtt', '.txt'):
                cand = os.path.join(args.vtt, f'{vid}{ext}')
                if os.path.exists(cand):
                    cap = cand
                    break
        if cap:
            text += ' ' + caption_text(cap)
            src = 'captions'
        cands = {t: n for t, n in candidates(text).items() if n >= args.min_hits}
        rows = []
        for t, n in sorted(cands.items(), key=lambda kv: -kv[1]):
            cls, note = classify(t, date_iso)
            rows.append(dict(ticker=t, hits=n, cls=cls, note=note))
        conf = [r for r in rows if r['cls'] == 'CONFIRMED']
        weak = [r for r in rows if r['cls'] == 'WEAK']
        print(f"{date_iso}  {m['title'][:52]}")
        print(f"   source: {src}")
        if conf:
            print('   TRADED/DISCUSSED (moved that day): ' +
                  ', '.join(f"{r['ticker']} ({r['note']}, x{r['hits']})" for r in conf))
        if weak:
            print('   also mentioned: ' + ', '.join(f"{r['ticker']} ({r['note']})" for r in weak))
        if not conf and not weak:
            print('   no validated ticker — captions missing or none moved')
        print()
        out.append(dict(video=vid, date=date_iso, title=m['title'],
                        source=src, rows=rows))
    if args.json:
        json.dump(out, open(args.json, 'w'), indent=1)
        print(f'wrote {args.json}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
