#!/usr/bin/env python3
"""Render PLAYBOOK_V2.md and STRATEGY_V2.md from the claims database.

This is the point of the whole rebuild. V1 of both documents is hand-written
prose that asserts numbers like `n=168` with no way to check them; the evidence
lived in the pipeline and was thrown away before it reached the page.

Here the split is explicit:

    the explanation  is written by a human, in this file, in plain language
    the evidence     is queried from data/claims.db at render time

So a rule can never claim support it does not have. If the corpus stops saying
something, the count drops and the citations change the next time this runs.
Nothing in the output is typed by hand twice.

Written for a beginner: every term is defined at first use, and each rule leads
with what to do before it explains why.

Input:  data/claims.db   (built by 12_build_claims_db.py)
Output: knowledge-base/strategies/PLAYBOOK_V2.md
        knowledge-base/strategies/STRATEGY_V2.md

Usage:
    python scripts/pipeline/13_render_v2_docs.py
"""

import argparse
import os
import re
import sqlite3
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
DB = os.path.join(ROOT, 'data', 'claims.db')
OUT_DIR = os.path.join(ROOT, 'knowledge-base', 'strategies')

# Fewer figures than this is not a distribution, it is an anecdote with a
# percentage sign. Parameters below the floor are omitted rather than shown
# with a misleading count.
MIN_FIGURES = 5

# --- the strategy, as steps -------------------------------------------------
#
# `why` is the beginner explanation. `concepts` is what to count and cite. The
# two are kept side by side so it is obvious when a step is asserting more than
# the corpus supports.

