import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import datetime as dt, json, os, sys

import sim
from sim import Indicators, PullbackTracker, evaluate
from run20 import fetch_symbol
sym,day='VEEE','2026-07-13'
_,d=fetch_symbol(sym); d=d[day]
ind=Indicators()
for b in d['pre']: ind.update(b,in_session=False)
tr=PullbackTracker(); prev=None; flipped=[]
print(f'{"time":>6} {"legLow":>7}{"legHi":>7}{"pbLow":>7}{"pole":>6}{"idx":>4}  failed checks')
n=0
for bar in d['session']:
    t=bar['dt'].time()
    if t>=dt.time(11,30): break
    ind.update(bar,in_session=True)
    pb=tr.update(bar,prev,ind)
    if pb and t>=dt.time(9,35):
        n+=1
        ok,checks=evaluate(pb,bar,ind,flipped)
        fail=[k for k,(p,_) in checks.items() if not p]
        print(f'{t.strftime("%H:%M"):>6} {pb["leg_low"]:>7.2f}{pb["leg_high"]:>7.2f}'
              f'{pb["low"]:>7.2f}{pb["pole"]:>6.2f}{pb["index"]:>4}  '
              + ('ALL PASS' if ok else '; '.join(fail[:3])))
    prev=bar
print('setups:',n)
