#!/usr/bin/env python3
"""Your journal vs the engine — every trade gets the script's verdict.

For each journal row, this fetches that symbol-day's real 1m tape, runs
the benchmark engine (the Python port of ross-fp-v4.pine's decision
core) with a trace, and reports what the engine believed at your entry
minute and WHY: MATCHED (it traded within 3 min of you), MISSED with the
gate that blocked it, or OFF-PATTERN (no setup structure at all there).

The aggregate table at the end is the improvement loop's input: a gate
that repeatedly blocks YOUR winners at n>=30 is a gate to re-measure
(never to delete by feel). Yahoo keeps 1m bars ~30 days — audit trades
while they are young.

    python3 scripts/trade_audit.py            # audit everything
    python3 scripts/trade_audit.py --sym JUNS

Caveats, honestly: the engine is the bar-level Python port, not the Pine
itself; Pine-only gates (max stop %, halt band, scanner pillars) are
shown when computable but not enforced; sequence inside a bar is
unknowable from OHLC.
"""
import argparse
import csv
import datetime as dt
import importlib.util
import os
import sys
from collections import Counter
from zoneinfo import ZoneInfo

ET = ZoneInfo('America/New_York')
HERE = os.path.dirname(os.path.abspath(__file__))
JOURNAL = os.path.join(HERE, '..', 'research', 'trade-journal', 'journal.csv')
BENCH = os.path.join(HERE, '..', 'research', 'momentum-replication', 'pine_bench.py')

spec = importlib.util.spec_from_file_location('pine_bench', BENCH)
pb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pb)


def fetch_day(sym, date):
    d = dt.datetime.strptime(date, '%Y-%m-%d')
    p1 = int(d.replace(hour=4, tzinfo=ET).timestamp())
    p2 = int(d.replace(hour=20, tzinfo=ET).timestamp())
    return pb.fetch_window(sym, p1, p2)


def hhmm_min(s):
    h, m = s.split(':')
    return int(h) * 60 + int(m)


def audit(row, cfg):
    sym, date = row['sym'], row['date']
    try:
        bars = fetch_day(sym, date)
    except Exception as e:
        return dict(cls='NO-DATA', detail=f'{e} (1m bars keep ~30 days)')
    if not bars:
        return dict(cls='NO-DATA', detail='empty tape')
    trace = []
    res = pb.run(sym, bars, cfg, trace=trace)
    e_min = hhmm_min(row['entry_hhmm'])

    for t in res['trades']:
        if abs(t['t_in'] - e_min) <= 3:
            return dict(cls='MATCHED', detail=f"engine {t['kind']} r={t['r']:+.2f}")

    state_at = None
    notes_before = []
    for rec in trace:
        m = dt.datetime.fromtimestamp(rec['t'], ET)
        rmin = m.hour * 60 + m.minute
        if 'state' in rec and rmin <= e_min:
            state_at = rec
        if 'note' in rec and e_min - 12 <= rmin <= e_min:
            notes_before.append((rmin, rec))

    why = None
    for rmin, rec in reversed(notes_before):
        n = rec['note']
        if n == 'NOARM':
            parts = []
            if not rec.get('in_win'):
                parts.append('outside 07:00-11:30 window')
            if not rec.get('macd_ok'):
                parts.append('MACD not positive')
            vr = rec.get('dip_vol_ratio')
            if vr is not None and vr > 0.70:
                parts.append(f'dip volume {vr}x (cap 0.70)')
            sp = rec.get('stop_pct')
            if sp is not None and sp > 3.0:
                parts.append(f'stop {sp}% (Pine caps 3%)')
            why = ' + '.join(parts) if parts else 'gates passed late — timing'
            break
        if n in ('REJECT', 'ARM-CANCEL'):
            why = rec.get('why', n)
            break
    st = state_at['state'] if state_at else '?'
    if why:
        return dict(cls='MISSED', detail=f'engine state {st} · blocked by: {why}')
    if st in ('IDLE',):
        return dict(cls='OFF-PATTERN', detail='no push/dip structure at your entry — '
                    'a different setup than first-pullback')
    return dict(cls='MISSED', detail=f'engine state {st}, no arm — likely timing/lane gap')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sym', default=None)
    args = ap.parse_args()
    if not os.path.exists(JOURNAL):
        print('journal empty — log trades first: python3 scripts/trade_log.py add ...')
        return 1
    with open(JOURNAL, newline='') as fh:
        rows = [r for r in csv.DictReader(fh)
                if not args.sym or r['sym'] == args.sym.upper()]
    if not rows:
        print('no matching journal rows')
        return 1
    cfg = pb.Cfg('audit', sameBarStop=True, entryTimeOK=True,
                 risk=20.0, maxPos=2000.0, retestBand=True)
    agg = Counter()
    pnl_by = Counter()
    print(f'{len(rows)} trade(s) · engine = Python port of ross-fp decision core\n')
    for r in rows:
        v = audit(r, cfg)
        agg[v['cls']] += 1
        pnl_by[v['cls']] += float(r['pnl'])
        print(f"  {r['date']} {r['sym']:6s} {r['entry_hhmm']}@{r['entry']} "
              f"{float(r['pnl']):+8.2f}$  {v['cls']:11s} {v['detail']}")
    print('\n── aggregate (the loop input) ──')
    for cls, n in agg.most_common():
        print(f'  {cls:11s} {n:3d} trades · your net {pnl_by[cls]:+.2f}$')
    print('\nRule: a gate blocking profitable MISSED trades gets re-measured at n>=30\n'
          '(research/trade-journal/README.md) — thresholds move on evidence, not feel.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
