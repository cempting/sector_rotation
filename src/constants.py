from typing import Dict
import re

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

US_INDUSTRY_ETFS: Dict[str, str] = {
    "Advertising": "XLC",
    "Aerospace & Defense": "ITA",
    "Airlines": "JETS",
    "Air Freight & Logistics": "IYT",
    "Agricultural & Farm Machinery": "MOO",
    "Agricultural Products & Services": "MOO",
    "Apparel": "XLY",
    "Apparel Retail": "XRT",
    "Apparel, Accessories & Luxury Goods": "XLY",
    "Alternative Energy": "ICLN",
    "Asset Management & Custody Banks": "IAI",
    "Banks": "KBE",
    "Beverages": "XLP",
    "Beverages - Brewers": "XLP",
    "Biotechnology": "IBB",
    "Broadline Retail": "XRT",
    "Capital Markets": "IAI",
    "Cable & Satellite": "XLC",
    "Commercial Services & Supplies": "XLI",
    "Chemicals": "IYM",
    "Communications Equipment": "IYZ",
    "Computer & Electronics Retail": "XRT",
    "Construction & Engineering": "XLI",
    "Construction Materials": "XLB",
    "Consumer Electronics": "XLY",
    "Consumer Finance": "XLF",
    "Consumer Staples Merchandise Retail": "XLP",
    "Cloud Computing": "WCLD",
    "Cybersecurity": "CIBR",
    "Construction Machinery & Heavy Transportation Equipment": "XLI",
    "Department Stores": "XRT",
    "Distillers & Vintners": "XLP",
    "Diversified Financial Services": "XLF",
    "Diversified Banks": "KBE",
    "Diversified Telecommunication Services": "IYZ",
    "Drug Manufacturers - Specialty & Generic": "XLV",
    "Electronic Components": "IYW",
    "Electrical Components & Equipment": "XLI",
    "Electric Utilities": "XLU",
    "Energy": "XLE",
    "Energy Equipment & Services": "IEZ",
    "Entertainment": "XLC",
    "Equity Real Estate Investment Trusts (REITs)": "VNQ",
    "Financials": "XLF",
    "Food & Staples Retailing": "XLP",
    "Food Distribution": "XLP",
    "Health Care Equipment & Supplies": "IHI",
    "Food Products": "XLP",
    "Health Care Providers & Services": "XLV",
    "Footwear & Accessories": "XLY",
    "Health Care Equipment": "IHI",
    "Health Care Providers": "IHF",
    "Health Care Technology": "VHT",
    "Health Care Services": "XLV",
    "Healthcare": "VHT",
    "Homebuilding": "XHB",
    "Homefurnishing Retail": "XLY",
    "Healthcare Plans": "XLV",
    "Home Improvement": "XHB",
    "Hotel & Resort REITs": "VNQ",
    "Home Improvement Retail": "XHB",
    "Household Durables": "XLY",
    "Hotels Restaurants & Leisure": "PEJ",
    "Hotels, Resorts & Cruise Lines": "PEJ",
    "Household Products": "XLP",
    "Industrial Machinery & Supplies & Components": "XLI",
    "Industrial REITs": "VNQ",
    "Industrial Machinery": "XLI",
    "Industrial Conglomerates": "XLI",
    "Internet & Direct Marketing Retail": "ONLN",
    "Internet Services & Infrastructure": "FDN",
    "Industrial Gases": "XLB",
    "Internet": "FDN",
    "Internet Retail": "ONLN",
    "IT Consulting & Other Services": "IGV",
    "IT Services": "IGV",
    "Insurance": "KIE",
    "Insurance Brokers": "KIE",
    "Insurance - Diversified": "KIE",
    "Insurance - Life": "KIE",
    "Interactive Home Entertainment": "XLC",
    "Insurance - Reinsurance": "KIE",
    "Marine": "IYT",
    "Investment Banking & Brokerage": "IAI",
    "Interactive Media & Services": "XLC",
    "Medical Care Facilities": "XLV",
    "Metal, Glass & Plastic Containers": "XLB",
    "Multi-Family Residential REITs": "VNQ",
    "Media": "XLC",
    "Media": "XLC",
    "Multi-line Insurance": "KIE",
    "Metals & Mining": "XME",
    "Multi-Utilities": "XLU",
    "Multi-Sector Holdings": "XLF",
    "Movies & Entertainment": "XLC",
    "Oil & Gas E&P": "XOP",
    "Oil & Gas Equipment & Services": "IEZ",
    "Office REITs": "VNQ",
    "Oil & Gas Exploration & Production": "XOP",
    "Oil & Gas Integrated": "XLE",
    "Oil & Gas Refining & Marketing": "XLE",
    "Paper & Forest Products": "XLB",
    "Paper & Paper Products": "XLB",
    "Passenger Transportation": "IYT",
    "Professional Services": "XLI",
    "Passenger Ground Transportation": "IYT",
    "Personal Care Products": "XLP",
    "Pharmaceuticals": "PPH",
    "Professional Services": "XLI",
    "Real Estate Investment Trusts": "VNQ",
    "Rail Transportation": "IYT",
    "Real Estate": "VNQ",
    "Real Estate - Development": "VNQ",
    "Real Estate Management & Development": "VNQ",
    "Regional Banks": "KRE",
    "Restaurants": "PEJ",
    "Retail": "XRT",
    "Retail REITs": "VNQ",
    "Semiconductors": "SMH",
    "Semiconductor Materials & Equipment": "SMH",
    "Soft Drinks & Non-alcoholic Beverages": "XLP",
    "Telecom Tower REITs": "VNQ",
    "Software": "IGV",
    "Systems Software": "IGV",
    "Transportation Infrastructure": "PAVE",
    "Transaction & Payment Processing Services": "IPAY",
    "Trading Companies & Distributors": "XLI",
    "Thrifts & Mortgage Finance": "KBE",
    "Textiles, Apparel & Luxury Goods": "XLY",
    "Wireless Telecommunication Services": "IYZ",
    "Telecom": "IYZ",
    "Telecommunications": "IYZ",
    "Tobacco": "XLP",
    "Transportation": "IYT",
    "Utilities": "XLU",
    "Utilities - Diversified": "XLU",
    "Utilities - Regulated Electric": "XLU",
    "Utilities - Regulated Water": "XLU",
    "Utilities - Renewable": "ICLN",
    "Commodity Chemicals": "IYM",
    "Electrical Equipment": "XLI",
    "Financial Exchanges & Data": "IAI",
    "Food Distributors": "XLP",
    "Footwear": "XLY",
    "Fertilizers & Agricultural Chemicals": "MOO",
    "Health Care Distributors": "XLV",
    "Health Care Facilities": "XLV",
    "Health Care REITs": "VNQ",
    "Health Care Supplies": "IHI",
    "Independent Power Producers & Energy Traders": "ICLN",
    "Independent Power and Renewable Electricity Producers": "ICLN",
    "Life & Health Insurance": "KIE",
    "Medical Care Facilities": "XLV",
    "Gold": "GLD",
    "Copper": "COPX",
    "Steel": "XME",
    "Other Industrial Metals & Mining": "XME",
    "Other Precious Metals & Mining": "GLD",
    "Oil, Gas & Consumable Fuels": "XLE",
    "Pharmaceutical Retailers": "XLV",
    "Real Estate Services": "VNQ",
    "Semiconductors & Semiconductor Equipment": "SMH",
    "Specialty Chemicals": "XLB",
    "Telecom Services": "IYZ",
    "Technology Hardware, Storage & Peripherals": "XLK",
    "Application Software": "IGV",
    "Building Products": "XHB",
    "Gas Utilities": "XLU",
    "Heavy Electrical Equipment": "XLI",
    "Integrated Oil & Gas": "XLE",
    "Managed Health Care": "XLV",
    "Road & Rail": "IYT",
    "Specialty Retail": "XRT",
    "Communication Services": "XLC",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Industrials": "XLI",
    "Information Technology": "XLK",
    "Materials": "XLB",
    "Commerce & Industry": "^HSI",
    "Finance": "^HSNF",
    "Properties": "^HSNP",
    "Asset Management": "IAI",
    "Banks - Diversified": "KBE",
    "Banks - Regional": "KRE",
    "Financial Conglomerates": "XLF",
    "Diagnostics & Research": "IBB",
    "Electrical Equipment & Parts": "XLI",
    "Farm Products": "MOO",
    "Financial Data & Stock Exchanges": "IAI",
    "Other Industrial Metals & Mining": "XME",
    "Packaged Foods": "XLP",
    "Real Estate Services": "VNQ",
    "Rental & Leasing Services": "XLI",
    "Residential Construction": "XHB",
    "Insurance - Specialty": "KIE",
    "Luxury Goods": "XLY",
    "Other Precious Metals & Mining": "GLD",
    "Pharmaceutical Retailers": "XLV",
    "REIT - Diversified": "VNQ",
    "Specialty Chemicals": "XLB",
    "Thermal Coal": "XLE",
}

