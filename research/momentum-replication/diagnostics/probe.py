"""What does the confluence check actually see at a real pullback low?"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import datetime as dt, json, os, sys

import sim
from sim import Indicators, PullbackTracker
from run20 import fetch_symbol
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
OUT = _DATA
lists=json.load(open(os.path.join(OUT,'watchlists20.json')))
need=sorted({r['sym'] for v in lists.values() for r in v})
bars={}
with ThreadPoolExecutor(max_workers=5) as ex:
    for s,d in ex.map(fetch_symbol,need): bars[s]=d

cnt=Counter(); hits=Counter(); dists=[]
for day,rows in lists.items():
    for r in rows:
        sym=r['sym']; d=bars.get(sym,{}).get(day)
        if not d: continue
        ind=Indicators()
        for b in d['pre']: ind.update(b,in_session=False)
        tr=PullbackTracker(); prev=None
        for bar in d['session']:
            if bar['dt'].time()>=dt.time(11,30): break
            ind.update(bar,in_session=True)
            pb=tr.update(bar,prev,ind)
            if pb:
                p=pb['low']; tol=max(p*sim.LEVEL_TOL_PCT,0.01)
                levels={'9EMA':(p-ind.ema9) if ind.ema9 else None,
                        '20EMA':(p-ind.ema20) if ind.ema20 else None,
                        'VWAP':(p-ind.vwap) if ind.vwap else None}
                n=0
                for k,v in levels.items():
                    if v is None: continue
                    dists.append((k,v/p*100))
                    if abs(v)<=tol: hits[k]+=1; n+=1
                cnt[n]+=1
            prev=bar
print('confluence count distribution at real pullback lows:')
for k in sorted(cnt): print(f'  {k} reasons: {cnt[k]:>4} setups')
print('\nwhich levels hit:', hits.most_common())
import statistics
print('\nSIGNED distance: pullback low MINUS level, % of price')
print('(positive = dip stopped ABOVE the level, i.e. never reached support)')
for k in ['9EMA','20EMA','VWAP']:
    v=[d for n,d in dists if n==k]
    if v:
        above=sum(1 for x in v if x>0)
        print(f'  {k:<8} median {statistics.median(v):+.3f}%   above level: {100*above/len(v):.0f}% of setups')
print(f'\ncurrent tolerance = {sim.LEVEL_TOL_PCT*100:.2f}% (floor 1 cent)')
