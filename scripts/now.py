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

Verdict: any hard kill (P, F, R, or gap-is-the-split) -> REJECT.
Hard gates pass but chart (V/E/M) or catalyst missing -> WATCH.
Everything green -> SETUP (the chart says yes; size it and find the entry).
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

PHASES = [
    (0,        'CLOSED',        'nothing to do'),
    (4 * 60,   'PRE-MARKET',    'scan: ./now --scan   (the move can happen HERE - JWEL ran 07:00-07:45)'),
    (9 * 60 + 30, 'OPENING DRIVE', 'HANDS OFF - let the first candles print'),
    (9 * 60 + 35, 'MONEY WINDOW', 'pullbacks 1-2 only, tape.py before every entry'),
    (11 * 60,  'WIND-DOWN',     'new entries only on a perfect setup'),
    (11 * 60 + 30, 'OFF-BOOK',  'past the hard stop - review, do not trade'),
    (16 * 60,  'AFTER HOURS',   'session over - run trade-review if trades were taken'),
    (20 * 60,  'CLOSED',        'nothing to do'),
]


def phase_at(now_et):
    m = now_et.hour * 60 + now_et.minute
    if now_et.weekday() >= 5:
        return 'CLOSED (weekend)', 'nothing to do', None
    cur, nxt = PHASES[0], None
    for i, p in enumerate(PHASES):
        if m >= p[0]:
            cur = p
            nxt = PHASES[i + 1] if i + 1 < len(PHASES) else None
    left = ''
    if nxt:
        d = nxt[0] - m
        left = f' -> {nxt[1]} in {d//60}h{d%60:02d}m' if d >= 60 else f' -> {nxt[1]} in {d}m'
    return cur[1], cur[2], left


PHASE_COLOR = {'MONEY WINDOW': GOOD, 'PRE-MARKET': WARN, 'OPENING DRIVE': WARN,
               'WIND-DOWN': WARN, 'OFF-BOOK': BAD, 'AFTER HOURS': BAD}


def header():
    now = dt.datetime.now(ET)
    name, advice, left = phase_at(now)
    paint = PHASE_COLOR.get(name, DIM)
    print('=' * 78)
    print(f"{now:%a %d %b} · {now:%H:%M:%S} ET ({now.astimezone(FR):%H:%M} France)")
    print(f"phase: {paint(name)}{left or ''}")
    print(f"       {advice}")
    print("money window 09:35-11:00 ET · hard stop 11:30 · paper only")
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


def catalyst_today(fv, now_et):
    """'+' dated today with catalyst flag, '-' none/old, with a label."""
    why, when = fv.get('why', ''), fv.get('why_time', '')
    if not fv.get('fv_ok'):
        return '?', 'finviz unreachable'
    if not why:
        return '?', 'no same-day read on finviz'
    today = now_et.strftime('%Y-%m-%d') in when or now_et.strftime('%b-%d') in when
    if fv.get('why_catalyst') and today:
        return '+', why[:46]
    if today:
        return '-', f'explained, not a catalyst: {why[:32]}'
    return '-', f'stale: {why[:38]}'


def gates(g, now_et):
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

    hard_fail = '-' in (gc['P'], gc['F'], gc['R']) or split_kill
    chart_ok = all(gc[k] == '+' for k in 'VEM')
    if hard_fail:
        verdict = 'REJECT'
    elif chart_ok and gc['C'] == '+':
        verdict = 'SETUP'
    else:
        verdict = 'WATCH'
    return gc, verdict, clabel, fade


# coloured lamps in a terminal; plain +/-/? when piped so nothing is lost
LAMP = ({'+': GOOD('●'), '-': BAD('●'), '?': DIM('○')} if tape._TTY
        else {'+': '+', '-': '-', '?': '?'})
VERDICT_PAINT = {'SETUP': lambda t: c(f' {t} ', '1;7;32'),   # inverted green
                 'WATCH': lambda t: c(f' {t} ', '1;33'),
                 'REJECT': lambda t: c(f' {t} ', '1;31')}


def board(rows, now_et):
    print(f"{'sym':<5} {'last':>7} {'gap%':>7} {'fade%':>6} {'float':>6} "
          f"{'vol':>7}  {'P F C R V E M':^13}  {'verdict':<8} catalyst")
    print('-' * 78)
    for g in rows:
        t, fv = g['tape'], g['fv']
        gc, verdict, clabel, fade = g['gates'], g['verdict'], g['clabel'], g['fade']
        last = f"{t['last']:.2f}" if t else '?'
        gap = f"{t['gap']:+.1f}" if t and t['gap'] is not None else '?'
        fd = f"{fade:+.1f}" if fade is not None else '?'
        if fade is not None and fade <= -25:
            fd = BAD(fd)
        fl = fv.get('float')
        fls = f"{fl/1e6:.2g}M" if fl else '?'
        vol = t['rth_vol'] or t['pm_vol'] if t else 0
        vs = f"{vol/1e6:.1f}M" if vol >= 1e6 else (f"{vol/1e3:.0f}k" if vol else '?')
        score = ' '.join(LAMP[gc[k]] for k in 'PFCRVEM')
        vpaint = VERDICT_PAINT.get(verdict, str)
        print(f"{g['sym']:<5} {last:>7} {gap:>7} {fd:>6} {fls:>6} "
              f"{vs:>7}  {score}  {vpaint(verdict):<8} {DIM(clabel)}")
    print('-' * 78)
    print(DIM("P price 2-20 · F float<20M · C catalyst today · R ≤25% off high · "
              "V >VWAP · E >EMA9 · M MACD   ") +
          GOOD('●') + DIM(' pass  ') + BAD('●') + DIM(' fail  ') +
          DIM('○ unknown'))
    print()


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

    if args.scan:
        cmd = [sys.executable,
               os.path.join(ROOT, 'scripts', 'premarket_stars.py'), '--all']
        # after the bell TradingView freezes premarket_change; switch to the
        # live intraday discovery so the scan can still surface new names
        if name in ('OPENING DRIVE', 'MONEY WINDOW', 'WIND-DOWN', 'OFF-BOOK'):
            cmd.append('--live')
        subprocess.run(cmd)
        print()

    syms = ([s.upper() for s in args.symbols]
            or (args.set_wl and [s.upper() for s in args.set_wl])
            or watchlist())
    if not syms:
        print('no watchlist - set one:  ./now --set SYM SYM')
        if name == 'PRE-MARKET' and not args.scan:
            print('or scan the gappers:     ./now --scan')
        return

    with ThreadPoolExecutor(max_workers=4) as ex:
        rows = list(ex.map(gather, syms))
    for g in rows:
        g['gates'], g['verdict'], g['clabel'], g['fade'] = gates(g, now_et)

    if name.startswith('CLOSED') or name == 'AFTER HOURS':
        print(f'[last session data for: {" ".join(syms)}]\n')

    board(rows, now_et)                          # layer 1

    for g in rows:                               # layer 2
        if g['tape']:
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
            if g['split'].get('split_today'):
                print(f"   REVERSE SPLIT {g['split']['split_today']}:1 took "
                      "effect today - the gap is the split")
            print()
        else:
            print(f"## {g['sym']} - tape fetch failed\n")

    print('-' * 78)
    print("NOT CHECKED here: spread, executable bid/ask, borrow, live halt state,")
    print("Level 2, filings (run catalyst_score.py). Selection only, no order.")


if __name__ == '__main__':
    main()