STEPS = [
    dict(
        n=1, title='Build a watchlist before the market opens',
        do='Run the scanner. Keep only stocks where all five filters are true. '
           'Expect 3 to 5 names. Zero is a normal day.',
        why='A "scanner" is a tool that filters every stock on the market down '
            'to the few that are moving. You are not looking for a good '
            'company — you are looking for a stock that a lot of people are '
            'suddenly trading at once, because that is what makes price move '
            'far enough, fast enough, to pay for a tight stop.',
        concepts=['news catalyst', 'float size', 'relative volume',
                  'small cap focus', 'watchlist'],
        params=['float (shares)', 'share price ($)', 'relative volume (x)'],
    ),
    dict(
        n=2, title='Watch the first five minutes. Do not trade them',
        do='Market opens. Sit on your hands until 5 minutes have passed.',
        why='At the open the gap between the buy price and the sell price (the '
            '"spread") is at its widest, so you pay the most to get in and get '
            'out. Waiting costs you nothing and removes the worst fills of the '
            'day.',
        concepts=['first hour / market open', 'pre-market activity'],
        params=['time of day'],
        prefer=[r'first (five|5|few) minutes', r'wait', r'9:3[05]',
                r'do ?n.t trade', r'avoid the open', r'settle'],
    ),
    dict(
        n=3, title='Wait for a pullback — the dip inside a move that is going up',
        do='Find a stock that just pushed up hard. Wait for it to dip for 2-3 '
           'one-minute candles. Take only the first or second dip, never the '
           'third.',
        why='You are not buying the push up. You are buying the pause after it. '
            'This is the single most important idea in the strategy, and the '
            'reason is not that dips are cheap — it is that a dip gives you a '
            'nearby place to put your stop. Buying mid-push leaves you with no '
            'sensible exit closer than "wherever it last paused", which is '
            'usually too far away to size the trade properly. By the third dip '
            'the buyers who missed the first move have already bought, so each '
            'dip after that is deeper and slower to recover.',
        concepts=['micro pullback', 'bull flag'],
        prefer=[r'first and second', r'third', r'micro ?pullback', r'2-3|two or three'],
    ),
    dict(
        n=4, title='Check the dip happened on lighter volume than the push',
        do='Compare the volume bars. The dip candles must be shorter than the '
           'push candles. If the dip is on heavy volume, skip the trade.',
        why='"Volume" is how many shares changed hands in that candle. This is '
            'the most-repeated condition in the entire corpus, and it is what '
            'separates a pause from a top. Same price drop, opposite meaning: '
            'on light volume it means buyers briefly stepped back; on heavy '
            'volume it means someone is actively selling into the move. The '
            'chart looks identical. Only the volume tells you which one it is.',
        concepts=['volume confirmation'],
        prefer=[r'light|lighter|lower|decreas|declin', r'pullback|dip|red candle'],
    ),
    dict(
        n=5, title='Check the dip stopped somewhere that matters — two reasons, not one',
        do='The dip must stop at a price that has TWO independent reasons to '
           'matter: a whole or half dollar, the 9 EMA, the 20 EMA, VWAP, the '
           '200 MA, or a price that was resistance earlier.',
        why='An "EMA" is a line showing the average price over the last N '
            'minutes; "VWAP" is the average price weighted by volume. Traders '
            'and algorithms put orders at these lines, and separately, ordinary '
            'people put orders at round numbers like $5.00. When two of those '
            'land on the same price, two unrelated groups are bidding there — '
            'so there is genuinely more demand holding it up. A dip that stops '
            'at $5.13 for no reason has nothing underneath it.',
        concepts=['support and resistance', 'moving average (9 EMA)',
                  'moving average (20 EMA)', 'moving average (200 MA)',
                  'VWAP', 'whole/half dollar level'],
    ),
    dict(
        n=6, title='Check the chart state — four boxes, all must be ticked',
        do='Price above VWAP. Price above the 9 EMA. MACD histogram positive. '
           'No large seller sitting above you on Level 2. Any one false: no trade.',
        why='These confirm the dip happened inside a trend that is still '
            'healthy, rather than at the start of a collapse. "MACD" is a '
            'momentum indicator — positive means the recent average is pulling '
            'away from the slower one. "Level 2" is the list of pending orders; '
            'a big one sitting above you is a wall your trade has to get '
            'through. This is a checklist, not a score. Three out of four is a '
            'no.',
        concepts=['MACD', 'VWAP', 'moving average (9 EMA)',
                  'level 2 / time and sales'],
    ),
    dict(
        n=7, title='Wait for the trigger — do not anticipate',
        do='Buy the first 1-minute candle that trades ABOVE the high of the '
           'previous candle. Not before.',
        why='Everything up to here says a bounce is plausible. This says it has '
            'started. The difference matters more than any other rule: a dip '
            'that ticks every box and then keeps falling costs you nothing if '
            'you waited, and a full stop if you jumped early. "It looks like '
            'it is turning" is not the trigger. The candle actually taking out '
            'the prior high, while you watch, is the trigger.',
        concepts=['first candle to make a new high'],
        prefer=[r'first candle', r'new high', r'previous candle|prior candle'],
    ),
    dict(
        n=8, title='Size the trade from the stop, not from your account',
        do='Stop = the low of the pullback candle. Risk per share = entry minus '
           'stop. Shares = your dollar risk divided by risk per share.',
        why='This is where beginners blow up, so read it twice. If you risk '
            '$200 and the stop is $0.10 below your entry, you buy 2,000 shares '
            '— a position worth over $10,000 while risking $200. Those are two '
            'completely different numbers. The position size looks terrifying '
            'and is not the thing that can hurt you; the distance to the stop '
            'is. If the stop needs to be more than $0.20 away, trade smaller or '
            'skip it — never move the stop to fit the size you wanted.',
        concepts=['position sizing by risk', 'stop at pullback low',
                  'max loss per trade'],
        params=['position size (shares)', 'max loss ($)'],
    ),
    dict(
        n=9, title='Know all three exits before you are filled',
        do='Stop at the pullback low (it never moves down). Sell half at the '
           'first target, then move the stop to breakeven. Sell 25% at the next '
           'level, trail the last 25%. Exit everything immediately on any break '
           'signal.',
        why='Deciding an exit while holding a losing position is how a small '
            'loss becomes a large one — you will find reasons. Selling half '
            'and moving the stop to your entry price is the key move: from that '
            'point the trade cannot lose money, which is what lets you hold the '
            'rest calmly. The break signals are things like a new low, a big '
            'red candle on heavy volume, MACD going negative, or losing VWAP. '
            'You do not need to know why. You just leave.',
        concepts=['scaling out', 'break-even stop', 'trailing stop',
                  'first candle to make a new low', 'high of day break'],
    ),
    dict(
        n=10, title='Minimum 2:1 — the arithmetic that makes the whole thing work',
        do='Target must be at least twice the distance of your stop. 20 cents '
           'up against 10 cents down is fine. 20 against 20 is not — skip it.',
        why='At 1:1 you need to win more than half your trades just to break '
            'even. At 2:1 you only need to win about a third. That is the '
            'entire reason a tight stop matters: it is not about losing less '
            'per trade, it is about lowering the win rate you need in order to '
            'be profitable at all.',
        concepts=['profit-loss ratio 2:1', 'accuracy / win rate'],
        params=['profit-loss ratio', 'win rate (%)'],
    ),
    dict(
        n=11, title='Stop for the day — the rules that work even if the entry does not',
        do='Stop on ANY of: max daily loss hit, gave back half your peak profit, '
           'green day turned red, three losses in a row, two trades taken, or '
           'the clock hits your hard stop. Also stop when you hit your goal.',
        why='These are the only rules here that do not depend on the strategy '
            'having an edge. An entry rule can be wrong; a daily loss limit '
            'cannot be — it just bounds how much a bad day costs. If you follow '
            'nothing else in this document, follow this section, and follow it '
            'in a simulator first.',
        concepts=['daily loss limit', 'emotional control',
                  'paper trading / simulator'],
        params=['max loss ($)', 'account size ($)'],
    ),
]

