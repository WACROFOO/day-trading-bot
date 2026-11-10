"""The instrument map stays consistent with the spec and the data layer."""

from portfolio_bot import instruments
from portfolio_bot.data import sleeves


def test_isin_check_digit():
    assert instruments.isin_is_valid("IE0002XZSHO1")  # WPEA
    assert instruments.isin_is_valid("LU0290358497")  # XEON
    assert not instruments.isin_is_valid("IE0002XZSHO2")  # wrong check digit
    assert not instruments.isin_is_valid("IE0002XZSHO")  # too short


def test_every_listed_isin_is_valid():
    df = instruments.load_instruments()
    bad = [i for i in df["isin"] if i and not instruments.isin_is_valid(i)]
    assert not bad, bad


def test_each_core_sleeve_has_one_primary():
    for sleeve in ["S1", "S2", "S3", "S4a", "S5", "S6", "S7"]:
        assert instruments.primary(sleeve)["isin"]


def test_s1_primary_is_pea_eligible():
    assert instruments.primary("S1")["pea_eligible"] == "yes"


def test_backtest_series_exist_in_the_data_layer():
    df = instruments.load_instruments()
    for name in set(df["backtest_series"]) - {""}:
        assert hasattr(sleeves, name), f"sleeves.{name} missing"
