"""Gates 5-8 get their inputs (review 2026-10-03: the desk never passed the split
test, the instrument type, the tick size, the buyout check or pre-market volume)."""
import types

from momentum_platform.cascade import GateState, Inputs, evaluate
from momentum_platform.catalyst import buyout_in
from momentum_platform.dashboard import ibkr_desk as D
from momentum_platform.dashboard import session_builder as SB
from momentum_platform.datasources.instrument_facts import ibkr_instrument, split_facts


def gate(r, gid):
    return next(g for g in r.gates if g.id == gid)


def base(**over):
    d = dict(symbol="T", last=6.0, change_pct=50.0, session_high=6.2, float_shares=4e6, float_verified=True,
             catalyst_today=True, is_fund_or_etf=False, tick_size=0.01, rvol=8.0, session_volume=3e6,
             above_vwap=True, above_ema9=True, macd_positive_and_above_signal=True)
    d.update(over)
    return Inputs(**d)


# ------------------------------------------------------------------ cascade
def test_an_untested_split_is_unknown_not_pass():
    r = evaluate(base())
    assert gate(r, "split").state is GateState.UNKNOWN and r.killed_by is None
    assert any("split test" in w for w in r.warnings)
    assert gate(evaluate(base(split_checked=True)), "split").state is GateState.PASS
    assert evaluate(base(split_checked=True, split_ratio_clean_integer=8.0)).killed_by == "split"


def test_buyout_is_unknown_without_a_headline_source():
    assert gate(evaluate(base()), "buyout").state is GateState.UNKNOWN
    assert gate(evaluate(base(buyout_announced=False)), "buyout").state is GateState.PASS
    assert evaluate(base(buyout_announced=True)).killed_by == "buyout"


def test_unknown_gates_do_not_change_the_verdict():
    assert evaluate(base()).verdict == evaluate(base(split_checked=True, buyout_announced=False)).verdict


# ------------------------------------------------------------------ buyout words
def test_buyout_fires_only_on_target_phrases():
    assert buyout_in(["Acme Agrees to Be Acquired by Big Co for $5.00 Per Share"])
    assert buyout_in(["Acme announces going private transaction"])
    assert not buyout_in(["Big Co to Acquire Acme"]), "the acquirer is not pinned"
    assert not buyout_in(["Acme enters merger agreement"])


def test_buyout_reads_only_todays_own_headlines():
    today = "2026-10-05"
    own = {"headline": "Acme to be acquired", "publishedAt": "2026-10-05T11:00:00Z"}
    old = {"headline": "Acme to be acquired", "publishedAt": "2026-10-01T11:00:00Z"}
    shared = dict(own, sharedTag=True)
    assert SB._buyout_today([own], today)
    assert not SB._buyout_today([old], today)
    assert not SB._buyout_today([shared], today)


# ------------------------------------------------------------------ desk -> cascade
def test_cascade_inputs_carry_the_facts():
    meta = {"symbol": "T", "isFundOrEtf": True, "minTick": 0.01, "splitChecked": True, "splitRatio": None,
            "news": [], "newsSourceOk": True, "tradingDate": "2026-10-05",
            "metrics": {"last": 6.0, "changePct": 50.0, "volumePremarket": 1_500_000}}
    i = SB.cascade_inputs(meta)
    assert i.is_fund_or_etf is True and i.tick_size == 0.01 and i.split_checked
    assert i.buyout_announced is False and i.premarket_volume == 1_500_000
    assert SB.cascade_inputs(dict(meta, newsSourceOk=False)).buyout_announced is None
    snap = types.SimpleNamespace(last=6.0, change_from_close_pct=50.0, session_high=6.2, rvol=8.0,
                                 volume_today=3e6, volume_premarket=0.0, event_ts=None)
    assert SB.cascade_inputs(meta, snap=snap).premarket_volume is None, "no pre-market tape is not a measured zero"


# ------------------------------------------------------------------ lookups
class _Details:
    def __init__(self, st, tick):
        self.stockType, self.minTick = st, tick


class _IB:
    def __init__(self, details=None, fail=False):
        self.details, self.fail = details, fail

    def reqContractDetails(self, c):
        if self.fail:
            raise RuntimeError("pacing")
        return self.details


def test_ibkr_instrument():
    assert ibkr_instrument(_IB([_Details("ETF", 0.01)]), None) == \
        {"stock_type": "ETF", "is_fund_or_etf": True, "min_tick": 0.01}
    assert ibkr_instrument(_IB([_Details("COMMON", 0.01)]), None)["is_fund_or_etf"] is False
    assert ibkr_instrument(_IB([_Details("", None)]), None)["is_fund_or_etf"] is None
    assert ibkr_instrument(_IB(fail=True), None) == {}


def test_split_facts_says_when_the_test_ran():
    assert split_facts("T", None) == {"split_checked": False, "split_ratio": None}
    assert split_facts("T", 2.0, check=lambda s, p: {}) == {"split_checked": False, "split_ratio": None}
    assert split_facts("T", 2.0, check=lambda s, p: {"checked": True}) == {"split_checked": True, "split_ratio": None}
    assert split_facts("T", 2.64, check=lambda s, p: {"checked": True, "split_today": 8}) == \
        {"split_checked": True, "split_ratio": 8.0}


def test_desk_records_facts_once_per_join(monkeypatch):
    class _Desk:
        session_day = lambda self: "2026-10-05"
        _instrument_facts = D.IbkrDesk._instrument_facts

        def __init__(self):
            self.stream = types.SimpleNamespace(ib=_IB([_Details("COMMON", 0.01)]))
            self.sec, self._facts, self.logs = False, {}, []

        def log(self, m):
            self.logs.append(m)

    d = _Desk()
    d._instrument_facts("T", None)
    assert d._facts["T"] == {"day": "2026-10-05", "stock_type": "COMMON", "is_fund_or_etf": False, "min_tick": 0.01}
    assert "split not checked" in d.logs[-1]


def test_premarket_volume_counts_only_the_premarket():
    from datetime import datetime, timezone
    from momentum_platform.models import Bar, DataStatus
    from momentum_platform.state import HotState, MarketUpdate
    hot = HotState()
    for hhmm_utc, v in (("13:28", 1000.0), ("13:29", 2000.0), ("13:31", 5000.0)):   # 09:28, 09:29, 09:31 ET
        ts = datetime.fromisoformat(f"2026-10-05T{hhmm_utc}:00+00:00").astimezone(timezone.utc)
        bar = Bar(symbol="AAA", timeframe="1m", ts=ts, open=5, high=5, low=5, close=5, volume=v)
        snap = hot.apply(MarketUpdate("AAA", ts, price=5, size=v, bar=bar, data_status=DataStatus.REPLAY))
    assert snap.volume_premarket == 3000.0 and snap.volume_today == 8000.0


def test_gate_7_judges_the_increment_at_the_price():
    assert SB._effective_tick(0.0001, 5.0) == 0.01
    assert SB._effective_tick(0.0001, 0.8) == 0.0001
    assert SB._effective_tick(0.05, 5.0) == 0.05
    assert SB._effective_tick(None, 5.0) is None
