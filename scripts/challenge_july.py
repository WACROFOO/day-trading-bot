#!/usr/bin/env python3
"""Extract the July 2026 small-account challenge from the daily recaps.

The recaps are his own account of each session: what he traded, when in the
session, why he took it, and what the day did to the account. They are the only
register in the corpus where the outcome is stated by the person who took the
trade, which is what makes them the calibration set.

This pulls the structured spine - day number, P&L, tickers, pattern, catalyst -
so the 36 July videos can be read as one series instead of 36 stories. Anything
ambiguous is left for a human to read; the point is to find WHICH file to read,
not to replace reading it.

Ticker extraction is the fragile part. Transcripts are auto-captioned, so
tickers arrive as "CUPR", "cupr", or spelled out. Only uppercase 3-5 letter
tokens are taken, minus a stopword list, and each is checked against the
2,486-name pool so that "NEWS" and "VWAP" do not become positions.

Usage:
    python scripts/challenge_july.py
    python scripts/challenge_july.py --detail CUPR
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECAPS = os.path.join(ROOT, 'knowledge-base', 'recaps')
META = os.path.join(ROOT, 'research', 'momentum-replication', 'data', 'july_meta.json')
POOL = os.path.join(ROOT, 'research', 'momentum-replication', 'data', 'pool20.json')

NOISE = {'THE', 'AND', 'FOR', 'YOU', 'BUT', 'NOT', 'ALL', 'OUT', 'GET', 'WAS',
         'ARE', 'THIS', 'THAT', 'WITH', 'HAVE', 'FROM', 'JUST', 'LIKE', 'WHAT',
         'VWAP', 'MACD', 'EMA', 'SEC', 'CEO', 'IPO', 'ETF', 'USA', 'AI', 'FDA',
         'NEWS', 'PDT', 'ATM', 'NASDAQ', 'NYSE', 'AMEX', 'OKAY', 'YEAH', 'DAY',
         'ONE', 'TWO', 'BIG', 'NEW', 'NOW', 'SEE', 'WAY', 'LOT', 'BIT', 'GOT'}

PATTERNS = {
    'micro pullback': r'micro[- ]?pullback',
    'bull flag': r'bull flag',
    'ABCD': r'\bab ?cd\b',
    'dip and rip': r'dip and rip|buy(ing)? the dip|dip trade',
    'gap and go': r'gap and go',
    'flat top': r'flat top',
    'halt resumption': r'(resum\w+|halt)\w*\s+(entry|trade|buy)|trade the (first|second) halt',
    'reversal': r'\breversal\b',
    'break of VWAP': r'break of (the )?vwap',
    'high of day break': r'high of day|new high of the day',
}
CATALYSTS = {
    'breaking news': r'breaking news',
    'no news / squeeze': r'no news|without news|nothing on the news',
    'earnings': r'earnings',
    'offering/dilution': r'offering|dilut|reverse split',
    'reverse merger': r'reverse merger',
    'FDA / clinical': r'\bfda\b|clinical|trial results|phase [123]',
    'contract/partnership': r'contract|partnership|agreement|deal',
}
MONEY = re.compile(r'\$\s?([\d,]+(?:\.\d\d)?)')
DAYNUM = re.compile(r'(?:welcome to )?day (\d+)\s+(?:of (?:my|the)\s+)?'
                    r'(?:small account\s+)?challenge', re.I)
# how the account itself is reported: "up 719%", "now at $29,471"
ACCT_PCT = re.compile(r"account'?s? (?:is |was )?(?:now )?up (\d+)\s?%", re.I)
ACCT_BAL = re.compile(r"account'?s? (?:is |was )?(?:now )?(?:at |worth )\$([\d,]+(?:\.\d\d)?)", re.I)


def load_pool():
    try:
        return {c['sym'] for c in json.load(open(POOL))}
    except (OSError, json.JSONDecodeError):
        return set()


def parse(path, pool):
    txt = open(path).read()
    head = {}
    for line in txt.splitlines()[:6]:
        m = re.match(r'#\s*(\w+):\s*(.+)', line)
        if m:
            head[m.group(1)] = m.group(2).strip()
    title = txt.splitlines()[0].lstrip('# ').strip()
    body = '\n'.join(l for l in txt.splitlines() if l.startswith('['))
    low = body.lower()

    toks = Counter(t for t in re.findall(r'\b[A-Z]{2,5}\b', body)
                   if t not in NOISE and (not pool or t in pool))
    dm = DAYNUM.search(body)
    if not dm:
        dm = re.search(r'welcome to day (\d+)', body, re.I)
    pct = ACCT_PCT.search(body)
    bal = ACCT_BAL.search(body)
    # dollar figures over 100 are P&L or balances; below that they are prices
    amts = sorted({float(x.replace(',', '')) for x in MONEY.findall(body)
                   if float(x.replace(',', '')) >= 100}, reverse=True)
    return dict(
        vid=os.path.splitext(os.path.basename(path))[0],
        title=title, date=head.get('upload_date', ''),
        dur=int(head.get('duration_sec', 0)) // 60,
        day=int(dm.group(1)) if dm else None,
        acct_pct=int(pct.group(1)) if pct else None,
        acct_bal=float(bal.group(1).replace(',', '')) if bal else None,
        tickers=[t for t, _ in toks.most_common(6)],
        tick_counts=dict(toks.most_common(6)),
        amounts=amts[:4],
        patterns=[k for k, rx in PATTERNS.items() if re.search(rx, low)],
        catalysts=[k for k, rx in CATALYSTS.items() if re.search(rx, low)],
        red=bool(re.search(r'red day|max loss|biggest loss|lost money', low)),
        green=bool(re.search(r'green day', low)),
        body=body,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--detail', help='print every line mentioning this ticker')
    a = ap.parse_args()
    pool = load_pool()
    meta = json.load(open(META))
    jul = {k: v for k, v in meta.items()
           if v.get('upload_date', '').startswith('202607')}
    rows = []
    for vid in jul:
        p = os.path.join(RECAPS, f'{vid}.txt')
        if os.path.exists(p):
            r = parse(p, pool)
            r['date'] = r['date'] or jul[vid]['upload_date']
            rows.append(r)
    rows.sort(key=lambda r: (r['date'], r['vid']))

    if a.detail:
        t = a.detail.upper()
        for r in rows:
            hits = [l for l in r['body'].splitlines()
                    if re.search(rf'\b{t}\b', l, re.I)]
            if hits:
                print(f'\n=== {r["date"]}  {r["title"]}  ({r["vid"]}) ===')
                for h in hits:
                    print(' ', h)
        return 0

    print(f'{len(rows)} July 2026 recaps\n')
    print(f'{"date":<11}{"d#":>4}  {"result":<6}{"account":<14}{"tickers":<26}pattern / catalyst')
    for r in rows:
        d = r['date']
        res = 'RED' if r['red'] and not r['green'] else ('green' if r['green'] else '')
        acct = (f'+{r["acct_pct"]}%' if r['acct_pct'] else '')
        if r['acct_bal']:
            acct += f' ${r["acct_bal"]:,.0f}'
        pc = '; '.join(r['patterns'][:2] + r['catalysts'][:2])
        print(f'{d[:4]}-{d[4:6]}-{d[6:]:<3}{r["day"] or "":>4}  {res:<6}{acct.strip():<14}'
              f'{",".join(r["tickers"][:4]):<26}{pc[:40]}')

    print('\n--- aggregates ---')
    tc = Counter(t for r in rows for t in r['tickers'])
    print(f'most-mentioned tickers: {", ".join(f"{t}({n})" for t, n in tc.most_common(12))}')
    pc = Counter(p for r in rows for p in r['patterns'])
    print(f'\npatterns named, by number of recaps:')
    for k, n in pc.most_common():
        print(f'  {n:>3}  {k}')
    cc = Counter(c for r in rows for c in r['catalysts'])
    print(f'\ncatalysts named:')
    for k, n in cc.most_common():
        print(f'  {n:>3}  {k}')
    print(f'\ndays flagged red: {sum(1 for r in rows if r["red"] and not r["green"])}'
          f' | green: {sum(1 for r in rows if r["green"])}')
    dn = [r['day'] for r in rows if r['day']]
    if dn:
        print(f'challenge day numbers seen: {min(dn)} .. {max(dn)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
