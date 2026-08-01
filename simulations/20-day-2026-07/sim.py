#!/usr/bin/env python3
"""Replay Friday 2026-07-31 one minute at a time, deciding as the bar arrives.

The engine is a strict left-to-right pass. At bar i it may read bars[0..i] and
nothing else - every indicator is incremental, and every decision is taken from
state that existed at that timestamp. There is no dataframe of the whole day in
scope at decision time, which is the usual way look-ahead sneaks in.

Intrabar ambiguity is always resolved against the trader:
  - a bar whose low breaks the stop AND whose high reaches the target is
    recorded as a stop, because a 1-minute bar does not say which came first
  - entry fills at the prior bar's high plus slippage, which is the worst
    plausible price for a break-of-high trigger, not the best

Two conditions from the playbook cannot be evaluated from OHLCV and are
recorded as unverifiable rather than silently passed: `no_seller_wall` and
`tape_green` need Level 2 depth and time-and-sales.
"""
import datetime as dt
import json
import os

OUT = os.path.dirname(os.path.abspath(__file__))
ET = dt.timezone(dt.timedelta(hours=-4))

# --- account rules, fixed before the session (playbook: decide while calm) ---
ACCOUNT = 10_000.0
RISK_PER_TRADE = 0.02 * ACCOUNT        # $200
MAX_DAILY_LOSS = 0.06 * ACCOUNT        # $600
PROFIT_GOAL = 0.06 * ACCOUNT           # $600
MAX_TRADES = 2
MAX_LOSSES_STREAK = 3
BUYING_POWER = 4 * ACCOUNT             # standard 4x day-trade margin

# --- strategy constants -----------------------------------------------------
STOP_MAX = 0.20                        # $/share; beyond this, CUT SIZE
STOP_MAX_PCT = 0.06                    # outer sanity bound, % of price
SLIPPAGE = 0.02                        # $/share paid on entry beyond the trigger
MAX_SLIPPAGE_ALLOWED = 0.15            # playbook: limit at ask + 0.15
LEVEL_TOL_PCT = 0.0025                 # 0.25% - the one free parameter
PULLBACK_RESET = 'vwap'                # 'vwap' | 'newhod' - see sweep.py
CONFLUENCE_MIN = 2
MIN_PILLARS = 9        # how many of the 9 entry conditions must hold
MAX_PULLBACK_INDEX = 2
LIQUIDITY_CAP = 0.10                   # never take more than 10% of a bar's volume

SESSION_OPEN = dt.time(9, 30)
TRADE_START = dt.time(9, 35)           # first 5 minutes: watch only
PRIME_END = dt.time(10, 30)
HARD_STOP = dt.time(11, 30)


class Indicators:
    """Incremental only. Every update() call sees exactly one new bar."""

    def __init__(self):
        self.ema9 = self.ema20 = None
        self.ema12 = self.ema26 = self.signal = None
        self.macd_hist = None
        self.vwap_pv = self.vwap_v = 0.0
        self.closes = []
        self.session_high = None
        self.bars = []

    @staticmethod
    def _ema(prev, price, n):
        k = 2 / (n + 1)
        return price if prev is None else price * k + prev * (1 - k)

    def update(self, bar, in_session):
        c = bar['c']
        self.closes.append(c)
        self.bars.append(bar)
        self.ema9 = self._ema(self.ema9, c, 9)
        self.ema20 = self._ema(self.ema20, c, 20)
        self.ema12 = self._ema(self.ema12, c, 12)
        self.ema26 = self._ema(self.ema26, c, 26)
        macd = self.ema12 - self.ema26
        self.signal = self._ema(self.signal, macd, 9)
        self.macd_hist = macd - self.signal

        # VWAP resets at the opening bell - pre-market volume is not in it.
        if in_session:
            tp = (bar['h'] + bar['l'] + bar['c']) / 3
            self.vwap_pv += tp * bar['v']
            self.vwap_v += bar['v']
            self.session_high = (bar['h'] if self.session_high is None
                                 else max(self.session_high, bar['h']))

    @property
    def vwap(self):
        return self.vwap_pv / self.vwap_v if self.vwap_v else None

    @property
    def ma200(self):
        if len(self.closes) < 200:
            return None
        return sum(self.closes[-200:]) / 200


