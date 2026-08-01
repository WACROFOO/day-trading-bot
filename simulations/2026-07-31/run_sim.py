#!/usr/bin/env python3
"""One trader, one screen, Friday 2026-07-31. Minute by minute, no peeking.

Symbols are interleaved in real time rather than simulated one after another,
because a trader with four names on screen takes whichever sets up FIRST - and
the 2-trade limit then removes the rest of the day. Running symbols
independently would quietly hand the account four chances instead of two.
"""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim import (Indicators, PullbackTracker, evaluate, ACCOUNT, RISK_PER_TRADE,
                 MAX_DAILY_LOSS, PROFIT_GOAL, MAX_TRADES, STOP_MAX, SLIPPAGE,
                 BUYING_POWER, LIQUIDITY_CAP, TRADE_START, HARD_STOP,
                 PRIME_END, MAX_LOSSES_STREAK)

OUT = os.path.dirname(os.path.abspath(__file__))
ET = dt.timezone(dt.timedelta(hours=-4))


def parse(rec):
    d = dt.datetime.fromisoformat(rec['iso'])
    return dict(dt=d, o=rec['o'], h=rec['h'], l=rec['l'], c=rec['c'],
                v=rec['v'] or 0)


def main(watch):
    raw = json.load(open(os.path.join(OUT, 'friday_bars.json')))
    log = []
    state = {}
    for sym in watch:
        d = raw[sym]
        ind = Indicators()
        for b in d['pre']:
            ind.update(parse(b), in_session=False)
        state[sym] = dict(ind=ind, tracker=PullbackTracker(), prev=None,
                          flipped=[],
                          bars={parse(b)['dt'].strftime('%H:%M'): parse(b)
                                for b in d['session']})

    minutes = []
    t = dt.datetime(2026, 7, 31, 9, 30, tzinfo=ET)
    while t.time() < HARD_STOP:
        minutes.append(t.strftime('%H:%M'))
        t += dt.timedelta(minutes=1)

    position, trades, day_pnl, losses = None, [], 0.0, 0
    halted_reason = None

    for hm in minutes:
        tm = dt.time(int(hm[:2]), int(hm[3:]))

        # ---------- manage the open position first ----------
        if position:
            s = state[position['sym']]
            bar = s['bars'].get(hm)
            if bar:
                ind = s['ind']
                p = position
                exit_reason = fill = None
                if bar['l'] <= p['stop']:
                    fill, exit_reason = p['stop'], f"stop {p['stop']:.2f} hit"
                elif p['scaled'] == 0 and bar['h'] >= p['t1']:
                    q = p['shares'] // 2
                    p['pnl'] += (p['t1'] - p['entry']) * q
                    p['shares'] -= q
                    p['scaled'] = 1
                    p['stop'] = p['entry']
                    log.append(f'{hm}  {p["sym"]}: +2R hit {p["t1"]:.2f} -> sold '
                               f'{q} (half), stop to breakeven {p["entry"]:.2f}')
                elif p['scaled'] == 1 and bar['h'] >= p['t2']:
                    q = p['shares'] // 2
                    p['pnl'] += (p['t2'] - p['entry']) * q
                    p['shares'] -= q
                    p['scaled'] = 2
                    log.append(f'{hm}  {p["sym"]}: +3R hit {p["t2"]:.2f} -> sold '
                               f'{q}, trailing the rest')

                if exit_reason is None and p['shares'] > 0:
                    broke = []
                    if ind.macd_hist is not None and ind.macd_hist < 0:
                        broke.append('MACD negative')
                    if ind.vwap and bar['c'] < ind.vwap:
                        broke.append('lost VWAP')
                    if s['prev'] and bar['l'] < s['prev']['l'] and bar['c'] < bar['o']:
                        broke.append('candle made a new low')
                    if broke:
                        fill, exit_reason = bar['c'], ', '.join(broke)

                if exit_reason:
                    p['pnl'] += (fill - p['entry']) * p['shares']
                    p['exit'], p['exit_time'], p['reason'] = fill, hm, exit_reason
                    day_pnl += p['pnl']
                    losses = losses + 1 if p['pnl'] < 0 else 0
                    trades.append(p)
                    log.append(f'{hm}  {p["sym"]}: OUT {p["shares"]} @ {fill:.2f} '
                               f'({exit_reason}).  Trade P&L ${p["pnl"]:+.0f}  '
                               f'| day ${day_pnl:+.0f}')
                    position = None

        # ---------- day-stop rules, checked after every close ----------
        if halted_reason is None:
            if day_pnl <= -MAX_DAILY_LOSS:
                halted_reason = f'max daily loss hit (${day_pnl:+.0f})'
            elif day_pnl >= PROFIT_GOAL:
                halted_reason = f'profit goal hit (${day_pnl:+.0f})'
            elif losses >= MAX_LOSSES_STREAK:
                halted_reason = '3 losses in a row'
            elif len(trades) >= MAX_TRADES:
                halted_reason = f'{MAX_TRADES} trades taken'
            if halted_reason:
                log.append(f'{hm}  --- STOP FOR THE DAY: {halted_reason} ---')

        # ---------- advance every symbol, look for setups ----------
        for sym in watch:
            s = state[sym]
            bar = s['bars'].get(hm)
            if not bar:
                continue
            ind, tr = s['ind'], s['tracker']
            ind.update(bar, in_session=True)
            pb = tr.update(bar, s['prev'], ind)

            if (pb and position is None and halted_reason is None
                    and TRADE_START <= tm < HARD_STOP):
                ok, checks = evaluate(pb, bar, ind, s['flipped'])
                entry = min(pb['trigger_level'] + SLIPPAGE, bar['h'])
                stop = pb['low']
                risk_ps = entry - stop
                sized_ok = 0 < risk_ps <= STOP_MAX
                failed = [k for k, (p_, _) in checks.items() if not p_]
                if not sized_ok:
                    failed.append(f'stop ${risk_ps:.2f} > ${STOP_MAX:.2f}')
                log.append(
                    f'{hm}  {sym}: pullback #{pb["index"]} low {stop:.2f}, '
                    f'trigger {pb["trigger_level"]:.2f} -> '
                    + ('ALL CHECKS PASS' if ok and sized_ok
                       else 'skip: ' + '; '.join(failed[:3])))
                if ok and sized_ok:
                    shares = int(RISK_PER_TRADE / risk_ps)
                    cap_bp, cap_liq = int(BUYING_POWER / entry), int(bar['v'] * LIQUIDITY_CAP)
                    final = max(0, min(shares, cap_bp, cap_liq))
                    if final <= 0:
                        log.append(f'{hm}  {sym}: size rounds to 0, skipped')
                    else:
                        cap = ('liquidity' if final == cap_liq and final < shares
                               else 'buying power' if final == cap_bp and final < shares
                               else None)
                        position = dict(sym=sym, entry=entry, stop=stop,
                                        init_stop=stop, risk_ps=risk_ps,
                                        shares=final, full=final, pnl=0.0,
                                        scaled=0, entry_time=hm,
                                        t1=entry + 2 * risk_ps,
                                        t2=entry + 3 * risk_ps,
                                        checks=checks, cap=cap,
                                        window='prime' if tm < PRIME_END else 'late')
                        log.append(
                            f'{hm}  {sym}: >>> BUY {final} @ {entry:.2f}  '
                            f'stop {stop:.2f} (${risk_ps:.2f}/sh, risk '
                            f'${risk_ps * final:.0f})  T1 {position["t1"]:.2f}'
                            + (f'  [size capped by {cap}]' if cap else ''))
            s['prev'] = bar
            if ind.session_high and bar['h'] >= ind.session_high:
                s['flipped'] = (s['flipped'] + [round(bar['h'], 2)])[-6:]

    if position:
        p = position
        last = [b for hm2, b in sorted(state[p['sym']]['bars'].items())
                if hm2 < HARD_STOP.strftime('%H:%M')][-1]
        p['pnl'] += (last['c'] - p['entry']) * p['shares']
        p['exit'], p['exit_time'], p['reason'] = last['c'], '11:29', 'hard stop 11:30'
        day_pnl += p['pnl']
        trades.append(p)
        log.append(f'11:29  {p["sym"]}: flat at the hard stop. '
                   f'Trade P&L ${p["pnl"]:+.0f}')

    json.dump(dict(log=log, day_pnl=day_pnl,
                   trades=[{k: v for k, v in t.items() if k != 'checks'}
                           for t in trades],
                   halted=halted_reason),
              open(os.path.join(OUT, 'sim_result.json'), 'w'), indent=1, default=str)
    print('\n'.join(log))
    print(f'\n=== DAY P&L ${day_pnl:+.2f} on ${ACCOUNT:,.0f} '
          f'({day_pnl / ACCOUNT * 100:+.2f}%) | trades {len(trades)} ===')


if __name__ == '__main__':
    main(sys.argv[1:] or ['FCUV', 'CUPR', 'TCX', 'JFB'])
