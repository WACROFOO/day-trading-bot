#!/usr/bin/env python3
"""The standard "where are we" command. One report shape, phase-aware.

    ./now                     phase header + board table + detail per ticker
    ./now MSGY WYHG           same, for these symbols (watchlist untouched)
    ./now --set MSGY WYHG     save the watchlist, then report
    ./now --scan              also run the gap scanner (pre-market phases)

Layer 1 is the board: one row per ticker - key values, the gate scorecard
(P F C R V E M), a verdict and the catalyst status. Layer 2 is the tape.py
workup per ticker. Both layers come from the same compute() call, so they
cannot disagree.

Gates (thresholds live in knowledge-base/strategies/FILTERS.md, which wins):
  P price $2-20 · F float <20M · C catalyst dated today · R still rising
  (≤25% off high) · V above VWAP · E above 9 EMA · M MACD positive AND
  above signal.  '+' pass · '-' fail · '?' unknown.

Verdict (non-actionable vocabulary, per the report-design pack):
any hard kill (P, F, R, split, buyout) -> REJECT. Chart or catalyst
incomplete -> WATCH. Everything green -> REVIEW inside the session
window (go read the chart yourself), LOG outside it.
"""
import argparse
import datetime as dt
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tape  # noqa: E402
import premarket_stars as ps  # noqa: E402
from tape import GOOD, BAD, WARN, DIM, c  # noqa: E402

ET = ZoneInfo('America/New_York')
FR = ZoneInfo('Europe/Paris')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST = os.path.join(ROOT, 'watchlist.txt')

# (minutes from ET midnight, label, repo action, Day Trade Dash action)
#
# The 4th field is the PLATFORM lane, kept visibly separate from the repo lane
# because they answer different questions: Dash says which name, our tools say
# whether it survives the reject cascade. Full block detail and every source:
# knowledge-base/daytrade-dash/PLAYBOOK.md
#
# Boundaries changed 2026-08-18 to match that playbook. Before this there was
# no 07:00 boundary at all - 04:00-09:30 was one undifferentiated PRE-MARKET
# block, which is why the 07:00 rule lived only in prose while the clock said
# nothing. 10:30 is new too: PARAMETERS.md §2 puts prime at 09:30-10:30 (n=44)
# and the typical close at "the 90-minute mark", so 09:35-11:00 as one flat
# block overstated the back half by 30 minutes.
PHASES = [
    (0,            'CLOSED',        'nothing to do', ''),
    (4 * 60,       'PRE-MARKET 04', 'too thin to act - platform is up, liquidity is not',
                                    'Top Gappers if awake. No decisions'),
    (7 * 60,       'PRE-MARKET 07', 'scan: ./now --scan   (the move can happen HERE - JWEL ran 07:00-07:45)',
                                    'Top Gappers + 5 Pillar List. Red/orange flame only. Running Up = news hour'),
    (8 * 60,       'NEWS WAVE',     'catalyst_score.py on the top 2, EDGAR by hand for 6-K filers',
                                    'Running Up + re-scan. Watch for flames TURNING red on your names'),
    (9 * 60,       'LIST LOCKS',    'final watchlist, 3 names max - stop adding',
                                    '5 Pillar List. Top Gappers FREEZES at 09:30'),
    (9 * 60 + 30,  'OPENING DRIVE', 'HANDS OFF - let the first candles print',
                                    'Small-Cap HOD Momo + Halt Scanner. Count which name alerts most'),
    (9 * 60 + 35,  'PRIME WINDOW',  'pullbacks 1-2 only, tape.py before every entry',
                                    'HOD Momo, audio on. REPEAT ALERTS on one symbol = the ranking'),
    (10 * 60 + 30, 'LATE WINDOW',   'reduce - past the 90-minute mark, new entries must be better',
                                    'HOD Momo thinning across lanes = the day is done'),
    (11 * 60,      'WIND-DOWN',     'new entries only on a perfect setup',
                                    'Halt Scanner only'),
    (11 * 60 + 30, 'OFF-BOOK',      'past the hard stop - review, do not trade',
                                    'dead zone to 15:00 - no trades (PARAMETERS.md §2)'),
    (15 * 60,      'POWER HOUR',    'watch only - nothing here has been measured',
                                    'Top of Trend (vendor built it for this hour). WATCH ONLY'),
    (16 * 60,      'AFTER HOURS',   'session over - run trade-review if trades were taken',
                                    'After Hours Top Gainers - tomorrow list, not today trades'),
    (20 * 60,      'CLOSED',        'nothing to do', ''),
]


