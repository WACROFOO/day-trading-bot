#!/usr/bin/env python3
"""The trade-proposition ledger — every call, taken or not.

A broker statement only records what you did. It cannot show the reject
that ran (MSGY 2026-08-11: rejected at 4.39, printed 5.43) or the board
call nobody acted on (ONFO 2026-08-14: ranked #1, ignored in the narration).
Those are the expensive lessons, so this ledger records propositions, not
fills, and measures outcomes from the tape rather than from memory.

    python3 scripts/tradelog.py add --sym IPST --source pine-strategy \
        --verdict TRIGGER-SET --entry 7.46 --stop 7.30 --target 7.78 --shares 1249
    python3 scripts/tradelog.py measure --id 20260817-IPST-01   # tape -> mfe/mae
    python3 scripts/tradelog.py report                          # the scoreboard
    python3 scripts/tradelog.py md                              # rebuild the .md mirror

Provenance: `measure` reads 1-minute bars via tape.py and stamps the
measurement time. Nothing in the outcome columns is typed from memory.
"""
import argparse
import csv
import datetime as dt
import os
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tape  # noqa: E402

ET = ZoneInfo('America/New_York')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGDIR = os.path.join(ROOT, 'research', 'trade-log')
CSVP = os.path.join(LOGDIR, 'propositions.csv')
MDP = os.path.join(LOGDIR, 'propositions.md')

FIELDS = [
    'id', 'ts_et', 'symbol', 'source', 'verdict',
    'entry', 'stop', 'target', 'risk_per_share', 'shares', 'risk_usd',
    'room_to_peak_R', 'gates', 'context',
    'taken', 'fill_price', 'outcome', 'pnl_usd',
    'mfe_R', 'mae_R', 'counterfactual_R', 'measured_at',
    'error_class', 'notes',
]

# error taxonomy — built from the cases, extended as new ones appear
ERROR_CLASSES = {
    'SELECTION': 'wrong vehicle — it should never have been on the board',
    'EXECUTION': 'right vehicle, wrong moment / size / exit',
    'PRESENTATION': 'the information was present but invisible',
    'DATA': 'the information was genuinely absent',
    'NARRATION': 'the tool was right, the human summary was wrong',
    'ANTICIPATION': 'the operator acted before the trigger — no proposition existed at that price',
    'VARIANCE': 'the rule fired correctly; the outcome was simply unfavourable',
    'NONE': 'no error — correct call, correct outcome',
}


def rows():
    if not os.path.exists(CSVP):
        return []
    with open(CSVP, newline='') as f:
        return list(csv.DictReader(f))


