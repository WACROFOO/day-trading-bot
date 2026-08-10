#!/usr/bin/env python3
"""The pre-market gap scanner, run the way he runs it — on published metrics.

Two jobs, deliberately split by source:

  DISCOVERY   who is gapping right now, and by how much.  TradingView's
              screener endpoint is the only free source that publishes live
              `premarket_change` / `premarket_volume` / `premarket_high`.
              Finviz's free tier serves last session's numbers before the
              bell, so it cannot rank a pre-market list.

  DECISION    every number that decides whether to keep the name comes from
              FINVIZ's quote page: Shs Float, Shs Outstand, Short Float,
              Avg Volume, Market Cap, sector, and the dated `whyMoving`
              catalyst block.  Nothing here is derived from OHLCV bars.

Why that split matters: on 2026-08-05 a name was graded off a screener row
carrying stale volume.  Screener rows are point-in-time.  A published float
and a published average volume are not.

The order of operations copies his, which is a REJECT CASCADE, not a score:

    "I start at the top of the gap scanner.  This is the way I have it every
     morning.  And I have the gap scanner sorted by the percentage of the
     gap."                                        (ZfwTJAMLroA 12:15-12:35)

    "Before I even pulled up the chart, I saw that it was a 50 million share
     float.  50 million shares is a little on the higher side, especially for
     a stock priced at $1."                                (ZfwTJAMLroA 12:49)

So float and price kill a name before anything else is looked at.  A 0-100
score is deliberately NOT produced: `reports/2026-08-score-basket.md` measured
the pillar score against equal weight and found it carries NEGATIVE
information — it lost 16 of 16 matched pairs.  Gates, then eyes.

Usage:
    python3 scripts/premarket_stars.py
    python3 scripts/premarket_stars.py --all         # + rejects and their gate
    python3 scripts/premarket_stars.py --notify      # desktop alert on a STAR
    python3 scripts/premarket_stars.py --min-gap 20 --top 25
    python3 scripts/premarket_stars.py --json

Output is grouped STARS / WATCH / REJECTED with the decisive reason on the
same line, because the question a scanner answers at 06:30 is "what do I
look at", not "what are all the columns".
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import html
import json
import re
import subprocess
import sys
from zoneinfo import ZoneInfo

ET = ZoneInfo('America/New_York')
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

TV_SCAN = 'https://scanner.tradingview.com/america/scan'
FINVIZ = 'https://finviz.com/quote.ashx?t='

# --- his thresholds, with provenance -------------------------------------
PRICE_MIN, PRICE_MAX = 2.00, 20.00        # PARAMETERS.md §1
PREF_LO, PREF_HI = 2.50, 9.00             # "I prefer stocks generally between
                                          #  $2.50 and $8 or $9" ZfwTJAMLroA 13:13
FLOAT_MAX = 20_000_000                    # PARAMETERS.md §1
FLOAT_SOFT = 10_000_000                   # under this is the sweet spot
VOL_MIN = 250_000                         # "the volume threshold is um 250,000
                                          #  shares minimum" 1zBC9RKwfeU 1:06:48
                                          #  A SCANNER DIAL, not a gate - he
                                          #  traded NCTY on 8,000 shares of
                                          #  pre-market volume.  PARAMETERS.md 15
PM_VOL_CROWDED = 1_000_000                # "volume not more than a million
                                          #  pre-market. You don't want it super
                                          #  crowded" keeping-my-head-above-water-142
GAP_MIN = 10.0                            # pillar 5
FADE_MAX = 25.0                           # % off the pre-market high before
                                          # "still rising" is no longer true


def sh(cmd, stdin=None):
    r = subprocess.run(cmd, input=stdin, capture_output=True, text=True,
                       timeout=60)
    return r.stdout


# --------------------------------------------------------------- discovery
def discover(min_gap, limit):
    """Live pre-market gappers, sorted by gap % descending — his sort order.

    The 250k volume floor is applied HERE rather than in grade(), because on
    his setup it is a property of the scanner itself: a name below it never
    appears at all ("I'm not sure why WHLM didn't hit the scanner... I think
    the volume threshold is um 250,000 shares minimum", 1zBC9RKwfeU 1:06:48).
    grade() keeps the same check as a safety net for late-arriving data.
    """
    body = json.dumps({
        'filter': [
            {'left': 'premarket_change', 'operation': 'greater', 'right': min_gap},
            {'left': 'premarket_volume', 'operation': 'greater', 'right': VOL_MIN},
            {'left': 'close', 'operation': 'in_range', 'right': [0.5, 60]},
        ],
        'columns': ['name', 'close', 'premarket_close', 'premarket_open',
                    'premarket_high', 'premarket_low', 'premarket_change',
                    'premarket_volume', 'exchange', 'type'],
        'sort': {'sortBy': 'premarket_change', 'sortOrder': 'desc'},
        'range': [0, limit],
        'markets': ['america'],
    })
    out = sh(['curl', '-s', '-X', 'POST', TV_SCAN, '--max-time', '30',
              '-H', 'Content-Type: application/json', '-H', f'User-Agent: {UA}',
              '-d', '@-'], stdin=body)
    try:
        rows = json.loads(out)['data']
    except Exception:
        print('discovery failed — TradingView scanner unreachable', file=sys.stderr)
        return []
    keys = ['sym', 'prev_close', 'pm_close', 'pm_open', 'pm_high', 'pm_low',
            'gap', 'pm_vol', 'exchange', 'type']
    return [dict(zip(keys, r['d'])) for r in rows]


# ------------------------------------------------------------ finviz metrics
LABEL_VALUE = re.compile(
    r'snapshot-td-label"[^>]*>(.*?)</div>.*?snapshot-td-content[^>]*>(.*?)</div>',
    re.S)
WHY_MOVING = re.compile(r'"whyMoving":(\{.*?\}),"whyMovingRatings"', re.S)
NEWS_ROW = re.compile(
    r'<td width="130" align="right">\s*([^<]+?)\s*</td>.*?'
    r'class="tab-link-news"[^>]*>\s*(.*?)\s*</a>', re.S)


def strip(s):
    return html.unescape(re.sub('<[^>]+>', '', s)).strip()


def to_num(v):
    """'0.74M' -> 740000, '19.26%' -> 19.26, '3,653,003' -> 3653003."""
    if not v or v in ('-', 'n/a'):
        return None
    v = v.replace(',', '').replace('%', '').strip()
    mult = {'K': 1e3, 'M': 1e6, 'B': 1e9, 'T': 1e12}.get(v[-1:].upper())
    if mult:
        v = v[:-1]
    try:
        return float(v) * (mult or 1)
    except ValueError:
        return None


def finviz(sym):
    raw = sh(['curl', '-sL', '--compressed', '--max-time', '25',
              '-H', f'User-Agent: {UA}',
              '-H', 'Accept: text/html,application/xhtml+xml',
              FINVIZ + sym])
    if len(raw) < 5000:
        return {'sym': sym, 'fv_ok': False}
    d = {strip(L): strip(V) for L, V in LABEL_VALUE.findall(raw)}
    out = {
        'sym': sym,
        'fv_ok': bool(d),
        'float': to_num(d.get('Shs Float')),
        'shares_out': to_num(d.get('Shs Outstand')),
        'short_float': to_num(d.get('Short Float')),
        'avg_vol': to_num(d.get('Avg Volume')),
        'mkt_cap': to_num(d.get('Market Cap')),
        'insider_own': to_num(d.get('Insider Own')),
        'inst_own': to_num(d.get('Inst Own')),
        'atr': to_num(d.get('ATR (14)')),
        'sma200': to_num(d.get('SMA200')),
        'perf_week': to_num(d.get('Perf Week')),
        'cash_sh': to_num(d.get('Cash/sh')),
        'debt_eq': to_num(d.get('Debt/Eq')),
        'ipo': d.get('IPO'),
        'prev_close_fv': to_num(d.get('Prev Close')),
        # "52W High" comes as "316.00 -99.10%" - the level, then the distance
        'high_52w': to_num((d.get('52W High') or '').split()[0] or None),
        'perf_year': to_num(d.get('Perf Year')),
    }
    # sector / industry / country live in the header filter links
    links = re.findall(r'screener\?v=1[^"]*f=(?:sec|ind|geo)[^"]*"[^>]*>([^<]+)', raw)
    out['sector'] = links[0] if links else ''

    # finviz's own same-day "why is this moving" block: dated, with a
    # catalyst boolean.  This is the cheapest honest read on pillar 3.
    m = WHY_MOVING.search(raw)
    if m:
        try:
            w = json.loads(m.group(1))
            out['why'] = w.get('headline', '')
            out['why_time'] = w.get('dateTime', '')
            out['why_catalyst'] = bool(w.get('catalyst'))
            out['why_sentiment'] = w.get('sentiment', '')
            out['why_summary'] = w.get('summary', '')
        except Exception:
            pass
    out['news'] = [(strip(t), strip(h)) for t, h in NEWS_ROW.findall(raw)[:5]]
    return out


# ------------------------------------------------------- reverse-split check
YF_DAILY = ('https://query1.finance.yahoo.com/v8/finance/chart/'
            '{}?interval=1d&range=1mo')


def split_check(sym, prev_close_fv):
    """Did a reverse split just happen, and does the history smell of one?

    Written after BYAH on 2026-08-06 looked like it had gone from $0.33 to
    $2.84 overnight.  It had not: the board consolidated 8 shares into 1 that
    morning, so the price was the same pizza in fewer slices.  Two tests:

      TODAY   Yahoo's last daily close has not yet been back-adjusted while
              finviz already reports the post-split Prev Close.  Their ratio
              is then the split factor, and a split factor is a CLEAN number.
              BYAH read 2.64 / 0.33 = 8.000.  A genuine overnight move gives
              a ragged ratio like 1.37, never 8.000.

      HISTORY 52-week high divided by price.  Real companies do not fall 50x
              in a year; adjusted history does.  BYAH: 316.00 / 2.84 = 111x.
              AZI: 125.70 / 2.30 = 55x.  Both had consolidated.

    Yahoo is used only as a SECOND OPINION on one number.  Nothing here is a
    metric in its own right - the whole test is that two sources disagree.
    """
    out = {}
    try:
        j = json.loads(sh(['curl', '-s', '--compressed', '--max-time', '20',
                           '-H', f'User-Agent: {UA}', YF_DAILY.format(sym)]))
        q = j['chart']['result'][0]['indicators']['quote'][0]['close']
        closes = [c for c in q if c]
        yf_prev = closes[-2] if len(closes) >= 2 else None
    except Exception:
        return out
    if yf_prev and prev_close_fv and yf_prev > 0:
        ratio = prev_close_fv / yf_prev
        near = round(ratio)
        if near >= 2 and abs(ratio - near) < 0.02:
            out['split_today'] = near
        elif ratio and abs(ratio - 1) > 0.15:
            # sources disagree but not by a clean factor - still worth saying
            out['prev_close_mismatch'] = ratio
    return out


# ------------------------------------------------------------- the cascade
def grade(r):
    """Reject cascade in his order: price and float before anything else.

    Returns (verdict, [reasons]).  Verdicts: STAR, WATCH, REJECT.
    """
    kill, warn, plus = [], [], []
    px = r.get('pm_close') or r.get('prev_close')
    fl = r.get('float')
    pmv = r.get('pm_vol') or 0

    # --- gate 1: price band -------------------------------------------
    if px is None:
        kill.append('no price')
    elif px < PRICE_MIN:
        kill.append(f'${px:.2f} under ${PRICE_MIN:.2f}')
    elif px > PRICE_MAX:
        kill.append(f'${px:.2f} over ${PRICE_MAX:.0f}')
    elif not (PREF_LO <= px <= PREF_HI):
        warn.append(f'${px:.2f} outside his preferred ${PREF_LO:.2f}-${PREF_HI:.0f}')

    # --- gate 2: float, checked before the chart ----------------------
    if fl is None:
        warn.append('float not published by finviz — verify before sizing')
    elif fl > FLOAT_MAX:
        kill.append(f'float {fl/1e6:.1f}M over {FLOAT_MAX/1e6:.0f}M')
    elif fl <= FLOAT_SOFT:
        plus.append(f'float {fl/1e6:.2f}M')

    # --- gate 3: is it actually trading -------------------------------
    if pmv < VOL_MIN:
        kill.append(f'pre-market volume {pmv:,.0f} under {VOL_MIN:,}')

    # --- gate 4: catalyst ---------------------------------------------
    if r.get('why_catalyst'):
        plus.append('finviz flags a dated catalyst')
    elif r.get('why'):
        warn.append('move explained but not flagged a catalyst')
    else:
        warn.append('no same-day catalyst on finviz — find one or pass')

    # --- gate 5: rate of change AND still rising ----------------------
    # "if a stock is stair stepping down that's not bullish"  xgnqOu_fchA 08:57
    hi, px_now = r.get('pm_high'), r.get('pm_close')
    if hi and px_now:
        off = (hi - px_now) / hi * 100
        r['off_high'] = off
        if off > FADE_MAX:
            kill.append(f'{off:.0f}% off the pre-market high — already faded')
        elif off > 10:
            warn.append(f'{off:.0f}% off the pre-market high')

    # --- context, not gates -------------------------------------------
    # Rotation is NOT a plus.  This tool awarded CLRO for 27x its float trading
    # pre-market; the corpus says that is the most damning fact about a
    # gap-and-go, not its best feature - the imbalance the trade bets on has
    # already resolved.  "It already has 2 million shares of premarket volume,
    # so I already have a little bit of a negative bias on it before I even
    # pull up the chart" (ZfwTJAMLroA 13:21); "stocks that have millions of
    # shares of pre-market volume don't really work for the gap and go as much,
    # because I'm not the first one to see it" (blog, day-2-of-our-nyc-seminar).
    # Soft, not a veto: 1.5M was accepted once (11th-green-day-in-a-row-3k).
    # Full evidence: reports/2026-08-parameter-audit.md section 3.
    if fl and pmv:
        r['rotation'] = pmv / fl
    if pmv > PM_VOL_CROWDED:
        warn.append(f'{pmv/1e6:.1f}M shares already traded pre-market — '
                    f'crowded, the move may be over before the bell')
    # finviz publishes a 3-month average of FULL-DAY volume, so this ratio is
    # "how much of a normal entire session has already traded before the bell",
    # not a like-for-like RVOL.  0.6 is already extraordinary.  Note the
    # denominator self-contaminates: a name that ran yesterday drags its own
    # average up, which is why CLRO reads low here and 771x against a
    # pre-market-only baseline.  Rotation vs float is the cleaner read.
    if r.get('avg_vol') and pmv:
        r['pct_avg_day'] = pmv / r['avg_vol']
    sf = r.get('short_float')
    if sf and sf >= 15:
        plus.append(f'short float {sf:.1f}% — squeeze fuel')

    # capital-structure smell tests that decided 2026-08-05.  finviz cannot
    # see a shelf, so these are pointers to the filing, not verdicts.
    # A reverse split makes the price look like it moved when it did not, so
    # this is a KILL, not a warning: the gap % that put the name on the list
    # is an accounting artefact.  BYAH, 2026-08-06.
    if r.get('split_today'):
        kill.append(f'{r["split_today"]}-for-1 reverse split effective today — '
                    f'the "gap" is the split, not a move')
    elif r.get('prev_close_mismatch'):
        warn.append(f'finviz and Yahoo disagree on prior close by '
                    f'{r["prev_close_mismatch"]:.2f}x — verify before trusting gap%')
    hi52, px_ = r.get('high_52w'), r.get('pm_close') or r.get('prev_close')
    if hi52 and px_ and hi52 / px_ > 20:
        warn.append(f'52w high {hi52/px_:.0f}x the price — history has been '
                    f'split-adjusted, this has consolidated before')

    so, mc = r.get('shares_out'), r.get('mkt_cap')
    if so and so < 5e6:
        warn.append(f'only {so/1e6:.2f}M shares out — check for a reverse split')
    if mc and mc < 50e6:
        warn.append(f'${mc/1e6:.0f}M cap — check the shelf/ATM in EDGAR')
    # 'dr' is a depositary receipt — he trades those (the Chinese small caps).
    # A fund or ETF is not a momentum name and has no float to squeeze.
    typ = r.get('type')
    if typ in ('fund', 'etf', 'etn', 'structured'):
        kill.append(f'instrument type "{typ}" — not common stock')
    elif typ and typ != 'stock':
        warn.append(f'instrument type "{typ}"')

    if kill:
        return 'REJECT', kill
    return ('STAR' if len(plus) >= 2 and not any('no same-day' in w for w in warn)
            else 'WATCH'), plus + warn


def pillars(r):
    """The five pillars as booleans, in his order: price, float, news,
    volume, rate-of-change. Returned separately from grade() because a
    verdict answers "do I look at this" and the scorecard answers "why".

    None means unknowable from the data, which is NOT the same as a fail —
    a float finviz does not publish is a reason to check, not to reject.
    """
    px = r.get('pm_close') or r.get('prev_close')
    fl, pmv = r.get('float'), r.get('pm_vol') or 0
    off = r.get('off_high')
    return [
        None if px is None else (PRICE_MIN <= px <= PRICE_MAX),
        None if fl is None else (fl <= FLOAT_MAX),
        bool(r.get('why_catalyst')),
        None if not pmv else (VOL_MIN <= pmv <= PM_VOL_CROWDED),
        None if off is None else (r.get('gap', 0) >= GAP_MIN and off <= FADE_MAX),
    ]


DOT = {True: '+', False: '-', None: '?'}


# ------------------------------------------------------------------ alerts
def notify(title, message):
    """Desktop notification. macOS osascript, Linux notify-send, else silent.

    Deliberately fire-and-forget: a scanner that crashes because a
    notification daemon is missing is worse than one that stays quiet.
    """
    for cmd in (['osascript', '-e',
                 f'display notification "{message}" with title "{title}"'],
                ['notify-send', title, message]):
        try:
            if subprocess.run(cmd, capture_output=True,
                              timeout=5).returncode == 0:
                return True
        except Exception:
            continue
    return False


# ------------------------------------------------------------------ output
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--min-gap', type=float, default=GAP_MIN)
    ap.add_argument('--top', type=int, default=20, help='candidates to enrich')
    ap.add_argument('--all', action='store_true', help='print rejects too')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--notify', action='store_true',
                    help='desktop notification when a STAR appears (macOS/Linux)')
    a = ap.parse_args()

    now = dt.datetime.now(ET)
    cands = discover(a.min_gap, a.top)
    if not cands:
        print(f'{now:%Y-%m-%d %H:%M ET} — nothing gapping over '
              f'{a.min_gap:.0f}% with {VOL_MIN:,}+ shares.')
        print('That is a legitimate answer.  "Sitting down to a fairly sparse '
              'gap scanner" (fy1NpvXJq0U 01:49).')
        return 0

    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        metrics = list(ex.map(finviz, [c['sym'] for c in cands]))
        splits = list(ex.map(lambda m: split_check(m['sym'],
                                                   m.get('prev_close_fv')),
                             metrics))
    rows = [{**c, **m, **s} for c, m, s in zip(cands, metrics, splits)]
    for r in rows:
        r['verdict'], r['reasons'] = grade(r)
        # must precede the --json return: grade() fills off_high, which
        # pillars() needs, and --json was emitting nulls for the scorecard
        r['pillars'] = pillars(r)

    if a.json:
        print(json.dumps(rows, indent=2, default=str))
        return 0

    stars = [r for r in rows if r['verdict'] == 'STAR']
    watch = [r for r in rows if r['verdict'] == 'WATCH']
    rej = [r for r in rows if r['verdict'] == 'REJECT']

    # --- header: where we are in the morning -------------------------
    bell = now.replace(hour=9, minute=30, second=0, microsecond=0)
    delta = (bell - now).total_seconds()
    if delta > 0:
        h, m = int(delta // 3600), int(delta % 3600 // 60)
        when = f'bell in {h}h{m:02d}' if h else f'bell in {m} min'
    else:
        when = 'OPEN — pre-market figures frozen at 09:30'

    # --- the session verdict: one answer, before any ticker ----------
    # A per-name verdict never answers "should I trade at all today", and
    # that is the question a 06:30 scan is actually for.
    withcat = [r for r in stars + watch if r.get('why_catalyst')]
    if stars:
        call, why = 'GO', f'{len(stars)} name(s) clear every gate'
    elif withcat:
        call, why = 'SELECTIVE', f'no star, but {len(withcat)} carry a real catalyst'
    elif watch:
        call, why = 'STAND DOWN', 'names qualify on price and float, none has a catalyst'
    else:
        call, why = 'STAND DOWN', 'nothing survives the cascade'

    bar = '─' * 68
    print(f'\n  ┌{bar}┐')
    print(f'  │ {call:<12}{why:<40}{when:>14} │')
    counts = (f'{len(rows)} gapped · {len(stars)} star · {len(watch)} watch · '
              f'{len(rej)} rejected')
    print('  │ ' + counts.ljust(66) + ' │')
    print(f'  └{bar}┘\n')

    def line(r):
        fl = f'{r["float"]/1e6:.1f}M' if r.get('float') else '  ?  '
        pil = ' '.join(DOT[p] for p in r['pillars'])
        # the single most decisive thing about this name, on the same line
        kills = [x for x in r['reasons'] if 'faded' in x or 'over' in x
                 or 'under' in x or 'split' in x or 'not common stock' in x]
        soft = [x for x in r['reasons'] if 'no same-day catalyst' in x
                or 'not flagged a catalyst' in x or 'crowded' in x]
        why = (kills or soft or r['reasons'] or [''])[0]
        why = re.sub(r' — .*', '', why)[:40]
        return (f'  {r["sym"]:<6}{r["gap"]:>5.0f}%'
                f'{(r.get("pm_close") or 0):>8.2f}{fl:>7}   {pil}   {why}')

    COLS = ('  sym      gap%   price  float   P F N V R   the one thing '
            'that decides it')

    if stars:
        print('  ▸ STARS'); print(COLS)
        for r in stars:
            print(line(r))
        print()
    if watch:
        print('  ▸ WATCH'); print(COLS)
        for r in watch:
            print(line(r))
        print()
    if rej and a.all:
        print('  ▸ REJECTED — and why'); print(COLS)
        for r in rej:
            print(line(r))
        print()

    # --- detail only for what survived --------------------------------
    for r in stars + watch:
        print(f'  {r["sym"]}  ·  {r.get("sector", "")}  ·  '
              f'{r.get("pm_vol", 0):,.0f} shares pre-market')
        if r.get('why'):
            print(f'      catalyst  {r["why"][:88]}')
        for x in r['reasons']:
            print(f'      · {x}')
        print()

    if not stars and not watch:
        print('  A sparse scanner is a normal morning. No trade is a position.\n')
    print('  P price · F float · N news · V volume · R rate-of-change      '
          '+ pass   - fail   ? unknown')
    print('  Gates, not a score.  --all shows rejects  ·  --json for data\n')

    if a.notify and stars:
        names = ', '.join(f'{r["sym"]} +{r["gap"]:.0f}%' for r in stars)
        notify(f'{len(stars)} star', names)
    return 0


if __name__ == '__main__':
    sys.exit(main())
