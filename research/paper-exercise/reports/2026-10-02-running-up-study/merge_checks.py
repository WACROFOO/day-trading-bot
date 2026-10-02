"""Checks run while merging the redesign proposals. Read-only on alerts.pkl; no repo file touched.
Same filters as runup_study.analyse (6 bad-basis symbol-days dropped, NaN max30 dropped), same split.
1. 4-feature grade (no `mins`) vs 5-feature: train and test AUC10 / AUCsmall / Spearman, RTH vs PM,
   test decile table by TRAIN cut points, day-clustered bootstrap CI on the RTH test AUC10.
2. Dim rules on test: share dimmed, P(+10) of dimmed, share of all +10% alerts dimmed (the cost),
   symbol-days fully dimmed that ran.
3. Context label (curl / back side / at HOD / ?) outcome table, train and test.
"""
import pickle, math, random
import numpy as np
from collections import defaultdict
HERE = __file__.rsplit('/', 1)[0]
alerts, infos = pickle.load(open(HERE + '/alerts.pkl', 'rb'))
bad = {(i['sym'], i['day']) for i in infos if i['basis'] is not None and not (0.9 <= i['basis'] <= 1.1)}
alerts = [a for a in alerts if (a['sym'], a['day']) not in bad and a['max30'] is not None and not math.isnan(a['max30'])]
SPLIT = '2024-01-01'
tr = [a for a in alerts if a['day'] < SPLIT]; te = [a for a in alerts if a['day'] >= SPLIT]
print(f'analysed alerts {len(alerts)} train {len(tr)} test {len(te)} (bad-basis symbol-days dropped: {len(bad)})')

def ranks(s):
    s = np.asarray(s, float); order = np.argsort(s, kind='mergesort'); ss = s[order]
    r = np.empty(len(s)); i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and ss[j + 1] == ss[i]: j += 1
        r[order[i:j + 1]] = (i + j) / 2 + 1; i = j + 1
    return r
def auc(s, y):
    y = np.asarray(y, bool); r = ranks(s); npos = y.sum(); nneg = len(y) - npos
    return (r[y].sum() - npos * (npos + 1) / 2) / (npos * nneg)
def spearman(x, y):
    return float(np.corrcoef(ranks(x), ranks(y))[0, 1])

def make_score(feats):
    ref = {k: np.sort(np.array([float(a[k]) for a in tr if a.get(k) is not None])) for k, _ in feats}
    def f(a):
        s = n = 0
        for k, sg in feats:
            x = a.get(k)
            if x is None: continue
            arr = ref[k]; lo = np.searchsorted(arr, float(x), 'left'); hi = np.searchsorted(arr, float(x), 'right')
            s += sg * (lo + hi) / 2 / len(arr); n += 1
        return s / n if n else 0.0
    return f

F5 = [('bar_range', 1), ('move', 1), ('chg', 1), ('vwap_dist', 1), ('mins', -1)]
F4 = F5[:4]
F3 = F5[:3]
pm = lambda a: a['t'] < '09:30'
def med(xs):
    xs = [x for x in xs if x is not None and not math.isnan(x)]
    return float(np.median(xs)) if xs else float('nan')
def row(g):
    if not g: return '     0'
    p10 = 100 * np.mean([a['max30'] >= 10 for a in g]); sm = 100 * np.mean([a['max30'] < 3 for a in g])
    up = 100 * np.mean([a['ret30'] > 0 for a in g if a['ret30'] is not None and not math.isnan(a['ret30'])])
    return (f"{len(g):6d} {p10:6.1f} {sm:6.1f} {med([a['ret30'] for a in g]):+6.1f} {up:6.1f} "
            f"{med([a['dd30'] for a in g]):+6.1f}")
HDR = '     n P>=10 small% ret30  up30%  dd30'

print('\n## 1. grade variants')
scores = {}
for name, feats in (('5-feature (published)', F5), ('4-feature (no mins)', F4), ('3-feature (bar_range, move, chg)', F3)):
    sc = make_score(feats); scores[name] = sc
    for part, sub_tr, sub_te in (('all', tr, te), ('PM 07:00-09:30', [a for a in tr if pm(a)], [a for a in te if pm(a)]),
                                 ('RTH 09:30-11:30', [a for a in tr if not pm(a)], [a for a in te if not pm(a)])):
        out = []
        for sub in (sub_tr, sub_te):
            s = np.array([sc(a) for a in sub]); y = np.array([a['max30'] for a in sub])
            out.append(f"n={len(sub):6d} AUC10={auc(s, y >= 10):.3f} AUCsm={auc(s, y < 3):.3f} rho={spearman(s, y):+.3f}")
        print(f"{name:34s} {part:16s} TRAIN {out[0]} | TEST {out[1]}")

