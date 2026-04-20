import os
import functools
import pandas as pd

UNIVERSE_DIR = os.path.join(os.path.dirname(__file__), '..', 'ticker_universes')

# Maps display name -> csv filename
_BUILTIN_UNIVERSES = {
    'S&P 100': 'sp100.csv',
    'S&P 500': 'sp500.csv',
    'Russell 2000': 'russell2000.csv',
    'STOXX Europe 600': 'stoxx600.csv',
    'Hang Seng': 'hangseng.csv',
}

# Files to skip (not stock lists)
_SKIP_FILES = {'fetch_universes.py', 'README.txt'}


def list_universes() -> list[str]:
    """Return display names for all available universe CSVs."""
    names = list(_BUILTIN_UNIVERSES.keys())
    try:
        files = os.listdir(UNIVERSE_DIR)
    except OSError:
        return names
    known_files = set(_BUILTIN_UNIVERSES.values())
    for f in sorted(files):
        if f in _SKIP_FILES or not f.endswith('.csv') or f in known_files:
            continue
        name = f.rsplit('.', 1)[0].replace('_', ' ').title()
        names.append(name)
    return names


def _filename_for(universe_name: str) -> str:
    """Resolve display name to CSV filename."""
    fname = _BUILTIN_UNIVERSES.get(universe_name)
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
    return df['Ticker'].tolist()

