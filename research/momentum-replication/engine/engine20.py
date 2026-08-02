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

# --- what counts as "a trade" -----------------------------------------------
# The engine took one entry per name, scaled out, and burned one of the day's
# trade slots. The live streams show a different unit of activity: he works a
# POSITION, entering and exiting the same name repeatedly through a move.
#
#   "Taking little profit and then looking to add back. Flat. Watching for
#    another dip."                                        0uunIYE_wVY [15:19]
#   "Add back 67. Now looking for the break of 70. Buying the dip off the flat
#    bottom, 56. Going flat 51 for now. Add back at 51, bought the dip."
#                                                         1NZS5CqCnj8 [42:13]
#   "in phase five, we're also scaling into trades. Starter position, half
#    size, full size, then scaling out."                   -KcmoPm_skg [57:50]
#
# "Add back" and "scaling in" occur 328 times across 138 of 289 streams. So
# `max_trades` counts the wrong unit: PARAMETERS.md's funnel ends "3-5
# watchlist -> 1-2 trades", which is 1-2 NAMES, while the engine spent a slot
# on every entry.
#
# RE_ENTRY=0 restores one entry per name.
# reports/2026-08-streams-roundup.md section 2.
RE_ENTRY = os.environ.get('RE_ENTRY', '1') != '0'
# Cap per name. He runs well past this on a strong mover; the cap exists so a
# single symbol cannot consume the whole session through a detector quirk, not
# because the corpus states a limit.
MAX_ENTRIES_PER_NAME = int(os.environ.get('MAX_ENTRIES_PER_NAME', 4))

# --- scaling IN --------------------------------------------------------------
# The engine entered once, at full size, and never added. That is the real gap
# the streams expose - re-entry after going flat already worked (ADVB 07-22
# 10:24 and 11:22 are two entries on one name), but BUILDING a position did not.
#
#   "starter position, half size, full size, then scaling out"  -KcmoPm_skg [57:50]
#   "watch add over 55" / "going to add for the break of 1445" / "add 1,000
#    shares over 515"          - 341 such phrasings across the stream corpus
#
# PARAMETERS.md:209 already carries the ladder - `size_ladder 100 -> 200 -> 400
# -> 800`, n=125. It was never implemented.
#
# The smallest model the evidence supports: open at half the risk-based size,
# add the rest on the next trigger that still clears the gate, and never let
# total risk exceed RISK_PER_TRADE. The stop may only move UP
# (PARAMETERS.md:165, widen_stop_allowed == false), so an add whose structure
# sits BELOW the current stop is refused rather than taken on a loosened stop.
#
# Adds stop once the first scale-out has happened: past that he is reducing,
# and re-entering later is the separate path above.
#
# DEFAULT OFF, and the reason is the result. Over 17 sessions this fires ONE
# add. Median hold on these positions is 2 minutes and only 5 of 13 last 3
# minutes or more, so there is no room for a second pullback to form inside a
# position that is already stopped out. Left on, it does nothing but halve
# every position: -$588.90 -> -$299.58 with expectancy going -0.26R -> -0.33R,
# which is smaller losses rather than better trading.
#
# That is not evidence against scaling in. It is the same finding as everything
# else in reports/2026-08-streams-roundup.md: his positions survive long enough
# to build, ours do not, because the entry is late. Turn this on once the entry
# is fixed - the model is here and tested, waiting on the trigger.
SCALE_IN = os.environ.get('SCALE_IN', '0') != '0'
STARTER_FRACTION = float(os.environ.get('STARTER_FRACTION', 0.5))


