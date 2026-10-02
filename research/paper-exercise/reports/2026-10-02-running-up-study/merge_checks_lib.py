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

