#!/usr/bin/env python3
"""Calibration: does the engine see what he saw, on the days he saw it?

Every P&L number this project has produced measured the engine against itself.
The recaps supply the missing external reference: he names the tickers he
traded, and with real upload dates attached each recap becomes a labelled
session. The engine can then be scored at five increasingly demanding levels:

    1. in the candidate pool      did the universe contain the name at all?
    2. scanned that session       was there pre-market data to rank it on?
    3. passed the five pillars    did the scanner put it on the watchlist?
    4. detector found a setup     did the pullback logic see structure?
    5. the engine took the trade  gate, 2:1 target and spread all clear

Whichever level drops sharply is where the replication actually fails. Levels
4 and 5 are evaluated for EVERY named ticker with bar data, not only for the
ones that reached the watchlist - otherwise a scanner miss would hide a
detector miss behind it.

Dates
    upload_date now comes from a per-video metadata call, not the channel
    index (whose sub-year precision is synthetic). Mapping is by rule, never
    by best fit: a recap is published after the close, so a weekday upload is
    that session and a weekend upload is the Friday before. "Watch List for
    MONDAY" videos are previews and map FORWARD to the next session.

Tickers
    Auto-captions garble spelled-out symbols - one recap renders INLF as
    INFL, INLX and INFS in the same paragraph. Tokens matching a pool symbol
    exactly are taken as-is; the rest are repaired only when exactly one pool
    symbol sits at edit distance 1 AND that symbol was on the tape that day.
    Both counts are reported separately, and the headline uses exact only.

Usage:
    python diagnostics/calibrate.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402

import datetime as dt
import json
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

from engine20 import run_day
from run20 import fetch_symbol
from run20b import build

OUT = _DATA
ROOT = os.path.abspath(os.path.join(OUT, '..', '..', '..'))
RECAPS = os.path.join(ROOT, 'knowledge-base', 'recaps')

# Words the [A-Z]{3,5} pattern picks up that are never tickers here. Garbled
# near-misses of real symbols are NOT listed - they are handled by the edit
# distance repair, which leaves a record of what it changed.
NOISE = set("""
THE AND FOR THAT THIS WITH WAS ARE ALL YOU OUT NOT BUT GOT ONE TWO NOW HAD ITS
NEWS HIGH LOW BIG RED NEW VWAP MACD EMA ETF FOMO USA ATH LOL YES WHY HOW GET
SEE CAN WAY DAY ALSO JUST LIKE BEEN WERE THEY WHAT WHEN FROM HERE MORE SOME
VERY WELL GOOD MOST OVER BACK DOWN ONLY THAN THEN TIME WILL YOUR ABLE EACH ADD
BUY SELL LONG RISK STOP GAIN LOSS PLAN NICE OKAY REAL SURE TAKE WANT SPY QQQ
CPI FED IRA SIM LLC PDT USD CEO CFO IPO SEC FDA NYSE PR ATM SPAC HOD LOD RVOL
JAN FEB MAR APR JUN JUL AUG SEP OCT NOV DEC MON TUE WED THU FRI
DID DOES DONE GOES GONE COME CAME KEEP KNOW LOOK MADE MAKE MANY MUCH NEXT ONCE
OPEN PUSH SAID SAME SHOT SIDE SIZE SOLD STILL SUCH THINK THOSE THREE TOOK TRY
UNDER UNTIL UPON WENT WHERE WHICH WHILE WHOLE WORTH YEAR AGO OFF PUT SAY SET
TOO USE HALF HOLD HUGE IDEA INTO LAST LATE LESS LINE LIVE MEAN MOVE MUST NEAR
NEED NEVER NEXT OTHER OWN PART PAST PLAY POINT PRICE QUITE RIGHT ROOM RUN
SHARE SHORT SLOW SMALL SPOT START STAY STOCK TAPE TEXT THING TRADE TREND TURN
VOLUME WAIT WATCH WEEK WHOSE WORK
""".split())

LEVELS = (('named', 'named in a recap'),
          ('in_pool', 'in the candidate pool'),
          ('scanned', 'scanned that session'),
          ('watchlist', 'passed the five pillars'),
          ('setups', 'detector found a setup'),
          ('gate', 'the engine would have traded it'))


def named_tickers(path):
    """Tokens mentioned at least twice - once is usually market commentary."""
    txt = ' '.join(' '.join(l.split(']', 1)[1].split())
                   for l in open(path, encoding='utf-8') if l.startswith('['))
    c = Counter(t for t in re.findall(r'\b[A-Z]{3,5}\b', txt) if t not in NOISE)
    return {t: n for t, n in c.items() if n >= 2}


def edit1(a, b):
    """True when a and b differ by one substitution, insertion or deletion."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    s, L = (a, b) if len(a) < len(b) else (b, a)
    for i in range(len(L)):
        if L[:i] + L[i + 1:] == s:
            return True
    return False


