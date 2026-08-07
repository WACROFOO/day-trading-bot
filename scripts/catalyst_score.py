#!/usr/bin/env python3
"""Score a catalyst on evidence, across three independent channels.

WHAT THIS SCORES, AND WHAT IT DOES NOT

It scores how well-evidenced the reason for a move is: who published it, how
long ago, how material the form type is, how specific the wording, and whether
more than one channel carries it.  It does NOT predict the return.  That
distinction is not pedantry - `reports/2026-08-score-basket.md` measured a
0-100 pillar score against equal weight and it lost 16 of 16 matched pairs, so
a score in this repo has to be honest about what it is measuring.  A 90 here
means "this catalyst is real and documented", never "this will go up".

THE THREE CHANNELS, deliberately independent

  1. SEC EDGAR   data.sec.gov submissions.  The only authoritative channel: a
                 filing is dated, typed, and legally binding.  8-K item codes
                 are the materiality signal - 1.01 is a definitive agreement,
                 2.02 earnings, 5.07 a shareholder vote - so the form itself
                 says how material it is, without parsing prose.

  2. finviz whyMoving   a dated, same-day narrative with a catalyst boolean.
                 Faster than any news search, and it says "No clear catalyst
                 identified" when there is none, which is an answer.

  3. finviz news table   wire headlines with timestamps.  Distinguishes a
                 company press release from third-party commentary.

Corroboration across channels is scored, because a move carried only by
third-party commentary is a different animal from one filed with the SEC.

THE DILUTION PENALTY

Subtracted, not warned about.  On 2026-08-05 ASTC had a real, dated catalyst
and a $24.5M ATM plus a $200M shelf against a $21M market cap.  The catalyst
was true; the trade was still wrong.  A shelf (S-3), a resale registration
(S-1), a takedown (424B5) or an employee plan (S-8) in the recent window means
someone is registered to sell into whatever the news creates.

Usage:
    python scripts/catalyst_score.py NAMI CLRO MB DSY
    python scripts/catalyst_score.py --json NAMI
    python scripts/catalyst_score.py --days 5 CLRO
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
from zoneinfo import ZoneInfo

ET = ZoneInfo('America/New_York')
SEC_UA = 'day-trading-research anassensamien@gmail.com'
BROWSER_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     'results', '.sec_tickers.json')

# --- criterion C: materiality, read off the form type, not the prose --------
# 8-K item codes are defined by the SEC, so this is a lookup, not a judgement.
ITEM_WEIGHT = {
    '1.01': 25,   # entry into a material definitive agreement (merger, contract)
    '2.01': 25,   # completion of acquisition or disposition
    '1.02': 18,   # termination of a material agreement
    '2.02': 15,   # results of operations - earnings
    '8.01': 10,   # other events - the catch-all companies use for PR
    '5.02': 8,    # departure/appointment of officers
    '5.07': 8,    # submission of matters to a vote
    '3.01': 4,    # listing-rule non-compliance - a bad "catalyst"
    '2.03': 4,    # creation of a direct financial obligation - debt
}
# EDGAR spells these "SCHEDULE 13G/A", not "SC 13G/A" - both appear in the
# wild depending on the endpoint, so normalise before looking up (see
# form_key).  Getting this wrong silently scored NAMI's 13G/A as "moderate
# wording, no matching filing" when the filing was right there.
FORM_WEIGHT = {
    'SC 13D': 20, 'SC 13D/A': 15,     # activist stake, intent to influence
    'SC 13G': 18, 'SC 13G/A': 14,     # passive stake over 5%; /A is an
                                      # amendment, so the stake may not be new
    '6-K': 10,                        # foreign issuer - no item codes exist
    '425': 20, 'DEFM14A': 20,         # merger communications
    '10-Q': 6, '10-K': 6, '20-F': 6,
    '4': 3,                           # insider transaction
}


def form_key(form):
    """'SCHEDULE 13G/A' -> 'SC 13G/A'. EDGAR uses both spellings."""
    return re.sub(r'^SCHEDULE ', 'SC ', (form or '').strip().upper())


DILUTION_FORMS = {'S-3': 25, 'S-1': 20, '424B5': 30, '424B4': 25,
                  'S-8': 10, 'S-3/A': 20, 'S-1/A': 15, 'F-1': 20, 'F-3': 25}

STRONG_WORDS = re.compile(
    r'(?i)\b(fda approval|fda clearance|breakthrough therapy|orphan drug|'
    r'phase (?:2|3|ii|iii)|primary endpoint|merger|acquisition|acquire|'
    r'buyout|tender offer|definitive agreement|awarded|contract win)\b')
MEDIUM_WORDS = re.compile(
    r'(?i)\b(beats|tops estimates|raises (?:guidance|outlook)|record revenue|'
    r'partnership|collaboration|letter of intent|stake|13[dg])\b')
WEAK_WORDS = re.compile(
    r'(?i)\b(no clear catalyst|momentum|retail|social media|chatter|'
    r'speculative|unusual (?:options|volume)|why is .{0,20} moving)\b')
# Things that are NOT catalysts, however well documented.  A reverse split is
# a change of units, not of the business; a lawyer's press release is an
# advert.  Both scored respectably before this veto existed - BYAH read 52/100
# on 2026-08-06 for "reverse stock split creates ultra-low float".
NOT_A_CATALYST = re.compile(
    r'(?i)(reverse (?:stock )?split|share consolidation|'
    r'lead plaintiff|class action|investors? who (?:lost|purchased)|'
    r'law (?:firm|offices)|securities fraud investigation|'
    r'reminds (?:shareholders|investors))')
DILUTION_WORDS = re.compile(
    r'(?i)\b(offering|registered direct|atm|at.the.market|shelf|'
    r'convertible note|warrant|private placement|reverse split|'
    r'share consolidation|dilution)\b')
MONEY = re.compile(r'\$[\d,.]+\s?(?:million|billion|m\b|bn\b|k\b)|\$[\d,]{4,}')
COUNTERPARTY = re.compile(r'\bwith ([A-Z][\w.&-]+(?: [A-Z][\w.&-]+){0,3})')


def sh(cmd, stdin=None, timeout=45):
    try:
        return subprocess.run(cmd, input=stdin, capture_output=True, text=True,
                              timeout=timeout).stdout
    except Exception:
        return ''


def strip(s):
    return html.unescape(re.sub('<[^>]+>', '', s)).strip()


# ------------------------------------------------------------ channel 1: SEC
def cik_map():
    if os.path.exists(CACHE) and os.path.getsize(CACHE) > 10000:
        age = dt.datetime.now().timestamp() - os.path.getmtime(CACHE)
        if age < 7 * 86400:
            return json.load(open(CACHE))
    raw = sh(['curl', '-s', '--compressed', '-H', f'User-Agent: {SEC_UA}',
              '--max-time', '40', 'https://www.sec.gov/files/company_tickers.json'])
    try:
        d = json.loads(raw)
    except Exception:
        return json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    m = {v['ticker']: v['cik_str'] for v in d.values()}
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(m, open(CACHE, 'w'))
    return m


def edgar(sym, cik, days):
    """Recent filings with form type, date and 8-K item codes."""
    if not cik:
        return {'filings': [], 'cik': None}
    raw = sh(['curl', '-s', '--compressed', '-H', f'User-Agent: {SEC_UA}',
              '--max-time', '30',
              f'https://data.sec.gov/submissions/CIK{int(cik):010d}.json'])
    try:
        r = json.loads(raw)['filings']['recent']
    except Exception:
        return {'filings': [], 'cik': cik}
    today = dt.datetime.now(ET).date()
    out = []
    for i in range(len(r['form'])):
        try:
            d = dt.date.fromisoformat(r['filingDate'][i])
        except Exception:
            continue
        age = (today - d).days
        if age > 120:
            break
        out.append({'form': r['form'][i], 'date': r['filingDate'][i],
                    'age': age, 'items': (r.get('items') or [''] * (i + 1))[i]})
    return {'filings': out, 'cik': cik, 'days': days}


# --------------------------------------------------------- channel 2 and 3
FV = 'https://finviz.com/quote.ashx?t='
NEWS_ROW = re.compile(
    r'<td width="130" align="right">\s*([^<]+?)\s*</td>.*?'
    r'class="tab-link-news"[^>]*>\s*(.*?)\s*</a>', re.S)
WHY = re.compile(r'"whyMoving":(\{.*?\}),"whyMovingRatings"', re.S)
DATE_RE = re.compile(r'([A-Z][a-z]{2}-\d{2}-\d{2}|Today)')


def finviz(sym):
    raw = sh(['curl', '-sL', '--compressed', '--max-time', '25',
              '-H', f'User-Agent: {BROWSER_UA}', FV + sym])
    out = {'why': None, 'news': []}
    if len(raw) < 5000:
        return out
    m = WHY.search(raw)
    if m:
        try:
            out['why'] = json.loads(m.group(1))
        except Exception:
            pass
    # finviz omits the date on continuation rows, so carry it forward
    cur = None
    for stamp, head in NEWS_ROW.findall(raw)[:25]:
        stamp = strip(stamp)
        d = DATE_RE.match(stamp)
        if d:
            cur = d.group(1)
        out['news'].append({'date': cur or '', 'time': stamp,
                            'headline': strip(head)})
    return out


def news_age_days(entry):
    """finviz dates are 'Aug-06-26' or 'Today'; missing means same day."""
    s = entry.get('date') or ''
    if s in ('', 'Today'):
        return 0
    try:
        return (dt.datetime.now(ET).date()
                - dt.datetime.strptime(s, '%b-%d-%y').date()).days
    except Exception:
        return 99


# ------------------------------------------------------------------ scoring
def score(sym, sec, fv, days):
    """Five positive criteria, one penalty. Every point traceable to a fact."""
    parts, notes = {}, []

    fresh = [f for f in sec['filings'] if f['age'] <= days]
    news = [n for n in fv['news'] if news_age_days(n) <= days]
    why = fv.get('why') or {}

    # --- A. source authority (0-30) -----------------------------------
    if fresh:
        parts['authority'] = 30
        # cite the MOST MATERIAL filing in the window, not the newest - a
        # form 4 filed this morning is not the reason a stock is up 140%
        top = max(fresh, key=lambda f: max(
            [FORM_WEIGHT.get(form_key(f['form']), 0)]
            + [ITEM_WEIGHT.get(i.strip(), 0) for i in (f['items'] or '').split(',')]))
        notes.append(f'SEC filing {top["form"]} on {top["date"]}')
    elif any(sym.lower() in n['headline'].lower()
             or re.match(r'^[A-Z][\w.,& ]+ (Announces|Reports|Enters)',
                         n['headline']) for n in news):
        parts['authority'] = 20
        notes.append('company press release, no filing')
    elif news:
        parts['authority'] = 10
        notes.append('third-party coverage only')
    else:
        parts['authority'] = 0
        notes.append('nothing published in the window')

    # --- B. recency (0-20) --------------------------------------------
    ages = [f['age'] for f in fresh] + [news_age_days(n) for n in news]
    if why.get('dateTime'):
        try:
            t = dt.datetime.fromisoformat(why['dateTime'][:19]).replace(tzinfo=ET)
            ages.append((dt.datetime.now(ET) - t).days)
        except Exception:
            pass
    a = min(ages) if ages else 99
    parts['recency'] = 20 if a == 0 else 14 if a == 1 else 7 if a <= 3 else 2 if a <= 7 else 0
    notes.append(f'newest evidence {a} day(s) old')

    # --- C. materiality, from the form type (0-25) --------------------
    best, why_best = 0, ''
    for f in fresh:
        for it in (f['items'] or '').split(','):
            w = ITEM_WEIGHT.get(it.strip(), 0)
            if w > best:
                best, why_best = w, f'8-K item {it.strip()}'
        w = FORM_WEIGHT.get(form_key(f['form']), 0)
        if w > best:
            best, why_best = w, f'form {f["form"]}'
    text = ' '.join([why.get('headline', '')] + [n['headline'] for n in news])
    if STRONG_WORDS.search(text) and best < 20:
        best, why_best = 20, 'strong wording, no matching filing'
    elif MEDIUM_WORDS.search(text) and best < 12:
        best, why_best = 12, 'moderate wording, no matching filing'
    parts['materiality'] = best
    if why_best:
        notes.append(f'materiality from {why_best}')

    # --- D. specificity (0-15) ----------------------------------------
    spec = 0
    blob = why.get('headline', '') + ' ' + why.get('summary', '') + ' ' + text
    if MONEY.search(blob):
        spec += 8
        notes.append(f'names a figure: {MONEY.search(blob).group(0)}')
    if COUNTERPARTY.search(blob):
        spec += 7
        notes.append(f'names a counterparty: {COUNTERPARTY.search(blob).group(1)}')
    parts['specificity'] = spec

    # --- E. corroboration (0-10) --------------------------------------
    ch = sum([bool(fresh), bool(news), bool(why.get('headline'))])
    parts['corroboration'] = 10 if ch >= 3 else 6 if ch == 2 else 3 if ch else 0
    notes.append(f'{ch} of 3 channels carry it')

    # --- the finviz catalyst boolean, as a veto not a bonus -----------
    if why.get('headline') and why.get('catalyst') is False:
        if WEAK_WORDS.search(why['headline']):
            parts['materiality'] = min(parts['materiality'], 6)
            notes.append('finviz: no clear catalyst — materiality capped')

    # --- hard veto: documented, but not a catalyst --------------------
    veto = NOT_A_CATALYST.search(why.get('headline') or '')
    if veto:
        parts['materiality'] = 0
        parts['specificity'] = 0
        parts['corroboration'] = min(parts['corroboration'], 3)
        notes.append(f'VETO: "{veto.group(0)}" is not a catalyst — '
                     f'the units changed, or a law firm is advertising')

    total = sum(parts.values())

    # --- penalty: who is registered to sell into this? ----------------
    pen, pnotes = 0, []
    for f in sec['filings']:
        w = DILUTION_FORMS.get(form_key(f['form']), 0)
        if w and f['age'] <= 120:
            decay = 1.0 if f['age'] <= 30 else 0.6 if f['age'] <= 60 else 0.35
            if w * decay > pen:
                pen = w * decay
                pnotes = [f'{f["form"]} filed {f["age"]}d ago']
    dil = [n for n in fv['news'] if DILUTION_WORDS.search(n['headline'])
           and news_age_days(n) <= 120]
    if dil:
        pen = max(pen, 15)
        pnotes.append(f'"{dil[0]["headline"][:60]}"')
    pen = round(pen)

    return {'sym': sym, 'parts': parts, 'gross': total,
            'penalty': pen, 'score': max(0, total - pen),
            'notes': notes, 'penalty_notes': pnotes,
            'why': why.get('headline'), 'why_time': why.get('dateTime'),
            'filings': fresh[:5]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('symbols', nargs='+')
    ap.add_argument('--days', type=int, default=3,
                    help='how far back evidence still counts')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()

    syms = [s.upper() for s in a.symbols]
    cm = cik_map()
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        secs = list(ex.map(lambda s: edgar(s, cm.get(s), a.days), syms))
        fvs = list(ex.map(finviz, syms))
    rows = [score(s, sc, f, a.days) for s, sc, f in zip(syms, secs, fvs)]
    rows.sort(key=lambda r: -r['score'])

    if a.json:
        print(json.dumps(rows, indent=2))
        return 0

    print(f'\nCatalyst evidence score — {dt.datetime.now(ET):%Y-%m-%d %H:%M ET}'
          f'  (window {a.days}d)')
    print('channels: SEC EDGAR · finviz whyMoving · finviz news wire\n')
    h = (f'{"sym":<6}{"auth":>6}{"recent":>7}{"material":>9}{"specific":>9}'
         f'{"corrob":>7}{"gross":>7}{"dilut":>7}{"SCORE":>7}')
    print(h); print('-' * len(h))
    for r in rows:
        p = r['parts']
        print(f'{r["sym"]:<6}{p["authority"]:>6}{p["recency"]:>7}'
              f'{p["materiality"]:>9}{p["specificity"]:>9}'
              f'{p["corroboration"]:>7}{r["gross"]:>7}{-r["penalty"]:>7}'
              f'{r["score"]:>7}')
    print()
    for r in rows:
        band = ('documented' if r['score'] >= 70 else
                'partial' if r['score'] >= 45 else 'thin')
        print(f'{r["sym"]}  {r["score"]}/100  [{band}]')
        if r['why']:
            print(f'    "{r["why"]}"  ({r["why_time"]})')
        for n in r['notes']:
            print(f'    {"!" if n.startswith("VETO") else "+"} {n}')
        for n in r['penalty_notes']:
            print(f'    - DILUTION {n}')
        if r['filings']:
            fl = ', '.join(f'{f["form"]}({f["date"]})' for f in r['filings'])
            print(f'    filings in window: {fl}')
        print()
    print('This scores EVIDENCE, not expected return. A high score means the '
          'reason is real and\ndocumented — it says nothing about direction. '
          'See reports/2026-08-score-basket.md.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
