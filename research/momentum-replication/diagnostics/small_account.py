#!/usr/bin/env python3
"""What the engine's July would have done on a small account.

The 17-session run is normally priced for $10,000. Nothing about the SIGNALS
changes with account size - the same setups fire on the same bars - but three
things about the OUTCOME do, and two of them are not in the playbook:

  risk per trade   2% of the account, so every P&L scales down with it
  share rounding   int(risk / risk_per_share). At $200 risk that rounds away
                   nothing; at $10 it rounds 16.1 shares to 16, and the
                   remainder is real money not put to work
  buying power     4x intraday margin is a pattern-day-trader privilege FINRA
                   grants at $25,000 and above. A $500 account gets 1x
  PDT rule         a margin account under $25,000 is capped at 3 day trades per
                   rolling 5 business days. The engine's 11 trades are not
                   evenly spread, so this binds

Reported both ways: the arithmetic scaling, and the same run with the day-trade
cap enforced in date order. Neither includes commissions or FX - see the note
the script prints at the end.

Usage:
    ACCOUNT=500 python diagnostics/small_account.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import datetime as dt
import json
from concurrent.futures import ThreadPoolExecutor

import sim
from engine20 import run_day
from run20 import fetch_symbol
from run20b import build

OUT = _DATA
PDT_MAX, PDT_WINDOW = 3, 5          # day trades per rolling business days

stats = json.load(open(os.path.join(OUT, 'scan20_stats.json')))
daily = json.load(open(os.path.join(OUT, 'daily20.json')))
pool = {c['sym']: c for c in json.load(open(os.path.join(OUT, 'pool20.json')))}
so = {s: c['mcap'] / c['price'] for s, c in pool.items() if c['price']}
lists = build(stats, daily, so)
need = sorted({r['sym'] for v in lists.values() for r in v})
bars = {}
with ThreadPoolExecutor(max_workers=5) as ex:
    for s, d in ex.map(fetch_symbol, need):
        bars[s] = d
for day in list(lists):
    keep = []
    for r in lists[day]:
        d = bars.get(r['sym'], {}).get(day)
        f5 = [b for b in (d or {}).get('session', []) if b['dt'].time() < dt.time(9, 35)]
        if f5 and f5[-1]['c'] > f5[0]['o']:
            keep.append(r)
    lists[day] = keep

sessions = sorted(lists)
rows = []
for day in sessions:
    syms = [r['sym'] for r in lists[day]]
    per = {s: bars[s][day] for s in syms if s in bars and day in bars[s]}
    if not per:
        continue
    res = run_day(dt.date(*map(int, day.split('-'))), syms, per, 5, [])
    rows += [(day, t) for t in res['trades']]

A = sim.ACCOUNT
print(f'=== {sessions[0]} .. {sessions[-1]}, {len(sessions)} sessions, '
      f'${A:,.0f} account ===')
print(f'risk per trade ${sim.RISK_PER_TRADE:,.2f} (2%)   '
      f'buying power ${sim.BUYING_POWER:,.0f} ({sim.MARGIN:g}x)   '
      f'daily loss limit ${sim.MAX_DAILY_LOSS:,.2f}\n')

print(f'{"day":<12}{"sym":<6}{"in":>6}{"$/sh":>6}{"shares":>7}{"cost":>9}'
      f'{"P&L":>9}{"R":>7}  reason')
for day, t in rows:
    R = t['pnl'] / (t['risk_ps'] * t['full'])
    print(f'{day:<12}{t["sym"]:<6}{t["entry_time"]:>6}{t["risk_ps"]:>6.2f}'
          f'{t["full"]:>7}{t["full"] * t["entry"]:>9.0f}{t["pnl"]:>9.2f}'
          f'{R:>+7.2f}  {t["reason"]}')

def summarise(label, sel):
    if not sel:
        print(f'\n{label}: no trades')
        return
    tot = sum(t['pnl'] for _, t in sel)
    w = [t for _, t in sel if t['pnl'] > 0]
    Rs = [t['pnl'] / (t['risk_ps'] * t['full']) for _, t in sel]
    print(f'\n{label}')
    print(f'  trades {len(sel)}   winners {len(w)} ({100*len(w)/len(sel):.0f}%)   '
          f'expectancy {sum(Rs)/len(Rs):+.2f}R')
    print(f'  P&L ${tot:+,.2f}   on a ${A:,.0f} account that is '
          f'{100*tot/A:+.1f}%   ending balance ${A + tot:,.2f}')

summarise('ALL SIGNALS TAKEN (ignores the day-trade cap)', rows)

# --- PDT: 3 day trades per rolling 5 business days ---------------------
idx = {d: i for i, d in enumerate(sessions)}
taken, skipped = [], []
for day, t in rows:
    i = idx[day]
    recent = [d for d, _ in taken if idx[d] > i - PDT_WINDOW]
    if len(recent) >= PDT_MAX:
        skipped.append((day, t))
    else:
        taken.append((day, t))

summarise(f'WITH THE PDT CAP ({PDT_MAX} day trades per {PDT_WINDOW} sessions)',
          taken)
if skipped:
    lost = sum(t['pnl'] for _, t in skipped)
    print(f'  {len(skipped)} signal(s) skipped for the cap: '
          + ', '.join(f'{d[5:]} {t["sym"]}' for d, t in skipped))
    print(f'  those would have been ${lost:+,.2f}')

# --- what the frictions would do ---------------------------------------
n = len(taken)
shares = sum(t['full'] for _, t in taken)
print(f'\nNOT modelled, and material at this size:')
print(f'  commissions   {n} round trips. At $0/trade (Schwab, IBKR Lite) this is')
print(f'                $0; at $1 per side it is ${2*n:.0f}, '
      f'{200*n/A:.1f}% of the account')
print(f'  regulatory    SEC + FINRA TAF on sells, roughly '
      f'${shares * 0.000166:.2f} total on {shares:,} shares')
print(f'  FX            a euro account buying US stock converts twice per trade.')
print(f'                At 0.25% per conversion that is about '
      f'{0.5 * n:.1f}% of turnover')
print(f'  slippage      ${sim.SLIPPAGE:.2f}/share IS modelled on entry, not exit')
