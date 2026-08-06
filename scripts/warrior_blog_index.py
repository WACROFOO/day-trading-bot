#!/usr/bin/env python3
"""Build a categorised index of the warriortrading.com written corpus.

The video corpus in knowledge-base/ is transcripts. The site carries a second,
independent written corpus - evergreen guides plus several hundred WRITTEN
trade recaps going back years - which is a different register again: edited
prose rather than speech, and dated.

robots.txt on the site explicitly Allows ClaudeBot, Claude-User and
Claude-SearchBot, and this reads only the public Yoast sitemaps.

Classification is by slug keyword. It is deliberately conservative: anything
that does not match a topic bucket lands in `other` rather than being forced
into one, and the recap/review/market-overview registers are split out first
because they dominate by count and would otherwise swamp the guides.

Usage:
    python scripts/warrior_blog_index.py                  # rebuild from the sitemaps
    python scripts/warrior_blog_index.py --out FILE.md
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict

SITE = 'https://www.warriortrading.com'
SITEMAPS = ['post-sitemap', 'post-sitemap2', 'post-sitemap3', 'page-sitemap']
UA = 'Mozilla/5.0 (compatible; ClaudeBot/1.0)'

# Registers stripped out before topic classification, in this order.
REGISTERS = [
    ('recaps', r'recap|green-day|red-day|-challenge|trade-of-the|day-\d+|'
               r'ross-trade|mikes-|small-account-\d'),
    ('reviews', r'-review(-20\d\d)?$|-review-'),
    ('market notes', r'market-overview|week-of-|market-recap|watch-?list-for'),
    ('quotes & answers', r'^/(quote|answers)/'),
]

TOPICS = [
    ('Core strategy & setups',
     r'momentum|bull-flag|gap-go|gap-and-go|micro-pullback|abcd|flat-top|breakout|'
     r'reversal|dip|scalp|swing-trad|red-to-green|opening-range|trading-strategy'),
    ('Candlesticks & chart reading',
     r'candlestick|doji|hammer|engulfing|harami|shooting-star|marubozu|spinning-top|'
     r'morning-star|evening-star|read-stock-chart|chart-pattern|head-and-shoulders|'
     r'triangle|wedge|cup-and-handle|pennant|support-and-resistance'),
    ('Indicators',
     r'vwap|macd|moving-average|\bema\b|\bsma\b|\brsi\b|bollinger|stochastic|'
     r'fibonacci|\batr\b|\badx\b|\bobv\b|ichimoku|indicator'),
    ('Risk, sizing & psychology',
     r'risk|position-siz|stop-loss|money-manage|psycholog|emotion|discipline|fomo|'
     r'revenge|tilt|journal|profit-loss-ratio|win-rate|expectancy|drawdown|mindset'),
    ('Rules & regulation',
     r'pdt|pattern-day-trader|25k|margin|settlement|wash-sale|tax|finra|regulation|'
     r'short-sale-rule|\bssr\b|halt|circuit-breaker'),
    ('Scanners, tools & platforms',
     r'scanner|screener|software|platform|thinkorswim|das-trader|lightspeed|sterling|'
     r'interactive-broker|webull|schwab|etrade|tradingview|hotkey|level-2|'
     r'time-and-sales|computer|monitor|broker'),
    ('Short selling',
     r'short-sell|how-to-short|short-squeeze|borrow|locate|hard-to-borrow|short-interest'),
    ('Market structure & terminology',
     r'terminolog|glossary|what-is|definition|float|market-cap|pre-market|after-hours|'
     r'extended-hours|order-type|limit-order|market-order|bid-ask|spread|liquidity|volume'),
    ('Getting started & career',
     r'how-much-money|small-account-guide|getting-started|beginner|make-a-living|'
     r'full-time|quit-your-job|prop-firm|funded|day-trading$|^/day-trading'),
]


def fetch():
    urls = {}
    for s in SITEMAPS:
        p = subprocess.run(['curl', '-sL', '--max-time', '30', '-H', f'User-Agent: {UA}',
                            f'{SITE}/{s}.xml'], capture_output=True, text=True)
        locs = re.findall(r'<loc>(.*?)</loc>', p.stdout)
        mods = re.findall(r'<lastmod>(.*?)</lastmod>', p.stdout)
        for i, u in enumerate(locs):
            if u.endswith('.xml'):
                continue
            urls[u] = mods[i][:10] if i < len(mods) else ''
    return urls


def classify(urls):
    reg = defaultdict(list)
    topic = defaultdict(list)
    other = []
    for u in sorted(urls):
        path = u.replace(SITE, '').rstrip('/') or '/'
        slug = path.split('/')[-1]
        for name, rx in REGISTERS:
            if re.search(rx, path, re.I):
                reg[name].append(u)
                break
        else:
            for name, rx in TOPICS:
                if re.search(rx, slug, re.I):
                    topic[name].append(u)
                    break
            else:
                other.append(u)
    return reg, topic, other


def title_of(u):
    s = u.replace(SITE, '').strip('/').split('/')[-1]
    return re.sub(r'-', ' ', s).strip().capitalize() or '(home)'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'knowledge-base', 'WARRIOR-BLOG-INDEX.md'))
    a = ap.parse_args()

    urls = fetch()
    if not urls:
        print('sitemap fetch failed')
        return 1
    reg, topic, other = classify(urls)

    lines = ['# warriortrading.com — written corpus index', '',
             f'{len(urls)} public URLs from the four Yoast sitemaps '
             f'(`post-sitemap`, `post-sitemap2`, `post-sitemap3`, `page-sitemap`).',
             '',
             'This is a **second corpus**, independent of the video transcripts in',
             '`transcripts/`, `recaps/` and `streams/` — edited prose rather than speech.',
             'The site\'s robots.txt explicitly allows ClaudeBot.', '',
             'Rebuild: `python scripts/warrior_blog_index.py`', '',
             '## Counts', '', '| register / topic | n |', '|---|---:|']
    for name, _ in TOPICS:
        lines.append(f'| {name} | {len(topic[name])} |')
    for name, _ in REGISTERS:
        lines.append(f'| _{name}_ | {len(reg[name])} |')
    lines.append(f'| _other_ | {len(other)} |')
    lines.append('')

    lines += ['## Guides, by topic', '']
    for name, _ in TOPICS:
        if not topic[name]:
            continue
        lines += [f'### {name} ({len(topic[name])})', '']
        for u in topic[name]:
            lines.append(f'- [{title_of(u)}]({u})')
        lines.append('')

    lines += ['## Other registers', '']
    for name, _ in REGISTERS:
        if not reg[name]:
            continue
        lines += [f'### {name} ({len(reg[name])})', '']
        if name == 'recaps':
            lines += ['**Written trade recaps.** A dated, edited register the video',
                      'corpus does not contain — worth mining the same way',
                      '`knowledge-base/recaps/` was.', '']
        for u in reg[name][:60]:
            lines.append(f'- [{title_of(u)}]({u})')
        if len(reg[name]) > 60:
            lines.append(f'- …and {len(reg[name]) - 60} more')
        lines.append('')

    lines += [f'## Unclassified ({len(other)})', '']
    for u in other[:80]:
        lines.append(f'- [{title_of(u)}]({u})')
    if len(other) > 80:
        lines.append(f'- …and {len(other) - 80} more')
    lines.append('')

    with open(a.out, 'w') as f:
        f.write('\n'.join(lines))
    print(f'{len(urls)} URLs -> {a.out}')
    for name, _ in TOPICS:
        print(f'  {len(topic[name]):>5}  {name}')
    for name, _ in REGISTERS:
        print(f'  {len(reg[name]):>5}  ({name})')
    print(f'  {len(other):>5}  (unclassified)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
