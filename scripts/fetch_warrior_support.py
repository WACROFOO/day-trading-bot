#!/usr/bin/env python3
"""Fetch the support.warriortrading.com help-desk corpus into the knowledge base.

A third written register, distinct from `warrior-blog/`. The blog is marketing
prose; this is the operational manual — what the platform actually does, which
scanner column means what, why an extended-hours order rejects, how the halt
codes read on Day Trade Dash. Where the blog explains a strategy, these pages
say which button produces it.

robots.txt disallows only /support/search, /support/tickets/, /support/login
and /helpdesk/; /support/solutions/** is explicitly crawlable and the site
publishes its own sitemap. This reads the sitemap plus the category tree, then
the article pages, at capped concurrency with a delay.

Categorisation is NOT regex-guessed the way the blog fetch had to guess: the
portal ships its own two-level tree (5 categories, 18 folders), so the folders
are used verbatim and an article that moves folders on the site moves here too.

Output layout, one directory per folder, each with its own README index:

    knowledge-base/warrior-support/
        README.md                      <- top-level index, grouped by category
        logging-in/README.md + *.md
        stock-scanners-day-trade-dash/README.md + *.md
        ...

Each article file keeps its source URL, folder, category and the site's own
"Modified on" date in a header comment, so a claim taken from it can be cited
the same way a video timestamp is.

Usage:
    python scripts/fetch_warrior_support.py                 # everything
    python scripts/fetch_warrior_support.py --limit 10      # smoke test
    python scripts/fetch_warrior_support.py --folder logging-in
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

SITE = 'https://support.warriortrading.com'
INDEX = f'{SITE}/support/solutions'
SITEMAP = f'{SITE}/support/sitemap.xml'
UA = 'Mozilla/5.0 (compatible; ClaudeBot/1.0; +research)'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'knowledge-base', 'warrior-support')
TREE_CACHE = os.path.join(OUT, 'TREE.json')     # tracked: it IS source data
WORKERS = 3
DELAY = 0.5


def curl(url, timeout=30, tries=3):
    """Retry with backoff — the help desk rate-limits above a few workers."""
    out = ''
    for i in range(tries):
        p = subprocess.run(['curl', '-sL', '--max-time', str(timeout),
                            '-H', f'User-Agent: {UA}', url],
                           capture_output=True, text=True, errors='replace')
        out = p.stdout
        if len(out) > 2000 and 'error code: 5' not in out[:200]:
            return out
        time.sleep(2 ** i)
    return out


def slugify(s):
    s = html.unescape(s).lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')[:60]


def strip_tags(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()


def build_tree():
    """Category -> folders, taken from the portal's own tree in document order.

    The solutions index renders each category as an h2.category-tree-item__title
    followed by its h3.folder__title children, so a single ordered scan of both
    tag types reconstructs the parent/child relation without fetching the five
    category pages separately.
    """
    raw = curl(INDEX)
    if len(raw) < 5000:
        return []
    tree, current = [], None
    pat = (r'(?is)<h2 class="category-tree-item__title[^"]*"[^>]*>(.*?)</h2>'
           r'|<h3 class="folder__title[^"]*"[^>]*>(.*?)</h3>')
    for m in re.finditer(pat, raw):
        if m.group(1) is not None:
            current = {'category': strip_tags(m.group(1)), 'folders': []}
            tree.append(current)
        elif current is not None:
            seg = m.group(2)
            href = re.search(r'href="([^"]+)"', seg)
            if not href:
                continue
            current['folders'].append({
                'name': strip_tags(seg),
                'url': SITE + href.group(1) if href.group(1).startswith('/') else href.group(1),
                'slug': slugify(strip_tags(seg)),
            })
    return tree


def folder_articles(folder_url):
    """Article URLs listed in one folder. Follows ?page=N if the folder paginates."""
    seen, page, urls = set(), 1, []
    while page <= 20:
        u = folder_url if page == 1 else f'{folder_url}?page={page}'
        raw = curl(u)
        found = re.findall(r'href="(/support/solutions/articles/[^"#?]+)"', raw)
        fresh = [SITE + f for f in dict.fromkeys(found) if SITE + f not in seen]
        if not fresh:
            break
        seen.update(fresh)
        urls += fresh
        if f'page={page + 1}' not in raw:
            break
        page += 1
        time.sleep(DELAY)
    return urls


def sitemap_articles():
    """Every article the site publishes — the completeness check on the tree walk."""
    raw = curl(SITEMAP)
    return [u for u in re.findall(r'<loc>(.*?)</loc>', raw)
            if '/support/solutions/articles/' in u]


def to_text(body):
    """HTML fragment -> readable markdown-ish text."""
    b = re.sub(r'(?is)<(script|style|noscript|svg|form|iframe)[^>]*>.*?</\1>', ' ', body)
    for lvl in range(6, 0, -1):
        b = re.sub(rf'(?is)<h{lvl}[^>]*>(.*?)</h{lvl}>',
                   lambda m, l=lvl: f'\n\n{"#" * min(l + 1, 6)} {strip_tags(m.group(1))}\n\n', b)
    b = re.sub(r'(?is)<li[^>]*>(.*?)</li>', r'\n- \1', b)
    b = re.sub(r'(?is)<img[^>]+alt="([^"]+)"[^>]*>', r'\n[image: \1]\n', b)
    b = re.sub(r'(?is)<img[^>]*>', '\n[image]\n', b)
    b = re.sub(r'(?is)<(p|div|br|tr|ul|ol|table)[^>]*>', '\n', b)
    b = re.sub(r'(?is)<t[dh][^>]*>', ' | ', b)
    b = re.sub(r'(?is)<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', r'[\2](\1)', b)
    b = re.sub(r'(?s)<[^>]+>', '', b)
    b = html.unescape(b)
    b = re.sub(r'[ \t]+', ' ', b)
    b = re.sub(r'\n[ \t]+', '\n', b)
    b = re.sub(r'\n\s*\n\s*\n+', '\n\n', b)
    return b.strip()


def extract(raw):
    """Title, the site's own Modified date, and the article body.

    The body is anchored on itemprop="articleBody" rather than the class name:
    the stylesheet in <head> mentions .article__body long before the article
    does, so a plain string search lands in the CSS. Div depth is then counted
    to the matching close so the prev/next nav and the related-article cards
    that follow it are not swept in.
    """
    m = re.search(r'(?is)<h1[^>]*>(.*?)</h1>', raw)
    title = strip_tags(m.group(1)) if m else ''

    m = re.search(r'(?is)<div class="meta"[^>]*>\s*Modified on:\s*(.*?)</div>', raw)
    modified = strip_tags(m.group(1)) if m else ''

    m = re.search(r'(?is)<div[^>]*itemprop="articleBody"[^>]*>', raw)
    if not m:
        return title, modified, None
    i = m.start()
    # `\b` ends the match at "</div", before the closing bracket, so the slice
    # has to run to the '>' or a bare "</div" is left for to_text to print.
    depth, j = 0, len(raw)
    for d in re.finditer(r'(?i)<(/?)div\b[^>]*>', raw[i:]):
        depth += -1 if d.group(1) else 1
        if depth == 0:
            j = i + d.end()
            break
    return title, modified, to_text(raw[i:j])


def slug_of(url):
    return url.rstrip('/').rsplit('/', 1)[-1][:90]


def fetch_one(job):
    """Extract and discard the HTML immediately — each page is ~320 KB against a
    fixed per-session disk allowance, and the extracted markdown is ~4 KB."""
    url, cat, folder, fslug = job
    dest = os.path.join(OUT, fslug, slug_of(url) + '.md')
    if os.path.exists(dest) and os.path.getsize(dest) > 300:
        txt = open(dest, encoding='utf-8', errors='replace').read()
        mod = re.search(r'^<!-- modified: (.*) -->$', txt, re.M)
        # Split on the title line, not on the first blank one: the header is
        # four comment lines THEN a blank THEN "# Title", so splitting on the
        # blank returns the title as part of the body and main() writes it a
        # second time on the next run.
        t = re.search(r'(?m)^# (.+)$', txt)
        # strip('\n'), not lstrip: main() re-appends the trailing newline, so a
        # left-only strip grows the file by one blank line on every re-run.
        title, body = (t.group(1), txt[t.end():].strip('\n')) if t else ('', txt.strip('\n'))
        return url, cat, folder, fslug, title, (mod.group(1) if mod else ''), body
    raw = curl(url)
    time.sleep(DELAY)
    if len(raw) < 2000:
        return url, cat, folder, fslug, None, '', None
    title, modified, text = extract(raw)
    del raw
    return url, cat, folder, fslug, title, modified, text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int)
    ap.add_argument('--folder', help='restrict to one folder slug')
    a = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    tree = build_tree()
    if not tree:
        print('solutions index fetch failed')
        return 1

    jobs, claimed = [], set()
    for cat in tree:
        for f in cat['folders']:
            for u in folder_articles(f['url']):
                if u in claimed:
                    continue
                claimed.add(u)
                jobs.append((u, cat['category'], f['name'], f['slug']))
            print(f'  {len(claimed):>4} listed  {f["slug"]}', flush=True)

    # Anything in the sitemap but in no folder — unfiled, but still fetched.
    orphans = [u for u in sitemap_articles() if u not in claimed]
    for u in orphans:
        jobs.append((u, 'Unfiled', 'Not in any folder tree', 'unfiled'))
    if orphans:
        print(f'  {len(orphans)} sitemap articles in no folder -> unfiled/')

    json.dump(tree, open(TREE_CACHE, 'w'), indent=1)

    if a.folder:
        jobs = [j for j in jobs if j[3] == a.folder]
    if a.limit:
        jobs = jobs[:a.limit]
    print(f'{len(jobs)} articles to fetch')

    got, fails = {}, 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for url, cat, folder, fslug, title, modified, text in ex.map(fetch_one, jobs):
            if not text or len(text) < 80:
                fails += 1
                print(f'  SKIP (empty) {url}')
                continue
            d = os.path.join(OUT, fslug)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, slug_of(url) + '.md'), 'w', encoding='utf-8') as fh:
                fh.write(f'<!-- source: {url} -->\n')
                fh.write(f'<!-- category: {cat} -->\n')
                fh.write(f'<!-- folder: {folder} -->\n')
                fh.write(f'<!-- modified: {modified} -->\n\n')
                fh.write(f'# {title}\n\n{text}\n')
            got.setdefault(fslug, {'category': cat, 'folder': folder, 'rows': []})
            got[fslug]['rows'].append((title or slug_of(url), url, modified, len(text)))

    if a.limit or a.folder:
        # The indexes are rebuilt from `got`, so writing them after a filtered
        # run would replace a complete index with the handful just fetched.
        # (Doing exactly this to the blog corpus is how the guard got written.)
        print(f'\n{sum(len(v["rows"]) for v in got.values())} articles written; '
              f'indexes NOT rebuilt (partial run). Re-run without '
              f'--limit/--folder to refresh them.')
        return 0

    for fslug, info in got.items():
        info['rows'].sort()
        with open(os.path.join(OUT, fslug, 'README.md'), 'w', encoding='utf-8') as fh:
            fh.write(f'# {info["folder"]} — {len(info["rows"])} articles\n\n')
            fh.write(f'Category: **{info["category"]}**  \n')
            fh.write('Fetched from support.warriortrading.com. Each file keeps its source\n'
                     'URL, folder and the site\'s own "Modified on" date in a header comment.\n\n')
            fh.write('| article | words | modified | source |\n|---|---:|---|---|\n')
            for title, url, modified, n in info['rows']:
                # Half these titles end in "| WT" — an unescaped pipe opens a
                # new table cell and shunts the word count into the next column.
                safe = title[:70].replace('|', '\\|')
                fh.write(f'| [{safe}]({slug_of(url)}.md) | {n // 6} | '
                         f'{modified[:30]} | [link]({url}) |\n')

    total = sum(len(v['rows']) for v in got.values())
    with open(os.path.join(OUT, 'README.md'), 'w', encoding='utf-8') as fh:
        fh.write('# warrior-support — the help-desk corpus\n\n')
        fh.write(f'{total} articles fetched from the public '
                 f'[support portal]({INDEX}), in the portal\'s own two-level tree.\n\n'
                 'A **third written register**, distinct from `warrior-blog/`: the blog\n'
                 'explains a strategy, these pages say which button produces it — scanner\n'
                 'columns, order routing, halt codes, extended-hours rejects, platform\n'
                 'mechanics. Operational, not directional. Nothing here is an edge claim.\n\n'
                 'Rebuild: `python scripts/fetch_warrior_support.py` (cached; re-runs are cheap)\n\n')
        by_slug = {k: v for k, v in got.items()}
        for cat in tree:
            rows = [f for f in cat['folders'] if f['slug'] in by_slug]
            if not rows:
                continue
            fh.write(f'\n## {cat["category"]}\n\n| folder | articles | |\n|---|---:|---|\n')
            for f in rows:
                fh.write(f'| {f["name"]} | {len(by_slug[f["slug"]]["rows"])} | '
                         f'[index]({f["slug"]}/README.md) |\n')
        if 'unfiled' in by_slug:
            fh.write(f'\n## Unfiled\n\nIn the sitemap but in no folder of the category tree.\n\n'
                     f'| folder | articles | |\n|---|---:|---|\n'
                     f'| Unfiled | {len(by_slug["unfiled"]["rows"])} | [index](unfiled/README.md) |\n')
    print(f'\n{total} articles written to {OUT} ({fails} skipped)')
    for fslug in sorted(got, key=lambda s: -len(got[s]['rows'])):
        print(f'  {len(got[fslug]["rows"]):>5}  {fslug}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
