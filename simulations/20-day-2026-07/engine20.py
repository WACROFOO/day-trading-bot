#!/usr/bin/env python3
"""The single-day engine, generalised over date and trade limit.

Same forward-only contract as sim.py: at minute T the engine has seen bars up
to T and nothing else. Symbols are interleaved in real time, so a trader with
several names on screen takes whichever sets up first and the trade counter
then removes the rest of the day.

Account state (P&L, trade count, loss streak) is per day. Nothing carries over,
which matches the playbook - each session starts from the same limits.
"""
import datetime as dt

from sim import (Indicators, PullbackTracker, evaluate, RISK_PER_TRADE,
                 MAX_DAILY_LOSS, PROFIT_GOAL, STOP_MAX, SLIPPAGE,
                 BUYING_POWER, LIQUIDITY_CAP, TRADE_START, HARD_STOP,
                 PRIME_END, MAX_LOSSES_STREAK)

ET = dt.timezone(dt.timedelta(hours=-4))


def run_day(day, watch, bars_by_sym, max_trades, log=None):
    """bars_by_sym: {sym: {'pre': [bar], 'session': [bar]}} with dt/o/h/l/c/v."""
    log = log if log is not None else []
    state = {}
    for sym in watch:
        d = bars_by_sym.get(sym)
        if not d or not d['session']:
            continue
        ind = Indicators()
        for b in d['pre']:
            ind.update(b, in_session=False)
        state[sym] = dict(ind=ind, tracker=PullbackTracker(), prev=None,
                          flipped=[],
                          bars={b['dt'].strftime('%H:%M'): b for b in d['session']})
    if not state:
        return dict(day=str(day), pnl=0.0, trades=[], setups=0, passes=0,
                    halted='no data', rejects={})

    minutes = []
    t = dt.datetime(day.year, day.month, day.day, 9, 30, tzinfo=ET)
    while t.time() < HARD_STOP:
        minutes.append(t.strftime('%H:%M'))
        t += dt.timedelta(minutes=1)

    position, trades, day_pnl, losses = None, [], 0.0, 0
    halted, setups, passes, rejects = None, 0, 0, {}

    for hm in minutes:
        tm = dt.time(int(hm[:2]), int(hm[3:]))

        if position:
            s = state[position['sym']]
            bar = s['bars'].get(hm)
            if bar:
                ind, p = s['ind'], position
                reason = fill = None
                if bar['l'] <= p['stop']:
                    fill, reason = p['stop'], 'stop hit'
                elif p['scaled'] == 0 and bar['h'] >= p['t1']:
                    q = p['shares'] // 2
                    p['pnl'] += (p['t1'] - p['entry']) * q
                    p['shares'] -= q
                    p['scaled'], p['stop'] = 1, p['entry']
                    log.append(f'{hm} {p["sym"]}: +2R, sold {q}, stop to breakeven')
                elif p['scaled'] == 1 and bar['h'] >= p['t2']:
                    q = p['shares'] // 2
                    p['pnl'] += (p['t2'] - p['entry']) * q
                    p['shares'] -= q
                    p['scaled'] = 2
                    log.append(f'{hm} {p["sym"]}: +3R, sold {q}, trailing')

                if reason is None and p['shares'] > 0:
                    broke = []
                    if ind.macd_hist is not None and ind.macd_hist < 0:
                        broke.append('MACD negative')
                    if ind.vwap and bar['c'] < ind.vwap:
                        broke.append('lost VWAP')
                    if s['prev'] and bar['l'] < s['prev']['l'] and bar['c'] < bar['o']:
                        broke.append('new low')
                    if broke:
                        fill, reason = bar['c'], ', '.join(broke)

                if reason:
                    p['pnl'] += (fill - p['entry']) * p['shares']
                    p['exit'], p['exit_time'], p['reason'] = fill, hm, reason
                    day_pnl += p['pnl']
                    losses = losses + 1 if p['pnl'] < 0 else 0
                    trades.append(p)
                    log.append(f'{hm} {p["sym"]}: OUT @ {fill:.2f} ({reason}) '
                               f'${p["pnl"]:+.0f} | day ${day_pnl:+.0f}')
                    position = None

        if halted is None:
            if day_pnl <= -MAX_DAILY_LOSS:
                halted = 'max daily loss'
            elif day_pnl >= PROFIT_GOAL:
                halted = 'profit goal'
            elif losses >= MAX_LOSSES_STREAK:
                halted = '3 losses in a row'
            elif len(trades) >= max_trades:
                halted = f'{max_trades} trades taken'
            if halted:
                log.append(f'{hm} --- STOP: {halted} ---')

        for sym in list(state):
            s = state[sym]
            bar = s['bars'].get(hm)
            if not bar:
                continue
            ind, tr = s['ind'], s['tracker']
            ind.update(bar, in_session=True)
            pb = tr.update(bar, s['prev'], ind)

            if pb and position is None and halted is None and TRADE_START <= tm < HARD_STOP:
                setups += 1
                ok, checks = evaluate(pb, bar, ind, s['flipped'])
                entry = min(pb['trigger_level'] + SLIPPAGE, bar['h'])
                stop = pb['low']
                risk_ps = entry - stop
                sized_ok = 0 < risk_ps <= STOP_MAX
                for k, (passed, _) in checks.items():
                    if not passed:
                        rejects[k] = rejects.get(k, 0) + 1
                if not sized_ok:
                    rejects['stop > $0.20'] = rejects.get('stop > $0.20', 0) + 1

                if ok and sized_ok:
                    passes += 1
                    shares = int(RISK_PER_TRADE / risk_ps)
                    final = max(0, min(shares, int(BUYING_POWER / entry),
                                       int(bar['v'] * LIQUIDITY_CAP)))
                    if final <= 0:
                        rejects['size rounds to 0'] = rejects.get('size rounds to 0', 0) + 1
                    else:
                        position = dict(sym=sym, entry=entry, stop=stop,
                                        risk_ps=risk_ps, shares=final, full=final,
                                        pnl=0.0, scaled=0, entry_time=hm,
                                        t1=entry + 2 * risk_ps, t2=entry + 3 * risk_ps,
                                        window='prime' if tm < PRIME_END else 'late')
                        log.append(f'{hm} {sym}: BUY {final} @ {entry:.2f} '
                                   f'stop {stop:.2f} (${risk_ps:.2f}/sh)')
            s['prev'] = bar
            if ind.session_high and bar['h'] >= ind.session_high:
                s['flipped'] = (s['flipped'] + [round(bar['h'], 2)])[-6:]

    if position:
        p = position
        last = sorted(state[p['sym']]['bars'].items())[-1][1]
        p['pnl'] += (last['c'] - p['entry']) * p['shares']
        p['exit'], p['exit_time'], p['reason'] = last['c'], '11:29', 'hard stop'
        day_pnl += p['pnl']
        trades.append(p)

    return dict(day=str(day), pnl=round(day_pnl, 2), trades=trades,
                setups=setups, passes=passes, halted=halted, rejects=rejects,
                watch=list(state))
