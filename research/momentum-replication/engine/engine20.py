#!/usr/bin/env python3
"""The single-day engine, generalised over date and trade limit.

Same forward-only contract as sim.py: at minute T the engine has seen bars up
to T and nothing else. Symbols are interleaved in real time, so a trader with
several names on screen takes whichever sets up first and the trade counter
then removes the rest of the day.

Account state (P&L, trade count, loss streak) is per day. Nothing carries over,
which matches the playbook - each session starts from the same limits.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import datetime as dt

import sim
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
                          flipped=[], hod_prev=None,
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
                    log.append(f'{hm} {p["sym"]}: T1 {p["t1"]:.2f} hit, sold {q}, stop to breakeven')
                elif p['scaled'] == 1 and bar['h'] >= p['t2']:
                    q = p['shares'] // 2
                    p['pnl'] += (p['t2'] - p['entry']) * q
                    p['shares'] -= q
                    p['scaled'] = 2
                    log.append(f'{hm} {p["sym"]}: T2 {p["t2"]:.2f} hit, sold {q}, trailing')

                if reason is None and p['shares'] > 0:
                    broke = []
                    if ind.macd_hist is not None and ind.macd_hist < 0:
                        broke.append('MACD negative')
                    if ind.vwap and bar['c'] < ind.vwap:
                        broke.append('lost VWAP')
                    # "first candle to make a new low" means a new low BELOW THE
                    # FLAG (Xdw5azEqs6o), i.e. below the pullback structure -
                    # which is the stop, already checked above. Firing it on any
                    # bar with a lower low than the one before it exits on
                    # ordinary noise: it closed 5 of 14 trades inside 4 minutes.
                    #
                    # The remaining Exit-3 signal that IS bar-local is the big
                    # red candle on heavy volume.
                    rng = bar['h'] - bar['l']
                    if (bar['c'] < bar['o'] and rng > 1.5 * p['avg_rng']
                            and bar['v'] > p['impulse_v']):
                        broke.append('big red candle on heavy volume')
                    if p['scaled'] >= 1 and s['prev'] and bar['c'] < s['prev']['l']:
                        broke.append('trailing stop')
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
            s['hod_prev'] = ind.session_high        # HOD excluding this bar
            ind.update(bar, in_session=True)
            pb = tr.update(bar, s['prev'], ind)

            if pb and position is None and halted is None and TRADE_START <= tm < HARD_STOP:
                setups += 1
                ok, checks = evaluate(pb, bar, ind, s['flipped'])
                # PARAMETERS.md sec.12 step 3: score the pillars instead of
                # requiring all of them, and check whether the gradient is
                # monotonic. Requiring 9 independent booleans simultaneously
                # gates out ~9,999 of every 10,000 setups; a human applies them
                # approximately and together.
                # Only the conditions PARAMETERS.md section 3 actually lists
                # gate the trade. The rest are observations carried alongside.
                gating = {k: v for k, v in checks.items()
                          if k in sim.GATE_CONDITIONS}
                score = sum(1 for v in gating.values() if v[0])
                ok = score >= sim.MIN_PILLARS
                entry = min(pb['trigger_level'] + SLIPPAGE, bar['h'])
                stop = pb['low']
                risk_ps = entry - stop
                # PARAMETERS.md:161 - stop_min_distance >= spread width.
                # Never implemented before, and it is the rule that PLRZ's
                # 2-cent stop on a $15 stock should have failed. No quote data
                # here, so spread is estimated from the bars themselves: the
                # 25th-percentile 1-minute range is about as tight as this name
                # trades, which is a floor on what the spread can be.
                rngs = sorted(x['h'] - x['l'] for x in ind.bars[-30:]
                              if x['h'] > x['l'])
                spread_est = rngs[len(rngs) // 4] if rngs else 0.01
                # PLAYBOOK.md:166 - "cut your size OR skip the trade". The
                # sizing formula already cuts size when the stop is wider, so a
                # wide stop is not a rejection; it is simply fewer shares. Only
                # a stop that is absurd relative to price, or tighter than the
                # spread, is a genuine skip.
                # The only per-share stop bound in the corpus is
                # stop_max_distance <= $0.20 (PARAMETERS.md:159), and
                # PLAYBOOK.md:166 says a wider stop is sized down, not skipped -
                # which the sizing formula already does. A 6%-of-price ceiling
                # was invented here; the only 6% in the source is the DAILY
                # ACCOUNT loss limit (PLAYBOOK.md:56), a different quantity.
                # Being relative it also cut both ways: on a $2.44 stock it
                # skipped stops past $0.15, tighter than the $0.20 allowed.
                # The one genuine floor stays: a stop cannot be tighter than
                # the spread (PARAMETERS.md:161).
                sized_ok = spread_est <= risk_ps
                wide = risk_ps > STOP_MAX

                # The first target is a retest of the high of day (n=5 videos),
                # or a measured move equal to the impulse height when entry is
                # already at the highs. 2:1 is a FILTER on that target, not the
                # target itself - using entry+2R as the target caps every
                # winner at exactly +1.00R once the stop moves to breakeven.
                hod = s['hod_prev']
                imp = pb['impulse']
                pole = (max(x['h'] for x in imp) - min(x['l'] for x in imp)) if imp else 0
                # FIRST target, so the NEAREST structural objective above the
                # entry - not the furthest. The documented target is a "retest
                # of the high of day" (5 videos) or "a measured move equal to
                # the pole height" (small-cap-momentum-bull-flag.md), typically
                # 15-20 cents away.
                #
                # Taking max() of those made the target the high of day even
                # after the stock had collapsed away from it. On CUPR
                # 2026-07-31 every trade after 10:55 carried a $5.77 target
                # while price sat in the $2.80s: unreachable, yet it satisfied
                # the 2:1 filter *trivially because it was so far away*. The
                # reward:risk check was being passed by an impossible target.
                objectives = [x for x in (hod, pb['low'] + pole)
                              if x and x > entry]
                t1 = min(objectives) if objectives else 0
                rr_ok = (t1 - entry) >= 2 * risk_ps
                for k, (passed, _) in checks.items():
                    if not passed:
                        tag = k if k in sim.GATE_CONDITIONS else f'{k} (not gating)'
                        rejects[tag] = rejects.get(tag, 0) + 1
                if not sized_ok:
                    key = 'stop tighter than spread'
                    rejects[key] = rejects.get(key, 0) + 1
                if not rr_ok:
                    rejects['target < 2:1'] = rejects.get('target < 2:1', 0) + 1

                if ok and sized_ok and rr_ok:
                    passes += 1
                    shares = int(RISK_PER_TRADE / risk_ps)
                    final = max(0, min(shares, int(BUYING_POWER / entry),
                                       int(bar['v'] * LIQUIDITY_CAP)))
                    if final <= 0:
                        rejects['size rounds to 0'] = rejects.get('size rounds to 0', 0) + 1
                    else:
                        recent = ind.bars[-20:]
                        avg_rng = (sum(x['h'] - x['l'] for x in recent)
                                   / max(1, len(recent)))
                        position = dict(sym=sym, entry=entry, stop=stop,
                                        risk_ps=risk_ps, shares=final, full=final,
                                        pnl=0.0, scaled=0, entry_time=hm,
                                        t1=t1, t2=entry + 2 * (t1 - entry),
                                        avg_rng=avg_rng, pb_bars=len(pb['bars']),
                                        spread_est=round(spread_est, 4),
                                        impulse_v=max((x['v'] for x in imp),
                                                      default=0),
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
