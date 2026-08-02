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
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _paths import DATA as _DATA  # noqa: E402
import datetime as dt
import json
import os

OUT = _DATA
ET = dt.timezone(dt.timedelta(hours=-4))

# --- account rules, fixed before the session (playbook: decide while calm) ---
# ACCOUNT is settable so the same run can be priced for a small account. Every
# limit below is a percentage of it, so they scale together the way the playbook
# intends - what does NOT scale is share counts, which are integers, and the
# margin multiple, which depends on the account size in law rather than in the
# playbook (see MARGIN).
ACCOUNT = float(os.environ.get('ACCOUNT', 10_000.0))
RISK_PER_TRADE = 0.02 * ACCOUNT        # 2% of the account
MAX_DAILY_LOSS = 0.06 * ACCOUNT        # 6%
PROFIT_GOAL = 0.06 * ACCOUNT           # 6%
MAX_TRADES = 2
MAX_LOSSES_STREAK = 3
# 4x intraday buying power is a pattern-day-trader privilege and FINRA grants it
# only at $25,000 and above. Below that an account gets Reg T 2x at best, and a
# cash account 1x with settlement delays. Defaulting to 4x for a $500 account
# would silently assume a margin line that broker cannot extend.
MARGIN = float(os.environ.get('MARGIN', 4 if ACCOUNT >= 25_000 else 1))
BUYING_POWER = MARGIN * ACCOUNT

# --- strategy constants -----------------------------------------------------
STOP_MAX = 0.20                        # $/share; beyond this, CUT SIZE
SLIPPAGE = 0.02                        # $/share paid on entry beyond the trigger
MAX_SLIPPAGE_ALLOWED = 0.15            # playbook: limit at ask + 0.15
LEVEL_TOL_PCT = 0.0025                 # 0.25% - the one free parameter
PULLBACK_RESET = 'vwap'                # 'vwap' | 'newhod' - see sweep.py
CONFLUENCE_MIN = 2
# PARAMETERS.md section 3 defines the entry gate as 7 booleans plus at_support.
# Two of them - tape_green and no_seller_wall - need Level 2 and cannot be
# evaluated here, leaving SIX evaluable conditions. These are they.
#
# Three further conditions were previously gated on and are NOT in that gate:
#   pullback 2-4 candles     PLAYBOOK.md:99 describes the PATTERN; it belongs in
#                            the detector, where it now lives, not in the gate
#   pullback holds 50% of leg  one claim (BUCPPCXOHbs 50:34) about first pullbacks
#   front side of the move   never quantified anywhere in the corpus - invented
#
# Measured over 460 setups, those three blocked 15 of the 31 that satisfied the
# source gate: 48% of legitimate setups rejected by rules the gate never had.
# They are still computed and reported, so the evidence stays visible, but they
# no longer gate.
# 'pullback index <= 2' was here. PARAMETERS.md cites BUCPPCXOHbs [52:17] for
# "third means stop", and it was implemented as a boolean that discards the
# setup. The live streams show him counting pullbacks and then taking the third
# anyway - "this is the third pullback... bought the dip at 68" (0uunIYE_wVY
# [19:22]), "coming into third pullback range and you guys know my feeling
# about that AND WHAT IT NEEDS TO DO in order for me" (RABUjMVS6pI [52:34]).
# It is a caution with conditions attached, not a veto, so it moves out of the
# gate and becomes a size reduction - the same correction already applied to
# stop_max_distance (HISTORY.md defect 7) and to extension, which he also
# handles with size: "I got to go with smaller size cuz I'm chasing it a little
# bit" (0zXUMrYyTx0 [49:27]).
# reports/2026-08-streams-roundup.md sections 3 and 4.
GATE_CONDITIONS = {
    'cumulative volume >= 500k',
    'not resumed lower after a halt',
    'pullback_volume < impulse_volume',
    'support confluence >= 2',
    'price > VWAP',
    'price > 9 EMA',
    'MACD histogram > 0',
}
# fraction of normal size taken on a pullback past the second
LATE_PULLBACK_SIZE = float(os.environ.get('LATE_PULLBACK_SIZE', 0.5))
MIN_PILLARS = len(GATE_CONDITIONS)
MAX_PULLBACK_INDEX = 2
# Shortest dip the detector will call a pullback. PLAYBOOK.md:99 says 2-3
# candles, which is why this is 2 - but that reading assumes the 1-minute chart
# is the finest one available. It is not: the source also reads a 10-second
# chart, where a 1-minute pause IS a 2-3 candle pullback. Exposed so the
# assumption can be tested rather than baked in.
MIN_DIP_BARS = 2

# volume_min >= 500,000 shares CUMULATIVE (PARAMETERS.md sec.1, n=102).
# Cumulative over the session, so it is checked at the setup rather than in the
# first five minutes - applying it to a 5-minute window excluded TCX on
# 2026-07-31, which then ran +36%.
MIN_CUM_VOLUME = 500_000