def confluence(price, ind, flipped_levels, wick=0.002):
    """Levels the dip came down to AND HELD. Not levels it sliced through.

    The previous version tested abs(price - level) <= tol, so a pullback low
    1.2% BELOW the 9 EMA counted as "at the 9 EMA". Measured across 300 real
    setups the dip low was below the 9 EMA 87% of the time, median -1.23% - so
    that test was systematically approving dips that had already broken the
    level and were bouncing underneath it. That is a different trade from the
    one the playbook describes, and a much worse one.

    A level counts as support when the dip reached it (within tol) and held it
    (no more than `wick` below, allowing for the wick that makes the touch).
    """
    tol = max(price * LEVEL_TOL_PCT, 0.01)
    wick_room = price * wick
    reasons = []

    def held(level):
        d = price - level                      # signed: + means dip stayed above
        return -wick_room <= d <= tol

    if abs(price - round(price * 2) / 2) <= tol:
        reasons.append('whole/half dollar')
    for name, level in (('9 EMA', ind.ema9), ('20 EMA', ind.ema20),
                        ('200 MA', ind.ma200), ('VWAP', ind.vwap)):
        if level is not None and held(level):
            reasons.append(name)
    for lvl in flipped_levels:
        if held(lvl):
            reasons.append(f'flipped ${lvl:.2f}')
            break
    return reasons


class PullbackTracker:
    """Swing structure, bar by bar: leg low -> leg high -> pullback -> trigger.

    The previous version tracked "impulse bars" as whatever run of higher highs
    immediately preceded a dip, so the leg it measured was often one or two
    bars. Everything downstream inherited that: the leg height used for the 50%
    retracement rule was meaningless, and any two-bar wiggle registered as a
    setup - 481 of them in 17 days, where a human sees a handful.

    Here a leg runs from a real swing low to the highest high since, and a
    pullback is measured against THAT. Legs chain the way they do on a chart:
    when a pullback resolves upward, the next leg starts from the pullback low.

    Front side only: the leg high must be at or near the high of day. Buying
    dips in a stock that is no longer making highs is a different trade, and
    not the one the playbook describes.
    """

    FRONT_SIDE = 0.98        # leg high must be within 2% of the high of day

    def __init__(self):
        self.leg_low = None          # where the current up-leg started
        self.leg_high = None         # highest high since leg_low
        self.pullback = []           # bars pulling back from leg_high
        self.index = 0
        self.armed = False           # a leg high has been established

    def _reset(self, bar):
        self.leg_low = bar['l']
        self.leg_high = bar['h']
        self.pullback = []
        self.index = 0
        self.armed = False

    def update(self, bar, prev, ind):
        if prev is None or self.leg_low is None:
            self._reset(bar)
            return None

        # Losing VWAP resets the leg only if it also breaks the leg low. The
        # unconditional reset was my invention, not a playbook rule - there
        # `price > VWAP` is an ENTRY GATE, which is enforced separately in
        # evaluate(). Using it to wipe swing structure destroyed the leg every
        # time a stock wobbled around VWAP, which on these names is most of the
        # session (57-68% of bars below VWAP).
        vwap = ind.vwap
        if vwap is not None and bar['c'] < vwap and bar['l'] < self.leg_low:
            self._reset(bar)
            return None

        if PULLBACK_RESET == 'newhod' and (ind.session_high is None
                                           or bar['h'] >= ind.session_high):
            self.index = 0

        # ORDER MATTERS. The trigger has to be tested before leg extension.
        #
        # On a strong mover the bar that ends the pullback usually takes out the
        # leg high as well as the previous bar's high. Testing leg extension
        # first meant that bar was filed as "leg continues", the accumulated
        # pullback was discarded, and the setup vanished - so the faster a stock
        # ran, the fewer signals it produced. VEEE went from $11.51 to $29.19 on
        # 2026-07-13 and yielded five setups all morning, the first at 10:37.
        # This is the entry the playbook actually describes: the first candle to
        # trade above the previous candle's high, after a 2-3 candle dip.
        if self.armed and self.pullback and bar['h'] > prev['h']:
            pb_low = min(x['l'] for x in self.pullback)
            pole = self.leg_high - self.leg_low
            front = (ind.session_high is None
                     or self.leg_high >= self.FRONT_SIDE * ind.session_high)
            self.index += 1
            out = dict(bars=list(self.pullback), low=pb_low, index=self.index,
                       trigger_level=prev['h'], leg_low=self.leg_low,
                       leg_high=self.leg_high, pole=pole, front_side=front,
                       impulse=[dict(h=self.leg_high, l=self.leg_low,
                                     v=self.impulse_volume(ind))])
            self.leg_low = pb_low
            self.leg_high = max(self.leg_high, bar['h'])
            self.pullback = []
            return out

        # extending the leg
        if bar['h'] > self.leg_high:
            self.leg_high = bar['h']
            self.pullback = []
            self.armed = True
            return None

        if not self.armed:
            self.leg_low = min(self.leg_low, bar['l'])
            return None

        # a bar that fails to take out the previous bar's high is part of the dip
        if bar['h'] <= prev['h']:
            self.pullback.append(bar)
            if len(self.pullback) > 6:
                self._reset(bar)          # too long to be a pause; new base
            return None

        # bar took out the previous bar's high: the pullback just ended
        if not self.pullback:
            return None

        pb_low = min(x['l'] for x in self.pullback)
        pole = self.leg_high - self.leg_low
        front = (ind.session_high is None
                 or self.leg_high >= self.FRONT_SIDE * ind.session_high)
        self.index += 1
        out = dict(bars=list(self.pullback), low=pb_low, index=self.index,
                   trigger_level=prev['h'], leg_low=self.leg_low,
                   leg_high=self.leg_high, pole=pole, front_side=front,
                   impulse=[dict(h=self.leg_high, l=self.leg_low,
                                 v=self.impulse_volume(ind))])
        # the next leg starts from this pullback low
        self.leg_low = pb_low
        self.leg_high = bar['h']
        self.pullback = []
        return out

    def impulse_volume(self, ind):
        """Average bar volume over the leg, for the lighter-volume-dip check."""
        bars = [b for b in ind.bars[-12:] if b['h'] <= self.leg_high]
        return (sum(b['v'] for b in bars) / len(bars)) if bars else 0


