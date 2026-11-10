"""Raw data sources: one parser and one fetcher per provider.

Parsers take the raw payload (bytes) and return tidy data indexed by
month-end ``Timestamp``. They never touch the network, so the tests run
offline on synthetic fixtures (LESSONS C2-C3). Fetchers only download and
hand the bytes to the parser.

Every source here is free. None of their data is committed to the repo:
downloads land in the gitignored ``systematic/data/`` cache. MSCI and AQR
data in particular are for personal research use only.
"""

from __future__ import annotations

import io
import json
import re
import time
import zipfile

import numpy as np
import pandas as pd
import requests

USER_AGENT = "portfolio-bot-research/0.1"
TIMEOUT = 60

MSCI_URL = (
    "https://app2.msci.com/products/service/index/indexmaster/getLevelDataForGraph"
    "?currency_symbol={currency}&index_variant={variant}&start_date={start}"
    "&end_date={end}&data_frequency=END_OF_MONTH&index_codes={code}"
)
MSCI_EARLIEST = "19970101"  # the endpoint refuses earlier start dates
KEN_FRENCH_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/{name}_CSV.zip"
AQR_URL = "https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/{name}.xlsx"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
ECB_URL = "https://data-api.ecb.europa.eu/service/data/{flow}/{key}?format=csvdata"
WORLD_BANK_PAGE = "https://www.worldbank.org/en/research/commodity-markets"

_KF_DATE = re.compile(r"^\d{6}$")
_WB_DATE = re.compile(r"^\d{4}M\d{2}$")


# --------------------------------------------------------------------------
# shared helpers
# --------------------------------------------------------------------------

def http_get(url: str, *, retries: int = 3, timeout: int = TIMEOUT) -> bytes:
    """GET with retries and exponential backoff; raises on final failure."""
    last: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as exc:
            last = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"download failed after {retries} attempts: {url}") from last


def to_month_end(index) -> pd.DatetimeIndex:
    """Normalise any date-like index to calendar month-end, midnight."""
    idx = pd.DatetimeIndex(pd.to_datetime(index)).normalize()
    return idx + pd.offsets.MonthEnd(0)


# --------------------------------------------------------------------------
# MSCI end-of-month index levels (1997+)
# --------------------------------------------------------------------------

def parse_msci(payload: bytes) -> pd.Series:
    """MSCI ``getLevelDataForGraph`` JSON -> month-end index levels."""
    data = json.loads(payload)
    if "error_message" in data:
        raise ValueError(f"MSCI error: {str(data['error_message']).strip()}")
    levels = data["indexes"]["INDEX_LEVELS"]
    if not levels:
        raise ValueError("MSCI returned no index levels")
    dates = to_month_end([str(x["calc_date"]) for x in levels])
    values = [float(x["level_eod"]) for x in levels]
    s = pd.Series(values, index=dates, name="level").sort_index()
    return s[~s.index.duplicated(keep="last")]


def fetch_msci(code: str, *, currency: str = "USD", variant: str = "NETR",
               start: str = MSCI_EARLIEST, end: str | None = None) -> pd.Series:
    end = end or pd.Timestamp.today().strftime("%Y%m%d")
    url = MSCI_URL.format(code=code, currency=currency, variant=variant,
                          start=start, end=end)
    return parse_msci(http_get(url))


# --------------------------------------------------------------------------
# Ken French data library (CSV inside a zip, values in percent)
# --------------------------------------------------------------------------

def parse_ken_french(payload: bytes) -> pd.DataFrame:
    """First (monthly) table of a Ken French CSV zip, converted to decimals.

    The file starts with free-text notes, then a header line whose first cell
    is empty (",Mkt-RF,SMB,HML,RF"), then rows keyed YYYYMM. The monthly table
    ends at the first row that is not YYYYMM (a blank line before the annual
    table). Missing values (-99.99 / -999) become NaN.
    """
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        lines = zf.read(name).decode("latin-1").splitlines()

    header: list[str] | None = None
    rows: list[list[str]] = []
    for i, line in enumerate(lines):
        cells = [c.strip() for c in line.split(",")]
        if header is None:
            nxt = lines[i + 1].split(",")[0].strip() if i + 1 < len(lines) else ""
            if line.startswith(",") and _KF_DATE.match(nxt):
                header = [c for c in cells[1:] if c]
            continue
        if not _KF_DATE.match(cells[0]):
            break
        rows.append(cells[: len(header) + 1])
    if header is None or not rows:
        raise ValueError("Ken French: monthly table not found")

    dates = to_month_end(pd.to_datetime([r[0] for r in rows], format="%Y%m"))
    values = np.array([[float(v) for v in r[1:]] for r in rows])
    values[values <= -99.99] = np.nan
    return pd.DataFrame(values / 100.0, index=dates, columns=header)


def fetch_ken_french(name: str) -> pd.DataFrame:
    return parse_ken_french(http_get(KEN_FRENCH_URL.format(name=name)))


# --------------------------------------------------------------------------
# AQR data sets (xlsx, values already in decimals)
# --------------------------------------------------------------------------

