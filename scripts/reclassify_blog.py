#!/usr/bin/env python3
"""Re-file the warrior-blog corpus by CONTENT instead of by URL slug.

The first pass classified on the slug alone, first-match-wins, and dropped 898
of 2,063 articles into `other/`. Reading the titles shows why: the slug rules
had no category at all for order types, options, crypto, market news, books, or
personal finance, and the recap rule only matched slugs containing the word
"recap" - so "Thumbs Up For +$2,400!" and "NOOO! The Winning Streak is Over
-$1,549" were not recognised as trade recaps.

Two changes fix it:

  * SCORE, don't first-match. Every rule that hits adds weight; the highest
    total wins. First-match meant "how to short a stock during earnings" landed
    wherever the rule list happened to reach first.
  * Read the TITLE AND BODY, not the URL. The body is already on disk, so this
    costs nothing and is far more informative than a slug.

Recaps are detected first and separately, because they are a register rather
than a topic and their giveaway is a P&L figure in the title, not a keyword.

Run with --dry-run first; it prints the proposed moves and leaves the tree
alone. Provenance is untouched - files keep their `<!-- source: -->` header,
only their directory changes.

Usage:
    python scripts/reclassify_blog.py --dry-run
    python scripts/reclassify_blog.py
"""
import argparse
import os
import re
import shutil
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'knowledge-base', 'warrior-blog')

# A P&L figure in the title is the reliable tell for a trade recap: "+$2,400",
# "-$1,549", "$1.3K A Day". Keyword rules alone miss most of them.
RECAP_TITLE = re.compile(
    # A P&L figure must be SIGNED. Allowing a bare "$12,345" swept in
    # "Elon Musk Offers To Buy Twitter For $54.20 A Share" and "7 Rules I
    # Learned from Making $12,374,892" - article figures, not session results.
    # signed AND either a dollar sign or a k-suffix - never a bare percent,
    # which matched "Elon Musk +9.2% Stake in Twitter".
    r'[-+]\s?\$[\d,]+(\.\d+)?\b|[-+]\s?[\d,]+(\.\d+)?\s?k\b|'
    r'\bgreen day\b|\bred day\b|\btrade recap\b|\bwinning streak\b|'
    r'\brecap\b|\bday \d+ (of|—|-)|\bchallenge\b|\bmidday\b', re.I)
RECAP_BODY = re.compile(
    # Body signals must be session-specific. "i made $" alone matched essays
    # about past trades, e.g. "Why We Hold Losing Trades Too Long".
    r'\bmidday market recap\b|\bmy p&l for (the day|today)\b|'
    r'\btoday.{0,12}(is|was) a (green|red) day\b|'
    r'\bwelcome to day \d+\b|\btime for our midday\b', re.I)
# A $TICKER in the title is a session write-up, not a guide: "Nice day for
# $HTZ and $CAR", "Scaling in and Out Case Study $OCEA".
RECAP_TICKER = re.compile(r'\$[A-Z]{2,5}\b')