for name in ('4-feature (no mins)', '5-feature (published)'):
    sc = scores[name]
    cuts = np.quantile(np.array([sc(a) for a in tr]), np.linspace(0.1, 0.9, 9))
    for a in tr + te:
        a['dec_' + name[0]] = int(np.searchsorted(cuts, sc(a), 'right')) + 1
    print(f'\n{name}: TEST deciles by TRAIN cut points (all 07:00-11:30)\n decile' + HDR)
    for d in range(1, 11):
        print(f'  {d:4d}  ' + row([a for a in te if a['dec_' + name[0]] == d]))
    print(f'{name}: TEST RTH-only deciles by the same TRAIN cut points\n decile' + HDR)
    for d in range(1, 11):
        print(f'  {d:4d}  ' + row([a for a in te if not pm(a) and a['dec_' + name[0]] == d]))
    print(f'{name}: TEST PM-only deciles by the same TRAIN cut points\n decile' + HDR)
    for d in range(1, 11):
        print(f'  {d:4d}  ' + row([a for a in te if pm(a) and a['dec_' + name[0]] == d]))

# day-clustered bootstrap CI of the RTH test AUC10, 4-feature
sc4 = scores['4-feature (no mins)']
rth = [a for a in te if not pm(a)]
byday = defaultdict(list)
for a in rth: byday[a['day']].append((sc4(a), a['max30'] >= 10))
days = sorted(byday); rng = random.Random(11); vals = []
for _ in range(300):
    pts = [p for d in (rng.choice(days) for _ in days) for p in byday[d]]
    s = np.array([p[0] for p in pts]); y = np.array([p[1] for p in pts])
    vals.append(auc(s, y))
print(f"\n4-feature RTH test AUC10 day-clustered bootstrap 95% CI [{np.percentile(vals, 2.5):.3f}, {np.percentile(vals, 97.5):.3f}] (300 draws, {len(days)} days)")
pmte = [a for a in te if pm(a)]
byday = defaultdict(list)
for a in pmte: byday[a['day']].append((sc4(a), a['max30'] >= 10))
days = sorted(byday); vals = []
for _ in range(300):
    pts = [p for d in (rng.choice(days) for _ in days) for p in byday[d]]
    vals.append(auc(np.array([p[0] for p in pts]), np.array([p[1] for p in pts])))
print(f"4-feature PM test AUC10 day-clustered bootstrap 95% CI [{np.percentile(vals, 2.5):.3f}, {np.percentile(vals, 97.5):.3f}] (300 draws, {len(days)} days)")

print('\n## 2. dim rules, TEST 07:00-11:30')
by = defaultdict(list)
for a in te: by[(a['sym'], a['day'])].append(a)
first = set()
for v in by.values():
    first.add(id(min(v, key=lambda a: a['epoch'])))
n_run = sum(a['max30'] >= 10 for a in te)
rules = {
    'R3 raw: move<4 OR range<1': lambda a: a['move'] < 4 or a['bar_range'] < 1,
    'RU-4(a): move<4 AND range<1': lambda a: a['move'] < 4 and a['bar_range'] < 1,
    'R3 protected: (move<4 OR range<1), not 1st alert, >=09:30': lambda a: (a['move'] < 4 or a['bar_range'] < 1) and id(a) not in first and not pm(a),
    'RQ3: 5f decile 1-2': lambda a: a['dec_5'] <= 2,
    'RQ3 on 4f: decile 1-2': lambda a: a['dec_4'] <= 2,
    '4f decile 1-2, not 1st alert, >=09:30': lambda a: a['dec_4'] <= 2 and id(a) not in first and not pm(a),
    '4f decile 1, not 1st alert, >=09:30': lambda a: a['dec_4'] <= 1 and id(a) not in first and not pm(a),
}
for name, f in rules.items():
    d = [a for a in te if f(a)]; nd = [a for a in te if not f(a)]
    alld = [k for k, v in by.items() if all(f(a) for a in v)]
    ran = [k for k in alld if any(a['max30'] >= 10 for a in by[k])]
    print(f"{name:58s} dimmed {len(d):6d} ({100*len(d)/len(te):4.1f}%)  P>=10 dimmed {100*np.mean([a['max30']>=10 for a in d]):4.1f} "
          f"vs undimmed {100*np.mean([a['max30']>=10 for a in nd]):4.1f}  small% dimmed {100*np.mean([a['max30']<3 for a in d]):4.1f}  "
          f"share of all +10% alerts dimmed {100*sum(a['max30']>=10 for a in d)/n_run:4.1f}%  sym-days all dimmed {len(alld)} (ran {len(ran)})")
print(f"test symbol-days {len(by)}; test alerts reaching +10%: {n_run}")

print('\n## 3. context label (hod_dist<0.001 = at HOD; else curl = above session VWAP & MACD ok; back side = MACD not ok or below VWAP; ? = MACD missing)')
def label(a):
    if a['hod_dist'] is not None and a['hod_dist'] < 0.001: return 'at HOD'
    if a['macd_ok'] is None: return '?'
    if a['above_vwap'] and a['macd_ok']: return 'curl'
    return 'back side'
for name, sub in (('TRAIN', tr), ('TEST', te)):
    print(f'{name}\n label     ' + HDR)
    for lab in ('at HOD', 'curl', 'back side', '?'):
        print(f'  {lab:9s}' + row([a for a in sub if label(a) == lab]))

print('\n## 4. first alert of the symbol-day, TEST, by session part')
for part, cond in (('PM', pm), ('RTH', lambda a: not pm(a))):
    f1 = [a for a in te if id(a) in first and cond(a)]; rest = [a for a in te if id(a) not in first and cond(a)]
    print(f'  {part:4s} first ' + row(f1)); print(f'  {part:4s} later ' + row(rest))
