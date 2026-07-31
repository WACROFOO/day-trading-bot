#!/usr/bin/env python3
"""Extract the trading platform he uses and the features he relies on.

The strategy documents say what to trade. This says what the software has to do
to trade it - which is a different question, and the one that matters if you are
building the tool rather than the rules.

Two passes:

  1. Which platform, by name. Counting mentions is enough here; the tools are
     named directly and there is nothing to infer.
  2. Which features, by capability rather than by product. A feature counts if
     he describes needing it, whether or not he names the vendor. This is the
     part worth building from, because it survives the platform going away.

Hotkeys get their own pass. They are the one feature where he states the actual
key bindings, so they can be reproduced exactly rather than approximated.

Input:  knowledge-base/transcripts/*.txt
Output: knowledge-base/data/platform_features.md

Usage:
    python scripts/pipeline/11_platform_features.py [--window 45] [--samples 5]
"""

import argparse
import glob
import os
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
TRANSCRIPTS = os.path.join(ROOT, 'knowledge-base', 'transcripts')
OUT = os.path.join(ROOT, 'knowledge-base', 'data', 'platform_features.md')

TS_RE = re.compile(r'^\[(\d{2}):(\d{2}):(\d{2})\]\s*')

# Word boundaries matter more here than anywhere else in the pipeline: an
# unanchored 'e trade' matches 'the trade' and invents a broker out of nothing.
PLATFORMS = [
    ('Warrior / own scanner', r'warrior (trading )?(scanner|pro)|our scanner|my scanner|'
                              r'the momentum scanner|momentum scanner'),
    ('Thinkorswim',           r'think ?or ?swim|thinker ?swim'),
    ('Lightspeed',            r'light ?speed'),
    ('Schwab',                r'\bschwab\b'),
    ('Robinhood',             r'robin ?hood'),
    ('TradeStation',          r'trade ?station'),
    ('Interactive Brokers',   r'interactive brokers|\bibkr\b'),
    ('Fidelity',              r'\bfidelity\b'),
    ('Trade Ideas',           r'trade ?ideas'),
    ('DAS Trader',            r'das trader|dastrader'),
    ('Centerpoint',           r'center ?point'),
    ('E*Trade',               r'\be\*?[- ]?trade\b'),
    ('TradingView',           r'trading ?view'),
    ('Sterling',              r'sterling (trader|pro)'),
    ('Benzinga',              r'benzinga'),
    ('Webull',                r'we ?bull'),
]