def phase_at(now_et):
    m = now_et.hour * 60 + now_et.minute
    if now_et.weekday() >= 5:
        return 'CLOSED (weekend)', 'nothing to do', '', None
    cur, nxt = PHASES[0], None
    for i, p in enumerate(PHASES):
        if m >= p[0]:
            cur = p
            nxt = PHASES[i + 1] if i + 1 < len(PHASES) else None
    left = ''
    if nxt:
        d = nxt[0] - m
        left = f' -> {nxt[1]} in {d//60}h{d%60:02d}m' if d >= 60 else f' -> {nxt[1]} in {d}m'
    return cur[1], cur[2], cur[3], left


PHASE_COLOR = {'PRIME WINDOW': GOOD,
               'PRE-MARKET 07': WARN, 'NEWS WAVE': WARN, 'LIST LOCKS': WARN,
               'OPENING DRIVE': WARN, 'LATE WINDOW': WARN, 'WIND-DOWN': WARN,
               'PRE-MARKET 04': DIM, 'POWER HOUR': DIM,
               'OFF-BOOK': BAD, 'AFTER HOURS': BAD}


def header():
    now = dt.datetime.now(ET)
    name, advice, dash, left = phase_at(now)
    paint = PHASE_COLOR.get(name, DIM)
    print('=' * 78)
    print(f"{now:%a %d %b} · {now:%H:%M:%S} ET ({now.astimezone(FR):%H:%M} France)")
    print(f"phase: {paint(name)}{left or ''}")
    print(f"       {advice}")
    if dash:
        print(f"  DASH {dash}")
    print("prime 09:35-10:30 · typical close 11:00 · hard stop 11:30 ET · paper only")
    print(DIM("data: yahoo 1m bars (per-ticker time = last print) · finviz metrics"))
    print(DIM("      before the open finviz price/volume fields are LAST session's"))
    print('=' * 78)
    return name


def watchlist():
    if os.path.exists(WATCHLIST):
        with open(WATCHLIST) as f:
            return [s.strip().upper() for s in f.read().split() if s.strip()]
    return []


def gather(sym):
    """Everything both layers need, one fetch set per ticker."""
    out = {'sym': sym, 'tape': None, 'fv': {}, 'split': {}}
    try:
        out['tape'] = tape.compute(sym)
    except Exception:
        pass
    try:
        out['fv'] = ps.finviz(sym)
    except Exception:
        pass
    if out['fv'].get('prev_close_fv'):
        try:
            out['split'] = ps.split_check(sym, out['fv']['prev_close_fv'])
        except Exception:
            pass
    return out


import re as _re
# target-side only: a company DOING an acquisition is not pinned to a deal
# price - only the one BEING bought is. (MSGY "to acquire 20% stake" was
# wrongly killed by a looser 'acquir' match.)
BUYOUT_RE = _re.compile(r'to be acquired|acquired by|buyout|to be bought'
                        r'|merger agreement|going private|take.?private',
                        _re.I)


def catalyst_today(fv, now_et):
    """'+' dated today with catalyst flag, '-' none/old, with a label."""
    why, when = fv.get('why', ''), fv.get('why_time', '')
    if not fv.get('fv_ok'):
        return '?', 'finviz unreachable'
    if not why:
        return '?', 'no same-day read on finviz'
    if BUYOUT_RE.search(why):
        # book, guardrail #13: "When a stock is a buyout, the value becomes
        # fixed at the buyout price and volatility disappears."
        return 'X', f'BUYOUT — price pinned to deal: {why[:40]}'
    today = now_et.strftime('%Y-%m-%d') in when or now_et.strftime('%b-%d') in when
    if fv.get('why_catalyst') and today:
        return '+', why[:46]
    if today:
        return '-', f'explained, not a catalyst: {why[:32]}'
    return '-', f'stale: {why[:38]}'


