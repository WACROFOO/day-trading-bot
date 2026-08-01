"""Leave-one-out: how many setups pass every condition EXCEPT one?

If dropping a single condition unlocks a lot of setups, that condition is the
binding constraint. If dropping any one still leaves ~0, the conditions are
jointly unsatisfiable on this data and the specification - not the parameters -
is the problem.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import datetime as dt, json, os, sys

import sim
from sim import Indicators, PullbackTracker, evaluate
from run20 import fetch_symbol
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
OUT = _DATA
lists=json.load(open(os.path.join(OUT,'watchlists20.json')))
need=sorted({r['sym'] for v in lists.values() for r in v})
bars={}
with ThreadPoolExecutor(max_workers=5) as ex:
    for s,d in ex.map(fetch_symbol,need): bars[s]=d

allchecks=[]
for day,rows in lists.items():
    for r in rows:
        d=bars.get(r['sym'],{}).get(day)
        if not d: continue
        ind=Indicators()
        for b in d['pre']: ind.update(b,in_session=False)
        tr=PullbackTracker(); prev=None; flipped=[]
        for bar in d['session']:
            t=bar['dt'].time()
            if t>=dt.time(11,30): break
            ind.update(bar,in_session=True)
            pb=tr.update(bar,prev,ind)
            if pb and t>=dt.time(9,35):
                ok,checks=evaluate(pb,bar,ind,flipped)
                allchecks.append({k:v[0] for k,v in checks.items()})
            prev=bar
keys=sorted(allchecks[0])
n=len(allchecks)
full=sum(1 for c in allchecks if all(c.values()))
print(f'setups: {n}   passing ALL conditions: {full}\n')
print(f'{"drop this condition":<34}{"then passing":>13}{"indiv pass%":>13}')
for k in keys:
    passing=sum(1 for c in allchecks if all(v for kk,v in c.items() if kk!=k))
    indiv=100*sum(1 for c in allchecks if c[k])/n
    print(f'{k:<34}{passing:>13}{indiv:>12.0f}%')
# how many conditions does a typical setup fail?
fails=Counter(sum(1 for v in c.values() if not v) for c in allchecks)
print('\nnumber of conditions failed per setup:')
for k in sorted(fails): print(f'  {k} failed: {fails[k]:>4} setups')