def resolve(tokens, pool, on_tape):
    """token -> (symbol, how). how is 'exact', 'repaired' or None."""
    out = {}
    for t in tokens:
        if t in pool:
            out[t] = (t, 'exact')
            continue
        near = [s for s in on_tape if edit1(t, s)]
        out[t] = (near[0], 'repaired') if len(near) == 1 else (None, None)
    return out


def session_for(upload, title, sessions):
    """Deterministic - by publication convention, never by which fits better."""
    d = dt.date(int(upload[:4]), int(upload[4:6]), int(upload[6:]))
    preview = re.search(r'watch ?list for', title, re.I)
    if preview:                                   # published before the session
        later = [s for s in sessions if s > str(d)]
        return later[0] if later else None
    if str(d) in sessions:                        # recap, posted after the close
        return str(d)
    earlier = [s for s in sessions if s < str(d)]  # weekend upload -> the Friday
    return earlier[-1] if earlier else None


def detect(sym, session, day_bars):
    """(setups, setups the engine would have traded) for one symbol-session.

    This calls run_day rather than re-deriving the gate. An earlier version
    re-implemented it as "every GATE_CONDITION holds" and so silently omitted
    the 2:1 target filter and the stop-versus-spread test, which run_day
    applies on top - it reported 14 gate-passing pairs where the engine trades
    3. The engine is the definition; anything that restates it will drift.

    The symbol is run alone so the daily trade limit cannot bind: a pair that
    still does not trade was stopped by a rule, not by a queue.
    """
    if not day_bars or not day_bars.get('session'):
        return None
    res = run_day(dt.date(*map(int, session.split('-'))), [sym],
                  {sym: day_bars}, 5, [])
    return res['setups'], res['passes']


