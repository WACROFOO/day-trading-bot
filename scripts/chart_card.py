#!/usr/bin/env python3
"""Turn a Warrior Top Gainers export into the chart's typed inputs.

Pine cannot read float (TradingView exposes no float field to scripts) and
Warrior's "Rel Vol Daily Rate" is a different measure from the TV
same-time proxy the chart computes. So the bridge is the operator: this
prints, for one symbol, exactly what to type into the ROSS FP inputs —
float in millions with its provenance choice — plus the Warrior-side
context the chart can NOT know (their RVOL, short interest, gap), so the
two screens can be compared without pretending they are the same number.

Usage:
    python3 scripts/chart_card.py ~/Downloads/Top_Gainers_20260820.csv MMA
    python3 scripts/chart_card.py export.csv            # whole board, brief
"""
import csv
import sys


def load(path):
    rows = []
    with open(path, newline='', encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            sym = r.get('Symbol', '').rstrip('/').rsplit('/', 1)[-1].upper()
            if sym:
                rows.append((sym, r))
    return rows


def fnum(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def card(sym, r):
    px = fnum(r.get('Close Price'))
    fl = fnum(r.get('Float'))
    rv_d = fnum(r.get('Rel Vol - Today'))
    rv_5 = fnum(r.get('Rel Vol - 5 Min'))
    gap = fnum(r.get('Rel Gap'))
    si = fnum(r.get('Short Interest'))
    vol = fnum(r.get('Volume Today'))
    flM = fl / 1e6 if fl else None
    print(f'── {sym} · ${px} · export values (Warrior definitions, not TV) ──')
    print(f'  TYPE INTO THE CHART INPUTS:')
    if flM is not None and flM > 0:
        print(f'    Float (millions)      = {flM:.2f}')
        print(f'    Float provenance      = "Trusted feed verified"  (Dash export)')
    else:
        print(f'    Float (millions)      = 0  (export has none — leave unknown)')
    print(f'  CONTEXT THE CHART CANNOT KNOW (do not type — compare):')
    print(f'    Warrior RelVol daily    {rv_d:,.1f}x   (their denominator, not the TV proxy)')
    print(f'    Warrior RelVol 5-min    {rv_5:,.0f}x')
    print(f'    Gap                     {gap:+.1f}%')
    print(f'    Volume today            {vol:,.0f}')
    print(f'    Short interest          {si:,.0f}' + (f'  ({si/fl*100:.1f}% of float)' if si and fl else ''))
    if flM is not None and flM > 20:
        print(f'    NOTE float {flM:.1f}M is over the 20M sweet-spot cap (FILTERS.md tiers)')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    rows = load(sys.argv[1])
    if len(sys.argv) >= 3:
        want = sys.argv[2].upper()
        hit = [(s, r) for s, r in rows if s == want]
        if not hit:
            print(f'{want}: not in this export ({len(rows)} rows)')
            return 1
        card(*hit[0])
    else:
        print(f'{len(rows)} rows · float(M) · Warrior RelVol daily / 5-min · gap')
        for s, r in rows[:20]:
            fl = fnum(r.get('Float')) or 0
            print(f"  {s:6s} {fl/1e6:8.2f}M  {fnum(r.get('Rel Vol - Today')) or 0:10,.1f}x"
                  f" {fnum(r.get('Rel Vol - 5 Min')) or 0:12,.0f}x  {fnum(r.get('Rel Gap')) or 0:+7.1f}%")
    return 0


if __name__ == '__main__':
    sys.exit(main())
