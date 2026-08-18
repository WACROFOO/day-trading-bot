#!/usr/bin/env python3
"""Fetch the warriortrading.com written corpus into the knowledge base.

The knowledge base is built entirely from auto-captioned speech. The site
carries a second corpus in edited prose - evergreen guides plus several hundred
dated written trade recaps - which states entries, exits and reasoning in
writing rather than talking over a chart.

robots.txt on the site explicitly Allows ClaudeBot / Claude-User /
Claude-SearchBot. This reads the public Yoast sitemaps and then the article
pages, at a capped concurrency with a delay, and caches so a re-run does not
re-request anything already stored.

Output layout, one directory per category, each with its own README index:

    knowledge-base/warrior-blog/
        README.md                     <- top-level index
        core-strategy/README.md + *.md
        indicators/README.md + *.md
        ...

Each article file keeps the source URL and lastmod in a header comment, so any
claim taken from it can be cited the same way a video timestamp is.

Usage:
    python scripts/fetch_warrior_blog.py                # everything
    python scripts/fetch_warrior_blog.py --limit 20     # smoke test
    python scripts/fetch_warrior_blog.py --category indicators
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

SITE = 'https://www.warriortrading.com'
SITEMAPS = ['post-sitemap', 'post-sitemap2', 'post-sitemap3', 'page-sitemap']
UA = 'Mozilla/5.0 (compatible; ClaudeBot/1.0; +research)'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'knowledge-base', 'warrior-blog')
CACHE = os.path.join(OUT, '.raw')
WORKERS = 3                      # the site 504s above this - it is a small business
DELAY = 0.6
URLS_CACHE = os.path.join(OUT, 'URLS.json')   # tracked: it IS source data

REGISTERS = [
    ('recaps', r'recap|green-day|red-day|-challenge|trade-of-the|day-\d+|ross-trade|mikes-|small-account-\d'),
    ('reviews', r'-review(-20\d\d)?$|-review-'),
    ('market-notes', r'market-overview|week-of-|market-recap|watch-?list-for'),
    ('quotes-answers', r'^/(quote|answers)/'),
]
TOPICS = [
    ('core-strategy', r'momentum|bull-flag|gap-go|gap-and-go|micro-pullback|abcd|flat-top|breakout|'
                      r'reversal|dip|scalp|swing-trad|red-to-green|opening-range|trading-strategy'),
    ('candlesticks', r'candlestick|doji|hammer|engulfing|harami|shooting-star|marubozu|spinning-top|'
                     r'morning-star|evening-star|read-stock-chart|chart-pattern|head-and-shoulders|'
                     r'triangle|wedge|cup-and-handle|pennant|support-and-resistance'),
    ('indicators', r'vwap|macd|moving-average|\bema\b|\bsma\b|\brsi\b|bollinger|stochastic|fibonacci|'
                   r'\batr\b|\badx\b|\bobv\b|ichimoku|indicator'),
    ('risk-psychology', r'risk|position-siz|stop-loss|money-manage|psycholog|emotion|discipline|fomo|'
                        r'revenge|tilt|journal|profit-loss-ratio|win-rate|expectancy|drawdown|mindset'),
    ('rules-regulation', r'pdt|pattern-day-trader|25k|margin|settlement|wash-sale|tax|finra|regulation|'
                         r'short-sale-rule|\bssr\b|halt|circuit-breaker'),
    ('tools-platforms', r'scanner|screener|software|platform|thinkorswim|das-trader|lightspeed|sterling|'
                        r'interactive-broker|webull|schwab|etrade|tradingview|hotkey|level-2|'
                        r'time-and-sales|computer|monitor|broker'),
    ('short-selling', r'short-sell|how-to-short|short-squeeze|borrow|locate|hard-to-borrow|short-interest'),
    ('terminology', r'terminolog|glossary|what-is|definition|float|market-cap|pre-market|after-hours|'
                    r'extended-hours|order-type|limit-order|market-order|bid-ask|spread|liquidity|volume'),
    ('getting-started', r'how-much-money|small-account-guide|getting-started|beginner|make-a-living|'
                        r'full-time|quit-your-job|prop-firm|funded'),
]


def curl(url, timeout=30, tries=3):
    """Retry with backoff. The site returns 504 under sustained concurrency."""
    for i in range(tries):
        p = subprocess.run(['curl', '-sL', '--max-time', str(timeout),
                            '-H', f'User-Agent: {UA}', url],
                           capture_output=True, text=True, errors='replace')
        out = p.stdout
        if len(out) > 2000 and 'error code: 5' not in out[:200]:
            return out
        time.sleep(2 ** i)
    return out


def sitemap_urls():
    """Sitemaps first; fall back to the cached list so a 504 does not lose the run."""
    if os.path.exists(URLS_CACHE):
        try:
            cached = json.load(open(URLS_CACHE))
            if len(cached) > 100:
                return cached
        except (OSError, json.JSONDecodeError):
            pass
    urls = {}
    for s in SITEMAPS:
        x = curl(f'{SITE}/{s}.xml')
        locs = re.findall(r'<loc>(.*?)</loc>', x)
        mods = re.findall(r'<lastmod>(.*?)</lastmod>', x)
        for i, u in enumerate(locs):
            if not u.endswith('.xml'):
                urls[u] = mods[i][:10] if i < len(mods) else ''
    if urls:
        os.makedirs(OUT, exist_ok=True)
        json.dump(urls, open(URLS_CACHE, 'w'))
    return urls


def category(u):
    path = u.replace(SITE, '').rstrip('/') or '/'
    slug = path.split('/')[-1]
    for name, rx in REGISTERS:
        if re.search(rx, path, re.I):
            return name
    for name, rx in TOPICS:
        if re.search(rx, slug, re.I):
            return name
    return 'other'


def to_text(body):
    """HTML fragment -> readable markdown-ish text."""
    b = re.sub(r'(?is)<(script|style|noscript|svg|form|iframe)[^>]*>.*?</\1>', ' ', body)
    b = re.sub(r'(?is)<figure[^>]*>.*?</figure>', ' ', b)
    for lvl in range(6, 0, -1):
        b = re.sub(rf'(?is)<h{lvl}[^>]*>(.*?)</h{lvl}>', lambda m, l=lvl: f'\n\n{"#" * l} {m.group(1)}\n\n', b)
    b = re.sub(r'(?is)<li[^>]*>(.*?)</li>', r'\n- \1', b)
    b = re.sub(r'(?is)<(p|div|br|tr)[^>]*>', '\n', b)
    b = re.sub(r'(?is)<td[^>]*>', ' | ', b)
    b = re.sub(r'(?is)<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', r'[\2](\1)', b)
    b = re.sub(r'(?s)<[^>]+>', '', b)
    b = html.unescape(b)
    b = re.sub(r'[ \t]+', ' ', b)
    b = re.sub(r'\n\s*\n\s*\n+', '\n\n', b)
    return b.strip()


def extract(raw):
    """Title from h1.post-title-blog; body from the FIRST div.post-content.

    The page nests five post-content divs - the article plus four related-post
    cards - and wraps the whole thing in a header that repeats "Warrior Trading
    Blog" as its own h1. Taking the <article> wholesale pulls in both, so the
    body is cut at whichever boundary marker appears first after the opening
    div: the tag list, a related-post h1, or the footer.
    """
    t = re.search(r'(?is)<h1[^>]*class="[^"]*post-title-blog[^"]*"[^>]*>(.*?)</h1>', raw)
    if not t:
        h1s = [x for x in re.findall(r'(?is)<h1[^>]*>(.*?)</h1>', raw)
               if 'Warrior Trading Blog' not in x]
        t = None
        title = html.unescape(re.sub(r'<[^>]+>', '', h1s[-1])).strip() if h1s else ''
    else:
        title = html.unescape(re.sub(r'<[^>]+>', '', t.group(1))).strip()

    i = raw.find('<div class="post-content">')
    if i < 0:
        m = re.search(r'(?is)<article[^>]*>(.*?)</article>', raw)
        return title, to_text(m.group(1)) if m else None
    # Walk the tags counting div depth to find the MATCHING close. Cutting at
    # the first '<h1 ' instead produced empty bodies on the older recap layout,
    # which puts an h1 inside post-content; the modern guide layout does not.
    depth, j = 0, i
    for m in re.finditer(r'(?i)<(/?)div\b', raw[i:]):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            j = i + m.end()
            break
    else:
        j = min([e for e in (raw.find('<footer', i + 26),
                             raw.find('class="related', i + 26)) if e > 0] or [len(raw)])
    return title, to_text(raw[i:j])


def slug_of(u):
    return (u.replace(SITE, '').strip('/').replace('/', '__')) or 'home'


def fetch_one(item):
    """Extract and discard the HTML immediately.

    Each page is ~1.4 MB; caching 2,162 of them would be ~3 GB against a fixed
    per-session disk allowance. The extracted markdown is ~5-10 KB, so only
    that is kept. Re-runs skip anything already written instead.
    """
    u, mod = item
    dest = os.path.join(OUT, category(u), slug_of(u)[:90] + '.md')
    if os.path.exists(dest) and os.path.getsize(dest) > 400:
        txt = open(dest, encoding='utf-8', errors='replace').read()
        # Split on the title line, not the first blank one. The header is two
        # comment lines THEN a blank THEN "# Title", so splitting on the blank
        # hands the title back as body text and main() writes it a second time
        # — every cached re-run added another copy. strip('\n') for the same
        # reason on the other end: main() re-appends the trailing newline.
        m = re.search(r'(?m)^# (.+)$', txt)
        return u, mod, (m.group(1) if m else ''), \
            (txt[m.end():] if m else txt).strip('\n')
    raw = curl(u)
    time.sleep(DELAY)
    if len(raw) < 2000:
        return u, mod, None, None
    title, text = extract(raw)
    del raw
    return u, mod, title, text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int)
    ap.add_argument('--category')
    a = ap.parse_args()

    urls = sitemap_urls()
    if not urls:
        print('sitemap fetch failed')
        return 1
    items = sorted(urls.items())
    if a.category:
        items = [(u, m) for u, m in items if category(u) == a.category]
    if a.limit:
        items = items[:a.limit]
    print(f'{len(items)} URLs to process (cache: {CACHE})')

    got = defaultdict(list)
    fails = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for i, (u, mod, title, text) in enumerate(ex.map(fetch_one, items)):
            if not text or len(text) < 200:
                fails += 1
                continue
            cat = category(u)
            name = slug_of(u)[:90] + '.md'
            d = os.path.join(OUT, cat)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, name), 'w', encoding='utf-8') as f:
                f.write(f'<!-- source: {u} -->\n<!-- lastmod: {mod} -->\n\n')
                f.write(f'# {title}\n\n{text}\n')
            got[cat].append((title or name, u, mod, len(text)))
            if (i + 1) % 200 == 0:
                print(f'  {i + 1}/{len(items)}  ({fails} skipped)', flush=True)

    # per-category index
    for cat, rows in got.items():
        rows.sort()
        with open(os.path.join(OUT, cat, 'README.md'), 'w', encoding='utf-8') as f:
            f.write(f'# {cat.replace("-", " ")} — {len(rows)} articles\n\n')
            f.write('Fetched from warriortrading.com. Each file keeps its source URL\n'
                    'and lastmod in a header comment.\n\n')
            f.write('| article | words | source |\n|---|---:|---|\n')
            for title, u, mod, n in rows:
                fn = slug_of(u)[:90] + '.md'
                f.write(f'| [{title[:70]}]({fn}) | {n // 6} | [link]({u}) |\n')

    total = sum(len(v) for v in got.values())
    with open(os.path.join(OUT, 'README.md'), 'w', encoding='utf-8') as f:
        f.write('# warrior-blog — the written corpus\n\n')
        f.write(f'{total} articles fetched from warriortrading.com public sitemaps.\n\n'
                'A **second register** independent of `transcripts/`, `recaps/` and\n'
                '`streams/`: edited prose rather than auto-captioned speech. The written\n'
                'trade recaps in particular state entries, exits and reasoning in writing.\n\n'
                'Rebuild: `python scripts/fetch_warrior_blog.py` (cached; re-runs are cheap)\n\n'
                '| category | articles | |\n|---|---:|---|\n')
        for cat in sorted(got, key=lambda c: -len(got[c])):
            f.write(f'| {cat.replace("-", " ")} | {len(got[cat])} | [index]({cat}/README.md) |\n')
    print(f'\n{total} articles written to {OUT} ({fails} skipped)')
    for cat in sorted(got, key=lambda c: -len(got[cat])):
        print(f'  {len(got[cat]):>5}  {cat}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