def main():
    meta_path = os.path.join(OUT, 'july_meta.json')
    if not os.path.exists(meta_path):
        sys.exit('data/july_meta.json missing - fetch real upload dates first')
    meta = json.load(open(meta_path))

    stats = json.load(open(os.path.join(OUT, 'scan20_stats.json')))
    daily = json.load(open(os.path.join(OUT, 'daily20.json')))
    pool = {c['sym']: c for c in json.load(open(os.path.join(OUT, 'pool20.json')))}
    shares_out = {s: c['mcap'] / c['price'] for s, c in pool.items() if c['price']}
    watch = build(stats, daily, shares_out)

    scanned = defaultdict(set)
    for r in stats:
        scanned[r['day']].add(r['sym'])
    sessions = sorted(scanned)

    # ---- label the sessions -------------------------------------------
    labelled, unmapped = [], []
    for vid, m in sorted(meta.items(), key=lambda kv: kv[1].get('upload_date') or ''):
        ud, title = m.get('upload_date'), m.get('title', '')
        path = os.path.join(RECAPS, f'{vid}.txt')
        if not ud or not os.path.exists(path):
            continue
        if ud[:6] != '202607':
            continue
        s = session_for(ud, title, sessions)
        if s is None or s < sessions[0] or (ud < sessions[0].replace('-', '')):
            unmapped.append((ud, title))
            continue
        labelled.append(dict(vid=vid, title=title, upload=ud, session=s,
                             tokens=named_tickers(path)))

    print('=== JULY CALIBRATION ===')
    print(f'bar data covers {sessions[0]} .. {sessions[-1]}  ({len(sessions)} sessions)')
    print(f'July videos with real upload dates and transcripts: '
          f'{len(labelled) + len(unmapped)}')
    print(f'  mapped onto a covered session : {len(labelled)}')
    print(f'  before the bar data starts    : {len(unmapped)}'
          + (f'  ({unmapped[0][0]} .. {unmapped[-1][0]})' if unmapped else ''))
    covered = sorted({L['session'] for L in labelled})
    print(f'sessions with at least one video: {len(covered)} of {len(sessions)}\n')

    # ---- resolve tickers ----------------------------------------------
    for L in labelled:
        on_tape = scanned.get(L['session'], set())
        L['res'] = resolve(L['tokens'], pool, on_tape)

    need = sorted({sym for L in labelled for sym, _ in L['res'].values() if sym})
    bars = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        for sym, d in ex.map(fetch_symbol, need):
            bars[sym] = d

    lvl, lvl_exact = Counter(), Counter()
    rows, unresolved = [], Counter()
    for L in labelled:
        wl = {r['sym'] for r in watch.get(L['session'], [])}
        for tok, (sym, how) in sorted(L['res'].items()):
            if not sym:
                unresolved[tok] += 1
                for c in (lvl,):
                    c['named'] += 1
                lvl_exact['named'] += 1
                rows.append((L['session'], tok, '?', 0, 0, 0, 0, 0))
                continue
            in_pool = sym in pool
            in_scan = sym in scanned.get(L['session'], set())
            on_wl = sym in wl
            d = detect(sym, L['session'], bars.get(sym, {}).get(L['session']))
            n_set, n_gate = d if d else (0, 0)
            for c in ((lvl, lvl_exact) if how == 'exact' else (lvl,)):
                c['named'] += 1
                c['in_pool'] += in_pool
                c['scanned'] += in_scan
                c['watchlist'] += on_wl
                c['setups'] += n_set > 0
                c['gate'] += n_gate > 0
            rows.append((L['session'], sym if how == 'exact' else f'{sym}*',
                         how, in_pool, in_scan, on_wl, n_set, n_gate))

    # ---- the table ----------------------------------------------------
    def table(c, title):
        n = c['named'] or 1
        print(title)
        print(f'  {"level":<32}{"count":>7}{"of named":>10}')
        for key, label in LEVELS:
            print(f'  {label:<32}{c[key]:>7}{100 * c[key] / n:>9.0f}%')
        print()

    table(lvl_exact, 'Tickers the captions spelled correctly (conservative):')
    table(lvl, 'Including edit-distance-1 caption repairs (marked * below):')

    print(f'{"session":<12}{"sym":<7}{"pool":>6}{"scan":>6}{"watch":>7}'
          f'{"setups":>8}{"passed":>8}')
    last = None
    for r in rows:
        if r[0] != last:
            print(f'{"-" * 54}')
            last = r[0]
        if r[2] == '?':
            print(f'{r[0]:<12}{r[1]:<7}{"unresolved caption token":>36}')
            continue
        y = lambda b: 'y' if b else '-'
        print(f'{r[0]:<12}{r[1]:<7}{y(r[3]):>6}{y(r[4]):>6}{y(r[5]):>7}'
              f'{r[6]:>8}{r[7]:>8}')

    if unresolved:
        print(f'\nunresolved caption tokens ({sum(unresolved.values())} mentions): '
              + ', '.join(f'{t}x{n}' for t, n in unresolved.most_common(20)))

    print('\n=== what he named, by session ===')
    for L in labelled:
        named = ', '.join(sorted({s for s, _ in L['res'].values() if s}))
        print(f'  {L["session"]}  {L["upload"]}  {L["title"][:44]:<46}{named}')

    json.dump(dict(levels=dict(lvl), levels_exact=dict(lvl_exact),
                   rows=rows, sessions=len(labelled),
                   unresolved=dict(unresolved)),
              open(os.path.join(OUT, 'calibration.json'), 'w'), indent=1)
    print('\nwrote data/calibration.json')


if __name__ == '__main__':
    main()
