#!/usr/bin/env python3
"""Deal one real setup as a decision, with the future withheld.

Everything here is a real symbol on a real July session, printed exactly as far
as the clock had run at the decision minute - the same forward-only contract
the engine works under. Nothing after the decision bar is shown, and the
indicators are computed from the bars above it only.

    python diagnostics/exercise.py SYM YYYY-MM-DD HH:MM        # deal it
    ANSWER=1 python diagnostics/exercise.py SYM YYYY-MM-DD HH:MM  # mark it

ANSWER prints what happened next and what the engine did. Do not run it until
the answer is written down.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import datetime as dt
import json

import sim
from sim import Indicators, PullbackTracker, evaluate, GATE_CONDITIONS, SLIPPAGE
from run20 import fetch_symbol

OUT = _DATA
SYM, DAY, AT = sys.argv[1].upper(), sys.argv[2], sys.argv[3]
SHOW = int(os.environ.get('SHOW', 26))          # bars of history to print

pool = {c['sym']: c for c in json.load(open(os.path.join(OUT, 'pool20.json')))}
stats = {(r['sym'], r['day']): r
         for r in json.load(open(os.path.join(OUT, 'scan20_stats.json')))}
_, d = fetch_symbol(SYM)
day = d[DAY]
pre, ses = day.get('pre', []), day['session']

ind = Indicators()
for b in pre:
    ind.update(b, in_session=False)
tr, prev, flipped, rows = PullbackTracker(), None, [], []
cut = None
for i, bar in enumerate(ses):
    hm = bar['dt'].strftime('%H:%M')
    hod_prev = ind.session_high
    ind.update(bar, in_session=True)
    pb = tr.update(bar, prev, ind)
    rows.append((hm, bar, ind.vwap, ind.ema9, ind.ema20, ind.macd_hist,
                 pb, hod_prev, i))
    if hm == AT:
        cut = len(rows)
        break
    prev = bar
    if ind.session_high and bar['h'] >= ind.session_high:
        flipped = (flipped + [round(bar['h'], 2)])[-6:]
if cut is None:
    sys.exit(f'no bar at {AT}')

c = pool.get(SYM, {})
st = stats.get((SYM, DAY), {})
print(f'{"=" * 68}')
print(f'  {SYM}   {DAY}   decision at {AT} ET')
print(f'{"=" * 68}')
print(f'  price band     ${c.get("price", 0):.2f}          '
      f'market cap ${c.get("mcap", 0)/1e6:.0f}M')
print(f'  float (proxy)  {c.get("mcap", 0)/max(c.get("price") or 1, .01)/1e6:.1f}M shares')
print(f'  gap at open    {st.get("gap_pct", 0):+.0f}%   '
      f'prev close ${st.get("prev_close", 0):.2f} -> open ${st.get("open_px", 0):.2f}')
print(f'  relative vol   {st.get("rvol5", 0):.0f}x normal in the first 5 minutes')
print(f'  pre-market     {len(pre)} bars'
      + (f', ${pre[0]["c"]:.2f} -> ${pre[-1]["c"]:.2f}' if pre else ''))
print(f'  catalyst       not in this dataset - assume there is news, as there')
print(f'                 always is on a name that gaps like this\n')

print(f'  {"time":<6}{"open":>7}{"high":>7}{"low":>7}{"close":>7}{"volume":>11}'
      f'{"VWAP":>7}{"9EMA":>7}{"MACD":>8}   bar')
run_hi = None
for hm, b, vwap, e9, e20, mh, pb, hod, i in rows[max(0, cut - SHOW):cut]:
    tag = 'green' if b['c'] >= b['o'] else 'RED'
    if hod and b['h'] >= hod:
        tag += ', new high'
    if hm == AT:
        tag += '   <-- now'
    print(f'  {hm:<6}{b["o"]:>7.2f}{b["h"]:>7.2f}{b["l"]:>7.2f}{b["c"]:>7.2f}'
          f'{b["v"]:>11,}{(vwap or 0):>7.2f}{(e9 or 0):>7.2f}'
          f'{(mh if mh is not None else 0):>+8.3f}   {tag}')
gaps = [rows[j][0] for j in range(max(1, cut - SHOW), cut)
        if (dt.datetime.strptime(rows[j][0], '%H:%M')
            - dt.datetime.strptime(rows[j-1][0], '%H:%M')).seconds > 60]
if gaps:
    print(f'\n  minutes with no bar before: {", ".join(gaps)}')
    print('  (no trades printed, or a halt - this dataset cannot tell them apart)')

hm, bar, vwap, e9, e20, mh, pb, hod, i = rows[cut - 1]
print(f'\n  session high so far  ${(hod or bar["h"]):.2f}')
print(f'  cumulative volume    {sum(x[1]["v"] for x in rows[:cut]):,}')

if not os.environ.get('ANSWER'):
    print(f'\n{"-" * 68}')
    print('  Your call. Say what you would do and why - and if you would')
    print('  trade it, give me the entry, the stop, the first target, and')
    print('  the share size on a 500 EUR account.')
    print(f'{"-" * 68}')
    sys.exit()

# ---- marking ---------------------------------------------------------
print(f'\n{"=" * 68}\n  WHAT HAPPENED NEXT\n{"=" * 68}')
fut = ses[i + 1:i + 31]
print(f'  {"time":<6}{"open":>7}{"high":>7}{"low":>7}{"close":>7}{"volume":>9}')
for b in fut:
    print(f'  {b["dt"].strftime("%H:%M"):<6}{b["o"]:>7.2f}{b["h"]:>7.2f}'
          f'{b["l"]:>7.2f}{b["c"]:>7.2f}{b["v"]:>9,}')
if fut:
    lo = min(x['l'] for x in fut)
    hi = max(x['h'] for x in fut)
    print(f'\n  over the next {len(fut)} minutes: low ${lo:.2f}, high ${hi:.2f}')

print(f'\n  ENGINE VIEW AT {AT}')
if not pb:
    print('  the detector saw no completed pullback on this bar')
else:
    ok, checks = evaluate(pb, bar, ind, flipped)
    entry = min(pb['trigger_level'] + SLIPPAGE, bar['h'])
    print(f'  pullback: {len(pb["bars"])} bars, index {pb["index"]}, '
          f'low ${pb["low"]:.2f}')
    print(f'  entry ${entry:.2f}   stop ${pb["low"]:.2f}   '
          f'risk ${entry - pb["low"]:.3f}/share')
    for k, v in sorted(checks.items()):
        if k in GATE_CONDITIONS:
            print(f'    [{"x" if v[0] else " "}] {k:<34}{v[1]}')
