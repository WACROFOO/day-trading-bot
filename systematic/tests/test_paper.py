"""The paper record is reproducible and the decision log never duplicates a day."""

import csv
import json

import numpy as np
import pandas as pd
import pytest

from portfolio_bot.crypto import paper, rules


def series(seed, n=900, start="2023-01-01"):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n, freq="D")
    return pd.Series(100 * np.cumprod(1 + rng.normal(0.001, 0.03, n)), index=idx)


def test_record_is_identical_on_rerun_and_starts_at_forward_date():
    btc, eth = series(1), series(2)
    rule = rules.FrozenRule()
    start = str(btc.index[600].date())
    a = paper.build_record(btc, eth, rule, start)
    b = paper.build_record(btc, eth, rule, start)
    pd.testing.assert_frame_equal(a, b)
    assert a.index[0] == pd.Timestamp(start)
    for s in paper.STRATEGIES:
        assert f"{s}_nav" in a


def test_primary_nav_matches_the_core_simulator():
    btc, eth = series(3), series(4)
    rule = rules.FrozenRule()
    start = str(btc.index[500].date())
    rec = paper.build_record(btc, eth, rule, start)
    sim = rules.simulate(btc, rules.primary_exposure(btc, rule), rule.maker_fee + rule.spread, 0.0, start=start)
    pd.testing.assert_series_equal(rec["primary_nav"], sim["nav"].reindex(rec.index), check_names=False)


def test_buy_and_hold_tracks_price_from_the_prior_close():
    btc, eth = series(5), series(6)
    start = str(btc.index[450].date())
    rec = paper.build_record(btc, eth, rules.FrozenRule(), start)
    assert rec["btc_buy_hold_nav"].iloc[-1] == pytest.approx(btc.iloc[-1] / btc.iloc[449])


def test_decision_is_logged_once_per_date(tmp_path):
    btc, eth = series(7), series(8)
    row = paper.decision(btc, eth, rules.FrozenRule())
    path = tmp_path / "decisions.csv"
    assert paper.append_decision(path, {**row, "run_utc": "x", "quote_source": "test"})
    assert not paper.append_decision(path, {**row, "run_utc": "y", "quote_source": "test"})
    with path.open() as f:
        assert len(list(csv.DictReader(f))) == 1


def test_decision_date_is_the_day_after_the_last_close():
    btc, eth = series(9), series(10)
    row = paper.decision(btc, eth, rules.FrozenRule())
    assert pd.Timestamp(row["decision_date"]) == btc.index[-1] + pd.Timedelta(days=1)
    assert 0.0 <= row["primary"] <= 1.0 and row["v1_btc"] <= 0.5 and row["v1_eth"] <= 0.5


def test_okx_ticker_parser():
    ok = json.dumps({"code": "0", "data": [{"instId": "BTC-USDC", "bidPx": "58604.1", "askPx": "58604.2"}]})
    assert paper.parse_okx_ticker(ok.encode()) == (58604.1, 58604.2)
    with pytest.raises(ValueError):
        paper.parse_okx_ticker(json.dumps({"code": "51001", "msg": "Instrument ID does not exist", "data": []}).encode())