# (category, weight, pattern). Weight 3 = decisive term, 1 = weak hint.
RULES = [
    ('order-types', 3, r'\b(limit|market|stop|stop-limit|trailing|iceberg|'
                       r'immediate-or-cancel|ioc|fill-or-kill|fok|all-or-none|'
                       r'market-on-open|market-on-close|iso|intermarket sweep|'
                       r'bracket|oco|good.til.cancel|gtc)\b.{0,20}order'),
    ('order-types', 3, r'order (type|explained|defined)'),
    ('options', 3, r'\b(call option|put option|covered call|strike price|'
                   r'option premium|expiration date|the greeks|delta|theta|'
                   r'implied volatility|leaps|straddle|strangle|iron condor)\b'),
    ('crypto', 3, r'\b(bitcoin|ethereum|crypto|blockchain|altcoin|satoshi|'
                  r'binance|coinbase|defi|nft|stablecoin)\b'),
    ('market-news', 3, r'\b(ipo|goes public|earnings report|acquisition|merger|'
                       r'takeover|stocks to watch|top \d+ .{0,20}stocks|'
                       r'best .{0,20}stocks|penny stocks to)\b'),
    ('books-education', 3, r'\b(books?|reading list|course|webinar|podcast)\b.{0,24}'
                           r'(trader|trading|beginner)|best .{0,15}books'),
    ('business-finance', 3, r'\b(401k|ira|roth|retirement|dividend|inflation|'
                            r'dodd-frank|federal reserve|interest rate|bond|etf|'
                            r'mutual fund|estate|insurance|credit)\b'),
    ('chart-patterns', 3, r'\b(wolfe wave|megaphone|pivot point|elliott wave|'
                          r'gartley|harmonic|fibonacci retracement|channel|'
                          r'double (top|bottom)|head and shoulders|cup and handle|'
                          r'pennant|wedge|triangle pattern|flag pattern)\b'),
    ('candlesticks', 3, r'\b(candlestick|doji|hammer|engulfing|harami|'
                        r'shooting star|marubozu|spinning top|morning star|'
                        r'evening star|hanging man|tweezer)\b'),
    ('indicators', 3, r'\b(vwap|macd|rsi|bollinger|stochastic|moving average|'
                      r'\bema\b|\bsma\b|\batr\b|\badx\b|ichimoku|oscillator|'
                      r'relative strength index)\b'),
    ('core-strategy', 3, r'\b(momentum|bull flag|gap and go|micro pullback|abcd|'
                         r'flat top|breakout|reversal|scalp|dip and rip|'
                         r'swing trad|opening range|red to green)\b'),
    ('short-selling', 3, r'\b(short sell|shorting|short squeeze|hard to borrow|'
                         r'short interest|locate|borrow fee|naked short)\b'),
    ('risk-psychology', 3, r'\b(risk management|position siz|stop loss|'
                           r'psycholog|discipline|fomo|revenge trad|emotion|'
                           r'mindset|journal|profit.loss ratio|win rate|'
                           r'drawdown|motivat|patience)\b'),
    ('rules-regulation', 3, r'\b(pdt|pattern day trader|\$25,?000|margin call|'
                            r'wash sale|finra|\bsec\b|regulation|circuit breaker|'
                            r'trading halt|settlement|t\+2|taxes?)\b'),
    ('tools-platforms', 3, r'\b(scanner|screener|thinkorswim|das trader|'
                           r'lightspeed|sterling|interactive brokers|webull|'
                           r'schwab|e-?trade|tradingview|hotkey|level 2|'
                           r'time and sales|broker|platform|charting software)\b'),
    ('getting-started', 3, r'\b(how much money|small account|get started|'
                           r'for beginners|make a living|full.time trad|'
                           r'quit your job|prop firm|funded account|'
                           r'trading business)\b'),
    # Deliberately narrow. The first version matched "explained" anywhere in a
    # 2,000-word body and turned terminology into the new dumping ground (187
    # files). It now needs the definitional phrasing, and TITLE_ONLY means it
    # is scored against the title alone.
    ('terminology', 3, r'^(what (is|are|does)|.{0,30}(defined|definition|'
                       r'explained|terminology|meaning of))'),
    # Market behaviour and plumbing, as opposed to a term needing a definition.
    ('market-concepts', 3, r'\b(sell in may|january effect|santa claus rally|'
                           r'seasonality|price discovery|meme stock|'
                           r'payment for order flow|pfof|market maker|'
                           r'dark pool|high.frequency|short squeeze mechanic|'
                           r'circuit break|market cycle|bear market|bull market|'
                           r'recession|volatility index|\bvix\b)\b'),
    # Site and community pages - not lessons, but not noise either.
    ('community-company', 4, r'\b(featured profile|our students|success stor|'
                             r'testimonial|contact|about us|meet the team|'
                             r'chat room member|warrior (pro|starter)|'
                             r'why i upload|our mission)\b'),
    # Lifestyle and general interest. Kept separate so a corpus search for a
    # trading term does not surface a car review.
    ('off-topic', 4, r'\b(mercedes|range rover|ferrari|lamborghini|porsche|'
                     r'win the lottery|real estate|vacation|watch collection|'
                     r'weaponized the dollar|geopolit|\bnba\b|\bnfl\b)\b'),
]
COMPILED = [(c, w, re.compile(p, re.I)) for c, w, p in RULES]
TITLE_ONLY = {'terminology'}
# Below this, the evidence is a couple of incidental word hits. Those stay in
# other/ rather than being force-fitted - which is what produced the 898 in the
# first place.
MIN_SCORE = 9
KEEP = {'reviews', 'market-notes', 'quotes-answers'}   # already precise


def read(path):
    t = open(path, encoding='utf-8', errors='replace').read()
    m = re.search(r'^# (.+)$', t, re.M)
    title = m.group(1) if m else ''
    body = t.split('\n\n', 2)[-1]
    return title, body


def classify(title, body):
    """Recap first (it is a register), then the highest-scoring topic."""
    if (RECAP_TITLE.search(title) or RECAP_TICKER.search(title)
            or RECAP_BODY.search(body[:1500])):
        return 'recaps', 99
    score = Counter()
    for cat, w, rx in COMPILED:
        hay = title if cat in TITLE_ONLY else title + '\n' + body[:4000]
        n = len(rx.findall(hay))
        if n:
            # title hits count double; body hits saturate so one long article
            # repeating "option" 40 times cannot outvote a decisive title
            score[cat] += w * (min(n, 4) + (2 if rx.search(title) else 0))
    if not score:
        return 'other', 0
    top, val = score.most_common(1)[0]
    return (top, val) if val >= MIN_SCORE else ('other', val)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--only-other', action='store_true',
                    help='only re-file what is currently in other/')
    a = ap.parse_args()

    cats = [d for d in sorted(os.listdir(OUT))
            if os.path.isdir(os.path.join(OUT, d)) and not d.startswith('.')]
    src = ['other'] if a.only_other else [c for c in cats if c not in KEEP]

    moves = defaultdict(list)
    stay = Counter()
    for cat in src:
        d = os.path.join(OUT, cat)
        for fn in sorted(os.listdir(d)):
            if not fn.endswith('.md') or fn == 'README.md':
                continue
            title, body = read(os.path.join(d, fn))
            new, sc = classify(title, body)
            if new != cat:
                moves[(cat, new)].append((fn, title, sc))
            else:
                stay[cat] += 1

    total = sum(len(v) for v in moves.values())
    print(f'{total} files would move\n')
    for (frm, to), items in sorted(moves.items(), key=lambda x: -len(x[1])):
        print(f'{frm:>16} -> {to:<18} {len(items)}')
    still = len(moves.get(('other', 'other'), [])) + stay.get('other', 0)
    print(f'\nstill in other/: {still}')
    if a.dry_run:
        print('\nsamples:')
        for (frm, to), items in sorted(moves.items(), key=lambda x: -len(x[1]))[:8]:
            print(f'\n  {frm} -> {to}')
            for fn, t, sc in items[:4]:
                print(f'    [{sc:>3}] {t[:72]}')
        return 0

    for (frm, to), items in moves.items():
        os.makedirs(os.path.join(OUT, to), exist_ok=True)
        for fn, _, _ in items:
            shutil.move(os.path.join(OUT, frm, fn), os.path.join(OUT, to, fn))
    print(f'\nmoved {total} files')
    return 0


if __name__ == '__main__':
    sys.exit(main())
