"""Is the pillar gradient monotonic? PARAMETERS.md sec.12 step 3."""
import datetime as dt, json, os, sys, importlib
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import sim
from run20 import fetch_symbol
from concurrent.futures import ThreadPoolExecutor
OUT=os.path.dirname(os.path.abspath(__file__))
lists=json.load(open(os.path.join(OUT,'watchlists20.json')))
need=sorted({r['sym'] for v in lists.values() for r in v})
bars={}
with ThreadPoolExecutor(max_workers=5) as ex:
    for s_,d in ex.map(fetch_symbol,need): bars[s_]=d
import engine20
print(f'{"min pillars":>12}{"trades":>8}{"wins":>6}{"win%":>7}{"P&L $":>11}{"exp R":>9}')
for mp in (9,8,7,6,5):
    sim.MIN_PILLARS=mp; importlib.reload(engine20)
    tot=ntr=nw=0; Rs=[]
    for day,rows in lists.items():
        watch=[r['sym'] for r in rows]
        if not watch: continue
        per={s_:bars[s_][day] for s_ in watch if s_ in bars and day in bars[s_]}
        res=engine20.run_day(dt.date(*map(int,day.split('-'))),watch,per,5,[])
        tot+=res['pnl']
        for t in res['trades']:
            ntr+=1; Rs.append(t['pnl']/(t['risk_ps']*t['full']))
            if t['pnl']>0: nw+=1
    exp=sum(Rs)/len(Rs) if Rs else 0
    print(f'{mp:>12}{ntr:>8}{nw:>6}{(100*nw/ntr if ntr else 0):>7.1f}{tot:>11.2f}{exp:>+9.3f}')