def gates(g, now_et, phase_open=True):
    t, fv, sp = g['tape'], g['fv'], g['split']
    last = t['last'] if t else None
    fl = fv.get('float')
    gc = {}
    gc['P'] = '?' if last is None else ('+' if 2.0 <= last <= 20.0 else '-')
    gc['F'] = '?' if fl is None else ('+' if fl < 20e6 else '-')
    cflag, clabel = catalyst_today(fv, now_et)
    gc['C'] = cflag
    fade = t.get('fade') if t else None
    if fade is None and t and t.get('pm_hi'):
        fade = (t['last'] / t['pm_hi'] - 1) * 100
    gc['R'] = '?' if fade is None else ('+' if fade > -25 else '-')
    gc['V'] = ('?' if not t or t.get('vwap') is None
               else '+' if t['last'] > t['vwap'] else '-')
    gc['E'] = '?' if not t else ('+' if t['above_e9'] else '-')
    gc['M'] = '?' if not t else ('+' if t['macd_pass'] else '-')

    split_kill = bool(sp.get('split_today'))
    if split_kill:
        clabel = f"gap IS a {sp['split_today']}:1 reverse split"
        gc['C'] = '-'
    buyout_kill = gc['C'] == 'X'
    if buyout_kill:
        gc['C'] = '-'

    hard_fail = ('-' in (gc['P'], gc['F'], gc['R']) or split_kill
                 or buyout_kill)
    chart_ok = all(gc[k] == '+' for k in 'VEM')
    # non-actionable vocabulary: REVIEW = all gates green, go read the chart
    # yourself; LOG = would be REVIEW but the session window is shut
    if hard_fail:
        verdict = 'REJECT'
    elif chart_ok and gc['C'] == '+':
        verdict = 'REVIEW' if phase_open else 'LOG'
    else:
        verdict = 'WATCH'

    # the one-line reason: the first thing that decides the row (device 4:
    # the reason must match the logic that fired)
    if split_kill:
        reason = 'gap IS the split ✗'
    elif buyout_kill:
        reason = 'BUYOUT — pinned ✗'
    elif gc['P'] == '-':
        reason = f'price {last:.2f} ✗' if last else 'price ✗'
    elif gc['F'] == '-':
        reason = f'float {fl/1e6:.0f}M ✗'
    elif gc['R'] == '-':
        reason = f'{fade:.0f}% off high ✗'
    # a WATCH must carry its own revival level — a snapshot verdict decays
    # silently, and the reader needs the price that flips it (ONFO 08-14:
    # 'below EMA9' at 10:43, reclaimed 4.00 at 10:56, ran to 5.57 unseen)
    elif gc['V'] == '-':
        reason = f"below VWAP (flips >{t['vwap']:.2f})"
    elif gc['E'] == '-':
        reason = f"below EMA9 (flips >{t['e9'][-1]:.2f})"
    elif gc['M'] == '-':
        reason = 'MACD below signal (needs the cross — no single price)'
    elif gc['C'] != '+':
        reason = clabel
    else:
        reason = 'all gates green'
    return gc, verdict, clabel, fade, reason


# coloured lamps in a terminal; plain +/-/? when piped so nothing is lost
LAMP = ({'+': GOOD('●'), '-': BAD('●'), '?': DIM('○')} if tape._TTY
        else {'+': '+', '-': '-', '?': '?'})
VERDICT_PAINT = {'REVIEW': lambda t: c(t, '1;32'),
                 'LOG': lambda t: c(t, '36'),
                 'WATCH': lambda t: c(t, '1;33'),
                 'REJECT': lambda t: c(t, '1;31')}


VERDICT_RANK = {'REVIEW': 0, 'LOG': 1, 'WATCH': 2, 'REJECT': 3}


def dollar_vol(g):
    t = g['tape']
    if not t:
        return 0.0
    return ((t['rth_vol'] or t['pm_vol']) or 0) * (t['last'] or 0)


