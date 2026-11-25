"""Parser tests on synthetic payloads that mimic each provider's real format.

No provider data is committed: every fixture is built here, by hand, with
made-up numbers (LESSONS C2: every parser gets a hand-verified case).
"""

import io
import json
import zipfile

import numpy as np
import pandas as pd
import pytest
from openpyxl import Workbook

from portfolio_bot.data import sources as src


def _ts(s):
    return pd.Timestamp(s)


# --------------------------------------------------------------------------
# MSCI
# --------------------------------------------------------------------------

def test_msci_levels_land_on_month_end():
    payload = json.dumps({"msci_index_code": "990100", "indexes": {"INDEX_LEVELS": [
        {"level_eod": 100.0, "calc_date": 20240131},
        {"level_eod": 102.0, "calc_date": 20240229},
        {"level_eod": 101.0, "calc_date": 20240328},  # last business day
    ]}}).encode()
    s = src.parse_msci(payload)
    assert list(s.index) == [_ts("2024-01-31"), _ts("2024-02-29"), _ts("2024-03-31")]
    assert s.iloc[-1] == 101.0


def test_msci_error_message_raises():
    payload = json.dumps({"error_code": " 100", "error_message": " Invalid Parameter start_date"}).encode()
    with pytest.raises(ValueError, match="Invalid Parameter"):
        src.parse_msci(payload)


# --------------------------------------------------------------------------
# Ken French
# --------------------------------------------------------------------------

def _kf_zip(text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("F-F_Test.csv", text)
    return buf.getvalue()


KF_TEXT = """This file was created using the 202609 CRSP database.
Some notes, with a comma, here.

,Mkt-RF,SMB,HML,RF
192607,   2.89,  -2.42,  -2.75,   0.22
192608,   2.64, -99.99,   4.13,   0.25
192609,   0.38,  -1.36,   0.05,   0.23

 Annual Factors: January-December
,Mkt-RF,SMB,HML,RF
  1927,  29.44,  -3.05,  -3.36,   3.12
"""


def test_ken_french_monthly_table_in_decimals():
    df = src.parse_ken_french(_kf_zip(KF_TEXT))
    assert list(df.columns) == ["Mkt-RF", "SMB", "HML", "RF"]
    assert list(df.index) == [_ts("1926-07-31"), _ts("1926-08-31"), _ts("1926-09-30")]
    assert df.loc["1926-07-31", "Mkt-RF"] == pytest.approx(0.0289)
    assert np.isnan(df.loc["1926-08-31", "SMB"])  # -99.99 means missing
    assert len(df) == 3  # stops before the annual table


def test_ken_french_single_column_file():
    text = "Notes\n\n,Mom\n192701,   0.36\n192702,  -2.14\n\nAnnual Factors:\n"
    df = src.parse_ken_french(_kf_zip(text))
    assert list(df.columns) == ["Mom"]
    assert df["Mom"].iloc[1] == pytest.approx(-0.0214)


def test_ken_french_without_table_raises():
    with pytest.raises(ValueError):
        src.parse_ken_french(_kf_zip("only notes\nno table\n"))


# --------------------------------------------------------------------------
# AQR
# --------------------------------------------------------------------------

def _xlsx(rows, sheet="Sheet1") -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_aqr_table_found_below_notes():
    rows = [
        ["AQR Capital Management — Time Series Momentum: Factors, Monthly"],
        [None],
        ["This file contains the excess returns..."],
        [None],
        [None, "TSMOM", "TSMOM^CM", None],
        [pd.Timestamp("1985-01-31"), 0.043, -0.013, None],
        [pd.Timestamp("1985-02-28"), 0.037, 0.046, None],
        [pd.Timestamp("1985-03-29"), -0.052, -0.081, None],
    ]
    df = src.parse_aqr(_xlsx(rows, "TSMOM Factors"))
    assert list(df.columns) == ["TSMOM", "TSMOM^CM"]
    assert df.index[-1] == _ts("1985-03-31")
    assert df["TSMOM"].iloc[0] == pytest.approx(0.043)


def test_aqr_without_header_raises():
    with pytest.raises(ValueError):
        src.parse_aqr(_xlsx([["notes only"], ["still notes"]]))


# --------------------------------------------------------------------------
# FRED and ECB
# --------------------------------------------------------------------------

def test_fred_drops_dot_missing_values():
    payload = b"observation_date,GS10\n2024-01-01,4.06\n2024-02-01,.\n2024-03-01,4.21\n"
    s = src.parse_fred(payload)
    assert list(s.values) == [4.06, 4.21]
    assert s.name == "GS10"


def test_ecb_monthly_periods_to_month_end():
    payload = (b"KEY,FREQ,TIME_PERIOD,OBS_VALUE\n"
               b"FM.M.U2,M,1994-01,6.3\nFM.M.U2,M,1994-02,6.2\n")
    s = src.parse_ecb(payload)
    assert list(s.index) == [_ts("1994-01-31"), _ts("1994-02-28")]
    assert s.iloc[0] == 6.3


# --------------------------------------------------------------------------
# World Bank Pink Sheet
# --------------------------------------------------------------------------

def test_world_bank_prices_layout():
    rows = [
        ["World Bank Commodity Price Data (The Pink Sheet)"],
        ["monthly prices in nominal US dollars, 1960 to present"],
        [None],
        [None, "Crude oil, average", "Gold", "Natural gas, US"],
        [None, "($/bbl)", "($/troy oz)", "($/mmbtu)"],
        ["1960M01", 1.6, 35.27, "…"],
        ["1960M02", 1.6, 35.27, 0.14],
    ]
    df = src.parse_world_bank(_xlsx(rows, "Monthly Prices"))
    assert list(df.columns) == ["Crude oil, average", "Gold", "Natural gas, US"]
    assert df.index[1] == _ts("1960-02-29")
    assert np.isnan(df.loc["1960-01-31", "Natural gas, US"])  # "…" is missing


def test_world_bank_indices_hierarchical_headers():
    rows = [
        ["World Bank Commodity Price Data (The Pink Sheet)"],
        [None],
        [None, "Total Index", "Energy", "Non-energy **", None],
        [None, None, None, None, "Agriculture **"],
        ["1960M01", 7.6, 2.1, 18.8, 22.0],
    ]
    df = src.parse_world_bank(_xlsx(rows, "Monthly Indices"), sheet="Monthly Indices")
    assert list(df.columns) == ["Total Index", "Energy", "Non-energy", "Agriculture"]


def test_world_bank_link_discovery():
    html = b'<a href="https://thedocs.worldbank.org/x/related/CMO-Historical-Data-Monthly.xlsx">'
    assert src.world_bank_monthly_url(html).endswith("CMO-Historical-Data-Monthly.xlsx")
    with pytest.raises(ValueError):
        src.world_bank_monthly_url(b"<html>no link</html>")