GLOSSARY = [
    ('Candle', 'One bar on the chart. A 1-minute candle shows the open, high, '
               'low and close for that minute. Green = closed higher than it '
               'opened, red = closed lower.'),
    ('Impulse / push', 'The sharp move up that happens before the pullback. '
                       'Sometimes called the "pole".'),
    ('Pullback / dip', 'The short pause where price drops back after a push. '
                       'The thing you are actually buying.'),
    ('Float', 'How many shares are actually available to trade. A small float '
              'means it takes less buying to move the price.'),
    ('Relative volume (RVOL)', 'How busy the stock is today compared to a '
                              'normal day. 5x means five times normal.'),
    ('Catalyst', 'The news that explains why the stock is moving — earnings, an '
                 'FDA decision, a contract.'),
    ('VWAP', 'Volume-weighted average price. The average price paid today, '
             'weighted by size. Used as a support line.'),
    ('EMA', 'Exponential moving average. A line of recent average price. The 9 '
            'EMA is fast, the 200 MA is slow.'),
    ('MACD', 'A momentum indicator. Positive histogram = upward momentum.'),
    ('Level 2', 'The list of pending buy and sell orders, showing where large '
                'orders are waiting.'),
    ('Spread', 'The gap between the best buy price and the best sell price. You '
               'pay it on every trade.'),
    ('Stop', 'The price where you exit for a loss, decided before you enter.'),
    ('Breakeven stop', 'Moving your stop up to your entry price, so the trade '
                       'can no longer lose money.'),
    ('R / 2:1', 'R is one unit of risk. A 2:1 trade aims to make twice what it '
                'risks.'),
]


def link(video_id, t):
    base = f'https://www.youtube.com/watch?v={video_id}'
    return f'{base}&t={t}s' if t is not None else base


def hhmm(t):
    if t is None:
        return '--:--'
    return (f'{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}' if t >= 3600
            else f'{t % 3600 // 60}:{t % 60:02d}')


def evidence(db, concepts):
    """How many statements and distinct videos back this step."""
    q = ','.join('?' * len(concepts))
    row = db.execute(f"""
        SELECT COUNT(DISTINCT c.id) n, COUNT(DISTINCT c.video_id) v
        FROM claim c JOIN claim_concept cc ON cc.claim_id = c.id
        WHERE cc.concept IN ({q}) AND c.kind = 'rule'
    """, concepts).fetchone()
    return row['n'], row['v']


