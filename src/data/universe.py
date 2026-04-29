import os
import functools
import pandas as pd

from ..constants import BUILTIN_UNIVERSE_FILES

UNIVERSE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'ticker_universes')

# Files to skip (not stock lists)
_SKIP_FILES = {'fetch_universes.py', 'README.txt'}


def list_universes() -> list[str]:
    """Return display names for all available universe CSVs."""
    names = list(BUILTIN_UNIVERSE_FILES.keys())
    try:
        files = os.listdir(UNIVERSE_DIR)
    except OSError:
        return names
    known_files = set(BUILTIN_UNIVERSE_FILES.values())
    for f in sorted(files):
        if f in _SKIP_FILES or not f.endswith('.csv') or f in known_files:
            continue
        name = f.rsplit('.', 1)[0].replace('_', ' ').title()
        names.append(name)
    return names


def _filename_for(universe_name: str) -> str:
    """Resolve display name to CSV filename."""
    fname = BUILTIN_UNIVERSE_FILES.get(universe_name)
    if not fname:
        fname = universe_name.lower().replace(' ', '_') + '.csv'
    return fname


@functools.lru_cache(maxsize=16)
def load_universe(universe_name: str) -> pd.DataFrame:
    """Load and return the full DataFrame for a universe CSV.

    Returns a DataFrame with columns: Ticker, Name, Sector, Industry.
    """
    fname = _filename_for(universe_name)
    path = os.path.join(UNIVERSE_DIR, fname)
    if not os.path.exists(path):
        return pd.DataFrame(columns=['Ticker', 'Name', 'Sector', 'Industry'])
    df = pd.read_csv(path)
    for col in ('Ticker', 'Name', 'Sector', 'Industry'):
        if col not in df.columns:
            df[col] = ''
    df['Ticker'] = df['Ticker'].astype(str).str.strip()
    df['Sector'] = df['Sector'].astype(str).str.strip()
    df['Industry'] = df['Industry'].astype(str).str.strip()
    return df[['Ticker', 'Name', 'Sector', 'Industry']]


def get_universe_sectors(universe_name: str) -> list[str]:
    """Return sorted list of unique sectors in a universe."""
    df = load_universe(universe_name)
    sectors = df['Sector'].dropna().loc[lambda s: s != ''].unique()
    return sorted(sectors)


def get_universe_industries(universe_name: str, sector: str) -> list[str]:
    """Return sorted list of unique industries for a sector in a universe."""
    df = load_universe(universe_name)
    mask = df['Sector'] == sector
    industries = df.loc[mask, 'Industry'].dropna().loc[lambda s: s != ''].unique()
    return sorted(industries)


def get_universe_tickers(universe_name: str, sector: str | None = None,
                         industry: str | None = None) -> list[str]:
    """Return tickers from a universe, optionally filtered by sector/industry."""
    df = load_universe(universe_name)
    if sector:
        df = df[df['Sector'] == sector]
    if industry:
        df = df[df['Industry'] == industry]
    return list(dict.fromkeys(df['Ticker'].tolist()))


def get_universe_stock_name(universe_name: str, ticker: str) -> str:
    """Return the company name for a ticker in a universe."""
    df = load_universe(universe_name)
    match = df.loc[df['Ticker'] == ticker, 'Name']
    if match.empty:
        return ticker
    name = str(match.iloc[0]).strip()
    return name or ticker


def search_universe_stocks(universe_name: str, query: str, limit: int = 50) -> list[str]:
    """Return matching tickers for a search query in ticker or company name.

    Search is case-insensitive and returns matches with ticker prefix hits first.
    """
    q = (query or "").strip().lower()
    if not q:
        return []

    df = load_universe(universe_name).copy()
    if df.empty:
        return []

    df["Ticker"] = df["Ticker"].astype(str)
    df["Name"] = df["Name"].astype(str)

    ticker_prefix = df["Ticker"].str.lower().str.startswith(q, na=False)
    ticker_contains = df["Ticker"].str.lower().str.contains(q, na=False)
    name_contains = df["Name"].str.lower().str.contains(q, na=False)

    matches = df[ticker_contains | name_contains].copy()
    if matches.empty:
        return []

    matches["_score"] = 0
    matches.loc[ticker_prefix, "_score"] = 2
    matches.loc[~ticker_prefix & ticker_contains, "_score"] = 1
    matches = matches.sort_values(["_score", "Ticker"], ascending=[False, True])

    tickers = matches["Ticker"].drop_duplicates().head(limit).tolist()
    return tickers


def search_all_universes(
    query: str,
    per_universe_limit: int = 12,
    total_limit: int = 80,
) -> list[dict[str, str]]:
    """Return cross-universe search matches with universe and ticker metadata."""
    q = (query or "").strip()
    if not q:
        return []

    results: list[dict[str, str]] = []
    for universe_name in list_universes():
        tickers = search_universe_stocks(universe_name, q, limit=per_universe_limit)
        if not tickers:
            continue

        df = load_universe(universe_name)
        info_by_ticker = {}
        if not df.empty:
            info_by_ticker = (
                df.drop_duplicates(subset=["Ticker"])
                .set_index("Ticker")[["Name", "Sector", "Industry"]]
                .to_dict("index")
            )

        for ticker in tickers:
            meta = info_by_ticker.get(ticker, {})
            results.append(
                {
                    "universe": universe_name,
                    "ticker": ticker,
                    "name": str(meta.get("Name", "") or ticker),
                    "sector": str(meta.get("Sector", "") or ""),
                    "industry": str(meta.get("Industry", "") or ""),
                }
            )
            if len(results) >= total_limit:
                return results

    return results


def get_sector_industry_counts(universe_name: str, sector: str) -> dict[str, int]:
    """Return {industry: stock_count} for all industries in a sector.

    'undefined' entries appear last if present.
    """
    df = load_universe(universe_name)
    df = df[df['Sector'] == sector]
    counts = df.groupby('Industry', sort=False).size().to_dict()
    # Sort alphabetically, undefined last
    sorted_counts = dict(
        sorted(counts.items(), key=lambda kv: (kv[0] == 'undefined', kv[0]))
    )
    return sorted_counts


def get_universe_sector_stock_count(universe_name: str, sector: str) -> int:
    """Return total number of stocks in a sector."""
    df = load_universe(universe_name)
    return int((df['Sector'] == sector).sum())

