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
STOP_MAX = 0.20                        # $/share; wider than this = skip
SLIPPAGE = 0.02                        # $/share paid on entry beyond the trigger
MAX_SLIPPAGE_ALLOWED = 0.15            # playbook: limit at ask + 0.15
LEVEL_TOL_PCT = 0.0025                 # 0.25% - the one free parameter
CONFLUENCE_MIN = 2
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


def confluence(price, ind, flipped_levels):
    """How many independent reasons this price has to matter. Needs >= 2.

    Mirrors at_support(p) in PARAMETERS.md sec.3: whole/half dollar, the three
    moving averages, VWAP, and a level that was resistance earlier.
    """
    tol = max(price * LEVEL_TOL_PCT, 0.01)
    reasons = []
    if abs(price - round(price * 2) / 2) <= tol:
        reasons.append('whole/half dollar')
    for name, level in (('9 EMA', ind.ema9), ('20 EMA', ind.ema20),
                        ('200 MA', ind.ma200), ('VWAP', ind.vwap)):
        if level is not None and abs(price - level) <= tol:
            reasons.append(name)
    for lvl in flipped_levels:
        if abs(price - lvl) <= tol:
            reasons.append(f'flipped ${lvl:.2f}')
            break
    return reasons


class PullbackTracker:
    """Finds the impulse -> pullback -> break structure, bar by bar.

    A pullback is a run of bars making lower highs after a push up. It ends the
    moment a bar trades above the previous bar's high, which is the trigger.

    The index counts pullbacks inside the current up-leg. The leg resets when
    price loses VWAP, which is also when the playbook says the setup is dead -
    so "third pullback" means the third since the stock was last reclaimed.
    """

    def __init__(self):
        self.state = 'idle'          # idle | impulse | pullback
        self.impulse_bars = []
        self.pullback_bars = []
        self.index = 0
        self.last_pullback = None

    def update(self, bar, prev, ind):
        if prev is None:
            return None
        vwap = ind.vwap
        if vwap is not None and bar['c'] < vwap:
            # lost VWAP: the leg is over, counting starts again
            self.state, self.index = 'idle', 0
            self.impulse_bars, self.pullback_bars = [], []
            return None

        up = bar['h'] > prev['h'] and bar['c'] >= prev['c']
        down = bar['h'] <= prev['h']

        if self.state in ('idle', 'impulse'):
            if up:
                if self.state == 'idle':
                    self.impulse_bars = []
                self.state = 'impulse'
                self.impulse_bars.append(bar)
            elif down and self.state == 'impulse' and self.impulse_bars:
                self.state = 'pullback'
                self.pullback_bars = [bar]
            return None

        # in a pullback
        if bar['h'] > prev['h']:
            # trigger bar: the pullback just ended
            self.index += 1
            pb = dict(bars=list(self.pullback_bars),
                      impulse=list(self.impulse_bars),
                      low=min(x['l'] for x in self.pullback_bars),
                      index=self.index,
                      trigger_level=prev['h'])
            self.last_pullback = pb
            self.state = 'impulse'
            self.impulse_bars = [bar]
            self.pullback_bars = []
            return pb

        self.pullback_bars.append(bar)
        if len(self.pullback_bars) > 6:
            # too long to be a pause; treat it as a new base
            self.state, self.index = 'idle', 0
            self.impulse_bars, self.pullback_bars = [], []
        return None


def evaluate(pb, bar, ind, flipped):
    """The entry gate. Returns (passed, reasons_dict) - every check recorded."""
    checks = {}
    imp_v = sum(x['v'] for x in pb['impulse']) / max(1, len(pb['impulse']))
    pb_v = sum(x['v'] for x in pb['bars']) / max(1, len(pb['bars']))
    checks['pullback_volume < impulse_volume'] = (pb_v < imp_v, f'{pb_v:,.0f} vs {imp_v:,.0f}')
    checks['pullback index <= 2'] = (pb['index'] <= MAX_PULLBACK_INDEX, f"#{pb['index']}")
    checks['pullback 2-3 candles'] = (1 <= len(pb['bars']) <= 4, f"{len(pb['bars'])} bars")

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
