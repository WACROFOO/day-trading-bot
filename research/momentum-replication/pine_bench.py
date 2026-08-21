"""Bar-level benchmark of ross-fp V7.5 vs V8.0 execution cores on real 1m data.

Shared: impulse->pullback->armed->fill state machine, T1/runner ladder,
07:00-11:30 window, bailout, slippage, commissions ($1/order).
Divergences modelled (the benchmarkable subset):
  D1 sameBarStop   V8: exits pre-staged -> bar touching trigger AND stop
                   stops out same bar (counted ambiguous). V7.5: bracket
                   lands next bar -> position survives the bar; protective
                   stop only active from the NEXT bar.
  D2 entryTimeOK   V8: no arming on the last in-window bar (>=11:29).
  D3 sizing        V7.5: $100k acct, $200 risk, $25k max pos.
                   V8:   $2k acct,  $20 risk,  $2k max pos. shares>=1 gate.
  D5 retestBand    V8: deep undercut (>0.5 ATR below broken HOD) kills the
                   retest episode. V7.5: any touch keeps it.
NOT modelled (tick-level / display-only, cannot be driven from OHLC):
varip rollback zombies, laneHits intrabar inflation, ghost/plan display,
alert dedup. Those change what the SCREEN says, not what fills.
"""
import pickle, datetime as dt, math
from zoneinfo import ZoneInfo
ET = ZoneInfo('America/New_York')
TICK = 0.01
SLIP = 10 * TICK          # strategy(slippage=10)
COMM = 1.0                # cash_per_order

def ema_series(vals, n):
    k = 2/(n+1); out=[vals[0]]
    for v in vals[1:]: out.append(v*k + out[-1]*(1-k))
    return out

class Cfg:
    def __init__(self, name, sameBarStop, entryTimeOK, risk, maxPos, retestBand,
                 winStart=7*60, winEnd=11*60+30, lateJoin=False,
                 macdMode='signal', maxStopPct=None):
        self.name=name; self.sameBarStop=sameBarStop; self.entryTimeOK=entryTimeOK
        self.risk=risk; self.maxPos=maxPos; self.retestBand=retestBand
        self.winStart=winStart; self.winEnd=winEnd; self.lateJoin=lateJoin
        # 'signal'   macd >= signal (the harness's original)
        # 'pine'     macd > 0 AND histogram > 0  (ross-fp-v4.pine V9.12)
        # 'sourced'  macd > 0 only — the corpus rule without the local
        #            histogram addition (STRATEGY.md: "MACD positive =
        #            green light"; the histogram condition is not sourced)
        self.macdMode=macdMode
        # riskGate's stop cap as % of price (ross-fp-v4.pine: 3.0).
        # None = no cap, which is what this harness did before.
        self.maxStopPct=maxStopPct

V75 = Cfg('V7.5', sameBarStop=False, entryTimeOK=False, risk=200.0, maxPos=25000.0, retestBand=False)
V80 = Cfg('V8.0', sameBarStop=True,  entryTimeOK=True,  risk=20.0,  maxPos=2000.0,  retestBand=True)

def _macd_ok(mode, m, s_, i):
    if mode == 'pine':
        return m[i] > 0 and (m[i] - s_[i]) > 0
    if mode == 'sourced':
        return m[i] > 0
    return m[i] >= s_[i]


