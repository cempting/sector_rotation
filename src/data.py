import pandas as pd
import yfinance as yf
from financedatabase import Equities
from .constants import (
    DEFAULT_TOP_TICKERS,
    INDEX_START_VALUE,
    SECTOR_NAME_MAP,
    TICKER_PERIOD,
)
from .cache import load_ticker_from_cache, save_ticker_to_cache, clear_ticker_cache


def get_db_sector_name(sector: str) -> str:
    return SECTOR_NAME_MAP.get(sector, sector)


def load_equities() -> Equities:
    return Equities()


def fetch_sector_data(ticker: str, period: str = TICKER_PERIOD) -> pd.DataFrame:
    try:
        return yf.download(ticker, period=period, progress=False)
    except Exception:
        return pd.DataFrame()


def fetch_sector_industries(sector: str) -> pd.Series:
    db_sector = get_db_sector_name(sector)
    equities = load_equities()
    industries = equities.options("industry", sector=db_sector)
    return pd.Series(sorted(industries.tolist()), name="industry")


def fetch_industry_counts(sector: str) -> pd.Series:
    db_sector = get_db_sector_name(sector)
    equities = load_equities()
    selected = equities.select(sector=db_sector, exclude_exchanges=False)
    return selected["industry"].dropna().value_counts().sort_values(ascending=False)


def validate_ticker(ticker: str) -> bool:
    try:
        df = yf.download(ticker, period="1d", progress=False)
        return not df.empty and "Close" in df.columns
    except Exception:
        return False


def fetch_industry_tickers(sector: str, industry: str, top_n: int = DEFAULT_TOP_TICKERS) -> list[str]:
    db_sector = get_db_sector_name(sector)
    equities = load_equities()
    selected = equities.select(sector=db_sector, industry=industry, exclude_exchanges=False)

    if "market_cap" in selected.columns:
        selected = selected.sort_values("market_cap", ascending=False)

    valid_tickers = []
    for ticker in selected.index:
        if validate_ticker(ticker):
            valid_tickers.append(ticker)
            if len(valid_tickers) >= top_n:
                break

    return valid_tickers


def fetch_industry_stock_list(sector: str, industry: str) -> list[str]:
    db_sector = get_db_sector_name(sector)
    equities = load_equities()
    selected = equities.select(sector=db_sector, industry=industry, exclude_exchanges=False)

    if "market_cap" in selected.columns:
        selected = selected.sort_values("market_cap", ascending=False)

    return [ticker for ticker in selected.index if validate_ticker(ticker)]


def compute_industry_aggregate(tickers: list[str]) -> tuple[pd.Series, pd.Series, int]:
    if not tickers:
        return pd.Series(), pd.Series(), 0

    closes = []
    volumes = []

    for ticker in tickers:
        try:
            df = yf.download(ticker, period="2y", progress=False)
            if not df.empty and "Close" in df.columns and "Volume" in df.columns:
                ticker_close = df["Close"]
                ticker_volume = df["Volume"]
                if not ticker_close.empty:
                    closes.append(ticker_close)
                    volumes.append(ticker_volume)
        except Exception:
            continue

    num_fetched = len(closes)
    if num_fetched == 0:
        return pd.Series(), pd.Series(), 0

    close_df = pd.concat(closes, axis=1, keys=[f"ticker_{i}" for i in range(num_fetched)]).ffill().dropna(axis=0, how="all")
    volume_df = pd.concat(volumes, axis=1, keys=[f"ticker_{i}" for i in range(num_fetched)]).fillna(0)

    pct_changes = close_df.pct_change().mean(axis=1, skipna=True)
    index = (1 + pct_changes).cumprod() * INDEX_START_VALUE
    total_volume = volume_df.sum(axis=1)

    return index, total_volume, num_fetched


def validate_ticker_batch(ticker: str) -> tuple[str, bool]:
    try:
        df = yf.download(ticker, period="1d", progress=False)
        is_valid = not df.empty and "Close" in df.columns
        return ticker, is_valid
    except Exception:
        return ticker, False


def fetch_ticker_data_batch(ticker: str, force_refresh: bool = False) -> tuple[str, pd.DataFrame]:
    """
    Fetch ticker data, using cache unless force_refresh is True.
    """
    if not force_refresh:
        cached = load_ticker_from_cache(ticker)
        if cached is not None and not cached.empty:
            return ticker, cached
    try:
        df = yf.download(ticker, period="6mo", progress=False)
        if not df.empty:
            save_ticker_to_cache(ticker, df)
        return ticker, df
    except Exception:
        return ticker, pd.DataFrame()