EUROPE_INDUSTRY_ETFS: Dict[str, str] = {
    "Automobiles and Parts": "EXV5.DE",
    "Banks": "EXV1.DE",
    "Biotechnology": "EXV4.DE",
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
    "Semiconductors": "EXV3.DE",
    "Software": "EXV3.DE",
    "Telecommunications": "EXV2.DE",
    "Travel and Leisure": "EXV9.DE",
    "Utilities": "EXH9.DE",
}


def _normalize_market_label(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(label or "").lower()).strip()


def _canonical_industry_key(industry_name: str) -> str:
    normalized = _normalize_market_label(industry_name)
    if not normalized:
        return ""

    patterns = [
        ("advertis", "Advertising"),
        ("aerospace", "Aerospace & Defense"),
        ("defense", "Aerospace & Defense"),
        ("air freight", "Air Freight & Logistics"),
        ("airline", "Airlines"),
        ("alternative energy", "Alternative Energy"),
        ("agricultural & farm machinery", "Agricultural & Farm Machinery"),
        ("agricultural products", "Agricultural Products & Services"),
        ("agricultural", "Agricultural Products & Services"),
        ("apparel retail", "Apparel Retail"),
        ("apparel", "Apparel"),
        ("asset management", "Asset Management & Custody Banks"),
        ("broadline retail", "Broadline Retail"),
        ("bank", "Banks"),
        ("beverage", "Beverages"),
        ("broadcast", "Media"),
        ("biotech", "Biotechnology"),
        ("capital market", "Capital Markets"),
        ("cable", "Cable & Satellite"),
        ("chemic", "Chemicals"),
        ("commercial services", "Commercial Services & Supplies"),
        ("communications equipment", "Communications Equipment"),
        ("cloud", "Cloud Computing"),
        ("construction & engineering", "Construction & Engineering"),
        ("construction materials", "Construction Materials"),
        ("cyber", "Cybersecurity"),
        ("consumer electronics", "Consumer Electronics"),
        ("consumer finance", "Consumer Finance"),
        ("consumer staples merchandise retail", "Consumer Staples Merchandise Retail"),
        ("electronic component", "Electronic Components"),
        ("electrical component", "Electrical Components & Equipment"),
        ("electric utilit", "Electric Utilities"),
        ("heavy transportation equipment", "Construction Machinery & Heavy Transportation Equipment"),
        ("equipment services", "Energy Equipment & Services"),
        ("entertainment", "Entertainment"),
        ("equity real estate investment trusts", "Equity Real Estate Investment Trusts (REITs)"),
        ("financial services", "Financials"),
        ("health care equipment", "Health Care Equipment"),
        ("health care equipment & supplies", "Health Care Equipment & Supplies"),
        ("healthcare equipment", "Health Care Equipment"),
        ("health care provider", "Health Care Providers"),
        ("healthcare provider", "Health Care Providers"),
        ("health care providers & services", "Health Care Providers & Services"),
        ("health care service", "Health Care Services"),
        ("healthcare plan", "Healthcare Plans"),
        ("health care technology", "Health Care Technology"),
        ("home improvement", "Home Improvement"),
        ("homebuilding", "Homebuilding"),
        ("homefurnishing", "Homefurnishing Retail"),
        ("household product", "Household Products"),
        ("household durable", "Household Durables"),
        ("hotel", "Hotels Restaurants & Leisure"),
        ("industrial conglomerate", "Industrial Conglomerates"),
        ("industrial gas", "Industrial Gases"),
        ("industrial machinery & supplies", "Industrial Machinery & Supplies & Components"),
        ("industrial reit", "Industrial REITs"),
        ("machinery", "Machinery"),
        ("media", "Media"),
        ("medical care facilities", "Medical Care Facilities"),
        ("movies", "Movies & Entertainment"),
        ("multi utility", "Multi-Utilities"),
        ("multi sector holdings", "Multi-Sector Holdings"),
        ("multi-line insurance", "Multi-line Insurance"),
        ("oil gas e&p", "Oil & Gas E&P"),
        ("media", "Media"),
        ("mining", "Metals & Mining"),
        ("metal", "Metals & Mining"),
        ("office reit", "Office REITs"),
        ("paper & forest", "Paper & Forest Products"),
        ("paper & paper", "Paper & Paper Products"),
        ("passenger ground transportation", "Passenger Ground Transportation"),
        ("personal care", "Personal Care Products"),
        ("payment processing", "Transaction & Payment Processing Services"),
        ("internet retail", "Internet Retail"),
        ("internet", "Internet"),
        ("insurance", "Insurance"),
        ("insurance brokers", "Insurance Brokers"),
        ("investment banking", "Investment Banking & Brokerage"),
        ("interactive media", "Interactive Media & Services"),
        ("interactive home entertainment", "Interactive Home Entertainment"),
        ("it consulting", "IT Consulting & Other Services"),
        ("it services", "IT Services"),
        ("marine", "Marine"),
        ("oil gas exploration", "Oil & Gas Exploration & Production"),
        ("oil gas equipment", "Oil & Gas Equipment & Services"),
        ("oil gas integrated", "Oil & Gas Integrated"),
        ("oil gas refining", "Oil & Gas Refining & Marketing"),
        ("pharmaceutical", "Pharmaceuticals"),
        ("pharma", "Pharmaceuticals"),
        ("real estate investment trusts", "Real Estate Investment Trusts"),
        ("real estate", "Real Estate"),
        ("reit", "Real Estate"),
        ("rail transport", "Rail Transportation"),
        ("regional bank", "Regional Banks"),
        ("restaurants", "Restaurants"),
        ("retail", "Retail"),
        ("semiconductor", "Semiconductors"),
        ("specialty retail", "Specialty Retail"),
        ("software", "Software"),
        ("soft drink", "Soft Drinks & Non-alcoholic Beverages"),
        ("systems software", "Systems Software"),
        ("telecom", "Telecom"),
        ("tower reit", "Telecom Tower REITs"),
        ("tobacco", "Tobacco"),
        ("transport", "Transportation"),
        ("trading companies", "Trading Companies & Distributors"),
        ("utilities - renewable", "Utilities - Renewable"),
        ("utilit", "Utilities"),
        ("wireless telecommunication", "Wireless Telecommunication Services"),
    ]
    for needle, canonical in patterns:
        if needle in normalized:
            return canonical
    return str(industry_name).strip()


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