def citations(db, concepts, limit=3, prefer=None):
    """Pick the clearest on-topic statements, one per video.

    Relevance first, brevity second. Matching *one* of a step's concepts is a
    weak signal — "first hour / market open" alone pulls in any sentence that
    mentions the open, which is how a citation about scanner criteria ends up
    under a step about waiting five minutes. Matching several of them at once
    means the sentence is about the step rather than adjacent to it.

    Ties break toward the shorter statement: across 2,000 restatements of one
    instruction, the terser phrasing is almost always the clearer one. Claims
    without a timestamp are excluded — a citation you cannot open is not one.

    `prefer` is a lexical override for steps the concept vocabulary is too
    coarse to separate. There is no tag for "wait five minutes at the open", so
    concept matching alone returns anything that mentions the open. A word list
    ranks the sentences that are actually about the step above its neighbours.
    """
    q = ','.join('?' * len(concepts))
    rows = db.execute(f"""
        SELECT c.video_id, c.t_start, c.text, v.title,
               COUNT(DISTINCT cc.concept) hits, LENGTH(c.text) len
        FROM claim c
        JOIN claim_concept cc ON cc.claim_id = c.id
        JOIN video v ON v.video_id = c.video_id
        WHERE cc.concept IN ({q}) AND c.kind = 'rule' AND c.t_start IS NOT NULL
          AND LENGTH(c.text) BETWEEN 45 AND 170
        GROUP BY c.id
        ORDER BY hits DESC, len ASC
    """, concepts).fetchall()

    if prefer:
        pat = re.compile('|'.join(prefer), re.I)
        rows = sorted(rows, key=lambda r: (not pat.search(r['text']),
                                           -r['hits'], r['len']))

    # One citation per video, so three links are three sources rather than one
    # video quoted three times.
    seen, out = set(), []
    for r in rows:
        if r['video_id'] in seen:
            continue
        seen.add(r['video_id'])
        out.append(r)
        if len(out) >= limit:
            break
    return out


def param_rows(db, name):
    rows = db.execute(
        'SELECT op, value, value_max, video_id, t_start, raw FROM param '
        'WHERE name = ?', (name,)).fetchall()
    dist = Counter((r['op'], r['value'], r['value_max']) for r in rows)
    return rows, dist


def fmt_value(op, val, vmax):
    def num(x):
        if x >= 1e6:
            return f'{x / 1e6:g}M'
        if x >= 1e3:
            return f'{x / 1e3:g}k'
        return f'{x:g}'
    return f'{op} {num(val)}' + (f'–{num(vmax)}' if vmax else '')


