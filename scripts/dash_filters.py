#!/usr/bin/env python3
"""Reverse-engineer Day Trade Dash filters from an alert CSV export.

Feed it one or more exports; it merges them, profiles every strategy branch,
and — the part that actually identifies thresholds — runs a single-axis
exclusion search:

    for each branch S, for each symbol X that NEVER fired S:
        test X against the observed envelope of S on every axis.
        if X fails EXACTLY ONE axis, that axis is a real filter of S,
        and the gap between X and the envelope brackets the threshold.

That is how the $10 price ceiling on Low Float / High Rel Vol was found
(PFSA passed float, volume, both RVOLs and change; only price failed).
A symbol failing two or more axes identifies nothing and is reported as
such rather than being quietly dropped.

    python3 scripts/dash_filters.py captures/*.csv
    python3 scripts/dash_filters.py captures/*.csv --hod      # verify vs tape.py bars
    python3 scripts/dash_filters.py captures/*.csv --md report.md

Observed bounds BRACKET a threshold; they never reveal it. Every number
printed is an envelope edge or an exclusion bracket, and is labelled as one.
Paper only — knowing the funnel is selection evidence, not edge.
"""
import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# axis -> (column, direction) where direction says which side is permissive.
# 'max' = the branch admits values UP TO some ceiling (float, price)
# 'min' = the branch admits values FROM some floor upward (volume, rvol, change)
AXES = {
    'price':     ('Price', 'both'),
    'float_M':   ('float_M', 'max'),
    'volume':    ('Volume', 'min'),
    'rvol_daily': ('rvolD', 'min'),
    'rvol_5min': ('rvol5', 'min'),
    'change_pct': ('chg', 'min'),
    'short_int': ('si', 'both'),
}

# Axes that are present in the export but are NOT plausibly scanner filters.
# Short interest is a displayed data column; no Warrior material describes it
# as a gate on a momentum scan. A single-axis exclusion landing here is far
# more likely to be the day's population than a rule, so it is graded SUSPECT
# rather than silently promoted alongside price and float.
NON_FILTER_AXES = {'short_int'}

RENAME = {
    'Relative Volume(Daily Rate)': 'rvolD',
    'Relative Volume(5 min %)': 'rvol5',
    'Change From Close(%)': 'chg',
    'Gap(%)': 'gap',
    'Short Interest': 'si',
    'Strategy Name': 'branch',
}


