"""Published figures used as known answers for the data checks (Gate G2).

All values are calendar-year net total returns in percent, in USD, copied
from MSCI index factsheets dated 30 October 2026:
https://www.msci.com/documents/10199/255599/msci-world-momentum-index-usd-net.pdf
https://www.msci.com/documents/10199/255599/msci-world-quality-index-usd-net.pdf
(the MSCI World column appears on both).
"""

MSCI_WORLD_USD_NET = {
    2013: 26.68, 2014: 4.94, 2015: -0.87, 2016: 7.51, 2017: 22.40,
    2018: -8.71, 2019: 27.67, 2020: 15.90, 2021: 21.82, 2022: -18.14,
    2023: 23.79, 2024: 18.67, 2025: 21.09,
}

MSCI_WORLD_MOMENTUM_USD_NET = {
    2013: 29.66, 2014: 6.55, 2015: 4.06, 2016: 4.19, 2017: 32.09,
    2018: -2.76, 2019: 27.68, 2020: 28.26, 2021: 14.64, 2022: -17.79,
    2023: 11.75, 2024: 30.15, 2025: 21.33,
}

MSCI_WORLD_QUALITY_USD_NET = {
    2013: 27.06, 2014: 8.45, 2015: 3.71, 2016: 4.55, 2017: 25.96,
    2018: -5.50, 2019: 36.08, 2020: 22.20, 2021: 25.66, 2022: -22.21,
    2023: 32.39, 2024: 18.44, 2025: 16.54,
}

# Months with moves above 25% that are real, not data errors. Each entry has
# to be checked by a human before it goes in (LESSONS C3).
KNOWN_BIG_MONTHS: dict[str, set[str]] = {}