def run(sym, bars, cfg, trace=None):
    """bars: list of (ts,o,h,l,c,v) ints/floats, chronological.
    trace: optional list — appended with per-bar state dicts and event
    notes so trade_audit.py can say what the engine believed at any
    minute. Caveat: this is the Python port, not the Pine; a few Pine
    gates (max stop %, halt band) are reported, not enforced."""
    closes=[b[4] for b in bars]
    e12=ema_series(closes,12); e26=ema_series(closes,26)
    macd=[a-b for a,b in zip(e12,e26)]; sig=ema_series(macd,9)
    # Wilder ATR14
    atr=[]; prev_c=None; a=None
    for (t,o,h,l,c,v) in bars:
        tr = h-l if prev_c is None else max(h-l, abs(h-prev_c), abs(l-prev_c))
        a = tr if a is None else (a*13+tr)/14
        atr.append(a); prev_c=c
    trades=[]; ambiguous=0; sharesRejected=0; armed_count=0; flattens=0
    samebar_risk=0; lastbar_arms=0; lj_peak=-1
    state='IDLE'; day=None
    pos=None  # dict(entry, stop, t1, t2, sh, half_done, entry_i)
    arm=None  # dict(trigger, stop, bar_armed)
    dayHigh=None; brokenHOD=None; brokenBar=None; retestArmedUsed=False
    setupsToday=0
    pull=None
    for i,(t,o,h,l,c,v) in enumerate(bars):
        d = dt.datetime.fromtimestamp(t, ET)
        if day != d.date():
            # new day: flatten anything (shouldn't exist), reset
            if pos is not None:
                trades.append(dict(sym=sym, day=day, t_in=pos['hhmm_in'], r=(bars[i-1][4]-pos['entry'])/pos['rps'],
                                   cash=pos['sh_open']*(bars[i-1][4]-pos['entry']) - COMM, kind='DAYEND'))
                pos=None; flattens+=1
            day=d.date(); state='IDLE'; arm=None; dayHigh=None; brokenHOD=None
            setupsToday=0; pull=None; retestArmedUsed=False
        hhmm = d.hour*60+d.minute
        if trace is not None:
            trace.append(dict(t=t, state=('LONG' if pos is not None else state), armed=arm is not None))
        in_win = cfg.winStart <= hhmm < cfg.winEnd
        last_win_bar = hhmm >= cfg.winEnd - 1
        dayHigh = h if dayHigh is None else max(dayHigh, h)
        # ---- position management first (orders live from prior bars) ----
        if pos is not None and pos.get('bail_next') and i > pos['bail_i']:
            px = o - SLIP
            cash = pos.get('cash_banked',0) + pos['sh']*(px-pos['entry']) - COMM*2
            r = pos.get('r_banked',0) + (pos['sh']/pos['sh_open'])*(px-pos['entry'])/pos['rps']
            trades.append(dict(sym=sym, day=day, t_in=pos['hhmm_in'], r=r, cash=cash, kind='BAIL')); pos=None
        if pos is not None:
            stop_active = (i > pos['entry_i']) or pos['stop_same_bar']
            exited=False
            # gap through stop
            if stop_active and o <= pos['stop']:
                px = o - SLIP
                trades.append(dict(sym=sym, day=day, t_in=pos['hhmm_in'], r=(px-pos['entry'])/pos['rps'],
                    cash=pos['sh_open']*(px-pos['entry']) - COMM*2, kind='STOP-GAP')); exited=True
            elif stop_active and l <= pos['stop'] and h >= (pos['t1'] if not pos['half_done'] else pos['t2']):
                ambiguous += 1  # both touched: resolve stop-first, both engines
                px = pos['stop'] - SLIP
                trades.append(dict(sym=sym, day=day, t_in=pos['hhmm_in'], r=(px-pos['entry'])/pos['rps'],
                    cash=pos['sh_open']*(px-pos['entry']) - COMM*2, kind='STOP-AMBIG')); exited=True
            elif stop_active and l <= pos['stop']:
                px = pos['stop'] - SLIP
                trades.append(dict(sym=sym, day=day, t_in=pos['hhmm_in'], r=(px-pos['entry'])/pos['rps'],
                    cash=pos['sh_open']*(px-pos['entry']) - COMM*2, kind='STOP')); exited=True
            else:
                if not pos['half_done'] and h >= pos['t1']:
                    px = max(o, pos['t1'])
                    half = pos['sh']//2
                    if half >= 1 and pos['sh'] > 1:
                        pos['cash_banked'] = pos.get('cash_banked',0) + half*(px-pos['entry']) - COMM
                        pos['r_banked'] = pos.get('r_banked',0) + 0.5*(px-pos['entry'])/pos['rps']
                        pos['sh'] -= half
                    pos['half_done']=True; pos['stop']=pos['entry']  # BE
                if pos is not None and pos['half_done'] and h >= pos['t2']:
                    px = max(o, pos['t2'])
                    cash = pos.get('cash_banked',0) + pos['sh']*(px-pos['entry']) - COMM*2
                    r = pos.get('r_banked',0) + (pos['sh']/pos['sh_open'])*(px-pos['entry'])/pos['rps']
                    trades.append(dict(sym=sym, day=day, t_in=pos['hhmm_in'], r=r, cash=cash, kind='T2')); exited=True
                # bailout: confirmed close below stop while stop not yet active (V7.5 path)
                if pos is not None and not exited and not stop_active and c < pos['stop']:
                    pos['bail_next']=True; pos['bail_i']=i
            if exited: pos=None
        # session-edge flatten
        if pos is not None and not in_win and cfg.winStart <= pos['hhmm_in'] :
            px = o - SLIP if o else c
            cash = pos.get('cash_banked',0) + pos['sh']*(px-pos['entry']) - COMM*2
            r = pos.get('r_banked',0) + (pos['sh']/pos['sh_open'])*(px-pos['entry'])/pos['rps']
            trades.append(dict(sym=sym, day=day, t_in=pos['hhmm_in'], r=r, cash=cash, kind='SESSFLAT')); pos=None; flattens+=1
        # ---- pending entry order ----
        if arm is not None and pos is None:
            if not in_win:
                arm=None
            elif c < arm['stop']:
                if trace is not None:
                    trace.append(dict(t=t, note='ARM-CANCEL', why='close below stop'))
                arm=None  # invalidated
            elif h >= arm['trigger']:
                entry = max(o, arm['trigger']) + SLIP
                rps = entry - arm['stop'] + 2*SLIP   # slippage-stressed risk/share
                if rps <= 0: arm=None
                else:
                    sh = min(int(cfg.risk // rps), int(cfg.maxPos // entry))
                    if setupsToday >= 2: sh = sh//2   # third fill half size
                    if sh < 1:
                        sharesRejected += 1; arm=None
                    else:
                        stop_same_bar = cfg.sameBarStop
                        pos = dict(entry=entry, stop=arm['stop'], rps=rps,
                                   t1=entry+rps, t2=entry+2*rps, sh=sh, sh_open=sh,
                                   half_done=False, entry_i=i, stop_same_bar=stop_same_bar,
                                   hhmm_in=hhmm)
                        setupsToday += 1
                        arm=None
                        if trace is not None:
                            trace.append(dict(t=t, note='FILL', entry=round(entry,4)))
                        if l <= pos['stop']: samebar_risk += 1
                        # V8 same-bar: stop touched after entry this very bar
                        if stop_same_bar and l <= pos['stop']:
                            ambiguous += 1
                            px = pos['stop'] - SLIP
                            trades.append(dict(sym=sym, day=day, t_in=pos['hhmm_in'], r=(px-pos['entry'])/pos['rps'],
                                cash=pos['sh_open']*(px-pos['entry']) - COMM*2, kind='STOP-SAMEBAR'))
                            pos=None
        # ---- setup detection (confirmed bars only; skip if in position) ----
        if pos is not None: continue
        if state=='IDLE' or state=='IMPULSE':
            # impulse scan: windows of 1..6 bars ending here
            found=None
            for w in range(1,7):
                j = i-w+1
                if j < 1: continue
                lo = min(b[3] for b in bars[j:i+1]); hi = max(b[2] for b in bars[j:i+1])
                if lo <= 0: continue
                push = hi - lo
                pushPct = push/lo*100
                if not (pushPct >= 5.0 or (atr[i] and push >= 2.0*atr[i])): continue
                net = bars[i][4]-bars[j][1]
                path = sum(abs(b[4]-b[1]) for b in bars[j:i+1]) or 1e-9
                if net/path < 0.60 or net <= 0: continue
                base = [b[5] for b in bars[max(0,j-20):j]]
                baseavg = sum(base)/len(base) if base else 0
                pv = sum(b[5] for b in bars[j:i+1])/w
                if baseavg > 0 and pv < 2.0*baseavg: continue
                if pv*c < 100000: continue
                found=dict(lo=lo, hi=hi, start=j)
                break
            if found and c > o and in_win:
                state='IMPULSE'; pull=dict(push=found, reds=0, plow=None, pvol=0, redhigh=None)
                continue
            # V8.2 LATE JOIN: peak printed while the machine was busy; join
            # the dip in progress. Mirrors the Pine block: peak green and
            # still the high, >=1 red since, push gates on the completed
            # window, retrace ok; arm same-bar off the last red high.
            if cfg.lateJoin and state=='IDLE' and not found and arm is None:
                ljdone=False
                for poff in range(1,5):
                    if ljdone or i-poff < 22 or (i-poff) == lj_peak: continue
                    pk = bars[i-poff]
                    if not pk[4] > pk[1]: continue
                    since = bars[i-poff+1:i+1]
                    if not since or any(b[2] >= pk[2] for b in since): continue
                    reds=[b for b in since if b[4]<b[1]]
                    if not reds: continue
                    plow=min(b[3] for b in since); pvol=sum(b[5] for b in since)
                    for cb in range(1,7):
                        j=i-poff-cb+1
                        if j<1 or ljdone: continue
                        wlo=min(b[3] for b in bars[j:i-poff+1]); whi=pk[2]
                        if wlo<=0: continue
                        push=whi-wlo; pushPct=push/wlo*100
                        if not (pushPct>=5.0 or (atr[i] and push>=2.0*atr[i])): continue
                        net=pk[4]-bars[j][1]
                        path=sum(abs(b[4]-b[1]) for b in bars[j:i-poff+1]) or 1e-9
                        if net/path<0.60 or net<=0: continue
                        base=[b[5] for b in bars[max(0,j-20):j]]
                        baseavg=sum(base)/len(base) if base else 0
                        pv=sum(b[5] for b in bars[j:i-poff+1])/cb
                        if baseavg>0 and pv<2.0*baseavg: continue
                        if pv*pk[4]<100000: continue
                        if (whi-plow)/max(push,1e-9)>0.50: continue
                        # join + same-bar arm off the last red candle's high
                        state='IMPULSE'
                        pull=dict(push=dict(lo=wlo,hi=whi,start=j), reds=len(reds),
                                  plow=plow, pvol=pvol, redhigh=reds[-1][2])
                        lj_peak=i-poff; ljdone=True
                        if in_win and (not cfg.entryTimeOK or not last_win_bar) and macd[i]>=sig[i]:
                            pbvol=pvol/len(reds)
                            if pv>0 and pbvol/pv<=0.70:
                                trigger=pull['redhigh']+TICK; stop=plow-TICK
                                if atr[i] and (trigger-stop)<0.3*atr[i]:
                                    stop=trigger-1.5*atr[i]
                                arm=dict(trigger=trigger, stop=stop)
                                armed_count+=1
                                if last_win_bar: lastbar_arms+=1
                continue
        if state=='IMPULSE' and pull is not None:
            if c < o:  # red bar: pullback building
                pull['reds'] += 1
                pull['plow'] = l if pull['plow'] is None else min(pull['plow'], l)
                pull['pvol'] += v
                pull['redhigh'] = h
                pushrange = pull['push']['hi'] - pull['push']['lo']
                retr = (pull['push']['hi'] - pull['plow'])/pushrange if pushrange>0 else 1
                if pull['reds'] > 4 or retr > 0.50:
                    if trace is not None:
                        trace.append(dict(t=t, note='REJECT',
                            why=f'dip too deep ({retr*100:.0f}%)' if retr > 0.50 else 'dip too long'))
                    state='IDLE'; pull=None
                elif pull['reds'] >= 1:
                    # armable on next green cross of red-bar high — place stop order now
                    if in_win and (not cfg.entryTimeOK or not last_win_bar) and _macd_ok(cfg.macdMode, macd, sig, i):
                        w = pull['push']['start']
                        pushbars = i - w
                        pushvol = sum(b[5] for b in bars[w:i+1-pull['reds']]) / max(1, pushbars-pull['reds']+1)
                        pbvol = pull['pvol']/pull['reds']
                        if pushvol>0 and pbvol/pushvol <= 0.70:
                            trigger = pull['redhigh'] + TICK
                            stop = pull['plow'] - TICK
                            if atr[i] and (trigger-stop) < 0.3*atr[i]:
                                stop = trigger - 1.5*atr[i]   # ATR-fallback
                            if cfg.maxStopPct is not None and trigger > 0 and \
                                    (trigger - stop) / trigger * 100 > cfg.maxStopPct:
                                pass          # riskGate: stop too wide to size
                            else:
                                arm = dict(trigger=trigger, stop=stop)
                                armed_count += 1
                                if last_win_bar: lastbar_arms += 1
                            if trace is not None:
                                trace.append(dict(t=t, note='ARM', trigger=round(trigger,4), stop=round(stop,4)))
                    if trace is not None and arm is None and pull['reds'] >= 1:
                        _w = pull['push']['start']
                        _pb = i - _w
                        _pv = sum(b[5] for b in bars[_w:i+1-pull['reds']]) / max(1, _pb-pull['reds']+1)
                        _vr = (pull['pvol']/pull['reds'])/_pv if _pv > 0 else None
                        _trig = pull['redhigh'] + TICK
                        _stp = pull['plow'] - TICK
                        trace.append(dict(t=t, note='NOARM',
                            in_win=in_win, macd_ok=bool(_macd_ok(cfg.macdMode, macd, sig, i)),
                            dip_vol_ratio=round(_vr, 2) if _vr else None,
                            stop_pct=round((_trig - _stp) / _trig * 100, 1) if _trig > 0 else None))
            elif h > pull['push']['hi']:
                pull['push']['hi']=h  # push extends
            elif pull['reds']>0 and c > o:
                state='IDLE'; pull=None
    return dict(trades=trades, ambiguous=ambiguous, sharesRejected=sharesRejected,
                armed=armed_count, flattens=flattens, samebar=samebar_risk, lastbar=lastbar_arms)

def agg(results):
    T=[t for r in results for t in r['trades']]
    wins=[t for t in T if t['r']>0]; losses=[t for t in T if t['r']<=0]
    return dict(fills=len(T), wins=len(wins), losses=len(losses),
        sumR=round(sum(t['r'] for t in T),2),
        cash=round(sum(t['cash'] for t in T),2),
        ambiguous=sum(r['ambiguous'] for r in results),
        samebar=sum(r['samebar'] for r in results),
        lastbarArms=sum(r['lastbar'] for r in results),
        shRej=sum(r['sharesRejected'] for r in results),
        armed=sum(r['armed'] for r in results),
        flats=sum(r['flattens'] for r in results))


# ---------------------------------------------------------------- data ----
import subprocess as _sp, json as _json, time as _time
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
UNIVERSE = ['SGLY','PFSA','WFF','XOS','HCWB','WETO','IPST','EHGO','YJ','TNON',
            'BTCT','CDTG','MSGY','JWEL','SCKT','WXM','WYHG','GENK','ELPW','STIM',
            'TDIC','DKI','INLF','NXTC','XHLD','ZJYL','CLRO','ASTC','AZI','BYAH']

def fetch_window(sym, p1, p2):
    """Yahoo v8 chart, 1m, pre/post included — same endpoint tape.py uses.
    1m data exists for ~30 days back, max ~8 calendar days per request."""
    url = (f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}'
           f'?period1={p1}&period2={p2}&interval=1m&includePrePost=true')
    r = _sp.run(['curl','-s','--compressed','--max-time','30',
                 '-H', f'User-Agent: {UA}', url], capture_output=True, text=True)
    res = _json.loads(r.stdout)['chart']['result'][0]
    ts = res['timestamp']; q = res['indicators']['quote'][0]
    return [(t, q['open'][i], q['high'][i], q['low'][i], q['close'][i], q['volume'][i])
            for i, t in enumerate(ts) if q['close'][i] is not None]

def fetch_all(cache, windows):
    out = {}
    for s in UNIVERSE:
        rows = []
        for (p1, p2) in windows:
            try:
                rows += fetch_window(s, p1, p2)
            except Exception as e:
                print(f'{s}: window FAIL {e}')
            _time.sleep(1.2)
        rows = sorted(set(rows))
        if rows:
            out[s] = rows
            print(f'{s}: {len(rows)} bars')
    pickle.dump(out, open(cache, 'wb'))
    return out

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='V7.5 vs V8.0 bar-level benchmark')
    ap.add_argument('--cache', default='/tmp/pine_bench_bars.pkl')
    ap.add_argument('--fetch', action='store_true',
                    help='refetch 1m bars (2026-08-05..08-19 windows)')
    args = ap.parse_args()
    if args.fetch:
        w1 = (int(dt.datetime(2026,8,5,4,0,tzinfo=ET).timestamp()),
              int(dt.datetime(2026,8,12,4,0,tzinfo=ET).timestamp()))
        w2 = (int(dt.datetime(2026,8,12,4,0,tzinfo=ET).timestamp()),
              int(dt.datetime(2026,8,19,20,0,tzinfo=ET).timestamp()))
        B = fetch_all(args.cache, [w1, w2])
    else:
        B = pickle.load(open(args.cache, 'rb'))
    H1 = Cfg('V8exec+V75size', sameBarStop=True, entryTimeOK=True,
             risk=200.0, maxPos=25000.0, retestBand=True)
    H2 = Cfg('V75exec+V8size', sameBarStop=False, entryTimeOK=False,
             risk=20.0, maxPos=2000.0, retestBand=False)
    # V8.1 executes identically to V8.0 (its changes are display-layer).
    # What V8.1 ADDS is the ghost layer: the same pattern engine shown
    # outside the clock window with no order. GHOST opens the window to
    # 04:00-20:00; its trades entered outside 07:00-11:30 are exactly what
    # the SEEN markers + PLAN row would have displayed (hypothetically
    # traded by the same rules, which the real script never would).
    V81G = Cfg('V8.1-GHOST', sameBarStop=True, entryTimeOK=True,
               risk=20.0, maxPos=2000.0, retestBand=True,
               winStart=4*60, winEnd=20*60)
    nbars = sum(len(v) for v in B.values())
    print(f'{len(B)} symbols · {nbars} 1m bars')
    V82 = Cfg('V8.2-lateJoin', sameBarStop=True, entryTimeOK=True,
              risk=20.0, maxPos=2000.0, retestBand=True, lateJoin=True)
    PINE = Cfg('pine macd>0+hist', sameBarStop=True, entryTimeOK=True,
               risk=40.0, maxPos=2000.0, retestBand=True, macdMode='pine')
    SRC = Cfg('sourced macd>0', sameBarStop=True, entryTimeOK=True,
              risk=40.0, maxPos=2000.0, retestBand=True, macdMode='sourced')
    PINE_NW = Cfg('pine no-window', sameBarStop=True, entryTimeOK=True,
                  risk=40.0, maxPos=2000.0, retestBand=True, macdMode='pine',
                  winStart=4*60, winEnd=20*60)
    SRC_NW = Cfg('sourced no-window', sameBarStop=True, entryTimeOK=True,
                 risk=40.0, maxPos=2000.0, retestBand=True, macdMode='sourced',
                 winStart=4*60, winEnd=20*60)
    caps = [('cap 3% (pine)', 3.0), ('cap 5% (their rpct5)', 5.0),
            ('cap 8%', 8.0), ('sans cap', None)]
    CAPCFG = [Cfg(n, sameBarStop=True, entryTimeOK=True, risk=40.0,
                  maxPos=2000.0, retestBand=True, macdMode='pine', maxStopPct=c)
              for n, c in caps]
    for cfg in (PINE, SRC, PINE_NW, SRC_NW, *CAPCFG):
        res = [run(s, bars, cfg) for s, bars in B.items()]
        print(f'{cfg.name:15s}', agg(res))
    print()
    print('--- V8.2 late-join: trades added vs V8.0 ---')
    r80={( t['sym'],str(t['day']),t['t_in']) for res in [[run(s,b,V80) for s,b in B.items()]] for r in res for t in r['trades']}
    for r in (run(s,b,V82) for s,b in B.items()):
        for t in r['trades']:
            if (t['sym'],str(t['day']),t['t_in']) not in r80:
                print(f"  {t['sym']:5s} {t['day']} {t['t_in']//60:02d}:{t['t_in']%60:02d} {t['kind']:12s} r={t['r']:+.2f}")
    print()
    print('--- V8.1 ghost layer: entries by clock bucket (GHOST run) ---')
    res = [run(s, bars, V81G) for s, bars in B.items()]
    T = [t for r in res for t in r['trades']]
    def bucket(m):
        return ('PRE 04:00-07:00' if m < 420 else
                'WINDOW 07:00-11:30' if m < 690 else
                'LATE 11:30-16:00' if m < 960 else 'AH 16:00-20:00')
    from collections import defaultdict
    agg2 = defaultdict(lambda: [0, 0.0, 0])
    for t in T:
        b = bucket(t['t_in'])
        agg2[b][0] += 1; agg2[b][1] += t['r']; agg2[b][2] += t['r'] > 0
    for b in ('PRE 04:00-07:00', 'WINDOW 07:00-11:30', 'LATE 11:30-16:00', 'AH 16:00-20:00'):
        n, sr, w = agg2[b]
        print(f'  {b:20s} {n:3d} trades · {w}W/{n-w}L · sumR {sr:+.2f}')
    print('  ghost-only trades (outside 07:00-11:30):')
    for t in sorted(T, key=lambda t: (str(t['day']), t['t_in'])):
        if not (420 <= t['t_in'] < 690):
            print(f"    {t['sym']:5s} {t['day']} {t['t_in']//60:02d}:{t['t_in']%60:02d} "
                  f"{t['kind']:12s} r={t['r']:+.2f}")
    for cfg in (V75, V80):
        print(f'--- {cfg.name} trades ---')
        for r in (run(s, bars, cfg) for s, bars in B.items()):
            for t in r['trades']:
                print(f"  {t['sym']:5s} {t['day']} {t['kind']:12s} "
                      f"r={t['r']:+.2f} cash={t['cash']:+9.2f}")