def load(paths):
    frames = []
    for p in paths:
        d = pd.read_csv(p, encoding='utf-8-sig')
        d.columns = [c.strip() for c in d.columns]
        d['_src'] = os.path.basename(p)
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df = df.rename(columns=RENAME)
    df['sym'] = df['Symbol / News'].str.extract(r'/quote/([A-Z.\-]+)/')
    df['float_M'] = df['Float'] / 1e6
    df['t'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_convert(
        'America/New_York')
    # a row is (alert instant x branch); identical rows across files are one alert
    n0 = len(df)
    df = df.drop_duplicates(subset=['timestamp', 'sym', 'branch'])
    return df, n0


def envelope(g):
    """Observed admissible range per axis for one branch."""
    env = {}
    for name, (col, _) in AXES.items():
        if col in g and g[col].notna().any():
            env[name] = (g[col].min(), g[col].max())
    return env


def violations(row_best, env):
    """Which axes does this symbol's BEST attempt fail against the envelope?

    'Best attempt' is deliberately generous: for a floor axis we take the
    symbol's maximum, for a ceiling axis its minimum. If even its best value
    cannot reach the branch's observed range, the axis genuinely excludes it.
    """
    out = []
    for name, (col, direction) in AXES.items():
        if name not in env or col not in row_best:
            continue
        lo, hi = env[name]
        vmin, vmax = row_best[col]
        if direction == 'min':
            if vmax < lo:
                out.append((name, f'best {vmax:,.2f} < branch floor {lo:,.2f}'))
        elif direction == 'max':
            if vmin > hi:
                out.append((name, f'best {vmin:,.2f} > branch ceiling {hi:,.2f}'))
        else:  # both — a two-sided window
            if vmin > hi:
                out.append((name, f'best {vmin:,.2f} > branch max {hi:,.2f}'))
            elif vmax < lo:
                out.append((name, f'best {vmax:,.2f} < branch min {lo:,.2f}'))
    return out


def exclusion_search(df):
    """The identification engine. Returns (identified, ambiguous)."""
    identified, ambiguous = [], []
    per_sym = {}
    for s, g in df.groupby('sym'):
        per_sym[s] = {col: (g[col].min(), g[col].max())
                      for _, (col, _) in AXES.items() if col in g}

    for branch, g in df.groupby('branch'):
        env = envelope(g)
        fired = set(g['sym'])
        for s in sorted(set(df['sym']) - fired):
            v = violations(per_sym[s], env)
            if len(v) == 1:
                name, why = v[0]
                col, direction = AXES[name]
                lo, hi = env[name]
                vmin, vmax = per_sym[s][col]
                if direction == 'min':
                    bracket = f'floor in ({vmax:,.4g}, {lo:,.4g}]'
                else:
                    bracket = f'ceiling in [{hi:,.4g}, {vmin:,.4g})'
                # Support = how many distinct symbols built the envelope. With
                # 2 symbols an "envelope" is two points, and a single-axis
                # exclusion is as likely coincidence as filter. Grading this
                # is the difference between a finding and a fluke: the $10
                # price ceiling (support 2 but corroborated) and a short-interest
                # "ceiling" (pure coincidence) otherwise print identically.
                sup = len(fired)
                grade = 'FIRM' if sup >= 4 else 'TENTATIVE' if sup == 3 else 'WEAK'
                if name in NON_FILTER_AXES:
                    grade = 'SUSPECT'
                identified.append((branch, s, name, why, bracket, sup, grade))
            elif v:
                ambiguous.append((branch, s, [n for n, _ in v]))
    order = {'FIRM': 0, 'TENTATIVE': 1, 'WEAK': 2, 'SUSPECT': 3}
    identified.sort(key=lambda r: (order[r[6]], r[0]))
    return identified, ambiguous


def hod_check(df):
    """Does the alert bar set a new high of day? Needs same-session bars."""
    try:
        import tape
    except Exception as e:
        return None, f'tape.py unavailable ({e})'
    bars, notes = {}, []
    for s in sorted(df['sym'].unique()):
        try:
            d = tape.compute(s)
            bars[s] = (pd.DataFrame(d['rows'], columns=['t', 'o', 'h', 'l', 'c', 'v'])
                       .set_index('t')) if d and d.get('rows') else None
        except Exception as e:
            bars[s] = None
            notes.append(f'{s}: {e}')

    day = df['t'].dt.strftime('%Y-%m-%d').mode()[0]
    hits = tot = 0
    base_hit = base_tot = 0
    for s, b in bars.items():
        if b is None or len(b) < 5:
            continue
        if b.index[-1].strftime('%Y-%m-%d') != day:
            notes.append(f'{s}: bars are {b.index[-1]:%Y-%m-%d}, capture is {day} — skipped')
            continue
        run = b['h'].cummax().shift(1)
        v = (b['h'] >= run).iloc[3:]
        base_hit += int(v.sum()); base_tot += len(v)
        for t in df.loc[df['sym'] == s, 't']:
            bt = t.floor('min')
            prior, cur = b[b.index < bt], b[b.index == bt]
            if len(prior) < 3 or len(cur) == 0:
                continue
            tot += 1
            hits += int(cur['h'].iloc[0] >= prior['h'].max())
    if not tot:
        return None, 'no measurable rows (bars not from the capture session)'
    return {'hits': hits, 'tot': tot,
            'base': (base_hit, base_tot)}, '; '.join(notes)


def report(df, n_raw, paths, hod, args):
    L = []
    a = L.append
    day = df['t'].dt.strftime('%Y-%m-%d').mode()[0]
    a('```')
    a(f'SOURCE · {len(paths)} export(s): ' + ', '.join(os.path.basename(p) for p in paths))
    a(f'         {len(df)} unique alert rows (from {n_raw} raw; duplicates merged)')
    a(f'         {day} · {df["t"].min():%H:%M:%S} → {df["t"].max():%H:%M:%S} ET')
    a(f'         {df["sym"].nunique()} distinct symbols · {df["branch"].nunique()} branches')
    a('CLEAN-ROOM · inferred from exported output only. Server thresholds UNDISCLOSED.')
    a('! OBSERVED BOUNDS BRACKET A THRESHOLD, THEY DO NOT REVEAL IT.')
    a(f'! EFFECTIVE n IS {df["sym"].nunique()} SYMBOLS, NOT {len(df)} ROWS — names re-alert continuously.')
    a('```')
    a('')

    a('## Branches present')
    a('')
    a('| branch | rows | symbols | price | float M | vol min | rvolD min | chg min |')
    a('|---|---:|---|---|---|---:|---:|---:|')
    for b, g in df.groupby('branch'):
        a(f'| {b} | {len(g)} | {len(set(g["sym"]))} | '
          f'{g["Price"].min():.2f}–{g["Price"].max():.2f} | '
          f'{g["float_M"].min():.2f}–{g["float_M"].max():.2f} | '
          f'{g["Volume"].min():,.0f} | {g["rvolD"].min():.2f} | {g["chg"].min():.1f}% |')
    a('')

    ev = df['event'].value_counts()
    a(f'`event` values: ' + ', '.join(f'**{k}** ×{v}' for k, v in ev.items()))
    a('')
    if hod:
        h, t = hod['hits'], hod['tot']
        bh, bt = hod['base']
        a(f'**HOD verification vs continuous 1-min bars:** alert bar sets a new high '
          f'in **{h}/{t}** measurable cases ({h / t * 100:.1f}%), against a baseline of '
          f'{bh}/{bt} ({bh / bt * 100:.1f}%) across all bars of these names.')
        a('')

    ident, amb = exclusion_search(df)
    a('## Identified filters (single-axis exclusions)')
    a('')
    a('A symbol that never fired a branch, yet clears that branch\'s observed range on')
    a('every axis but one. The surviving axis is a real filter; the gap brackets it.')
    a('')
    a('Graded by **support** — how many distinct symbols built the branch envelope.')
    a('FIRM ≥4 · TENTATIVE 3 · WEAK 2 (an "envelope" of two points) · SUSPECT = the')
    a('axis is not a plausible scanner filter. Only FIRM rows deserve a dial change.')
    a('')
    if ident:
        a('| grade | branch | excluded | axis | evidence | bracket | support |')
        a('|---|---|---|---|---|---|---:|')
        for b, sy, ax, why, br, sup, gr in ident:
            a(f'| **{gr}** | {b} | {sy} | **{ax}** | {why} | **{br}** | {sup} sym |')
    else:
        a('_None. No symbol in this capture fails exactly one axis of a branch it '
          'never fired — nothing is identified._')
    a('')

    a('## Not identified (excluded on 2+ axes — reported, not hidden)')
    a('')
    if amb:
        for b, s, axes in sorted(amb):
            a(f'- `{b}` × **{s}** — fails {len(axes)}: {", ".join(axes)}')
    else:
        a('_None._')
    a('')

    a('## Limitations')
    a('')
    a(f'- **{df["sym"].nunique()} symbols.** Envelope edges are set by which names '
      'qualified, not by a boundary being approached.')
    a('- Row counts are not observation counts; a name re-alerts every few seconds.')
    a('- Single-axis exclusion identifies an axis, not a value. The bracket is the claim.')
    a('- The export carries no news/catalyst field — the flame is UI-only.')
    if hod:
        a('- HOD cross-check uses yahoo pre-market bars, thinner than the platform feed.')
    a('- Paper only. Selection evidence, not edge.')
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv', nargs='+')
    ap.add_argument('--hod', action='store_true',
                    help='verify the New High condition against tape.py bars (same session only)')
    ap.add_argument('--md', help='write the report to this path')
    args = ap.parse_args()

    df, n_raw = load(args.csv)
    hod, note = (None, '')
    if args.hod:
        hod, note = hod_check(df)
        if note:
            print(f'# hod notes: {note}', file=sys.stderr)
    out = report(df, n_raw, args.csv, hod, args)
    if args.md:
        with open(args.md, 'w') as fh:
            fh.write(out + '\n')
        print(f'wrote {args.md}')
    else:
        print(out)


if __name__ == '__main__':
    sys.exit(main() or 0)