def evaluate(pb, bar, ind, flipped):
    """The entry gate. Returns (passed, reasons_dict) - every check recorded."""
    checks = {}
    imp_v = pb['impulse'][0]['v'] if pb['impulse'] else 0
    pb_v = sum(x['v'] for x in pb['bars']) / max(1, len(pb['bars']))
    checks['pullback_volume < impulse_volume'] = (pb_v < imp_v, f'{pb_v:,.0f} vs {imp_v:,.0f}')
    checks['pullback index <= 2'] = (pb['index'] <= MAX_PULLBACK_INDEX, f"#{pb['index']}")
    checks['pullback 2-4 candles'] = (2 <= len(pb['bars']) <= 4, f"{len(pb['bars'])} bars")

    # "a strong push up (the impulse)" - one green bar is not a push. Without
    # this the tracker calls any two-bar wiggle a setup and fires ~28 times a
    # day per watchlist where a human sees a handful.
    checks['front side of the move'] = (pb['front_side'],
                                        f"leg high {pb['leg_high']:.2f}")

    # "first pullback should hold at least 50% of initial leg up"
    # (BUCPPCXOHbs 00:50:34). A dip that gives back most of the push is a
    # failed move, not a flag.
    pole = pb['pole']
    held = ((pb['low'] - pb['leg_low']) / pole) if pole > 0 else 0
    checks['pullback holds 50% of leg'] = (pole > 0 and held >= 0.5,
                                           f'{held*100:.0f}% of a {pole:.2f} leg')

    reasons = confluence(pb['low'], ind, flipped)
    checks['support confluence >= 2'] = (len(reasons) >= CONFLUENCE_MIN,
                                         ', '.join(reasons) or 'none')
    checks['price > VWAP'] = (ind.vwap is not None and bar['c'] > ind.vwap,
                              f"{bar['c']:.2f} vs {ind.vwap:.2f}" if ind.vwap else 'n/a')
    checks['price > 9 EMA'] = (ind.ema9 is not None and bar['c'] > ind.ema9,
                               f"{bar['c']:.2f} vs {ind.ema9:.2f}" if ind.ema9 else 'n/a')
    checks['MACD histogram > 0'] = (ind.macd_hist is not None and ind.macd_hist > 0,
                                    f'{ind.macd_hist:+.4f}' if ind.macd_hist else 'n/a')
    return all(v[0] for v in checks.values()), checks