def write(rs):
    os.makedirs(LOGDIR, exist_ok=True)
    with open(CSVP, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rs:
            w.writerow({k: r.get(k, '') for k in FIELDS})


def f(v):
    """'' and '—' both mean absent — never zero."""
    if v in (None, '', '—'):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def next_id(sym, day):
    n = sum(1 for r in rows() if r['id'].startswith(f'{day}-{sym}-'))
    return f'{day}-{sym}-{n + 1:02d}'


def cmd_add(a):
    day = (a.date or dt.datetime.now(ET).strftime('%Y%m%d')).replace('-', '')
    entry, stop = f(a.entry), f(a.stop)
    rps = round(entry - stop, 4) if entry and stop else None
    r = {
        'id': next_id(a.sym.upper(), day),
        'ts_et': a.ts or dt.datetime.now(ET).strftime('%Y-%m-%d %H:%M'),
        'symbol': a.sym.upper(), 'source': a.source, 'verdict': a.verdict,
        'entry': a.entry or '—', 'stop': a.stop or '—', 'target': a.target or '—',
        'risk_per_share': rps if rps else '—',
        'shares': a.shares or '—',
        'risk_usd': round(rps * float(a.shares), 2) if rps and a.shares else '—',
        'room_to_peak_R': a.room or '—', 'gates': a.gates or '—',
        'context': a.context or '—',
        'taken': a.taken, 'fill_price': a.fill or '—',
        'outcome': a.outcome or ('NOT-TAKEN' if a.taken == 'no' else ''),
        'pnl_usd': a.pnl or '—',
        'mfe_R': '', 'mae_R': '', 'counterfactual_R': '', 'measured_at': '',
        'error_class': a.error or '', 'notes': a.notes or '',
    }
    rs = rows()
    rs.append(r)
    write(rs)
    print(f"added {r['id']}")


def cmd_measure(a):
    """Measure MFE/MAE/counterfactual from the tape. Today's bars only —
    Yahoo's 1-minute history is intraday-limited, so older rows must be
    measured on the day or flagged UNMEASURABLE rather than guessed."""
    rs = rows()
    hit = [r for r in rs if r['id'] == a.id]
    if not hit:
        print(f'no row {a.id}'); return 1
    r = hit[0]
    entry, stop, target = f(r['entry']), f(r['stop']), f(r['target'])
    if not (entry and stop):
        print('row has no entry/stop — nothing to measure'); return 1

    d = tape.compute(r['symbol'])
    if not d:
        print('no bars'); return 1
    day = r['ts_et'][:10]
    if d['rows'][-1][0].strftime('%Y-%m-%d') != day:
        r['counterfactual_R'] = 'UNMEASURABLE (bars are not that day)'
        r['measured_at'] = dt.datetime.now(ET).strftime('%Y-%m-%d %H:%M')
        write(rs)
        print('bars are from a different session — flagged UNMEASURABLE, not guessed')
        return 0

    hhmm = r['ts_et'][11:16]
    after = [b for b in d['rows'] if b[0].strftime('%H:%M') >= hhmm]
    risk = entry - stop
    mfe = max((b[2] for b in after), default=None)
    mae = min((b[3] for b in after), default=None)
    r['mfe_R'] = round((mfe - entry) / risk, 2) if mfe else '—'
    r['mae_R'] = round((mae - entry) / risk, 2) if mae else '—'

    # walk forward: whichever of stop/target the tape touches first
    cf = 'no resolution by session end'
    for b in after:
        if b[3] <= stop:
            cf = '-1.00 (stop touched first)'
            break
        if target and b[2] >= target:
            cf = f'+{round((target - entry) / risk, 2):.2f} (target hit first)'
            break
    r['counterfactual_R'] = cf
    r['measured_at'] = dt.datetime.now(ET).strftime('%Y-%m-%d %H:%M')
    write(rs)
    print(f"{r['id']}  MFE {r['mfe_R']}R  MAE {r['mae_R']}R  counterfactual {cf}")


def cmd_report(a):
    rs = rows()
    now = dt.datetime.now(ET)
    print('=' * 74)
    print(f'TRADE-PROPOSITION LEDGER · {len(rs)} propositions · built {now:%Y-%m-%d %H:%M} ET')
    print('measured from tape.py 1-minute bars · paper account · selection only')
    print('=' * 74)
    if not rs:
        print('empty'); return

    taken = [r for r in rs if r['taken'] == 'yes']
    untaken = [r for r in rs if r['taken'] != 'yes']
    print(f'\n{len(rs)} propositions · {len(taken)} acted on · {len(untaken)} not acted on')
    print(f'  → a broker statement would show only the {len(taken)}.\n')

    def block(title, sub):
        if not sub:
            return
        print(f'  {title}  (n={len(sub)})')
        for r in sub:
            cf = r.get('counterfactual_R') or '—'
            print(f"    {r['id']:<20} {r['verdict']:<12} {r['outcome'] or '—':<10} "
                  f"cf {cf:<28} {r.get('error_class') or '—'}")
        print()

    for src in sorted({r['source'] for r in rs}):
        block(f'source: {src}', [r for r in rs if r['source'] == src])

    # the column no broker statement has
    ran = [r for r in rs if r['taken'] != 'yes'
           and str(r.get('counterfactual_R', '')).startswith('+')]
    print(f'  REJECTS / UNTAKEN THAT WOULD HAVE WORKED  (n={len(ran)})')
    for r in ran:
        print(f"    {r['id']:<20} {r['symbol']:<6} {r['counterfactual_R']}  {r['notes'][:44]}")
    if not ran:
        print('    none measured yet')

    n_meas = sum(1 for r in rs if r.get('counterfactual_R'))
    print(f'\n  measured: {n_meas}/{len(rs)}')
    if n_meas < 10:
        print('  ⚠ SAMPLE TOO SMALL FOR ANY THRESHOLD CHANGE (<10 measured).')
        print('    Read the rows; do not tune a parameter on this.')
    print('\n' + '-' * 74)
    print('NOT CHECKED: spread, executable size, borrow, halt fills. Simulated')
    print('counterfactuals fill AT the level; a real stop on a halting name does not.')


def cmd_md(a):
    rs = rows()
    os.makedirs(LOGDIR, exist_ok=True)
    with open(MDP, 'w') as fh:
        fh.write('# Trade propositions — readable mirror\n\n')
        fh.write('```\nGenerated from propositions.csv by scripts/tradelog.py md.\n'
                 'The CSV is the source of truth. Outcome columns are MEASURED\n'
                 'from tape.py, never typed from memory.\n```\n\n')
        fh.write('| id | ts ET | sym | source | verdict | entry/stop/target | '
                 'room R | taken | outcome | counterfactual | error class |\n')
        fh.write('|---|---|---|---|---|---|---|---|---|---|---|\n')
        for r in rs:
            est = f"{r['entry']}/{r['stop']}/{r['target']}"
            fh.write(f"| {r['id']} | {r['ts_et']} | {r['symbol']} | {r['source']} | "
                     f"{r['verdict']} | {est} | {r['room_to_peak_R']} | {r['taken']} | "
                     f"{r['outcome'] or '—'} | {r.get('counterfactual_R') or '—'} | "
                     f"{r.get('error_class') or '—'} |\n")
        fh.write('\n## Error taxonomy\n\n')
        for k, v in ERROR_CLASSES.items():
            fh.write(f'- **{k}** — {v}\n')
        fh.write('\nPaper only. Selection evidence, not edge.\n')
    print(f'wrote {MDP}')


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)

    a = sub.add_parser('add')
    a.add_argument('--sym', required=True)
    a.add_argument('--source', required=True,
                   choices=['chat', 'now-board', 'pine-strategy', 'pine-scanner', 'dash'])
    a.add_argument('--verdict', required=True)
    a.add_argument('--date'); a.add_argument('--ts')
    a.add_argument('--entry'); a.add_argument('--stop'); a.add_argument('--target')
    a.add_argument('--shares'); a.add_argument('--room'); a.add_argument('--gates')
    a.add_argument('--context'); a.add_argument('--taken', default='no', choices=['yes', 'no'])
    a.add_argument('--fill'); a.add_argument('--outcome'); a.add_argument('--pnl')
    a.add_argument('--error'); a.add_argument('--notes')
    a.set_defaults(func=cmd_add)

    m = sub.add_parser('measure'); m.add_argument('--id', required=True)
    m.set_defaults(func=cmd_measure)
    sub.add_parser('report').set_defaults(func=cmd_report)
    sub.add_parser('md').set_defaults(func=cmd_md)

    args = ap.parse_args()
    return args.func(args) or 0


if __name__ == '__main__':
    sys.exit(main())