def _spread(ind):
    """Cheapest plausible spread: the 25th-percentile 1-minute range.

    The same estimate the entry path uses. Factored out because the add path
    needs it too - see 'add: stop would sit inside the spread'.
    """
    rngs = sorted(x['h'] - x['l'] for x in ind.bars[-30:] if x['h'] > x['l'])
    return rngs[len(rngs) // 4] if rngs else 0.01


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
    entries_by_sym = {}          # symbol -> entries taken; keys are the names
                                 # traded, which is what max_trades now counts

    for hm in minutes:
        tm = dt.time(int(hm[:2]), int(hm[3:]))

        if position:
            s = state[position['sym']]
            bar = s['bars'].get(hm)
            if bar:
                ind, p = s['ind'], position
                reason = fill = None
                if bar['l'] <= p['stop']:
                    # if the bar OPENED below the stop, the resting order fills
                    # near that open, not at the stop price - taking the stop
                    # price on a gap-through understates the loss
                    fill = min(p['stop'], bar['o'])
                    reason = 'stop hit'
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
            elif len(entries_by_sym if RE_ENTRY else trades) >= max_trades:
                halted = (f'{max_trades} names traded' if RE_ENTRY
                          else f'{max_trades} trades taken')
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

            # A name already worked today may be re-entered, but only up to its
            # own cap; a NEW name is refused once the day's slots are spent.
            # Expressed as a flag rather than a `continue`, because the tail of
            # this loop still has to advance s['prev'] and s['flipped'] - the
            # flipped levels feed support confluence, and skipping them would
            # silently corrupt the gate for the rest of the session.
            allowed = True
            if RE_ENTRY and pb and position is None and halted is None:
                n_taken = entries_by_sym.get(sym, 0)
                if n_taken >= MAX_ENTRIES_PER_NAME:
                    allowed = False
                    rejects['name at its entry cap'] = rejects.get('name at its entry cap', 0) + 1
                elif n_taken == 0 and len(entries_by_sym) >= max_trades:
                    allowed = False
                    rejects['day at its name limit'] = rejects.get('day at its name limit', 0) + 1

            # --- add to a position already open in this name ----------------
            if (SCALE_IN and pb and position is not None
                    and position['sym'] == sym and position['scaled'] == 0
                    and position['shares'] < position['target_size']
                    and halted is None and TRADE_START <= tm < HARD_STOP):
                ok_a, checks_a = evaluate(pb, bar, ind, s['flipped'])
                gating_a = {k: v for k, v in checks_a.items()
                            if k in sim.GATE_CONDITIONS}
                add_px = min(pb['trigger_level'] + SLIPPAGE, bar['h'])
                new_stop = pb['low']
                p_ = position
                if not all(v[0] for v in gating_a.values()):
                    rejects['add: gate no longer clear'] = rejects.get('add: gate no longer clear', 0) + 1
                elif new_stop < p_['stop']:
                    # taking it would mean widening the stop on the whole
                    # position, which PARAMETERS.md:165 forbids outright
                    rejects['add: would widen the stop'] = rejects.get('add: would widen the stop', 0) + 1
                elif add_px - new_stop < _spread(ind):
                    # stop_min_distance >= spread width (PARAMETERS.md:163) is
                    # tested on a fresh entry but was not on an add, and an add
                    # ratchets the stop up toward the average price. EHGO
                    # 2026-07-13 11:29 came out with $0.002/share of room -
                    # inside the spread, so noise alone closes it, and the R
                    # denominator goes to zero with it.
                    rejects['add: stop would sit inside the spread'] = rejects.get('add: stop would sit inside the spread', 0) + 1
                else:
                    want = p_['target_size'] - p_['shares']
                    qty = max(0, min(want, int(bar['v'] * LIQUIDITY_CAP),
                                     int((BUYING_POWER - p_['shares'] * p_['entry'])
                                         / add_px)))
                    # total risk on the combined position, at the new stop
                    if qty > 0:
                        avg = ((p_['entry'] * p_['shares'] + add_px * qty)
                               / (p_['shares'] + qty))
                        risk_total = (avg - new_stop) * (p_['shares'] + qty)
                        while qty > 0 and risk_total > RISK_PER_TRADE:
                            qty -= max(1, qty // 20)
                            if qty <= 0:
                                break
                            avg = ((p_['entry'] * p_['shares'] + add_px * qty)
                                   / (p_['shares'] + qty))
                            risk_total = (avg - new_stop) * (p_['shares'] + qty)
                    if qty <= 0:
                        rejects['add: no room inside the risk budget'] = rejects.get('add: no room inside the risk budget', 0) + 1
                    else:
                        p_['entry'] = avg
                        p_['shares'] += qty
                        p_['full'] += qty
                        p_['stop'] = new_stop
                        p_['risk_ps'] = avg - new_stop
                        p_['adds'] = p_.get('adds', 0) + 1
                        hod_a = s['hod_prev']
                        imp_a = pb['impulse']
                        pole_a = ((max(x['h'] for x in imp_a)
                                   - min(x['l'] for x in imp_a)) if imp_a else 0)
                        objs = [x for x in (hod_a, pb['low'] + pole_a)
                                if x and x > avg]
                        if objs:
                            p_['t1'] = min(objs)
                            p_['t2'] = avg + 2 * (p_['t1'] - avg)
                        log.append(f'{hm} {sym}: ADD {qty} @ {add_px:.2f}, '
                                   f'{p_["shares"]} total, avg {avg:.2f}, '
                                   f'stop up to {new_stop:.2f}')

            if (pb and allowed and position is None and halted is None
                    and TRADE_START <= tm < HARD_STOP):
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
                spread_est = _spread(ind)
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
                        starter = (max(1, int(final * STARTER_FRACTION))
                                   if SCALE_IN else final)
                        position = dict(sym=sym, entry=entry, stop=stop,
                                        target_size=final, adds=0,
                                        risk_ps=risk_ps, shares=starter,
                                        full=starter,
                                        pnl=0.0, scaled=0, entry_time=hm,
                                        t1=t1, t2=entry + 2 * (t1 - entry),
                                        avg_rng=avg_rng, pb_bars=len(pb['bars']),
                                        spread_est=round(spread_est, 4),
                                        impulse_v=max((x['v'] for x in imp),
                                                      default=0),
                                        window='prime' if tm < PRIME_END else 'late')
                        entries_by_sym[sym] = entries_by_sym.get(sym, 0) + 1
                        position['entry_n'] = entries_by_sym[sym]
                        log.append(f'{hm} {sym}: BUY {starter} @ {entry:.2f} '
                                   f'stop {stop:.2f} (${risk_ps:.2f}/sh)'
                                   + (f'  [entry {entries_by_sym[sym]} on {sym}]'
                                      if entries_by_sym[sym] > 1 else ''))
                        # The entry bar itself can touch the stop - its low is
                        # the whole minute's low, and whether it printed before
                        # or after the trigger is unknowable from OHLCV. The
                        # module contract says intrabar ambiguity resolves
                        # AGAINST the trader, and every later bar already does;
                        # this bar was silently exempt because the position was
                        # created after its management pass had run.
                        if bar['l'] <= stop:
                            p = position
                            p['pnl'] += (stop - entry) * p['shares']
                            p['exit'], p['exit_time'] = stop, hm
                            p['reason'] = 'stop hit (entry bar)'
                            day_pnl += p['pnl']
                            losses += 1
                            trades.append(p)
                            log.append(f'{hm} {sym}: OUT @ {stop:.2f} (stop on '
                                       f'the entry bar) ${p["pnl"]:+.0f}')
                            position = None
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
                watch=list(state), names=len(entries_by_sym),
                entries_by_sym=dict(entries_by_sym))
