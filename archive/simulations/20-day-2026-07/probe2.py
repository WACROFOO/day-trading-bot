"""When do setups occur, and how often does the VWAP reset fire?"""
import datetime as dt, json, os, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import sim
from sim import Indicators, PullbackTracker
from run20 import fetch_symbol
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
OUT=os.path.dirname(os.path.abspath(__file__))
lists=json.load(open(os.path.join(OUT,'watchlists20.json')))
need=sorted({r['sym'] for v in lists.values() for r in v})
bars={}
with ThreadPoolExecutor(max_workers=5) as ex:
    for s,d in ex.map(fetch_symbol,need): bars[s]=d
buckets=Counter(); resets=Counter(); belowvwap=Counter(); barcount=Counter()
symdays=0
for day,rows in lists.items():
    for r in rows:
        sym=r['sym']; d=bars.get(sym,{}).get(day)
        if not d or not d['session']: continue
        symdays+=1
        ind=Indicators()
        for b in d['pre']: ind.update(b,in_session=False)
        tr=PullbackTracker(); prev=None
        for bar in d['session']:
            t=bar['dt'].time()
            if t>=dt.time(11,30): break
            b='09:30-10:00' if t<dt.time(10,0) else '10:00-10:30' if t<dt.time(10,30) else '10:30-11:30'
            ind.update(bar,in_session=True); barcount[b]+=1
            if ind.vwap and bar['c']<ind.vwap: belowvwap[b]+=1
            pb=tr.update(bar,prev,ind)
            if pb: buckets[b]+=1
            prev=bar
print('symbol-days:',symdays)
print(f'\n{"window":<14}{"bars":>7}{"setups":>8}{"below VWAP":>12}{"% below":>9}')
for b in ['09:30-10:00','10:00-10:30','10:30-11:30']:
    n=barcount[b]
    print(f'{b:<14}{n:>7}{buckets[b]:>8}{belowvwap[b]:>12}{100*belowvwap[b]/max(n,1):>8.0f}%')
