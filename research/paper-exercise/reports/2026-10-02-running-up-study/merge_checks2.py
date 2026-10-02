"""Add-on to merge_checks.py: the 3-feature grade (bar_range, move, chg; train percentiles, train cut points)
as the candidate shipped grade. Test decile and quintile readouts (all / RTH / PM), RTH and PM bootstrap CI,
and the protected dim rules on it. Read-only on alerts.pkl."""
import importlib.util, sys, random, math
import numpy as np
from collections import defaultdict
spec = importlib.util.spec_from_file_location('mc', __file__.rsplit('/',1)[0] + '/merge_checks_lib.py')
mc = importlib.util.module_from_spec(spec); spec.loader.exec_module(mc)
tr, te, pm, row, HDR, auc = mc.tr, mc.te, mc.pm, mc.row, mc.HDR, mc.auc
sc = mc.make_score(mc.F3)
trs = np.array([sc(a) for a in tr])
for q, name in ((10, 'decile'), (5, 'quintile')):
    cuts = np.quantile(trs, np.linspace(1/q, 1 - 1/q, q - 1))
    for a in tr + te:
        a[name] = int(np.searchsorted(cuts, sc(a), 'right')) + 1
    for lab, sub in (('TRAIN all', tr), ('TEST all', te), ('TEST RTH 09:30-11:30', [a for a in te if not pm(a)]), ('TEST PM 07:00-09:30', [a for a in te if pm(a)])):
        print(f'\n3-feature {name}s by TRAIN cut points — {lab}\n {name[:4]}  ' + HDR)
        for d in range(1, q + 1):
            print(f'  {d:3d}  ' + row([a for a in sub if a[name] == d]))
rng = random.Random(13)
for part, sub in (('RTH', [a for a in te if not pm(a)]), ('PM', [a for a in te if pm(a)])):
    byday = defaultdict(list)
    for a in sub: byday[a['day']].append((sc(a), a['max30'] >= 10))
    days = sorted(byday); vals = []
    for _ in range(300):
        pts = [p for d in (rng.choice(days) for _ in days) for p in byday[d]]
        vals.append(auc(np.array([p[0] for p in pts]), np.array([p[1] for p in pts])))
    print(f"3-feature {part} test AUC10 day-clustered bootstrap 95% CI [{np.percentile(vals, 2.5):.3f}, {np.percentile(vals, 97.5):.3f}] (300 draws, {len(days)} days)")
by = defaultdict(list)
for a in te: by[(a['sym'], a['day'])].append(a)
first = {id(min(v, key=lambda a: a['epoch'])) for v in by.values()}
n_run = sum(a['max30'] >= 10 for a in te)
rules = {
    '3f quintile 1 (=deciles 1-2), unprotected': lambda a: a['quintile'] == 1,
    '3f quintile 1, not 1st alert, >=09:30': lambda a: a['quintile'] == 1 and id(a) not in first and not pm(a),
    '3f decile 1, not 1st alert, >=09:30': lambda a: a['decile'] == 1 and id(a) not in first and not pm(a),
    'no-grade fallback: move<4 AND range<1, not 1st, >=09:30': lambda a: a['move'] < 4 and a['bar_range'] < 1 and id(a) not in first and not pm(a),
}
print('\n## dim rules on TEST 07:00-11:30')
for name, f in rules.items():
    d = [a for a in te if f(a)]; nd = [a for a in te if not f(a)]
    alld = [k for k, v in by.items() if all(f(a) for a in v)]
    ran = [k for k in alld if any(a['max30'] >= 10 for a in by[k])]
    print(f"{name:58s} dimmed {len(d):6d} ({100*len(d)/len(te):4.1f}%)  P>=10 dimmed {100*np.mean([a['max30']>=10 for a in d]):4.1f} "
          f"vs undimmed {100*np.mean([a['max30']>=10 for a in nd]):4.1f}  small% dimmed {100*np.mean([a['max30']<3 for a in d]):4.1f}  "
          f"share of all +10% alerts dimmed {100*sum(a['max30']>=10 for a in d)/n_run:4.1f}%  sym-days all dimmed {len(alld)} (ran {len(ran)})")
# same protected rule on TRAIN, for stability
byt = defaultdict(list)
for a in tr: byt[(a['sym'], a['day'])].append(a)
firstt = {id(min(v, key=lambda a: a['epoch'])) for v in byt.values()}
f = lambda a: a['quintile'] == 1 and id(a) not in firstt and not pm(a)
d = [a for a in tr if f(a)]; nrt = sum(a['max30'] >= 10 for a in tr)
print(f"TRAIN 3f quintile 1, not 1st, >=09:30: dimmed {len(d)} ({100*len(d)/len(tr):.1f}%) P>=10 dimmed {100*np.mean([a['max30']>=10 for a in d]):.1f} share of all +10% dimmed {100*sum(a['max30']>=10 for a in d)/nrt:.1f}%")
