"""Did the watchlist names go up after the open, or fade?"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import datetime as dt, json, os, sys

from run20 import fetch_symbol
from concurrent.futures import ThreadPoolExecutor
OUT = _DATA
lists=json.load(open(os.path.join(OUT,'watchlists20.json')))
need=sorted({r['sym'] for v in lists.values() for r in v})
bars={}
with ThreadPoolExecutor(max_workers=5) as ex:
    for s,d in ex.map(fetch_symbol,need): bars[s]=d
faded=held=0; rows=[]
for day,ws in lists.items():
    for r in ws:
        d=bars.get(r['sym'],{}).get(day)
        if not d or not d['session']: continue
        sess=[b for b in d['session'] if b['dt'].time()<dt.time(11,30)]
        if not sess: continue
        o=sess[0]['o']; hi=max(b['h'] for b in sess); last=sess[-1]['c']
        # was it above its opening price at 09:35, and did it trend up?
        at935=[b for b in sess if b['dt'].time()<=dt.time(9,35)][-1]['c']
        rows.append((day,r['sym'],o,at935,hi,last,(hi/o-1)*100,(last/o-1)*100))
        if last<o: faded+=1
        else: held+=1
print(f'watchlist symbol-days: {len(rows)}   closed 11:30 BELOW the open: {faded}  above: {held}')
print(f'fade rate: {100*faded/len(rows):.0f}%')
import statistics
print(f'median run open->high: {statistics.median(r[6] for r in rows):+.1f}%')
print(f'median open->11:30:    {statistics.median(r[7] for r in rows):+.1f}%')
print(f'\n{"day":<11}{"sym":<6}{"open":>7}{"09:35":>7}{"high":>7}{"11:30":>7}{"run%":>7}{"net%":>7}')
for r in sorted(rows)[:14]:
    print(f'{r[0]:<11}{r[1]:<6}{r[2]:>7.2f}{r[3]:>7.2f}{r[4]:>7.2f}{r[5]:>7.2f}{r[6]:>+7.1f}{r[7]:>+7.1f}')