# A halt is invisible in OHLCV except as a gap in an otherwise continuous
# minute series. An LULD/volatility halt lasts a 5-minute minimum
# (FN-uqfbEVKw 01:24), so 5 consecutive missing minutes inside regular hours is
# the detection threshold - the shortest gap a real halt can produce.
HALT_GAP_MIN = 5
# A >=5-min gap only counts as a halt when the bars around it show halt-scale
# volume. Measured separation in the 17-session window: real halts 63k-3.1M
# shares adjacent, no-print gaps 159-2,744. The threshold sits mid-band.
HALT_MIN_ADJ_VOLUME = int(os.environ.get('HALT_MIN_ADJ_VOLUME', 25_000))
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
        bar = dict(bar, in_session=in_session)
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


def confluence(price, ind, flipped_levels, wick=0.002, spread=None):
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
    # PARAMETERS.md:127 - tolerance is a % of price with a FLOOR AT SPREAD
    # WIDTH. A hardcoded 1-cent floor was far tighter than these names
    # actually quote, which is why the confluence test passed only 9% of
    # setups: it demanded the dip stop within a penny of two levels.
    tol = max(price * LEVEL_TOL_PCT, spread if spread else 0.01)
    wick_room = max(price * wick, tol)
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

    # Front side = the leg still reaches up to the day's highs. Expressed
    # in leg-heights rather than a flat percentage, so it scales with the
    # stock instead of excluding everything that has run hard.
    FRONT_SIDE_LEGS = 1.0

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
        self.halted_down = getattr(self, 'halted_down', False)

    def update(self, bar, prev, ind):
        if prev is None or self.leg_low is None:
            self._reset(bar)
            return None

        # A halt breaks the structure. Price does not travel from the pre-halt
        # bar to the resumption bar - it is re-auctioned, and the corpus treats
        # the resumption as its own setup ("dip and rip", 2kMgCjsmFzY 02:06).
        # Carrying leg_low, leg_high and the pullback count across the gap
        # invents a move that never traded, and makes the resumption print look
        # like an ordinary bar-to-bar advance.
        #
        # But a missing minute is not a halt. On a quiet name, minutes with no
        # prints are routine - CUPR 2026-07-31 shows eighteen 5-minute-plus
        # gaps through the afternoon with 159-2,744 shares trading around
        # them, while the REAL halts in the same 17 sessions (ZCMD and ADVB on
        # 07-22) have 63k-3.1M shares on the bars either side. Two orders of
        # magnitude of clean separation. A volatility halt is triggered BY
        # heavy one-directional trading, so volume around the gap is the
        # discriminator OHLCV actually carries. Without it, every quiet
        # afternoon stretch that drifted a cent set halted_down and vetoed
        # the rest of the day.
        gap = (bar['dt'] - prev['dt']).total_seconds() / 60.0
        if gap >= HALT_GAP_MIN:
            if max(prev['v'], bar['v']) >= HALT_MIN_ADJ_VOLUME:
                self._reset(bar)
                self.halted_down = bar['c'] < prev['c']
                return None
            # no-print stretch on a quiet tape: nothing was re-auctioned,
            # structure simply continues across the missing minutes

        # "Stock halted going down typically resumes lower" (FN-uqfbEVKw
        # 19:03) is a caution about the RESUMPTION, not a verdict on the rest
        # of the session. The flag used to persist until the next gap
        # happened to close higher, vetoing every setup in between - hours of
        # them. A new session high is the direct falsification of "resumed
        # lower and heading lower": once it prints, the caution has expired.
        if (self.halted_down and ind.session_high is not None
                and bar['h'] >= ind.session_high):
            self.halted_down = False

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
            # Only a dip the source would CALL a pullback counts as one.
            # PLAYBOOK.md:99 "pulls back 2-3 candles"; the bull-flag document
            # allows 2-4. The candle-count test used to live only in evaluate(),
            # so a 1-bar pause was rejected as an entry but had already
            # incremented the index and rebased leg_low. Phantom dips therefore
            # consumed the "first or second pullback" budget (PARAMETERS.md:89)
            # and pushed the first real flag to #3+, and they moved the leg
            # origin used by the 50%-of-leg test.
            n = len(self.pullback)
            if n < MIN_DIP_BARS:
                # a single pause bar is part of the impulse, not a pullback
                self.leg_high = max(self.leg_high, bar['h'])
                self.pullback = []
                return None
            if n > 4:
                # a 5-6 bar consolidation is a base, not a flag
                self._reset(bar)
                return None
            pb_low = min(x['l'] for x in self.pullback)
            pole = self.leg_high - self.leg_low
            front = (ind.session_high is None or pole <= 0
                     or self.leg_high >= ind.session_high - self.FRONT_SIDE_LEGS * pole)
            self.index += 1
            out = dict(bars=list(self.pullback), low=pb_low,
                       body_low=min(min(x['o'], x['c']) for x in self.pullback),
                       index=self.index, halted_down=self.halted_down,
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

        # Nothing reaches here. A bar that takes out the previous high with a
        # pullback accumulated is the trigger branch above (pullback non-empty
        # implies armed - bars are only appended once a leg high exists), and
        # without one it fell through the extension/append branches. A second
        # copy of the trigger logic used to live here; it had drifted from the
        # real one (no halted_down on the pb it built, different leg rebase)
        # and 0 of 1,362 setups across the 17 sessions came from it. Dead code
        # that can drift is a defect: removed.
        return None

    def impulse_volume(self, ind):
        """Average bar volume over the leg, for the lighter-volume-dip check.

        Called at trigger time, while self.pullback still holds the dip bars.
        The previous version averaged ind.bars[-12:], which CONTAINS those dip
        bars - so 'pullback volume < impulse volume' compared the dip partly
        against itself and decided marginal cases by noise (ADVB 07-22 passed
        by 481 shares). The dip is excluded now, and pre-market bars with it.
        """
        k = len(self.pullback)
        window = ind.bars[-(12 + k):-k] if k else ind.bars[-12:]
        bars = [b for b in window if b.get('in_session')]
        return (sum(b['v'] for b in bars) / len(bars)) if bars else 0


def spread_estimate(ind):
    """Tightest quartile of recent 1-minute ranges: a floor on the spread."""
    rngs = sorted(x['h'] - x['l'] for x in ind.bars[-30:] if x['h'] > x['l'])
    return rngs[len(rngs) // 4] if rngs else 0.01


def evaluate(pb, bar, ind, flipped):
    """The entry gate. Returns (passed, reasons_dict) - every check recorded."""
    checks = {}
    imp_v = pb['impulse'][0]['v'] if pb['impulse'] else 0
    pb_v = sum(x['v'] for x in pb['bars']) / max(1, len(pb['bars']))
    checks['pullback_volume < impulse_volume'] = (pb_v < imp_v, f'{pb_v:,.0f} vs {imp_v:,.0f}')
    cum = sum(b['v'] for b in ind.bars if b.get('in_session'))
    checks['cumulative volume >= 500k'] = (cum >= MIN_CUM_VOLUME, f'{cum:,.0f}')
    # "Stock halted going down typically resumes lower" (FN-uqfbEVKw 19:03).
    checks['not resumed lower after a halt'] = (not pb.get('halted_down'),
                                                'resumed lower' if pb.get('halted_down') else 'ok')
    checks['pullback index <= 2'] = (pb['index'] <= MAX_PULLBACK_INDEX, f"#{pb['index']}")

    # "a strong push up (the impulse)" - one green bar is not a push. Without
    # this the tracker calls any two-bar wiggle a setup and fires ~28 times a
    # day per watchlist where a human sees a handful.
    # 'Front side of the move' is not a separate test: iIC62xnblLc 26:20
    # defines it AS the MACD condition - "only trade when MACD is positive
    # and above the signal line (front side of move)". Checking it
    # separately duplicated a gate condition with an invented threshold.

    # "first pullback should hold at least 50% of initial leg up"
    # (BUCPPCXOHbs 00:50:34). A dip that gives back most of the push is a
    # failed move, not a flag.
    # Structure is read from candle BODIES. The wick extreme is what the
    # stop is placed under; it is not where the dip 'stopped'. Measuring
    # the retracement from the wick low made this reject 76% of setups.

    reasons = confluence(pb['body_low'], ind, flipped,
                         spread=spread_estimate(ind))
    checks['support confluence >= 2'] = (len(reasons) >= CONFLUENCE_MIN,
                                         ', '.join(reasons) or 'none')
    checks['price > VWAP'] = (ind.vwap is not None and bar['c'] > ind.vwap,
                              f"{bar['c']:.2f} vs {ind.vwap:.2f}" if ind.vwap else 'n/a')
    checks['price > 9 EMA'] = (ind.ema9 is not None and bar['c'] > ind.ema9,
                               f"{bar['c']:.2f} vs {ind.ema9:.2f}" if ind.ema9 else 'n/a')
    checks['MACD histogram > 0'] = (ind.macd_hist is not None and ind.macd_hist > 0,
                                    f'{ind.macd_hist:+.4f}' if ind.macd_hist else 'n/a')
    return all(v[0] for v in checks.values()), checks


# simulate() lived here: the original single-day runner. It was dead code -
# nothing imported it - and it still carried two defects the live path had
# already fixed (target at entry+2R, HISTORY #3; the any-lower-low exit,
# HISTORY #4). A stale copy of the engine inside the engine's own module is
# how fixed defects come back. engine20.run_day is the only execution path.
