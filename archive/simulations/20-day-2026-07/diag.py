"""DIAGNOSTIC: which component loses the money - the entries or the exits?

Run the identical entry signals under three exit regimes. If the entries have
no edge, none of them profits. If the exits are the problem, the stop-and-
target-only variant separates from the rest.
"""
import datetime as dt, json, os, sys, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim
from run20 import fetch_symbol
from concurrent.futures import ThreadPoolExecutor
OUT=os.path.dirname(os.path.abspath(__file__))
lists=json.load(open(os.path.join(OUT,'watchlists20.json')))
need=sorted({r['sym'] for v in lists.values() for r in v})
bars={}
with ThreadPoolExecutor(max_workers=5) as ex:
    for s,d in ex.map(fetch_symbol, need): bars[s]=d

import engine20
src=open(os.path.join(OUT,'engine20.py')).read()

VARIANTS={
 'as-documented (all exits)': src,
 'stop + target only':        src.replace("if ind.macd_hist is not None and ind.macd_hist < 0:","if False:")
                                 .replace("if ind.vwap and bar['c'] < ind.vwap:","if False:"),
 'stop + target, no MACD':    src.replace("if ind.macd_hist is not None and ind.macd_hist < 0:","if False:"),
}
print(f'{"exit regime":<28}{"trades":>7}{"wins":>6}{"win%":>7}{"reachT1":>8}{"P&L $":>10}{"exp R":>8}')
for name,code in VARIANTS.items():
    open(os.path.join(OUT,'_v.py'),'w').write(code)
    import _v; importlib.reload(_v)
    tot=ntr=nw=t1hit=0; Rs=[]
    for day,rows in lists.items():
        watch=[r['sym'] for r in rows]
        if not watch: continue
        per={s:bars[s][day] for s in watch if s in bars and day in bars[s]}
        res=_v.run_day(dt.date(*map(int,day.split('-'))),watch,per,5,[])
        tot+=res['pnl']
        for t in res['trades']:
            ntr+=1; Rs.append(t['pnl']/(t['risk_ps']*t['full']))
            if t['pnl']>0: nw+=1
            if t['scaled']>=1: t1hit+=1
    exp=sum(Rs)/len(Rs) if Rs else 0
    print(f'{name:<28}{ntr:>7}{nw:>6}{(100*nw/ntr if ntr else 0):>7.1f}{t1hit:>8}{tot:>10.2f}{exp:>+8.3f}')