MARKET_INDUSTRY_CONFIG: Dict[str, Dict[str, Dict[str, str]]] = {
    "us": {
        "industry_proxies": US_INDUSTRY_ETFS,
        "sector_fallbacks": US_SECTOR_ETFS,
    },
    "eu": {
        "industry_proxies": {**US_INDUSTRY_ETFS, **EUROPE_INDUSTRY_ETFS},
        "sector_fallbacks": EUROPE_SECTOR_ETFS,
    },
    "asia": {
        "industry_proxies": US_INDUSTRY_ETFS,
        "sector_fallbacks": ASIA_SECTOR_PROXIES,
    },
    "asx": {
        "industry_proxies": US_INDUSTRY_ETFS,
        "sector_fallbacks": ASX_SECTOR_INDICES,
    },
    "brazil": {
        "industry_proxies": US_INDUSTRY_ETFS,
        "sector_fallbacks": MORNINGSTAR_SECTOR_ETFS,
    },
    "jse": {
        "industry_proxies": US_INDUSTRY_ETFS,
        "sector_fallbacks": MORNINGSTAR_SECTOR_ETFS,
    },
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


def resolve_industry_proxy_ticker(
    universe_name: str,
    sector_name: str | None,
    industry_name: str,
) -> str | None:
    """Resolve an industry to a representative ETF or proxy ticker.

    The resolver prefers a market-specific industry ETF when available and falls
    back to the sector proxy if the industry has no direct representation.
    """
    market = get_market_for_universe(universe_name)
    market_cfg = MARKET_INDUSTRY_CONFIG.get(market, MARKET_INDUSTRY_CONFIG["us"])
    proxies = market_cfg.get("industry_proxies", {})

    canonical = _canonical_industry_key(industry_name)
    ticker = proxies.get(canonical)
    if ticker:
        return ticker

    if industry_name:
        normalized = _normalize_market_label(industry_name)
        for proxy_name, proxy_ticker in proxies.items():
            proxy_normalized = _normalize_market_label(proxy_name)
            if proxy_normalized == normalized or proxy_normalized in normalized or normalized in proxy_normalized:
                return proxy_ticker

    if sector_name:
        sector_proxy = resolve_sector_proxy_ticker(universe_name, sector_name)
        if sector_proxy:
            return sector_proxy

    sector_fallbacks = market_cfg.get("sector_fallbacks", {})
    if sector_name:
        return sector_fallbacks.get(sector_name)

    return None


# Backward compatibility for older imports.
SECTORS: Dict[str, str] = US_SECTOR_ETFS