# Capabilities, stated independently of vendor. This is the build spec.
FEATURES = [
    ('scanner: momentum / gappers',
     r'momentum scanner|gap ?(up )?scanner|scanner (is |shows|lights|alerts|picks)|'
     r'top (gainers|list)|scanning for|scanner criteria'),
    ('scanner: filter by float / price / volume',
     r'(filter|sort|screen|criteria) (by|on|for) (float|price|volume|relative)|'
     r'scanner (settings|filters|parameters)|set (the )?scanner'),
    ('alerts: audio / visual trigger',
     r'\balerts?\b|\balerted\b|audio (alert|cue)|\bdings?\b|'
     r'pops? up on (the|my) scanner|flash(es|ing)? (up|on)'),
    ('hotkeys: one-key order entry',
     r'hot ?keys?|shift ?\d|ctrl ?\+?\d|control ?\d|\bf\d\b key|keyboard shortcut|'
     r'press (shift|control|the)|one (click|key)|button (to|that) (buy|sell)'),
    ('hotkeys: preset share size',
     r'(preset|programmed|set up|configured) (to|for|with) \d+ shares|'
     r'\d+ share (hot ?key|button)|share size (button|preset|hot ?key)'),
    ('Level 2 / depth of book',
     r'level ?(2|two|ii)\b|depth of (book|market)|market makers?|\bmontage\b|'
     r'bid (and|\/) ask (display|window)'),
    ('time and sales / tape',
     r'time and sales|\bthe tape\b|prints (going|coming)|order flow window'),
    ('charts: multi-timeframe layout',
     r'(one|1|five|5|daily|fifteen|15) minute chart|chart (layout|setup|window)|'
     r'multiple (charts|time ?frames)|side by side'),
    ('charts: indicator overlay',
     r'\bvwap\b|moving average|\bmacd\b|indicator|overlay|study|\bema\b'),
    ('order: market vs limit control',
     r'market order|limit order|marketable limit|\bask (plus|\+)|'
     r'order type|smart routing|\broute\b|\barca\b|\bedgx\b'),
    ('order: bracket / auto stop',
     r'bracket order|auto (stop|matic stop)|stop (order|loss order)|'
     r'oco\b|attach(ed)? (a )?stop|trailing stop'),
    ('risk: auto share sizing from stop',
     r'(calculat|comput|work)(e|es|ing|ed) (my|the|your) (share size|position size)|'
     r'share size (based on|from|calculator)|risk (per trade )?calculator|'
     r'divide (my|the) risk'),
    ('risk: hard daily loss lockout',
     r'(lock(s|ed|out)?|shut (me |it )?(off|down)|cut(s|off)?) (me )?(out|off)|'
     r'max (daily )?loss (limit|setting|rule)|stop me from trading|'
     r'daily loss (limit|lockout)'),
    ('news feed integration',
     r'news (feed|scanner|window|alert)|headline(s| scanner)|press release (feed|comes)'),
    ('watchlist',
     r'watch ?list'),
    ('halt indicator',
     r'\bhalt(ed|s)?\b|circuit breaker|resumption'),
    ('simulator / paper trading',
     r'simulator|sim (account|trading|mode)|paper trad|demo account|practice account'),
    ('metrics / trade journal',
     r'(trade )?journal|track (my|your) (trades|metrics|stats)|'
     r'\bmetrics\b|statistics on (my|your)|profit ?loss (report|statement)'),
    ('broker: commissions / borrows',
     r'commission|per share fee|\bborrow\b|locate|hard to borrow|routing fee|\becn\b'),
    ('platform speed / execution quality',
     r'(fast|slow|instant|delay(ed)?|lag(gy|ging)?) (execution|fills?|platform|'
     r'software|data)|execution (speed|quality)|slippage on the fill'),
]

# Explicit key bindings. Captured separately so they can be transcribed exactly.
# A separator is required so that the plural 'shifts' is not read as shift+S,
# and spelled-out digits are included because he says them aloud ('shift one').
HOTKEY_RE = re.compile(
    r'\b(shift|control|ctrl|alt)[ +-]+'
    r'(\d+|one|two|three|four|five|six|seven|eight|nine|zero|[a-z])\b'
    r'|\bf(\d{1,2})\b key', re.I)


def load(path):
    stream = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            m = TS_RE.match(line)
            if not m:
                continue
            h, mm, s = (int(g) for g in m.groups())
            for w in TS_RE.sub('', line).split():
                stream.append((h * 3600 + mm * 60 + s, w))
    return stream


