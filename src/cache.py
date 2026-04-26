def update_all_ticker_caches(progress_callback=None, force_refresh=False):
    """Update cache for all tickers in the currently selected universe."""
    from .data import fetch_ticker_data_batch
    from .universe import get_universe_tickers
    import time
    try:
        import streamlit as st
        universe = st.session_state.get("selected_universe", "S&P 500")
    except Exception:
        universe = "S&P 500"
    tickers = get_universe_tickers(universe)
    total = len(tickers)
    for i, ticker in enumerate(tickers):
        fetch_ticker_data_batch(ticker, force_refresh=force_refresh)
        if progress_callback:
            progress_callback(i + 1, total, ticker)
        time.sleep(0.05)  # avoid hammering yfinance
import os
import pandas as pd
import hashlib
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "data_cache"
CACHE_DIR.mkdir(exist_ok=True)


def _ticker_cache_path(ticker: str) -> Path:
    # Use a hash to avoid issues with special characters
    ticker_str = str(ticker) if not isinstance(ticker, str) else ticker
    h = hashlib.sha1(ticker_str.encode()).hexdigest()
    return CACHE_DIR / f"{ticker_str}_{h}.parquet"


MIN_CACHE_ROWS = 20  # reject obviously invalid/test cache entries


def load_ticker_from_cache(ticker: str) -> pd.DataFrame | None:
    path = _ticker_cache_path(ticker)
    if path.exists():
        try:
            df = pd.read_parquet(path)
            if df is not None and len(df) >= MIN_CACHE_ROWS and "Close" in df.columns:
                return df
            return None
        except Exception:
            return None
    return None


def save_ticker_to_cache(ticker: str, df: pd.DataFrame) -> None:
    path = _ticker_cache_path(ticker)
    try:
        df.to_parquet(path)
    except Exception:
        pass


def clear_ticker_cache(ticker: str) -> None:
    path = _ticker_cache_path(ticker)
    if path.exists():
        path.unlink()


def clear_tickers_cache(tickers: list) -> None:
    """Clear cache for a list of tickers."""
    for ticker in tickers:
        clear_ticker_cache(ticker)