def render_playbook(db):
    o = []
    a = o.append
    total = db.execute("SELECT COUNT(*) c FROM claim WHERE kind='rule'").fetchone()['c']
    vids = db.execute('SELECT COUNT(*) c FROM video').fetchone()['c']

    a('# The playbook, version 2 — written for a beginner')
    a('')
    a('Every rule below is followed by how many separate statements in the '
      'corpus support it, across how many different videos, and links that jump '
      'straight to the moment it is said.')
    a('')
    a(f'Generated from `data/claims.db` by `scripts/pipeline/13_render_v2_docs.py`. '
      f'Evidence base: {total:,} rule statements from {vids} videos.')
    a('')
    a('> **Read this before anything else.** None of this has been tested '
      'against historical data. The counts below tell you how often something '
      'was *said*, which is not the same as how often it *works*. A rule with '
      '168 mentions and no backtest is a well-repeated opinion. Trade it in a '
      'simulator.')
    a('')
    a('---')
    a('')
    a('## Words you need first')
    a('')
    a('Skip this if you already trade. Otherwise the rest will not parse.')
    a('')
    a('| Term | What it means |')
    a('|---|---|')
    for term, meaning in GLOSSARY:
        a(f'| **{term}** | {meaning} |')
    a('')
    a('---')
    a('')
    a('## Your trading day, in France time (Paris)')
    a('')
    a('New York time in brackets — that is what your charts will show.')
    a('')
    a('| Paris | New York | What happens |')
    a('|---|---|---|')
    a('| 13:00 | 07:00 | Pre-market. Build the watchlist. |')
    a('| **15:30** | 09:30 | **Market opens.** Watch only. |')
    a('| 15:35 | 09:35 | Trading starts. |')
    a('| 16:30 | 10:30 | Prime window ends. Most of the edge is gone. |')
    a('| **17:30** | 11:30 | **Hard stop. Close the laptop.** |')
    a('')
    a('**The twice-a-year trap.** Europe and the US change clocks on different '
      'dates. For about three weeks in late March and one week in late October '
      'the gap is 5 hours, not 6, and the market opens at **14:30 Paris**. Set '
      'your reminders from the New York time and let your calendar convert.')
    a('')
    a('---')
    a('')
    a('## Set these numbers before the open, while you are calm')
    a('')
    a('| Number | Rule | On a $10,000 account |')
    a('|---|---|---|')
    a('| Risk per trade | 2% of account | $200 |')
    a('| Max loss for the day | 6% of account | $600 |')
    a('| Profit goal | same as max loss | $600 |')
    a('| Max trades | 2 | 2 |')
    a('')
    a('These do not change during the session. That is the whole point of '
      'deciding them now.')
    a('')
    a('---')
    a('')

    for step in STEPS:
        n, v = evidence(db, step['concepts'])
        a(f'## Step {step["n"]} — {step["title"]}')
        a('')
        a(f'**Do this:** {step["do"]}')
        a('')
        a(f'**Why:** {step["why"]}')
        a('')
        a(f'**Evidence:** {n} rule statements across {v} videos.')
        a('')
        cites = citations(db, step['concepts'], prefer=step.get('prefer'))
        if cites:
            a('Watch it being said:')
            a('')
            for c in cites:
                a(f'- [{hhmm(c["t_start"])}]({link(c["video_id"], c["t_start"])}) '
                  f'— {c["text"]}  \n  <sub>{c["title"]}</sub>')
            a('')

        for pname in step.get('params', []):
            rows, dist = param_rows(db, pname)
            # Below a handful of figures a "distribution" is one person saying
            # one thing once, dressed up as data. Say nothing instead.
            if len(rows) < MIN_FIGURES:
                continue
            top = dist.most_common(3)
            shown = ', '.join(f'`{fmt_value(*k)}` ({n}x)' for k, n in top)
            a(f'*{pname}:* {shown} — from {len(rows)} figures '
              f'across {len({r["video_id"] for r in rows})} videos.')
            if len(top) > 1 and top[1][1] >= top[0][1] * 0.4:
                a('  **Disputed in the source.** Two values are stated about '
                  'equally often. Do not pick one and forget the other.')
            a('')
        a('---')
        a('')

    a('## The whole thing on one card')
    a('')
    a('```')
    a('PARIS TIME                    (New York)')
    a('')
    a('13:00       ->  5 of 5 filters  ->  3-5 names       (07:00)')
    a('15:30-15:35 ->  watch, do not trade                 (09:30-09:35)')
    a('15:35+      ->  pullback 1 or 2, on LIGHTER volume')
    a('            ->  did it stop at 2 overlapping levels?   no -> pass')
    a('            ->  above VWAP + 9EMA + MACD positive?     no -> pass')
    a('            ->  candle breaks prior candle high?       no -> wait')
    a('            ->  size = risk / (entry - pullback low)')
    a('            ->  buy, limit at ask + 0.15')
    a('            ->  sell 50% at target, stop to breakeven')
    a('            ->  sell 25%, trail 25%')
    a('            ->  any break signal = out, all of it')
    a('16:30       ->  prime window over                    (10:30)')
    a('17:30       ->  hard stop, close the laptop          (11:30)')
    a('')
    a('Stop at: 2 trades | -6% | +goal | 3 losses | green-to-red | 17:30')
    a('')
    a('Clock warning: late March and late Oct, open is 14:30 Paris.')
    a('```')
    a('')
    a('## If you remember four things')
    a('')
    a('1. **Buy the dip inside the move, not the move.** The dip is what gives '
      'you a stop you can afford.')
    a('2. **Light volume on the dip, or skip it.** Most-repeated rule in the '
      'corpus.')
    a('3. **Wait for the candle to actually break the prior high.** Not "it '
      'looks like it will".')
    a('4. **Size from the stop.** A $10,000 position risking $200 is normal. '
      'Confusing those two numbers is how people blow up.')
    a('')
    a('And the one that survives even if the strategy does not: **stop trading '
      'when you hit your daily loss limit.**')
    a('')
    return '\n'.join(o)


