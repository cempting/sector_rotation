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
import json
import os
import pandas as pd
import hashlib
import time
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent.parent.parent / "data_cache"
CACHE_DIR.mkdir(exist_ok=True)


def _ticker_cache_path(ticker: str) -> Path:
    # Use a hash to avoid issues with special characters
    ticker_str = str(ticker) if not isinstance(ticker, str) else ticker
    h = hashlib.sha1(ticker_str.encode()).hexdigest()
    return CACHE_DIR / f"{ticker_str}_{h}.parquet"


MIN_CACHE_ROWS = 20  # reject obviously invalid/test cache entries
CACHE_MAX_AGE_SECONDS = 24 * 60 * 60
UNAVAILABLE_TICKERS_FILE = CACHE_DIR / "unavailable_tickers.json"
DEFAULT_TICKER_COOLDOWN_SECONDS = 6 * 60 * 60


def _read_cache_file(path: Path, allow_expired: bool = False) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        if not allow_expired and time.time() - path.stat().st_mtime > CACHE_MAX_AGE_SECONDS:
            return None
        df = pd.read_parquet(path)
        if df is not None and len(df) >= MIN_CACHE_ROWS and "Close" in df.columns:
            return df
        return None
    except Exception:
        return None


def get_ticker_cache_age_seconds(ticker: str) -> int | None:
    path = _ticker_cache_path(ticker)
    if not path.exists():
        return None
    try:
        return int(max(0, time.time() - path.stat().st_mtime))
    except Exception:
        return None


def load_ticker_from_cache(ticker: str) -> pd.DataFrame | None:
    path = _ticker_cache_path(ticker)
    return _read_cache_file(path, allow_expired=False)


def load_ticker_from_cache_any_age(ticker: str) -> pd.DataFrame | None:
    """Load cached data even if it is older than the freshness threshold."""
    path = _ticker_cache_path(ticker)
    return _read_cache_file(path, allow_expired=True)


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


def _read_unavailable_registry() -> dict[str, dict[str, object]]:
    if not UNAVAILABLE_TICKERS_FILE.exists():
        return {}
    try:
        with UNAVAILABLE_TICKERS_FILE.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            return {}
        registry: dict[str, dict[str, object]] = {}
        now = time.time()
        dirty = False
        for raw_ticker, details in payload.items():
            ticker = str(raw_ticker).strip().upper()
            if not ticker or not isinstance(details, dict):
                dirty = True
                continue
            until = float(details.get("until", 0) or 0)
            if until <= now:
                dirty = True
                continue
            registry[ticker] = {
                "until": until,
                "reason": str(details.get("reason", "")),
                "first_seen": float(details.get("first_seen", now) or now),
                "last_seen": float(details.get("last_seen", now) or now),
            }
        if dirty:
            _write_unavailable_registry(registry)
        return registry
    except Exception:
        return {}


def _write_unavailable_registry(registry: dict[str, dict[str, object]]) -> None:
    try:
        with UNAVAILABLE_TICKERS_FILE.open("w", encoding="utf-8") as handle:
            json.dump(registry, handle, indent=2, sort_keys=True)
    except Exception:
        pass


def mark_ticker_temporarily_unavailable(
    ticker: str,
    reason: str = "",
    cooldown_seconds: int = DEFAULT_TICKER_COOLDOWN_SECONDS,
) -> None:
    symbol = str(ticker).strip().upper()
    if not symbol:
        return

    now = time.time()
    until = now + max(60, int(cooldown_seconds))
    registry = _read_unavailable_registry()
    existing = registry.get(symbol, {})
    registry[symbol] = {
        "until": max(until, float(existing.get("until", 0) or 0)),
        "reason": reason,
        "first_seen": float(existing.get("first_seen", now) or now),
        "last_seen": now,
    }
    _write_unavailable_registry(registry)


def clear_ticker_unavailable_flag(ticker: str) -> None:
    symbol = str(ticker).strip().upper()
    if not symbol:
        return
    registry = _read_unavailable_registry()
    if symbol in registry:
        registry.pop(symbol, None)
        _write_unavailable_registry(registry)


def is_ticker_temporarily_unavailable(ticker: str) -> bool:
    symbol = str(ticker).strip().upper()
    if not symbol:
        return False
    registry = _read_unavailable_registry()
    details = registry.get(symbol)
    if not details:
        return False
    return float(details.get("until", 0) or 0) > time.time()


def get_ticker_unavailable_retry_after_seconds(ticker: str) -> int:
    symbol = str(ticker).strip().upper()
    if not symbol:
        return 0
    registry = _read_unavailable_registry()
    details = registry.get(symbol)
    if not details:
        return 0
    return max(0, int(float(details.get("until", 0) or 0) - time.time()))
