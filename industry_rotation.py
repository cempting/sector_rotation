import argparse
import sys
from typing import Iterable

import pandas as pd
from financedatabase import Equities

SECTOR_ALIASES = {
    "technology": "Information Technology",
    "info tech": "Information Technology",
    "financials": "Financials",
    "finance": "Financials",
    "health care": "Health Care",
    "healthcare": "Health Care",
    "consumer discretionary": "Consumer Discretionary",
    "consumer disc": "Consumer Discretionary",
    "consumer staples": "Consumer Staples",
    "communication services": "Communication Services",
    "communication": "Communication Services",
    "real estate": "Real Estate",
    "materials": "Materials",
    "energy": "Energy",
    "utilities": "Utilities",
    "industrials": "Industrials",
}

TICKER_TO_SECTOR = {
    "XLK": "Information Technology",
    "XLV": "Health Care",
    "XLF": "Financials",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLU": "Utilities",
    "XLRE": "Real Estate",
    "XLC": "Communication Services",
}

# Known ETFs for industries (subset; can be expanded)
INDUSTRY_ETFS = {
    "Software": "VGT",
    "Semiconductors & Semiconductor Equipment": "SOXX",
    "Communications Equipment": "VOX",
    "Electronic Equipment, Instruments & Components": "VGT",
    "IT Services": "VGT",
    "Technology Hardware, Storage & Peripherals": "VGT",
    # Add more as needed
}


def normalize_sector_name(sector_or_ticker: str, available_sectors: Iterable[str]) -> str:
    normalized = sector_or_ticker.strip().upper()
    if not normalized:
        raise ValueError("Sector name or ticker must not be empty.")

    # Check if it's a ticker
    if normalized in TICKER_TO_SECTOR:
        return TICKER_TO_SECTOR[normalized]

    # Otherwise, treat as sector name
    lookup = normalized.lower()
    if lookup in SECTOR_ALIASES:
        return SECTOR_ALIASES[lookup]

    exact_matches = [s for s in available_sectors if s.lower() == lookup]
    if exact_matches:
        return exact_matches[0]

    fuzzy_matches = [s for s in available_sectors if lookup in s.lower()]
    if len(fuzzy_matches) == 1:
        return fuzzy_matches[0]

    raise ValueError(
        f"Unknown sector '{sector_or_ticker}'. Available sectors are: {', '.join(sorted(available_sectors))}. "
        f"Or use a ticker like: {', '.join(sorted(TICKER_TO_SECTOR.keys()))}"
    )


def load_equities() -> Equities:
    return Equities()


def fetch_sector_industries(sector: str) -> pd.Series:
    equities = load_equities()
    industries = equities.options("industry", sector=sector)
    return pd.Series(sorted(industries.tolist()), name="industry")


def fetch_industry_counts(sector: str) -> pd.Series:
    equities = load_equities()
    selected = equities.select(sector=sector, exclude_exchanges=False)
    return selected["industry"].dropna().value_counts().sort_values(ascending=False)


def render_industry_list(sector: str, industries: pd.Series, industry_counts: pd.Series) -> None:
    print(f"Sector: {sector}")
    print(f"Industries found: {len(industries)}")
    print()

    if industries.empty:
        print("No industries found for the given sector.")
        return

    for industry in industries:
        count = industry_counts.get(industry, 0)
        etf = INDUSTRY_ETFS.get(industry, "N/A")
        etf_str = f" (ETF: {etf})" if etf != "N/A" else ""
        print(f"- {industry} ({count} equities){etf_str}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Retrieve all industries for a given sector, with ETF suggestions."
    )
    parser.add_argument(
        "sector_or_ticker",
        help="Sector name (e.g., 'Technology') or ticker (e.g., 'XLK') to query.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    equities = load_equities()
    available_sectors = equities.options("sector")

    try:
        sector = normalize_sector_name(args.sector_or_ticker, available_sectors)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    industries = fetch_sector_industries(sector)
    industry_counts = fetch_industry_counts(sector)
    render_industry_list(sector, industries, industry_counts)


if __name__ == "__main__":
    main()