def board(rows, phase_open=True, now_et=None):
    """The verdict table, screenshot-style: box frame, verdict first column,
    session-position columns coloured by state, WHY block underneath."""
    rows.sort(key=lambda g: (VERDICT_RANK.get(g['verdict'], 4), -dollar_vol(g)))

    W = [7, 8, 8, 6, 9, 10, 10, 8, 7, 6, 8]   # column content widths
    HEAD = ['', 'TICKER', 'PRICE', 'CHG', 'vs OPEN', 'off HIGH', 'in RANGE',
            'VOLUME', 'FLOAT', 'RVOL', 'NEWS']

    def edge(l, m, r):
        return l + m.join('─' * w for w in W) + r

    def rowline(cells):
        out = '│'
        for w, (txt, paint) in zip(W, cells):
            pad = f'{txt:^{w}}' if paint is None else f'{txt:^{w}}'
            out += (pad if paint is None else paint(pad)) + '│'
        return out

    def col_off_high(v):
        if v is None:
            return '—', None
        t = f'{v:+.0f}%'
        return t, (GOOD if v > -7 else WARN if v > -15 else BAD)

    def col_range(v):
        if v is None:
            return '—', None
        t = f'{v:.0f}%'
        return t, (GOOD if v >= 60 else WARN if v >= 30 else BAD)

    now = now_et or dt.datetime.now(ET)
    state = 'regular session live' if phase_open else 'window shut — log only'
    print(f"VERDICT   {GOOD('OPEN') if phase_open else BAD('SHUT')}  "
          f"{now:%H:%M} ET · {state}")
    print(edge('┌', '┬', '┐'))
    print(rowline([(h, None) for h in HEAD]))
    print(edge('├', '┼', '┤'))
    for g in rows:
        t, fv, gc = g['tape'], g['fv'], g['gates']
        last = f"{t['last']:.2f}" if t else '—'
        chg = f"{t['gap']:+.0f}%" if t and t['gap'] is not None else '—'
        vso, vso_p = '—', None
        if t and t.get('day_open'):
            v = (t['last'] / t['day_open'] - 1) * 100
            vso, vso_p = f'{v:+.0f}%', (GOOD if v > 0 else BAD)
        offh, offh_p = col_off_high(g['fade'])
        rng, rng_p = col_range(t.get('in_range') if t else None)
        vol = ((t['rth_vol'] or t['pm_vol']) if t else 0) or 0
        vs = f'{vol/1e6:.1f}M' if vol >= 1e6 else (f'{vol/1e3:.0f}K' if vol else '—')
        fl = fv.get('float')
        fls = f'{fl/1e6:.1f}M' if fl else '—'
        av = fv.get('avg_vol')
        rv = f'{vol/av:.0f}x' if av and vol else '—'
        news = ('C', GOOD) if gc['C'] == '+' else (
            ('—', None) if 'no ' in g['clabel'][:14] else ('MANUAL', WARN))
        verdict = g['verdict'] if g['verdict'] != 'REJECT' else 'NO'
        vp = VERDICT_PAINT.get(g['verdict'], str)
        print(rowline([
            (verdict, lambda x, _vp=vp: _vp_pad(x, _vp)),
            (g['sym'], None), (last, None), (chg, None), (vso, vso_p),
            (offh, offh_p), (rng, rng_p), (vs, None), (fls, None),
            (rv, None), news]))
    print(edge('└', '┴', '┘'))
    print(DIM("in RANGE: 100% = at the day's high (front side) · 0% = at the "
              "low (back side, move is over)"))
    print()
    print('WHY')
    for g in rows:
        verdict = g['verdict'] if g['verdict'] != 'REJECT' else 'NO'
        vp = VERDICT_PAINT.get(g['verdict'], str)
        reason = g['reason']
        t = g['tape']
        if (t and g['fade'] is not None and t.get('in_range') is not None
                and g['fade'] <= -15):
            reason = (f"back side of the move — {abs(g['fade']):.0f}% off the "
                      f"high, sitting at {t['in_range']:.0f}% of the day's range")
        print(f"  {vp(f'{verdict:<6}')} {g['sym']:<6} {reason}")
    print()
    if not phase_open:
        print(BAD("Outside the 07:00-11:00 ET window (13:00-17:00 France) — "
                  "log these, don't trade them."))
        print()
    return rows


