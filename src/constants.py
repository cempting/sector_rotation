from typing import Dict

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

# Universe onboarding: add new display name -> CSV filename here.
BUILTIN_UNIVERSE_FILES: Dict[str, str] = {
    "S&P 100": "sp100.csv",
    "S&P 500": "sp500.csv",
    "Russell 2000": "russell2000.csv",
    "NASDAQ": "nasdaq.csv",
    "NYSE": "nyse.csv",
    "STOXX Europe 600": "stoxx600.csv",
    "Hang Seng": "hangseng.csv",
    # new markets
    "ASX 200": "asx200.csv",
    "Ibovespa": "ibovespa.csv",
    "JSE Top 40": "jse_top40.csv",
}

US_SECTOR_ETFS: Dict[str, str] = {
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

EUROPE_SECTOR_ETFS: Dict[str, str] = {
    # iShares STOXX Europe 600 sector UCITS ETFs (Xetra)
    "Automobiles and Parts": "EXV5.DE",
    "Banks": "EXV1.DE",
    "Basic Resources": "EXV6.DE",
    "Chemicals": "EXV7.DE",
    "Construction and Materials": "EXV8.DE",
    "Consumer Products and Services": "EXH7.DE",
    "Energy": "EXH1.DE",
    "Financial Services": "EXH2.DE",
    "Food, Beverage and Tobacco": "EXH3.DE",
    "Health Care": "EXV4.DE",
    "Industrial Goods and Services": "EXH4.DE",
    "Insurance": "EXH5.DE",
    "Media": "EXH6.DE",
    "Personal Care, Drug and Grocery Stores": "EXH7.DE",
    "Real Estate": "EXI5.DE",
    "Retail": "EXH8.DE",
    "Technology": "EXV3.DE",
    "Telecommunications": "EXV2.DE",
    "Travel and Leisure": "EXV9.DE",
    "Utilities": "EXH9.DE",
}

ASIA_SECTOR_PROXIES: Dict[str, str] = {
    # Hang Seng sector proxies (index symbols where sector ETFs are limited)
    "Commerce & Industry": "^HSI",
    "Finance": "^HSNF",
    "Properties": "^HSNP",
    "Utilities": "^HSNU",
}

# ASX 200 — S&P/ASX GICS sector accumulation indices (Yahoo Finance)
ASX_SECTOR_INDICES: Dict[str, str] = {
    "Communication Services": "^AXTJ",
    "Consumer Discretionary": "^AXDJ",
    "Consumer Staples": "^AXSJ",
    "Energy": "^AXEJ",
    "Financials": "^AXFJ",
    "Health Care": "^AXHJ",
    "Healthcare": "^AXHJ",
    "Industrials": "^AXIJ",
    "Information Technology": "^AXNJ",
    "Materials": "^AXMJ",
    "Real Estate": "^AXPJ",
    "Utilities": "^AXUJ",
}

# Morningstar sector labels (used by yfinance for Brazil/JSE) → SPDR ETF proxies
MORNINGSTAR_SECTOR_ETFS: Dict[str, str] = {
    "Basic Materials": "XLB",
    "Communication Services": "XLC",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Energy": "XLE",
    "Financial Services": "XLF",
    "Healthcare": "XLV",
    "Industrials": "XLI",
    "Real Estate": "XLRE",
    "Technology": "XLK",
    "Utilities": "XLU",
}

UNIVERSE_MARKET: Dict[str, str] = {
    "S&P 100": "us",
    "S&P 500": "us",
    "Russell 2000": "us",
    "NASDAQ": "us",
    "NYSE": "us",
    "STOXX Europe 600": "eu",
    "Hang Seng": "asia",
    "ASX 200": "asx",
    "Ibovespa": "brazil",
    "JSE Top 40": "jse",
}

MARKET_SECTOR_CONFIG: Dict[str, Dict[str, Dict[str, str]]] = {
    "us": {
        "sector_proxies": US_SECTOR_ETFS,
        "aliases": SECTOR_NAME_MAP,
    },
    "eu": {
        "sector_proxies": EUROPE_SECTOR_ETFS,
        "aliases": {},
    },
    "asia": {
        "sector_proxies": ASIA_SECTOR_PROXIES,
        "aliases": {},
    },
    "asx": {
        "sector_proxies": ASX_SECTOR_INDICES,
        "aliases": {},
    },
    "brazil": {
        "sector_proxies": MORNINGSTAR_SECTOR_ETFS,
        "aliases": {},
    },
    "jse": {
        "sector_proxies": MORNINGSTAR_SECTOR_ETFS,
        "aliases": {},
    },
}


def get_market_for_universe(universe_name: str) -> str:
    """Return market key for a universe; defaults to US for unknown universes."""
    return UNIVERSE_MARKET.get(universe_name, "us")


def list_supported_markets() -> list[str]:
    """Return configured market keys that can resolve sector proxies."""
    return sorted(MARKET_SECTOR_CONFIG.keys())


def resolve_sector_proxy_ticker(universe_name: str, sector_name: str) -> str | None:
    """Resolve a sector to a market-appropriate ETF/proxy ticker.

    US universes use SPDR sector ETFs, STOXX Europe 600 uses iShares STOXX Europe
    sector UCITS ETFs, and Hang Seng uses sector proxy indices.
    """
    market = get_market_for_universe(universe_name)
    market_cfg = MARKET_SECTOR_CONFIG.get(market, MARKET_SECTOR_CONFIG["us"])
    proxies = market_cfg.get("sector_proxies", {})
    aliases = market_cfg.get("aliases", {})

    ticker = proxies.get(sector_name)
    if ticker:
        return ticker

    for short, long_name in aliases.items():
        if long_name == sector_name:
            return proxies.get(short)

    return None


# Backward compatibility for older imports.
SECTORS: Dict[str, str] = US_SECTOR_ETFS
