from typing import Dict, Tuple

TREND_LOOKBACK_DAYS = 5
MIN_TREND_LENGTH = 4
TREND_SLOPE_THRESHOLD = 0
VOLUME_BAR_ALPHA = 0.3
VOLUME_BAR_WIDTH = 1.5
VOLUME_SCALE_FACTOR = 2
DEFAULT_FONTSIZE = 7
SECTOR_FIGSIZE = (5, 3)
INDUSTRY_FIGSIZE = (4, 2.5)
FIGSIZE_FONTSIZE_THRESHOLD = 5
SMALL_FONTSIZE = 6
LINE_WIDTH = 1.2
INDEX_START_VALUE = 100
DEFAULT_TOP_TICKERS = 50
SECTOR_GRID_COLS = 2
INDUSTRY_GRID_COLS = 2
TICKER_PERIOD = "1y"

SECTORS: Dict[str, str] = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Consumer Disc": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication": "XLC",
}

SECTOR_NAME_MAP: Dict[str, str] = {
    "Technology": "Information Technology",
    "Healthcare": "Health Care",
    "Consumer Disc": "Consumer Discretionary",
    "Communication": "Communication Services",
}
