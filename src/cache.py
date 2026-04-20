import os
import pandas as pd
import hashlib
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "data_cache"
CACHE_DIR.mkdir(exist_ok=True)


def _ticker_cache_path(ticker: str) -> Path:
    # Use a hash to avoid issues with special characters
    h = hashlib.sha1(ticker.encode()).hexdigest()
    return CACHE_DIR / f"{ticker}_{h}.parquet"


def load_ticker_from_cache(ticker: str) -> pd.DataFrame | None:
    path = _ticker_cache_path(ticker)
    if path.exists():
        try:
            return pd.read_parquet(path)
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