def hms(sec):
    return f'{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--window', type=int, default=45)
    ap.add_argument('--samples', type=int, default=5)
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(TRANSCRIPTS, '*.txt')))
    if not paths:
        print('No transcripts found.')
        return

    plat_re = [(n, re.compile(p, re.I)) for n, p in PLATFORMS]
    feat_re = [(n, re.compile(p, re.I)) for n, p in FEATURES]

    plat_hits, plat_videos = Counter(), defaultdict(set)
    feat_hits, feat_videos = Counter(), defaultdict(set)
    feat_samples = defaultdict(list)
    hotkey_lines, hotkey_combos = [], Counter()

    for path in paths:
        vid = os.path.splitext(os.path.basename(path))[0]
        stream = load(path)
        words = [w for _, w in stream]
        text = ' '.join(words)
        low = text.lower()

        for name, pat in plat_re:
            n = len(pat.findall(low))
            if n:
                plat_hits[name] += n
                plat_videos[name].add(vid)

        # Character offset -> word index, so excerpts stay citable to a timestamp.
        offsets, pos = [], 0
        for idx, w in enumerate(words):
            offsets.append((pos, idx))
            pos += len(w) + 1

        def word_at(char_i):
            wi = 0
            for start, idx in offsets:
                if start > char_i:
                    break
                wi = idx
            return wi

        for name, pat in feat_re:
            for m in pat.finditer(low):
                wi = word_at(m.start())
                feat_hits[name] += 1
                feat_videos[name].add(vid)
                if len(feat_samples[name]) < args.samples:
                    lo = max(0, wi - args.window)
                    hi = min(len(words), wi + args.window + 1)
                    feat_samples[name].append(
                        (vid, hms(stream[wi][0]), ' '.join(words[lo:hi])))

        for m in HOTKEY_RE.finditer(low):
            wi = word_at(m.start())
            combo = re.sub(r'[ -]+', ' ', m.group(0).lower())
            hotkey_combos[combo] += 1
            if len(hotkey_lines) < 40:
                lo, hi = max(0, wi - 30), min(len(words), wi + 31)
                hotkey_lines.append((vid, hms(stream[wi][0]), ' '.join(words[lo:hi])))

    lines = [
        '# The platform, and what it has to do',
        '',
        'What software he uses, and more usefully, which capabilities he leans on '
        'often enough that a replacement has to have them. Features are counted by '
        'capability rather than by vendor, so the list survives any particular '
        'product going away.',
        '',
        f'Context window: {args.window} words. Generated by '
        '`scripts/pipeline/11_platform_features.py`.',
        '',
        '## Platforms named',
        '',
        '| platform | mentions | videos |',
        '|---|---|---|',
    ]
    for name, n in plat_hits.most_common():
        lines.append(f'| {name} | {n} | {len(plat_videos[name])} |')

    lines += ['', '## Capabilities relied on', '',
              'Ranked by video breadth, which is the better signal — raw mentions '
              'skew toward one video that happens to be about that feature.', '',
              '| capability | mentions | videos |', '|---|---|---|']
    for name in sorted(feat_hits, key=lambda k: (-len(feat_videos[k]), -feat_hits[k])):
        lines.append(f'| {name} | {feat_hits[name]} | {len(feat_videos[name])} |')

    lines += ['', '## Hotkey bindings stated', '',
              'Key combinations spoken aloud. These are the only part of the UI he '
              'specifies precisely enough to copy.', '',
              '| combo | times stated |', '|---|---|']
    for combo, n in hotkey_combos.most_common(20):
        lines.append(f'| `{combo}` | {n} |')

    lines += ['', '### Hotkeys in context', '']
    for vid, ts, ctx in hotkey_lines[:20]:
        lines.append(f'- `{vid}` [{ts}] …{ctx}…')

    lines += ['', '## Capability detail', '']
    for name in sorted(feat_hits, key=lambda k: -len(feat_videos[k])):
        if not feat_samples[name]:
            continue
        lines += [f'### {name}', '']
        for vid, ts, ctx in feat_samples[name]:
            lines.append(f'- `{vid}` [{ts}] …{ctx}…')
        lines.append('')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    print('PLATFORMS')
    for name, n in plat_hits.most_common(8):
        print(f'  {name:24} {n:5d}  ({len(plat_videos[name])} videos)')
    print('\nCAPABILITIES (by video breadth)')
    for name in sorted(feat_hits, key=lambda k: -len(feat_videos[k])):
        print(f'  {name:38} {feat_hits[name]:5d}  ({len(feat_videos[name])} videos)')
    print('\nHOTKEY COMBOS')
    for combo, n in hotkey_combos.most_common(10):
        print(f'  {combo:12} {n}')
    print(f'\nWrote {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
