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

# min_reward_risk (PARAMETERS.md:177, n=37) as a PRE-ENTRY VETO: skip any setup
# whose nearest structural objective sits closer than 2x the stop distance.
#
# That reading is doubtful. Every citation in the corpus is retrospective and
# aggregate - "~2:1 profit-to-loss ratio achieved", "profit-loss ratio this
# week", "$500 average winners, 61% accuracy" - and the one stated as a rule
# ties it to accuracy over a sample: "Trade 2:1 minimum. If accuracy around
# 65%, this ratio ensures profitability" (4t3GDiAXW18 [40:07]). PARAMETERS.md
# section 9 uses it the same way, as avg_win/avg_loss inside an expectancy
# formula. A ratio of averages is produced by the EXIT plan - scale at target
# 1, trail the rest - not by refusing entries.
#
# It also collides with the setup it is filtering: a micro-pullback enters just
# under the high of day, so the nearest objective is a few cents away while the
# stop is the depth of the dip. Requiring 2x of that rejects the entry the
# strategy is built on. It is the single largest rejection reason in the
# 17-day run.
#
# Measured, the veto is anti-correlated with the gate it sits behind. Across
# 406 setups the median distance to target 1 is $0.160/share - the middle of
# the documented `target_typical` $0.15-0.20 - and among setups passing all
# eight gate conditions the median is 1.14R, with only 26% reaching 2R. The
# gate selects names pushed up against their own high of day, which is exactly
# where the nearest objective is closest. The stronger the setup by the
# documented criteria, the more certainly the veto killed it.
#
# So it is OFF by default. 2:1 is measured as a realised ratio over trades
# (diagnostics/trades.py prints it), which is how every citation states it.
# RR_FILTER=1 restores the veto for comparison.
RR_FILTER = os.environ.get('RR_FILTER', '0') != '0'


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
                rr_ok = (not RR_FILTER) or (t1 - entry) >= 2 * risk_ps
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
                    # a pullback past the second is taken at reduced size rather
                    # than skipped - reports/2026-08-streams-roundup.md sec.3
                    if pb['index'] > sim.MAX_PULLBACK_INDEX:
                        shares = int(shares * sim.LATE_PULLBACK_SIZE)
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
        # A position still open when the trading window closes is flattened at
        # the cutoff. This took sorted(bars)[-1] - the LAST BAR OF THE SESSION,
        # 15:59 - and stamped it '11:29', so the exit price came from four and a
        # half hours after the engine was allowed to look. It was not a small
        # effect: EHGO 2026-07-13 was flat at 11:30 and booked -6.38R against
        # the 15:59 close, and ADVB 2026-07-22, the largest winner in the study
        # at +4.17R, was the same path in the favourable direction.
        p = position
        cutoff = max((hm for hm in state[p['sym']]['bars']
                      if dt.time(int(hm[:2]), int(hm[3:])) < HARD_STOP),
                     default=None)
        if cutoff is not None:
            last = state[p['sym']]['bars'][cutoff]
            # never worse than the resting stop - it would have filled first
            fill = max(last['c'], p['stop'])
            p['pnl'] += (fill - p['entry']) * p['shares']
            p['exit'], p['exit_time'], p['reason'] = fill, cutoff, 'window closed'
            day_pnl += p['pnl']
            trades.append(p)

    return dict(day=str(day), pnl=round(day_pnl, 2), trades=trades,
                setups=setups, passes=passes, halted=halted, rejects=rejects,
                watch=list(state))