def _vp_pad(cell, paint):
    """Center-pad a verdict cell, then colour only the word."""
    word = cell.strip()
    total = len(cell)
    left = (total - len(word)) // 2
    right = total - len(word) - left
    return ' ' * left + paint(word) + ' ' * right


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('symbols', nargs='*')
    ap.add_argument('--set', nargs='+', metavar='SYM', dest='set_wl')
    ap.add_argument('--scan', action='store_true')
    ap.add_argument('--bars', type=int, default=5)
    args = ap.parse_args()

    if args.set_wl:
        with open(WATCHLIST, 'w') as f:
            f.write('\n'.join(s.upper() for s in args.set_wl) + '\n')
        print(f'watchlist -> {" ".join(s.upper() for s in args.set_wl)}')

    name = header()
    now_et = dt.datetime.now(ET)

    scan_rows, scan_rejects = [], []
    if args.scan:
        # after the bell TradingView freezes premarket_change; switch to the
        # live intraday discovery so the scan can still surface new names
        live = name in ('OPENING DRIVE', 'PRIME WINDOW', 'LATE WINDOW',
                        'WIND-DOWN', 'OFF-BOOK')
        scan_rows = ps.scan(live=live)

    survivors = [r['sym'] for r in scan_rows if r['verdict'] != 'REJECT']
    listed = ([s.upper() for s in args.symbols]
              or (args.set_wl and [s.upper() for s in args.set_wl])
              or watchlist())
    # unified universe: scan survivors first (they carry today's move),
    # then the watchlist — deduplicated, capped so the run stays <60s
    syms = list(dict.fromkeys(survivors + listed))[:12]
    # a name on the board never repeats in the reject list (and would
    # double-count in the funnel)
    scan_rejects = [r for r in scan_rows
                    if r['verdict'] == 'REJECT' and r['sym'] not in set(syms)]
    if not syms:
        if args.scan:
            print('scan: nothing gapping — a sparse scanner is a normal '
                  'morning. No trade is a position.')
        else:
            print('no watchlist - set one:  ./now --set SYM SYM')
            if name == 'PRE-MARKET':
                print('or scan the gappers:     ./now --scan')
        return

    phase_open = name in ('OPENING DRIVE', 'PRIME WINDOW', 'LATE WINDOW')
    with ThreadPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(gather, syms))
    for g in rows:
        (g['gates'], g['verdict'], g['clabel'],
         g['fade'], g['reason']) = gates(g, now_et, phase_open)

    if name.startswith('CLOSED') or name == 'AFTER HOURS':
        print(f'[last session data for: {" ".join(syms)}]\n')

    # document order per the design pack: funnel (universe before filter),
    # then what died and why, then the verdict board, then detail
    n_rev = sum(1 for g in rows if g['verdict'] in ('REVIEW', 'LOG'))
    n_watch = sum(1 for g in rows if g['verdict'] == 'WATCH')
    n_rej = sum(1 for g in rows if g['verdict'] == 'REJECT') + len(scan_rejects)
    universe = (len(scan_rows) if args.scan else 0) + len(rows) - len(
        [g for g in rows if any(r['sym'] == g['sym'] for r in scan_rows)])
    print(f"{universe} considered · {n_rev} review · {n_watch} watch · "
          f"{n_rej} rejected"
          + ('' if args.scan else '   (watchlist only — ./now --scan for the market)'))
    print()

    if scan_rejects:                                       # one line each
        print(DIM('  ✗ scan rejects — the killing gate:'))
        for r in scan_rejects:
            print(f"  {BAD('✗')} {r['sym']:<6}{r.get('gap') or 0:>5.0f}%   "
                  f"{ps.kill_reason(r)[:58]}")
        print()

    rows = board(rows, phase_open, now_et)                 # the verdict table

    detail = [g for g in rows if g['verdict'] != 'REJECT'][:3]
    rest = [g for g in rows if g not in detail]
    for g in detail:                                       # layer 2, top 3
        if not g['tape']:
            print(f"## {g['sym']} - tape fetch failed\n")
            continue
        tape.render(g['tape'], args.bars)
        fv = g['fv']
        bits = []
        if fv.get('shares_out'):
            bits.append(f"shs out {fv['shares_out']/1e6:.2g}M")
        if fv.get('cash_sh') is not None:
            bits.append(f"cash/sh {fv['cash_sh']:.2f}")
        if fv.get('high_52w') and g['tape']['last']:
            mult = fv['high_52w'] / g['tape']['last']
            bits.append(f"52W high {fv['high_52w']:.2f} ({mult:.0f}x)"
                        + (' ← split-adjusted history' if mult > 20 else ''))
        if fv.get('short_float') is not None:
            bits.append(f"short {fv['short_float']:.1f}%")
        if bits:
            print('   ' + ' · '.join(bits))
        if fv.get('why'):
            print(DIM(f"   catalyst: {fv['why'][:70]}"))
        if g['split'].get('split_today'):
            print(BAD(f"   REVERSE SPLIT {g['split']['split_today']}:1 took "
                      "effect today - the gap is the split"))
        print()
    if rest:
        print(DIM('  details on demand: '
                  + ' · '.join(f"./now {g['sym']}" for g in rest[:8])))
        print()

    print('-' * 78)
    print("NOT CHECKED here: spread, executable bid/ask, borrow, live halt state,")
    print("Level 2, filings (run catalyst_score.py). Selection only, no order.")


if __name__ == '__main__':
    main()
