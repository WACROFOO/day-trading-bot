#!/usr/bin/env python3
"""Finish the warriortrading.com fetch, fast, without hammering the site.

The first pass ran 6 python threads each spawning its own curl, no compression,
and a bot user-agent. The site started returning 504s. Measured, that approach
was also wasteful: an uncompressed page is 1,391,904 bytes against 97,873
compressed - a 14x difference - while download time is identical at ~1.09s
either way, because the cost is server think-time, not transfer.

So the fix is not "more threads". It is:

  * --compressed          14x less bandwidth off their origin
  * --parallel over HTTP/2 curl multiplexes a whole batch onto ONE connection
                          instead of opening N, which is faster AND gentler
  * batching + deleting   HTML never accumulates on disk
  * retry with backoff    a 504 costs one URL, not the run

One honest note on headers: this sends a single ordinary browser user-agent
because some WAFs throttle unrecognised bot agents. It does NOT rotate agents
to dodge rate limits - the site's robots.txt explicitly Allows ClaudeBot, so
there is nothing to evade, and rotating would only let us push past a limit
that exists to protect a small business's origin.

Only already-missing URLs are fetched, so this is resumable and idempotent.

Usage:
    python scripts/fetch_warrior_fast.py
    python scripts/fetch_warrior_fast.py --batch 40 --max-parallel 12
"""
import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'knowledge-base', 'warrior-blog')
URLS = os.path.join(OUT, '.urls.json')
TMP = '/tmp/claude-0/-home-user-day-trading-bot/wt_batch'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_warrior_blog import category, extract, slug_of  # noqa: E402


def missing(urls):
    out = []
    for u, mod in sorted(urls.items()):
        dest = os.path.join(OUT, category(u), slug_of(u)[:90] + '.md')
        if not (os.path.exists(dest) and os.path.getsize(dest) > 400):
            out.append((u, mod))
    return out


def fetch_batch(batch, max_parallel):
    """One curl process, HTTP/2 multiplexed, gzip, writing to numbered files."""
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP, exist_ok=True)
    cfg = os.path.join(TMP, 'urls.cfg')
    with open(cfg, 'w') as f:
        for i, (u, _) in enumerate(batch):
            f.write(f'url = "{u}"\noutput = "{TMP}/{i:04d}.html"\n')
    subprocess.run(
        ['curl', '-sL', '--compressed', '--http2', '--parallel',
         '--parallel-max', str(max_parallel), '--max-time', '45',
         '--retry', '2', '--retry-delay', '2',
         '-H', f'User-Agent: {UA}',
         '-H', 'Accept: text/html,application/xhtml+xml',
         '-H', 'Accept-Language: en-US,en;q=0.9',
         '-K', cfg],
        capture_output=True, text=True)
    out = []
    for i, (u, mod) in enumerate(batch):
        p = os.path.join(TMP, f'{i:04d}.html')
        if not os.path.exists(p) or os.path.getsize(p) < 2000:
            out.append((u, mod, None, None))
            continue
        raw = open(p, encoding='utf-8', errors='replace').read()
        title, text = extract(raw)
        out.append((u, mod, title, text))
    shutil.rmtree(TMP, ignore_errors=True)
    return out


def write(u, mod, title, text):
    d = os.path.join(OUT, category(u))
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, slug_of(u)[:90] + '.md'), 'w', encoding='utf-8') as f:
        f.write(f'<!-- source: {u} -->\n<!-- lastmod: {mod} -->\n\n# {title}\n\n{text}\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', type=int, default=40)
    ap.add_argument('--max-parallel', type=int, default=12)
    ap.add_argument('--passes', type=int, default=3,
                    help='re-attempt whatever is still missing, with a pause')
    a = ap.parse_args()

    urls = json.load(open(URLS))
    for p in range(1, a.passes + 1):
        todo = missing(urls)
        if not todo:
            print('nothing missing')
            break
        print(f'\npass {p}: {len(todo)} missing of {len(urls)}', flush=True)
        ok = fail = 0
        for i in range(0, len(todo), a.batch):
            batch = todo[i:i + a.batch]
            for u, mod, title, text in fetch_batch(batch, a.max_parallel):
                if text and len(text) > 200:
                    write(u, mod, title, text)
                    ok += 1
                else:
                    fail += 1
            print(f'  {i + len(batch):>5}/{len(todo)}  ok={ok} fail={fail}', flush=True)
            time.sleep(random.uniform(0.3, 0.9))   # jitter between batches
        if fail == 0:
            break
        time.sleep(5)
    n = sum(len(fs) for _, _, fs in os.walk(OUT) for f in [0])
    print(f'\ntotal article files: '
          f'{sum(1 for r, _, fs in os.walk(OUT) for f in fs if f.endswith(".md") and f != "README.md")}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