def simulate(sym, fri_bars, pre_bars, log):
    """One symbol, one day, strictly forward."""
    ind = Indicators()
    for b in pre_bars:                       # seed indicators, pre-market only
        ind.update(b, in_session=False)

    tracker = PullbackTracker()
    flipped, prev = [], None
    trades, position = [], None

    for bar in fri_bars:
        tm = bar['dt'].time()
        in_sess = SESSION_OPEN <= tm < dt.time(16, 0)
        if not in_sess:
            continue
        ind.update(bar, in_session=True)

        # ---- manage an open position first, on this bar ----
        if position:
            p = position
            exit_reason = None
            fill = None
            # conservative ordering: stop is checked before target
            if bar['l'] <= p['stop']:
                fill, exit_reason = p['stop'], 'stop hit'
            elif p['scaled'] == 0 and bar['h'] >= p['t1']:
                realised = (p['t1'] - p['entry']) * (p['shares'] // 2)
                p['pnl'] += realised
                p['shares'] -= p['shares'] // 2
                p['scaled'] = 1
                p['stop'] = p['entry']       # breakeven, playbook step 9
                log.append(f"    {tm} scale 50% at {p['t1']:.2f} "
                           f"(+${realised:.0f}), stop -> breakeven")
            elif p['scaled'] == 1 and bar['h'] >= p['t2']:
                q = p['shares'] // 2
                realised = (p['t2'] - p['entry']) * q
                p['pnl'] += realised
                p['shares'] -= q
                p['scaled'] = 2
                log.append(f"    {tm} scale 25% at {p['t2']:.2f} (+${realised:.0f})")

            if exit_reason is None and p['shares'] > 0:
                broke = []
                if ind.macd_hist is not None and ind.macd_hist < 0:
                    broke.append('MACD negative')
                if ind.vwap and bar['c'] < ind.vwap:
                    broke.append('lost VWAP')
                if prev and bar['l'] < prev['l'] and bar['c'] < bar['o']:
                    broke.append('new low')
                if broke and p['scaled'] >= 1:
                    fill, exit_reason = bar['c'], ' + '.join(broke)
                elif broke and p['scaled'] == 0:
                    fill, exit_reason = bar['c'], ' + '.join(broke)

            if exit_reason:
                realised = (fill - p['entry']) * p['shares']
                p['pnl'] += realised
                p['exit_time'], p['exit'] = tm, fill
                p['reason'] = exit_reason
                log.append(f"    {tm} EXIT {p['shares']} @ {fill:.2f} "
                           f"({exit_reason})  trade P&L ${p['pnl']:+.0f}")
                trades.append(p)
                position = None

        # ---- look for a new setup ----
        pb = tracker.update(bar, prev, ind)
        if pb and position is None and TRADE_START <= tm < HARD_STOP:
            ok, checks = evaluate(pb, bar, ind, flipped)
            entry = min(pb['trigger_level'] + SLIPPAGE, bar['h'])
            stop = pb['low']
            risk_ps = entry - stop
            sized_ok = 0 < risk_ps <= STOP_MAX
            log.append(f"  {tm} pullback #{pb['index']} low {stop:.2f} "
                       f"trigger {pb['trigger_level']:.2f}")
            for k, (passed, detail) in checks.items():
                log.append(f"      [{'PASS' if passed else 'FAIL'}] {k}: {detail}")
            log.append(f"      [{'PASS' if sized_ok else 'FAIL'}] stop <= $0.20: "
                       f"${risk_ps:.3f}/share")
            log.append('      [N/A ] no seller wall / green tape: needs Level 2')

            if ok and sized_ok:
                shares = int(RISK_PER_TRADE / risk_ps)
                cap_bp = int(BUYING_POWER / entry)
                cap_liq = int(bar['v'] * LIQUIDITY_CAP)
                shares = max(0, min(shares, cap_bp, cap_liq))
                if shares > 0:
                    position = dict(
                        sym=sym, entry_time=tm, entry=entry, stop=stop,
                        init_stop=stop, risk_ps=risk_ps, shares=shares,
                        full_shares=shares, pnl=0.0, scaled=0,
                        t1=entry + 2 * risk_ps, t2=entry + 3 * risk_ps,
                        checks=checks,
                        capped=('liquidity' if shares == cap_liq else
                                'buying power' if shares == cap_bp else None))
                    log.append(f"    >>> ENTRY {shares} @ {entry:.2f}, stop "
                               f"{stop:.2f}, risk ${risk_ps * shares:.0f}, "
                               f"T1 {position['t1']:.2f}")
                else:
                    log.append('      -> size rounds to 0 shares, skipped')

        if ind.session_high and bar['h'] >= ind.session_high:
            flipped.append(round(bar['h'], 2))
            flipped[:] = flipped[-6:]
        prev = bar

    if position:                              # forced flat at the bell we stop at
        p = position
        last = fri_bars[-1]
        p['pnl'] += (last['c'] - p['entry']) * p['shares']
        p['exit_time'], p['exit'] = last['dt'].time(), last['c']
        p['reason'] = 'end of window'
        trades.append(p)
    return trades