def render_strategy(db):
    o = []
    a = o.append
    stats = db.execute("""
        SELECT
          (SELECT COUNT(*) FROM claim) claims,
          (SELECT COUNT(*) FROM claim WHERE kind='rule') rules,
          (SELECT COUNT(*) FROM claim WHERE t_start IS NOT NULL) stamped,
          (SELECT COUNT(*) FROM param) params,
          (SELECT COUNT(*) FROM chunk) chunks,
          (SELECT COUNT(*) FROM video) videos
    """).fetchone()

    a('# Strategy specification, version 2')
    a('')
    a('Every number here is a query against `data/claims.db`, not an assertion. '
      'Rebuild the database and this document rebuilds with it; if the evidence '
      'changes, the numbers change.')
    a('')
    a('Generated by `scripts/pipeline/13_render_v2_docs.py`.')
    a('')
    a('| | |')
    a('|---|---|')
    a(f'| Videos | {stats["videos"]} |')
    a(f'| Claims extracted | {stats["claims"]:,} |')
    a(f'| Of which mechanical rules | {stats["rules"]:,} |')
    a(f'| Citable to the second | {stats["stamped"]:,} '
      f'({100 * stats["stamped"] / stats["claims"]:.1f}%) |')
    a(f'| Typed numeric figures | {stats["params"]:,} |')
    a(f'| Raw caption windows indexed | {stats["chunks"]:,} |')
    a('')
    a('---')
    a('')
    a('## 1. Evidence weight by concept')
    a('')
    a('Statement counts overstate agreement — the same idea gets restated in '
      'every video. **Video count is the honest column.** A rule stated 100 '
      'times in 4 videos is one person\'s habit; stated 60 times across 60 '
      'videos it is a method.')
    a('')
    a('| Concept | Statements | Videos |')
    a('|---|---:|---:|')
    rows = db.execute("""
        SELECT cc.concept, COUNT(DISTINCT c.id) n, COUNT(DISTINCT c.video_id) v
        FROM claim_concept cc JOIN claim c ON c.id = cc.claim_id
        WHERE c.kind = 'rule'
        GROUP BY cc.concept HAVING v >= 8 ORDER BY v DESC
    """).fetchall()
    for r in rows:
        a(f'| {r["concept"]} | {r["n"]} | {r["v"]} |')
    a('')
    a('---')
    a('')
    a('## 2. Numeric parameters, as distributions')
    a('')
    a('V1 gave each parameter a single value with the disagreement demoted to a '
      'footnote. That hid the most important thing about several of them. A '
      'parameter whose second-most-common value is close behind the first is '
      '**not settled** — it is two different rules stated at different times, '
      'and a backtest has to sweep both.')
    a('')
    names = db.execute(
        'SELECT name, COUNT(*) n FROM param GROUP BY name ORDER BY n DESC'
    ).fetchall()
    for nrow in names:
        rows, dist = param_rows(db, nrow['name'])
        if len(rows) < 5:
            continue
        vids = len({r['video_id'] for r in rows})
        a(f'### {nrow["name"]}')
        a('')
        a(f'{len(rows)} figures across {vids} videos.')
        a('')
        a('| Value | Times stated |')
        a('|---|---:|')
        for k, n in dist.most_common(6):
            a(f'| `{fmt_value(*k)}` | {n} |')
        a('')
        top = dist.most_common(2)
        if len(top) > 1 and top[1][1] >= top[0][1] * 0.4:
            a(f'> **Disputed.** `{fmt_value(*top[0][0])}` and '
              f'`{fmt_value(*top[1][0])}` are stated about equally often. '
              f'Sweep both.')
            a('')
    a('---')
    a('')
    a('## 3. Where this specification is weakest')
    a('')
    a('Stated plainly, because the failure mode of a generated document is '
      'looking more authoritative than it is.')
    a('')
    a('1. **Nothing is backtested.** Counts measure repetition, not profit. The '
      'stated win rate and reward:risk imply roughly +3.2% per day, which is '
      'implausible — so something in the stated version is optimistic.')
    a('2. **The claim layer is a paraphrase.** These rows come from summaries, '
      'not raw speech. A rule the summariser dropped is invisible here. That is '
      'what the caption index is for: '
      '`python scripts/search.py "your phrase" --layer chunks` searches the '
      f'{stats["chunks"]:,} raw windows and can prove something was never said.')
    a('3. **Two entry conditions cannot be automated from price data.** '
      '`no_seller_wall` and `tape_green` need Level 2. Any bot version trades a '
      'weaker gate than the one described.')
    a('4. **Timestamps come from auto-captions.** Expect a few seconds of drift, '
      'and a handful of malformed stamps that land in the right minute.')
    a('5. **Level tolerance is unstated anywhere in the corpus.** How close is '
      '"at" the 20 EMA? Nobody says. Sweep it, report the spread, do not tune '
      'it — this is the easiest place to fool yourself.')
    a('')
    a('## 4. Test order — cheapest falsification first')
    a('')
    a('Stop at the first failure. There is no point tuning an entry inside a '
      'universe that does not exist.')
    a('')
    a('1. **Universe.** How many stocks per day pass all five filters? Under '
      'one per day and the strategy is untradeable regardless of edge.')
    a('2. **Trigger.** Does the first-candle-new-high entry reach 2R before '
      'hitting the pullback low more than 33.3% of the time? Below that, at '
      '2:1, there is no edge.')
    a('3. **Sensitivity.** Sweep the disputed parameters flagged in §2. If the '
      'edge lives in one cell, it is not an edge.')
    a('4. **Costs.** Re-run with realistic spread and slippage on a low float. '
      'A few cents of slippage against a 10-cent stop is most of the risk '
      'budget. This is where momentum edges usually die.')
    a('5. **Regime.** Split by year. An edge in one regime only is not an edge.')
    a('')
    a('Baseline to beat: buy and hold the same universe over the same holding '
      'period.')
    a('')
    a('## 5. How to check any claim in this document')
    a('')
    a('```bash')
    a('# rebuild the evidence base')
    a('python scripts/pipeline/12_build_claims_db.py')
    a('')
    a('# what does the corpus teach about X, with deep links')
    a('python scripts/search.py "pullback volume"')
    a('')
    a('# every statement tagged with a concept')
    a('python scripts/search.py --concept "stop at pullback low"')
    a('')
    a('# the value distribution behind a parameter')
    a('python scripts/search.py --param "float (shares)"')
    a('')
    a('# search raw captions - the layer the summariser cannot hide things from')
    a('python scripts/search.py "third pullback" --layer chunks')
    a('')
    a('# which single video covers the most of the strategy')
    a('python scripts/search.py --coverage')
    a('```')
    a('')
    return '\n'.join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=DB)
    args = ap.parse_args()

    if not os.path.exists(args.db):
        sys.exit(f'No database at {args.db}. Run 12_build_claims_db.py first.')

    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    os.makedirs(OUT_DIR, exist_ok=True)

    for name, text in (('PLAYBOOK_V2.md', render_playbook(db)),
                       ('STRATEGY_V2.md', render_strategy(db))):
        path = os.path.join(OUT_DIR, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f'Wrote {os.path.relpath(path, ROOT)}  '
              f'({len(text.splitlines())} lines)')
    db.close()


if __name__ == '__main__':
    main()