def parse_aqr(payload: bytes, sheet: str | int = 0) -> pd.DataFrame:
    """AQR data-set sheet -> month-end DataFrame.

    The sheet opens with notes; the table header is the first row whose first
    cell is empty, which has labels to its right, and which is followed by a
    date in the first column.
    """
    raw = pd.read_excel(io.BytesIO(payload), sheet_name=sheet, header=None)
    first_col = pd.to_datetime(raw.iloc[:, 0], errors="coerce", format="mixed")
    header_row = None
    for i in range(len(raw) - 1):
        if pd.isna(raw.iat[i, 0]) and raw.iloc[i, 1:].notna().any() and pd.notna(first_col.iat[i + 1]):
            header_row = i
            break
    if header_row is None:
        raise ValueError("AQR: table header not found")

    labels = raw.iloc[header_row, 1:]
    keep = [j for j, lab in enumerate(labels, start=1) if pd.notna(lab) and str(lab).strip()]
    body = raw.iloc[header_row + 1:]
    body = body[first_col.iloc[header_row + 1:].notna()]
    data = body.iloc[:, keep].apply(pd.to_numeric, errors="coerce")
    data.columns = [str(raw.iat[header_row, j]).strip() for j in keep]
    data.index = to_month_end(first_col.loc[body.index])
    return data.dropna(how="all").astype(float)


def fetch_aqr(name: str, sheet: str | int = 0) -> pd.DataFrame:
    return parse_aqr(http_get(AQR_URL.format(name=name)), sheet=sheet)


# --------------------------------------------------------------------------
# FRED (fredgraph CSV; no API key needed)
# --------------------------------------------------------------------------

def parse_fred(payload: bytes) -> pd.Series:
    """FRED CSV -> Series on the file's own dates ('.' = missing, dropped)."""
    df = pd.read_csv(io.BytesIO(payload))
    if df.shape[1] < 2:
        raise ValueError("FRED: unexpected CSV layout")
    values = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    s = pd.Series(values.to_numpy(), index=pd.to_datetime(df.iloc[:, 0]),
                  name=str(df.columns[1]))
    return s.dropna().sort_index()


def fetch_fred(series: str) -> pd.Series:
    return parse_fred(http_get(FRED_URL.format(series=series)))


# --------------------------------------------------------------------------
# ECB Data Portal (SDMX CSV)
# --------------------------------------------------------------------------

def parse_ecb(payload: bytes) -> pd.Series:
    """ECB csvdata -> month-end Series (monthly series only)."""
    df = pd.read_csv(io.BytesIO(payload))
    if "TIME_PERIOD" not in df or "OBS_VALUE" not in df:
        raise ValueError("ECB: TIME_PERIOD/OBS_VALUE columns missing")
    values = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
    s = pd.Series(values.to_numpy(), index=to_month_end(df["TIME_PERIOD"]), name="value")
    return s.dropna().sort_index()


def fetch_ecb(flow: str, key: str) -> pd.Series:
    return parse_ecb(http_get(ECB_URL.format(flow=flow, key=key)))


# --------------------------------------------------------------------------
# World Bank commodity prices, the "Pink Sheet" (xlsx, 1960+)
# --------------------------------------------------------------------------

def parse_world_bank(payload: bytes, sheet: str = "Monthly Prices") -> pd.DataFrame:
    """Pink Sheet monthly sheet -> month-end DataFrame (nominal USD).

    Dates look like ``1960M01``. Column names sit in the rows above the first
    date; each column takes its first non-empty label that is not a unit line
    such as ``($/bbl)``. Footnote markers (``**``) are stripped and ``…``
    means missing.
    """
    raw = pd.read_excel(io.BytesIO(payload), sheet_name=sheet, header=None)
    col0 = raw.iloc[:, 0].astype(str).str.strip()
    date_rows = raw.index[col0.str.match(_WB_DATE)]
    if len(date_rows) == 0:
        raise ValueError("World Bank: no YYYYMmm dates found")
    first = date_rows[0]

    names: dict[int, str] = {}
    for j in range(1, raw.shape[1]):
        for i in range(first):
            cell = raw.iat[i, j]
            if pd.isna(cell):
                continue
            label = str(cell).replace("*", "").strip()
            if label and not label.startswith("("):
                names[j] = label
                break

    body = raw.loc[date_rows]
    data = body[list(names)].apply(pd.to_numeric, errors="coerce")
    data.columns = [names[j] for j in names]
    data.index = to_month_end(pd.to_datetime(col0.loc[date_rows], format="%YM%m"))
    return data.astype(float)


def world_bank_monthly_url(page_html: bytes) -> str:
    """Find the current CMO-Historical-Data-Monthly.xlsx link (it moves)."""
    match = re.search(rb'href="([^"]*CMO-Historical-Data-Monthly\.xlsx)"', page_html)
    if not match:
        raise ValueError("World Bank: monthly Pink Sheet link not found")
    return match.group(1).decode()


def fetch_world_bank(sheet: str = "Monthly Prices") -> pd.DataFrame:
    url = world_bank_monthly_url(http_get(WORLD_BANK_PAGE))
    return parse_world_bank(http_get(url), sheet=sheet)
